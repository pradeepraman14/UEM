import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DeviceEnrollRequest(BaseModel):
    """Sent by agent at first-run enrollment."""
    enrollment_token: str
    device_uuid: str
    hostname: str
    fqdn: str | None = None
    serial_number: str | None = None
    os_version: str | None = None
    os_build: str | None = None
    os_edition: str | None = None
    os_architecture: str | None = None
    agent_version: str
    csr_pem: str  # PEM-encoded certificate signing request


class DeviceEnrollResponse(BaseModel):
    device_id: str
    cert_pem: str        # signed device certificate
    ca_cert_pem: str     # CA certificate for verification
    server_url: str
    config: dict[str, Any]  # agent config: intervals, etc.


class DeviceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_name: str
    hostname: str
    fqdn: str | None
    serial_number: str | None
    device_uuid: str
    status: str
    is_online: bool
    last_seen: datetime | None
    ip_address: str | None
    os_version: str | None
    os_build: str | None
    os_edition: str | None
    agent_version: str | None
    platform: str
    compliance_status: str
    compliance_score: int | None
    assigned_user: str | None
    department: str | None
    location: str | None
    tags: list[str] | None
    enrolled_at: datetime | None
    created_at: datetime


class DeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    total: int
    page: int
    page_size: int


class DeviceUpdate(BaseModel):
    device_name: str | None = None
    assigned_user: str | None = None
    assigned_user_email: str | None = None
    department: str | None = None
    location: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class DeviceHeartbeat(BaseModel):
    """Sent by agent periodically."""
    device_id: str
    ip_address: str | None = None
    agent_version: str | None = None
    cpu_usage: float | None = None
    ram_usage_percent: float | None = None
    disk_usage_percent: float | None = None
    uptime_seconds: int | None = None
    logged_in_user: str | None = None
