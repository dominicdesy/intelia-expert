"""
Anomaly tracker for managing persistent alerts with multi-level persistence.
Tracks anomaly history and prevents alert spam through intelligent cooldowns.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels with different persistence requirements."""
    EMERGENCY = "emergency"
    CRITICAL = "critical" 
    WARNING = "warning"
    RAG_EXPERT = "rag_expert"
    NORMAL = "normal"


@dataclass
class RAGAnomalyRecord:
    """RAG-based anomaly detection record."""
    timestamp: datetime
    alert_type: str
    expert_warning: str
    knowledge_source: str
    confidence_score: float
    conditions: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "alert_type": self.alert_type,
            "expert_warning": self.expert_warning,
            "knowledge_source": self.knowledge_source,
            "confidence_score": self.confidence_score,
            "conditions": self.conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RAGAnomalyRecord':
        """Create instance from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            alert_type=data["alert_type"],
            expert_warning=data["expert_warning"],
            knowledge_source=data["knowledge_source"],
            confidence_score=data["confidence_score"],
            conditions=data["conditions"]
        )


@dataclass
class AnomalyRecord:
    """Single anomaly detection record."""
    timestamp: datetime
    value: float
    alert_level: AlertLevel
    outdoor_temp: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "alert_level": self.alert_level.value,
            "outdoor_temp": self.outdoor_temp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AnomalyRecord':
        """Create instance from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            value=data["value"],
            alert_level=AlertLevel(data["alert_level"]),
            outdoor_temp=data.get("outdoor_temp")
        )


