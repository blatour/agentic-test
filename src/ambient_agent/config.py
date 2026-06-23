from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RuntimeConfig:
    interval_seconds: int = 30
    dry_run: bool = False
    tenant_id: str = "default"
    source_set: str = "web-all"
    model_name: str = "qwen3.5:4b"


@dataclass(frozen=True)
class SourceConfig:
    source_id: str
    enabled: bool = True
    settings: Dict[str, str] | None = None
