"""
Ingestion Workers Package

Contains worker implementations for various ingestion tasks:
- Document similarity computation
- Quality metrics calculation  
- Semantic section detection

Author: GitHub Copilot
Date: 2025-11-19
"""

from ingestion.workers.similarity_worker import SimilarityWorker
from ingestion.workers.quality_worker import QualityMetricsWorker

__all__ = [
    'SimilarityWorker',
    'QualityMetricsWorker',
]
