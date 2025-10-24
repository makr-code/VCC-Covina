#!/usr/bin/env python3
"""Fix all postgres_backend.connect() calls in main_backend.py"""

import re

# Read file
with open('main_backend.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace pattern: Comment out all postgres_backend.connect() EXCEPT the initial one (line 231)
lines = content.split('\n')
new_lines = []
in_startup_block = False

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Check if we're in the startup block (around line 220-240)
    if 220 <= line_num <= 240:
        in_startup_block = True
    else:
        in_startup_block = False
    
    # Comment out postgres_backend.connect() EXCEPT in startup block
    if 'postgres_backend.connect()' in line and not in_startup_block:
        # Check if already commented
        if not line.strip().startswith('#'):
            # Add comment
            indent = len(line) - len(line.lstrip())
            commented_line = ' ' * indent + f"# {line.strip()}  # ← Backend bereits connected beim Start!"
            new_lines.append(commented_line)
            print(f"Line {line_num}: Commented out - {line.strip()}")
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# Write back
new_content = '\n'.join(new_lines)
with open('main_backend.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\n✅ Fixed all postgres_backend.connect() calls!")
print("   Kept only the initial connect() in startup block (line 231)")
print("   All other connect() calls are now commented out")
