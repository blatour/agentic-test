import argparse
import json
import os
import random
import time

import requests

# Points directly to your local Ollama endpoint.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
LOG_FILE = os.getenv("AMBIENT_LOG_FILE", "ambient_agent_history.md")
STATE_FILE = os.getenv("AMBIENT_STATE_FILE", "ambient_agent_state.json")

DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_WEB_SOURCE_URL = "https://hn.algolia.com/api/v1/search_by_date?tags=story"
DEFAULT_GITHUB_EVENTS_URL = "https://api.github.com/events"
DEFAULT_USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
DEFAULT_NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
DEFAULT_NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

SIMULATED_EVENTS = [
    "LOG [16:40:12] - Node-02 high memory warning: Container 'kube-proxy' spiked to 88% allocation.",
    "LOG [16:41:00] - Deploy pipeline success: SurvivalTrial build #104 compiled with 0 errors, 2 minor animation warnings.",
    "LOG [16:41:45] - Home Automation sync: Govee light temperature adjusted to 3000K based on solar elevation.",
    "LOG [16:42:10] - Security: Unrecognized local MAC address detected attempting to handshake on IoT VLAN.",
]

# Keep minimal in-memory state for event dedupe during a single process run.
LAST_SEEN_EVENT_IDS = {}

WEB_ALL_SOURCES = ["web-github", "web-usgs", "web-nasa"]

def fetch_simulated_system_stream():
    """
    Simulates a running background stream from a home lab cluster node.
    In a full production box, this would read from journalctl, an RSS feed, or a webhook.
    """
    return random.choice(SIMULATED_EVENTS)


def _is_new_event(source_key, event_id):
    if not event_id:
        return True
    last_id = LAST_SEEN_EVENT_IDS.get(source_key)
    if event_id == last_id:
        return False
    LAST_SEEN_EVENT_IDS[source_key] = event_id
    return True


def load_agent_state(state_file):
    default_state = {
        "last_seen_event_ids": {},
        "cycle_count": 0,
        "last_run": None,
        "last_cycle_mode": None,
        "last_cycle_checks": [],
    }

    if not os.path.exists(state_file):
        return default_state

    try:
        with open(state_file, "r", encoding="utf-8") as input_file:
            state = json.load(input_file)
            if not isinstance(state, dict):
                return default_state
            return {
                "last_seen_event_ids": state.get("last_seen_event_ids", {}),
                "cycle_count": state.get("cycle_count", 0),
                "last_run": state.get("last_run"),
                "last_cycle_mode": state.get("last_cycle_mode"),
                "last_cycle_checks": state.get("last_cycle_checks", []),
            }
    except (json.JSONDecodeError, OSError):
        return default_state


def save_agent_state(state_file, state):
    with open(state_file, "w", encoding="utf-8") as output_file:
        json.dump(state, output_file, indent=2)


def hydrate_runtime_state(state):
    LAST_SEEN_EVENT_IDS.clear()
    LAST_SEEN_EVENT_IDS.update(state.get("last_seen_event_ids", {}))


def fetch_hn_event_stream(web_url):
    """
    Fetches one event from a lightweight public JSON endpoint.
    Default source is Hacker News recent stories via Algolia.
    """
    response = requests.get(web_url, timeout=20)
    response.raise_for_status()
    payload = response.json()

    hits = payload.get("hits", [])
    for hit in hits:
        event_id = hit.get("objectID")
        title = hit.get("title") or "Untitled"
        author = hit.get("author") or "unknown"
        points = hit.get("points", 0)
        created_at = hit.get("created_at") or "unknown time"
        if _is_new_event("web_hn", event_id):
            return (
                "WEB "
                f"[{created_at}] - HN story by @{author}: '{title}' "
                f"({points} points, id={event_id})."
            )

    # Fallback if API returns only already-seen items in this process.
    return "WEB - No new story item found since last poll."


