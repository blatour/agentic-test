"""Orchestration regression tests.

Covers:
- Stage order enforcement (ingest→compare→act→persist).
- ChangeSet always produced by compare stage (even when ingest fails).
- Loop stop conditions: --once, --max-cycles.
- --dry-run mode: no external calls.
- Per-stage StageResult emission.
"""
from __future__ import annotations

import sys
import os

# Make the src tree importable without installation.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch, call
import pytest

from ambient_agent.analysis.gateway import AnalysisGateway
from ambient_agent.runtime import Orchestrator
from ambient_agent.sources.registry import SourceRegistry
from ambient_agent.stages import ChangeSet, SourceEntry, StageResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(sources: dict[str, str]) -> SourceRegistry:
    """Build a registry whose adapters return fixed strings."""
    registry = SourceRegistry()
    for name, event in sources.items():
        mock_source = MagicMock()
        mock_source.name = name
        mock_source.fetch.return_value = event
        registry.register(mock_source)
    return registry


def _make_orchestrator(
    sources: dict[str, str],
    dry_run: bool = True,
    state: dict | None = None,
) -> Orchestrator:
    registry = _make_registry(sources)
    gateway = AnalysisGateway(dry_run=dry_run)
    return Orchestrator(
        source_registry=registry,
        analysis_gateway=gateway,
        source_names=list(sources.keys()),
        state=state or {},
        state_file="/tmp/test_state.json",
        log_file="/tmp/test_history.md",
    )


# ---------------------------------------------------------------------------
# Stage order
# ---------------------------------------------------------------------------


class TestStageOrder:
    def test_run_cycle_returns_four_stages(self):
        orch = _make_orchestrator({"simulated": "LOG test event"})
        with patch.object(orch, "_run_persist", wraps=orch._run_persist):
            results = orch.run_cycle({})
        assert len(results) == 4

    def test_stage_names_in_order(self):
        orch = _make_orchestrator({"simulated": "LOG test event"})
        results = orch.run_cycle({})
        assert [r.stage for r in results] == ["ingest", "compare", "act", "persist"]

    def test_stages_called_sequentially(self):
        """Confirm that each stage receives output from the previous one."""
        orch = _make_orchestrator({"simulated": "LOG test event"})
        call_order: list[str] = []

        orig_ingest = orch._run_ingest
        orig_compare = orch._run_compare
        orig_act = orch._run_act
        orig_persist = orch._run_persist

        def track(name, fn, *args, **kwargs):
            call_order.append(name)
            return fn(*args, **kwargs)

        orch._run_ingest = lambda *a, **kw: track("ingest", orig_ingest, *a, **kw)
        orch._run_compare = lambda *a, **kw: track("compare", orig_compare, *a, **kw)
        orch._run_act = lambda *a, **kw: track("act", orig_act, *a, **kw)
        orch._run_persist = lambda *a, **kw: track("persist", orig_persist, *a, **kw)

        orch.run_cycle({})
        assert call_order == ["ingest", "compare", "act", "persist"]


# ---------------------------------------------------------------------------
# ChangeSet always produced
# ---------------------------------------------------------------------------


class TestChangeSet:
    def test_compare_produces_changeset_on_success(self):
        orch = _make_orchestrator({"simulated": "LOG ok"})
        results = orch.run_cycle({})
        compare_result = next(r for r in results if r.stage == "compare")
        assert compare_result.status == "ok"
        assert isinstance(compare_result.data, ChangeSet)

    def test_compare_produces_changeset_even_when_ingest_errors(self):
        """ChangeSet is always present regardless of ingest outcome."""
        registry = SourceRegistry()
        bad_source = MagicMock()
        bad_source.name = "failing"
        bad_source.fetch.side_effect = RuntimeError("network down")
        registry.register(bad_source)

        orch = Orchestrator(
            source_registry=registry,
            analysis_gateway=AnalysisGateway(dry_run=True),
            source_names=["failing"],
            state={},
            state_file="/tmp/test_state.json",
            log_file="/tmp/test_history.md",
        )
        results = orch.run_cycle({})
        compare_result = next(r for r in results if r.stage == "compare")
        assert isinstance(compare_result.data, ChangeSet)

    def test_changeset_is_empty_when_all_entries_errored(self):
        registry = SourceRegistry()
        bad_source = MagicMock()
        bad_source.name = "failing"
        bad_source.fetch.side_effect = RuntimeError("gone")
        registry.register(bad_source)

        orch = Orchestrator(
            source_registry=registry,
            analysis_gateway=AnalysisGateway(dry_run=True),
            source_names=["failing"],
            state={},
            state_file="/tmp/test_state.json",
            log_file="/tmp/test_history.md",
        )
        results = orch.run_cycle({})
        changeset: ChangeSet = next(r for r in results if r.stage == "compare").data
        assert changeset.is_empty

    def test_changeset_not_empty_when_ok_entry_present(self):
        orch = _make_orchestrator({"simulated": "LOG ok event"})
        results = orch.run_cycle({})
        changeset: ChangeSet = next(r for r in results if r.stage == "compare").data
        assert not changeset.is_empty


