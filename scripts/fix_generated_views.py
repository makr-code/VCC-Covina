"""
Fix escaped newlines in generated view files.

Replaces literal \n with actual newlines.
"""

import re
from pathlib import Path

view_files = [
    "frontend/views/database_health_view_migrated.py",
    "frontend/views/error_tracking_view_migrated.py",
    "frontend/views/golden_dataset_view_migrated.py",
    "frontend/views/security_view_migrated.py",
]

print("Fixing escaped newlines in generated views...")
print("=" * 60)

for filepath in view_files:
    path = Path(filepath)
    
    if not path.exists():
        print(f"⚠️  File not found: {filepath}")
        continue
    
    # Read file
    content = path.read_text(encoding='utf-8')
    original_content = content
    
    # Replace \n with actual newlines (but keep proper indentation)
    # Pattern: )\n        self.event_bus
    content = re.sub(
        r'\)\\n\s+self\.event_bus',
        r')\n        self.event_bus',
        content
    )
    
    if content != original_content:
        path.write_text(content, encoding='utf-8')
        print(f"✅ Fixed: {filepath}")
    else:
        print(f"⏭️  No changes: {filepath}")

print("=" * 60)
print("✅ All files processed!")
