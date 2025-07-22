"""Farm health scoring system with centralized status evaluation."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import centralized analyzer system
try:
    from .analyzer import (
        BroilerAnalyzer, get_status_system, get_weight_status_info,
        get_performance_status_info, get_temperature_status_info,
        get_humidity_status_info, StatusInfo, CentralizedStatusSystem
    )
    ANALYZER_AVAILABLE = True
except ImportError:
    try:
        from core.analysis.analyzer import (
            BroilerAnalyzer, get_status_system, get_weight_status_info,
            get_performance_status_info, get_temperature_status_info,
            get_humidity_status_info, StatusInfo, CentralizedStatusSystem
        )
        ANALYZER_AVAILABLE = True
    except ImportError:
        ANALYZER_AVAILABLE = False
        logger.warning("Centralized analyzer not available in farm_health_scoring")

# Import barn diagnostics
try:
    from .barn_diagnostics import BarnDiagnostics
    DIAGNOSTICS_AVAILABLE = True
except ImportError:
    try:
        from barn_diagnostics import BarnDiagnostics
        DIAGNOSTICS_AVAILABLE = True
    except ImportError:
        DIAGNOSTICS_AVAILABLE = False
        logger.warning("Barn diagnostics not available in farm_health_scoring")


@dataclass
class HealthMetric:
    """Individual health metric with centralized scoring."""
    name: str
    value: float
    weight: float  # Importance weight (0-1)
    status_info: Optional[StatusInfo] = None
    
    @property
    def weighted_score(self) -> float:
        """Get weighted score for this metric."""
        base_score = self.status_info.numeric_score if self.status_info else 50.0
        return base_score * self.weight
    
    @property
    def is_critical(self) -> bool:
        """Check if metric is in critical state."""
        return self.status_info and self.status_info.level == "critical"


@dataclass
class FarmHealthScore:
    """Complete farm health score with detailed breakdown."""
    overall_score: float
    grade: str  # A, B, C, D, F
    status: str  # excellent, good, fair, poor, critical
    metrics: List[HealthMetric]
    timestamp: datetime
    barn_count: int
    critical_issues: List[str]
    recommendations: List[str]
    
    @property
    def performance_metrics(self) -> List[HealthMetric]:
        """Get performance-related metrics."""
        return [m for m in self.metrics if 'weight' in m.name.lower() or 'gain' in m.name.lower()]
    
    @property
    def environmental_metrics(self) -> List[HealthMetric]:
        """Get environment-related metrics."""
        return [m for m in self.metrics if 'temperature' in m.name.lower() or 'humidity' in m.name.lower()]
    
    @property
    def critical_metric_count(self) -> int:
        """Count of metrics in critical state."""
        return sum(1 for m in self.metrics if m.is_critical)


class FarmHealthScorer:
    """Calculate farm health scores from broiler performance data."""
    
    def __init__(self, api_client=None):
        """Initialize farm health scorer."""
        if ANALYZER_AVAILABLE:
            self.status_system = get_status_system()
            self.analyzer = BroilerAnalyzer(api_client)
            logger.info("FarmHealthScorer initialized with centralized system")
        else:
            self.status_system = None
            self.analyzer = None
            logger.warning("FarmHealthScorer initialized without centralized system")
        
        if DIAGNOSTICS_AVAILABLE:
            self.diagnostics = BarnDiagnostics(api_client)
        else:
            self.diagnostics = None
        
        # Metric weights for overall score calculation
        self.metric_weights = {
            'weight_performance': 0.25,
            'gain_performance': 0.25,
            'temperature_control': 0.20,
            'humidity_control': 0.15,
            'data_quality': 0.10,
            'system_health': 0.05
        }
    
    def calculate_health_score(self, data: Dict[str, Any]) -> float:
        """Calculate health score for farm data."""
        farm_score = self.calculate_comprehensive_score(data)
        return farm_score.overall_score
    
    def calculate_comprehensive_score(self, data: Dict[str, Any]) -> FarmHealthScore:
        """Calculate comprehensive farm health score."""
        logger.info("Calculating comprehensive farm health score")
        
        try:
            if self.status_system and isinstance(data, dict):
                return self._calculate_score_with_status_system(data)
            else:
                return self._calculate_basic_score(data)
                
        except Exception as e:
            logger.error(f"Health score calculation failed: {e}")
            return self._create_error_score(str(e))
    
    def _calculate_score_with_status_system(self, data: Dict[str, Any]) -> FarmHealthScore:
        """Calculate score using status system."""
        metrics = []
        barn_ids = data.get('barn_ids', [])
        
        if not barn_ids:
            barn_ids = [data.get('barn_id', 'unknown')]
        
        barn_scores = []
        all_critical_issues = []
        all_recommendations = []
        
        for barn_id in barn_ids:
            try:
                barn_score, barn_metrics, issues, recommendations = self._analyze_barn_health(barn_id, data)
                barn_scores.append(barn_score)
                metrics.extend(barn_metrics)
                all_critical_issues.extend(issues)
                all_recommendations.extend(recommendations)
                
            except Exception as e:
                logger.warning(f"Failed to analyze barn {barn_id}: {e}")
                # Add error metric
                error_metric = HealthMetric(
                    name=f"barn_{barn_id}_error",
                    value=0.0,
                    weight=1.0 / len(barn_ids)
                )
                metrics.append(error_metric)
                barn_scores.append(0.0)
        
        # Calculate overall score
        if barn_scores:
            overall_score = sum(barn_scores) / len(barn_scores)
        else:
            overall_score = 0.0
        
        # Determine grade and status
        grade, status = self._calculate_grade_and_status(overall_score)
        
        return FarmHealthScore(
            overall_score=overall_score,
            grade=grade,
            status=status,
            metrics=metrics,
            timestamp=datetime.now(),
            barn_count=len(barn_ids),
            critical_issues=list(set(all_critical_issues)),
            recommendations=list(set(all_recommendations))
        )
    
    def _analyze_barn_health(self, barn_id: str, data: Dict[str, Any]) -> Tuple[float, List[HealthMetric], List[str], List[str]]:
        """Analyze individual barn health using centralized system."""
        if not self.analyzer:
            return 50.0, [], [], []
        
        try:
            # Get comprehensive analysis
            analysis_result = self.analyzer.analyze_barn(barn_id)
            if not analysis_result:
                return 50.0, [], [f"No data available for barn {barn_id}"], []
            
            metrics = []
            issues = []
            recommendations = []
            
            # Weight performance metric
            if analysis_result.weight_status_info:
                weight_metric = HealthMetric(
                    name=f"weight_performance_{barn_id}",
                    value=analysis_result.observed_weight,
                    weight=self.metric_weights['weight_performance'],
                    status_info=analysis_result.weight_status_info
                )
                metrics.append(weight_metric)
                
                if weight_metric.is_critical:
                    issues.append(f"Barn {barn_id}: Critical weight performance")
                    recommendations.append(f"Barn {barn_id}: Review feeding program")
            
            # Gain performance metric
            if analysis_result.gain_status_info:
                gain_metric = HealthMetric(
                    name=f"gain_performance_{barn_id}",
                    value=analysis_result.gain_ratio,
                    weight=self.metric_weights['gain_performance'],
                    status_info=analysis_result.gain_status_info
                )
                metrics.append(gain_metric)
                
                if gain_metric.is_critical:
                    issues.append(f"Barn {barn_id}: Critical gain performance")
                    recommendations.append(f"Barn {barn_id}: Assess management practices")
            
            # Temperature control metric
            if analysis_result.temperature_status_info:
                temp_metric = HealthMetric(
                    name=f"temperature_control_{barn_id}",
                    value=analysis_result.environmental_metrics.temperature_avg if analysis_result.environmental_metrics else 0,
                    weight=self.metric_weights['temperature_control'],
                    status_info=analysis_result.temperature_status_info
                )
                metrics.append(temp_metric)
                
                if temp_metric.is_critical:
                    issues.append(f"Barn {barn_id}: Critical temperature control")
                    recommendations.append(f"Barn {barn_id}: Check HVAC system")
            
            # Humidity control metric
            if analysis_result.humidity_status_info:
                humidity_metric = HealthMetric(
                    name=f"humidity_control_{barn_id}",
                    value=analysis_result.environmental_metrics.humidity_avg if analysis_result.environmental_metrics else 0,
                    weight=self.metric_weights['humidity_control'],
                    status_info=analysis_result.humidity_status_info
                )
                metrics.append(humidity_metric)
                
                if humidity_metric.is_critical:
                    issues.append(f"Barn {barn_id}: Critical humidity control")
                    recommendations.append(f"Barn {barn_id}: Check ventilation system")
            
            # Data quality metric
            if analysis_result.environmental_metrics:
                data_quality_score = analysis_result.environmental_metrics.data_quality_score
                # Create status info for data quality
                if data_quality_score >= 90:
                    dq_level = "excellent"
                elif data_quality_score >= 75:
                    dq_level = "normal"
                elif data_quality_score >= 50:
                    dq_level = "attention"
                else:
                    dq_level = "critical"
                
                dq_status = StatusInfo(
                    level=dq_level,
                    color_hex=self.status_system.colors.get(dq_level, "#808080"),
                    status_key=f"status.{dq_level}",
                    description_key=f"data_quality.{dq_level}",
                    numeric_score=data_quality_score
                )
                
                dq_metric = HealthMetric(
                    name=f"data_quality_{barn_id}",
                    value=data_quality_score,
                    weight=self.metric_weights['data_quality'],
                    status_info=dq_status
                )
                metrics.append(dq_metric)
                
                if data_quality_score < 50:
                    issues.append(f"Barn {barn_id}: Poor data quality")
                    recommendations.append(f"Barn {barn_id}: Check sensor connections")
            
            # Calculate barn score
            if metrics:
                barn_score = sum(m.weighted_score for m in metrics) / sum(m.weight for m in metrics)
            else:
                barn_score = 50.0
            
            return barn_score, metrics, issues, recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing barn {barn_id}: {e}")
            return 25.0, [], [f"Analysis error for barn {barn_id}"], []
    
    def _calculate_basic_score(self, data: Dict[str, Any]) -> FarmHealthScore:
        """Calculate basic score when centralized system not available."""
        logger.info("Calculating basic farm health score")
        
        # Simple scoring based on available data
        basic_score = 75.0  # Default reasonable score
        
        # Adjust based on available data indicators
        if 'barn_count' in data:
            barn_count = data['barn_count']
        else:
            barn_count = 1
        
        # Create basic metrics
        metrics = [
            HealthMetric(
                name="system_availability",
                value=basic_score,
                weight=1.0
            )
        ]
        
        grade, status = self._calculate_grade_and_status(basic_score)
        
        return FarmHealthScore(
            overall_score=basic_score,
            grade=grade,
            status=status,
            metrics=metrics,
            timestamp=datetime.now(),
            barn_count=barn_count,
            critical_issues=["Centralized analyzer not available"],
            recommendations=["Enable centralized monitoring system"]
        )
    
    def _create_error_score(self, error_msg: str) -> FarmHealthScore:
        """Create error score when calculation fails."""
        return FarmHealthScore(
            overall_score=0.0,
            grade="F",
            status="error",
            metrics=[],
            timestamp=datetime.now(),
            barn_count=0,
            critical_issues=[f"Scoring error: {error_msg}"],
            recommendations=["Contact system administrator"]
        )
    
    def _calculate_grade_and_status(self, score: float) -> Tuple[str, str]:
        """Calculate letter grade and status from numeric score."""
        if score >= 90:
            return "A", "excellent"
        elif score >= 80:
            return "B", "good"
        elif score >= 70:
            return "C", "fair"
        elif score >= 60:
            return "D", "poor"
        else:
            return "F", "critical"
    
    def get_historical_trends(self, barn_ids: List[str], days: int = 7) -> Dict[str, List[float]]:
        """Get historical health score trends."""
        trends = {}
        
        if not self.diagnostics:
            logger.warning("Historical trends not available - diagnostics system unavailable")
            return trends
        
        for barn_id in barn_ids:
            daily_scores = []
            
            # Simulate historical data (in real implementation, would query database)
            for day in range(days):
                try:
                    # In real implementation, would get historical data for specific date
                    score = self.diagnostics.get_health_score(barn_id)
                    # Add some variation to simulate historical changes
                    import random
                    historical_score = max(0, min(100, score + random.uniform(-10, 10)))
                    daily_scores.append(historical_score)
                except Exception as e:
                    logger.debug(f"Failed to get historical score for {barn_id}: {e}")
                    daily_scores.append(50.0)  # Default
            
            trends[barn_id] = daily_scores
        
        return trends
    
    def compare_farms(self, farm_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple farms."""
        farm_scores = []
        
        for i, farm_data in enumerate(farm_data_list):
            farm_name = farm_data.get('farm_name', f'Farm_{i+1}')
            score = self.calculate_comprehensive_score(farm_data)
            farm_scores.append({
                'name': farm_name,
                'score': score.overall_score,
                'grade': score.grade,
                'status': score.status,
                'barn_count': score.barn_count,
                'critical_issues': len(score.critical_issues)
            })
        
        # Sort by score (descending)
        farm_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Calculate statistics
        scores = [f['score'] for f in farm_scores]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'farms': farm_scores,
            'statistics': {
                'average_score': avg_score,
                'highest_score': max(scores) if scores else 0,
                'lowest_score': min(scores) if scores else 0,
                'farms_with_issues': sum(1 for f in farm_scores if f['critical_issues'] > 0)
            },
            'timestamp': datetime.now().isoformat()
        }


