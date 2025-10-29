"""Konfigurationslader für die Ingestion-Pipeline (Phase A).

Funktionen:
- load_ingestion_config(path: Optional[str]) -> dict
  Lädt YAML, interpoliert ${ENV:default}, konvertiert bekannte Bool-Werte.

Hinweis: PyYAML ist optional. Wenn nicht installiert, wird eine informative
RuntimeError erhoben. Tests können mit pytest.importorskip('yaml') arbeiten.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

_YAML_DEFAULT_PATH = Path(__file__).resolve().parent / "ingestion.yaml"
_ENV_PATTERN = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)\:(?P<default>[^}]*)\}|\$\{(?P<name2>[A-Za-z_][A-Za-z0-9_]*)\}")


def _interpolate_env(value: str) -> str:
    """Ersetzt ${VAR[:default]} Platzhalter durch Umgebungswerte.
    Bleibt bei Nicht-Strings unverändert.
    """
    if not isinstance(value, str):
        return value

    def repl(match: re.Match) -> str:
        name = match.group("name") or match.group("name2")
        default = match.group("default")
        if default is None:
            default = ""
        return os.environ.get(name, default)

    return _ENV_PATTERN.sub(repl, value)


def _postprocess(value: Any) -> Any:
    """Konvertiert bekannte String-Bool-Werte in echte Booleans rekursiv."""
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"true", "1", "yes", "y", "on"}:
            return True
        if low in {"false", "0", "no", "n", "off"}:
            return False
        return value
    if isinstance(value, list):
        return [_postprocess(v) for v in value]
    if isinstance(value, dict):
        return {k: _postprocess(v) for k, v in value.items()}
    return value


def _interpolate_tree(tree: Any) -> Any:
    if isinstance(tree, dict):
        return {k: _interpolate_tree(_interpolate_env(v)) for k, v in tree.items()}
    if isinstance(tree, list):
        return [_interpolate_tree(_interpolate_env(v)) for v in tree]
    return _interpolate_env(tree)


def load_ingestion_config(path: Optional[str] = None) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "PyYAML ist erforderlich, um die YAML-Konfiguration zu laden. Bitte 'pip install pyyaml' ausführen."
        ) from e

    cfg_path = Path(path).resolve() if path else _YAML_DEFAULT_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    data = _interpolate_tree(data)
    data = _postprocess(data)
    return data


__all__ = ["load_ingestion_config"]
