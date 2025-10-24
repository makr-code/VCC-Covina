"""
Covina Branding Components

Wiederverwendbare UI-Komponenten für einheitliches Corporate Design.
Alle Covina-Tools nutzen diese Komponenten für konsistentes Branding.

Author: Covina System
Date: 24. Oktober 2025
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple


class CovinarBranding:
    """
    Corporate Identity / Branding Konstanten für Covina-Anwendungen.
    
    Features:
    - Farbschema (Primär, Sekundär, Akzent)
    - Schriftarten (Titel, Normal, Mono)
    - Logo/Schriftzug-Varianten
    - Spacing/Padding-Standards
    """
    
    # Farbpalette (Corporate Design)
    COLOR_PRIMARY = "#0078D7"      # Covina Blau (Microsoft-Style)
    COLOR_SECONDARY = "#F5F5F5"    # Heller Grau (Hintergrund)
    COLOR_ACCENT = "#005A9E"       # Dunkles Blau (Hover/Focus)
    COLOR_TEXT = "#333333"         # Dunkelgrau (Text)
    COLOR_TEXT_LIGHT = "#666666"   # Mittelgrau (Subtitel)
    COLOR_SUCCESS = "#107C10"      # Grün (Success States)
    COLOR_WARNING = "#FF8C00"      # Orange (Warnings)
    COLOR_ERROR = "#E81123"        # Rot (Errors)
    
    # Schriftarten
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_SUBTITLE = ("Segoe UI", 12, "bold")
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_MONO = ("Consolas", 10)
    
    # Spacing (Konsistente Abstände)
    PADDING_SMALL = 5
    PADDING_MEDIUM = 10
    PADDING_LARGE = 20
    
    # Logo/Schriftzug Varianten
    LOGO_TEXT = "COVINA"
    LOGO_ICON = "🔷"  # Unicode Diamond (Platzhalter für echtes Logo)
    TAGLINE = "Polyglot Persistence Platform"
    
    @staticmethod
    def get_window_icon() -> str:
        """Gibt Icon-String für Window.iconbitmap() zurück (wenn verfügbar)."""
        # TODO: Pfad zu echtem .ico File (optional)
        return ""


class CovinaBrandingHeader(ttk.Frame):
    """
    Wiederverwendbare Header-Komponente mit Covina-Branding.
    
    Layout:
    - Links: Titel + Untertitel (vertikal gestapelt)
    - Rechts: Covina Logo/Schriftzug (oben rechts)
    
    Usage:
        header = CovinaBrandingHeader(
            parent, 
            title="Polyglot Admin Tool", 
            subtitle="Document Inspector"
        )
        header.pack(fill=tk.X, padx=10, pady=10)
    """
    
    def __init__(
        self, 
        parent: tk.Widget,
        title: str,
        subtitle: Optional[str] = None,
        show_tagline: bool = False,
        **kwargs
    ):
        """
        Initialisiere Header mit Titel und optionalem Untertitel.
        
        Args:
            parent: Parent Widget (meist Main Window oder Frame)
            title: Haupt-Titel der Anwendung
            subtitle: Optionaler Untertitel (z.B. "Document Inspector")
            show_tagline: Zeige Covina Tagline unter Logo (default: False)
            **kwargs: Zusätzliche ttk.Frame-Parameter
        """
        super().__init__(parent, **kwargs)
        
        # Configure Grid
        self.columnconfigure(0, weight=1)  # Linke Spalte (Titel) wächst
        self.columnconfigure(1, weight=0)  # Rechte Spalte (Logo) fix
        
        # Left Side: Title + Subtitle
        left_frame = ttk.Frame(self)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.N))
        
        # Title
        title_label = ttk.Label(
            left_frame,
            text=title,
            font=CovinarBranding.FONT_TITLE,
            foreground=CovinarBranding.COLOR_TEXT
        )
        title_label.pack(anchor=tk.W)
        
        # Subtitle (optional)
        if subtitle:
            subtitle_label = ttk.Label(
                left_frame,
                text=subtitle,
                font=CovinarBranding.FONT_NORMAL,
                foreground=CovinarBranding.COLOR_TEXT_LIGHT
            )
            subtitle_label.pack(anchor=tk.W)
        
        # Right Side: Covina Logo/Schriftzug
        right_frame = ttk.Frame(self)
        right_frame.grid(row=0, column=1, sticky=(tk.E, tk.N), padx=(20, 0))
        
        # Logo Icon + Text (horizontal)
        logo_container = ttk.Frame(right_frame)
        logo_container.pack(anchor=tk.E)
        
        logo_icon = ttk.Label(
            logo_container,
            text=CovinarBranding.LOGO_ICON,
            font=("Segoe UI", 20),
            foreground=CovinarBranding.COLOR_PRIMARY
        )
        logo_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        logo_text = ttk.Label(
            logo_container,
            text=CovinarBranding.LOGO_TEXT,
            font=("Segoe UI", 18, "bold"),
            foreground=CovinarBranding.COLOR_PRIMARY
        )
        logo_text.pack(side=tk.LEFT)
        
        # Tagline (optional)
        if show_tagline:
            tagline_label = ttk.Label(
                right_frame,
                text=CovinarBranding.TAGLINE,
                font=CovinarBranding.FONT_SMALL,
                foreground=CovinarBranding.COLOR_TEXT_LIGHT
            )
            tagline_label.pack(anchor=tk.E)
        
        # Separator Line (unterhalb Header)
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))


class CovinaStatusBar(ttk.Frame):
    """
    Wiederverwendbare Status-Bar (unten im Fenster).
    
    Features:
    - Status-Nachricht (links)
    - Connection Indicators (rechts): DB-Status, Backend-Status
    - Auto-Clear nach Timeout (optional)
    
    Usage:
        statusbar = CovinaStatusBar(root)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        statusbar.set_status("Ready", "success")
        statusbar.set_connection_status("PostgreSQL", True)
    """
    
    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, relief=tk.SUNKEN, **kwargs)
        
        # Status Message (links)
        self.status_label = ttk.Label(
            self,
            text="Ready",
            font=CovinarBranding.FONT_SMALL,
            foreground=CovinarBranding.COLOR_TEXT_LIGHT
        )
        self.status_label.pack(side=tk.LEFT, padx=CovinarBranding.PADDING_SMALL)
        
        # Connection Indicators (rechts)
        self.connection_frame = ttk.Frame(self)
        self.connection_frame.pack(side=tk.RIGHT, padx=CovinarBranding.PADDING_SMALL)
        
        self.connection_labels = {}
    
    def set_status(self, message: str, status_type: str = "info"):
        """
        Setze Status-Nachricht.
        
        Args:
            message: Status-Text
            status_type: 'info', 'success', 'warning', 'error'
        """
        color_map = {
            "info": CovinarBranding.COLOR_TEXT_LIGHT,
            "success": CovinarBranding.COLOR_SUCCESS,
            "warning": CovinarBranding.COLOR_WARNING,
            "error": CovinarBranding.COLOR_ERROR
        }
        
        self.status_label.config(
            text=message,
            foreground=color_map.get(status_type, CovinarBranding.COLOR_TEXT_LIGHT)
        )
    
    def set_connection_status(self, name: str, connected: bool):
        """
        Zeige/Update Connection Status Indicator.
        
        Args:
            name: Backend-Name (z.B. "PostgreSQL", "ChromaDB")
            connected: True (grün), False (rot)
        """
        if name not in self.connection_labels:
            label = ttk.Label(
                self.connection_frame,
                font=CovinarBranding.FONT_SMALL
            )
            label.pack(side=tk.LEFT, padx=(10, 0))
            self.connection_labels[name] = label
        
        label = self.connection_labels[name]
        icon = "●" if connected else "○"
        color = CovinarBranding.COLOR_SUCCESS if connected else CovinarBranding.COLOR_ERROR
        
        label.config(
            text=f"{icon} {name}",
            foreground=color
        )


# Convenience Functions

def apply_covina_style(root: tk.Tk):
    """
    Wende Covina-Style auf ttk Widgets an.
    
    Konfiguriert ttk.Style mit Covina-Farbschema.
    Sollte einmalig nach tk.Tk() Initialisierung aufgerufen werden.
    
    Args:
        root: tk.Tk() Root Window
    """
    style = ttk.Style(root)
    
    # Theme auswählen (plattformabhängig)
    try:
        style.theme_use('clam')  # Windows: neutral, modern
    except tk.TclError:
        style.theme_use('default')
    
    # Custom Styles
    style.configure(
        'Covina.TButton',
        foreground=CovinarBranding.COLOR_PRIMARY,
        font=CovinarBranding.FONT_NORMAL
    )
    
    style.configure(
        'CovinaAccent.TButton',
        background=CovinarBranding.COLOR_PRIMARY,
        foreground='white',
        font=CovinarBranding.FONT_NORMAL
    )
    
    style.configure(
        'Covina.TLabel',
        font=CovinarBranding.FONT_NORMAL,
        foreground=CovinarBranding.COLOR_TEXT
    )
    
    style.configure(
        'CovinaTitle.TLabel',
        font=CovinarBranding.FONT_TITLE,
        foreground=CovinarBranding.COLOR_TEXT
    )


def create_branded_window(
    title: str,
    geometry: str = "1200x800"
) -> Tuple[tk.Tk, CovinaBrandingHeader, CovinaStatusBar]:
    """
    Factory-Funktion: Erstelle vorbereitetes Tkinter-Fenster mit Covina-Branding.
    
    Inkludiert:
    - Configured Root Window
    - Covina Header (oben)
    - Covina Status Bar (unten)
    - Applied Covina Style
    
    Args:
        title: Window-Titel und Header-Titel
        geometry: Fenstergröße (z.B. "1200x800")
    
    Returns:
        (root, header, statusbar): Konfiguriertes Window + Header + StatusBar
    
    Usage:
        root, header, statusbar = create_branded_window("Polyglot Admin")
        # Füge Content zwischen header und statusbar ein
        content_frame = ttk.Frame(root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        root.mainloop()
    """
    root = tk.Tk()
    root.title(title)
    root.geometry(geometry)
    
    # Apply Covina Style
    apply_covina_style(root)
    
    # Header (oben)
    header = CovinaBrandingHeader(
        root,
        title=title,
        subtitle=None,
        show_tagline=False
    )
    header.pack(fill=tk.X, padx=CovinarBranding.PADDING_LARGE, pady=(CovinarBranding.PADDING_LARGE, 0))
    
    # Status Bar (unten)
    statusbar = CovinaStatusBar(root)
    statusbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    return root, header, statusbar
