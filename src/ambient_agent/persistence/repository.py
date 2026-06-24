"""Typed data-access layer for the ambient agent persistence schema.

Usage::

    from ambient_agent.persistence import Repository, Cycle, Event

    repo = Repository("ambient.db")
    cycle = Cycle.new(mode="web-all")
    repo.save_cycle(cycle)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    """Return a compact random UUID string."""
    return uuid.uuid4().hex


def _deterministic_id(*parts: Any) -> str:
    """Return a 32-hex-char deterministic ID derived from *parts*.

    Used where the same logical entity must map to the same row key so that
    duplicate inserts are rejected by the UNIQUE constraint rather than
    producing orphaned rows.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _now_iso() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Entity dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Cycle:
    """One agent wake-cycle record."""

    id: str
    started_at: str
    status: str = "running"
    mode: Optional[str] = None
    ended_at: Optional[str] = None
    source_count: int = 0
    ok_count: int = 0
    error_count: int = 0
    latency_ms: Optional[int] = None

    @classmethod
    def new(cls, mode: Optional[str] = None) -> "Cycle":
        return cls(id=_uuid(), started_at=_now_iso(), mode=mode)


@dataclass
class Event:
    """A single canonical event fetched from one source."""

    id: str
    cycle_id: str
    source: str
    raw_text: str
    fetched_at: str
    status: str = "ok"
    source_event_id: Optional[str] = None
    latency_ms: Optional[int] = None

    @classmethod
    def new(
        cls,
        cycle_id: str,
        source: str,
        raw_text: str,
        source_event_id: Optional[str] = None,
        status: str = "ok",
        latency_ms: Optional[int] = None,
    ) -> "Event":
        # Deterministic ID when source_event_id is known; random otherwise.
        if source_event_id:
            eid = _deterministic_id(source, source_event_id)
        else:
            eid = _uuid()
        return cls(
            id=eid,
            cycle_id=cycle_id,
            source=source,
            raw_text=raw_text,
            fetched_at=_now_iso(),
            status=status,
            source_event_id=source_event_id,
            latency_ms=latency_ms,
        )


@dataclass
class Analysis:
    """Model analysis output for an event."""

    id: str
    cycle_id: str
    analyzed_at: str
    event_id: Optional[str] = None
    model: Optional[str] = None
    severity: Optional[str] = None
    summary: Optional[str] = None
    recommendation: Optional[str] = None
    raw_response: Optional[str] = None
    is_mock: bool = False
    latency_ms: Optional[int] = None

    @classmethod
    def new(
        cls,
        cycle_id: str,
        event_id: Optional[str] = None,
        model: Optional[str] = None,
        severity: Optional[str] = None,
        summary: Optional[str] = None,
        recommendation: Optional[str] = None,
        raw_response: Optional[str] = None,
        is_mock: bool = False,
        latency_ms: Optional[int] = None,
    ) -> "Analysis":
        return cls(
            id=_uuid(),
            cycle_id=cycle_id,
            analyzed_at=_now_iso(),
            event_id=event_id,
            model=model,
            severity=severity,
            summary=summary,
            recommendation=recommendation,
            raw_response=raw_response,
            is_mock=is_mock,
            latency_ms=latency_ms,
        )


@dataclass
class Action:
    """A decision artifact: notification, alert, or follow-up task."""

    id: str
    cycle_id: str
    action_type: str
    payload: dict
    analysis_id: Optional[str] = None
    status: str = "pending"
    dispatched_at: Optional[str] = None

    @classmethod
    def new(
        cls,
        cycle_id: str,
        action_type: str,
        payload: dict,
        analysis_id: Optional[str] = None,
    ) -> "Action":
        return cls(
            id=_uuid(),
            cycle_id=cycle_id,
            action_type=action_type,
            payload=payload,
            analysis_id=analysis_id,
        )


