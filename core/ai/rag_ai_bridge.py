"""
RAG-AI Integration Bridge with Virtual Barn Support
Clean code compliant version with proper error handling
"""

import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# Virtual barn IDs that don't require weather data
VIRTUAL_BARN_IDS = ["expert_query", "default_barn", "virtual_barn", "test_barn"]

# Import RAG system with fallback handling
try:
    rag_path = Path("rag").absolute()
    if rag_path.exists() and str(rag_path) not in sys.path:
        sys.path.insert(0, str(rag_path))
    
    parsers_path = Path("parsers").absolute()
    if parsers_path.exists() and str(parsers_path) not in sys.path:
        sys.path.insert(0, str(parsers_path))
    
    from retriever import ContextualRetriever
    RAG_AVAILABLE = True
    logging.info("RAG Retriever imported successfully")
except ImportError as e:
    RAG_AVAILABLE = False
    logging.warning(f"RAG retriever not available: {e}")
    
    class ContextualRetriever:
        def __init__(self, *args, **kwargs):
            self.available = False
        
        def is_available(self):
            return False
        
        def get_contextual_diagnosis(self, query):
            return None

# Import existing systems with corrected paths
try:
    from .weather_integration import get_weather_analysis_for_barn
except ImportError:
    try:
        from weather_integration import get_weather_analysis_for_barn
    except ImportError:
        try:
            from core.data.weather_integration import get_weather_analysis_for_barn
        except ImportError:
            def get_weather_analysis_for_barn(barn_id, age, language):
                # Handle virtual barns
                if barn_id in VIRTUAL_BARN_IDS:
                    return None
                return None

try:
    from .barn_list_parser import get_clients_for_barn
except ImportError:
    try:
        from barn_list_parser import get_clients_for_barn
    except ImportError:
        try:
            from core.data.barn_list_parser import get_clients_for_barn
        except ImportError:
            def get_clients_for_barn(barn_id):
                return []

try:
    from core.notifications.translation_manager import get_translation_manager
except ImportError:
    try:
        from ..notifications.translation_manager import get_translation_manager
    except ImportError:
        try:
            from notifications.translation_manager import get_translation_manager
        except ImportError:
            def get_translation_manager():
                logging.warning("Translation manager not available in rag_ai_bridge")
                return None

logger = logging.getLogger(__name__)


@dataclass
class EnrichedContext:
    """Enriched context with RAG and weather data for AI analysis."""
    barn_id: str
    performance_context: str
    weather_context: str
    expert_recommendations: List[str]
    source_documents: List[Dict[str, Any]]
    confidence_score: float
    language: str


@dataclass
class RAGSearchQuery:
    """Optimized query for RAG search operations."""
    query: str
    barn_type: str
    breed: str
    age: int
    language: str
    search_type: str = "performance"
    max_results: int = 5


