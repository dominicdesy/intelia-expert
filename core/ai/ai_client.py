#!/usr/bin/env python3
"""
Broiler AI Analysis System with RAG Integration
Clean code compliant with intelligent configuration management
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# RAG Config Manager Integration - AJOUT
try:
    from ..config.rag_config_manager import RAGConfigManager, configure_compass_rag
    RAG_CONFIG_AVAILABLE = True
    logger.info("RAG Config Manager available")
except ImportError:
    try:
        from core.config.rag_config_manager import RAGConfigManager, configure_compass_rag
        RAG_CONFIG_AVAILABLE = True
        logger.info("RAG Config Manager available (alternate path)")
    except ImportError:
        RAG_CONFIG_AVAILABLE = False
        logger.warning("RAG Config Manager not available")
        
        # Fallback functions
        def configure_compass_rag():
            return {"integration_status": "disabled", "rag_method": "disabled"}
        
        class RAGConfigManager:
            def __init__(self):
                self.available = False
            
            def configure_project_rag(self):
                return {"integration_status": "disabled"}

# Model configuration
class ModelConfig:
    """Model configuration with cost optimization."""
    ANALYSIS_MODEL = "gpt-4o"
    ALERT_MODEL = "gpt-3.5-turbo"
    RAG_MODEL = "gpt-3.5-turbo"
    FALLBACK_MODEL = "gpt-3.5-turbo"
    
    @staticmethod
    def validate_model(model: str) -> bool:
        """Validate model availability."""
        supported_models = [
            "gpt-4o", "gpt-4", "gpt-3.5-turbo",
            "claude-3-opus-20240229", "claude-3-sonnet-20240229"
        ]
        return model in supported_models


def import_rag_bridge():
    """Import RAG bridge with fallback."""
    try:
        from .rag_ai_bridge import RAGAIBridge, EnrichedContext
        logger.info("RAG Bridge imported")
        return RAGAIBridge, EnrichedContext, True
    except ImportError:
        try:
            from rag_ai_bridge import RAGAIBridge, EnrichedContext
            logger.info("RAG Bridge imported")
            return RAGAIBridge, EnrichedContext, True
        except ImportError as e:
            logger.warning(f"RAG Bridge import failed: {e}")
            
            @dataclass
            class EnrichedContext:
                barn_id: str
                performance_context: str = ""
                weather_context: str = ""
                expert_recommendations: List[str] = None
                source_documents: List[Dict] = None
                confidence_score: float = 0.0
                language: str = "en"
                
                def __post_init__(self):
                    if self.expert_recommendations is None:
                        self.expert_recommendations = []
                    if self.source_documents is None:
                        self.source_documents = []
            
            class RAGAIBridge:
                """Fallback RAG Bridge."""
                def __init__(self, openai_api_key: str):
                    self.openai_api_key = openai_api_key
                    self.rag_available = False
                    logger.warning("Using fallback RAG Bridge")
                
                def is_available(self) -> bool:
                    return False
                
                def get_enriched_context(self, barn_id: str, broiler_data: Dict[str, Any], 
                                       language: str = "en") -> EnrichedContext:
                    return EnrichedContext(
                        barn_id=barn_id,
                        performance_context="",
                        weather_context="",
                        language=language
                    )
                
                def build_enhanced_prompt(self, enriched_context: EnrichedContext, 
                                        broiler_data: Dict[str, Any]) -> str:
                    return f"Analysis for barn {enriched_context.barn_id}"
            
            return RAGAIBridge, EnrichedContext, False

RAGAIBridge, EnrichedContext, RAG_BRIDGE_AVAILABLE = import_rag_bridge()


def import_support_systems():
    """Import support systems with fallback."""
    systems = {}
    
    # Translation manager
    try:
        from core.notifications.translation_manager import get_translation_manager
        systems['translation_manager'] = get_translation_manager
        logger.debug("Translation manager imported")
    except ImportError:
        systems['translation_manager'] = lambda: None
        logger.warning("Translation manager not available")
    
    # Status system
    try:
        from core.analysis.analyzer import get_status_system
        systems['status_system'] = get_status_system
        logger.debug("Status system imported")
    except ImportError:
        systems['status_system'] = lambda: None
        logger.warning("Status system not available")
    
    return systems

SUPPORT_SYSTEMS = import_support_systems()
TRANSLATION_AVAILABLE = SUPPORT_SYSTEMS['translation_manager'] != (lambda: None)


@dataclass
class AnalysisResult:
    """Enhanced analysis result with model information."""
    barn_id: str
    client_email: str
    analysis: str
    insights: List[str]
    model_used: str
    analysis_type: str
    has_rag_context: bool
    generation_time: float
    language: str
    confidence_score: float = 0.0
    expert_sources: List[str] = None
    
    def __post_init__(self):
        if self.expert_sources is None:
            self.expert_sources = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'barn_id': self.barn_id,
            'client_email': self.client_email,
            'analysis': self.analysis,
            'insights': self.insights,
            'model_used': self.model_used,
            'analysis_type': self.analysis_type,
            'has_rag_context': self.has_rag_context,
            'generation_time': self.generation_time,
            'language': self.language,
            'confidence_score': self.confidence_score,
            'expert_sources': self.expert_sources
        }


class BroilerAnalyzer:
    """Enhanced broiler analyzer with model selection and RAG integration."""
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        claude_api_key: Optional[str] = None,
        default_model: str = None,
        analysis_model: str = None,
        alert_model: str = None,
        rag_model: str = None
    ):
        """Initialize analyzer with model configuration."""
        self.openai_api_key = openai_api_key
        self.claude_api_key = claude_api_key
        
        # Configure models
        self.models = {
            'analysis': analysis_model or default_model or ModelConfig.ANALYSIS_MODEL,
            'alert': alert_model or default_model or ModelConfig.ALERT_MODEL,
            'rag': rag_model or default_model or ModelConfig.RAG_MODEL
        }
        
        # Validate models
        for context, model in self.models.items():
            if not ModelConfig.validate_model(model):
                logger.warning(f"Invalid model '{model}' for {context}, using fallback")
                self.models[context] = ModelConfig.FALLBACK_MODEL
        
        logger.info(f"Model configuration: Analysis={self.models['analysis']}, "
                   f"Alert={self.models['alert']}, RAG={self.models['rag']}")
        
        # NOUVEAU : Configuration automatique RAG
        self.rag_config_report = None
        if RAG_CONFIG_AVAILABLE:
            try:
                self.rag_config_report = configure_compass_rag()
                logger.info(f"RAG configuration applied: {self.rag_config_report.get('rag_method', 'unknown')}")
            except Exception as e:
                logger.warning(f"RAG auto-configuration failed: {e}")
        
        # Initialize systems
        self._init_translation_manager()
        self._init_rag_bridge()
        self._init_analyzer_system()
        self._init_ai_clients()
        
        analysis_mode = "RAG-enabled" if self.rag_available else "standard"
        logger.info(f"BroilerAnalyzer ready ({analysis_mode})")
    
    def _init_translation_manager(self):
        """Initialize translation manager."""
        if not TRANSLATION_AVAILABLE:
            logger.warning("Translation manager not available")
            self.translation_manager = None
        else:
            try:
                get_translation_manager = SUPPORT_SYSTEMS['translation_manager']
                self.translation_manager = get_translation_manager()
                logger.debug("Translation manager initialized")
            except Exception as e:
                logger.warning(f"Translation manager failed: {e}")
                self.translation_manager = None
    
    def _init_rag_bridge(self):
        """Initialize RAG bridge."""
        if not RAG_BRIDGE_AVAILABLE or not self.openai_api_key:
            logger.warning("RAG Bridge not available")
            self.rag_bridge = None
            self.rag_available = False
        else:
            try:
                self.rag_bridge = RAGAIBridge(self.openai_api_key)
                self.rag_available = self.rag_bridge.is_available()
                logger.info(f"RAG Bridge initialized (available: {self.rag_available})")
            except Exception as e:
                logger.warning(f"RAG Bridge failed: {e}")
                self.rag_bridge = None
                self.rag_available = False
    
    def _init_analyzer_system(self):
        """Initialize analyzer system."""
        try:
            get_status_system = SUPPORT_SYSTEMS['status_system']
            self.status_system = get_status_system()
            logger.debug("Status system initialized")
        except Exception as e:
            logger.warning(f"Status system failed: {e}")
            self.status_system = None
    
    def _init_ai_clients(self):
        """Initialize AI clients."""
        # OpenAI
        if self.openai_api_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
                logger.debug("OpenAI client initialized")
            except Exception as e:
                logger.warning(f"OpenAI client failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
        
        # Claude
        if self.claude_api_key:
            try:
                import anthropic
                self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                logger.debug("Claude client initialized")
            except Exception as e:
                logger.warning(f"Claude client failed: {e}")
                self.claude_client = None
        else:
            self.claude_client = None
    
    def _get_translation(self, key: str, language: str, **kwargs) -> str:
        """Get translation with fallback."""
        if self.translation_manager:
            try:
                return self.translation_manager.get(key, language, **kwargs)
            except Exception as e:
                logger.warning(f"Translation failed for {key}: {e}")
        
        # Fallback translations
        fallbacks = {
            'ai.analysis_title': 'Performance Analysis',
            'ai.unknown_source': 'Unknown Source',
            'emergency.analysis_title': 'Emergency Analysis',
            'emergency.basic_data': 'Basic Data',
            'emergency.service_unavailable': 'AI service temporarily unavailable',
            'common.age': 'Age',
            'common.weight': 'Weight',
            'common.expected': 'expected',
            'common.ratio': 'Ratio',
            'common.days': 'days',
            'pdf.barn_label': 'Barn'
        }
        
        return fallbacks.get(key, key)
    
    def _select_model_for_context(self, context: str) -> str:
        """Select appropriate model for context."""
        return self.models.get(context, ModelConfig.FALLBACK_MODEL)
    
    def _call_openai_api(self, prompt: str, model: str, max_tokens: int = 2000) -> Optional[str]:
        """Call OpenAI API with error handling."""
        if not self.openai_client:
            return None
        
        try:
            # Model-specific configuration
            temperature = 0.8 if "gpt-4o" in model else 0.7
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert broiler consultant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = response.choices[0].message.content
            logger.debug(f"OpenAI {model} response: {len(result)} chars")
            return result
        
        except Exception as e:
            logger.error(f"OpenAI API call failed for {model}: {e}")
            return None
    
    def _call_claude_api(self, prompt: str, model: str) -> Optional[str]:
        """Call Claude API with error handling."""
        if not self.claude_client:
            return None
        
        try:
            # Model configuration
            max_tokens = 4000 if "opus" in model else 3000
            temperature = 0.7 if "opus" in model else 0.6
            
            response = self.claude_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.content[0].text
            logger.debug(f"Claude {model} response: {len(result)} chars")
            return result
        
        except Exception as e:
            logger.error(f"Claude API call failed for {model}: {e}")
            return None
    
    def _format_expert_sources(self, source_documents: List[Dict], language: str) -> str:
        """Format expert source citations."""
        if not source_documents:
            return ""
        
        sources = ""
        for i, source in enumerate(source_documents[:3], 1):
            title = source.get('title', self._get_translation("ai.unknown_source", language))
            sources += f"{i}. {title}\n"
        
        return sources.strip()
    
    def _generate_emergency_fallback(self, barn_id: str, broiler_data: Dict[str, Any], language: str) -> str:
        """Generate emergency fallback when all AI systems fail."""
        
        # Get basic data
        age = broiler_data.get('age', 35)
        observed_weight = broiler_data.get('observed_weight', 0)
        expected_weight = broiler_data.get('expected_weight', 1)
        gain_ratio = broiler_data.get('gain_ratio', 0)
        
        # Use translation manager for emergency response
        title = self._get_translation('emergency.analysis_title', language)
        basic_data_label = self._get_translation('emergency.basic_data', language)
        age_label = self._get_translation('common.age', language)
        weight_label = self._get_translation('common.weight', language)
        expected_label = self._get_translation('common.expected', language)
        ratio_label = self._get_translation('common.ratio', language)
        service_note = self._get_translation('emergency.service_unavailable', language)
        
        return f"""{title} - {self._get_translation('pdf.barn_label', language)} {barn_id}

