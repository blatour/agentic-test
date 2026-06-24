"""Root conftest: add src/ to sys.path for all tests."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
