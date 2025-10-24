"""
Polyglot Admin Tool - Package Initializer

Exposes main components for easy import.
"""

from .utils.branding import (
    CovinarBranding,
    CovinaBrandingHeader,
    CovinaStatusBar,
    apply_covina_style,
    create_branded_window
)

__version__ = "1.0.0"
__author__ = "Covina System"

__all__ = [
    "CovinarBranding",
    "CovinaBrandingHeader", 
    "CovinaStatusBar",
    "apply_covina_style",
    "create_branded_window"
]
