import uuid
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class Patch(Base):
    __tablename__ = "patches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_article_id: Mapped[str | None] = mapped_column(sa.String(20), unique=True, nullable=True, index=True)
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    patch_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        comment="security|quality|feature|driver|definition|third_party",
    )
    severity: Mapped[str | None] = mapped_column(
        sa.String(20), nullable=True, comment="critical|important|moderate|low"
    )
    release_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    affected_products: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reboot_required: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    download_url: Mapped[str | None] = mapped_column(sa.String(1000), nullable=True)

    device_patches: Mapped[list["DevicePatch"]] = relationship(
        "DevicePatch", back_populates="patch", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["PatchApproval"]] = relationship(
        "PatchApproval", back_populates="patch", cascade="all, delete-orphan"
    )


class DevicePatch(Base):
    __tablename__ = "device_patches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("patches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        comment="missing|installed|failed|excluded|pending_install",
    )
    installed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="device_patches")  # type: ignore[name-defined]
    patch: Mapped["Patch"] = relationship("Patch", back_populates="device_patches")

    __table_args__ = (
        sa.UniqueConstraint("device_id", "patch_id", name="uq_device_patch"),
    )


class PatchApproval(Base):
    __tablename__ = "patch_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("patches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    scheduled_deploy_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    target_type: Mapped[str] = mapped_column(sa.String(20), comment="all|group|device")
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    patch: Mapped["Patch"] = relationship("Patch", back_populates="approvals")
