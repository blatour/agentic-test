"""Replay-test conftest: ensure the monolithic samples agent is importable."""

import sys
import os

# The replay tests import ``ambient_agent`` to reach the dry-run analysis
# function defined in ``samples/ambient_agent.py``.  Insert samples/ at the
# front of sys.path so the file takes precedence over any package installed
# from src/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "samples"))
