"""Abstract base class for event source adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict


class Source(ABC):
    """Fetch one raw-event string from an event source."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier used to register this source."""
        ...

    @abstractmethod
    def fetch(self, config: Dict[str, Any]) -> str:
        """Return a raw event string.

        Args:
            config: Runtime config dict (web_url, nasa_api_key, …).

        Returns:
            A non-empty raw event string.

        Raises:
            requests.RequestException: On network/HTTP errors.
            ValueError: On malformed response payloads.
        """
        ...
