import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user, get_device_by_id
from app.models.bitlocker import BitLockerStatus
from app.models.device import Device
from app.models.user import User

router = APIRouter(prefix="/bitlocker", tags=["BitLocker"])


@router.get("/status")
async def bitlocker_overview(
    _: Annotated[User, require_permission("bitlocker:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """Get BitLocker status across all devices."""
    result = await db.execute(
        select(BitLockerStatus, Device.hostname, Device.device_name, Device.status)
        .join(Device, Device.id == BitLockerStatus.device_id)
        .order_by(BitLockerStatus.collected_at.desc())
        .offset(offset)
        .limit(limit)
    )

    rows = result.all()
    enabled_count = sum(1 for r in rows if r[0].is_enabled)
    total = len(rows)

    return {
        "summary": {
            "total": total,
            "enabled": enabled_count,
            "disabled": total - enabled_count,
            "coverage_percent": round(enabled_count / total * 100, 1) if total else 0,
        },
        "devices": [
            {
                "device_id": str(r[0].device_id),
                "hostname": r[1],
                "device_name": r[2],
                "device_status": r[3],
                "is_enabled": r[0].is_enabled,
                "os_volume_protected": r[0].os_volume_protected,
                "encryption_method": r[0].encryption_method,
                "encryption_percentage": r[0].encryption_percentage,
                "recovery_key_escrowed": r[0].recovery_key_escrowed,
                "collected_at": r[0].collected_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/{device_id}")
async def get_device_bitlocker(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("bitlocker:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(BitLockerStatus).where(BitLockerStatus.device_id == device.id)
    )
    bl = result.scalar_one_or_none()
    if not bl:
        raise HTTPException(status_code=404, detail="BitLocker status not collected yet")

    return {
        "device_id": str(device.id),
        "hostname": device.hostname,
        "is_enabled": bl.is_enabled,
        "os_volume_protected": bl.os_volume_protected,
        "encryption_method": bl.encryption_method,
        "encryption_percentage": bl.encryption_percentage,
        "volumes": bl.volumes,
        "recovery_key_escrowed": bl.recovery_key_escrowed,
        "escrowed_at": bl.escrowed_at.isoformat() if bl.escrowed_at else None,
        "collected_at": bl.collected_at.isoformat(),
    }


@router.get("/{device_id}/recovery-key")
async def get_recovery_key(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("bitlocker:recovery_key")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(BitLockerStatus).where(BitLockerStatus.device_id == device.id)
    )
    bl = result.scalar_one_or_none()
    if not bl or not bl.recovery_keys:
        raise HTTPException(status_code=404, detail="No recovery keys stored")

    return {
        "device_id": str(device.id),
        "hostname": device.hostname,
        "recovery_keys": bl.recovery_keys,
        "escrowed_at": bl.escrowed_at.isoformat() if bl.escrowed_at else None,
    }


@router.post("/{device_id}/enable")
async def enable_bitlocker(
    device: Annotated[Device, Depends(get_device_by_id)],
    current_user: Annotated[User, require_permission("bitlocker:manage")],
    db: Annotated[AsyncSession, Depends(get_db)],
    drive: str = "C:",
    encryption_method: str = "XtsAes256",
    escrow_recovery_key: bool = True,
):
    from app.models.command import Command
    cmd = Command(
        device_id=device.id,
        command_type="policy_apply",
        payload={
            "action": "enable_bitlocker",
            "drive": drive,
            "encryption_method": encryption_method,
            "escrow_recovery_key": escrow_recovery_key,
        },
        initiated_by_id=current_user.id,
        correlation_id=str(uuid.uuid4()),
    )
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)

    await ws_manager.send_to_agent(
        device.id,
        {
            "type": "command_dispatch",
            "correlation_id": str(cmd.id),
            "payload": cmd.payload,
        },
    )
    return {"message": "BitLocker enable command dispatched", "command_id": str(cmd.id)}
