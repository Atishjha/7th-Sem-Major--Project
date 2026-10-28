"""
Real AI provider: calls an OpenAI-compatible /chat/completions endpoint
(Groq, OpenRouter, OpenAI itself, and most self-hosted gateways share this
request/response shape). Chosen by factory.py when AI_PROVIDER != "mock" and
AI_API_KEY is set.

Real models are less tidy than a mock, so this module does three jobs beyond
"send a request":

  1. Tolerant parsing. Models sometimes wrap JSON in ```fences```, add prose
     around it, return a string where a list was asked for, or return null.
     All of that is normalised. A reply with no usable summary is still rejected
     (and the caller falls back to the offline analyst).
  2. A grounding guard. The prompt tells the model never to invent facts, but a
     prompt is a request, not a guarantee. After the reply arrives, any IP
     address or MITRE technique id that does NOT appear in the incident data is
     removed (lists) or masked (prose), and the report says so in
     `unknown_information`. The MITRE table is never taken from the model at all:
     it comes from the project's own rule-to-technique mapping.
  3. One polite retry on HTTP 429 (rate limit), which free tiers hit easily.

Honesty note: verified against a stub server (request shape, auth header, JSON
mode, parsing, grounding, retry, fallback); not exercised against a live model
in the build environment. `scripts/check_ai.py` runs this same code against the
real endpoint on your machine.
"""

import asyncio
import json
import re
from datetime import datetime, timezone

import httpx

from app.ai.base import AIProvider
from app.config import settings
from app.schemas.ai_investigation import InvestigationOut, MitreTechniqueOut

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai_compatible": None,  # supply AI_BASE_URL
}

# Only providers whose model catalogue we know get a default. Sending a Groq
# model name to OpenRouter (or anything else) would just fail, so other
# providers must set AI_MODEL. Catalogues change: check the provider's models page.
PROVIDER_DEFAULT_MODELS = {"groq": "llama-3.3-70b-versatile"}

MAX_RETRY_WAIT_SECONDS = 5.0
_sleep = asyncio.sleep  # indirection so tests don't really wait

SYSTEM_PROMPT = """You are a SOC analyst assistant. You will be given a JSON \
object describing a correlated security incident (its alerts, linked \
events, risk breakdown, and MITRE mapping). Respond with ONLY a JSON \
object matching this exact schema, no prose outside the JSON:

{
  "executive_summary": str, "what_happened": str, "timeline_summary": str,
  "observed_evidence": [str], "inference": [str],
  "affected_assets": [str], "indicators": [str],
  "mitre_mapping": [{"tactic": str, "technique_id": str, "technique_name": str, "confidence": str, "evidence_rule": str}],
  "risk_explanation": str,
  "recommended_investigation": [str], "recommended_containment": [str], "recommended_remediation": [str],
  "unknown_information": [str], "questions_for_analyst": [str]
}

Rules: "observed_evidence" must only contain facts literally present in the \
input — never invent an IP, username, or count. "inference" is your \
interpretation, clearly separate from observed_evidence. Never state \
something as certain if the data doesn't support it; use "unknown_information" \
for genuine gaps instead of guessing."""

LIST_FIELDS = [
    "observed_evidence", "inference", "affected_assets", "indicators",
    "recommended_investigation", "recommended_containment", "recommended_remediation",
    "unknown_information", "questions_for_analyst",
]
TEXT_FIELDS = ["executive_summary", "what_happened", "timeline_summary", "risk_explanation"]
REQUIRED_TEXT = ("executive_summary", "what_happened")
MITRE_KEYS = ("tactic", "technique_id", "technique_name", "confidence", "evidence_rule")

IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
TECHNIQUE_ID = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")


# ----------------------------------------------------------------- configuration
def configuration_problem() -> str | None:
    """What is wrong with the AI settings, or None if a live call can be attempted.
    Pure: no network. Used by the provider and by the status endpoint."""
    base = PROVIDER_BASE_URLS.get(settings.AI_PROVIDER) or settings.AI_BASE_URL
    if not base:
        return (
            f"No base URL for AI_PROVIDER={settings.AI_PROVIDER}. "
            "Set AI_BASE_URL for openai_compatible, or use groq/openrouter."
        )
    if not (settings.AI_MODEL or PROVIDER_DEFAULT_MODELS.get(settings.AI_PROVIDER)):
        return f"AI_MODEL is required for AI_PROVIDER={settings.AI_PROVIDER}."
    return None


