#!/usr/bin/env python3
"""Test connectivity to Neo4j instance(s).

Runs native driver test if `neo4j` package is available, else does HTTP/TCP probes.
"""
import sys
from urllib.parse import urljoin
from pathlib import Path
import socket
import requests
import traceback

HOST = '192.168.178.94'
HTTP_PORTS = [32772, 32773]
BOLT_PORT = 32774

print('Testing Neo4j connectivity to', HOST)

# Try native neo4j driver
try:
    from neo4j import GraphDatabase
    print('neo4j driver available')
    uri = f'bolt://{HOST}:{BOLT_PORT}'
    print('Trying bolt URI', uri)
    try:
        driver = GraphDatabase.driver(uri, auth=('neo4j', 'neo4j'))
        with driver.session() as session:
            res = session.run('RETURN 1')
            v = list(res)
            print('Bolt test query returned rows:', len(v))
        driver.close()
    except Exception as e:
        print('Bolt driver connect failed:', e)
except Exception as e:
    print('neo4j driver not available or failed to import:', e)
    traceback.print_exc()

# HTTP probes
for p in HTTP_PORTS:
    try:
        url = f'http://{HOST}:{p}/'
        print('HTTP probe', url)
        r = requests.get(url, timeout=5)
        print('->', r.status_code)
        print('body:', r.text[:200])
    except Exception as e:
        print('HTTP probe failed for', p, e)

# TCP probe for bolt
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((HOST, BOLT_PORT))
    print('TCP connect to bolt port succeeded')
    s.close()
except Exception as e:
    print('TCP connect to bolt failed:', e)

print('Done')
