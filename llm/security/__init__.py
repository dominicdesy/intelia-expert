# -*- coding: utf-8 -*-
"""
Security module - Sécurité et validation des réponses
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Security module - Sécurité et validation des réponses
"""

from .ood_detector import EnhancedOODDetector

# New modular guardrails architecture (recommended)
try:
    from .guardrails.core import GuardrailsOrchestrator
    from .guardrails.models import GuardrailResult, VerificationLevel

    GUARDRAILS_AVAILABLE = True
except ImportError:
    GuardrailsOrchestrator = None
    GuardrailResult = None
    VerificationLevel = None
    GUARDRAILS_AVAILABLE = False

# Legacy compatibility wrapper (deprecated)
try:
    from .advanced_guardrails import (
        AdvancedResponseGuardrails,
        create_response_guardrails,
    )

    LEGACY_GUARDRAILS_AVAILABLE = True
except ImportError:
    AdvancedResponseGuardrails = None
    create_response_guardrails = None
    LEGACY_GUARDRAILS_AVAILABLE = False

__all__ = [
    "EnhancedOODDetector",
    # New architecture (recommended)
    "GuardrailsOrchestrator",
    "GuardrailResult",
    "VerificationLevel",
    "GUARDRAILS_AVAILABLE",
    # Legacy (deprecated, for backward compatibility)
    "AdvancedResponseGuardrails",
    "create_response_guardrails",
    "LEGACY_GUARDRAILS_AVAILABLE",
]
