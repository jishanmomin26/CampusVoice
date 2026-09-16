"""Production Configuration Hardening Tests (Step 9.18.1).

Validates:
1. Development configuration continues working seamlessly with defaults.
2. Production requires non-local database URL and rejects empty or missing URLs.
3. Production rejects localhost and 127.0.0.1 database URLs.
4. Production requires explicit JWT secret and rejects empty/whitespace secrets.
5. Production rejects the known development JWT placeholder.
6. Production rejects JWT secrets shorter than 32 characters.
7. Production accepts safe test configurations (strong secret, non-local DB, non-localhost CORS).
8. Production requires explicit CORS origin and rejects missing CORS configurations.
9. Production rejects localhost-only CORS configurations.
10. Wildcard CORS ('*') is strictly disallowed with credentials.
11. Configuration error messages never leak secrets or database credentials.
"""

from pathlib import Path
import sys
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import (
    DEFAULT_DEV_DATABASE_URL,
    DEFAULT_DEV_JWT_SECRET,
    Settings,
)

# Safe fake test fixtures (NEVER real credentials)
SAFE_PROD_DB = "postgresql+psycopg://test_user:test_password@db.cloud.internal:5432/campusvoice_test"
SAFE_PROD_JWT = "super-secure-production-test-key-32-chars-long!"
SAFE_PROD_CORS = "https://campusvoice.test.edu"


class TestProductionConfigurationHardening:
    """Validates production environment settings validation."""

    def test_development_configuration_remains_valid(self):
        """Default Settings in development mode loads cleanly without raising validation errors."""
        dev_settings = Settings(
            _env_file=None,
            ENVIRONMENT="development",
            DATABASE_URL=DEFAULT_DEV_DATABASE_URL,
            JWT_SECRET_KEY=DEFAULT_DEV_JWT_SECRET,
            FRONTEND_URL="http://localhost:5173",
        )
        assert dev_settings.ENVIRONMENT == "development"
        origins = dev_settings.get_cors_origins()
        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins

    def test_production_accepts_valid_configuration(self):
        """Production Settings initializes successfully when all production requirements are satisfied."""
        prod_settings = Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DATABASE_URL=SAFE_PROD_DB,
            JWT_SECRET_KEY=SAFE_PROD_JWT,
            FRONTEND_URL=SAFE_PROD_CORS,
            CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
        )
        assert prod_settings.ENVIRONMENT == "production"
        origins = prod_settings.get_cors_origins()
        assert SAFE_PROD_CORS in origins
        assert "http://localhost:5173" not in origins

    def test_production_rejects_empty_database_url(self):
        """Production rejects missing or empty DATABASE_URL."""
        with pytest.raises(ValueError, match="Production DATABASE_URL must be explicitly configured"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL="",
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )

    def test_production_rejects_default_development_database_url(self):
        """Production rejects the default local development DATABASE_URL fallback."""
        with pytest.raises(ValueError, match="cannot use the development default fallback"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=DEFAULT_DEV_DATABASE_URL,
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )

    def test_production_rejects_localhost_database_url(self):
        """Production rejects database URLs pointing to localhost, 127.0.0.1, 0.0.0.0, or ::1."""
        local_db_urls = [
            "postgresql+psycopg://user:pass@localhost:5432/campusvoice",
            "postgresql+psycopg://user:pass@127.0.0.1:5432/campusvoice",
            "postgresql+psycopg://user:pass@0.0.0.0:5432/campusvoice",
            "postgresql+psycopg://user:pass@[::1]:5432/campusvoice",
        ]
        for url in local_db_urls:
            with pytest.raises(ValueError, match="cannot point to localhost or 127.0.0.1"):
                Settings(
                    _env_file=None,
                    ENVIRONMENT="production",
                    DATABASE_URL=url,
                    JWT_SECRET_KEY=SAFE_PROD_JWT,
                    CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
                )

    def test_production_rejects_empty_jwt_secret(self):
        """Production rejects missing or empty JWT_SECRET_KEY."""
        with pytest.raises(ValueError, match="Production JWT_SECRET_KEY must be explicitly configured"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY="",
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )

    def test_production_rejects_default_development_jwt_placeholder(self):
        """Production rejects the default development JWT_SECRET_KEY placeholder."""
        with pytest.raises(ValueError, match="cannot use the development placeholder"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY=DEFAULT_DEV_JWT_SECRET,
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )

    def test_production_rejects_jwt_secret_shorter_than_32_chars(self):
        """Production rejects JWT secrets shorter than 32 characters."""
        with pytest.raises(ValueError, match="at least 32 characters long"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY="too-short-secret-12345",
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )

    def test_production_rejects_missing_cors_configuration(self):
        """Production rejects configuration when no non-localhost CORS origins are provided."""
        with pytest.raises(ValueError, match="requires explicitly configured non-localhost CORS origin"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                FRONTEND_URL="",
                CORS_ALLOWED_ORIGINS=None,
            )

    def test_production_rejects_localhost_only_cors(self):
        """Production rejects CORS configuration that only contains localhost or 127.0.0.1."""
        with pytest.raises(ValueError, match="cannot include local development host"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                CORS_ALLOWED_ORIGINS="http://localhost:5173, http://127.0.0.1:5173",
            )

    def test_wildcard_cors_stripped_and_rejected_in_production(self):
        """Setting only '*' as CORS origin in production is stripped and triggers missing origin error."""
        with pytest.raises(ValueError, match="requires explicitly configured non-localhost CORS origin"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=SAFE_PROD_DB,
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                FRONTEND_URL="",
                CORS_ALLOWED_ORIGINS="*",
            )

    def test_validation_errors_never_leak_secrets_or_credentials(self):
        """Error messages never print passwords, database connection credentials, or JWT secrets."""
        test_sensitive_db = "postgresql+psycopg://super_secret_user:super_secret_pass@127.0.0.1:5432/campusvoice"
        try:
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                DATABASE_URL=test_sensitive_db,
                JWT_SECRET_KEY=SAFE_PROD_JWT,
                CORS_ALLOWED_ORIGINS=SAFE_PROD_CORS,
            )
            pytest.fail("Expected ValueError was not raised.")
        except ValueError as exc:
            err_msg = str(exc)
            assert "super_secret_user" not in err_msg
            assert "super_secret_pass" not in err_msg
            assert "cannot point to localhost or 127.0.0.1" in err_msg
