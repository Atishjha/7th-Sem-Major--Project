"""Authentication: login, token handling, and the ways a token can be wrong."""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import settings
from app.models.user import User, UserRole
from app.security.hashing import hash_password, verify_password
from app.security.jwt import create_access_token, decode_access_token


def _login(client, username, password):
    return client.post("/api/auth/login", json={"username": username, "password": password})


# ------------------------------------------------------------------- login
@pytest.mark.parametrize(
    "username,password,role",
    [("admin", "admin123", "ADMIN"), ("analyst", "analyst123", "SOC_ANALYST"), ("viewer", "viewer123", "VIEWER")],
)
def test_login_success_returns_token_and_role(client, users, username, password, role):
    r = _login(client, username, password)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == role
    assert body["access_token"]


def test_login_wrong_password_and_unknown_user_look_identical(client, users):
    """Same status and message either way, so the API can't be used to
    discover which usernames exist."""
    wrong_pw = _login(client, "admin", "not-the-password")
    unknown = _login(client, "nobody", "whatever")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_login_rejects_deactivated_user(client, users, db):
    user = db.query(User).filter(User.username == "viewer").one()
    user.is_active = False
    db.commit()
    assert _login(client, "viewer", "viewer123").status_code == 401


def test_login_requires_both_fields(client, users):
    assert client.post("/api/auth/login", json={"username": "admin"}).status_code == 422


# ------------------------------------------------------------------ /me
def test_me_returns_profile_without_password_hash(client, users, headers):
    r = client.get("/api/auth/me", headers=headers["analyst"])
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "analyst"
    assert body["role"] == "SOC_ANALYST"
    assert "hashed_password" not in body and "password" not in body


# ----------------------------------------------------------- bad tokens
def test_missing_token_is_401(client, users):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


@pytest.mark.parametrize("token", ["garbage", "a.b.c", "", "Bearer"])
def test_malformed_token_is_401(client, users, token):
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_signed_with_wrong_secret_is_401(client, users):
    forged = jwt.encode(
        {"sub": "admin", "role": "ADMIN", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "attacker-guessed-secret", algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_expired_token_is_401(client, users):
    expired = jwt.encode(
        {"sub": "admin", "role": "ADMIN", "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_unsigned_alg_none_token_is_rejected(client, users):
    """Classic JWT attack: claim `alg: none` and send no signature."""
    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    token = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': 'admin', 'role': 'ADMIN'})}."
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_without_subject_is_401(client, users):
    token = jwt.encode(
        {"role": "ADMIN", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_deleted_or_deactivated_user_stops_working(client, users, headers, db):
    assert client.get("/api/auth/me", headers=headers["viewer"]).status_code == 200
    db.query(User).filter(User.username == "viewer").one().is_active = False
    db.commit()
    assert client.get("/api/auth/me", headers=headers["viewer"]).status_code == 401

    db.query(User).filter(User.username == "analyst").delete()
    db.commit()
    assert client.get("/api/auth/me", headers=headers["analyst"]).status_code == 401


@pytest.mark.security
def test_role_claim_inside_token_cannot_escalate_privileges(client, users):
    """A viewer holding a validly-signed token that *claims* role ADMIN must
    still be treated as a viewer: authorization reads the role from the DB."""
    token = create_access_token(username="viewer", role="ADMIN")
    r = client.post(
        "/api/rules", json={"rule_key": "brute_force", "enabled": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


# ----------------------------------------------------- hashing / tokens
def test_passwords_are_stored_hashed(db, users):
    for username, (password, _role) in {"admin": ("admin123", None), "viewer": ("viewer123", None)}.items():
        stored = db.query(User).filter(User.username == username).one().hashed_password
        assert stored != password
        assert stored.startswith("$2")          # bcrypt
        assert verify_password(password, stored)
        assert not verify_password(password + "x", stored)


def test_hashing_is_salted():
    assert hash_password("same") != hash_password("same")


def test_token_payload_and_expiry():
    token = create_access_token(username="admin", role="ADMIN")
    payload = decode_access_token(token)
    assert payload["sub"] == "admin" and payload["role"] == "ADMIN"
    remaining = datetime.fromtimestamp(payload["exp"], tz=timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES - 1) < remaining <= timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )


def test_decode_returns_none_for_garbage():
    assert decode_access_token("not-a-token") is None
