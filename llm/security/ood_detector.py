# -*- coding: utf-8 -*-
"""
ood_detector_refactored.py - Ultimate Backward Compatibility Wrapper
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
ood_detector_refactored.py - Ultimate Backward Compatibility Wrapper

DEPRECATION NOTICE:
    This module provides 100% backward compatibility with the original
    security/ood_detector.py file. It re-exports all classes and functions
    from the refactored security.ood package.

    For new code, please import directly from security.ood:
        from security.ood import OODDetector
        from security.ood import MultilingualOODDetector, EnhancedOODDetector
        from security.ood import create_ood_detector, create_multilingual_ood_detector

    This wrapper ensures that existing code importing from:
        from security.ood_detector import MultilingualOODDetector
        from security.ood_detector import EnhancedOODDetector
        from security.ood_detector import create_ood_detector

    ...will continue to work without any modifications.

Migration Guide:
    Old (still works):
        from security.ood_detector import MultilingualOODDetector
        detector = MultilingualOODDetector(blocked_terms_path="...")

    New (recommended):
        from security.ood import OODDetector
        detector = OODDetector(blocked_terms_path="...")

Version: 3.0.0 (Refactored)
Original: security/ood_detector.py (1,135 lines) -> security/ood/ (10 modules)
"""

# Re-export everything from the refactored security.ood package
from security.ood import (
    # Models
    DomainRelevance,
    DomainScore,
    # Main detector (new API)
    OODDetector,
    # Legacy wrappers (backward compatibility)
    MultilingualOODDetector,
    EnhancedOODDetector,
    # Factory functions
    create_ood_detector,
    create_multilingual_ood_detector,
    # Version
    __version__,
)

# Re-export __all__ for compatibility
__all__ = [
    # Models
    "DomainRelevance",
    "DomainScore",
    # New API
    "OODDetector",
    # Legacy API
    "MultilingualOODDetector",
    "EnhancedOODDetector",
    # Factory functions
    "create_ood_detector",
    "create_multilingual_ood_detector",
    # Version
    "__version__",
]
