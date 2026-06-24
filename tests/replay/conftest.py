"""Replay-test conftest: load the monolithic samples agent for direct testing."""

import sys
import os
import importlib.util

# Load ``samples/ambient_agent.py`` directly via importlib so it does not
# conflict with the ``ambient_agent`` src-package used by contract tests.
# Registered under the key ``_samples_ambient_agent`` so test modules can
# do ``import _samples_ambient_agent as agent``.
_samples_path = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "ambient_agent.py")
_spec = importlib.util.spec_from_file_location("_samples_ambient_agent", _samples_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["_samples_ambient_agent"] = _mod
