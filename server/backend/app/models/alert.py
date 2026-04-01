import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    alert_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        comment="device_offline|compliance_failure|patch_overdue|disk_space|malware_detected|unauthorized_usb|certificate_expiry|agent_error|custom",
    )
    severity: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, index=True, comment="critical|high|medium|low|info"
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="open",
        index=True,
        comment="open|acknowledged|resolved|suppressed",
    )
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    notification_sent: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    device: Mapped["Device | None"] = relationship("Device", back_populates="alerts")  # type: ignore[name-defined]

    __table_args__ = (
        sa.Index("idx_alerts_open", "status", "severity"),
    )
