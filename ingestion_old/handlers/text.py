"""text ingestion handler stub."""
from .base import BaseIngestionHandler, HandlerContext
from typing import Dict, Any, Optional

class TextIngestionHandler(BaseIngestionHandler):
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        return {"handler": "text", "file": str(context.file_path)}
    
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        try:
            with open(context.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except:
            return None

__all__ = ["TextIngestionHandler"]
