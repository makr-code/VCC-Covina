"""Compatibility shim for tests expecting `main_backend` at project root.

Exports the FastAPI `app` from `backend/main_backend.py`.
"""
from backend.main_backend import app  # re-export
