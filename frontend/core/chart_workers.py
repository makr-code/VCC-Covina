#!/usr/bin/env python3
"""
Specialized Chart Workers
=========================

12 spezialisierte Chart-Worker für Home-Dashboard.
Jeder Worker rendert einen spezifischen Chart-Typ.

Autor: Covina System
Datum: Oktober 2025
"""

import logging
import numpy as np
from typing import Dict, Any
import warnings

# ✅ Suppress matplotlib font warnings for missing Unicode glyphs
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from frontend.core.chart_threading import ChartWorker, ChartType
from frontend.config import COLORS, CHART_COLORS
from frontend.services.api_client import api_client

logger = logging.getLogger(__name__)


class SystemHealthWorker(ChartWorker):
    """System Health Gauge Chart"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        health_score = data.get('health_score', 0)
        
        # Horizontal Bar für Health Score
        color = CHART_COLORS[0] if health_score >= 80 else CHART_COLORS[3]
        ax.barh([0], [health_score], color=color, height=0.5)
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.set_title("System Health", color='white', fontsize=12, pad=10)
        ax.set_xlabel("Score (%)", color='white')
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_yticks([])
        
        # Health Score Text
        ax.text(health_score/2, 0, f'{health_score:.1f}%', 
                ha='center', va='center', color='white', fontsize=14, fontweight='bold')
        
        fig.tight_layout()
        return fig


class BackendStatusWorker(ChartWorker):
    """Backend Status Indicators"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        backends = data.get('backends', {})
        
        # Status-Symbole
        labels = []
        colors_list = []
        for name, status in backends.items():
            labels.append(name)
            colors_list.append(CHART_COLORS[0] if status else CHART_COLORS[3])
        
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, [1]*len(labels), color=colors_list)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color='white')
        ax.set_xlim(0, 1)
        ax.set_title("Backend Status", color='white', fontsize=12, pad=10)
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_color('white')
        ax.set_xticks([])
        
        # Status-Text
        for i, (name, status) in enumerate(backends.items()):
            symbol = "✓" if status else "✗"
            ax.text(0.5, i, symbol, ha='center', va='center', 
                   color='white', fontsize=16, fontweight='bold')
        
        fig.tight_layout()
        return fig


class DatabaseConnectionsWorker(ChartWorker):
    """Database Connection Counts"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        connections = data.get('connections', {})
        
        labels = list(connections.keys())
        values = list(connections.values())
        colors_list = CHART_COLORS[:len(labels)]
        
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, values, color=colors_list)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color='white')
        ax.set_title("Database Connections", color='white', fontsize=12, pad=10)
        ax.set_xlabel("Connections", color='white')
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        fig.tight_layout()
        return fig


class PerformanceGaugeWorker(ChartWorker):
    """Performance Gauge (Response Time)"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111, projection='polar')
        
        response_time = data.get('response_time_ms', 0)
        max_time = 1000  # ms
        
        # Semicircle Gauge
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)
        
        # Background
        ax.fill_between(theta, 0, r, color='#444', alpha=0.3)
        
        # Value
        value_angle = (response_time / max_time) * np.pi
        theta_value = np.linspace(0, value_angle, 50)
        color = CHART_COLORS[0] if response_time < 200 else CHART_COLORS[3]
        ax.fill_between(theta_value, 0, 1, color=color, alpha=0.8)
        
        ax.set_ylim(0, 1)
        ax.set_theta_direction(-1)
        ax.set_theta_offset(np.pi/2)
        ax.set_xticks([0, np.pi/2, np.pi])
        ax.set_xticklabels(['0ms', '500ms', '1000ms'], color='white', fontsize=8)
        ax.set_yticks([])
        ax.set_facecolor(COLORS["panel"])
        ax.set_title("Response Time", color='white', fontsize=12, pad=20)
        
        fig.tight_layout()
        return fig


