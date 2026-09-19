"""Authentication Pydantic Schemas (Step 9.12)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for user authentication request."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User login username",
        examples=["admin"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=72,
        description="User plain-text password",
        examples=["secretpassword"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is non-empty and stripped of excess whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Username cannot be empty or whitespace-only.")
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password is non-empty."""
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or whitespace-only.")
        return v


class GoogleLoginRequest(BaseModel):
    """Schema for Google Sign-In credential authentication request."""

    credential: str = Field(
        ...,
        min_length=1,
        description="Google ID Token issued by Google Identity Services",
        examples=["eyJhbGciOiJSUzI1NiIs..."],
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("credential")
    @classmethod
    def validate_credential(cls, v: str) -> str:
        """Ensure credential is non-empty and stripped of excess whitespace."""
        if not v or not isinstance(v, str):
            raise ValueError("Credential cannot be empty or invalid.")
        stripped = v.strip()
        if not stripped:
            raise ValueError("Credential cannot be empty or whitespace-only.")
        return stripped


class TokenResponse(BaseModel):
    """Schema for successful authentication token response."""

    access_token: str = Field(..., description="Signed JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token authentication type")
    role: Optional[str] = Field(default=None, description="Assigned user role")
    username: Optional[str] = Field(default=None, description="Username")


class CurrentUserResponse(BaseModel):
    """Schema representing current authenticated user profile without sensitive credentials."""

    id: int = Field(..., description="Unique user identifier")
    username: str = Field(..., description="User login username")
    role: str = Field(..., description="Assigned user role (e.g. 'admin', 'student')")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Timestamp of account creation")

    model_config = ConfigDict(from_attributes=True)
