import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user
from app.models.patch import Patch, DevicePatch, PatchApproval
from app.models.user import User

router = APIRouter(prefix="/patches", tags=["Patch Management"])


@router.get("")
async def list_patches(
    _: Annotated[User, require_permission("patch:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    patch_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    query = select(Patch)
    if patch_type:
        query = query.where(Patch.patch_type == patch_type)
    if severity:
        query = query.where(Patch.severity == severity)
    query = query.order_by(Patch.release_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    patches = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "kb_article_id": p.kb_article_id,
            "title": p.title,
            "patch_type": p.patch_type,
            "severity": p.severity,
            "release_date": p.release_date.isoformat() if p.release_date else None,
            "reboot_required": p.reboot_required,
            "size_bytes": p.size_bytes,
        }
        for p in patches
    ]


@router.post("/approve")
async def approve_patches(
    current_user: Annotated[User, require_permission("patch:approve")],
    db: Annotated[AsyncSession, Depends(get_db)],
    patch_ids: list[uuid.UUID] = ...,
    scheduled_deploy_at: datetime | None = None,
    target_type: str = "all",
    target_id: uuid.UUID | None = None,
    notes: str | None = None,
):
    now = datetime.now(timezone.utc)
    approvals = []
    for patch_id in patch_ids:
        # Check patch exists
        result = await db.execute(select(Patch).where(Patch.id == patch_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Patch {patch_id} not found")

        approval = PatchApproval(
            patch_id=patch_id,
            approved_by_id=current_user.id,
            approved_at=now,
            scheduled_deploy_at=scheduled_deploy_at,
            target_type=target_type,
            target_id=target_id,
            notes=notes,
        )
        db.add(approval)
        approvals.append(patch_id)

    await db.commit()
    return {"message": f"{len(approvals)} patches approved", "patch_ids": [str(p) for p in approvals]}


@router.post("/deploy")
async def deploy_patches(
    current_user: Annotated[User, require_permission("patch:deploy")],
    db: Annotated[AsyncSession, Depends(get_db)],
    device_ids: list[uuid.UUID] | None = None,
    patch_ids: list[uuid.UUID] | None = None,
):
    """Trigger immediate patch installation on devices."""
    if not device_ids:
        raise HTTPException(status_code=400, detail="device_ids required")

    dispatched = 0
    for device_id in device_ids:
        sent = await ws_manager.send_to_agent(
            device_id,
            {
                "type": "patch_trigger",
                "payload": {
                    "patch_ids": [str(p) for p in (patch_ids or [])],
                    "install_all_approved": not patch_ids,
                    "initiated_by": current_user.email,
                },
            },
        )
        if sent:
            dispatched += 1

    return {
        "message": f"Patch deployment triggered on {dispatched} online devices",
        "devices_targeted": len(device_ids),
        "devices_notified": dispatched,
    }


@router.get("/dashboard")
async def patch_dashboard(
    _: Annotated[User, require_permission("patch:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Summary stats for the patch management dashboard."""
    total_patches = (await db.execute(select(func.count(Patch.id)))).scalar()
    critical = (
        await db.execute(
            select(func.count(Patch.id)).where(Patch.severity == "critical")
        )
    ).scalar()
    missing_patches = (
        await db.execute(
            select(func.count(DevicePatch.id)).where(DevicePatch.status == "missing")
        )
    ).scalar()
    installed = (
        await db.execute(
            select(func.count(DevicePatch.id)).where(DevicePatch.status == "installed")
        )
    ).scalar()
    failed = (
        await db.execute(
            select(func.count(DevicePatch.id)).where(DevicePatch.status == "failed")
        )
    ).scalar()

    return {
        "total_patches_in_catalog": total_patches,
        "critical_patches": critical,
        "missing_on_devices": missing_patches,
        "installed": installed,
        "failed": failed,
    }
