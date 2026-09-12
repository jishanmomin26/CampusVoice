"""Pydantic v2 Schemas for Feedback."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FeedbackBase(BaseModel):
    """Base schema containing shared feedback attributes."""

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


class FeedbackCreate(FeedbackBase):
    """Schema for incoming feedback submission requests."""

    pass


class FeedbackResponse(FeedbackBase):
    """Schema for outgoing feedback responses with database attributes."""

    id: int = Field(..., description="Unique feedback record ID", examples=[1])
    created_at: datetime = Field(
        ..., description="Timezone-aware timestamp of creation"
    )

    # Pydantic v2 ORM mode configuration
    model_config = ConfigDict(from_attributes=True)
