import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.device import Device, DeviceGroup, DeviceGroupMember
from app.models.user import User

router = APIRouter(prefix="/groups", tags=["Device Groups"])


@router.get("")
async def list_groups(
    _: Annotated[User, require_permission("device:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceGroup).order_by(DeviceGroup.name))
    groups = result.scalars().all()
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "is_dynamic": g.is_dynamic,
            "color": g.color,
        }
        for g in groups
    ]


@router.post("", status_code=201)
async def create_group(
    _: Annotated[User, require_permission("device:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str = ...,
    description: str | None = None,
    is_dynamic: bool = False,
    dynamic_filter: dict | None = None,
    color: str | None = None,
):
    group = DeviceGroup(
        name=name,
        description=description,
        is_dynamic=is_dynamic,
        dynamic_filter=dynamic_filter,
        color=color,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return {"id": str(group.id), "name": group.name}


@router.post("/{group_id}/members")
async def add_devices_to_group(
    group_id: uuid.UUID,
    device_ids: list[uuid.UUID],
    _: Annotated[User, require_permission("device:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(DeviceGroup).where(DeviceGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    added = 0
    for device_id in device_ids:
        existing = await db.execute(
            select(DeviceGroupMember).where(
                DeviceGroupMember.group_id == group_id,
                DeviceGroupMember.device_id == device_id,
            )
        )
        if not existing.scalar_one_or_none():
            db.add(DeviceGroupMember(group_id=group_id, device_id=device_id))
            added += 1

    await db.commit()
    return {"message": f"{added} devices added to group"}


@router.get("/{group_id}/members")
async def get_group_members(
    group_id: uuid.UUID,
    _: Annotated[User, require_permission("device:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Device)
        .join(DeviceGroupMember, DeviceGroupMember.device_id == Device.id)
        .where(DeviceGroupMember.group_id == group_id)
    )
    devices = result.scalars().all()
    return [
        {"id": str(d.id), "hostname": d.hostname, "status": d.status, "is_online": d.is_online}
        for d in devices
    ]
