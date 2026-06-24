"""3-cycle loop harness scaffold.

This harness drives a deterministic three-cycle ingest → compare → act →
persist scenario and verifies state convergence.

Scenario
--------
Cycle 1  New high-severity security event detected.
         ChangeSet: new item added.
         Action:    escalate.

Cycle 2  Same security event still active.
         ChangeSet: no new items, no resolved items.
         Action:    follow_up.

Cycle 3  Event resolved.
         ChangeSet: open item resolved.
         Action:    none.

After all three cycles open_items must be empty (convergence achieved).

The harness validates every intermediate payload against the four
canonical contracts so that integration failures surface immediately.
"""

import json
import os
import pytest

from contracts.canonical_event import validate_canonical_event
from contracts.knowledge_state import validate_knowledge_state
from contracts.changeset import validate_changeset
from contracts.action_decision import validate_action_decision


FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "loop_3cycle.json"
)


def _load_fixture() -> dict:
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helpers — minimal in-process simulation of the loop phases
# ---------------------------------------------------------------------------

def _ingest(cycle_data: dict) -> dict:
    """Return the canonical event for this cycle."""
    return cycle_data["event"]


def _compare(cycle_data: dict) -> dict:
    """Return the changeset for this cycle."""
    return cycle_data["changeset"]


def _act(cycle_data: dict) -> dict:
    """Return the action decision for this cycle."""
    return cycle_data["action_decision"]


def _persist(cycle_data: dict) -> dict:
    """Return the knowledge state snapshot for this cycle."""
    return cycle_data["knowledge_state"]


# ---------------------------------------------------------------------------
# Contract conformance for every payload in the fixture
# ---------------------------------------------------------------------------

class TestLoopFixtureConformance:
    def setup_method(self):
        self.fixture = _load_fixture()

    def test_fixture_has_three_cycles(self):
        assert len(self.fixture["cycles"]) == 3

    @pytest.mark.parametrize("cycle_index", [0, 1, 2])
    def test_event_conforms_to_canonical_event(self, cycle_index):
        cycle = _load_fixture()["cycles"][cycle_index]
        validate_canonical_event(_ingest(cycle))

    @pytest.mark.parametrize("cycle_index", [0, 1, 2])
    def test_knowledge_state_conforms_to_schema(self, cycle_index):
        cycle = _load_fixture()["cycles"][cycle_index]
        validate_knowledge_state(_persist(cycle))

    @pytest.mark.parametrize("cycle_index", [0, 1, 2])
    def test_changeset_conforms_to_schema(self, cycle_index):
        cycle = _load_fixture()["cycles"][cycle_index]
        validate_changeset(_compare(cycle))

    @pytest.mark.parametrize("cycle_index", [0, 1, 2])
    def test_action_decision_conforms_to_schema(self, cycle_index):
        cycle = _load_fixture()["cycles"][cycle_index]
        validate_action_decision(_act(cycle))


# ---------------------------------------------------------------------------
# Loop scenario assertions
# ---------------------------------------------------------------------------

class TestLoopScenarioAssertions:
    def setup_method(self):
        self.fixture = _load_fixture()
        self.cycles = self.fixture["cycles"]

    def test_cycle_1_detects_new_item(self):
        cycle = self.cycles[0]
        assertions = cycle["assertions"]
        changeset = _compare(cycle)
        assert changeset["new_items"] == assertions["new_items"]
        assert changeset["resolved_items"] == assertions["resolved_items"]

    def test_cycle_1_action_is_escalate(self):
        cycle = self.cycles[0]
        action = _act(cycle)
        assert action["action_type"] == cycle["assertions"]["action_type"]

    def test_cycle_1_has_one_open_item(self):
        cycle = self.cycles[0]
        state = _persist(cycle)
        assert len(state["open_items"]) == cycle["assertions"]["open_items_count"]

    def test_cycle_2_item_remains_open(self):
        cycle = self.cycles[1]
        changeset = _compare(cycle)
        assert changeset["new_items"] == []
        assert changeset["resolved_items"] == []

    def test_cycle_2_action_is_follow_up(self):
        cycle = self.cycles[1]
        action = _act(cycle)
        assert action["action_type"] == "follow_up"

    def test_cycle_2_still_has_one_open_item(self):
        cycle = self.cycles[1]
        state = _persist(cycle)
        assert len(state["open_items"]) == 1

    def test_cycle_3_resolves_item(self):
        cycle = self.cycles[2]
        changeset = _compare(cycle)
        assert "item-security-iot-001" in changeset["resolved_items"]
        assert changeset["new_items"] == []

    def test_cycle_3_action_is_none(self):
        cycle = self.cycles[2]
        action = _act(cycle)
        assert action["action_type"] == "none"

    def test_cycle_3_converges_to_empty_open_items(self):
        cycle = self.cycles[2]
        state = _persist(cycle)
        assert state["open_items"] == [], (
            "Expected open_items to be empty after cycle 3 (convergence not achieved)"
        )


# ---------------------------------------------------------------------------
# Full loop execution
# ---------------------------------------------------------------------------

class TestFullLoopExecution:
    def test_full_loop_runs_without_error(self):
        """Drive all three cycles end-to-end and confirm no exceptions."""
        fixture = _load_fixture()
        for cycle in fixture["cycles"]:
            event = _ingest(cycle)
            validate_canonical_event(event)

            changeset = _compare(cycle)
            validate_changeset(changeset)

            action = _act(cycle)
            validate_action_decision(action)

            state = _persist(cycle)
            validate_knowledge_state(state)

    def test_open_items_converge_to_zero(self):
        """After all cycles, the final knowledge state must have no open items."""
        fixture = _load_fixture()
        final_cycle = fixture["cycles"][-1]
        final_state = _persist(final_cycle)
        assert final_state["open_items"] == []

    def test_action_types_follow_expected_sequence(self):
        """Cycle action types must match: escalate → follow_up → none."""
        fixture = _load_fixture()
        expected_sequence = ["escalate", "follow_up", "none"]
        actual_sequence = [
            _act(cycle)["action_type"] for cycle in fixture["cycles"]
        ]
        assert actual_sequence == expected_sequence, (
            f"Expected action sequence {expected_sequence}, got {actual_sequence}"
        )

    def test_cycle_ids_are_unique(self):
        fixture = _load_fixture()
        cycle_ids = [c["cycle_id"] for c in fixture["cycles"]]
        assert len(cycle_ids) == len(set(cycle_ids)), "Duplicate cycle IDs found in fixture"
