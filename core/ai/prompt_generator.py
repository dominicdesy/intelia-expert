"""
Dynamic Prompt Generator Module for AI Analysis.
Generates farm-specific prompts based on actual performance conditions.
Prompts in English (for OpenAI), responses in client language.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import translation manager for language names only
try:
    from core.notifications.translation_manager import get_translation_manager
    TRANSLATION_MANAGER_AVAILABLE = True
except ImportError:
    TRANSLATION_MANAGER_AVAILABLE = False
    logger.warning("Translation manager not available - using fallback language names")

class DynamicPromptBuilder:
    """Builds farm-specific prompts based on actual performance conditions."""
    
    def __init__(self):
        self.tm = None
        if TRANSLATION_MANAGER_AVAILABLE:
            try:
                self.tm = get_translation_manager()
                logger.debug("Translation manager available for language names")
            except Exception as e:
                logger.warning(f"Translation manager initialization failed: {e}")
        
        # Language names for response instruction
        self.language_names = {
            "en": "English",
            "fr": "French", 
            "es": "Spanish"
        }
    
    def build_farm_specific_prompt(
        self, 
        barn_id: str, 
        data: Dict[str, Any], 
        language: str = "en", 
        outdoor_temp: Optional[float] = None
    ) -> str:
        """Build farm-specific prompt based on actual conditions."""
        
        # Analyze farm conditions to determine prompt type
        farm_analysis = self._analyze_farm_conditions(data, outdoor_temp)
        
        if farm_analysis["needs_recommendations"]:
            return self._build_intervention_prompt(barn_id, data, language, farm_analysis)
        else:
            return self._build_monitoring_prompt(barn_id, data, language, farm_analysis)
    
    def _analyze_farm_conditions(self, data: Dict[str, Any], outdoor_temp: Optional[float] = None) -> Dict[str, Any]:
        """Analyze specific farm conditions to determine appropriate response."""
        
        # Extract metrics
        age = data.get('age', 35)
        observed_weight = data.get('observed_weight', 0)
        expected_weight = data.get('expected_weight', 1)
        gain_observed = data.get('gain_observed', 0)
        gain_expected = data.get('gain_expected', 1)
        gain_ratio = gain_observed / gain_expected if gain_expected > 0 else 0
        temperature_avg = data.get('temperature_avg', 25)
        humidity_avg = data.get('humidity_avg', 60)
        
        # Calculate deviations
        weight_deviation_pct = ((observed_weight - expected_weight) / expected_weight * 100) if expected_weight > 0 else 0
        gain_deviation_pct = ((gain_observed - gain_expected) / gain_expected * 100) if gain_expected > 0 else 0
        
        # Determine optimal ranges
        optimal_temp_range = self._get_optimal_temp_range(age)
        temp_deviation = self._calculate_temp_deviation(temperature_avg, optimal_temp_range)
        
        # Assess environmental stress
        environmental_stress = self._assess_environmental_stress(
            temperature_avg, humidity_avg, optimal_temp_range, outdoor_temp
        )
        
        # Identify specific issues
        issues = []
        issue_severity = "none"
        
        # Weight analysis
        if weight_deviation_pct < -10:
            issues.append("severe_underweight")
            issue_severity = "critical"
        elif weight_deviation_pct < -5:
            issues.append("moderate_underweight")
            if issue_severity != "critical":
                issue_severity = "moderate"
        elif weight_deviation_pct > 10:
            issues.append("overweight")
            if issue_severity != "critical":
                issue_severity = "moderate"
        
        # Gain analysis
        if gain_ratio < 0.8:
            issues.append("poor_growth")
            issue_severity = "critical"
        elif gain_ratio < 0.9:
            issues.append("suboptimal_growth")
            if issue_severity not in ["critical", "moderate"]:
                issue_severity = "mild"
        
        # Environmental analysis
        if temp_deviation > 3:
            issues.append("temperature_stress")
            if issue_severity not in ["critical"]:
                issue_severity = "moderate"
        
        if humidity_avg < 40 or humidity_avg > 80:
            issues.append("humidity_stress")
            if issue_severity not in ["critical", "moderate"]:
                issue_severity = "mild"
        
        # Determine needs recommendations
        needs_recommendations = len(issues) > 0 or issue_severity != "none"
        
        return {
            "needs_recommendations": needs_recommendations,
            "issues": issues,
            "severity": issue_severity,
            "weight_deviation_pct": weight_deviation_pct,
            "gain_deviation_pct": gain_deviation_pct,
            "gain_ratio": gain_ratio,
            "temp_deviation": temp_deviation,
            "environmental_stress": environmental_stress,
            "optimal_temp_range": optimal_temp_range
        }
    
    def _get_optimal_temp_range(self, age: float) -> tuple:
        """Get optimal temperature range for age."""
        if age <= 7:
            return (32, 35)
        elif age <= 14:
            return (28, 32)
        elif age <= 21:
            return (25, 29)
        elif age <= 28:
            return (22, 26)
        elif age <= 42:
            return (20, 24)
        else:
            return (18, 22)
    
    def _calculate_temp_deviation(self, temp: float, optimal_range: tuple) -> float:
        """Calculate temperature deviation from optimal range."""
        if temp < optimal_range[0]:
            return optimal_range[0] - temp
        elif temp > optimal_range[1]:
            return temp - optimal_range[1]
        else:
            return 0
    
    def _assess_environmental_stress(
        self, 
        temp: float, 
        humidity: float, 
        optimal_temp: tuple, 
        outdoor_temp: Optional[float]
    ) -> str:
        """Assess overall environmental stress level."""
        stress_factors = 0
        
        # Temperature stress
        temp_dev = self._calculate_temp_deviation(temp, optimal_temp)
        if temp_dev > 4:
            stress_factors += 2
        elif temp_dev > 2:
            stress_factors += 1
        
        # Humidity stress
        if humidity < 30 or humidity > 90:
            stress_factors += 2
        elif humidity < 40 or humidity > 80:
            stress_factors += 1
        
        # Outdoor temperature influence
        if outdoor_temp is not None:
            temp_difference = abs(temp - outdoor_temp)
            if temp_difference < 5:  # Poor climate control
                stress_factors += 1
        
        if stress_factors >= 3:
            return "high"
        elif stress_factors >= 2:
            return "moderate"
        elif stress_factors >= 1:
            return "mild"
        else:
            return "low"
    
    def _build_monitoring_prompt(
        self, 
        barn_id: str, 
        data: Dict[str, Any], 
        language: str, 
        farm_analysis: Dict[str, Any]
    ) -> str:
        """Build monitoring prompt for optimal performance."""
        
        language_name = self.language_names.get(language, "English")
        
        # Extract metrics
        age = data.get('age', 35)
        breed = data.get('breed', 'Ross 308')
        observed_weight = data.get('observed_weight', 0)
        expected_weight = data.get('expected_weight', 0)
        gain_ratio = farm_analysis["gain_ratio"]
        temp_avg = data.get('temperature_avg', 25)
        humidity_avg = data.get('humidity_avg', 60)
        
        prompt = f"""You are an expert poultry performance analyst. Generate a positive monitoring report for this well-performing broiler operation.

