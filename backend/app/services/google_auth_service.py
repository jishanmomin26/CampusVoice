"""Google Authentication and OpenID Connect Service (Step 9.19.1).

Handles cryptographic Google ID-token verification against Google's public
certificates and safe provisioning/mapping of CampusVoice student user accounts.
"""

import logging
import secrets
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)

# Canonical Google OpenID Connect token issuers
VALID_GOOGLE_ISSUERS = frozenset({
    "accounts.google.com",
    "https://accounts.google.com",
})


def verify_google_id_token(
    credential: str,
    expected_audience: Optional[str] = None,
    request_adapter: Optional[Any] = None,
) -> Dict[str, Any]:
    """Cryptographically verifies a Google ID token using Google public certificates.

    Validates:
    - Signature validity via Google certificates
    - Token expiration (exp)
    - Token issuer (iss in accounts.google.com / https://accounts.google.com)
    - Audience (aud matches configured GOOGLE_CLIENT_ID)
    - Presence of essential identity claims ('sub', 'email', 'email_verified')
    - Email verification status (email_verified must be True)

    Args:
        credential: Raw Google ID token string.
        expected_audience: Optional audience override; defaults to settings.GOOGLE_CLIENT_ID.
        request_adapter: Optional HTTP transport adapter for fetching Google public keys.

    Returns:
        Dict[str, Any]: Sanitized verified claims containing:
            - sub: Google stable subject identifier
            - email: Verified lowercase email address
            - name: Optional display name
            - picture: Optional avatar URL

    Raises:
        HTTPException(401): If token verification fails for any reason.
        HTTPException(500): If GOOGLE_CLIENT_ID is not configured on the server.
    """
    if not credential or not isinstance(credential, str) or not credential.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google authentication credential.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clean_credential = credential.strip()

    audience = expected_audience if expected_audience is not None else settings.GOOGLE_CLIENT_ID
    if not audience:
        logger.error("Google authentication attempted but GOOGLE_CLIENT_ID is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication service is not configured.",
        )

    transport = request_adapter if request_adapter is not None else google_requests.Request()

    try:
        # Cryptographically verify token signature, expiration, and audience
        id_info = google_id_token.verify_oauth2_token(
            clean_credential,
            transport,
            audience=audience,
        )

        # Verify token issuer
        issuer = id_info.get("iss")
        if issuer not in VALID_GOOGLE_ISSUERS:
            logger.warning("Rejected Google token with invalid issuer: %s", issuer)
            raise ValueError(f"Invalid token issuer: {issuer}")

        # Verify required claims
        sub = id_info.get("sub")
        if not sub or not isinstance(sub, str) or not sub.strip():
            raise ValueError("Missing 'sub' claim in Google token.")

        email = id_info.get("email")
        if not email or not isinstance(email, str) or not email.strip():
            raise ValueError("Missing 'email' claim in Google token.")

        # Require verified email
        email_verified = id_info.get("email_verified")
        if email_verified is not True:
            logger.warning("Rejected Google token with unverified email.")
            raise ValueError("Google email address is not verified.")

        return {
            "sub": sub.strip(),
            "email": email.strip().lower(),
            "name": id_info.get("name"),
            "picture": id_info.get("picture"),
        }

    except HTTPException:
        raise
    except Exception as exc:
        # Never log credential values or expose stack traces in responses
        logger.warning("Google ID token verification failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google authentication credential.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_or_provision_google_user(
    db: Session,
    google_claims: Dict[str, Any],
) -> User:
    """Authenticates existing user or safely provisions a new student account.

    Resolution Policy:
    1. If a user with google_sub == claims["sub"] exists:
       - Validate active status (HTTP 401 if inactive).
       - Return user.
    2. If no user has google_sub, search by verified email:
       - If user exists with role 'admin': reject with HTTP 401 to prevent
         privilege escalation / account takeover via OAuth.
       - If user exists with role 'student':
         - Validate active status (HTTP 401 if inactive).
         - Link user.google_sub = claims["sub"].
         - Return user.
    3. If no matching user exists:
       - Provision brand new student user.
       - Generate cryptographically random password using secrets module.
       - Hash immediately with bcrypt (hash_password()) and store only the hash.
       - Plaintext password is never logged, stored, or returned.
       - Role is strictly forced to 'student' (UserRole.STUDENT.value).
       - Set is_active = True.
       - Return newly created user.

    Args:
        db: Active SQLAlchemy database session.
        google_claims: Sanitized claims dictionary from verified Google ID token.

    Returns:
        User: Authenticated or newly provisioned User ORM instance.

    Raises:
        HTTPException(401): If account is inactive or account linking is disallowed.
    """
    sub = google_claims["sub"]
    email = google_claims["email"]

    # 1. Check for existing user by Google sub identifier
    user_by_sub = db.scalar(select(User).where(User.google_sub == sub))
    if user_by_sub:
        if not user_by_sub.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_by_sub

    # 2. Check for existing user by verified email (case-insensitive username match)
    user_by_email = db.scalar(
        select(User).where(func.lower(User.username) == email.lower())
    )
    if user_by_email:
        # Prevent privilege takeover of administrator accounts via OAuth
        if user_by_email.role.lower() == UserRole.ADMIN.value:
            logger.warning(
                "Rejected Google Sign-In linking attempt for administrative account ID %s.",
                user_by_email.id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user_by_email.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Safely link Google identity to existing student account
        user_by_email.google_sub = sub
        db.commit()
        db.refresh(user_by_email)
        logger.info(
            "Successfully linked Google identity to student user ID %s.",
            user_by_email.id,
        )
        return user_by_email

    # 3. Provision brand new student user
    base_username = email[:100]

    # Handle rare collision with another non-matching account
    existing_collision = db.scalar(
        select(User).where(func.lower(User.username) == base_username.lower())
    )
    if existing_collision:
        suffix = f"_{secrets.token_hex(4)}"
        base_username = f"{base_username[:100 - len(suffix)]}{suffix}"

    # Generate cryptographically secure random password and hash with bcrypt
    temp_random_pwd = secrets.token_urlsafe(32)
    secure_hash = hash_password(temp_random_pwd)
    del temp_random_pwd  # Clean up plaintext variable from local memory immediately

    new_user = User(
        username=base_username,
        password_hash=secure_hash,
        role=UserRole.STUDENT.value,  # Strictly student role
        is_active=True,
        google_sub=sub,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(
        "Provisioned new Google student user ID %s (username: %s).",
        new_user.id,
        new_user.username,
    )
    return new_user
