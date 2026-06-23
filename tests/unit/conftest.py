"""Unit-test conftest: ensure the monolithic samples agent is importable."""

import sys
import os

# The unit tests import ``ambient_agent`` to reach functions defined in the
# monolithic ``samples/ambient_agent.py`` script.  Insert samples/ at the
# front of sys.path *after* any package-level path setup (e.g. src/ added by
# a root conftest from main) so the file takes precedence only for these tests.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "samples"))
