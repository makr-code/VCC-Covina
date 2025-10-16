import sys
import importlib
import socket

checks = []

checks.append(('python_executable', sys.executable))
checks.append(('python_version', sys.version))

# socket attributes
socket_attrs = ['EAI_ADDRFAMILY', 'EAI_AGAIN', 'AF_INET', 'AF_INET6']
for a in socket_attrs:
    checks.append((f'socket.{a}', hasattr(socket, a)))

# try importing neo4j and inspect a typical symbol
for pkg in ('neo4j', 'psycopg', 'psycopg2'):
    try:
        m = importlib.import_module(pkg)
        checks.append((f'import_{pkg}', True))
        # try to access a representative attribute
        if pkg == 'neo4j':
            checks.append(('neo4j.GraphDatabase', hasattr(m, 'GraphDatabase')))
        if pkg.startswith('psycopg'):
            checks.append((f'{pkg}.__name__', getattr(m, '__name__', None)))
    except Exception as e:
        checks.append((f'import_{pkg}', f'error: {e}'))

# print results
for k, v in checks:
    print(f'{k}: {v}')
