from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass(frozen=True)
class CanonicalEnvelope:
    envelope_id: str
    envelope_type: str
    envelope_version: str
    tenant_id: str
    correlation_id: str
    causation_id: str | None
    occurred_at: datetime
    producer: str
    payload_schema_version: str
    payload: Dict[str, Any] = field(default_factory=dict)
