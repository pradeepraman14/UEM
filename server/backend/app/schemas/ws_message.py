"""
WebSocket message envelope schemas.
All WS messages use a typed envelope for routing.
"""
from typing import Any, Literal

from pydantic import BaseModel


class WSMessage(BaseModel):
    """Base WebSocket message envelope."""
    type: str
    device_id: str | None = None
    correlation_id: str | None = None
    timestamp: str | None = None
    payload: dict[str, Any] = {}


# Agent → Server
class HeartbeatMessage(WSMessage):
    type: Literal["heartbeat"] = "heartbeat"


class InventoryUpdateMessage(WSMessage):
    type: Literal["inventory_update"] = "inventory_update"


class CommandResultMessage(WSMessage):
    type: Literal["command_result"] = "command_result"


class ComplianceReportMessage(WSMessage):
    type: Literal["compliance_report"] = "compliance_report"


class AlertMessage(WSMessage):
    type: Literal["alert"] = "alert"


class FileChunkMessage(WSMessage):
    type: Literal["file_chunk"] = "file_chunk"


# Server → Agent
class PolicyPushMessage(WSMessage):
    type: Literal["policy_push"] = "policy_push"


class CommandDispatchMessage(WSMessage):
    type: Literal["command_dispatch"] = "command_dispatch"


class PatchTriggerMessage(WSMessage):
    type: Literal["patch_trigger"] = "patch_trigger"


class ConfigUpdateMessage(WSMessage):
    type: Literal["config_update"] = "config_update"


class PingMessage(WSMessage):
    type: Literal["ping"] = "ping"


# Server → Console
class DeviceStatusChangedMessage(WSMessage):
    type: Literal["device_status_changed"] = "device_status_changed"


class NewAlertMessage(WSMessage):
    type: Literal["new_alert"] = "new_alert"
