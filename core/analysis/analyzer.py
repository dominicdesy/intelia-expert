"""
Broiler performance analysis with conditional recommendation logic.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import logging
from enum import Enum
import pandas as pd
from datetime import datetime, timedelta

try:
    from .constants import (
        DeviationLevel, ProductionPhase, 
        WEIGHT_STANDARDS,
        validate_age, validate_weight, get_expected_weight,
        DEFAULT_WEIGHT_CONVERSION
    )
except ImportError:
    class DeviationLevel(Enum):
        EXCELLENT = "excellent"
        NORMAL = "normal"
        ATTENTION = "attention"
        WARNING = "warning"
        CRITICAL = "critical"
    
    class ProductionPhase(Enum):
        STARTER = "starter"
        GROWER = "grower"
        FINISHER = "finisher"

logger = logging.getLogger(__name__)

@dataclass
class StatusInfo:
    """Status information with color and translation key."""
    level: str
    color_hex: str
    status_key: str
    description_key: str
    numeric_score: float
    
    @property
    def is_good(self) -> bool:
        return self.level in ["excellent", "normal", "optimal", "acceptable"]
    
    @property
    def needs_attention(self) -> bool:
        return self.level in ["attention", "warning", "critical"]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "color_hex": self.color_hex,
            "status_key": self.status_key,
            "description_key": self.description_key,
            "numeric_score": self.numeric_score,
            "is_good": self.is_good,
            "needs_attention": self.needs_attention
        }


@dataclass
class VariationAlert:
    """Alert for rapid environmental variations."""
    sensor_type: str
    variation_magnitude: float
    time_window_minutes: int
    alert_level: str
    description: str
    timestamp: datetime
    current_value: float
    previous_value: float
    
    @property
    def is_critical(self) -> bool:
        return self.alert_level in ["critical", "warning"]


@dataclass
class EnvironmentalVariationAnalysis:
    """Analysis of environmental variations over time intervals."""
    temperature_alerts: List[VariationAlert]
    humidity_alerts: List[VariationAlert]
    co2_alerts: List[VariationAlert]
    analysis_window_hours: int
    data_points_analyzed: int
    max_temperature_variation: float
    max_humidity_variation: float
    critical_alerts_count: int
    
    @property
    def has_critical_alerts(self) -> bool:
        return self.critical_alerts_count > 0
    
    @property
    def overall_stability_score(self) -> float:
        """Calculate environmental stability score (0-100)."""
        if self.data_points_analyzed < 4:
            return 50.0
        
        base_score = 100.0
        
        # Apply temperature variation penalties
        if self.max_temperature_variation > 5.0:
            base_score -= 30
        elif self.max_temperature_variation > 3.0:
            base_score -= 20
        elif self.max_temperature_variation > 2.0:
            base_score -= 10
        
        # Apply humidity variation penalties
        if self.max_humidity_variation > 20.0:
            base_score -= 20
        elif self.max_humidity_variation > 15.0:
            base_score -= 10
        
        # Apply critical alert penalties
        base_score -= (self.critical_alerts_count * 15)
        
        return max(0.0, min(100.0, base_score))


@dataclass
class EnvironmentalMetrics:
    """Environmental metrics with variation analysis."""
    temperature_avg: float
    humidity_avg: float
    data_points_count: int
    
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity_min: Optional[float] = None
    humidity_max: Optional[float] = None
    external_temp_min_24h: Optional[float] = None
    external_temp_max_24h: Optional[float] = None
    external_temp_avg_24h: Optional[float] = None
    has_temperature_data: bool = True
    has_humidity_data: bool = True
    has_external_data: bool = False
    variation_analysis: Optional[EnvironmentalVariationAnalysis] = None
    
    @property
    def data_quality_score(self) -> float:
        return min(self.data_points_count / 144, 1.0) * 100
    
    @property
    def temperature_range(self) -> str:
        if self.temperature_min is not None and self.temperature_max is not None:
            return f"{self.temperature_min:.1f}°C - {self.temperature_max:.1f}°C"
        return f"{self.temperature_avg:.1f}°C (avg)"
    
    @property
    def humidity_range(self) -> str:
        if self.humidity_min is not None and self.humidity_max is not None:
            return f"{self.humidity_min:.0f}% - {self.humidity_max:.0f}%"
        return f"{self.humidity_avg:.0f}% (avg)"


@dataclass
class AnalysisResult:
    """Complete analysis result for a barn."""
    barn_id: str
    age: int
    breed: str
    
    observed_weight: int
    expected_weight: int
    
    observed_gain: int
    expected_gain: int
    gain_ratio: float
    
    deviation_level: str
    production_phase: Optional[str] = None
    temperature_status: str = "No data"
    environmental_metrics: Optional[EnvironmentalMetrics] = None
    weight_data: Optional[Dict] = None
    
    weight_status_info: Optional[StatusInfo] = None
    gain_status_info: Optional[StatusInfo] = None
    temperature_status_info: Optional[StatusInfo] = None
    humidity_status_info: Optional[StatusInfo] = None
    
    @property
    def weight_deviation(self) -> int:
        return self.observed_weight - self.expected_weight
    
    @property
    def weight_deviation_percentage(self) -> float:
        if self.expected_weight > 0:
            return (self.weight_deviation / self.expected_weight) * 100
        return 0.0
    
    @property
    def is_underweight(self) -> bool:
        return self.weight_deviation < 0
    
    @property
    def is_overweight(self) -> bool:
        return self.weight_deviation > 0
    
    @property
    def performance_level(self) -> str:
        if self.gain_ratio >= 0.95:
            return "excellent"
        elif self.gain_ratio >= 0.85:
            return "good"
        elif self.gain_ratio >= 0.75:
            return "attention"
        else:
            return "critical"
    
    @property
    def performance_status(self) -> str:
        if self.gain_status_info:
            return self.gain_status_info.level.title()
        if self.gain_ratio >= 1.10:
            return "Excellent"
        elif self.gain_ratio >= 0.95:
            return "Normal"
        elif self.gain_ratio >= 0.85:
            return "Needs Attention"
        elif self.gain_ratio >= 0.75:
            return "Warning"
        else:
            return "Critical"
    
    @property
    def has_environmental_alerts(self) -> bool:
        """Check if there are critical environmental alerts."""
        if (self.environmental_metrics and 
            self.environmental_metrics.variation_analysis):
            return self.environmental_metrics.variation_analysis.has_critical_alerts
        return False
    
    def needs_recommendations(self, outdoor_temp: Optional[float] = None) -> bool:
        """Determine if recommendations are needed based on all status indicators."""
        # Check weight status
        if self.weight_status_info and self.weight_status_info.needs_attention:
            return True
        
        # Check gain performance status
        if self.gain_status_info and self.gain_status_info.needs_attention:
            return True
        
        # Check temperature status with outdoor context
        if self.temperature_status_info and self.temperature_status_info.needs_attention:
            # Consider outdoor temperature for context
            if outdoor_temp is not None and hasattr(self.environmental_metrics, 'temperature_avg'):
                temp_differential = abs(self.environmental_metrics.temperature_avg - outdoor_temp)
                # If temperature difference is reasonable, don't flag as issue
                if temp_differential < 15 and self.temperature_status_info.level in ["attention"]:
                    pass  # Temperature is acceptable given outdoor conditions
                else:
                    return True
            else:
                return True
        
        # Check humidity status
        if self.humidity_status_info and self.humidity_status_info.needs_attention:
            return True
        
        # Check environmental alerts
        if self.has_environmental_alerts:
            return True
        
        return False


class CentralizedStatusSystem:
    """System for determining status, colors, and temperatures."""
    
    def __init__(self):
        self.colors = {
            "excellent": "#2E8B57",
            "normal": "#32CD32",
            "attention": "#FFD700",
            "warning": "#FF8C00",
            "critical": "#DC143C",
            "poor": "#8B0000",
            "optimal": "#228B22",
            "acceptable": "#90EE90",
            "unknown": "#808080"
        }
        
        self.performance_thresholds = {
            "excellent": 1.05,  # Fixed threshold consistency
            "normal": 0.95,
            "attention": 0.85,
            "warning": 0.75,
            "critical": 0.0
        }
        
        self.weight_thresholds = {
            "excellent": 1.05,
            "normal": 0.98,
            "attention": 0.90,
            "warning": 0.80,
            "critical": 0.0
        }
        
        self.temperature_thresholds = {
            "optimal_ranges": {
                (1, 7): (32, 35),
                (8, 14): (28, 32),
                (15, 21): (25, 29),
                (22, 28): (22, 26),
                (29, 42): (20, 24),
                (43, 70): (18, 22)
            }
        }
        
        self.optimal_temperature_midpoints = {
            1: 33.5, 7: 31.5, 14: 29.5, 21: 27.5,
            28: 25.5, 35: 23.5, 42: 21.5, 70: 20.0
        }
        
        self.humidity_thresholds = {
            "optimal": (50, 70),
            "acceptable": (40, 80),
            "critical_low": 30,
            "critical_high": 85
        }
    
    def get_performance_status(self, ratio: float) -> StatusInfo:
        thresholds = self.performance_thresholds
        
        if ratio >= thresholds["excellent"]:
            level = "excellent"
            score = min(100, 85 + (ratio - thresholds["excellent"]) * 50)
        elif ratio >= thresholds["normal"]:
            level = "normal"
            score = 70 + (ratio - thresholds["normal"]) * 100
        elif ratio >= thresholds["attention"]:
            level = "attention"
            score = 50 + (ratio - thresholds["attention"]) * 200
        elif ratio >= thresholds["warning"]:
            level = "warning"
            score = 25 + (ratio - thresholds["warning"]) * 250
        else:
            level = "critical"
            score = max(0, ratio * 33.33)
        
        return StatusInfo(
            level=level,
            color_hex=self.colors[level],
            status_key=f"status.{level}",
            description_key=f"performance.{level}_description",
            numeric_score=score
        )
    
    def get_weight_status(self, observed: float, expected: float) -> StatusInfo:
        if expected <= 0:
            return StatusInfo("unknown", self.colors["unknown"], "status.unknown", 
                           "performance.unknown_description", 0)
        
        ratio = observed / expected
        thresholds = self.weight_thresholds
        
        if ratio >= thresholds["excellent"]:
            level = "excellent"
            score = min(100, 85 + (ratio - thresholds["excellent"]) * 50)
        elif ratio >= thresholds["normal"]:
            level = "normal"
            score = 70 + (ratio - thresholds["normal"]) * 100
        elif ratio >= thresholds["attention"]:
            level = "attention" 
            score = 50 + (ratio - thresholds["attention"]) * 125
        elif ratio >= thresholds["warning"]:
            level = "warning"
            score = 25 + (ratio - thresholds["warning"]) * 125
        else:
            level = "critical"
            score = max(0, ratio * 31.25)
        
        return StatusInfo(
            level=level,
            color_hex=self.colors[level],
            status_key=f"status.{level}",
            description_key=f"weight.{level}_description",
            numeric_score=score
        )
    
    def get_temperature_status(self, temp: float, age: int, outdoor_temp: Optional[float] = None) -> StatusInfo:
        """Evaluate temperature status with optional outdoor temperature context."""
        optimal_range = self._get_optimal_temp_range(age)
        
        # Calculate base status without outdoor context
        if optimal_range[0] <= temp <= optimal_range[1]:
            base_level = "optimal"
            base_score = 100
        elif optimal_range[0] - 2 <= temp <= optimal_range[1] + 2:
            base_level = "acceptable"
            base_score = 75
        elif optimal_range[0] - 5 <= temp <= optimal_range[1] + 5:
            base_level = "attention"
            base_score = 50
        elif optimal_range[0] - 8 <= temp <= optimal_range[1] + 8:
            base_level = "warning"
            base_score = 25
        else:
            base_level = "critical"
            base_score = 0
        
        # Adjust status based on outdoor temperature context
        if outdoor_temp is not None:
            temp_differential = temp - outdoor_temp
            
            # Hot weather conditions (outdoor > 30°C)
            if outdoor_temp > 30:
                if temp_differential <= 5:  # Excellent cooling
                    if base_level in ["attention", "acceptable"]:
                        base_level = "optimal"
                        base_score = 95
                elif temp_differential <= 8:  # Good cooling
                    if base_level == "attention":
                        base_level = "acceptable"
                        base_score = 80
            
            # Cold weather conditions (outdoor < 10°C)
            elif outdoor_temp < 10:
                if temp_differential >= 15:  # Good heating
                    if base_level in ["attention", "acceptable"]:
                        base_level = "optimal"
                        base_score = 95
                elif temp_differential >= 10:  # Adequate heating
                    if base_level == "attention":
                        base_level = "acceptable"
                        base_score = 80
        
        return StatusInfo(
            level=base_level,
            color_hex=self.colors[base_level],
            status_key=f"status.{base_level}",
            description_key=f"temperature.{base_level}_description",
            numeric_score=base_score
        )
    
    def get_humidity_status(self, humidity: float) -> StatusInfo:
        optimal_min, optimal_max = self.humidity_thresholds["optimal"]
        acceptable_min, acceptable_max = self.humidity_thresholds["acceptable"]
        critical_low = self.humidity_thresholds["critical_low"]
        critical_high = self.humidity_thresholds["critical_high"]
        
        if optimal_min <= humidity <= optimal_max:
            level = "optimal"
            score = 100
        elif acceptable_min <= humidity <= acceptable_max:
            level = "acceptable"
            score = 75
        elif humidity < critical_low or humidity > critical_high:
            level = "critical"
            score = 0
        else:
            level = "attention"
            score = 50
        
        return StatusInfo(
            level=level,
            color_hex=self.colors[level],
            status_key=f"status.{level}",
            description_key=f"humidity.{level}_description",
            numeric_score=score
        )
    
    def _get_optimal_temp_range(self, age: int) -> Tuple[float, float]:
        for (min_age, max_age), temp_range in self.temperature_thresholds["optimal_ranges"].items():
            if min_age <= age <= max_age:
                return temp_range
        return (18, 22)
    
    def get_optimal_temperature_midpoint(self, age: int) -> float:
        if age in self.optimal_temperature_midpoints:
            return self.optimal_temperature_midpoints[age]
        
        ages = sorted(self.optimal_temperature_midpoints.keys())
        
        lower_age = max([a for a in ages if a <= age], default=ages[0])
        upper_age = min([a for a in ages if a >= age], default=ages[-1])
        
        if lower_age == upper_age:
            return self.optimal_temperature_midpoints[lower_age]
        
        lower_temp = self.optimal_temperature_midpoints[lower_age]
        upper_temp = self.optimal_temperature_midpoints[upper_age]
        
        temp_per_day = (upper_temp - lower_temp) / (upper_age - lower_age)
        return lower_temp + (age - lower_age) * temp_per_day
    
    def get_production_phase(self, age: int) -> str:
        if age <= 14:
            return ProductionPhase.STARTER.value
        elif age <= 28:
            return ProductionPhase.GROWER.value
        else:
            return ProductionPhase.FINISHER.value


class EnvironmentalVariationDetector:
    """Detects critical environmental variations in time intervals."""
    
    VARIATION_THRESHOLDS = {
        'temperature': {
            'critical': 5.0,
            'warning': 3.0,
            'attention': 2.0
        },
        'humidity': {
            'critical': 20.0,
            'warning': 15.0,
            'attention': 10.0
        },
        'co2': {
            'critical': 500.0,
            'warning': 300.0,
            'attention': 200.0
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_variations(self, raw_data: Dict[str, List[Dict]], 
                          analysis_hours: int = 24) -> EnvironmentalVariationAnalysis:
        """Analyze environmental variations from raw sensor data."""
        
        temperature_alerts = self._detect_sensor_variations(
            raw_data.get('temperature', []), 'temperature'
        )
        
        humidity_alerts = self._detect_sensor_variations(
            raw_data.get('humidity', []), 'humidity'
        )
        
        co2_alerts = self._detect_sensor_variations(
            raw_data.get('co2', []), 'co2'
        )
        
        all_alerts = temperature_alerts + humidity_alerts + co2_alerts
        critical_count = len([a for a in all_alerts if a.is_critical])
        
        max_temp_variation = self._calculate_max_variation(
            raw_data.get('temperature', [])
        )
        max_humidity_variation = self._calculate_max_variation(
            raw_data.get('humidity', [])
        )
        
        total_data_points = sum(len(data) for data in raw_data.values())
        
        return EnvironmentalVariationAnalysis(
            temperature_alerts=temperature_alerts,
            humidity_alerts=humidity_alerts,
            co2_alerts=co2_alerts,
            analysis_window_hours=analysis_hours,
            data_points_analyzed=total_data_points,
            max_temperature_variation=max_temp_variation,
            max_humidity_variation=max_humidity_variation,
            critical_alerts_count=critical_count
        )
    
    def _detect_sensor_variations(self, sensor_data: List[Dict], 
                                sensor_type: str) -> List[VariationAlert]:
        """Detect variations for a specific sensor type."""
        alerts = []
        
        if len(sensor_data) < 2:
            return alerts
        
        try:
            df = self._prepare_sensor_dataframe(sensor_data)
            
            if df.empty:
                return alerts
            
            df = df.sort_values('timestamp')
            df['value_15min_ago'] = df['value'].shift(1)
            df['variation'] = abs(df['value'] - df['value_15min_ago'])
            
            thresholds = self.VARIATION_THRESHOLDS.get(sensor_type, {})
            
            for _, row in df.iterrows():
                if pd.isna(row['variation']):
                    continue
                
                variation = row['variation']
                alert_level = self._determine_alert_level(variation, thresholds)
                
                if alert_level:
                    alert = VariationAlert(
                        sensor_type=sensor_type,
                        variation_magnitude=variation,
                        time_window_minutes=15,
                        alert_level=alert_level,
                        description=f"{sensor_type.title()} changed by {variation:.1f} in 15 minutes",
                        timestamp=row['timestamp'],
                        current_value=row['value'],
                        previous_value=row['value_15min_ago']
                    )
                    alerts.append(alert)
        
        except Exception as e:
            self.logger.warning(f"Variation detection failed for {sensor_type}: {e}")
        
        return alerts
    
    def _prepare_sensor_dataframe(self, sensor_data: List[Dict]) -> pd.DataFrame:
        """Convert sensor data to DataFrame with proper timestamps."""
        if not sensor_data:
            return pd.DataFrame()
        
        try:
            df = pd.DataFrame(sensor_data)
            
            df['value'] = pd.to_numeric(df.get('value', df.get('latest_value', 0)), errors='coerce')
            
            timestamp_col = 'timestamp'
            if 'timestamp' not in df.columns:
                timestamp_col = next((col for col in df.columns if 'timestamp' in col.lower()), None)
            
            if timestamp_col:
                df['timestamp_numeric'] = pd.to_numeric(df[timestamp_col], errors='coerce')
                
                # Handle milliseconds vs seconds
                sample_timestamp = df['timestamp_numeric'].dropna().iloc[0] if not df['timestamp_numeric'].dropna().empty else 0
                if sample_timestamp > 1e12:
                    df['timestamp'] = pd.to_datetime(df['timestamp_numeric'], unit='ms', errors='coerce')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp_numeric'], unit='s', errors='coerce')
            else:
                df['timestamp'] = pd.to_datetime('now')
            
            return df[['timestamp', 'value']].dropna()
        
        except Exception as e:
            self.logger.warning(f"DataFrame preparation failed: {e}")
            return pd.DataFrame()
    
    def _determine_alert_level(self, variation: float, thresholds: Dict[str, float]) -> Optional[str]:
        """Determine alert level based on variation magnitude."""
        if variation >= thresholds.get('critical', float('inf')):
            return 'critical'
        elif variation >= thresholds.get('warning', float('inf')):
            return 'warning'
        elif variation >= thresholds.get('attention', float('inf')):
            return 'attention'
        return None
    
    def _calculate_max_variation(self, sensor_data: List[Dict]) -> float:
        """Calculate maximum variation for a sensor."""
        try:
            df = self._prepare_sensor_dataframe(sensor_data)
            if df.empty or len(df) < 2:
                return 0.0
            
            df = df.sort_values('timestamp')
            df['prev_value'] = df['value'].shift(1)
            df['variation'] = abs(df['value'] - df['prev_value'])
            
            return df['variation'].max() or 0.0
        
        except Exception:
            return 0.0


class MetricsCalculator:
    """Calculates performance metrics."""
    
    @staticmethod
    def calculate_performance_metrics(today: int, yesterday: int, 
                                   expected_today: int, expected_yesterday: int,
                                   age: int) -> 'PerformanceMetrics':
        observed_gain = today - yesterday
        expected_gain = expected_today - expected_yesterday
        gain_ratio = observed_gain / expected_gain if expected_gain > 0 else 0
        gain_deviation = observed_gain - expected_gain
        
        status_info = get_status_system().get_performance_status(gain_ratio)
        
        return PerformanceMetrics(
            observed_gain=observed_gain,
            expected_gain=expected_gain,
            gain_ratio=gain_ratio,
            gain_deviation=gain_deviation,
            status_info=status_info
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics calculations."""
    observed_gain: float
    expected_gain: float
    gain_ratio: float
    gain_deviation: float
    status_info: StatusInfo


