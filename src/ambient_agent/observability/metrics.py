"""In-memory accumulator for loop-quality telemetry.

CycleMetrics is created once per process run and updated after every cycle.
It provides the raw data consumed by the health formatter.

Tracked dimensions:
    cycles_total        Number of complete cycles executed this run.
    uptime_s            Seconds since the CycleMetrics instance was created.
    sources             Per-source ok/error counts, ok-rate, and avg latency.
    model               Model call ok/error counts, ok-rate, and avg latency.
    stages              Per-stage (ingest/analyze/persist/cycle) timing stats.
"""

import time
from collections import defaultdict


def _avg(values: list) -> "float | None":
    return round(sum(values) / len(values), 1) if values else None


def _max(values: list) -> "float | None":
    return round(max(values), 1) if values else None


def _rate(ok: int, total: int) -> "float | None":
    return round(ok / total, 3) if total > 0 else None


def _convergence_label(ok_rate: "float | None") -> str:
    """Return a simple convergence indicator label from an ok-rate."""
    if ok_rate is None:
        return "unknown"
    if ok_rate >= 0.9:
        return "healthy"
    if ok_rate >= 0.5:
        return "degraded"
    return "down"


class CycleMetrics:
    """Accumulates per-run telemetry across all agent cycles."""

    def __init__(self) -> None:
        self._started_at: float = time.time()
        self._cycles_total: int = 0

        self._source_ok: dict = defaultdict(int)
        self._source_error: dict = defaultdict(int)
        self._source_latencies: dict = defaultdict(list)

        self._model_ok: int = 0
        self._model_error: int = 0
        self._model_latencies: list = []

        self._stage_latencies: dict = defaultdict(list)

    # --- record helpers ---

    def record_cycle(self) -> None:
        """Call once at the end of every complete cycle."""
        self._cycles_total += 1

    def record_source(self, source: str, status: str, latency_ms: "float | None" = None) -> None:
        """Record ingest outcome for one source in a cycle."""
        if status == "ok":
            self._source_ok[source] += 1
        else:
            self._source_error[source] += 1
        if latency_ms is not None:
            self._source_latencies[source].append(latency_ms)

    def record_model(self, status: str, latency_ms: "float | None" = None) -> None:
        """Record one model/analysis call outcome."""
        if status == "ok":
            self._model_ok += 1
        else:
            self._model_error += 1
        if latency_ms is not None:
            self._model_latencies.append(latency_ms)

    def record_stage(self, stage: str, latency_ms: float) -> None:
        """Record timing for a named pipeline stage."""
        self._stage_latencies[stage].append(latency_ms)

    # --- reporting ---

    def get_summary(self) -> dict:
        """Return a serialisable summary dict suitable for health reporting."""
        uptime_s = time.time() - self._started_at

        all_sources = sorted(set(self._source_ok) | set(self._source_error))
        sources: dict = {}
        for src in all_sources:
            ok = self._source_ok.get(src, 0)
            err = self._source_error.get(src, 0)
            lats = self._source_latencies.get(src, [])
            ok_rate = _rate(ok, ok + err)
            sources[src] = {
                "ok": ok,
                "error": err,
                "ok_rate": ok_rate,
                "avg_latency_ms": _avg(lats),
                "convergence": _convergence_label(ok_rate),
            }

        model_total = self._model_ok + self._model_error
        model_ok_rate = _rate(self._model_ok, model_total)
        model: dict = {
            "ok": self._model_ok,
            "error": self._model_error,
            "ok_rate": model_ok_rate,
            "avg_latency_ms": _avg(self._model_latencies),
            "convergence": _convergence_label(model_ok_rate),
        }

        stages: dict = {}
        for stage, lats in sorted(self._stage_latencies.items()):
            stages[stage] = {
                "count": len(lats),
                "avg_ms": _avg(lats),
                "max_ms": _max(lats),
            }

        return {
            "cycles_total": self._cycles_total,
            "uptime_s": round(uptime_s, 1),
            "sources": sources,
            "model": model,
            "stages": stages,
        }
