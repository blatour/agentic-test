"""Knowledge State contract.

The KnowledgeState captures the agent's current understanding of the
monitored system at the end of a cycle. It records per-source health
and any open items that require follow-up in later cycles.

Fields
------
cycle_id        Unique identifier for the analysis cycle (required).
state_at        ISO-8601 timestamp of when this state was captured (required).
source_states   Per-source health records keyed by source name (required).
open_items      List of unresolved items requiring attention (required).
"""

import jsonschema

VALID_SEVERITIES = ["Low", "Medium", "High", "Critical"]

KNOWLEDGE_STATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "KnowledgeState",
    "description": "Agent knowledge snapshot at the end of a cycle.",
    "type": "object",
    "required": ["cycle_id", "state_at", "source_states", "open_items"],
    "properties": {
        "cycle_id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for this analysis cycle.",
        },
        "state_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp of when this state was captured.",
        },
        "source_states": {
            "type": "object",
            "description": "Per-source health and event records.",
            "additionalProperties": {
                "type": "object",
                "required": ["last_event_id", "last_status", "last_seen_at"],
                "properties": {
                    "last_event_id": {
                        "type": ["string", "null"],
                        "description": "ID of the last event seen from this source.",
                    },
                    "last_status": {
                        "type": "string",
                        "description": "Last fetch status for this source.",
                    },
                    "last_seen_at": {
                        "type": ["string", "null"],
                        "description": "ISO-8601 timestamp of the last successful fetch.",
                    },
                },
                "additionalProperties": False,
            },
        },
        "open_items": {
            "type": "array",
            "description": "Unresolved items requiring follow-up.",
            "items": {
                "type": "object",
                "required": ["item_id", "description", "severity"],
                "properties": {
                    "item_id": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Unique identifier for this open item.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the item.",
                    },
                    "severity": {
                        "type": "string",
                        "enum": VALID_SEVERITIES,
                        "description": "Severity level of the open item.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


def validate_knowledge_state(state: dict) -> None:
    """Validate *state* against the KnowledgeState contract.

    Raises
    ------
    jsonschema.ValidationError
        When *state* does not conform to the schema.
    """
    jsonschema.validate(instance=state, schema=KNOWLEDGE_STATE_SCHEMA)
