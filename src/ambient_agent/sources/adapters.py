"""Concrete source adapter implementations.

Each adapter wraps one event origin and exposes it through the Source interface.
Event deduplication (last-seen-ID tracking) lives here so the compare stage can
remain stateless with respect to individual source protocols.
"""
from __future__ import annotations

import random
from typing import Any, Dict

import requests

from ..config import (
    DEFAULT_GITHUB_EVENTS_URL,
    DEFAULT_NASA_APOD_URL,
    DEFAULT_NASA_API_KEY,
    DEFAULT_USGS_EARTHQUAKE_URL,
    DEFAULT_WEB_SOURCE_URL,
)
from .base import Source
from .registry import SourceRegistry

# ---------------------------------------------------------------------------
# Module-level dedup state (process-lifetime; hydrated from persisted state)
# ---------------------------------------------------------------------------

_LAST_SEEN_EVENT_IDS: Dict[str, str] = {}


def get_last_seen_ids() -> Dict[str, str]:
    return dict(_LAST_SEEN_EVENT_IDS)


def set_last_seen_ids(ids: Dict[str, str]) -> None:
    _LAST_SEEN_EVENT_IDS.clear()
    _LAST_SEEN_EVENT_IDS.update(ids)


def _is_new_event(source_key: str, event_id: str) -> bool:
    if not event_id:
        return True
    last_id = _LAST_SEEN_EVENT_IDS.get(source_key)
    if event_id == last_id:
        return False
    _LAST_SEEN_EVENT_IDS[source_key] = event_id
    return True


# ---------------------------------------------------------------------------
# Simulated
# ---------------------------------------------------------------------------

_SIMULATED_EVENTS = [
    "LOG [16:40:12] - Node-02 high memory warning: Container 'kube-proxy' spiked to 88% allocation.",
    "LOG [16:41:00] - Deploy pipeline success: SurvivalTrial build #104 compiled with 0 errors, 2 minor animation warnings.",
    "LOG [16:41:45] - Home Automation sync: Govee light temperature adjusted to 3000K based on solar elevation.",
    "LOG [16:42:10] - Security: Unrecognized local MAC address detected attempting to handshake on IoT VLAN.",
]


class SimulatedSource(Source):
    @property
    def name(self) -> str:
        return "simulated"

    def fetch(self, config: Dict[str, Any]) -> str:
        return random.choice(_SIMULATED_EVENTS)


# ---------------------------------------------------------------------------
# Hacker News (web)
# ---------------------------------------------------------------------------


class HackerNewsSource(Source):
    @property
    def name(self) -> str:
        return "web"

    def fetch(self, config: Dict[str, Any]) -> str:
        web_url = config.get("web_url", DEFAULT_WEB_SOURCE_URL)
        response = requests.get(web_url, timeout=20)
        response.raise_for_status()
        payload = response.json()

        for hit in payload.get("hits", []):
            event_id = hit.get("objectID")
            title = hit.get("title") or "Untitled"
            author = hit.get("author") or "unknown"
            points = hit.get("points", 0)
            created_at = hit.get("created_at") or "unknown time"
            if _is_new_event("web_hn", event_id):
                return (
                    f"WEB [{created_at}] - HN story by @{author}: '{title}' "
                    f"({points} points, id={event_id})."
                )

        return "WEB - No new story item found since last poll."


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


class GitHubSource(Source):
    @property
    def name(self) -> str:
        return "web-github"

    def fetch(self, config: Dict[str, Any]) -> str:
        url = config.get("github_events_url", DEFAULT_GITHUB_EVENTS_URL)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ambient-agent-test",
        }
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        for event in response.json():
            event_id = event.get("id")
            if not _is_new_event("web_github", event_id):
                continue
            event_type = event.get("type") or "UnknownEvent"
            actor = (event.get("actor") or {}).get("login") or "unknown"
            repo = (event.get("repo") or {}).get("name") or "unknown/repo"
            created_at = event.get("created_at") or "unknown time"
            return (
                f"WEB [{created_at}] - GitHub {event_type} by @{actor} on {repo} "
                f"(id={event_id})."
            )

        return "WEB - No new GitHub event found since last poll."


# ---------------------------------------------------------------------------
# USGS Earthquakes
# ---------------------------------------------------------------------------


class USGSSource(Source):
    @property
    def name(self) -> str:
        return "web-usgs"

    def fetch(self, config: Dict[str, Any]) -> str:
        url = config.get("usgs_url", DEFAULT_USGS_EARTHQUAKE_URL)
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        for feature in response.json().get("features", []):
            event_id = feature.get("id")
            if not _is_new_event("web_usgs", event_id):
                continue
            props = feature.get("properties") or {}
            mag = props.get("mag")
            place = props.get("place") or "unknown location"
            event_time_ms = props.get("time")
            url_value = props.get("url") or "no link"
            return (
                f"WEB [quake] - USGS earthquake M{mag} near {place} "
                f"(time_ms={event_time_ms}, id={event_id}, info={url_value})."
            )

        return "WEB - No new USGS earthquake event found since last poll."


# ---------------------------------------------------------------------------
# NASA APOD
# ---------------------------------------------------------------------------


class NASASource(Source):
    @property
    def name(self) -> str:
        return "web-nasa"

    def fetch(self, config: Dict[str, Any]) -> str:
        url = config.get("nasa_apod_url", DEFAULT_NASA_APOD_URL)
        api_key = config.get("nasa_api_key", DEFAULT_NASA_API_KEY)
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
            f"WEB [{apod_date}] - NASA APOD '{title}' ({media_type}, url={item_url})."
        )


# ---------------------------------------------------------------------------
# Registry factory
# ---------------------------------------------------------------------------


def build_source_registry() -> SourceRegistry:
    """Build and return a SourceRegistry with all adapters wired at startup."""
    registry = SourceRegistry()
    for adapter in (
        SimulatedSource(),
        HackerNewsSource(),
        GitHubSource(),
        USGSSource(),
        NASASource(),
    ):
        registry.register(adapter)
    return registry
