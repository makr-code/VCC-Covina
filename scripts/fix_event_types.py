"""
Quick fix script: Update all widget event emissions to use EventType enums
"""

import re
import os

# Event type mappings
event_mappings = [
    ("SIDEBAR_LEFT_NAVIGATE", "EventType.SIDEBAR_LEFT_NAVIGATE"),
    ("SIDEBAR_LEFT_TOGGLED", "EventType.SIDEBAR_LEFT_TOGGLED"),
    ("SIDEBAR_RIGHT_TOGGLED", "EventType.SIDEBAR_RIGHT_TOGGLED"),
    ("QUICK_ACTION_UPLOAD", "EventType.QUICK_ACTION_UPLOAD"),
    ("QUICK_ACTION_QUERY", "EventType.QUICK_ACTION_QUERY"),
    ("QUICK_ACTION_LOGS", "EventType.QUICK_ACTION_LOGS"),
    ("AI_COMMAND_SUBMITTED", "EventType.AI_COMMAND_SUBMITTED"),
    ("AI_TERMINAL_TOGGLED", "EventType.AI_TERMINAL_TOGGLED"),
    ("STATUS_BAR_BACKEND_UPDATE", "EventType.STATUS_BAR_BACKEND_UPDATE"),
    ("STATUS_BAR_JOBS_UPDATE", "EventType.STATUS_BAR_JOBS_UPDATE"),
    ("STATUS_BAR_RESOURCES_UPDATE", "EventType.STATUS_BAR_RESOURCES_UPDATE"),
    ("STATUS_BAR_PROGRESS_UPDATE", "EventType.STATUS_BAR_PROGRESS_UPDATE"),
    ("TOOLBAR_HAMBURGER_CLICKED", "EventType.TOOLBAR_HAMBURGER_CLICKED"),
    ("TOOLBAR_SETTINGS_CLICKED", "EventType.TOOLBAR_SETTINGS_CLICKED"),
    ("TOOLBAR_PROFILE_CLICKED", "EventType.TOOLBAR_PROFILE_CLICKED"),
]

# Files to update
widget_files = [
    "frontend/widgets/top_toolbar.py",
    "frontend/widgets/sidebar_left.py",
    "frontend/widgets/sidebar_right.py",
    "frontend/widgets/ai_terminal.py",
    "frontend/widgets/status_bar.py",
]

def update_file(filepath):
    """Update a single file with EventType imports and usage."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has EventType import
    has_import = "from frontend.core.event_bus import EventType" in content
    
    # Add import if needed
    if not has_import:
        # Find the last import line
        lines = content.split('\n')
        import_index = -1
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i
        
        if import_index >= 0:
            lines.insert(import_index + 1, "from frontend.core.event_bus import EventType")
            content = '\n'.join(lines)
    
    # Replace string events with EventType
    for string_event, enum_event in event_mappings:
        # Replace patterns like emit("EVENT_NAME", ...) or emit_sync("EVENT_NAME", ...)
        content = re.sub(
            rf'(emit(?:_sync)?)\("({string_event})"',
            rf'\1({enum_event}',
            content
        )
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Updated: {filepath}")

# Update all files
print("Updating widget files to use EventType enums...")
for filepath in widget_files:
    if os.path.exists(filepath):
        update_file(filepath)
    else:
        print(f"⚠️  File not found: {filepath}")

print("\n✅ All files updated!")
