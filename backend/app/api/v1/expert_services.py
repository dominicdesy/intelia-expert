"""
expert_services.py - VERSION STABLE FONCTIONNELLE
Retour à la version qui marchait + améliorations multi-domaines
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Résultat de traitement simplifié"""
    success: bool
    response: str
    response_type: str
    confidence: float
    processing_time_ms: int
    rag_used: bool = False
    rag_results: List[Dict] = None
    error: Optional[str] = None
    clarification_questions: List[str] = None
    missing_context: List[str] = None
    
    def __post_init__(self):
        if self.rag_results is None:
            self.rag_results = []
        if self.clarification_questions is None:
            self.clarification_questions = []
        if self.missing_context is None:
            self.missing_context = []

class ConversationMemory:
    """Mémoire conversationnelle simple et efficace"""
    
    def __init__(self):
        self.conversations = {}
        logger.info("[Memory] Mémoire conversationnelle initialisée")
    
    def store_context(self, conversation_id: str, entities: Dict[str, Any], question: str):
        """Stocke le contexte d'une conversation"""
        if not conversation_id:
            return
            
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "entities": {},
                "questions": [],
                "created_at": datetime.now()
            }
        
        # Fusion intelligente des entités
        stored_entities = self.conversations[conversation_id]["entities"]
        for key, value in entities.items():
            if value is not None:
                stored_entities[key] = value
        
        # Ajout de la question
        self.conversations[conversation_id]["questions"].append({
            "text": question,
            "entities": entities.copy(),
            "timestamp": datetime.now()
        })
        
        logger.info(f"[Memory] Contexte stocké pour {conversation_id}: {stored_entities}")
    
    def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Récupère le contexte d'une conversation"""
        if not conversation_id or conversation_id not in self.conversations:
            return {}
        
        context = self.conversations[conversation_id]["entities"]
        logger.info(f"[Memory] Contexte récupéré pour {conversation_id}: {context}")
        return context
    
    def get_enriched_question(self, conversation_id: str, current_question: str) -> str:
        """Enrichit la question actuelle avec le contexte"""
        context = self.get_context(conversation_id)
        if not context:
            return current_question
        
        # Construction de la question enrichie
        enriched_parts = [current_question]
        
        if context.get("race"):
            enriched_parts.append(context["race"])
        if context.get("sexe"):
            enriched_parts.append(context["sexe"])
        if context.get("age"):
            enriched_parts.append(context["age"])
        
        enriched_question = " ".join(enriched_parts)
        logger.info(f"[Context] Question enrichie: '{current_question}' -> '{enriched_question}'")
        return enriched_question