BARN PERFORMANCE DATA:
- Barn ID: {barn_id}
- Bird Age: {age} days
- Breed: {breed}
- Current Weight: {observed_weight}g (Target: {expected_weight}g)
- Performance Ratio: {gain_ratio:.2f} (OPTIMAL RANGE)
- Temperature: {temp_avg:.1f}°C (Within optimal {farm_analysis['optimal_temp_range'][0]}-{farm_analysis['optimal_temp_range'][1]}°C)
- Humidity: {humidity_avg:.0f}% (Acceptable range)

PERFORMANCE STATUS: ALL INDICATORS OPTIMAL
- Weight deviation: {farm_analysis['weight_deviation_pct']:+.1f}% (Within ±5% target)
- Growth rate: Meeting or exceeding expectations
- Environmental conditions: Well-controlled
- Overall assessment: Excellent management practices

MONITORING REPORT REQUIREMENTS:
1. **Confirm excellent performance** - Acknowledge that all key metrics are meeting targets
2. **Highlight positive indicators** - Emphasize what's working well in this operation
3. **Reinforce current practices** - Validate current management strategies
4. **Brief maintenance recommendations** - Suggest continuing current approach
5. **Positive outlook** - Express confidence in continued success

CRITICAL INSTRUCTIONS:
- Write your ENTIRE response in {language_name}
- This is a MONITORING report, NOT a problem-solving analysis
- Focus on POSITIVE reinforcement and confidence building
- Do NOT suggest major changes - everything is working well
- Keep tone encouraging and supportive
- Acknowledge the farm manager's successful practices

