"""Core runtime orchestrator.

Enforces the ingest → compare → act → persist stage order every cycle and
emits an explicit StageResult for each stage.  No source-specific branching
lives here; sources are resolved via the SourceRegistry at startup.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List

import requests

from .analysis.gateway import AnalysisGateway
from .persistence.state import (
    append_multi_source_history,
    append_to_history,
    save_agent_state,
)
from .sources.adapters import get_last_seen_ids
from .sources.registry import SourceRegistry
from .stages import ChangeSet, SourceEntry, StageResult


def _new_cycle_id() -> str:
    return str(uuid.uuid4())[:8]


class Orchestrator:
    """Executes the ingest→compare→act→persist loop.

    Args:
        source_registry: Registry of all wired source adapters.
        analysis_gateway: Gateway for LLM or mock analysis.
        source_names: Ordered list of source names to poll each cycle.
        state: Mutable agent-state dict (mutated in-place each cycle).
        state_file: Path to the JSON state persistence file.
        log_file: Path to the Markdown history log file.
    """

    def __init__(
        self,
        source_registry: SourceRegistry,
        analysis_gateway: AnalysisGateway,
        source_names: List[str],
        state: Dict[str, Any],
        state_file: str,
        log_file: str,
    ) -> None:
        self.source_registry = source_registry
        self.analysis_gateway = analysis_gateway
        self.source_names = source_names
        self.state = state
        self.state_file = state_file
        self.log_file = log_file

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(self, config: Dict[str, Any]) -> List[StageResult]:
        """Execute one full ingest→compare→act→persist cycle.

        Returns:
            A list of four StageResult objects, one per stage, in order.
            The compare stage always produces a ChangeSet even when empty.
        """
        cycle_id = _new_cycle_id()
        results: List[StageResult] = []

        # Stage 1 — Ingest
        ingest_result = self._run_ingest(config, cycle_id)
        results.append(ingest_result)

        # Stage 2 — Compare (always runs, always produces a ChangeSet)
        compare_result = self._run_compare(ingest_result, cycle_id)
        results.append(compare_result)

        # Stage 3 — Act
        act_result = self._run_act(compare_result)
        results.append(act_result)

        # Stage 4 — Persist
        persist_result = self._run_persist(act_result, config)
        results.append(persist_result)

        return results

    def run_loop(
        self,
        config: Dict[str, Any],
        interval: int,
        once: bool = False,
        max_cycles: int | None = None,
    ) -> None:
        """Run cycles in a loop until a stop condition is met."""
        cycles_completed = 0
        try:
            while True:
                stage_results = self.run_cycle(config)
                self._print_cycle_summary(stage_results)
                cycles_completed += 1

                if once:
                    break
                if max_cycles is not None and cycles_completed >= max_cycles:
                    break

                time.sleep(max(1, interval))
        except KeyboardInterrupt:
            print("\nAmbient agent shutting down cleanly. Goodbye.")

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _run_ingest(
        self, config: Dict[str, Any], cycle_id: str
    ) -> StageResult:
        """Fetch raw events from all registered sources without branching."""
        entries: List[SourceEntry] = []
        overall_status = "ok"

        for source_name in self.source_names:
            try:
                raw_event = self.source_registry.fetch(source_name, config)
                entries.append(
                    SourceEntry(source=source_name, status="ok", raw_event=raw_event)
                )
            except requests.RequestException as exc:
                entries.append(
                    SourceEntry(
                        source=source_name,
                        status="fetch-error",
                        raw_event=f"Fetch failed for {source_name}: {exc}",
                    )
                )
                overall_status = "error"
            except ValueError as exc:
                entries.append(
                    SourceEntry(
                        source=source_name,
                        status="parse-error",
                        raw_event=f"Parse failure for {source_name}: {exc}",
                    )
                )
                overall_status = "error"
            except Exception as exc:  # noqa: BLE001
                entries.append(
                    SourceEntry(
                        source=source_name,
                        status="error",
                        raw_event=f"Unexpected failure for {source_name}: {exc}",
                    )
                )
                overall_status = "error"

        return StageResult(stage="ingest", status=overall_status, data=entries)

    def _run_compare(
        self, ingest_result: StageResult, cycle_id: str
    ) -> StageResult:
        """Wrap ingest entries into a ChangeSet.

        Always produces a ChangeSet—even when ingest failed—so downstream
        stages always have a well-typed input.
        """
        entries: List[SourceEntry] = ingest_result.data or []
        changeset = ChangeSet(cycle_id=cycle_id, entries=entries)
        return StageResult(stage="compare", status="ok", data=changeset)

    def _run_act(self, compare_result: StageResult) -> StageResult:
        """Run analysis on each successfully-ingested entry in the ChangeSet."""
        changeset: ChangeSet = compare_result.data
        overall_status = "ok"

        for entry in changeset.entries:
            if entry.status != "ok":
                entry.analysis = (
                    "- **Severity:** Medium\n"
                    "- **Summary:** Source processing failed this cycle.\n"
                    "- **Recommendation:** Review traceback and keep agent running for next interval."
                )
                continue
            try:
                entry.analysis = self.analysis_gateway.analyze(entry.raw_event)
            except Exception as exc:  # noqa: BLE001
                entry.analysis = f"Analysis failed: {exc}"
                overall_status = "error"

        return StageResult(stage="act", status=overall_status, data=changeset)

    def _run_persist(
        self, act_result: StageResult, config: Dict[str, Any]
    ) -> StageResult:
        """Save cycle results to the history log and state file."""
        changeset: ChangeSet = act_result.data

        try:
            entries = changeset.entries
            if len(entries) == 1:
                entry = entries[0]
                if entry.status == "ok" and entry.analysis:
                    append_to_history(self.log_file, entry.raw_event, entry.analysis)
                    print(
                        f"[{time.strftime('%H:%M:%S')}] Cycle complete. "
                        f"Analysis written to {self.log_file}."
                    )
            elif len(entries) > 1:
                row_list = [
                    {
                        "source": e.source,
                        "status": e.status,
                        "raw_event": e.raw_event,
                        "analysis": e.analysis or "",
                    }
                    for e in entries
                ]
                append_multi_source_history(self.log_file, row_list)
                print(
                    f"[{time.strftime('%H:%M:%S')}] Multi-source cycle complete. "
                    f"Summary written to {self.log_file}."
                )

            # Update mutable state dict
            self.state["last_seen_event_ids"] = get_last_seen_ids()
            self.state["cycle_count"] = self.state.get("cycle_count", 0) + 1
            self.state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.state["last_cycle_mode"] = (
                "web-all" if len(self.source_names) > 1 else self.source_names[0]
            )
            self.state["last_cycle_checks"] = [
                {"source": e.source, "status": e.status, "raw_event": e.raw_event}
                for e in entries
            ]
            save_agent_state(self.state_file, self.state)
        except Exception as exc:  # noqa: BLE001
            return StageResult(stage="persist", status="error", error=str(exc))

        return StageResult(stage="persist", status="ok")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print_cycle_summary(self, results: List[StageResult]) -> None:
        """Print a one-line per-stage outcome summary."""
        summary = "  ".join(
            f"[{r.stage}:{r.status}]" for r in results
        )
        print(f"[{time.strftime('%H:%M:%S')}] Cycle stages — {summary}")