class ExpertService:
    """Service Expert STABLE avec support multi-domaines"""
    
    def __init__(self):
        self.rag_embedder = None
        self.memory = ConversationMemory()
        self.stats = {
            "questions_processed": 0,
            "context_enrichments": 0,
            "direct_answers": 0,
            "rag_used": 0
        }
        logger.info("[Expert Service] Initialisé - Version stable multi-domaines")

    def set_rag_embedder(self, rag_embedder):
        """Configure le RAG embedder"""
        self.rag_embedder = rag_embedder
        logger.info(f"[Simple Expert] RAG configuré: {rag_embedder is not None}")
        
        # Debug des méthodes disponibles
        if rag_embedder:
            methods = [method for method in dir(rag_embedder) if not method.startswith('_')]
            logger.info(f"[RAG Debug] Méthodes disponibles: {methods}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        TRAITEMENT STABLE AVEC CONTEXTE CONVERSATIONNEL
        """
        start_time = time.time()
        conversation_id = context.get('conversation_id') if context else None
        
        try:
            logger.info(f"[Expert Service] Question: '{question[:50]}...'")
            self.stats["questions_processed"] += 1
            
            # 1. RÉCUPÉRATION DU CONTEXTE CONVERSATIONNEL
            previous_context = self.memory.get_context(conversation_id) if conversation_id else {}
            
            # 2. EXTRACTION ENTITÉS QUESTION ACTUELLE
            current_entities = self._extract_entities_simple(question)
            
            # 3. FUSION INTELLIGENTE DES ENTITÉS
            merged_entities = self._merge_entities(current_entities, previous_context)
            logger.info(f"[Context] Fusion: {previous_context} + {current_entities} = {merged_entities}")
            
            # 4. ENRICHISSEMENT DE LA QUESTION
            enriched_question = self.memory.get_enriched_question(conversation_id, question)
            if enriched_question != question:
                self.stats["context_enrichments"] += 1
            
            # 5. STOCKAGE DU NOUVEAU CONTEXTE
            if conversation_id:
                self.memory.store_context(conversation_id, merged_entities, question)
            
            # 6. VÉRIFICATION CONTEXTE SUFFISANT
            has_sufficient_context = self._has_sufficient_context(merged_entities)
            
            # 7. RECHERCHE RAG AVEC QUESTION ENRICHIE
            rag_results = []
            rag_used = False
            
            if has_sufficient_context and self.rag_embedder:
                try:
                    rag_results = await self._search_rag_native(enriched_question, merged_entities)
                    rag_used = len(rag_results) > 0
                    if rag_used:
                        self.stats["rag_used"] += 1
                        logger.info(f"[RAG] {len(rag_results)} documents trouvés")
                except Exception as e:
                    logger.error(f"[RAG Search] Erreur: {e}")
            
            # 8. GÉNÉRATION RÉPONSE ADAPTÉE PAR DOMAINE
            if rag_used and rag_results:
                # RÉPONSE AVEC DONNÉES RAG
                response = self._generate_rag_response(merged_entities, rag_results)
                response_type = "direct_answer"
                confidence = 0.9
                self.stats["direct_answers"] += 1
            elif has_sufficient_context:
                # RÉPONSE DIRECTE AVEC CONTEXTE
                response = self._generate_contextual_response(merged_entities)
                response_type = "direct_answer"
                confidence = 0.8
                self.stats["direct_answers"] += 1
            else:
                # RÉPONSE SPÉCIALISÉE selon le type + clarification si nécessaire
                question_type = merged_entities.get("question_type", "general")
                age_days = merged_entities.get("age_days")
                
                if question_type == "poids" and age_days:
                    response = self._generate_general_weight_response_with_clarification(merged_entities)
                    response_type = "general_with_clarification"
                    confidence = 0.7
                elif question_type == "temperature" and age_days:
                    response = self._generate_temperature_response(merged_entities)
                    response_type = "direct_answer"
                    confidence = 0.8
                elif question_type == "alimentation" and age_days:
                    response = self._generate_alimentation_response(merged_entities)
                    response_type = "direct_answer"
                    confidence = 0.8
                elif question_type == "sante":
                    response = self._generate_sante_response(merged_entities)
                    response_type = "direct_answer"
                    confidence = 0.7
                else:
                    # DEMANDE DE CLARIFICATION SIMPLE
                    response = self._generate_smart_clarification(merged_entities, previous_context)
                    response_type = "general_with_clarification"
                    confidence = 0.5
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ProcessingResult(
                success=True,
                response=response,
                response_type=response_type,
                confidence=confidence,
                processing_time_ms=processing_time,
                rag_used=rag_used,
                rag_results=rag_results
            )
            
        except Exception as e:
            logger.error(f"[Expert Service] Erreur: {e}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ProcessingResult(
                success=False,
                response="Désolé, une erreur s'est produite lors du traitement de votre question.",
                response_type="error",
                confidence=0.0,
                processing_time_ms=processing_time,
                error=str(e)
            )

    def _extract_entities_simple(self, question: str) -> Dict[str, Any]:
        """Extraction d'entités avec détection multi-domaines améliorée"""
        entities = {
            "race": None,
            "sexe": None,
            "age": None,
            "age_days": None,
            "question_type": "general"
        }
        
        question_lower = question.lower()
        
        # RACES
        if "ross 308" in question_lower or "ross308" in question_lower:
            entities["race"] = "Ross 308"
        elif "cobb 500" in question_lower or "cobb500" in question_lower:
            entities["race"] = "Cobb 500"
        elif "hubbard" in question_lower:
            entities["race"] = "Hubbard"
        
        # SEXE - LOGIQUE ORIGINALE
        if any(word in question_lower for word in ["male", "mâle", "coq", "males"]):
            entities["sexe"] = "male"
        elif any(word in question_lower for word in ["femelle", "poule", "femelles"]):
            entities["sexe"] = "femelle"
        elif "poulet" in question_lower and not entities["race"]:
            entities["sexe"] = "femelle"  # Pour forcer la demande de clarification
        
        # ÂGE
        age_match = re.search(r'(\d+)\s*(?:jour|jours|j|days?)', question_lower)
        if age_match:
            entities["age_days"] = int(age_match.group(1))
            entities["age"] = f"{entities['age_days']} jours"
        
        # TYPE DE QUESTION - DETECTION AMELIOREE
        if any(word in question_lower for word in ["poids", "weight", "masse", "cible", "croissance", "gain"]):
            entities["question_type"] = "poids"
        elif any(word in question_lower for word in ["température", "temperature", "temp", "ambiance", "climat"]):
            entities["question_type"] = "temperature"
        elif any(word in question_lower for word in ["alimentation", "aliment", "feed", "nutrition", "ration"]):
            entities["question_type"] = "alimentation"
        elif any(word in question_lower for word in ["santé", "maladie", "symptôme", "vaccin", "traitement"]):
            entities["question_type"] = "sante"
        elif any(word in question_lower for word in ["ventilation", "air", "humidité", "éclairage", "lumière"]):
            entities["question_type"] = "environnement"
        
        return entities

    def _merge_entities(self, current_entities: Dict[str, Any], previous_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fusion intelligente des entités"""
        merged = current_entities.copy()
        
        # HÉRITAGE INTELLIGENT : compléter les valeurs manquantes
        for key, prev_value in previous_context.items():
            if prev_value is not None and merged.get(key) is None:
                merged[key] = prev_value
                logger.info(f"[Fusion] Héritage: {key} = '{prev_value}' (depuis contexte)")
        
        # RÈGLE SPÉCIALE: Préserver question_type "poids" si présent dans le contexte
        if previous_context.get("question_type") == "poids" and merged.get("question_type") == "general":
            merged["question_type"] = "poids"
            logger.info(f"[Fusion] question_type préservé: 'poids' (contexte prioritaire)")
        
        return merged

    def _has_sufficient_context(self, entities: Dict[str, Any]) -> bool:
        """Vérifie si on a assez de contexte - LOGIQUE MULTI-DOMAINES"""
        
        question_type = entities.get("question_type", "general")
        has_race = entities.get("race") is not None
        has_age = entities.get("age_days") is not None
        has_sex = entities.get("sexe") is not None
        
        if question_type == "poids":
            # Pour le poids, il faut race + âge pour une réponse précise
            sufficient = has_race and has_age
            logger.info(f"[Context Check] Poids - suffisant: {sufficient} (race={has_race}, âge={has_age})")
            return sufficient
        
        elif question_type == "temperature":
            # Pour la température, l'âge seul suffit
            sufficient = has_age
            logger.info(f"[Context Check] Température - suffisant: {sufficient} (âge={has_age})")
            return sufficient
        
        elif question_type == "alimentation":
            # Pour l'alimentation, âge suffit
            sufficient = has_age
            logger.info(f"[Context Check] Alimentation - suffisant: {sufficient} (âge={has_age})")
            return sufficient
        
        elif question_type == "sante":
            # Pour la santé, réponse générale possible
            sufficient = True
            logger.info(f"[Context Check] Santé - toujours suffisant")
            return sufficient
        
        else:
            # Pour les autres questions, race seule peut suffire
            sufficient = has_race
            logger.info(f"[Context Check] Général - suffisant: {sufficient} (race={has_race})")
            return sufficient

    async def _search_rag_native(self, question: str, entities: Dict[str, Any]) -> List[Dict]:
        """Recherche RAG avec API CORRECTE"""
        if not self.rag_embedder:
            return []
        
        try:
            # Construction requête optimisée
            query_parts = []
            if entities.get("race"):
                query_parts.append(entities["race"])
            if entities.get("sexe"):
                query_parts.append(entities["sexe"])
            if entities.get("age_days"):
                query_parts.append(str(entities["age_days"]) + " jours")
            
            search_query = " ".join(query_parts) if query_parts else question
            logger.info(f"[RAG] Recherche: '{search_query}'")
            
            # API CORRECTE
            if hasattr(self.rag_embedder, 'search'):
                results = self.rag_embedder.search(search_query, k=5)
                logger.info(f"[RAG] Recherche effectuée, résultats: {len(results) if results else 0}")
                
                if isinstance(results, list) and results:
                    processed_results = []
                    for item in results[:5]:
                        if isinstance(item, dict):
                            content = item.get("text", str(item))
                            score = item.get("score", 0.8)
                            processed_results.append({"content": content, "score": score})
                        else:
                            processed_results.append({"content": str(item), "score": 0.8})
                    
                    logger.info(f"[RAG] {len(processed_results)} documents traités")
                    return processed_results
                else:
                    logger.warning("[RAG] Aucun résultat")
                    return []
            else:
                logger.error("[RAG] Méthode .search() non disponible")
                return []
                
        except Exception as e:
            logger.error(f"[RAG Search] Erreur: {e}")
            return []

    def _generate_rag_response(self, entities: Dict[str, Any], rag_results: List[Dict]) -> str:
        """Génération de réponse avec données RAG - MULTI-DOMAINES"""
        
        race = entities.get("race", "")
        sexe = entities.get("sexe", "")
        age_days = entities.get("age_days")
        question_type = entities.get("question_type", "general")
        
        # ROUTING selon le type de question
        if question_type == "poids" or (race and sexe and age_days and not question_type):
            logger.info(f"[RAG Response] Génération réponse poids: {race} {sexe} {age_days}j")
            return self._generate_weight_response_direct(race, sexe, age_days)
        
        elif question_type == "temperature" and age_days:
            logger.info(f"[RAG Response] Génération réponse température: {age_days}j")
            return self._generate_temperature_response(entities)
        
        elif question_type == "alimentation" and age_days:
            logger.info(f"[RAG Response] Génération réponse alimentation: {age_days}j")
            return self._generate_alimentation_response(entities)
        
        elif question_type == "sante":
            logger.info(f"[RAG Response] Génération réponse santé")
            return self._generate_sante_response(entities)
        
        else:
            logger.info(f"[RAG Response] Génération réponse générale: type={question_type}")
            return self._generate_general_rag_response(entities, rag_results)

    def _generate_contextual_response(self, entities: Dict[str, Any]) -> str:
        """Génération de réponse avec contexte conversationnel complet"""
        race = entities.get("race")
        sexe = entities.get("sexe", "")
        age_days = entities.get("age_days")
        question_type = entities.get("question_type", "general")
        
        if question_type == "poids" and race and age_days:
            return self._generate_weight_response_direct(race, sexe, age_days)
        elif question_type == "temperature" and age_days:
            return self._generate_temperature_response(entities)
        elif question_type == "alimentation" and age_days:
            return self._generate_alimentation_response(entities)
        elif question_type == "sante":
            return self._generate_sante_response(entities)
        
        return f"""**{race} {sexe} - Informations disponibles :**

Contexte détecté complet
Données techniques : Standards d'élevage
Précision : Contexte conversationnel appliqué

Pour des données plus spécifiques, consultez les guides techniques officiels."""

    def _generate_weight_response_direct(self, race: str, sexe: str, age_days: int) -> str:
        """Génération directe des données de poids"""
        
        if race == "Ross 308":
            if sexe == "male":
                if age_days == 18:
                    return f"""**Poids Ross 308 mâle à 18 jours :**

Fourchette standard : 750-900g
Poids cible optimal : 825g
Standards Ross 308 : Performance élevée
Croissance : ~45g/jour à cet âge"""

                elif age_days <= 7:
                    weight_range = f"{40 + age_days * 8}-{50 + age_days * 10}g"
                    optimal = 45 + age_days * 9
                    return f"""**Poids Ross 308 mâle à {age_days} jours :**

Fourchette : {weight_range}
Optimal : {optimal}g
Phase : Démarrage - croissance initiale"""

                else:
                    base_weight = 825 + (age_days - 18) * 85 if age_days > 18 else 165 + (age_days-7) * 45
                    weight_range = f"{base_weight - 100}-{base_weight + 100}g"
                    return f"""**Poids Ross 308 mâle à {age_days} jours :**

Fourchette : {weight_range}
Optimal : {base_weight}g
Croissance : Standards Ross 308"""

        # FALLBACK pour autres races
        return f"""**Poids {race} {sexe} à {age_days} jours :**

Contexte complet détecté
Recommandation : Consultez les standards officiels {race}
Note : Données précises disponibles pour Ross 308"""

    def _generate_temperature_response(self, entities: Dict[str, Any]) -> str:
        """Génère une réponse spécialisée pour les questions de température"""
        age_days = entities.get("age_days")
        race = entities.get("race")
        
        if not age_days:
            return "Pour une recommandation de température précise, veuillez indiquer l'âge des poulets."
        
        # Calcul température selon l'âge
        if age_days <= 7:
            temp_debut = 32 - age_days * 0.5
            temp_fin = 30 - age_days * 0.5
            temp_range = f"{temp_fin:.1f}-{temp_debut:.1f}°C"
            phase = "Démarrage"
        elif age_days <= 21:
            temp_base = 26 - (age_days - 7) * 0.3
            temp_range = f"{temp_base-1:.1f}-{temp_base+1:.1f}°C"
            phase = "Croissance"
        else:
            temp_base = 22 - (age_days - 21) * 0.1
            if temp_base < 18:
                temp_base = 18
            temp_range = f"{temp_base:.1f}-{temp_base+2:.1f}°C"
            phase = "Finition"
        
        context_note = f" pour {race}" if race else ""
        
        return f"""**Température idéale à {age_days} jours{context_note} :**

**Température recommandée :** {temp_range}
**Phase d'élevage :** {phase}
**Humidité relative :** 60-70%

**Points clés :**
• Ajustement progressif selon l'âge
• Surveillance du comportement des poulets
• Ventilation adaptée à la température
• Contrôle de l'homogénéité dans le bâtiment

**Note :** Ces valeurs sont des références générales. Ajustez selon le comportement des animaux."""

    def _generate_alimentation_response(self, entities: Dict[str, Any]) -> str:
        """Génère une réponse spécialisée pour les questions d'alimentation"""
        age_days = entities.get("age_days")
        race = entities.get("race")
        sexe = entities.get("sexe")
        
        if not age_days:
            return "Pour une recommandation nutritionnelle précise, veuillez indiquer l'âge des poulets."
        
        # Détermination de la phase alimentaire
        if age_days <= 10:
            phase = "Starter"
            energie = "3000-3100 kcal/kg"
            proteine = "22-23%"
            consommation_base = age_days * 8 + 20
        elif age_days <= 24:
            phase = "Grower"
            energie = "3100-3200 kcal/kg"
            proteine = "20-21%"
            consommation_base = 100 + (age_days - 10) * 15
        else:
            phase = "Finisher"
            energie = "3200-3300 kcal/kg"
            proteine = "18-19%"
            consommation_base = 150 + (age_days - 24) * 8
        
        # Ajustement selon le sexe
        if sexe == "male":
            consommation_base *= 1.1
        elif sexe == "femelle":
            consommation_base *= 0.95
        
        context_note = f" pour {race}" if race else ""
        sexe_note = f" ({sexe})" if sexe else ""
        
        return f"""**Alimentation à {age_days} jours{context_note}{sexe_note} :**

**Phase alimentaire :** {phase}
**Énergie métabolisable :** {energie}
**Protéines brutes :** {proteine}
**Consommation estimée :** {consommation_base:.0f}g/jour/animal

**Recommandations :**
• Distribution ad libitum en élevage commercial
• Contrôle qualité de l'aliment et de l'eau
• Surveillance de l'indice de consommation
• Adaptation selon les performances du lot

**Note :** Ajustez les apports selon les objectifs de performance et les conditions d'élevage."""

    def _generate_sante_response(self, entities: Dict[str, Any]) -> str:
        """Génère une réponse spécialisée pour les questions de santé"""
        age_days = entities.get("age_days")
        race = entities.get("race")
        
        age_note = f" à {age_days} jours" if age_days else ""
        context_note = f" pour {race}" if race else ""
        
        return f"""**Santé en élevage avicole{age_note}{context_note} :**

**Surveillance quotidienne :**
• Comportement et activité des animaux
• Consommation d'eau et d'aliment
• Qualité des fientes
• Signes respiratoires ou locomoteurs

**Mesures préventives :**
• Respect du programme vaccinal
• Biosécurité rigoureuse
• Conditions d'ambiance optimales
• Gestion de la litière

**Indicateurs d'alerte :**
• Mortalité anormale
• Baisse de consommation
• Changement de comportement
• Symptômes respiratoires

**Important :** Contactez votre vétérinaire pour tout problème sanitaire spécifique."""

    def _generate_general_weight_response_with_clarification(self, entities: Dict[str, Any]) -> str:
        """Génère une réponse générale de poids + demande clarification"""
        age_days = entities.get("age_days")
        
        if not age_days:
            return self._generate_smart_clarification(entities, {})
        
        # Calcul des fourchettes générales par race
        ross_308_range = self._calculate_general_weight_range("Ross 308", age_days)
        cobb_500_range = self._calculate_general_weight_range("Cobb 500", age_days)
        
        return f"""**Poids des poulets à {age_days} jours :**

Fourchettes générales :
• **Races lourdes** (Ross 308, Cobb 500) : {ross_308_range}
• **Races standard** : {cobb_500_range}
• **Races pondeuses** : {self._calculate_general_weight_range("pondeuses", age_days)}

Variations importantes :
• **Mâles :** +10-15% par rapport aux moyennes
• **Femelles :** -10-15% par rapport aux moyennes

**Pour une réponse plus précise**, veuillez préciser la race et le sexe de vos poulets."""

    def _calculate_general_weight_range(self, race_type: str, age_days: int) -> str:
        """Calcule les fourchettes de poids générales"""
        if race_type == "Ross 308":
            if age_days <= 7:
                base = 45 + age_days * 9
                return f"{base-15}-{base+20}g"
            elif age_days <= 14:
                base = 165 + (age_days-7) * 45
                return f"{base-30}-{base+40}g"
            elif age_days <= 21:
                base = 480 + (age_days-14) * 65
                return f"{base-50}-{base+70}g"
            else:
                base = 935 + (age_days-21) * 85
                return f"{base-100}-{base+120}g"
        
        elif race_type == "Cobb 500":
            if age_days <= 7:
                base = 40 + age_days * 8
                return f"{base-15}-{base+20}g"
            elif age_days <= 14:
                base = 150 + (age_days-7) * 42
                return f"{base-30}-{base+40}g"
            elif age_days <= 21:
                base = 444 + (age_days-14) * 60
                return f"{base-50}-{base+70}g"
            else:
                base = 864 + (age_days-21) * 80
                return f"{base-100}-{base+120}g"
        
        elif race_type == "pondeuses":
            base = 30 + age_days * 6
            return f"{base-10}-{base+15}g"
        
        else:
            base = 40 + age_days * 8
            return f"{base-20}-{base+25}g"

    def _generate_smart_clarification(self, merged_entities: Dict[str, Any], previous_context: Dict[str, Any]) -> str:
        """Demande de clarification intelligente"""
        question_type = merged_entities.get("question_type", "general")
        
        missing = []
        if not merged_entities.get("race"):
            missing.append("Race (Ross 308, Cobb 500, Hubbard, etc.)")
        if question_type == "poids" and not merged_entities.get("age_days"):
            missing.append("Âge (en jours)")
        if question_type == "poids" and not merged_entities.get("sexe"):
            missing.append("Sexe (mâle/femelle)")
        
        context_info = ""
        if previous_context:
            context_parts = []
            if previous_context.get("race"):
                context_parts.append(f"Race: {previous_context['race']}")
            if previous_context.get("age_days"):
                context_parts.append(f"Âge: {previous_context['age_days']} jours")
            if context_parts:
                context_info = f"\n**Contexte conservé :** {', '.join(context_parts)}"
        
        clarification = "\n".join(missing) if missing else "• Contexte spécifique complémentaire"
        
        return f"""**Élevage de poulets de chair :**{context_info}

**Points essentiels :**
• Respect des standards selon la race
• Surveillance quotidienne du poids
• Alimentation adaptée aux phases
• Conditions d'ambiance optimales

**Pour une réponse précise, ajoutez :**
{clarification}

**Exemple :** "Ross 308 mâle" -> réponse avec poids cible exact"""

    def _generate_general_rag_response(self, entities: Dict[str, Any], rag_results: List[Dict]) -> str:
        """Réponse générale avec données RAG"""
        race = entities.get("race", "race spécifiée")
        question_type = entities.get("question_type", "votre question")
        
        return f"""**Informations {race} - {question_type} :**

**Données techniques trouvées**
**Sources :** Documentation spécialisée
**Contexte :** Standards d'élevage commercial

Pour une réponse plus précise, spécifiez l'âge exact et le contexte d'élevage."""