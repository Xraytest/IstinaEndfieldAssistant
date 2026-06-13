"""Shared path setup for scripts/ directory.

Usage from scripts/*.py:
    from _path_setup import PROJECT_ROOT, SRC_DIR

Usage from scripts/subdir/*.py:
    import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from _path_setup import PROJECT_ROOT, SRC_DIR
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
