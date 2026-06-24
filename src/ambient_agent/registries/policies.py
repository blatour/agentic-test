from __future__ import annotations

from typing import Dict

from ambient_agent.contracts.interfaces import PolicyEngine


class PolicyRegistry:
    def __init__(self) -> None:
        self._engines: Dict[str, PolicyEngine] = {}

    def register(self, policy_id: str, engine: PolicyEngine) -> None:
        self._engines[policy_id] = engine

    def get(self, policy_id: str) -> PolicyEngine:
        return self._engines[policy_id]