class DocumentCountsWorker(ChartWorker):
    """Document Counts Bar Chart"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        counts = data.get('document_counts', {})
        
        labels = list(counts.keys())
        values = list(counts.values())
        colors_list = CHART_COLORS[:len(labels)]
        
        ax.bar(labels, values, color=colors_list)
        ax.set_title("Document Counts", color='white', fontsize=12, pad=10)
        ax.set_ylabel("Count", color='white')
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white', labelrotation=45)
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        fig.tight_layout()
        return fig


class ClassificationPieWorker(ChartWorker):
    """Classification Distribution Pie Chart"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        classifications = data.get('classifications', {})
        
        # Top 5
        sorted_items = sorted(classifications.items(), key=lambda x: x[1], reverse=True)[:5]
        labels = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        
        if values:
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=CHART_COLORS,
                   textprops={'color': 'white'})
            ax.set_title("Top 5 Classifications", color='white', fontsize=12, pad=10)
        else:
            ax.text(0.5, 0.5, "No Data", ha='center', va='center', 
                   color='white', fontsize=14, transform=ax.transAxes)
        
        fig.tight_layout()
        return fig


class IngestionTimelineWorker(ChartWorker):
    """Ingestion Timeline (24h)"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        timeline = data.get('timeline', [])
        
        if timeline:
            hours = list(range(len(timeline)))
            ax.plot(hours, timeline, color=CHART_COLORS[1], linewidth=2)
            ax.fill_between(hours, timeline, alpha=0.3, color=CHART_COLORS[1])
            ax.set_title("Ingestion (24h)", color='white', fontsize=12, pad=10)
            ax.set_xlabel("Hours", color='white')
            ax.set_ylabel("Documents", color='white')
        else:
            ax.text(0.5, 0.5, "No Data", ha='center', va='center',
                   color='white', fontsize=14, transform=ax.transAxes)
        
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        fig.tight_layout()
        return fig


class QualitySpiderWorker(ChartWorker):
    """Quality Metrics Radar Chart"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111, projection='polar')
        
        metrics = data.get('quality_metrics', {
            'Complete': 0, 'Accurate': 0, 'Valid': 0, 'Consistent': 0, 'Current': 0
        })
        
        categories = list(metrics.keys())
        values = list(metrics.values())
        
        # Close the plot
        values += values[:1]
        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]
        
        ax.plot(angles, values, 'o-', linewidth=2, color=CHART_COLORS[2])
        ax.fill(angles, values, alpha=0.25, color=CHART_COLORS[2])
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, color='white', fontsize=9)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(['25', '50', '75', '100'], color='white', fontsize=8)
        ax.set_facecolor(COLORS["panel"])
        ax.set_title("Quality Metrics", color='white', fontsize=12, pad=20)
        ax.grid(True, color='white', alpha=0.3)
        
        fig.tight_layout()
        return fig


class BackendMatrixWorker(ChartWorker):
    """Backend Heatmap Matrix"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        matrix_data = data.get('matrix', np.random.rand(3, 4) * 100)
        
        im = ax.imshow(matrix_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
        ax.set_xticks(range(4))
        ax.set_xticklabels(['PostgreSQL', 'Neo4j', 'ChromaDB', 'CouchDB'], 
                          rotation=45, ha='right', color='white', fontsize=8)
        ax.set_yticks(range(3))
        ax.set_yticklabels(['Available', 'Response', 'Capacity'], color='white')
        ax.set_title("Backend Matrix", color='white', fontsize=12, pad=10)
        
        # Colorbar
        cbar = fig.colorbar(im, ax=ax)
        cbar.ax.tick_params(colors='white')
        
        ax.set_facecolor(COLORS["panel"])
        
        fig.tight_layout()
        return fig


class ProcessingRateWorker(ChartWorker):
    """Processing Rate Gauge"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        rate = data.get('processing_rate', 0)
        max_rate = 100
        
        ax.barh([0], [rate], color=CHART_COLORS[1], height=0.5)
        ax.set_xlim(0, max_rate)
        ax.set_ylim(-0.5, 0.5)
        ax.set_title("Processing Rate", color='white', fontsize=12, pad=10)
        ax.set_xlabel("docs/s", color='white')
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_yticks([])
        
        ax.text(rate/2, 0, f'{rate:.1f}', ha='center', va='center',
               color='white', fontsize=14, fontweight='bold')
        
        fig.tight_layout()
        return fig


