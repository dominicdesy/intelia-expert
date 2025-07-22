"""
Alert system module - central imports for alert functionality.
This module provides a unified interface to all alert system components.
"""

# Re-export main alert system components
try:
    from .alert_thresholds_config import (
        ThresholdConfig, AlertLevel, evaluate_sensor_reading,
        get_enhanced_threshold_config, check_expert_safety_conditions, RAGAlert,
        get_threshold_config
    )
    THRESHOLDS_AVAILABLE = True
except ImportError:
    THRESHOLDS_AVAILABLE = False

try:
    from .anomaly_tracker import (
        AnomalyTracker, should_send_alert, should_send_rag_alert, 
        get_anomaly_tracker, get_anomaly_stats, reset_anomaly_tracker
    )
    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False

try:
    from .multi_client_orchestrator import (
        RAGEnabledMultiClientOrchestrator, EnhancedOrchestrationResult,
        generate_rag_enhanced_reports, validate_system_configuration
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# System availability check
def get_alert_system_status():
    """Get the availability status of alert system components."""
    return {
        "thresholds_available": THRESHOLDS_AVAILABLE,
        "tracker_available": TRACKER_AVAILABLE, 
        "orchestrator_available": ORCHESTRATOR_AVAILABLE,
        "system_ready": THRESHOLDS_AVAILABLE and TRACKER_AVAILABLE
    }

# Main imports for convenience
__all__ = [
    'ThresholdConfig', 'AlertLevel', 'evaluate_sensor_reading',
    'get_enhanced_threshold_config', 'check_expert_safety_conditions', 'RAGAlert',
    'AnomalyTracker', 'should_send_alert', 'should_send_rag_alert',
    'get_anomaly_tracker', 'get_alert_system_status'
]
