#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Covina Backend Startup Script

Startet das Enhanced Covina Backend mit Multi-Database Distribution
und stellt eine nahtlose Integration mit dem bestehenden System bereit.

Usage:
    python enhanced_covina_backend.py                    # Standard startup
    python enhanced_covina_backend.py --multi-db         # Mit Multi-DB Distribution
    python enhanced_covina_backend.py --performance      # Mit Performance Monitoring
    python enhanced_covina_backend.py --quick-test       # Quick Performance Test
    python enhanced_covina_backend.py --benchmark        # Full Benchmark Suite

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import sys
import os
import json
import signal
from pathlib import Path
from typing import Optional
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_covina_backend.log')
    ]
)

logger = logging.getLogger("EnhancedCovinaBackend")

# Import enhanced components
try:
    from uds3_production_integration import (
        initialize_enhanced_covina_backend,
        create_production_multi_db_config,
        ProductionMultiDBConfig,
        MULTI_DB_DISTRIBUTION_AVAILABLE
    )
    INTEGRATION_AVAILABLE = True
except ImportError as e:
    logger.error(f"Enhanced integration not available: {e}")
    INTEGRATION_AVAILABLE = False

# Import existing Covina Backend
try:
    from backend import UDS3JobManager
    COVINA_BACKEND_AVAILABLE = True
except ImportError:
    logger.error("Covina Backend not available")
    COVINA_BACKEND_AVAILABLE = False

# Global state
enhanced_job_manager: Optional[object] = None
shutdown_event = asyncio.Event()


def print_startup_banner():
    """Prints enhanced startup banner"""
    
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     🚀 Enhanced Covina Backend v1.0.0                       ║
    ║                                                              ║
    ║     Multi-Database Distribution System                       ║
    ║     Enterprise-Ready Document Processing                     ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    
    print(banner)
    print(f"📅 Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 Integration Available: {'✅' if INTEGRATION_AVAILABLE else '❌'}")
    print(f"📦 Multi-DB Distribution: {'✅' if MULTI_DB_DISTRIBUTION_AVAILABLE else '❌'}")
    print(f"🏠 Covina Backend: {'✅' if COVINA_BACKEND_AVAILABLE else '❌'}")
    print()


def setup_signal_handlers():
    """Sets up graceful shutdown signal handlers"""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def start_enhanced_backend(enable_multi_db: bool = True, enable_performance: bool = False):
    """Starts the enhanced backend with specified options"""
    
    global enhanced_job_manager
    
    try:
        if enable_multi_db and INTEGRATION_AVAILABLE:
            logger.info("🔧 Starting Enhanced Covina Backend with Multi-DB Distribution...")
            
            # Initialize enhanced job manager
            enhanced_job_manager = await initialize_enhanced_covina_backend()
            
            if enhanced_job_manager:
                logger.info("✅ Enhanced Covina Backend started successfully")
                
                # Print initial statistics
                if enable_performance:
                    stats = enhanced_job_manager.get_enhanced_statistics()
                    logger.info("📊 Initial Statistics:")
                    logger.info(json.dumps(stats, indent=2, default=str))
                
                return True
            else:
                logger.error("❌ Failed to start Enhanced Covina Backend")
                return False
        
        elif COVINA_BACKEND_AVAILABLE:
            logger.info("📦 Starting Standard Covina Backend...")
            
            # Fallback to standard Covina Backend
            enhanced_job_manager = UDS3JobManager()
            
            # Initialize if it has an initialize method
            if hasattr(enhanced_job_manager, 'initialize'):
                await enhanced_job_manager.initialize()
            
            logger.info("✅ Standard Covina Backend started")
            return True
        
        else:
            logger.error("❌ No backend components available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to start backend: {e}")
        return False


async def run_performance_test(quick: bool = True):
    """Runs performance tests on the Multi-DB system"""
    
    if not MULTI_DB_DISTRIBUTION_AVAILABLE:
        logger.error("❌ Multi-DB Distribution not available for performance testing")
        return
    
    try:
        if quick:
            logger.info("⚡ Running quick performance test...")
            from uds3.performance_testing_optimization import run_quick_performance_check
            await run_quick_performance_check()
        else:
            logger.info("🔄 Running comprehensive performance benchmark...")
            from uds3.performance_testing_optimization import run_full_performance_suite
            await run_full_performance_suite()
            
        logger.info("✅ Performance testing completed")
        
    except Exception as e:
        logger.error(f"❌ Performance testing failed: {e}")


