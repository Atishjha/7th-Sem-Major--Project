"""
Real AI provider: calls an OpenAI-compatible /chat/completions endpoint
(works for Groq, OpenRouter, OpenAI itself, and most self-hosted
OpenAI-compatible servers since they share this request/response
shape). Selected automatically when AI_PROVIDER != "mock" and
AI_API_KEY is set (see factory.py); the base URL per provider is
resolved from PROVIDER_BASE_URLS.

Honesty note for anyone reading this code: this provider is
implemented against the documented OpenAI-compatible API shape and
was verified mechanically against a local stub server (request
format, auth header, JSON-mode response parsing, and the fallback
path all behave correctly) — but it has not been exercised against a
real LLM backend in this environment, since no API key is available
here. The MockAIProvider is what's fully tested end-to-end and what
makes the demo work with zero configuration; this one is the
documented upgrade path.
"""

import json

import httpx

from app.config import settings
from app.schemas.ai_investigation import InvestigationOut
from app.ai.base import AIProvider

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai_compatible": None,  # AI_MODEL / a custom base must be reachable; see README
}

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


class LLMProvider(AIProvider):
    def __init__(self) -> None:
        self.name = f"llm:{settings.AI_PROVIDER}:{settings.AI_MODEL or 'default'}"
        self.base_url = PROVIDER_BASE_URLS.get(settings.AI_PROVIDER) or settings.AI_BASE_URL
        if not self.base_url:
            raise RuntimeError(
                f"No base URL for AI_PROVIDER={settings.AI_PROVIDER}. "
                "Set AI_BASE_URL for openai_compatible, or use groq/openrouter."
            )

    async def investigate(self, context: dict) -> InvestigationOut:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.AI_MODEL or "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(context)},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)

        from datetime import datetime, timezone
        parsed["generated_by"] = self.name
        parsed["generated_at"] = datetime.now(timezone.utc)
        return InvestigationOut(**parsed)
