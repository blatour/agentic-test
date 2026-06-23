from __future__ import annotations

from typing import Dict

from ambient_agent.contracts.interfaces import AnalysisProvider


class AnalysisRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, AnalysisProvider] = {}

    def register(self, provider_type: str, provider: AnalysisProvider) -> None:
        self._providers[provider_type] = provider

    def get(self, provider_type: str) -> AnalysisProvider:
        return self._providers[provider_type]
