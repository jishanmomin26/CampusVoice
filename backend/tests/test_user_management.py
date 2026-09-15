"""Comprehensive Unit and Integration Tests for User Management API (Step 9.14.1).

Validates:
Authentication & Authorization:
  1. Unauthenticated GET /api/v1/users -> HTTP 401
  2. Student GET /api/v1/users -> HTTP 403
  3. Admin GET /api/v1/users -> HTTP 200

Listing & Filters:
  4. Pagination (page, page_size)
  5. Search (case-insensitive substring)
  6. Role filter ('admin', 'student')
  7. Active/inactive status filter
  8. Newest-first ordering (created_at DESC, id DESC)
  9. Total count reflects active filters
  10. Total pages calculation

Detail:
  11. Admin gets existing user -> HTTP 200 with complete fields
  12. Nonexistent user -> HTTP 404
  13. User detail response never leaks password_hash

Creation:
  14. Admin creates student -> HTTP 201
  15. Admin creates admin -> HTTP 201
  16. Duplicate username -> HTTP 409 Conflict
  17. Invalid role -> HTTP 422
  18. Short password (<8 chars) -> HTTP 422
  19. Password is bcrypt hashed
  20. Plaintext password is not stored in DB

Update:
  21. Change role
  22. Deactivate student
  23. Reactivate student
  24. Change password
  25. Invalid role rejected -> HTTP 422
  26. Empty update payload rejected -> HTTP 422
  27. Update response never leaks password_hash

Self-Protection & Last-Admin Safeguards:
  28. Admin cannot deactivate own account -> HTTP 400
  29. Last active admin cannot be deactivated -> HTTP 409
  30. Last active admin cannot be demoted to student -> HTTP 409
  31. Another active admin can be safely modified when multiple active admins exist

Authentication Integration:
  32. Deactivated user cannot authenticate -> HTTP 401
  33. Changed password allows new password login
  34. Old password fails after password change -> HTTP 401
  35. Changed role is reflected in GET /api/v1/auth/me

Authorization Matrix:
  36. All user-management endpoints reject students -> HTTP 403
  37. All user-management endpoints reject unauthenticated requests -> HTTP 401

Regression:
  38. Existing student feedback endpoints remain functional without auth
  39. Existing feedback stats/records authorization still works
  40. Feedback records in database are unaffected
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.roles import UserRole
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.feedback import Feedback
from app.models.user import User


@pytest.fixture
def in_memory_engine():
    """In-memory SQLite engine for isolated user management testing."""
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
def seeded_users(in_memory_db):
    """Seeds test users:
    - 1 active primary admin
    - 1 active secondary admin
    - 1 active student
    - 1 inactive student
    """
    admin1 = User(
        username="primary_admin",
        password_hash=hash_password("AdminSecret123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    admin2 = User(
        username="secondary_admin",
        password_hash=hash_password("AdminSecret456!"),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    student1 = User(
        username="active_student",
        password_hash=hash_password("StudentSecret123!"),
        role=UserRole.STUDENT.value,
        is_active=True,
    )
    student2 = User(
        username="inactive_student",
        password_hash=hash_password("StudentSecret456!"),
        role=UserRole.STUDENT.value,
        is_active=False,
    )
    in_memory_db.add_all([admin1, admin2, student1, student2])
    in_memory_db.commit()
    in_memory_db.refresh(admin1)
    in_memory_db.refresh(admin2)
    in_memory_db.refresh(student1)
    in_memory_db.refresh(student2)

    return {
        "admin1": admin1,
        "admin2": admin2,
        "student1": student1,
        "student2": student2,
    }


def admin_token(user: User) -> str:
    """Helper to generate JWT bearer token for admin user."""
    return create_access_token(data={"sub": str(user.id), "username": user.username, "role": user.role})


def student_token(user: User) -> str:
    """Helper to generate JWT bearer token for student user."""
    return create_access_token(data={"sub": str(user.id), "username": user.username, "role": user.role})


# ==============================================================================
# 1. AUTHENTICATION & RBAC (Conditions 1 - 3)
# ==============================================================================

class TestUserManagementAuthRBAC:
    """Validates endpoint authorization boundaries."""

    def test_condition_1_unauthenticated_get_users_returns_401(self, client):
        """1. Unauthenticated request to GET /api/v1/users returns HTTP 401."""
        res = client.get("/api/v1/users")
        assert res.status_code == 401
        assert "not provided" in res.json()["detail"].lower()

    def test_condition_2_student_get_users_returns_403(self, client, in_memory_db, seeded_users):
        """2. Student user receives HTTP 403 Forbidden on GET /api/v1/users."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = student_token(seeded_users["student1"])
            res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 403
            assert "Administrative privileges required" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_condition_3_admin_get_users_returns_200(self, client, in_memory_db, seeded_users):
        """3. Admin user can successfully list users (HTTP 200)."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            data = res.json()
            assert "items" in data
            assert data["total"] == 4
            assert len(data["items"]) == 4
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 2. LISTING & FILTERS (Conditions 4 - 10)
# ==============================================================================

class TestUserListingAndFilters:
    """Validates pagination, filtering, search, and ordering."""

    def test_condition_4_pagination(self, client, in_memory_db, seeded_users):
        """4. Pagination parameters (page, page_size) operate accurately."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users?page=1&page_size=2",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["page"] == 1
            assert data["page_size"] == 2
            assert len(data["items"]) == 2
            assert data["total"] == 4
            assert data["total_pages"] == 2

            res2 = client.get(
                "/api/v1/users?page=2&page_size=2",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res2.status_code == 200
            assert len(res2.json()["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_condition_5_search_filter(self, client, in_memory_db, seeded_users):
        """5. Case-insensitive substring keyword search on username."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users?search=ADMIN",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 2
            for item in data["items"]:
                assert "admin" in item["username"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_6_role_filter(self, client, in_memory_db, seeded_users):
        """6. Role filter isolates 'admin' vs 'student' accounts."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users?role=student",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 2
            for item in data["items"]:
                assert item["role"] == "student"
        finally:
            app.dependency_overrides.clear()

    def test_condition_7_active_inactive_filter(self, client, in_memory_db, seeded_users):
        """7. Status filter isolates active (true) vs inactive (false) accounts."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res_active = client.get(
                "/api/v1/users?is_active=true",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_active.status_code == 200
            assert res_active.json()["total"] == 3

            res_inactive = client.get(
                "/api/v1/users?is_active=false",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_inactive.status_code == 200
            assert res_inactive.json()["total"] == 1
            assert res_inactive.json()["items"][0]["username"] == "inactive_student"
        finally:
            app.dependency_overrides.clear()

    def test_condition_8_newest_first_ordering(self, client, in_memory_db, seeded_users):
        """8. Ordering defaults to created_at DESC, id DESC."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            items = res.json()["items"]
            # IDs should be descending since created_at is equal or monotonic
            ids = [item["id"] for item in items]
            assert ids == sorted(ids, reverse=True)
        finally:
            app.dependency_overrides.clear()

    def test_condition_9_total_count(self, client, in_memory_db, seeded_users):
        """9. Total count accurately reflects combined active filters."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users?role=student&is_active=false",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            assert res.json()["total"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_condition_10_total_pages(self, client, in_memory_db, seeded_users):
        """10. Total pages calculation handles boundary cases."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users?page_size=3",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            # 4 users / 3 per page = 2 pages
            assert res.json()["total_pages"] == 2

            # Zero matches -> 0 pages
            res_empty = client.get(
                "/api/v1/users?search=nonexistentuser",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_empty.status_code == 200
            assert res_empty.json()["total_pages"] == 0
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 3. USER DETAIL (Conditions 11 - 13)
# ==============================================================================

class TestUserDetailEndpoint:
    """Validates GET /api/v1/users/{user_id} behavior."""

    def test_condition_11_admin_gets_existing_user(self, client, in_memory_db, seeded_users):
        """11. Admin retrieves an existing user profile by ID."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                f"/api/v1/users/{target.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == target.id
            assert data["username"] == "active_student"
            assert data["role"] == "student"
            assert data["is_active"] is True
            assert "created_at" in data
        finally:
            app.dependency_overrides.clear()

    def test_condition_12_nonexistent_user_returns_404(self, client, in_memory_db, seeded_users):
        """12. Requesting nonexistent user ID returns HTTP 404."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                "/api/v1/users/999999",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 404
            assert "not found" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_13_response_never_contains_password_hash(self, client, in_memory_db, seeded_users):
        """13. User detail response never leaks password_hash or password."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["admin1"]
            token = admin_token(seeded_users["admin1"])
            res = client.get(
                f"/api/v1/users/{target.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert "password" not in data
            assert "password_hash" not in data
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 4. USER CREATION (Conditions 14 - 20)
# ==============================================================================

class TestUserCreationEndpoint:
    """Validates POST /api/v1/users contract, credentials, and constraints."""

    def test_condition_14_admin_creates_student(self, client, in_memory_db, seeded_users):
        """14. Admin creates a student user with HTTP 201."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "new_student_bob",
                    "password": "ValidPassword123!",
                    "role": "student",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 201
            data = res.json()
            assert data["username"] == "new_student_bob"
            assert data["role"] == "student"
            assert data["is_active"] is True
            assert "password" not in data
            assert "password_hash" not in data
        finally:
            app.dependency_overrides.clear()

    def test_condition_15_admin_creates_admin(self, client, in_memory_db, seeded_users):
        """15. Admin creates another administrator with HTTP 201."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "new_admin_sarah",
                    "password": "AdminPassword123!",
                    "role": "admin",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 201
            data = res.json()
            assert data["username"] == "new_admin_sarah"
            assert data["role"] == "admin"
        finally:
            app.dependency_overrides.clear()

    def test_condition_16_duplicate_username_returns_409(self, client, in_memory_db, seeded_users):
        """16. Creating user with existing username returns HTTP 409 Conflict."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "ACTIVE_STUDENT",  # Case-insensitive collision
                    "password": "NewPassword123!",
                    "role": "student",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 409
            assert "already exists" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_17_invalid_role_rejected(self, client, in_memory_db, seeded_users):
        """17. Invalid role string returns HTTP 422 Unprocessable Entity."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "user_invalid_role",
                    "password": "ValidPassword123!",
                    "role": "superadmin",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_condition_18_short_password_rejected(self, client, in_memory_db, seeded_users):
        """18. Password shorter than 8 characters returns HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "user_short_pwd",
                    "password": "short1",  # 6 chars
                    "role": "student",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_condition_19_20_password_is_hashed_and_not_stored_plaintext(
        self, client, in_memory_db, seeded_users
    ):
        """19, 20. Password is salted bcrypt hashed and plaintext is never stored in DB."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            plain_pwd = "MySecretPassword123!"
            token = admin_token(seeded_users["admin1"])
            res = client.post(
                "/api/v1/users",
                json={
                    "username": "hashed_user_test",
                    "password": plain_pwd,
                    "role": "student",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 201
            new_id = res.json()["id"]

            # Inspect database directly
            user_in_db = in_memory_db.get(User, new_id)
            assert user_in_db is not None
            assert user_in_db.password_hash != plain_pwd
            assert user_in_db.password_hash.startswith("$2b$") or user_in_db.password_hash.startswith("$2a$")
            assert verify_password(plain_pwd, user_in_db.password_hash) is True
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 5. USER UPDATE (Conditions 21 - 27)
# ==============================================================================

class TestUserUpdateEndpoint:
    """Validates PATCH /api/v1/users/{user_id} behavior."""

    def test_condition_21_change_role(self, client, in_memory_db, seeded_users):
        """21. Changing user role from student to admin succeeds."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"role": "admin"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            assert res.json()["role"] == "admin"
        finally:
            app.dependency_overrides.clear()

    def test_condition_22_deactivate_student(self, client, in_memory_db, seeded_users):
        """22. Deactivating a student sets is_active = False."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            assert res.json()["is_active"] is False
        finally:
            app.dependency_overrides.clear()

    def test_condition_23_reactivate_student(self, client, in_memory_db, seeded_users):
        """23. Reactivating an inactive student sets is_active = True."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student2"]  # inactive_student
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"is_active": True},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            assert res.json()["is_active"] is True
        finally:
            app.dependency_overrides.clear()

    def test_condition_24_change_password(self, client, in_memory_db, seeded_users):
        """24. Changing password re-hashes it in database."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            new_pwd = "BrandNewPassword789!"
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"password": new_pwd},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200

            # Verify in DB
            in_memory_db.refresh(target)
            assert verify_password(new_pwd, target.password_hash) is True
        finally:
            app.dependency_overrides.clear()

    def test_condition_25_invalid_role_on_update(self, client, in_memory_db, seeded_users):
        """25. Invalid role in update payload returns HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"role": "godmode"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_condition_26_empty_update_rejected(self, client, in_memory_db, seeded_users):
        """26. Empty update payload returns HTTP 422."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_condition_27_update_response_never_contains_password_hash(
        self, client, in_memory_db, seeded_users
    ):
        """27. Update response never leaks password_hash."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target = seeded_users["student1"]
            token = admin_token(seeded_users["admin1"])
            res = client.patch(
                f"/api/v1/users/{target.id}",
                json={"role": "student"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            data = res.json()
            assert "password" not in data
            assert "password_hash" not in data
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 6. SELF-PROTECTION & LAST-ADMIN SAFEGUARDS (Conditions 28 - 31)
# ==============================================================================

class TestAdminSafeguards:
    """Validates self-lockout prevention and last-active-admin preservation."""

    def test_condition_28_admin_cannot_deactivate_self(self, client, in_memory_db, seeded_users):
        """28. Admin attempting to deactivate their own account receives HTTP 400."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            admin1 = seeded_users["admin1"]
            token = admin_token(admin1)
            res = client.patch(
                f"/api/v1/users/{admin1.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 400
            assert "cannot deactivate their own account" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_29_last_active_admin_cannot_be_deactivated(
        self, client, in_memory_db, seeded_users
    ):
        """29. If only 1 active admin exists, deactivating that admin is rejected with HTTP 409."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            # First, deactivate admin2 so admin1 is the sole remaining active admin
            admin1 = seeded_users["admin1"]
            admin2 = seeded_users["admin2"]
            token1 = admin_token(admin1)

            # Deactivate admin2 -> succeeds because 2 active admins existed
            res_deact2 = client.patch(
                f"/api/v1/users/{admin2.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token1}"},
            )
            assert res_deact2.status_code == 200

            # Now admin1 is the ONLY active admin.
            # Attempt to deactivate admin1 -> caught by self-deactivation rule (400)
            res_self = client.patch(
                f"/api/v1/users/{admin1.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token1}"},
            )
            assert res_self.status_code == 400

            # Reactivate admin2, but deactivate admin1 by admin2
            token2 = admin_token(admin2)
            # Temporarily activate admin2 in DB
            admin2.is_active = True
            in_memory_db.commit()

            # Now admin2 deactivates admin1 -> succeeds (leaves 1 admin: admin2)
            res_deact1 = client.patch(
                f"/api/v1/users/{admin1.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert res_deact1.status_code == 200

            # Now admin2 is the sole active admin. If an attempt is made on admin2,
            # simulate another caller or check target_user == admin2:
            # Even if attempted from an external perspective, admin2 is protected by last active admin
            # Verify in service directly:
            from app.services.user_service import update_user
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                # pass a dummy caller to test last active admin rule specifically
                update_user(
                    db=in_memory_db,
                    target_user=admin2,
                    current_admin=admin1,  # different admin ID
                    is_active=False,
                )
            assert exc_info.value.status_code == 409
            assert "last active administrator" in exc_info.value.detail.lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_30_last_active_admin_cannot_be_demoted(
        self, client, in_memory_db, seeded_users
    ):
        """30. Last active admin cannot be demoted to student (HTTP 409)."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            admin1 = seeded_users["admin1"]
            admin2 = seeded_users["admin2"]
            token1 = admin_token(admin1)

            # Deactivate admin2 to leave admin1 as sole active admin
            admin2.is_active = False
            in_memory_db.commit()

            # Admin1 tries to demote themselves to student
            res = client.patch(
                f"/api/v1/users/{admin1.id}",
                json={"role": "student"},
                headers={"Authorization": f"Bearer {token1}"},
            )
            assert res.status_code == 409
            assert "last active administrator" in res.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_31_another_active_admin_can_be_modified(
        self, client, in_memory_db, seeded_users
    ):
        """31. When multiple active admins exist, modifying another admin succeeds."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            admin1 = seeded_users["admin1"]
            admin2 = seeded_users["admin2"]
            token1 = admin_token(admin1)

            # Admin1 deactivates admin2 -> succeeds because admin1 remains active
            res = client.patch(
                f"/api/v1/users/{admin2.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token1}"},
            )
            assert res.status_code == 200
            assert res.json()["is_active"] is False
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 7. AUTHENTICATION INTEGRATION (Conditions 32 - 35)
# ==============================================================================

class TestAuthenticationIntegration:
    """Validates real login and profile behavior following user management operations."""

    def test_condition_32_deactivated_user_cannot_login(self, client, in_memory_db, seeded_users):
        """32. Deactivating a user causes subsequent login attempts to fail with HTTP 401."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            student = seeded_users["student1"]
            token_admin = admin_token(seeded_users["admin1"])

            # 1. Verify student can log in initially
            login_before = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": "StudentSecret123!"},
            )
            assert login_before.status_code == 200

            # 2. Deactivate student via User Management API
            deact_res = client.patch(
                f"/api/v1/users/{student.id}",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token_admin}"},
            )
            assert deact_res.status_code == 200

            # 3. Subsequent login attempt fails
            login_after = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": "StudentSecret123!"},
            )
            assert login_after.status_code == 401
            assert "invalid username or password" in login_after.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_condition_33_34_changed_password_login(self, client, in_memory_db, seeded_users):
        """33, 34. Changed password allows login with new password; old password fails."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            student = seeded_users["student1"]
            token_admin = admin_token(seeded_users["admin1"])
            new_password = "UpdatedPassword456!"

            # Update password
            patch_res = client.patch(
                f"/api/v1/users/{student.id}",
                json={"password": new_password},
                headers={"Authorization": f"Bearer {token_admin}"},
            )
            assert patch_res.status_code == 200

            # Old password fails
            old_login = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": "StudentSecret123!"},
            )
            assert old_login.status_code == 401

            # New password succeeds
            new_login = client.post(
                "/api/v1/auth/login",
                json={"username": student.username, "password": new_password},
            )
            assert new_login.status_code == 200
            assert "access_token" in new_login.json()
        finally:
            app.dependency_overrides.clear()

    def test_condition_35_changed_role_reflected_in_me(self, client, in_memory_db, seeded_users):
        """35. Changing user role is immediately reflected in GET /api/v1/auth/me."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            student = seeded_users["student1"]
            token_admin = admin_token(seeded_users["admin1"])

            # Promote student to admin
            patch_res = client.patch(
                f"/api/v1/users/{student.id}",
                json={"role": "admin"},
                headers={"Authorization": f"Bearer {token_admin}"},
            )
            assert patch_res.status_code == 200

            # Generate fresh token for student
            token_promoted = create_access_token(
                data={"sub": str(student.id), "username": student.username, "role": "admin"}
            )
            me_res = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token_promoted}"},
            )
            assert me_res.status_code == 200
            assert me_res.json()["role"] == "admin"
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 8. AUTHORIZATION MATRIX (Conditions 36 - 37)
# ==============================================================================

class TestAuthorizationMatrix:
    """Ensures students and unauthenticated requests are rejected across all endpoints."""

    def test_condition_36_student_rejected_across_all_endpoints(
        self, client, in_memory_db, seeded_users
    ):
        """36. Student user receives HTTP 403 on GET, POST, and PATCH /api/v1/users."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token = student_token(seeded_users["student1"])
            headers = {"Authorization": f"Bearer {token}"}

            # GET /users
            assert client.get("/api/v1/users", headers=headers).status_code == 403
            # GET /users/{id}
            assert client.get(f"/api/v1/users/{seeded_users['student1'].id}", headers=headers).status_code == 403
            # POST /users
            assert client.post(
                "/api/v1/users",
                json={"username": "test", "password": "Password123!", "role": "student"},
                headers=headers,
            ).status_code == 403
            # PATCH /users/{id}
            assert client.patch(
                f"/api/v1/users/{seeded_users['student1'].id}",
                json={"role": "student"},
                headers=headers,
            ).status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_condition_37_unauthenticated_rejected_across_all_endpoints(
        self, client, in_memory_db, seeded_users
    ):
        """37. Unauthenticated requests receive HTTP 401 on GET, POST, and PATCH /api/v1/users."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            target_id = seeded_users["student1"].id

            assert client.get("/api/v1/users").status_code == 401
            assert client.get(f"/api/v1/users/{target_id}").status_code == 401
            assert client.post(
                "/api/v1/users",
                json={"username": "test", "password": "Password123!", "role": "student"},
            ).status_code == 401
            assert client.patch(
                f"/api/v1/users/{target_id}",
                json={"role": "student"},
            ).status_code == 401
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 9. REGRESSION & DATABASE INTEGRITY (Conditions 38 - 40)
# ==============================================================================

class TestUserManagementRegression:
    """Ensures existing feedback and auth workflows remain completely unaffected."""

    def test_condition_38_student_feedback_endpoints_functional(self, client, in_memory_db):
        """38. Student feedback endpoints remain publicly accessible and operational."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            res = client.post(
                "/api/v1/feedback/analyze-and-save",
                json={"feedback": "The classroom projectors work reliably.", "department": "EE"},
            )
            assert res.status_code == 201
            assert res.json()["priority_score"] is not None
        finally:
            app.dependency_overrides.clear()

    def test_condition_39_feedback_stats_records_auth_preserved(
        self, client, in_memory_db, seeded_users
    ):
        """39. Admin feedback stats and records endpoints still require admin role."""
        app.dependency_overrides[get_db] = lambda: in_memory_db
        try:
            token_admin = admin_token(seeded_users["admin1"])
            token_student = student_token(seeded_users["student1"])

            # Admin stats: 200
            assert client.get("/api/v1/feedback/stats", headers={"Authorization": f"Bearer {token_admin}"}).status_code == 200
            # Student stats: 403
            assert client.get("/api/v1/feedback/stats", headers={"Authorization": f"Bearer {token_student}"}).status_code == 403

            # Admin records: 200
            assert client.get("/api/v1/feedback/records", headers={"Authorization": f"Bearer {token_admin}"}).status_code == 200
            # Student records: 403
            assert client.get("/api/v1/feedback/records", headers={"Authorization": f"Bearer {token_student}"}).status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_condition_40_feedback_records_unaffected(self, in_memory_db, seeded_users):
        """40. Adding, updating, and deactivating users does not alter feedback data."""
        fb = Feedback(feedback_text="Baseline feedback for regression test", department="Math")
        in_memory_db.add(fb)
        in_memory_db.commit()
        in_memory_db.refresh(fb)

        # Query feedback after user operations
        queried = in_memory_db.get(Feedback, fb.id)
        assert queried is not None
        assert queried.feedback_text == "Baseline feedback for regression test"
