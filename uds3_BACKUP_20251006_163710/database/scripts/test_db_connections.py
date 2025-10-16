#!/usr/bin/env python3
"""Erweitertes Diagnose-Skript zum Überprüfen der Datenbankverbindungen.

Funktionen:
- Lädt die Standard-Konfiguration aus ``database.config``
- Optionaler Netzwerkvorab-Check (TCP / HTTP) pro Backend
- Verbindungsaufbau über ``DatabaseManager.start_all_backends``
- Ausgabe als Tabelle oder JSON
- Steuerung via CLI-Argumente (z. B. ``--only vector graph``)

Ausführung (Beispiele):
- ``python -m database.scripts.test_db_connections``
- ``python -m database.scripts.test_db_connections --network --json``
"""
from __future__ import annotations

import argparse
import ast
import json
import logging
import socket
import sys
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

try:  # psycopg3
    import psycopg
except Exception:  # pragma: no cover - optional dependency
    psycopg = None  # type: ignore

from database import config
from database.database_manager import DatabaseManager

# ---------------------------------------------------------------------------
# CLI & Logging
# ---------------------------------------------------------------------------

CLI_BACKEND_CHOICES = ["vector", "graph", "relational", "file", "key_value", "keyvalue"]

DISPLAY_KEY_BY_CANONICAL = {
    "vector": "vector",
    "graph": "graph",
    "relational": "relational",
    "file": "file",
    "keyvalue": "key_value",
}

ERROR_PREFIX = {
    "vector": "vector",
    "graph": "graph",
    "relational": "relational",
    "file": "file",
    "keyvalue": "keyvalue",
}

BACKEND_ACCESSORS = {
    "vector": DatabaseManager.get_vector_backend,
    "graph": DatabaseManager.get_graph_backend,
    "relational": DatabaseManager.get_relational_backend,
    "file": DatabaseManager.get_file_backend,
    "keyvalue": DatabaseManager.get_key_value_backend,
}


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prüft Datenbankverbindungen via DatabaseManager.")
    parser.add_argument(
        "--only",
        nargs="+",
        choices=CLI_BACKEND_CHOICES,
        help="Nur die angegebenen Backends prüfen (vector, graph, relational, file, key_value).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Timeout pro Backend-Verbindung in Sekunden (Standard: 5s).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Aktiviert den Strict-Mode des DatabaseManager (Fehler führen zu Ausnahmen).",
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="Führt vor dem Verbindungsaufbau einen TCP/HTTP-Vorabcheck durch (falls Host/Port vorhanden).",
    )
    parser.add_argument(
        "--network-only",
        action="store_true",
        help="Überspringt den Verbindungsaufbau über den DatabaseManager und führt nur Netzwerk/Driver-Diagnosen aus.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Gibt das Ergebnis zusätzlich als JSON auf stdout aus.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Setzt einen Exit-Code ungleich Null, wenn mindestens ein Backend fehlschlägt.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Erhöht die Log-Ausgabe (mehrfach möglich).",
    )
    parser.add_argument(
        "--override",
        action="append",
        metavar="PATH=VALUE",
        help="Überschreibt Konfigurationswerte, z. B. relational.password=secret oder graph.settings.uri=bolt://...",
    )
    return parser.parse_args(argv)


