from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class ChangeSet:
    changeset_id: str
    tenant_id: str
    generated_at: datetime
    input_envelope_ids: List[str] = field(default_factory=list)
    new_facts: List[Dict[str, Any]] = field(default_factory=list)
    changed_facts: List[Dict[str, Any]] = field(default_factory=list)
    resolved_facts: List[Dict[str, Any]] = field(default_factory=list)
    risk_delta: float = 0.0
    confidence_delta: float = 0.0
    reason_codes: List[str] = field(default_factory=list)
