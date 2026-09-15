"""Centralized User Roles for CampusVoice Authentication & Authorization (Step 9.12)."""

from enum import Enum


class UserRole(str, Enum):
    """Canonical user roles within CampusVoice."""

    STUDENT = "student"
    ADMIN = "admin"

    @classmethod
    def normalize(cls, value: str) -> "UserRole":
        """Safely normalize and validate role strings (case-insensitive).
        
        Args:
            value: Raw role string representation.
            
        Returns:
            UserRole: Canonical enum member.
            
        Raises:
            ValueError: If the role value is not recognized.
        """
        if not isinstance(value, str):
            raise ValueError(f"Invalid role type: {type(value).__name__}")
        norm = value.strip().lower()
        for role in cls:
            if role.value == norm:
                return role
        raise ValueError(f"Unknown role '{value}'. Supported roles: {[r.value for r in cls]}")
