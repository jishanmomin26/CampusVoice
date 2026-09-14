"""Feedback API Endpoints."""

import logging
from pathlib import Path
import sys
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Ensure CampusVoice project root is on sys.path so the ml package is discoverable
def _ensure_project_root_in_path() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "ml").exists() and (parent / "backend").exists():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return parent
    fallback = current.parents[4]
    if str(fallback) not in sys.path:
        sys.path.insert(0, str(fallback))
    return fallback

_ensure_project_root_in_path()

from ml.pipeline.feedback_intelligence import analyze_feedback
from app.db.session import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackAnalyzeAndSaveRequest,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStatsResponse,
)
from app.services.feedback_service import save_analyzed_feedback
from app.services.feedback_stats_service import get_feedback_statistics

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


@router.post(
    "/analyze-and-save",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze Student Feedback and Persist to Database",
    description=(
        "Executes the unified ML feedback intelligence pipeline on student feedback text "
        "and immediately persists the resulting intelligence (clean text, sentiment, "
        "category, and deterministic priority) into the PostgreSQL feedback table."
    ),
)
def analyze_and_save_feedback(
    payload: FeedbackAnalyzeAndSaveRequest,
    db: Session = Depends(get_db),
) -> Feedback:
    """Analyze student feedback and persist the result into PostgreSQL."""
    # 1. Execute ML Feedback Intelligence Pipeline
    try:
        analysis_result = analyze_feedback(payload.feedback)
    except FileNotFoundError as exc:
        logger.error(
            "ML model or vectorizer artifact missing during feedback analysis: %s",
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Machine learning model artifacts are currently unavailable.",
        )
    except ValueError as exc:
        logger.warning("Validation error during feedback analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(
            "Unexpected error during feedback analysis: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the feedback text.",
        )

    # 2. Persist Analyzed Feedback to Database with Transaction Safety
    try:
        feedback_record = save_analyzed_feedback(
            db=db,
            feedback_text=payload.feedback,
            analysis_result=analysis_result,
            department=payload.department,
            semester=payload.semester,
        )
        return feedback_record
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while persisting analyzed feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist feedback due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while persisting analyzed feedback: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )


@router.get(
    "/stats",
    response_model=FeedbackStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Feedback Statistics",
    description=(
        "Retrieves dynamic, database-backed aggregate feedback statistics for the "
        "administrator dashboard, including total volume, analyzed vs. unclassified counts, "
        "sentiment breakdown, priority distribution, and dynamic category frequency."
    ),
)
def get_feedback_stats(
    db: Session = Depends(get_db),
) -> FeedbackStatsResponse:
    """Retrieve aggregate feedback statistics from PostgreSQL."""
    try:
        stats = get_feedback_statistics(db)
        return FeedbackStatsResponse.model_validate(stats)
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while calculating feedback statistics: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback statistics due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while calculating feedback statistics: %s",
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
