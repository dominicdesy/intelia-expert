# -*- coding: utf-8 -*-
"""
Services module for Intelia Expert LLM
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Services module for Intelia Expert LLM

Provides:
- AGROVOCService: Hybrid 3-level poultry term detection using FAO's AGROVOC
"""

from .agrovoc_service import AGROVOCService, get_agrovoc_service

__all__ = ["AGROVOCService", "get_agrovoc_service"]
