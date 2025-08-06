# Module modifié: rag_context_enhancer.py
# Intègre l'IA pour l'amélioration contextuelle avec fallback vers les patterns classiques
# VERSION MODIFIÉE selon le Plan de Transformation - Phase 2

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set

logger = logging.getLogger(__name__)

# NOUVEAU: Import des services IA (à créer séparément)
try:
    from .ai_context_enhancer import AIContextEnhancer
    AI_AVAILABLE = True
except ImportError:
    logger.warning("AIContextEnhancer non disponible - fallback vers patterns classiques")
    AI_AVAILABLE = False

class RAGContextEnhancer:
    """
    Améliore le contexte conversationnel pour optimiser les requêtes RAG
    VERSION HYBRIDE: IA + Fallback patterns classiques
    """
    
    def __init__(self):
        # ✅ NOUVEAU: Service IA principal
        self.ai_enhancer = None
        if AI_AVAILABLE:
            try:
                self.ai_enhancer = AIContextEnhancer()
                logger.info("🤖 AIContextEnhancer initialisé avec succès")
            except Exception as e:
                logger.warning(f"Échec initialisation AIContextEnhancer: {e}")
                self.ai_enhancer = None
        
        # ✅ CONSERVÉ: Patterns critiques comme fallback (patterns minimalistes)
        self._minimal_patterns = self._load_minimal_patterns()
        self._compiled_patterns = {}
        self._compile_minimal_patterns()
        
        # Entités importantes à extraire du contexte (conservé)
        self.key_entities = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
    
    def _load_minimal_patterns(self) -> Dict[str, List[str]]:
        """Charge uniquement les patterns critiques essentiels pour le fallback"""
        return {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance)',
                r'\b(qu\'?est-ce\s+que|quel\s+est)\s+(son|sa|ses)',
                r'\b(ces|cette|ce)\s+(poulets?|animaux)',
                r'\b(ma|mes)\s+(poules?|poulets?)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth)',
                r'\b(what\s+is|how\s+much\s+is)\s+(their|its)',
                r'\b(these|this)\s+(chickens?|animals?)',
                r'\b(my)\s+(chickens?|animals?)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento)',
                r'\b(cuál\s+es|cuánto\s+es)\s+(su|sus)',
                r'\b(estos|estas|este|esta)\s+(pollos?|animales?)',
                r'\b(mis?)\s+(pollos?|animales?)'
            ]
        }
    
    def _compile_minimal_patterns(self):
        """Compile les patterns essentiels uniquement"""
        for language, patterns in self._minimal_patterns.items():
            self._compiled_patterns[language] = []
            for pattern in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns[language].append(compiled)
                except re.error as e:
                    logger.warning(f"Pattern regex invalide pour {language}: {pattern} - Erreur: {e}")
    
    async def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr",
        missing_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Améliore une question pour le RAG
        ✅ PRIORITÉ: IA avec fallback patterns classiques
        
        Args:
            question: Question originale
            conversation_context: Contexte conversationnel
            language: Langue (doit être dans ['fr', 'en', 'es'])
            missing_entities: Liste des entités manquantes (optionnel)
        
        Returns:
            Dict contenant la question optimisée et métadonnées
        """
        
        # Validation des entrées (conservé)
        if not question or not isinstance(question, str):
            logger.error("Question invalide fournie")
            return self._get_empty_result(question or "")
        
        if not isinstance(conversation_context, str):
            conversation_context = str(conversation_context) if conversation_context else ""
        
        if language not in ['fr', 'en', 'es']:
            logger.warning(f"Langue non supportée: {language}, utilisation de 'fr' par défaut")
            language = 'fr'
        
        # ✅ NOUVEAU: Tentative avec IA en priorité
        if self.ai_enhancer is not None:
            try:
                logger.info("🤖 [RAG Context] Tentative amélioration avec IA")
                ai_result = await self.ai_enhancer.enhance_question_for_rag(
                    question, conversation_context, language, missing_entities
                )
                
                # Ajouter métadonnées sur l'utilisation de l'IA
                ai_result["enhancement_info"]["ai_used"] = True
                ai_result["enhancement_info"]["fallback_used"] = False
                
                logger.info(f"✨ [RAG Context] IA réussie: '{ai_result['question']}'")
                return ai_result
                
            except Exception as e:
                logger.warning(f"⚠️ [RAG Context] IA échouée, basculement vers fallback: {e}")
                # Continuer vers le fallback
        
        # ✅ FALLBACK: Logique classique simplifiée
        logger.info("🔄 [RAG Context] Utilisation fallback patterns classiques")
        return await self._enhance_with_fallback_patterns(
            question, conversation_context, language, missing_entities
        )
    
    async def _enhance_with_fallback_patterns(
        self, 
        question: str, 
        conversation_context: str, 
        language: str,
        missing_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Amélioration avec patterns classiques simplifiés (fallback)
        ✅ Version ALLÉGÉE du code original (30% des patterns essentiels)
        """
        
        result = {
            "question": question,
            "missing_entities": missing_entities or [],
            "context_entities": {},
            "enhancement_info": {
                "ai_used": False,
                "fallback_used": True,
                "pronoun_detected": False,
                "question_enriched": False,
                "original_question": question,
                "variants_tested": [question],
                "best_variant_score": 0.0,
                "variant_selection_method": "fallback_patterns"
            }
        }
        
        try:
            # 1. Détecter les pronoms (version simplifiée)
            has_pronouns = self._detect_contextual_references_minimal(question, language)
            if has_pronouns:
                result["enhancement_info"]["pronoun_detected"] = True
                logger.info(f"🔍 [RAG Context Fallback] Pronoms détectés: '{question}'")
            
            # 2. Extraire entités du contexte (version simplifiée)
            context_entities = self._extract_essential_context_entities(conversation_context)
            result["context_entities"] = context_entities
            
            # 3. Générer question enrichie simple
            if context_entities and has_pronouns:
                enriched_question = self._build_simple_enriched_question(
                    question, context_entities, language
                )
                
                if enriched_question != question:
                    result["question"] = enriched_question
                    result["enhancement_info"]["question_enriched"] = True
                    result["enhancement_info"]["variants_tested"] = [question, enriched_question]
                    logger.info(f"✨ [RAG Context Fallback] Question enrichie: '{enriched_question}'")
            
        except Exception as e:
            logger.error(f"Erreur fallback patterns: {e}")
            # En cas d'erreur, retourner la question originale
        
        return result
    
    def _detect_contextual_references_minimal(self, question: str, language: str) -> bool:
        """Détection simplifiée des références contextuelles (patterns essentiels uniquement)"""
        
        if not question or language not in self._compiled_patterns:
            return False
        
        try:
            question_lower = question.lower()
            
            for pattern in self._compiled_patterns[language]:
                if pattern.search(question_lower):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur détection références minimale: {e}")
            return False
    
    def _extract_essential_context_entities(self, context: str) -> Dict[str, str]:
        """Extraction simplifiée des entités les plus critiques uniquement"""
        
        if not context or not isinstance(context, str):
            return {}
        
        try:
            entities = {}
            context_lower = context.lower()
            
            # Extraire race (patterns critiques uniquement)
            breed_patterns = [
                r'(ross\s*308|cobb\s*500|hubbard)',
                r'race[:\s]+([a-zA-Z0-9\s]{3,20}?)(?:\n|,|\.|\s*$)'
            ]
            
            for pattern in breed_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        breed_value = match.group(1).strip()
                        if breed_value and len(breed_value) > 0:
                            entities["breed"] = breed_value
                            break
                except (re.error, IndexError):
                    continue
            
            # Extraire âge (patterns critiques uniquement)
            age_patterns = [
                r'(\d+)\s*(?:jour|day)s?(?:\s|$|,|\.)',
                r'(\d+)\s*(?:semaine|week)s?(?:\s|$|,|\.)'
            ]
            
            for pattern in age_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        age_value = match.group(1).strip()
                        if age_value and len(age_value) > 0:
                            entities["age"] = f"{age_value} jours" if "jour" in pattern else f"{age_value} semaines"
                            break
                except (re.error, IndexError):
                    continue
            
            # Extraire poids (patterns critiques uniquement)
            weight_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:gramme|gram|kg)s?(?:\s|$|,|\.)'
            ]
            
            for pattern in weight_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        weight_value = match.group(1).strip()
                        if weight_value and len(weight_value) > 0:
                            entities["weight"] = weight_value
                            break
                except (re.error, IndexError):
                    continue
            
            return entities
            
        except Exception as e:
            logger.error(f"Erreur extraction entités essentielles: {e}")
            return {}
    
    def _build_simple_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie simple (version allégée)"""
        
        if not question or not context_entities:
            return question
        
        try:
            # Templates simples par langue
            templates = {
                "fr": "Pour des {breed} de {age}: {question}",
                "en": "For {breed} chickens at {age}: {question}",
                "es": "Para pollos {breed} de {age}: {question}"
            }
            
            template = templates.get(language, templates["fr"])
            
            # Vérifier que les entités critiques sont présentes
            if "breed" in context_entities and "age" in context_entities:
                try:
                    enriched = template.format(
                        breed=context_entities["breed"],
                        age=context_entities["age"],
                        question=question
                    )
                    return enriched
                except KeyError:
                    # Si formatage échoue, retourner original
                    pass
            
            # Fallback: ajouter seulement la race ou l'âge
            if "breed" in context_entities:
                breed_templates = {
                    "fr": f"Pour des {context_entities['breed']}: {question}",
                    "en": f"For {context_entities['breed']} chickens: {question}",
                    "es": f"Para pollos {context_entities['breed']}: {question}"
                }
                return breed_templates.get(language, breed_templates["fr"])
            
            return question
            
        except Exception as e:
            logger.error(f"Erreur construction question enrichie simple: {e}")
            return question
    
    def _get_empty_result(self, question: str) -> Dict[str, Any]:
        """Retourne un résultat vide sécurisé (conservé du code original)"""
        return {
            "question": question,
            "missing_entities": [],
            "context_entities": {},
            "enhancement_info": {
                "ai_used": False,
                "fallback_used": True,
                "pronoun_detected": False,
                "question_enriched": False,
                "original_question": question,
                "technical_context_added": False,
                "missing_context_added": False,
                "variants_tested": [question] if question else [],
                "best_variant_score": 0.0,
                "variant_selection_method": "emergency_fallback"
            }
        }

    # ✅ MÉTHODES CONSERVÉES pour compatibilité (versions simplifiées)
    
    def enhance_question_for_rag_sync(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr",
        missing_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Version synchrone pour compatibilité avec le code existant
        Utilise uniquement le fallback patterns (pas d'IA)
        """
        logger.info("🔄 [RAG Context] Version synchrone - patterns uniquement")
        
        import asyncio
        
        # Créer une boucle d'événements si nécessaire
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Exécuter la version fallback (sans IA)
        return loop.run_until_complete(
            self._enhance_with_fallback_patterns(
                question, conversation_context, language, missing_entities
            )
        )


