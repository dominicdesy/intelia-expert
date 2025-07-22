"""
Weather Integration with Virtual Barn Support
Clean code compliant version with proper error handling
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Virtual barn IDs that don't require GPS coordinates
VIRTUAL_BARN_IDS = ["expert_query", "default_barn", "virtual_barn", "test_barn"]


def get_weather_analysis_for_barn(barn_id: str, age: Optional[int] = None, language: str = "en") -> Optional[Dict[str, Any]]:
    """
    Get weather analysis for barn with virtual barn support.
    Returns None for virtual barns to avoid GPS coordinate errors.
    """
    
    # Handle virtual barns - no weather data needed
    if barn_id in VIRTUAL_BARN_IDS:
        logger.debug(f"Skipping weather analysis for virtual barn: {barn_id}")
        return None
    
    # Check for disabled weather integration
    import os
    if os.environ.get("DISABLE_WEATHER_FOR_EXPERT") == "true":
        logger.debug(f"Weather integration disabled for barn: {barn_id}")
        return None
    
    try:
        # Your existing weather integration logic here
        # This is where the original function would continue
        
        # For now, return a basic weather structure or None
        logger.info(f"Weather analysis requested for barn: {barn_id}")
        
        # If no GPS coordinates are available, return None instead of error
        gps_coordinates = get_barn_gps_coordinates(barn_id)
        if not gps_coordinates:
            logger.debug(f"No GPS coordinates found for barn {barn_id} - skipping weather analysis")
            return None
        
        # Continue with actual weather logic...
        weather_data = fetch_weather_data(gps_coordinates)
        
        if weather_data:
            return analyze_weather_impact(weather_data, age, language)
        
        return None
        
    except Exception as e:
        logger.warning(f"Weather analysis failed for barn {barn_id}: {e}")
        return None


def get_barn_gps_coordinates(barn_id: str) -> Optional[Tuple[float, float]]:
    """
    Get GPS coordinates for barn.
    Returns None for virtual barns or when coordinates are not available.
    """
    
    # Virtual barns don't have coordinates
    if barn_id in VIRTUAL_BARN_IDS:
        return None
    
    try:
        # Your existing logic to get GPS coordinates
        # This would typically query a database or configuration file
        
        # For demo purposes, return None if not found
        # In a real implementation, this would query your barn database
        
        barn_coordinates = {
            # Add your real barn coordinates here
            # "real_barn_001": (45.5017, -73.5673),  # Montreal coordinates example
        }
        
        return barn_coordinates.get(barn_id)
        
    except Exception as e:
        logger.error(f"Failed to get GPS coordinates for barn {barn_id}: {e}")
        return None


def fetch_weather_data(coordinates: Tuple[float, float]) -> Optional[Dict[str, Any]]:
    """
    Fetch weather data for given coordinates.
    """
    try:
        # Your existing weather API logic here
        lat, lon = coordinates
        
        # Mock weather data for now
        # Replace with your actual weather API call
        return {
            "temperature": 20.0,
            "humidity": 65,
            "condition": "Clear",
            "wind_speed": 10.0
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {e}")
        return None


def analyze_weather_impact(weather_data: Dict[str, Any], age: Optional[int], language: str) -> Dict[str, Any]:
    """
    Analyze weather impact on broiler performance.
    """
    try:
        # Your existing weather impact analysis logic
        temperature = weather_data.get("temperature", 20)
        humidity = weather_data.get("humidity", 60)
        
        # Simple impact analysis
        impact_score = calculate_weather_impact_score(temperature, humidity, age)
        
        return {
            "weather_data": weather_data,
            "impact_score": impact_score,
            "recommendations": generate_weather_recommendations(temperature, humidity, language),
            "language": language
        }
        
    except Exception as e:
        logger.error(f"Weather impact analysis failed: {e}")
        return {
            "weather_data": weather_data,
            "impact_score": 50.0,
            "recommendations": [],
            "language": language
        }


def calculate_weather_impact_score(temperature: float, humidity: float, age: Optional[int]) -> float:
    """Calculate weather impact score (0-100)."""
    try:
        # Optimal temperature range for broilers
        optimal_temp_min = 18.0
        optimal_temp_max = 24.0
        
        # Temperature score
        if optimal_temp_min <= temperature <= optimal_temp_max:
            temp_score = 100.0
        else:
            temp_deviation = min(abs(temperature - optimal_temp_min), abs(temperature - optimal_temp_max))
            temp_score = max(0, 100 - (temp_deviation * 5))
        
        # Humidity score (optimal 60-70%)
        if 60 <= humidity <= 70:
            humidity_score = 100.0
        else:
            humidity_deviation = min(abs(humidity - 60), abs(humidity - 70))
            humidity_score = max(0, 100 - (humidity_deviation * 2))
        
        # Combined score
        impact_score = (temp_score + humidity_score) / 2
        
        return round(impact_score, 1)
        
    except Exception as e:
        logger.error(f"Weather impact calculation failed: {e}")
        return 50.0


def generate_weather_recommendations(temperature: float, humidity: float, language: str) -> list:
    """Generate weather-based recommendations."""
    try:
        recommendations = []
        
        # Temperature recommendations
        if temperature > 25:
            if language == "fr":
                recommendations.append("Augmenter la ventilation pour réduire la température")
            else:
                recommendations.append("Increase ventilation to reduce temperature")
        elif temperature < 18:
            if language == "fr":
                recommendations.append("Augmenter le chauffage")
            else:
                recommendations.append("Increase heating")
        
        # Humidity recommendations
        if humidity > 75:
            if language == "fr":
                recommendations.append("Réduire l'humidité avec une meilleure ventilation")
            else:
                recommendations.append("Reduce humidity with better ventilation")
        elif humidity < 50:
            if language == "fr":
                recommendations.append("Augmenter l'humidité")
            else:
                recommendations.append("Increase humidity")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Weather recommendations generation failed: {e}")
        return []


# Compatibility functions
def get_real_weather_service():
    """Get real weather service instance."""
    return WeatherService()


class WeatherService:
    """Weather service class for compatibility."""
    
    def __init__(self):
        self.available = True
    
    def get_weather_data(self, coordinates=None):
        """Get weather data."""
        if coordinates:
            return fetch_weather_data(coordinates)
        return None
    
    def is_available(self):
        """Check if weather service is available."""
        return self.available
