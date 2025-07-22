"""
Barn diagnostics module for comprehensive barn health analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Import analyzer system
try:
    from .analyzer import (
        BroilerAnalyzer, get_status_system, get_weight_status_info, 
        get_performance_status_info, get_temperature_status_info,
        get_humidity_status_info, StatusInfo
    )
    ANALYZER_AVAILABLE = True
except ImportError:
    try:
        from core.analysis.analyzer import (
            BroilerAnalyzer, get_status_system, get_weight_status_info,
            get_performance_status_info, get_temperature_status_info, 
            get_humidity_status_info, StatusInfo
        )
        ANALYZER_AVAILABLE = True
    except ImportError:
        ANALYZER_AVAILABLE = False

# Import API client
try:
    from core.data.api_client import CompassAPI
    API_CLIENT_AVAILABLE = True
except ImportError:
    API_CLIENT_AVAILABLE = False


class BarnDiagnostics:
    """Comprehensive barn diagnostics system."""
    
    def __init__(self, api_client=None):
        """Initialize barn diagnostics with optional API client."""
        self.api_client = api_client or (CompassAPI() if API_CLIENT_AVAILABLE else None)
        
        if ANALYZER_AVAILABLE:
            self.analyzer = BroilerAnalyzer(self.api_client)
            self.status_system = get_status_system()
            logger.info("BarnDiagnostics initialized with analyzer system")
        else:
            self.analyzer = None
            self.status_system = None
            logger.warning("BarnDiagnostics initialized without analyzer system")
    
    def run_diagnostics(self, barn_id: str) -> Dict[str, Any]:
        """Run comprehensive diagnostics for a barn."""
        logger.info(f"Running diagnostics for barn {barn_id}")
        
        try:
            # Use analyzer system if available
            if self.analyzer:
                analysis_result = self.analyzer.analyze_barn(barn_id)
                if analysis_result:
                    return self._create_comprehensive_diagnostics(analysis_result)
            
            # Fallback to basic diagnostics
            return self._create_basic_diagnostics(barn_id)
            
        except Exception as e:
            logger.error(f"Diagnostics failed for barn {barn_id}: {e}")
            return self._create_error_diagnostics(barn_id, str(e))
    
    def _create_comprehensive_diagnostics(self, analysis_result) -> Dict[str, Any]:
        """Create comprehensive diagnostics report from analysis result."""
        diagnostics = {
            "barn_id": analysis_result.barn_id,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "overall_score": 0,
            "issues": [],
            "recommendations": [],
            "metrics": {},
            "status_info": {},
            "data_quality": "good"
        }
        
        issues = []
        recommendations = []
        total_score = 0
        metric_count = 0
        
        # Process weight diagnostics
        if analysis_result.weight_status_info:
            weight_info = analysis_result.weight_status_info
            diagnostics["status_info"]["weight"] = {
                "level": weight_info.level,
                "color": weight_info.color_hex,
                "score": weight_info.numeric_score
            }
            
            total_score += weight_info.numeric_score
            metric_count += 1
            
            if weight_info.needs_attention:
                issues.append(f"Weight status: {weight_info.level}")
                recommendations.append("Monitor weight performance closely")
        
        # Process gain performance diagnostics
        if analysis_result.gain_status_info:
            gain_info = analysis_result.gain_status_info
            diagnostics["status_info"]["gain"] = {
                "level": gain_info.level,
                "color": gain_info.color_hex,
                "score": gain_info.numeric_score
            }
            
            total_score += gain_info.numeric_score
            metric_count += 1
            
            if gain_info.needs_attention:
                issues.append(f"Gain performance: {gain_info.level}")
                recommendations.append("Review feeding program and management practices")
        
        # Process temperature diagnostics
        if analysis_result.temperature_status_info:
            temp_info = analysis_result.temperature_status_info
            diagnostics["status_info"]["temperature"] = {
                "level": temp_info.level,
                "color": temp_info.color_hex,
                "score": temp_info.numeric_score
            }
            
            total_score += temp_info.numeric_score
            metric_count += 1
            
            if temp_info.needs_attention:
                issues.append(f"Temperature: {temp_info.level}")
                recommendations.append("Adjust environmental controls")
        
        # Process humidity diagnostics
        if analysis_result.humidity_status_info:
            humidity_info = analysis_result.humidity_status_info
            diagnostics["status_info"]["humidity"] = {
                "level": humidity_info.level,
                "color": humidity_info.color_hex,
                "score": humidity_info.numeric_score
            }
            
            total_score += humidity_info.numeric_score
            metric_count += 1
            
            if humidity_info.needs_attention:
                issues.append(f"Humidity: {humidity_info.level}")
                recommendations.append("Check ventilation system")
        
        # Calculate overall score and status
        if metric_count > 0:
            overall_score = total_score / metric_count
            diagnostics["overall_score"] = overall_score
            
            # Determine overall status based on score
            if overall_score >= 85:
                diagnostics["status"] = "excellent"
            elif overall_score >= 70:
                diagnostics["status"] = "healthy"
            elif overall_score >= 50:
                diagnostics["status"] = "attention_needed"
            elif overall_score >= 25:
                diagnostics["status"] = "warning"
            else:
                diagnostics["status"] = "critical"
        
        # Add performance metrics
        diagnostics["metrics"] = {
            "observed_weight": analysis_result.observed_weight,
            "expected_weight": analysis_result.expected_weight,
            "gain_ratio": analysis_result.gain_ratio,
            "age": analysis_result.age,
            "breed": analysis_result.breed
        }
        
        # Add environmental metrics
        if analysis_result.environmental_metrics:
            env = analysis_result.environmental_metrics
            diagnostics["metrics"]["environmental"] = {
                "temperature_avg": env.temperature_avg,
                "humidity_avg": env.humidity_avg,
                "data_quality_score": env.data_quality_score
            }
            
            if env.data_quality_score < 70:
                issues.append("Low environmental data quality")
                recommendations.append("Check sensor connections and calibration")
        
        diagnostics["issues"] = issues
        diagnostics["recommendations"] = recommendations
        
        logger.info(f"Diagnostics completed: {diagnostics['status']} ({overall_score:.1f}/100)")
        return diagnostics
    
    def _create_basic_diagnostics(self, barn_id: str) -> Dict[str, Any]:
        """Create basic diagnostics when analyzer is unavailable."""
        logger.info(f"Creating basic diagnostics for barn {barn_id}")
        
        diagnostics = {
            "barn_id": barn_id,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "overall_score": 75,
            "issues": [],
            "recommendations": ["Regular monitoring recommended"],
            "metrics": {},
            "status_info": {},
            "data_quality": "limited",
            "note": "Basic diagnostics - analyzer not available"
        }
        
        # Attempt to get basic data from API client
        if self.api_client:
            try:
                # Test API connectivity
                if hasattr(self.api_client, 'test_connection'):
                    connected = self.api_client.test_connection()
                    if not connected:
                        diagnostics["issues"].append("API connection unavailable")
                        diagnostics["status"] = "warning"
                        diagnostics["overall_score"] = 50
                
                # Get basic metrics
                if hasattr(self.api_client, 'get_current_weight'):
                    weight = self.api_client.get_current_weight(barn_id)
                    if weight:
                        diagnostics["metrics"]["current_weight"] = weight
                
                if hasattr(self.api_client, 'get_age'):
                    age = self.api_client.get_age(barn_id)
                    if age:
                        diagnostics["metrics"]["age"] = age
                        
            except Exception as e:
                logger.debug(f"Basic API diagnostics failed: {e}")
                diagnostics["issues"].append("API data retrieval issues")
        
        return diagnostics
    
    def _create_error_diagnostics(self, barn_id: str, error_msg: str) -> Dict[str, Any]:
        """Create error diagnostics when diagnostics fail."""
        return {
            "barn_id": barn_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "overall_score": 0,
            "issues": [f"Diagnostics error: {error_msg}"],
            "recommendations": ["Contact system administrator"],
            "metrics": {},
            "status_info": {},
            "data_quality": "unavailable",
            "error": error_msg
        }
    
    def get_health_score(self, barn_id: str) -> float:
        """Get overall health score for a barn."""
        diagnostics = self.run_diagnostics(barn_id)
        return diagnostics.get("overall_score", 0)
    
    def get_critical_issues(self, barn_id: str) -> List[str]:
        """Get list of critical issues for a barn."""
        diagnostics = self.run_diagnostics(barn_id)
        
        critical_issues = []
        status = diagnostics.get("status", "unknown")
        
        if status in ["critical", "warning"]:
            critical_issues.extend(diagnostics.get("issues", []))
        
        # Check specific thresholds
        if ANALYZER_AVAILABLE and self.status_system:
            status_info = diagnostics.get("status_info", {})
            
            for metric, info in status_info.items():
                if info.get("level") in ["critical", "warning"]:
                    critical_issues.append(f"Critical {metric} status: {info.get('level')}")
        
        return critical_issues
    
    def run_system_check(self) -> Dict[str, Any]:
        """Run system-wide diagnostic check."""
        system_check = {
            "timestamp": datetime.now().isoformat(),
            "components": {},
            "overall_status": "healthy"
        }
        
        # Check analyzer availability
        system_check["components"]["analyzer"] = {
            "available": ANALYZER_AVAILABLE,
            "status": "healthy" if ANALYZER_AVAILABLE else "unavailable"
        }
        
        # Check API client availability
        system_check["components"]["api_client"] = {
            "available": API_CLIENT_AVAILABLE,
            "status": "healthy" if API_CLIENT_AVAILABLE else "unavailable"
        }
        
        # Test API connection if client available
        if self.api_client:
            try:
                connected = self.api_client.test_connection() if hasattr(self.api_client, 'test_connection') else False
                system_check["components"]["api_connection"] = {
                    "available": True,
                    "status": "healthy" if connected else "warning"
                }
            except Exception:
                system_check["components"]["api_connection"] = {
                    "available": False,
                    "status": "error"
                }
        
        # Determine overall system status
        component_statuses = [comp["status"] for comp in system_check["components"].values()]
        if "error" in component_statuses:
            system_check["overall_status"] = "error"
        elif "warning" in component_statuses or "unavailable" in component_statuses:
            system_check["overall_status"] = "warning"
        
        return system_check


def run_barn_diagnostics(barn_id: str) -> Dict[str, Any]:
    """Run barn diagnostics for specified barn."""
    diagnostics = BarnDiagnostics()
    return diagnostics.run_diagnostics(barn_id)


def get_barn_health_score(barn_id: str) -> float:
    """Get barn health score."""
    diagnostics = BarnDiagnostics()
    return diagnostics.get_health_score(barn_id)


def get_critical_barn_issues(barn_id: str) -> List[str]:
    """Get critical barn issues."""
    diagnostics = BarnDiagnostics()
    return diagnostics.get_critical_issues(barn_id)


if __name__ == "__main__":
    # Test diagnostics system
    diagnostics = BarnDiagnostics()
    
    # Run system check
    system_check = diagnostics.run_system_check()
    print("System Check:")
    print(f"Overall Status: {system_check['overall_status']}")
    for component, status in system_check["components"].items():
        print(f"  {component}: {status['status']}")
    
    # Run barn diagnostics
    test_barn_id = "799"
    results = diagnostics.run_diagnostics(test_barn_id)
    print(f"\nBarn {test_barn_id} Diagnostics:")
    print(f"Status: {results['status']}")
    print(f"Overall Score: {results['overall_score']}")
    print(f"Issues: {len(results['issues'])}")
    print(f"Recommendations: {len(results['recommendations'])}")
