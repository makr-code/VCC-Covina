"""
Home Dashboard
==============

Massive Übersicht über den Gesamtzustand mit 4×3 Grid von Matplotlib Charts
"""

import logging
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from typing import Optional, Dict, Any

from frontend.config import COLORS, FONTS, CHART_COLORS
from frontend.services.api_client import api_client

# Configure logging
logger = logging.getLogger(__name__)


class HomeDashboardView(ttk.Frame):
    """Home Dashboard mit 4×3 Grid von Visualisierungen"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(style='TFrame')
        
        # Data cache
        self.health_data: Optional[Dict[str, Any]] = None
        self.uds3_data: Optional[Dict[str, Any]] = None
        self.db_stats: Optional[Dict[str, Any]] = None
        self.vector_stats: Optional[Dict[str, Any]] = None
        
        # Canvas storage
        self.canvases = {}
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create 4×3 Grid Layout"""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title = ttk.Label(title_frame, text="🏠 Covina System Overview", style='Title.TLabel')
        title.pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(title_frame, text="🔄 Refresh All", command=self.refresh)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Main grid container
        grid_container = ttk.Frame(self)
        grid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure grid weights (4 columns × 3 rows)
        for i in range(4):
            grid_container.columnconfigure(i, weight=1)
        for i in range(3):
            grid_container.rowconfigure(i, weight=1)
        
        # Create 12 cards (4×3)
        self.cards = {}
        card_configs = [
            # Row 0
            ("system_health", 0, 0, "System Health", self._create_system_health_chart),
            ("backend_status", 0, 1, "Backend Status", self._create_backend_status_chart),
            ("database_connections", 0, 2, "Database Connections", self._create_database_connections_chart),
            ("performance", 0, 3, "Performance", self._create_performance_gauge),
            
            # Row 1
            ("document_counts", 1, 0, "Document Statistics", self._create_document_counts_chart),
            ("classification_pie", 1, 1, "Classification Distribution", self._create_classification_pie),
            ("ingestion_timeline", 1, 2, "Ingestion Timeline", self._create_ingestion_timeline),
            ("quality_spider", 1, 3, "Data Quality", self._create_quality_spider),
            
            # Row 2
            ("backend_matrix", 2, 0, "Backend Health Matrix", self._create_backend_matrix),
            ("processing_rate", 2, 1, "Processing Rate", self._create_processing_rate),
            ("storage_usage", 2, 2, "Storage Distribution", self._create_storage_usage),
            ("system_metrics", 2, 3, "System Metrics", self._create_system_metrics)
        ]
        
        for card_id, row, col, title, chart_func in card_configs:
            card = self._create_card(grid_container, title)
            card.grid(row=row, column=col, sticky=(tk.N, tk.S, tk.E, tk.W), padx=3, pady=3)
            self.cards[card_id] = {"frame": card, "chart_func": chart_func}
        
        # Initial placeholder
        self._plot_all_placeholders()
    
    def _create_card(self, parent, title):
        """Create a single card frame with title"""
        card = ttk.LabelFrame(parent, text=title, padding=5)
        return card
    
    def _plot_all_placeholders(self):
        """Plot loading placeholders for all cards"""
        for card_id, card_data in self.cards.items():
            frame = card_data["frame"]
            
            # Create small matplotlib figure
            fig = Figure(figsize=(3, 2), facecolor=COLORS["panel"])
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'Loading...', ha='center', va='center',
                   fontsize=10, color=COLORS["foreground"])
            ax.set_facecolor(COLORS["panel"])
            ax.axis('off')
            
            canvas = FigureCanvasTkAgg(fig, frame)
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self.canvases[card_id] = (fig, ax, canvas)
    
    def refresh(self):
        """Refresh all data and update all charts"""
        # Fetch all data with safe type checking
        try:
            health_response = api_client.get_connection_status()
            self.health_data = health_response if isinstance(health_response, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch health data: {e}")
            self.health_data = {}
        
        try:
            uds3_response = api_client.get_uds3_strategy_status()
            self.uds3_data = uds3_response if isinstance(uds3_response, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch UDS3 data: {e}")
            self.uds3_data = {}
        
        try:
            db_response = api_client.get_database_stats()
            self.db_stats = db_response if isinstance(db_response, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch database stats: {e}")
            self.db_stats = {}
        
        try:
            vector_response = api_client.get_vector_monitoring()
            self.vector_stats = vector_response if isinstance(vector_response, dict) else {}
        except Exception as e:
            logger.warning(f"Failed to fetch vector stats: {e}")
            self.vector_stats = {}
        
        # Update all charts
        for card_id, card_data in self.cards.items():
            try:
                chart_func = card_data["chart_func"]
                chart_func()
            except Exception as e:
                logger.warning(f"Error updating {card_id}: {e}")
    
    # ========================================================================
    # ROW 0: SYSTEM STATUS
    # ========================================================================
    
    def _create_system_health_chart(self):
        """Card 1: System Health Gauge"""
        fig, ax, canvas = self.canvases["system_health"]
        ax.clear()
        
        # Calculate health score (0-100)
        health_score = 100
        
        if self.health_data and self.health_data.get("connected"):
            latency = self.health_data.get("latency_ms", 0)
            if latency > 500:
                health_score -= 20
            elif latency > 100:
                health_score -= 10
        else:
            health_score = 0
        
        # Gauge chart
        categories = ['Health\nScore']
        values = [health_score]
        
        colors_map = [CHART_COLORS["success"] if health_score > 70 else 
                     CHART_COLORS["warning"] if health_score > 40 else 
                     CHART_COLORS["danger"]]
        
        bars = ax.barh(categories, values, color=colors_map, alpha=0.8)
        ax.set_xlim(0, 100)
        ax.set_xlabel('Score', color=COLORS["foreground"], fontsize=8)
        
        # Add value label
        for bar in bars:
            width = bar.get_width()
            ax.text(width/2, bar.get_y() + bar.get_height()/2,
                   f'{int(width)}%',
                   ha='center', va='center',
                   fontsize=12, fontweight='bold', color='white')
        
        ax.tick_params(colors=COLORS["foreground"], labelsize=8)
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_backend_status_chart(self):
        """Card 2: Backend Status (Online/Offline)"""
        fig, ax, canvas = self.canvases["backend_status"]
        ax.clear()
        
        if self.health_data and self.health_data.get("connected"):
            status = "ONLINE"
            color = CHART_COLORS["success"]
            icon = "✓"
        else:
            status = "OFFLINE"
            color = CHART_COLORS["danger"]
            icon = "✗"
        
        # Simple status indicator
        ax.text(0.5, 0.6, icon, ha='center', va='center',
               fontsize=60, color=color, fontweight='bold')
        ax.text(0.5, 0.3, status, ha='center', va='center',
               fontsize=16, color=color, fontweight='bold')
        
        if self.health_data and self.health_data.get("connected"):
            latency = self.health_data.get("latency_ms", 0)
            ax.text(0.5, 0.15, f'{latency:.0f} ms', ha='center', va='center',
                   fontsize=10, color=COLORS["foreground"])
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_database_connections_chart(self):
        """Card 3: Database Connections (4 Backends)"""
        fig, ax, canvas = self.canvases["database_connections"]
        ax.clear()
        
        backends = ["PostgreSQL", "Neo4j", "ChromaDB", "CouchDB"]
        status_values = []
        colors_list = []
        
        if isinstance(self.uds3_data, dict) and self.uds3_data and "backends" in self.uds3_data:
            backend_map = {
                "PostgreSQL": "relational",
                "Neo4j": "graph",
                "ChromaDB": "vector",
                "CouchDB": "document"
            }
            
            for db_name in backends:
                backend_info = self.uds3_data["backends"].get(backend_map[db_name], {})
                available = backend_info.get("available", False)
                status_values.append(1 if available else 0)
                colors_list.append(CHART_COLORS["success"] if available else CHART_COLORS["danger"])
        else:
            status_values = [0, 0, 0, 0]
            colors_list = [CHART_COLORS["danger"]] * 4
        
        # Horizontal bar chart
        y_pos = np.arange(len(backends))
        bars = ax.barh(y_pos, [1]*4, color='#404040', alpha=0.3)
        bars = ax.barh(y_pos, status_values, color=colors_list, alpha=0.8)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(backends, fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['Off', 'On'], fontsize=7)
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_performance_gauge(self):
        """Card 4: Performance Gauge (Response Time)"""
        fig, ax, canvas = self.canvases["performance"]
        ax.clear()
        
        latency = 0
        if self.health_data and self.health_data.get("connected"):
            latency = self.health_data.get("latency_ms", 0)
        
        # Gauge visualization (semicircle)
        theta = np.linspace(0, np.pi, 100)
        r = 1
        
        # Background arc
        ax.plot(r * np.cos(theta), r * np.sin(theta), color='#404040', linewidth=20, alpha=0.3)
        
        # Performance arc (green to red)
        if latency < 100:
            color = CHART_COLORS["success"]
            angle_fraction = min(latency / 100, 1.0)
        elif latency < 500:
            color = CHART_COLORS["warning"]
            angle_fraction = min((latency - 100) / 400 + 0.33, 0.66)
        else:
            color = CHART_COLORS["danger"]
            angle_fraction = min((latency - 500) / 500 + 0.66, 1.0)
        
        theta_perf = np.linspace(0, np.pi * angle_fraction, 50)
        ax.plot(r * np.cos(theta_perf), r * np.sin(theta_perf), color=color, linewidth=20)
        
        # Center text
        ax.text(0, 0.2, f'{latency:.0f}', ha='center', va='center',
               fontsize=20, fontweight='bold', color=COLORS["foreground"])
        ax.text(0, -0.1, 'ms', ha='center', va='center',
               fontsize=10, color=COLORS["foreground"])
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.3, 1.2)
        ax.axis('off')
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    # ========================================================================
    # ROW 1: DATA OVERVIEW
    # ========================================================================
    
    def _create_document_counts_chart(self):
        """Card 5: Document Counts Bar Chart"""
        fig, ax, canvas = self.canvases["document_counts"]
        ax.clear()
        
        if isinstance(self.db_stats, dict) and self.db_stats and "total_documents" in self.db_stats:
            total = self.db_stats.get("total_documents", 0)
            
            # Mock data for different backends (would need separate endpoints)
            backends = ["PostgreSQL", "Neo4j", "ChromaDB", "CouchDB"]
            counts = [total, total, 0, 0]  # Vector/Doc might be 0
            
            colors_list = [CHART_COLORS["primary"], CHART_COLORS["success"],
                          CHART_COLORS["info"], CHART_COLORS["warning"]]
            
            bars = ax.bar(range(len(backends)), counts, color=colors_list, alpha=0.8)
            
            ax.set_xticks(range(len(backends)))
            ax.set_xticklabels(['PG', 'Neo4j', 'Chroma', 'Couch'], fontsize=7, rotation=15)
            ax.set_ylabel('Docs', color=COLORS["foreground"], fontsize=8)
            ax.ticklabel_format(style='plain', axis='y')
            
            # Add compact value labels
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height/1000)}k' if height > 1000 else f'{int(height)}',
                           ha='center', va='bottom', fontsize=7, color=COLORS["foreground"])
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                   color=COLORS["foreground"])
        
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_classification_pie(self):
        """Card 6: Classification Distribution Pie Chart"""
        fig, ax, canvas = self.canvases["classification_pie"]
        ax.clear()
        
        if isinstance(self.db_stats, dict) and self.db_stats and "classifications" in self.db_stats:
            classifications = self.db_stats["classifications"]
            
            # Top 5 classifications
            sorted_items = sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:5]
            labels = [item[0][:8] for item in sorted_items]  # Shorten labels
            sizes = [item[1] for item in sorted_items]
            
            colors_list = [CHART_COLORS["primary"], CHART_COLORS["success"],
                          CHART_COLORS["info"], CHART_COLORS["warning"],
                          CHART_COLORS["secondary"]]
            
            ax.pie(sizes, labels=labels, colors=colors_list[:len(labels)],
                  autopct='%1.0f%%', startangle=90, textprops={'fontsize': 7, 'color': 'white'})
            ax.axis('equal')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                   transform=ax.transAxes, color=COLORS["foreground"])
        
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_ingestion_timeline(self):
        """Card 7: Ingestion Timeline (Line Chart)"""
        fig, ax, canvas = self.canvases["ingestion_timeline"]
        ax.clear()
        
        # Mock timeline data (would need time-series endpoint)
        hours = np.arange(0, 24, 4)
        docs_per_hour = [150, 200, 180, 220, 190, 210]
        
        ax.plot(hours, docs_per_hour, color=CHART_COLORS["primary"], linewidth=2, marker='o')
        ax.fill_between(hours, docs_per_hour, alpha=0.3, color=CHART_COLORS["primary"])
        
        ax.set_xlabel('Hours', color=COLORS["foreground"], fontsize=8)
        ax.set_ylabel('Docs/h', color=COLORS["foreground"], fontsize=8)
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        ax.grid(True, alpha=0.2, color=COLORS["foreground"])
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_quality_spider(self):
        """Card 8: Data Quality Spider/Radar Chart"""
        fig, ax, canvas = self.canvases["quality_spider"]
        ax.clear()
        
        # Quality metrics (0-100)
        categories = ['Complete', 'Accurate', 'Valid', 'Consistent', 'Current']
        values = [85, 92, 88, 90, 95]  # Mock data
        
        # Number of variables
        N = len(categories)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]
        
        ax = plt.subplot(111, projection='polar')
        ax.plot(angles, values, 'o-', linewidth=2, color=CHART_COLORS["success"])
        ax.fill(angles, values, alpha=0.25, color=CHART_COLORS["success"])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=7, color=COLORS["foreground"])
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(['25', '50', '75', '100'], fontsize=6, color=COLORS["foreground"])
        ax.grid(True, alpha=0.3, color=COLORS["foreground"])
        ax.set_facecolor(COLORS["panel"])
        fig.patch.set_facecolor(COLORS["panel"])
        
        # Re-draw to canvas
        self.canvases["quality_spider"] = (fig, ax, canvas)
        canvas.draw()
    
    # ========================================================================
    # ROW 2: ADVANCED METRICS
    # ========================================================================
    
    def _create_backend_matrix(self):
        """Card 9: Backend Health Matrix (Heatmap)"""
        fig, ax, canvas = self.canvases["backend_matrix"]
        ax.clear()
        
        backends = ["PostgreSQL", "Neo4j", "ChromaDB", "CouchDB"]
        metrics = ["Available", "Response", "Capacity"]
        
        # Mock matrix data (3x4)
        data = np.array([
            [1, 1, 1, 1],      # Available (1=yes, 0=no)
            [0.95, 0.92, 0.88, 0.90],  # Response (0-1, lower=better)
            [0.65, 0.58, 0.12, 0.08]   # Capacity used (0-1)
        ])
        
        if isinstance(self.uds3_data, dict) and self.uds3_data and "backends" in self.uds3_data:
            backend_map = ["relational", "graph", "vector", "document"]
            for i, key in enumerate(backend_map):
                backend_info = self.uds3_data["backends"].get(key, {})
                data[0, i] = 1 if backend_info.get("available", False) else 0
        
        im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        ax.set_xticks(np.arange(len(backends)))
        ax.set_yticks(np.arange(len(metrics)))
        ax.set_xticklabels(['PG', 'Neo', 'Chr', 'Cou'], fontsize=7)
        ax.set_yticklabels(metrics, fontsize=7)
        
        # Add values
        for i in range(len(metrics)):
            for j in range(len(backends)):
                text = ax.text(j, i, f'{data[i, j]:.0%}' if i > 0 else ('✓' if data[i, j] else '✗'),
                             ha="center", va="center", color="black", fontsize=7, fontweight='bold')
        
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        fig.tight_layout()
        canvas.draw()
    
    def _create_processing_rate(self):
        """Card 10: Processing Rate Gauge"""
        fig, ax, canvas = self.canvases["processing_rate"]
        ax.clear()
        
        # Mock processing rate (docs/sec)
        rate = 5.0
        
        if self.db_stats:
            total = self.db_stats.get("total_documents", 0)
            # Estimate rate (would need time-series data)
            rate = min(total / 10000, 10.0)  # Cap at 10 docs/sec
        
        # Speedometer-style gauge
        max_rate = 10.0
        categories = ['Processing\nRate']
        values = [rate]
        max_values = [max_rate]
        
        # Background bar
        ax.barh(categories, max_values, color='#404040', alpha=0.3)
        
        # Actual rate bar
        color = CHART_COLORS["success"] if rate > 3 else CHART_COLORS["warning"]
        bars = ax.barh(categories, values, color=color, alpha=0.8)
        
        ax.set_xlim(0, max_rate)
        ax.set_xlabel('docs/sec', color=COLORS["foreground"], fontsize=8)
        
        # Value label
        for bar in bars:
            width = bar.get_width()
            ax.text(width/2, bar.get_y() + bar.get_height()/2,
                   f'{width:.1f}',
                   ha='center', va='center',
                   fontsize=12, fontweight='bold', color='white')
        
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_storage_usage(self):
        """Card 11: Storage Distribution (Stacked Bar)"""
        fig, ax, canvas = self.canvases["storage_usage"]
        ax.clear()
        
        if self.db_stats:
            total_docs = self.db_stats.get("total_documents", 0)
            classifications = self.db_stats.get("classifications", {})
            
            # Top 4 classifications
            sorted_items = sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:4]
            labels = [item[0][:6] for item in sorted_items]
            sizes = [item[1] for item in sorted_items]
            
            colors_list = [CHART_COLORS["primary"], CHART_COLORS["success"],
                          CHART_COLORS["info"], CHART_COLORS["warning"]]
            
            # Stacked horizontal bar
            left = 0
            for i, (label, size) in enumerate(zip(labels, sizes)):
                ax.barh(['Storage'], [size], left=left, color=colors_list[i], alpha=0.8, label=label)
                left += size
            
            ax.set_xlim(0, total_docs)
            ax.legend(fontsize=6, loc='upper right', framealpha=0.8)
            ax.set_xlabel('Documents', color=COLORS["foreground"], fontsize=8)
            ax.ticklabel_format(style='plain', axis='x')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center',
                   transform=ax.transAxes, color=COLORS["foreground"])
        
        ax.tick_params(colors=COLORS["foreground"], labelsize=7)
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
    
    def _create_system_metrics(self):
        """Card 12: System Metrics (Multi-metric Display)"""
        fig, ax, canvas = self.canvases["system_metrics"]
        ax.clear()
        
        # Key metrics
        metrics = []
        
        if self.db_stats:
            total_docs = self.db_stats.get("total_documents", 0)
            avg_terms = self.db_stats.get("average_legal_terms", 0)
            metrics.append(f"📄 {total_docs:,} docs")
            metrics.append(f"📊 {avg_terms:.1f} avg terms")
        
        if self.health_data and self.health_data.get("connected"):
            active_jobs = self.health_data.get("active_jobs", 0)
            metrics.append(f"⚙️ {active_jobs} active jobs")
        
        if self.uds3_data:
            backends_available = sum(1 for b in self.uds3_data.get("backends", {}).values() if b.get("available", False))
            metrics.append(f"🔌 {backends_available}/4 backends")
        
        # Display metrics as text list
        y_pos = 0.85
        for metric in metrics:
            ax.text(0.5, y_pos, metric,
                   ha='center', va='center',
                   fontsize=10, color=COLORS["foreground"],
                   transform=ax.transAxes)
            y_pos -= 0.20
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_facecolor(COLORS["panel"])
        fig.tight_layout()
        canvas.draw()
