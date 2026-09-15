"""User Management Service Layer (Step 9.14.1).

Encapsulates database and business logic for listing, inspecting,
creating, updating, and deactivating users.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Dict[str, Any]:
    """Retrieves paginated, filtered user accounts from PostgreSQL.

    Executes filtering, counting, deterministic ordering, and pagination
    at the database level.

    Args:
        db: Active SQLAlchemy database session.
        page: Current page number (1-indexed, default: 1).
        page_size: Number of items per page (default: 20, max: 100).
        search: Optional case-insensitive substring search for username.
        role: Optional role filter ('admin' or 'student').
        is_active: Optional boolean filter for active status.

    Returns:
        Dict[str, Any]: Formatted data dictionary containing:
            - items: List of User instances for current page.
            - total: Total count of users matching active filters.
            - page: Current page number.
            - page_size: Items per page.
            - total_pages: Total number of pages.

    Raises:
        HTTPException: 422 if role filter is unrecognized.
    """
    conditions = []

    # 1. Search filter (case-insensitive substring on username)
    if search is not None:
        search_clean = search.strip()
        if search_clean:
            conditions.append(User.username.ilike(f"%{search_clean}%"))

    # 2. Role filter
    if role is not None:
        role_clean = role.strip()
        if role_clean:
            try:
                normalized_role = UserRole.normalize(role_clean)
                conditions.append(func.lower(User.role) == normalized_role.value)
            except ValueError:
                valid_roles = [r.value for r in UserRole]
                logger.warning("Invalid role filter requested: %s", role)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid role filter: '{role}'. Allowed roles: {', '.join(valid_roles)}.",
                )

    # 3. Active status filter
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    # 4. Count query
    count_stmt = select(func.count(User.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = db.scalar(count_stmt) or 0

    # 5. Total pages calculation
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # 6. Pagination and deterministic ordering (newest first, tie-break by ID desc)
    offset = (page - 1) * page_size
    query_stmt = select(User)
    if conditions:
        query_stmt = query_stmt.where(*conditions)

    query_stmt = (
        query_stmt.order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(page_size)
    )

    items: List[User] = list(db.scalars(query_stmt).all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieves a user by their unique primary key identifier.

    Args:
        db: Active SQLAlchemy database session.
        user_id: Unique integer user ID.

    Returns:
        Optional[User]: User ORM instance if found, None otherwise.
    """
    return db.scalar(select(User).where(User.id == user_id))


def create_user(
    db: Session,
    username: str,
    password: str,
    role: Optional[str] = None,
) -> User:
    """Creates a new user with salted bcrypt password hashing and uniqueness enforcement.

    Args:
        db: Active SQLAlchemy database session.
        username: Sanitized login username.
        password: Plain-text candidate password.
        role: Optional role string (defaults to 'student').

    Returns:
        User: Freshly created and persisted User ORM instance.

    Raises:
        HTTPException: 409 Conflict if username already exists.
        HTTPException: 422 if role is invalid.
    """
    clean_username = username.strip()

    # Check for existing username (case-insensitive)
    existing_user = db.scalar(
        select(User).where(func.lower(User.username) == clean_username.lower())
    )
    if existing_user:
        logger.warning("Attempted to create duplicate username: %s", clean_username)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{clean_username}' already exists.",
        )

    # Normalize role
    if role:
        try:
            role_val = UserRole.normalize(role).value
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role '{role}'. Allowed roles: {', '.join(valid_roles)}.",
            )
    else:
        role_val = UserRole.STUDENT.value

    # Hash password with bcrypt
    password_hash = hash_password(password)

    new_user = User(
        username=clean_username,
        password_hash=password_hash,
        role=role_val,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("Successfully created user ID %s (role: %s)", new_user.id, new_user.role)
    return new_user


def update_user(
    db: Session,
    target_user: User,
    current_admin: User,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> User:
    """Updates an existing user account with self-protection and last-admin safeguards.

    Args:
        db: Active SQLAlchemy database session.
        target_user: The User ORM record to be updated.
        current_admin: The currently authenticated administrator executing the request.
        role: Optional updated role ('admin' or 'student').
        is_active: Optional updated active status.
        password: Optional updated plain-text password.

    Returns:
        User: Refreshed User ORM instance reflecting the applied changes.

    Raises:
        HTTPException: 400 Bad Request if administrator attempts to deactivate own account.
        HTTPException: 409 Conflict if operation would deactivate or demote the last active admin.
        HTTPException: 422 if role is invalid.
    """
    # 1. Self-deactivation protection
    if current_admin.id == target_user.id and is_active is False:
        logger.warning(
            "Admin ID %s attempted to deactivate their own account.", current_admin.id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account.",
        )

    # 2. Last active admin safeguard
    target_is_active_admin = (
        target_user.role.lower() == UserRole.ADMIN.value and target_user.is_active is True
    )
    will_deactivate = (is_active is False)
    will_demote = (
        role is not None and role.strip().lower() != UserRole.ADMIN.value
    )

    if target_is_active_admin and (will_deactivate or will_demote):
        active_admin_count = (
            db.scalar(
                select(func.count(User.id)).where(
                    func.lower(User.role) == UserRole.ADMIN.value,
                    User.is_active.is_(True),
                )
            )
            or 0
        )
        if active_admin_count <= 1:
            logger.warning(
                "Rejected operation on user ID %s: cannot deactivate or demote last active admin.",
                target_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operation rejected: Cannot deactivate or demote the last active administrator account.",
            )

    # 3. Apply role update if provided
    if role is not None:
        try:
            target_user.role = UserRole.normalize(role).value
        except ValueError:
            valid_roles = [r.value for r in UserRole]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role '{role}'. Allowed roles: {', '.join(valid_roles)}.",
            )

    # 4. Apply is_active update if provided
    if is_active is not None:
        target_user.is_active = is_active

    # 5. Apply password update if provided (re-hashed)
    if password is not None:
        target_user.password_hash = hash_password(password)

    db.commit()
    db.refresh(target_user)
    logger.info("Successfully updated user ID %s", target_user.id)
    return target_user
