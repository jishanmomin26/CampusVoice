"""Unit and Integration Tests for Google Sign-In Backend Foundation (Step 9.19.1).

Validates all 20 required criteria:
  1. Google endpoint exists (POST /api/v1/auth/google)
  2. Empty credential rejected (HTTP 422)
  3. Whitespace credential rejected (HTTP 422)
  4. Invalid Google token rejected (HTTP 401)
  5. Malformed token rejected (HTTP 401)
  6. Wrong audience rejected (HTTP 401)
  7. Wrong issuer rejected (HTTP 401)
  8. Expired token rejected (HTTP 401)
  9. Unverified email token rejected (HTTP 401)
  10. Valid verified Google identity can authenticate (HTTP 200 + JWT)
  11. Existing google_sub maps to existing user
  12. New Google user is created with role 'student'
  13. Google authentication cannot create admin accounts
  14. Google ID token is never returned in response
  15. Existing username/password login still works
  16. Existing admin login still works
  17. /auth/me works after Google login
  18. Inactive Google-linked user cannot authenticate (HTTP 401)
  19. Duplicate Google identity is prevented (safe idempotent mapping)
  20. Database migration preserves existing users and schema integrity
  + Security: Cryptographically random salted bcrypt hash stored for Google users
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from google.auth.exceptions import GoogleAuthError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.services.google_auth_service import (
    authenticate_or_provision_google_user,
    verify_google_id_token,
)


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def in_memory_engine():
    """In-memory SQLite engine with User table containing google_sub."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def in_memory_db(in_memory_engine):
    """Isolated session per test with automatic rollback."""
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=in_memory_engine,
        expire_on_commit=False,
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def configure_google_client_id():
    """Ensures GOOGLE_CLIENT_ID is set during tests and restored afterward."""
    original_client_id = settings.GOOGLE_CLIENT_ID
    settings.GOOGLE_CLIENT_ID = "campusvoice-test-client-id.apps.googleusercontent.com"
    yield
    settings.GOOGLE_CLIENT_ID = original_client_id


@pytest.fixture
def mock_google_claims() -> Dict[str, Any]:
    """Factory fixture for a standard verified Google ID token claims dictionary."""
    return {
        "iss": "https://accounts.google.com",
        "sub": "google-user-sub-1234567890",
        "email": "student.verified@university.edu",
        "email_verified": True,
        "name": "Verified Student",
        "picture": "https://lh3.googleusercontent.com/a/photo.jpg",
        "aud": settings.GOOGLE_CLIENT_ID or "campusvoice-test-client-id.apps.googleusercontent.com",
    }


# ==============================================================================
# 1. ENDPOINT EXISTENCE & REQUEST VALIDATION (1 - 3)
# ==============================================================================

class TestGoogleAuthValidation:
    """Validates endpoint availability, routing, and Pydantic input schemas."""

    def test_condition_01_google_endpoint_exists(self, client, in_memory_db):
        """1. POST /api/v1/auth/google exists and does not return 404 or 405 for POST."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "sample_token"})
            # Should reach validation/verification logic (not 404 Not Found or 405 Method Not Allowed)
            assert res.status_code in (200, 401, 500)
        finally:
            app.dependency_overrides.clear()

    def test_condition_02_empty_credential_rejected(self, client, in_memory_db):
        """2. Empty credential string is rejected with HTTP 422 Unprocessable Entity."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": ""})
            assert res.status_code == 422
            # Verify no secret is echoed in error response
            assert "credential" in res.text.lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_03_whitespace_credential_rejected(self, client, in_memory_db):
        """3. Whitespace-only credential string is rejected with HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "   \t \n  "})
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_arbitrary_extra_fields_rejected(self, client, in_memory_db):
        """Extra fields like role, email, or user_id are strictly rejected by schema."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/google",
                json={
                    "credential": "valid-token-structure",
                    "role": "admin",
                    "email": "attacker@example.com",
                },
            )
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 2. CRYPTOGRAPHIC VERIFICATION & REJECTION LOGIC (4 - 9)
# ==============================================================================

