from __future__ import annotations


class CompatibilityError(ValueError):
    """Raised when a contract version is not supported."""


def assert_supported_major(version: str, supported_major: int = 1) -> None:
    major = int(version.split(".", maxsplit=1)[0])
    if major != supported_major:
        raise CompatibilityError(
            f"Unsupported major version: {major}. Expected: {supported_major}."
        )
