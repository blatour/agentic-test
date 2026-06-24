"""Action Decision contract.

An ActionDecision is produced by the policy engine in response to a
ChangeSet. It records what action the agent chose to take, why, and
what payload was attached.

Fields
------
action_id       Unique identifier for this action (required).
cycle_id        Cycle that triggered this action (required).
action_type     Type of action taken (required).
triggered_by    Item ID or field path that triggered the action (required).
created_at      ISO-8601 timestamp of when the decision was made (required).
payload         Optional structured data attached to the action.
"""

import jsonschema

VALID_ACTION_TYPES = ["notify", "escalate", "suppress", "follow_up", "none"]

ACTION_DECISION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ActionDecision",
    "description": "Policy engine output: the action the agent decided to take.",
    "type": "object",
    "required": ["action_id", "cycle_id", "action_type", "triggered_by", "created_at"],
    "properties": {
        "action_id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique identifier for this action.",
        },
        "cycle_id": {
            "type": "string",
            "minLength": 1,
            "description": "Cycle that triggered this action.",
        },
        "action_type": {
            "type": "string",
            "enum": VALID_ACTION_TYPES,
            "description": "Type of action taken.",
        },
        "triggered_by": {
            "type": "string",
            "minLength": 1,
            "description": "Item ID or field path that triggered the action.",
        },
        "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp of when the decision was made.",
        },
        "payload": {
            "type": "object",
            "description": "Optional structured data attached to the action.",
        },
    },
    "additionalProperties": False,
}


def validate_action_decision(action: dict) -> None:
    """Validate *action* against the ActionDecision contract.

    Raises
    ------
    jsonschema.ValidationError
        When *action* does not conform to the schema.
    """
    jsonschema.validate(instance=action, schema=ACTION_DECISION_SCHEMA)
