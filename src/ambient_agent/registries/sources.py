from __future__ import annotations

from typing import Dict

from ambient_agent.contracts.interfaces import SourceAdapter


class SourceRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, SourceAdapter] = {}

    def register(self, source_type: str, adapter: SourceAdapter) -> None:
        self._adapters[source_type] = adapter

    def get(self, source_type: str) -> SourceAdapter:
        return self._adapters[source_type]
