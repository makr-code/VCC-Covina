"""
Covina Main Application - Phase 4 Integration

Complete integration of all Phase 1-3 components:
- EventBus Architecture
- UI Components (TopToolbar, Sidebars, Terminal, StatusBar)
- All 10 Views (RecoveryView, HomeView, etc.)
- ViewManager for dynamic switching

Author: Covina Development Team
Version: 4.0.0 (Frontend Modernization - Phase 4)
Date: 14.10.2025, 11:40 Uhr
"""

import tkinter as tk
from tkinter import ttk
import logging

# Phase 1: Core
from frontend.core.event_bus import EventBus, EventType
from frontend.core.task_executor import TaskExecutor
from frontend.core.view_manager import ViewManager

# Phase 2: UI Components
from frontend.widgets.top_toolbar import TopToolbar
from frontend.widgets.sidebar_left import SidebarLeft
from frontend.widgets.sidebar_right import SidebarRight
from frontend.widgets.ai_terminal import AITerminal
from frontend.widgets.status_bar import EnhancedStatusBar

# Phase 3: Views
from frontend.views import (
    RecoveryView,
    HomeView,
    SystemStatusViewMigrated,
    IngestionViewMigrated,
    DatabaseHealthViewMigrated,
    SecurityViewMigrated,
    ErrorTrackingViewMigrated,
    GoldenDatasetViewMigrated,
    UDS3View,
    SAGAView,
)

