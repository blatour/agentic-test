from __future__ import annotations

from typing import Any, Dict, Iterable

from ambient_agent.contracts.envelopes import CanonicalEnvelope


class BaseSourceAdapter:
    source_type = "base"

    def ingest(self, source_config: Dict[str, Any]) -> Iterable[CanonicalEnvelope]:
        raise NotImplementedError