@dataclass
class AlertState:
    """Current alert state for barn-sensor combination."""
    barn_id: str
    sensor: str
    consecutive_anomalies: int = 0
    last_alert_sent: Optional[datetime] = None
    last_anomaly_level: Optional[AlertLevel] = None
    anomaly_history: List[AnomalyRecord] = None
    rag_alerts_history: List[RAGAnomalyRecord] = None
    
    def __post_init__(self):
        if self.anomaly_history is None:
            self.anomaly_history = []
        if self.rag_alerts_history is None:
            self.rag_alerts_history = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for persistence."""
        return {
            "barn_id": self.barn_id,
            "sensor": self.sensor,
            "consecutive_anomalies": self.consecutive_anomalies,
            "last_alert_sent": self.last_alert_sent.isoformat() if self.last_alert_sent else None,
            "last_anomaly_level": self.last_anomaly_level.value if self.last_anomaly_level else None,
            "anomaly_history": [record.to_dict() for record in self.anomaly_history],
            "rag_alerts_history": [record.to_dict() for record in self.rag_alerts_history]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AlertState':
        """Create instance from dictionary."""
        return cls(
            barn_id=data["barn_id"],
            sensor=data["sensor"],
            consecutive_anomalies=data.get("consecutive_anomalies", 0),
            last_alert_sent=datetime.fromisoformat(data["last_alert_sent"]) if data.get("last_alert_sent") else None,
            last_anomaly_level=AlertLevel(data["last_anomaly_level"]) if data.get("last_anomaly_level") else None,
            anomaly_history=[AnomalyRecord.from_dict(r) for r in data.get("anomaly_history", [])],
            rag_alerts_history=[RAGAnomalyRecord.from_dict(r) for r in data.get("rag_alerts_history", [])]
        )


class AnomalyTracker:
    """Tracks anomalies and manages alert persistence logic."""
    
    # Minimum consecutive readings required before alert
    PERSISTENCE_REQUIREMENTS = {
        AlertLevel.EMERGENCY: 0,      # Immediate alert
        AlertLevel.CRITICAL: 2,       # 2 consecutive readings
        AlertLevel.WARNING: 3,        # 3 consecutive readings
        AlertLevel.RAG_EXPERT: 1,     # 1 reading for expert alerts
        AlertLevel.NORMAL: None       # No alert needed
    }
    
    # Cooldown periods in minutes before re-alerting
    ALERT_COOLDOWNS = {
        AlertLevel.EMERGENCY: 240,    # 4 hours
        AlertLevel.CRITICAL: 360,     # 6 hours
        AlertLevel.WARNING: 720,      # 12 hours
        AlertLevel.RAG_EXPERT: 480    # 8 hours
    }
    
    DEFAULT_COOLDOWN_MINUTES = 360
    RAG_CONFIDENCE_THRESHOLD = 0.7
    HISTORY_RETENTION_DAYS = 7
    
    def __init__(self, state_file: str = "data/anomaly_tracker_state.json"):
        """Initialize anomaly tracker with persistent state."""
        self.state_file = Path(state_file)
        self.alert_states: Dict[str, AlertState] = {}
        self.logger = logging.getLogger(__name__)
        self._load_state()
    
    def _get_state_key(self, barn_id: str, sensor: str) -> str:
        """Generate unique key for barn-sensor combination."""
        return f"{barn_id}_{sensor}"
    
    def _load_state(self):
        """Load persistent state from file."""
        if not self.state_file.exists():
            self.logger.info(f"No existing state file: {self.state_file}")
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            for key, state_data in data.items():
                self.alert_states[key] = AlertState.from_dict(state_data)
            
            self.logger.info(f"Loaded state for {len(self.alert_states)} barn-sensor combinations")
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            self.alert_states = {}
    
    def _save_state(self):
        """Save current state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self._cleanup_old_history()
            
            data = {key: state.to_dict() for key, state in self.alert_states.items()}
            
            with open(self.state_file, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved state to {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def _cleanup_old_history(self):
        """Remove old history records to keep file size manageable."""
        cutoff_time = datetime.now() - timedelta(days=self.HISTORY_RETENTION_DAYS)
        
        for state in self.alert_states.values():
            state.anomaly_history = [
                record for record in state.anomaly_history 
                if record.timestamp > cutoff_time
            ]
            state.rag_alerts_history = [
                record for record in state.rag_alerts_history
                if record.timestamp > cutoff_time
            ]
    
    def _get_or_create_state(self, barn_id: str, sensor: str) -> AlertState:
        """Get existing state or create new one."""
        key = self._get_state_key(barn_id, sensor)
        
        if key not in self.alert_states:
            self.alert_states[key] = AlertState(barn_id=barn_id, sensor=sensor)
        
        return self.alert_states[key]
    
    def record_anomaly(self, barn_id: str, sensor: str, value: float, 
                      alert_level: AlertLevel, outdoor_temp: Optional[float] = None) -> bool:
        """Record anomaly and determine if alert should be sent."""
        current_time = datetime.now()
        state = self._get_or_create_state(barn_id, sensor)
        
        # Create anomaly record
        anomaly_record = AnomalyRecord(
            timestamp=current_time,
            value=value,
            alert_level=alert_level,
            outdoor_temp=outdoor_temp
        )
        
        state.anomaly_history.append(anomaly_record)
        
        # Update consecutive counter
        if state.last_anomaly_level == alert_level:
            state.consecutive_anomalies += 1
        else:
            state.consecutive_anomalies = 1
        
        state.last_anomaly_level = alert_level
        
        # Determine if alert should be sent
        should_alert = self._should_send_alert(state, alert_level, current_time)
        
        if should_alert:
            state.last_alert_sent = current_time
            self.logger.info(f"Alert triggered for {barn_id}.{sensor}: {alert_level.value}")
        
        self._save_state()
        return should_alert
    
    def record_rag_alert(self, barn_id: str, alert_type: str, expert_warning: str,
                         knowledge_source: str, confidence_score: float,
                         conditions: Dict[str, Any]) -> bool:
        """Record RAG-based expert alert and determine if notification should be sent."""
        current_time = datetime.now()
        state = self._get_or_create_state(barn_id, "rag_system")
        
        rag_record = RAGAnomalyRecord(
            timestamp=current_time,
            alert_type=alert_type,
            expert_warning=expert_warning,
            knowledge_source=knowledge_source,
            confidence_score=confidence_score,
            conditions=conditions
        )
        
        state.rag_alerts_history.append(rag_record)
        
        # Send alert if confidence is high and cooldown has passed
        if confidence_score > self.RAG_CONFIDENCE_THRESHOLD:
            should_alert = self._check_cooldown(state, AlertLevel.RAG_EXPERT, current_time)
            
            if should_alert:
                state.last_alert_sent = current_time
                self.logger.info(f"RAG expert alert triggered for {barn_id}: {alert_type}")
                self._save_state()
                return True
        
        self._save_state()
        return False
    
    def _should_send_alert(self, state: AlertState, alert_level: AlertLevel, 
                          current_time: datetime) -> bool:
        """Determine if alert should be sent based on persistence and cooldown."""
        
        if alert_level == AlertLevel.NORMAL:
            return False
        
        if alert_level not in self.PERSISTENCE_REQUIREMENTS:
            self.logger.debug(f"No persistence requirement defined for {alert_level}")
            return False
        
        persistence_required = self.PERSISTENCE_REQUIREMENTS[alert_level]
        
        # Emergency alerts send immediately, check cooldown only for subsequent alerts
        if persistence_required == 0:
            if state.last_alert_sent is None:
                return True  # First emergency alert always sends
            
            cooldown_minutes = self.ALERT_COOLDOWNS.get(alert_level, self.DEFAULT_COOLDOWN_MINUTES)
            time_since_last = (current_time - state.last_alert_sent).total_seconds() / 60
            return time_since_last >= cooldown_minutes
        
        # Persistence-based alerts require multiple consecutive readings
        if state.consecutive_anomalies >= persistence_required:
            return self._check_cooldown(state, alert_level, current_time)
        
        return False
    
    def _check_cooldown(self, state: AlertState, alert_level: AlertLevel, 
                       current_time: datetime) -> bool:
        """Check if cooldown period has passed since last alert."""
        if not state.last_alert_sent:
            return True
        
        cooldown_minutes = self.ALERT_COOLDOWNS.get(alert_level, self.DEFAULT_COOLDOWN_MINUTES)
        time_since_last = (current_time - state.last_alert_sent).total_seconds() / 60
        
        return time_since_last >= cooldown_minutes
    
    def get_current_state(self, barn_id: str, sensor: str) -> Optional[AlertState]:
        """Get current alert state for barn-sensor combination."""
        key = self._get_state_key(barn_id, sensor)
        return self.alert_states.get(key)
    
    def get_recent_anomalies(self, barn_id: str, sensor: str, 
                           hours: int = 24) -> List[AnomalyRecord]:
        """Get recent anomalies for barn-sensor combination."""
        state = self.get_current_state(barn_id, sensor)
        if not state:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            record for record in state.anomaly_history
            if record.timestamp >= cutoff_time and record.alert_level != AlertLevel.NORMAL
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        total_states = len(self.alert_states)
        active_anomalies = sum(1 for state in self.alert_states.values() 
                             if state.consecutive_anomalies > 0)
        
        recent_alerts = sum(1 for state in self.alert_states.values()
                          if (state.last_alert_sent and 
                              datetime.now() - state.last_alert_sent < timedelta(hours=24)))
        
        total_history_records = sum(len(state.anomaly_history) for state in self.alert_states.values())
        
        return {
            "total_tracked_sensors": total_states,
            "active_anomalies": active_anomalies,
            "recent_alerts_24h": recent_alerts,
            "total_history_records": total_history_records,
            "state_file": str(self.state_file.absolute()),
            "state_file_exists": self.state_file.exists()
        }
    
    def clear_state(self, barn_id: Optional[str] = None):
        """Clear tracking state for specific barn or all barns."""
        if barn_id:
            keys_to_remove = [key for key in self.alert_states.keys() 
                            if key.startswith(f"{barn_id}_")]
            for key in keys_to_remove:
                del self.alert_states[key]
            self.logger.info(f"Cleared state for barn {barn_id}")
        else:
            self.alert_states.clear()
            self.logger.info("Cleared all tracking state")
        
        self._save_state()
    
    def reset_state_for_testing(self):
        """Reset all tracking state for testing purposes."""
        self.alert_states.clear()
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass


# Global anomaly tracker instance
_anomaly_tracker = None

def get_anomaly_tracker() -> AnomalyTracker:
    """Get global anomaly tracker instance."""
    global _anomaly_tracker
    if _anomaly_tracker is None:
        _anomaly_tracker = AnomalyTracker()
    return _anomaly_tracker


def should_send_alert(barn_id: str, sensor: str, value: float, 
                     alert_level: AlertLevel, outdoor_temp: Optional[float] = None) -> bool:
    """Check if alert should be sent for given conditions."""
    if alert_level == AlertLevel.NORMAL:
        return False
    
    return get_anomaly_tracker().record_anomaly(barn_id, sensor, value, alert_level, outdoor_temp)


def should_send_rag_alert(barn_id: str, alert_type: str, expert_warning: str,
                         knowledge_source: str, confidence_score: float,
                         conditions: Dict[str, Any]) -> bool:
    """Check if RAG expert alert should be sent."""
    return get_anomaly_tracker().record_rag_alert(
        barn_id, alert_type, expert_warning, knowledge_source, 
        confidence_score, conditions
    )


def get_anomaly_stats() -> Dict[str, Any]:
    """Get anomaly tracking statistics."""
    return get_anomaly_tracker().get_stats()


def reset_anomaly_tracker():
    """Reset global anomaly tracker for testing."""
    global _anomaly_tracker
    if _anomaly_tracker is not None:
        _anomaly_tracker.reset_state_for_testing()
    _anomaly_tracker = None