"""
VCC-Covina AI/ML Module
Self-hosted LLM, RAG, and MLOps infrastructure
On-premise, no vendor dependencies
"""

from ai_ml.llm import LLMService, LLMConfig
from ai_ml.rag import RAGPipeline, RAGConfig
from ai_ml.embeddings import EmbeddingService, EmbeddingConfig
from ai_ml.graphrag import GraphRAGPipeline, GraphRAGConfig

__all__ = [
    "LLMService",
    "LLMConfig",
    "RAGPipeline",
    "RAGConfig",
    "EmbeddingService",
    "EmbeddingConfig",
    "GraphRAGPipeline",
    "GraphRAGConfig",
]

__version__ = "1.0.0"
