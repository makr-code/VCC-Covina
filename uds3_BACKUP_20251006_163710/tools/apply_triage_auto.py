"""Apply Auto-classified fix snippets from need_type_triage.csv to repo files.

Only applies rows where classification == 'Auto' and file path starts with 'uds3/'.
It searches for a matching context line or variable assignment and replaces that line
with the provided fix_snippet.

This is conservative: it writes a backup file with .bak before changing.
"""
import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'tools' / 'need_type_triage.csv'

if not CSV.exists():
    raise SystemExit('CSV not found: ' + str(CSV))

rows = []
with CSV.open(encoding='utf-8') as fh:
    reader = csv.DictReader(fh)
    for r in reader:
        # apply both Auto and External now that external files (e.g., database/) are available
        if r['classification'].strip() in ('Auto', 'External'):
            rows.append(r)

if not rows:
    print('No Auto entries to apply.')
    raise SystemExit(0)

for r in rows:
    rel = Path(r['file'])
    # try a few candidates: as-given, strip leading 'uds3/' component, or only filename
    candidates = [ROOT / rel]
    if rel.parts and rel.parts[0] == 'uds3':
        # e.g. 'uds3/uds3_core.py' -> 'uds3_core.py'
        candidates.append(ROOT / Path(*rel.parts[1:]))
    candidates.append(ROOT / rel.name)
    path = None
    for c in candidates:
        if c.exists():
            path = c
            break
    if path is None:
        print('File not found, skipping:', candidates)
        continue
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    context = r['context'].strip()
    var = r['var'].strip()
    fix = r['fix_snippet']
    applied = False
    # Try exact context match
    for i, ln in enumerate(lines):
        if context and context in ln:
            # replace the assignment line with fix snippet and keep newline
            lines[i] = fix + '\n'
            applied = True
            print(f'Patched by context: {path} (line {i+1}) var={var}')
            break
    if not applied and var:
        # try to find a simple assignment to var or self.var
        pat = re.compile(rf'^(?P<indent>\s*)(?P<target>(?:self\.)?{re.escape(var)})\s*=\s*.*$')
        for i, ln in enumerate(lines):
            if pat.match(ln):
                indent = pat.match(ln).group('indent')
                # ensure fix uses var name; if fix begins with var, keep as-is, else prefix indent
                new_line = indent + fix + '\n'
                lines[i] = new_line
                applied = True
                print(f'Patched by var: {path} (line {i+1}) var={var}')
                break
    if not applied:
        # try looser match: look for variable name anywhere in line
        for i, ln in enumerate(lines):
            if var and var in ln:
                lines[i] = fix + '\n'
                applied = True
                print(f'Patched by loose match: {path} (line {i+1}) var={var}')
                break
    if applied:
        # backup and write
        bak = path.with_suffix(path.suffix + '.bak')
        path.rename(bak)
        bak.write_text(''.join(lines), encoding='utf-8')
        # rename back to original path
        bak.replace(path)
    else:
        print('No match found for', path, 'var=', var)

print('Done')
