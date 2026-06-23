"""Runtime configuration constants."""
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
LOG_FILE = os.getenv("AMBIENT_LOG_FILE", "ambient_agent_history.md")
STATE_FILE = os.getenv("AMBIENT_STATE_FILE", "ambient_agent_state.json")

DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_WEB_SOURCE_URL = "https://hn.algolia.com/api/v1/search_by_date?tags=story"
DEFAULT_GITHUB_EVENTS_URL = "https://api.github.com/events"
DEFAULT_USGS_EARTHQUAKE_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)
DEFAULT_NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
DEFAULT_NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")

# Ordered list of sources polled when --source web-all is selected.
WEB_ALL_SOURCES = ["web-github", "web-usgs", "web-nasa"]
