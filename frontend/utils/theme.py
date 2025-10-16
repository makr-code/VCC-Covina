"""
Theme Configuration
===================

Tkinter ttk.Style Configuration mit Dark/Light Theme Support
"""

from tkinter import ttk

from frontend.config import COLORS, FONTS


class ThemeManager:
    """Theme Manager für Covina LiveView"""
    
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style()
        self.current_theme = "dark"
        
        self._setup_dark_theme()
    
    def _setup_dark_theme(self):
        """Configure dark theme"""
        self.style.theme_use('clam')
        
        # Background colors
        self.style.configure('.',
                           background=COLORS["background"],
                           foreground=COLORS["foreground"],
                           fieldbackground=COLORS["panel"],
                           bordercolor=COLORS["border"])
        
        # Notebook (Tabs)
        self.style.configure('TNotebook',
                           background=COLORS["background"],
                           borderwidth=0)
        
        self.style.configure('TNotebook.Tab',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           font=FONTS["body"],
                           padding=[20, 10],
                           borderwidth=1)
        
        self.style.map('TNotebook.Tab',
                      background=[('selected', COLORS["info"])],
                      foreground=[('selected', '#ffffff')])
        
        # Frames
        self.style.configure('TFrame',
                           background=COLORS["panel"],
                           borderwidth=1,
                           relief='flat')
        
        # LabelFrame
        self.style.configure('TLabelframe',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           bordercolor=COLORS["border"],
                           borderwidth=1)
        
        self.style.configure('TLabelframe.Label',
                           background=COLORS["panel"],
                           foreground=COLORS["info"],
                           font=FONTS["subtitle"])
        
        # Labels
        self.style.configure('TLabel',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           font=FONTS["body"])
        
        self.style.configure('Title.TLabel',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           font=FONTS["title"])
        
        self.style.configure('Body.TLabel',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           font=FONTS["body"])
        
        self.style.configure('Small.TLabel',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           font=FONTS["small"])
        
        # Buttons
        self.style.configure('TButton',
                           background=COLORS["info"],
                           foreground='#ffffff',
                           font=FONTS["body"],
                           borderwidth=1,
                           relief='raised',
                           padding=[10, 5])
        
        self.style.map('TButton',
                      background=[('active', COLORS["primary"])],
                      relief=[('pressed', 'sunken')])
        
        # Combobox
        self.style.configure('TCombobox',
                           fieldbackground=COLORS["panel"],
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           arrowcolor=COLORS["foreground"],
                           bordercolor=COLORS["border"])
        
        # Treeview (Tables)
        self.style.configure('Treeview',
                           background=COLORS["panel"],
                           foreground=COLORS["foreground"],
                           fieldbackground=COLORS["panel"],
                           borderwidth=0,
                           font=FONTS["body"])
        
        self.style.configure('Treeview.Heading',
                           background=COLORS["info"],
                           foreground='#ffffff',
                           font=FONTS["subtitle"],
                           borderwidth=1,
                           relief='raised')
        
        self.style.map('Treeview',
                      background=[('selected', COLORS["info"])],
                      foreground=[('selected', '#ffffff')])
        
        # Scrollbar
        self.style.configure('TScrollbar',
                           background=COLORS["panel"],
                           troughcolor=COLORS["background"],
                           bordercolor=COLORS["border"],
                           arrowcolor=COLORS["foreground"])
        
        # Progressbar
        self.style.configure('TProgressbar',
                           background=COLORS["success"],
                           troughcolor=COLORS["panel"],
                           borderwidth=0,
                           thickness=20)
    
    def _setup_light_theme(self):
        """Configure light theme (coming soon)"""
        # TODO: Implement light theme
        pass
    
    def toggle_theme(self):
        """Toggle between dark and light theme"""
        if self.current_theme == "dark":
            self._setup_light_theme()
            self.current_theme = "light"
        else:
            self._setup_dark_theme()
            self.current_theme = "dark"
    
    def get_current_theme(self):
        """Get current theme name"""
        return self.current_theme


def setup_theme(root):
    """
    Setup theme for root window
    
    Args:
        root: Tkinter root window
    
    Returns:
        ThemeManager instance
    """
    return ThemeManager(root)
