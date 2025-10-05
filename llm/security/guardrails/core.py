# -*- coding: utf-8 -*-
"""
core.py - Main orchestrator for guardrails system

Simple orchestration layer that coordinates all verification modules.
"""

import asyncio
import logging
import time
from utils.types import Dict, List, Any

from .models import GuardrailResult, VerificationLevel
from .config import get_thresholds
from .cache import GuardrailCache
from .evidence_checker import EvidenceChecker
from .hallucination_detector import HallucinationDetector

logger = logging.getLogger(__name__)


class GuardrailsOrchestrator:
    """
    Main orchestrator for guardrails verification system

    Coordinates evidence checking, hallucination detection, and other
    verification modules to produce comprehensive guardrail results.
    """

    def __init__(
        self,
        client,
        verification_level: VerificationLevel = VerificationLevel.STANDARD,
        enable_cache: bool = True,
        cache_size: int = 1000,
    ):
        """
        Initialize orchestrator

        Args:
            client: LLM client for advanced verifications
            verification_level: Level of verification strictness
            enable_cache: Enable result caching
            cache_size: Maximum cache entries
        """
        self.client = client
        self.verification_level = verification_level
        self.enable_cache = enable_cache

        # Initialize modules
        self.cache = GuardrailCache(cache_size) if enable_cache else None
        self.evidence_checker = EvidenceChecker()
        self.hallucination_detector = HallucinationDetector()

        # Get validation thresholds for current level
        self.thresholds = get_thresholds(verification_level)

    async def verify_response(
        self,
        query: str,
        response: str,
        context_docs: List[Dict],
        intent_result=None,
        use_cache: bool = True,
    ) -> GuardrailResult:
        """
        Comprehensive response verification

        Args:
            query: User query
            response: LLM response to verify
            context_docs: Context documents for evidence checking
            intent_result: Optional intent classification result
            use_cache: Whether to use cache

        Returns:
            GuardrailResult with verification details
        """
        start_time = time.time()

        try:
            # Check cache
            cache_key = None
            if self.enable_cache and use_cache and self.cache:
                cache_key = self.cache.generate_key(
                    query, response, context_docs, self.verification_level
                )
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    cached_result.processing_time = time.time() - start_time
                    cached_result.metadata["cache_hit"] = True
                    return cached_result

            # Parallel verification tasks
            verification_tasks = [
                self.evidence_checker._check_evidence_support(response, context_docs),
                self.hallucination_detector._detect_hallucination_risk(
                    response, context_docs
                ),
            ]

            # Execute in parallel
            results = await asyncio.gather(*verification_tasks, return_exceptions=True)

            # Extract results safely
            evidence_score, evidence_details = self._safe_extract(results[0], (0.5, {}))
            hallucination_risk, hallucination_details = self._safe_extract(
                results[1], (0.5, {})
            )

            # Analyze violations and warnings
            violations, warnings, corrections = self._analyze_violations(
                evidence_score, hallucination_risk
            )

            # Calculate confidence
            confidence = self._calculate_confidence(
                evidence_score, hallucination_risk, len(violations), len(warnings)
            )

            # Make validation decision
            is_valid = self._make_validation_decision(
                evidence_score, hallucination_risk, len(violations), len(warnings)
            )

            processing_time = time.time() - start_time

            result = GuardrailResult(
                is_valid=is_valid,
                confidence=confidence,
                violations=violations,
                warnings=warnings,
                evidence_support=evidence_score,
                hallucination_risk=hallucination_risk,
                correction_suggestions=corrections,
                processing_time=processing_time,
                metadata={
                    "verification_level": self.verification_level.value,
                    "evidence_details": evidence_details,
                    "hallucination_details": hallucination_details,
                    "thresholds": self.thresholds,
                    "cache_hit": False,
                },
            )

            # Store in cache
            if self.enable_cache and cache_key and self.cache:
                self.cache.store(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Error in guardrails verification: {e}")
            processing_time = time.time() - start_time
            return GuardrailResult(
                is_valid=True,  # Fail-open for safety
                confidence=0.5,
                violations=[],
                warnings=[f"Verification error: {str(e)}"],
                evidence_support=0.5,
                hallucination_risk=0.5,
                correction_suggestions=["Manual verification recommended"],
                processing_time=processing_time,
                metadata={"error": str(e), "fallback_mode": True},
            )

    async def quick_verify(self, response: str, context_docs: List[Dict]) -> bool:
        """
        Quick verification (fast check)

        Args:
            response: Response to verify
            context_docs: Context documents

        Returns:
            True if response passes quick verification
        """
        try:
            # Quick document overlap check
            total_overlap = 0.0
            for doc in context_docs:
                overlap = await self.evidence_checker._quick_document_overlap(
                    response, doc
                )
                total_overlap += overlap

            avg_overlap = total_overlap / len(context_docs) if context_docs else 0
            return avg_overlap > 0.3  # 30% threshold for quick check

        except Exception as e:
            logger.warning(f"Quick verify error: {e}")
            return True  # Fail-open

    def _safe_extract(self, result, default):
        """Extract result safely, handling exceptions"""
        if isinstance(result, Exception):
            logger.warning(f"Verification task failed: {result}")
            return default
        return result

    def _analyze_violations(
        self, evidence_score: float, hallucination_risk: float
    ) -> tuple:
        """
        Analyze violations and generate warnings/corrections

        Returns:
            (violations, warnings, corrections)
        """
        violations = []
        warnings = []
        corrections = []

        thresholds = self.thresholds

        # Check evidence support
        if evidence_score < thresholds["evidence_min"]:
            violations.append(
                f"Insufficient evidence support ({evidence_score:.2f} < {thresholds['evidence_min']})"
            )
            corrections.append("Add explicit references to source documents")

        # Check hallucination risk
        if hallucination_risk > thresholds["hallucination_max"]:
            violations.append(
                f"High hallucination risk ({hallucination_risk:.2f} > {thresholds['hallucination_max']})"
            )
            corrections.append("Remove speculative language and opinions")

        # Warnings for borderline cases
        if (
            evidence_score < thresholds["evidence_min"] + 0.1
            and evidence_score >= thresholds["evidence_min"]
        ):
            warnings.append("Evidence support is borderline")

        if (
            hallucination_risk > thresholds["hallucination_max"] - 0.1
            and hallucination_risk <= thresholds["hallucination_max"]
        ):
            warnings.append("Hallucination risk is borderline")

        return violations, warnings, corrections

    def _calculate_confidence(
        self,
        evidence_score: float,
        hallucination_risk: float,
        violation_count: int,
        warning_count: int,
    ) -> float:
        """Calculate overall confidence score"""
        # Weighted combination
        base_confidence = (evidence_score * 0.6) + ((1 - hallucination_risk) * 0.4)

        # Penalties
        violation_penalty = violation_count * 0.15
        warning_penalty = warning_count * 0.05

        confidence = max(0.0, base_confidence - violation_penalty - warning_penalty)
        return min(1.0, confidence)

    def _make_validation_decision(
        self,
        evidence_score: float,
        hallucination_risk: float,
        violation_count: int,
        warning_count: int,
    ) -> bool:
        """Make final validation decision based on thresholds"""
        thresholds = self.thresholds

        # Check all criteria
        has_sufficient_evidence = evidence_score >= thresholds["evidence_min"]
        has_low_hallucination = hallucination_risk <= thresholds["hallucination_max"]
        has_acceptable_violations = violation_count <= thresholds.get(
            "max_violations", 0
        )
        has_acceptable_warnings = warning_count <= thresholds.get("max_warnings", 3)

        return all(
            [
                has_sufficient_evidence,
                has_low_hallucination,
                has_acceptable_violations,
                has_acceptable_warnings,
            ]
        )

    def clear_cache(self) -> int:
        """Clear cache and return number of entries removed"""
        if self.cache:
            return self.cache.clear()
        return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"cache_disabled": True}

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            "verification_level": self.verification_level.value,
            "cache_enabled": self.enable_cache,
            "thresholds": self.thresholds,
        }


__all__ = ["GuardrailsOrchestrator"]
