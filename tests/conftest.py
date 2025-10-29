"""Pytest configuration for Covina test suite.

Ensures project root is on sys.path so package imports like `security.auth`
resolve reliably across different invocation contexts.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root (Covina) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optionally enforce minimal env for auth tests (safe defaults)
os.environ.setdefault("ENABLE_AUTH", "true")
os.environ.setdefault("JWT_SECRET", "test_secret_key_for_testing_only")