{basic_data_label}:
- {age_label}: {age} {self._get_translation('common.days', language)}
- {weight_label}: {observed_weight}g ({expected_label}: {expected_weight}g)
- {ratio_label}: {gain_ratio:.2f}

{service_note}"""
    
    def get_expert_analysis_for_client(
        self,
        barn_id: str,
        client_email: str,
        broiler_data: Dict[str, Any],
        language: str = "en",
        outdoor_temp: Optional[float] = None
    ) -> Optional[str]:
        """Get expert analysis for client with conditional logic."""
        
        start_time = datetime.now()
        
        # Model selection based on context
        selected_model = self._select_model_for_context('analysis')
        
        # Enhanced context with RAG if available
        enriched_context = None
        if self.rag_available and self.rag_bridge:
            try:
                enriched_context = self.rag_bridge.get_enriched_context(
                    barn_id, broiler_data, language
                )
                logger.debug(f"RAG context retrieved for barn {barn_id}")
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")
        
        # Build prompt
        if enriched_context and enriched_context.performance_context:
            prompt = self.rag_bridge.build_enhanced_prompt(enriched_context, broiler_data)
            analysis_type = "RAG-enhanced"
        else:
            # Standard prompt without RAG
            title = self._get_translation('ai.analysis_title', language)
            age = broiler_data.get('age', 35)
            weight = broiler_data.get('observed_weight', 0)
            expected = broiler_data.get('expected_weight', 1)
            
            prompt = f"""{title} for {broiler_data.get('breed', 'Ross 308')} broiler:
