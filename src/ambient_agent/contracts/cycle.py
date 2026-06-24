"""Canonical cycle phases for Contract V1."""

from enum import Enum


class CyclePhase(str, Enum):
    """Ordered phases of one agent cycle.

    Phases must be executed in the declared order:
    ``INGEST`` → ``COMPARE`` → ``ACT`` → ``PERSIST``.
    """

    INGEST = "ingest"
    """Source adapters fetch raw events from external feeds."""

    COMPARE = "compare"
    """Analysis provider diffs current ingest against stored KnowledgeState."""

    ACT = "act"
    """Policy adapters evaluate the ChangeSet and produce action candidates."""

    PERSIST = "persist"
    """Sink adapters write the ChangeSet and action candidates to storage."""
