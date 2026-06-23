from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class KnowledgeState:
    state_id: str
    tenant_id: str
    as_of: datetime
    open_items: List[Dict[str, Any]] = field(default_factory=list)
    active_facts: List[Dict[str, Any]] = field(default_factory=list)
    suppression_windows: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
