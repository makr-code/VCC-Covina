"""Project-level sitecustomize to expose sibling repositories.

Python automatically imports this module (if present on sys.path) during start-up
via the built-in `site` module. By inserting the parent folder and the sibling
`uds3` and `database` packages into ``sys.path`` we can keep the rest of the
codebase free from manual path hacks while still allowing direct imports such as
``import uds3`` or ``from database import ...``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ============================================================================
# Neo4j Python 3.13 Socket-Kompatibilitäts-Patch
# ============================================================================
# MUSS VOR ALLEN IMPORTS PASSIEREN - sitecustomize wird automatisch geladen
import socket
if not hasattr(socket, 'EAI_ADDRFAMILY'):
    socket.EAI_ADDRFAMILY = socket.EAI_FAIL
if not hasattr(socket, 'EAI_NODATA'):
    socket.EAI_NODATA = socket.EAI_NONAME
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent

# UDS3 Package liegt in C:\VCC (eine Ebene höher)
# Wir fügen C:\VCC zum Path hinzu, damit "import uds3.database.xxx" funktioniert
VCC_ROOT = PROJECT_ROOT.parent  # C:\VCC
UDS3_ROOT = VCC_ROOT / "uds3"  # C:\VCC\uds3

EXTRA_PATHS = [
    PROJECT_ROOT,        # C:\VCC\Covina (für Covina-Module)
    VCC_ROOT,           # C:\VCC (für "import uds3")
    UDS3_ROOT,          # C:\VCC\uds3 (für "from database import")
]

for path in EXTRA_PATHS:
    path_str = str(path)
    if path.exists() and path_str not in sys.path:
        sys.path.insert(0, path_str)

# Preload critical local packages so later sys.path changes won't break imports
try:
    import security  # noqa: F401
    import security.auth  # noqa: F401
    import security.secrets  # noqa: F401
except Exception:
    # Do not fail startup if optional modules are missing in certain contexts
    pass
