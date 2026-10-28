"""scripts/check_ai.py: the connection check you run on your own machine."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from app.config import settings

ROOT = Path(__file__).resolve().parents[2]


def _script():
    spec = importlib.util.spec_from_file_location("check_ai", ROOT / "scripts" / "check_ai.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub(monkeypatch, handler):
    real = httpx.AsyncClient

    class Stubbed(real):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr("app.ai.llm_provider.httpx.AsyncClient", Stubbed)


def _live(monkeypatch, key="gsk_check-secret"):
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", key)
    monkeypatch.setattr(settings, "AI_MODEL", "test-model")


def _good_reply():
    """What a well-behaved model returns for the synthetic incident."""
    return {
        "executive_summary": "Repeated failed logins from 203.0.113.50 were followed by a success for demo_user.",
        "what_happened": "A brute-force pattern preceded a successful login from the same address.",
        "timeline_summary": "Failed logins, then a successful login, then a location change.",
        "observed_evidence": ["Failed login for demo_user from 203.0.113.50", "Successful login for demo_user from 203.0.113.50"],
        "inference": ["The account may have been guessed."],
        "affected_assets": ["WIN-CLIENT-01"], "indicators": ["203.0.113.50"],
        "mitre_mapping": [], "risk_explanation": "Two high-severity alerts on one account.",
        "recommended_investigation": ["Review the account's recent sign-ins."],
        "recommended_containment": ["Reset the credentials for demo_user."], "recommended_remediation": ["Enforce MFA."],
        "unknown_information": ["Whether the login was the real user."], "questions_for_analyst": ["Is travel expected?"],
    }


def test_the_synthetic_incident_uses_only_non_routable_addresses():
    import ipaddress

    ips = [ip for a in _script().SYNTHETIC_CONTEXT["alerts"] for ip in [a["source_ip"]]]
    assert all(ipaddress.ip_address(ip).is_private or ip.startswith("203.0.113.") for ip in ips)


def test_mock_mode_says_there_is_nothing_to_check(capsys):
    assert _script().main() == 2
    assert "Nothing to check" in capsys.readouterr().out


def test_missing_key_is_reported(monkeypatch, capsys):
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    assert _script().main() == 2
    assert "AI_API_KEY is empty" in capsys.readouterr().out


def test_a_working_model_is_reported_ok(monkeypatch, capsys):
    _live(monkeypatch)
    reply = _good_reply()
    _stub(monkeypatch, lambda r: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}}]}))
    assert _script().main() == 0
    out = capsys.readouterr().out
    assert "OK: a live model answered" in out and "llm:groq:test-model" in out and "clean" in out


def test_the_check_shows_when_the_grounding_guard_caught_something(monkeypatch, capsys):
    _live(monkeypatch)
    reply = _good_reply()
    reply["observed_evidence"].append("Beacon to 45.33.32.156")
    _stub(monkeypatch, lambda r: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reply)}}]}))
    assert _script().main() == 0
    assert "45.33.32.156" in capsys.readouterr().out.split("grounding")[1]


@pytest.mark.parametrize(
    "status,hint",
    [(401, "key was rejected"), (404, "model name is not known"), (400, "JSON mode"), (429, "Rate limited")],
)
def test_http_failures_get_a_plain_language_hint(monkeypatch, capsys, status, hint):
    async def no_wait(_):
        return None

    monkeypatch.setattr("app.ai.llm_provider._sleep", no_wait)
    _live(monkeypatch)
    _stub(monkeypatch, lambda r: httpx.Response(status, text="provider error"))
    assert _script().main() == 1
    out = capsys.readouterr().out
    assert f"HTTP {status}" in out and hint in out


def test_the_key_is_never_printed_even_if_the_provider_echoes_it(monkeypatch, capsys):
    _live(monkeypatch, key="gsk_check-secret")
    _stub(monkeypatch, lambda r: httpx.Response(401, text="Invalid key gsk_check-secret"))
    _script().main()
    out = capsys.readouterr().out
    assert "gsk_check-secret" not in out and "***" in out


def test_network_failure_is_reported_as_unreachable(monkeypatch, capsys):
    _live(monkeypatch)

    def down(request):
        raise httpx.ConnectError("no route")

    _stub(monkeypatch, down)
    assert _script().main() == 1
    assert "could not reach the provider" in capsys.readouterr().out


def test_a_reply_that_is_not_a_report_is_reported_as_unusable(monkeypatch, capsys):
    _live(monkeypatch)
    _stub(monkeypatch, lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "sorry, no"}}]}))
    assert _script().main() == 1
    assert "not a usable report" in capsys.readouterr().out
