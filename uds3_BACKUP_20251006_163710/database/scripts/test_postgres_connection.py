#!/usr/bin/env python3
"""Test connectivity to PostgreSQL instance.

Tries psycopg2 if available, otherwise does a TCP probe.
"""
import sys
import socket
import traceback

HOST = '192.168.178.94'
PORT = 5432

print('Testing PostgreSQL connectivity to', f'{HOST}:{PORT}')

# Try psycopg2
try:
    import psycopg2
    print('psycopg2 available')
    try:
        conn = psycopg2.connect(host=HOST, port=PORT, user='postgres', password='', dbname='postgres', connect_timeout=5)
        print('psycopg2 connect succeeded')
        conn.close()
    except Exception as e:
        print('psycopg2 connect failed:', e)
except Exception as e:
    print('psycopg2 not available:', e)
    traceback.print_exc()

# TCP probe
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((HOST, PORT))
    print('TCP connect succeeded')
    s.close()
except Exception as e:
    print('TCP connect failed:', e)

print('Done')
