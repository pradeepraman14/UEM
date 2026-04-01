import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        comment="os|patch|security|antivirus|encryption|network|application|custom",
    )
    check_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        comment="os_version|os_build|patch_level|bitlocker_enabled|defender_enabled|defender_updated|firewall_enabled|password_complexity|screen_lock|usb_restricted|software_installed|software_not_installed|registry_value|custom_script",
    )
    operator: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, comment="equals|not_equals|greater_than|less_than|contains|exists|not_exists"
    )
    expected_value: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    severity: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="medium", comment="critical|high|medium|low|info"
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    remediation_hint: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    auto_remediate: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    remediation_command: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    device_compliance: Mapped[list["DeviceCompliance"]] = relationship(
        "DeviceCompliance", back_populates="rule", cascade="all, delete-orphan"
    )


class DeviceCompliance(Base):
    __tablename__ = "device_compliance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("compliance_rules.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, comment="compliant|non_compliant|unknown|error"
    )
    actual_value: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="compliance_records")  # type: ignore[name-defined]
    rule: Mapped["ComplianceRule"] = relationship("ComplianceRule", back_populates="device_compliance")

    __table_args__ = (
        sa.UniqueConstraint("device_id", "rule_id", name="uq_device_compliance_rule"),
        sa.Index("idx_device_compliance_status", "device_id", "status"),
    )
