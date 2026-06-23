"""ChangeSet contract.

A ChangeSet records the delta between two consecutive KnowledgeState
snapshots. The compare phase produces a ChangeSet; the act phase
consumes it to decide which actions to take.

Fields
------
cycle_id        Cycle that produced this ChangeSet (required).
detected_at     ISO-8601 timestamp of when the comparison was run (required).
changes         List of field-level changes between prior and current state (required).
resolved_items  Open items from the previous cycle that are now resolved (required).
new_items       New open items detected this cycle (required).
"""

import jsonschema

CHANGESET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ChangeSet",
    "description": "Delta between two consecutive KnowledgeState snapshots.",
    "type": "object",
    "required": ["cycle_id", "detected_at", "changes", "resolved_items", "new_items"],
    "properties": {
        "cycle_id": {
            "type": "string",
            "minLength": 1,
            "description": "Cycle that produced this ChangeSet.",
        },
        "detected_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp of when the comparison was run.",
        },
        "changes": {
            "type": "array",
            "description": "Field-level differences between prior and current state.",
            "items": {
                "type": "object",
                "required": ["field", "old_value", "new_value"],
                "properties": {
                    "field": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Dot-path to the changed field.",
                    },
                    "old_value": {
                        "description": "Value before this cycle.",
                    },
                    "new_value": {
                        "description": "Value after this cycle.",
                    },
                },
                "additionalProperties": False,
            },
        },
        "resolved_items": {
            "type": "array",
            "description": "Item IDs from the previous cycle now resolved.",
            "items": {"type": "string"},
        },
        "new_items": {
            "type": "array",
            "description": "Item IDs that are new this cycle.",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


def validate_changeset(changeset: dict) -> None:
    """Validate *changeset* against the ChangeSet contract.

    Raises
    ------
    jsonschema.ValidationError
        When *changeset* does not conform to the schema.
    """
    jsonschema.validate(instance=changeset, schema=CHANGESET_SCHEMA)
