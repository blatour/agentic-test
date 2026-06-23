from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from ambient_agent.contracts.changeset import ChangeSet
from ambient_agent.contracts.envelopes import CanonicalEnvelope
from ambient_agent.contracts.knowledge_state import KnowledgeState


class BaselineCompareEngine:
    """Temporary compare engine.

    Agent owners should replace this with domain-aware resolvers.
    """

    def compare(
        self,
        envelopes: Iterable[CanonicalEnvelope],
        current_state: KnowledgeState,
    ) -> ChangeSet:
        envelope_ids = [item.envelope_id for item in envelopes]
        return ChangeSet(
            changeset_id=f"changeset-{int(datetime.now(tz=timezone.utc).timestamp())}",
            tenant_id=current_state.tenant_id,
            generated_at=datetime.now(tz=timezone.utc),
            input_envelope_ids=envelope_ids,
            new_facts=[],
            changed_facts=[],
            resolved_facts=[],
            risk_delta=0.0,
            confidence_delta=0.0,
            reason_codes=["baseline.compare.executed"],
        )
