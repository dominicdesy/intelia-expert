"""
Weather data integration with factory pattern and interface contracts.

Dependencies:
- External WeatherAPI service for real weather data
- GPS coordinates from farm location data
- No internal system dependencies (base layer)
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

@dataclass
class Coordinates:
    """GPS coordinates for weather location lookup"""
    latitude: float
    longitude: float
    
    def to_query_string(self) -> str:
        """Convert coordinates to API query format"""
        return f"{self.latitude},{self.longitude}"

@dataclass
class WeatherData:
    """Weather measurement data structure"""
    temperature: float
    humidity: float
    condition: str
    wind_speed: Optional[float] = None
    pressure: Optional[float] = None

@dataclass
class FarmLocation:
    """Farm location with coordinates and metadata"""
    barn_id: str
    coordinates: Coordinates
    name: Optional[str] = None

class WeatherServiceInterface(ABC):
    """Contract for weather service implementations"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if weather service is configured and accessible"""
        pass
    
    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test service connectivity and return status with message"""
        pass
    
    @abstractmethod
    def get_weather(self, coordinates: Coordinates) -> Optional[WeatherData]:
        """Retrieve current weather data for given coordinates"""
        pass

class WeatherService:
    """Base weather service with mock implementation"""
    
    def __init__(self):
        self.api_key = None
    
    def is_available(self) -> bool:
        """Check API key availability"""
        return self.api_key is not None
    
    def test_connection(self) -> tuple[bool, str]:
        """Test mock connection"""
        if not self.is_available():
            return False, "API key not configured"
        return True, "Connection test not implemented"
    
    def get_weather(self, coordinates: Coordinates) -> Optional[WeatherData]:
        """Return mock weather data for testing"""
        return WeatherData(
            temperature=20.0,
            humidity=65.0,
            condition="Clear"
        )

def get_weather_service(config: Optional[Dict[str, Any]] = None) -> WeatherService:
    """
    Factory function for weather service instances.
    
    Args:
        config: Configuration dict with 'weather_api_key' and 'weather_provider'
        
    Returns:
        Appropriate weather service implementation
    """
    if not config:
        return WeatherService()
    
    # Future-extensible for multiple providers
    provider = config.get('weather_provider', 'weatherapi')
    api_key = config.get('weather_api_key')
    
    if api_key and provider == 'weatherapi':
        try:
            from .weather_integration import RealWeatherService
            return RealWeatherService()
        except ImportError:
            # Fallback if integration module unavailable
            return WeatherService()
    
    # Default mock service
    return WeatherService()

# Legacy compatibility - preserve existing function signatures
def create_mock_weather_service() -> WeatherService:
    """Create mock weather service for testing"""
    return WeatherService()
