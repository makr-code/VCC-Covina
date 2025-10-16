"""Worker Executor - Minimal Stub"""
import logging
logger = logging.getLogger(__name__)

class WorkerExecutor:
    def __init__(self):
        logger.warning("WorkerExecutor STUB mode")
    
    def execute(self, task): pass
    def get_status(self): return {"mode": "STUB"}

__all__ = ["WorkerExecutor"]
