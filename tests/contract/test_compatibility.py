"""Compatibility tests for Contract V1 major-version enforcement.

Covers acceptance criterion:
  "Runtime rejects incompatible major versions with explicit error category."
"""

import pytest

from src.ambient_agent.contracts.versions import (
    CONTRACT_MAJOR_VERSION,
    IncompatibleVersionError,
    check_compatibility,
)


class TestCompatibleVersion:
    def test_current_major_version_passes(self):
        """The runtime's own major version must not raise."""
        check_compatibility(CONTRACT_MAJOR_VERSION)  # no exception expected

    def test_return_value_is_none(self):
        """check_compatibility returns None on success (no side-effect value)."""
        result = check_compatibility(CONTRACT_MAJOR_VERSION)
        assert result is None


class TestIncompatibleVersion:
    def test_future_major_version_raises(self):
        """A plugin declaring a higher major version is rejected."""
        with pytest.raises(IncompatibleVersionError):
            check_compatibility(CONTRACT_MAJOR_VERSION + 1)

    def test_past_major_version_raises(self):
        """A plugin declaring a lower major version is also rejected."""
        with pytest.raises(IncompatibleVersionError):
            check_compatibility(CONTRACT_MAJOR_VERSION - 1)

    def test_zero_major_version_raises(self):
        """Version 0 is always incompatible with V1 runtime."""
        with pytest.raises(IncompatibleVersionError):
            check_compatibility(0)

    def test_error_has_stable_category_attribute(self):
        """IncompatibleVersionError must expose a stable error_category string."""
        with pytest.raises(IncompatibleVersionError) as exc_info:
            check_compatibility(CONTRACT_MAJOR_VERSION + 99)
        assert exc_info.value.error_category == "incompatible_major_version"

    def test_error_message_contains_category_token(self):
        """The exception message must include the error_category token."""
        with pytest.raises(IncompatibleVersionError) as exc_info:
            check_compatibility(CONTRACT_MAJOR_VERSION + 1)
        assert "incompatible_major_version" in str(exc_info.value)

    def test_error_records_plugin_and_runtime_versions(self):
        """IncompatibleVersionError should record both versions for diagnostics."""
        bad_version = CONTRACT_MAJOR_VERSION + 5
        with pytest.raises(IncompatibleVersionError) as exc_info:
            check_compatibility(bad_version)
        error = exc_info.value
        assert error.plugin_major == bad_version
        assert error.runtime_major == CONTRACT_MAJOR_VERSION

    def test_incompatible_version_error_is_exception(self):
        """IncompatibleVersionError must derive from Exception."""
        assert issubclass(IncompatibleVersionError, Exception)