def resolve_model() -> str:
    return settings.AI_MODEL or PROVIDER_DEFAULT_MODELS[settings.AI_PROVIDER]


# ------------------------------------------------------------------- parsing
def extract_json(text: str) -> dict:
    """Find the JSON object in a model reply, tolerating fences and surrounding prose."""
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate = fenced.group(1).strip()
        else:
            start, end = candidate.find("{"), candidate.rfind("}")
            if start == -1 or end <= start:
                raise ValueError("model reply contains no JSON object")
            candidate = candidate[start : end + 1]
        parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("model reply is JSON but not an object")
    return parsed


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v).strip() for v in value if v is not None)
    return str(value)


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [s for s in (str(v).strip() for v in value if v is not None) if s]
    return [str(value)]


def normalize_report(raw: dict, context: dict) -> dict:
    """Coerce a model's reply into the report shape. Raises ValueError if it has no usable summary."""
    for field in REQUIRED_TEXT:
        if not _as_text(raw.get(field)).strip():
            raise ValueError(f"model reply is missing '{field}'")
    report = {f: _as_text(raw.get(f)) for f in TEXT_FIELDS}
    report.update({f: _as_list(raw.get(f)) for f in LIST_FIELDS})
    # Authoritative: the project's own rule -> technique mapping, never the model's.
    report["mitre_mapping"] = [
        MitreTechniqueOut(**{k: t[k] for k in MITRE_KEYS}).model_dump() for t in context.get("mitre_mapping", [])
    ]
    return report


# ------------------------------------------------------------- grounding guard
def apply_grounding_guard(report: dict, context: dict) -> dict:
    """Remove or mask IPs / technique ids the incident data does not contain."""
    haystack = json.dumps(context, default=str)
    known_ips, known_techniques = set(IPV4.findall(haystack)), set(TECHNIQUE_ID.findall(haystack))

    def unverified(text: str) -> list[str]:
        return [m for m in IPV4.findall(text) if m not in known_ips] + [
            m for m in TECHNIQUE_ID.findall(text) if m not in known_techniques
        ]

    flagged: set[str] = set()
    dropped = masked = 0
    for field in LIST_FIELDS:
        kept = []
        for item in report[field]:
            bad = unverified(item)
            if bad:
                flagged.update(bad)
                dropped += 1
            else:
                kept.append(item)
        report[field] = kept
    for field in TEXT_FIELDS:
        text = report[field]
        for token in set(unverified(text)):
            text = text.replace(token, "[unverified]")
            flagged.add(token)
            masked += 1
        report[field] = text

    if flagged:
        report["unknown_information"].append(
            f"Grounding check: the model mentioned values that are not in the incident data "
            f"({', '.join(sorted(flagged))}). {dropped} statement(s) were removed and {masked} "
            f"value(s) masked. Verify this report against the evidence."
        )
    return report


# -------------------------------------------------------------------- provider
class LLMProvider(AIProvider):
    def __init__(self) -> None:
        problem = configuration_problem()
        if problem:
            raise RuntimeError(problem)
        self.base_url = PROVIDER_BASE_URLS.get(settings.AI_PROVIDER) or settings.AI_BASE_URL
        self.model = resolve_model()
        self.name = f"llm:{settings.AI_PROVIDER}:{self.model}"

    async def _post(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in (0, 1):
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 429 and attempt == 0:
                    try:
                        wait = float(resp.headers.get("retry-after", 2))
                    except ValueError:
                        wait = 2.0
                    await _sleep(min(max(wait, 0.0), MAX_RETRY_WAIT_SECONDS))
                    continue
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError("unreachable")  # pragma: no cover

    async def investigate(self, context: dict) -> InvestigationOut:
        body = await self._post(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(context, default=str)},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
        )
        content = body["choices"][0]["message"]["content"]
        report = apply_grounding_guard(normalize_report(extract_json(content), context), context)
        report["generated_by"] = self.name
        report["generated_at"] = datetime.now(timezone.utc)
        return InvestigationOut(**report)
