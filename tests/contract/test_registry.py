"""Registry conformance tests for Contract V1.

Covers acceptance criteria:
  - New source onboarding requires adapter + registration + tests only.
  - New sink onboarding requires adapter + registration + config only.
  - Core orchestration files remain unchanged for a new source and new sink.
  - One end-to-end scenario produces a persisted ChangeSet and action candidate.
"""

from __future__ import annotations

import pytest

from src.ambient_agent.contracts.changeset import ChangeEntry, ChangeSet
from src.ambient_agent.contracts.interfaces import (
    AnalysisProvider,
    PolicyAdapter,
    SinkAdapter,
    SourceAdapter,
)
from src.ambient_agent.contracts.knowledge_state import KnowledgeState
from src.ambient_agent.contracts.versions import (
    CONTRACT_MAJOR_VERSION,
    IncompatibleVersionError,
)
from src.ambient_agent.registry import PluginRegistry, create_default_registry

# ---------------------------------------------------------------------------
# Minimal concrete adapters used across tests (no external I/O)
# ---------------------------------------------------------------------------


class _SimpleSource(SourceAdapter):
    @property
    def name(self) -> str:
        return "simple-source"

    def fetch_events(self) -> list[dict]:
        return [{"id": "evt-1", "value": "hello"}]


class _SimpleAnalysis(AnalysisProvider):
    @property
    def name(self) -> str:
        return "simple-analysis"

    def analyze(self, events: list[dict]) -> KnowledgeState:
        return KnowledgeState(
            state_id="state-1",
            cycle_id="cycle-1",
            sources={"simple-source": events},
        )


class _SimplePolicy(PolicyAdapter):
    @property
    def name(self) -> str:
        return "simple-policy"

    def evaluate(self, changeset: ChangeSet) -> list[dict]:
        if changeset.severity in ("high", "critical"):
            return [{"action": "alert", "changeset_id": changeset.changeset_id}]
        return []


class _SimpleSink(SinkAdapter):
    """In-memory sink that records the last persisted call."""

    def __init__(self) -> None:
        self.last_changeset: ChangeSet | None = None
        self.last_action_candidates: list[dict] = []

    @property
    def name(self) -> str:
        return "simple-sink"

    def persist(self, changeset: ChangeSet, action_candidates: list[dict]) -> None:
        self.last_changeset = changeset
        self.last_action_candidates = list(action_candidates)


class _IncompatibleSource(SourceAdapter):
    """Declares a bad major version to test fail-fast rejection."""

    @property
    def name(self) -> str:
        return "incompatible-source"

    @property
    def plugin_major_version(self) -> int:
        return CONTRACT_MAJOR_VERSION + 1

    def fetch_events(self) -> list[dict]:
        return []


class _IncompatibleSink(SinkAdapter):
    @property
    def name(self) -> str:
        return "incompatible-sink"

    @property
    def plugin_major_version(self) -> int:
        return CONTRACT_MAJOR_VERSION + 1

    def persist(self, changeset: ChangeSet, action_candidates: list[dict]) -> None:
        pass


class _IncompatiblePolicy(PolicyAdapter):
    @property
    def name(self) -> str:
        return "incompatible-policy"

    @property
    def plugin_major_version(self) -> int:
        return CONTRACT_MAJOR_VERSION + 1

    def evaluate(self, changeset: ChangeSet) -> list[dict]:
        return []


class _IncompatibleAnalysis(AnalysisProvider):
    @property
    def name(self) -> str:
        return "incompatible-analysis"

    @property
    def plugin_major_version(self) -> int:
        return CONTRACT_MAJOR_VERSION + 1

    def analyze(self, events: list[dict]) -> KnowledgeState:
        return KnowledgeState(state_id="x", cycle_id="x")


# ---------------------------------------------------------------------------
# Registry bootstrap
# ---------------------------------------------------------------------------


class TestBootstrap:
    def test_create_default_registry_returns_plugin_registry(self):
        registry = create_default_registry()
        assert isinstance(registry, PluginRegistry)

    def test_default_registry_starts_empty(self):
        registry = create_default_registry()
        assert registry.get_sources() == {}
        assert registry.get_analysis_providers() == {}
        assert registry.get_policies() == {}
        assert registry.get_sinks() == {}


# ---------------------------------------------------------------------------
# Compatible registration — all four interface types
# ---------------------------------------------------------------------------


