"""Unit tests for the observability.metrics module."""

import time

import pytest

from ambient_agent.observability.metrics import CycleMetrics


def test_initial_state():
    m = CycleMetrics()
    summary = m.get_summary()
    assert summary["cycles_total"] == 0
    assert summary["sources"] == {}
    assert summary["model"]["ok"] == 0
    assert summary["model"]["error"] == 0
    assert summary["model"]["ok_rate"] is None
    assert summary["stages"] == {}


def test_record_cycle_increments_count():
    m = CycleMetrics()
    m.record_cycle()
    m.record_cycle()
    assert m.get_summary()["cycles_total"] == 2


def test_record_source_ok():
    m = CycleMetrics()
    m.record_source("web-github", "ok", 100.0)
    summary = m.get_summary()
    src = summary["sources"]["web-github"]
    assert src["ok"] == 1
    assert src["error"] == 0
    assert src["ok_rate"] == 1.0
    assert src["avg_latency_ms"] == 100.0


def test_record_source_error():
    m = CycleMetrics()
    m.record_source("web-usgs", "fetch-error")
    summary = m.get_summary()
    src = summary["sources"]["web-usgs"]
    assert src["ok"] == 0
    assert src["error"] == 1
    assert src["ok_rate"] == 0.0
    assert src["avg_latency_ms"] is None


def test_record_source_mixed_rates():
    m = CycleMetrics()
    m.record_source("web-github", "ok", 50.0)
    m.record_source("web-github", "ok", 150.0)
    m.record_source("web-github", "fetch-error")
    summary = m.get_summary()
    src = summary["sources"]["web-github"]
    assert src["ok"] == 2
    assert src["error"] == 1
    assert abs(src["ok_rate"] - 2 / 3) < 0.001
    assert src["avg_latency_ms"] == 100.0


def test_record_model_ok():
    m = CycleMetrics()
    m.record_model("ok", 200.0)
    model = m.get_summary()["model"]
    assert model["ok"] == 1
    assert model["error"] == 0
    assert model["ok_rate"] == 1.0
    assert model["avg_latency_ms"] == 200.0


def test_record_model_error():
    m = CycleMetrics()
    m.record_model("error")
    model = m.get_summary()["model"]
    assert model["ok"] == 0
    assert model["error"] == 1
    assert model["ok_rate"] == 0.0


def test_record_stage_timing():
    m = CycleMetrics()
    m.record_stage("ingest", 100.0)
    m.record_stage("ingest", 200.0)
    m.record_stage("analyze", 500.0)
    stages = m.get_summary()["stages"]
    assert stages["ingest"]["count"] == 2
    assert stages["ingest"]["avg_ms"] == 150.0
    assert stages["ingest"]["max_ms"] == 200.0
    assert stages["analyze"]["count"] == 1
    assert stages["analyze"]["avg_ms"] == 500.0


def test_uptime_increases():
    m = CycleMetrics()
    time.sleep(0.05)
    assert m.get_summary()["uptime_s"] > 0.0


def test_convergence_healthy():
    m = CycleMetrics()
    for _ in range(9):
        m.record_source("web-github", "ok")
    m.record_source("web-github", "error")
    src = m.get_summary()["sources"]["web-github"]
    assert src["convergence"] == "healthy"


def test_convergence_degraded():
    m = CycleMetrics()
    m.record_source("web-github", "ok")
    m.record_source("web-github", "error")
    src = m.get_summary()["sources"]["web-github"]
    assert src["convergence"] == "degraded"


def test_convergence_down():
    m = CycleMetrics()
    for _ in range(3):
        m.record_source("web-github", "error")
    src = m.get_summary()["sources"]["web-github"]
    assert src["convergence"] == "down"


def test_convergence_unknown_when_no_data():
    m = CycleMetrics()
    model = m.get_summary()["model"]
    assert model["convergence"] == "unknown"
