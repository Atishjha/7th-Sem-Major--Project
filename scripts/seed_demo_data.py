"""
Seed the three demo accounts, plus a batch of baseline synthetic
events, required by the project spec.

DEMO CREDENTIALS — NOT FOR PRODUCTION.
Passwords below are intentionally simple (this is an academic demo,
not a real deployment) but are still hashed before storage — the
database never contains plaintext passwords.

Usage:
    python scripts/seed_demo_data.py

Safe to re-run: existing users are left untouched, and events are
only seeded once (skipped if the table is already non-empty).

Alerts and incidents will be added here once those tables exist
(Phases 5/7 and 9) — for now this seeds users and baseline event
noise, which is everything Phases 2–4 need.
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
# Host layout: <project>/backend/app ; in-container layout: /app/app (scripts are mounted at /app/scripts).
for _candidate in (_ROOT / "backend", _ROOT):
    if (_candidate / "app" / "__init__.py").exists():
        sys.path.append(str(_candidate))
        break

from app.database.session import SessionLocal  # noqa: E402
from app.models.common import Severity  # noqa: E402
from app.models.event import Event  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.security.hashing import hash_password  # noqa: E402
from app.utils.ids import next_event_id  # noqa: E402

DEMO_ACCOUNTS = [
    {"username": "admin", "password": "admin123", "role": UserRole.ADMIN},
    {"username": "analyst", "password": "analyst123", "role": UserRole.SOC_ANALYST},
    {"username": "viewer", "password": "viewer123", "role": UserRole.VIEWER},
]

# Same synthetic pools used by the live scenario generator, so
# baseline noise and live-demo events look like they belong to the
# same fictional environment.
USERS = ["demo_user", "demo_admin", "j.doe.demo", "a.patel.demo"]
HOSTS = ["WIN-CLIENT-01", "WIN-CLIENT-02", "WIN-SRV-DB01", "WIN-SRV-WEB01"]
INTERNAL_IPS = ["192.168.56.10", "192.168.56.11", "192.168.56.20", "10.10.0.15"]
DOC_DEST_IPS = ["198.51.100.23", "198.51.100.77", "198.51.100.201"]

BASELINE_EVENT_COUNT = 600
BASELINE_WINDOW_HOURS = 24


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


def _random_baseline_event(timestamp: datetime) -> Event:
    """A quiet, mostly-boring event — this is normal background noise,
    not an attack. Occasional 'failed' logins are realistic mistyped
    passwords, not brute force (too sparse/spread out to trigger the
    Phase 5 brute-force rule)."""
    kind = random.choices(
        ["login_success", "login_failed", "dns_query", "network_connection", "process"],
        weights=[35, 5, 25, 25, 10],
    )[0]
    user = random.choice(USERS)
    host = random.choice(HOSTS)
    ip = random.choice(INTERNAL_IPS)

    if kind == "login_success":
        return Event(
            timestamp=timestamp, source="authentication", source_ip=ip,
            username=user, hostname=host, event_type="login", action="login",
            status="success", severity=Severity.LOW,
            message="Authentication succeeded", event_metadata={},
        )
    if kind == "login_failed":
        return Event(
            timestamp=timestamp, source="authentication", source_ip=ip,
            username=user, hostname=host, event_type="login", action="login",
            status="failed", severity=Severity.LOW,
            message="Failed authentication attempt (isolated)", event_metadata={},
        )
    if kind == "dns_query":
        return Event(
            timestamp=timestamp, source="dns", source_ip=ip, hostname=host,
            event_type="dns_query", action="query", status="n/a",
            severity=Severity.LOW, message="DNS query observed",
            event_metadata={"domain": "internal-service.example-test.invalid"},
        )
    if kind == "network_connection":
        return Event(
            timestamp=timestamp, source="network", source_ip=ip,
            destination_ip=random.choice(DOC_DEST_IPS), hostname=host,
            event_type="network_connection", action="connect", status="n/a",
            severity=Severity.LOW, message="Normal outbound connection",
            event_metadata={},
        )
    return Event(
        timestamp=timestamp, source="endpoint", source_ip=ip, username=user,
        hostname=host, event_type="process_execution", action="start",
        status="n/a", severity=Severity.LOW, message="Process started: notepad.exe",
        event_metadata={"process": "notepad.exe"},
    )


def seed_events() -> None:
    db = SessionLocal()
    try:
        existing_count = db.query(Event).count()
        if existing_count > 0:
            print(f"  - events table already has {existing_count} rows, skipping")
            return

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=BASELINE_WINDOW_HOURS)

        for _ in range(BASELINE_EVENT_COUNT):
            offset_seconds = random.uniform(0, BASELINE_WINDOW_HOURS * 3600)
            ts = window_start + timedelta(seconds=offset_seconds)
            event = _random_baseline_event(ts)
            event_id_num, event_id_str = next_event_id(db)
            event.id = event_id_num
            event.event_id = event_id_str
            db.add(event)

        db.commit()

        print(f"  - created {BASELINE_EVENT_COUNT} baseline synthetic events "
              f"spread over the last {BASELINE_WINDOW_HOURS}h")
    finally:
        db.close()


if __name__ == "__main__":
    print("DEMO CREDENTIALS — NOT FOR PRODUCTION")
    print("Seeding demo user accounts...")
    seed_users()
    print("Seeding baseline synthetic events...")
    seed_events()
    print("Done.")