def configure_logging(verbosity: int) -> None:
    base_level = logging.WARNING
    if verbosity == 1:
        base_level = logging.INFO
    elif verbosity >= 2:
        base_level = logging.DEBUG
    logging.basicConfig(
        level=base_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _coerce_value(value: str) -> Any:
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        return ast.literal_eval(value)
    except Exception:
        return value


def apply_overrides(backend_dict: MutableMapping[str, Dict[str, Any]], overrides: Optional[List[str]]) -> None:
    if not overrides:
        return

    for item in overrides:
        if not item or "=" not in item:
            logging.warning("Ignoriere ungültiges Override '%s' (Format PATH=VALUE)", item)
            continue
        path_raw, raw_value = item.split("=", 1)
        path_parts = [p for p in path_raw.strip().split(".") if p]
        if len(path_parts) < 2:
            logging.warning("Override '%s' benötigt mindestens zwei Pfadebenen (backend.field)", item)
            continue

        backend_key = path_parts[0]
        canonical = canonical_to_display(normalize_backend_name(backend_key))
        target = backend_dict.get(canonical)
        if target is None:
            logging.warning("Override '%s': Backend '%s' nicht in Konfiguration gefunden", item, backend_key)
            continue

        value = _coerce_value(raw_value)
        cursor: MutableMapping[str, Any] = target
        for key in path_parts[1:-1]:
            if key not in cursor or not isinstance(cursor[key], MutableMapping):
                cursor[key] = {}
            cursor = cursor[key]  # type: ignore[assignment]
        cursor[path_parts[-1]] = value
        logging.debug("Override angewendet: %s -> %r", item, value)

def normalize_backend_name(name: str) -> str:
    norm = name.lower().replace("-", "_")
    if norm == "key_value":
        return "keyvalue"
    return norm


def canonical_to_display(name: str) -> str:
    return DISPLAY_KEY_BY_CANONICAL.get(name, name)


def tcp_probe(host: str, port: int, timeout: float) -> Tuple[bool, Optional[str]]:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, None
    except Exception as exc:  # pragma: no cover - Netzwerkfehler im Livebetrieb
        return False, str(exc)


def http_probe(host: str, port: int, path: str, timeout: float) -> Tuple[Optional[bool], Optional[str]]:
    if requests is None:
        return None, "requests not installed"
    url = f"http://{host}:{port}{path}"
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code < 500, f"status={resp.status_code}"
    except Exception as exc:  # pragma: no cover - Netzwerkfehler im Livebetrieb
        return False, str(exc)


def guess_http_path(canonical: str, cfg: Mapping[str, Any]) -> Optional[str]:
    settings = cfg.get("settings") or {}
    if isinstance(settings, Mapping) and settings.get("health_path"):
        return str(settings["health_path"])
    backend_name = str(cfg.get("backend", "")).lower()
    if backend_name in {"chromadb", "couchdb"}:
        return "/"
    return None


def perform_network_probe(canonical: str, cfg: Mapping[str, Any], timeout: float) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    host = cfg.get("host")
    port = cfg.get("port")
    if host and port:
        ok, err = tcp_probe(str(host), int(port), timeout)
        result["tcp_ok"] = ok
        if err:
            result["tcp_error"] = err
        http_path = guess_http_path(canonical, cfg)
        if http_path is not None:
            http_ok, http_detail = http_probe(str(host), int(port), http_path, timeout)
            result["http_ok"] = http_ok
            if http_detail:
                result["http_detail"] = http_detail
    return result


def diagnose_postgres(cfg: Mapping[str, Any], timeout: float) -> Dict[str, Any]:
    diag: Dict[str, Any] = {}
    if psycopg is None:
        diag["driver"] = "missing"
        diag["hint"] = "Installiere psycopg[binary] oder psycopg2"
        return diag

    host = cfg.get("host", "localhost")
    port = cfg.get("port", 5432)
    user = cfg.get("user") or cfg.get("username") or "postgres"
    password = cfg.get("password") or cfg.get("secret") or cfg.get("settings", {}).get("password")
    database = cfg.get("database") or cfg.get("dbname") or "postgres"
    allowed_option_keys = {
        "sslmode",
        "target_session_attrs",
        "application_name",
        "connect_timeout",
        "options",
        "passfile",
        "channel_binding",
        "keepalives",
        "keepalives_idle",
        "keepalives_interval",
        "keepalives_count",
    }
    settings = cfg.get("settings") or {}
    options = {
        k: v
        for k, v in settings.items()
        if isinstance(k, str) and k in allowed_option_keys
    }

    conn = None
    try:
        conn = psycopg.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            dbname=database,
            connect_timeout=max(1, int(timeout)),
            **options,
        )
        diag["driver"] = "ok"
    except Exception as exc:  # pragma: no cover - echte Verbindungsfehler
        diag["driver"] = "error"
        diag["error"] = str(exc)
        if "no password supplied" in diag["error"]:
            diag["hint"] = "Setze POSTGRES_PASSWORD oder verwende --override relational.password=<wert>"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return diag


def diagnose_keyvalue(cfg: Mapping[str, Any], timeout: float) -> Dict[str, Any]:
    backend_name = str(cfg.get("backend") or "").lower()
    if backend_name in {"postgresql", "postgres", "postgresql-keyvalue"}:
        return {"postgres": diagnose_postgres(cfg, timeout)}
    if backend_name in {"redis", "redis_cluster"}:
        return {"hint": "Redis-Diagnose nicht implementiert"}
    return {"hint": f"Keine Diagnose für Backend '{backend_name}' verfügbar"}


