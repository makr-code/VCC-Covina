"""
Lightweight frontend.views package initializer.

Hinweis:
- Bewusst KEINE schweren Re-Exports, um Kreis-Importe und fehlende Module zu vermeiden.
- Views werden direkt über ihre Module importiert, z. B.:
    from frontend.views.system_status_view import SystemStatusView
"""

# Optional: Basis-Klasse verfügbar machen (low risk)
try:
    from .base_view import BaseView  # noqa: F401
except Exception:
    # BaseView ist optional; direkte Modul-Imports funktionieren weiterhin
    pass

__all__ = []
