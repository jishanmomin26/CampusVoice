"""Comprehensive Unit and Integration Tests for Authentication & Authorization (Step 9.12).

Validates:
  1. Password hashing produces a non-plaintext salted hash
  2. Correct password verifies successfully
  3. Incorrect password verification fails
  4. Salting ensures repeated hashes of the same password are distinct
  5. Valid credentials return HTTP 200 on /api/v1/auth/login
  6. Login token response contains access_token string
  7. Token type is 'bearer'
  8. Invalid username returns HTTP 401
  9. Invalid password returns HTTP 401
  10. Inactive user cannot authenticate (HTTP 401)
  11. Blank/whitespace username is rejected (HTTP 422)
  12. Blank/whitespace password is rejected (HTTP 422)
  13. Valid JWT token authenticates successfully
  14. Expired JWT token is rejected (HTTP 401)
  15. Malformed JWT token is rejected (HTTP 401)
  16. Invalid signature is rejected (HTTP 401)
  17. Unknown user ID in token is rejected (HTTP 401)
  18. Authenticated user can call GET /api/v1/auth/me
  19. Unauthenticated GET /api/v1/auth/me returns HTTP 401
  20. password_hash is never returned in API responses
  21. Admin user passes require_admin dependency
  22. Student user receives HTTP 403 from admin-protected endpoint
  23. Unauthenticated user receives HTTP 401 from admin-protected endpoint
  24. Admin user can access GET /api/v1/feedback/stats
  25. Admin user can access GET /api/v1/feedback/records
  26. Student user cannot access GET /api/v1/feedback/stats (HTTP 403)
  27. Student user cannot access GET /api/v1/feedback/records (HTTP 403)
  28. Existing non-admin/student-facing endpoints remain functional without auth
  29. Existing feedback records remain intact
  30. Alembic migration is at expected head (003_create_users)
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient
import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
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
from app.models.feedback import Feedback
from app.models.user import User


@pytest.fixture
def in_memory_engine():
    """In-memory SQLite engine for isolated auth testing."""
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
    """Database session fixture with rollback per test."""
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


@pytest.fixture
def test_users(in_memory_db):
    """Seeds test users: 1 active admin, 1 active student, 1 inactive admin."""
    admin_pwd_hash = hash_password("AdminSecret123!")
    student_pwd_hash = hash_password("StudentSecret123!")
    inactive_pwd_hash = hash_password("InactiveSecret123!")

    admin_user = User(
        username="admin_user",
        password_hash=admin_pwd_hash,
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    student_user = User(
        username="student_user",
        password_hash=student_pwd_hash,
        role=UserRole.STUDENT.value,
        is_active=True,
    )
    inactive_user = User(
        username="inactive_user",
        password_hash=inactive_pwd_hash,
        role=UserRole.ADMIN.value,
        is_active=False,
    )
    in_memory_db.add_all([admin_user, student_user, inactive_user])
    in_memory_db.commit()
    in_memory_db.refresh(admin_user)
    in_memory_db.refresh(student_user)
    in_memory_db.refresh(inactive_user)

    return {
        "admin": admin_user,
        "student": student_user,
        "inactive": inactive_user,
    }


# ==============================================================================
# PASSWORDS (1 - 4)
# ==============================================================================

class TestPasswordSecurity:
    """Validates hashing, verification, and salting behavior."""

    def test_condition_1_password_hashing_produces_non_plaintext(self):
        """1. Password hashing produces a strong non-plaintext hash."""
        password = "SuperSecretPassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 40
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_condition_2_correct_password_verifies(self):
        """2. Correct password verifies successfully."""
        password = "ValidPassword456"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_condition_3_incorrect_password_fails(self):
        """3. Incorrect password fails verification."""
        password = "ValidPassword456"
        hashed = hash_password(password)
        assert verify_password("WrongPassword789", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password("validpassword456", hashed) is False  # case sensitive

    def test_condition_4_salting_produces_distinct_hashes(self):
        """4. Two hashes of same password are not identical due to random salts."""
        password = "IdenticalPassword777"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ==============================================================================
# LOGIN (5 - 12)
# ==============================================================================

class TestLoginEndpoint:
    """Validates POST /api/v1/auth/login contract, credentials, and errors."""

    def test_condition_5_6_7_valid_credentials_return_200_and_token(self, client, in_memory_db, test_users):
        """5, 6, 7. Valid credentials return 200, access_token, and bearer type."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_user", "password": "AdminSecret123!"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 20
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()

    def test_condition_8_invalid_username_returns_401(self, client, in_memory_db, test_users):
        """8. Non-existent username returns 401 with generic error."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "nonexistent_user", "password": "AdminSecret123!"},
            )
            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_9_invalid_password_returns_401(self, client, in_memory_db, test_users):
        """9. Incorrect password returns 401 with generic error."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_user", "password": "IncorrectPassword999"},
            )
            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_10_inactive_user_cannot_login(self, client, in_memory_db, test_users):
        """10. Inactive user cannot authenticate (HTTP 401)."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "inactive_user", "password": "InactiveSecret123!"},
            )
            assert response.status_code == 401
            assert "Invalid username or password" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_11_blank_username_rejected(self, client):
        """11. Blank or whitespace-only username is rejected with HTTP 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "   ", "password": "ValidPassword123!"},
        )
        assert response.status_code == 422

    def test_condition_12_blank_password_rejected(self, client):
        """12. Blank or whitespace-only password is rejected with HTTP 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin_user", "password": "   "},
        )
        assert response.status_code == 422


# ==============================================================================
# JWT (13 - 17)
# ==============================================================================

class TestJWTValidation:
    """Validates token decoding, expiration, forgery, and invalid claims."""

    def test_condition_13_valid_token_authenticates(self, in_memory_db, test_users):
        """13. Valid JWT token decodes and contains expected user claims."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        payload = decode_access_token(token)
        assert payload["sub"] == str(admin.id)
        assert payload["username"] == admin.username
        assert payload["role"] == UserRole.ADMIN.value
        assert "exp" in payload

    def test_condition_14_expired_token_rejected(self, client, in_memory_db, test_users):
        """14. Expired JWT token is rejected with HTTP 401."""
        admin = test_users["admin"]
        # Generate expired token
        expired_token = create_access_token(
            data={"sub": str(admin.id), "username": admin.username, "role": admin.role},
            expires_delta=timedelta(minutes=-10),
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
            assert response.status_code == 401
            assert "expired" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_15_malformed_token_rejected(self, client, in_memory_db):
        """15. Malformed non-JWT token is rejected with HTTP 401."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer this-is-not-a-valid-jwt-token"},
            )
            assert response.status_code == 401
            assert "invalid" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_16_invalid_signature_rejected(self, client, in_memory_db, test_users):
        """16. Token signed with wrong secret key is rejected with HTTP 401."""
        admin = test_users["admin"]
        fake_token = jwt.encode(
            {
                "sub": str(admin.id),

                "username": admin.username,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "completely-wrong-secret-key-min-32-chars-long!",
            algorithm=settings.JWT_ALGORITHM,
        )

        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {fake_token}"},
            )
            assert response.status_code == 401
            assert "invalid" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_17_unknown_user_token_rejected(self, client, in_memory_db):
        """17. Valid token pointing to non-existent user ID returns HTTP 401."""
        ghost_token = create_access_token(data={"sub": "999999", "username": "ghost", "role": "admin"})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {ghost_token}"},
            )
            assert response.status_code == 401
            assert "no longer exists" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# CURRENT USER / ME (18 - 20)
# ==============================================================================

class TestCurrentUserEndpoint:
    """Validates GET /api/v1/auth/me and credential exposure safeguards."""

    def test_condition_18_authenticated_user_can_call_me(self, client, in_memory_db, test_users):
        """18. Authenticated user can call /auth/me and receive profile."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == admin.id
            assert data["username"] == admin.username
            assert data["role"] == admin.role
            assert data["is_active"] is True
        finally:
            app.dependency_overrides.clear()

    def test_condition_19_unauthenticated_me_returns_401(self, client):
        """19. Unauthenticated request to /auth/me returns HTTP 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "not provided" in response.json()["detail"].lower()

    def test_condition_20_password_hash_never_returned(self, client, in_memory_db, test_users):
        """20. Responses from /auth/me and /auth/login never leak password_hash."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            me_res = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert "password" not in me_res.json()
            assert "password_hash" not in me_res.json()

            login_res = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_user", "password": "AdminSecret123!"},
            )
            assert "password" not in login_res.json()
            assert "password_hash" not in login_res.json()
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# ROLES & RBAC (21 - 23)
# ==============================================================================

