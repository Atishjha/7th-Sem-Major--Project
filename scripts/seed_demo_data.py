"""
Seed the three demo accounts required by the project spec.

DEMO CREDENTIALS — NOT FOR PRODUCTION.
Passwords below are intentionally simple (this is an academic demo,
not a real deployment) but are still hashed before storage — the
database never contains plaintext passwords.

Usage:
    python scripts/seed_demo_data.py

Safe to re-run: existing users are left untouched.

This script will grow in later phases to also seed synthetic events,
alerts, and incidents (Phase 25 in the project spec) — for now it
only seeds users, since that's all Phase 2 requires.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))
from app.database.session import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.security.hashing import hash_password  # noqa: E402
DEMO_ACCOUNTS = [
    {"username": "admin", "password": "admin123", "role": UserRole.ADMIN},
    {"username": "analyst", "password": "analyst123", "role": UserRole.SOC_ANALYST},
    {"username": "viewer", "password": "viewer123", "role": UserRole.VIEWER},
]
def seed_users() -> None:
    db = SessionLocal()
    try:
        for account in DEMO_ACCOUNTS:
            existing = (
                db.query(User).filter(User.username == account["username"]).first()
            )
            if existing:
                print(f"  - {account['username']} already exists, skipping")
                continue

            user = User(
                username=account["username"],
                hashed_password=hash_password(account["password"]),
                role=account["role"],
                is_active=True,
            )
            db.add(user)
            print(f"  - created {account['username']} ({account['role'].value})")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("DEMO CREDENTIALS — NOT FOR PRODUCTION")
    print("Seeding demo user accounts...")
    seed_users()
    print("Done.")
