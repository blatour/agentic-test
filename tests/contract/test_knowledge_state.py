"""Contract tests for the Knowledge State schema.

These tests verify that KnowledgeState payloads conform to the contract
that the compare phase consumes.  Failures here indicate schema drift
between the analysis layer and the decision layer.
"""

import pytest
import jsonschema

from contracts.knowledge_state import validate_knowledge_state, KNOWLEDGE_STATE_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_state(**overrides):
    base = {
        "cycle_id": "cycle-001",
        "state_at": "2024-01-15T10:05:00Z",
        "source_states": {
            "github": {
                "last_event_id": "evt-github-001",
                "last_status": "ok",
                "last_seen_at": "2024-01-15T10:00:00Z",
            }
        },
        "open_items": [],
    }
    base.update(overrides)
    return base


def _open_item(**overrides):
    base = {
        "item_id": "item-001",
        "description": "Unrecognized MAC address on IoT VLAN.",
        "severity": "High",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid payloads
# ---------------------------------------------------------------------------

class TestKnowledgeStateValid:
    def test_minimal_no_open_items(self):
        validate_knowledge_state(_valid_state())

    def test_multiple_sources(self):
        state = _valid_state(
            source_states={
                "github": {"last_event_id": "g-1", "last_status": "ok", "last_seen_at": "2024-01-15T10:00:00Z"},
                "usgs": {"last_event_id": None, "last_status": "fetch-error", "last_seen_at": None},
                "nasa": {"last_event_id": "n-1", "last_status": "ok", "last_seen_at": "2024-01-15T09:00:00Z"},
            }
        )
        validate_knowledge_state(state)

    def test_with_open_items(self):
        validate_knowledge_state(_valid_state(open_items=[_open_item()]))

    @pytest.mark.parametrize("severity", ["Low", "Medium", "High", "Critical"])
    def test_all_severities_accepted(self, severity):
        validate_knowledge_state(
            _valid_state(open_items=[_open_item(severity=severity)])
        )

    def test_null_last_event_id(self):
        state = _valid_state(
            source_states={
                "usgs": {
                    "last_event_id": None,
                    "last_status": "fetch-error",
                    "last_seen_at": None,
                }
            }
        )
        validate_knowledge_state(state)

    def test_empty_source_states(self):
        validate_knowledge_state(_valid_state(source_states={}))


# ---------------------------------------------------------------------------
# Invalid payloads
# ---------------------------------------------------------------------------

class TestKnowledgeStateInvalid:
    def test_missing_cycle_id(self):
        state = _valid_state()
        del state["cycle_id"]
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_missing_state_at(self):
        state = _valid_state()
        del state["state_at"]
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_missing_source_states(self):
        state = _valid_state()
        del state["source_states"]
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_missing_open_items(self):
        state = _valid_state()
        del state["open_items"]
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_source_state_missing_last_event_id(self):
        state = _valid_state(
            source_states={
                "github": {
                    "last_status": "ok",
                    "last_seen_at": "2024-01-15T10:00:00Z",
                }
            }
        )
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_open_item_invalid_severity(self):
        state = _valid_state(open_items=[_open_item(severity="Catastrophic")])
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_open_item_missing_item_id(self):
        item = _open_item()
        del item["item_id"]
        state = _valid_state(open_items=[item])
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_open_item_empty_item_id(self):
        state = _valid_state(open_items=[_open_item(item_id="")])
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_extra_top_level_field_rejected(self):
        state = _valid_state()
        state["extra_field"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)

    def test_open_item_extra_field_rejected(self):
        item = _open_item()
        item["unknown_field"] = "not allowed"
        state = _valid_state(open_items=[item])
        with pytest.raises(jsonschema.ValidationError):
            validate_knowledge_state(state)
