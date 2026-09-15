"""Application Configuration using Pydantic Settings."""

import urllib.parse
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for CampusVoice API."""

    PROJECT_NAME: str = "CampusVoice API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI-Powered Student Feedback Intelligence System"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Database URL with psycopg (psycopg3) driver
    # Example: postgresql+psycopg://postgres:password@localhost:5432/campusvoice
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/campusvoice"
    )

    # Allowed frontend CORS origin URL
    FRONTEND_URL: str = "http://localhost:5173"

    # JWT Authentication Settings (Step 9.12)
    JWT_SECRET_KEY: str = (
        "campusvoice-dev-secret-key-change-in-production-min-32-chars-long"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Local Development Admin Seed Settings (Optional)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def sanitize_database_url(cls, v: str) -> str:
        """Properly encode special characters in database credentials."""
        if not isinstance(v, str):
            return v
        prefix, sep, rest = v.partition("://")
        if not sep:
            return v
        last_at_idx = rest.rfind("@")
        if last_at_idx == -1:
            return v
        user_pass = rest[:last_at_idx]
        host_db = rest[last_at_idx + 1 :]
        user, p_sep, pwd = user_pass.partition(":")
        if p_sep:
            # Safely encode special characters (e.g. '@', '%') in password
            encoded_pwd = urllib.parse.quote(
                urllib.parse.unquote(pwd), safe=""
            )
            return f"{prefix}://{user}:{encoded_pwd}@{host_db}"
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
