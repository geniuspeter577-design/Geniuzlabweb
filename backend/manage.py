#!/usr/bin/env python
"""Compatibility entry point for the Django backend.

The canonical project package remains at the repository root during the
incremental restructuring. This entry point lets operators and CI use a
backend-owned command path without changing Django import paths yet.
"""
import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.geniuzlab.settings")

from django.core.management import execute_from_command_line  # noqa: E402


if __name__ == "__main__":
    execute_from_command_line([sys.argv[0], *sys.argv[1:]])
