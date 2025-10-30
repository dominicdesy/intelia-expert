"""
Compass API Service - Adapter for Intelia Compass platform
Version: 1.0.0
Date: 2025-10-30
Description: Service to interact with Compass API for real-time barn data
Adapted from: broiler-agent/broiler_agent/core/data/api_client.py
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CompassBarnData:
    """Real-time barn data from Compass"""
    device_id: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    average_weight: Optional[float] = None  # in grams
    age_days: Optional[int] = None
    production_day: Optional[int] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "device_id": self.device_id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "average_weight": self.average_weight,
            "age_days": self.age_days,
            "production_day": self.production_day,
            "timestamp": self.timestamp
        }


class CompassAPIService:
    """Service to interact with Compass API"""

    # Default configuration
    DEFAULT_BASE_URL = "https://compass.intelia.com/api/v1"
    REQUEST_TIMEOUT = 30

    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Compass API Service

        Args:
            api_token: Compass API token (if None, uses COMPASS_API_TOKEN env var)
            base_url: Compass API base URL (if None, uses default)
        """
        self.api_token = api_token or os.getenv("COMPASS_API_TOKEN")
        self.base_url = base_url or self.DEFAULT_BASE_URL

        if not self.api_token:
            logger.warning("COMPASS_API_TOKEN not configured - API calls will fail")

        self.headers = {
            "api_authorization": self.api_token
        }

        # Create session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        logger.info(f"CompassAPIService initialized with base URL: {self.base_url}")

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute HTTP GET request

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response JSON or None if failed
        """
        url = f"{self.base_url}{endpoint}"

        try:
            logger.debug(f"GET {url} with params {params}")
            response = self.session.get(url, params=params, timeout=self.REQUEST_TIMEOUT)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: HTTP {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"API request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            return None

    def get_device_list(self, entity_id: Optional[int] = None) -> List[Dict]:
        """
        Get list of all devices accessible via API

        Args:
            entity_id: Optional entity ID to filter devices

        Returns:
            List of device dictionaries
        """
        params = {"entity_id": entity_id} if entity_id else None
        response = self._get("/devices", params)

        if response and "devices" in response:
            devices = response["devices"]
            logger.info(f"Retrieved {len(devices)} devices from Compass")
            return devices

        logger.warning("Failed to retrieve device list")
        return []

    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """
        Get device information including name

        Args:
            device_id: Device ID

        Returns:
            Device info dictionary or None
        """
        response = self._get(f"/devices/{device_id}")

        if response:
            logger.debug(f"Retrieved device info for {device_id}")
            return response

        logger.warning(f"Failed to retrieve device info for {device_id}")
        return None

    def get_latest_data(self, device_id: str, tag_name: str) -> Optional[Dict]:
        """
        Get latest sensor data for specific tag

        Args:
            device_id: Device ID
            tag_name: Sensor tag name (e.g., "Temperature", "Humidity")

        Returns:
            Sensor data dictionary or None
        """
        endpoint = f"/user/devices/{device_id}/sensors/data/latest"
        params = {"tag_names[]": [tag_name]}

        response = self._get(endpoint, params)

        if not response:
            return None

        # Extract sensor data from response
        sensor_data = self._extract_sensor_data(response)

        if sensor_data:
            logger.debug(f"Retrieved latest data for {device_id}/{tag_name}")
            return sensor_data[0]

        logger.warning(f"No data found for {device_id}/{tag_name}")
        return None

    def _extract_sensor_data(self, response: Dict) -> List[Dict]:
        """
        Extract sensor data array from API response

        Args:
            response: API response dictionary

        Returns:
            List of sensor data records
        """
        if not response:
            return []

        # Handle different response structures
        if "sensors_data" in response:
            return response["sensors_data"] or []
        elif "latest_sensors_data" in response:
            return response["latest_sensors_data"] or []
        elif "data" in response:
            data = response["data"]
            if "sensors_data" in data:
                return data["sensors_data"] or []
            elif "latest_sensors_data" in data:
                return data["latest_sensors_data"] or []

        return []

    def _extract_numeric_value(self, record: Optional[Dict], field: str = "latest_value") -> Optional[float]:
        """
        Extract numeric value from sensor record

        Args:
            record: Sensor data record
            field: Field name to extract

        Returns:
            Float value or None
        """
        if not record:
            return None

        value = record.get(field)
        if value is None:
            return None

        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert {field}={value} to float")
            return None

    def get_barn_realtime_data(self, device_id: str) -> CompassBarnData:
        """
        Get comprehensive real-time data for a barn

        Args:
            device_id: Device ID

        Returns:
            CompassBarnData object with all available data
        """
        logger.info(f"Fetching real-time data for device {device_id}")

        barn_data = CompassBarnData(device_id=device_id)
        barn_data.timestamp = datetime.utcnow().isoformat()

        # Temperature
        temp_data = self.get_latest_data(device_id, "Temperature")
        if temp_data:
            barn_data.temperature = self._extract_numeric_value(temp_data)

        # Humidity
        humidity_data = self.get_latest_data(device_id, "Humidity")
        if humidity_data:
            barn_data.humidity = self._extract_numeric_value(humidity_data)

        # Weight (API returns kg, convert to grams)
        weight_data = self.get_latest_data(device_id, "AveragePoultryWeight")
        if weight_data:
            weight_kg = self._extract_numeric_value(weight_data)
            if weight_kg:
                barn_data.average_weight = weight_kg * 1000  # Convert to grams

        # Production Day (age in days)
        age_data = self.get_latest_data(device_id, "ProductionDay")
        if age_data:
            age_value = self._extract_numeric_value(age_data)
            if age_value:
                barn_data.age_days = int(age_value)
                barn_data.production_day = int(age_value)

        logger.info(f"Retrieved barn data: temp={barn_data.temperature}, humidity={barn_data.humidity}, "
                   f"weight={barn_data.average_weight}, age={barn_data.age_days}")

        return barn_data

    def test_connection(self) -> bool:
        """
        Test API connectivity

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("Testing Compass API connection...")
            device_list = self.get_device_list()
            success = device_list is not None

            if success:
                logger.info("Compass API connection test successful")
            else:
                logger.error("Compass API connection test failed")

            return success
        except Exception as e:
            logger.error(f"Compass API connection test error: {e}")
            return False

    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
            logger.debug("Compass API session closed")


