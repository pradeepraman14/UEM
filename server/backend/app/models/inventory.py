import uuid
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class HardwareInventory(Base):
    __tablename__ = "hardware_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # CPU
    cpu_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    cpu_threads: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    cpu_speed_mhz: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    cpu_architecture: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)

    # Memory
    ram_total_mb: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    ram_available_mb: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    ram_slots: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)

    # Storage
    disk_info: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # GPU
    gpu_info: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # BIOS / Firmware
    bios_vendor: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    bios_version: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    bios_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)

    # Motherboard
    motherboard_manufacturer: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    motherboard_model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    # Chassis
    chassis_type: Mapped[str | None] = mapped_column(
        sa.String(50), nullable=True, comment="desktop|laptop|server|tablet|workstation"
    )
    manufacturer: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    # Security
    tpm_version: Mapped[str | None] = mapped_column(sa.String(10), nullable=True)
    tpm_enabled: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    secure_boot: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    virtualization_enabled: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)

    # Battery
    battery_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Display
    monitor_info: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    collected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    raw_wmi: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="hardware_inventory")  # type: ignore[name-defined]


class InstalledSoftware(Base):
    __tablename__ = "installed_software"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    publisher: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    install_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    install_location: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    uninstall_string: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    source: Mapped[str | None] = mapped_column(
        sa.String(50), nullable=True, comment="registry_x64|registry_x86|appx|winget|msi"
    )
    is_64bit: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="installed_software")  # type: ignore[name-defined]

    __table_args__ = (
        sa.UniqueConstraint("device_id", "display_name", "version", name="uq_device_software_version"),
        sa.Index("idx_software_name", "display_name"),
        sa.Index(
            "idx_software_fts",
            sa.func.to_tsvector(
                sa.literal_column("'english'::regconfig"),
                sa.func.coalesce(sa.column("display_name"), "")
                + sa.literal(" ")
                + sa.func.coalesce(sa.column("publisher"), ""),
            ),
            postgresql_using="gin",
        ),
    )


class NetworkInterface(Base):
    __tablename__ = "network_interfaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(sa.String(17), nullable=True)
    ip_addresses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    ipv6_addresses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    gateway: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    dns_servers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    subnet_mask: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    dhcp_enabled: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    dhcp_server: Mapped[str | None] = mapped_column(sa.String(45), nullable=True)
    is_connected: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    speed_mbps: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    adapter_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="network_interfaces")  # type: ignore[name-defined]