def diagnose_neo4j(cfg: Mapping[str, Any], timeout: float) -> Dict[str, Any]:
    diag: Dict[str, Any] = {}
    try:
        from neo4j import GraphDatabase  # type: ignore
    except Exception as exc:  # pragma: no cover - Importfehler im Livebetrieb
        diag["driver"] = "missing"
        diag["error"] = str(exc)
        diag["hint"] = "Installiere neo4j>=5.16 (Python 3.12) oder nutze HTTP-Fallback"
        return diag

    host = cfg.get("host", "localhost")
    bolt_port = cfg.get("bolt_port") or cfg.get("port") or 7687
    uri = cfg.get("settings", {}).get("uri") or f"bolt://{host}:{bolt_port}"
    user = cfg.get("username") or cfg.get("user")
    password = cfg.get("password")
    database = cfg.get("database") or cfg.get("settings", {}).get("db_name")

    driver = None
    try:
        if user is not None:
            driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            driver = GraphDatabase.driver(uri)
        with driver.session(database=database) as session:
            session.run("RETURN 1")
        diag["driver"] = "ok"
    except Exception as exc:  # pragma: no cover - echte Verbindungsfehler
        diag["driver"] = "error"
        diag["error"] = str(exc)
        if "EAI_ADDRFAMILY" in diag["error"]:
            diag["hint"] = "Der offizielle neo4j Treiber unterstützt Python 3.13 noch nicht. Verwende Python 3.12 oder `pip install neo4j>=5.20`."
    finally:
        if driver is not None:
            try:
                driver.close()
            except Exception:
                pass
    return diag


def summarize_backends(
    backend_dict: Mapping[str, Dict[str, Any]],
    manager: Optional[DatabaseManager],
    start_results: Mapping[str, bool],
    timeout: float,
    include_network: bool,
    selected: Optional[Iterable[str]] = None,
) -> Tuple["OrderedDict[str, Dict[str, Any]]", bool]:
    summary: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    attempted = set(start_results.keys())
    targets = {normalize_backend_name(name) for name in (selected or []) if name}
    manager_errors = manager.get_backend_errors() if manager else []
    has_failure = False

    for raw_key, cfg in backend_dict.items():
        canonical = normalize_backend_name(raw_key)
        display_key = canonical_to_display(canonical)

        enabled = bool(cfg.get("enabled", True))
        connection_attempted = canonical in attempted
        connect_success = start_results.get(canonical)

        entry: Dict[str, Any] = {
            "backend": cfg.get("backend"),
            "enabled": enabled,
            "connection_attempted": connection_attempted,
            "connect_success": bool(connect_success) if connection_attempted else None,
            "host": cfg.get("host"),
            "port": cfg.get("port"),
        }

        # Nur dann Netzwerk-Check durchführen, wenn explizit angefordert.
        if include_network and enabled:
            network_result = perform_network_probe(canonical, cfg, timeout)
            if network_result:
                entry["network_probe"] = network_result
                if network_result.get("tcp_ok") is False or network_result.get("http_ok") is False:
                    has_failure = True

        accessor = BACKEND_ACCESSORS.get(canonical)
        backend_instance = None
        availability = None
        availability_error = None

        if manager and accessor and enabled and connection_attempted and connect_success:
            try:
                backend_instance = accessor(manager)
                if backend_instance and hasattr(backend_instance, "is_available"):
                    availability = bool(backend_instance.is_available())
                elif backend_instance is not None:
                    availability = True
            except Exception as exc:  # pragma: no cover - echte Backends werfen evtl. Fehler
                availability = False
                availability_error = str(exc)

        entry["available"] = availability
        if availability_error:
            entry["availability_error"] = availability_error

        relevant_errors = [err for err in manager_errors if err.lower().startswith(ERROR_PREFIX.get(canonical, ""))]
        if relevant_errors:
            entry["manager_errors"] = relevant_errors

        if enabled and connection_attempted and not entry.get("connect_success"):
            has_failure = True
        if enabled and availability is False:
            has_failure = True

        need_diag = (
            enabled
            and (
                (connection_attempted and not entry.get("connect_success"))
                or (entry.get("network_probe", {}).get("tcp_ok") is False)
            )
        )
        diagnostics: Dict[str, Any] = {}
        if need_diag:
            if canonical == "relational":
                diagnostics["postgres"] = diagnose_postgres(cfg, timeout)
            elif canonical == "graph":
                diagnostics["neo4j"] = diagnose_neo4j(cfg, timeout)
            elif canonical == "keyvalue":
                diagnostics.update(diagnose_keyvalue(cfg, timeout))
            if diagnostics:
                entry["diagnostics"] = diagnostics

        summary[display_key] = entry

    # Füge Ziel-Backends hinzu, die nicht in der Konfiguration waren
    for target in targets:
        display_target = canonical_to_display(target)
        if display_target not in summary:
            summary[display_target] = {
                "backend": None,
                "enabled": False,
                "connection_attempted": False,
                "connect_success": None,
            }

    return summary, has_failure


