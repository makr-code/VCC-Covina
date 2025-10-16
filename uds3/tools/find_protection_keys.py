from typing import Any
#!/usr/bin/env python3
"""Find files containing protection/license key markers and report them.

This tool intentionally does NOT print or store key values. It only records
which files contain the markers (e.g. module_licence_key, module_file_key,
VERITAS PROTECTION KEYS) so they can be reviewed with legal/licensing.

Usage:
    python tools/find_protection_keys.py > security/key_inventory.md

"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKERS = [
    r"VERITAS PROTECTION KEYS",
    r"module_licence_key",
    r"module_file_key",
    r"module_licenced_organization",
]

pattern = re.compile("|".join(re.escape(m) for m in MARKERS), re.IGNORECASE)

results: list[Any] = []
for p in ROOT.rglob("*.py"):
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if pattern.search(text):
        # count occurrences
        occ = [m.group(0) for m in pattern.finditer(text)]
        results.append((str(p.relative_to(ROOT)), sorted(set(occ))))

# Print a markdown inventory without exposing any secret values
print("# Protection Keys Inventory")
print()
print(
    "This report lists files that contain protected/license markers (e.g. VERITAS protection markers).\nThe script does NOT display key values. Review and handle these files according to your license policies."
)
print()
print(f"Repository root: {ROOT}")
print()
if not results:
    print("No protection markers found.")
else:
    for path, markers in sorted(results):
        print(f"- **{path}**")
        for m in markers:
            print(f"  - Marker: `{m}`")
        print()

print(
    "\n\n**Note**: Do NOT remove or modify embedded protection markers without explicit approval from the license owner. If changes are required, coordinate with legal/compliance before committing."
)
