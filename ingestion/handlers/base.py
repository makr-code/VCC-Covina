"""Base ingestion handler and context."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class HandlerContext:
    """Context passed to ingestion handlers."""
    file_path: Path
    temp_dir: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tables: Optional[list] = None  # NEW: Store extracted tables
    
    def __post_init__(self):
        """Ensure paths are Path objects"""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        if isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir)


class BaseIngestionHandler(ABC):
    """Base class for all file type handlers."""
    
    category: Optional[str] = None  # Set by registry
    
    @abstractmethod
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        """Extract metadata from file.
        
        Args:
            context: Handler context with file path
            
        Returns:
            Dictionary with extracted metadata
        """
        pass
    
    @abstractmethod
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract text content from file.
        
        Args:
            context: Handler context
            metadata: Previously extracted metadata
            
        Returns:
            Extracted text content or None
        """
        pass
    
    def handle(self, context: HandlerContext) -> Dict[str, Any]:
        """Main entry point - extract metadata and content.
        
        Args:
            context: Handler context
            
        Returns:
            Dictionary with metadata and content
        """
        metadata = self.extract_metadata(context)
        content = self.extract_content(context, metadata)
        
        return {
            "metadata": metadata,
            "content": content,
            "file_path": str(context.file_path),
            "category": self.category
        }


__all__ = ["BaseIngestionHandler", "HandlerContext"]
