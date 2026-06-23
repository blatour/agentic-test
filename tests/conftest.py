"""Shared pytest fixtures for the ambient agent test suite."""

import sys
import os

# Make contracts importable from within tests.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
