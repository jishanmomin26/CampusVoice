"""Security and Cryptographic Utilities (Step 9.12 & Step 9.17 Hardening).

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

# Pre-computed valid bcrypt hash used for constant-time comparison when a username does not exist.
# Prevents response latency differences from leaking whether a username exists.
DUMMY_BCRYPT_HASH = "$2b$12$e8kPqY81c62zUOBi1iF7s.b8jV7J1mC/y4p8aW12kL8fQ3Kq6fKqO"

# Sensitive keys that must NEVER be included in JWT payloads
SENSITIVE_CLAIM_KEYS = frozenset({
    "password",
    "password_hash",
    "hashed_password",
    "secret",
    "feedback_text",
    "feedback",
})


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt with automatic salting.

    Enforces a minimum password length of 8 characters and a maximum
    of 72 bytes (bcrypt input limit).

    Args:
        password: The plain-text candidate password to hash.

    Returns:
        str: Salted bcrypt password hash encoded as UTF-8 string.

    Raises:
        ValueError: If password is empty, whitespace-only, less than 8
                    characters, or exceeds 72 bytes.
    """
    if not password or not isinstance(password, str) or not password.strip():
        raise ValueError("Password cannot be empty or whitespace-only.")

    stripped = password.strip()
    if len(stripped) < 8:
        raise ValueError("Password must be at least 8 characters long.")

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
        logger.warning("Password verification failed safely: %s", type(exc).__name__)
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token containing minimal claims.

    Strips any sensitive data fields (e.g. password hashes or feedback texts)
    to guarantee payload privacy. Requires a valid subject identifier ('sub').

    Args:
        data: Payload claims to embed in the token (e.g. sub, username, role).
        expires_delta: Optional custom lifetime. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT string.

    Raises:
        ValueError: If 'sub' claim is missing, empty, or if invalid data is provided.
    """
    if not data or not isinstance(data, dict):
        raise ValueError("Token payload data must be a non-empty dictionary.")

    sub = data.get("sub")
    if sub is None or (isinstance(sub, str) and not sub.strip()):
        raise ValueError("Token payload must contain a non-empty 'sub' claim.")

    # Filter out sensitive keys from JWT claims
    to_encode = {k: v for k, v in data.items() if k.lower() not in SENSITIVE_CLAIM_KEYS}

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "sub": str(sub),
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a signed JWT access token.

    Strictly validates the expected signing algorithm and requires
    essential claims ('sub', 'iat', 'exp').

    Args:
        token: Raw JWT bearer token string.

    Returns:
        Dict[str, Any]: Verified token claims payload.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the signature, algorithm, or required claims are invalid.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={
            "require": ["exp", "iat", "sub"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
        },
    )

