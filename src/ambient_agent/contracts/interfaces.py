"""Plugin interface ABCs for Contract V1.

All adapters must inherit from :class:`PluginBase` (via one of the four concrete
base classes below) and declare a compatible ``plugin_major_version``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .versions import CONTRACT_MAJOR_VERSION
from .knowledge_state import KnowledgeState
from .changeset import ChangeSet


class PluginBase(ABC):
    """Common base for all Contract V1 plugins.

    Subclasses automatically inherit the current ``CONTRACT_MAJOR_VERSION``
    as their default ``plugin_major_version``.  Override the property only
    when intentionally declaring a different version (which will cause
    :func:`~ambient_agent.contracts.versions.check_compatibility` to raise).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable, unique identifier for this plugin instance."""

    @property
    def plugin_major_version(self) -> int:
        """Major version this plugin was built against.

        Defaults to :data:`~ambient_agent.contracts.versions.CONTRACT_MAJOR_VERSION`.
        Override to declare an intentionally different (and incompatible) version.
        """
        return CONTRACT_MAJOR_VERSION


class SourceAdapter(PluginBase):
    """Fetches raw events from one external feed during the ``ingest`` phase."""

    @abstractmethod
    def fetch_events(self) -> list[dict]:
        """Return a list of raw event dicts from the external source.

        Returns
        -------
        list[dict]
            Zero or more raw event payloads.  Empty list signals no new events.
        """


class AnalysisProvider(PluginBase):
    """Produces a new :class:`~.KnowledgeState` during the ``compare`` phase."""

    @abstractmethod
    def analyze(self, events: list[dict]) -> KnowledgeState:
        """Analyse *events* and return a fresh :class:`~.KnowledgeState`.

        Parameters
        ----------
        events:
            Raw event dicts collected from all registered source adapters.

        Returns
        -------
        KnowledgeState
            Updated knowledge snapshot reflecting the current ingest batch.
        """


class PolicyAdapter(PluginBase):
    """Evaluates a :class:`~.ChangeSet` and produces action candidates during ``act``."""

    @abstractmethod
    def evaluate(self, changeset: ChangeSet) -> list[dict]:
        """Evaluate *changeset* and return zero or more action candidate dicts.

        Parameters
        ----------
        changeset:
            The change set produced by the ``compare`` phase.

        Returns
        -------
        list[dict]
            Action candidate payloads.  Empty list means no action is required.
        """


class SinkAdapter(PluginBase):
    """Persists a :class:`~.ChangeSet` and action candidates during ``persist``."""

    @abstractmethod
    def persist(self, changeset: ChangeSet, action_candidates: list[dict]) -> None:
        """Write *changeset* and *action_candidates* to the backing store.

        Parameters
        ----------
        changeset:
            The change set to persist.
        action_candidates:
            Action candidates produced by all registered policy adapters.
        """