def calculate_farm_health_score(data: Dict[str, Any]) -> float:
    """Convenience function to calculate farm health score."""
    scorer = FarmHealthScorer()
    return scorer.calculate_health_score(data)


def get_comprehensive_farm_health(data: Dict[str, Any]) -> FarmHealthScore:
    """Convenience function to get comprehensive farm health score."""
    scorer = FarmHealthScorer()
    return scorer.calculate_comprehensive_score(data)


if __name__ == "__main__":
    # Test the farm health scorer
    scorer = FarmHealthScorer()
    
    # Test data
    test_data = {
        'barn_ids': ['799', '800', '801'],
        'farm_name': 'Test Farm'
    }
    
    # Calculate comprehensive score
    health_score = scorer.calculate_comprehensive_score(test_data)
    
    print(f"Farm Health Assessment:")
    print(f"Overall Score: {health_score.overall_score:.1f}/100")
    print(f"Grade: {health_score.grade}")
    print(f"Status: {health_score.status}")
    print(f"Barn Count: {health_score.barn_count}")
    print(f"Critical Issues: {len(health_score.critical_issues)}")
    print(f"Metrics Analyzed: {len(health_score.metrics)}")
    
    if health_score.critical_issues:
        print("\nCritical Issues:")
        for issue in health_score.critical_issues[:5]:  # Show first 5
            print(f"  - {issue}")
    
    if health_score.recommendations:
        print("\nRecommendations:")
        for rec in health_score.recommendations[:5]:  # Show first 5
            print(f"  - {rec}")