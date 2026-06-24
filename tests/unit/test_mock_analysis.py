"""Unit tests for generate_mock_analysis.

Validates the dry-run analysis function that produces severity/summary/
recommendation output without calling an external model.
"""

import pytest

import _samples_ambient_agent as agent


class TestGenerateMockAnalysis:
    def test_security_event_returns_high_severity(self):
        result = agent.generate_mock_analysis("Security: Unrecognized MAC address detected.")
        assert "High" in result

    def test_unrecognized_keyword_returns_high(self):
        result = agent.generate_mock_analysis("LOG - Unrecognized device handshake on VLAN.")
        assert "High" in result

    def test_warning_keyword_returns_medium(self):
        result = agent.generate_mock_analysis("LOG - Node-02 high memory warning: 88% allocation.")
        assert "Medium" in result

    def test_spiked_keyword_returns_medium(self):
        result = agent.generate_mock_analysis("Container kube-proxy spiked to 92% memory.")
        assert "Medium" in result

    def test_routine_event_returns_low(self):
        result = agent.generate_mock_analysis("Deploy pipeline success: build #104 compiled.")
        assert "Low" in result

    def test_output_contains_summary(self):
        raw = "Deploy pipeline success."
        result = agent.generate_mock_analysis(raw)
        assert raw in result

    def test_output_contains_recommendation(self):
        result = agent.generate_mock_analysis("Routine home automation sync completed.")
        assert "Recommendation" in result

    def test_output_is_markdown_bullet_list(self):
        result = agent.generate_mock_analysis("Normal log entry.")
        lines = result.strip().splitlines()
        assert all(line.startswith("- ") for line in lines if line.strip())

    def test_case_insensitive_security_detection(self):
        result = agent.generate_mock_analysis("SECURITY ALERT: Something bad happened.")
        assert "High" in result
