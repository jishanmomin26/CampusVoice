"""User SQLAlchemy 2.x Model (Step 9.12)."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.roles import UserRole


class User(Base):
    """SQLAlchemy 2.x model representing system users (students and admins)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        doc="Unique user identifier",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique login username",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="One-way salted bcrypt password hash",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default=UserRole.STUDENT.value,
        nullable=False,
        doc="User role: 'student' or 'admin'",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the account is active and allowed to authenticate",
    )
    google_sub: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        doc="Google OpenID Connect stable subject identifier (sub)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware timestamp of account creation",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}', is_active={self.is_active})>"
