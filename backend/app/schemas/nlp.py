"""Pydantic v2 Schemas for NLP Preprocessing."""

from typing import List
from pydantic import BaseModel, ConfigDict, Field


class PreprocessingRequest(BaseModel):
    """Request schema for text preprocessing."""

    text: str = Field(
        ...,
        description="Raw student feedback text to be processed",
        examples=[
            "The practical sessions are very useful and the faculty explains concepts clearly."
        ],
    )


class PreprocessingResult(BaseModel):
    """Structured result of the NLP text preprocessing pipeline."""

    original_text: str = Field(
        ...,
        description="Original unprocessed raw input text",
    )
    normalized_text: str = Field(
        ...,
        description="Text after lowercasing and whitespace normalization",
    )
    tokens: List[str] = Field(
        ...,
        description="All extracted linguistic word tokens",
    )
    filtered_tokens: List[str] = Field(
        ...,
        description="Tokens after punctuation and stopword removal (with negations preserved)",
    )
    lemmatized_tokens: List[str] = Field(
        ...,
        description="Lemmatized root forms of the filtered tokens",
    )
    clean_text: str = Field(
        ...,
        description="Final normalized, space-separated cleaned text ready for downstream ML/NLP models",
    )

    model_config = ConfigDict(from_attributes=True)
