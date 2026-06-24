"""Source registry: maps source names to Source implementations."""
from typing import Any, Dict, List

from .base import Source


class SourceRegistry:
    """Holds all registered source adapters, wired at startup."""

    def __init__(self) -> None:
        self._sources: Dict[str, Source] = {}

    def register(self, source: Source) -> None:
        """Register a source adapter by its name."""
        self._sources[source.name] = source

    def fetch(self, name: str, config: Dict[str, Any]) -> str:
        """Delegate a fetch call to the named source adapter.

        Raises:
            KeyError: If *name* was not registered.
        """
        if name not in self._sources:
            raise KeyError(f"Source '{name}' is not registered")
        return self._sources[name].fetch(config)

    def registered_names(self) -> List[str]:
        return list(self._sources.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._sources
