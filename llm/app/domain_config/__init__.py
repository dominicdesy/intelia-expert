"""
LLM Service Domain Configuration Module

This module provides domain-specific configurations for the LLM service.
Configurations are organized by domain (e.g., aviculture, agriculture, etc.)
"""

from .domains.aviculture.config import AvicultureConfig, get_aviculture_config

__all__ = [
    "AvicultureConfig",
    "get_aviculture_config",
]

# Domain registry for multi-domain support
AVAILABLE_DOMAINS = {
    "aviculture": get_aviculture_config,
}


def get_domain_config(domain_name: str):
    """
    Get configuration for a specific domain

    Args:
        domain_name: Name of the domain (e.g., "aviculture")

    Returns:
        Domain configuration instance

    Raises:
        ValueError: If domain is not supported
    """
    if domain_name not in AVAILABLE_DOMAINS:
        raise ValueError(
            f"Unsupported domain: {domain_name}. "
            f"Available domains: {list(AVAILABLE_DOMAINS.keys())}"
        )

    return AVAILABLE_DOMAINS[domain_name]()
