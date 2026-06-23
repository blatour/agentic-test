"""Shared pytest fixtures for the ambient agent test suite."""

import sys
import os
import pytest

# Make the samples directory importable so unit tests can reference the
# agent implementation directly without requiring the full src/ package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "samples"))

# Make contracts importable from within tests.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
