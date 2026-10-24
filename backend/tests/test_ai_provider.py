"""AI SOC analyst (Phase 10): mock provider, provider selection, and the mandatory fallback."""

import asyncio

import pytest

from app.ai.context_builder import build_context
from app.ai.factory import run_investigation
from app.ai.llm_provider import LLMProvider
from app.ai.mock_provider import MockAIProvider
from app.config import settings
from app.models.alert import Alert
from app.schemas.ai_investigation import InvestigationOut
from helpers import replay_scenario

SCENARIO_FOR_TYPE = {
    "brute_force": "account_compromise", "powershell": "endpoint_compromise", "dns_anomaly": "dns_anomaly",
    "network_anomaly": "network_anomaly", "multi_stage": "account_compromise",
}


def _context(db, scenario):
    _alerts, (incident,) = replay_scenario(db, scenario)
    db.refresh(incident)
    alerts = db.query(Alert).filter(Alert.incident_id == incident.id).order_by(Alert.detected_at).all()
    return incident, build_context(db, incident, alerts)


def run(coro):
    return asyncio.run(coro)


# -------------------------------------------------------------------- context
def test_context_contains_incident_alerts_events_risk_and_mitre(db):
    incident, ctx = _context(db, "multi_stage")
    assert ctx["incident"]["incident_id"] == incident.incident_id
    assert len(ctx["alerts"]) == 4
    assert len(ctx["events"]) >= 8
    assert len(ctx["incident"]["risk_breakdown"]) == 5
    assert {t["technique_id"] for t in ctx["mitre_mapping"]} == {"T1110", "T1078", "T1059.001", "T1041"}
    assert incident.primary_source_ip in ctx["indicators"]


# --------------------------------------------------------------- mock provider
@pytest.mark.parametrize("scenario", list(SCENARIO_FOR_TYPE))
def test_mock_provider_produces_a_valid_complete_investigation(db, scenario):
    incident, ctx = _context(db, scenario)
    result = run(MockAIProvider().investigate(ctx))
    assert isinstance(result, InvestigationOut)
    assert incident.incident_type == SCENARIO_FOR_TYPE[scenario]
    for text_field in ("executive_summary", "what_happened", "timeline_summary", "risk_explanation"):
        assert getattr(result, text_field).strip()
    for list_field in ("observed_evidence", "inference", "recommended_investigation",
                       "recommended_containment", "recommended_remediation"):
        assert getattr(result, list_field), list_field
    assert result.generated_by == "mock" or result.generated_by.startswith("mock")


@pytest.mark.parametrize("scenario", list(SCENARIO_FOR_TYPE))
def test_mock_evidence_is_built_from_real_incident_values(db, scenario):
    """Anti-hallucination check: the evidence cites the actual IP / host / user."""
    incident, ctx = _context(db, scenario)
    result = run(MockAIProvider().investigate(ctx))
    evidence = " ".join(result.observed_evidence + [result.executive_summary, result.what_happened])
    assert any(v and v in evidence for v in (
        incident.primary_source_ip, incident.primary_hostname, incident.primary_username)), evidence
    assert "{" not in evidence and "None" not in " ".join(result.observed_evidence[:1])   # no template leakage
    assert str(round(incident.risk_score)) in result.executive_summary or incident.risk_score is None


def test_mock_provider_is_deterministic(db):
    _incident, ctx = _context(db, "multi_stage")
    a = run(MockAIProvider().investigate(ctx)).model_dump(exclude={"generated_at"})
    b = run(MockAIProvider().investigate(ctx)).model_dump(exclude={"generated_at"})
    assert a == b


def test_mock_mitre_section_matches_the_shared_mapping(db):
    _incident, ctx = _context(db, "brute_force")
    result = run(MockAIProvider().investigate(ctx))
    assert {t.technique_id for t in result.mitre_mapping} == {"T1110", "T1078"}


# ------------------------------------------------------ provider selection
def test_default_configuration_uses_the_mock_provider(db):
    _incident, ctx = _context(db, "powershell")
    result, used = run(run_investigation(ctx))
    assert used.startswith("mock") and "llm_failed" not in used
    assert isinstance(result, InvestigationOut)


