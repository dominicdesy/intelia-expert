# app/api/v1/agent_rag_enhancer.py
"""
Agent RAG Enhancer - Amélioration des réponses après RAG

🎯 FONCTIONNALITÉS:
- Adapte les réponses RAG selon le contexte utilisateur
- Vérifie la cohérence entre question enrichie et réponse RAG
- Ajoute des avertissements si informations manquantes
- Propose des clarifications optionnelles
- Améliore la lisibilité et la pertinence
- ✅ CORRECTION: Propagation systématique de tous les champs
- ✅ CORRECTION: Gestion des champs absents avec valeurs par défaut
- ✅ FIX: Validation défensive et standardisation nomenclature
- ✅ NOUVEAU: Correction rag_used et injection enriched_question
"""

import os
import logging
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import OpenAI sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

logger = logging.getLogger(__name__)

class AgentRAGEnhancer:
    """Agent intelligent pour améliorer les réponses RAG"""
    
    def __init__(self):
        self.openai_available = OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('RAG_ENHANCER_MODEL', 'gpt-4o-mini')
        self.timeout = int(os.getenv('RAG_ENHANCER_TIMEOUT', '15'))
        self.max_retries = int(os.getenv('RAG_ENHANCER_RETRIES', '2'))
        
        # Statistiques
        self.stats = {
            "total_requests": 0,
            "openai_success": 0,
            "openai_failures": 0,
            "fallback_used": 0,
            "answers_enhanced": 0,
            "clarifications_generated": 0,
            "coherence_checks": 0,
            "coherence_issues_detected": 0,
            "field_propagation_success": 0,
            "field_propagation_fallback": 0,
            "input_validation_fixes": 0,
            "rag_used_corrections": 0,  # ✅ NOUVEAU: Tracking corrections rag_used
            "enriched_question_injections": 0  # ✅ NOUVEAU: Tracking injections enriched_question
        }
        
        logger.info(f"🔧 [AgentRAGEnhancer] Initialisé")
        logger.info(f"   OpenAI disponible: {'✅' if self.openai_available else '❌'}")
        logger.info(f"   Modèle: {self.model}")
    
    def _validate_and_sanitize_inputs(
        self,
        entities: Dict[str, Any],
        missing_entities: List[str],
        original_question: str,
        enriched_question: str,
        language: str
    ) -> tuple:
        """
        ✅ FIX: Validation défensive des inputs pour éviter les erreurs
        """
        
        validation_fixes = 0
        
        # Validation entities
        if entities is None:
            entities = {}
            validation_fixes += 1
            logger.debug("🔧 [AgentRAGEnhancer] entities était None, initialisé à {}")
        elif not isinstance(entities, dict):
            entities = {}
            validation_fixes += 1
            logger.warning(f"⚠️ [AgentRAGEnhancer] entities n'était pas un dict: {type(entities)}")
        
        # Validation missing_entities
        if missing_entities is None:
            missing_entities = []
            validation_fixes += 1
            logger.debug("🔧 [AgentRAGEnhancer] missing_entities était None, initialisé à []")
        elif not isinstance(missing_entities, list):
            missing_entities = []
            validation_fixes += 1
            logger.warning(f"⚠️ [AgentRAGEnhancer] missing_entities n'était pas une liste: {type(missing_entities)}")
        
        # Validation strings
        if not isinstance(original_question, str):
            original_question = str(original_question) if original_question is not None else ""
            validation_fixes += 1
        
        if not isinstance(enriched_question, str):
            enriched_question = str(enriched_question) if enriched_question is not None else ""
            validation_fixes += 1
        
        if not isinstance(language, str) or language not in ["fr", "en", "es"]:
            language = "fr"
            validation_fixes += 1
        
        if validation_fixes > 0:
            self.stats["input_validation_fixes"] += validation_fixes
            logger.debug(f"🔧 [AgentRAGEnhancer] {validation_fixes} corrections d'input appliquées")
        
        return entities, missing_entities, original_question, enriched_question, language
    
    def _check_and_fix_rag_used(
        self, 
        response_data: Dict[str, Any], 
        rag_results: List[Dict] = None,
        has_rag_context: bool = False
    ) -> Dict[str, Any]:
        """
        ✅ NOUVEAU: Vérifie et corrige le flag rag_used selon les résultats RAG
        
        Args:
            response_data: Données de réponse à corriger
            rag_results: Résultats du système RAG (FAISS/Pinecone)
            has_rag_context: Indicateur si contexte RAG présent
            
        Returns:
            response_data corrigé avec rag_used approprié
        """
        
        original_rag_used = response_data.get("rag_used", False)
        
        # Détection si RAG a été utilisé
        rag_was_used = False
        
        # Cas 1: Résultats RAG explicites fournis
        if rag_results and len(rag_results) > 0:
            rag_was_used = True
            logger.debug(f"🔍 [AgentRAGEnhancer] RAG détecté via rag_results: {len(rag_results)} résultats")
        
        # Cas 2: Contexte RAG détecté
        elif has_rag_context:
            rag_was_used = True
            logger.debug("🔍 [AgentRAGEnhancer] RAG détecté via has_rag_context")
        
        # Cas 3: Indices dans la réponse
        elif response_data.get("enhanced_answer") or response_data.get("answer"):
            answer_text = response_data.get("enhanced_answer") or response_data.get("answer", "")
            
            # Rechercher des indices de contexte RAG dans la réponse
            rag_indicators = [
                "selon la documentation",
                "d'après les informations",
                "based on documentation",
                "according to the information",
                "les données indiquent",
                "the data indicates",
                "documents consultés",
                "consulted documents"
            ]
            
            if any(indicator in answer_text.lower() for indicator in rag_indicators):
                rag_was_used = True
                logger.debug("🔍 [AgentRAGEnhancer] RAG détecté via indicateurs dans la réponse")
        
        # Cas 4: Sources ou citations présentes
        if response_data.get("sources") or response_data.get("citations"):
            rag_was_used = True
            logger.debug("🔍 [AgentRAGEnhancer] RAG détecté via sources/citations")
        
        # Correction si nécessaire
        if rag_was_used and not original_rag_used:
            response_data["rag_used"] = True
            self.stats["rag_used_corrections"] += 1
            logger.info("✅ [AgentRAGEnhancer] Correction: rag_used passé de False à True")
        
        elif not rag_was_used and original_rag_used:
            # Cas rare: flag rag_used était True mais pas d'évidence RAG
            logger.warning("⚠️ [AgentRAGEnhancer] rag_used=True mais pas d'évidence RAG détectée")
            # On garde True par sécurité mais on log
        
        return response_data
    
    def _inject_enriched_question(
        self, 
        response_data: Dict[str, Any], 
        original_question: str,
        context_entities: Dict[str, Any] = None,
        rag_results: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        ✅ NOUVEAU: Génère et injecte enriched_question si manquant
        
        Args:          response_data: Données de réponse
            original_question: Question originale utilisateur
            context_entities: Entités extraites du contexte
            rag_results: Résultats RAG pour enrichissement
            
        Returns:
            response_data avec enriched_question injecté
        """
        
        # Vérifier si enriched_question existe déjà
        existing_enriched = response_data.get("enriched_question", "").strip()
        
        if existing_enriched and existing_enriched != original_question:
            # enriched_question déjà présent et différent
            logger.debug("✅ [AgentRAGEnhancer] enriched_question déjà présent")
            return response_data
        
        # Générer enriched_question
        enriched_question = self._enrich_question_with_context(
            original_question, context_entities, rag_results
        )
        
        # Injecter si différent de la question originale
        if enriched_question and enriched_question.strip() != original_question.strip():
            response_data["enriched_question"] = enriched_question
            self.stats["enriched_question_injections"] += 1
            logger.info("✅ [AgentRAGEnhancer] enriched_question injecté")
            logger.debug(f"   Original: {original_question}")
            logger.debug(f"   Enrichie: {enriched_question}")
        else:
            # Pas d'enrichissement possible ou identique
            response_data["enriched_question"] = original_question
            logger.debug("🔄 [AgentRAGEnhancer] enriched_question = original (pas d'enrichissement)")
        
        return response_data
    
    def _enrich_question_with_context(
        self,
        original_question: str,
        entities: Dict[str, Any] = None,
        rag_results: List[Dict] = None
    ) -> str:
        """
        ✅ NOUVEAU: Enrichit une question avec le contexte disponible
        
        Args:
            original_question: Question originale
            entities: Entités extraites du contexte
            rag_results: Résultats RAG pour contexte supplémentaire
            
        Returns:
            Question enrichie avec contexte
        """
        
        if not original_question:
            return ""
        
        enriched_parts = [original_question]
        context_additions = []
        
        # Enrichissement via entités
        if entities:
            # Race/souche
            if entities.get("breed") and entities.get("breed_confidence", 0) > 0.6:
                context_additions.append(f"race {entities['breed']}")
            
            # Âge
            if entities.get("age_days") and entities.get("age_confidence", 0) > 0.6:
                weeks = entities.get("age_weeks", entities["age_days"] / 7)
                context_additions.append(f"âge {entities['age_days']} jours ({weeks:.1f} semaines)")
            
            # Poids (nomenclature standardisée)
            weight_grams = entities.get("weight_grams") or entities.get("weight")
            if weight_grams and entities.get("weight_confidence", 0) > 0.5:
                context_additions.append(f"poids {weight_grams}g")
            
            # Sexe
            if entities.get("sex") and entities.get("sex_confidence", 0) > 0.6:
                context_additions.append(f"sexe {entities['sex']}")
            
            # Symptômes
            if entities.get("symptoms"):
                symptoms = ", ".join(entities["symptoms"]) if isinstance(entities["symptoms"], list) else str(entities["symptoms"])
                context_additions.append(f"symptômes: {symptoms}")
            
            # Environnement critique
            if entities.get("temperature") and (entities["temperature"] < 18 or entities["temperature"] > 30):
                context_additions.append(f"température {entities['temperature']}°C")
            
            if entities.get("mortality_rate") and entities["mortality_rate"] > 2:
                context_additions.append(f"mortalité {entities['mortality_rate']}%")
        
        # Enrichissement via résultats RAG
        if rag_results and len(rag_results) > 0:
            # Extraire thèmes principaux des résultats RAG
            rag_themes = set()
            for result in rag_results[:3]:  # Top 3 résultats
                content = result.get("content", "").lower()
                
                # Détecter thèmes importants
                theme_keywords = {
                    "vaccination": ["vaccin", "vaccination", "immunisation"],
                    "nutrition": ["alimentation", "nutrition", "aliment"],
                    "croissance": ["croissance", "poids", "développement"],
                    "santé": ["maladie", "symptôme", "diagnostic"],
                    "environnement": ["température", "ventilation", "logement"]
                }
                
                for theme, keywords in theme_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        rag_themes.add(theme)
            
            if rag_themes:
                themes_text = ", ".join(list(rag_themes)[:2])  # Max 2 thèmes
                context_additions.append(f"contexte: {themes_text}")
        
        # Construire question enrichie
        if context_additions:
            context_text = " - " + " - ".join(context_additions)
            enriched_question = original_question + context_text
            
            # Limiter la longueur
            if len(enriched_question) > 200:
                # Garder les éléments les plus importants
                priority_additions = [add for add in context_additions 
                                    if any(word in add for word in ["race", "âge", "poids", "symptômes"])]
                if priority_additions:
                    context_text = " - " + " - ".join(priority_additions[:2])
                    enriched_question = original_question + context_text
                else:
                    enriched_question = original_question  # Fallback
            
            return enriched_question
        
        return original_question
    
    async def enhance_rag_answer(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        original_question: str = "",
        enriched_question: str = "",
        language: str = "fr",
        rag_results: List[Dict] = None,  # ✅ NOUVEAU: Paramètre rag_results
        **additional_fields  # ✅ Capture tous les champs supplémentaires
    ) -> Dict[str, Any]:
        """
        Améliore une réponse RAG avec le contexte utilisateur et vérifie la cohérence
        ✅ NOUVEAU: Corrections automatiques rag_used et enriched_question
        
        Args:
            rag_answer: Réponse brute du système RAG
            entities: Entités extraites du contexte
            missing_entities: Entités manquantes critiques
            conversation_context: Contexte conversationnel
            original_question: Question originale posée
            enriched_question: Question enrichie par le pré-RAG
            language: Langue de la conversation
            rag_results: Résultats du système RAG (NOUVEAU)
            **additional_fields: Tous les champs supplémentaires à propager
            
        Returns:
            Dict avec tous les champs requis garantis, corrections rag_used/enriched_question
        """
        
        self.stats["total_requests"] += 1
        self.stats["coherence_checks"] += 1
        
        # ✅ FIX: Validation défensive des inputs dès le début
        entities, missing_entities, original_question, enriched_question, language = (
            self._validate_and_sanitize_inputs(
                entities, missing_entities, original_question, enriched_question, language
            )
        )
        
        # ✅ FIX: Validation rag_answer et rag_results
        if not isinstance(rag_answer, str):
            rag_answer = str(rag_answer) if rag_answer is not None else ""
        
        if not isinstance(conversation_context, str):
            conversation_context = str(conversation_context) if conversation_context is not None else ""
        
        if rag_results is None:
            rag_results = []
        elif not isinstance(rag_results, list):
            rag_results = []
        
        try:
            # ✅ CORRECTION: Initialiser le résultat avec TOUS les champs requis
            base_result = self._initialize_complete_result(
                rag_answer, entities, missing_entities, original_question, 
                enriched_question, language, additional_fields
            )
            
            # ✅ NOUVEAU: Corrections automatiques AVANT traitement OpenAI
            # 1. Corriger rag_used selon les résultats RAG
            base_result = self._check_and_fix_rag_used(
                base_result, rag_results, bool(conversation_context or rag_answer)
            )
            
            # 2. Injecter enriched_question si manquant/inadéquat
            base_result = self._inject_enriched_question(
                base_result, original_question, entities, rag_results
            )
            
            # Tentative OpenAI si disponible
            if self.openai_available:
                enhancement_result = await self._enhance_with_openai(
                    rag_answer, entities, missing_entities, conversation_context, 
                    original_question, base_result.get("enriched_question", original_question), language
                )
                
                if enhancement_result.get("success"):
                    # ✅ CORRECTION: Fusionner avec le résultat de base pour garantir tous les champs
                    final_result = self._merge_results(base_result, enhancement_result)
                    self.stats["openai_success"] += 1
                    self.stats["field_propagation_success"] += 1
                    
                    # ✅ NOUVEAU: Réappliquer les corrections après OpenAI (au cas où)
                    final_result = self._check_and_fix_rag_used(final_result, rag_results, True)
                    
                    # Mise à jour des statistiques
                    if final_result["enhanced_answer"] != rag_answer:
                        self.stats["answers_enhanced"] += 1
                    if final_result.get("optional_clarifications"):
                        self.stats["clarifications_generated"] += 1
                    if final_result.get("coherence_check") in ["partial", "poor"]:
                        self.stats["coherence_issues_detected"] += 1
                    
                    return final_result
                else:
                    self.stats["openai_failures"] += 1
            
            # Fallback: Amélioration basique avec tous les champs
            logger.info("🔄 [AgentRAGEnhancer] Utilisation fallback basique")
            fallback_result = self._enhance_fallback(
                rag_answer, entities, missing_entities, 
                original_question, base_result.get("enriched_question", original_question), language
            )
            
            # ✅ CORRECTION: Fusionner avec le résultat de base
            final_result = self._merge_results(base_result, fallback_result)
            self.stats["fallback_used"] += 1
            self.stats["field_propagation_fallback"] += 1
            
            # ✅ NOUVEAU: Garantir corrections finales
            final_result = self._check_and_fix_rag_used(final_result, rag_results, True)
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur critique inattendue: {e}")
            
            # ✅ CORRECTION: Même en cas d'erreur, retourner un résultat complet avec corrections
            error_result = self._initialize_complete_result(
                rag_answer, entities, missing_entities, original_question, 
                enriched_question, language, additional_fields
            )
            
            # ✅ NOUVEAU: Appliquer corrections même en cas d'erreur
            error_result = self._check_and_fix_rag_used(error_result, rag_results, bool(rag_answer))
            error_result = self._inject_enriched_question(error_result, original_question, entities, rag_results)
            
            error_result.update({
                "enhanced_answer": rag_answer,
                "warnings": [f"Erreur amélioration: {str(e)}"],
                "confidence_impact": "unknown",
                "coherence_check": "unknown",
                "coherence_notes": "Impossible de vérifier la cohérence en raison d'une erreur",
                "method_used": "error_fallback",
                "success": False
            })
            
            return error_result
    
    def _initialize_complete_result(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        original_question: str,
        enriched_question: str,
        language: str,
        additional_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ FIX: Initialise un résultat complet avec TOUS les champs requis
        Nomenclature standardisée sur weight_grams
        """
        
        # Champs de base toujours présents
        base_result = {
            # Champs de réponse principaux
            "enhanced_answer": rag_answer,
            "optional_clarifications": [],
            "warnings": [],
            "confidence_impact": "medium",
            "coherence_check": "unknown",
            "coherence_notes": "En cours d'évaluation",
            "improvement_notes": "Traitement en cours",
            "method_used": "initializing",
            "success": True,
            
            # Champs d'entrée propagés
            "original_question": original_question,
            "enriched_question": enriched_question,  # Sera corrigé si nécessaire
            "language": language,
            
            # Champs contextuels
            "entities": entities,
            "missing_entities": missing_entities,
            
            # ✅ NOUVEAU: Champ rag_used (sera corrigé par _check_and_fix_rag_used)
            "rag_used": False,  # Valeur par défaut, sera corrigée
            
            # Champs techniques
            "processing_time": datetime.now().isoformat(),
            "entities_considered": len([k for k, v in entities.items() if v is not None]),
            "missing_entities_count": len(missing_entities),
            
            # ✅ FIX: Standardisation nomenclature weight_grams
            "weight_grams": None,  # ✅ CHANGÉ: weight -> weight_grams
            "weight_confidence": None,
            "age_days": None,
            "age_weeks": None,
            "age_confidence": None,
            "breed": None,
            "breed_confidence": None,
            "sex": None,
            "sex_confidence": None,
            "symptoms": None,
            "mortality_rate": None,
            "temperature": None,
            "housing_type": None,
            "flock_size": None,
            
            # Champs d'évaluation technique
            "context_relevance": "unknown",
            "technical_accuracy": "unknown",
            "practical_applicability": "unknown",
            
            # ✅ NOUVEAU: Champs d'extraction automatique
            "detected_weight_grams": None,  # ✅ Poids détecté dans la réponse
            "detected_age_days": None,      # ✅ Âge détecté dans la réponse
            "detected_breed": None,         # ✅ Race détectée dans la réponse
            "extraction_confidence": 0.0    # ✅ Confiance dans l'extraction
        }
        
        # ✅ CORRECTION: Propager les valeurs des entités si disponibles
        if entities:
            # ✅ FIX: Mapping standardisé weight_grams
            entity_mapping = {
                "weight_grams": "weight_grams",  # ✅ Standardisé
                "weight": "weight_grams",        # ✅ Compatibilité ancienne nomenclature
                "age_days": "age_days",
                "age_weeks": "age_weeks", 
                "breed": "breed",
                "sex": "sex",
                "symptoms": "symptoms",
                "mortality_rate": "mortality_rate",
                "temperature": "temperature",
                "housing_type": "housing_type",
                "flock_size": "flock_size"
            }
            
            for entity_key, result_key in entity_mapping.items():
                if entity_key in entities and entities[entity_key] is not None:
                    base_result[result_key] = entities[entity_key]
            
            # Propager les champs de confiance
            confidence_fields = ["weight_confidence", "age_confidence", "breed_confidence", "sex_confidence"]
            for field in confidence_fields:
                if field in entities and entities[field] is not None:
                    base_result[field] = entities[field]
        
        # ✅ CORRECTION: Propager tous les champs supplémentaires fournis
        if additional_fields:
            for key, value in additional_fields.items():
                if key not in base_result:  # Éviter d'écraser les champs de base
                    base_result[key] = value
                elif value is not None:  # Remplacer les None par des valeurs réelles
                    base_result[key] = value
        
        # ✅ NOUVEAU: Extraction automatique de données implicites
        base_result.update(self._extract_implicit_data(rag_answer, entities))
        
        logger.debug(f"🔧 [AgentRAGEnhancer] Résultat initialisé avec {len(base_result)} champs")
        
        return base_result
    
    def _extract_implicit_data(self, text: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ NOUVEAU: Extrait des données implicites du texte (poids, âge, race)
        """
        
        implicit_data = {
            "detected_weight_grams": None,
            "detected_age_days": None,
            "detected_breed": None,
            "extraction_confidence": 0.0
        }
        
        extractions_count = 0
        
        try:
            # Extraction poids (grammes/kg)
            weight_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:g|gr|grammes?|grams?)\b',
                r'(\d+(?:\.\d+)?)\s*(?:kg|kilogrammes?|kilograms?)\b',
                r'poids(?:.*?)(\d+(?:\.\d+)?)\s*(?:g|kg)',
                r'weight(?:.*?)(\d+(?:\.\d+)?)\s*(?:g|kg)'
            ]
            
            for pattern in weight_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    weight = float(match.group(1))
                    # Convertir kg en grammes
                    if 'kg' in pattern.lower() or weight < 10:
                        weight *= 1000
                    implicit_data["detected_weight_grams"] = int(weight)
                    extractions_count += 1
                    break
            
            # Extraction âge (jours/semaines)
            age_patterns = [
                r'(\d+)\s*(?:jours?|days?)\b',
                r'(\d+)\s*(?:semaines?|weeks?)\b',
                r'âge(?:.*?)(\d+)',
                r'age(?:.*?)(\d+)'
            ]
            
            for pattern in age_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    age = int(match.group(1))
                    # Convertir semaines en jours
                    if 'semaine' in pattern.lower() or 'week' in pattern.lower():
                        age *= 7
                    implicit_data["detected_age_days"] = age
                    extractions_count += 1
                    break
            
            # Extraction race
            breed_patterns = [
                r'\b(Ross\s*\d+)\b',
                r'\b(Cobb\s*\d+)\b',
                r'\b(Hubbard)\b',
                r'\b(Arbor\s*Acres?)\b'
            ]
            
            for pattern in breed_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    implicit_data["detected_breed"] = match.group(1).strip()
                    extractions_count += 1
                    break
            
            # Calculer confiance d'extraction
            if extractions_count > 0:
                implicit_data["extraction_confidence"] = min(extractions_count / 3.0, 1.0)
                logger.debug(f"🔍 [AgentRAGEnhancer] {extractions_count} données extraites automatiquement")
        
        except Exception as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur extraction implicite: {e}")
        
        return implicit_data
    
    def _merge_results(self, base_result: Dict[str, Any], enhancement_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ Fusionne les résultats en préservant tous les champs
        """
        
        # Commencer avec le résultat de base complet
        merged = base_result.copy()
        
        # Mettre à jour avec les améliorations, en préservant les valeurs non-None existantes
        for key, value in enhancement_result.items():
            if value is not None:  # Seulement écraser si la nouvelle valeur n'est pas None
                merged[key] = value
            elif key not in merged:  # Ajouter les nouveaux champs même s'ils sont None
                merged[key] = value
        
        # S'assurer que certains champs critiques sont présents
        required_fields = [
            "enhanced_answer", "optional_clarifications", "warnings", 
            "confidence_impact", "coherence_check", "coherence_notes", 
            "method_used", "success", "rag_used", "enriched_question"  # ✅ AJOUTÉ: rag_used, enriched_question
        ]
        
        for field in required_fields:
            if field not in merged:
                merged[field] = None
        
        return merged
    
    async def _enhance_with_openai(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        original_question: str,
        enriched_question: str,
        language: str
    ) -> Dict[str, Any]:
        """Amélioration avec OpenAI GPT"""
        
        try:
            # Préparer le contexte pour GPT
            entities_summary = self._format_entities_for_gpt(entities)
            missing_summary = ", ".join(missing_entities) if missing_entities else "Aucune"
            
            # Prompt spécialisé selon la langue
            system_prompt = self._get_system_prompt(language)
            user_prompt = self._build_enhancement_prompt(
                rag_answer, entities_summary, missing_summary, conversation_context,
                original_question, enriched_question, language
            )
            
            # Appel OpenAI
            client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Parser la réponse JSON
            result = self._parse_gpt_response(answer, rag_answer, entities, missing_entities)
            result["success"] = True
            result["method_used"] = "openai"
            
            logger.info(f"✅ [AgentRAGEnhancer] Amélioration OpenAI réussie")
            logger.debug(f"   Clarifications générées: {len(result.get('optional_clarifications', []))}")
            logger.debug(f"   Cohérence: {result.get('coherence_check', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur OpenAI: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_system_prompt(self, language: str) -> str:
        """Retourne le prompt système selon la langue"""
        
        system_prompts = {
            "fr": """Tu es un expert vétérinaire en aviculture spécialisé dans l'adaptation de réponses techniques.

Ta mission:
1. Vérifier la cohérence entre la question enrichie et la réponse RAG
2. Adapter la réponse RAG pour qu'elle soit pertinente malgré les informations manquantes
3. Ajouter des avertissements si l'absence de données affecte la précision
4. Proposer 1-3 questions de clarification pour améliorer le conseil
5. Garder un ton professionnel mais accessible
6. Prioriser la sécurité des animaux

VÉRIFICATION DE COHÉRENCE:
- "good": La réponse RAG correspond parfaitement à la question enrichie
- "partial": La réponse RAG est pertinente mais incomplète ou tangentielle
- "poor": La réponse RAG ne correspond pas bien à la question enrichie

IMPORTANT: 
- Si des informations critiques manquent, le mentionner clairement
- Si la réponse RAG semble hors-sujet, l'adapter ou le signaler
- Proposer des questions de clarification utiles, pas évidentes
- Éviter les conseils dangereux sans contexte complet
- Répondre UNIQUEMENT en JSON avec la structure exacte demandée""",
            
            "en": """You are a poultry veterinary expert specialized in adapting technical responses.

Your mission:
1. Verify coherence between enriched question and RAG response
2. Adapt the RAG response to be relevant despite missing information
3. Add warnings if missing data affects accuracy
4. Propose 1-3 clarification questions to improve advice
5. Keep professional but accessible tone
6. Prioritize animal safety

COHERENCE CHECK:
- "good": RAG response perfectly matches the enriched question
- "partial": RAG response is relevant but incomplete or tangential
- "poor": RAG response doesn't match well with the enriched question

IMPORTANT:
- If critical information is missing, mention it clearly
- If RAG response seems off-topic, adapt it or flag it
- Propose useful clarification questions, not obvious ones
- Avoid dangerous advice without complete context
- Respond ONLY in JSON with the exact requested structure""",
            
            "es": """Eres un experto veterinario en avicultura especializado en adaptar respuestas técnicas.

Tu misión:
1. Verificar la coherencia entre la pregunta enriquecida y la respuesta RAG
2. Adaptar la respuesta RAG para que sea relevante a pesar de la información faltante
3. Agregar advertencias si los datos faltantes afectan la precisión
4. Proponer 1-3 preguntas de aclaración para mejorar el consejo
5. Mantener tono profesional pero accesible
6. Priorizar la seguridad de los animales

VERIFICACIÓN DE COHERENCIA:
- "good": La respuesta RAG coincide perfectamente con la pregunta enriquecida
- "partial": La respuesta RAG es relevante pero incompleta o tangencial
- "poor": La respuesta RAG no coincide bien con la pregunta enriquecida

IMPORTANTE:
- Si falta información crítica, mencionarlo claramente
- Si la respuesta RAG parece fuera de tema, adaptarla o señalarlo
- Proponer preguntas de aclaración útiles, no obvias
- Evitar consejos peligrosos sin contexto completo
- Responder SOLO en JSON con la estructura exacta solicitada"""
        }
        
        return system_prompts.get(language, system_prompts["fr"])
    
    def _build_enhancement_prompt(
        self,
        rag_answer: str,
        entities_summary: str,
        missing_summary: str,
        conversation_context: str,
        original_question: str,
        enriched_question: str,
        language: str
    ) -> str:
        """Construit le prompt d'amélioration avec vérification de cohérence"""
        
        if language == "fr":
            return f"""QUESTION ORIGINALE: "{original_question}"

QUESTION ENRICHIE (générée par le pré-RAG): "{enriched_question}"

RÉPONSE RAG BRUTE:
"{rag_answer}"

ENTITÉS CONNUES:
{entities_summary}

ENTITÉS MANQUANTES CRITIQUES: {missing_summary}

CONTEXTE CONVERSATIONNEL:
{conversation_context}

INSTRUCTIONS:
1. COHÉRENCE: Compare la question enrichie avec la réponse RAG. La réponse traite-t-elle bien le sujet de la question enrichie ?
2. Adapte la réponse pour le contexte spécifique de l'utilisateur
3. Si des informations critiques manquent, ajoute un avertissement et explique l'impact
4. Si la réponse RAG ne correspond pas bien à la question enrichie, corrige ou signale le problème
5. Améliore la lisibilité et la structure de la réponse
6. Propose 1-3 questions de clarification pertinentes (pas évidentes)
7. Garde la précision technique mais rends accessible

EXEMPLE VÉRIFICATION COHÉRENCE:
Question enrichie: "Évaluation poids poulet Ross 308, 21 jours, croissance normale ?"
Réponse RAG: "Les poulets doivent peser 800g à 3 semaines"
Cohérence: "partial" - répond au poids mais ignore la race spécifique et l'évaluation de normalité

Réponds en JSON:
{{
  "enhanced_answer": "réponse adaptée et améliorée",
  "optional_clarifications": ["Question précise 1?", "Question précise 2?"],
  "warnings": ["Avertissement si info manquante impacte conseil"],
  "confidence_impact": "low/medium/high selon impact infos manquantes",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "explication détaillée de la cohérence entre question enrichie et réponse RAG",
  "improvement_notes": "explications des améliorations apportées"
}}"""
        
        elif language == "en":
            return f"""ORIGINAL QUESTION: "{original_question}"

ENRICHED QUESTION (generated by pre-RAG): "{enriched_question}"

RAW RAG RESPONSE:
"{rag_answer}"

KNOWN ENTITIES:
{entities_summary}

MISSING CRITICAL ENTITIES: {missing_summary}

CONVERSATIONAL CONTEXT:
{conversation_context}

INSTRUCTIONS:
1. COHERENCE: Compare enriched question with RAG response. Does the response properly address the enriched question's topic?
2. Adapt response for user's specific context
3. If critical information missing, add warning and explain impact
4. If RAG response doesn't match well with enriched question, correct or flag the issue
5. Improve readability and structure of response
6. Propose 1-3 relevant clarification questions (not obvious ones)
7. Keep technical accuracy but make accessible

EXAMPLE COHERENCE CHECK:
Enriched question: "Ross 308 chicken weight evaluation, 21 days, normal growth?"
RAG response: "Chickens should weigh 800g at 3 weeks"
Coherence: "partial" - addresses weight but ignores specific breed and normality evaluation

Respond in JSON:
{{
  "enhanced_answer": "adapted and improved response",
  "optional_clarifications": ["Specific question 1?", "Specific question 2?"],
  "warnings": ["Warning if missing info impacts advice"],
  "confidence_impact": "low/medium/high based on missing info impact",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "detailed explanation of coherence between enriched question and RAG response",
  "improvement_notes": "explanations of improvements made"
}}"""
        
        else:  # Spanish
            return f"""PREGUNTA ORIGINAL: "{original_question}"

PREGUNTA ENRIQUECIDA (generada por pre-RAG): "{enriched_question}"

RESPUESTA RAG BRUTA:
"{rag_answer}"

ENTIDADES CONOCIDAS:
{entities_summary}

ENTIDADES CRÍTICAS FALTANTES: {missing_summary}

CONTEXTO CONVERSACIONAL:
{conversation_context}

INSTRUCCIONES:
1. COHERENCIA: Compara la pregunta enriquecida con la respuesta RAG. ¿La respuesta aborda adecuadamente el tema de la pregunta enriquecida?
2. Adapta la respuesta para el contexto específico del usuario
3. Si falta información crítica, agrega advertencia y explica el impacto
4. Si la respuesta RAG no coincide bien con la pregunta enriquecida, corrige o señala el problema
5. Mejora la legibilidad y estructura de la respuesta
6. Propone 1-3 preguntas de aclaración relevantes (no obvias)
7. Mantén precisión técnica pero hazla accesible

EJEMPLO VERIFICACIÓN COHERENCIA:
Pregunta enriquecida: "Evaluación peso pollo Ross 308, 21 días, crecimiento normal?"
Respuesta RAG: "Los pollos deben pesar 800g a las 3 semanas"
Coherencia: "partial" - aborda el peso pero ignora la raza específica y evaluación de normalidad

Responde en JSON:
{{
  "enhanced_answer": "respuesta adaptada y mejorada",
  "optional_clarifications": ["Pregunta específica 1?", "Pregunta específica 2?"],
  "warnings": ["Advertencia si info faltante impacta consejo"],
  "confidence_impact": "low/medium/high según impacto info faltante",
  "coherence_check": "good/partial/poor",
  "coherence_notes": "explicación detallada de la coherencia entre pregunta enriquecida y respuesta RAG",
  "improvement_notes": "explicaciones de mejoras realizadas"
}}"""
    
    def _format_entities_for_gpt(self, entities: Dict[str, Any]) -> str:
        """✅ FIX: Formate les entités pour le prompt GPT - nomenclature standardisée"""
        
        formatted_parts = []
        
        # Informations de base avec niveaux de confiance
        if entities.get("breed"):
            confidence = entities.get("breed_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            formatted_parts.append(f"{status} Race: {entities['breed']} (confiance: {confidence:.1f})")
        else:
            formatted_parts.append("❌ Race: inconnue")
        
        if entities.get("sex"):
            confidence = entities.get("sex_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            formatted_parts.append(f"{status} Sexe: {entities['sex']} (confiance: {confidence:.1f})")
        else:
            formatted_parts.append("❌ Sexe: inconnu")
        
        if entities.get("age_days"):
            confidence = entities.get("age_confidence", 0.0)
            status = "✅" if confidence > 0.7 else "⚠️" if confidence > 0.4 else "❌"
            weeks = entities.get("age_weeks", entities["age_days"] / 7)
            formatted_parts.append(f"{status} Âge: {entities['age_days']} jours ({weeks:.1f} semaines)")
        else:
            formatted_parts.append("❌ Âge: inconnu")
        
        # ✅ FIX: Poids standardisé sur weight_grams
        weight_grams = entities.get("weight_grams") or entities.get("weight")  # Compatibilité
        if weight_grams:
            confidence = entities.get("weight_confidence", 0.0)
            status = "✅" if confidence > 0.6 else "⚠️"
            formatted_parts.append(f"{status} Poids actuel: {weight_grams}g")
        else:
            formatted_parts.append("❌ Poids: inconnu")
        
        # Performance et santé
        if entities.get("symptoms"):
            symptoms = ", ".join(entities["symptoms"]) if isinstance(entities["symptoms"], list) else str(entities["symptoms"])
            formatted_parts.append(f"🚨 Symptômes observés: {symptoms}")
        
        if entities.get("mortality_rate") is not None:
            rate = entities["mortality_rate"]
            status = "🚨" if rate > 5 else "⚠️" if rate > 2 else "✅"
            formatted_parts.append(f"{status} Mortalité: {rate}%")
        
        # Environnement
        if entities.get("temperature"):
            temp = entities["temperature"]
            status = "🚨" if temp < 18 or temp > 30 else "✅"
            formatted_parts.append(f"{status} Température: {temp}°C")
        
        if entities.get("housing_type"):
            formatted_parts.append(f"🏠 Logement: {entities['housing_type']}")
        
        if entities.get("flock_size"):
            formatted_parts.append(f"👥 Taille troupeau: {entities['flock_size']}")
        
        return "\n".join(formatted_parts) if formatted_parts else "Aucune information contextuelle disponible"
    
    def _parse_gpt_response(
        self, 
        response: str, 
        original_answer: str, 
        entities: Dict[str, Any], 
        missing_entities: List[str]
    ) -> Dict[str, Any]:
        """Parse la réponse JSON de GPT avec vérification de cohérence"""
        
        try:
            # Extraction JSON robuste
            json_match = None
            
            # Patterns améliorés pour extraction JSON robuste
            json_patterns = [
                r'```json\s*({.*?})\s*```',
                r'```\s*({.*?})\s*```',
                r'({(?:[^{}]|{[^{}]*})*})'
            ]
            
            for pattern in json_patterns:
                match = re.search(pattern, response, re.DOTALL | re.MULTILINE)
                if match:
                    json_match = match.group(1)
                    break
            
            if not json_match:
                raise ValueError("Pas de JSON trouvé dans la réponse")
            
            # Parser le JSON
            data = json.loads(json_match)
            
            # Valider et enrichir la réponse
            enhanced_answer = data.get("enhanced_answer", original_answer)
            optional_clarifications = data.get("optional_clarifications", [])
            warnings = data.get("warnings", [])
            
            # Validation de la cohérence
            coherence_check = data.get("coherence_check", "unknown")
            if coherence_check not in ["good", "partial", "poor"]:
                coherence_check = "unknown"
            
            coherence_notes = data.get("coherence_notes", "")
            if not coherence_notes:
                coherence_notes = f"Cohérence évaluée comme: {coherence_check}"
            
            # Validation des clarifications (max 3, non vides)
            if isinstance(optional_clarifications, list):
                optional_clarifications = [q.strip() for q in optional_clarifications if q and q.strip()]
                optional_clarifications = optional_clarifications[:3]
            else:
                optional_clarifications = []
            
            # Validation des avertissements
            if isinstance(warnings, list):
                warnings = [w.strip() for w in warnings if w and w.strip()]
                warnings = warnings[:2]  # Max 2 avertissements
            else:
                warnings = []
            
            # Déterminer l'impact sur la confiance
            confidence_impact = data.get("confidence_impact", "medium")
            if confidence_impact not in ["low", "medium", "high"]:
                confidence_impact = "medium"
            
            result = {
                "enhanced_answer": enhanced_answer,
                "optional_clarifications": optional_clarifications,
                "warnings": warnings,
                "confidence_impact": confidence_impact,
                "coherence_check": coherence_check,
                "coherence_notes": coherence_notes,
                "improvement_notes": data.get("improvement_notes", "Améliorations appliquées"),
                "method_used": "openai",
                "processing_time": datetime.now().isoformat(),
                "entities_considered": len([k for k, v in (entities or {}).items() if v is not None]),
                "missing_entities_count": len(missing_entities or [])
            }
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"❌ [AgentRAGEnhancer] Erreur parsing JSON: {e}")
            logger.debug(f"   Réponse GPT: {response}")
            
            # Fallback: chercher des améliorations dans le texte brut
            if len(response) > len(original_answer) and response != original_answer:
                # Extraire des clarifications potentielles du texte
                clarifications = []
                question_patterns = [r'([^.!?]*\?)', r'pourriez-vous[^.!?]*\?', r'pouvez-vous[^.!?]*\?']
                
                for pattern in question_patterns:
                    matches = re.findall(pattern, response, re.IGNORECASE)
                    for match in matches[:2]:  # Max 2
                        if len(match.strip()) > 10:
                            clarifications.append(match.strip())
                
                return {
                    "enhanced_answer": response.strip(),
                    "optional_clarifications": clarifications,
                    "warnings": ["Réponse générée automatiquement - vérifiez la pertinence"],
                    "confidence_impact": "medium",
                    "coherence_check": "unknown",
                    "coherence_notes": "Impossible de vérifier la cohérence - JSON parsing échoué",
                    "improvement_notes": "JSON parsing failed, used raw GPT response",
                    "method_used": "openai_fallback"
                }
            else:
                # Fallback complet
                return self._enhance_fallback(original_answer, entities, missing_entities, "", "", "fr")
    
    def _enhance_fallback(
        self,
        rag_answer: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        original_question: str,
        enriched_question: str,
        language: str
    ) -> Dict[str, Any]:
        """Amélioration fallback sans OpenAI avec vérification basique de cohérence"""
        
        enhanced_answer = rag_answer
        warnings = []
        clarifications = []
        
        # Vérification basique de cohérence améliorée
        coherence_check = "unknown"
        coherence_notes = "Vérification automatique basique"
        
        if enriched_question and original_question:
            # Vérification de cohérence améliorée
            enriched_words = set(word.lower() for word in enriched_question.split() if len(word) > 2)
            answer_words = set(word.lower() for word in rag_answer.split() if len(word) > 2)
            
            # Mots de stop à ignorer
            stop_words = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'est', 'sont', 'the', 'and', 'or', 'is', 'are', 'a', 'an', 'of', 'to', 'in', 'for'}
            enriched_words -= stop_words
            answer_words -= stop_words
            
            # Mots-clés importants communs
            important_words = enriched_words.intersection(answer_words)
            important_words = {w for w in important_words if len(w) > 3 or w in ['âge', 'age', 'sex', 'sexe', 'kg', 'gr']}
            
            total_important_words = len(enriched_words.union(answer_words))
            
            if total_important_words > 0:
                similarity_ratio = len(important_words) / total_important_words
                
                if similarity_ratio >= 0.3:
                    coherence_check = "good"
                    coherence_notes = f"Réponse cohérente (similarité: {similarity_ratio:.1f}, mots-clés: {', '.join(list(important_words)[:3])})"
                elif similarity_ratio >= 0.15:
                    coherence_check = "partial"
                    coherence_notes = f"Cohérence partielle (similarité: {similarity_ratio:.1f}, mots-clés: {', '.join(important_words)})"
                else:
                    coherence_check = "poor"
                    coherence_notes = f"Faible cohérence (similarité: {similarity_ratio:.1f})"
            else:
                coherence_check = "poor"
                coherence_notes = "Aucun mot-clé significatif en commun"
        
        # Ajouter des avertissements selon les entités manquantes
        if "breed" in missing_entities:
            if language == "fr":
                warnings.append("⚠️ Sans connaître la race exacte, cette réponse est générale. Les performances varient selon la souche.")
                clarifications.append("Quelle est la race/souche de vos volailles ?")
            elif language == "en":
                warnings.append("⚠️ Without knowing the exact breed, this response is general. Performance varies by strain.")
                clarifications.append("What is the breed/strain of your poultry?")
            else:  # Spanish
                warnings.append("⚠️ Sin conocer la raza exacta, esta respuesta es general. El rendimiento varía según la cepa.")
                clarifications.append("¿Cuál es la raza/cepa de sus aves?")
        
        if "age" in missing_entities:
            if language == "fr":
                warnings.append("⚠️ L'âge est crucial pour évaluer la normalité des paramètres.")
                clarifications.append("Quel est l'âge de vos volailles (en jours ou semaines) ?")
            elif language == "en":
                warnings.append("⚠️ Age is crucial for evaluating parameter normality.")
                clarifications.append("What is the age of your poultry (in days or weeks)?")
            else:  # Spanish
                warnings.append("⚠️ La edad es crucial para evaluar la normalidad de los parámetros.")
                clarifications.append("¿Cuál es la edad de sus aves (en días o semanas)?")
        
        if "sex" in missing_entities and any(word in rag_answer.lower() for word in ["poids", "weight", "peso", "croissance", "growth"]):
            if language == "fr":
                clarifications.append("S'agit-il de mâles, femelles, ou d'un troupeau mixte ?")
            elif language == "en":
                clarifications.append("Are these males, females, or a mixed flock?")
            else:  # Spanish
                clarifications.append("¿Son machos, hembras, o un lote mixto?")
        
        # Déterminer l'impact sur la confiance
        confidence_impact = "low"
        if len(missing_entities) >= 2:
            confidence_impact = "high"
        elif len(missing_entities) == 1:
            confidence_impact = "medium"
        
        # Ajouter un contexte si des entités sont connues
        context_additions = []
        if entities.get("breed") and entities.get("breed_confidence", 0) > 0.6:
            context_additions.append(f"race {entities['breed']}")
        
        if entities.get("age_days") and entities.get("age_confidence", 0) > 0.6:
            context_additions.append(f"âge {entities['age_days']} jours")
        
        if context_additions:
            context_text = " et ".join(context_additions)
            if language == "fr":
                enhanced_answer += f"\n\n💡 Cette réponse considère votre contexte : {context_text}."
            elif language == "en":
                enhanced_answer += f"\n\n💡 This response considers your context: {context_text}."
            else:  # Spanish
                enhanced_answer += f"\n\n💡 Esta respuesta considera su contexto: {context_text}."
        
        # Ajouter les avertissements à la réponse si critiques
        if warnings and confidence_impact in ["medium", "high"]:
            enhanced_answer += f"\n\n{' '.join(warnings)}"
        
        return {
            "enhanced_answer": enhanced_answer,
            "optional_clarifications": clarifications[:3],
            "warnings": warnings,
            "confidence_impact": confidence_impact,
            "coherence_check": coherence_check,
            "coherence_notes": coherence_notes,
            "improvement_notes": "Amélioration basique appliquée",
            "method_used": "fallback"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """✅ FIX: Retourne les statistiques enrichies de l'agent"""
        
        total = self.stats["total_requests"]
        success_rate = (self.stats["openai_success"] / total * 100) if total > 0 else 0
        enhancement_rate = (self.stats["answers_enhanced"] / total * 100) if total > 0 else 0
        clarification_rate = (self.stats["clarifications_generated"] / total * 100) if total > 0 else 0
        coherence_issue_rate = (self.stats["coherence_issues_detected"] / total * 100) if total > 0 else 0
        field_propagation_success_rate = (self.stats["field_propagation_success"] / total * 100) if total > 0 else 0
        input_validation_rate = (self.stats["input_validation_fixes"] / total * 100) if total > 0 else 0
        rag_used_correction_rate = (self.stats["rag_used_corrections"] / total * 100) if total > 0 else 0  # ✅ NOUVEAU
        enriched_question_injection_rate = (self.stats["enriched_question_injections"] / total * 100) if total > 0 else 0  # ✅ NOUVEAU
        
        return {
            "agent_type": "rag_enhancer",
            "total_requests": total,
            "openai_success_rate": f"{success_rate:.1f}%",
            "answer_enhancement_rate": f"{enhancement_rate:.1f}%",
            "clarification_generation_rate": f"{clarification_rate:.1f}%",
            "coherence_issue_detection_rate": f"{coherence_issue_rate:.1f}%",
            "field_propagation_success_rate": f"{field_propagation_success_rate:.1f}%",
            "input_validation_fixes_rate": f"{input_validation_rate:.1f}%",
            "rag_used_correction_rate": f"{rag_used_correction_rate:.1f}%",  # ✅ NOUVEAU
            "enriched_question_injection_rate": f"{enriched_question_injection_rate:.1f}%",  # ✅ NOUVEAU
            "openai_available": self.openai_available,
            "model_used": self.model,
            "detailed_stats": self.stats.copy()
        }

# Instance globale
agent_rag_enhancer = AgentRAGEnhancer()

# ✅ FIX: Fonction utilitaire avec validation défensive et nouvelles corrections
async def enhance_rag_answer(
    rag_answer: str,
    entities: Dict[str, Any] = None,  # ✅ FIX: Valeur par défaut None
    missing_entities: List[str] = None,  # ✅ FIX: Valeur par défaut None
    conversation_context: str = "",
    original_question: str = "",
    enriched_question: str = "",
    language: str = "fr",
    rag_results: List[Dict] = None,  # ✅ NOUVEAU: Paramètre rag_results
    **additional_fields
) -> Dict[str, Any]:
    """
    ✅ FIX: Fonction utilitaire avec validation défensive, propagation complète 
    et corrections automatiques rag_used/enriched_question
    
    NOUVELLES FONCTIONNALITÉS:
    - Détection et correction automatique du flag rag_used
    - Génération et injection automatique d'enriched_question
    - Propagation systématique de tous les champs
    - Validation défensive des inputs
    
    Args:
        rag_answer: Réponse brute du système RAG
        entities: Entités extraites (défaut: {})
        missing_entities: Entités manquantes (défaut: [])
        conversation_context: Contexte conversationnel
        original_question: Question originale utilisateur
        enriched_question: Question enrichie (sera générée si manquante)
        language: Langue de conversation
        rag_results: Résultats FAISS/Pinecone (NOUVEAU)
        **additional_fields: Champs supplémentaires à propager
        
    Returns:
        Dict complet avec corrections rag_used et enriched_question garanties
    """
    return await agent_rag_enhancer.enhance_rag_answer(
        rag_answer, 
        entities or {}, 
        missing_entities or [], 
        conversation_context, 
        original_question, 
        enriched_question, 
        language,
        rag_results or [],  # ✅ NOUVEAU: Passer rag_results
        **additional_fields
    )

# ✅ NOUVEAU: Fonction utilitaire pour corriger response_data existant
def fix_rag_response_data(
    response_data: Dict[str, Any],
    rag_results: List[Dict] = None,
    original_question: str = "",
    entities: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    ✅ NOUVEAU: Corrige un response_data existant avec rag_used et enriched_question
    
    Usage dans les endpoints existants:
    ```python
    # Après avoir généré la réponse RAG
    response_data = fix_rag_response_data(
        response_data=response_data,
        rag_results=rag_results,
        original_question=query,
        entities=context_entities
    )
    ```
    
    Args:
        response_data: Données de réponse à corriger
        rag_results: Résultats du système RAG
        original_question: Question originale
        entities: Entités du contexte
        
    Returns:
        response_data corrigé avec rag_used et enriched_question
    """
    
    if not isinstance(response_data, dict):
        logger.warning("⚠️ [fix_rag_response_data] response_data n'est pas un dict")
        return response_data
    
    # 1. Corriger rag_used
    corrected_data = agent_rag_enhancer._check_and_fix_rag_used(
        response_data, rag_results, bool(response_data.get("answer") or response_data.get("enhanced_answer"))
    )
    
    # 2. Injecter enriched_question si nécessaire
    corrected_data = agent_rag_enhancer._inject_enriched_question(
        corrected_data, original_question, entities, rag_results
    )
    
    logger.debug("✅ [fix_rag_response_data] Corrections appliquées")
    return corrected_data

# ✅ NOUVEAU: Exemple d'intégration dans un endpoint
"""
EXEMPLE D'UTILISATION DANS UN ENDPOINT:

```python
@app.post("/api/v1/expert/ask")
async def ask_expert_question(request: QuestionRequest):
    # ... logique existante ...
    
    # Recherche RAG
    rag_results = await rag_system.search(enriched_query)
    
    # Génération réponse
    rag_answer = await llm.generate_answer(enriched_query, rag_results)
    
    # Construction response_data initial
    response_data = {
        "answer": rag_answer,
        "rag_used": False,  # ❌ Incorrect - sera corrigé
        "original_question": request.question,
        # enriched_question manquant - sera injecté
        **other_fields
    }
    
    # ✅ CORRECTION AUTOMATIQUE
    response_data = fix_rag_response_data(
        response_data=response_data,
        rag_results=rag_results,
        original_question=request.question,
        entities=extracted_entities
    )
    
    # Maintenant response_data a:
    # - rag_used: True (si rag_results non vide)
    # - enriched_question: question enrichie générée
    # - tous les autres champs préservés
    
    return response_data
```

ALTERNATIVE - Utilisation complète de enhance_rag_answer:

```python
@app.post("/api/v1/expert/ask")  
async def ask_expert_question(request: QuestionRequest):
    # ... logique existante ...
    
    # Recherche RAG
    rag_results = await rag_system.search(enriched_query)
    rag_answer = await llm.generate_answer(enriched_query, rag_results)
    
    # ✅ AMÉLIORATION COMPLÈTE avec toutes les corrections
    enhanced_response = await enhance_rag_answer(
        rag_answer=rag_answer,
        entities=extracted_entities,
        missing_entities=missing_entities,
        conversation_context=conversation_context,
        original_question=request.question,
        enriched_question="",  # Sera généré automatiquement
        language=request.language,
        rag_results=rag_results,  # ✅ IMPORTANT: Passer les résultats RAG
        # Tous les champs supplémentaires
        user_id=request.user_id,
        session_id=request.session_id,
        sources=extracted_sources,
        **other_fields
    )
    
    # enhanced_response contient TOUT avec corrections garanties
    return enhanced_response
```
"""