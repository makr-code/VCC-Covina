"""
Covina LiveView Configuration
==============================

Backend URL und Refresh-Intervalle konfigurieren
"""

# Backend API Configuration
BACKEND_URL = "http://127.0.0.1:45678"  # ✅ Main Backend (Queries, DSGVO, Review Queue)
INGESTION_BACKEND_URL = "http://127.0.0.1:45679"  # ✅ Ingestion Backend (Document Upload, Batch Processing)

# Refresh Intervals (in seconds)
REFRESH_INTERVAL_CRITICAL = 5    # System Status, Active Jobs
REFRESH_INTERVAL_NORMAL = 10     # Database Stats, UDS3 Counts
REFRESH_INTERVAL_SLOW = 30       # Security Logs, Error History

# UI Configuration
WINDOW_TITLE = "Covina LiveView Dashboard"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 1200
WINDOW_MIN_HEIGHT = 700

# Theme Colors
COLORS = {
    "primary": "#007bff",      # Blue
    "success": "#28a745",      # Green
    "warning": "#ffc107",      # Yellow
    "error": "#dc3545",        # Red
    "info": "#17a2b8",         # Blue
    "background": "#1e1e1e",   # Dark Gray
    "foreground": "#ffffff",   # White
    "panel": "#2d2d2d",        # Light Gray
    "border": "#404040"        # Medium Gray
}

# Font Configuration
FONTS = {
    "title": ("Segoe UI", 14, "bold"),
    "subtitle": ("Segoe UI", 11, "bold"),
    "body": ("Segoe UI", 10),
    "mono": ("Consolas", 9),
    "small": ("Segoe UI", 8)
}

# Chart Configuration
CHART_COLORS_DICT = {
    "primary": "#007bff",
    "secondary": "#6c757d",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8"
}

# Chart Colors as list (for Matplotlib)
CHART_COLORS = list(CHART_COLORS_DICT.values())

# API Endpoints
ENDPOINTS = {
    # Main Backend Endpoints (Port 45678)
    "health": "/health",
    "database_stats": "/database/stats",
    "uds3_status": "/uds3/status",
    "uds3_strategy": "/uds3/strategy/status",
    "vector_monitoring": "/monitoring/vector",
    "saga_status": "/admin/saga/status",
    "security_audit": "/admin/security/audit",
    "errors_recent": "/errors/recent",
    "ingestion_status": "/admin/ingestion/status",
    "golden_dataset": "/admin/golden-dataset/status"
}

# Ingestion Backend Endpoints (Port 45679)
INGESTION_ENDPOINTS = {
    "upload_files": "/upload/files",
    "upload_directory": "/upload/directory",
    "jobs_list": "/jobs",
    "job_status": "/jobs/{job_id}/status",
    "job_metrics": "/jobs/{job_id}/metrics",
    "health": "/health"
}

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "frontend/logs/covina_liveview.log"
