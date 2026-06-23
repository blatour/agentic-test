from __future__ import annotations

from typing import Protocol

from ambient_agent.contracts.changeset import ChangeSet
from ambient_agent.contracts.envelopes import CanonicalEnvelope
from ambient_agent.contracts.interfaces import ActionDecision, DeliveryReceipt
from ambient_agent.contracts.knowledge_state import KnowledgeState


class Repository(Protocol):
    def save_raw_envelope(self, envelope: CanonicalEnvelope) -> None:
        ...

    def save_canonical_envelope(self, envelope: CanonicalEnvelope) -> None:
        ...

    def load_knowledge_state(self, tenant_id: str) -> KnowledgeState:
        ...

    def save_changeset(self, changeset: ChangeSet) -> None:
        ...

    def save_action_decision(self, decision: ActionDecision) -> None:
        ...

    def save_delivery_receipt(self, receipt: DeliveryReceipt) -> None:
        ...

    def save_knowledge_state(self, state: KnowledgeState) -> None:
        ...
