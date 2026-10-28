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


# ================================================ real-model robustness (Phase 17)
import logging  # noqa: E402

from app.ai.llm_provider import (  # noqa: E402
    apply_grounding_guard, configuration_problem, extract_json, normalize_report,
)

SECRET = "gsk_super-secret-key-123"


def _reply(content) -> httpx.Response:
    text = content if isinstance(content, str) else _json.dumps(content)
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def _llm_report(ctx, **overrides):
    """A valid model reply built from the mock analyst, with optional overrides."""
    base = run(MockAIProvider().investigate(ctx)).model_dump(mode="json", exclude={"generated_by", "generated_at"})
    base.update(overrides)
    return base


def _run_llm(db, monkeypatch, scenario, handler):
    _llm_settings(monkeypatch)
    _install_stub(monkeypatch, handler)
    incident, ctx = _context(db, scenario)
    result, used = run(run_investigation(ctx))
    return incident, ctx, result, used


# -------------------------------------------------------------- configuration
def test_groq_has_a_default_model_but_other_providers_must_name_one(monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL", None)
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    assert configuration_problem() is None
    assert LLMProvider().model == "llama-3.3-70b-versatile"

    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    assert "AI_MODEL is required" in configuration_problem()
    with pytest.raises(RuntimeError, match="AI_MODEL is required"):
        LLMProvider()


def test_a_groq_model_name_is_never_sent_to_another_provider(db, monkeypatch):
    """Old behaviour: any provider without AI_MODEL got a Groq model id and failed with a 400."""
    monkeypatch.setattr(settings, "AI_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "AI_API_KEY", "k")
    monkeypatch.setattr(settings, "AI_MODEL", None)
    calls = []
    _install_stub(monkeypatch, lambda r: calls.append(r) or httpx.Response(200, json={}))
    _incident, ctx = _context(db, "powershell")
    _result, used = run(run_investigation(ctx))
    assert calls == [] and used == "mock (llm_failed: RuntimeError)"


# ------------------------------------------------------------- tolerant parsing
@pytest.mark.parametrize(
    "wrap",
    [
        lambda s: s,                                              # plain JSON
        lambda s: f"```json\n{s}\n```",                           # code fence
        lambda s: f"Here is the report:\n{s}\nHope this helps!",  # chatter around it
        lambda s: f"```\n{s}\n```",                               # fence without a language
        lambda s: f"I'll answer using the {{schema}} you gave:\n```json\n{s}\n```\nLet me know if {{anything}} is unclear.",  # braces in the prose
    ],
    ids=["plain", "json_fence", "prose_around", "bare_fence", "braces_in_prose"],
)
def test_json_is_found_however_the_model_wraps_it(db, monkeypatch, wrap):
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "dns_anomaly")
    body = wrap(_json.dumps(_llm_report(ctx)))
    _install_stub(monkeypatch, lambda r: _reply(body))
    _result, used = run(run_investigation(ctx))
    assert used == "llm:groq:test-model"


def test_sloppy_field_types_are_repaired_not_rejected(db, monkeypatch):
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "dns_anomaly")
    sloppy = _llm_report(
        ctx,
        observed_evidence="a single string instead of a list",
        inference=None,
        recommended_containment=["fine", None, 42, "  "],
        questions_for_analyst={"unexpected": "shape"},
        some_extra_field="ignored",
    )
    _install_stub(monkeypatch, lambda r: _reply(sloppy))
    result, used = run(run_investigation(ctx))
    assert used == "llm:groq:test-model"
    assert result.observed_evidence == ["a single string instead of a list"]
    assert result.inference == []
    assert result.recommended_containment == ["fine", "42"]
    assert isinstance(result.questions_for_analyst, list)


@pytest.mark.parametrize("missing", ["executive_summary", "what_happened"])
def test_a_reply_without_a_summary_falls_back(db, monkeypatch, missing):
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "dns_anomaly")
    bad = _llm_report(ctx)
    bad[missing] = ""
    _install_stub(monkeypatch, lambda r: _reply(bad))
    _result, used = run(run_investigation(ctx))
    assert used == "mock (llm_failed: ValueError)"


def test_extract_json_rejects_non_objects():
    with pytest.raises(ValueError):
        extract_json("[1, 2, 3]")
    with pytest.raises(ValueError, match="no JSON object"):
        extract_json("I'm sorry, I can't help with that.")


# --------------------------------------------------------- the grounding guard
def test_the_model_cannot_change_the_mitre_mapping(db, monkeypatch):
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "brute_force")
    lying = _llm_report(ctx, mitre_mapping=[{
        "tactic": "Impact", "technique_id": "T1486", "technique_name": "Data Encrypted for Impact",
        "confidence": "high", "evidence_rule": "brute_force"}])
    _install_stub(monkeypatch, lambda r: _reply(lying))
    result, used = run(run_investigation(ctx))
    assert used == "llm:groq:test-model"
    assert {t.technique_id for t in result.mitre_mapping} == {"T1110", "T1078"}      # from the project's own mapping