# Singleton instance for easy access
_compass_service_instance: Optional[CompassAPIService] = None


def get_compass_service() -> CompassAPIService:
    """
    Get singleton instance of CompassAPIService

    Returns:
        CompassAPIService instance
    """
    global _compass_service_instance

    if _compass_service_instance is None:
        _compass_service_instance = CompassAPIService()

    return _compass_service_instance


# Helper functions for common operations
def get_barn_temperature(device_id: str) -> Optional[float]:
    """
    Get current temperature for a barn

    Args:
        device_id: Device ID

    Returns:
        Temperature in Celsius or None
    """
    service = get_compass_service()
    data = service.get_latest_data(device_id, "Temperature")
    return service._extract_numeric_value(data) if data else None


def get_barn_humidity(device_id: str) -> Optional[float]:
    """
    Get current humidity for a barn

    Args:
        device_id: Device ID

    Returns:
        Humidity percentage or None
    """
    service = get_compass_service()
    data = service.get_latest_data(device_id, "Humidity")
    return service._extract_numeric_value(data) if data else None


def get_barn_weight(device_id: str) -> Optional[float]:
    """
    Get current average poultry weight for a barn

    Args:
        device_id: Device ID

    Returns:
        Weight in grams or None
    """
    service = get_compass_service()
    data = service.get_latest_data(device_id, "AveragePoultryWeight")
    if data:
        weight_kg = service._extract_numeric_value(data)
        return weight_kg * 1000 if weight_kg else None
    return None


def get_barn_age(device_id: str) -> Optional[int]:
    """
    Get flock age for a barn

    Args:
        device_id: Device ID

    Returns:
        Age in days or None
    """
    service = get_compass_service()
    data = service.get_latest_data(device_id, "ProductionDay")
    if data:
        age_value = service._extract_numeric_value(data)
        return int(age_value) if age_value else None
    return None
