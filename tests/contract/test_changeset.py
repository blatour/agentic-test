"""Contract tests for the ChangeSet schema.

These tests verify that ChangeSet payloads produced by the compare phase
conform to the contract consumed by the act (policy) phase.  Failures
indicate that the comparison layer is emitting malformed deltas.
"""

import pytest
import jsonschema

from contracts.changeset import validate_changeset, CHANGESET_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_changeset(**overrides):
    base = {
        "cycle_id": "cycle-002",
        "detected_at": "2024-01-15T10:10:00Z",
        "changes": [],
        "resolved_items": [],
        "new_items": [],
    }
    base.update(overrides)
    return base


def _change(field="github.last_status", old_value="ok", new_value="fetch-error"):
    return {"field": field, "old_value": old_value, "new_value": new_value}


# ---------------------------------------------------------------------------
# Valid payloads
# ---------------------------------------------------------------------------

class TestChangeSetValid:
    def test_empty_changeset(self):
        validate_changeset(_valid_changeset())

    def test_with_one_change(self):
        validate_changeset(_valid_changeset(changes=[_change()]))

    def test_with_multiple_changes(self):
        validate_changeset(
            _valid_changeset(
                changes=[
                    _change("github.last_status", "ok", "fetch-error"),
                    _change("usgs.last_event_id", None, "usgs-quake-999"),
                ]
            )
        )

    def test_with_resolved_items(self):
        validate_changeset(
            _valid_changeset(resolved_items=["item-001", "item-002"])
        )

    def test_with_new_items(self):
        validate_changeset(_valid_changeset(new_items=["item-003"]))

    def test_change_with_null_old_value(self):
        validate_changeset(
            _valid_changeset(changes=[_change(old_value=None, new_value="usgs-001")])
        )

    def test_change_with_object_values(self):
        validate_changeset(
            _valid_changeset(
                changes=[
                    {
                        "field": "source_states.github",
                        "old_value": {"last_status": "ok"},
                        "new_value": {"last_status": "fetch-error"},
                    }
                ]
            )
        )


# ---------------------------------------------------------------------------
# Invalid payloads
# ---------------------------------------------------------------------------

class TestChangeSetInvalid:
    def test_missing_cycle_id(self):
        cs = _valid_changeset()
        del cs["cycle_id"]
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_missing_detected_at(self):
        cs = _valid_changeset()
        del cs["detected_at"]
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_missing_changes(self):
        cs = _valid_changeset()
        del cs["changes"]
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_missing_resolved_items(self):
        cs = _valid_changeset()
        del cs["resolved_items"]
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_missing_new_items(self):
        cs = _valid_changeset()
        del cs["new_items"]
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_empty_cycle_id(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(_valid_changeset(cycle_id=""))

    def test_change_missing_field(self):
        cs = _valid_changeset(changes=[{"old_value": "ok", "new_value": "error"}])
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_change_empty_field(self):
        cs = _valid_changeset(changes=[_change(field="")])
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_change_extra_field_rejected(self):
        change = _change()
        change["extra"] = "not allowed"
        cs = _valid_changeset(changes=[change])
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)

    def test_resolved_items_not_strings(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(_valid_changeset(resolved_items=[{"id": "item-001"}]))

    def test_extra_top_level_field_rejected(self):
        cs = _valid_changeset()
        cs["extra_field"] = "not allowed"
        with pytest.raises(jsonschema.ValidationError):
            validate_changeset(cs)
