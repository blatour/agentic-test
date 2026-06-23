"""Observability package for the ambient agent.

Exports:
    configure_logging   Enable/disable structured JSON log emission.
    emit_log            Emit one structured log record.
    CycleMetrics        In-memory loop-quality telemetry accumulator.
    format_health_report  Format a human-readable health report.
"""

from .logging import configure as configure_logging
from .logging import emit as emit_log
from .metrics import CycleMetrics
from .health import format_health_report

__all__ = [
    "configure_logging",
    "emit_log",
    "CycleMetrics",
    "format_health_report",
]
