#!/usr/bin/env python3
"""Check all database_api_* adapters for import/initialization errors.

The script imports each module under the `database` package matching
`database_api_*.py`, locates classes whose name ends with 'Backend' or a
`get_backend_class` function, and attempts a safe instantiation with a
minimal config. It catches and reports any exceptions so we can find
adapters that call non-callable globals or rely on missing optional
dependencies.
"""
import sys
import traceback
import importlib
from pathlib import Path
import pkgutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PACKAGE = 'database'
PREFIX = 'database.database_api_'


def find_adapter_modules():
    pkg = importlib.import_module(PACKAGE)
    pkgpath = getattr(pkg, '__path__', None)
    if not pkgpath:
        return []
    mods = []
    for finder, name, ispkg in pkgutil.iter_modules(pkgpath):
        if name.startswith('database_api_'):
            mods.append(f"{PACKAGE}.{name}")
    return sorted(mods)


def safe_instantiate(cls, config):
    try:
        inst = cls(config)
    except TypeError:
        # maybe no-arg constructor
        try:
            inst = cls()
        except Exception as e:
            raise
    return inst


def test_module(module_name: str):
    results = []
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        return {'module': module_name, 'import_error': traceback.format_exc()}

    # 1) If module exposes get_backend_class, try that
    if hasattr(mod, 'get_backend_class') and callable(getattr(mod, 'get_backend_class')):
        try:
            cls = mod.get_backend_class()
            try:
                inst = safe_instantiate(cls, {})
                results.append({'class': getattr(cls, '__name__', str(cls)), 'init': 'ok'})
            except Exception:
                results.append({'class': getattr(cls, '__name__', str(cls)), 'init_error': traceback.format_exc()})
        except Exception:
            results.append({'get_backend_class_error': traceback.format_exc()})

    # 2) scan for classes ending with Backend
    for attr in dir(mod):
        if attr.endswith('Backend'):
            obj = getattr(mod, attr)
            if isinstance(obj, type):
                try:
                    inst = safe_instantiate(obj, {})
                    # Do NOT call connect() here to avoid blocking/side-effects.
                    # Instead report that connect() is available so you can
                    # decide to test it manually with a short timeout.
                    if hasattr(inst, 'connect') and callable(getattr(inst, 'connect')):
                        results.append({'class': attr, 'init': 'ok', 'connect_method': True})
                    else:
                        results.append({'class': attr, 'init': 'ok', 'connect_method': False})
                    # attempt graceful disconnect only if exists
                    try:
                        if hasattr(inst, 'disconnect') and callable(getattr(inst, 'disconnect')):
                            try:
                                inst.disconnect()
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    results.append({'class': attr, 'init_error': traceback.format_exc()})

    return {'module': module_name, 'results': results}


def main():
    modules = find_adapter_modules()
    summary = []
    print(f"Found {len(modules)} adapter modules to check:\n")
    for m in modules:
        print(f"--- {m} ---")
        res = test_module(m)
        summary.append(res)
        if 'import_error' in res:
            print('IMPORT ERROR')
            print(res['import_error'])
        else:
            for item in res.get('results', []):
                if 'init' in item and item['init'] == 'ok':
                    s = f"OK: {item.get('class')}"
                    if 'connect_result' in item:
                        s += f" connect_result={item['connect_result']}"
                    if 'connect_error' in item:
                        s += f" connect_error=\n{item['connect_error']}"
                    print(s)
                else:
                    print('ERROR:', item)
        print()

    print('\nSummary:')
    for s in summary:
        module = s['module']
        if 'import_error' in s:
            print(f"{module}: IMPORT_ERROR")
        else:
            problems = [r for r in s.get('results', []) if r.get('init_error') or r.get('connect_error') or 'get_backend_class_error' in r]
            if problems:
                print(f"{module}: ISSUES ({len(problems)})")
            else:
                print(f"{module}: OK")


if __name__ == '__main__':
    main()
