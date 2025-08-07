"""
expert_services.py - SERVICE EXPERT SIMPLIFIÉ ET EFFICACE

🎯 PHILOSOPHIE SIMPLE:
1. Question → Peut répondre directement ? → Réponse avec RAG
2. Question → Trop vague ? → Réponse générale + demande clarification  
3. Clarification → Réponse finale précise avec RAG

✅ COMPOSANTS CONSERVÉS:
- RAG pour recherche documentaire
- Extraction d'entités basique
- Génération de réponses
- Contexte conversationnel simple

❌ SUPPRIMÉ (trop complexe):
- ClarificationAgent avec IA
- Pipeline IA complexe
- ContextManager lourd
- Logique de classification compliquée

🚀 RÉSULTAT: ~200 lignes au lieu de 1500+, fiable et prévisible
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

# Imports essentiels seulement
from .entities_extractor import EntitiesExtractor, ExtractedEntities
from .unified_response_generator import UnifiedResponseGenerator, ResponseData

logger = logging.getLogger(__name__)

@dataclass
class SimpleProcessingResult:
    """Résultat de traitement simplifié"""
    success: bool
    response: str
    response_type: str
    confidence: float
    processing_time_ms: int
    rag_used: bool = False
    entities: Optional[ExtractedEntities] = None
    conversation_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class SimpleExpertService:
    """Service expert simplifié - logique claire et prévisible"""
    
    def __init__(self):
        """Initialisation simple avec composants essentiels"""
        
        # Composants de base
        self.entity_extractor = EntitiesExtractor()
        self.response_generator = UnifiedResponseGenerator()
        
        # RAG (configuré par l'application)
        self.rag_embedder = None
        
        # Contexte conversationnel simple
        self.conversation_history = {}  # {conversation_id: {questions: [], responses: [], entities: {}}}
        
        # Configuration simple
        self.config = {
            "enable_rag": False,  # Activé quand RAG configuré
            "max_history": 5,     # Nombre max de questions/réponses gardées
            "enable_context": True
        }
        
        # Statistiques simples
        self.stats = {
            "questions_processed": 0,
            "direct_answers": 0,
            "clarifications_requested": 0,
            "rag_searches": 0,
            "errors": 0
        }
        
        logger.info("✅ [Simple Expert Service] Initialisé - Version épurée et efficace")
        logger.info(f"   🔧 Extracteur d'entités: Actif")
        logger.info(f"   🎨 Générateur de réponses: Actif")
        logger.info(f"   🔍 RAG: En attente de configuration")
        logger.info(f"   💾 Contexte: Mémoire simple activée")

    def set_rag_embedder(self, rag_embedder):
        """Configure l'accès au RAG (appelé par expert.py)"""
        self.rag_embedder = rag_embedder
        self.config["enable_rag"] = rag_embedder is not None
        logger.info(f"✅ [Simple Expert Service] RAG configuré: {self.config['enable_rag']}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> SimpleProcessingResult:
        """
        POINT D'ENTRÉE PRINCIPAL - Logique simple et efficace
        
        Flux simplifié:
        1. Extraire entités
        2. Récupérer contexte conversationnel si disponible
        3. Décider: suffisant pour réponse directe OU clarification nécessaire
        4. Générer réponse appropriée avec RAG si possible
        5. Sauvegarder dans historique simple
        """
        start_time = time.time()
        conversation_id = context.get('conversation_id') if context else None
        
        try:
            logger.info(f"🚀 [Simple Expert] Question: '{question[:50]}...'")
            if conversation_id:
                logger.info(f"🔗 [Simple Expert] Conversation: {conversation_id}")
            
            self.stats["questions_processed"] += 1
            
            # Validation de base
            if not question or len(question.strip()) < 2:
                return self._create_error_result("Question trop courte", start_time, conversation_id)
            
            # 1️⃣ EXTRACTION D'ENTITÉS
            entities = await self._safe_extract_entities(question)
            logger.info(f"   🔍 Entités: âge={entities.age_days}, race={entities.breed_specific or entities.breed_generic}, sexe={entities.sex}")
            
            # 2️⃣ RÉCUPÉRATION DU CONTEXTE CONVERSATIONNEL SIMPLE
            conversation_context = self._get_simple_context(conversation_id)
            established_entities = conversation_context.get('established_entities', {})
            
            # 3️⃣ ENRICHISSEMENT DES ENTITÉS AVEC CONTEXTE
            enriched_entities = self._enrich_entities_with_context(entities, established_entities)
            
            # 4️⃣ DÉCISION SIMPLE: Suffisant pour réponse directe ?
            context_sufficient = self._has_enough_context(enriched_entities, question)
            
            if context_sufficient:
                # ✅ RÉPONSE DIRECTE AVEC RAG
                logger.info("   ✅ [Simple Expert] Contexte suffisant → Réponse directe")
                result = await self._generate_direct_answer(question, enriched_entities, conversation_id)
                self.stats["direct_answers"] += 1
            else:
                # 📝 RÉPONSE GÉNÉRALE + CLARIFICATION
                logger.info("   📝 [Simple Expert] Contexte insuffisant → Clarification")
                result = self._generate_clarification_response(question, enriched_entities, conversation_id)
                self.stats["clarifications_requested"] += 1
            
            # 5️⃣ SAUVEGARDER DANS HISTORIQUE SIMPLE
            self._save_to_simple_history(conversation_id, question, result, enriched_entities)
            
            processing_time = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time
            
            logger.info(f"✅ [Simple Expert] Réponse: {result.response_type} en {processing_time}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ [Simple Expert] Erreur: {e}")
            self.stats["errors"] += 1
            return self._create_error_result(str(e), start_time, conversation_id)

    async def _safe_extract_entities(self, question: str) -> ExtractedEntities:
        """Extraction d'entités sécurisée"""
        try:
            return await self.entity_extractor.extract(question)
        except Exception as e:
            logger.warning(f"⚠️ [Simple Expert] Erreur extraction: {e}")
            # Fallback vers entités vides mais valides
            return ExtractedEntities()

    def _get_simple_context(self, conversation_id: str) -> Dict[str, Any]:
        """Récupère le contexte conversationnel simple"""
        if not conversation_id or not self.config["enable_context"]:
            return {}
        
        return self.conversation_history.get(conversation_id, {
            'questions': [],
            'responses': [],
            'established_entities': {}
        })

    def _enrich_entities_with_context(self, current_entities: ExtractedEntities, 
                                    established_entities: Dict[str, Any]) -> ExtractedEntities:
        """Enrichit les entités actuelles avec le contexte établi"""
        
        # Si pas d'entités établies, retourner les entités actuelles
        if not established_entities:
            return current_entities
        
        # Créer une copie enrichie
        enriched = ExtractedEntities()
        
        # Copier les entités actuelles
        for attr in ['age_days', 'age_weeks', 'breed_specific', 'breed_generic', 
                    'sex', 'weight_grams', 'weight_mentioned', 'symptoms', 'context_type']:
            setattr(enriched, attr, getattr(current_entities, attr))
        
        # Enrichir avec le contexte établi si l'entité actuelle est manquante
        if not enriched.age_days and established_entities.get('age_days'):
            enriched.age_days = established_entities['age_days']
            logger.info(f"   🔗 [Enrichissement] Âge du contexte: {enriched.age_days}j")
        
        if not enriched.breed_specific and established_entities.get('breed'):
            enriched.breed_specific = established_entities['breed']
            logger.info(f"   🔗 [Enrichissement] Race du contexte: {enriched.breed_specific}")
        
        if not enriched.sex and established_entities.get('sex'):
            enriched.sex = established_entities['sex']
            logger.info(f"   🔗 [Enrichissement] Sexe du contexte: {enriched.sex}")
        
        return enriched

    def _has_enough_context(self, entities: ExtractedEntities, question: str) -> bool:
        """
        Décision simple: a-t-on assez de contexte pour une réponse directe ?
        
        Critères simples et clairs:
        - Âge ET (race OU question technique) = Suffisant
        - Question technique spécialisée = Suffisant
        - Sinon = Clarification nécessaire
        """
        
        has_age = entities.age_days is not None
        has_breed = entities.breed_specific is not None or entities.breed_generic is not None
        is_technical = self._is_technical_question(question)
        
        # Règles simples
        if is_technical:
            return True  # Questions techniques = toujours suffisant
        
        if has_age and has_breed:
            return True  # Âge + race = suffisant
        
        if has_age and self._mentions_weight_or_growth(question):
            return True  # Âge + question sur poids/croissance = suffisant
        
        return False  # Sinon = clarification

    def _is_technical_question(self, question: str) -> bool:
        """Détecte les questions techniques spécialisées"""
        question_lower = question.lower()
        
        technical_keywords = [
            'température', 'ventilation', 'humidité', 'éclairage', 'densité',
            'vaccination', 'prophylaxie', 'antibiotique', 'maladie',
            'alimentation', 'nutrition', 'starter', 'grower', 'finisher',
            'mortalité', 'ponte', 'reproduction', 'couvaison'
        ]
        
        return any(keyword in question_lower for keyword in technical_keywords)

    def _mentions_weight_or_growth(self, question: str) -> bool:
        """Détecte les questions sur le poids ou la croissance"""
        question_lower = question.lower()
        
        weight_growth_keywords = [
            'poids', 'weight', 'gramme', 'kg', 'croissance', 'growth',
            'développement', 'taille', 'size', 'lourd', 'léger'
        ]
        
        return any(keyword in question_lower for keyword in weight_growth_keywords)

    async def _generate_direct_answer(self, question: str, entities: ExtractedEntities,
                                    conversation_id: str) -> SimpleProcessingResult:
        """Génère une réponse directe avec RAG si possible"""
        
        rag_used = False
        rag_results = []
        
        # Essayer d'utiliser le RAG
        if self.rag_embedder:
            try:
                query = self._build_rag_query(question, entities)
                rag_results = self.rag_embedder.search(query, k=5)
                rag_used = len(rag_results) > 0
                
                if rag_used:
                    logger.info(f"   🔍 [RAG] {len(rag_results)} documents trouvés pour: '{query}'")
                    self.stats["rag_searches"] += 1
                
            except Exception as e:
                logger.warning(f"   ⚠️ [RAG] Erreur recherche: {e}")
        
        # Générer la réponse
        if rag_used and hasattr(self.response_generator, 'generate_with_rag'):
            # Avec RAG
            response_data = await self.response_generator.generate_with_rag(
                question, self._entities_to_dict(entities), 
                self._create_mock_classification("contextual_answer"), rag_results
            )
        else:
            # Sans RAG - réponse classique
            response_data = await self.response_generator.generate(
                question, self._entities_to_dict(entities),
                self._create_mock_classification("precise_answer")
            )
        
        return SimpleProcessingResult(
            success=True,
            response=response_data.response,
            response_type="direct_answer",
            confidence=response_data.confidence,
            processing_time_ms=0,  # Sera mis à jour
            rag_used=rag_used,
            entities=entities,
            conversation_id=conversation_id
        )

    def _generate_clarification_response(self, question: str, entities: ExtractedEntities,
                                       conversation_id: str) -> SimpleProcessingResult:
        """Génère une réponse générale + demande de clarification"""
        
        # Analyser ce qui manque
        missing = []
        if not entities.age_days:
            missing.append("l'âge de vos animaux (en jours ou semaines)")
        if not entities.breed_specific and not entities.breed_generic:
            missing.append("la race ou le type (Ross 308, Cobb 500, pondeuses, etc.)")
        if not entities.sex and self._mentions_weight_or_growth(question):
            missing.append("le sexe (mâles, femelles, ou mixte)")
        
        # Réponse générale basique
        general_response = self._generate_general_context_response(question, entities)
        
        # Demande de clarification
        if missing:
            if len(missing) == 1:
                clarification = f"\n\n💡 **Pour une réponse plus précise**, précisez {missing[0]}."
            else:
                clarification = f"\n\n💡 **Pour une réponse plus précise**, précisez :\n"
                for item in missing:
                    clarification += f"• {item.capitalize()}\n"
                clarification = clarification.rstrip()
        else:
            clarification = "\n\n💡 **Pour une réponse plus précise**, donnez plus de détails sur votre situation."
        
        full_response = general_response + clarification
        
        return SimpleProcessingResult(
            success=True,
            response=full_response,
            response_type="general_with_clarification",
            confidence=0.7,
            processing_time_ms=0,  # Sera mis à jour
            rag_used=False,
            entities=entities,
            conversation_id=conversation_id
        )

    def _generate_general_context_response(self, question: str, entities: ExtractedEntities) -> str:
        """Génère une réponse générale contextuelle"""
        
        question_lower = question.lower()
        
        # Réponses spécialisées selon le type de question
        if self._mentions_weight_or_growth(question):
            return self._get_general_weight_response(entities)
        elif any(word in question_lower for word in ['alimentation', 'nutrition', 'nourrir']):
            return self._get_general_feeding_response(entities)
        elif any(word in question_lower for word in ['santé', 'maladie', 'symptôme']):
            return self._get_general_health_response(entities)
        elif any(word in question_lower for word in ['température', 'chauffage', 'ambiance']):
            return self._get_general_environment_response(entities)
        else:
            return self._get_general_default_response(entities)

    def _get_general_weight_response(self, entities: ExtractedEntities) -> str:
        """Réponse générale sur le poids"""
        if entities.age_days:
            return f"""**Poids des poulets à {entities.age_days} jours :**

Les fourchettes de poids varient selon la race et le sexe :

📊 **Fourchettes générales** :
• Ross 308 : 300-800g (selon sexe)
• Cobb 500 : 290-780g (selon sexe)  
• Hubbard : 280-760g (selon sexe)

⚠️ **Important** : Ces valeurs sont indicatives."""
        else:
            return """**Poids des poulets de chair :**

Le poids varie énormément selon l'âge, la race et le sexe :

📈 **Évolution générale** :
• 7 jours : 150-220g
• 14 jours : 350-550g
• 21 jours : 700-1050g
• 28 jours : 1200-1700g
• 35 jours : 1800-2400g"""

    def _get_general_feeding_response(self, entities: ExtractedEntities) -> str:
        """Réponse générale sur l'alimentation"""
        return """**Alimentation des poulets de chair :**

🍽️ **Programmes alimentaires par phases** :
• **Starter** (0-14j) : 20-22% protéines
• **Grower** (15-28j) : 18-20% protéines
• **Finisher** (29j+) : 16-18% protéines

💧 **Eau** : Accès permanent, 1,8-2,2L par kg d'aliment"""

    def _get_general_health_response(self, entities: ExtractedEntities) -> str:
        """Réponse générale sur la santé"""
        return """**Santé des poulets de chair :**

🏥 **Surveillance quotidienne** :
• Observation du comportement général
• Contrôle consommation eau/aliment
• Vérification signes cliniques

⚠️ **Signaux d'alerte** :
• Mortalité anormale (>1% par semaine)
• Baisse d'appétit ou de croissance
• Symptômes respiratoires ou digestifs"""

    def _get_general_environment_response(self, entities: ExtractedEntities) -> str:
        """Réponse générale sur l'environnement"""
        return """**Conditions d'ambiance :**

🌡️ **Température** :
• Démarrage : 32-35°C
• Diminution : 2-3°C par semaine
• Finition : 18-21°C

💨 **Ventilation** : 0,8-4 m³/h/kg selon saison"""

    def _get_general_default_response(self, entities: ExtractedEntities) -> str:
        """Réponse générale par défaut"""
        return """**Élevage de poulets de chair :**

🐔 **Points essentiels** :
• Respect des standards selon la race
• Surveillance quotidienne
• Alimentation adaptée aux phases
• Conditions d'ambiance optimales"""

    def _build_rag_query(self, question: str, entities: ExtractedEntities) -> str:
        """Construit une requête optimisée pour le RAG"""
        base_query = question
        
        # Enrichir avec les entités disponibles
        enrichments = []
        
        if entities.breed_specific:
            enrichments.append(entities.breed_specific)
        elif entities.breed_generic:
            enrichments.append(entities.breed_generic)
        
        if entities.age_days:
            enrichments.append(f"{entities.age_days} jours")
        
        if entities.sex:
            enrichments.append(entities.sex)
        
        if enrichments:
            return f"{base_query} {' '.join(enrichments)}"
        else:
            return base_query

    def _save_to_simple_history(self, conversation_id: str, question: str, 
                              result: SimpleProcessingResult, entities: ExtractedEntities):
        """Sauvegarde simple dans l'historique conversationnel"""
        
        if not conversation_id or not self.config["enable_context"]:
            return
        
        # Initialiser l'historique si nécessaire
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = {
                'questions': [],
                'responses': [],
                'established_entities': {}
            }
        
        history = self.conversation_history[conversation_id]
        
        # Ajouter question et réponse
        history['questions'].append(question)
        history['responses'].append(result.response)
        
        # Limiter l'historique
        max_history = self.config["max_history"]
        if len(history['questions']) > max_history:
            history['questions'] = history['questions'][-max_history:]
            history['responses'] = history['responses'][-max_history:]
        
        # Mettre à jour les entités établies
        if entities.age_days:
            history['established_entities']['age_days'] = entities.age_days
        if entities.breed_specific:
            history['established_entities']['breed'] = entities.breed_specific
        elif entities.breed_generic:
            history['established_entities']['breed'] = entities.breed_generic
        if entities.sex:
            history['established_entities']['sex'] = entities.sex
        
        logger.debug(f"   💾 [Historique] Sauvegardé pour {conversation_id}")

    def _create_error_result(self, error_msg: str, start_time: float, 
                           conversation_id: str) -> SimpleProcessingResult:
        """Crée un résultat d'erreur"""
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return SimpleProcessingResult(
            success=False,
            response="Je rencontre une difficulté technique. Pouvez-vous reformuler votre question ?",
            response_type="error",
            confidence=0.0,
            processing_time_ms=processing_time,
            rag_used=False,
            entities=None,
            conversation_id=conversation_id,
            error=error_msg
        )

    def _entities_to_dict(self, entities: ExtractedEntities) -> Dict[str, Any]:
        """Convertit les entités en dictionnaire"""
        return {
            'age_days': entities.age_days,
            'age_weeks': entities.age_weeks,
            'breed_specific': entities.breed_specific,
            'breed_generic': entities.breed_generic,
            'sex': entities.sex,
            'weight_mentioned': entities.weight_mentioned,
            'weight_grams': entities.weight_grams,
            'symptoms': entities.symptoms or [],
            'context_type': entities.context_type
        }

    def _create_mock_classification(self, response_type: str):
        """Crée une classification mock pour la compatibilité"""
        class MockClassification:
            def __init__(self, resp_type):
                self.response_type = type('ResponseType', (), {resp_type: resp_type, 'value': resp_type})()
                self.merged_entities = {}
                self.weight_data = {}
                self.confidence = 0.8
        
        return MockClassification(response_type)

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques simples"""
        total = self.stats["questions_processed"]
        
        if total == 0:
            return {
                "service_version": "simple_v1.0",
                "questions_processed": 0,
                "status": "ready"
            }
        
        return {
            "service_version": "simple_v1.0",
            "questions_processed": total,
            "direct_answers": self.stats["direct_answers"],
            "clarifications_requested": self.stats["clarifications_requested"],
            "rag_searches": self.stats["rag_searches"],
            "errors": self.stats["errors"],
            "direct_answer_rate": round((self.stats["direct_answers"] / total) * 100, 2),
            "clarification_rate": round((self.stats["clarifications_requested"] / total) * 100, 2),
            "error_rate": round((self.stats["errors"] / total) * 100, 2),
            "rag_enabled": self.config["enable_rag"],
            "context_enabled": self.config["enable_context"]
        }

    def reset_stats(self):
        """Remet à zéro les statistiques"""
        self.stats = {
            "questions_processed": 0,
            "direct_answers": 0,
            "clarifications_requested": 0,
            "rag_searches": 0,
            "errors": 0
        }

    def get_conversation_history(self, conversation_id: str) -> Dict[str, Any]:
        """Retourne l'historique d'une conversation"""
        return self.conversation_history.get(conversation_id, {})

    def clear_conversation_history(self, conversation_id: str = None):
        """Efface l'historique (toutes les conversations ou une spécifique)"""
        if conversation_id:
            self.conversation_history.pop(conversation_id, None)
            logger.info(f"   🗑️ [Historique] Effacé pour {conversation_id}")
        else:
            self.conversation_history.clear()
            logger.info(f"   🗑️ [Historique] Effacé pour toutes les conversations")

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

async def simple_ask(question: str, conversation_id: str = None, language: str = "fr") -> str:
    """Interface simple pour poser une question"""
    service = SimpleExpertService()
    context = {"conversation_id": conversation_id} if conversation_id else None
    result = await service.process_question(question, context=context, language=language)
    return result.response

def create_simple_expert_service() -> SimpleExpertService:
    """Factory pour créer le service simplifié"""
    return SimpleExpertService()

# =============================================================================
# POINT D'ENTRÉE POUR REMPLACEMENT DIRECT
# =============================================================================

# Alias pour compatibilité avec l'ancienne interface
ExpertService = SimpleExpertService
ProcessingResult = SimpleProcessingResult
quick_ask = simple_ask
create_expert_service = create_simple_expert_service