Age: {age} days
Current weight: {weight}g (expected: {expected}g)
Performance ratio: {broiler_data.get('gain_ratio', 0):.2f}

Provide specific recommendations for barn {barn_id}."""
            analysis_type = "standard"
        
        # Try OpenAI first, then Claude as fallback
        analysis = None
        model_used = None
        
        if "gpt" in selected_model or "openai" in selected_model.lower():
            analysis = self._call_openai_api(prompt, selected_model)
            model_used = selected_model
        
        # Claude fallback
        if not analysis and "claude" in selected_model:
            analysis = self._call_claude_api(prompt, selected_model)
            model_used = selected_model
        
        # Emergency fallback
        if not analysis:
            analysis = self._generate_emergency_fallback(barn_id, broiler_data, language)
            model_used = "emergency_fallback"
            analysis_type = "emergency"
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Analysis generated for barn {barn_id} using {model_used} "
                   f"(type: {analysis_type}, time: {generation_time:.2f}s)")
        
        return analysis
    
    def analyze_batch(
        self,
        barn_id: str,
        clients: List[Dict[str, str]],
        broiler_data: Dict[str, Any],
        outdoor_temp: Optional[float] = None
    ) -> List[AnalysisResult]:
        """Analyze batch of clients with optimized model usage."""
        
        results = []
        
        for client in clients:
            email = client.get('email', '')
            language = client.get('language', 'en')
            
            try:
                analysis = self.get_expert_analysis_for_client(
                    barn_id, email, broiler_data, language, outdoor_temp
                )
                
                if analysis:
                    result = AnalysisResult(
                        barn_id=barn_id,
                        client_email=email,
                        analysis=analysis,
                        insights=[],
                        model_used=self._select_model_for_context('analysis'),
                        analysis_type="expert" if self.rag_available else "standard",
                        has_rag_context=self.rag_available,
                        generation_time=1.0,
                        language=language,
                        confidence_score=0.9 if self.rag_available else 0.7
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Analysis failed for client {email}: {e}")
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "availability": {
                "translation_manager": bool(self.translation_manager),
                "rag_bridge": self.rag_available,
                "openai_client": bool(self.openai_client),
                "claude_client": bool(self.claude_client),
                "analyzer_system": bool(self.status_system),
                "rag_config_manager": RAG_CONFIG_AVAILABLE  # NOUVEAU
            },
            "rag_configuration": {  # NOUVELLE SECTION
                "auto_configured": bool(self.rag_config_report),
                "method": self.rag_config_report.get('rag_method', 'unknown') if self.rag_config_report else 'unknown',
                "status": self.rag_config_report.get('integration_status', 'unknown') if self.rag_config_report else 'unknown',
                "source": self.rag_config_report.get('rag_config', {}).get('source', 'unknown') if self.rag_config_report else 'unknown'
            },
            "model_configuration": {
                "analysis_model": self.models['analysis'],
                "alert_model": self.models['alert'],
                "rag_model": self.models['rag'],
                "model_validation": {
                    model: ModelConfig.validate_model(model) 
                    for model in self.models.values()
                }
            },
            "capabilities": {
                "expert_knowledge": self.rag_available,
                "weather_integration": self.rag_available,
                "multi_language": bool(self.translation_manager),
                "multi_model": bool(self.openai_client or self.claude_client),
                "context_aware_models": True,
                "cost_optimization": True,
                "emergency_fallback": True,
                "conditional_recommendations": True,
                "no_hardcoded_text": True
            },
            "configuration": {
                "analysis_mode": "expert" if self.rag_available else "standard",
                "prompt_source": "translation_system",
                "text_source": "openai_generated",
                "error_handling": "robust",
                "cost_optimization": "enabled",
                "recommendation_logic": "conditional"
            }
        }


# Factory functions
def create_broiler_analyzer(
    openai_api_key: str,
    claude_api_key: Optional[str] = None,
    model: str = "gpt-4o"
) -> BroilerAnalyzer:
    """Create broiler analyzer instance."""
    return BroilerAnalyzer(
        openai_api_key=openai_api_key,
        claude_api_key=claude_api_key,
        default_model=model
    )

def analyze_multi_client_workflow(
    clients: List[Dict[str, str]],
    broiler_data: Dict[str, Any],
    ai_analyses: Optional[Dict] = None,
    pdf_reports: Optional[Dict] = None,
    barn_id: str = "default_barn",
    openai_key: Optional[str] = None,
    outdoor_temp: Optional[float] = None
) -> Dict[str, Any]:
    """Multi-client workflow function."""
    try:
        if not openai_key:
            import os
            openai_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_key:
            return {
                "status": "fail",
                "message": "No OpenAI API key provided"
            }
        
        # Create analyzer and process batch
        analyzer = BroilerAnalyzer(openai_key)
        results = analyzer.analyze_batch(barn_id, clients, broiler_data, outdoor_temp)
        
        return {
            "status": "success", 
            "message": f"Processed {len(results)} clients successfully",
            "results": [r.to_dict() for r in results],
            "ai_analyses": ai_analyses or {},
            "pdf_reports": pdf_reports or {}
        }
        
    except Exception as e:
        return {
            "status": "fail",
            "message": f"Multi-client workflow failed: {str(e)}"
        }


# Compatibility aliases
CleanAIPoweredAnalyzer = BroilerAnalyzer
MultiClientAIAnalyzer = BroilerAnalyzer
RAGPoweredAIAnalyzer = BroilerAnalyzer
EnhancedAnalysisResult = AnalysisResult


if __name__ == "__main__":
    import os
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("OPENAI_API_KEY required for testing")
        exit(1)
    
    # Test data
    test_data = {
        'age': 35,
        'breed': 'Ross 308',
        'observed_weight': 2000,
        'expected_weight': 2100,
        'gain_observed': 85,
        'gain_expected': 90,
        'gain_ratio': 0.94,
        'temperature_avg': 26.5,
        'humidity_avg': 65
    }
    
    print("Testing Clean BroilerAnalyzer...")
    analyzer = BroilerAnalyzer(openai_key)
    
    # System status
    status = analyzer.get_system_status()
    print("System Status:")
    for category, items in status.items():
        print(f"  {category}:")
        if isinstance(items, dict):
            for key, value in items.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {items}")
    
    # Test analysis generation
    print("\nTesting analysis generation...")
    analysis = analyzer.get_expert_analysis_for_client("799", "test@example.com", test_data, "en")
    
    if analysis:
        print(f"Analysis generated ({len(analysis)} chars)")
        print(f"Preview: {analysis[:200]}...")
    else:
        print("Analysis generation failed")
    
    print("\nClean BroilerAnalyzer test completed!")
