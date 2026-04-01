import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INET, JSONB

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    hostname: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    fqdn: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(sa.String(100), unique=True, nullable=True)
    device_uuid: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False, index=True)

    # Enrollment
    enrollment_token: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    enrolled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    enrollment_method: Mapped[str | None] = mapped_column(
        sa.String(50), nullable=True, comment="manual|gpo|bulk_csv|self_service"
    )

    # Status
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="pending|active|inactive|quarantined|retired",
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True, index=True
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    is_online: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False, index=True)

    # Network
    ip_address: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(sa.String(17), nullable=True)

    # OS / Agent
    os_version: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    os_build: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    os_edition: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    os_architecture: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    platform: Mapped[str] = mapped_column(sa.String(50), default="windows", nullable=False)

    # Compliance
    compliance_status: Mapped[str] = mapped_column(
        sa.String(50),
        default="unknown",
        index=True,
        comment="compliant|non_compliant|unknown",
    )
    compliance_score: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    last_compliance_check: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # User / Identity
    assigned_user: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    assigned_user_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    # Metadata
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(sa.Text), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    certificate: Mapped["DeviceCertificate | None"] = relationship(
        "DeviceCertificate", back_populates="device", uselist=False, cascade="all, delete-orphan"
    )
    hardware_inventory: Mapped["HardwareInventory | None"] = relationship(  # type: ignore[name-defined]
        "HardwareInventory", back_populates="device", uselist=False, cascade="all, delete-orphan"
    )
    installed_software: Mapped[list["InstalledSoftware"]] = relationship(  # type: ignore[name-defined]
        "InstalledSoftware", back_populates="device", cascade="all, delete-orphan"
    )
    network_interfaces: Mapped[list["NetworkInterface"]] = relationship(  # type: ignore[name-defined]
        "NetworkInterface", back_populates="device", cascade="all, delete-orphan"
    )
    commands: Mapped[list["Command"]] = relationship(  # type: ignore[name-defined]
        "Command", back_populates="device", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(  # type: ignore[name-defined]
        "Alert", back_populates="device", cascade="all, delete-orphan"
    )
    bitlocker_status: Mapped["BitLockerStatus | None"] = relationship(  # type: ignore[name-defined]
        "BitLockerStatus", back_populates="device", uselist=False, cascade="all, delete-orphan"
    )
    compliance_records: Mapped[list["DeviceCompliance"]] = relationship(  # type: ignore[name-defined]
        "DeviceCompliance", back_populates="device", cascade="all, delete-orphan"
    )
    device_patches: Mapped[list["DevicePatch"]] = relationship(  # type: ignore[name-defined]
        "DevicePatch", back_populates="device", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.Index("idx_devices_status_online", "status", "is_online"),
        sa.Index("idx_devices_compliance", "compliance_status"),
        sa.Index("idx_devices_last_seen", "last_seen"),
    )


class DeviceCertificate(Base):
    __tablename__ = "device_certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    serial_number: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    thumbprint: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    subject_dn: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    cert_pem: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="certificate")


class DeviceGroup(Base):
    __tablename__ = "device_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_dynamic: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    dynamic_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    color: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)

    members: Mapped[list["DeviceGroupMember"]] = relationship(
        "DeviceGroupMember", back_populates="group", cascade="all, delete-orphan"
    )


class DeviceGroupMember(Base):
    __tablename__ = "device_group_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("device_groups.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )

    group: Mapped["DeviceGroup"] = relationship("DeviceGroup", back_populates="members")

    __table_args__ = (
        sa.UniqueConstraint("group_id", "device_id", name="uq_group_device"),
        sa.Index("idx_group_members_device", "device_id"),
    )
