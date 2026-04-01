import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        comment="shell|powershell|file_upload|file_download|install|uninstall|reboot|shutdown|lock|wipe|patch_install|policy_apply",
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending|sent|running|completed|failed|timeout|cancelled",
    )
    output: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    initiated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(sa.Integer, default=300, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, unique=True)

    device: Mapped["Device"] = relationship("Device", back_populates="commands")  # type: ignore[name-defined]

    __table_args__ = (
        sa.Index("idx_commands_status_device", "device_id", "status"),
        sa.Index("idx_commands_correlation", "correlation_id"),
    )
