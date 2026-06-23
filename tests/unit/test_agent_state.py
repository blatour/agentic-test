"""Unit tests for agent state management functions.

Tests cover load_agent_state and save_agent_state from the ambient agent,
validating default values, round-trip persistence, and error handling.
"""

import json
import os
import pytest
import tempfile

import ambient_agent as agent


# ---------------------------------------------------------------------------
# load_agent_state
# ---------------------------------------------------------------------------

class TestLoadAgentState:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        state = agent.load_agent_state(str(tmp_path / "no_such_file.json"))
        assert state["cycle_count"] == 0
        assert state["last_seen_event_ids"] == {}
        assert state["last_run"] is None
        assert state["last_cycle_mode"] is None
        assert state["last_cycle_checks"] == []

    def test_returns_defaults_when_file_is_empty_json_object(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        state = agent.load_agent_state(str(state_file))
        assert state["cycle_count"] == 0

    def test_loads_persisted_values(self, tmp_path):
        state_file = tmp_path / "state.json"
        persisted = {
            "last_seen_event_ids": {"web_github": "evt-001"},
            "cycle_count": 5,
            "last_run": "2024-01-15 10:00:00",
            "last_cycle_mode": "web-all",
            "last_cycle_checks": [{"source": "github", "status": "ok", "raw_event": "x"}],
        }
        state_file.write_text(json.dumps(persisted), encoding="utf-8")
        state = agent.load_agent_state(str(state_file))
        assert state["cycle_count"] == 5
        assert state["last_seen_event_ids"] == {"web_github": "evt-001"}
        assert state["last_cycle_mode"] == "web-all"

    def test_returns_defaults_for_invalid_json(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("this is not json", encoding="utf-8")
        state = agent.load_agent_state(str(state_file))
        assert state["cycle_count"] == 0

    def test_returns_defaults_when_file_contains_list(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("[1, 2, 3]", encoding="utf-8")
        state = agent.load_agent_state(str(state_file))
        assert state["cycle_count"] == 0


# ---------------------------------------------------------------------------
# save_agent_state / round-trip
# ---------------------------------------------------------------------------

class TestSaveAgentState:
    def test_saves_and_reloads_state(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = {
            "last_seen_event_ids": {"web_usgs": "quake-42"},
            "cycle_count": 3,
            "last_run": "2024-01-15 10:05:00",
            "last_cycle_mode": "web-usgs",
            "last_cycle_checks": [],
        }
        agent.save_agent_state(state_file, state)
        reloaded = agent.load_agent_state(state_file)
        assert reloaded["cycle_count"] == 3
        assert reloaded["last_seen_event_ids"] == {"web_usgs": "quake-42"}

    def test_overwrites_existing_state(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        agent.save_agent_state(state_file, {"cycle_count": 1, "last_seen_event_ids": {}, "last_run": None, "last_cycle_mode": None, "last_cycle_checks": []})
        agent.save_agent_state(state_file, {"cycle_count": 2, "last_seen_event_ids": {}, "last_run": None, "last_cycle_mode": None, "last_cycle_checks": []})
        reloaded = agent.load_agent_state(state_file)
        assert reloaded["cycle_count"] == 2

    def test_saved_file_is_valid_json(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        state = {"cycle_count": 0, "last_seen_event_ids": {}, "last_run": None, "last_cycle_mode": None, "last_cycle_checks": []}
        agent.save_agent_state(state_file, state)
        with open(state_file, encoding="utf-8") as f:
            parsed = json.load(f)
        assert parsed["cycle_count"] == 0
