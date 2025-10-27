# -*- coding: utf-8 -*-
"""
Central type definitions for entire LLM codebase
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Central type definitions for entire LLM codebase

This module consolidates all common typing imports to reduce duplication
across 65+ files that were importing the same types individually.

Usage:
    from utils.types import Dict, List, JSON, Optional

Instead of:
    from typing import Dict, List, Any, Optional
"""

from typing import (
    Dict,
    List,
    Any,
    Optional,
    Tuple,
    Union,
    Callable,
    Awaitable,
    Set,
    Iterable,
    TypeVar,
    Generic,
    Protocol,
    Literal,
    cast,
)

# Common type aliases
JSON = Dict[str, Any]
JSONList = List[JSON]
Headers = Dict[str, str]
QueryParams = Dict[str, Any]
Metadata = Dict[str, Any]

# Generic type variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

# Export all
__all__ = [
    # Basic types
    "Dict",
    "List",
    "Any",
    "Optional",
    "Tuple",
    "Union",
    "Callable",
    "Awaitable",
    "Set",
    "Iterable",
    "TypeVar",
    "Generic",
    "Protocol",
    "Literal",
    "cast",
    # Type aliases
    "JSON",
    "JSONList",
    "Headers",
    "QueryParams",
    "Metadata",
    # Type variables
    "T",
    "K",
    "V",
]
