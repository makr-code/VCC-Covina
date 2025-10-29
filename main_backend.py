"""Compatibility shim for tests expecting `main_backend` at project root.

Exports the FastAPI `app` from `backend/main.py`.
"""
from backend.main import app  # re-export
