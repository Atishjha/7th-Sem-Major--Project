"""
Role-based access control, checked as a matrix over every route.

  * No token                       -> 401 on every protected route
  * Read routes                    -> every role (ADMIN, SOC_ANALYST, VIEWER)
  * State-changing routes          -> ADMIN and SOC_ANALYST only; VIEWER gets 403

For the "allowed" side we send an intentionally invalid or unknown payload and
assert the status is *neither 401 nor 403*: that proves the role check passed
without having to build valid data for every endpoint. (FastAPI resolves the
auth dependency before it validates the body, so a viewer is stopped with 403
even when the body is empty.)
"""

import pytest

pytestmark = pytest.mark.security

READ_ROUTES = [
    "/api/dashboard", "/api/events", "/api/alerts", "/api/detections", "/api/rules",
    "/api/incidents", "/api/incidents/INC-9999", "/api/incidents/INC-9999/mitre",
    "/api/incidents/INC-9999/investigation", "/api/incidents/INC-9999/response",
    "/api/assets", "/api/mitre/techniques", "/api/audit", "/api/response",
    "/api/ml/status", "/api/ml/predictions", "/api/dataset/files", "/api/dataset/runs",
    "/api/simulator/status", "/api/auth/me", "/api/ai/status",
]

# (method, path, json body) — bodies are deliberately invalid/unknown
WRITE_ROUTES = [
    ("POST", "/api/rules", {}),
    ("POST", "/api/simulator/start", {}),
    ("POST", "/api/simulator/stop", None),
    ("POST", "/api/ml/train", {"contamination": "not-a-number"}),
    ("POST", "/api/dataset/preprocess", {}),
    ("POST", "/api/dataset/train", {}),
    ("POST", "/api/incidents/INC-9999/investigate", None),
    ("POST", "/api/response/RESP-999999/approve", None),
    ("POST", "/api/response/RESP-999999/reject", None),
]


def _call(client, method, path, headers=None, body=None):
    kwargs = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return client.request(method, path, **kwargs)


def test_health_is_public(client):
    assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("path", READ_ROUTES)
def test_read_routes_require_authentication(client, users, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("method,path,body", WRITE_ROUTES)
def test_write_routes_require_authentication(client, users, method, path, body):
    assert _call(client, method, path, body=body).status_code == 401


def test_upload_requires_authentication(client, users):
    assert client.post("/api/dataset/upload", files={"file": ("a.csv", b"x\n1\n")}).status_code == 401


@pytest.mark.parametrize("role", ["admin", "analyst", "viewer"])
@pytest.mark.parametrize("path", READ_ROUTES)
def test_every_role_may_read(client, headers, role, path):
    status = client.get(path, headers=headers[role]).status_code
    assert status not in (401, 403), f"{role} was refused on GET {path}"


@pytest.mark.parametrize("method,path,body", WRITE_ROUTES)
def test_viewer_is_forbidden_from_every_write_route(client, headers, method, path, body):
    r = _call(client, method, path, headers["viewer"], body)
    assert r.status_code == 403
    assert "not permitted" in r.json()["detail"]


def test_viewer_is_forbidden_from_upload(client, headers):
    r = client.post("/api/dataset/upload", files={"file": ("a.csv", b"x\n1\n")}, headers=headers["viewer"])
    assert r.status_code == 403


@pytest.mark.parametrize("role", ["admin", "analyst"])
@pytest.mark.parametrize("method,path,body", WRITE_ROUTES)
def test_admin_and_analyst_pass_the_role_check_on_write_routes(client, headers, role, method, path, body):
    r = _call(client, method, path, headers[role], body)
    assert r.status_code not in (401, 403), f"{role} refused on {method} {path}: {r.text}"


@pytest.mark.parametrize("role", ["admin", "analyst"])
def test_admin_and_analyst_pass_the_role_check_on_upload(client, headers, ml_sandbox, role):
    r = client.post("/api/dataset/upload", files={"file": ("ok.csv", b"a,b\n1,2\n")}, headers=headers[role])
    assert r.status_code == 201


def test_forbidden_request_changes_nothing(client, headers, db):
    """A rejected viewer request must leave the rule untouched."""
    from app.models.detection_rule import DetectionRule

    before = db.query(DetectionRule).filter_by(rule_key="brute_force").one().enabled
    client.post("/api/rules", json={"rule_key": "brute_force", "enabled": not before}, headers=headers["viewer"])
    db.expire_all()
    assert db.query(DetectionRule).filter_by(rule_key="brute_force").one().enabled == before