class RAGAIBridge:
    """Bridge between RAG system and AI analysis with virtual barn support."""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.rag_available = False
        self.rag_retriever = None
        
        # Initialize RAG retriever if available
        if RAG_AVAILABLE and openai_api_key:
            try:
                import inspect
                sig = inspect.signature(ContextualRetriever.__init__)
                params = list(sig.parameters.keys())
                
                if len(params) > 1:
                    self.rag_retriever = ContextualRetriever(openai_api_key)
                else:
                    self.rag_retriever = ContextualRetriever()
                
                if hasattr(self.rag_retriever, 'is_available'):
                    self.rag_available = self.rag_retriever.is_available()
                else:
                    self.rag_available = True
                
                logger.info(f"RAG Bridge initialized (available: {self.rag_available})")
                
            except Exception as e:
                logger.error(f"Failed to initialize RAG retriever: {e}")
                self.rag_available = False
        else:
            logger.warning("RAG Bridge initialized without retriever")
    
    def is_available(self) -> bool:
        """Check if RAG bridge is available."""
        return self.rag_available
    
    def set_retriever(self, retriever: Optional[ContextualRetriever] = None):
        """Configure or force specific retriever."""
        if retriever:
            self.rag_retriever = retriever
            if hasattr(retriever, 'is_available'):
                self.rag_available = retriever.is_available()
            else:
                self.rag_available = True
            logger.info("RAG Retriever manually configured")
        elif RAG_AVAILABLE and self.openai_api_key:
            try:
                import inspect
                sig = inspect.signature(ContextualRetriever.__init__)
                params = list(sig.parameters.keys())
                
                if len(params) > 1:
                    self.rag_retriever = ContextualRetriever(self.openai_api_key)
                else:
                    self.rag_retriever = ContextualRetriever()
                
                if hasattr(self.rag_retriever, 'is_available'):
                    self.rag_available = self.rag_retriever.is_available()
                else:
                    self.rag_available = True
                logger.info("RAG Retriever auto-configured")
            except Exception as e:
                logger.error(f"Failed to auto-configure retriever: {e}")
                self.rag_available = False
    
    def get_enriched_context(self, barn_id: str, broiler_data: Dict[str, Any], 
                           language: str = "en") -> EnrichedContext:
        """Get enriched context combining RAG knowledge and weather data with virtual barn support."""
        
        # Initialize default context
        enriched_context = EnrichedContext(
            barn_id=barn_id,
            performance_context="",
            weather_context="",
            expert_recommendations=[],
            source_documents=[],
            confidence_score=0.5,
            language=language
        )
        
        try:
            # Get RAG context if available
            if self.rag_available and self.rag_retriever:
                performance_context, source_docs = self._get_rag_context(broiler_data, language)
                enriched_context.performance_context = performance_context
                enriched_context.source_documents = source_docs
                enriched_context.confidence_score = 0.8 if performance_context else 0.5
            
            # Get weather context - skip for virtual barns
            if barn_id not in VIRTUAL_BARN_IDS:
                weather_context = self._get_weather_context(barn_id, broiler_data, language)
                enriched_context.weather_context = weather_context
            else:
                logger.debug(f"Skipping weather context for virtual barn: {barn_id}")
                enriched_context.weather_context = ""
            
            # Generate expert recommendations
            enriched_context.expert_recommendations = self._generate_expert_recommendations(
                enriched_context, broiler_data, language
            )
            
            logger.debug(f"Enriched context generated for barn {barn_id}")
            
        except Exception as e:
            logger.error(f"Failed to build enriched context for barn {barn_id}: {e}")
        
        return enriched_context
    
    def _get_rag_context(self, broiler_data: Dict[str, Any], language: str) -> tuple:
        """Get RAG context from knowledge base."""
        if not self.rag_available or not self.rag_retriever:
            return "", []
        
        try:
            # Build search query based on broiler data
            age = broiler_data.get('age', 35)
            breed = broiler_data.get('breed', 'Ross 308')
            query_text = broiler_data.get('query', '')
            
            # Construct search query
            if query_text:
                search_query = f"{query_text} {breed} {age} days"
            else:
                search_query = f"{breed} performance management {age} days optimal conditions"
            
            # Search RAG system
            result = self.rag_retriever.get_contextual_diagnosis(search_query)
            
            if result:
                performance_context = result.get('answer', '')
                source_documents = result.get('source_documents', [])
                
                logger.debug(f"RAG context retrieved: {len(performance_context)} chars, {len(source_documents)} sources")
                return performance_context, source_documents
            
        except Exception as e:
            logger.error(f"RAG context retrieval failed: {e}")
        
        return "", []
    
    def _get_weather_context(self, barn_id: str, broiler_data: Dict[str, Any], language: str) -> str:
        """Get weather context for barn - returns empty string for virtual barns."""
        
        # Skip weather for virtual barns
        if barn_id in VIRTUAL_BARN_IDS:
            return ""
        
        # Check if weather is disabled
        if os.environ.get("DISABLE_WEATHER_FOR_EXPERT") == "true":
            return ""
        
        try:
            age = broiler_data.get('age', 35)
            weather_analysis = get_weather_analysis_for_barn(barn_id, age, language)
            
            if weather_analysis:
                weather_data = weather_analysis.get('weather_data', {})
                impact_score = weather_analysis.get('impact_score', 50)
                
                weather_context = f"""
Weather conditions for analysis:
- Temperature: {weather_data.get('temperature', 'N/A')}°C
- Humidity: {weather_data.get('humidity', 'N/A')}%
- Condition: {weather_data.get('condition', 'N/A')}
- Impact score: {impact_score}/100
"""
                logger.debug(f"Weather context retrieved for barn {barn_id}")
                return weather_context.strip()
                
        except Exception as e:
            logger.warning(f"Weather context retrieval failed for barn {barn_id}: {e}")
        
        return ""
    
    def _generate_expert_recommendations(self, context: EnrichedContext, 
                                       broiler_data: Dict[str, Any], language: str) -> List[str]:
        """Generate expert recommendations based on context."""
        recommendations = []
        
        try:
            # Basic recommendations based on age
            age = broiler_data.get('age', 35)
            
            if language == "fr":
                if age < 14:
                    recommendations.append("Surveillance accrue de la température pour les jeunes poussins")
                elif age < 28:
                    recommendations.append("Optimisation de l'alimentation pour la croissance")
                else:
                    recommendations.append("Préparation pour la phase de finition")
            else:
                if age < 14:
                    recommendations.append("Enhanced temperature monitoring for young chicks")
                elif age < 28:
                    recommendations.append("Optimize feeding for growth phase")
                else:
                    recommendations.append("Prepare for finishing phase")
            
            # Add recommendations based on performance context
            if context.performance_context:
                if "ventilation" in context.performance_context.lower():
                    if language == "fr":
                        recommendations.append("Vérifier le système de ventilation")
                    else:
                        recommendations.append("Check ventilation system")
            
            # Add weather-based recommendations
            if context.weather_context and "high temperature" in context.weather_context.lower():
                if language == "fr":
                    recommendations.append("Augmenter la ventilation en raison des températures élevées")
                else:
                    recommendations.append("Increase ventilation due to high temperatures")
            
        except Exception as e:
            logger.error(f"Expert recommendations generation failed: {e}")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def build_enhanced_prompt(self, enriched_context: EnrichedContext, 
                            broiler_data: Dict[str, Any]) -> str:
        """Build enhanced prompt with RAG context and weather data."""
        
        try:
            age = broiler_data.get('age', 35)
            breed = broiler_data.get('breed', 'Ross 308')
            query = broiler_data.get('query', '')
            
            # Base prompt
            if enriched_context.language == "fr":
                prompt = f"""Analyse experte pour poulets {breed} de {age} jours.

Question: {query}

"""
            else:
                prompt = f"""Expert analysis for {breed} broilers at {age} days.

Query: {query}

"""
            
            # Add RAG context if available
            if enriched_context.performance_context:
                if enriched_context.language == "fr":
                    prompt += f"""CONTEXTE EXPERT:
{enriched_context.performance_context}

"""
                else:
                    prompt += f"""EXPERT CONTEXT:
{enriched_context.performance_context}

"""
            
            # Add weather context if available and not virtual barn
            if enriched_context.weather_context and enriched_context.barn_id not in VIRTUAL_BARN_IDS:
                if enriched_context.language == "fr":
                    prompt += f"""CONDITIONS MÉTÉOROLOGIQUES:
{enriched_context.weather_context}

"""
                else:
                    prompt += f"""WEATHER CONDITIONS:
{enriched_context.weather_context}

"""
            
            # Add expert recommendations
            if enriched_context.expert_recommendations:
                if enriched_context.language == "fr":
                    prompt += f"""RECOMMANDATIONS PRÉLIMINAIRES:
"""
                else:
                    prompt += f"""PRELIMINARY RECOMMENDATIONS:
"""
                
                for i, rec in enumerate(enriched_context.expert_recommendations, 1):
                    prompt += f"{i}. {rec}\n"
                
                prompt += "\n"
            
            # Final instruction
            if enriched_context.language == "fr":
                prompt += "Fournissez une analyse détaillée et des recommandations pratiques basées sur ces informations."
            else:
                prompt += "Provide detailed analysis and practical recommendations based on this information."
            
            logger.debug(f"Enhanced prompt built: {len(prompt)} characters")
            return prompt
            
        except Exception as e:
            logger.error(f"Enhanced prompt building failed: {e}")
            # Fallback to simple prompt
            query = broiler_data.get('query', 'General broiler management advice')
            return f"Provide expert advice for: {query}"


