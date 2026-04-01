import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import require_permission
from app.database import get_db
from app.dependencies import get_device_by_id
from app.models.device import Device
from app.models.inventory import HardwareInventory, InstalledSoftware, NetworkInterface
from app.models.user import User

router = APIRouter(prefix="/devices/{device_id}", tags=["Inventory"])


@router.get("/inventory/hardware")
async def get_hardware_inventory(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(HardwareInventory).where(HardwareInventory.device_id == device.id)
    )
    hw = result.scalar_one_or_none()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware inventory not yet collected")

    return {
        "device_id": str(device.id),
        "cpu": {
            "name": hw.cpu_name,
            "cores": hw.cpu_cores,
            "threads": hw.cpu_threads,
            "speed_mhz": hw.cpu_speed_mhz,
            "architecture": hw.cpu_architecture,
        },
        "memory": {
            "total_mb": hw.ram_total_mb,
            "available_mb": hw.ram_available_mb,
            "slots": hw.ram_slots,
        },
        "storage": hw.disk_info,
        "gpu": hw.gpu_info,
        "bios": {
            "vendor": hw.bios_vendor,
            "version": hw.bios_version,
            "date": hw.bios_date.isoformat() if hw.bios_date else None,
        },
        "system": {
            "manufacturer": hw.manufacturer,
            "model": hw.model,
            "chassis_type": hw.chassis_type,
            "motherboard": hw.motherboard_model,
        },
        "security": {
            "tpm_version": hw.tpm_version,
            "tpm_enabled": hw.tpm_enabled,
            "secure_boot": hw.secure_boot,
            "virtualization": hw.virtualization_enabled,
        },
        "battery": hw.battery_info,
        "monitors": hw.monitor_info,
        "collected_at": hw.collected_at.isoformat(),
    }


@router.get("/inventory/software")
async def get_software_inventory(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = None,
    limit: int = 500,
    offset: int = 0,
):
    query = select(InstalledSoftware).where(InstalledSoftware.device_id == device.id)
    if search:
        query = query.where(InstalledSoftware.display_name.ilike(f"%{search}%"))

    query = query.order_by(InstalledSoftware.display_name).offset(offset).limit(limit)
    result = await db.execute(query)
    apps = result.scalars().all()

    return {
        "device_id": str(device.id),
        "software": [
            {
                "id": str(s.id),
                "name": s.display_name,
                "publisher": s.publisher,
                "version": s.version,
                "install_date": s.install_date.isoformat() if s.install_date else None,
                "size_bytes": s.size_bytes,
                "source": s.source,
                "is_64bit": s.is_64bit,
            }
            for s in apps
        ],
        "total": len(apps),
    }


@router.get("/inventory/network")
async def get_network_inventory(
    device: Annotated[Device, Depends(get_device_by_id)],
    _: Annotated[User, require_permission("device:read")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(NetworkInterface).where(NetworkInterface.device_id == device.id)
    )
    interfaces = result.scalars().all()

    return {
        "device_id": str(device.id),
        "interfaces": [
            {
                "name": i.name,
                "description": i.description,
                "mac_address": i.mac_address,
                "ip_addresses": i.ip_addresses,
                "ipv6_addresses": i.ipv6_addresses,
                "gateway": i.gateway,
                "dns_servers": i.dns_servers,
                "dhcp_enabled": i.dhcp_enabled,
                "is_connected": i.is_connected,
                "speed_mbps": i.speed_mbps,
                "adapter_type": i.adapter_type,
            }
            for i in interfaces
        ],
    }