# Backend Service
from frontend.core.backend_service import CovinaBackendService as BackendService


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CovinaApp(tk.Tk):
    """
    Covina Main Application - Phase 4 Integration.
    
    Complete modern frontend with:
    - Event-driven architecture
    - Dynamic view switching
    - Responsive UI components
    - Backend integration
    """
    
    def __init__(self):
        super().__init__()
        
        logger.info("=" * 60)
        logger.info("Starting Covina Application v4.0.0")
        logger.info("=" * 60)
        
        # Window configuration
        self.title("Covina Document Management System v4.0.0")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Apply modern theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Phase 1: Initialize Core
        logger.info("Phase 1: Initializing Core Components...")
        self.event_bus = EventBus()
        self.event_bus.start()  # ⚠️ CRITICAL: Start dispatch thread!
        self.task_executor = TaskExecutor()
        self.backend_service = BackendService(self.event_bus, self.task_executor)
        
        # Phase 2: Build UI Components
        logger.info("Phase 2: Building UI Components...")
        self._build_ui()
        
        # Phase 3: Initialize Views
        logger.info("Phase 3: Initializing Views...")
        self._initialize_views()
        
        # Phase 4: Wire Events
        logger.info("Phase 4: Wiring Event Handlers...")
        self._wire_events()
        
        # Start with home view
        logger.info("Switching to home view...")
        self.view_manager.switch_view("home")
        
        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        logger.info("✅ Covina Application started successfully!")
        logger.info("=" * 60)
    
    def _build_ui(self):
        """Build UI layout (Phase 2 components)."""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)
        
        # Top Toolbar (60px height)
        self.toolbar = TopToolbar(main_container, self.event_bus)
        self.toolbar.pack(side="top", fill="x")
        
        # Content area (horizontal layout)
        content_container = ttk.Frame(main_container)
        content_container.pack(side="top", fill="both", expand=True)
        
        # Left Sidebar (250px ↔ 50px)
        self.sidebar_left = SidebarLeft(content_container, self.event_bus)
        self.sidebar_left.pack(side="left", fill="y")
        
        # Center area ({
  "pageCacheStats" : {
    "cachedChannelsStatistics" : {
      "hit" : 1777,
      "miss" : 0,
      "load" : 159,
      "capacity" : 400
    },
    "uncachedFileAccess" : 1217,
    "maxRegisteredFiles" : 491,
    "maxCacheSizeInBytes" : 328826880,
    "totalCachedSizeInBytes" : 170983424,
    "pageHits" : 17729,
    "pageFastCacheHits" : 166129,
    "pageLoadsAboveSizeThreshold" : 0,
    "regularPageLoads" : 1935,
    "disposedBuffers" : 1764,
    "totalPageDisposalUs" : 2273,
    "totalPageLoadUs" : 2413379,
    "totalPagesLoaded" : 1935,
    "capacityInBytes" : 629145600
  },
  "indexStorageStats" : {
    "indexStoragesStats" : {
      "BindingXmlIndex" : {
        "statsPerPhm" : {
          "BindingXmlIndex.storage" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : -1,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 4,
                "elements" : 8191,
                "height" : 2,
                "moves" : 1,
                "leafPages" : 3,
                "maxSearchStepsInRequest" : 332,
                "searchRequests" : 108603,
                "searchSteps" : 185340,
                "pageCapacity" : 32768,
                "sizeInBytes" : 131072
              }
            },
            "valueStorageSizeInBytes" : 366393
          }
        }
      },
      "DomFileIndex" : {
        "statsPerPhm" : {
          "DomFileIndex.storage" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 448,
              "dataFileSizeInBytes" : 14441,
              "storageSizeInBytes" : 3712,
              "btreeStatistics" : {
                "pages" : 1,
                "elements" : 448,
                "height" : 1,
                "moves" : 0,
                "leafPages" : 1,
                "maxSearchStepsInRequest" : 2,
                "searchRequests" : 995,
                "searchSteps" : 42,
                "pageCapacity" : 32768,
                "sizeInBytes" : 32768
              }
            },
            "valueStorageSizeInBytes" : 16697
          },
          "DomFileIndex_inputs" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : -1,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 6,
                "elements" : 11513,
                "height" : 2,
                "moves" : 2,
                "leafPages" : 5,
                "maxSearchStepsInRequest" : 548,
                "searchRequests" : 51446,
                "searchSteps" : 132183,
                "pageCapacity" : 32768,
                "sizeInBytes" : 196608
              }
            },
            "valueStorageSizeInBytes" : 258681
          }
        }
      },
      "FileNameWithoutExtensionIndex" : {
        "statsPerPhm" : {
          "FileNameWithoutExtensionIndex.storage" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 5030,
              "values" : 193436,
              "dataFileSizeInBytes" : 4854474,
              "storageSizeInBytes" : 1591600,
              "btreeStatistics" : {
                "pages" : 67,
                "elements" : 190677,
                "height" : 2,
                "moves" : 1006,
                "leafPages" : 66,
                "maxSearchStepsInRequest" : 89,
                "searchRequests" : 729557,
                "searchSteps" : 1067366,
                "pageCapacity" : 32768,
                "sizeInBytes" : 2195456
              }
            },
            "valueStorageSizeInBytes" : 2468043
          },
          "FileNameWithoutExtensionIndex_inputs" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : -1,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 163,
                "elements" : 358381,
                "height" : 2,
                "moves" : 4298,
                "leafPages" : 162,
                "maxSearchStepsInRequest" : 957,
                "searchRequests" : 1676198,
                "searchSteps" : 2109851,
                "pageCapacity" : 32768,
                "sizeInBytes" : 5341184
              }
            },
            "valueStorageSizeInBytes" : 9236769
          }
        }
      },
      "FrameworkDetectionIndex" : {
        "statsPerPhm" : {
          ".perFileVersion\\indexed_versions\\indexed_versions" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : 0,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 0,
                "elements" : 0,
                "height" : 0,
                "moves" : 0,
                "leafPages" : 1,
                "maxSearchStepsInRequest" : 0,
                "searchRequests" : 0,
                "searchSteps" : 0,
                "pageCapacity" : 32768,
                "sizeInBytes" : 0
              }
            },
            "valueStorageSizeInBytes" : 0
          },
          "FrameworkDetectionIndex.storage" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : 0,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 0,
                "elements" : 0,
                "height" : 0,
                "moves" : 0,
                "leafPages" : 1,
                "maxSearchStepsInRequest" : 0,
                "searchRequests" : 0,
                "searchSteps" : 0,
                "pageCapacity" : 32768,
                "sizeInBytes" : 0
              }
            },
            "valueStorageSizeInBytes" : 0
          },
          "FrameworkDetectionIndex_inputs" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : -1,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 0,
                "elements" : 0,
                "height" : 0,
                "moves" : 0,
                "leafPages" : 1,
                "maxSearchStepsInRequest" : 0,
                "searchRequests" : 0,
                "searchSteps" : 0,
                "pageCapacity" : 32768,
                "sizeInBytes" : 0
              }
            },
            "valueStorageSizeInBytes" : 0
          }
        }
      },
      "HtmlTagIdIndex" : {
        "statsPerPhm" : {
          "HtmlTagIdIndex.storage" : {
            "persistentEnumeratorStatistics" : {
              "collisions" : 0,
              "values" : 0,
              "dataFileSizeInBytes" : 0,
              "storageSizeInBytes" : 96,
              "btreeStatistics" : {
                "pages" : 0,
                "elements" : 0,
                "height" : 0,
                "moves" : 0,
                "leafPages" : 1,
                "maxSearchStepsInRequest" : 0,
                "searchRequests" : 0,
                "searchSteps" : 0,
                "pageCapacity" : 32768,
                "sizeInBytes" : 0
              }
            },
            "valueStorageSizeInBytes" : 0
          },
         