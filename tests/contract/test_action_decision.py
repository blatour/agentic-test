"""Contract tests for the Action Decision schema.

These tests verify that ActionDecision payloads emitted by the policy
engine conform to the contract consumed by the notification dispatcher
and persistence layer.
"""

import pytest
import jsonschema

from contracts.action_decision import validate_action_decision, ACTION_DECISION_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_action(**overrides):
    base = {
        "action_id": "action-001",
        "cycle_id": "cycle-002",
        "action_type": "escalate",
        "triggered_by": "item-001",
        "created_at": "2024-01-15T10:10:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid payloads
# ---------------------------------------------------------------------------

class TestActionDecisionValid:
    def test_minimal_required_fields(self):
        validate_action_decision(_valid_action())

    def test_with_empty_payload(self):
        validate_action_decision(_valid_action(payload={}))

    def test_with_populated_payload(self):
        validate_action_decision(
            _valid_action(
                payload={
                    "channel": "ops-alerts",
                    "message": "High-severity item detected on IoT VLAN.",
                }
            )
        )

    @pytest.mark.parametrize(
        "action_type", ["notify", "escalate", "suppress", "follow_up", "none"]
    )
    def test_all_valid_action_types(self, action_type):
        validate_action_decision(_valid_action(action_type=action_type))

    def test_none_action_type(self):
        validate_action_decision(_valid_action(action_type="none"))

    def test_triggered_by_field_path(self):
        validate_action_decision(_valid_action(triggered_by="source_states.github.last_status"))


# ---------------------------------------------------------------------------
# Invalid payloads
# ---------------------------------------------------------------------------

class TestActionDecisionInvalid:
    def test_missing_action_id(self):
        action = _valid_action()
        del action["action_id"]
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_missing_cycle_id(self):
        action = _valid_action()
        del action["cycle_id"]
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_missing_action_type(self):
        action = _valid_action()
        del action["action_type"]
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_missing_triggered_by(self):
        action = _valid_action()
        del action["triggered_by"]
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_missing_created_at(self):
        action = _valid_action()
        del action["created_at"]
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_invalid_action_type(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(_valid_action(action_type="delete"))

    def test_empty_action_id(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(_valid_action(action_id=""))

    def test_empty_cycle_id(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(_valid_action(cycle_id=""))

    def test_empty_triggered_by(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(_valid_action(triggered_by=""))

    def test_extra_field_rejected(self):
        action = _valid_action()
        action["unknown_field"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(action)

    def test_action_id_wrong_type(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision(_valid_action(action_id=42))

    def test_not_an_object(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_action_decision("escalate")
