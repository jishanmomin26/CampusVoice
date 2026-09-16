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

    # Environment Deployment Mode: "development", "production", or "testing"
    ENVIRONMENT: str = "development"

    # Configurable CORS Origins: Comma-separated list of origins (e.g. "https://campusvoice.example.edu,http://localhost:5173")
    CORS_ALLOWED_ORIGINS: str | None = None

    # JWT Authentication Settings (Step 9.12 & 9.17)
    JWT_SECRET_KEY: str = (
        "campusvoice-dev-secret-key-change-in-production-min-32-chars-long"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Local Development Admin Seed Settings (Optional)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None

    def get_cors_origins(self) -> list[str]:
        """Resolves the allowed CORS origins based on environment settings.
        
        Guarantees that wildcard origins ('*') are never used alongside
        credentials, and separates production restrictions from development defaults.
        """
        origins: list[str] = []

        if self.CORS_ALLOWED_ORIGINS:
            # Parse comma-separated list of allowed origins
            parsed = [
                origin.strip().rstrip("/")
                for origin in self.CORS_ALLOWED_ORIGINS.split(",")
                if origin.strip()
            ]
            origins.extend(parsed)
        elif self.ENVIRONMENT.lower() == "production":
            # In production, require explicit configured frontend origin
            if self.FRONTEND_URL and self.FRONTEND_URL.strip():
                clean_url = self.FRONTEND_URL.strip().rstrip("/")
                if clean_url not in ("http://localhost:5173", "http://127.0.0.1:5173"):
                    origins.append(clean_url)
        else:
            # Development / Testing defaults
            dev_defaults = [
                self.FRONTEND_URL.strip().rstrip("/"),
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
            for origin in dev_defaults:
                if origin and origin not in origins:
                    origins.append(origin)

        # Enforce security invariant: Never allow '*' with credentials
        safe_origins = [o for o in origins if o != "*"]
        return safe_origins


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
