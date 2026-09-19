"""Authentication API Endpoints (Step 9.12)."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import DUMMY_BCRYPT_HASH, create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponse,
    GoogleLoginRequest,
    LoginRequest,
    TokenResponse,
)
from app.services.google_auth_service import (
    authenticate_or_provision_google_user,
    verify_google_id_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates credentials and returns a signed JWT bearer access token.",
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials and issue access token."""
    # Lookup user by case-insensitive username match
    user = db.scalar(
        select(User).where(func.lower(User.username) == login_data.username.lower())
    )

    # Mitigate username enumeration timing attacks:
    # When user is not found, execute a dummy verify_password against DUMMY_BCRYPT_HASH
    # so response time is indistinguishable from existing accounts.
    if not user:
        verify_password(login_data.password, DUMMY_BCRYPT_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Inactive users receive the exact same generic authentication failure
    # to avoid disclosing sensitive account-state information.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )


    # Issue JWT access token with user claims
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
    )


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google Sign-In Authentication",
    description="Verifies a Google ID token and issues a CampusVoice JWT bearer access token.",
)
def google_login(
    login_data: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with verified Google ID token and issue JWT access token."""
    # 1. Cryptographically verify Google ID token and extract verified identity claims
    google_claims = verify_google_id_token(login_data.credential)

    # 2. Find existing account or provision student user
    user = authenticate_or_provision_google_user(db, google_claims)

    # 3. Issue standard CampusVoice JWT access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile and role of the currently authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Retrieve authenticated user details without exposing sensitive hashes."""
    return CurrentUserResponse.model_validate(current_user)
