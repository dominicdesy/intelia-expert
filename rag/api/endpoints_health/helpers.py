# -*- coding: utf-8 -*-
"""
api/endpoints_health/helpers.py - Shared helper functions for health endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_health/helpers.py - Shared helper functions for health endpoints
"""

import logging
from utils.types import Any

logger = logging.getLogger(__name__)


def get_service_from_dict(services: dict, name: str) -> Any:
    """Helper to retrieve a service from the services dictionary"""
    return services.get(name)
