"""Conservative codemod to annotate module-level variables.

It searches for top-level assignments like:
  name = None
  items: list[Any] = []
  mapping: dict[Any, Any] = {}

and rewrites them to include a typing annotation:
  name: Any = None
  items: list[Any] = []
  mapping: dict[Any, Any] = {}

The script avoids magic names (dunder), uppercase constants, and files in venv/docs/security.
Run, review changes and run mypy to observe progress.
"""
import re
from pathlib import Path
from typing import Tuple, Any

ROOT = Path(__file__).resolve().parents[1]
PY_GLOB = "**/*.py"

# Patterns
ASSIGN_NONE_RE = re.compile(r'^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*None\s*(#.*)?$')
ASSIGN_LIST_RE = re.compile(r'^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\[\]\s*(#.*)?$')
ASSIGN_DICT_RE = re.compile(r'^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{\}\s*(#.*)?$')


def should_skip_name(name: str) -> bool:
    # skip dunder and all-caps constants
    if name.startswith("__") and name.endswith("__"):
        return True
    if name.isupper():
        return True
    return False


def annotate_lines(lines: list[str]) -> Tuple[list[str], bool]:
    changed = False
    new_lines: list[Any] = []
    for i, line in enumerate(lines):
        stripped = line.rstrip('\n')
        # only consider top-level (no indentation)
        if stripped.startswith(' ') or stripped.startswith('\t'):
            new_lines.append(line)
            continue

        m_none = ASSIGN_NONE_RE.match(stripped)
        if m_none:
            name = m_none.group('name')
            if should_skip_name(name):
                new_lines.append(line)
                continue
            new_line = f"{name}: Any = None\n"
            new_lines.append(new_line)
            changed = True
            continue

        m_list = ASSIGN_LIST_RE.match(stripped)
        if m_list:
            name = m_list.group('name')
            if should_skip_name(name):
                new_lines.append(line)
                continue
            new_line = f"{name}: list[Any] = []\n"
            new_lines.append(new_line)
            changed = True
            continue

        m_dict = ASSIGN_DICT_RE.match(stripped)
        if m_dict:
            name = m_dict.group('name')
            if should_skip_name(name):
                new_lines.append(line)
                continue
            new_line = f"{name}: dict[Any, Any] = {{}}\n"
            new_lines.append(new_line)
            changed = True
            continue

        new_lines.append(line)

    return new_lines, changed


def ensure_any_import(lines: list[str]) -> Tuple[list[str], bool]:
    text = ''.join(lines)
    if 'Any' not in text:
        return lines, False
    # if there's a typing import, try to append Any
    for i, line in enumerate(lines[:50]):
        if line.startswith('from typing import'):
            if 'Any' in line:
                return lines, False
            lines[i] = line.rstrip('\n') + ', Any\n'
            return lines, True
    # otherwise insert a new import after module docstring or at top
    insert_at = 0
    if lines and lines[0].startswith(('"""', "'''")):
        # find end of docstring
        for j in range(1, min(50, len(lines))):
            if lines[j].strip().endswith('"""') or lines[j].strip().endswith("'''"):
                insert_at = j + 1
                break
    lines.insert(insert_at, 'from typing import Any\n')
    return lines, True


def process_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    # skip venv, __pycache__, docs, security, third_party_stubs
    if any(part in ('.venv', '__pycache__', 'docs', 'security', 'third_party_stubs') for part in path.parts):
        return False

    lines = text.splitlines(keepends=True)
    new_lines, changed = annotate_lines(lines)
    if not changed:
        return False

    new_lines, import_added = ensure_any_import(new_lines)
    path.write_text(''.join(new_lines), encoding='utf-8')
    print(f'Annotated: {path} (+import={import_added})')
    return True


def main() -> None:
    patched = 0
    for p in ROOT.glob(PY_GLOB):
        try:
            if process_file(p):
                patched += 1
        except Exception as e:
            print(f'Error {p}: {e}')
    print(f'Done. Files patched: {patched}')


if __name__ == '__main__':
    main()
