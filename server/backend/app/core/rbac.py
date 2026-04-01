"""Role-Based Access Control."""
from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import HTTPException, status


class Role(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    HELPDESK = "helpdesk"
    READONLY = "readonly"


# Role hierarchy: higher index = more privileges
ROLE_LEVELS = {
    Role.READONLY: 0,
    Role.HELPDESK: 1,
    Role.ADMIN: 2,
    Role.SUPERADMIN: 3,
}


def has_role(user_role: str, required_role: Role) -> bool:
    """Check if user role meets or exceeds required role level."""
    user_level = ROLE_LEVELS.get(Role(user_role), -1)
    required_level = ROLE_LEVELS.get(required_role, 99)
    return user_level >= required_level


PERMISSIONS = {
    # Device management
    "device:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "device:write": [Role.ADMIN, Role.SUPERADMIN],
    "device:delete": [Role.SUPERADMIN],
    "device:wipe": [Role.SUPERADMIN],
    "device:retire": [Role.ADMIN, Role.SUPERADMIN],

    # Remote tools
    "remote:shell": [Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "remote:file_transfer": [Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "remote:reboot": [Role.ADMIN, Role.SUPERADMIN],
    "remote:lock": [Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],

    # Policies
    "policy:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "policy:write": [Role.ADMIN, Role.SUPERADMIN],

    # Patches
    "patch:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "patch:approve": [Role.ADMIN, Role.SUPERADMIN],
    "patch:deploy": [Role.ADMIN, Role.SUPERADMIN],

    # Software
    "software:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "software:deploy": [Role.ADMIN, Role.SUPERADMIN],
    "software:upload": [Role.ADMIN, Role.SUPERADMIN],

    # BitLocker
    "bitlocker:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "bitlocker:manage": [Role.ADMIN, Role.SUPERADMIN],
    "bitlocker:recovery_key": [Role.ADMIN, Role.SUPERADMIN],

    # Compliance
    "compliance:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "compliance:write": [Role.ADMIN, Role.SUPERADMIN],

    # Users
    "user:read": [Role.ADMIN, Role.SUPERADMIN],
    "user:write": [Role.SUPERADMIN],

    # Reports
    "report:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "report:export": [Role.ADMIN, Role.SUPERADMIN],

    # Alerts
    "alert:read": [Role.READONLY, Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],
    "alert:manage": [Role.HELPDESK, Role.ADMIN, Role.SUPERADMIN],

    # Settings
    "settings:read": [Role.ADMIN, Role.SUPERADMIN],
    "settings:write": [Role.SUPERADMIN],
}


def check_permission(user_role: str, permission: str) -> bool:
    allowed_roles = PERMISSIONS.get(permission, [])
    return any(has_role(user_role, r) for r in allowed_roles)


def require_permission(permission: str):
    """FastAPI dependency factory for permission checking."""
    from fastapi import Depends
    from app.dependencies import get_current_user
    from app.models.user import User

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return current_user

    return Depends(_check)
