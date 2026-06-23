from __future__ import annotations

from ambient_agent.contracts.envelopes import CanonicalEnvelope
from ambient_agent.contracts.interfaces import AnalysisProvider, AnalysisResult


class AnalysisGateway:
    def __init__(self, provider: AnalysisProvider) -> None:
        self._provider = provider

    def analyze(self, envelope: CanonicalEnvelope) -> AnalysisResult:
        return self._provider.analyze(envelope=envelope, policy_config={})
