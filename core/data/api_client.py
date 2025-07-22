"""
Compass API client for broiler management system.
"""

import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Import constants with fallbacks
try:
    from .constants import APIConfig, SensorDefaults
    from .error_handler import get_error_handler
    from .config_loader import get_api_key
except ImportError:
    class APIConfig:
        REQUEST_TIMEOUT = 30
        DEFAULT_COMPASS_BASE_URL = "https://compass.intelia.com/api/v1"
    
    class SensorDefaults:
        WEIGHT_SENSORS = ["AveragePoultryWeight", "AvgWeight", "Weight"]
        TEMPERATURE_SENSORS = ["Temperature", "Temp", "AmbientTemperature"]
        HUMIDITY_SENSORS = ["Humidity", "RelativeHumidity", "RH"]
        PRODUCTION_DAY = "ProductionDay"
        POULTRY_CURVE = "PoultryCurve"
        AVERAGE_WEIGHT = "AveragePoultryWeight"
    
    def get_error_handler(module_name=None):
        class MockErrorHandler:
            def info(self, msg): print(f"INFO: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
        return MockErrorHandler()
    
    def get_api_key(key_name):
        try:
            import streamlit as st
            return st.secrets.get('compass_token')
        except:
            return None

error_handler = get_error_handler(__name__)


class DataInterval(Enum):
    """Data intervals for sensor readings."""
    DAILY = "daily"
    HOURLY = "hourly"
    FIFTEEN_MIN = "15min"
    RAW = "raw"


@dataclass
class APIEndpoints:
    """API endpoint URLs."""
    base_url: str
    
    # Device endpoints
    device_info: str
    device_list: str
    device_production_status: str
    device_timestamp: str
    device_users: str
    device_entities: str
    
    # Sensor data endpoints
    daily_data: str
    latest_data: str
    raw_data: str
    sensor_data: str
    
    # Production and prediction endpoints
    weight_predictions: str
    production_history: str
    device_comparison: str
    
    # Export endpoints
    excel_current_production: str
    excel_data: str
    
    # Curve endpoints
    curve_data: str
    curve_info: str
    curve_list: str
    
    # Reference data endpoints
    reference_curves: str
    reference_curve_info: str
    poultry_sexes: str
    
    # Tag endpoints
    tag_list: str
    tag_info: str
    timezones: str
    
    @classmethod
    def create(cls, base_url: str) -> 'APIEndpoints':
        """Create endpoint configuration."""
        return cls(
            base_url=base_url,
            
            # Device endpoints
            device_info=f"{base_url}/devices/{{device_id}}",
            device_list=f"{base_url}/devices",
            device_production_status=f"{base_url}/devices/{{device_id}}/in-production",
            device_timestamp=f"{base_url}/devices/{{device_id}}/most-recent-sensor-timestamp/",
            device_users=f"{base_url}/devices/{{device_id}}/users",
            device_entities=f"{base_url}/devices/{{device_id}}/entities/parents",
            
            # Sensor data endpoints (using working format)
            daily_data=f"{base_url}/user/devices/{{device_id}}/sensors/data/daily/current-production",
            latest_data=f"{base_url}/user/devices/{{device_id}}/sensors/data/latest",
            raw_data=f"{base_url}/user/devices/{{device_id}}/sensors/data/current-production",
            sensor_data=f"{base_url}/user/devices/{{device_id}}/sensors/data",
            
            # Production endpoints
            weight_predictions=f"{base_url}/devices/{{device_id}}/prediction/poultry-weight/current-production",
            production_history=f"{base_url}/devices/{{device_id}}/productions",
            device_comparison=f"{base_url}/devices/{{device_id}}/compare/production",
            
            # Export endpoints
            excel_current_production=f"{base_url}/devices/{{device_id}}/sensors/data/current-production-as-excel",
            excel_data=f"{base_url}/devices/{{device_id}}/sensors/data-as-excel-file",
            
            # Curve endpoints
            curve_data=f"{base_url}/poultry-curves/{{curve_id}}/data",
            curve_info=f"{base_url}/poultry-curves/{{curve_id}}",
            curve_list=f"{base_url}/poultry-curves",
            
            # Reference data endpoints
            reference_curves=f"{base_url}/reference-curves",
            reference_curve_info=f"{base_url}/reference-curves/{{curve_id}}",
            poultry_sexes=f"{base_url}/poultry-sexes",
            
            # Tag endpoints
            tag_list=f"{base_url}/tags",
            tag_info=f"{base_url}/tags/{{tag_id}}",
            timezones=f"{base_url}/time-zones"
        )


class HTTPService:
    """Handles HTTP requests with error management."""
    
    def __init__(self, headers: Dict[str, str]):
        self.headers = headers
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.api_failed = False
    
    def get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute HTTP GET request."""
        if self.api_failed:
            return None
        
        try:
            response = self.session.get(url, params=params, timeout=APIConfig.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            else:
                if not self.api_failed:
                    error_handler.debug(f"API request failed: HTTP {response.status_code}")
                    self.api_failed = True
                return None
                
        except requests.exceptions.RequestException:
            if not self.api_failed:
                error_handler.debug("API connection unavailable")
                self.api_failed = True
            return None
        except Exception as e:
            if not self.api_failed:
                error_handler.debug(f"API request error: {e}")
                self.api_failed = True
            return None


class DataExtractor:
    """Extracts data from API responses."""
    
    @staticmethod
    def extract_sensor_data(response: Dict) -> List[Dict]:
        """Extract sensor data array from response."""
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
    
    @staticmethod
    def extract_latest_record(response: Dict) -> Optional[Dict]:
        """Extract latest sensor record."""
        sensor_data = DataExtractor.extract_sensor_data(response)
        return sensor_data[0] if sensor_data else None
    
    @staticmethod
    def extract_numeric_value(record: Dict, field: str = "latest_value") -> Optional[float]:
        """Extract numeric value from record."""
        if not record:
            return None
        
        value = record.get(field)
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_most_recent_record(records: List[Dict]) -> Optional[Dict]:
        """Get record with highest timestamp."""
        if not records:
            return None
        
        try:
            return max(records, key=lambda d: d.get("start_day_timestamp", 0))
        except Exception:
            return None


class DeviceService:
    """Handles device operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_info(self, device_id: str) -> Optional[Dict]:
        """Get device information."""
        url = self.endpoints.device_info.format(device_id=device_id)
        return self.http.get(url)
    
    def get_list(self, entity_id: Optional[int] = None) -> List[Dict]:
        """Get device list."""
        params = {"entity_id": entity_id} if entity_id else None
        response = self.http.get(self.endpoints.device_list, params)
        return response.get("devices", []) if response else []
    
    def get_production_status(self, device_id: str) -> Optional[Dict]:
        """Get device production status."""
        url = self.endpoints.device_production_status.format(device_id=device_id)
        return self.http.get(url)
    
    def get_most_recent_timestamp(self, device_id: str, report_id: Optional[int] = None) -> Optional[Dict]:
        """Get most recent sensor timestamp."""
        url = self.endpoints.device_timestamp.format(device_id=device_id)
        params = {"report_id": report_id} if report_id else None
        return self.http.get(url, params)


class SensorService:
    """Handles sensor data operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_daily_data(self, device_id: str, tag_names: List[str], day_count: int = 7) -> List[Dict]:
        """Get daily sensor data."""
        url = self.endpoints.daily_data.format(device_id=device_id)
        params = {"tag_names[]": tag_names, "day_count": day_count}
        
        response = self.http.get(url, params)
        return DataExtractor.extract_sensor_data(response) if response else []
    
    def get_latest_data(self, device_id: str, tag_names: List[str]) -> List[Dict]:
        """Get latest sensor data."""
        url = self.endpoints.latest_data.format(device_id=device_id)
        params = {"tag_names[]": tag_names}
        
        response = self.http.get(url, params)
        return DataExtractor.extract_sensor_data(response) if response else []
    
    def get_raw_data(self, device_id: str, tag_names: List[str], day_count: int = 1) -> List[Dict]:
        """Get raw sensor data."""
        url = self.endpoints.raw_data.format(device_id=device_id)
        params = {"tag_names[]": tag_names, "day_count": day_count}
        
        response = self.http.get(url, params)
        return DataExtractor.extract_sensor_data(response) if response else []


class ProductionService:
    """Handles production and prediction operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_weight_predictions(self, device_id: str, days_to_predict: int = 7, 
                              predictions_per_day: int = 1) -> Optional[Dict]:
        """Get poultry weight predictions."""
        url = self.endpoints.weight_predictions.format(device_id=device_id)
        params = {
            "days_to_predict": days_to_predict,
            "predictions_per_day": predictions_per_day
        }
        return self.http.get(url, params)
    
    def get_production_history(self, device_id: str, 
                              interval_start_timestamp: Optional[int] = None,
                              interval_end_timestamp: Optional[int] = None) -> List[Dict]:
        """Get device production history."""
        url = self.endpoints.production_history.format(device_id=device_id)
        params = {}
        if interval_start_timestamp:
            params["interval_start_timestamp"] = interval_start_timestamp
        if interval_end_timestamp:
            params["interval_end_timestamp"] = interval_end_timestamp
        
        response = self.http.get(url, params)
        return response.get("productions", []) if response else []


class CurveService:
    """Handles growth curve operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_curve_list(self) -> List[Dict]:
        """Get list of poultry curves."""
        response = self.http.get(self.endpoints.curve_list)
        if response and "data" in response:
            return response["data"].get("poultry-curves", [])
        return []
    
    def get_curve_info(self, curve_id: str) -> Optional[Dict]:
        """Get poultry curve information."""
        url = self.endpoints.curve_info.format(curve_id=curve_id)
        response = self.http.get(url)
        if response and "data" in response:
            return response["data"].get("curve")
        return None
    
    def get_curve_data(self, curve_id: str) -> Optional[Dict]:
        """Get poultry curve data."""
        url = self.endpoints.curve_data.format(curve_id=curve_id)
        return self.http.get(url)
    
    def get_expected_weight(self, curve_id: str, age: int) -> Optional[float]:
        """Get expected weight for specific age."""
        if not curve_id or not (1 <= age <= 70):
            return None
        
        curve_data = self.get_curve_data(curve_id)
        if not curve_data or "data" not in curve_data:
            return None
        
        try:
            data_points = curve_data["data"].get("poultry-curve", [])
            age_data = next((item for item in data_points if item.get("day") == age), None)
            
            if age_data and "male_weight" in age_data:
                return float(age_data["male_weight"])
        except (KeyError, TypeError, ValueError):
            pass
        
        return None


class ReferenceService:
    """Handles reference data operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_reference_curves(self, locale_id: Optional[int] = None) -> List[Dict]:
        """Get list of reference curves."""
        params = {"locale_id": locale_id} if locale_id else None
        response = self.http.get(self.endpoints.reference_curves, params)
        if response and "data" in response:
            return response["data"].get("reference_curves", [])
        return []
    
    def get_reference_curve_info(self, curve_id: str, locale_id: Optional[int] = None) -> Optional[Dict]:
        """Get reference curve information."""
        url = self.endpoints.reference_curve_info.format(curve_id=curve_id)
        params = {"locale_id": locale_id} if locale_id else None
        response = self.http.get(url, params)
        if response and "data" in response:
            return response["data"].get("reference_curve")
        return None
    
    def get_poultry_sexes(self) -> List[Dict]:
        """Get list of poultry sexes."""
        response = self.http.get(self.endpoints.poultry_sexes)
        if response and "data" in response:
            return response["data"].get("poultry_sexes", [])
        return []


class TagService:
    """Handles tag metadata operations."""
    
    def __init__(self, http_service: HTTPService, endpoints: APIEndpoints):
        self.http = http_service
        self.endpoints = endpoints
    
    def get_tag_list(self, locale_id: Optional[int] = None, 
                    names: Optional[List[str]] = None,
                    search: Optional[str] = None) -> List[Dict]:
        """Get list of available tags."""
        params = {}
        if locale_id:
            params["locale_id"] = locale_id
        if names:
            params["names"] = names
        if search:
            params["search"] = search
        
        response = self.http.get(self.endpoints.tag_list, params)
        if response and "data" in response:
            return response["data"].get("tags", [])
        return []
    
    def get_tag_info(self, tag_id: int, locale_id: Optional[int] = None) -> Optional[Dict]:
        """Get tag information."""
        url = self.endpoints.tag_info.format(tag_id=tag_id)
        params = {"locale_id": locale_id} if locale_id else None
        
        response = self.http.get(url, params)
        if response and "data" in response:
            return response["data"].get("tag")
        return None


class CompassAPI:
    """Main API client for Compass platform."""
    
    def __init__(self, base_url: str = None):
        """Initialize API client."""
        self.api_token = get_api_key('compass')
        if not self.api_token:
            try:
                import streamlit as st
                self.api_token = st.secrets.get('compass_token')
            except:
                pass
        
        if not self.api_token:
            error_handler.info("No Compass API token found")
            self.api_token = "mock_token"
        
        self.base_url = base_url or APIConfig.DEFAULT_COMPASS_BASE_URL
        self.endpoints = APIEndpoints.create(self.base_url)
        self.http_service = HTTPService({"api_authorization": self.api_token})
        
        # Initialize services
        self.device_service = DeviceService(self.http_service, self.endpoints)
        self.sensor_service = SensorService(self.http_service, self.endpoints)
        self.production_service = ProductionService(self.http_service, self.endpoints)
        self.curve_service = CurveService(self.http_service, self.endpoints)
        self.reference_service = ReferenceService(self.http_service, self.endpoints)
        self.tag_service = TagService(self.http_service, self.endpoints)
        
        error_handler.info(f"CompassAPI initialized with base URL: {self.base_url}")
    
    # Device methods
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get device information."""
        return self.device_service.get_info(device_id)
    
    def get_device_list(self, entity_id: Optional[int] = None) -> List[Dict]:
        """Get list of devices."""
        return self.device_service.get_list(entity_id)
    
    def get_production_status(self, device_id: str) -> Optional[Dict]:
        """Get device production status."""
        return self.device_service.get_production_status(device_id)
    
    # Sensor data methods
    def get_daily_data(self, device_id: str, tag_name: str, day_count: int = 7) -> List[Dict]:
        """Get daily sensor data."""
        return self.sensor_service.get_daily_data(device_id, [tag_name], day_count)
    
    def get_latest_data(self, device_id: str, tag_name: str) -> Optional[Dict]:
        """Get latest sensor data."""
        data = self.sensor_service.get_latest_data(device_id, [tag_name])
        return data[0] if data else None
    
    def get_raw_data(self, device_id: str, tag_name: str, day_count: int = 1) -> List[Dict]:
        """Get raw sensor data."""
        return self.sensor_service.get_raw_data(device_id, [tag_name], day_count)
    
    # Production and prediction methods
    def get_weight_predictions(self, device_id: str, days_to_predict: int = 7,
                              predictions_per_day: int = 1) -> Optional[Dict]:
        """Get poultry weight predictions."""
        return self.production_service.get_weight_predictions(device_id, days_to_predict, predictions_per_day)
    
    def get_production_history(self, device_id: str) -> List[Dict]:
        """Get device production history."""
        return self.production_service.get_production_history(device_id)
    
    # Curve methods
    def get_curve_list(self) -> List[Dict]:
        """Get list of poultry curves."""
        return self.curve_service.get_curve_list()
    
    def get_curve_info(self, curve_id: str) -> Optional[Dict]:
        """Get curve information."""
        return self.curve_service.get_curve_info(curve_id)
    
    def get_curve_data(self, curve_id: str) -> Optional[Dict]:
        """Get curve data."""
        return self.curve_service.get_curve_data(curve_id)
    
    def get_expected_weight(self, curve_id: str, age: int) -> Optional[float]:
        """Get expected weight for specific age."""
        return self.curve_service.get_expected_weight(curve_id, age)
    
    # Reference data methods
    def get_reference_curves(self, locale_id: Optional[int] = None) -> List[Dict]:
        """Get list of reference curves."""
        return self.reference_service.get_reference_curves(locale_id)
    
    def get_reference_curve_info(self, curve_id: str, locale_id: Optional[int] = None) -> Optional[Dict]:
        """Get reference curve information."""
        return self.reference_service.get_reference_curve_info(curve_id, locale_id)
    
    def get_poultry_sexes(self) -> List[Dict]:
        """Get list of poultry sexes."""
        return self.reference_service.get_poultry_sexes()
    
    # Tag methods
    def get_tag_list(self, search: Optional[str] = None) -> List[Dict]:
        """Get list of available tags."""
        return self.tag_service.get_tag_list(search=search)
    
    def get_tag_info(self, tag_id: int) -> Optional[Dict]:
        """Get tag information."""
        return self.tag_service.get_tag_info(tag_id)
    
    # Helper methods for backward compatibility
    def get_current_weight(self, device_id: str) -> Optional[float]:
        """Get current weight in grams."""
        latest_data = self.get_latest_data(device_id, "AveragePoultryWeight")
        if latest_data:
            weight_kg = DataExtractor.extract_numeric_value(latest_data)
            return weight_kg * 1000 if weight_kg else None
        return None
    
    def get_yesterday_weight(self, device_id: str) -> Optional[float]:
        """Get yesterday weight in grams."""
        daily_data = self.get_daily_data(device_id, "AveragePoultryWeight", 2)
        if len(daily_data) >= 2:
            weight_kg = DataExtractor.extract_numeric_value(daily_data[-2], "latest_value")
            return weight_kg * 1000 if weight_kg else None
        return None
    
    def get_age(self, device_id: str) -> Optional[int]:
        """Get flock age in days."""
        latest_data = self.get_latest_data(device_id, "ProductionDay")
        if latest_data:
            age_value = DataExtractor.extract_numeric_value(latest_data)
            return int(age_value) if age_value else None
        return None
    
    def get_curve_id(self, device_id: str) -> Optional[str]:
        """Get growth curve ID."""
        latest_data = self.get_latest_data(device_id, "PoultryCurve")
        if latest_data:
            curve_value = DataExtractor.extract_numeric_value(latest_data)
            return str(int(curve_value)) if curve_value else None
        return None
    
    def get_curve_name(self, curve_id: str) -> Optional[str]:
        """Get growth curve name."""
        curve_info = self.get_curve_info(curve_id)
        return curve_info.get("name") if curve_info else None
    
    def test_connection(self) -> bool:
        """Test API connectivity."""
        try:
            device_list = self.get_device_list()
            return device_list is not None
        except Exception:
            return False


# Legacy compatibility functions
def get_daily_data(device_id: str, tag_name: str, token: str) -> List[Dict]:
    """Legacy function for backward compatibility."""
    api = CompassAPI()
    api.api_token = token
    return api.get_daily_data(device_id, tag_name)


def get_latest_data(device_id: str, tag_name: str, token: str) -> Optional[Dict]:
    """Legacy function for backward compatibility.""" 
    api = CompassAPI()
    api.api_token = token
    return api.get_latest_data(device_id, tag_name)


def compute_deltas(today: float, yesterday: float, ref_today: float, ref_yesterday: float) -> Tuple[float, float, Optional[float]]:
    """Calculate weight gain deltas."""
    gain_observed = today - yesterday
    gain_expected = ref_today - ref_yesterday
    ratio = gain_observed / gain_expected if gain_expected else None
    return gain_observed, gain_expected, ratio