async def monitor_system_health():
    """Monitors system health while backend is running"""
    
    global enhanced_job_manager
    
    while not shutdown_event.is_set():
        try:
            if enhanced_job_manager and hasattr(enhanced_job_manager, 'get_enhanced_statistics'):
                stats = enhanced_job_manager.get_enhanced_statistics()
                
                # Log key metrics
                integration_stats = stats.get('enhanced_job_manager', {}).get('integration_stats', {})
                
                if integration_stats.get('distributions_processed', 0) > 0:
                    logger.info(
                        f"📊 Processed: {integration_stats.get('distributions_processed', 0)}, "
                        f"Errors: {integration_stats.get('errors_encountered', 0)}, "
                        f"Fallbacks: {integration_stats.get('fallbacks_used', 0)}"
                    )
            
            # Wait before next health check
            await asyncio.wait_for(shutdown_event.wait(), timeout=60.0)
            
        except asyncio.TimeoutError:
            # Normal timeout, continue monitoring
            continue
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
            await asyncio.sleep(30.0)


async def graceful_shutdown():
    """Performs graceful shutdown of the enhanced backend"""
    
    global enhanced_job_manager
    
    logger.info("🔄 Starting graceful shutdown...")
    
    try:
        if enhanced_job_manager and hasattr(enhanced_job_manager, 'shutdown_enhanced_features'):
            await enhanced_job_manager.shutdown_enhanced_features()
        
        logger.info("✅ Graceful shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def main():
    """Main application entry point"""
    
    print_startup_banner()
    setup_signal_handlers()
    
    # Parse command line arguments
    enable_multi_db = "--multi-db" in sys.argv or "--performance" in sys.argv
    enable_performance = "--performance" in sys.argv
    quick_test = "--quick-test" in sys.argv
    benchmark = "--benchmark" in sys.argv
    
    # Handle special modes
    if quick_test:
        await run_performance_test(quick=True)
        return
    
    if benchmark:
        await run_performance_test(quick=False)
        return
    
    # Start the backend
    success = await start_enhanced_backend(
        enable_multi_db=enable_multi_db,
        enable_performance=enable_performance
    )
    
    if not success:
        logger.error("❌ Failed to start backend")
        sys.exit(1)
    
    # Start monitoring task
    monitoring_task = asyncio.create_task(monitor_system_health())
    
    try:
        logger.info("🎯 Enhanced Covina Backend is running...")
        logger.info("Press Ctrl+C to shutdown gracefully")
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
    finally:
        # Cancel monitoring
        monitoring_task.cancel()
        
        # Graceful shutdown
        await graceful_shutdown()
        
        logger.info("👋 Enhanced Covina Backend shutdown complete")


def print_usage():
    """Prints usage information"""
    
    usage = """
Enhanced Covina Backend - Usage:

Basic Commands:
    python enhanced_covina_backend.py                    # Standard startup
    python enhanced_covina_backend.py --multi-db         # With Multi-DB Distribution  
    python enhanced_covina_backend.py --performance      # With Performance Monitoring

Testing Commands:
    python enhanced_covina_backend.py --quick-test       # Quick Performance Test
    python enhanced_covina_backend.py --benchmark        # Full Benchmark Suite

Environment Variables:
    UDS3_ENVIRONMENT                    # development|staging|production
    POSTGRESQL_HOST                     # PostgreSQL host (default: localhost)
    POSTGRESQL_PORT                     # PostgreSQL port (default: 5432)
    COUCHDB_HOST                        # CouchDB host (default: localhost)
    COUCHDB_PORT                        # CouchDB port (default: 5984)
    CHROMADB_HOST                       # ChromaDB host (default: localhost)
    CHROMADB_PORT                       # ChromaDB port (default: 8000)
    NEO4J_URI                          # Neo4j URI (default: bolt://localhost:7687)

Examples:
    # Development with SQLite fallback
    UDS3_ENVIRONMENT=development python enhanced_covina_backend.py
    
    # Production with full Multi-DB
    UDS3_ENVIRONMENT=production python enhanced_covina_backend.py --multi-db
    
    # Performance testing
    python enhanced_covina_backend.py --benchmark
"""
    
    print(usage)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        sys.exit(0)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Shutdown by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)       