def render_table(summary: Mapping[str, Dict[str, Any]]) -> str:
    lines: List[str] = []
    header = f"{'Backend':<12} {'Enabled':<8} {'Connect':<10} {'Available':<11} {'Network':<18} Backend-Typ"
    lines.append(header)
    lines.append("-" * len(header))
    for name, entry in summary.items():
        enabled = "yes" if entry.get("enabled") else "no"
        connect_status = entry.get("connect_success")
        if connect_status is True:
            connect_text = "OK"
        elif connect_status is False:
            connect_text = "FAIL"
        elif entry.get("connection_attempted"):
            connect_text = "FAIL"  # attempted but bool(None) -> False
        else:
            connect_text = "SKIP"

        availability = entry.get("available")
        if availability is True:
            avail_text = "OK"
        elif availability is False:
            avail_text = "FAIL"
        elif availability is None and entry.get("connection_attempted"):
            avail_text = "UNK"
        else:
            avail_text = "-"

        network_text = "-"
        if "network_probe" in entry:
            net = entry["network_probe"]
            parts = []
            if "tcp_ok" in net:
                parts.append(f"tcp={'OK' if net['tcp_ok'] else 'FAIL'}")
            if "http_ok" in net and net["http_ok"] is not None:
                parts.append(f"http={'OK' if net['http_ok'] else 'FAIL'}")
            network_text = ",".join(parts) if parts else "-"

        backend_type = entry.get("backend") or "-"

        lines.append(
            f"{name:<12} {enabled:<8} {connect_text:<10} {avail_text:<11} {network_text:<18} {backend_type}"
        )

    details: List[str] = []
    for name, entry in summary.items():
        if entry.get("manager_errors"):
            details.append(f"{name}: Manager-Fehler -> {entry['manager_errors']}")
        if entry.get("availability_error"):
            details.append(f"{name}: availability_check -> {entry['availability_error']}")
        net = entry.get("network_probe")
        if isinstance(net, Mapping):
            if net.get("tcp_error"):
                details.append(f"{name}: TCP-Fehler -> {net['tcp_error']}")
            if net.get("http_detail") and net.get("http_ok") is False:
                details.append(f"{name}: HTTP-Detail -> {net['http_detail']}")
        diagnostics = entry.get("diagnostics")
        if isinstance(diagnostics, Mapping):
            for diag_name, diag_info in diagnostics.items():
                status = diag_info.get("driver") or diag_info.get("status")
                detail = diag_info.get("error")
                hint = diag_info.get("hint")
                msg_parts = [f"{diag_name}: {status}"]
                if detail:
                    msg_parts.append(f"{detail}")
                if hint:
                    msg_parts.append(f"Hinweis: {hint}")
                details.append(f"{name}: {' | '.join(msg_parts)}")

    if details:
        lines.append("")
        lines.append("Details:")
        lines.extend(f"  - {line}" for line in details)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hauptlogik
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> Tuple[OrderedDict[str, Dict[str, Any]], bool]:
    configure_logging(args.verbose)
    logger = logging.getLogger("test_db_connections")

    backend_dict = config.get_database_backend_dict()
    apply_overrides(backend_dict, args.override)
    if not backend_dict:
        logger.error("Keine Backends in der Konfiguration gefunden.")
        return OrderedDict(), True

    logger.debug("Verfügbare Backends aus Konfiguration: %s", list(backend_dict.keys()))
    if args.only:
        logger.info("Beschränke Tests auf: %s", args.only)

    manager: Optional[DatabaseManager] = None
    results: Dict[str, bool] = {}

    if not args.network_only:
        manager = DatabaseManager(backend_dict, strict_mode=args.strict)

        try:
            start_targets = None
            if args.only:
                start_targets = {normalize_backend_name(name) for name in args.only}
            results = manager.start_all_backends(backend_names=start_targets, timeout_per_backend=args.timeout)
        except Exception as exc:
            logger.exception("start_all_backends fehlgeschlagen: %s", exc)
            if manager:
                try:
                    manager.disconnect_all()
                except Exception:
                    pass
            return OrderedDict(), True

    summary, has_failure = summarize_backends(
        backend_dict,
        manager,
        results,
        timeout=args.timeout,
        include_network=args.network or args.network_only,
        selected=args.only,
    )

    if manager:
        try:
            manager.disconnect_all()
        except Exception as exc:  # pragma: no cover - nur relevante Laufzeitfehler
            logger.warning("Fehler beim Trennen der Backends: %s", exc)

    return summary, has_failure


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    summary, has_failure = run(args)

    if summary:
        print(render_table(summary))

    if args.json and summary:
        print("\n-- JSON --------------------------------------------------------------")
        print(json.dumps(summary, indent=2, default=str))

    exit_code = 1 if (has_failure and args.fail_on_error) else 0
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
