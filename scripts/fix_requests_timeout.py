#!/usr/bin/env python3
"""
Automated Fix Script: Add timeout=30 to all requests.get/post/put/delete/patch calls
Fixes Bandit B113 (request_without_timeout) vulnerability.

Usage:
    python scripts/fix_requests_timeout.py [--dry-run] [--timeout 30]
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple

# Patterns to match requests calls without timeout
PATTERNS = [
    # Pattern 1: requests.get(...) without timeout
    (r'(requests\.(get|post|put|delete|patch)\([^)]*)\)', r'\1, timeout={timeout})'),
    
    # Pattern 2: Already has timeout (skip)
    (r'requests\.(get|post|put|delete|patch)\([^)]*timeout\s*=', None),
]

def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped"""
    skip_patterns = [
        '__pycache__',
        '.git',
        '.venv',
        'venv',
        'node_modules',
        '.pyc',
    ]
    
    return any(pattern in str(file_path) for pattern in skip_patterns)

def already_has_timeout(line: str) -> bool:
    """Check if line already has timeout parameter"""
    return 'timeout=' in line or 'timeout =' in line

def fix_line(line: str, timeout: int = 30) -> Tuple[str, bool]:
    """
    Fix a single line by adding timeout parameter.
    Returns (fixed_line, was_changed)
    """
    if already_has_timeout(line):
        return line, False
    
    # Match requests.METHOD(...) pattern
    pattern = r'(requests\.(get|post|put|delete|patch)\([^)]*)\)'
    
    if not re.search(pattern, line):
        return line, False
    
    # Add timeout before closing parenthesis
    fixed = re.sub(pattern, rf'\1, timeout={timeout})', line)
    
    return fixed, (fixed != line)

def fix_file(file_path: Path, timeout: int = 30, dry_run: bool = False) -> int:
    """
    Fix all requests calls in a file.
    Returns number of changes made.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.splitlines(keepends=True)
        
        changed_lines = 0
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            fixed_line, was_changed = fix_line(line, timeout)
            new_lines.append(fixed_line)
            
            if was_changed:
                changed_lines += 1
                if dry_run:
                    print(f"  Line {i}: {line.strip()}")
                    print(f"       → {fixed_line.strip()}")
        
        if changed_lines > 0 and not dry_run:
            file_path.write_text(''.join(new_lines), encoding='utf-8')
            print(f"✅ Fixed {changed_lines} lines in {file_path}")
        
        return changed_lines
    
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description='Fix requests timeout issues')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout value in seconds (default: 30)')
    parser.add_argument('--path', type=str, default='.', help='Root path to scan (default: current dir)')
    
    args = parser.parse_args()
    
    root_path = Path(args.path)
    
    if not root_path.exists():
        print(f"❌ Path not found: {root_path}")
        sys.exit(1)
    
    print(f"🔍 Scanning for requests calls without timeout...")
    print(f"   Path: {root_path}")
    print(f"   Timeout: {args.timeout}s")
    print(f"   Mode: {'DRY-RUN' if args.dry_run else 'LIVE FIX'}")
    print()
    
    # Find all Python files
    python_files = [f for f in root_path.rglob('*.py') if not should_skip_file(f)]
    
    total_changes = 0
    files_changed = 0
    
    for file_path in python_files:
        changes = fix_file(file_path, args.timeout, args.dry_run)
        if changes > 0:
            total_changes += changes
            files_changed += 1
    
    print()
    print(f"📊 Summary:")
    print(f"   Files scanned: {len(python_files)}")
    print(f"   Files changed: {files_changed}")
    print(f"   Total fixes: {total_changes}")
    
    if args.dry_run:
        print()
        print("⚠️  DRY-RUN mode: No files were modified")
        print("   Run without --dry-run to apply changes")

if __name__ == '__main__':
    main()
