"""Parse mypy output and generate a triage CSV for remaining 'Need type annotation' errors.

Reads: tools/mypy_output_after_codmod.txt
Writes: tools/need_type_triage.csv

Heuristics:
 - Files under 'database\' -> classification External
 - Known var names mapped to likely collection types -> Auto
 - operation_plan, word_freq -> Manual
 - Otherwise -> Auto (conservative)
"""
import re
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'tools' / 'mypy_output_after_codmod.txt'
OUTPUT = ROOT / 'tools' / 'need_type_triage.csv'

VAR_MAP = {
    '_adaptive_processors': 'dict[Any, Any]',
    'results': 'dict[Any, Any]',
    'document_mapping': 'dict[Any, Any]',
    'batch_operations': 'list[Any]',
    'operation_plan': 'dict[str, Any]',
    'geo_info': 'dict[str, Any]',
    'relationships': 'list[Any]',
    'result': 'Any',
    'admin_areas': 'list[Any]',
    'stats': 'dict[str, Any]',
    'categories': 'dict[str, Any]',
    'issue_frequency': 'dict[str, Any]',
    'word_freq': 'dict[str, int]',
}

RE_NEED = re.compile(r'^(?P<path>[^:]+):(?P<lineno>\d+):(?P<col>\d+)?:?\s*error: Need type annotation for "?(?P<var>[\w_\"]+)"?', re.IGNORECASE)
RE_NEED_ALT = re.compile(r'error: Need type annotation for\s*(?P<var>"[^"]+"|[\w_]+)', re.IGNORECASE)

rows = []
if not INPUT.exists():
    raise SystemExit(f'Input file not found: {INPUT}')

text = INPUT.read_text(encoding='utf-8')
lines = text.splitlines()
for i, line in enumerate(lines):
    if 'Need type annotation' in line:
        # try to extract path/line from this or nearby lines
        m = RE_NEED.search(line)
        path = ''
        lineno = ''
        var = ''
        if m:
            path = m.group('path')
            lineno = m.group('lineno')
            var = m.group('var').strip('"')
        else:
            # look back up to 3 lines to find a path prefix
            for j in range(max(0, i-3), i+1):
                if ':' in lines[j]:
                    parts = lines[j].split(':')
                    if len(parts) >= 3 and parts[0].endswith('.py'):
                        path = parts[0]
                        try:
                            lineno = parts[1]
                        except Exception:
                            lineno = ''
                        break
            m2 = RE_NEED_ALT.search(line)
            if m2:
                var = m2.group('var').strip('"')
        # normalize path
        path = path.replace('\\', '/')
        classification = 'Auto'
        suggested = ''
        if path.startswith('database/') or path.startswith('database\\') or path.lower().startswith('database'):
            classification = 'External'
        if var in VAR_MAP:
            suggested = VAR_MAP[var]
            if var in ('operation_plan', 'word_freq'):
                classification = 'Manual'
        else:
            # fallback guesses
            if var.startswith('_'):
                suggested = 'dict[Any, Any]'
            elif var.startswith('is_') or var.startswith('has_'):
                suggested = 'bool'
            else:
                suggested = 'Any'
        context = ''
        # capture following few chars for context
        snippet = lines[i].strip()
        rows.append({'file': path, 'line': lineno, 'var': var, 'context': snippet, 'classification': classification, 'suggested': suggested})

# write CSV
with OUTPUT.open('w', newline='', encoding='utf-8') as fh:
    writer = csv.DictWriter(fh, fieldnames=['file','line','var','context','classification','suggested','fix_snippet'])
    writer.writeheader()
    for r in rows:
        fix = ''
        if r['suggested'].startswith('list'):
            fix = f"{r['var']}: {r['suggested']} = []"
        elif r['suggested'].startswith('dict'):
            fix = f"{r['var']}: {r['suggested']} = {{}}"
        elif r['suggested'] == 'bool':
            fix = f"{r['var']}: bool = False"
        else:
            fix = f"{r['var']}: {r['suggested']} = None"
        writer.writerow({**r, 'fix_snippet': fix})

print(f'Wrote {len(rows)} rows to {OUTPUT}')
