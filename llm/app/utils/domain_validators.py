# -*- coding: utf-8 -*-
"""
domain_validators.py - Domain-specific validation rules to prevent hallucinations
Version: 1.0.0
Last modified: 2025-10-28

CRITICAL: These validators prevent dangerous numerical hallucinations that could
cause massive economic losses in poultry production.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """Represents a validation warning for out-of-range values"""
    metric: str
    value: float
    expected_range: Tuple[float, float]
    context: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    suggestion: Optional[str] = None


class PoultryMetricsValidator:
    """
    Validates poultry metrics in LLM responses to block dangerous hallucinations

    Example hallucinations this prevents:
    - "FCR of 0.2" (impossible - realistic is 1.3-2.0)
    - "Mortality of 85%" (catastrophic - normal is 2-8%)
    - "Vaccinate at 150 days" (wrong species - broilers are 35-42 days old at slaughter)
    - "Temperature of 60°C" (would kill birds - correct is 18-25°C)

    Usage:
        validator = PoultryMetricsValidator()
        result = validator.validate_response(text, language="en")

        if result["blocked"]:
            # Response contains critical hallucinations - do not return to user
            return error_message
    """

    # Acceptable value ranges for common poultry metrics
    # Format: metric_key: (min_value, max_value, unit)
    VALID_RANGES = {
        # === PERFORMANCE METRICS ===
        "fcr": (0.8, 3.5, "ratio", "Feed Conversion Ratio"),
        "adg": (15, 120, "g/day", "Average Daily Gain"),
        "bw_broiler": (500, 4500, "g", "Broiler Body Weight"),
        "bw_layer": (1200, 2200, "g", "Layer Body Weight"),
        "feed_intake_broiler": (50, 200, "g/day", "Broiler Feed Intake"),
        "feed_intake_layer": (90, 140, "g/day", "Layer Feed Intake"),

        # === MORTALITY & HEALTH ===
        "mortality_daily": (0.0, 2.0, "%", "Daily Mortality Rate"),
        "mortality_cumulative": (0.0, 25.0, "%", "Cumulative Mortality"),
        "hatchability": (60.0, 95.0, "%", "Hatchability Rate"),

        # === PRODUCTION (LAYERS) ===
        "hen_day_production": (60.0, 98.0, "%", "Hen-Day Egg Production"),
        "egg_weight": (45, 75, "g", "Egg Weight"),
        "eggs_per_hen": (200, 340, "eggs/year", "Annual Eggs per Hen"),

        # === AGE & TIMING (DAYS) ===
        "age_vaccination": (1, 150, "days", "Vaccination Age"),
        "age_slaughter_broiler": (28, 70, "days", "Broiler Slaughter Age"),
        "age_first_egg": (100, 200, "days", "Age at First Egg"),

        # === ENVIRONMENTAL ===
        "temperature": (10, 38, "°C", "Environmental Temperature"),
        "humidity": (35, 85, "%", "Relative Humidity"),
        "ventilation_rate": (0.5, 15.0, "m³/h/kg", "Ventilation Rate"),

        # === NUTRITION ===
        "protein_percent": (12.0, 28.0, "%", "Dietary Protein"),
        "energy_me": (2400, 3400, "kcal/kg", "Metabolizable Energy"),
        "calcium_percent": (0.5, 5.0, "%", "Dietary Calcium"),

        # === DOSAGES (general ranges - specific drugs vary) ===
        "vaccine_dose": (0.05, 2.0, "mL", "Vaccine Dose"),
        "water_medication": (0.01, 100.0, "g/L", "Water Medication Concentration"),
    }

    # Regex patterns to extract metrics from text
    # Format: metric_key: [list of regex patterns]
    EXTRACTION_PATTERNS = {
        "fcr": [
            r"FCR\s+(?:of|is|=|:)?\s*(\d+\.?\d*)",
            r"feed\s+conversion\s+(?:ratio)?\s+(?:of|is)?\s*(\d+\.?\d*)",
            r"conversion\s+ratio[:\s]+(\d+\.?\d*)",
        ],
        "mortality_cumulative": [
            r"(\d+\.?\d*)\s*%\s+mortality",
            r"mortality\s+(?:of|is|=|:)?\s*(\d+\.?\d*)\s*%",
            r"cumulative\s+mortality[:\s]+(\d+\.?\d*)\s*%",
        ],
        "mortality_daily": [
            r"daily\s+mortality[:\s]+(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*%\s+daily\s+deaths",
        ],
        "age_vaccination": [
            r"vaccin(?:e|ate|ation)\s+at\s+(\d+)\s+days?",
            r"vaccin(?:e|ate|ation)\s+(?:à|au)\s+(\d+)\s+jours?",
            r"day\s+(\d+)\s+vaccin",
        ],
        "age_slaughter_broiler": [
            r"slaughter\s+at\s+(\d+)\s+days?",
            r"abattage\s+(?:à|au)\s+(\d+)\s+jours?",
            r"(\d+)\s+days?\s+(?:old\s+)?(?:for\s+)?slaughter",
        ],
        "temperature": [
            r"temperature\s+(?:of|is|at|=|:)?\s*(\d+\.?\d*)\s*°?C",
            r"(\d+\.?\d*)\s*°C",
            r"temp[érature]+\s+(?:de|à)?\s*(\d+\.?\d*)\s*°?C",
        ],
        "adg": [
            r"ADG\s+(?:of|is|=|:)?\s*(\d+\.?\d*)",
            r"average\s+daily\s+gain[:\s]+(\d+\.?\d*)\s*g",
            r"gain\s+(?:moyen\s+)?quotidien[:\s]+(\d+\.?\d*)\s*g",
        ],
        "hen_day_production": [
            r"hen[- ]day\s+production[:\s]+(\d+\.?\d*)\s*%",
            r"HD\s+production[:\s]+(\d+\.?\d*)\s*%",
            r"(\d+\.?\d*)\s*%\s+(?:hen[- ]day|HD)",
        ],
    }

    def __init__(self) -> None:
        """Initialize the validator"""
        logger.info(f"[OK] PoultryMetricsValidator initialized with {len(self.VALID_RANGES)} metric ranges")

    def validate_response(
        self,
        text: str,
        language: str = "en",
        strict_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Validate a generated response for metric hallucinations

        Args:
            text: Generated response text
            language: Response language (for localized patterns)
            strict_mode: If True, block on HIGH/CRITICAL severity. If False, only warn.

        Returns:
            {
                "is_valid": bool,  # False if hallucinations detected
                "warnings": List[ValidationWarning],  # List of issues found
                "blocked": bool,  # True if response should be blocked
                "suggestion": str  # Suggested corrective action
            }
        """
        warnings = []

        # Extract and validate all metrics
        for metric_key, patterns in self.EXTRACTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    try:
                        value = float(match.group(1))
                        warning = self._validate_metric(metric_key, value, match.group(0))
                        if warning:
                            warnings.append(warning)
                    except (ValueError, IndexError):
                        continue

        # Determine if response should be blocked
        critical_warnings = [w for w in warnings if w.severity in ["HIGH", "CRITICAL"]]
        blocked = strict_mode and len(critical_warnings) > 0

        # Generate suggestion
        suggestion = self._generate_suggestion(warnings, blocked)

        result = {
            "is_valid": len(warnings) == 0,
            "warnings": [self._warning_to_dict(w) for w in warnings],
            "blocked": blocked,
            "suggestion": suggestion,
        }

        if warnings:
            logger.warning(
                f"[VALIDATION] Found {len(warnings)} metric issues "
                f"(blocked={blocked}, critical={len(critical_warnings)})"
            )

        return result

    def _validate_metric(
        self,
        metric_key: str,
        value: float,
        context: str
    ) -> Optional[ValidationWarning]:
        """
        Validate a single metric value against acceptable ranges

        Returns:
            ValidationWarning if out of range, None otherwise
        """
        if metric_key not in self.VALID_RANGES:
            return None

        min_val, max_val, unit, description = self.VALID_RANGES[metric_key]

        # Check if value is within acceptable range
        if min_val <= value <= max_val:
            return None  # Valid value

        # Value is out of range - determine severity
        severity = self._calculate_severity(value, min_val, max_val)

        # Generate suggestion
        suggestion = self._generate_correction_suggestion(metric_key, value, min_val, max_val, unit)

        return ValidationWarning(
            metric=metric_key,
            value=value,
            expected_range=(min_val, max_val),
            context=context,
            severity=severity,
            suggestion=suggestion
        )

    def _calculate_severity(self, value: float, min_val: float, max_val: float) -> str:
        """
        Calculate severity of out-of-range value

        CRITICAL: Value is completely unrealistic (>3x out of range)
        HIGH: Value is very wrong (2-3x out of range)
        MEDIUM: Value is somewhat wrong (1.5-2x out of range)
        LOW: Value is slightly out of range (<1.5x out of range)
        """
        if value < min_val:
            ratio = min_val / value if value > 0 else float('inf')
        else:  # value > max_val
            ratio = value / max_val

        if ratio >= 3.0:
            return "CRITICAL"
        elif ratio >= 2.0:
            return "HIGH"
        elif ratio >= 1.5:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_correction_suggestion(
        self,
        metric_key: str,
        value: float,
        min_val: float,
        max_val: float,
        unit: str
    ) -> str:
        """Generate a human-readable correction suggestion"""
        _, _, _, description = self.VALID_RANGES[metric_key]

        if value < min_val:
            return (
                f"{description} of {value} {unit} is too low. "
                f"Expected range: {min_val}-{max_val} {unit}. "
                f"Typical value: ~{(min_val + max_val) / 2:.1f} {unit}"
            )
        else:
            return (
                f"{description} of {value} {unit} is too high. "
                f"Expected range: {min_val}-{max_val} {unit}. "
                f"Typical value: ~{(min_val + max_val) / 2:.1f} {unit}"
            )

    def _generate_suggestion(self, warnings: List[ValidationWarning], blocked: bool) -> str:
        """Generate overall suggestion based on warnings"""
        if not warnings:
            return "Response validated successfully"

        if blocked:
            critical_warnings = [w for w in warnings if w.severity in ["HIGH", "CRITICAL"]]
            return (
                f"Response contains {len(critical_warnings)} critical metric hallucination(s). "
                f"This response should NOT be shown to users. "
                f"Consider regenerating with explicit constraints in the prompt."
            )
        else:
            return (
                f"Response contains {len(warnings)} metric warning(s). "
                f"Review these values for accuracy before presenting to users."
            )

    def _warning_to_dict(self, warning: ValidationWarning) -> Dict[str, Any]:
        """Convert ValidationWarning to dict for JSON serialization"""
        return {
            "metric": warning.metric,
            "value": warning.value,
            "expected_range": warning.expected_range,
            "context": warning.context,
            "severity": warning.severity,
            "suggestion": warning.suggestion,
        }


# Singleton instance
_validator_instance = None


def get_poultry_validator() -> PoultryMetricsValidator:
    """Get or create PoultryMetricsValidator singleton"""
    global _validator_instance

    if _validator_instance is None:
        _validator_instance = PoultryMetricsValidator()

    return _validator_instance