# ✅ Instance globale (conservé pour compatibilité)
rag_context_enhancer = RAGContextEnhancer()

# ✅ Fonction utilitaire (conservée, mise à jour pour version hybride)
def enhance_question_for_rag(
    question: str, 
    conversation_context: str, 
    language: str = "fr",
    missing_entities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour améliorer une question pour le RAG
    ✅ VERSION HYBRIDE: IA + Fallback patterns
    
    Returns:
        Dict contenant:
        - question: Question optimisée pour RAG
        - missing_entities: Liste des entités manquantes identifiées  
        - context_entities: Dictionnaire des entités extraites du contexte
        - enhancement_info: Métadonnées (incluant ai_used, fallback_used)
    """
    
    import asyncio
    
    # Utiliser la version asynchrone si possible
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            rag_context_enhancer.enhance_question_for_rag(
                question, conversation_context, language, missing_entities
            )
        )
    except Exception as e:
        logger.warning(f"Erreur version async, fallback sync: {e}")
        # Fallback vers version synchrone  
        return rag_context_enhancer.enhance_question_for_rag_sync(
            question, conversation_context, language, missing_entities
        )

# ✅ NOUVEAU: Fonction pour vérifier le statut IA
def get_ai_status() -> Dict[str, Any]:
    """Retourne le statut des services IA"""
    return {
        "ai_available": AI_AVAILABLE,
        "ai_enhancer_initialized": rag_context_enhancer.ai_enhancer is not None,
        "fallback_patterns_loaded": len(rag_context_enhancer._compiled_patterns) > 0,
        "supported_languages": list(rag_context_enhancer._minimal_patterns.keys())
    }