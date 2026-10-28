"""
Check the real-AI connection.

Sends one realistic (synthetic) incident to the AI provider configured in your
.env, using exactly the code the app uses, and tells you plainly whether it
worked and, if not, why.

    python scripts/check_ai.py

Run it from the project root (so .env is found) with the virtual environment
active, or inside Docker:   docker compose exec backend python scripts/check_ai.py

Exit codes: 0 = a live model answered and its reply was usable
            1 = the provider was reached but the call failed (details printed)
            2 = nothing to check yet: AI_PROVIDER is mock, or the settings are incomplete
It never prints your API key.
"""

import asyncio
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
# Host layout: <project>/backend/app ; in-container layout: /app/app (scripts are mounted at /app/scripts).
for _candidate in (_ROOT / "backend", _ROOT):
    if (_candidate / "app" / "__init__.py").exists():
        sys.path.append(str(_candidate))
        break

from app.ai import llm_provider  # noqa: E402
from app.config import settings  # noqa: E402

# Documentation-range addresses only (RFC 5737 / RFC 1918); nothing real.
SYNTHETIC_CONTEXT = {
    "incident": {
        "incident_id": "INC-CHECK", "title": "Possible Account Compromise (demo_user)",
        "incident_type": "account_compromise", "severity": "high", "status": "open", "risk_score": 62.0,
        "primary_username": "demo_user", "primary_source_ip": "203.0.113.50", "primary_hostname": "WIN-CLIENT-01",
        "alert_count": 2, "risk_breakdown": [
            {"factor": "severity", "points": 25, "max_points": 30},
            {"factor": "correlated_alerts", "points": 8, "max_points": 20},
        ],
    },
    "alerts": [
        {"alert_id": "ALT-1", "rule_key": "brute_force", "severity": "high", "source_ip": "203.0.113.50",
         "username": "demo_user", "title": "5 failed logins in 5 minutes"},
        {"alert_id": "ALT-2", "rule_key": "impossible_travel", "severity": "high", "source_ip": "203.0.113.50",
         "username": "demo_user", "title": "Login location changed within 10 minutes"},
    ],
    "events": [
        {"event_id": "EVT-1", "event_type": "login", "status": "failed", "source_ip": "203.0.113.50", "username": "demo_user"},
        {"event_id": "EVT-2", "event_type": "login", "status": "success", "source_ip": "203.0.113.50", "username": "demo_user"},
    ],
    "mitre_mapping": [
        {"tactic": "Credential Access", "technique_id": "T1110", "technique_name": "Brute Force",
         "confidence": "high", "evidence_rule": "brute_force"},
        {"tactic": "Initial Access", "technique_id": "T1078", "technique_name": "Valid Accounts",
         "confidence": "high", "evidence_rule": "impossible_travel"},
    ],
    "indicators": ["203.0.113.50", "demo_user", "WIN-CLIENT-01"],
}

HINTS = {
    400: "The provider rejected the request. The model may not support JSON mode, or the name is wrong. Try another model.",
    401: "The API key was rejected. Check AI_API_KEY (no quotes or spaces) and that the key is still active.",
    403: "The key is valid but not allowed to use this model or endpoint.",
    404: "Not found. The model name is not known to this provider, or AI_BASE_URL is wrong.",
    429: "Rate limited (free tiers are strict). Wait a minute and retry, or use a smaller model.",
}


def _mask(text: str) -> str:
    key = settings.AI_API_KEY
    return text.replace(key, "***") if key else text


def main() -> int:
    key_state = "set" if settings.AI_API_KEY else "NOT set"
    print(f"AI_PROVIDER = {settings.AI_PROVIDER}   AI_API_KEY = {key_state}   AI_MODEL = {settings.AI_MODEL or '(provider default)'}")

    if settings.AI_PROVIDER == "mock":
        print("\nNothing to check: AI_PROVIDER is 'mock' (the offline analyst).")
        print("To use a real model set AI_PROVIDER=groq, AI_API_KEY=<your key> in .env, then restart.")
        return 2
    if not settings.AI_API_KEY:
        print(f"\nAI_PROVIDER is {settings.AI_PROVIDER} but AI_API_KEY is empty, so the app would use the offline analyst.")
        return 2
    problem = llm_provider.configuration_problem()
    if problem:
        print(f"\nConfiguration problem: {problem}")
        return 2

    provider = llm_provider.LLMProvider()
    print(f"Calling {provider.base_url}  model={provider.model} ...")
    try:
        report = asyncio.run(provider.investigate(SYNTHETIC_CONTEXT))
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        print(f"\nFAILED: HTTP {status}")
        print("  Provider said:", _mask(exc.response.text[:300]).strip() or "(empty body)")
        print("  Hint:", HINTS.get(status, "Server-side error; try again shortly." if status >= 500 else "See the provider's message above."))
        return 1
    except httpx.TransportError as exc:
        print(f"\nFAILED: could not reach the provider ({type(exc).__name__}).")
        print("  Hint: check your internet connection, any proxy/VPN, and AI_BASE_URL.")
        return 1
    except (ValueError, KeyError, TypeError) as exc:
        print(f"\nFAILED: the provider answered, but the reply was not a usable report ({type(exc).__name__}: {_mask(str(exc))}).")
        print("  Hint: try a larger or instruction-tuned model; small models often ignore the JSON format.")
        return 1

    print("\nOK: a live model answered and its reply was usable.")
    print(f"  generated_by : {report.generated_by}")
    print(f"  summary      : {report.executive_summary[:200]}")
    print(f"  sections     : {len(report.observed_evidence)} evidence, {len(report.inference)} inference, "
          f"{len(report.recommended_containment)} containment, {len(report.mitre_mapping)} MITRE")
    guard = [n for n in report.unknown_information if n.startswith("Grounding check")]
    print("  grounding    : " + (guard[0] if guard else "clean (no invented IPs or technique ids)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