def test_real_provider_without_a_key_still_uses_mock(db, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", None)
    _incident, ctx = _context(db, "powershell")
    _result, used = run(run_investigation(ctx))
    assert used.startswith("mock") and "llm_failed" not in used


@pytest.mark.parametrize("failure", [RuntimeError("boom"), ConnectionError("net down"), ValueError("bad json")])
def test_llm_failure_falls_back_to_mock_and_says_so(db, monkeypatch, failure):
    """Spec: if the external LLM is unavailable the system must still return a
    structured investigation — and the provider label must not hide the fallback."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", "fake-key")

    async def broken(self, context):
        raise failure

    monkeypatch.setattr(LLMProvider, "investigate", broken)
    _incident, ctx = _context(db, "dns_anomaly")
    result, used = run(run_investigation(ctx))
    assert isinstance(result, InvestigationOut)
    assert used == f"mock (llm_failed: {type(failure).__name__})"


def test_llm_provider_requires_a_base_url(monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai_compatible")
    monkeypatch.setattr(settings, "AI_BASE_URL", None)
    with pytest.raises(RuntimeError, match="No base URL"):
        LLMProvider()


# --------------------------------------------- real provider, against a stub server
import json as _json

import httpx


def _install_stub(monkeypatch, handler):
    """Route LLMProvider's HTTP calls to `handler` instead of the network."""
    real = httpx.AsyncClient

    class Stubbed(real):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    monkeypatch.setattr("app.ai.llm_provider.httpx.AsyncClient", Stubbed)


def _llm_settings(monkeypatch, provider="groq"):
    monkeypatch.setattr(settings, "AI_PROVIDER", provider)
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AI_MODEL", "test-model")


def _good_completion(ctx):
    mock = run(MockAIProvider().investigate(ctx)).model_dump(mode="json", exclude={"generated_by", "generated_at"})
    return {"choices": [{"message": {"content": _json.dumps(mock)}}]}


def test_llm_provider_sends_a_correct_request_and_parses_the_reply(db, monkeypatch):
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "dns_anomaly")
    completion = _good_completion(ctx)          # built up front: can't asyncio.run() inside the stub's running loop
    seen = {}

    def handler(request: httpx.Request):
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], _json.loads(request.content)
        return httpx.Response(200, json=completion)

    _install_stub(monkeypatch, handler)
    result, used = run(run_investigation(ctx))
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert _json.loads(seen["body"]["messages"][1]["content"])["incident"]["incident_id"] == ctx["incident"]["incident_id"]
    assert used == "llm:groq:test-model" == result.generated_by


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500, text="upstream down"),                                         # server error
        lambda r: httpx.Response(401, json={"error": "bad key"}),                                    # auth failure
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "not json at all"}}]}),   # prose, not JSON
        lambda r: httpx.Response(200, json={"choices": [{"message": {"content": "{\"executive_summary\": \"x\"}"}}]}),  # wrong shape
        lambda r: httpx.Response(200, json={"unexpected": True}),                                    # missing choices
    ],
    ids=["http_500", "http_401", "non_json_reply", "wrong_schema", "missing_choices"],
)
def test_every_kind_of_bad_llm_response_falls_back_to_a_valid_mock_investigation(db, monkeypatch, handler):
    _llm_settings(monkeypatch)
    _install_stub(monkeypatch, handler)
    _incident, ctx = _context(db, "powershell")
    result, used = run(run_investigation(ctx))
    assert isinstance(result, InvestigationOut) and result.observed_evidence
    assert used.startswith("mock (llm_failed: ")


def test_timeouts_fall_back_too(db, monkeypatch):
    _llm_settings(monkeypatch)

    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    _install_stub(monkeypatch, handler)
    _incident, ctx = _context(db, "powershell")
    _result, used = run(run_investigation(ctx))
    assert used == "mock (llm_failed: ConnectTimeout)"
