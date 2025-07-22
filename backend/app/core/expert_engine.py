import sys
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Import your existing modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from core.ai.ai_client import BroilerAnalyzer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    BroilerAnalyzer = None

try:
    from core.data.api_client import CompassAPI
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    CompassAPI = None

try:
    from core.config.rag_config_manager import configure_compass_rag
    RAG_CONFIG_AVAILABLE = True
except ImportError:
    RAG_CONFIG_AVAILABLE = False
    def configure_compass_rag():
        return {"integration_status": "disabled", "rag_method": "disabled"}

logger = logging.getLogger(__name__)

class InteliaExpertEngine:
    """Expert engine adapte de votre SimpleExpertInterface."""
    
    def __init__(self):
        self.ai_analyzer = None
        self.api_client = None
        self.rag_configured = False
        self.rag_status = "unknown"
        self._configure_rag()
        self._initialize_services()
        logger.info("Intelia Expert Engine initialized")
    
    def _configure_rag(self):
        """Configure RAG system automatically."""
        if RAG_CONFIG_AVAILABLE:
            try:
                rag_report = configure_compass_rag()
                self.rag_configured = rag_report.get('integration_status') == 'success'
                self.rag_status = rag_report.get('rag_method', 'unknown')
                logger.info(f"RAG auto-configuration: {self.rag_status}")
            except Exception as e:
                logger.warning(f"RAG auto-configuration failed: {e}")
                self.rag_configured = False
                self.rag_status = "error"
        else:
            self.rag_configured = False
            self.rag_status = "unavailable"
    
    def _initialize_services(self):
        """Initialize services with error handling."""
        # Initialize AI Analyzer
        if AI_AVAILABLE:
            try:
                import os
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    self.ai_analyzer = BroilerAnalyzer(
                        openai_api_key=openai_key,
                        default_model="gpt-4o"
                    )
                    logger.info("AI Analyzer initialized")
            except Exception as e:
                logger.error(f"AI Analyzer failed: {e}")
        
        # Initialize API Client
        if API_AVAILABLE:
            try:
                compass_token = os.getenv("COMPASS_TOKEN")
                if compass_token:
                    self.api_client = CompassAPI("https://compass.intelia.com/api/v1")
                    self.api_client.api_token = compass_token
                    logger.info("API Client initialized")
            except Exception as e:
                logger.error(f"API Client failed: {e}")
    
    async def process_query(self, query: str, model: str = "gpt-4o") -> Dict:
        """Process query."""
        try:
            start_time = datetime.now()
            
            if self.ai_analyzer:
                response = self._get_ai_response(query, model)
            else:
                response = self._get_direct_openai_response(query, model)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "response": response,
                "rag_status": self.rag_status,
                "rag_configured": self.rag_configured,
                "model_used": model,
                "processing_time": processing_time,
                "timestamp": start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return {
                "response": f"Processing error: {str(e)}",
                "rag_status": self.rag_status,
                "error": True
            }
    
    def _get_ai_response(self, query: str, model: str) -> str:
        """Get response via AI Analyzer."""
        try:
            if hasattr(self.ai_analyzer, 'get_expert_analysis_for_client'):
                response = self.ai_analyzer.get_expert_analysis_for_client(
                    barn_id="default_barn",
                    client_email="user@expert.local", 
                    broiler_data={
                        "query": query, 
                        "age": 35, 
                        "breed": "Ross 308",
                        "observed_weight": 2000,
                        "expected_weight": 2100,
                        "gain_ratio": 0.95
                    },
                    language="fr"
                )
                return response if response else "No response generated"
            else:
                return self._get_direct_openai_response(query, model)
        except Exception as e:
            logger.error(f"AI Analyzer error: {e}")
            return self._get_direct_openai_response(query, model)
    
    def _get_direct_openai_response(self, query: str, model: str) -> str:
        """Direct OpenAI response."""
        try:
            import openai
            import os
            
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return "OpenAI API key missing. Check configuration."
            
            client = openai.OpenAI(api_key=openai_key)
            
            system_prompt = "You are an expert in Ross 308 broiler management. Respond concisely and practically in French."
            if self.rag_configured:
                system_prompt += " You have access to a specialized knowledge base."
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI direct call failed: {e}")
            return f"OpenAI error: {str(e)}"
    
    def get_system_status(self) -> Dict:
        """Get system status."""
        return {
            "ai_analyzer_available": self.ai_analyzer is not None,
            "api_client_available": self.api_client is not None,
            "rag_configured": self.rag_configured,
            "rag_status": self.rag_status,
            "services": {
                "ai_available": AI_AVAILABLE,
                "api_available": API_AVAILABLE,
                "rag_config_available": RAG_CONFIG_AVAILABLE
            }
        }
    
    def get_examples(self) -> list:
        """Get example queries."""
        return [
            "Temperature for 21-day Ross 308",
            "Heat stress management", 
            "Feeding protocols",
            "Ventilation guidelines",
            "Health management"
        ]