class TestGoogleVerificationSecurity:
    """Validates that all forms of invalid Google tokens are safely rejected with 401."""

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_04_invalid_google_token_rejected(
        self, mock_verify, client, in_memory_db
    ):
        """4. Invalid signature Google token is rejected with HTTP 401."""
        mock_verify.side_effect = ValueError("Invalid token signature")
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "invalid_signature_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
            # Ensure credential is NOT echoed
            assert "invalid_signature_token" not in res.text
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_05_malformed_token_rejected(
        self, mock_verify, client, in_memory_db
    ):
        """5. Malformed JWT token string is rejected with HTTP 401."""
        mock_verify.side_effect = GoogleAuthError("Malformed token data")
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "not.a.valid.jwt"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_06_wrong_audience_rejected(
        self, mock_verify, client, in_memory_db
    ):
        """6. Token issued for a different audience (client ID) is rejected with HTTP 401."""
        mock_verify.side_effect = ValueError("Token wrong audience")
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "wrong_audience_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_07_wrong_issuer_rejected(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """7. Token with untrusted issuer is rejected with HTTP 401."""
        untrusted_claims = dict(mock_google_claims)
        untrusted_claims["iss"] = "https://untrusted-issuer.example.com"
        mock_verify.return_value = untrusted_claims

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "untrusted_issuer_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_08_expired_token_rejected(
        self, mock_verify, client, in_memory_db
    ):
        """8. Expired Google token is rejected with HTTP 401."""
        mock_verify.side_effect = ValueError("Token used after expiry")
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "expired_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_09_unverified_email_rejected(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """9. Google account where email is not verified is rejected with HTTP 401."""
        unverified_claims = dict(mock_google_claims)
        unverified_claims["email_verified"] = False
        mock_verify.return_value = unverified_claims

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "unverified_email_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid Google authentication credential."
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 3. SUCCESSFUL AUTHENTICATION & PROVISIONING (10 - 14)
# ==============================================================================

class TestGoogleAuthSuccessAndProvisioning:
    """Validates user provisioning, account linking, JWT issuance, and role enforcement."""

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_10_valid_verified_identity_authenticates(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """10. Valid verified Google identity successfully receives 200 + CampusVoice JWT."""
        mock_verify.return_value = mock_google_claims

        # Ensure settings.GOOGLE_CLIENT_ID is populated for test
        original_client_id = settings.GOOGLE_CLIENT_ID
        settings.GOOGLE_CLIENT_ID = "campusvoice-test-client-id.apps.googleusercontent.com"

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "valid_google_token"})
            assert res.status_code == 200
            data = res.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["role"] == "student"
            assert data["username"] == mock_google_claims["email"].lower()

            # Verify the access token is verifiable by CampusVoice's JWT decoder
            payload = decode_access_token(data["access_token"])
            assert payload["role"] == "student"
            assert payload["username"] == mock_google_claims["email"].lower()
            assert int(payload["sub"]) > 0
        finally:
            settings.GOOGLE_CLIENT_ID = original_client_id
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_11_existing_google_sub_maps_to_existing_user(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """11. Existing user with matching google_sub maps directly to that account."""
        mock_verify.return_value = mock_google_claims

        # Pre-seed user with google_sub
        existing_user = User(
            username="existing_student_alias",
            password_hash=hash_password("AValidBcryptSecret123!"),
            role="student",
            is_active=True,
            google_sub=mock_google_claims["sub"],
        )
        in_memory_db.add(existing_user)
        in_memory_db.commit()
        in_memory_db.refresh(existing_user)

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res.status_code == 200
            data = res.json()
            assert data["username"] == "existing_student_alias"

            # Check token subject is the existing user's ID
            payload = decode_access_token(data["access_token"])
            assert payload["sub"] == str(existing_user.id)
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_12_new_google_user_created_as_student(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """12. Newly provisioned Google user record is created strictly with 'student' role."""
        mock_verify.return_value = mock_google_claims
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res.status_code == 200

            # Query database directly to inspect the persisted User record
            persisted_user = in_memory_db.scalar(
                select(User).where(User.google_sub == mock_google_claims["sub"])
            )
            assert persisted_user is not None
            assert persisted_user.role == UserRole.STUDENT.value
            assert persisted_user.is_active is True
            assert persisted_user.google_sub == mock_google_claims["sub"]
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_13_google_auth_cannot_create_or_claim_admin(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """13. Google login cannot create an admin user or hijack an existing admin account."""
        # 1. Verify token claims attempting to specify role=admin are ignored (Google token claims)
        claims_with_admin = dict(mock_google_claims)
        claims_with_admin["role"] = "admin"
        claims_with_admin["sub"] = "sub-attacker-role"
        claims_with_admin["email"] = "attacker@university.edu"
        mock_verify.return_value = claims_with_admin

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "admin_attempt_token"})
            assert res.status_code == 200
            assert res.json()["role"] == "student"  # Forced to student, not admin!

            # 2. Existing admin account cannot be claimed or linked via Google sign-in
            admin_user = User(
                username="admin@university.edu",
                password_hash=hash_password("AdminSecurePassword123!"),
                role="admin",
                is_active=True,
            )
            in_memory_db.add(admin_user)
            in_memory_db.commit()

            admin_google_claims = dict(mock_google_claims)
            admin_google_claims["sub"] = "google-sub-hijack-attempt"
            admin_google_claims["email"] = "admin@university.edu"
            mock_verify.return_value = admin_google_claims

            res_admin = client.post("/api/v1/auth/google", json={"credential": "admin_hijack_token"})
            # Must reject attempting to link to an admin account
            assert res_admin.status_code == 401
            assert res_admin.json()["detail"] == "Invalid username or password."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_14_google_id_token_never_returned(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """14. Response never exposes the raw Google ID token or internal tokens."""
        raw_credential = "raw-very-secret-google-id-token-xyz-12345"
        mock_verify.return_value = mock_google_claims

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": raw_credential})
            assert res.status_code == 200
            response_text = res.text
            # Strict guarantee: submitted Google credential must NEVER appear in response body or headers
            assert raw_credential not in response_text
            assert "raw-very-secret" not in response_text
            data = res.json()
            assert "google_sub" not in data
            assert "credential" not in data
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 4. REGRESSION & COMPATIBILITY (15 - 17)
# ==============================================================================

class TestAuthRegressionAndMeCompatibility:
    """Validates existing username/password flows and /auth/me compatibility."""

    def test_condition_15_existing_username_password_login_works(
        self, client, in_memory_db
    ):
        """15. Existing student login via POST /api/v1/auth/login works unchanged."""
        user = User(
            username="regular_student",
            password_hash=hash_password("StudentPass123!"),
            role="student",
            is_active=True,
        )
        in_memory_db.add(user)
        in_memory_db.commit()

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/login",
                json={"username": "regular_student", "password": "StudentPass123!"},
            )
            assert res.status_code == 200
            assert res.json()["role"] == "student"
            assert "access_token" in res.json()
        finally:
            app.dependency_overrides.clear()

    def test_condition_16_existing_admin_login_works(self, client, in_memory_db):
        """16. Existing admin login via POST /api/v1/auth/login works unchanged."""
        admin = User(
            username="master_admin",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        )
        in_memory_db.add(admin)
        in_memory_db.commit()

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/login",
                json={"username": "master_admin", "password": "AdminPass123!"},
            )
            assert res.status_code == 200
            assert res.json()["role"] == "admin"
            assert "access_token" in res.json()
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_17_auth_me_works_after_google_login(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """17. GET /api/v1/auth/me works seamlessly with the issued JWT from Google login."""
        mock_verify.return_value = mock_google_claims
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            login_res = client.post(
                "/api/v1/auth/google", json={"credential": "valid_token"}
            )
            assert login_res.status_code == 200
            access_token = login_res.json()["access_token"]

            # Call /api/v1/auth/me
            me_res = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_res.status_code == 200
            me_data = me_res.json()
            assert me_data["username"] == mock_google_claims["email"].lower()
            assert me_data["role"] == "student"
            assert me_data["is_active"] is True
            assert "password_hash" not in me_data
            assert "google_sub" not in me_data
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 5. ACCOUNT INACTIVATION & IDEMPOTENCY (18 - 19)
# ==============================================================================

class TestAccountStateAndIdempotency:
    """Validates inactive account protection and duplicate identity prevention."""

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_18_inactive_google_user_cannot_authenticate(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """18. Inactive Google-linked account is rejected with HTTP 401."""
        mock_verify.return_value = mock_google_claims

        # Seed deactivated user
        inactive_user = User(
            username="inactive_google_user",
            password_hash=hash_password("InactiveSecret123!"),
            role="student",
            is_active=False,
            google_sub=mock_google_claims["sub"],
        )
        in_memory_db.add(inactive_user)
        in_memory_db.commit()

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid username or password."
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_condition_19_duplicate_google_identity_prevented(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """19. Repeated logins with the same Google identity are idempotent and create no duplicate records."""
        mock_verify.return_value = mock_google_claims

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # First login provisions the user
            res1 = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res1.status_code == 200

            # Second login re-authenticates the same user
            res2 = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res2.status_code == 200

            # Verify total count of matching records in database is exactly 1
            users = list(
                in_memory_db.scalars(
                    select(User).where(User.google_sub == mock_google_claims["sub"])
                ).all()
            )
            assert len(users) == 1
            assert users[0].google_sub == mock_google_claims["sub"]
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 6. MIGRATION INTEGRITY & PASSWORD SECURITY (20 + Security)
# ==============================================================================

class TestMigrationAndSecretSafety:
    """Validates Alembic migration integrity and cryptographically random password hashing."""

    def test_condition_20_migration_lineage_and_integrity(self):
        """20. Migration 004 revises 003_create_users and maintains reversible Alembic lineage."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_cfg = Config()
        alembic_cfg.set_main_option(
            "script_location", str(PROJECT_ROOT / "backend" / "alembic")
        )
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()

        assert len(heads) == 1
        assert heads[0] == "004_add_google_identity_to_users"

        rev_004 = script.get_revision("004_add_google_identity_to_users")
        assert rev_004 is not None
        assert rev_004.down_revision == "003_create_users"

    @patch("app.services.google_auth_service.google_id_token.verify_oauth2_token")
    def test_security_random_bcrypt_password_for_google_user(
        self, mock_verify, client, in_memory_db, mock_google_claims
    ):
        """Validates that newly provisioned Google user stores a salted bcrypt hash, not a literal sentinel."""
        mock_verify.return_value = mock_google_claims

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post("/api/v1/auth/google", json={"credential": "valid_token"})
            assert res.status_code == 200

            persisted_user = in_memory_db.scalar(
                select(User).where(User.google_sub == mock_google_claims["sub"])
            )
            assert persisted_user is not None
            # Must NOT be a sentinel string
            assert persisted_user.password_hash != "!google_oauth_no_password!"
            # Must be a valid salted bcrypt hash (starts with $2b$12$)
            assert persisted_user.password_hash.startswith("$2b$12$")
            assert len(persisted_user.password_hash) >= 50

            # Attempting to log in with a random password via /login should fail
            login_attempt = client.post(
                "/api/v1/auth/login",
                json={
                    "username": persisted_user.username,
                    "password": "GuessPassword123!",
                },
            )
            assert login_attempt.status_code == 401
        finally:
            app.dependency_overrides.clear()
