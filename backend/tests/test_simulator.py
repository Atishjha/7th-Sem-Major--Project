"""Event simulator (Phase 4): scenario data, the synthetic-only guarantee, runner control, WebSocket."""

import ipaddress

import pytest

from app.models.common import Severity
from app.services.event_scenarios import SCENARIOS
from app.services.event_simulator import simulator_runner
from app.services.ws_manager import manager

REQUIRED_FIELDS = {"source", "event_type", "action", "status", "severity", "message"}
# RFC 5737 documentation ranges + RFC 1918 private space: can never be a real internet host.
SAFE_NETWORKS = [ipaddress.ip_network(n) for n in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


@pytest.fixture(autouse=True)
def _reset_runner():
    yield
    simulator_runner._reset()


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_scenario_plan_is_well_formed(key):
    plan = SCENARIOS[key]()
    assert plan
    for delay, fields in plan:
        assert delay >= 0
        assert REQUIRED_FIELDS <= set(fields)
        assert isinstance(fields["severity"], Severity)
        assert fields["status"] in {"success", "failed", "n/a"}


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_scenarios_only_ever_use_non_routable_synthetic_ips(key):
    """The project promise: no real indicator ever appears in demo data."""
    for _delay, fields in SCENARIOS[key]():
        for field in ("source_ip", "destination_ip"):
            value = fields.get(field)
            if value:
                ip = ipaddress.ip_address(value)
                assert any(ip in net for net in SAFE_NETWORKS), f"{key}: {field}={value} is not a safe synthetic address"


@pytest.mark.parametrize("key", list(SCENARIOS))
def test_scenario_domains_and_commands_are_inert(key):
    for _delay, fields in SCENARIOS[key]():
        meta = fields.get("metadata") or {}
        if meta.get("domain"):
            assert meta["domain"].endswith(".invalid")                 # RFC 2606: can never resolve
        if meta.get("command_line"):
            assert "<SYNTHETIC_PLACEHOLDER>" in meta["command_line"]    # never a working command


def test_scenario_registry_matches_the_api_enum():
    from app.schemas.event import ScenarioName

    assert set(SCENARIOS) == {s.value for s in ScenarioName}


# ----------------------------------------------------------------- runner API
def test_start_status_stop_cycle(client, headers):
    h = headers["analyst"]
    assert client.get("/api/simulator/status", headers=h).json()["running"] is False

    r = client.post("/api/simulator/start", headers=h, json={"scenario": "dns_anomaly"})
    assert r.status_code == 200
    assert r.json()["running"] is True and r.json()["scenario"] == "dns_anomaly"

    r = client.post("/api/simulator/stop", headers=h)
    assert r.status_code == 200 and r.json()["running"] is False and r.json()["scenario"] is None


def test_only_one_scenario_runs_at_a_time(client, headers):
    h = headers["admin"]
    assert client.post("/api/simulator/start", headers=h, json={"scenario": "dns_anomaly"}).status_code == 200
    r = client.post("/api/simulator/start", headers=h, json={"scenario": "brute_force"})
    assert r.status_code == 409 and "already running" in r.json()["detail"]
    client.post("/api/simulator/stop", headers=h)


def test_unknown_scenario_is_rejected(client, headers):
    assert client.post("/api/simulator/start", headers=headers["analyst"], json={"scenario": "ransomware"}).status_code == 422
    assert simulator_runner.running is False


def test_stopping_when_idle_is_harmless(client, headers):
    assert client.post("/api/simulator/stop", headers=headers["analyst"]).json()["running"] is False


# ------------------------------------------------------------------ WebSocket
def test_websocket_connects_and_receives_broadcasts(client):
    """The /ws/events stream is intentionally unauthenticated (documented in app/api/ws.py
    as a demo simplification; it only carries synthetic telemetry)."""
    import asyncio

    with client.websocket_connect("/ws/events") as ws:
        client.portal.call(manager.broadcast, {"type": "status", "data": {"running": False}})
        assert ws.receive_json() == {"type": "status", "data": {"running": False}}
    assert asyncio.run(asyncio.sleep(0)) is None


def test_manager_drops_dead_connections_silently():
    import asyncio

    class Dead:
        async def send_text(self, _):
            raise RuntimeError("closed")

    mgr = type(manager)()
    mgr._connections.append(Dead())
    asyncio.run(mgr.broadcast({"x": 1}))
    assert mgr._connections == []


# ---------------------------------------------- the real runner, start to finish
def test_runner_streams_a_whole_scenario_into_db_and_websocket(client, headers, db, monkeypatch):
    """Drive SimulatorRunner._run itself (not a re-implementation of it): persist each
    event, detect, correlate, score, and broadcast over the WebSocket, in order.
    The real scenario is used, with the live-feel delays shrunk to 1 ms."""
    import time

    from app.models.alert import Alert
    from app.models.event import Event
    from app.models.incident import Incident

    plan = [(0.001, fields) for _delay, fields in SCENARIOS["brute_force"]()]
    monkeypatch.setitem(SCENARIOS, "brute_force", lambda: plan)

    with client.websocket_connect("/ws/events") as ws:
        r = client.post("/api/simulator/start", headers=headers["analyst"], json={"scenario": "brute_force"})
        assert r.status_code == 200

        messages, finished = [], False
        for _ in range(500):                                  # hard bound: never hang the suite
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "status" and msg["data"]["running"] is False and any(m["type"] == "event" for m in messages):
                finished = True
                break
        assert finished, "runner never reported completion"

    kinds = [m["type"] for m in messages]
    assert kinds.count("event") == len(plan)
    assert kinds.count("alert") == 2
    assert kinds.index("event") < kinds.index("alert") < kinds.index("incident")      # causal order
    # An incident message goes out when the incident is created and again when the 2nd alert
    # joins it: two messages, one incident, the latest carrying the full picture.
    incident_msgs = [m["data"] for m in messages if m["type"] == "incident"]
    assert len({m["incident_id"] for m in incident_msgs}) == 1
    assert [m["alert_count"] for m in incident_msgs] == [1, 2]
    assert incident_msgs[-1]["incident_type"] == "account_compromise" and incident_msgs[-1]["risk_score"] > 0

    db.expire_all()
    assert db.query(Event).count() == len(plan)
    assert db.query(Alert).count() == 2 and db.query(Incident).count() == 1
    status = client.get("/api/simulator/status", headers=headers["viewer"]).json()
    assert status["running"] is False and status["events_emitted"] == 0           # reset after completion
