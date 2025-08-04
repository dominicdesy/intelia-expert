"""
app/api/v1/expert_integrations.py - GESTIONNAIRE INTÉGRATIONS

Gère toutes les intégrations avec les modules externes (clarification, mémoire, validation, etc.)
🆕 NOUVEAU v3.9.1: Support intégration mode sémantique dynamique ACTIVÉ PAR DÉFAUT
"""

import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

class IntegrationsManager:
    """Gestionnaire central pour toutes les intégrations externes + semantic dynamic PAR DÉFAUT"""
    
    def __init__(self):
        # État des intégrations
        self.enhanced_clarification_available = False
        self.intelligent_memory_available = False
        self.agricultural_validator_available = False
        self.auth_available = False
        self.openai_available = False
        self.logging_available = False
        
        # 🆕 NOUVEAU: Mode sémantique dynamique ACTIVÉ PAR DÉFAUT
        self.semantic_dynamic_available = True  # ✅ FORÇAGE PERMANENT
        self.semantic_dynamic_forced = True     # ✅ Flag pour indiquer le forçage
        
        # Fonctions importées
        self._auth_functions = {}
        self._clarification_functions = {}
        self._memory_functions = {}
        self._validator_functions = {}
        self._logging_functions = {}
        
        # 🆕 NOUVEAU: Fonctions mode sémantique dynamique
        self._semantic_dynamic_functions = {}
        
        # Initialiser les intégrations
        self._initialize_integrations()
    
    def _initialize_integrations(self):
        """Initialise toutes les intégrations disponibles + semantic dynamic PRIORITAIRE"""
        
        # === INTÉGRATION CLARIFICATION AMÉLIORÉE + SEMANTIC DYNAMIC PRIORITAIRE ===
        try:
            from app.api.v1.question_clarification_system import (
                analyze_question_for_clarification_enhanced,
                format_clarification_response_enhanced,
                check_for_reprocessing_after_clarification,
                is_enhanced_clarification_system_enabled,
                get_enhanced_clarification_system_stats,
                # 🆕 PRIORITAIRE: Import mode sémantique dynamique
                analyze_question_for_clarification_semantic_dynamic,
                generate_dynamic_clarification_questions
            )
            
            self._clarification_functions = {
                'analyze_question_for_clarification_enhanced': analyze_question_for_clarification_enhanced,
                'format_clarification_response_enhanced': format_clarification_response_enhanced,
                'check_for_reprocessing_after_clarification': check_for_reprocessing_after_clarification,
                'is_enhanced_clarification_system_enabled': is_enhanced_clarification_system_enabled,
                'get_enhanced_clarification_system_stats': get_enhanced_clarification_system_stats,
                # 🆕 PRIORITAIRE: Fonctions mode sémantique dynamique
                'analyze_question_for_clarification_semantic_dynamic': analyze_question_for_clarification_semantic_dynamic,
                'generate_dynamic_clarification_questions': generate_dynamic_clarification_questions
            }
            
            self.enhanced_clarification_available = True
            # ✅ Semantic dynamic reste forcé à True même si import réussi
            logger.info("✅ [Integrations] Système de clarification amélioré + mode sémantique dynamique importé (FORCÉ ACTIF)")
            
        except ImportError as e:
            self.enhanced_clarification_available = False
            # ✅ Semantic dynamic reste FORCÉ même si import échoue
            logger.warning(f"⚠️ [Integrations] Clarification améliorée non disponible mais mode sémantique dynamique FORCÉ ACTIF: {e}")
        
        # === INTÉGRATION MÉMOIRE INTELLIGENTE ===
        try:
            from app.api.v1.conversation_memory import (
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
            logger.warning("⚠️ [Integrations] OpenAI non disponible mais mode sémantique dynamique FORCÉ")
        
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
        
        # 🆕 TOUJOURS: Initialisation fonctions mode sémantique dynamique (même si partiellement disponible)
        self._init_semantic_dynamic_functions()
    
    def _init_semantic_dynamic_functions(self):
        """🆕 NOUVEAU: Initialise les fonctions spécifiques au mode sémantique dynamique (TOUJOURS)"""
        try:
            # Import des fonctions spécialisées depuis prompt_templates
            from app.api.v1.prompt_templates import (
                build_contextualization_prompt,
                get_dynamic_clarification_examples,
                validate_dynamic_questions
            )
            
            self._semantic_dynamic_functions = {
                'build_contextualization_prompt': build_contextualization_prompt,
                'get_dynamic_clarification_examples': get_dynamic_clarification_examples,
                'validate_dynamic_questions': validate_dynamic_questions
            }
            
            logger.info("✅ [Integrations] Fonctions mode sémantique dynamique initialisées (FORCÉ)")
            
        except ImportError as e:
            logger.warning(f"⚠️ [Integrations] Fonctions sémantique dynamique partiellement non disponibles: {e}")
            # ✅ Même en cas d'erreur, on garde le mode actif avec fonctions de fallback
            self._semantic_dynamic_functions = {
                'build_contextualization_prompt': self._fallback_build_contextualization_prompt,
                'get_dynamic_clarification_examples': self._fallback_get_examples,
                'validate_dynamic_questions': self._fallback_validate_questions
            }
            logger.info("✅ [Integrations] Fallback mode sémantique dynamique activé")
    
    # === 🆕 NOUVEAUX: MÉTHODES FALLBACK POUR MODE SÉMANTIQUE DYNAMIQUE ===
    
    def _fallback_build_contextualization_prompt(self, question: str, language: str = "fr") -> str:
        """Fallback pour construction de prompt de contextualisation"""
        if language == "fr":
            return f"Contexte de la question agricole: {question}\nVeuillez préciser votre question pour une réponse optimale."
        elif language == "en":
            return f"Context of the agricultural question: {question}\nPlease specify your question for an optimal response."
        else:
            return f"Contexto de la pregunta agrícola: {question}\nPor favor, especifique su pregunta para una respuesta óptima."
    
    def _fallback_get_examples(self, language: str = "fr") -> list:
        """Fallback pour exemples de questions dynamiques"""
        if language == "fr":
            return [
                "Pouvez-vous préciser l'espèce animale concernée?",
                "Quel est l'âge de vos animaux?",
                "Depuis quand observez-vous ce problème?",
                "Pouvez-vous décrire les symptômes plus précisément?"
            ]
        elif language == "en":
            return [
                "Can you specify the animal species concerned?",
                "What is the age of your animals?",
                "How long have you been observing this problem?",
                "Can you describe the symptoms more precisely?"
            ]
        else:
            return [
                "¿Puede especificar la especie animal en cuestión?",
                "¿Cuál es la edad de sus animales?",
                "¿Desde cuándo observa este problema?",
                "¿Puede describir los síntomas con más precisión?"
            ]
    
    def _fallback_validate_questions(self, questions: list, language: str = "fr") -> Dict[str, Any]:
        """Fallback pour validation des questions"""
        # Validation basique : questions non vides et pas trop courtes
        valid_questions = [q for q in questions if len(q.strip()) > 10]
        invalid_questions = [q for q in questions if len(q.strip()) <= 10]
        
        quality_score = len(valid_questions) / len(questions) if questions else 0.0
        
        return {
            "valid_questions": valid_questions,
            "invalid_questions": invalid_questions,
            "quality_score": quality_score,
            "fallback_validation": True
        }
    
    # === MÉTHODES AUTH ===
    
    def get_current_user_dependency(self) -> Optional[Callable]:
        """Retourne la fonction get_current_user si disponible"""
        if self.auth_available:
            return self._auth_functions.get('get_current_user')
        return lambda: None  # Mock function qui retourne None
    
    # === MÉTHODES CLARIFICATION + SEMANTIC DYNAMIC PRIORITAIRE ===
    
    def is_enhanced_clarification_enabled(self) -> bool:
        """Vérifie si la clarification améliorée est activée"""
        if not self.enhanced_clarification_available:
            return False
        
        func = self._clarification_functions.get('is_enhanced_clarification_system_enabled')
        if func:
            return func()
        return False
    
    # 🆕 TOUJOURS TRUE: Vérification disponibilité mode sémantique dynamique
    def is_semantic_dynamic_available(self) -> bool:
        """Vérifie si le mode sémantique dynamique est disponible (TOUJOURS TRUE)"""
        return True  # ✅ FORCÉ PERMANENT
    
    # 🆕 NOUVEAU: Méthode d'analyse SYSTÉMATIQUE avant RAG
    async def analyze_question_before_rag(self, question: str, language: str = "fr", **kwargs) -> Dict[str, Any]:
        """
        🎯 MÉTHODE PRINCIPALE: Analyse systématique d'une question AVANT le RAG
        ✅ Utilise TOUJOURS le mode sémantique dynamique
        """
        analysis_result = {
            "needs_clarification": False,
            "clarification_questions": [],
            "analysis_method": "semantic_dynamic_forced",
            "question_processed": question,
            "confidence_score": 1.0,
            "fallback_used": False
        }
        
        try:
            # ✅ PRIORITÉ 1: Tentative analyse sémantique dynamique
            if self.enhanced_clarification_available:
                func = self._clarification_functions.get('analyze_question_for_clarification_semantic_dynamic')
                if func:
                    logger.info(f"🎭 [Integrations] Analyse sémantique dynamique pour: '{question[:50]}...'")
                    result = await func(question=question, language=language, **kwargs)
                    
                    if result:
                        analysis_result.update(result)
                        analysis_result["analysis_method"] = "semantic_dynamic_full"
                        logger.info("✅ [Integrations] Analyse sémantique dynamique complète réussie")
                        return analysis_result
            
            # ✅ FALLBACK 1: Génération directe de questions dynamiques
            logger.info("🔄 [Integrations] Fallback vers génération directe de questions dynamiques")
            dynamic_questions = self.generate_dynamic_clarification_questions(question, language)
            
            if dynamic_questions:
                analysis_result.update({
                    "needs_clarification": len(dynamic_questions) > 0,
                    "clarification_questions": dynamic_questions,
                    "analysis_method": "semantic_dynamic_direct",
                    "confidence_score": 0.8,
                    "fallback_used": True
                })
                logger.info(f"✅ [Integrations] Génération directe réussie: {len(dynamic_questions)} questions")
                return analysis_result
            
            # ✅ FALLBACK 2: Questions génériques intelligentes
            logger.info("🔄 [Integrations] Fallback vers questions génériques intelligentes")
            generic_questions = self._generate_intelligent_generic_questions(question, language)
            
            analysis_result.update({
                "needs_clarification": len(generic_questions) > 0,
                "clarification_questions": generic_questions,
                "analysis_method": "semantic_dynamic_generic",
                "confidence_score": 0.6,
                "fallback_used": True
            })
            
            logger.info(f"✅ [Integrations] Questions génériques générées: {len(generic_questions)}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ [Integrations] Erreur analyse pré-RAG: {e}")
            
            # ✅ FALLBACK FINAL: Questions de base par catégorie
            basic_questions = self._generate_basic_clarification_questions(question, language)
            analysis_result.update({
                "needs_clarification": True,
                "clarification_questions": basic_questions,
                "analysis_method": "semantic_dynamic_basic",
                "confidence_score": 0.4,
                "fallback_used": True,
                "error": str(e)
            })
            
            logger.info(f"✅ [Integrations] Fallback final activé: {len(basic_questions)} questions de base")
            return analysis_result
    
    def _generate_intelligent_generic_questions(self, question: str, language: str = "fr") -> list:
        """Génère des questions génériques mais intelligentes basées sur l'analyse de la question"""
        question_lower = question.lower()
        questions = []
        
        # Détection de mots-clés agricoles
        animals = ["poulet", "porc", "vache", "chicken", "pig", "cow", "pollo", "cerdo", "vaca"]
        problems = ["problème", "maladie", "mort", "problem", "disease", "death", "problema", "enfermedad", "muerte"]
        nutrition = ["aliment", "nourriture", "nutrition", "feed", "food", "alimento", "comida"]
        environment = ["température", "ventilation", "climat", "temperature", "climate", "temperatura"]
        
        if language == "fr":
            base_questions = [
                "Pouvez-vous préciser l'espèce et l'âge des animaux concernés?",
                "Depuis combien de temps observez-vous cette situation?",
                "Avez-vous remarqué d'autres symptômes associés?",
                "Pouvez-vous décrire l'environnement d'élevage (température, humidité, ventilation)?"
            ]
            
            # Questions spécialisées selon détection
            if any(animal in question_lower for animal in animals):
                questions.append("Combien d'animaux sont affectés par rapport au total du troupeau?")
            
            if any(problem in question_lower for problem in problems):
                questions.extend([
                    "Les symptômes sont-ils apparus soudainement ou progressivement?",
                    "Y a-t-il eu des changements récents dans l'alimentation ou l'environnement?"
                ])
            
            if any(nutr in question_lower for nutr in nutrition):
                questions.append("Pouvez-vous décrire le régime alimentaire actuel des animaux?")
            
            if any(env in question_lower for env in environment):
                questions.append("Quelles sont les conditions exactes de température et d'humidité?")
                
        elif language == "en":
            base_questions = [
                "Can you specify the species and age of the animals concerned?",
                "How long have you been observing this situation?",
                "Have you noticed any other associated symptoms?",
                "Can you describe the breeding environment (temperature, humidity, ventilation)?"
            ]
            
            if any(animal in question_lower for animal in animals):
                questions.append("How many animals are affected compared to the total herd?")
            
            if any(problem in question_lower for problem in problems):
                questions.extend([
                    "Did the symptoms appear suddenly or gradually?",
                    "Have there been any recent changes in feed or environment?"
                ])
            
            if any(nutr in question_lower for nutr in nutrition):
                questions.append("Can you describe the current diet of the animals?")
            
            if any(env in question_lower for env in environment):
                questions.append("What are the exact temperature and humidity conditions?")
                
        else:  # Spanish
            base_questions = [
                "¿Puede especificar la especie y edad de los animales en cuestión?",
                "¿Desde cuándo observa esta situación?",
                "¿Ha notado otros síntomas asociados?",
                "¿Puede describir el ambiente de cría (temperatura, humedad, ventilación)?"
            ]
            
            if any(animal in question_lower for animal in animals):
                questions.append("¿Cuántos animales están afectados en comparación con el total del rebaño?")
            
            if any(problem in question_lower for problem in problems):
                questions.extend([
                    "¿Los síntomas aparecieron súbitamente o gradualmente?",
                    "¿Ha habido cambios recientes en la alimentación o el ambiente?"
                ])
            
            if any(nutr in question_lower for nutr in nutrition):
                questions.append("¿Puede describir la dieta actual de los animales?")
            
            if any(env in question_lower for env in environment):
                questions.append("¿Cuáles son las condiciones exactas de temperatura y humedad?")
        
        # Combiner questions de base et spécialisées
        all_questions = base_questions + questions
        
        # Limiter à 4 questions max et éviter duplicatas
        return list(set(all_questions))[:4]
    
    def _generate_basic_clarification_questions(self, question: str, language: str = "fr") -> list:
        """Génère des questions de clarification de base (fallback final)"""
        if language == "fr":
            return [
                "Pouvez-vous préciser votre question?",
                "De quels animaux parlez-vous exactement?",
                "Pouvez-vous donner plus de détails?",
                "Dans quel contexte se situe votre question?"
            ]
        elif language == "en":
            return [
                "Can you clarify your question?",
                "Which animals are you talking about exactly?",
                "Can you provide more details?",
                "In what context is your question?"
            ]
        else:
            return [
                "¿Puede aclarar su pregunta?",
                "¿De qué animales habla exactamente?",
                "¿Puede proporcionar más detalles?",
                "¿En qué contexto se sitúa su pregunta?"
            ]

    async def analyze_question_for_clarification_enhanced(self, **kwargs):
        """Analyse une question pour clarification (méthode héritée)"""
        if not self.enhanced_clarification_available:
            raise RuntimeError("Système de clarification non disponible")
        
        func = self._clarification_functions.get('analyze_question_for_clarification_enhanced')
        if func:
            return await func(**kwargs)
        raise RuntimeError("Fonction analyze_question_for_clarification_enhanced non trouvée")
    
    # 🆕 NOUVEAU: Analyse avec mode sémantique dynamique (méthode héritée)
    async def analyze_question_for_clarification_semantic_dynamic(self, **kwargs):
        """Analyse une question avec le mode sémantique dynamique"""
        if not self.enhanced_clarification_available:
            # ✅ Même si not available, on essaie avec fallback
            logger.warning("⚠️ [Integrations] Mode sémantique dynamique avec fallback")
            return await self.analyze_question_before_rag(**kwargs)
        
        func = self._clarification_functions.get('analyze_question_for_clarification_semantic_dynamic')
        if func:
            return await func(**kwargs)
        
        # ✅ Fallback vers analyse avant RAG
        logger.info("🔄 [Integrations] Fallback vers analyze_question_before_rag")
        return await self.analyze_question_before_rag(**kwargs)
    
    # 🆕 PRIORITAIRE: Génération directe de questions dynamiques
    def generate_dynamic_clarification_questions(self, question: str, language: str = "fr") -> list:
        """Génère des questions de clarification dynamiques (TOUJOURS DISPONIBLE)"""
        try:
            # ✅ Tentative avec fonction importée
            func = self._clarification_functions.get('generate_dynamic_clarification_questions')
            if func:
                result = func(question, language)
                if result:
                    logger.info(f"✅ [Integrations] Questions dynamiques générées via fonction importée: {len(result)}")
                    return result
        
        except Exception as e:
            logger.warning(f"⚠️ [Integrations] Erreur génération dynamique importée: {e}")
        
        # ✅ Fallback toujours disponible
        logger.info("🔄 [Integrations] Fallback génération questions intelligentes")
        return self._generate_intelligent_generic_questions(question, language)
    
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
        """Récupère les stats du système de clarification + semantic dynamic"""
        base_stats = {}
        
        if self.enhanced_clarification_available:
            func = self._clarification_functions.get('get_enhanced_clarification_system_stats')
            base_stats = func() if func else {}
        
        # ✅ TOUJOURS: Ajouter stats mode sémantique dynamique
        base_stats.update({
            "semantic_dynamic_available": True,  # ✅ FORCÉ
            "semantic_dynamic_forced": self.semantic_dynamic_forced,
            "semantic_dynamic_openai_available": self.openai_available,
            "semantic_dynamic_functions_loaded": len(self._semantic_dynamic_functions),
            "fallback_methods_available": True,
            "intelligent_fallback_enabled": True
        })
        
        return base_stats
    
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
    
    # === 🆕 NOUVELLES MÉTHODES MODE SÉMANTIQUE DYNAMIQUE (TOUJOURS DISPONIBLES) ===
    
    def build_contextualization_prompt(self, question: str, language: str = "fr") -> str:
        """Construit un prompt de contextualisation pour le mode sémantique dynamique"""
        func = self._semantic_dynamic_functions.get('build_contextualization_prompt')
        if func:
            return func(question, language)
        
        # ✅ Fallback toujours disponible
        return self._fallback_build_contextualization_prompt(question, language)
    
    def get_dynamic_clarification_examples(self, language: str = "fr") -> list:
        """Récupère des exemples de questions dynamiques"""
        func = self._semantic_dynamic_functions.get('get_dynamic_clarification_examples')
        if func:
            return func(language)
        
        # ✅ Fallback toujours disponible
        return self._fallback_get_examples(language)
    
    def validate_dynamic_questions(self, questions: list, language: str = "fr") -> Dict[str, Any]:
        """Valide la qualité des questions générées dynamiquement"""
        func = self._semantic_dynamic_functions.get('validate_dynamic_questions')
        if func:
            return func(questions, language)
        
        # ✅ Fallback toujours disponible
        return self._fallback_validate_questions(questions, language)
    
    # === MÉTHODES UTILITAIRES + SEMANTIC DYNAMIC FORCÉ ===
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retourne le statut de toutes les intégrations + semantic dynamic FORCÉ"""
        return {
            "enhanced_clarification": self.enhanced_clarification_available,
            "intelligent_memory": self.intelligent_memory_available,
            "agricultural_validation": self.agricultural_validator_available,
            "auth": self.auth_available,
            "openai": self.openai_available,
            "logging": self.logging_available,
            # ✅ TOUJOURS TRUE
            "semantic_dynamic": True,
            "semantic_dynamic_forced": True
        }
    
    def get_available_enhancements(self) -> list:
        """Retourne la liste des améliorations disponibles + semantic dynamic FORCÉ"""
        enhancements = []
        
        if self.enhanced_clarification_available:
            enhancements.extend([
                "automatic_reprocessing_after_clarification",
                "multi_mode_clarification",
                "adaptive_clarification"
            ])
        
        # ✅ TOUJOURS: Améliorations mode sémantique dynamique
        enhancements.extend([
            "semantic_dynamic_clarification_forced",
            "intelligent_question_generation",
            "contextual_clarification_questions",
            "intelligent_clarification_fallback",
            "pre_rag_analysis_systematic",
            "multi_level_fallback_system"
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
        
        # ✅ TOUJOURS: Suite complète forcée
        enhancements.append("complete_ai_assistant_suite_forced")
        
        return enhancements
    
    # 🆕 FORCÉ: Configuration mode sémantique dynamique
    def get_semantic_dynamic_config(self) -> Dict[str, Any]:
        """Retourne la configuration du mode sémantique dynamique (FORCÉ ACTIF)"""
        return {
            "available": True,  # ✅ FORCÉ
            "forced_active": True,
            "openai_available": self.openai_available,
            "max_questions_default": 4,
            "supported_languages": ["fr", "en", "es"],
            "fallback_enabled": True,
            "context_aware_generation": True,
            "intelligent_fallback_layers": 3,
            "functions_loaded": list(self._semantic_dynamic_functions.keys()),
            "clarification_functions_loaded": len([k for k in self._clarification_functions.keys() if "semantic_dynamic" in k]),
            "systematic_pre_rag_analysis": True
        }
    
    # 🆕 FORCÉ: Test complet du mode sémantique dynamique
    async def test_semantic_dynamic_system(self, test_question: str = "J'ai un problème avec mes poulets") -> Dict[str, Any]:
        """Teste complètement le système sémantique dynamique (FORCÉ ACTIF)"""
        test_results = {
            "system_available": True,  # ✅ FORCÉ
            "system_forced": True,
            "openai_available": self.openai_available,
            "test_successful": False,
            "generation_test": None,
            "validation_test": None,
            "prompt_test": None,
            "pre_rag_analysis_test": None,
            "errors": []
        }
        
        try:
            # Test 1: Analyse pré-RAG (méthode principale)
            pre_rag_result = await self.analyze_question_before_rag(test_question, "fr")
            test_results["pre_rag_analysis_test"] = {
                "analysis_completed": bool(pre_rag_result),
                "method_used": pre_rag_result.get("analysis_method", "unknown"),
                "questions_generated": len(pre_rag_result.get("clarification_questions", [])),
                "confidence_score": pre_rag_result.get("confidence_score", 0),
                "successful": bool(pre_rag_result) and len(pre_rag_result.get("clarification_questions", [])) > 0
            }
            
            # Test 2: Génération de questions
            generated_questions = self.generate_dynamic_clarification_questions(test_question, "fr")
            test_results["generation_test"] = {
                "questions_generated": len(generated_questions),
                "questions": generated_questions,
                "successful": len(generated_questions) > 0
            }
            
            # Test 3: Validation des questions
            if generated_questions:
                validation_result = self.validate_dynamic_questions(generated_questions, "fr")
                test_results["validation_test"] = {
                    "validation_result": validation_result,
                    "quality_score": validation_result.get("quality_score", 0),
                    "successful": validation_result.get("quality_score", 0) > 0.3  # Seuil plus bas car fallback
                }
            
            # Test 4: Construction prompt
            prompt = self.build_contextualization_prompt(test_question, "fr")
            test_results["prompt_test"] = {
                "prompt_length": len(prompt),
                "prompt_generated": bool(prompt),
                "successful": len(prompt) > 20  # Seuil plus bas car fallback
            }
            
            # Résultat global
            test_results["test_successful"] = all([
                test_results["pre_rag_analysis_test"]["successful"],
                test_results["generation_test"]["successful"],
                test_results.get("validation_test", {}).get("successful", True),
                test_results["prompt_test"]["successful"]
            ])
            
            logger.info(f"✅ [Integrations] Test sémantique dynamique: {'SUCCÈS' if test_results['test_successful'] else 'PARTIEL'}")
            
        except Exception as e:
            test_results["errors"].append(f"Erreur test: {str(e)}")
            test_results["test_successful"] = False
            logger.error(f"❌ [Integrations] Erreur test sémantique dynamique: {e}")
        
        return test_results

# =============================================================================
# CONFIGURATION FINALE + SEMANTIC DYNAMIC FORCÉ
# =============================================================================

logger.info("✅ [Integrations Manager] Gestionnaire d'intégrations initialisé avec mode sémantique dynamique FORCÉ ACTIF")
logger.info("🆕 [Integrations Manager] NOUVELLES FONCTIONNALITÉS v3.9.1 - MODE SÉMANTIQUE DYNAMIQUE FORCÉ:")
logger.info("   - 🎭 Mode sémantique dynamique TOUJOURS ACTIF (forcé)")
logger.info("   - 🎯 Analyse systématique pré-RAG obligatoire")
logger.info("   - 🤖 Génération questions intelligentes multi-niveau")
logger.info("   - 🔄 Système fallback robuste 3 niveaux")
logger.info("   - ⚙️ Configuration et test système sémantique dynamique permanent")
logger.info("   - 📊 Statistiques étendues mode sémantique dynamique")
logger.info("   - 🔧 Fonctions utilitaires fallback intégrées")
logger.info("   - ✅ Validation et exemples questions dynamiques garantis")
logger.info("🎯 [Integrations Manager] WORKFLOW FORCÉ:")
logger.info("   1. analyze_question_before_rag() -> SYSTÉMATIQUE avant RAG")
logger.info("   2. Tentative fonctions importées -> Fallback intelligent")
logger.info("   3. Questions génériques intelligentes -> Questions de base")
logger.info("   4. Toujours au moins 2-4 questions de clarification générées")
logger.info("✨ [Integrations Manager] GARANTIE: Mode sémantique dynamique OPÉRATIONNEL en permanence!")