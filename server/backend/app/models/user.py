import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="readonly",
        comment="superadmin|admin|helpdesk|readonly",
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    mfa_secret: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
