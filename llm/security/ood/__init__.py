# -*- coding: utf-8 -*-
"""
security.ood - Out-Of-Domain Detection Module (Refactored v3.0.0)
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
security.ood - Out-Of-Domain Detection Module (Refactored v3.0.0)

This package provides multilingual out-of-domain detection capabilities
for filtering queries that fall outside the poultry farming domain.

Architecture:
    - Modular design with separated concerns
    - Translation service integration with robust fallback
    - Language-specific normalization and analysis
    - Adaptive thresholds based on query context
    - Comprehensive backward compatibility layer

New API (Recommended):
    from security.ood import OODDetector

    detector = OODDetector(blocked_terms_path="path/to/blocked.json")
    is_in_domain, score, details = detector.calculate_ood_score_multilingual(
        query="Ma question",
        intent_result=None,
        language="fr"
    )

Legacy API (Backward Compatibility):
    from security.ood import MultilingualOODDetector, EnhancedOODDetector
    from security.ood import create_ood_detector, create_multilingual_ood_detector

    # These wrappers provide 100% backward compatibility with the original API
    detector = MultilingualOODDetector(blocked_terms_path="path/to/blocked.json")
    detector = EnhancedOODDetector(blocked_terms_path="path/to/blocked.json", openai_client=None)

    # Factory functions also available
    detector = create_ood_detector(blocked_terms_path="path/to/blocked.json")
    detector = create_multilingual_ood_detector(blocked_terms_path="path/to/blocked.json")

Version: 3.0.0
"""

# Import new API - Main detector
from .detector import OODDetector

# Import models
from .models import DomainRelevance, DomainScore

# Import backward compatibility wrappers
from utils.types import Dict, Tuple

import logging

logger = logging.getLogger(__name__)

__version__ = "3.0.0"


# ===== BACKWARD COMPATIBILITY LAYER =====


class MultilingualOODDetector:
    """
    Backward compatibility wrapper for the original MultilingualOODDetector class.

    This class delegates all method calls to the new OODDetector implementation
    while maintaining the exact same API as the original class.

    Args:
        blocked_terms_path: Optional path to blocked terms JSON file
    """

    def __init__(self, blocked_terms_path: str = None):
        """Initialize the detector wrapper with backward compatible signature."""
        self._detector = OODDetector(blocked_terms_path=blocked_terms_path)
        # Expose properties for backward compatibility
        self.blocked_terms = self._detector.blocked_terms
        self.domain_vocabulary = self._detector.domain_vocabulary
        self.supported_languages = self._detector.supported_languages
        self.default_language = self._detector.default_language

    def calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Main entry point for multilingual OOD detection.

        Args:
            query: The user query to analyze
            intent_result: Optional intent detection result
            language: Optional language code (auto-detected if None)

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        return self._detector.calculate_ood_score_multilingual(
            query=query, intent_result=intent_result, language=language
        )

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Legacy entry point for OOD detection using default language.

        Args:
            query: The user query to analyze
            intent_result: Optional intent detection result

        Returns:
            Tuple of (is_in_domain, score, details_dict)
        """
        return self._detector.calculate_ood_score(
            query=query, intent_result=intent_result
        )

    def get_detector_stats(self) -> Dict:
        """
        Get detector statistics.

        Returns:
            Dictionary with detector statistics
        """
        return self._detector.get_detector_stats()

    def test_query_analysis(self, query: str, language: str = None) -> Dict:
        """
        Test and diagnose a query.

        Args:
            query: The query to test
            language: Optional language code (auto-detected if None)

        Returns:
            Dictionary with detailed analysis results
        """
        return self._detector.test_query_analysis(query=query, language=language)


class EnhancedOODDetector(MultilingualOODDetector):
    """
    Backward compatibility wrapper for the original EnhancedOODDetector class.

    This class extends MultilingualOODDetector and adds a compatibility method
    for calculate_ood_score that was specific to EnhancedOODDetector.

    Args:
        blocked_terms_path: Optional path to blocked terms JSON file
        openai_client: Legacy parameter (ignored, kept for API compatibility)
    """

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        """
        Initialize the enhanced detector wrapper.

        Note: openai_client parameter is ignored as we use the universal
        translation service, but it's kept for backward compatibility.
        """
        super().__init__(blocked_terms_path=blocked_terms_path)
        # Log deprecation of openai_client parameter if provided
        if openai_client is not None:
            logger.debug(
                "openai_client parameter is deprecated and ignored. "
                "Using universal translation service instead."
            )


# ===== FACTORY FUNCTIONS =====


def create_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> EnhancedOODDetector:
    """
    Create an instance of the OOD detector with backward compatibility.

    Factory function that creates an EnhancedOODDetector instance.

    Args:
        blocked_terms_path: Optional path to blocked terms JSON file
        openai_client: Legacy parameter (ignored, kept for API compatibility)

    Returns:
        EnhancedOODDetector instance
    """
    return EnhancedOODDetector(
        blocked_terms_path=blocked_terms_path, openai_client=openai_client
    )


def create_multilingual_ood_detector(
    blocked_terms_path: str = None,
) -> MultilingualOODDetector:
    """
    Create an instance of the multilingual OOD detector.

    Factory function that creates a MultilingualOODDetector instance.

    Args:
        blocked_terms_path: Optional path to blocked terms JSON file

    Returns:
        MultilingualOODDetector instance
    """
    return MultilingualOODDetector(blocked_terms_path=blocked_terms_path)


# ===== PUBLIC EXPORTS =====

__all__ = [
    # Version
    "__version__",
    # New API - Recommended
    "OODDetector",
    # Models
    "DomainRelevance",
    "DomainScore",
    # Legacy API - Backward Compatibility
    "MultilingualOODDetector",
    "EnhancedOODDetector",
    # Factory functions
    "create_ood_detector",
    "create_multilingual_ood_detector",
]