# Compatibility and fallback classes
class FallbackRAGBridge:
    """Fallback RAG Bridge when RAG system is not available."""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key
        self.rag_available = False
        logger.warning("Using fallback RAG Bridge - RAG system not available")
    
    def is_available(self) -> bool:
        return False
    
    def get_enriched_context(self, barn_id: str, broiler_data: Dict[str, Any], 
                           language: str = "en") -> EnrichedContext:
        return EnrichedContext(
            barn_id=barn_id,
            performance_context="",
            weather_context="",
            expert_recommendations=[],
            source_documents=[],
            confidence_score=0.3,
            language=language
        )
    
    def build_enhanced_prompt(self, enriched_context: EnrichedContext, 
                            broiler_data: Dict[str, Any]) -> str:
        query = broiler_data.get('query', 'General broiler management advice')
        return f"Provide expert advice for: {query}"


# Factory function
def create_rag_ai_bridge(openai_api_key: str) -> RAGAIBridge:
    """Create RAG AI Bridge with fallback handling."""
    try:
        if RAG_AVAILABLE:
            return RAGAIBridge(openai_api_key)
        else:
            return FallbackRAGBridge(openai_api_key)
    except Exception as e:
        logger.error(f"Failed to create RAG AI Bridge: {e}")
        return FallbackRAGBridge(openai_api_key)
