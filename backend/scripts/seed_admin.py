"""Local Development Admin User Seeding Script (Step 9.12).

Creates an initial administrator account for local development and testing.
Credentials MUST be provided via environment variables:
- ADMIN_USERNAME (defaults to 'admin')
- ADMIN_PASSWORD (required)

Usage:
    $env:ADMIN_USERNAME="admin"
    $env:ADMIN_PASSWORD="MySecureLocalPassword123"
    python scripts/seed_admin.py

NOTE: For local development and testing only. Passwords are never logged
or stored in plaintext.
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import select

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def seed_admin() -> bool:
    """Creates a development administrator account if one does not already exist."""
    username = os.getenv("ADMIN_USERNAME", settings.ADMIN_USERNAME or "admin").strip()
    password = os.getenv("ADMIN_PASSWORD", settings.ADMIN_PASSWORD)

    if not password or not password.strip():
        print(
            "ERROR: ADMIN_PASSWORD environment variable is required to seed an admin account.\n"
            "Please set ADMIN_PASSWORD before running this script.\n"
            "Example: $env:ADMIN_PASSWORD=\"YourDevelopmentPassword123\"; python scripts/seed_admin.py"
        )
        return False

    clean_password = password.strip()
    if len(clean_password) < 8:
        print("ERROR: ADMIN_PASSWORD must be at least 8 characters long.")
        return False

    if len(clean_password.encode("utf-8")) > 72:
        print("ERROR: ADMIN_PASSWORD cannot exceed 72 bytes.")
        return False


    db = SessionLocal()
    try:
        # Check if an admin with this username already exists
        existing_user = db.scalar(
            select(User).where(User.username.ilike(username))
        )
        if existing_user:
            print(f"INFO: User '{username}' already exists (Role: {existing_user.role}). No changes made.")
            return True

        # Hash password and create admin user
        pwd_hash = hash_password(password.strip())
        admin_user = User(
            username=username,
            password_hash=pwd_hash,
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"SUCCESS: Admin user '{username}' created successfully (ID: {admin_user.id}).")
        return True
    except Exception as exc:
        db.rollback()
        print(f"ERROR: Failed to seed admin user: {type(exc).__name__}: {exc}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_admin()
    sys.exit(0 if success else 1)
