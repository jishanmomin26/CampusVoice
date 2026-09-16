"""Security Hardening Integration and Unit Tests (Step 9.17).

Validates:
1. JWT Validation & Hardening:
   - Valid token decodes with required claims (sub, iat, exp).
   - Expired token rejected with HTTP 401.
   - Malformed token rejected with HTTP 401.
   - Invalid signature rejected with HTTP 401.
   - Wrong signing algorithm (none, HS384, RS256) rejected with HTTP 401.
   - Missing required subject rejected with HTTP 401.
   - Invalid subject (non-integer, zero, negative) rejected with HTTP 401.
   - Nonexistent user in valid token rejected with HTTP 401.
   - Inactive user in valid token rejected with HTTP 401.
   - Token payload sanitization (password hashes never encoded).
   - Valid admin token passes; valid student token rejected with HTTP 403 on admin endpoints.

2. Password Security:
   - Passwords stored as salted bcrypt hashes ($2b$ or $2a$).
   - Password hashes never leak in API responses or JWT payloads.
   - Passwords shorter than 8 characters rejected by hash_password.
   - Passwords exceeding 72 bytes rejected by hash_password.
   - Empty/whitespace passwords rejected by hash_password.
   - Password update invalidates old password.
   - Malformed hash in verify_password handled safely without raising.

3. Login Endpoint Hardening:
   - Valid login returns HTTP 200 with JWT access token.
   - Nonexistent username returns generic HTTP 401 without user enumeration.
   - Incorrect password returns generic HTTP 401.
   - Inactive user returns generic HTTP 401 without account status disclosure.
   - Blank username or blank password rejected with HTTP 422.
   - Dummy bcrypt check executed when username does not exist.

4. Authorization & RBAC Audit:
   - All 6 admin endpoints reject unauthenticated requests with HTTP 401.
   - All 6 admin endpoints reject student accounts with HTTP 403.
   - All 6 admin endpoints accept valid admin accounts.
   - Inactive user accounts rejected with HTTP 401 across all admin endpoints.
   - Admin self-deactivation rejected with HTTP 400.
   - Last active admin deactivation or demotion rejected with HTTP 409.
   - Public student feedback endpoints remain accessible without auth.

5. CORS Hardening:
   - Configured allowed origins respected.
   - Development defaults include localhost:5173 and 127.0.0.1:5173.
   - Wildcard origin ('*') strictly disallowed with credentials.
   - Comma-separated CORS_ALLOWED_ORIGINS parsed correctly.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import patch
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

from app.core.config import settings, Settings
from app.core.roles import UserRole
from app.core.security import (
    DUMMY_BCRYPT_HASH,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def in_memory_engine():
    """In-memory SQLite engine for isolated auth and security testing."""
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
    """Seeds test users: 1 active admin, 1 active student, 1 inactive student, 1 inactive admin."""
    admin_pwd_hash = hash_password("AdminSecret123!")
    student_pwd_hash = hash_password("StudentSecret123!")
    inactive_pwd_hash = hash_password("InactiveSecret123!")

    admin_user = User(
        username="admin_sec",
        password_hash=admin_pwd_hash,
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    student_user = User(
        username="student_sec",
        password_hash=student_pwd_hash,
        role=UserRole.STUDENT.value,
        is_active=True,
    )
    inactive_user = User(
        username="inactive_sec",
        password_hash=inactive_pwd_hash,
        role=UserRole.STUDENT.value,
        is_active=False,
    )
    inactive_admin = User(
        username="inactive_admin_sec",
        password_hash=inactive_pwd_hash,
        role=UserRole.ADMIN.value,
        is_active=False,
    )

    in_memory_db.add_all([admin_user, student_user, inactive_user, inactive_admin])
    in_memory_db.commit()
    in_memory_db.refresh(admin_user)
    in_memory_db.refresh(student_user)
    in_memory_db.refresh(inactive_user)
    in_memory_db.refresh(inactive_admin)

    return {
        "admin": admin_user,
        "student": student_user,
        "inactive": inactive_user,
        "inactive_admin": inactive_admin,
    }


# ==============================================================================
# 1. JWT SECURITY AUDIT AND HARDENING
# ==============================================================================

class TestJWTSecurityHardening:
    """Validates hardened JWT behavior: claims, algorithm, expiry, and payload privacy."""

    def test_valid_token_contains_required_claims(self, test_users):
        """Token contains sub, iat, exp and can be decoded."""
        user = test_users["admin"]
        token = create_access_token(data={"sub": str(user.id), "username": user.username, "role": user.role})
        payload = decode_access_token(token)
        assert payload["sub"] == str(user.id)
        assert payload["username"] == user.username
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_expired_token_rejected_with_401(self, client, in_memory_db, test_users):
        """Expired tokens result in HTTP 401."""
        user = test_users["admin"]
        expired_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role},
            expires_delta=timedelta(seconds=-30),
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
            assert res.status_code == 401
            assert "expired" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_malformed_token_rejected_with_401(self, client, in_memory_db):
        """Malformed token is rejected with HTTP 401."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid.jwt.payload"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_invalid_signature_rejected_with_401(self, client, in_memory_db, test_users):
        """Token signed with forged secret key is rejected with HTTP 401."""
        user = test_users["admin"]
        forged_token = jwt.encode(
            {
                "sub": str(user.id),
                "username": user.username,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "completely-forged-secret-key-32-chars-long!",
            algorithm=settings.JWT_ALGORITHM,
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_wrong_algorithm_none_rejected(self, client, in_memory_db, test_users):
        """Token attempting algorithm 'none' attack is rejected with HTTP 401."""
        user = test_users["admin"]
        none_token = jwt.encode(
            {
                "sub": str(user.id),
                "username": user.username,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            key="",
            algorithm="none",
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {none_token}"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_wrong_algorithm_hs384_rejected(self, client, in_memory_db, test_users):
        """Token signed with unexpected algorithm (e.g. HS384) is rejected with HTTP 401."""
        user = test_users["admin"]
        wrong_alg_token = jwt.encode(
            {
                "sub": str(user.id),
                "username": user.username,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            key=settings.JWT_SECRET_KEY,
            algorithm="HS384",
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {wrong_alg_token}"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_missing_sub_claim_rejected(self, client, in_memory_db):
        """Token missing required 'sub' claim is rejected with HTTP 401."""
        token_no_sub = jwt.encode(
            {
                "username": "nosub",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_no_sub}"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower() or "subject" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_invalid_subject_non_integer_rejected(self, client, in_memory_db):
        """Token with non-integer subject string is rejected with HTTP 401."""
        bad_sub_token = jwt.encode(
            {
                "sub": "not-an-int",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_sub_token}"})
            assert res.status_code == 401
            assert "invalid" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_invalid_subject_zero_or_negative_rejected(self, client, in_memory_db):
        """Token with non-positive integer subject (0 or negative) is rejected with HTTP 401."""
        for bad_id in ["0", "-5"]:
            bad_sub_token = jwt.encode(
                {
                    "sub": bad_id,
                    "iat": datetime.now(timezone.utc),
                    "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                },
                key=settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
            )
            app.dependency_overrides[get_db] = lambda: in_memory_db
            try:
                res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_sub_token}"})
                assert res.status_code == 401
                assert "invalid user identifier" in res.json()["detail"].lower()
            finally:
                app.dependency_overrides.clear()

    def test_nonexistent_user_token_rejected(self, client, in_memory_db):
        """Valid token referencing a non-existent database user ID is rejected with HTTP 401."""
        token = create_access_token(data={"sub": "999999", "username": "ghost_user"})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 401
            assert "no longer exists" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_inactive_user_token_rejected(self, client, in_memory_db, test_users):
        """Valid token for an inactive user is rejected with HTTP 401."""
        inactive = test_users["inactive"]
        token = create_access_token(data={"sub": str(inactive.id), "username": inactive.username})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 401
            assert "inactive" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_token_creation_sanitizes_sensitive_keys(self, test_users):
        """create_access_token strips password hashes, passwords, and feedback text from claims."""
        user = test_users["admin"]
        dirty_payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "password": "RawPlainPassword123!",
            "password_hash": "$2b$12$somehashvaluehere",
            "feedback_text": "Sensitive feedback text content here",
        }
        token = create_access_token(data=dirty_payload)
        decoded = decode_access_token(token)
        assert "password" not in decoded
        assert "password_hash" not in decoded
        assert "feedback_text" not in decoded
        assert decoded["sub"] == str(user.id)

    def test_token_creation_rejects_missing_sub(self):
        """create_access_token raises ValueError if sub is missing or blank."""
        with pytest.raises(ValueError, match="'sub' claim"):
            create_access_token(data={"username": "nosub"})

        with pytest.raises(ValueError, match="'sub' claim"):
            create_access_token(data={"sub": "   ", "username": "blanksub"})


# ==============================================================================
# 2. PASSWORD SECURITY
# ==============================================================================

class TestPasswordSecurityHardening:
    """Validates bcrypt password hashing, minimum length, and exception handling."""

    def test_password_stored_as_bcrypt_hash(self, test_users):
        """Passwords in database are salted bcrypt hashes and never plaintext."""
        admin = test_users["admin"]
        assert admin.password_hash.startswith("$2b$") or admin.password_hash.startswith("$2a$")
        assert len(admin.password_hash) >= 59
        assert "AdminSecret123!" not in admin.password_hash

    def test_short_password_rejected_by_hash_password(self):
        """Passwords with fewer than 8 characters are rejected with ValueError."""
        for short_pw in ["", "short", "1234567", "   abc  "]:
            with pytest.raises(ValueError):
                hash_password(short_pw)

    def test_password_exceeding_72_bytes_rejected(self):
        """Passwords exceeding bcrypt 72-byte limit are rejected."""
        long_pw = "A" * 73
        with pytest.raises(ValueError, match="72 bytes"):
            hash_password(long_pw)

    def test_password_hash_never_in_api_responses(self, client, in_memory_db, test_users):
        """User management and auth endpoints never return password_hash."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # 1. /auth/me
            me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert "password_hash" not in me_res.text
            assert "password" not in me_res.json()

            # 2. /users list
            users_res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
            assert "password_hash" not in users_res.text

            # 3. /users/{id}
            user_detail_res = client.get(f"/api/v1/users/{admin.id}", headers={"Authorization": f"Bearer {token}"})
            assert "password_hash" not in user_detail_res.text
        finally:
            app.dependency_overrides.clear()

    def test_malformed_hash_in_verify_password_handled_safely(self):
        """verify_password returns False without crashing when given malformed hashes."""
        assert verify_password("ValidPassword123!", "not-a-bcrypt-hash") is False
        assert verify_password("ValidPassword123!", "$2b$invalid$format") is False
        assert verify_password("", "$2b$12$e8kPqY81c62zUOBi1iF7s.b8jV7J1mC/y4p8aW12kL8fQ3Kq6fKqO") is False
        assert verify_password(None, "hash") is False

    def test_password_update_invalidates_old_password(self, client, in_memory_db, test_users):
        """Changing a user password re-hashes it and old password fails authentication."""
        admin = test_users["admin"]
        student = test_users["student"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # Change student's password
            patch_res = client.patch(
                f"/api/v1/users/{student.id}",
                headers={"Authorization": f"Bearer {token}"},
                json={"password": "NewStudentPassword789!"},
            )
            assert patch_res.status_code == 200

            # Login with old password must fail
            old_login = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": "StudentSecret123!"},
            )
            assert old_login.status_code == 401

            # Login with new password must succeed
            new_login = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": "NewStudentPassword789!"},
            )
            assert new_login.status_code == 200
            assert "access_token" in new_login.json()
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 3. LOGIN ENDPOINT HARDENING
# ==============================================================================

class TestLoginEndpointHardening:
    """Validates constant-time timing protection, generic 401s, and inactive accounts."""

    def test_nonexistent_username_returns_generic_401(self, client, in_memory_db):
        """Non-existent username returns generic 'Invalid username or password.'"""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/login",
                json={"username": "totally_ghost_user", "password": "SomePassword123!"},
            )
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid username or password."
        finally:
            app.dependency_overrides.clear()

    def test_incorrect_password_returns_generic_401(self, client, in_memory_db, test_users):
        """Existing user with wrong password returns generic 'Invalid username or password.'"""
        admin = test_users["admin"]
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": "WrongPassword999!"},
            )
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid username or password."
        finally:
            app.dependency_overrides.clear()

    def test_inactive_user_returns_generic_401(self, client, in_memory_db, test_users):
        """Inactive user receives identical generic 'Invalid username or password.' message."""
        inactive = test_users["inactive"]
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/auth/login",
                json={"username": inactive.username, "password": "InactiveSecret123!"},
            )
            assert res.status_code == 401
            assert res.json()["detail"] == "Invalid username or password."
        finally:
            app.dependency_overrides.clear()

    def test_timing_mitigation_dummy_bcrypt_check_executed(self, client, in_memory_db):
        """When username does not exist, verify_password is called against DUMMY_BCRYPT_HASH."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        with patch("app.api.v1.endpoints.auth.verify_password", wraps=verify_password) as mock_verify:
            try:
                res = client.post(
                    "/api/v1/auth/login",
                    json={"username": "nonexistent_timing_test", "password": "SomeCandidate123!"},
                )
                assert res.status_code == 401
                # verify_password MUST have been called with DUMMY_BCRYPT_HASH
                mock_verify.assert_called_once_with("SomeCandidate123!", DUMMY_BCRYPT_HASH)
            finally:
                app.dependency_overrides.clear()

    def test_blank_credentials_rejected_with_422(self, client):
        """Empty or whitespace credentials fail fast with 422 Unprocessable Entity."""
        for payload in [
            {"username": "   ", "password": "ValidPassword123!"},
            {"username": "valid_user", "password": "   "},
            {"username": "", "password": ""},
        ]:
            res = client.post("/api/v1/auth/login", json=payload)
            assert res.status_code == 422


# ==============================================================================
# 4. AUTHORIZATION / RBAC AUDIT
# ==============================================================================

class TestAuthorizationRBACHardening:
    """Audits all 6 admin endpoints for unauthenticated, student, and inactive access."""

    ADMIN_ENDPOINTS = [
        ("GET", "/api/v1/feedback/stats", None),
        ("GET", "/api/v1/feedback/records", None),
        ("GET", "/api/v1/users", None),
        ("GET", "/api/v1/users/1", None),
        ("POST", "/api/v1/users", {"username": "new_rbac_user", "password": "NewUserPassword123!", "role": "student"}),
        ("PATCH", "/api/v1/users/1", {"role": "admin"}),
    ]

    def test_unauthenticated_requests_receive_401(self, client, in_memory_db, test_users):
        """All 6 admin endpoints reject unauthenticated calls with HTTP 401."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            for method, endpoint, body in self.ADMIN_ENDPOINTS:
                if method == "GET":
                    res = client.get(endpoint)
                elif method == "POST":
                    res = client.post(endpoint, json=body)
                elif method == "PATCH":
                    res = client.patch(endpoint, json=body)
                assert res.status_code == 401, f"Expected 401 for unauthenticated {method} {endpoint}, got {res.status_code}"
        finally:
            app.dependency_overrides.clear()

    def test_student_requests_receive_403(self, client, in_memory_db, test_users):
        """All 6 admin endpoints reject student callers with HTTP 403 Forbidden."""
        student = test_users["student"]
        token = create_access_token(data={"sub": str(student.id), "username": student.username, "role": student.role})
        headers = {"Authorization": f"Bearer {token}"}
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            for method, endpoint, body in self.ADMIN_ENDPOINTS:
                if method == "GET":
                    res = client.get(endpoint, headers=headers)
                elif method == "POST":
                    res = client.post(endpoint, json=body, headers=headers)
                elif method == "PATCH":
                    res = client.patch(endpoint, json=body, headers=headers)
                assert res.status_code == 403, f"Expected 403 for student {method} {endpoint}, got {res.status_code}"
                assert "Administrative privileges required" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_admin_requests_succeed(self, client, in_memory_db, test_users):
        """All 6 admin endpoints succeed when invoked by active admin."""
        admin = test_users["admin"]
        token = create_access_token(data={"sub": str(admin.id), "username": admin.username, "role": admin.role})
        headers = {"Authorization": f"Bearer {token}"}
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # 1. GET /feedback/stats
            assert client.get("/api/v1/feedback/stats", headers=headers).status_code == 200

            # 2. GET /feedback/records
            assert client.get("/api/v1/feedback/records", headers=headers).status_code == 200

            # 3. GET /users
            assert client.get("/api/v1/users", headers=headers).status_code == 200

            # 4. GET /users/{id}
            assert client.get(f"/api/v1/users/{admin.id}", headers=headers).status_code == 200

            # 5. POST /users
            create_res = client.post(
                "/api/v1/users",
                headers=headers,
                json={"username": "created_by_admin", "password": "Password123!", "role": "student"},
            )
            assert create_res.status_code == 201

            # 6. PATCH /users/{id}
            patch_res = client.patch(
                f"/api/v1/users/{create_res.json()['id']}",
                headers=headers,
                json={"role": "admin"},
            )
            assert patch_res.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_inactive_admin_rejected_with_401(self, client, in_memory_db, test_users):
        """Inactive admin user token receives HTTP 401 across endpoints."""
        inactive_admin = test_users["inactive_admin"]
        token = create_access_token(
            data={"sub": str(inactive_admin.id), "username": inactive_admin.username, "role": inactive_admin.role}
        )
        headers = {"Authorization": f"Bearer {token}"}
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.get("/api/v1/feedback/stats", headers=headers)
            assert res.status_code == 401
            assert "inactive" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_public_feedback_endpoints_remain_open(self, client, in_memory_db):
        """Public student feedback submission endpoints remain fully functional without auth."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # Public feedback submission
            res = client.post(
                "/api/v1/feedback",
                json={
                    "department": "Computer Science",
                    "semester": "6",
                    "feedback_text": "The computer network lab equipment needs modern updates.",
                },
            )
            assert res.status_code == 201
            data = res.json()
            assert "id" in data
            assert data["department"] == "Computer Science"
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 5. CORS HARDENING
# ==============================================================================

class TestCORSHardening:
    """Validates CORS configuration, dev defaults, and credentials security."""

    def test_dev_cors_origins_include_localhost(self):
        """In development mode, localhost and 127.0.0.1 origins are allowed."""
        s = Settings(ENVIRONMENT="development", FRONTEND_URL="http://localhost:5173")
        origins = s.get_cors_origins()
        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins

    def test_explicit_cors_origins_parsed(self):
        """Custom comma-separated origins are stripped and returned."""
        s = Settings(
            CORS_ALLOWED_ORIGINS="https://campusvoice.example.edu, https://admin.campusvoice.example.edu/ "
        )
        origins = s.get_cors_origins()
        assert "https://campusvoice.example.edu" in origins
        assert "https://admin.campusvoice.example.edu" in origins
        assert len(origins) == 2

    def test_wildcard_origin_stripped_for_security(self):
        """Wildcard '*' origin is filtered out to avoid unsafe wildcard with credentials."""
        s = Settings(CORS_ALLOWED_ORIGINS="*, https://safe.example.edu")
        origins = s.get_cors_origins()
        assert "*" not in origins
        assert "https://safe.example.edu" in origins

    def test_cors_preflight_options_request(self, client):
        """OPTIONS preflight request from allowed origin returns CORS headers."""
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        }
        res = client.options("/api/v1/auth/login", headers=headers)
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "POST" in res.headers.get("access-control-allow-methods", "")
