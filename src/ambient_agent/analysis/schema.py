"""
Analysis response schema definition and ChangeSet enrichment mapping.

This module defines the strict JSON schema for structured model analysis output,
including confidence scores and reason codes consumable by compare/policy stages.
"""

from __future__ import annotations

# Severity levels recognized by the policy engine.
SEVERITY_LEVELS = ("High", "Medium", "Low")

# Reason codes that can appear in an analysis response.
# Policy and compare stages should treat these as stable identifiers.
REASON_CODES = {
    "SECURITY_ALERT",
    "NETWORK_ANOMALY",
    "RESOURCE_PRESSURE",
    "DEPLOYMENT_EVENT",
    "EXTERNAL_EVENT",
    "ROUTINE_ACTIVITY",
    "PARSE_FALLBACK",
    "DRY_RUN_MOCK",
    "UNKNOWN",
}

# JSON Schema (Draft 7) for a structured analysis payload.
ANALYSIS_RESPONSE_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AnalysisResponse",
    "description": "Structured output from a model analysis of a single source event.",
    "type": "object",
    "required": ["severity", "confidence", "summary", "recommendation", "reason_codes"],
    "additionalProperties": False,
    "properties": {
        "severity": {
            "type": "string",
            "enum": list(SEVERITY_LEVELS),
            "description": "Triage severity assessed by the model.",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Model confidence in its assessment, in the range [0.0, 1.0].",
        },
        "summary": {
            "type": "string",
            "minLength": 1,
            "description": "Plain-English summary of the event.",
        },
        "recommendation": {
            "type": "string",
            "minLength": 1,
            "description": "Actionable one-sentence recommendation for the operator.",
        },
        "reason_codes": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": sorted(REASON_CODES),
            },
            "minItems": 1,
            "uniqueItems": True,
            "description": "Machine-readable reason tags consumable by policy/compare stages.",
        },
        "source_event": {
            "type": "string",
            "description": "Original event text that was analysed (optional, for audit).",
        },
    },
}


def map_to_changeset_fields(payload: dict) -> dict:
    """Return a flat dict of ChangeSet enrichment fields from a validated payload.

    The keys returned here are the canonical field names that Agent B persistence
    and Agent D policy stages consume. Callers should merge these into their
    ChangeSet or analysis record.

    Args:
        payload: A validated analysis payload (passes ``ANALYSIS_RESPONSE_SCHEMA``).

    Returns:
        Dict with keys: ``analysis_severity``, ``analysis_confidence``,
        ``analysis_summary``, ``analysis_recommendation``, ``analysis_reason_codes``.
    """
    return {
        "analysis_severity": payload["severity"],
        "analysis_confidence": payload["confidence"],
        "analysis_summary": payload["summary"],
        "analysis_recommendation": payload["recommendation"],
        "analysis_reason_codes": list(payload["reason_codes"]),
    }
