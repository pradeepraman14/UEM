import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CommandCreate(BaseModel):
    device_id: uuid.UUID
    command_type: str
    payload: dict[str, Any] = {}
    timeout_seconds: int = 300


class CommandResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: uuid.UUID
    command_type: str
    payload: dict[str, Any]
    status: str
    output: str | None
    exit_code: int | None
    error_message: str | None
    sent_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


# Specific command payloads
class ShellCommandPayload(BaseModel):
    command: str
    shell: str = "powershell"  # powershell|cmd


class FileUploadPayload(BaseModel):
    destination_path: str
    file_name: str
    chunk_size: int = 65536


class FileDownloadPayload(BaseModel):
    source_path: str


class InstallPackagePayload(BaseModel):
    package_id: str
    package_url: str | None = None
    install_args: str | None = None


class RebootPayload(BaseModel):
    delay_seconds: int = 0
    force: bool = False
    message: str | None = None
