"""ChangeSet and ChangeEntry contracts for Contract V1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .versions import CONTRACT_MAJOR_VERSION

_VALID_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
_VALID_KINDS = frozenset({"new", "updated", "removed"})


@dataclass
class ChangeEntry:
    """A single detected change produced during the ``compare`` phase.

    Attributes
    ----------
    source:
        Name of the source adapter that produced this change.
    kind:
        Change kind: ``new``, ``updated``, or ``removed``.
    payload:
        Raw event data from the source adapter.
    """

    source: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(
                f"ChangeEntry.kind must be one of {sorted(_VALID_KINDS)!r}, got {self.kind!r}"
            )


@dataclass
class ChangeSet:
    """Collection of detected differences between consecutive KnowledgeState snapshots.

    Produced by the ``compare`` phase and consumed by ``act`` and ``persist``.

    Attributes
    ----------
    changeset_id:
        Unique identifier for this changeset.
    cycle_id:
        Owning cycle identifier.
    schema_version:
        Must equal :data:`~ambient_agent.contracts.versions.CONTRACT_MAJOR_VERSION` (1).
    changes:
        Ordered list of individual change entries.
    severity:
        Aggregate severity: ``low``, ``medium``, ``high``, or ``critical``.
    """

    changeset_id: str
    cycle_id: str
    changes: list[ChangeEntry] = field(default_factory=list)
    severity: str = "low"
    schema_version: int = CONTRACT_MAJOR_VERSION

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(
                f"ChangeSet.severity must be one of {sorted(_VALID_SEVERITIES)!r}, "
                f"got {self.severity!r}"
            )