@dataclass
class KnowledgeState:
    """Current projected knowledge state for one (source, key) pair.

    The compare step reads this to diff against incoming events and writes
    the updated snapshot back via :meth:`Repository.upsert_knowledge_state`.
    """

    id: str
    cycle_id: str
    source: str
    key: str
    value: dict
    version: int = 1

    @classmethod
    def new(
        cls,
        cycle_id: str,
        source: str,
        key: str,
        value: dict,
        version: int = 1,
    ) -> "KnowledgeState":
        ks_id = _deterministic_id(source, key)
        return cls(
            id=ks_id,
            cycle_id=cycle_id,
            source=source,
            key=key,
            value=value,
            version=version,
        )


@dataclass
class ChangeSet:
    """A single diff entry produced by the compare step."""

    id: str
    cycle_id: str
    source: str
    key: str
    change_type: str  # added | removed | updated | unchanged
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None

    @classmethod
    def new(
        cls,
        cycle_id: str,
        source: str,
        key: str,
        change_type: str,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
    ) -> "ChangeSet":
        cs_id = _deterministic_id(cycle_id, source, key, change_type)
        return cls(
            id=cs_id,
            cycle_id=cycle_id,
            source=source,
            key=key,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
        )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class Repository:
    """SQLite-backed data-access object for all persistence entities.

    The constructor opens (or creates) the database at *db_path* and enables
    WAL mode and foreign-key enforcement.  It does **not** run schema
    migrations automatically; call :func:`ambient_agent.persistence.bootstrap`
    once during application startup to apply the schema.

    All ``save_*`` methods use ``INSERT OR IGNORE`` so that re-inserting an
    entity with the same primary key is a no-op (idempotent).
    :meth:`upsert_knowledge_state` is the exception — it replaces the
    existing row so the compare step always works with the latest snapshot.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    def __enter__(self) -> "Repository":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Cycle
    # ------------------------------------------------------------------

    def save_cycle(self, cycle: Cycle) -> None:
        """Persist *cycle*; silently no-ops if the ID already exists."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO cycles
                (id, started_at, ended_at, status, mode,
                 source_count, ok_count, error_count, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cycle.id,
                cycle.started_at,
                cycle.ended_at,
                cycle.status,
                cycle.mode,
                cycle.source_count,
                cycle.ok_count,
                cycle.error_count,
                cycle.latency_ms,
            ),
        )
        self._conn.commit()

    def update_cycle(self, cycle: Cycle) -> None:
        """Update mutable fields on an existing cycle row."""
        self._conn.execute(
            """
            UPDATE cycles SET
                ended_at     = ?,
                status       = ?,
                source_count = ?,
                ok_count     = ?,
                error_count  = ?,
                latency_ms   = ?
            WHERE id = ?
            """,
            (
                cycle.ended_at,
                cycle.status,
                cycle.source_count,
                cycle.ok_count,
                cycle.error_count,
                cycle.latency_ms,
                cycle.id,
            ),
        )
        self._conn.commit()

    def get_cycle(self, cycle_id: str) -> Optional[Cycle]:
        """Return the :class:`Cycle` with *cycle_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT * FROM cycles WHERE id = ?", (cycle_id,)
        ).fetchone()
        if row is None:
            return None
        return Cycle(
            id=row["id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            status=row["status"],
            mode=row["mode"],
            source_count=row["source_count"],
            ok_count=row["ok_count"],
            error_count=row["error_count"],
            latency_ms=row["latency_ms"],
        )

    def list_cycles(self, limit: int = 100) -> list[Cycle]:
        """Return up to *limit* cycles ordered by started_at descending."""
        rows = self._conn.execute(
            "SELECT * FROM cycles ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            Cycle(
                id=r["id"],
                started_at=r["started_at"],
                ended_at=r["ended_at"],
                status=r["status"],
                mode=r["mode"],
                source_count=r["source_count"],
                ok_count=r["ok_count"],
                error_count=r["error_count"],
                latency_ms=r["latency_ms"],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Event
    # ------------------------------------------------------------------

    def save_event(self, event: Event) -> None:
        """Persist *event*; silently no-ops on duplicate (source, source_event_id)."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO events
                (id, cycle_id, source, source_event_id,
                 raw_text, status, fetched_at, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.cycle_id,
                event.source,
                event.source_event_id,
                event.raw_text,
                event.status,
                event.fetched_at,
                event.latency_ms,
            ),
        )
        self._conn.commit()

    def get_event(self, event_id: str) -> Optional[Event]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def list_events_for_cycle(self, cycle_id: str) -> list[Event]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE cycle_id = ? ORDER BY fetched_at",
            (cycle_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def list_failed_events(self, limit: int = 100) -> list[Event]:
        """Return recent non-ok events for failure triage."""
        rows = self._conn.execute(
            """
            SELECT * FROM events
            WHERE status != 'ok'
            ORDER BY fetched_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            cycle_id=row["cycle_id"],
            source=row["source"],
            raw_text=row["raw_text"],
            fetched_at=row["fetched_at"],
            status=row["status"],
            source_event_id=row["source_event_id"],
            latency_ms=row["latency_ms"],
        )

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def save_analysis(self, analysis: Analysis) -> None:
        """Persist *analysis*; silently no-ops if the ID already exists."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO analyses
                (id, cycle_id, event_id, model, severity, summary,
                 recommendation, raw_response, is_mock, analyzed_at, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.id,
                analysis.cycle_id,
                analysis.event_id,
                analysis.model,
                analysis.severity,
                analysis.summary,
                analysis.recommendation,
                analysis.raw_response,
                int(analysis.is_mock),
                analysis.analyzed_at,
                analysis.latency_ms,
            ),
        )
        self._conn.commit()

    def get_analysis(self, analysis_id: str) -> Optional[Analysis]:
        row = self._conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (analysis_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_analysis(row)

    def list_analyses_for_cycle(self, cycle_id: str) -> list[Analysis]:
        rows = self._conn.execute(
            "SELECT * FROM analyses WHERE cycle_id = ? ORDER BY analyzed_at",
            (cycle_id,),
        ).fetchall()
        return [self._row_to_analysis(r) for r in rows]

    @staticmethod
    def _row_to_analysis(row: sqlite3.Row) -> Analysis:
        return Analysis(
            id=row["id"],
            cycle_id=row["cycle_id"],
            analyzed_at=row["analyzed_at"],
            event_id=row["event_id"],
            model=row["model"],
            severity=row["severity"],
            summary=row["summary"],
            recommendation=row["recommendation"],
            raw_response=row["raw_response"],
            is_mock=bool(row["is_mock"]),
            latency_ms=row["latency_ms"],
        )

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------

    def save_action(self, action: Action) -> None:
        """Persist *action*; silently no-ops if the ID already exists."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO actions
                (id, cycle_id, analysis_id, action_type,
                 payload, status, dispatched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action.id,
                action.cycle_id,
                action.analysis_id,
                action.action_type,
                json.dumps(action.payload),
                action.status,
                action.dispatched_at,
            ),
        )
        self._conn.commit()

    def update_action_status(
        self, action_id: str, status: str, dispatched_at: Optional[str] = None
    ) -> None:
        """Update the dispatch status of an existing action."""
        self._conn.execute(
            "UPDATE actions SET status = ?, dispatched_at = ? WHERE id = ?",
            (status, dispatched_at, action_id),
        )
        self._conn.commit()

    def get_action(self, action_id: str) -> Optional[Action]:
        row = self._conn.execute(
            "SELECT * FROM actions WHERE id = ?", (action_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_action(row)

    def list_actions_for_cycle(self, cycle_id: str) -> list[Action]:
        rows = self._conn.execute(
            "SELECT * FROM actions WHERE cycle_id = ? ORDER BY created_at",
            (cycle_id,),
        ).fetchall()
        return [self._row_to_action(r) for r in rows]

    @staticmethod
    def _row_to_action(row: sqlite3.Row) -> Action:
        return Action(
            id=row["id"],
            cycle_id=row["cycle_id"],
            action_type=row["action_type"],
            payload=json.loads(row["payload"]),
            analysis_id=row["analysis_id"],
            status=row["status"],
            dispatched_at=row["dispatched_at"],
        )

    # ------------------------------------------------------------------
    # KnowledgeState
    # ------------------------------------------------------------------

    def upsert_knowledge_state(self, ks: KnowledgeState) -> None:
        """Insert or replace the knowledge state for (source, key).

        This is an upsert — the compare step calls this each cycle to keep
        the snapshot current.  ``version`` is incremented on conflict so
        callers can detect how many times a key has been updated.
        """
        self._conn.execute(
            """
            INSERT INTO knowledge_state
                (id, cycle_id, source, key, value, version, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, key) DO UPDATE SET
                id         = excluded.id,
                cycle_id   = excluded.cycle_id,
                value      = excluded.value,
                version    = knowledge_state.version + 1,
                updated_at = excluded.updated_at
            """,
            (
                ks.id,
                ks.cycle_id,
                ks.source,
                ks.key,
                json.dumps(ks.value),
                ks.version,
                _now_iso(),
            ),
        )
        self._conn.commit()

    def get_knowledge_state(self, source: str, key: str) -> Optional[KnowledgeState]:
        """Return the current projected state for *(source, key)*."""
        row = self._conn.execute(
            "SELECT * FROM knowledge_state WHERE source = ? AND key = ?",
            (source, key),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_ks(row)

    def list_knowledge_state(self, source: Optional[str] = None) -> list[KnowledgeState]:
        """Return all knowledge-state rows, optionally filtered by *source*."""
        if source is not None:
            rows = self._conn.execute(
                "SELECT * FROM knowledge_state WHERE source = ? ORDER BY key",
                (source,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM knowledge_state ORDER BY source, key"
            ).fetchall()
        return [self._row_to_ks(r) for r in rows]

    @staticmethod
    def _row_to_ks(row: sqlite3.Row) -> KnowledgeState:
        return KnowledgeState(
            id=row["id"],
            cycle_id=row["cycle_id"],
            source=row["source"],
            key=row["key"],
            value=json.loads(row["value"]),
            version=row["version"],
        )

    # ------------------------------------------------------------------
    # ChangeSet
    # ------------------------------------------------------------------

    def save_changeset(self, cs: ChangeSet) -> None:
        """Persist a :class:`ChangeSet` entry; silently no-ops on duplicate ID."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO changesets
                (id, cycle_id, source, key, change_type, old_value, new_value)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cs.id,
                cs.cycle_id,
                cs.source,
                cs.key,
                cs.change_type,
                json.dumps(cs.old_value) if cs.old_value is not None else None,
                json.dumps(cs.new_value) if cs.new_value is not None else None,
            ),
        )
        self._conn.commit()

    def list_changesets_for_cycle(self, cycle_id: str) -> list[ChangeSet]:
        """Return all changeset entries for *cycle_id*."""
        rows = self._conn.execute(
            "SELECT * FROM changesets WHERE cycle_id = ? ORDER BY source, key",
            (cycle_id,),
        ).fetchall()
        return [self._row_to_cs(r) for r in rows]

    @staticmethod
    def _row_to_cs(row: sqlite3.Row) -> ChangeSet:
        return ChangeSet(
            id=row["id"],
            cycle_id=row["cycle_id"],
            source=row["source"],
            key=row["key"],
            change_type=row["change_type"],
            old_value=json.loads(row["old_value"]) if row["old_value"] else None,
            new_value=json.loads(row["new_value"]) if row["new_value"] else None,
        )

    # ------------------------------------------------------------------
    # Projection helpers for compare logic
    # ------------------------------------------------------------------

    def load_knowledge_projection(self, source: str) -> dict[str, dict]:
        """Return a {key: value} snapshot for *source*.

        This is the primary read path for the compare step: load the current
        projection, diff against incoming events, produce :class:`ChangeSet`
        entries, then call :meth:`upsert_knowledge_state` with the new values.
        """
        states = self.list_knowledge_state(source=source)
        return {ks.key: ks.value for ks in states}

    def cycle_failure_summary(self, limit: int = 10) -> list[dict]:
        """Return recent cycles with their failure counts and latencies.

        Useful for health-check queries and trend analysis.
        """
        rows = self._conn.execute(
            """
            SELECT id, started_at, ended_at, status,
                   error_count, latency_ms
            FROM cycles
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
