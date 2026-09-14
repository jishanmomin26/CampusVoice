"""Feedback SQLAlchemy 2.x Model."""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, Integer, String, Text, func
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
    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Academic department the feedback relates to",
    )
    semester: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Academic semester (e.g., Semester 4, Fall 2026)",
    )
    feedback_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw text feedback provided by the student",
    )
    clean_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="NLP-preprocessed normalized text with negation preserved",
    )
    sentiment_label: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Numeric sentiment label (-1 for negative, 0 for neutral, 1 for positive)",
    )
    sentiment_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Canonical sentiment name (negative, neutral, positive)",
    )
    sentiment_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Calibrated confidence score for the predicted sentiment",
    )
    category_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Identified feedback category (e.g., Teaching, Lab Work)",
    )
    category_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Confidence score for the predicted category",
    )
    priority_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Deterministic priority score between 0 and 100",
    )
    priority_level: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Priority tier: High, Medium, or Low",
    )
    priority_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Explainable administrative reasoning for priority assignment",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timezone-aware timestamp of when feedback was submitted",
    )

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, department='{self.department}', semester='{self.semester}')>"

