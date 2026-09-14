"""Feedback Analysis API Endpoint."""

import logging
from pathlib import Path
import sys
from fastapi import APIRouter, HTTPException, status

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
from app.schemas.analysis import FeedbackAnalyzeRequest, FeedbackAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=FeedbackAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Student Feedback Intelligence & Priority",
    description=(
        "Executes the unified ML feedback intelligence pipeline on raw student feedback text. "
        "Performs text normalization, lemmatization with negation preservation, TF-IDF transformation, "
        "sentiment classification, category classification, and deterministic priority scoring."
    ),
)
def analyze_student_feedback(
    payload: FeedbackAnalyzeRequest,
) -> FeedbackAnalysisResponse:
    """Analyze student feedback and return sentiment, category, and priority intelligence."""
    try:
        result = analyze_feedback(payload.feedback)
        return FeedbackAnalysisResponse.model_validate(result)
    except FileNotFoundError as exc:
        logger.error("ML model or vectorizer artifact missing during feedback analysis: %s", exc)
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
        logger.error("Unexpected error during feedback analysis: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing the feedback text.",
        )