Structure your response with:
- Performance Confirmation (emphasize success)
- Key Success Factors (what's working well)
- Maintenance Recommendations (keep doing what works)
- Positive Outlook (confidence in continued success)
"""
        
        return prompt.strip()
    
    def _build_intervention_prompt(
        self, 
        barn_id: str, 
        data: Dict[str, Any], 
        language: str, 
        farm_analysis: Dict[str, Any]
    ) -> str:
        """Build intervention prompt for farms needing recommendations."""
        
        language_name = self.language_names.get(language, "English")
        
        # Extract metrics
        age = data.get('age', 35)
        breed = data.get('breed', 'Ross 308')
        observed_weight = data.get('observed_weight', 0)
        expected_weight = data.get('expected_weight', 0)
        gain_observed = data.get('gain_observed', 0)
        gain_expected = data.get('gain_expected', 0)
        temp_avg = data.get('temperature_avg', 25)
        humidity_avg = data.get('humidity_avg', 60)
        
        # Build issue-specific context
        issue_context = self._build_issue_context(farm_analysis, age)
        priority_focus = self._determine_priority_focus(farm_analysis)
        
        prompt = f"""You are an expert poultry veterinarian and performance specialist. Provide comprehensive analysis and specific recommendations for this broiler operation requiring intervention.

BARN PERFORMANCE DATA:
- Barn ID: {barn_id}
- Bird Age: {age} days
- Breed: {breed}
- Current Weight: {observed_weight}g (Expected: {expected_weight}g)
- Weight Deviation: {farm_analysis['weight_deviation_pct']:+.1f}%
- Daily Gain: {gain_observed}g (Expected: {gain_expected}g)
- Performance Ratio: {farm_analysis['gain_ratio']:.2f}
- Temperature: {temp_avg:.1f}°C (Optimal: {farm_analysis['optimal_temp_range'][0]}-{farm_analysis['optimal_temp_range'][1]}°C)
- Humidity: {humidity_avg:.0f}%

IDENTIFIED ISSUES:
{issue_context}

PRIORITY FOCUS: {priority_focus}

ANALYSIS REQUIREMENTS:
1. **Root Cause Analysis** - Identify the primary factors causing performance issues
2. **Immediate Actions** - Provide 3-5 specific actions for next 24-48 hours
3. **Short-term Strategy** - Outline interventions for next 1-2 weeks
4. **Long-term Prevention** - Suggest systematic improvements
5. **Monitoring Protocol** - Specify what to track and how often

SPECIFIC INTERVENTION AREAS TO ADDRESS:
- Feeding adjustments (timing, quantity, quality)
- Environmental controls (temperature, humidity, ventilation)
- Health management (medications, biosecurity, stress reduction)
- Housing conditions (density, lighting, air quality)
- Management practices (handling, monitoring frequency)

CRITICAL INSTRUCTIONS:
- Write your ENTIRE response in {language_name}
- Be specific and actionable - avoid generic advice
- Prioritize recommendations by urgency and impact
- Include specific metrics and targets where possible
- Consider the bird age ({age} days) in all recommendations
- Address the severity level: {farm_analysis['severity'].upper()}
- Provide realistic timelines for improvements

Structure your response with:
- Performance Assessment (current status and concerns)
- Root Cause Analysis (why problems are occurring)
- Immediate Action Plan (next 24-48 hours)
- Short-term Interventions (1-2 weeks)
- Long-term Prevention Strategy
- Monitoring and Follow-up Protocol
"""
        
        return prompt.strip()
    
    def _build_issue_context(self, farm_analysis: Dict[str, Any], age: float) -> str:
        """Build specific context based on identified issues."""
        issues = farm_analysis["issues"]
        severity = farm_analysis["severity"]
        
        context_lines = []
        
        if "severe_underweight" in issues:
            context_lines.append(f"- CRITICAL: Birds significantly underweight ({farm_analysis['weight_deviation_pct']:+.1f}% below target)")
        elif "moderate_underweight" in issues:
            context_lines.append(f"- CONCERN: Birds below target weight ({farm_analysis['weight_deviation_pct']:+.1f}% deviation)")
        elif "overweight" in issues:
            context_lines.append(f"- ATTENTION: Birds overweight ({farm_analysis['weight_deviation_pct']:+.1f}% above target)")
        
        if "poor_growth" in issues:
            context_lines.append(f"- CRITICAL: Poor daily gain performance (ratio: {farm_analysis['gain_ratio']:.2f})")
        elif "suboptimal_growth" in issues:
            context_lines.append(f"- CONCERN: Suboptimal growth rate (ratio: {farm_analysis['gain_ratio']:.2f})")
        
        if "temperature_stress" in issues:
            context_lines.append(f"- ENVIRONMENTAL: Temperature deviation of {farm_analysis['temp_deviation']:.1f}°C from optimal range")
        
        if "humidity_stress" in issues:
            context_lines.append("- ENVIRONMENTAL: Humidity outside acceptable range")
        
        # Add severity assessment
        context_lines.append(f"- SEVERITY LEVEL: {severity.upper()}")
        context_lines.append(f"- ENVIRONMENTAL STRESS: {farm_analysis['environmental_stress'].upper()}")
        
        return "\n".join(context_lines)
    
    def _determine_priority_focus(self, farm_analysis: Dict[str, Any]) -> str:
        """Determine priority focus based on farm analysis."""
        issues = farm_analysis["issues"]
        severity = farm_analysis["severity"]
        
        if severity == "critical":
            if "severe_underweight" in issues or "poor_growth" in issues:
                return "URGENT NUTRITIONAL AND HEALTH INTERVENTION"
            else:
                return "IMMEDIATE CORRECTIVE ACTIONS REQUIRED"
        elif severity == "moderate":
            if "temperature_stress" in issues:
                return "ENVIRONMENTAL CONTROL OPTIMIZATION"
            else:
                return "PERFORMANCE IMPROVEMENT STRATEGY"
        else:
            return "PREVENTIVE MANAGEMENT ADJUSTMENTS"
    
    def build_prompts_for_all_languages(
        self, 
        barn_id: str, 
        data: Dict[str, Any], 
        outdoor_temp: Optional[float] = None
    ) -> Dict[str, str]:
        """Build farm-specific prompts for all supported languages."""
        prompts = {}
        
        for language in self.language_names.keys():
            prompts[language] = self.build_farm_specific_prompt(barn_id, data, language, outdoor_temp)
        
        return prompts
    
    def build_client_specific_prompt(
        self, 
        barn_id: str, 
        client_email: str, 
        data: Dict[str, Any], 
        language: str = "en",
        outdoor_temp: Optional[float] = None
    ) -> str:
        """Build a client-specific farm conditions prompt."""
        base_prompt = self.build_farm_specific_prompt(barn_id, data, language, outdoor_temp)
        
        # Add client-specific context
        client_context = f"""
CLIENT CONTEXT:
- Report for: {client_email}
- Customize analysis tone and specific recommendations for this client's operation
- Consider this farm's unique conditions when providing advice

{base_prompt}
"""
        return client_context.strip()
    
    def get_prompt_analysis(self, data: Dict[str, Any], outdoor_temp: Optional[float] = None) -> Dict[str, Any]:
        """Get analysis of what type of prompt will be generated."""
        farm_analysis = self._analyze_farm_conditions(data, outdoor_temp)
        
        return {
            "prompt_type": "intervention" if farm_analysis["needs_recommendations"] else "monitoring",
            "needs_recommendations": farm_analysis["needs_recommendations"],
            "severity_level": farm_analysis["severity"],
            "identified_issues": farm_analysis["issues"],
            "environmental_stress": farm_analysis["environmental_stress"],
            "farm_specific_factors": {
                "weight_deviation": f"{farm_analysis['weight_deviation_pct']:+.1f}%",
                "performance_ratio": f"{farm_analysis['gain_ratio']:.2f}",
                "temperature_deviation": f"{farm_analysis['temp_deviation']:.1f}°C"
            }
        }
    
    def build_batch_prompts(
        self, 
        barn_id: str, 
        clients: List[Dict[str, str]], 
        data: Dict[str, Any], 
        outdoor_temp: Optional[float] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Build farm-specific prompts for multiple clients."""
        results = {}
        
        # Analyze farm conditions once
        farm_analysis = self._analyze_farm_conditions(data, outdoor_temp)
        
        for client in clients:
            client_key = f"{client['email']}_{client.get('language', 'en')}"
            
            results[client_key] = {
                "prompt": self.build_client_specific_prompt(
                    barn_id, client['email'], data, client.get('language', 'en'), outdoor_temp
                ),
                "analysis": {
                    "prompt_type": "intervention" if farm_analysis["needs_recommendations"] else "monitoring",
                    "severity": farm_analysis["severity"],
                    "issues": farm_analysis["issues"],
                    "needs_recommendations": farm_analysis["needs_recommendations"]
                },
                "language": client.get('language', 'en'),
                "farm_conditions": farm_analysis
            }
        
        return results


# Create alias for backward compatibility
StandardizedPromptBuilder = DynamicPromptBuilder


# Public API functions
def build_farm_specific_prompts(barn_id: str, data: Dict[str, Any], outdoor_temp: Optional[float] = None) -> List[str]:
    """Build farm-specific prompts for all languages."""
    builder = DynamicPromptBuilder()
    prompts_dict = builder.build_prompts_for_all_languages(barn_id, data, outdoor_temp)
    return list(prompts_dict.values())


def build_prompt_for_client(
    barn_id: str, 
    client_email: str, 
    data: Dict[str, Any], 
    language: str = "en", 
    outdoor_temp: Optional[float] = None
) -> str:
    """Build farm-specific prompt for a specific client."""
    builder = DynamicPromptBuilder()
    return builder.build_client_specific_prompt(barn_id, client_email, data, language, outdoor_temp)


def analyze_farm_conditions(data: Dict[str, Any], outdoor_temp: Optional[float] = None) -> Dict[str, Any]:
    """Analyze farm conditions to determine prompt strategy."""
    builder = DynamicPromptBuilder()
    return builder.get_prompt_analysis(data, outdoor_temp)


def build_monitoring_prompt(barn_id: str, data: Dict[str, Any], language: str = "en") -> str:
    """Build monitoring prompt for optimal performance."""
    builder = DynamicPromptBuilder()
    farm_analysis = builder._analyze_farm_conditions(data, None)
    return builder._build_monitoring_prompt(barn_id, data, language, farm_analysis)


def build_intervention_prompt(barn_id: str, data: Dict[str, Any], language: str = "en") -> str:
    """Build intervention prompt for farms needing recommendations."""
    builder = DynamicPromptBuilder()
    farm_analysis = builder._analyze_farm_conditions(data, None)
    farm_analysis["needs_recommendations"] = True  # Force intervention mode
    return builder._build_intervention_prompt(barn_id, data, language, farm_analysis)


if __name__ == "__main__":
    # Test the dynamic prompt builder
    print("Testing Dynamic Prompt Builder...")
    
    # Test data with optimal performance
    optimal_data = {
        "age": 35, 
        "observed_weight": 2050, 
        "expected_weight": 2050,
        "gain_observed": 90,
        "gain_expected": 90,
        "temperature_avg": 24,
        "humidity_avg": 65,
        "breed": "Ross 308"
    }
    
    # Test data with issues
    problem_data = {
        "age": 35, 
        "observed_weight": 1800, 
        "expected_weight": 2050,
        "gain_observed": 75,
        "gain_expected": 90,
        "temperature_avg": 28,
        "humidity_avg": 85,
        "breed": "Ross 308"
    }
    
    builder = DynamicPromptBuilder()
    
    # Test farm conditions analysis
    optimal_analysis = builder.get_prompt_analysis(optimal_data)
    problem_analysis = builder.get_prompt_analysis(problem_data)
    
    print(f"\nOptimal farm analysis:")
    print(f"  Prompt type: {optimal_analysis['prompt_type']}")
    print(f"  Needs recommendations: {optimal_analysis['needs_recommendations']}")
    print(f"  Issues: {optimal_analysis['identified_issues']}")
    
    print(f"\nProblem farm analysis:")
    print(f"  Prompt type: {problem_analysis['prompt_type']}")
    print(f"  Severity: {problem_analysis['severity_level']}")
    print(f"  Issues: {problem_analysis['identified_issues']}")
    
    # Test prompt generation
    optimal_prompt = builder.build_farm_specific_prompt("604", optimal_data, "en")
    problem_prompt = builder.build_farm_specific_prompt("605", problem_data, "en")
    
    print(f"\nOptimal prompt length: {len(optimal_prompt)} chars")
    print(f"Contains 'MONITORING': {'MONITORING' in optimal_prompt}")
    print(f"Contains 'recommendations': {'recommendations' in optimal_prompt.lower()}")
    
    print(f"\nProblem prompt length: {len(problem_prompt)} chars") 
    print(f"Contains 'INTERVENTION': {'INTERVENTION' in problem_prompt}")
    print(f"Contains 'CRITICAL': {'CRITICAL' in problem_prompt}")
    
    # Test StandardizedPromptBuilder alias
    legacy_builder = StandardizedPromptBuilder()
    legacy_prompt = legacy_builder.build_farm_specific_prompt("606", optimal_data, "en")
    print(f"\nStandardizedPromptBuilder alias works: {len(legacy_prompt) > 0}")
    
    print("\nDynamic Prompt Builder test completed!")