def test_invented_ips_and_techniques_are_removed_and_the_report_says_so(db, monkeypatch):
    _llm_settings(monkeypatch)
    incident, ctx = _context(db, "brute_force")
    real_ip = incident.primary_source_ip
    fake = _llm_report(
        ctx,
        executive_summary=f"Attack from {real_ip}, relayed via 8.8.8.8 using T1486 ransomware.",
        observed_evidence=[f"Failed logins from {real_ip}", "Beacon to 45.33.32.156 observed", "Technique T1110 matched"],
        indicators=[real_ip, "198.18.0.99"],
        inference=["Probably automated (no invented values here)"],
    )
    _install_stub(monkeypatch, lambda r: _reply(fake))
    result, used = run(run_investigation(ctx))
    assert used == "llm:groq:test-model"

    everything = " ".join([result.executive_summary, *result.observed_evidence, *result.indicators, *result.inference])
    for invented in ("8.8.8.8", "45.33.32.156", "198.18.0.99", "T1486"):
        assert invented not in everything, invented
    assert real_ip in result.executive_summary and f"Failed logins from {real_ip}" in result.observed_evidence
    assert "Technique T1110 matched" in result.observed_evidence          # T1110 IS in the incident data
    assert result.indicators == [real_ip]
    assert "[unverified]" in result.executive_summary
    note = next(n for n in result.unknown_information if n.startswith("Grounding check"))
    for invented in ("8.8.8.8", "45.33.32.156", "198.18.0.99", "T1486"):
        assert invented in note                                           # named, so the analyst can see what was caught


def test_a_clean_report_is_left_untouched_by_the_guard(db):
    incident, ctx = _context(db, "brute_force")
    clean = _llm_report(ctx, observed_evidence=[f"Failed logins from {incident.primary_source_ip}"])
    before = _json.dumps(clean, sort_keys=True)
    normalized = normalize_report(clean, ctx)
    guarded = apply_grounding_guard(normalized, ctx)
    assert not any(n.startswith("Grounding check") for n in guarded["unknown_information"])
    assert guarded["observed_evidence"] == clean["observed_evidence"]
    assert before == _json.dumps(clean, sort_keys=True)


# ------------------------------------------------------------ rate limits / retry
def test_one_rate_limit_is_retried_after_the_advertised_wait(db, monkeypatch):
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.ai.llm_provider._sleep", fake_sleep)
    _llm_settings(monkeypatch)
    _incident, ctx = _context(db, "dns_anomaly")
    good = _llm_report(ctx)
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(429, headers={"retry-after": "3"}) if len(attempts) == 1 else _reply(good)

    _install_stub(monkeypatch, handler)
    _result, used = run(run_investigation(ctx))
    assert used == "llm:groq:test-model" and len(attempts) == 2 and waits == [3.0]


def test_retry_wait_is_capped_and_a_second_429_falls_back(db, monkeypatch):
    waits = []

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("app.ai.llm_provider._sleep", fake_sleep)
    _llm_settings(monkeypatch)
    _install_stub(monkeypatch, lambda r: httpx.Response(429, headers={"retry-after": "600"}))
    _incident, ctx = _context(db, "dns_anomaly")
    _result, used = run(run_investigation(ctx))
    assert waits == [5.0]                                    # never stalls a demo for 10 minutes
    assert used == "mock (llm_failed: HTTPStatusError)"


# ------------------------------------------------------------- key safety
def test_the_api_key_never_leaks_into_labels_reports_or_logs(db, monkeypatch, caplog):
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", SECRET)
    monkeypatch.setattr(settings, "AI_MODEL", "m")
    _install_stub(monkeypatch, lambda r: httpx.Response(401, text=f"Invalid API key: {SECRET}"))
    _incident, ctx = _context(db, "dns_anomaly")
    with caplog.at_level(logging.WARNING, logger="ai"):
        result, used = run(run_investigation(ctx))
    assert used == "mock (llm_failed: HTTPStatusError)"
    assert SECRET not in used and SECRET not in result.model_dump_json()
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "401" in logged and "Invalid API key" in logged       # the reason IS logged for diagnosis ...
    assert SECRET not in logged and "***" in logged               # ... with the key masked


# ----------------------------------------------------------- status endpoint
def test_status_reports_mock_by_default(client, headers):
    body = client.get("/api/ai/status", headers=headers["viewer"]).json()
    assert body == {"mode": "mock", "provider": "mock", "model": None, "key_configured": False, "label": "mock",
                    "note": "Offline analyst. Set AI_PROVIDER and AI_API_KEY to use a real model."}


def test_status_reports_live_without_ever_returning_the_key(client, headers, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "groq")
    monkeypatch.setattr(settings, "AI_API_KEY", SECRET)
    monkeypatch.setattr(settings, "AI_MODEL", None)
    r = client.get("/api/ai/status", headers=headers["viewer"])
    body = r.json()
    assert body["mode"] == "live" and body["key_configured"] is True
    assert body["model"] == "llama-3.3-70b-versatile" and body["label"] == "llm:groq:llama-3.3-70b-versatile"
    assert SECRET not in r.text


@pytest.mark.parametrize(
    "provider,key,model,base,expect_in_note",
    [
        ("groq", None, None, None, "AI_API_KEY is empty"),
        ("openrouter", "k", None, None, "AI_MODEL is required"),
        ("openai_compatible", "k", "m", None, "No base URL"),
        ("gemini", "k", "m", None, "No base URL"),
    ],
)
def test_status_explains_a_half_configured_setup(client, headers, monkeypatch, provider, key, model, base, expect_in_note):
    monkeypatch.setattr(settings, "AI_PROVIDER", provider)
    monkeypatch.setattr(settings, "AI_API_KEY", key)
    monkeypatch.setattr(settings, "AI_MODEL", model)
    monkeypatch.setattr(settings, "AI_BASE_URL", base)
    body = client.get("/api/ai/status", headers=headers["viewer"]).json()
    assert body["mode"] == "mock" and body["label"] == "mock"
    assert expect_in_note in body["note"]


def test_status_requires_sign_in(client):
    assert client.get("/api/ai/status").status_code == 401
