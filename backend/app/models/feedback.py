"""Feedback SQLAlchemy 2.x Model."""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Feedback(Base):
    """SQLAlchemy 2.x model representing student feedback."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        doc="Unique feedback record identifier",
    )
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Academic department the feedback relates to",
    )
    semester: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Academic semester (e.g., Semester 4, Fall 2026)",
    )
    feedback_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw text feedback provided by the student",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware timestamp of when feedback was submitted",
    )

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, department='{self.department}', semester='{self.semester}')>"