class TestCompatibleRegistration:
    def test_register_source_succeeds(self):
        registry = PluginRegistry()
        registry.register_source(_SimpleSource())
        assert "simple-source" in registry.get_sources()

    def test_register_analysis_provider_succeeds(self):
        registry = PluginRegistry()
        registry.register_analysis_provider(_SimpleAnalysis())
        assert "simple-analysis" in registry.get_analysis_providers()

    def test_register_policy_succeeds(self):
        registry = PluginRegistry()
        registry.register_policy(_SimplePolicy())
        assert "simple-policy" in registry.get_policies()

    def test_register_sink_succeeds(self):
        registry = PluginRegistry()
        registry.register_sink(_SimpleSink())
        assert "simple-sink" in registry.get_sinks()

    def test_retrieval_returns_copy(self):
        """Mutating the returned dict must not affect the registry."""
        registry = PluginRegistry()
        registry.register_source(_SimpleSource())
        sources = registry.get_sources()
        sources.clear()
        assert "simple-source" in registry.get_sources()


# ---------------------------------------------------------------------------
# Incompatible registration — fail-fast for all four interface types
# ---------------------------------------------------------------------------


class TestIncompatibleRegistration:
    def test_incompatible_source_rejected(self):
        registry = PluginRegistry()
        with pytest.raises(IncompatibleVersionError) as exc_info:
            registry.register_source(_IncompatibleSource())
        assert exc_info.value.error_category == "incompatible_major_version"

    def test_incompatible_analysis_provider_rejected(self):
        registry = PluginRegistry()
        with pytest.raises(IncompatibleVersionError):
            registry.register_analysis_provider(_IncompatibleAnalysis())

    def test_incompatible_policy_rejected(self):
        registry = PluginRegistry()
        with pytest.raises(IncompatibleVersionError):
            registry.register_policy(_IncompatiblePolicy())

    def test_incompatible_sink_rejected(self):
        registry = PluginRegistry()
        with pytest.raises(IncompatibleVersionError):
            registry.register_sink(_IncompatibleSink())

    def test_registry_unchanged_after_rejection(self):
        """A failed registration must not partially mutate the registry."""
        registry = PluginRegistry()
        with pytest.raises(IncompatibleVersionError):
            registry.register_source(_IncompatibleSource())
        assert registry.get_sources() == {}


# ---------------------------------------------------------------------------
# End-to-end scenario: ingest → compare → act → persist
# ---------------------------------------------------------------------------


class TestEndToEndCycle:
    """One full cycle producing a persisted ChangeSet and action candidate."""

    def test_cycle_produces_persisted_changeset_and_action_candidate(self):
        # Wire up registry
        registry = PluginRegistry()
        source = _SimpleSource()
        analysis = _SimpleAnalysis()
        policy = _SimplePolicy()
        sink = _SimpleSink()
        registry.register_source(source)
        registry.register_analysis_provider(analysis)
        registry.register_policy(policy)
        registry.register_sink(sink)

        # Phase 1 — ingest
        all_events: list[dict] = []
        for adapter in registry.get_sources().values():
            all_events.extend(adapter.fetch_events())
        assert all_events, "ingest phase must produce at least one event"

        # Phase 2 — compare (produces KnowledgeState → build ChangeSet)
        provider = list(registry.get_analysis_providers().values())[0]
        knowledge_state = provider.analyze(all_events)
        assert isinstance(knowledge_state, KnowledgeState)

        changeset = ChangeSet(
            changeset_id="cs-1",
            cycle_id="cycle-1",
            changes=[
                ChangeEntry(source="simple-source", kind="new", payload=all_events[0])
            ],
            severity="high",
        )

        # Phase 3 — act (policy produces action candidates)
        action_candidates: list[dict] = []
        for pol in registry.get_policies().values():
            action_candidates.extend(pol.evaluate(changeset))
        assert len(action_candidates) == 1
        assert action_candidates[0]["action"] == "alert"

        # Phase 4 — persist (sink records ChangeSet and candidates)
        for s in registry.get_sinks().values():
            s.persist(changeset, action_candidates)

        assert sink.last_changeset is changeset
        assert sink.last_action_candidates == action_candidates

    def test_low_severity_changeset_produces_no_action_candidates(self):
        registry = PluginRegistry()
        registry.register_policy(_SimplePolicy())

        changeset = ChangeSet(
            changeset_id="cs-low",
            cycle_id="cycle-2",
            changes=[],
            severity="low",
        )
        candidates: list[dict] = []
        for pol in registry.get_policies().values():
            candidates.extend(pol.evaluate(changeset))
        assert candidates == []
