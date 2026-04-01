import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user
from app.models.device import Device, DeviceGroup, DeviceGroupMember
from app.models.policy import Policy, PolicyAssignment
from app.models.user import User
from app.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate, PolicyAssignRequest

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, require_permission("policy:read")],
    policy_type: str | None = None,
    is_active: bool | None = None,
):
    query = select(Policy)
    if policy_type:
        query = query.where(Policy.policy_type == policy_type)
    if is_active is not None:
        query = query.where(Policy.is_active == is_active)
    result = await db.execute(query.order_by(Policy.priority))
    return [PolicyResponse.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    body: PolicyCreate,
    current_user: Annotated[User, require_permission("policy:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    policy = Policy(**body.model_dump(), created_by_id=current_user.id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, require_permission("policy:read")],
):
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyResponse.model_validate(policy)


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, require_permission("policy:write")],
):
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(policy, field, value)
    policy.version += 1
    await db.commit()
    await db.refresh(policy)
    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, require_permission("policy:write")],
):
    await db.execute(delete(Policy).where(Policy.id == policy_id))
    await db.commit()


@router.post("/{policy_id}/assign")
async def assign_policy(
    policy_id: uuid.UUID,
    body: PolicyAssignRequest,
    current_user: Annotated[User, require_permission("policy:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    assigned_devices: list[uuid.UUID] = []

    # Direct device assignments
    if body.device_ids:
        for device_id in body.device_ids:
            # Check no duplicate
            existing = await db.execute(
                select(PolicyAssignment).where(
                    PolicyAssignment.policy_id == policy_id,
                    PolicyAssignment.device_id == device_id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(PolicyAssignment(
                    policy_id=policy_id,
                    device_id=device_id,
                    assigned_by_id=current_user.id,
                ))
            assigned_devices.append(device_id)

    # Group assignments
    if body.group_ids:
        for group_id in body.group_ids:
            existing = await db.execute(
                select(PolicyAssignment).where(
                    PolicyAssignment.policy_id == policy_id,
                    PolicyAssignment.group_id == group_id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(PolicyAssignment(
                    policy_id=policy_id,
                    group_id=group_id,
                    assigned_by_id=current_user.id,
                ))
            # Get all devices in group
            members = await db.execute(
                select(DeviceGroupMember.device_id).where(DeviceGroupMember.group_id == group_id)
            )
            assigned_devices.extend(members.scalars().all())

    await db.commit()

    # Push policy to online devices
    pushed = 0
    for device_id in set(assigned_devices):
        sent = await ws_manager.send_to_agent(
            device_id,
            {
                "type": "policy_push",
                "payload": {
                    "policy_id": str(policy_id),
                    "policy_type": policy.policy_type,
                    "config": policy.config,
                    "version": policy.version,
                },
            },
        )
        if sent:
            pushed += 1

    return {
        "message": "Policy assigned",
        "devices_targeted": len(set(assigned_devices)),
        "devices_notified": pushed,
    }
