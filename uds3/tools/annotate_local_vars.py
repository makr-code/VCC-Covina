"""Annotate simple untyped assignments to lists/dicts/queues with conservative Any types.

Targets:
 - name = [] or name = {}
 - self.name = [] or self.name = {}
 - name = PriorityQueue()
 - self.name = PriorityQueue()

Behaviour: insert an inline annotation if possible:
 - self.name: list[Any] = []
 - name: dict[Any, Any] = {}

This is conservative: uses Any for element types and avoids changing logic.
"""
import re
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
PY_GLOB = '**/*.py'

ASSIGN_SIMPLE_RE = re.compile(r'^(?P<indent>\s*)(?P<target>(?:self\.)?[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>\[\]|\{\}|PriorityQueue\(\))\s*(#.*)?$')


def annotate_lines(lines: list[str]) -> Tuple[list[str], bool]:
    changed = False
    new_lines: list[str] = []
    for line in lines:
        m = ASSIGN_SIMPLE_RE.match(line.rstrip('\n'))
        if not m:
            new_lines.append(line)
            continue
        indent = m.group('indent')
        target = m.group('target')
        value = m.group('value')
        # decide annotation
        if value == '[]':
            ann = 'list[Any]'
        elif value == '{}':
            ann = 'dict[Any, Any]'
        elif value.startswith('PriorityQueue'):
            ann = 'PriorityQueue[Any]'
        else:
            ann = 'Any'
        new_line = f"{indent}{target}: {ann} = {value}\n"
        new_lines.append(new_line)
        changed = True
    return new_lines, changed


def ensure_imports(lines: list[str]) -> Tuple[list[str], bool]:
    text = ''.join(lines)
    need_any = 'Any' in text
    need_queue = 'PriorityQueue' in text
    changed = False
    if need_any:
        # ensure 'from typing import Any' exists
        for i in range(min(60, len(lines))):
            if lines[i].startswith('from typing import'):
                if 'Any' in lines[i]:
                    break
                lines[i] = lines[i].rstrip('\n') + ', Any\n'
                changed = True
                break
        else:
            # insert after docstring or at top
            insert_at = 0
            if lines and lines[0].startswith(('"""', "'''")):
                for j in range(1, min(60, len(lines))):
                    if lines[j].strip().endswith('"""') or lines[j].strip().endswith("'''"):
                        insert_at = j+1
                        break
            lines.insert(insert_at, 'from typing import Any\n')
            changed = True
    if need_queue:
        # ensure PriorityQueue is imported from queue
        for i in range(min(60, len(lines))):
            if lines[i].startswith('from queue import') and 'PriorityQueue' in lines[i]:
                break
        else:
            lines.insert(0, 'from queue import PriorityQueue\n')
            changed = True
    return lines, changed


def process_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')
    if any(part in ('.venv', '__pycache__', 'docs', 'security', 'third_party_stubs') for part in path.parts):
        return False
    lines = text.splitlines(keepends=True)
    new_lines, changed = annotate_lines(lines)
    if not changed:
        return False
    new_lines, imports_changed = ensure_imports(new_lines)
    path.write_text(''.join(new_lines), encoding='utf-8')
    print(f'Patched: {path} (+imports={imports_changed})')
    return True


def main() -> None:
    patched = 0
    for p in ROOT.glob(PY_GLOB):
        try:
            if process_file(p):
                patched += 1
        except Exception as e:
            print('Error', p, e)
    print('Done. Files patched:', patched)


if __name__ == '__main__':
    main()
