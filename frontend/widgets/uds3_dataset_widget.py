"""
UDS3 Dataset Count Widget
==========================

Matplotlib Bar Chart für Document Counts pro Backend + Classifications Breakdown
"""

import logging
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from typing import Optional, Dict, Any
import warnings

# ✅ Suppress matplotlib font warnings for missing Unicode glyphs
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

from frontend.config import COLORS, FONTS, CHART_COLORS
from frontend.services.api_client import api_client

logger = logging.getLogger(__name__)

# ✅ Chart color palette (using indexed access since CHART_COLORS is a list)
CHART_COLOR_PALETTE = {
    "primary": CHART_COLORS[0] if len(CHART_COLORS) > 0 else "#007bff",
    "success": CHART_COLORS[1] if len(CHART_COLORS) > 1 else "#28a745",
    "info": CHART_COLORS[2] if len(CHART_COLORS) > 2 else "#17a2b8",
    "warning": CHART_COLORS[3] if len(CHART_COLORS) > 3 else "#ffc107",
    "danger": CHART_COLORS[4] if len(CHART_COLORS) > 4 else "#dc3545",
    "secondary": CHART_COLORS[5] if len(CHART_COLORS) > 5 else "#6c757d",
}


class UDS3DatasetWidget(ttk.Frame):
    """UDS3 Dataset Count Widget mit Live-Diagrammen"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        # Data cache
        self.database_stats: Optional[Dict[str, Any]] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all widgets"""
        # Title
        title = ttk.Label(self, text="UDS3 Dataset Overview", style='Title.TLabel')
        title.pack(pady=10, anchor=tk.W, padx=20)
        
        # Main container with two charts
        charts_frame = ttk.Frame(self)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left: Backend Document Counts
        left_frame = ttk.LabelFrame(charts_frame, text="Documents per Backend", padding=10)
        left_frame.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)
        
        self.backend_fig = Figure(figsize=(6, 4), facecolor=COLORS["panel"])
        self.backend_ax = self.backend_fig.add_subplot(111)
        self.backend_canvas = FigureCanvasTkAgg(self.backend_fig, left_frame)
        self.backend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right: Classification Breakdown
        right_frame = ttk.LabelFrame(charts_frame, text="Classification Breakdown", padding=10)
        right_frame.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W), padx=5)
        
        self.classification_fig = Figure(figsize=(6, 4), facecolor=COLORS["panel"])
        self.classification_ax = self.classification_fig.add_subplot(111)
        self.classification_canvas = FigureCanvasTkAgg(self.classification_fig, right_frame)
        self.classification_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        charts_frame.columnconfigure(0, weight=1)
        charts_frame.columnconfigure(1, weight=1)
        charts_frame.rowconfigure(0, weight=1)
        
        # Stats summary at bottom
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.total_docs_label = ttk.Label(stats_frame, text="Total Documents: N/A", style='Body.TLabel')
        self.total_docs_label.pack(side=tk.LEFT, padx=20)
        
        self.avg_legal_terms_label = ttk.Label(stats_frame, text="Avg Legal Terms: N/A", style='Body.TLabel')
        self.avg_legal_terms_label.pack(side=tk.LEFT, padx=20)
        
        # Refresh button
        refresh_btn = ttk.Button(self, text="Refresh Data", command=self.refresh)
        refresh_btn.pack(pady=10)
        
        # Initial plot
        self._plot_placeholder()
    
    def _plot_placeholder(self):
        """Plot placeholder charts"""
        # Backend chart
        self.backend_ax.clear()
        self.backend_ax.text(0.5, 0.5, 'Loading...', 
                           ha='center', va='center',
                           fontsize=14, color=COLORS["foreground"])
        self.backend_ax.set_facecolor(COLORS["panel"])
        self.backend_fig.tight_layout()
        self.backend_canvas.draw()
        
        # Classification chart
        self.classification_ax.clear()
        self.classification_ax.text(0.5, 0.5, 'Loading...',
                                  ha='center', va='center',
                                  fontsize=14, color=COLORS["foreground"])
        self.classification_ax.set_facecolor(COLORS["panel"])
        self.classification_fig.tight_layout()
        self.classification_canvas.draw()
    
    def refresh(self):
        """Refresh data and update charts"""
        try:
            self.database_stats = api_client.get_database_stats()
            
            # ✅ Type guard: Ensure database_stats is a dict
            if not isinstance(self.database_stats, dict):
                logger.warning(f"⚠️ database_stats is not a dict: {type(self.database_stats)}")
                self._plot_error()
                return
            
            if self.database_stats and "error" not in self.database_stats:
                self._update_charts()
                self._update_stats()
            else:
                self._plot_error()
        except Exception as e:
            logger.error(f"❌ Error refreshing UDS3 Datasets: {e}", exc_info=True)
            self._plot_error()
    
    def _update_charts(self):
        """Update both charts with data"""
        if not self.database_stats:
            return
        
        # Backend Counts Chart
        self._plot_backend_counts()
        
        # Classification Breakdown Chart
        self._plot_classification_breakdown()
    
    def _plot_backend_counts(self):
        """Plot document counts per backend"""
        self.backend_ax.clear()
        
        # ✅ FIX: Extract counts from polyglot_status (real data from all backends)
        polyglot_status = self.database_stats.get("polyglot_status", {})
        
        # Extract real counts
        postgres_count = polyglot_status.get("relational_db", {}).get("documents", 0)
        neo4j_count = polyglot_status.get("neo4j", {}).get("nodes", 0)
        chromadb_count = polyglot_status.get("chromadb", {}).get("documents", 0)
        couchdb_count = polyglot_status.get("couchdb", {}).get("documents", 0)
        
        backends = ["PostgreSQL", "Neo4j", "ChromaDB", "CouchDB"]
        counts = [postgres_count, neo4j_count, chromadb_count, couchdb_count]
        
        colors = [CHART_COLOR_PALETTE["primary"], CHART_COLOR_PALETTE["success"], 
                 CHART_COLOR_PALETTE["info"], CHART_COLOR_PALETTE["warning"]]
        
        bars = self.backend_ax.bar(backends, counts, color=colors, alpha=0.8)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            self.backend_ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{int(height):,}',
                               ha='center', va='bottom',
                               fontsize=10, color=COLORS["foreground"])
        
        self.backend_ax.set_ylabel('Document Count', color=COLORS["foreground"])
        self.backend_ax.set_title('Documents per Backend', color=COLORS["foreground"], fontsize=12)
        self.backend_ax.tick_params(colors=COLORS["foreground"])
        self.backend_ax.set_facecolor(COLORS["panel"])
        
        # Rotate x labels
        plt.setp(self.backend_ax.get_xticklabels(), rotation=15, ha='right')
        
        self.backend_fig.tight_layout()
        self.backend_canvas.draw()
    
    def _plot_classification_breakdown(self):
        """Plot classification breakdown as horizontal bar chart"""
        self.classification_ax.clear()
        
        # ✅ Type guard: Ensure database_stats is a dict
        if not isinstance(self.database_stats, dict):
            self.classification_ax.text(0.5, 0.5, 'Invalid data format',
                                      ha='center', va='center',
                                      fontsize=12, color=COLORS["foreground"])
            self.classification_ax.set_facecolor(COLORS["panel"])
            self.classification_fig.tight_layout()
            self.classification_canvas.draw()
            return
        
        classifications = self.database_stats.get("classifications", {})
        
        if not classifications:
            self.classification_ax.text(0.5, 0.5, 'No classification data',
                                      ha='center', va='center',
                                      fontsize=12, color=COLORS["foreground"])
            self.classification_ax.set_facecolor(COLORS["panel"])
            self.classification_fig.tight_layout()
            self.classification_canvas.draw()
            return
        
        # Sort by count (descending)
        sorted_items = sorted(classifications.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_items[:8]]  # Top 8
        values = [item[1] for item in sorted_items[:8]]
        
        # Color palette
        colors_list = [
            CHART_COLOR_PALETTE["primary"],
            CHART_COLOR_PALETTE["success"],
            CHART_COLOR_PALETTE["info"],
            CHART_COLOR_PALETTE["warning"],
            CHART_COLOR_PALETTE["secondary"],
            CHART_COLOR_PALETTE["danger"],
            "#17a2b8",
            "#6c757d"
        ]
        
        bars = self.classification_ax.barh(labels, values, color=colors_list[:len(labels)], alpha=0.8)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            self.classification_ax.text(width, bar.get_y() + bar.get_height()/2.,
                                      f'{int(width):,}',
                                      ha='left', va='center',
                                      fontsize=9, color=COLORS["foreground"])
        
        self.classification_ax.set_xlabel('Document Count', color=COLORS["foreground"])
        self.classification_ax.set_title('Top Classifications', color=COLORS["foreground"], fontsize=12)
        self.classification_ax.tick_params(colors=COLORS["foreground"])
        self.classification_ax.set_facecolor(COLORS["panel"])
        
        self.classification_fig.tight_layout()
        self.classification_canvas.draw()
    
    def _update_stats(self):
        """Update statistics labels"""
        if not self.database_stats:
            return
        
        total_docs = self.database_stats.get("total_documents", 0)
        self.total_docs_label.config(text=f"Total Documents: {total_docs:,}")
        
        avg_legal_terms = self.database_stats.get("average_legal_terms", 0)
        self.avg_legal_terms_label.config(text=f"Avg Legal Terms: {avg_legal_terms:.1f}")
    
    def _plot_error(self):
        """Plot error message"""
        error_msg = "Failed to load data"
        
        if self.database_stats:
            error_msg = self.database_stats.get("message", error_msg)
        
        # Backend chart
        self.backend_ax.clear()
        self.backend_ax.text(0.5, 0.5, f'❌ {error_msg}',
                           ha='center', va='center',
                           fontsize=12, color=COLORS["error"])
        self.backend_ax.set_facecolor(COLORS["panel"])
        self.backend_fig.tight_layout()
        self.backend_canvas.draw()
        
        # Classification chart
        self.classification_ax.clear()
        self.classification_ax.text(0.5, 0.5, f'❌ {error_msg}',
                                  ha='center', va='center',
                                  fontsize=12, color=COLORS["error"])
        self.classification_ax.set_facecolor(COLORS["panel"])
        self.classification_fig.tight_layout()
        self.classification_canvas.draw()
