"""User Management Pydantic Schemas (Step 9.14.1).

Defines schemas for listing, creating, inspecting, and updating users.
Excludes password hashes from all response models.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.roles import UserRole


class UserListItem(BaseModel):
    """Schema representing an individual user entry in a paginated list."""

    id: int = Field(..., description="Unique user identifier")
    username: str = Field(..., description="User login username")
    role: str = Field(..., description="User role ('admin' or 'student')")
    is_active: bool = Field(..., description="Account activation status")
    created_at: datetime = Field(..., description="Timestamp of account creation")

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for paginated user list responses."""

    items: List[UserListItem] = Field(..., description="List of user items for the current page")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total count of users matching active filters")
    total_pages: int = Field(..., description="Total number of pages")


class UserCreateRequest(BaseModel):
    """Schema for administrator user creation."""

    username: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique login username",
        examples=["student_john"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Plain-text password (minimum 8 characters, maximum 72 bytes)",
        examples=["SecurePassword123!"],
    )
    role: Optional[str] = Field(
        default=UserRole.STUDENT.value,
        description="Assigned user role ('student' or 'admin')",
        examples=["student"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Ensure username is stripped and non-empty."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Username cannot be empty or whitespace-only.")
        return stripped

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password is non-empty and has at least 8 characters."""
        stripped = v.strip()
        if len(stripped) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        """Normalize and validate the role."""
        if v is None:
            return UserRole.STUDENT.value
        try:
            return UserRole.normalize(v).value
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {', '.join(valid_roles)}.")


class UserUpdateRequest(BaseModel):
    """Schema for administrator user updates.
    
    All fields are optional, but at least one field must be provided.
    """

    role: Optional[str] = Field(
        default=None,
        description="Updated user role ('admin' or 'student')",
        examples=["admin"],
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Updated account activation status",
        examples=[False],
    )
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=72,
        description="Updated plain-text password (minimum 8 characters, maximum 72 bytes)",
        examples=["NewSecurePassword456!"],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Normalize and validate the role if provided."""
        if v is None:
            return None
        try:
            return UserRole.normalize(v).value
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {', '.join(valid_roles)}.")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """Validate updated password if provided."""
        if v is None:
            return None
        stripped = v.strip()
        if len(stripped) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes.")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UserUpdateRequest":
        """Enforce that at least one field is provided for update."""
        if self.role is None and self.is_active is None and self.password is None:
            raise ValueError("At least one field (role, is_active, or password) must be provided for update.")
        return self


class UserDetailResponse(BaseModel):
    """Schema representing complete, safe user details (no credentials or hashes)."""

    id: int = Field(..., description="Unique user identifier")
    username: str = Field(..., description="User login username")
    role: str = Field(..., description="Assigned user role ('admin' or 'student')")
    is_active: bool = Field(..., description="Account activation status")
    created_at: datetime = Field(..., description="Timestamp of account creation")

    model_config = ConfigDict(from_attributes=True)
