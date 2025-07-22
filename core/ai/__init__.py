"""
AI and machine learning package.
Provides AI clients, prompt generation, and RAG capabilities.
"""

try:
    from .ai_client import BroilerAnalyzer as BroilerAIAnalyzer
    from .rag_ai_bridge import RAGAIBridge
    from .prompt_generator import *
except ImportError:
    pass

__all__ = ['BroilerAIAnalyzer', 'RAGAIBridge']