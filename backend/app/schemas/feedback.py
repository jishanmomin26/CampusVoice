"""Pydantic v2 Schemas for Feedback & Persisted Analysis."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackBase(BaseModel):
    """Base schema containing shared feedback attributes."""

    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Academic department related to the feedback",
        examples=["Computer Science"],
    )
    semester: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Academic semester or term",
        examples=["Semester 4"],
    )
    feedback_text: str = Field(
        ...,
        min_length=1,
        description="Student's feedback message",
        examples=["The laboratory equipment needs more regular maintenance."],
    )


class FeedbackCreate(BaseModel):
    """Schema for incoming feedback submission requests (Step 2 endpoint)."""

    department: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Academic department related to the feedback",
        examples=["Computer Science"],
    )
    semester: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Academic semester or term",
        examples=["Semester 4"],
    )
    feedback_text: str = Field(
        ...,
        min_length=1,
        description="Student's feedback message",
        examples=["The laboratory equipment needs more regular maintenance."],
    )


class FeedbackAnalyzeAndSaveRequest(BaseModel):
    """Schema for incoming feedback analysis and persistence requests (Step 9.3)."""

    feedback: str = Field(
        ...,
        strict=True,
        description="Raw student feedback text to be analyzed and persisted",
        examples=["The faculty is not helpful and the explanations are not clear."],
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional academic department related to the feedback",
        examples=["Computer Science"],
    )
    semester: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Optional academic semester or term",
        examples=["Semester 4"],
    )

    @field_validator("feedback")
    @classmethod
    def validate_feedback_not_empty(cls, value: str) -> str:
        """Validates that feedback text is not empty or whitespace-only."""
        if not value.strip():
            raise ValueError("feedback cannot be empty or whitespace-only.")
        return value


class FeedbackResponse(BaseModel):
    """Schema for outgoing feedback responses with database and analysis attributes."""

    id: int = Field(..., description="Unique feedback record ID", examples=[1])
    department: Optional[str] = Field(
        default=None,
        description="Academic department related to the feedback",
        examples=["Computer Science"],
    )
    semester: Optional[str] = Field(
        default=None,
        description="Academic semester or term",
        examples=["Semester 4"],
    )
    feedback_text: str = Field(
        ...,
        description="Student's raw feedback message",
        examples=["The laboratory equipment needs more regular maintenance."],
    )
    clean_text: Optional[str] = Field(
        default=None,
        description="NLP-preprocessed normalized text with negation preserved",
    )
    sentiment_label: Optional[int] = Field(
        default=None,
        description="Numeric sentiment label (-1 for negative, 0 for neutral, 1 for positive)",
    )
    sentiment_name: Optional[str] = Field(
        default=None,
        description="Canonical sentiment name (negative, neutral, positive)",
    )
    sentiment_confidence: Optional[float] = Field(
        default=None,
        description="Calibrated confidence score for the predicted sentiment",
    )
    category_name: Optional[str] = Field(
        default=None,
        description="Identified feedback category (e.g., Teaching, Lab Work)",
    )
    category_confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for the predicted category",
    )
    priority_score: Optional[int] = Field(
        default=None,
        description="Deterministic priority score between 0 and 100",
    )
    priority_level: Optional[str] = Field(
        default=None,
        description="Priority tier: High, Medium, or Low",
    )
    priority_reason: Optional[str] = Field(
        default=None,
        description="Explainable administrative reasoning for priority assignment",
    )
    created_at: datetime = Field(
        ..., description="Timezone-aware timestamp of creation"
    )

    # Pydantic v2 ORM mode configuration
    model_config = ConfigDict(from_attributes=True)
