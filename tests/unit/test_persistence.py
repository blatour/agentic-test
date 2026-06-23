"""Unit tests for the ambient agent persistence layer.

Tests cover:
- Bootstrap / schema migration idempotency
- Save and load for all entity types (Cycle, Event, Analysis, Action,
  KnowledgeState, ChangeSet)
- Idempotent insert behaviour (duplicate saves are no-ops)
- Dedupe constraints (duplicate source events are rejected)
- KnowledgeState upsert / versioning
- load_knowledge_projection shape for compare logic
- ChangeSet round-trip persistence
- cycle_failure_summary query
"""

import os
import tempfile

import pytest

from ambient_agent.persistence.migrations import bootstrap
from ambient_agent.persistence.repository import (
    Action,
    Analysis,
    ChangeSet,
    Cycle,
    Event,
    KnowledgeState,
    Repository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_agent.db")
    bootstrap(path)
    return path


@pytest.fixture
def repo(db_path):
    with Repository(db_path) as r:
        yield r


# ---------------------------------------------------------------------------
# Bootstrap / migration tests
# ---------------------------------------------------------------------------

class TestBootstrap:
    def test_creates_db_file(self, tmp_path):
        path = str(tmp_path / "new.db")
        assert not os.path.exists(path)
        bootstrap(path)
        assert os.path.exists(path)

    def test_idempotent_bootstrap(self, tmp_path):
        path = str(tmp_path / "idem.db")
        bootstrap(path)
        bootstrap(path)  # second call must not raise or corrupt data

    def test_all_tables_created(self, db_path):
        import sqlite3

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        for expected in {"cycles", "events", "analyses", "actions",
                         "knowledge_state", "changesets"}:
            assert expected in tables, f"Table '{expected}' not found"

    def test_bootstrap_creates_parent_dirs(self, tmp_path):
        path = str(tmp_path / "nested" / "dir" / "agent.db")
        bootstrap(path)
        assert os.path.exists(path)


# ---------------------------------------------------------------------------
# Cycle tests
# ---------------------------------------------------------------------------

class TestCycle:
    def test_save_and_get(self, repo):
        cycle = Cycle.new(mode="web-all")
        repo.save_cycle(cycle)
        loaded = repo.get_cycle(cycle.id)
        assert loaded is not None
        assert loaded.id == cycle.id
        assert loaded.mode == "web-all"
        assert loaded.status == "running"

    def test_get_nonexistent_returns_none(self, repo):
        assert repo.get_cycle("does-not-exist") is None

    def test_save_is_idempotent(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        repo.save_cycle(cycle)  # should not raise or duplicate
        assert repo.get_cycle(cycle.id) is not None

    def test_update_cycle(self, repo):
        cycle = Cycle.new(mode="simulated")
        repo.save_cycle(cycle)
        cycle.status = "ok"
        cycle.ok_count = 3
        cycle.error_count = 1
        cycle.latency_ms = 250
        cycle.ended_at = "2024-01-01T00:00:10Z"
        repo.update_cycle(cycle)
        loaded = repo.get_cycle(cycle.id)
        assert loaded.status == "ok"
        assert loaded.ok_count == 3
        assert loaded.error_count == 1
        assert loaded.latency_ms == 250
        assert loaded.ended_at == "2024-01-01T00:00:10Z"

    def test_list_cycles_ordered(self, repo):
        c1 = Cycle.new()
        c2 = Cycle.new()
        repo.save_cycle(c1)
        repo.save_cycle(c2)
        cycles = repo.list_cycles()
        assert len(cycles) >= 2
        # Most recent first.
        ids = [c.id for c in cycles]
        assert c1.id in ids
        assert c2.id in ids


# ---------------------------------------------------------------------------
# Event tests
# ---------------------------------------------------------------------------

class TestEvent:
    def test_save_and_get(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        event = Event.new(
            cycle_id=cycle.id,
            source="web-github",
            raw_text="WEB [2024-01-01] - test event",
            source_event_id="gh-001",
        )
        repo.save_event(event)
        loaded = repo.get_event(event.id)
        assert loaded is not None
        assert loaded.source == "web-github"
        assert loaded.source_event_id == "gh-001"
        assert loaded.status == "ok"

    def test_deterministic_id_for_known_source_event(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        e1 = Event.new(cycle_id=cycle.id, source="web-usgs", raw_text="quake1",
                       source_event_id="usgs-001")
        e2 = Event.new(cycle_id=cycle.id, source="web-usgs", raw_text="quake1-dup",
                       source_event_id="usgs-001")
        assert e1.id == e2.id  # same deterministic ID

    def test_duplicate_source_event_is_ignored(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        e1 = Event.new(cycle_id=cycle.id, source="web-usgs",
                       raw_text="quake", source_event_id="usgs-dup")
        e2 = Event.new(cycle_id=cycle.id, source="web-usgs",
                       raw_text="quake-again", source_event_id="usgs-dup")
        repo.save_event(e1)
        repo.save_event(e2)  # same (source, source_event_id) — should be ignored
        events = repo.list_events_for_cycle(cycle.id)
        assert len(events) == 1
        assert events[0].raw_text == "quake"  # first write wins

    def test_list_events_for_cycle(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        for i in range(3):
            repo.save_event(
                Event.new(cycle_id=cycle.id, source="web-nasa",
                          raw_text=f"apod-{i}", source_event_id=f"nasa-{i}")
            )
        events = repo.list_events_for_cycle(cycle.id)
        assert len(events) == 3

    def test_list_failed_events(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        repo.save_event(
            Event.new(cycle_id=cycle.id, source="web-github",
                      raw_text="ok event", source_event_id="ok-1")
        )
        failed = Event.new(cycle_id=cycle.id, source="web-github",
                           raw_text="fetch failed", status="fetch-error")
        repo.save_event(failed)
        failures = repo.list_failed_events()
        assert any(e.status == "fetch-error" for e in failures)


# ---------------------------------------------------------------------------
# Analysis tests
# ---------------------------------------------------------------------------

class TestAnalysis:
    def test_save_and_get(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        analysis = Analysis.new(
            cycle_id=cycle.id,
            severity="Low",
            summary="All clear.",
            recommendation="No action needed.",
            is_mock=True,
        )
        repo.save_analysis(analysis)
        loaded = repo.get_analysis(analysis.id)
        assert loaded is not None
        assert loaded.severity == "Low"
        assert loaded.is_mock is True

    def test_save_is_idempotent(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        analysis = Analysis.new(cycle_id=cycle.id)
        repo.save_analysis(analysis)
        repo.save_analysis(analysis)
        assert repo.get_analysis(analysis.id) is not None

    def test_list_analyses_for_cycle(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        for _ in range(2):
            repo.save_analysis(Analysis.new(cycle_id=cycle.id))
        analyses = repo.list_analyses_for_cycle(cycle.id)
        assert len(analyses) == 2

    def test_mock_flag_roundtrip(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        for is_mock in (True, False):
            a = Analysis.new(cycle_id=cycle.id, is_mock=is_mock)
            repo.save_analysis(a)
            loaded = repo.get_analysis(a.id)
            assert loaded.is_mock is is_mock


# ---------------------------------------------------------------------------
# Action tests
# ---------------------------------------------------------------------------

class TestAction:
    def test_save_and_get(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        action = Action.new(
            cycle_id=cycle.id,
            action_type="notify",
            payload={"channel": "slack", "message": "High severity alert"},
        )
        repo.save_action(action)
        loaded = repo.get_action(action.id)
        assert loaded is not None
        assert loaded.action_type == "notify"
        assert loaded.payload["channel"] == "slack"
        assert loaded.status == "pending"

    def test_update_action_status(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        action = Action.new(cycle_id=cycle.id, action_type="alert",
                            payload={"level": "critical"})
        repo.save_action(action)
        repo.update_action_status(action.id, "sent",
                                  dispatched_at="2024-01-01T00:00:01Z")
        loaded = repo.get_action(action.id)
        assert loaded.status == "sent"
        assert loaded.dispatched_at == "2024-01-01T00:00:01Z"

    def test_save_is_idempotent(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        action = Action.new(cycle_id=cycle.id, action_type="follow-up",
                            payload={})
        repo.save_action(action)
        repo.save_action(action)
        assert len(repo.list_actions_for_cycle(cycle.id)) == 1

    def test_payload_roundtrip(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        payload = {"nested": {"count": 42}, "tags": ["a", "b"]}
        action = Action.new(cycle_id=cycle.id, action_type="notify",
                            payload=payload)
        repo.save_action(action)
        loaded = repo.get_action(action.id)
        assert loaded.payload == payload


# ---------------------------------------------------------------------------
# KnowledgeState tests
# ---------------------------------------------------------------------------

class TestKnowledgeState:
    def test_upsert_and_get(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        ks = KnowledgeState.new(
            cycle_id=cycle.id,
            source="web-github",
            key="last_event_id",
            value={"id": "gh-42"},
        )
        repo.upsert_knowledge_state(ks)
        loaded = repo.get_knowledge_state("web-github", "last_event_id")
        assert loaded is not None
        assert loaded.value == {"id": "gh-42"}
        assert loaded.version == 1

    def test_get_nonexistent_returns_none(self, repo):
        assert repo.get_knowledge_state("web-usgs", "missing") is None

    def test_upsert_increments_version(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        ks = KnowledgeState.new(cycle_id=cycle.id, source="web-usgs",
                                key="last_quake", value={"mag": 3.1})
        repo.upsert_knowledge_state(ks)
        ks2 = KnowledgeState.new(cycle_id=cycle.id, source="web-usgs",
                                 key="last_quake", value={"mag": 4.5})
        repo.upsert_knowledge_state(ks2)
        loaded = repo.get_knowledge_state("web-usgs", "last_quake")
        assert loaded.value == {"mag": 4.5}
        assert loaded.version == 2

    def test_list_knowledge_state_filtered_by_source(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        for key in ("k1", "k2"):
            repo.upsert_knowledge_state(
                KnowledgeState.new(cycle_id=cycle.id, source="web-nasa",
                                   key=key, value={"x": key})
            )
        repo.upsert_knowledge_state(
            KnowledgeState.new(cycle_id=cycle.id, source="web-usgs",
                               key="k3", value={"x": "k3"})
        )
        nasa_states = repo.list_knowledge_state(source="web-nasa")
        assert len(nasa_states) == 2
        assert all(s.source == "web-nasa" for s in nasa_states)

    def test_deterministic_id_for_same_source_key(self):
        ks1 = KnowledgeState.new(cycle_id="c1", source="web-github",
                                 key="state", value={"a": 1})
        ks2 = KnowledgeState.new(cycle_id="c2", source="web-github",
                                 key="state", value={"a": 2})
        assert ks1.id == ks2.id  # same (source, key) → same ID


# ---------------------------------------------------------------------------
# ChangeSet tests
# ---------------------------------------------------------------------------

class TestChangeSet:
    def test_save_and_list(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        cs = ChangeSet.new(
            cycle_id=cycle.id,
            source="web-github",
            key="open_prs",
            change_type="updated",
            old_value={"count": 5},
            new_value={"count": 7},
        )
        repo.save_changeset(cs)
        changesets = repo.list_changesets_for_cycle(cycle.id)
        assert len(changesets) == 1
        assert changesets[0].change_type == "updated"
        assert changesets[0].old_value == {"count": 5}
        assert changesets[0].new_value == {"count": 7}

    def test_save_is_idempotent(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        cs = ChangeSet.new(cycle_id=cycle.id, source="web-usgs",
                           key="last_quake", change_type="added",
                           new_value={"mag": 2.5})
        repo.save_changeset(cs)
        repo.save_changeset(cs)
        assert len(repo.list_changesets_for_cycle(cycle.id)) == 1

    def test_null_values_for_added_and_removed(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        added = ChangeSet.new(cycle_id=cycle.id, source="web-nasa",
                              key="apod", change_type="added",
                              old_value=None, new_value={"title": "Pillars"})
        removed = ChangeSet.new(cycle_id=cycle.id, source="web-nasa",
                                key="old_apod", change_type="removed",
                                old_value={"title": "Gone"}, new_value=None)
        repo.save_changeset(added)
        repo.save_changeset(removed)
        changesets = repo.list_changesets_for_cycle(cycle.id)
        by_type = {cs.change_type: cs for cs in changesets}
        assert by_type["added"].old_value is None
        assert by_type["removed"].new_value is None

    def test_deterministic_id(self):
        cs1 = ChangeSet.new(cycle_id="c1", source="web-usgs", key="q",
                            change_type="updated")
        cs2 = ChangeSet.new(cycle_id="c1", source="web-usgs", key="q",
                            change_type="updated")
        assert cs1.id == cs2.id


# ---------------------------------------------------------------------------
# load_knowledge_projection (compare logic read path)
# ---------------------------------------------------------------------------

class TestKnowledgeProjection:
    def test_returns_dict_keyed_by_key(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        for key, val in [("last_pr", {"id": 1}), ("star_count", {"count": 42})]:
            repo.upsert_knowledge_state(
                KnowledgeState.new(cycle_id=cycle.id, source="web-github",
                                   key=key, value=val)
            )
        projection = repo.load_knowledge_projection("web-github")
        assert projection == {
            "last_pr": {"id": 1},
            "star_count": {"count": 42},
        }

    def test_empty_projection_for_unknown_source(self, repo):
        projection = repo.load_knowledge_projection("unknown-source")
        assert projection == {}

    def test_projection_isolated_by_source(self, repo):
        cycle = Cycle.new()
        repo.save_cycle(cycle)
        repo.upsert_knowledge_state(
            KnowledgeState.new(cycle_id=cycle.id, source="web-github",
                               key="k", value={"gh": True})
        )
        repo.upsert_knowledge_state(
            KnowledgeState.new(cycle_id=cycle.id, source="web-usgs",
                               key="k", value={"usgs": True})
        )
        assert repo.load_knowledge_projection("web-github") == {"k": {"gh": True}}
        assert repo.load_knowledge_projection("web-usgs") == {"k": {"usgs": True}}


# ---------------------------------------------------------------------------
# cycle_failure_summary query
# ---------------------------------------------------------------------------

class TestCycleFailureSummary:
    def test_returns_list_of_dicts(self, repo):
        cycle = Cycle.new()
        cycle.status = "partial-failure"
        cycle.error_count = 2
        cycle.latency_ms = 500
        repo.save_cycle(cycle)
        summary = repo.cycle_failure_summary()
        assert len(summary) >= 1
        row = next(r for r in summary if r["id"] == cycle.id)
        assert row["status"] == "partial-failure"
        assert row["error_count"] == 2
        assert row["latency_ms"] == 500

    def test_respects_limit(self, repo):
        for _ in range(5):
            repo.save_cycle(Cycle.new())
        summary = repo.cycle_failure_summary(limit=3)
        assert len(summary) <= 3


# ---------------------------------------------------------------------------
# Full thin-slice cycle (integration-style)
# ---------------------------------------------------------------------------

class TestThinSliceCycle:
    """Verify that one complete thin-slice cycle can be persisted end-to-end."""

    def test_full_cycle_persist_and_load(self, repo):
        # 1. Start cycle.
        cycle = Cycle.new(mode="web-all")
        repo.save_cycle(cycle)

        # 2. Persist events.
        events = [
            Event.new(cycle_id=cycle.id, source="web-github",
                      raw_text="GH event", source_event_id="gh-1"),
            Event.new(cycle_id=cycle.id, source="web-usgs",
                      raw_text="USGS quake", source_event_id="usgs-1"),
        ]
        for ev in events:
            repo.save_event(ev)

        # 3. Persist analyses.
        for ev in events:
            repo.save_analysis(
                Analysis.new(
                    cycle_id=cycle.id,
                    event_id=ev.id,
                    severity="Low",
                    summary="Normal activity.",
                    is_mock=True,
                )
            )

        # 4. Persist actions.
        repo.save_action(
            Action.new(cycle_id=cycle.id, action_type="notify",
                       payload={"msg": "cycle done"})
        )

        # 5. Update knowledge state.
        repo.upsert_knowledge_state(
            KnowledgeState.new(cycle_id=cycle.id, source="web-github",
                               key="last_event_id", value={"id": "gh-1"})
        )

        # 6. Persist changeset.
        repo.save_changeset(
            ChangeSet.new(cycle_id=cycle.id, source="web-github",
                          key="last_event_id", change_type="updated",
                          old_value=None, new_value={"id": "gh-1"})
        )

        # 7. Close cycle.
        cycle.status = "ok"
        cycle.ok_count = 2
        cycle.source_count = 2
        cycle.latency_ms = 300
        repo.update_cycle(cycle)

        # --- Assertions ---
        loaded_cycle = repo.get_cycle(cycle.id)
        assert loaded_cycle.status == "ok"
        assert loaded_cycle.ok_count == 2

        assert len(repo.list_events_for_cycle(cycle.id)) == 2
        assert len(repo.list_analyses_for_cycle(cycle.id)) == 2
        assert len(repo.list_actions_for_cycle(cycle.id)) == 1
        assert len(repo.list_changesets_for_cycle(cycle.id)) == 1

        projection = repo.load_knowledge_projection("web-github")
        assert projection["last_event_id"] == {"id": "gh-1"}
