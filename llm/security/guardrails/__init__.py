# -*- coding: utf-8 -*-
"""
Guardrails Package - Modular Response Verification System

This package provides a modular architecture for verifying LLM responses
against source documents to detect hallucinations and ensure factual accuracy.

Main Components:
- GuardrailsOrchestrator: Main entry point for verification
- GuardrailResult: Result dataclass
- VerificationLevel: Enum for verification strictness levels

Usage:
    from security.guardrails import GuardrailsOrchestrator, VerificationLevel

    orchestrator = GuardrailsOrchestrator(
        client=openai_client,
        verification_level=VerificationLevel.STANDARD
    )

    result = await orchestrator.verify_response(
        query=user_query,
        response=llm_response,
        context_docs=documents
    )
"""

from .models import GuardrailResult, VerificationLevel
from .core import GuardrailsOrchestrator
from .cache import GuardrailCache
from .evidence_checker import EvidenceChecker
from .hallucination_detector import HallucinationDetector
from .relevance_checker import RelevanceChecker  # NEW: Add relevance checker
from .claims_extractor import ClaimsExtractor
from .text_analyzer import TextAnalyzer

__version__ = "2.1.0"  # NEW: Bump version for relevance feature

__all__ = [
    # Main API
    "GuardrailsOrchestrator",
    "GuardrailResult",
    "VerificationLevel",
    # Components (for advanced usage)
    "GuardrailCache",
    "EvidenceChecker",
    "HallucinationDetector",
    "RelevanceChecker",  # NEW: Export relevance checker
    "ClaimsExtractor",
    "TextAnalyzer",
]
