# -*- coding: utf-8 -*-
"""
rag_engine_handlers.py - DEPRECATED - Use handlers package instead

This file is kept for backward compatibility.
Import from handlers package directly:
    from core.handlers import (
        BaseQueryHandler,
        ComparativeQueryHandler,
        TemporalQueryHandler,
        StandardQueryHandler,
    )
"""

import warnings

# Import all handlers from the new package structure
from .handlers import (
    BaseQueryHandler,
    ComparativeQueryHandler,
    TemporalQueryHandler,
    StandardQueryHandler,
)

# Show deprecation warning when this module is imported
warnings.warn(
    "rag_engine_handlers.py is deprecated. "
    "Import from 'core.handlers' package instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "BaseQueryHandler",
    "ComparativeQueryHandler",
    "TemporalQueryHandler",
    "StandardQueryHandler",
]
