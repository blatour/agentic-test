"""KnowledgeState contract for Contract V1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .versions import CONTRACT_MAJOR_VERSION


@dataclass
class KnowledgeState:
    """Normalized snapshot of agent knowledge at the end of a cycle.

    This object is written by the ``persist`` phase and read at the start
    of the next cycle's ``compare`` phase.

    Attributes
    ----------
    state_id:
        Deterministic or UUID identifier for this snapshot.
    cycle_id:
        Identifier of the cycle that produced this snapshot.
    schema_version:
        Must equal :data:`~ambient_agent.contracts.versions.CONTRACT_MAJOR_VERSION` (1).
    sources:
        Per-source latest event payload keyed by source adapter name.
    last_updated:
        ISO-8601 timestamp of the last update, or ``None`` on first cycle.
    """

    state_id: str
    cycle_id: str
    sources: dict[str, Any] = field(default_factory=dict)
    last_updated: str | None = None
    schema_version: int = CONTRACT_MAJOR_VERSION