class TestRoleBasedAccessControl:
    """Validates require_admin dependency and role isolation."""

    def test_condition_21_admin_user_passes_require_admin(self, client, in_memory_db, test_users):
        """21. Admin user can successfully access admin-protected endpoint."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/feedback/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_condition_22_student_user_receives_403_from_admin_endpoint(self, client, in_memory_db, test_users):
        """22. Student user receives HTTP 403 Forbidden from admin-protected endpoint."""
        student = test_users["student"]
        token = create_access_token(data={"sub": str(student.id), "username": student.username, "role": student.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            response = client.get(
                "/api/v1/feedback/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403
            assert "Administrative privileges required" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_23_unauthenticated_user_receives_401_from_admin_endpoint(self, client):
        """23. Unauthenticated user receives HTTP 401 from admin-protected endpoint."""
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code == 401
        assert "not provided" in response.json()["detail"].lower()


# ==============================================================================
# ADMIN ENDPOINTS (24 - 27)
# ==============================================================================

class TestProtectedAdminEndpoints:
    """Validates /feedback/stats and /feedback/records role enforcement."""

    def test_condition_24_admin_can_access_stats(self, client, in_memory_db, test_users):
        """24. Admin accesses GET /feedback/stats successfully."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/feedback/stats", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_condition_25_admin_can_access_records(self, client, in_memory_db, test_users):
        """25. Admin accesses GET /feedback/records successfully."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/feedback/records", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_condition_26_student_cannot_access_stats(self, client, in_memory_db, test_users):
        """26. Student cannot access GET /feedback/stats (HTTP 403)."""
        student = test_users["student"]
        token = create_access_token(data={"sub": str(student.id), "username": student.username, "role": student.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/feedback/stats", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_condition_27_student_cannot_access_records(self, client, in_memory_db, test_users):
        """27. Student cannot access GET /feedback/records (HTTP 403)."""
        student = test_users["student"]
        token = create_access_token(data={"sub": str(student.id), "username": student.username, "role": student.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/feedback/records", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# REGRESSION & MIGRATION INTEGRITY (28 - 30)
# ==============================================================================

class TestRegressionAndIntegrity:
    """Validates student endpoints remain open, data persists, and migration head."""

    def test_condition_28_student_endpoints_remain_functional(self, client, in_memory_db):
        """28. Student-facing feedback submission does not require authentication."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # POST /api/v1/feedback
            sub_res = client.post(
                "/api/v1/feedback",
                json={"feedback_text": "The lecture slides were clear.", "department": "CS", "semester": "Sem 3"},
            )
            assert sub_res.status_code == 201

            # POST /api/v1/feedback/analyze-and-save
            save_res = client.post(
                "/api/v1/feedback/analyze-and-save",
                json={"feedback": "The internet connection in the library is too slow.", "department": "IT"},
            )
            assert save_res.status_code == 201
            assert save_res.json()["priority_score"] is not None

            # GET /api/v1/feedback (legacy list endpoint)
            list_res = client.get("/api/v1/feedback")
            assert list_res.status_code == 200
            assert len(list_res.json()) >= 2
        finally:
            app.dependency_overrides.clear()

    def test_condition_29_existing_records_unchanged(self, in_memory_db):
        """29. Inserting and querying users does not modify or delete feedback records."""
        fb = Feedback(feedback_text="Baseline feedback record", department="Physics")
        in_memory_db.add(fb)
        in_memory_db.commit()
        in_memory_db.refresh(fb)

        # Create user
        user = User(username="unique_user_test", password_hash=hash_password("Pass123!"), role="student")
        in_memory_db.add(user)
        in_memory_db.commit()

        # Query feedback again
        queried_fb = in_memory_db.get(Feedback, fb.id)
        assert queried_fb is not None
        assert queried_fb.feedback_text == "Baseline feedback record"
        assert queried_fb.department == "Physics"

    def test_condition_30_migration_head_is_003(self):
        """30. Alembic migration history maintains 003_create_users lineage."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = script.get_heads()

        assert len(heads) == 1
        assert heads[0] in ("003_create_users", "004_add_google_identity_to_users")
        rev_003 = script.get_revision("003_create_users")
        assert rev_003 is not None
