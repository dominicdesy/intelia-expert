# -*- coding: utf-8 -*-
"""
Generation Package - Modular Response Generation System
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Generation Package - Modular Response Generation System

Version 2.0 - Refactored modular architecture

This package provides a modular architecture for generating LLM responses
with entity enrichment, prompt building, and post-processing.

Main Components:
- ResponseGenerator: Main entry point (NEW)
- EnhancedResponseGenerator: Legacy API (DEPRECATED, uses ResponseGenerator internally)

Usage (New API):
    from generation import ResponseGenerator

    generator = ResponseGenerator(client=openai_client, language="fr")
    response = await generator.generate_response(query, context_docs)

Usage (Legacy API - Deprecated):
    from generation import EnhancedResponseGenerator

    generator = EnhancedResponseGenerator(client)  # Still works!
"""

# New modular API
from .models import ContextEnrichment
from .response_generator import ResponseGenerator, create_response_generator
from .entity_manager import EntityDescriptionsManager, EntityEnrichmentBuilder
from .language_handler import LanguageHandler
from .prompt_builder import PromptBuilder
from .post_processor import ResponsePostProcessor
from .veterinary_handler import VeterinaryHandler
from .document_utils import DocumentUtils

# Legacy API (backward compatibility)
from .generators import EnhancedResponseGenerator, create_enhanced_generator

__version__ = "2.0.0"

__all__ = [
    # Main API (NEW)
    "ResponseGenerator",
    "create_response_generator",
    "ContextEnrichment",
    # Components (for advanced usage)
    "EntityDescriptionsManager",
    "EntityEnrichmentBuilder",
    "LanguageHandler",
    "PromptBuilder",
    "ResponsePostProcessor",
    "VeterinaryHandler",
    "DocumentUtils",
    # Legacy API (DEPRECATED but still available)
    "EnhancedResponseGenerator",
    "create_enhanced_generator",
]
