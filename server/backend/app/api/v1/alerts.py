import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.user import User

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("")
async def list_alerts(
    _: Annotated[User, require_permission("alert:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    severity: str | None = None,
    device_id: uuid.UUID | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    query = select(Alert)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)
    if device_id:
        query = query.where(Alert.device_id == device_id)

    count_q = select(func.count(Alert.id))
    if status:
        count_q = count_q.where(Alert.status == status)
    total = (await db.execute(count_q)).scalar()

    result = await db.execute(
        query.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
    )
    alerts = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": str(a.id),
                "device_id": str(a.device_id) if a.device_id else None,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            }
            for a in alerts
        ],
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    current_user: Annotated[User, require_permission("alert:manage")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_by_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Alert acknowledged"}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: uuid.UUID,
    current_user: Annotated[User, require_permission("alert:manage")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Alert resolved"}


@router.get("/summary")
async def alert_summary(
    _: Annotated[User, require_permission("alert:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    open_count = (
        await db.execute(select(func.count(Alert.id)).where(Alert.status == "open"))
    ).scalar()
    critical = (
        await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "open", Alert.severity == "critical")
        )
    ).scalar()
    high = (
        await db.execute(
            select(func.count(Alert.id)).where(Alert.status == "open", Alert.severity == "high")
        )
    ).scalar()

    return {
        "open_alerts": open_count,
        "critical": critical,
        "high": high,
        "medium": open_count - critical - high,
    }
