"""Kleines CLI-Tool: db_health_check

Usage:
    python scripts/db_health_check.py

Gibt eine Kurzübersicht über konfigurierte Backends, deren Status und optionale ModuleStatus-Informationen.
"""
import sys
from pathlib import Path

# Ensure package imports work: add project root (one level above 'database') to sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import logging

import database.database_config as db_config
import database.database_manager as db_manager

try:
    from module_status_manager import get_all_statuses  # optional
    STATUS_MANAGER_AVAILABLE = True
except Exception:
    STATUS_MANAGER_AVAILABLE = False


def format_status(status_dict):
    lines = []
    for k, v in status_dict.items():
        if isinstance(v, dict):
            lines.append(f"- {k}: {json.dumps(v)}")
        else:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    cfg = db_config.get_database_config()
    dm = db_manager.DatabaseManager(cfg)

    verify = None
    try:
        verify = dm.verify_backends()
    except Exception as e:
        logging.error(f'Error during verify_backends: {e}')

    health = None
    try:
        # Some managers implement health_check()
        health = dm.health_check() if hasattr(dm, 'health_check') else None
    except Exception as e:
        logging.error(f'Error during health_check: {e}')

    report = {
        'verify': verify,
        'health': health,
        'status_manager_available': STATUS_MANAGER_AVAILABLE
    }

    if STATUS_MANAGER_AVAILABLE:
        try:
            report['module_statuses'] = get_all_statuses()
        except Exception as e:
            logging.warning(f'Could not fetch module statuses: {e}')

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print('\n=== VERIFY BACKENDS ===')
        if verify is None:
            print('No verify result')
        else:
            print(format_status(verify))

        print('\n=== HEALTH CHECK ===')
        if health is None:
            print('No health result')
        else:
            print(format_status(health))

        print('\n=== MODULE STATUS MANAGER ===')
        print('Available:' if STATUS_MANAGER_AVAILABLE else 'Not available')


if __name__ == '__main__':
    main()
