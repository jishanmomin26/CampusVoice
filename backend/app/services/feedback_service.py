"""Service module for persisting feedback and analysis records."""

import logging
from typing import Any, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.feedback import Feedback

logger = logging.getLogger(__name__)


def save_analyzed_feedback(
    db: Session,
    feedback_text: str,
    analysis_result: Dict[str, Any],
    department: Optional[str] = None,
    semester: Optional[str] = None,
) -> Feedback:
    """Persists a feedback submission alongside its precomputed analysis results.

    Args:
        db: Active SQLAlchemy database session.
        feedback_text: The original raw feedback submitted by the student.
        analysis_result: Precomputed intelligence dictionary from FeedbackIntelligencePipeline.
        department: Optional department name if provided.
        semester: Optional semester or term if provided.

    Returns:
        Feedback: The freshly persisted and refreshed SQLAlchemy record.

    Raises:
        SQLAlchemyError: If an error occurs during database insertion or commit.
    """
    sentiment_data = analysis_result.get("sentiment", {})
    category_data = analysis_result.get("category", {})
    priority_data = analysis_result.get("priority", {})

    record = Feedback(
        feedback_text=feedback_text,
        department=department,
        semester=semester,
        clean_text=analysis_result.get("clean_text"),
        sentiment_label=sentiment_data.get("label"),
        sentiment_name=sentiment_data.get("name"),
        sentiment_confidence=sentiment_data.get("confidence"),
        category_name=category_data.get("name"),
        category_confidence=category_data.get("confidence"),
        priority_score=priority_data.get("score"),
        priority_level=priority_data.get("level"),
        priority_reason=priority_data.get("reason"),
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Successfully persisted analyzed feedback with ID: %s", record.id)
        return record
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database rollback triggered while persisting analyzed feedback: %s",
            exc,
        )
        raise
