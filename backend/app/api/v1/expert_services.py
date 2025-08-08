"""
expert_services.py - SERVICE EXPERT SIMPLIFIE ET EFFICACE

PHILOSOPHIE SIMPLE:
1. Question -> Peut repondre directement ? -> Reponse avec RAG
2. Question -> Trop vague ? -> Reponse generale + demande clarification  
3. Clarification -> Reponse finale precise avec RAG

COMPOSANTS CONSERVES:
- RAG pour recherche documentaire
- Extraction d'entites basique
- Generation de reponses
- Contexte conversationnel simple

SUPPRIME (trop complexe):
- ClarificationAgent avec IA
- Pipeline IA complexe
- ContextManager lourd
- Logique de classification compliquee

RESULTAT: ~200 lignes au lieu de 1500+, fiable et previsible
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
        
        logger.info("Service Expert Simplifie initialise - Version epuree et efficace")
        logger.info("   Extracteur d'entites: Actif")
        logger.info("   Generateur de reponses: Actif")
        logger.info("   RAG: En attente de configuration")
        logger.info("   Contexte: Memoire simple activee")

    def set_rag_embedder(self, rag_embedder):
        """Configure l'acces au RAG (appele par expert.py)"""
        self.rag_embedder = rag_embedder
        self.config["enable_rag"] = rag_embedder is not None
        logger.info(f"RAG configure: {self.config['enable_rag']}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> SimpleProcessingResult:
        """
        POINT D'ENTREE PRINCIPAL - Logique simple et efficace
        
        Flux simplifie:
        1. Extraire entites
        2. Recuperer contexte conversationnel si disponible
        3. Decider: suffisant pour reponse directe OU clarification necessaire
        4. Generer reponse appropriee avec RAG si possible
        5. Sauvegarder dans historique simple
        """
        start_time = time.time()
        conversation_id = context.get('conversation_id') if context else None
        
        try:
            logger.info(f"[Simple Expert] Question: '{question[:50]}...'")
            if conversation_id:
                logger.info(f"[Simple Expert] Conversation: {conversation_id}")
            
            self.stats["questions_processed"] += 1
            
            # Validation de base
            if not question or len(question.strip()) < 2:
                return self._create_error_result("Question trop courte", start_time, conversation_id)
            
            # 1. EXTRACTION D'ENTITES
            entities = await self._safe_extract_entities(question)
            
            # Detecter le type d'entites retourne et s'adapter
            breed = getattr(entities, 'breed_specific', None) or getattr(entities, 'breed', None) or getattr(entities, 'breed_generic', None)
            age = getattr(entities, 'age_days', None)
            sex = getattr(entities, 'sex', None)
            
            logger.info(f"   Entites: age={age}, race={breed}, sexe={sex}")
            
            # 2. RECUPERATION DU CONTEXTE CONVERSATIONNEL SIMPLE
            conversation_context = self._get_simple_context(conversation_id)
            established_entities = conversation_context.get('established_entities', {})
            
            # 3. ENRICHISSEMENT DES ENTITES AVEC CONTEXTE
            enriched_entities = self._enrich_entities_with_context(entities, established_entities)
            
            # 4. DECISION SIMPLE: Suffisant pour reponse directe ?
            context_sufficient = self._has_enough_context(enriched_entities, question)
            
            if context_sufficient:
                # REPONSE DIRECTE AVEC RAG
                logger.info("   [Simple Expert] Contexte suffisant -> Reponse directe")
                result = await self._generate_direct_answer(question, enriched_entities, conversation_id)
                self.stats["direct_answers"] += 1
            else:
                # REPONSE GENERALE + CLARIFICATION
                logger.info("   [Simple Expert] Contexte insuffisant -> Clarification")
                result = self._generate_clarification_response(question, enriched_entities, conversation_id)
                self.stats["clarifications_requested"] += 1
            
            # 5. SAUVEGARDER DANS HISTORIQUE SIMPLE
            self._save_to_simple_history(conversation_id, question, result, enriched_entities)
            
            processing_time = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time
            
            logger.info(f"[Simple Expert] Reponse: {result.response_type} en {processing_time}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ [Simple Expert] Erreur: {e}")
            self.stats["errors"] += 1
            return self._create_error_result(str(e), start_time, conversation_id)

    async def _safe_extract_entities(self, question: str) -> ExtractedEntities:
        """Extraction d'entités sécurisée avec détection async/sync"""
        try:
            # Essayer la méthode async d'abord
            import asyncio
            if asyncio.iscoroutinefunction(self.entity_extractor.extract):
                return await self.entity_extractor.extract(question)
            else:
                # Méthode synchrone
                return self.entity_extractor.extract(question)
        except Exception as e:
            logger.warning(f"⚠️ [Simple Expert] Erreur extraction: {e}")
            # Fallback vers patterns basiques
            try:
                if hasattr(self.entity_extractor, '_raw_extract_with_patterns'):
                    return self.entity_extractor._raw_extract_with_patterns(question)
            except:
                pass
            # Dernier recours: entités vides
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

    def _enrich_entities_with_context(self, current_entities, established_entities: Dict[str, Any]):
        """Enrichit les entités actuelles avec le contexte établi - Compatible avec tous types d'entités"""
        
        # Si pas d'entités établies, retourner les entités actuelles
        if not established_entities:
            return current_entities
        
        # Travailler avec l'objet tel qu'il est (flexible pour ExtractedEntities ET NormalizedEntities)
        # Enrichir avec le contexte établi si l'entité actuelle est manquante
        age = getattr(current_entities, 'age_days', None)
        if not age and established_entities.get('age_days'):
            if hasattr(current_entities, 'age_days'):
                current_entities.age_days = established_entities['age_days']
            logger.info(f"   🔗 [Enrichissement] Âge du contexte: {established_entities['age_days']}j")
        
        # Gestion flexible des races selon le type d'entités
        breed = (getattr(current_entities, 'breed_specific', None) or 
                getattr(current_entities, 'breed', None) or 
                getattr(current_entities, 'breed_generic', None) or
                getattr(current_entities, 'specific_breed', None) or
                getattr(current_entities, 'generic_breed', None))
        if not breed and established_entities.get('breed'):
            # Essayer de setter sur l'attribut qui existe
            for attr in ['breed_specific', 'breed', 'breed_generic', 'specific_breed', 'generic_breed']:
                if hasattr(current_entities, attr):
                    setattr(current_entities, attr, established_entities['breed'])
                    break
            logger.info(f"   🔗 [Enrichissement] Race du contexte: {established_entities['breed']}")
        
        sex = getattr(current_entities, 'sex', None)
        if not sex and established_entities.get('sex'):
            if hasattr(current_entities, 'sex'):
                current_entities.sex = established_entities['sex']
            logger.info(f"   🔗 [Enrichissement] Sexe du contexte: {established_entities['sex']}")
        
        return current_entities

    def _has_enough_context(self, entities, question: str) -> bool:
        """
        Décision simple: a-t-on assez de contexte pour une réponse directe ?
        Compatible avec ExtractedEntities ET NormalizedEntities
        
        RÈGLES AJUSTÉES pour réponses générales + clarification :
        - Âge ET race spécifique ET sexe (pour questions de poids) = Suffisant pour RAG précis
        - Question technique spécialisée = Suffisant  
        - Tout autre cas = Réponse générale + clarification
        """
        
        # Extraction flexible des attributs selon le type d'entités
        has_age = getattr(entities, 'age_days', None) is not None
        
        # CORRECTION: Gestion plus stricte des races - ignorer les races génériques
        breed_specific = (getattr(entities, 'breed_specific', None) or 
                         getattr(entities, 'breed', None) or 
                         getattr(entities, 'specific_breed', None))
        breed_generic = (getattr(entities, 'breed_generic', None) or 
                        getattr(entities, 'generic_breed', None))
        
        # Ne considérer que les vraies races spécifiques
        has_real_breed = False
        if breed_specific and not any(generic in breed_specific.lower() for generic in ['poulet', 'générique', 'chicken', 'generic']):
            has_real_breed = True
        elif breed_generic and not any(generic in breed_generic.lower() for generic in ['poulet', 'générique', 'chicken', 'generic']):
            has_real_breed = True
        
        has_sex = getattr(entities, 'sex', None) is not None
        is_technical = self._is_technical_question(question)
        is_weight_question = self._mentions_weight_or_growth(question)
        
        # NOUVELLES RÈGLES AJUSTÉES :
        
        # 1. Questions techniques spécialisées = toujours suffisant
        if is_technical:
            return True  
        
        # 2. Questions de poids/croissance = besoin de TOUS les détails pour réponse précise
        if is_weight_question:
            # Pour une réponse RAG précise, il faut âge ET race spécifique ET sexe
            return has_age and has_real_breed and has_sex
        
        # 3. Autres questions = âge + race spécifique suffisant
        if has_age and has_real_breed:
            return True
        
        # 4. Sinon = réponse générale + clarification
        return False

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

    async def _generate_direct_answer(self, question: str, entities,
                                    conversation_id: str) -> SimpleProcessingResult:
        """Génère une réponse directe avec RAG si possible - Compatible avec tous types d'entités"""
        
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
                logger.warning(f"⚠️ [RAG] Erreur recherche: {e}")
        
        # Générer la réponse
        try:
            if rag_used and hasattr(self.response_generator, 'generate_with_rag'):
                # Avec RAG - Méthode asynchrone
                response_data = await self.response_generator.generate_with_rag(
                    question, self._entities_to_dict(entities), 
                    self._create_mock_classification("contextual_answer"), rag_results
                )
            else:
                # Sans RAG - Méthode asynchrone
                response_data = await self.response_generator.generate(
                    question, self._entities_to_dict(entities),
                    self._create_mock_classification("precise_answer")
                )
        except Exception as e:
            logger.warning(f"⚠️ [Simple Expert] Erreur génération: {e}")
            # PRIORITÉ: Utiliser notre fallback RAG intelligent si on a des données RAG
            if rag_used and rag_results:
                logger.info(f"🔧 [Simple Expert] Utilisation fallback RAG intelligent avec {len(rag_results)} documents")
                fallback_response = self._generate_rag_fallback_response(question, entities, rag_results)
                confidence = 0.8  # Confiance élevée car on a des données RAG
            else:
                # Fallback contextuel sans RAG
                age_days = getattr(entities, 'age_days', None)
                breed = (getattr(entities, 'breed_specific', None) or 
                        getattr(entities, 'breed', None) or 
                        getattr(entities, 'specific_breed', None))
                sex = getattr(entities, 'sex', None)
                
                if age_days and breed and sex:
                    logger.info(f"🔧 [Simple Expert] Utilisation fallback contextuel: {breed} {sex} {age_days}j")
                    fallback_response = self._generate_contextual_fallback_response(question, age_days, breed, sex)
                    confidence = 0.7
                else:
                    logger.info(f"🔧 [Simple Expert] Utilisation fallback basique")
                    fallback_response = self._generate_fallback_response(question, entities)
                    confidence = 0.6
            
            response_data = type('MockResponse', (), {
                'response': fallback_response,
                'confidence': confidence
            })()
        
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

    def _generate_clarification_response(self, question: str, entities,
                                       conversation_id: str) -> SimpleProcessingResult:
        """Génère une réponse générale + demande de clarification - Compatible avec tous types d'entités"""
        
        # Analyser ce qui manque (gestion flexible des types d'entités)
        missing = []
        age_days = getattr(entities, 'age_days', None)
        
        # Gestion flexible des races - CORRECTION: ignorer les races génériques
        breed_specific = (getattr(entities, 'breed_specific', None) or 
                         getattr(entities, 'breed', None) or 
                         getattr(entities, 'specific_breed', None))
        breed_generic = (getattr(entities, 'breed_generic', None) or 
                        getattr(entities, 'generic_breed', None))
        
        # CORRECTION CRITIQUE: Ne pas considérer "Poulet générique" comme une vraie race
        has_real_breed = False
        if breed_specific and not any(generic in breed_specific.lower() for generic in ['poulet', 'générique', 'chicken', 'generic']):
            has_real_breed = True
        elif breed_generic and not any(generic in breed_generic.lower() for generic in ['poulet', 'générique', 'chicken', 'generic']):
            has_real_breed = True
        
        sex = getattr(entities, 'sex', None)
        is_weight_question = self._mentions_weight_or_growth(question)
        
        # Analyser ce qui manque selon le type de question
        if not age_days:
            missing.append("l'âge de vos animaux (en jours ou semaines)")
        
        # CORRECTION: Toujours demander la race si ce n'est pas une race spécifique
        if not has_real_breed:
            missing.append("la race ou le type (Ross 308, Cobb 500, pondeuses, etc.)")
        
        if is_weight_question and not sex:
            missing.append("le sexe (mâles, femelles, ou mixte)")
        
        # Réponse générale basique
        general_response = self._generate_general_context_response(question, entities)
        
        # Demande de clarification adaptée
        if missing:
            if is_weight_question:
                if age_days and not has_real_breed and not sex:
                    # Cas comme votre exemple : âge connu, mais manque race ET sexe
                    clarification = f"\n\n💡 **Pour une réponse plus précise**, veuillez préciser la race et le sexe de vos poulets."
                elif age_days and not has_real_breed and sex:
                    # Âge + sexe mais pas de race spécifique
                    clarification = f"\n\n💡 **Pour une réponse plus précise**, veuillez préciser la race (Ross 308, Cobb 500, etc.)."
                elif age_days and has_real_breed and not sex:
                    # Âge + race mais pas de sexe  
                    clarification = f"\n\n💡 **Pour une réponse plus précise**, veuillez préciser le sexe (mâles, femelles, ou mixte)."
                elif len(missing) == 1:
                    clarification = f"\n\n💡 **Pour une réponse plus précise**, précisez {missing[0]}."
                else:
                    clarification = f"\n\n💡 **Pour une réponse plus précise**, précisez :\n"
                    for item in missing:
                        clarification += f"• {item.capitalize()}\n"
                    clarification = clarification.rstrip()
            else:
                # Questions non-poids
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

    def _generate_general_context_response(self, question: str, entities) -> str:
        """Génère une réponse générale contextuelle - Compatible avec tous types d'entités"""
        
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

    def _get_general_weight_response(self, entities) -> str:
        """Réponse générale sur le poids - Compatible avec tous types d'entités"""
        age_days = getattr(entities, 'age_days', None)
        if age_days:
            return f"""**Poids des poulets à {age_days} jours :**

📊 **Fourchettes générales** :
• **Races lourdes** (Ross 308, Cobb 500) : 120-360g
• **Races standard** : 100-145g  
• **Races pondeuses** : 80-120g

🐓 **Différences moyennes** :
• **Mâles** : +10-15% par rapport aux moyennes
• **Femelles** : -10-15% par rapport aux moyennes

🔍 **Surveillance recommandée** :
• Pesée quotidienne d'échantillon représentatif
• Contrôle de l'homogénéité du troupeau
• Ajustement alimentaire selon l'évolution du poids

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

    def _get_general_feeding_response(self, entities) -> str:
        """Réponse générale sur l'alimentation"""
        return """**Alimentation des poulets de chair :**

🍽️ **Programmes alimentaires par phases** :
• **Starter** (0-14j) : 20-22% protéines
• **Grower** (15-28j) : 18-20% protéines
• **Finisher** (29j+) : 16-18% protéines

💧 **Eau** : Accès permanent, 1,8-2,2L par kg d'aliment"""

    def _get_general_health_response(self, entities) -> str:
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

    def _get_general_environment_response(self, entities) -> str:
        """Réponse générale sur l'environnement"""
        return """**Conditions d'ambiance :**

🌡️ **Température** :
• Démarrage : 32-35°C
• Diminution : 2-3°C par semaine
• Finition : 18-21°C

💨 **Ventilation** : 0,8-4 m³/h/kg selon saison"""

    def _get_general_default_response(self, entities) -> str:
        """Réponse générale par défaut"""
        return """**Élevage de poulets de chair :**

🐔 **Points essentiels** :
• Respect des standards selon la race
• Surveillance quotidienne
• Alimentation adaptée aux phases
• Conditions d'ambiance optimales"""

    def _build_rag_query(self, question: str, entities) -> str:
        """Construit une requête optimisée pour le RAG - Compatible avec tous types d'entités"""
        base_query = question
        
        # Enrichir avec les entités disponibles (gestion flexible)
        enrichments = []
        
        # Gestion flexible des races
        breed_specific = (getattr(entities, 'breed_specific', None) or 
                         getattr(entities, 'breed', None) or 
                         getattr(entities, 'specific_breed', None))
        breed_generic = (getattr(entities, 'breed_generic', None) or 
                        getattr(entities, 'generic_breed', None))
        
        if breed_specific:
            enrichments.append(breed_specific)
        elif breed_generic:
            enrichments.append(breed_generic)
        
        age_days = getattr(entities, 'age_days', None)
        if age_days:
            enrichments.append(f"{age_days} jours")
        
        sex = getattr(entities, 'sex', None)
        if sex:
            enrichments.append(sex)
        
        if enrichments:
            return f"{base_query} {' '.join(enrichments)}"
        else:
            return base_query

    def _save_to_simple_history(self, conversation_id: str, question: str, 
                              result: SimpleProcessingResult, entities):
        """Sauvegarde simple dans l'historique conversationnel - Compatible avec tous types d'entités"""
        
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
        
        # Mettre à jour les entités établies (gestion flexible)
        age_days = getattr(entities, 'age_days', None)
        if age_days:
            history['established_entities']['age_days'] = age_days
        
        # Gestion flexible des races
        breed_specific = (getattr(entities, 'breed_specific', None) or 
                         getattr(entities, 'breed', None) or 
                         getattr(entities, 'specific_breed', None))
        breed_generic = (getattr(entities, 'breed_generic', None) or 
                        getattr(entities, 'generic_breed', None))
        
        if breed_specific:
            history['established_entities']['breed'] = breed_specific
        elif breed_generic:
            history['established_entities']['breed'] = breed_generic
        
        sex = getattr(entities, 'sex', None)
        if sex:
            history['established_entities']['sex'] = sex
        
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

    def _entities_to_dict(self, entities) -> Dict[str, Any]:
        """Convertit les entités en dictionnaire - Version flexible compatible avec NormalizedEntities"""
        result = {}
        
        # Extraction flexible selon le type d'entités (ExtractedEntities OU NormalizedEntities)
        result['age_days'] = getattr(entities, 'age_days', None)
        result['age_weeks'] = getattr(entities, 'age_weeks', None)
        
        # Gestion flexible des races selon le type d'entités
        breed_specific = (getattr(entities, 'breed_specific', None) or 
                         getattr(entities, 'breed', None) or 
                         getattr(entities, 'specific_breed', None))
        result['breed_specific'] = breed_specific
        
        breed_generic = (getattr(entities, 'breed_generic', None) or 
                        getattr(entities, 'generic_breed', None))
        result['breed_generic'] = breed_generic
        
        result['sex'] = getattr(entities, 'sex', None)
        result['weight_mentioned'] = getattr(entities, 'weight_mentioned', False)
        result['weight_grams'] = getattr(entities, 'weight_grams', None)
        result['symptoms'] = getattr(entities, 'symptoms', []) or []
        result['context_type'] = getattr(entities, 'context_type', None)
        
        return result

    def _create_mock_classification(self, response_type: str):
        """Crée une classification mock pour la compatibilité"""
        class MockClassification:
            def __init__(self, resp_type):
                self.response_type = type('ResponseType', (), {resp_type: resp_type, 'value': resp_type})()
                self.merged_entities = {}
                self.weight_data = {}
                self.confidence = 0.8
        
        return MockClassification(response_type)

    def _generate_fallback_response(self, question: str, entities) -> str:
        """Génère une réponse de secours basique - Compatible avec tous types d'entités"""
        question_lower = question.lower()
        
        age_days = getattr(entities, 'age_days', None)
        
        if 'poids' in question_lower or 'weight' in question_lower:
            if age_days:
                return f"**Poids indicatif à {age_days} jours :** 300-800g selon la race et le sexe. Pour des valeurs précises, spécifiez la race (Ross 308, Cobb 500...) et le sexe."
            else:
                return "**Poids des poulets de chair :** Les valeurs varient selon l'âge, la race et le sexe. Précisez ces informations pour une réponse personnalisée."
        
        elif 'alimentation' in question_lower or 'nutrition' in question_lower:
            return "**Alimentation des poulets :** Adaptez selon l'âge (starter, grower, finisher) et la race. Précisez votre situation pour des recommandations spécifiques."
        
        elif 'température' in question_lower or 'chauffage' in question_lower:
            return "**Température d'élevage :** Varie selon l'âge des animaux. Démarrage à 32-35°C puis diminution progressive. Précisez l'âge pour des valeurs exactes."
        
        elif 'santé' in question_lower or 'maladie' in question_lower:
            return "**Santé des poulets :** Surveillez quotidiennement le comportement, l'appétit et les signes cliniques. Décrivez les symptômes observés pour un conseil adapté."
        
        else:
            return "**Élevage de poulets de chair :** Je peux vous aider avec des questions sur le poids, l'alimentation, la santé, l'ambiance, etc. Précisez votre question avec l'âge et la race si possible."

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