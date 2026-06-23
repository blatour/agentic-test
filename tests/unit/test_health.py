"""Unit tests for the observability.health module."""

import pytest

from ambient_agent.observability.health import format_health_report


def _minimal_state(**kwargs):
    state = {
        "cycle_count": 0,
        "last_run": None,
        "last_cycle_mode": None,
        "last_cycle_checks": [],
    }
    state.update(kwargs)
    return state


def test_format_returns_string():
    report = format_health_report(_minimal_state())
    assert isinstance(report, str)


def test_report_contains_header():
    report = format_health_report(_minimal_state())
    assert "Ambient Agent Health Report" in report


def test_report_contains_cycle_count():
    report = format_health_report(_minimal_state(cycle_count=42))
    assert "42" in report


def test_report_shows_never_when_no_last_run():
    report = format_health_report(_minimal_state())
    assert "never" in report


def test_report_shows_last_run_timestamp():
    report = format_health_report(_minimal_state(last_run="2026-01-01 12:00:00"))
    assert "2026-01-01 12:00:00" in report


def test_report_shows_last_cycle_mode():
    report = format_health_report(_minimal_state(last_cycle_mode="web-all"))
    assert "web-all" in report


def test_report_shows_last_cycle_checks():
    checks = [
        {"source": "web-github", "status": "ok", "raw_event": "some event"},
    ]
    report = format_health_report(_minimal_state(last_cycle_checks=checks))
    assert "web-github" in report
    assert "ok" in report


def test_report_truncates_long_raw_event():
    long_event = "x" * 200
    checks = [{"source": "web-usgs", "status": "ok", "raw_event": long_event}]
    report = format_health_report(_minimal_state(last_cycle_checks=checks))
    assert "..." in report


def test_report_shows_model_status_when_present():
    state = _minimal_state(last_model_status={"status": "ok", "latency_ms": 320.0, "model": "qwen3.5:4b"})
    report = format_health_report(state)
    assert "qwen3.5:4b" in report
    assert "320" in report


def test_report_excludes_model_section_when_absent():
    report = format_health_report(_minimal_state())
    assert "Model Status" not in report


def test_report_excludes_runtime_telemetry_when_no_metrics():
    report = format_health_report(_minimal_state())
    assert "Runtime Telemetry" not in report


def test_report_includes_runtime_telemetry_when_metrics_provided():
    metrics_summary = {
        "cycles_total": 5,
        "uptime_s": 300.0,
        "model": {
            "ok": 5,
            "error": 0,
            "ok_rate": 1.0,
            "avg_latency_ms": 400.0,
            "convergence": "healthy",
        },
        "sources": {},
        "stages": {},
    }
    report = format_health_report(_minimal_state(), metrics_summary=metrics_summary)
    assert "Runtime Telemetry" in report
    assert "5" in report


def test_report_shows_source_health_when_metrics_have_sources():
    metrics_summary = {
        "cycles_total": 3,
        "uptime_s": 90.0,
        "model": {"ok": 3, "error": 0, "ok_rate": 1.0, "avg_latency_ms": None, "convergence": "healthy"},
        "sources": {
            "web-github": {
                "ok": 3,
                "error": 0,
                "ok_rate": 1.0,
                "avg_latency_ms": 120.0,
                "convergence": "healthy",
            }
        },
        "stages": {},
    }
    report = format_health_report(_minimal_state(), metrics_summary=metrics_summary)
    assert "Source Health" in report
    assert "web-github" in report
    assert "healthy" in report


def test_report_shows_stage_timing_when_metrics_have_stages():
    metrics_summary = {
        "cycles_total": 2,
        "uptime_s": 60.0,
        "model": {"ok": 2, "error": 0, "ok_rate": 1.0, "avg_latency_ms": None, "convergence": "healthy"},
        "sources": {},
        "stages": {
            "ingest": {"count": 2, "avg_ms": 80.0, "max_ms": 100.0},
        },
    }
    report = format_health_report(_minimal_state(), metrics_summary=metrics_summary)
    assert "Stage Timing" in report
    assert "ingest" in report
