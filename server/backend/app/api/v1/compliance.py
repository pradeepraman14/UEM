import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.database import get_db
from app.dependencies import get_current_user, get_device_by_id
from app.models.compliance import ComplianceRule, DeviceCompliance
from app.models.device import Device
from app.models.user import User
from app.schemas.policy import PolicyCreate

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get("/dashboard")
async def compliance_dashboard(
    _: Annotated[User, require_permission("compliance:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    total_devices = (await db.execute(select(func.count(Device.id)))).scalar()
    compliant = (
        await db.execute(
            select(func.count(Device.id)).where(Device.compliance_status == "compliant")
        )
    ).scalar()
    non_compliant = (
        await db.execute(
            select(func.count(Device.id)).where(Device.compliance_status == "non_compliant")
        )
    ).scalar()
    unknown = (
        await db.execute(
            select(func.count(Device.id)).where(Device.compliance_status == "unknown")
        )
    ).scalar()

    # Top failing rules
    failing = await db.execute(
        select(
            ComplianceRule.name,
            ComplianceRule.severity,
            func.count(DeviceCompliance.id).label("fail_count"),
        )
        .join(DeviceCompliance, DeviceCompliance.rule_id == ComplianceRule.id)
        .where(DeviceCompliance.status == "non_compliant")
        .group_by(ComplianceRule.id)
        .order_by(func.count(DeviceCompliance.id).desc())
        .limit(10)
    )

    return {
        "summary": {
            "total_devices": total_devices,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "unknown": unknown,
            "compliance_rate": round(compliant / total_devices * 100, 1) if total_devices else 0,
        },
        "top_failing_rules": [
            {"rule_name": r[0], "severity": r[1], "failing_devices": r[2]}
            for r in failing.all()
        ],
    }


@router.get("/rules")
async def list_rules(
    _: Annotated[User, require_permission("compliance:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    is_active: bool | None = None,
):
    query = select(ComplianceRule)
    if category:
        query = query.where(ComplianceRule.category == category)
    if is_active is not None:
        query = query.where(ComplianceRule.is_active == is_active)
    result = await db.execute(query.order_by(ComplianceRule.severity, ComplianceRule.name))
    rules = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "category": r.category,
            "check_type": r.check_type,
            "severity": r.severity,
            "is_active": r.is_active,
            "remediation_hint": r.remediation_hint,
            "auto_remediate": r.auto_remediate,
        }
        for r in rules
    ]


@router.post("/rules", status_code=201)
async def create_rule(
    current_user: Annotated[User, require_permission("compliance:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str = ...,
    category: str = ...,
    check_type: str = ...,
    operator: str = ...,
    severity: str = "medium",
    expected_value: str | None = None,
    description: str | None = None,
    remediation_hint: str | None = None,
    auto_remediate: bool = False,
):
    rule = ComplianceRule(
        name=name,
        description=description,
        category=category,
        check_type=check_type,
        operator=operator,
        severity=severity,
        expected_value=expected_value,
        remediation_hint=remediation_hint,
        auto_remediate=auto_remediate,
        created_by_id=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": str(rule.id), "message": "Compliance rule created"}


@router.get("/devices/{device_id}")
async def device_compliance_detail(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("compliance:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(DeviceCompliance, ComplianceRule.name, ComplianceRule.severity, ComplianceRule.category)
        .join(ComplianceRule, ComplianceRule.id == DeviceCompliance.rule_id)
        .where(DeviceCompliance.device_id == device.id)
        .order_by(ComplianceRule.severity)
    )
    rows = result.all()

    return {
        "device_id": str(device.id),
        "hostname": device.hostname,
        "compliance_status": device.compliance_status,
        "compliance_score": device.compliance_score,
        "last_check": device.last_compliance_check.isoformat() if device.last_compliance_check else None,
        "checks": [
            {
                "rule_name": r[1],
                "severity": r[2],
                "category": r[3],
                "status": r[0].status,
                "actual_value": r[0].actual_value,
                "checked_at": r[0].checked_at.isoformat(),
            }
            for r in rows
        ],
    }
