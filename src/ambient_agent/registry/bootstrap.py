"""Bootstrap helper for runtime registry wiring.

Import :func:`create_default_registry` in the runtime entry-point to obtain a
pre-wired :class:`~.PluginRegistry` populated with the built-in adapters.
Additional adapters can be registered on the returned instance before the first
cycle executes.
"""

from __future__ import annotations

from .registry import PluginRegistry


def create_default_registry() -> PluginRegistry:
    """Create and return a :class:`PluginRegistry` with built-in adapters registered.

    At Contract V1 the default registry is intentionally empty — built-in
    adapter implementations are delivered by later milestones (Agent A–D).
    Callers add their own adapters after receiving the registry instance.

    Returns
    -------
    PluginRegistry
        A fresh, empty registry ready for adapter registration.

    Example
    -------
    ::

        from src.ambient_agent.registry import create_default_registry

        registry = create_default_registry()
        registry.register_source(MySourceAdapter())
        registry.register_sink(MySinkAdapter())
    """
    return PluginRegistry()
