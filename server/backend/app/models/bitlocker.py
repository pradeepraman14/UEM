import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class BitLockerStatus(Base):
    __tablename__ = "bitlocker_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Per-volume status (JSONB array)
    # [{drive: "C:", protection_status: "on", encryption_method: "XtsAes256",
    #   encryption_percentage: 100, lock_status: "unlocked", recovery_key_id: "..."}]
    volumes: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Summary
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    os_volume_protected: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    encryption_method: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    encryption_percentage: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)

    # Recovery keys (encrypted at rest)
    recovery_keys: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Escrow status
    recovery_key_escrowed: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    escrowed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    collected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    device: Mapped["Device"] = relationship("Device", back_populates="bitlocker_status")  # type: ignore[name-defined]
