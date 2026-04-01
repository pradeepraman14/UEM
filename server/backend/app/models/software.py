import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class SoftwarePackage(Base):
    __tablename__ = "software_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    version: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    # Package file
    filename: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)

    # Install config
    install_type: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, comment="msi|exe|zip|script|winget|choco"
    )
    install_args: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    uninstall_args: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    install_script: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    uninstall_script: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    reboot_required: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    run_as_system: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)

    # Winget / Choco
    winget_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    choco_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    deployments: Mapped[list["SoftwareDeployment"]] = relationship(
        "SoftwareDeployment", back_populates="package", cascade="all, delete-orphan"
    )


class SoftwareDeployment(Base):
    __tablename__ = "software_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("software_packages.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(sa.String(20), nullable=False, comment="install|uninstall|update")
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="pending",
        comment="pending|sent|running|completed|failed|cancelled",
    )
    initiated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    output: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    package: Mapped["SoftwarePackage"] = relationship("SoftwarePackage", back_populates="deployments")
