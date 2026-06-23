"""Analysis gateway: routes event analysis to the local LLM or mock engine."""
from __future__ import annotations

import requests

from ..config import MODEL_NAME, OLLAMA_URL


def _build_prompt(raw_event: str) -> str:
    return (
        "You are an ambient background AI assistant running autonomously on a home server.\n"
        "Review this single system event log entry. Determine if it requires attention,\n"
        "summarize what happened in plain English, and provide a 1-sentence recommendation.\n\n"
        f"Log Entry: {raw_event}\n\n"
        "Format your entire response as a clean Markdown bulleted list. "
        "Do not include conversational filler."
    )


def _generate_mock_analysis(raw_event: str) -> str:
    lowered = raw_event.lower()
    if "security" in lowered or "unrecognized" in lowered:
        level = "High"
        recommendation = (
            "Investigate immediately, isolate the device, and review recent network logs."
        )
    elif "warning" in lowered or "spiked" in lowered:
        level = "Medium"
        recommendation = (
            "Track this signal over the next hour and alert if usage remains elevated."
        )
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


def _query_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    # 120 s allows for cold model load (qwen3.5:4b ≈ 3.4 GB).
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "").strip()


class AnalysisGateway:
    """Routes analysis requests to the mock engine (dry-run) or Ollama."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def analyze(self, raw_event: str) -> str:
        """Return an analysis string for *raw_event*."""
        if self.dry_run:
            return _generate_mock_analysis(raw_event)
        return _query_ollama(_build_prompt(raw_event))
