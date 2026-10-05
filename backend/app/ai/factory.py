"""
Provider selection with mandatory fallback: per the spec, "if an
external LLM is unavailable, the system should still generate a
structured AI investigation from the incident evidence" — so any
failure of the real provider (missing config, network error, bad
response shape) falls back to MockAIProvider rather than failing the
request. The returned `provider_used` string always says which
actually ran, so a fallback is never silently indistinguishable from
a successful real call.
"""

from app.config import settings
from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider


async def run_investigation(context: dict):
    if settings.AI_PROVIDER != "mock" and settings.AI_API_KEY:
        try:
            from app.ai.llm_provider import LLMProvider

            provider: AIProvider = LLMProvider()
            result = await provider.investigate(context)
            return result, provider.name
        except Exception as e:
            fallback = MockAIProvider()
            result = await fallback.investigate(context)
            return result, f"mock (llm_failed: {type(e).__name__})"

    provider = MockAIProvider()
    result = await provider.investigate(context)
    return result, provider.name