def fetch_github_event_stream(url=DEFAULT_GITHUB_EVENTS_URL):
    """Fetches one event from GitHub public events API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ambient-agent-test",
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    events = response.json()

    for event in events:
        event_id = event.get("id")
        if not _is_new_event("web_github", event_id):
            continue
        event_type = event.get("type") or "UnknownEvent"
        actor = (event.get("actor") or {}).get("login") or "unknown"
        repo = (event.get("repo") or {}).get("name") or "unknown/repo"
        created_at = event.get("created_at") or "unknown time"
        return (
            "WEB "
            f"[{created_at}] - GitHub {event_type} by @{actor} on {repo} "
            f"(id={event_id})."
        )

    return "WEB - No new GitHub event found since last poll."


def fetch_usgs_event_stream(url=DEFAULT_USGS_EARTHQUAKE_URL):
    """Fetches one event from USGS earthquake feed."""
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features", [])

    for feature in features:
        event_id = feature.get("id")
        if not _is_new_event("web_usgs", event_id):
            continue
        properties = feature.get("properties") or {}
        mag = properties.get("mag")
        place = properties.get("place") or "unknown location"
        event_time_ms = properties.get("time")
        url_value = properties.get("url") or "no link"
        return (
            "WEB "
            f"[quake] - USGS earthquake M{mag} near {place} "
            f"(time_ms={event_time_ms}, id={event_id}, info={url_value})."
        )

    return "WEB - No new USGS earthquake event found since last poll."


def fetch_nasa_apod_event_stream(
    url=DEFAULT_NASA_APOD_URL,
    api_key=DEFAULT_NASA_API_KEY,
):
    """Fetches NASA APOD metadata as a daily low-noise event source."""
    response = requests.get(url, params={"api_key": api_key}, timeout=20)
    response.raise_for_status()
    payload = response.json()

    apod_date = payload.get("date") or "unknown-date"
    if not _is_new_event("web_nasa_apod", apod_date):
        return "WEB - No new NASA APOD item since last poll."

    title = payload.get("title") or "Untitled"
    media_type = payload.get("media_type") or "unknown"
    item_url = payload.get("url") or "no link"
    return (
        "WEB "
        f"[{apod_date}] - NASA APOD '{title}' ({media_type}, url={item_url})."
    )


def fetch_web_event_stream(source, web_url, nasa_api_key):
    if source == "web":
        return fetch_hn_event_stream(web_url)
    if source == "web-github":
        return fetch_github_event_stream()
    if source == "web-usgs":
        return fetch_usgs_event_stream()
    if source == "web-nasa":
        return fetch_nasa_apod_event_stream(api_key=nasa_api_key)
    return fetch_hn_event_stream(web_url)


def build_prompt(raw_event):
    return f"""
    You are an ambient background AI assistant running autonomously on a home server.
    Review this single system event log entry. Determine if it requires attention,
    summarize what happened in plain English, and provide a 1-sentence recommendation.

    Log Entry: {raw_event}

    Format your entire response as a clean Markdown bulleted list. Do not include conversational filler.
    """


def generate_mock_analysis(raw_event):
    """Fallback analysis for dry-run mode when no LLM call should be made."""
    lowered = raw_event.lower()
    if "security" in lowered or "unrecognized" in lowered:
        level = "High"
        recommendation = "Investigate immediately, isolate the device, and review recent network logs."
    elif "warning" in lowered or "spiked" in lowered:
        level = "Medium"
        recommendation = "Track this signal over the next hour and alert if usage remains elevated."
    else:
        level = "Low"
        recommendation = "No urgent action required; record the event and continue monitoring."

    return "\n".join(
        [
            f"- **Severity:** {level}",
            f"- **Summary:** {raw_event}",
            f"- **Recommendation:** {recommendation}",
        ]
    )


def query_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    # 120s allows for cold model load (qwen3.5:4b is ~3.4 GB).
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "").strip()


def append_to_history(raw_event, analysis):
    with open(LOG_FILE, "a", encoding="utf-8") as history_file:
        history_file.write(f"\n### Cycle Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        history_file.write(f"**Observed Event:** `{raw_event}`\n\n")
        history_file.write(f"{analysis}\n")
        history_file.write("\n---\n")


def append_multi_source_history(entries):
    ok_count = sum(1 for entry in entries if entry["status"] == "ok")
    failed_count = len(entries) - ok_count

    with open(LOG_FILE, "a", encoding="utf-8") as history_file:
        history_file.write(f"\n### Cycle Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        history_file.write("**Mode:** multi-source web check\n\n")

        for entry in entries:
            history_file.write(f"#### Source: {entry['source']}\n")
            history_file.write(f"**Status:** {entry['status']}\n")
            history_file.write(f"**Observed Event:** `{entry['raw_event']}`\n\n")
            history_file.write(f"{entry['analysis']}\n\n")

        history_file.write("#### Cycle Summary\n")
        history_file.write(f"- Sources checked: {len(entries)}\n")
        history_file.write(f"- Successful checks: {ok_count}\n")
        history_file.write(f"- Failed checks: {failed_count}\n")
        history_file.write("\n---\n")


def print_startup_report(state):
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
            compact_event = raw_event if len(raw_event) <= 160 else f"{raw_event[:157]}..."
            print(f"  - {source}: {status} | {compact_event}")
    else:
        print("- Last cycle checks: none found")

    if last_seen_ids:
        print("- Last seen IDs:")
        for source_key, event_id in last_seen_ids.items():
            print(f"  - {source_key}: {event_id}")
    else:
        print("- Last seen IDs: none")
    print("")


def run_agent_cycle(
    dry_run=False,
    source="simulated",
    web_url=DEFAULT_WEB_SOURCE_URL,
    nasa_api_key=DEFAULT_NASA_API_KEY,
):
    try:
        if source.startswith("web"):
            raw_event = fetch_web_event_stream(source, web_url, nasa_api_key)
        else:
            raw_event = fetch_simulated_system_stream()

        if dry_run:
            analysis = generate_mock_analysis(raw_event)
        else:
            prompt = build_prompt(raw_event)
            analysis = query_ollama(prompt)

        append_to_history(raw_event, analysis)
        print(f"[{time.strftime('%H:%M:%S')}] Cycle complete. Analysis written to {LOG_FILE}.")
        return [
            {
                "source": source,
                "status": "ok",
                "raw_event": raw_event,
            }
        ]
    except requests.RequestException as e:
        print(f"Cycle execution failed due to HTTP/network error: {e}")
        return [
            {
                "source": source,
                "status": "fetch-error",
                "raw_event": f"Fetch failed for {source}: {e}",
            }
        ]
    except ValueError as e:
        print(f"Cycle execution failed due to invalid JSON response: {e}")
        return [
            {
                "source": source,
                "status": "parse-error",
                "raw_event": f"Parse failure for {source}: {e}",
            }
        ]
    except Exception as e:
        print(f"Cycle execution failed: {e}")
        return [
            {
                "source": source,
                "status": "error",
                "raw_event": f"Unexpected failure for {source}: {e}",
            }
        ]


def run_web_all_cycle(dry_run=False, web_url=DEFAULT_WEB_SOURCE_URL, nasa_api_key=DEFAULT_NASA_API_KEY):
    entries = []

    for source in WEB_ALL_SOURCES:
        try:
            raw_event = fetch_web_event_stream(source, web_url, nasa_api_key)
            if dry_run:
                analysis = generate_mock_analysis(raw_event)
            else:
                analysis = query_ollama(build_prompt(raw_event))

            entries.append(
                {
                    "source": source,
                    "status": "ok",
                    "raw_event": raw_event,
                    "analysis": analysis,
                }
            )
        except requests.RequestException as e:
            entries.append(
                {
                    "source": source,
                    "status": "fetch-error",
                    "raw_event": f"Fetch failed for {source}: {e}",
                    "analysis": "- **Severity:** Medium\n- **Summary:** Source fetch failed this cycle.\n- **Recommendation:** Retry next cycle and inspect network/API limits if failures persist.",
                }
            )
        except Exception as e:
            entries.append(
                {
                    "source": source,
                    "status": "error",
                    "raw_event": f"Unexpected failure for {source}: {e}",
                    "analysis": "- **Severity:** Medium\n- **Summary:** Source processing failed this cycle.\n- **Recommendation:** Review traceback and keep agent running for next interval.",
                }
            )

    append_multi_source_history(entries)
    print(
        f"[{time.strftime('%H:%M:%S')}] Multi-source cycle complete. "
        f"Summary written to {LOG_FILE}."
    )
    return entries


def parse_args():
    parser = argparse.ArgumentParser(description="Ambient agentic test harness for local event triage.")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Seconds between cycles (default: 30).",
    )
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit.")
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
        help="Event source type (default: simulated).",
    )
    parser.add_argument(
        "--web-url",
        default=DEFAULT_WEB_SOURCE_URL,
        help="Web JSON endpoint used when --source web.",
    )
    parser.add_argument(
        "--nasa-api-key",
        default=DEFAULT_NASA_API_KEY,
        help="NASA API key used when --source web-nasa (default: DEMO_KEY or NASA_API_KEY env).",
    )
    parser.add_argument(
        "--state-file",
        default=STATE_FILE,
        help="Path to persistent state file used to remember last seen events.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    state = load_agent_state(args.state_file)
    hydrate_runtime_state(state)

    print(f"Starting Ambient Server Agent POC using {MODEL_NAME}...")
    print(f"Monitoring background stream. Logging updates to: {os.path.abspath(LOG_FILE)}\n")
    print(f"Event source: {args.source}")
    print(f"State file: {os.path.abspath(args.state_file)}")
    if state.get("last_run"):
        print(f"Recovered previous run state from: {state['last_run']}")
    print_startup_report(state)
    if args.dry_run:
        print("Dry-run mode enabled. No external model calls will be made.\n")
    if args.source == "web":
        print(f"Web endpoint: {args.web_url}\n")
    if args.source == "web-nasa" and args.nasa_api_key == "DEMO_KEY":
        print("NASA source using DEMO_KEY. For higher limits, set NASA_API_KEY.\n")

    cycles_completed = 0

    try:
        while True:
            if args.source == "web-all":
                cycle_entries = run_web_all_cycle(
                    dry_run=args.dry_run,
                    web_url=args.web_url,
                    nasa_api_key=args.nasa_api_key,
                )
            else:
                cycle_entries = run_agent_cycle(
                    dry_run=args.dry_run,
                    source=args.source,
                    web_url=args.web_url,
                    nasa_api_key=args.nasa_api_key,
                )
            cycles_completed += 1

            state["last_seen_event_ids"] = dict(LAST_SEEN_EVENT_IDS)
            state["cycle_count"] = state.get("cycle_count", 0) + 1
            state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            state["last_cycle_mode"] = args.source
            state["last_cycle_checks"] = cycle_entries
            save_agent_state(args.state_file, state)

            if args.once:
                break
            if args.max_cycles is not None and cycles_completed >= args.max_cycles:
                break

            # Sleep between cycles to simulate continuous monitoring without excessive CPU use.
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        print("\nAmbient agent shutting down cleanly. Goodbye.")