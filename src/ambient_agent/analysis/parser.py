"""
Analysis response parser and validator utilities.

Responsibilities:
- Extract JSON from raw model output (handles markdown code fences).
- Validate payloads against ``ANALYSIS_RESPONSE_SCHEMA``.
- Classify malformed model output into typed failure kinds.
- Build safe fallback analysis payloads from raw event text.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Optional

import jsonschema

from .schema import ANALYSIS_RESPONSE_SCHEMA, map_to_changeset_fields


class ParseFailureKind(str, Enum):
    """Taxonomy of reasons why model output could not be parsed or validated."""

    NOT_JSON = "not_json"
    SCHEMA_VIOLATION = "schema_violation"
    EMPTY_RESPONSE = "empty_response"
    UNKNOWN = "unknown"


class ParseResult:
    """Container returned by :func:`parse_and_validate`.

    Attributes:
        payload:    Validated analysis dict when ``ok`` is True, else ``None``.
        ok:         True when parsing and validation both succeeded.
        failure:    :class:`ParseFailureKind` when ``ok`` is False, else ``None``.
        error_detail: Human-readable description of the failure (when ``ok`` is False).
        changeset_fields: Convenience mapping for ChangeSet enrichment (when ``ok`` is True).
    """

    def __init__(
        self,
        *,
        payload: Optional[dict],
        ok: bool,
        failure: Optional[ParseFailureKind] = None,
        error_detail: str = "",
    ) -> None:
        self.payload = payload
        self.ok = ok
        self.failure = failure
        self.error_detail = error_detail
        self.changeset_fields: dict = (
            map_to_changeset_fields(payload) if ok and payload else {}
        )

    def __repr__(self) -> str:  # pragma: no cover
        if self.ok:
            return f"<ParseResult ok severity={self.payload['severity']}>"
        return f"<ParseResult FAIL {self.failure}: {self.error_detail[:60]}>"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _extract_json_text(raw: str) -> str:
    """Return the best candidate JSON string from raw model output.

    Tries, in order:
    1. Content inside the first ```json … ``` or ``` … ``` code fence.
    2. The substring from the first ``{`` to the last ``}``.
    3. The raw string itself (stripped).
    """
    fence_match = _FENCE_RE.search(raw)
    if fence_match:
        return fence_match.group(1).strip()

    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        return raw[brace_start : brace_end + 1]

    return raw.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_parse_failure(raw: str, exc: Exception) -> ParseFailureKind:
    """Classify a parse or validation exception into a :class:`ParseFailureKind`.

    Args:
        raw:  Raw model output string.
        exc:  The exception raised during parsing or validation.

    Returns:
        A :class:`ParseFailureKind` enum value.
    """
    if not raw or not raw.strip():
        return ParseFailureKind.EMPTY_RESPONSE
    if isinstance(exc, json.JSONDecodeError):
        return ParseFailureKind.NOT_JSON
    if isinstance(exc, jsonschema.ValidationError):
        return ParseFailureKind.SCHEMA_VIOLATION
    return ParseFailureKind.UNKNOWN


def parse_and_validate(raw: str) -> ParseResult:
    """Parse raw model output and validate it against ``ANALYSIS_RESPONSE_SCHEMA``.

    The function is lenient at the extraction stage (handles code fences, leading
    prose) but strict at the validation stage (jsonschema).

    Args:
        raw: Raw string returned by the model.

    Returns:
        A :class:`ParseResult` — check ``result.ok`` before using ``result.payload``.
    """
    if not raw or not raw.strip():
        return ParseResult(
            payload=None,
            ok=False,
            failure=ParseFailureKind.EMPTY_RESPONSE,
            error_detail="Model returned an empty response.",
        )

    json_text = _extract_json_text(raw)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        return ParseResult(
            payload=None,
            ok=False,
            failure=ParseFailureKind.NOT_JSON,
            error_detail=str(exc),
        )

    try:
        jsonschema.validate(instance=data, schema=ANALYSIS_RESPONSE_SCHEMA)
    except jsonschema.ValidationError as exc:
        return ParseResult(
            payload=None,
            ok=False,
            failure=ParseFailureKind.SCHEMA_VIOLATION,
            error_detail=exc.message,
        )

    return ParseResult(payload=data, ok=True)


def build_fallback_analysis(raw_event: str, failure: ParseFailureKind) -> dict:
    """Build a safe fallback analysis payload when model output is invalid.

    The returned payload is always valid against ``ANALYSIS_RESPONSE_SCHEMA``.
    The ``reason_codes`` field will include ``"PARSE_FALLBACK"`` so downstream
    stages can distinguish genuine model assessments from fallbacks.

    Args:
        raw_event:  Original event text that was analysed.
        failure:    Classification of why the model output was unusable.

    Returns:
        A validated analysis payload dict.
    """
    lowered = raw_event.lower()
    if "security" in lowered or "unrecognized" in lowered:
        severity = "High"
        recommendation = (
            "Investigate immediately, isolate the device, and review recent network logs."
        )
        reason_codes = ["SECURITY_ALERT", "PARSE_FALLBACK"]
    elif "warning" in lowered or "spiked" in lowered or "memory" in lowered:
        severity = "Medium"
        recommendation = (
            "Track this signal over the next hour and alert if usage remains elevated."
        )
        reason_codes = ["RESOURCE_PRESSURE", "PARSE_FALLBACK"]
    else:
        severity = "Low"
        recommendation = "No urgent action required; record the event and continue monitoring."
        reason_codes = ["ROUTINE_ACTIVITY", "PARSE_FALLBACK"]

    payload = {
        "severity": severity,
        "confidence": 0.0,
        "summary": raw_event[:500] if raw_event else "Event text unavailable.",
        "recommendation": recommendation,
        "reason_codes": reason_codes,
        "source_event": raw_event,
    }

    jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)
    return payload
