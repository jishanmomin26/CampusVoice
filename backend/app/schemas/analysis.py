"""Pydantic v2 Schemas for Feedback Analysis & Intelligence."""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackAnalyzeRequest(BaseModel):
    """Request schema for student feedback analysis."""

    feedback: str = Field(
        ...,
        strict=True,
        description="Raw student feedback text to be analyzed",
        examples=["The faculty is not helpful and the explanations are not clear."],
    )

    @field_validator("feedback")
    @classmethod
    def validate_feedback_not_empty(cls, value: str) -> str:
        """Validates that feedback text is not empty or whitespace-only."""
        if not value.strip():
            raise ValueError("feedback cannot be empty or whitespace-only.")
        return value


class SentimentAnalysisResult(BaseModel):
    """Sentiment classification result schema."""

    label: int = Field(..., description="Numeric sentiment label (-1 for negative, 0 for neutral, 1 for positive)")
    name: str = Field(..., description="Canonical sentiment name (negative, neutral, positive)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the predicted sentiment")
    probabilities: Optional[Dict[str, float]] = Field(
        default=None,
        description="Calibrated probability distribution across sentiment classes",
    )


class CategoryAnalysisResult(BaseModel):
    """Category classification result schema."""

    name: str = Field(..., description="Identified feedback category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for the predicted category")
    probabilities: Optional[Dict[str, float]] = Field(
        default=None,
        description="Probability distribution across all 6 canonical categories",
    )


class ModelProvenance(BaseModel):
    """Metadata detailing the models used for inference."""

    sentiment: str = Field(..., description="Sentiment model identifier")
    category: str = Field(..., description="Category model identifier")


class PriorityAnalysisResult(BaseModel):
    """Deterministic priority assessment result schema."""

    score: int = Field(..., ge=0, le=100, description="Deterministic priority score clamped between 0 and 100")
    level: str = Field(..., description="Priority tier: High, Medium, or Low")
    reason: str = Field(..., description="Explainable administrative reasoning for the assigned priority")


class FeedbackAnalysisResponse(BaseModel):
    """Unified feedback intelligence and priority response schema."""

    feedback: str = Field(..., description="Original unprocessed student feedback text")
    clean_text: str = Field(..., description="NLP-preprocessed normalized text with negation preserved")
    sentiment: SentimentAnalysisResult = Field(..., description="Sentiment classification details")
    category: CategoryAnalysisResult = Field(..., description="Category classification details")
    models: ModelProvenance = Field(..., description="Identifiers of the models used for inference")
    priority: PriorityAnalysisResult = Field(..., description="Priority scoring assessment")

    model_config = ConfigDict(from_attributes=True)
