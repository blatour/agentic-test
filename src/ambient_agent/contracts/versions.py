"""Version constants and compatibility enforcement for Contract V1."""

CONTRACT_MAJOR_VERSION: int = 1
"""Breaking-change boundary. Plugins must declare this exact value."""

CONTRACT_MINOR_VERSION: int = 0
"""Non-breaking additions. Minor version differences are always compatible."""

CONTRACT_VERSION: str = f"{CONTRACT_MAJOR_VERSION}.{CONTRACT_MINOR_VERSION}"


class IncompatibleVersionError(Exception):
    """Raised when a plugin declares a major version that differs from the runtime.

    Attributes
    ----------
    error_category:
        Stable string token for programmatic handling.
    """

    error_category: str = "incompatible_major_version"

    def __init__(self, plugin_major: int, runtime_major: int) -> None:
        self.plugin_major = plugin_major
        self.runtime_major = runtime_major
        super().__init__(
            f"Plugin major version {plugin_major} is incompatible with "
            f"runtime contract major version {runtime_major}. "
            f"error_category={self.error_category}"
        )


def check_compatibility(plugin_major_version: int) -> None:
    """Raise :exc:`IncompatibleVersionError` if *plugin_major_version* differs from the runtime.

    Parameters
    ----------
    plugin_major_version:
        The major version declared by the plugin or adapter being registered.

    Raises
    ------
    IncompatibleVersionError
        When *plugin_major_version* != :data:`CONTRACT_MAJOR_VERSION`.
    """
    if plugin_major_version != CONTRACT_MAJOR_VERSION:
        raise IncompatibleVersionError(
            plugin_major=plugin_major_version,
            runtime_major=CONTRACT_MAJOR_VERSION,
        )
