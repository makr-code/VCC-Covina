"""Automation Scheduler - Minimal Stub"""
import logging
logger = logging.getLogger(__name__)

class AutomationScheduler:
    def __init__(self):
        logger.warning("AutomationScheduler STUB mode")
    
    def start(self): pass
    def stop(self): pass
    def schedule_task(self, task): pass
    
    @property
    def status(self): return {"mode": "STUB"}

__all__ = ["AutomationScheduler"]
