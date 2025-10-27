# -*- coding: utf-8 -*-
"""
advanced_guardrails_refactored.py - Backward compatibility wrapper
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
advanced_guardrails_refactored.py - Backward compatibility wrapper

This file maintains backward compatibility with the old AdvancedResponseGuardrails API
while using the new modular architecture underneath.

DEPRECATED: Use GuardrailsOrchestrator from security.guardrails.core directly.
"""

import logging
from utils.types import Dict, List, Any

from security.guardrails.models import GuardrailResult, VerificationLevel
from security.guardrails.core import GuardrailsOrchestrator

logger = logging.getLogger(__name__)


class AdvancedResponseGuardrails:
    """
    DEPRECATED: Backward compatibility wrapper for AdvancedResponseGuardrails

    Use GuardrailsOrchestrator from security.guardrails.core instead.

    This class provides the same interface as the old monolithic implementation
    but delegates to the new modular architecture.
    """

    def __init__(
        self,
        client,
        verification_level: VerificationLevel = VerificationLevel.STANDARD,
        enable_cache: bool = True,
        cache_size: int = 1000,
    ):
        """
        Initialize guardrails (delegates to GuardrailsOrchestrator)

        Args:
            client: LLM client
            verification_level: Verification level
            enable_cache: Enable caching
            cache_size: Cache size
        """
        logger.warning(
            "AdvancedResponseGuardrails is deprecated. "
            "Use GuardrailsOrchestrator from security.guardrails.core instead."
        )

        # Delegate to new implementation
        self._orchestrator = GuardrailsOrchestrator(
            client=client,
            verification_level=verification_level,
            enable_cache=enable_cache,
            cache_size=cache_size,
        )

        # Expose inner attributes for backward compatibility
        self.client = client
        self.verification_level = verification_level
        self.enable_cache = enable_cache

    async def verify_response(
        self,
        query: str,
        response: str,
        context_docs: List[Dict],
        intent_result=None,
        use_cache: bool = True,
    ) -> GuardrailResult:
        """Verify response (delegates to orchestrator)"""
        return await self._orchestrator.verify_response(
            query, response, context_docs, intent_result, use_cache
        )

    async def quick_verify(self, response: str, context_docs: List[Dict]) -> bool:
        """Quick verify (delegates to orchestrator)"""
        return await self._orchestrator.quick_verify(response, context_docs)

    def clear_cache(self) -> int:
        """Clear cache (delegates to orchestrator)"""
        return self._orchestrator.clear_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache stats (delegates to orchestrator)"""
        return self._orchestrator.get_cache_stats()

    def get_guardrails_config(self) -> Dict[str, Any]:
        """Get config (delegates to orchestrator)"""
        return self._orchestrator.get_config()


def create_response_guardrails(
    client,
    verification_level: str = "standard",
    enable_cache: bool = True,
    cache_size: int = 1000,
) -> AdvancedResponseGuardrails:
    """
    Factory function (backward compatibility)

    DEPRECATED: Use GuardrailsOrchestrator directly.

    Args:
        client: LLM client
        verification_level: "minimal", "standard", "strict", or "critical"
        enable_cache: Enable caching
        cache_size: Cache size

    Returns:
        AdvancedResponseGuardrails instance
    """
    logger.warning(
        "create_response_guardrails is deprecated. "
        "Use GuardrailsOrchestrator from security.guardrails.core instead."
    )

    level_map = {
        "minimal": VerificationLevel.MINIMAL,
        "standard": VerificationLevel.STANDARD,
        "strict": VerificationLevel.STRICT,
        "critical": VerificationLevel.CRITICAL,
    }

    level = level_map.get(verification_level.lower(), VerificationLevel.STANDARD)
    return AdvancedResponseGuardrails(client, level, enable_cache, cache_size)


__all__ = [
    "AdvancedResponseGuardrails",
    "GuardrailResult",
    "VerificationLevel",
    "create_response_guardrails",
]
