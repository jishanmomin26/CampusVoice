"""Feedback API Endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Student Feedback",
    description="Validates incoming student feedback and stores it in the PostgreSQL database.",
)
def create_feedback(
    feedback_in: FeedbackCreate,
    db: Session = Depends(get_db),
) -> Feedback:
    """Create a new feedback record in PostgreSQL."""
    try:
        feedback_record = Feedback(
            department=feedback_in.department,
            semester=feedback_in.semester,
            feedback_text=feedback_in.feedback_text,
        )
        db.add(feedback_record)
        db.commit()
        db.refresh(feedback_record)
        return feedback_record
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error while saving feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save feedback due to an internal database error.",
        )
    except Exception as exc:
        db.rollback()
        logger.error(
            "Unexpected error while saving feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )


@router.get(
    "",
    response_model=List[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="List Feedback Records",
    description="Retrieves all feedback records stored in the database, ordered by newest first.",
)
def list_feedback(
    db: Session = Depends(get_db),
) -> List[Feedback]:
    """Retrieve all feedback entries from PostgreSQL."""
    try:
        statement = select(Feedback).order_by(Feedback.created_at.desc())
        results = db.scalars(statement).all()
        return list(results)
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while fetching feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback records due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while fetching feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )
