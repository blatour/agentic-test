from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Protocol

from ambient_agent.contracts.changeset import ChangeSet
from ambient_agent.contracts.envelopes import CanonicalEnvelope
from ambient_agent.contracts.knowledge_state import KnowledgeState


@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionDecision:
    decision_id: str
    changeset_id: str
    policy_id: str
    action_type: str
    priority: str
    should_execute: bool
    reason: str
    idempotency_key: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeliveryReceipt:
    sink_type: str
    status: str
    external_reference: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    source_type: str

    def ingest(self, source_config: Dict[str, Any]) -> Iterable[CanonicalEnvelope]:
        ...


class AnalysisProvider(Protocol):
    provider_type: str

    def analyze(
        self,
        envelope: CanonicalEnvelope,
        policy_config: Dict[str, Any],
    ) -> AnalysisResult:
        ...


class CompareEngine(Protocol):
    def compare(
        self,
        envelopes: Iterable[CanonicalEnvelope],
        current_state: KnowledgeState,
    ) -> ChangeSet:
        ...


class PolicyEngine(Protocol):
    def decide(
        self,
        changeset: ChangeSet,
        current_state: KnowledgeState,
    ) -> List[ActionDecision]:
        ...


class SinkAdapter(Protocol):
    sink_type: str

    def dispatch(self, decision: ActionDecision) -> DeliveryReceipt:
        ...
