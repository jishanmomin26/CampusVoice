"""Application Configuration using Pydantic Settings."""

import urllib.parse
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known development fallback defaults
DEFAULT_DEV_DATABASE_URL = (
    "postgresql+psycopg://postgres:postgres@localhost:5432/campusvoice"
)
DEFAULT_DEV_JWT_SECRET = (
    "campusvoice-dev-secret-key-change-in-production-min-32-chars-long"
)


class Settings(BaseSettings):
    """Global configuration settings for CampusVoice API."""

    PROJECT_NAME: str = "CampusVoice API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI-Powered Student Feedback Intelligence System"
    API_V1_STR: str = "/api/v1"

    # PostgreSQL Database URL with psycopg (psycopg3) driver
    # Example: postgresql+psycopg://postgres:password@localhost:5432/campusvoice
    DATABASE_URL: str = DEFAULT_DEV_DATABASE_URL

    # Allowed frontend CORS origin URL
    FRONTEND_URL: str = "http://localhost:5173"

    # Environment Deployment Mode: "development", "production", or "testing"
    ENVIRONMENT: str = "development"

    # Configurable CORS Origins: Comma-separated list of origins (e.g. "https://campusvoice.example.edu,http://localhost:5173")
    CORS_ALLOWED_ORIGINS: str | None = None

    # JWT Authentication Settings (Step 9.12 & 9.17)
    JWT_SECRET_KEY: str = DEFAULT_DEV_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Local Development Admin Seed Settings (Optional)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str | None = None

    # Google OAuth / OpenID Connect Settings (Step 9.19.1)
    GOOGLE_CLIENT_ID: str | None = None

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

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """Validates that production environment variables are secure and explicit.
        
        Guarantees:
        1. DATABASE_URL cannot use the dev fallback or point to localhost/127.0.0.1.
        2. JWT_SECRET_KEY cannot be empty, the dev placeholder, or shorter than 32 chars.
        3. CORS origins must be explicitly configured and not include localhost/127.0.0.1.
        4. Secrets or credentials are never exposed in validation errors.
        """
        if self.ENVIRONMENT.lower() == "production":
            # 1. DATABASE_URL Validation
            if not self.DATABASE_URL or not self.DATABASE_URL.strip():
                raise ValueError(
                    "Production DATABASE_URL must be explicitly configured."
                )
            clean_db_url = self.DATABASE_URL.strip()
            if clean_db_url == DEFAULT_DEV_DATABASE_URL:
                raise ValueError(
                    "Production DATABASE_URL cannot use the development default fallback."
                )

            # Check database host without exposing credentials
            try:
                parsed_db = urllib.parse.urlsplit(clean_db_url)
                db_host = parsed_db.hostname
            except Exception:
                raise ValueError(
                    "Production DATABASE_URL is not a valid database connection URL."
                )

            if not db_host or db_host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                raise ValueError(
                    "Production DATABASE_URL cannot point to localhost or 127.0.0.1."
                )

            # 2. JWT_SECRET_KEY Validation
            if not self.JWT_SECRET_KEY or not self.JWT_SECRET_KEY.strip():
                raise ValueError(
                    "Production JWT_SECRET_KEY must be explicitly configured."
                )
            clean_secret = self.JWT_SECRET_KEY.strip()
            if clean_secret == DEFAULT_DEV_JWT_SECRET:
                raise ValueError(
                    "Production JWT_SECRET_KEY cannot use the development placeholder."
                )
            if len(clean_secret) < 32:
                raise ValueError(
                    "Production JWT_SECRET_KEY must be at least 32 characters long."
                )

            # 3. CORS Origins Validation
            origins = self.get_cors_origins()
            if not origins:
                raise ValueError(
                    "Production requires explicitly configured non-localhost CORS origin(s) via CORS_ALLOWED_ORIGINS or FRONTEND_URL."
                )

            for origin in origins:
                try:
                    parsed_orig = urllib.parse.urlsplit(origin)
                    orig_host = parsed_orig.hostname
                except Exception:
                    raise ValueError("Production CORS origin is invalid.")

                if not orig_host or orig_host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
                    raise ValueError(
                        f"Production CORS origins cannot include local development host '{orig_host}'."
                    )

        return self

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

