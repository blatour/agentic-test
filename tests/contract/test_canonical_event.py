"""Contract tests for the Canonical Event Envelope.

These tests verify that the CanonicalEvent schema accepts well-formed
events and rejects payloads that violate the contract.  A test failure
here means either the fixture is wrong or the contract definition has
drifted — both warrant immediate attention.
"""

import pytest
import jsonschema

from contracts.canonical_event import validate_canonical_event, CANONICAL_EVENT_SCHEMA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_event(**overrides):
    base = {
        "event_id": "evt-github-001",
        "source": "github",
        "raw_event": "WEB [2024-01-15T10:00:00Z] - GitHub PushEvent by @alice on alice/repo (id=evt-001).",
        "fetched_at": "2024-01-15T10:00:00Z",
        "status": "ok",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid payloads — must pass validation
# ---------------------------------------------------------------------------

class TestCanonicalEventValid:
    def test_minimal_required_fields(self):
        validate_canonical_event(_valid_event())

    def test_with_empty_metadata(self):
        validate_canonical_event(_valid_event(metadata={}))

    def test_with_populated_metadata(self):
        validate_canonical_event(_valid_event(metadata={"points": 42, "region": "us-west"}))

    def test_status_fetch_error(self):
        validate_canonical_event(
            _valid_event(
                status="fetch-error",
                raw_event="Fetch failed for github: connection refused",
            )
        )

    def test_status_parse_error(self):
        validate_canonical_event(_valid_event(status="parse-error"))

    def test_status_error(self):
        validate_canonical_event(_valid_event(status="error"))

    @pytest.mark.parametrize("source", ["github", "usgs", "nasa", "simulated", "web-hn"])
    def test_all_valid_sources(self, source):
        validate_canonical_event(_valid_event(source=source))


# ---------------------------------------------------------------------------
# Invalid payloads — must raise ValidationError
# ---------------------------------------------------------------------------

class TestCanonicalEventInvalid:
    def test_missing_event_id(self):
        event = _valid_event()
        del event["event_id"]
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_missing_source(self):
        event = _valid_event()
        del event["source"]
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_missing_raw_event(self):
        event = _valid_event()
        del event["raw_event"]
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_missing_fetched_at(self):
        event = _valid_event()
        del event["fetched_at"]
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_missing_status(self):
        event = _valid_event()
        del event["status"]
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_unknown_source(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(_valid_event(source="unknown-source"))

    def test_invalid_status(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(_valid_event(status="timeout"))

    def test_empty_event_id(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(_valid_event(event_id=""))

    def test_event_id_wrong_type(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(_valid_event(event_id=12345))

    def test_extra_field_rejected(self):
        event = _valid_event()
        event["unknown_field"] = "should not be here"
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(event)

    def test_not_an_object(self):
        with pytest.raises(jsonschema.ValidationError):
            validate_canonical_event(["not", "an", "object"])
