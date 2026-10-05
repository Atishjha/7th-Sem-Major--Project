"""
AI provider interface. Every provider — mock or real — implements
`investigate(context) -> InvestigationOut`. The context dict is built
once by context_builder.py and handed to whichever provider is active,
so swapping providers never changes what data is available to them.
"""

from abc import ABC, abstractmethod

from app.schemas.ai_investigation import InvestigationOut


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def investigate(self, context: dict) -> InvestigationOut:
        ...
