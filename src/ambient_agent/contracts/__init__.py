"""Contract types for loop artifacts and plugin interfaces."""

from .versions import CONTRACT_MAJOR_VERSION, CONTRACT_MINOR_VERSION, IncompatibleVersionError, check_compatibility
from .cycle import CyclePhase
from .knowledge_state import KnowledgeState
from .changeset import ChangeEntry, ChangeSet
from .interfaces import SourceAdapter, AnalysisProvider, PolicyAdapter, SinkAdapter

__all__ = [
    "CONTRACT_MAJOR_VERSION",
    "CONTRACT_MINOR_VERSION",
    "IncompatibleVersionError",
    "check_compatibility",
    "CyclePhase",
    "KnowledgeState",
    "ChangeEntry",
    "ChangeSet",
    "SourceAdapter",
    "AnalysisProvider",
    "PolicyAdapter",
    "SinkAdapter",
]
