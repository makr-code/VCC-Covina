#!/usr/bin/env python3
"""Probe all configured database backends for relevant ports and drivers.

This script attempts to read the project's DB configuration via
`database.config.get_database_backend_dict()` (preferred) and falls back to
`server_config.json`. For each backend it will try:
- TCP connect on listed host/port
- HTTP probe for HTTP-based services (Chroma, CouchDB)
- Attempt a driver connect where a Python driver is available (Postgres, Neo4j)

The script is PowerShell-friendly and avoids complex quoting.
"""
import json
import os
import socket
import sys
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import requests
except Exception:
    requests = None

try:
    import psycopg2
except Exception:
    psycopg2 = None

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None

def load_config() -> Dict[str, Any]:
    cfg = {}
    try:
        import database.config as db_config

        cfg = db_config.get_database_backend_dict() or {}
    except Exception:
        cfg_path = ROOT / "server_config.json"
        if cfg_path.exists():
            with cfg_path.open("r", encoding="utf-8") as fh:
                cfg = json.load(fh)
    return cfg


def tcp_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def http_probe(url: str, timeout: float = 1.5) -> bool:
    if requests is None:
        return False
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def test_postgres(cfg: Dict[str, Any]) -> Dict[str, Any]:
    host = cfg.get("host", "127.0.0.1")
    port = cfg.get("port", 5432)
    result = {"tcp": tcp_connect(host, port)}
    if psycopg2 is not None:
        try:
            user = cfg.get("user") or cfg.get("username") or "postgres"
            pwd = cfg.get("password") or os.environ.get("SAGA_PG_PASSWORD")
            dbname = cfg.get("database") or cfg.get("dbname") or "postgres"
            conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=dbname, connect_timeout=3)
            conn.close()
            result["driver"] = "ok"
        except Exception as exc:
            result["driver"] = f"error: {exc}"
    else:
        result["driver"] = "driver-missing"
    return result


def test_neo4j(cfg: Dict[str, Any]) -> Dict[str, Any]:
    host = cfg.get("host", "127.0.0.1")
    bolt_port = cfg.get("bolt_port") or cfg.get("port") or 7687
    http_port = cfg.get("http_port") or cfg.get("http_port") or 7474
    res = {"bolt_tcp": tcp_connect(host, bolt_port), "http_tcp": tcp_connect(host, http_port)}
    if GraphDatabase is not None:
        try:
            uri = f"bolt://{host}:{bolt_port}"
            auth = (cfg.get("username"), cfg.get("password")) if cfg.get("username") else None
            driver = GraphDatabase.driver(uri, auth=auth) if auth else GraphDatabase.driver(uri)
            # quick verify
            with driver.session() as sess:
                sess.run("RETURN 1")
            driver.close()
            res["driver"] = "ok"
        except Exception as exc:
            res["driver"] = f"error: {exc}"
    else:
        res["driver"] = "driver-missing"
    return res


def test_http_service(host: str, port: int, path: str = "/") -> Dict[str, Any]:
    tcp = tcp_connect(host, port)
    http_ok = False
    if tcp and requests is not None:
        url = f"http://{host}:{port}{path}"
        http_ok = http_probe(url)
    return {"tcp": tcp, "http": http_ok}


def main():
    cfg = load_config()
    print("Loaded config keys:", list(cfg.keys()))

    # relational
    rel = cfg.get("relational") or cfg.get("postgres") or cfg.get("postgresql")
    if rel:
        print("Postgres-like backend:")
        print(json.dumps(test_postgres(rel), indent=2))

    # neo4j
    neo = cfg.get("neo4j") or cfg.get("graph") or cfg.get("neo")
    if neo:
        print("Neo4j-like backend:")
        print(json.dumps(test_neo4j(neo), indent=2))

    # chroma
    chroma = cfg.get("chroma") or cfg.get("vector")
    if chroma:
        host = chroma.get("host", "127.0.0.1")
        port = chroma.get("port", 8000)
        print("Chroma-like backend:")
        print(json.dumps(test_http_service(host, port, path="/"), indent=2))

    # couchdb
    couch = cfg.get("couchdb") or cfg.get("couch")
    if couch:
        host = couch.get("host", "127.0.0.1")
        port = couch.get("port", 5984)
        print("CouchDB-like backend:")
        print(json.dumps(test_http_service(host, port, path="/"), indent=2))

    # sqlite fallback
    sqlite = cfg.get("sqlite") or cfg.get("file")
    if sqlite:
        print("SQLite backend configured (local file); no network checks needed.")


if __name__ == "__main__":
    main()
