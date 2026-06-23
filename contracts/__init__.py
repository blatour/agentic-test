"""Contract schema definitions for the ambient agent system.

These schemas define the canonical data shapes exchanged between agent
subsystems (ingestion, analysis, decision, persistence). Tests validate
that all runtime payloads conform to these contracts.
"""

from contracts.canonical_event import CANONICAL_EVENT_SCHEMA, validate_canonical_event
from contracts.knowledge_state import KNOWLEDGE_STATE_SCHEMA, validate_knowledge_state
from contracts.changeset import CHANGESET_SCHEMA, validate_changeset
from contracts.action_decision import ACTION_DECISION_SCHEMA, validate_action_decision

__all__ = [
    "CANONICAL_EVENT_SCHEMA",
    "validate_canonical_event",
    "KNOWLEDGE_STATE_SCHEMA",
    "validate_knowledge_state",
    "CHANGESET_SCHEMA",
    "validate_changeset",
    "ACTION_DECISION_SCHEMA",
    "validate_action_decision",
]
