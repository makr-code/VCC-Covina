import sys
from pathlib import Path
# Ensure project root on sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

try:
    import frontend.main  # Import should NOT start GUI (guarded by __name__)
    print("IMPORT_OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("IMPORT_FAIL")
    raise
