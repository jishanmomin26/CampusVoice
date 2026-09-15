"""Security and Cryptographic Utilities (Step 9.12).

Provides salted password hashing using bcrypt and signed JWT access-token
generation and verification using PyJWT.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt with automatic salting.

    Args:
        password: The plain-text password to hash.

    Returns:
        str: Salted bcrypt password hash encoded as UTF-8 string.

    Raises:
        ValueError: If password is empty, whitespace-only, or not a string.
    """
    if not password or not isinstance(password, str) or not password.strip():
        raise ValueError("Password cannot be empty or whitespace-only.")

    # bcrypt has a maximum password length of 72 bytes
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        raise ValueError("Password cannot exceed 72 bytes.")

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verifies a plain-text password against a stored bcrypt hash.

    Safely handles malformed hashes and exceptions without crashing.

    Args:
        plain_password: The candidate plain-text password.
        password_hash: The stored salted bcrypt hash.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    if not plain_password or not password_hash:
        return False
    if not isinstance(plain_password, str) or not isinstance(password_hash, str):
        return False

    try:
        pwd_bytes = plain_password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as exc:
        logger.warning("Password verification failed with exception: %s", type(exc).__name__)
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token containing minimal claims.

    Args:
        data: Payload claims to embed in the token (e.g. sub, username, role).
        expires_delta: Optional custom lifetime. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT string.
    """
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a signed JWT access token.

    Args:
        token: Raw JWT bearer token string.

    Returns:
        Dict[str, Any]: Verified token claims payload.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the signature or structure is invalid.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
