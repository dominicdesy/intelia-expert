"""
app/api/v1/expert_integrations.py - GESTIONNAIRE INTÉGRATIONS

Gère toutes les intégrations avec les modules externes (clarification, mémoire, validation, etc.)
"""

import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

class IntegrationsManager:
    """Gestionnaire central pour toutes les intégrations externes"""
    
    def __init__(self):
        # État des intégrations
        self.enhanced_clarification_available = False
        self.intelligent_memory_available = False
        self.agricultural_validator_available = False
        self.auth_available = False
        self.openai_available = False
        self.logging_available = False
        
        # Fonctions importées
        self._auth_functions = {}
        self._clarification_functions = {}
        self._memory_functions = {}
        self._validator_functions = {}
        self._logging_functions = {}
        
        # Initialiser les intégrations
        self._initialize_integrations()
    
    def _initialize_integrations(self):
        """Initialise toutes les intégrations disponibles"""
        
        # === INTÉGRATION CLARIFICATION AMÉLIORÉE ===
        try:
            from app.api.v1.question_clarification_system_enhanced import (
                analyze_question_for_clarification_enhanced,
                format_clarification_response_enhanced,
                check_for_reprocessing_after_clarification,
                is_enhanced_clarification_system_enabled,
                get_enhanced_clarification_system_stats
            )
            
            self._clarification_functions = {
                'analyze_question_for_clarification_enhanced': analyze_question_for_clarification_enhanced,
                'format_clarification_response_enhanced': format_clarification_response_enhanced,
                'check_for_reprocessing_after_clarification': check_for_reprocessing_after_clarification,
                'is_enhanced_clarification_system_enabled': is_enhanced_clarification_system_enabled,
                'get_enhanced_clarification_system_stats': get_enhanced_clarification_system_stats
            }
            
            self.enhanced_clarification_available = True
            logger.info("✅ [Integrations] Système de clarification amélioré importé")
            
        except ImportError as e:
            self.enhanced_clarification_available = False
            logger.warning(f"⚠️ [Integrations] Clarification améliorée non disponible: {e}")
        
        # === INTÉGRATION MÉMOIRE INTELLIGENTE ===
        try:
            from app.api.v1.conversation_memory_enhanced import (
                add_message_to_conversation,
                get_conversation_context,
                get_context_for_clarification,
                get_context_for_rag,
                get_conversation_memory_stats
            )
            
            self._memory_functions = {
                'add_message_to_conversation': add_message_to_conversation,
                'get_conversation_context': get_conversation_context,
                'get_context_for_clarification': get_context_for_clarification,
                'get_context_for_rag': get_context_for_rag,
                'get_conversation_memory_stats': get_conversation_memory_stats
            }
            
            self.intelligent_memory_available = True
            logger.info("✅ [Integrations] Mémoire intelligente importée")
            
        except ImportError as e:
            self.intelligent_memory_available = False
            logger.warning(f"⚠️ [Integrations] Mémoire intelligente non disponible: {e}")
        
        # === INTÉGRATION VALIDATEUR AGRICOLE ===
        try:
            from app.api.v1.agricultural_domain_validator import (
                validate_agricultural_question,
                get_agricultural_validator_stats,
                is_agricultural_validation_enabled
            )
            
            self._validator_functions = {
                'validate_agricultural_question': validate_agricultural_question,
                'get_agricultural_validator_stats': get_agricultural_validator_stats,
                'is_agricultural_validation_enabled': is_agricultural_validation_enabled
            }
            
            self.agricultural_validator_available = True
            logger.info("✅ [Integrations] Validateur agricole importé")
            
        except ImportError as e:
            self.agricultural_validator_available = False
            logger.error(f"❌ [Integrations] Validateur agricole non disponible: {e}")
        
        # === INTÉGRATION AUTH ===
        try:
            from .auth import get_current_user
            self._auth_functions = {'get_current_user': get_current_user}
            self.auth_available = True
            logger.info("✅ [Integrations] Auth importé")
        except ImportError:
            try:
                from app.api.v1.auth import get_current_user
                self._auth_functions = {'get_current_user': get_current_user}
                self.auth_available = True
                logger.info("✅ [Integrations] Auth importé (path alternatif)")
            except ImportError as e:
                self.auth_available = False
                logger.error(f"❌ [Integrations] Auth non disponible: {e}")
        
        # === INTÉGRATION OPENAI ===
        try:
            import openai
            self.openai_available = True
            logger.info("✅ [Integrations] OpenAI disponible")
        except ImportError:
            self.openai_available = False
            logger.warning("⚠️ [Integrations] OpenAI non disponible")
        
        # === INTÉGRATION LOGGING ===
        try:
            from app.api.v1.logging import logger_instance, ConversationCreate
            if logger_instance:
                self._logging_functions = {
                    'logger_instance': logger_instance,
                    'ConversationCreate': ConversationCreate
                }
                self.logging_available = True
                logger.info("✅ [Integrations] Système de logging intégré")
            else:
                self.logging_available = False
        except ImportError as e:
            self.logging_available = False
            logger.warning(f"⚠️ [Integrations] Système de logging non disponible: {e}")
    
    # === MÉTHODES AUTH ===
    
    def get_current_user_dependency(self) -> Optional[Callable]:
        """Retourne la fonction get_current_user si disponible"""
        if self.auth_available:
            return self._auth_functions.get('get_current_user')
        return lambda: None  # Mock function qui retourne None
    
    # === MÉTHODES CLARIFICATION ===
    
    def is_enhanced_clarification_enabled(self) -> bool:
        """Vérifie si la clarification améliorée est activée"""
        if not self.enhanced_clarification_available:
            return False
        
        func = self._clarification_functions.get('is_enhanced_clarification_system_enabled')
        if func:
            return func()
        return False
    
    async def analyze_question_for_clarification_enhanced(self, **kwargs):
        """Analyse une question pour clarification"""
        if not self.enhanced_clarification_available:
            raise RuntimeError("Système de clarification non disponible")
        
        func = self._clarification_functions.get('analyze_question_for_clarification_enhanced')
        if func:
            return await func(**kwargs)
        raise RuntimeError("Fonction analyze_question_for_clarification_enhanced non trouvée")
    
    def format_clarification_response_enhanced(self, **kwargs):
        """Formate une réponse de clarification"""
        if not self.enhanced_clarification_available:
            raise RuntimeError("Système de clarification non disponible")
        
        func = self._clarification_functions.get('format_clarification_response_enhanced')
        if func:
            return func(**kwargs)
        raise RuntimeError("Fonction format_clarification_response_enhanced non trouvée")
    
    async def check_for_reprocessing_after_clarification(self, **kwargs):
        """Vérifie si retraitement nécessaire après clarification"""
        if not self.enhanced_clarification_available:
            return None
        
        func = self._clarification_functions.get('check_for_reprocessing_after_clarification')
        if func:
            return await func(**kwargs)
        return None
    
    def get_enhanced_clarification_system_stats(self):
        """Récupère les stats du système de clarification"""
        if not self.enhanced_clarification_available:
            return {}
        
        func = self._clarification_functions.get('get_enhanced_clarification_system_stats')
        if func:
            return func()
        return {}
    
    # === MÉTHODES MÉMOIRE INTELLIGENTE ===
    
    def add_message_to_conversation(self, **kwargs):
        """Ajoute un message à la conversation"""
        if not self.intelligent_memory_available:
            return None
        
        func = self._memory_functions.get('add_message_to_conversation')
        if func:
            return func(**kwargs)
        return None
    
    def get_conversation_context(self, conversation_id: str):
        """Récupère le contexte d'une conversation"""
        if not self.intelligent_memory_available:
            return None
        
        func = self._memory_functions.get('get_conversation_context')
        if func:
            return func(conversation_id)
        return None
    
    def get_context_for_clarification(self, conversation_id: str):
        """Récupère le contexte pour clarification"""
        if not self.intelligent_memory_available:
            return {}
        
        func = self._memory_functions.get('get_context_for_clarification')
        if func:
            return func(conversation_id)
        return {}
    
    def get_context_for_rag(self, conversation_id: str, max_chars: int = 800):
        """Récupère le contexte pour RAG"""
        if not self.intelligent_memory_available:
            return ""
        
        func = self._memory_functions.get('get_context_for_rag')
        if func:
            return func(conversation_id, max_chars)
        return ""
    
    def get_conversation_memory_stats(self):
        """Récupère les stats de la mémoire"""
        if not self.intelligent_memory_available:
            return {}
        
        func = self._memory_functions.get('get_conversation_memory_stats')
        if func:
            return func()
        return {}
    
    # === MÉTHODES VALIDATION AGRICOLE ===
    
    def is_agricultural_validation_enabled(self) -> bool:
        """Vérifie si la validation agricole est activée"""
        if not self.agricultural_validator_available:
            return False
        
        func = self._validator_functions.get('is_agricultural_validation_enabled')
        if func:
            return func()
        return False
    
    def validate_agricultural_question(self, **kwargs):
        """Valide une question agricole"""
        if not self.agricultural_validator_available:
            raise RuntimeError("Validateur agricole non disponible")
        
        func = self._validator_functions.get('validate_agricultural_question')
        if func:
            return func(**kwargs)
        raise RuntimeError("Fonction validate_agricultural_question non trouvée")
    
    def get_agricultural_validator_stats(self):
        """Récupère les stats du validateur"""
        if not self.agricultural_validator_available:
            return {}
        
        func = self._validator_functions.get('get_agricultural_validator_stats')
        if func:
            return func()
        return {}
    
    # === MÉTHODES LOGGING ===
    
    async def update_feedback(self, conversation_id: str, rating_numeric: int) -> bool:
        """Met à jour le feedback d'une conversation"""
        if not self.logging_available:
            return False
        
        logger_instance = self._logging_functions.get('logger_instance')
        if not logger_instance:
            return False
        
        try:
            # Essayer update_feedback si disponible
            if hasattr(logger_instance, 'update_feedback'):
                return logger_instance.update_feedback(conversation_id, rating_numeric)
            
            # Fallback vers SQL direct
            import sqlite3
            with sqlite3.connect(logger_instance.db_path) as conn:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET feedback = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE conversation_id = ?
                """, (rating_numeric, conversation_id))
                
                return cursor.rowcount > 0
        
        except Exception as e:
            logger.error(f"❌ [Integrations] Erreur update_feedback: {e}")
            return False
    
    # === MÉTHODES UTILITAIRES ===
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retourne le statut de toutes les intégrations"""
        return {
            "enhanced_clarification": self.enhanced_clarification_available,
            "intelligent_memory": self.intelligent_memory_available,
            "agricultural_validation": self.agricultural_validator_available,
            "auth": self.auth_available,
            "openai": self.openai_available,
            "logging": self.logging_available
        }
    
    def get_available_enhancements(self) -> list:
        """Retourne la liste des améliorations disponibles"""
        enhancements = []
        
        if self.enhanced_clarification_available:
            enhancements.extend([
                "automatic_reprocessing_after_clarification",
                "multi_mode_clarification",
                "adaptive_clarification"
            ])
        
        if self.intelligent_memory_available:
            enhancements.extend([
                "intelligent_entity_extraction",
                "contextual_reasoning",
                "conversation_state_tracking"
            ])
        
        if self.intelligent_memory_available and self.enhanced_clarification_available:
            enhancements.append("ai_powered_enhancements")
        
        if self.openai_available:
            enhancements.append("enhanced_prompts_with_numerical_data")
        
        return enhancements

# =============================================================================
# CONFIGURATION
# =============================================================================

logger.info("✅ [Integrations Manager] Gestionnaire d'intégrations initialisé")
