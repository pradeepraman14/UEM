import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user, get_device_by_id
from app.models.command import Command
from app.models.device import Device
from app.models.user import User
from app.schemas.command import CommandCreate, CommandResponse

router = APIRouter(prefix="/commands", tags=["Remote Commands"])


@router.post("", response_model=CommandResponse, status_code=201)
async def dispatch_command(
    body: CommandCreate,
    current_user: Annotated[User, require_permission("remote:shell")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Verify device exists
    result = await db.execute(select(Device).where(Device.id == body.device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    correlation_id = str(uuid.uuid4())
    cmd = Command(
        device_id=body.device_id,
        command_type=body.command_type,
        payload=body.payload,
        timeout_seconds=body.timeout_seconds,
        initiated_by_id=current_user.id,
        correlation_id=correlation_id,
    )
    db.add(cmd)
    await db.flush()

    # Dispatch via WebSocket if device is online
    if ws_manager.is_agent_connected(body.device_id):
        sent = await ws_manager.send_to_agent(
            body.device_id,
            {
                "type": "command_dispatch",
                "correlation_id": correlation_id,
                "payload": {
                    "command_id": str(cmd.id),
                    "command_type": body.command_type,
                    **body.payload,
                },
            },
        )
        if sent:
            cmd.status = "sent"
            cmd.sent_at = datetime.now(timezone.utc)
    # else: stays pending, will be sent on next agent connection

    await db.commit()
    await db.refresh(cmd)
    return CommandResponse.model_validate(cmd)


@router.get("/{command_id}", response_model=CommandResponse)
async def get_command(
    command_id: uuid.UUID,
    _: Annotated[User, require_permission("remote:shell")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Command).where(Command.id == command_id))
    cmd = result.scalar_one_or_none()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    return CommandResponse.model_validate(cmd)


@router.get("")
async def list_commands(
    _: Annotated[User, require_permission("remote:shell")],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    query = select(Command)
    if device_id:
        query = query.where(Command.device_id == device_id)
    if status:
        query = query.where(Command.status == status)
    query = query.order_by(Command.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    cmds = result.scalars().all()
    return [CommandResponse.model_validate(c) for c in cmds]
