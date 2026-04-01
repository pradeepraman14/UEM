from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.database import get_db
from app.dependencies import get_current_user
from app.models.device import Device
from app.models.inventory import InstalledSoftware
from app.models.patch import DevicePatch, Patch
from app.models.compliance import ComplianceRule, DeviceCompliance
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/device-summary")
async def device_summary_report(
    _: Annotated[User, require_permission("report:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    total = (await db.execute(select(func.count(Device.id)))).scalar()
    online = (await db.execute(select(func.count(Device.id)).where(Device.is_online == True))).scalar()
    by_status = await db.execute(
        select(Device.status, func.count(Device.id))
        .group_by(Device.status)
    )
    by_compliance = await db.execute(
        select(Device.compliance_status, func.count(Device.id))
        .group_by(Device.compliance_status)
    )
    by_os = await db.execute(
        select(Device.os_version, func.count(Device.id))
        .group_by(Device.os_version)
        .order_by(func.count(Device.id).desc())
        .limit(10)
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "total_devices": total,
        "online_devices": online,
        "by_status": {r[0]: r[1] for r in by_status.all()},
        "by_compliance": {r[0]: r[1] for r in by_compliance.all()},
        "top_os_versions": [{"os": r[0], "count": r[1]} for r in by_os.all()],
    }


@router.get("/patch-compliance")
async def patch_compliance_report(
    _: Annotated[User, require_permission("report:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    by_status = await db.execute(
        select(DevicePatch.status, func.count(DevicePatch.id))
        .group_by(DevicePatch.status)
    )
    critical_missing = await db.execute(
        select(func.count(DevicePatch.id))
        .join(Patch, Patch.id == DevicePatch.patch_id)
        .where(DevicePatch.status == "missing", Patch.severity == "critical")
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "patch_status_breakdown": {r[0]: r[1] for r in by_status.all()},
        "critical_missing": (await critical_missing).scalar(),
    }


@router.get("/software-inventory")
async def software_inventory_report(
    _: Annotated[User, require_permission("report:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    top_n: int = Query(20, le=100),
):
    top_software = await db.execute(
        select(InstalledSoftware.display_name, InstalledSoftware.publisher, func.count(InstalledSoftware.device_id))
        .group_by(InstalledSoftware.display_name, InstalledSoftware.publisher)
        .order_by(func.count(InstalledSoftware.device_id).desc())
        .limit(top_n)
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "top_installed_software": [
            {"name": r[0], "publisher": r[1], "device_count": r[2]}
            for r in top_software.all()
        ],
    }


@router.get("/compliance-summary")
async def compliance_summary_report(
    _: Annotated[User, require_permission("report:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    failing_rules = await db.execute(
        select(
            ComplianceRule.name,
            ComplianceRule.category,
            ComplianceRule.severity,
            func.count(DeviceCompliance.device_id).label("fail_count"),
        )
        .join(DeviceCompliance, DeviceCompliance.rule_id == ComplianceRule.id)
        .where(DeviceCompliance.status == "non_compliant")
        .group_by(ComplianceRule.id)
        .order_by(func.count(DeviceCompliance.device_id).desc())
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "failing_rules": [
            {
                "rule": r[0],
                "category": r[1],
                "severity": r[2],
                "failing_device_count": r[3],
            }
            for r in failing_rules.all()
        ],
    }
