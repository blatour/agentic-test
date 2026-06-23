from __future__ import annotations

from typing import List

from ambient_agent.contracts.changeset import ChangeSet
from ambient_agent.contracts.interfaces import ActionDecision
from ambient_agent.contracts.knowledge_state import KnowledgeState


class BaselinePolicyEngine:
    def decide(self, changeset: ChangeSet, current_state: KnowledgeState) -> List[ActionDecision]:
        # Placeholder policy baseline. Agent D owns expansion.
        _ = current_state
        if not changeset.reason_codes:
            return []
        return [
            ActionDecision(
                decision_id=f"decision-{changeset.changeset_id}",
                changeset_id=changeset.changeset_id,
                policy_id="baseline",
                action_type="notify",
                priority="low",
                should_execute=True,
                reason="baseline changeset generated",
                idempotency_key=f"baseline:{changeset.changeset_id}",
            )
        ]
