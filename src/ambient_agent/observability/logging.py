"""Structured log emitter for the ambient agent pipeline.

Records are written as newline-delimited JSON to stderr so they remain
machine-parsable without disrupting normal stdout output.

Standard fields emitted on every record:
    ts          ISO-8601 UTC timestamp.
    event       Dot-namespaced event name (e.g. "cycle.start", "ingest.ok").
    cycle_id    UUID4 string that correlates all records in one loop cycle.
    source      Event-source name (e.g. "web-github", "web-usgs").
    stage       Pipeline stage name: ingest | analyze | persist | cycle.
    status      Outcome token: ok | error | fetch-error | parse-error | dry-run.
    latency_ms  Elapsed milliseconds for the named operation (float, 1 dp).
"""

import json
import sys
import time

_enabled: bool = False


def configure(*, enabled: bool) -> None:
    """Enable or disable structured JSON log emission globally."""
    global _enabled
    _enabled = enabled


def is_enabled() -> bool:
    return _enabled


def emit(
    event: str,
    *,
    cycle_id: "str | None" = None,
    source: "str | None" = None,
    stage: "str | None" = None,
    status: "str | None" = None,
    latency_ms: "float | None" = None,
    **extra,
) -> None:
    """Emit one structured log record to stderr.

    When structured logging is disabled this is a no-op, so callers do not
    need to guard every call site.
    """
    if not _enabled:
        return
    record: dict = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
    }
    if cycle_id is not None:
        record["cycle_id"] = cycle_id
    if source is not None:
        record["source"] = source
    if stage is not None:
        record["stage"] = stage
    if status is not None:
        record["status"] = status
    if latency_ms is not None:
        record["latency_ms"] = round(latency_ms, 1)
    record.update(extra)
    print(json.dumps(record, default=str), file=sys.stderr, flush=True)
