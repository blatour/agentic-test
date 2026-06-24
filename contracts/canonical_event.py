"""Canonical Event Envelope contract.

Every event ingested from any source (GitHub, USGS, NASA, simulated)
must be normalized into this envelope before analysis or persistence.

Fields
------
event_id    Deterministic unique identifier for the event (required).
source      Originating source key (required).
raw_event   Raw text content of the event (required).
fetched_at  ISO-8601 timestamp of when the event was fetched (required).
status      Outcome of the fetch: ok | fetch-error | parse-error | error (required).
metadata    Optional source-specific key/value bag.
"""

import jsonschema

VALID_SOURCES = ["github", "usgs", "nasa", "simulated", "web-hn"]
VALID_STATUSES = ["ok", "fetch-error", "parse-error", "error"]

CANONICAL_EVENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CanonicalEvent",
    "description": "Normalized event envelope produced by a source adapter.",
    "type": "object",
    "required": ["event_id", "source", "raw_event", "fetched_at", "status"],
    "properties": {
        "event_id": {
            "type": "string",
            "minLength": 1,
            "description": "Deterministic unique identifier for this event.",
        },
        "source": {
            "type": "string",
            "enum": VALID_SOURCES,
            "description": "Originating source adapter key.",
        },
        "raw_event": {
            "type": "string",
            "description": "Raw text representation of the event.",
        },
        "fetched_at": {
            "type": "string",
            "format": "date-time",
            "description": "ISO-8601 timestamp of when the event was fetched.",
        },
        "status": {
            "type": "string",
            "enum": VALID_STATUSES,
            "description": "Fetch outcome status.",
        },
        "metadata": {
            "type": "object",
            "description": "Optional source-specific supplementary data.",
        },
    },
    "additionalProperties": False,
}


def validate_canonical_event(event: dict) -> None:
    """Validate *event* against the CanonicalEvent contract.

    Raises
    ------
    jsonschema.ValidationError
        When *event* does not conform to the schema.
    """
    jsonschema.validate(instance=event, schema=CANONICAL_EVENT_SCHEMA)
