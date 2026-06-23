"""Unit tests for the observability.logging module."""

import io
import json
import sys

import pytest

from ambient_agent.observability.logging import configure, emit, is_enabled


@pytest.fixture(autouse=True)
def reset_logging():
    """Ensure structured logging is disabled before and after every test."""
    configure(enabled=False)
    yield
    configure(enabled=False)


def test_disabled_by_default():
    assert is_enabled() is False


def test_configure_enables_logging():
    configure(enabled=True)
    assert is_enabled() is True


def test_configure_disables_logging():
    configure(enabled=True)
    configure(enabled=False)
    assert is_enabled() is False


def test_emit_is_noop_when_disabled(capsys):
    configure(enabled=False)
    emit("test.event")
    captured = capsys.readouterr()
    assert captured.err == ""


def test_emit_writes_json_to_stderr(capsys):
    configure(enabled=True)
    emit("test.event")
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    record = json.loads(captured.err.strip())
    assert record["event"] == "test.event"
    assert "ts" in record


def test_emit_includes_optional_fields_when_provided(capsys):
    configure(enabled=True)
    emit(
        "ingest.ok",
        cycle_id="abc123",
        source="web-github",
        stage="ingest",
        status="ok",
        latency_ms=150.0,
    )
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert record["cycle_id"] == "abc123"
    assert record["source"] == "web-github"
    assert record["stage"] == "ingest"
    assert record["status"] == "ok"
    assert record["latency_ms"] == 150.0


def test_emit_omits_none_optional_fields(capsys):
    configure(enabled=True)
    emit("cycle.start")
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert "cycle_id" not in record
    assert "source" not in record
    assert "stage" not in record
    assert "status" not in record
    assert "latency_ms" not in record


def test_emit_rounds_latency_to_one_decimal(capsys):
    configure(enabled=True)
    emit("ingest.ok", latency_ms=123.456)
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert record["latency_ms"] == 123.5


def test_emit_passes_extra_kwargs(capsys):
    configure(enabled=True)
    emit("cycle.error", error="something went wrong", model="qwen3.5:4b")
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip())
    assert record["error"] == "something went wrong"
    assert record["model"] == "qwen3.5:4b"
