"""NLP API Test Endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.nlp.preprocessing import preprocess_text
from app.nlp.resources import MissingNLPResourceError
from app.schemas.nlp import PreprocessingRequest, PreprocessingResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/preprocess",
    response_model=PreprocessingResult,
    status_code=status.HTTP_200_OK,
    summary="Test NLP Text Preprocessing Pipeline",
    description=(
        "Processes raw student feedback through text normalization, "
        "linguistic tokenization, stopword filtering (with negations preserved), "
        "and spaCy lemmatization."
    ),
)
def test_preprocessing(payload: PreprocessingRequest) -> PreprocessingResult:
    """Preprocess student feedback text and return structured pipeline results."""
    try:
        return preprocess_text(payload.text)
    except MissingNLPResourceError as exc:
        logger.error("NLP resource missing during preprocessing: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Missing NLP Resource",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.error("Unexpected error during text preprocessing: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while preprocessing the feedback text.",
        )