class StorageUsageWorker(ChartWorker):
    """Storage Usage Stacked Bar"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        storage = data.get('storage_by_type', {})
        
        labels = list(storage.keys())
        values = list(storage.values())
        
        if values:
            ax.bar(labels, values, color=CHART_COLORS[:len(labels)])
            ax.set_title("Storage Usage", color='white', fontsize=12, pad=10)
            ax.set_ylabel("MB", color='white')
            ax.tick_params(colors='white', labelrotation=45)
        else:
            ax.text(0.5, 0.5, "No Data", ha='center', va='center',
                   color='white', fontsize=14, transform=ax.transAxes)
        
        ax.set_facecolor(COLORS["panel"])
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        fig.tight_layout()
        return fig


class SystemMetricsWorker(ChartWorker):
    """System Metrics Text Display"""
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Figure:
        fig = Figure(figsize=(4, 3), facecolor=COLORS["panel"])
        ax = fig.add_subplot(111)
        
        metrics = data.get('metrics', {})
        
        ax.axis('off')
        ax.set_facecolor(COLORS["panel"])
        
        # Text Display
        y_pos = 0.9
        for key, value in metrics.items():
            ax.text(0.1, y_pos, f"{key}:", color='white', fontsize=10,
                   ha='left', va='top', transform=ax.transAxes)
            ax.text(0.9, y_pos, str(value), color=CHART_COLORS[0], fontsize=10,
                   ha='right', va='top', fontweight='bold', transform=ax.transAxes)
            y_pos -= 0.15
        
        ax.set_title("System Metrics", color='white', fontsize=12, pad=10)
        
        fig.tight_layout()
        return fig


class RefreshAllWorker(ChartWorker):
    """
    Special worker for REFRESH_ALL command.
    
    Fetches all data from API in background thread,
    then returns the data as "figure" (actually a dict).
    """
    
    def render_chart(self, data: Dict[str, Any], config: Dict[str, Any]) -> Any:
        """
        Fetch all data from API.
        
        Returns Dict instead of Figure - will be handled specially.
        """
        logger.info("📡 RefreshAllWorker.render_chart() called - fetching all data from API...")
        
        fetched_data = {
            'health_data': None,
            'uds3_data': None,
            'db_stats': None,
            'vector_stats': None
        }
        
        try:
            fetched_data['health_data'] = api_client.get_health()
            fetched_data['uds3_data'] = api_client.get_uds3_status()
            fetched_data['db_stats'] = api_client.get_database_stats()
            fetched_data['vector_stats'] = api_client.get_vector_monitoring()
            
            logger.info("✅ All data fetched successfully")
            
        except Exception as e:
            logger.error(f"❌ Data fetch error: {e}")
            raise
        
        # Return data dict (not a Figure!)
        logger.info(f"📤 RefreshAllWorker returning Dict: {type(fetched_data)}")
        return fetched_data


# Worker-Mapping für ChartThreadPool
CHART_WORKERS = {
    ChartType.SYSTEM_HEALTH: SystemHealthWorker,
    ChartType.BACKEND_STATUS: BackendStatusWorker,
    ChartType.DATABASE_CONNECTIONS: DatabaseConnectionsWorker,
    ChartType.PERFORMANCE_GAUGE: PerformanceGaugeWorker,
    ChartType.DOCUMENT_COUNTS: DocumentCountsWorker,
    ChartType.CLASSIFICATION_PIE: ClassificationPieWorker,
    ChartType.INGESTION_TIMELINE: IngestionTimelineWorker,
    ChartType.QUALITY_SPIDER: QualitySpiderWorker,
    ChartType.BACKEND_MATRIX: BackendMatrixWorker,
    ChartType.PROCESSING_RATE: ProcessingRateWorker,
    ChartType.STORAGE_USAGE: StorageUsageWorker,
    ChartType.SYSTEM_METRICS: SystemMetricsWorker,
    ChartType.REFRESH_ALL: RefreshAllWorker,  # Special command worker
}
