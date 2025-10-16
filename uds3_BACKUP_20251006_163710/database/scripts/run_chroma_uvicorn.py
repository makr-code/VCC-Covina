#!/usr/bin/env python3
"""Start helper for chromadb server using the installed chromadb package or fallback to python -m chromadb.

This script performs inspection of `chromadb.server` to find a suitable entrypoint. By default it will only print what it would do; pass --execute to actually run the discovered entrypoint.

Usage:
  python database/scripts/run_chroma_uvicorn.py [--execute]
"""
import argparse
import importlib
import inspect
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true', help='Actually execute the detected start command')
parser.add_argument('--host', default='0.0.0.0')
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()

# Attempt to import chromadb.server
try:
    chroma_server = importlib.import_module('chromadb.server')
    logging.info('Imported chromadb.server')
except Exception as e:
    chroma_server = None
    logging.info(f'chromadb.server import failed: {e}')

# Heuristics
if chroma_server:
    # Look for create_app
    if hasattr(chroma_server, 'create_app'):
        logging.info('Detected create_app in chromadb.server')
        cmd = ('uvicorn', 'chromadb.server:create_app()', '--host', args.host, '--port', str(args.port))
        action = f"uvicorn chromadb.server:create_app() --host {args.host} --port {args.port}"
    elif hasattr(chroma_server, 'Server'):
        logging.info('Detected Server class in chromadb.server')
        action = 'Instantiate Server class programmatically or use chromadb CLI'
        cmd = None
    elif hasattr(chroma_server, 'main'):
        logging.info('Detected main() in chromadb.server')
        action = 'Call chromadb.server.main()'
        cmd = None
    else:
        logging.info('No known entrypoint found in chromadb.server; will fallback to python -m chromadb')
        chroma_server = None
        cmd = None
else:
    cmd = None
    action = 'Fallback: python -m chromadb'

print('\n=== Chroma start plan ===')
print('Action:', action)

if not args.execute:
    print('\nDry-run: pass --execute to actually run it')
    sys.exit(0)

# If --execute: perform the chosen action
if chroma_server and cmd:
    # run uvicorn with the module:app syntax
    try:
        logging.info('Starting uvicorn...')
        subprocess.check_call(list(cmd))
    except Exception as e:
        logging.error(f'Failed to start uvicorn: {e}')
        sys.exit(2)
else:
    # Try python -m chromadb
    try:
        logging.info('Attempting to run `python -m chromadb`')
        subprocess.check_call([sys.executable, '-m', 'chromadb'])
    except Exception as e:
        logging.error(f'Failed to start chromadb via -m: {e}')
        sys.exit(3)
