"""
Contract tests for the analysis schema, parser, and gateway.

These tests cover:
- Valid analysis payloads pass schema validation.
- Invalid payloads are rejected with appropriate failure kinds.
- Parser extracts JSON from code-fenced and plain model output.
- Fallback analysis is always schema-valid.
- DryRunGateway returns structured, validated results.
- OllamaGateway handles HTTP failures gracefully (returns fallback).
- ChangeSet enrichment fields are correctly populated.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from ambient_agent.analysis.schema import (
    ANALYSIS_RESPONSE_SCHEMA,
    REASON_CODES,
    SEVERITY_LEVELS,
    map_to_changeset_fields,
)
from ambient_agent.analysis.parser import (
    ParseFailureKind,
    ParseResult,
    build_fallback_analysis,
    classify_parse_failure,
    parse_and_validate,
)
from ambient_agent.analysis.gateway import (
    AnalysisResult,
    DryRunGateway,
    OllamaGateway,
    make_gateway,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_PAYLOAD = {
    "severity": "High",
    "confidence": 0.95,
    "summary": "Unrecognized MAC address attempted handshake on IoT VLAN.",
    "recommendation": "Isolate the device and review recent network logs immediately.",
    "reason_codes": ["SECURITY_ALERT"],
    "source_event": "LOG - Security: Unrecognized local MAC address detected.",
}

MINIMAL_VALID_PAYLOAD = {
    "severity": "Low",
    "confidence": 0.3,
    "summary": "Routine deployment event observed.",
    "recommendation": "No action required.",
    "reason_codes": ["ROUTINE_ACTIVITY"],
}


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestAnalysisSchema:
    def test_valid_payload_passes(self):
        jsonschema.validate(instance=VALID_PAYLOAD, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_minimal_valid_payload_passes(self):
        jsonschema.validate(instance=MINIMAL_VALID_PAYLOAD, schema=ANALYSIS_RESPONSE_SCHEMA)

    @pytest.mark.parametrize("severity", SEVERITY_LEVELS)
    def test_all_severity_levels_pass(self, severity):
        payload = {**MINIMAL_VALID_PAYLOAD, "severity": severity}
        jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    @pytest.mark.parametrize("code", sorted(REASON_CODES))
    def test_all_reason_codes_valid(self, code):
        payload = {**MINIMAL_VALID_PAYLOAD, "reason_codes": [code]}
        jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_invalid_severity_fails(self):
        payload = {**VALID_PAYLOAD, "severity": "Critical"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_confidence_below_zero_fails(self):
        payload = {**VALID_PAYLOAD, "confidence": -0.1}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_confidence_above_one_fails(self):
        payload = {**VALID_PAYLOAD, "confidence": 1.1}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_missing_required_field_fails(self):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "summary"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_empty_reason_codes_fails(self):
        payload = {**VALID_PAYLOAD, "reason_codes": []}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_invalid_reason_code_fails(self):
        payload = {**VALID_PAYLOAD, "reason_codes": ["NOT_A_REAL_CODE"]}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_additional_properties_rejected(self):
        payload = {**VALID_PAYLOAD, "unexpected_field": "value"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_map_to_changeset_fields_keys(self):
        fields = map_to_changeset_fields(VALID_PAYLOAD)
        assert set(fields.keys()) == {
            "analysis_severity",
            "analysis_confidence",
            "analysis_summary",
            "analysis_recommendation",
            "analysis_reason_codes",
        }

    def test_map_to_changeset_fields_values(self):
        fields = map_to_changeset_fields(VALID_PAYLOAD)
        assert fields["analysis_severity"] == "High"
        assert fields["analysis_confidence"] == 0.95
        assert "SECURITY_ALERT" in fields["analysis_reason_codes"]


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestParser:
    def test_parse_plain_json(self):
        raw = json.dumps(VALID_PAYLOAD)
        result = parse_and_validate(raw)
        assert result.ok
        assert result.payload["severity"] == "High"

    def test_parse_json_with_code_fence(self):
        raw = "```json\n" + json.dumps(VALID_PAYLOAD) + "\n```"
        result = parse_and_validate(raw)
        assert result.ok
        assert result.payload["confidence"] == 0.95

    def test_parse_json_with_plain_fence(self):
        raw = "```\n" + json.dumps(VALID_PAYLOAD) + "\n```"
        result = parse_and_validate(raw)
        assert result.ok

    def test_parse_json_with_surrounding_prose(self):
        raw = "Here is my analysis:\n" + json.dumps(VALID_PAYLOAD) + "\nEnd."
        result = parse_and_validate(raw)
        assert result.ok

    def test_changeset_fields_populated_on_success(self):
        raw = json.dumps(VALID_PAYLOAD)
        result = parse_and_validate(raw)
        assert result.ok
        assert "analysis_severity" in result.changeset_fields
        assert result.changeset_fields["analysis_severity"] == "High"

    def test_empty_response_classified(self):
        result = parse_and_validate("")
        assert not result.ok
        assert result.failure == ParseFailureKind.EMPTY_RESPONSE

    def test_whitespace_only_response_classified(self):
        result = parse_and_validate("   \n  ")
        assert not result.ok
        assert result.failure == ParseFailureKind.EMPTY_RESPONSE

    def test_non_json_classified(self):
        result = parse_and_validate("This is not JSON at all.")
        assert not result.ok
        assert result.failure == ParseFailureKind.NOT_JSON

    def test_schema_violation_classified(self):
        bad = {**VALID_PAYLOAD, "severity": "EXTREME"}
        result = parse_and_validate(json.dumps(bad))
        assert not result.ok
        assert result.failure == ParseFailureKind.SCHEMA_VIOLATION

    def test_changeset_fields_empty_on_failure(self):
        result = parse_and_validate("bad input")
        assert not result.ok
        assert result.changeset_fields == {}

    def test_classify_parse_failure_empty(self):
        kind = classify_parse_failure("", ValueError("err"))
        assert kind == ParseFailureKind.EMPTY_RESPONSE

    def test_classify_parse_failure_json_decode(self):
        import json as _json
        try:
            _json.loads("{bad}")
        except _json.JSONDecodeError as exc:
            kind = classify_parse_failure("{bad}", exc)
        assert kind == ParseFailureKind.NOT_JSON

    def test_classify_parse_failure_schema_violation(self):
        try:
            jsonschema.validate(instance={"x": 1}, schema=ANALYSIS_RESPONSE_SCHEMA)
        except jsonschema.ValidationError as exc:
            kind = classify_parse_failure("{}", exc)
        assert kind == ParseFailureKind.SCHEMA_VIOLATION


# ---------------------------------------------------------------------------
# Fallback tests
# ---------------------------------------------------------------------------


class TestFallback:
    @pytest.mark.parametrize(
        "event,expected_severity,expected_code",
        [
            (
                "Security: Unrecognized MAC detected",
                "High",
                "SECURITY_ALERT",
            ),
            (
                "Container memory spiked to 88%",
                "Medium",
                "RESOURCE_PRESSURE",
            ),
            (
                "Deploy pipeline success build #104",
                "Low",
                "ROUTINE_ACTIVITY",
            ),
        ],
    )
    def test_fallback_severity_and_code(self, event, expected_severity, expected_code):
        payload = build_fallback_analysis(event, ParseFailureKind.NOT_JSON)
        assert payload["severity"] == expected_severity
        assert expected_code in payload["reason_codes"]

    def test_fallback_always_schema_valid(self):
        for event in [
            "Security alert triggered",
            "Memory warning spiked",
            "Routine log entry",
            "",
        ]:
            payload = build_fallback_analysis(event, ParseFailureKind.UNKNOWN)
            jsonschema.validate(instance=payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_fallback_has_parse_fallback_code(self):
        payload = build_fallback_analysis("some event", ParseFailureKind.NOT_JSON)
        assert "PARSE_FALLBACK" in payload["reason_codes"]

    def test_fallback_confidence_zero(self):
        payload = build_fallback_analysis("some event", ParseFailureKind.SCHEMA_VIOLATION)
        assert payload["confidence"] == 0.0

    def test_fallback_includes_source_event(self):
        event = "test event text"
        payload = build_fallback_analysis(event, ParseFailureKind.NOT_JSON)
        assert payload["source_event"] == event


# ---------------------------------------------------------------------------
# DryRunGateway tests
# ---------------------------------------------------------------------------


class TestDryRunGateway:
    def setup_method(self):
        self.gateway = DryRunGateway()

    def test_returns_analysis_result(self):
        result = self.gateway.analyse("LOG - Node high memory warning.")
        assert isinstance(result, AnalysisResult)

    def test_ok_true(self):
        result = self.gateway.analyse("LOG - Deploy pipeline success.")
        assert result.ok is True

    def test_is_not_fallback(self):
        result = self.gateway.analyse("LOG - Deploy pipeline success.")
        assert result.is_fallback is False

    def test_payload_is_schema_valid(self):
        result = self.gateway.analyse("LOG - Security unrecognized MAC detected.")
        jsonschema.validate(instance=result.payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_dry_run_reason_code_present(self):
        result = self.gateway.analyse("Some event")
        assert "DRY_RUN_MOCK" in result.payload["reason_codes"]

    def test_changeset_fields_populated(self):
        result = self.gateway.analyse("Deploy event")
        assert "analysis_severity" in result.changeset_fields
        assert "analysis_confidence" in result.changeset_fields
        assert "analysis_reason_codes" in result.changeset_fields

    def test_model_name_is_dry_run(self):
        result = self.gateway.analyse("event")
        assert result.model_name == DryRunGateway.MODEL_NAME

    def test_security_event_high_severity(self):
        result = self.gateway.analyse("Security: Unrecognized MAC address detected")
        assert result.payload["severity"] == "High"

    def test_warning_event_medium_severity(self):
        result = self.gateway.analyse("Container memory spiked warning")
        assert result.payload["severity"] == "Medium"

    def test_routine_event_low_severity(self):
        result = self.gateway.analyse("Deploy pipeline success build #104")
        assert result.payload["severity"] == "Low"


# ---------------------------------------------------------------------------
# OllamaGateway tests (HTTP mocked)
# ---------------------------------------------------------------------------


class TestOllamaGateway:
    def _make_mock_response(self, payload: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(payload)}
        return mock_resp

    def test_valid_response_returns_ok(self):
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", return_value=self._make_mock_response(VALID_PAYLOAD)):
            result = gateway.analyse("Security: Unrecognized MAC detected")
        assert result.ok is True
        assert result.is_fallback is False
        assert result.payload["severity"] == "High"

    def test_valid_response_changeset_fields(self):
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", return_value=self._make_mock_response(VALID_PAYLOAD)):
            result = gateway.analyse("Security event")
        assert result.changeset_fields["analysis_severity"] == "High"
        assert result.changeset_fields["analysis_confidence"] == 0.95

    def test_invalid_json_returns_fallback(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "Not JSON at all."}
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", return_value=mock_resp):
            result = gateway.analyse("Security event")
        assert result.ok is False
        assert result.is_fallback is True
        assert result.failure == ParseFailureKind.NOT_JSON

    def test_schema_violation_returns_fallback(self):
        bad_payload = {**VALID_PAYLOAD, "severity": "ULTRA"}
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": json.dumps(bad_payload)}
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", return_value=mock_resp):
            result = gateway.analyse("Some event")
        assert result.ok is False
        assert result.failure == ParseFailureKind.SCHEMA_VIOLATION

    def test_http_error_returns_fallback(self):
        import requests as req
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", side_effect=req.ConnectionError("refused")):
            result = gateway.analyse("Memory warning spiked")
        assert result.ok is False
        assert result.is_fallback is True
        assert "refused" in result.error_detail

    def test_fallback_on_http_error_is_schema_valid(self):
        import requests as req
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", side_effect=req.ConnectionError("refused")):
            result = gateway.analyse("Memory warning spiked")
        jsonschema.validate(instance=result.payload, schema=ANALYSIS_RESPONSE_SCHEMA)

    def test_fallback_changeset_fields_populated_on_error(self):
        import requests as req
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", side_effect=req.ConnectionError("refused")):
            result = gateway.analyse("Some event")
        assert "analysis_severity" in result.changeset_fields

    def test_model_name_recorded(self):
        gateway = OllamaGateway(url="http://mock", model_name="my-model")
        with patch("requests.post", return_value=self._make_mock_response(VALID_PAYLOAD)):
            result = gateway.analyse("event")
        assert result.model_name == "my-model"

    def test_latency_recorded(self):
        gateway = OllamaGateway(url="http://mock", model_name="test-model")
        with patch("requests.post", return_value=self._make_mock_response(VALID_PAYLOAD)):
            result = gateway.analyse("event")
        assert result.latency_ms >= 0.0


# ---------------------------------------------------------------------------
# make_gateway factory tests
# ---------------------------------------------------------------------------


class TestMakeGateway:
    def test_dry_run_returns_dry_run_gateway(self):
        gw = make_gateway(dry_run=True)
        assert isinstance(gw, DryRunGateway)

    def test_live_returns_ollama_gateway(self):
        gw = make_gateway(dry_run=False)
        assert isinstance(gw, OllamaGateway)

    def test_live_kwargs_passed_through(self):
        gw = make_gateway(dry_run=False, url="http://custom:11434/api/generate", model_name="llama3")
        assert isinstance(gw, OllamaGateway)
        assert gw.url == "http://custom:11434/api/generate"
        assert gw.model_name == "llama3"
