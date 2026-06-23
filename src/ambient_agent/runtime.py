from __future__ import annotations

from typing import Iterable

from ambient_agent.contracts.changeset import ChangeSet
from ambient_agent.contracts.envelopes import CanonicalEnvelope
from ambient_agent.contracts.knowledge_state import KnowledgeState


class RuntimeLoop:
    """Coordinates ingest -> compare -> act -> persist.

    This class intentionally keeps stage order fixed so plugin additions
    do not require orchestration rewrites.
    """

    def run_cycle(
        self,
        envelopes: Iterable[CanonicalEnvelope],
        current_state: KnowledgeState,
    ) -> ChangeSet:
        # Placeholder orchestration contract for Agent A implementation.
        raise NotImplementedError("Runtime loop implementation is owned by Agent A")
