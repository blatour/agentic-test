from __future__ import annotations

from typing import Dict

from ambient_agent.contracts.interfaces import SinkAdapter


class SinkRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, SinkAdapter] = {}

    def register(self, sink_type: str, adapter: SinkAdapter) -> None:
        self._adapters[sink_type] = adapter

    def get(self, sink_type: str) -> SinkAdapter:
        return self._adapters[sink_type]
