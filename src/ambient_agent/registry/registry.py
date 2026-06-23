"""PluginRegistry — composition root for all Contract V1 adapters.

The registry validates :attr:`~.PluginBase.plugin_major_version` on every
registration call and raises :exc:`~.IncompatibleVersionError` immediately
for any incompatible major version, satisfying the fail-fast acceptance criterion.
"""

from __future__ import annotations

from ..contracts.interfaces import (
    AnalysisProvider,
    PolicyAdapter,
    SinkAdapter,
    SourceAdapter,
)
from ..contracts.versions import check_compatibility


class PluginRegistry:
    """Runtime composition root for source, analysis, policy, and sink adapters.

    Usage
    -----
    ::

        registry = PluginRegistry()
        registry.register_source(MySourceAdapter())
        registry.register_sink(MySinkAdapter())

    All ``register_*`` methods call
    :func:`~ambient_agent.contracts.versions.check_compatibility` before
    storing the adapter.  Incompatible plugins are rejected immediately.
    """

    def __init__(self) -> None:
        self._sources: dict[str, SourceAdapter] = {}
        self._analysis_providers: dict[str, AnalysisProvider] = {}
        self._policies: dict[str, PolicyAdapter] = {}
        self._sinks: dict[str, SinkAdapter] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_source(self, adapter: SourceAdapter) -> None:
        """Register a source adapter after validating its major version.

        Raises
        ------
        IncompatibleVersionError
            If ``adapter.plugin_major_version`` differs from the runtime contract.
        """
        check_compatibility(adapter.plugin_major_version)
        self._sources[adapter.name] = adapter

    def register_analysis_provider(self, provider: AnalysisProvider) -> None:
        """Register an analysis provider after validating its major version.

        Raises
        ------
        IncompatibleVersionError
            If ``provider.plugin_major_version`` differs from the runtime contract.
        """
        check_compatibility(provider.plugin_major_version)
        self._analysis_providers[provider.name] = provider

    def register_policy(self, policy: PolicyAdapter) -> None:
        """Register a policy adapter after validating its major version.

        Raises
        ------
        IncompatibleVersionError
            If ``policy.plugin_major_version`` differs from the runtime contract.
        """
        check_compatibility(policy.plugin_major_version)
        self._policies[policy.name] = policy

    def register_sink(self, sink: SinkAdapter) -> None:
        """Register a sink adapter after validating its major version.

        Raises
        ------
        IncompatibleVersionError
            If ``sink.plugin_major_version`` differs from the runtime contract.
        """
        check_compatibility(sink.plugin_major_version)
        self._sinks[sink.name] = sink

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_sources(self) -> dict[str, SourceAdapter]:
        """Return all registered source adapters, keyed by name."""
        return dict(self._sources)

    def get_analysis_providers(self) -> dict[str, AnalysisProvider]:
        """Return all registered analysis providers, keyed by name."""
        return dict(self._analysis_providers)

    def get_policies(self) -> dict[str, PolicyAdapter]:
        """Return all registered policy adapters, keyed by name."""
        return dict(self._policies)

    def get_sinks(self) -> dict[str, SinkAdapter]:
        """Return all registered sink adapters, keyed by name."""
        return dict(self._sinks)
