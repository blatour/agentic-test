"""Stage result types that flow through the ingest→compare→act→persist pipeline."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class SourceEntry:
    """Outcome of fetching a single source during an ingest stage."""

    source: str
    status: str  # "ok" | "fetch-error" | "parse-error" | "error"
    raw_event: str
    analysis: Optional[str] = None


@dataclass
class ChangeSet:
    """Result produced by the compare stage each cycle.

    Always present—even when no new events were found (is_empty == True).
    """

    cycle_id: str
    entries: List[SourceEntry] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """True when no successfully-ingested entries are present."""
        return not any(e.status == "ok" for e in self.entries)

    @classmethod
    def empty(cls, cycle_id: Optional[str] = None) -> "ChangeSet":
        cid = cycle_id or str(uuid.uuid4())[:8]
        return cls(cycle_id=cid)


@dataclass
class StageResult:
    """Explicit outcome record for one stage of the processing pipeline."""

    stage: str  # "ingest" | "compare" | "act" | "persist"
    status: str  # "ok" | "error"
    data: Any = None
    error: Optional[str] = None
