#!/usr/bin/env python3
"""Static scan of adapter sources to find unsafe calls to optional factories.

Searches for direct calls like `get_unified_database_strategy()` which may raise
`NoneType is not callable` if the name is None during runtime. Reports file and
line numbers to guide small defensive fixes.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_GLOB = ROOT.glob('database_api_*.py')

CALL_PATTERN = re.compile(r"get_unified_database_strategy\s*\(")
ASSIGN_PATTERN = re.compile(r"\bself\.strategy\s*=\s*get_unified_database_strategy\s*\(")
UDS_CALL_GENERIC = re.compile(r"UnifiedDatabaseStrategy\s*\(")

results = []
for p in sorted(ADAPTER_GLOB):
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    file_issues = []
    for i, line in enumerate(lines, start=1):
        if CALL_PATTERN.search(line):
            file_issues.append((i, line.strip()))
        elif ASSIGN_PATTERN.search(line):
            file_issues.append((i, line.strip()))
        elif UDS_CALL_GENERIC.search(line):
            file_issues.append((i, line.strip()))
    if file_issues:
        results.append((str(p), file_issues))

if not results:
    print('No direct UDS3-call patterns found in adapter files.')
    sys.exit(0)

print('Possible unsafe UDS3 calls detected:')
for fname, issues in results:
    print(f"\nFile: {fname}")
    for ln, src in issues:
        print(f"  {ln}: {src}")

print('\nRecommendation: wrap calls to get_unified_database_strategy() with a callable check or try/except, e.g.:')
print('    try:')
print('        if callable(get_unified_database_strategy):')
print('            self.strategy = get_unified_database_strategy()')
print('        else:')
print('            self.strategy = None')
print('    except Exception as exc:')
print("        logger.warning(f'UDS3 init failed: {exc}')\n        self.strategy = None")
