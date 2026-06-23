"""Backward-compatible CLI entry point for the ambient agent.

Accepts the same flags as the original ``samples/ambient_agent.py`` and
delegates execution to the modular Orchestrator runtime.

Usage (same as before):
    python -m ambient_agent.cli [--dry-run] [--once] [--max-cycles N]
        [--interval S] [--source SOURCE] [--web-url URL]
        [--nasa-api-key KEY] [--state-file PATH]
"""
from __future__ import annotations

import argparse
import os

from .analysis.gateway import AnalysisGateway
from .config import (
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_NASA_API_KEY,
    DEFAULT_WEB_SOURCE_URL,
    LOG_FILE,
    MODEL_NAME,
    STATE_FILE,
    WEB_ALL_SOURCES,
)
from .persistence.state import load_agent_state
from .runtime import Orchestrator
from .sources.adapters import build_source_registry, set_last_seen_ids


def _resolve_source_names(source: str) -> list[str]:
    """Map the --source flag value to an ordered list of registry names."""
    if source == "web-all":
        return list(WEB_ALL_SOURCES)
    return [source]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ambient agentic test harness for local event triage."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Seconds between cycles (default: 30).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle and exit.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Maximum number of cycles before exiting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use local mock analysis instead of calling Ollama.",
    )
    parser.add_argument(
        "--source",
        choices=["simulated", "web", "web-github", "web-usgs", "web-nasa", "web-all"],
        default="web-all",
        help="Event source type (default: web-all).",
    )
    parser.add_argument(
        "--web-url",
        default=DEFAULT_WEB_SOURCE_URL,
        help="Web JSON endpoint used when --source web.",
    )
    parser.add_argument(
        "--nasa-api-key",
        default=DEFAULT_NASA_API_KEY,
        help=(
            "NASA API key used when --source web-nasa "
            "(default: DEMO_KEY or NASA_API_KEY env)."
        ),
    )
    parser.add_argument(
        "--state-file",
        default=STATE_FILE,
        help="Path to persistent state file used to remember last seen events.",
    )
    return parser.parse_args(argv)


def _print_startup_report(state: dict) -> None:
    cycle_count = state.get("cycle_count", 0)
    last_run = state.get("last_run")
    last_cycle_mode = state.get("last_cycle_mode")
    last_cycle_checks = state.get("last_cycle_checks", [])
    last_seen_ids = state.get("last_seen_event_ids", {})

    print("Startup report:")
    print(f"- Prior cycles completed: {cycle_count}")
    if last_run:
        print(f"- Last run time: {last_run}")
    if last_cycle_mode:
        print(f"- Last cycle mode: {last_cycle_mode}")

    if last_cycle_checks:
        print("- Last cycle checks:")
        for entry in last_cycle_checks:
            source = entry.get("source", "unknown")
            status = entry.get("status", "unknown")
            raw_event = entry.get("raw_event", "")
            compact = raw_event if len(raw_event) <= 160 else f"{raw_event[:157]}..."
            print(f"  - {source}: {status} | {compact}")
    else:
        print("- Last cycle checks: none found")

    if last_seen_ids:
        print("- Last seen IDs:")
        for source_key, event_id in last_seen_ids.items():
            print(f"  - {source_key}: {event_id}")
    else:
        print("- Last seen IDs: none")
    print("")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    state = load_agent_state(args.state_file)
    set_last_seen_ids(state.get("last_seen_event_ids", {}))

    print(f"Starting Ambient Server Agent POC using {MODEL_NAME}...")
    print(f"Monitoring background stream. Logging updates to: {os.path.abspath(LOG_FILE)}\n")
    print(f"Event source: {args.source}")
    print(f"State file: {os.path.abspath(args.state_file)}")
    if state.get("last_run"):
        print(f"Recovered previous run state from: {state['last_run']}")
    _print_startup_report(state)

    if args.dry_run:
        print("Dry-run mode enabled. No external model calls will be made.\n")
    if args.source == "web":
        print(f"Web endpoint: {args.web_url}\n")
    if args.source == "web-nasa" and args.nasa_api_key == "DEMO_KEY":
        print("NASA source using DEMO_KEY. For higher limits, set NASA_API_KEY.\n")

    source_names = _resolve_source_names(args.source)
    registry = build_source_registry()
    gateway = AnalysisGateway(dry_run=args.dry_run)

    run_config = {
        "web_url": args.web_url,
        "nasa_api_key": args.nasa_api_key,
    }

    orchestrator = Orchestrator(
        source_registry=registry,
        analysis_gateway=gateway,
        source_names=source_names,
        state=state,
        state_file=args.state_file,
        log_file=LOG_FILE,
    )

    orchestrator.run_loop(
        config=run_config,
        interval=args.interval,
        once=args.once,
        max_cycles=args.max_cycles,
    )


if __name__ == "__main__":
    main()