class BroilerAnalyzer:
    """Main broiler performance analyzer with conditional recommendation logic."""
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.status_system = get_status_system()
        self.variation_detector = EnvironmentalVariationDetector()
        logger.info("BroilerAnalyzer initialized")
    
    def analyze_barn(self, barn_id: str, outdoor_temp: Optional[float] = None) -> Optional[AnalysisResult]:
        """Perform comprehensive analysis with conditional recommendation logic."""
        try:
            logger.info(f"Starting analysis for barn {barn_id}")
            
            age = self._get_age(barn_id)
            breed = self._get_breed(barn_id)
            current_weight = self._get_current_weight(barn_id)
            yesterday_weight = self._get_yesterday_weight(barn_id)
            
            if not all([age, current_weight, yesterday_weight]):
                logger.info(f"Using mock data for barn {barn_id}")
                return self._create_mock_result(barn_id, outdoor_temp)
            
            expected_weight = self._get_expected_weight(breed, age)
            expected_yesterday_weight = self._get_expected_weight(breed, age - 1)
            
            metrics = MetricsCalculator.calculate_performance_metrics(
                current_weight, yesterday_weight,
                expected_weight, expected_yesterday_weight,
                age
            )
            
            weight_status_info = self.status_system.get_weight_status(current_weight, expected_weight)
            
            environmental_metrics = self._get_environmental_metrics_with_variations(barn_id, age)
            temperature_status_info = None
            humidity_status_info = None
            
            if environmental_metrics:
                temperature_status_info = self.status_system.get_temperature_status(
                    environmental_metrics.temperature_avg, age, outdoor_temp
                )
                humidity_status_info = self.status_system.get_humidity_status(
                    environmental_metrics.humidity_avg
                )
            
            production_phase = self.status_system.get_production_phase(age)
            
            result = AnalysisResult(
                barn_id=barn_id,
                age=age,
                breed=breed,
                observed_weight=int(current_weight),
                expected_weight=int(expected_weight),
                observed_gain=int(metrics.observed_gain),
                expected_gain=int(metrics.expected_gain),
                gain_ratio=metrics.gain_ratio,
                deviation_level=metrics.status_info.level,
                production_phase=production_phase,
                environmental_metrics=environmental_metrics,
                temperature_status=temperature_status_info.level if temperature_status_info else "No data",
                weight_status_info=weight_status_info,
                gain_status_info=metrics.status_info,
                temperature_status_info=temperature_status_info,
                humidity_status_info=humidity_status_info
            )
            
            if result.has_environmental_alerts:
                logger.warning(f"Environmental alerts detected for barn {barn_id}")
            
            logger.info(f"Analysis completed for barn {barn_id}")
            return result
            
        except Exception as e:
            logger.warning(f"Analysis failed for barn {barn_id}: {e}")
            return self._create_mock_result(barn_id, outdoor_temp)
    
    def _get_environmental_metrics_with_variations(self, barn_id: str, age: int) -> Optional[EnvironmentalMetrics]:
        """Get environmental metrics with variation analysis."""
        try:
            if not self.api_client:
                return self._create_mock_environmental_metrics()
            
            raw_sensor_data = self._fetch_raw_environmental_data(barn_id)
            
            if not raw_sensor_data:
                return self._create_mock_environmental_metrics()
            
            variation_analysis = self.variation_detector.analyze_variations(raw_sensor_data)
            
            temp_values = [d.get('value', 0) for d in raw_sensor_data.get('temperature', [])]
            humidity_values = [d.get('value', 0) for d in raw_sensor_data.get('humidity', [])]
            
            temp_avg = sum(temp_values) / len(temp_values) if temp_values else 25.0
            humidity_avg = sum(humidity_values) / len(humidity_values) if humidity_values else 60.0
            
            total_points = sum(len(data) for data in raw_sensor_data.values())
            
            return EnvironmentalMetrics(
                temperature_avg=temp_avg,
                humidity_avg=humidity_avg,
                data_points_count=total_points,
                temperature_min=min(temp_values) if temp_values else None,
                temperature_max=max(temp_values) if temp_values else None,
                humidity_min=min(humidity_values) if humidity_values else None,
                humidity_max=max(humidity_values) if humidity_values else None,
                variation_analysis=variation_analysis
            )
            
        except Exception as e:
            logger.warning(f"Environmental metrics failed: {e}")
            return self._create_mock_environmental_metrics()
    
    def _fetch_raw_environmental_data(self, barn_id: str) -> Dict[str, List[Dict]]:
        """Fetch raw environmental sensor data."""
        raw_data = {}
        
        sensors = ['Temperature', 'Humidity', 'CarbonDioxide', 'CO2']
        
        for sensor in sensors:
            try:
                sensor_data = self.api_client.get_raw_data(barn_id, sensor, day_count=1)
                if sensor_data:
                    sensor_key = 'temperature' if 'temp' in sensor.lower() else \
                                 'humidity' if 'humid' in sensor.lower() else \
                                 'co2' if 'co2' in sensor.lower() or 'carbon' in sensor.lower() else sensor.lower()
                    raw_data[sensor_key] = sensor_data
                    logger.debug(f"Fetched {len(sensor_data)} data points for {sensor}")
            except Exception as e:
                logger.debug(f"Failed to fetch {sensor} data: {e}")
        
        return raw_data
    
    def _create_mock_environmental_metrics(self) -> EnvironmentalMetrics:
        """Create mock environmental metrics."""
        mock_alerts = []
        mock_variation_analysis = EnvironmentalVariationAnalysis(
            temperature_alerts=mock_alerts,
            humidity_alerts=mock_alerts,
            co2_alerts=mock_alerts,
            analysis_window_hours=24,
            data_points_analyzed=144,
            max_temperature_variation=1.5,
            max_humidity_variation=8.0,
            critical_alerts_count=0
        )
        
        return EnvironmentalMetrics(
            temperature_avg=25.0,
            humidity_avg=60.0,
            data_points_count=144,
            temperature_min=23.5,
            temperature_max=26.5,
            humidity_min=55.0,
            humidity_max=65.0,
            variation_analysis=mock_variation_analysis
        )
    
    def get_performance_summary(self, result: AnalysisResult) -> Dict[str, Any]:
        """Get performance summary with environmental alerts."""
        if not result:
            return {"status": "no_data", "message": "No analysis data available"}
        
        summary = {
            "status": "success",
            "barn_id": result.barn_id,
            "age": result.age,
            "breed": result.breed,
            "performance_status": result.performance_status,
            "weight_status": "Underweight" if result.is_underweight else "Overweight" if result.is_overweight else "Normal",
            "weight_deviation_pct": result.weight_deviation_percentage,
            "gain_ratio": result.gain_ratio,
            "deviation_level": result.deviation_level,
            "production_phase": result.production_phase,
            "data_quality": result.environmental_metrics.data_quality_score if result.environmental_metrics else 0,
            "weight_status_info": result.weight_status_info,
            "gain_status_info": result.gain_status_info,
            "temperature_status_info": result.temperature_status_info,
            "humidity_status_info": result.humidity_status_info,
            "has_environmental_alerts": result.has_environmental_alerts
        }
        
        if result.environmental_metrics and result.environmental_metrics.variation_analysis:
            variation_analysis = result.environmental_metrics.variation_analysis
            summary.update({
                "environmental_stability_score": variation_analysis.overall_stability_score,
                "critical_alerts_count": variation_analysis.critical_alerts_count,
                "max_temperature_variation": variation_analysis.max_temperature_variation,
                "max_humidity_variation": variation_analysis.max_humidity_variation
            })
        
        return summary
    
    def _get_age(self, barn_id: str) -> Optional[int]:
        if self.api_client and hasattr(self.api_client, 'get_age'):
            try:
                age = self.api_client.get_age(barn_id)
                if age:
                    return age
            except Exception as e:
                logger.debug(f"API age unavailable for barn {barn_id}: {e}")
        return 35
    
    def _get_breed(self, barn_id: str) -> str:
        if self.api_client and hasattr(self.api_client, 'get_curve_name'):
            try:
                curve_id = self.api_client.get_curve_id(barn_id)
                if curve_id:
                    breed_name = self.api_client.get_curve_name(curve_id)
                    if breed_name:
                        return breed_name
            except Exception as e:
                logger.debug(f"API breed unavailable for barn {barn_id}: {e}")
        return "Ross 308"
    
    def _get_current_weight(self, barn_id: str) -> Optional[float]:
        if self.api_client and hasattr(self.api_client, 'get_current_weight'):
            try:
                weight = self.api_client.get_current_weight(barn_id)
                if weight:
                    return weight
            except Exception as e:
                logger.debug(f"API current weight unavailable for barn {barn_id}: {e}")
        
        try:
            base_weight = 2000 + (int(barn_id) % 100) * 10
            return float(base_weight)
        except:
            return 2000.0
    
    def _get_yesterday_weight(self, barn_id: str) -> Optional[float]:
        if self.api_client and hasattr(self.api_client, 'get_yesterday_weight'):
            try:
                return self.api_client.get_yesterday_weight(barn_id)
            except Exception as e:
                logger.debug(f"API yesterday weight unavailable for barn {barn_id}: {e}")
        
        current = self._get_current_weight(barn_id)
        if current:
            return current - 85
        return 1915.0
    
    def _get_expected_weight(self, breed: str, age: int) -> float:
        try:
            if 'DEFAULT_WEIGHT_CONVERSION' in globals():
                return DEFAULT_WEIGHT_CONVERSION.get_expected_weight(breed, age)
            elif get_expected_weight:
                return get_expected_weight(breed, age) or 2100.0
        except:
            pass
        
        # Standard weight curve
        if age <= 7:
            return 155.0
        elif age <= 14:
            return 410.0
        elif age <= 21:
            return 840.0
        elif age <= 28:
            return 1410.0
        elif age <= 35:
            return 2050.0
        elif age <= 42:
            return 2740.0
        else:
            return 3460.0
    
    def _create_mock_result(self, barn_id: str, outdoor_temp: Optional[float] = None) -> AnalysisResult:
        """Create mock analysis result."""
        logger.info(f"Creating mock data for barn {barn_id}")
        
        try:
            base_offset = int(barn_id) % 100
        except:
            base_offset = 0
        
        age = 35
        breed = "Ross 308"
        observed_weight = 2000 + base_offset * 10
        expected_weight = 2050
        observed_gain = 85 + base_offset
        expected_gain = 90
        gain_ratio = observed_gain / expected_gain
        
        weight_status_info = self.status_system.get_weight_status(observed_weight, expected_weight)
        gain_status_info = self.status_system.get_performance_status(gain_ratio)
        
        env_metrics = self._create_mock_environmental_metrics()
        
        temperature_status_info = self.status_system.get_temperature_status(
            env_metrics.temperature_avg, age, outdoor_temp
        )
        humidity_status_info = self.status_system.get_humidity_status(env_metrics.humidity_avg)
        
        return AnalysisResult(
            barn_id=barn_id,
            age=age,
            breed=breed,
            observed_weight=observed_weight,
            expected_weight=expected_weight,
            observed_gain=observed_gain,
            expected_gain=expected_gain,
            gain_ratio=gain_ratio,
            deviation_level=gain_status_info.level,
            production_phase=self.status_system.get_production_phase(age),
            environmental_metrics=env_metrics,
            temperature_status=temperature_status_info.level,
            weight_status_info=weight_status_info,
            gain_status_info=gain_status_info,
            temperature_status_info=temperature_status_info,
            humidity_status_info=humidity_status_info
        )


# Singleton instance
_status_system = CentralizedStatusSystem()

def get_status_system() -> CentralizedStatusSystem:
    return _status_system

def get_performance_level(ratio: float) -> str:
    return get_status_system().get_performance_status(ratio).level

def get_production_phase(age: int) -> str:
    return get_status_system().get_production_phase(age)

def get_status_color(level: str) -> str:
    return get_status_system().colors.get(level, "#808080")

def get_weight_status_info(observed: float, expected: float) -> StatusInfo:
    return get_status_system().get_weight_status(observed, expected)

def get_performance_status_info(ratio: float) -> StatusInfo:
    return get_status_system().get_performance_status(ratio)

def get_temperature_status_info(temp: float, age: int, outdoor_temp: Optional[float] = None) -> StatusInfo:
    return get_status_system().get_temperature_status(temp, age, outdoor_temp)

def get_humidity_status_info(humidity: float) -> StatusInfo:
    return get_status_system().get_humidity_status(humidity)

def get_optimal_temperature_for_age(age: int) -> float:
    return get_status_system().get_optimal_temperature_midpoint(age)

def get_optimal_temperature_range(age: int) -> Tuple[float, float]:
    return get_status_system()._get_optimal_temp_range(age)
