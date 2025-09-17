# -*- coding: utf-8 -*-
"""
Security module - Sécurité et validation des réponses
"""

from .ood_detector import EnhancedOODDetector

try:
    from .advanced_guardrails import (
        AdvancedResponseGuardrails, 
        GuardrailResult,
        VerificationLevel,
        create_response_guardrails
    )
    GUARDRAILS_AVAILABLE = True
except ImportError:
    AdvancedResponseGuardrails = None
    GuardrailResult = None
    VerificationLevel = None
    create_response_guardrails = None
    GUARDRAILS_AVAILABLE = False

__all__ = [
    "EnhancedOODDetector",
    "AdvancedResponseGuardrails",
    "GuardrailResult", 
    "VerificationLevel",
    "create_response_guardrails",
    "GUARDRAILS_AVAILABLE"
]