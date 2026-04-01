import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    actor_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)
    resource_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    outcome: Mapped[str] = mapped_column(sa.String(20), default="success", comment="success|failure")

    __table_args__ = (
        sa.Index("idx_audit_logs_time", "created_at"),
        sa.Index("idx_audit_logs_actor", "actor_user_id", "created_at"),
        sa.Index("idx_audit_logs_resource", "resource_type", "resource_id"),
    )
