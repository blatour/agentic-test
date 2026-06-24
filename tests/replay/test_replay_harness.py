"""Replay harness tests.

These tests load deterministic cycle fixtures and replay them through the
dry-run analysis path.  They validate that:
  1. Each fixture event conforms to the CanonicalEvent contract.
  2. The mock analysis produces the expected severity and recommendation.
  3. Failure-path events (fetch-error, parse-error) are handled gracefully.

Replay tests are deterministic: the same fixture always produces the same
analysis outcome, making them safe to use as regression gates.
"""

import json
import os
import pytest

from contracts.canonical_event import validate_canonical_event
import _samples_ambient_agent as agent


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixture(name: str) -> dict:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _all_fixture_names():
    return [f for f in os.listdir(FIXTURES_DIR) if f.endswith(".json")]


# ---------------------------------------------------------------------------
# Fixture contract conformance
# ---------------------------------------------------------------------------

class TestReplayFixtureConformance:
    @pytest.mark.parametrize("fixture_name", _all_fixture_names())
    def test_fixture_event_conforms_to_canonical_event_schema(self, fixture_name):
        """Every replay fixture must contain a valid CanonicalEvent envelope."""
        fixture = _load_fixture(fixture_name)
        validate_canonical_event(fixture["event"])

    @pytest.mark.parametrize("fixture_name", _all_fixture_names())
    def test_fixture_has_required_top_level_keys(self, fixture_name):
        fixture = _load_fixture(fixture_name)
        for key in ("description", "cycle_id", "source", "event", "expected_analysis"):
            assert key in fixture, f"Fixture '{fixture_name}' missing required key '{key}'"

    @pytest.mark.parametrize("fixture_name", _all_fixture_names())
    def test_expected_analysis_has_required_keys(self, fixture_name):
        fixture = _load_fixture(fixture_name)
        ea = fixture["expected_analysis"]
        assert "severity" in ea
        assert "recommendation_contains" in ea


# ---------------------------------------------------------------------------
# Replay: dry-run analysis against fixtures
# ---------------------------------------------------------------------------

class TestReplayDryRunAnalysis:
    def test_ok_cycle_produces_low_severity(self):
        fixture = _load_fixture("cycle_ok.json")
        raw_event = fixture["event"]["raw_event"]
        analysis = agent.generate_mock_analysis(raw_event)
        expected = fixture["expected_analysis"]
        assert expected["severity"] in analysis
        assert expected["recommendation_contains"] in analysis

    def test_fetch_error_cycle_produces_medium_severity(self):
        fixture = _load_fixture("cycle_fetch_error.json")
        raw_event = fixture["event"]["raw_event"]
        analysis = agent.generate_mock_analysis(raw_event)
        expected = fixture["expected_analysis"]
        assert expected["severity"] in analysis

    def test_model_error_cycle_analysis_contains_recommendation(self):
        fixture = _load_fixture("cycle_model_error.json")
        raw_event = fixture["event"]["raw_event"]
        analysis = agent.generate_mock_analysis(raw_event)
        assert "Recommendation" in analysis

    def test_security_event_produces_high_severity(self):
        fixture = _load_fixture("cycle_security_event.json")
        raw_event = fixture["event"]["raw_event"]
        analysis = agent.generate_mock_analysis(raw_event)
        expected = fixture["expected_analysis"]
        assert expected["severity"] in analysis
        assert expected["recommendation_contains"] in analysis


# ---------------------------------------------------------------------------
# Failure-path: network and model error categories
# ---------------------------------------------------------------------------

class TestReplayFailurePaths:
    def test_fetch_error_status_is_conformant(self):
        """Fetch-error events must still have a conformant CanonicalEvent envelope."""
        fixture = _load_fixture("cycle_fetch_error.json")
        validate_canonical_event(fixture["event"])

    def test_parse_error_status_is_conformant(self):
        """Parse-error events must still have a conformant CanonicalEvent envelope."""
        fixture = _load_fixture("cycle_model_error.json")
        validate_canonical_event(fixture["event"])

    def test_fetch_error_event_source_is_known(self):
        fixture = _load_fixture("cycle_fetch_error.json")
        from contracts.canonical_event import VALID_SOURCES
        assert fixture["event"]["source"] in VALID_SOURCES

    def test_analysis_is_deterministic_for_same_raw_event(self):
        """Running analysis twice on the same raw event yields identical output."""
        fixture = _load_fixture("cycle_security_event.json")
        raw = fixture["event"]["raw_event"]
        assert agent.generate_mock_analysis(raw) == agent.generate_mock_analysis(raw)
