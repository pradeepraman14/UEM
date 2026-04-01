import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pki import issue_device_certificate, get_ca_cert_pem
from app.core.rbac import require_permission
from app.core.ws_manager import manager as ws_manager
from app.database import get_db
from app.dependencies import get_current_user, get_device_by_id
from app.models.device import Device, DeviceCertificate
from app.models.user import User
from app.schemas.device import (
    DeviceEnrollRequest,
    DeviceEnrollResponse,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
)
from app.config import settings

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/enroll", response_model=DeviceEnrollResponse)
async def enroll_device(
    body: DeviceEnrollRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Agent calls this endpoint at first-run to enroll and receive a certificate."""
    # Check for existing device by UUID
    result = await db.execute(
        select(Device).where(Device.device_uuid == body.device_uuid)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.status not in ("pending", "inactive"):
        # Re-enrollment allowed for inactive devices
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already enrolled. Use re-enrollment endpoint.",
        )

    # Issue certificate from our CA
    cert_pem, _key_pem, serial_hex, thumbprint = issue_device_certificate(
        device_uuid=body.device_uuid,
        hostname=body.hostname,
    )

    now = datetime.now(timezone.utc)

    if existing:
        device = existing
        device.status = "active"
        device.hostname = body.hostname
        device.fqdn = body.fqdn
        device.os_version = body.os_version
        device.os_build = body.os_build
        device.agent_version = body.agent_version
        device.enrolled_at = now
    else:
        device = Device(
            device_name=body.hostname,
            hostname=body.hostname,
            fqdn=body.fqdn,
            serial_number=body.serial_number,
            device_uuid=body.device_uuid,
            os_version=body.os_version,
            os_build=body.os_build,
            os_edition=body.os_edition,
            os_architecture=body.os_architecture,
            agent_version=body.agent_version,
            enrollment_method="manual",
            enrolled_at=now,
            status="active",
        )
        db.add(device)
        await db.flush()

    # Store/update certificate record
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    cert_obj = x509.load_pem_x509_certificate(cert_pem.encode())

    if existing and existing.certificate:
        cert_record = existing.certificate
        cert_record.cert_pem = cert_pem
        cert_record.serial_number = serial_hex
        cert_record.thumbprint = thumbprint
        cert_record.issued_at = cert_obj.not_valid_before_utc
        cert_record.expires_at = cert_obj.not_valid_after_utc
        cert_record.revoked_at = None
        cert_record.is_active = True
    else:
        cert_record = DeviceCertificate(
            device_id=device.id,
            serial_number=serial_hex,
            thumbprint=thumbprint,
            subject_dn=f"CN=uem-device-{body.device_uuid}",
            issued_at=cert_obj.not_valid_before_utc,
            expires_at=cert_obj.not_valid_after_utc,
            cert_pem=cert_pem,
        )
        db.add(cert_record)

    await db.commit()
    await db.refresh(device)

    return DeviceEnrollResponse(
        device_id=str(device.id),
        cert_pem=cert_pem,
        ca_cert_pem=get_ca_cert_pem(),
        server_url=settings.SERVER_BASE_URL,
        config={
            "heartbeat_interval": settings.AGENT_HEARTBEAT_INTERVAL,
            "inventory_interval": settings.AGENT_INVENTORY_INTERVAL,
            "patch_check_interval": settings.AGENT_PATCH_CHECK_INTERVAL,
            "ws_url": f"{settings.SERVER_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/agent/{device.id}",
        },
    )


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, require_permission("device:read")],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: str | None = None,
    compliance_status: str | None = None,
    is_online: bool | None = None,
    search: str | None = None,
):
    query = select(Device)
    count_query = select(func.count(Device.id))

    if status:
        query = query.where(Device.status == status)
        count_query = count_query.where(Device.status == status)
    if compliance_status:
        query = query.where(Device.compliance_status == compliance_status)
        count_query = count_query.where(Device.compliance_status == compliance_status)
    if is_online is not None:
        query = query.where(Device.is_online == is_online)
        count_query = count_query.where(Device.is_online == is_online)
    if search:
        pattern = f"%{search}%"
        from sqlalchemy import or_
        query = query.where(
            or_(
                Device.hostname.ilike(pattern),
                Device.device_name.ilike(pattern),
                Device.assigned_user.ilike(pattern),
                Device.ip_address.ilike(pattern),
            )
        )
        count_query = count_query.where(
            or_(
                Device.hostname.ilike(pattern),
                Device.device_name.ilike(pattern),
                Device.assigned_user.ilike(pattern),
                Device.ip_address.ilike(pattern),
            )
        )

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Device.last_seen.desc().nulls_last()).offset(offset).limit(page_size)
    )
    devices = result.scalars().all()

    return DeviceListResponse(
        items=[DeviceResponse.model_validate(d) for d in devices],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:read")],
):
    return DeviceResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    body: DeviceUpdate,
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:write")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(device, field, value)
    await db.commit()
    await db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/retire")
async def retire_device(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:retire")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    device.status = "retired"
    # Revoke certificate
    if device.certificate:
        device.certificate.revoked_at = datetime.now(timezone.utc)
        device.certificate.revocation_reason = "device_retired"
        device.certificate.is_active = False
    await db.commit()
    return {"message": "Device retired"}


@router.post("/{device_id}/wipe")
async def wipe_device(
    device: Annotated[Device, Depends(get_device_by_id)],
    current_user: Annotated[User, require_permission("device:wipe")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Send remote wipe command to device."""
    from app.models.command import Command
    cmd = Command(
        device_id=device.id,
        command_type="wipe",
        payload={"confirm": True, "initiated_by": current_user.email},
        initiated_by_id=current_user.id,
        correlation_id=str(uuid.uuid4()),
    )
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)

    # Dispatch over WebSocket
    await ws_manager.send_to_agent(
        device.id,
        {
            "type": "command_dispatch",
            "correlation_id": str(cmd.id),
            "payload": {"command_type": "wipe", "confirm": True},
        },
    )

    return {"message": "Wipe command dispatched", "command_id": str(cmd.id)}


@router.get("/{device_id}/status")
async def device_status(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:read")],
):
    return {
        "device_id": str(device.id),
        "is_online": ws_manager.is_agent_connected(device.id),
        "status": device.status,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "compliance_status": device.compliance_status,
        "compliance_score": device.compliance_score,
    }


@router.post("/generate-token")
async def generate_enrollment_token(
    _: Annotated[User, require_permission("device:write")],
):
    """Generate a one-time enrollment token for manual agent enrollment."""
    token = secrets.token_urlsafe(32)
    return {"enrollment_token": token, "expires_in": 86400}
