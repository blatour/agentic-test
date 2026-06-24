"""Shared pytest fixtures for the ambient agent test suite."""

import sys
import os

# Make the root contracts package importable from within tests.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Allow importing the src/ package tree without requiring a full install.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
