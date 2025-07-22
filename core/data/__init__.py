"""
Data access package.
Provides APIs for data retrieval, weather integration, and barn management.
"""

try:
    from .api_client import CompassAPI
    from .barn_list_parser import get_barn_manager, BarnClient
    from .weather_integration import get_real_weather_service
except ImportError:
    pass

__all__ = ['CompassAPI', 'get_barn_manager', 'BarnClient', 'get_real_weather_service']