# ---------------------------------------------------------------------------
# Per-stage StageResult emission
# ---------------------------------------------------------------------------


class TestStageResults:
    def test_all_stages_have_status(self):
        orch = _make_orchestrator({"simulated": "LOG event"})
        results = orch.run_cycle({})
        for r in results:
            assert r.status in ("ok", "error"), f"Unexpected status: {r.status}"

    def test_ingest_result_contains_entries(self):
        orch = _make_orchestrator({"simulated": "LOG event"})
        results = orch.run_cycle({})
        ingest_result = next(r for r in results if r.stage == "ingest")
        assert isinstance(ingest_result.data, list)
        assert len(ingest_result.data) == 1
        assert isinstance(ingest_result.data[0], SourceEntry)

    def test_act_result_contains_analysis(self):
        orch = _make_orchestrator({"simulated": "LOG security alert"})
        results = orch.run_cycle({})
        act_result = next(r for r in results if r.stage == "act")
        changeset: ChangeSet = act_result.data
        entry = changeset.entries[0]
        assert entry.analysis is not None
        assert "Severity" in entry.analysis


# ---------------------------------------------------------------------------
# Loop stop conditions
# ---------------------------------------------------------------------------


class TestLoopStopConditions:
    def test_once_flag_runs_exactly_one_cycle(self):
        orch = _make_orchestrator({"simulated": "LOG once"})
        cycle_count = 0
        orig_run_cycle = orch.run_cycle

        def counting_cycle(config):
            nonlocal cycle_count
            cycle_count += 1
            return orig_run_cycle(config)

        orch.run_cycle = counting_cycle
        with patch.object(orch, "_print_cycle_summary"):
            orch.run_loop({}, interval=0, once=True)

        assert cycle_count == 1

    def test_max_cycles_stops_loop(self):
        orch = _make_orchestrator({"simulated": "LOG event"})
        cycle_count = 0
        orig_run_cycle = orch.run_cycle

        def counting_cycle(config):
            nonlocal cycle_count
            cycle_count += 1
            return orig_run_cycle(config)

        orch.run_cycle = counting_cycle
        with patch.object(orch, "_print_cycle_summary"):
            orch.run_loop({}, interval=0, max_cycles=3)

        assert cycle_count == 3

    def test_max_cycles_one_equals_once(self):
        orch = _make_orchestrator({"simulated": "LOG event"})
        cycle_count = 0
        orig_run_cycle = orch.run_cycle

        def counting_cycle(config):
            nonlocal cycle_count
            cycle_count += 1
            return orig_run_cycle(config)

        orch.run_cycle = counting_cycle
        with patch.object(orch, "_print_cycle_summary"):
            orch.run_loop({}, interval=0, max_cycles=1)

        assert cycle_count == 1


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    def test_dry_run_does_not_call_ollama(self):
        orch = _make_orchestrator({"simulated": "LOG event"}, dry_run=True)
        with patch("ambient_agent.analysis.gateway._query_ollama") as mock_ollama:
            orch.run_cycle({})
        mock_ollama.assert_not_called()

    def test_dry_run_produces_analysis(self):
        orch = _make_orchestrator({"simulated": "Security alert detected"}, dry_run=True)
        results = orch.run_cycle({})
        act_result = next(r for r in results if r.stage == "act")
        changeset: ChangeSet = act_result.data
        assert changeset.entries[0].analysis is not None


# ---------------------------------------------------------------------------
# Multi-source (no source-specific branching in orchestrator)
# ---------------------------------------------------------------------------


class TestMultiSource:
    def test_multi_source_produces_one_entry_per_source(self):
        orch = _make_orchestrator(
            {
                "web-github": "WEB github event",
                "web-usgs": "WEB usgs event",
                "web-nasa": "WEB nasa event",
            }
        )
        results = orch.run_cycle({})
        ingest_result = next(r for r in results if r.stage == "ingest")
        assert len(ingest_result.data) == 3

    def test_partial_source_failure_still_processes_others(self):
        registry = SourceRegistry()
        good = MagicMock()
        good.name = "good-source"
        good.fetch.return_value = "LOG good event"
        registry.register(good)

        bad = MagicMock()
        bad.name = "bad-source"
        bad.fetch.side_effect = RuntimeError("gone")
        registry.register(bad)

        orch = Orchestrator(
            source_registry=registry,
            analysis_gateway=AnalysisGateway(dry_run=True),
            source_names=["good-source", "bad-source"],
            state={},
            state_file="/tmp/test_state.json",
            log_file="/tmp/test_history.md",
        )
        results = orch.run_cycle({})
        ingest_result = next(r for r in results if r.stage == "ingest")
        statuses = {e.source: e.status for e in ingest_result.data}
        assert statuses["good-source"] == "ok"
        assert statuses["bad-source"] == "error"
