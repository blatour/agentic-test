"""Agent state and history file persistence."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


_DEFAULT_STATE: Dict[str, Any] = {
    "last_seen_event_ids": {},
    "cycle_count": 0,
    "last_run": None,
    "last_cycle_mode": None,
    "last_cycle_checks": [],
}


def load_agent_state(state_file: str) -> Dict[str, Any]:
    if not os.path.exists(state_file):
        return dict(_DEFAULT_STATE)

    try:
        with open(state_file, "r", encoding="utf-8") as fh:
            state = json.load(fh)
            if not isinstance(state, dict):
                return dict(_DEFAULT_STATE)
            return {
                "last_seen_event_ids": state.get("last_seen_event_ids", {}),
                "cycle_count": state.get("cycle_count", 0),
                "last_run": state.get("last_run"),
                "last_cycle_mode": state.get("last_cycle_mode"),
                "last_cycle_checks": state.get("last_cycle_checks", []),
            }
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_STATE)


def save_agent_state(state_file: str, state: Dict[str, Any]) -> None:
    with open(state_file, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def append_to_history(log_file: str, raw_event: str, analysis: str) -> None:
    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(f"\n### Cycle Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"**Observed Event:** `{raw_event}`\n\n")
        fh.write(f"{analysis}\n")
        fh.write("\n---\n")


def append_multi_source_history(log_file: str, entries: List[Dict[str, Any]]) -> None:
    ok_count = sum(1 for e in entries if e.get("status") == "ok")
    failed_count = len(entries) - ok_count

    with open(log_file, "a", encoding="utf-8") as fh:
        fh.write(f"\n### Cycle Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write("**Mode:** multi-source web check\n\n")

        for entry in entries:
            fh.write(f"#### Source: {entry['source']}\n")
            fh.write(f"**Status:** {entry['status']}\n")
            fh.write(f"**Observed Event:** `{entry['raw_event']}`\n\n")
            fh.write(f"{entry.get('analysis', '')}\n\n")

        fh.write("#### Cycle Summary\n")
        fh.write(f"- Sources checked: {len(entries)}\n")
        fh.write(f"- Successful checks: {ok_count}\n")
        fh.write(f"- Failed checks: {failed_count}\n")
        fh.write("\n---\n")
