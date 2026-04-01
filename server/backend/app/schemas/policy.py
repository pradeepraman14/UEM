import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    description: str | None = None
    policy_type: str
    config: dict[str, Any]
    priority: int = 100


class PolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    priority: int | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str | None
    policy_type: str
    config: dict[str, Any]
    priority: int
    is_active: bool
    version: int
    created_at: datetime


class PolicyAssignRequest(BaseModel):
    device_ids: list[uuid.UUID] | None = None
    group_ids: list[uuid.UUID] | None = None


# Policy config schemas per type
class PasswordPolicyConfig(BaseModel):
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_numbers: bool = True
    require_symbols: bool = False
    max_age_days: int = 90
    min_age_days: int = 1
    history_count: int = 5
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 30


class ScreenLockPolicyConfig(BaseModel):
    idle_timeout_minutes: int = 15
    require_password_on_wake: bool = True


class FirewallPolicyConfig(BaseModel):
    domain_profile: str = "on"     # on|off|not_configured
    private_profile: str = "on"
    public_profile: str = "on"
    block_all_inbound: bool = False
    rules: list[dict[str, Any]] = []


class USBPolicyConfig(BaseModel):
    block_removable_storage: bool = False
    block_all_usb: bool = False
    allowed_device_ids: list[str] = []
    audit_only: bool = False


class BitLockerPolicyConfig(BaseModel):
    require_encryption: bool = True
    encryption_method: str = "XtsAes256"
    require_tpm: bool = True
    recovery_key_escrow: bool = True
    pin_required: bool = False
