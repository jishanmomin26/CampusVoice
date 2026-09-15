"""User Management API Endpoints (Step 9.14.1).

Provides admin-only endpoints to list, inspect, create, update, and deactivate users.
All endpoints require administrative privileges via `Depends(require_admin)`.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.users import (
    UserCreateRequest,
    UserDetailResponse,
    UserListResponse,
    UserUpdateRequest,
)
from app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Users",
    description=(
        "Retrieves a paginated list of user accounts with optional search by username, "
        "role filtering, and active status filtering. Requires administrative privileges."
    ),
)
def list_users_endpoint(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max: 100)"),
    search: Optional[str] = Query(default=None, description="Case-insensitive keyword search for username"),
    role: Optional[str] = Query(default=None, description="Role filter ('admin' or 'student')"),
    is_active: Optional[bool] = Query(default=None, description="Account active status filter"),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """List users with pagination, search, and filtering."""
    try:
        users_data = user_service.list_users(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            is_active=is_active,
        )
        return UserListResponse.model_validate(users_data)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while listing users: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while listing users: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Detail",
    description="Retrieves details for an individual user by ID. Requires administrative privileges.",
)
def get_user_detail_endpoint(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Retrieve user details by ID."""
    try:
        user = user_service.get_user_by_id(db=db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found.",
            )
        return UserDetailResponse.model_validate(user)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while retrieving user %s: %s",
            user_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while retrieving user %s: %s",
            user_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )


@router.post(
    "",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description=(
        "Creates a new user account with salted bcrypt password hashing and "
        "case-insensitive username uniqueness enforcement. Requires administrative privileges."
    ),
)
def create_user_endpoint(
    payload: UserCreateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Create a new user account."""
    try:
        new_user = user_service.create_user(
            db=db,
            username=payload.username,
            password=payload.password,
            role=payload.role,
        )
        return UserDetailResponse.model_validate(new_user)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error while creating user: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while creating user: %s",
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )


@router.patch(
    "/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update User",
    description=(
        "Updates user account attributes (role, active status, or password). "
        "Enforces self-protection (admins cannot deactivate their own account) and "
        "last-active-admin safeguards. Requires administrative privileges."
    ),
)
def update_user_endpoint(
    user_id: int,
    payload: UserUpdateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Update an existing user account."""
    try:
        target_user = user_service.get_user_by_id(db=db, user_id=user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found.",
            )

        updated_user = user_service.update_user(
            db=db,
            target_user=target_user,
            current_admin=current_admin,
            role=payload.role,
            is_active=payload.is_active,
            password=payload.password,
        )
        return UserDetailResponse.model_validate(updated_user)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Database error while updating user %s: %s",
            user_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user due to an internal database error.",
        )
    except Exception as exc:
        logger.error(
            "Unexpected error while updating user %s: %s",
            user_id,
            type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request.",
        )
