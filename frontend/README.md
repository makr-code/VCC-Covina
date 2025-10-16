# Covina LiveView Frontend

**Real-time monitoring dashboard for Covina backend system**

## Features

- 🔴 **Live System Status** - Backend health, uptime, active jobs
- 📊 **UDS3 Dataset Monitoring** - Document counts across all backends (Vector, Graph, Relational, Document)
- 📈 **Ingestion Pipeline** - Real-time ingestion metrics and processed files
- 💾 **Database Health** - PostgreSQL, Neo4j, ChromaDB, CouchDB status
- 🔄 **SAGA Transactions** - Transaction monitoring with success/rollback ratios
- 🔒 **Security & Audit** - Security events timeline and audit logs
- ⚠️ **Error Tracking** - Real-time error logs with filtering and export
- 🎯 **Golden Dataset** - Gap detection and coverage analysis

## Installation

### Prerequisites

- Python 3.11+
- Tkinter (included in Python standard library on Windows)
- Covina Backend running on `http://localhost:45678`

### Install Dependencies

```powershell
cd c:\VCC\Covina\frontend
pip install -r requirements.txt
```

Dependencies:
- `matplotlib` - For charts and graphs
- `requests` - For API calls
- `Pillow` - For icons and images
- `pandas` - For data tables
- `seaborn` - For enhanced visualizations

## Configuration

Edit `frontend/config.py` to customize:

```python
# Backend URL
BACKEND_URL = "http://localhost:45678"

# Refresh Intervals (seconds)
REFRESH_INTERVAL_CRITICAL = 5    # System status
REFRESH_INTERVAL_NORMAL = 10     # Database stats
REFRESH_INTERVAL_SLOW = 30       # Audit logs
```

## Usage

### Start Frontend

```powershell
cd c:\VCC\Covina
python frontend\main.py
```

Or on Linux/Mac:

```bash
cd /path/to/Covina
python3 frontend/main.py
```

### Navigate Dashboard

- **System Status Tab** - Overview of backend health
- **UDS3 Datasets Tab** - Document counts and classification breakdown
- **Ingestion Tab** - Pipeline metrics and recent files
- **Database Health Tab** - Connection status for all 4 backends
- **SAGA Monitor Tab** - Transaction logs and rollback analysis
- **Security & Audit Tab** - Security events and audit trail
- **Error Tracking Tab** - Error logs with filtering
- **Golden Dataset Tab** - Gap detection and coverage matrix

### Menu Bar

- **File → Refresh All** - Force refresh all views
- **File → Exit** - Close application
- **View → [Tab Name]** - Quick jump to specific tab
- **Settings → Configure Backend URL** - Show current backend URL
- **Settings → Toggle Theme** - Switch between dark/light theme (coming soon)
- **Help → About** - Show version info

## Architecture

```
frontend/
├── main.py                 # Main application entry point
├── config.py               # Configuration (backend URL, refresh intervals)
├── requirements.txt        # Python dependencies
│
├── services/
│   └── api_client.py       # REST API client for backend
│
├── views/
│   ├── system_status_view.py       # System status dashboard
│   ├── database_health_view.py     # Database health panels
│   ├── ingestion_view.py           # Ingestion monitoring
│   ├── security_view.py            # Security & audit logs
│   ├── error_tracking_view.py      # Error tracking
│   └── golden_dataset_view.py      # Golden dataset & gap detection
│
├── widgets/
│   ├── uds3_dataset_widget.py      # UDS3 dataset chart
│   └── saga_monitor_widget.py      # SAGA transaction monitor
│
├── utils/
│   ├── live_updater.py     # Background thread for live updates
│   └── theme.py            # Theme configuration
│
└── assets/
    └── (icons, images)
```

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/health` | Backend health status |
| `/database/stats` | PostgreSQL statistics |
| `/uds3/status` | UDS3 framework status |
| `/uds3/strategy/status` | All backend status (Vector, Graph, Relational, Document) |
| `/monitoring/vector` | ChromaDB monitoring |
| `/admin/saga/status` | SAGA transaction status |
| `/admin/security/audit` | Security audit logs |
| `/errors/recent` | Recent errors |
| `/admin/ingestion/status` | Ingestion pipeline status |
| `/admin/golden-dataset/status` | Golden dataset & gap detection |

## Troubleshooting

### "Cannot connect to backend"

- Verify backend is running: `curl http://localhost:45678/health`
- Check `frontend/config.py` for correct `BACKEND_URL`
- Ensure no firewall blocking port 45678

### "ModuleNotFoundError: No module named 'tkinter'"

On Linux, install tkinter:

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter
```

### Slow Performance / High CPU

- Increase refresh intervals in `config.py`
- Reduce chart complexity (e.g., limit data points)
- Check backend response times

## Screenshots

_(Coming soon)_

## Version History

- **v1.0.0** (2025-10-09)
  - Initial release
  - 8 monitoring tabs
  - Live updates (5-30s intervals)
  - Dark theme
  - Error handling and graceful degradation

## License

Part of the Covina project.

## Support

For issues or questions, refer to main Covina documentation.
