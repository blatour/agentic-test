"""Health report formatter for the ambient agent.

format_health_report() accepts the persisted state dict (loaded from the
JSON state file) and an optional CycleMetrics summary dict produced by
CycleMetrics.get_summary().  When the metrics summary is absent (e.g. when
reading health from a cold-start or via the --health CLI flag) only the
lifetime state-derived section is shown.

Acceptance criteria addressed:
  - Health output includes cycle, source, and model status.
  - Health output includes loop stage metrics and convergence indicators.
"""

import time


def _ok_rate_str(rate: "float | None") -> str:
    return f"{rate:.1%}" if rate is not None else "n/a"


def _latency_str(ms: "float | None") -> str:
    return f"{ms:.0f}ms" if ms is not None else "n/a"


def format_health_report(
    state: dict,
    metrics_summary: "dict | None" = None,
) -> str:
    """Return a human-readable multi-section health report."""
    lines = [
        "=== Ambient Agent Health Report ===",
        f"Generated:  {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # --- Cycle status (from persistent state) ---
    lines.append("--- Cycle Status ---")
    lines.append(f"Lifetime cycles completed : {state.get('cycle_count', 0)}")
    lines.append(f"Last run                  : {state.get('last_run') or 'never'}")
    lines.append(f"Last cycle mode           : {state.get('last_cycle_mode') or 'unknown'}")

    # --- Source status from last persisted cycle ---
    last_checks = state.get("last_cycle_checks", [])
    if last_checks:
        lines.append("")
        lines.append("--- Last Cycle Source Status ---")
        for entry in last_checks:
            src = entry.get("source", "unknown")
            status = entry.get("status", "unknown")
            raw = entry.get("raw_event", "")
            compact = raw if len(raw) <= 100 else f"{raw[:97]}..."
            lines.append(f"  {src:<20} {status:<15} {compact}")

    # --- Model status from last cycle (stored in state if available) ---
    model_status = state.get("last_model_status")
    if model_status:
        lines.append("")
        lines.append("--- Model Status ---")
        lines.append(f"Last model call status    : {model_status.get('status', 'unknown')}")
        lat = model_status.get("latency_ms")
        lines.append(f"Last model call latency   : {_latency_str(lat)}")
        lines.append(f"Model                     : {model_status.get('model', 'unknown')}")

    # --- Runtime telemetry (only available when process is live) ---
    if metrics_summary:
        lines.append("")
        lines.append("--- Runtime Telemetry ---")
        lines.append(f"Cycles this run  : {metrics_summary.get('cycles_total', 0)}")
        uptime = metrics_summary.get("uptime_s", 0)
        lines.append(f"Uptime           : {uptime:.1f}s")

        model = metrics_summary.get("model", {})
        lines.append(
            f"Model calls      : ok={model.get('ok', 0)}  error={model.get('error', 0)}"
            f"  ok_rate={_ok_rate_str(model.get('ok_rate'))}"
            f"  avg_latency={_latency_str(model.get('avg_latency_ms'))}"
            f"  convergence={model.get('convergence', 'unknown')}"
        )

        sources = metrics_summary.get("sources", {})
        if sources:
            lines.append("")
            lines.append("--- Source Health (this run) ---")
            for src, stats in sources.items():
                lines.append(
                    f"  {src:<20}"
                    f" ok={stats.get('ok', 0):<4}"
                    f" error={stats.get('error', 0):<4}"
                    f" ok_rate={_ok_rate_str(stats.get('ok_rate')):<8}"
                    f" avg_latency={_latency_str(stats.get('avg_latency_ms')):<8}"
                    f" convergence={stats.get('convergence', 'unknown')}"
                )

        stages = metrics_summary.get("stages", {})
        if stages:
            lines.append("")
            lines.append("--- Stage Timing (this run) ---")
            for stage, timing in stages.items():
                lines.append(
                    f"  {stage:<12}"
                    f" count={timing.get('count', 0):<5}"
                    f" avg={_latency_str(timing.get('avg_ms')):<8}"
                    f" max={_latency_str(timing.get('max_ms'))}"
                )

    lines.append("")
    lines.append("===================================")
    return "\n".join(lines)
