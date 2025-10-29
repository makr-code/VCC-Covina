"""Ingestion App Factory (A1 Bootstrapping-Extraktion)

Stellt eine stabile Factory bereit, um die FastAPI-App des Ingestion-Backends
zu erhalten oder zu starten, ohne direkt die monolithische Datei zu berühren.

Nutzung (factory):
    uvicorn ingestion.launchers.app_factory:get_app --factory --host 0.0.0.0 --port 45679

Optional (direkter Start, z. B. lokal):
    python -m ingestion.launchers.app_factory
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI


def get_app() -> FastAPI:
    """Gibt die existierende FastAPI-App des Ingestion-Backends zurück.

    Delegiert an backend.ingestion.app. Dadurch kann der Launcher unabhängig
    von der monolithischen Datei existieren und Skripte/Deployments können
    diese Factory verwenden.
    """
    # Lazy-Import, um Import-Zeit und Seiteneffekte zu minimieren
    from backend.ingestion import app as ingestion_app  # type: ignore
    return ingestion_app


def run(host: str = "0.0.0.0", port: int = 45679, log_level: str = "info") -> None:
    """Startet die App via uvicorn (optional)."""
    import uvicorn
    uvicorn.run("ingestion.launchers.app_factory:get_app", factory=True, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    # Optionaler direkter Start
    run()
