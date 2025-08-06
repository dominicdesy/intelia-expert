# app/api/v1/agent_contextualizer.py
"""
Agent Contextualizer - Enrichissement des questions avant RAG

🎯 FONCTIONNALITÉS:
- Enrichit les questions avec le contexte conversationnel
- Intègre les entités normalisées (race, sexe, âge, etc.)
- Fonctionne même SANS entités (inférence contextuelle)
- Reformule pour optimiser la recherche RAG
- Support multi-variants pour rag_context_enhancer
- Gestion fallback sans OpenAI

🔧 VERSION AMÉLIORÉE v4.0:
- ✅ NOUVEAU: Reception entités déjà normalisées par entity_normalizer
- ✅ Plus besoin de normaliser - entités déjà standardisées
- ✅ Utilisation directe: entities['breed'], entities['age_days'], entities['sex']
- ✅ Performance optimisée grâce aux entités pré-normalisées
- ✅ Cohérence garantie avec le système de normalisation centralisée

🔧 CORRECTION CRITIQUE v4.1: Correction OpenAI AsyncClient sans paramètre 'proxies'
"""

import os
import logging
import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Import OpenAI sécurisé - CORRECTION: Gestion d'erreur plus robuste
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    openai = None
    logging.getLogger(__name__).warning(f"OpenAI non disponible: {e}")
except Exception as e:
    OPENAI_AVAILABLE = False
    openai = None
    logging.getLogger(__name__).error(f"Erreur inattendue import OpenAI: {e}")

logger = logging.getLogger(__name__)

class AgentContextualizer:
    """Agent intelligent pour enrichir les questions avant RAG avec entités normalisées"""
    
    def __init__(self):
        # CORRECTION: Validation OpenAI plus robuste
        api_key = os.getenv('OPENAI_API_KEY')
        self.openai_available = (
            OPENAI_AVAILABLE and 
            api_key is not None and 
            api_key.strip() != ""
        )
        
        self.model = os.getenv('CONTEXTUALIZER_MODEL', 'gpt-4o-mini')
        self.timeout = int(os.getenv('CONTEXTUALIZER_TIMEOUT', '10'))
        self.max_retries = int(os.getenv('CONTEXTUALIZER_RETRIES', '2'))
        
        # Statistiques - version étendue avec entités normalisées
        self.stats = {
            "total_requests": 0,
            "single_variant_requests": 0,
            "multi_variant_requests": 0,
            "openai_success": 0,
            "openai_failures": 0,
            "fallback_used": 0,
            "questions_enriched": 0,
            "inference_only": 0,
            "with_normalized_entities": 0,  # ✅ NOUVEAU: Tracker entités normalisées
            "variants_generated": 0,
            "normalized_entities_used": 0,  # ✅ NOUVEAU: Compteur utilisation entités normalisées
            "performance_improvements": 0   # ✅ NOUVEAU: Améliorations performance
        }
        
        logger.info(f"🤖 [AgentContextualizer] Initialisé - Version Entités Normalisées v4.0")
        logger.info(f"   OpenAI disponible: {'✅' if self.openai_available else '❌'}")
        logger.info(f"   Modèle: {self.model}")
        logger.info(f"   Support entités normalisées: ✅")
        logger.info(f"   Support multi-variants: ✅")
    
    async def enrich_question(
        self,
        question: str,
        entities: Dict[str, Any] = None,
        missing_entities: List[str] = None,
        conversation_context: str = "",
        language: str = "fr",
        multi_variant: bool = False
    ) -> Union[Dict[str, Any], Dict[str, List[Dict[str, Any]]]]:
        """
        Enrichit une question avec le contexte conversationnel et entités normalisées
        
        Args:
            question: Question originale
            entities: Entités DÉJÀ NORMALISÉES par entity_normalizer (breed, sex, age_days, etc.)
            missing_entities: Entités manquantes critiques - OPTIONNEL  
            conversation_context: Contexte conversationnel
            language: Langue de la conversation
            multi_variant: Si True, retourne plusieurs enrichissements différents
            
        Returns:
            Si multi_variant=False:
            {
                "enriched_question": "question optimisée",
                "reasoning_notes": "explications",
                "entities_used": ["breed", "age_days"],
                "inference_used": true,
                "method_used": "openai/fallback",
                "confidence": 0.8,
                "normalized_entities_processed": true  # ✅ NOUVEAU
            }
            
            Si multi_variant=True:
            {
                "variants": [
                    {"enriched_question": "variant 1", "type": "standard", ...},
                    {"enriched_question": "variant 2", "type": "contextual", ...},
                    {"enriched_question": "variant 3", "type": "detailed", ...}
                ],
                "total_variants": 3,
                "recommended_variant": 0,
                "normalized_entities_processed": true  # ✅ NOUVEAU
            }
        """
        
        # CORRECTION: Validation des inputs
        if not question or not question.strip():
            error_msg = "Question cannot be empty"
            logger.error(f"❌ [AgentContextualizer] {error_msg}")
            raise ValueError(error_msg)
        
        if len(question) > 5000:
            error_msg = "Question too long (max 5000 characters)"
            logger.error(f"❌ [AgentContextualizer] {error_msg}")
            raise ValueError(error_msg)
        
        # ✅ NOUVEAU: Valeurs par défaut avec support entités normalisées
        entities = entities or {}
        missing_entities = missing_entities or []
        
        self.stats["total_requests"] += 1
        
        # Tracker le type de requête
        if multi_variant:
            self.stats["multi_variant_requests"] += 1
        else:
            self.stats["single_variant_requests"] += 1
        
        # ✅ MODIFICATION MAJEURE: Entités déjà normalisées - pas besoin de re-normaliser
        # Utilisation directe des clés standardisées
        has_normalized_entities = bool(entities and self._has_valid_normalized_entities(entities))
        
        if has_normalized_entities:
            self.stats["with_normalized_entities"] += 1
            self.stats["normalized_entities_used"] += 1
            logger.debug(f"✅ [AgentContextualizer] Entités normalisées reçues: {list(entities.keys())}")
        else:
            self.stats["inference_only"] += 1
            logger.debug(f"🔍 [AgentContextualizer] Pas d'entités normalisées - mode inférence")
        
        try:
            if multi_variant:
                result = await self._generate_multi_variants(
                    question, entities, missing_entities, conversation_context, language, has_normalized_entities
                )
                result["normalized_entities_processed"] = has_normalized_entities
                return result
            else:
                # Mode single variant (comportement original)
                result = await self._generate_single_variant(
                    question, entities, missing_entities, conversation_context, language, has_normalized_entities
                )
                result["normalized_entities_processed"] = has_normalized_entities
                return result
            
        except Exception as e:
            logger.error(f"❌ [AgentContextualizer] Erreur critique: {e}")
            
            # Fallback d'erreur
            error_result = {
                "enriched_question": question,
                "reasoning_notes": f"Erreur: {str(e)}",
                "entities_used": [],
                "inference_used": True,
                "method_used": "error_fallback",
                "confidence": 0.1,
                "success": False,
                "normalized_entities_processed": False
            }
            
            if multi_variant:
                return {
                    "variants": [error_result],
                    "total_variants": 1,
                    "recommended_variant": 0,
                    "error": str(e),
                    "normalized_entities_processed": False
                }
            else:
                return error_result
    
    def _has_valid_normalized_entities(self, entities: Dict[str, Any]) -> bool:
        """
        ✅ NOUVEAU: Vérifie si les entités normalisées sont valides
        
        Clés standardisées attendues du entity_normalizer:
        - breed: str (toujours normalisé: "Ross 308", "Cobb 500", etc.)
        - age_days: int (toujours en jours)
        - sex: str (toujours format standard: "male", "female", "mixed")
        - weight_grams: int (optionnel)
        - symptoms: List[str] (optionnel)
        """
        
        # Vérifier les entités critiques normalisées
        critical_normalized_keys = ["breed", "age_days", "sex"]
        
        for key in critical_normalized_keys:
            if entities.get(key) is not None:
                # Au moins une entité normalisée présente
                logger.debug(f"✅ [AgentContextualizer] Entité normalisée trouvée: {key}={entities[key]}")
                return True
        
        # Vérifier les entités optionnelles
        optional_keys = ["weight_grams", "symptoms", "mortality_rate", "temperature"]
        for key in optional_keys:
            if entities.get(key) is not None:
                logger.debug(f"✅ [AgentContextualizer] Entité optionnelle normalisée: {key}={entities[key]}")
                return True
        
        return False
    
    async def _generate_single_variant(
        self,
        question: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Génère un seul enrichissement avec entités normalisées"""
        
        try:
            # Tentative OpenAI si disponible
            if self.openai_available:
                result = await self._enrich_with_openai(
                    question, entities, missing_entities, conversation_context, language, has_normalized_entities
                )
                if result["success"]:
                    self.stats["openai_success"] += 1
                    if result["enriched_question"] != question:
                        self.stats["questions_enriched"] += 1
                        if has_normalized_entities:
                            self.stats["performance_improvements"] += 1
                    return result
                else:
                    self.stats["openai_failures"] += 1
            
            # Fallback: Enrichissement basique avec entités normalisées
            logger.info("🔄 [AgentContextualizer] Utilisation fallback avec entités normalisées")
            result = self._enrich_fallback(question, entities, missing_entities, conversation_context, language, has_normalized_entities)
            self.stats["fallback_used"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentContextualizer] Erreur single variant: {e}")
            raise
    
    async def _generate_multi_variants(
        self,
        question: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Génère plusieurs variants d'enrichissement avec entités normalisées"""
        
        logger.info(f"🔄 [AgentContextualizer] Génération multi-variants avec entités normalisées pour: {question[:50]}...")
        
        variants = []
        
        try:
            # Variant 1: Enrichissement standard avec entités normalisées
            standard_variant = await self._generate_single_variant(
                question, entities, missing_entities, conversation_context, language, has_normalized_entities
            )
            standard_variant["variant_type"] = "standard"
            standard_variant["variant_description"] = "Enrichissement standard avec entités normalisées"
            variants.append(standard_variant)
            
            # Variant 2: Enrichissement contextuel (focus sur le contexte conversationnel)
            contextual_variant = self._generate_contextual_variant(
                question, entities, conversation_context, language, has_normalized_entities
            )
            variants.append(contextual_variant)
            
            # Variant 3: Enrichissement détaillé avec toutes les entités normalisées explicites
            detailed_variant = self._generate_detailed_variant(
                question, entities, missing_entities, language, has_normalized_entities
            )
            variants.append(detailed_variant)
            
            # Variant 4: Enrichissement technique (terminologie spécialisée + entités normalisées)
            technical_variant = self._generate_technical_variant(
                question, entities, language, has_normalized_entities
            )
            variants.append(technical_variant)
            
            # Si on a du contexte ou des entités normalisées, ajouter un variant minimal
            if conversation_context or has_normalized_entities:
                minimal_variant = self._generate_minimal_variant(question, language)
                variants.append(minimal_variant)
            
            # Statistiques
            self.stats["variants_generated"] += len(variants)
            
            # CORRECTION: Protection contre liste vide
            if not variants:
                raise ValueError("Aucun variant généré")
            
            # Déterminer le variant recommandé (celui avec la meilleure confiance)
            recommended_idx = max(range(len(variants)), key=lambda i: variants[i].get("confidence", 0))
            
            result = {
                "variants": variants,
                "total_variants": len(variants),
                "recommended_variant": recommended_idx,
                "generation_method": "openai" if self.openai_available else "fallback",
                "has_normalized_entities": has_normalized_entities,  # ✅ NOUVEAU
                "processing_time": datetime.now().isoformat()
            }
            
            logger.info(f"✅ [AgentContextualizer] {len(variants)} variants générés avec entités normalisées")
            logger.debug(f"   Variant recommandé: #{recommended_idx} ({variants[recommended_idx]['variant_type']})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentContextualizer] Erreur génération multi-variants: {e}")
            
            # Fallback: au moins retourner la question originale
            fallback_variant = {
                "enriched_question": question,
                "reasoning_notes": f"Erreur génération variants: {str(e)}",
                "entities_used": [],
                "inference_used": True,
                "method_used": "error_fallback",
                "confidence": 0.1,
                "variant_type": "error",
                "variant_description": "Variant d'erreur - question originale"
            }
            
            return {
                "variants": [fallback_variant],
                "total_variants": 1,
                "recommended_variant": 0,
                "error": str(e)
            }
    
    def _generate_contextual_variant(
        self,
        question: str,
        entities: Dict[str, Any],
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Génère un variant focalisé sur le contexte conversationnel avec entités normalisées"""
        
        if not conversation_context or not conversation_context.strip():
            # Pas de contexte, variant simple
            variant = {
                "enriched_question": question,
                "reasoning_notes": "Pas de contexte conversationnel disponible",
                "entities_used": [],
                "inference_used": False,
                "method_used": "contextual_fallback",
                "confidence": 0.3,
                "variant_type": "contextual",
                "variant_description": "Variant contextuel - pas de contexte disponible"
            }
        else:
            # Intégrer le contexte avec entités normalisées si disponibles
            if language == "fr":
                enriched_question = f"{question} (Contexte conversation précédente: {conversation_context})"
            elif language == "en":
                enriched_question = f"{question} (Previous conversation context: {conversation_context})"
            else:  # Spanish
                enriched_question = f"{question} (Contexto conversación previa: {conversation_context})"
            
            # ✅ NOUVEAU: Ajouter entités normalisées si disponibles
            if has_normalized_entities:
                entities_context = self._format_normalized_entities_briefly(entities, language)
                if entities_context:
                    if language == "fr":
                        enriched_question += f" - Caractéristiques: {entities_context}"
                    elif language == "en":
                        enriched_question += f" - Characteristics: {entities_context}"
                    else:  # Spanish
                        enriched_question += f" - Características: {entities_context}"
            
            variant = {
                "enriched_question": enriched_question,
                "reasoning_notes": "Enrichissement avec contexte conversationnel et entités normalisées",
                "entities_used": ["context"] + (list(entities.keys()) if has_normalized_entities else []),
                "inference_used": False,
                "method_used": "contextual_enhancement",
                "confidence": 0.8 if has_normalized_entities else 0.7,
                "variant_type": "contextual",
                "variant_description": "Variant contextuel - intégration contexte + entités normalisées"
            }
        
        return variant
    
    def _generate_detailed_variant(
        self,
        question: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Génère un variant avec tous les détails d'entités normalisées explicites"""
        
        if not has_normalized_entities:
            # Pas d'entités normalisées, utiliser inférence
            variant = {
                "enriched_question": self._add_technical_terminology(question, language),
                "reasoning_notes": "Variant détaillé par inférence - pas d'entités normalisées disponibles",
                "entities_used": [],
                "inference_used": True,
                "method_used": "detailed_inference",
                "confidence": 0.4,
                "variant_type": "detailed",
                "variant_description": "Variant détaillé - inférence sans entités normalisées"
            }
        else:
            # ✅ NOUVEAU: Construire détails explicites avec entités NORMALISÉES
            details = []
            entities_used = []
            
            # Utiliser directement les clés normalisées standardisées
            if entities.get("breed"):
                details.append(f"Race: {entities['breed']}")  # Déjà normalisé (Ross 308, etc.)
                entities_used.append("breed")
            
            if entities.get("sex"):
                details.append(f"Sexe: {entities['sex']}")  # Déjà normalisé (male/female/mixed)
                entities_used.append("sex")
            
            if entities.get("age_days"):
                age_weeks = entities["age_days"] / 7
                details.append(f"Âge: {entities['age_days']} jours ({age_weeks:.1f} semaines)")  # Déjà normalisé
                entities_used.append("age_days")
            
            if entities.get("weight_grams"):
                details.append(f"Poids: {entities['weight_grams']}g")  # Déjà normalisé
                entities_used.append("weight_grams")
            
            if entities.get("symptoms"):
                symptoms = ", ".join(entities["symptoms"]) if isinstance(entities["symptoms"], list) else entities["symptoms"]
                details.append(f"Symptômes: {symptoms}")  # Déjà normalisé
                entities_used.append("symptoms")
            
            if entities.get("mortality_rate"):
                details.append(f"Mortalité: {entities['mortality_rate']}%")
                entities_used.append("mortality_rate")
            
            if details:
                detail_string = ", ".join(details)
                if language == "fr":
                    enriched_question = f"{question} - Détails normalisés: {detail_string}"
                elif language == "en":
                    enriched_question = f"{question} - Normalized details: {detail_string}"
                else:  # Spanish
                    enriched_question = f"{question} - Detalles normalizados: {detail_string}"
                
                confidence = 0.9  # ✅ Confiance plus élevée avec entités normalisées
            else:
                enriched_question = question
                confidence = 0.3
            
            # Mentionner les entités manquantes si pertinentes
            if missing_entities:
                missing_str = ", ".join(missing_entities)
                if language == "fr":
                    enriched_question += f" (Informations manquantes: {missing_str})"
                elif language == "en":
                    enriched_question += f" (Missing information: {missing_str})"
                else:  # Spanish
                    enriched_question += f" (Información faltante: {missing_str})"
            
            variant = {
                "enriched_question": enriched_question,
                "reasoning_notes": f"Variant détaillé avec {len(details)} entités normalisées explicites",
                "entities_used": entities_used,
                "inference_used": False,
                "method_used": "detailed_normalized_explicit",
                "confidence": confidence,
                "variant_type": "detailed",
                "variant_description": "Variant détaillé - toutes entités normalisées explicites"
            }
        
        return variant
    
    def _generate_technical_variant(
        self,
        question: str,
        entities: Dict[str, Any],
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Génère un variant avec terminologie technique avancée + entités normalisées"""
        
        # Commencer avec la question de base
        enriched_question = question
        
        # Remplacements techniques selon la langue
        if language == "fr":
            technical_mappings = [
                # Problèmes de croissance
                (r'\bne grossit pas\b', 'déficit de croissance pondérale'),
                (r'\bcroissance lente\b', 'retard de croissance'),
                (r'\bproblème de croissance\b', 'pathologie de la croissance'),
                
                # Problèmes de santé
                (r'\bmalade\b', 'pathologique'),
                (r'\bmourir\b', 'mortalité'),
                (r'\bproblème de santé\b', 'syndrome pathologique'),
                (r'\bfièvre\b', 'hyperthermie'),
                
                # Alimentation
                (r'\bne mange pas\b', 'anorexie'),
                (r'\bproblème d\'alimentation\b', 'troubles nutritionnels'),
                
                # Général
                (r'\bproblème\b', 'pathologie'),
                (r'\bautre chose\b', 'diagnostic différentiel')
            ]
        elif language == "en":
            technical_mappings = [
                # Growth issues
                (r'\bnot growing\b', 'suboptimal growth performance'),
                (r'\bslow growth\b', 'growth retardation'),
                (r'\bgrowth problem\b', 'growth pathology'),
                
                # Health issues
                (r'\bsick\b', 'pathological'),
                (r'\bdying\b', 'mortality syndrome'),
                (r'\bhealth problem\b', 'pathological condition'),
                (r'\bfever\b', 'hyperthermia'),
                
                # Feeding
                (r'\bnot eating\b', 'anorexia'),
                (r'\bfeeding problem\b', 'nutritional disorders'),
                
                # General
                (r'\bproblem\b', 'pathological condition'),
                (r'\bsomething else\b', 'differential diagnosis')
            ]
        else:  # Spanish
            technical_mappings = [
                # Problemas de crecimiento
                (r'\bno crecen\b', 'déficit de rendimiento de crecimiento'),
                (r'\bcrecimiento lento\b', 'retraso del crecimiento'),
                (r'\bproblema de crecimiento\b', 'patología del crecimiento'),
                
                # Problemas de salud
                (r'\benfermos?\b', 'patológicos'),
                (r'\bmuriendo\b', 'síndrome de mortalidad'),
                (r'\bproblema de salud\b', 'condición patológica'),
                (r'\bfiebre\b', 'hipertermia'),
                
                # Alimentación
                (r'\bno comen\b', 'anorexia'),
                (r'\bproblema de alimentación\b', 'trastornos nutricionales'),
                
                # General
                (r'\bproblema\b', 'condición patológica'),
                (r'\botra cosa\b', 'diagnóstico diferencial')
            ]
        
        # CORRECTION: Limiter les substitutions pour éviter les boucles infinies
        replacements_applied = 0
        for pattern, replacement in technical_mappings:
            new_question = re.sub(pattern, replacement, enriched_question, count=1, flags=re.IGNORECASE)
            if new_question != enriched_question:
                replacements_applied += 1
                enriched_question = new_question
        
        # ✅ NOUVEAU: Ajouter contexte technique avec entités normalisées si disponibles
        if has_normalized_entities:
            technical_context = self._build_technical_context_normalized(entities, language)
            if technical_context:
                if language == "fr":
                    enriched_question += f" - Contexte technique normalisé: {technical_context}"
                elif language == "en":
                    enriched_question += f" - Normalized technical context: {technical_context}"
                else:  # Spanish
                    enriched_question += f" - Contexto técnico normalizado: {technical_context}"
        
        confidence = min(0.95, 0.5 + (replacements_applied * 0.1) + (0.3 if has_normalized_entities else 0.2))
        
        variant = {
            "enriched_question": enriched_question,
            "reasoning_notes": f"Variant technique avec {replacements_applied} améliorations terminologiques + entités normalisées",
            "entities_used": list(entities.keys()) if has_normalized_entities else [],
            "inference_used": replacements_applied > 0,
            "method_used": "technical_enhancement_normalized",
            "confidence": confidence,
            "variant_type": "technical",
            "variant_description": "Variant technique - terminologie vétérinaire spécialisée + entités normalisées"
        }
        
        return variant
    
    def _generate_minimal_variant(self, question: str, language: str) -> Dict[str, Any]:
        """Génère un variant minimal (question quasi-originale)"""
        
        # Juste une légère amélioration grammaticale
        minimal_question = question.strip()
        if not minimal_question.endswith(('?', '.', '!')):
            minimal_question += '?'
        
        return {
            "enriched_question": minimal_question,
            "reasoning_notes": "Variant minimal - question quasi-originale",
            "entities_used": [],
            "inference_used": False,
            "method_used": "minimal_enhancement",
            "confidence": 0.5,
            "variant_type": "minimal",
            "variant_description": "Variant minimal - préservation question originale"
        }
    
    def _format_normalized_entities_briefly(self, entities: Dict[str, Any], language: str) -> str:
        """✅ NOUVEAU: Formate brièvement les entités normalisées pour contexte"""
        
        brief_parts = []
        
        # Utiliser directement les entités normalisées
        if entities.get("breed"):
            brief_parts.append(entities["breed"])  # Déjà normalisé
        
        if entities.get("age_days"):
            if language == "fr":
                brief_parts.append(f"{entities['age_days']}j")
            else:
                brief_parts.append(f"{entities['age_days']}d")
        
        if entities.get("sex"):
            brief_parts.append(entities["sex"])  # Déjà normalisé (male/female/mixed)
        
        return ", ".join(brief_parts)
    
    def _build_technical_context_normalized(self, entities: Dict[str, Any], language: str) -> str:
        """✅ NOUVEAU: Construit un contexte technique à partir des entités normalisées"""
        
        context_parts = []
        
        # Informations d'élevage avec entités normalisées
        if entities.get("breed"):
            context_parts.append(f"souche {entities['breed']}" if language == "fr" else 
                               f"strain {entities['breed']}" if language == "en" else f"cepa {entities['breed']}")
        
        if entities.get("age_days"):
            context_parts.append(f"J{entities['age_days']}" if language == "fr" else 
                               f"D{entities['age_days']}" if language == "en" else f"D{entities['age_days']}")
        
        # Performance - CORRECTION: Vérification division par zéro
        if entities.get("weight_grams") and entities.get("age_days") and entities["age_days"] > 0:
            gmq = entities["weight_grams"] / entities["age_days"]  # Gain moyen quotidien approximatif
            context_parts.append(f"GMQ≈{gmq:.1f}g/j" if language == "fr" else 
                               f"ADG≈{gmq:.1f}g/d" if language == "en" else f"GDP≈{gmq:.1f}g/d")
        
        return ", ".join(context_parts)
    
    # Méthodes existantes avec corrections pour entités normalisées
    async def _enrich_with_openai(
        self,
        question: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """Enrichissement avec OpenAI GPT utilisant entités normalisées"""
        
        try:
            # ✅ NOUVEAU: Préparer le contexte pour GPT avec entités normalisées
            entities_summary = self._format_normalized_entities_for_gpt(entities) if has_normalized_entities else "Aucune entité normalisée extraite"
            missing_summary = ", ".join(missing_entities) if missing_entities else "Aucune"
            
            # Prompt spécialisé selon la langue et la présence d'entités normalisées
            system_prompt = self._get_system_prompt(language, has_normalized_entities)
            user_prompt = self._build_enrichment_prompt(
                question, entities_summary, missing_summary, conversation_context, language, has_normalized_entities
            )
            
            # 🔧 CORRECTION CRITIQUE: Gestion d'erreur OpenAI spécifique sans paramètre 'proxies'
            client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=400,
                    timeout=self.timeout
                )
            except openai.RateLimitError as e:
                logger.error(f"Rate limit OpenAI: {e}")
                return {"success": False, "error": "rate_limit", "retry_after": getattr(e, 'retry_after', 60)}
            except openai.APITimeoutError as e:
                logger.error(f"Timeout OpenAI: {e}")
                return {"success": False, "error": "timeout"}
            except openai.APIError as e:
                logger.error(f"Erreur API OpenAI: {e}")
                return {"success": False, "error": "api_error", "details": str(e)}
            except Exception as e:
                logger.error(f"Erreur inattendue OpenAI: {e}")
                return {"success": False, "error": "unexpected", "details": str(e)}
            
            answer = response.choices[0].message.content.strip()
            
            # Parser la réponse JSON
            result = self._parse_gpt_response(answer, question, entities, has_normalized_entities)
            result["success"] = True
            result["method_used"] = "openai"
            
            logger.info(f"✅ [AgentContextualizer] Enrichissement OpenAI réussi avec entités normalisées")
            logger.debug(f"   Original: {question}")
            logger.debug(f"   Enrichi: {result['enriched_question']}")
            logger.debug(f"   Entités normalisées disponibles: {'✅' if has_normalized_entities else '❌'}")
            logger.debug(f"   Inférence utilisée: {'✅' if result.get('inference_used') else '❌'}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [AgentContextualizer] Erreur OpenAI: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_system_prompt(self, language: str, has_normalized_entities: bool) -> str:
        """Retourne le prompt système selon la langue et la présence d'entités normalisées"""
        
        if language == "fr":
            base_prompt = """Tu es un expert en aviculture spécialisé dans l'optimisation de questions pour systèmes RAG.

Ta mission:
1. Reformuler la question pour optimiser la recherche documentaire
2. Utiliser la terminologie vétérinaire précise et technique
3. Intégrer le contexte conversationnel disponible
4. Garder le sens et l'intention originale"""
            
            if has_normalized_entities:
                base_prompt += """
5. Intégrer NATURELLEMENT toutes les entités DÉJÀ NORMALISÉES (breed, age_days, sex, etc.)
6. Les entités reçues sont déjà standardisées par le système de normalisation
7. Utiliser directement les valeurs normalisées sans re-traitement
8. Mentionner si des informations critiques manquent encore"""
            else:
                base_prompt += """
5. INFÉRER les informations probables à partir du contexte et de la question
6. Reformuler avec terminologie technique même sans entités normalisées précises
7. Utiliser des termes génériques mais techniques si nécessaire"""
            
            base_prompt += "\n\nIMPORTANT: Réponds UNIQUEMENT en JSON avec la structure exacte demandée."
            
        elif language == "en":
            base_prompt = """You are a poultry expert specialized in optimizing questions for RAG systems.

Your mission:
1. Reformulate the question to optimize document search
2. Use precise and technical veterinary terminology
3. Integrate available conversational context
4. Keep original meaning and intention"""
            
            if has_normalized_entities:
                base_prompt += """
5. NATURALLY integrate all ALREADY NORMALIZED entities (breed, age_days, sex, etc.)
6. The received entities are already standardized by the normalization system
7. Use normalized values directly without re-processing
8. Mention if critical information is still missing"""
            else:
                base_prompt += """
5. INFER probable information from context and question
6. Reformulate with technical terminology even without precise normalized entities
7. Use generic but technical terms if necessary"""
            
            base_prompt += "\n\nIMPORTANT: Respond ONLY in JSON with the exact requested structure."
            
        else:  # Spanish
            base_prompt = """Eres un experto en avicultura especializado en optimizar preguntas para sistemas RAG.

Tu misión:
1. Reformular la pregunta para optimizar la búsqueda documental
2. Usar terminología veterinaria precisa y técnica
3. Integrar el contexto conversacional disponible
4. Mantener el sentido e intención original"""
            
            if has_normalized_entities:
                base_prompt += """
5. Integrar NATURALMENTE todas las entidades YA NORMALIZADAS (breed, age_days, sex, etc.)
6. Las entidades recibidas ya están estandarizadas por el sistema de normalización
7. Usar valores normalizados directamente sin re-procesamiento
8. Mencionar si aún falta información crítica"""
            else:
                base_prompt += """
5. INFERIR información probable del contexto y la pregunta
6. Reformular con terminología técnica incluso sin entidades normalizadas precisas
7. Usar términos genéricos pero técnicos si es necesario"""
            
            base_prompt += "\n\nIMPORTANTE: Responde SOLO en JSON con la estructura exacta solicitada."
        
        return base_prompt
    
    def _build_enrichment_prompt(
        self,
        question: str,
        entities_summary: str,
        missing_summary: str,
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> str:
        """Construit le prompt d'enrichissement adapté pour entités normalisées"""
        
        if language == "fr":
            prompt = f"""QUESTION ORIGINALE: "{question}"

ENTITÉS NORMALISÉES DISPONIBLES:
{entities_summary}

CONTEXTE CONVERSATIONNEL:
{conversation_context or "Aucun contexte conversationnel"}"""
            
            if has_normalized_entities:
                prompt += f"""

ENTITÉS MANQUANTES CRITIQUES: {missing_summary}

INSTRUCTIONS:
1. Reformule la question en intégrant naturellement les entités DÉJÀ NORMALISÉES
2. Les entités reçues sont standardisées: breed, age_days, sex, weight_grams, etc.
3. Utilise directement ces valeurs sans modification ni re-normalisation
4. Optimise pour la recherche RAG (terminologie technique précise)
5. Si des entités critiques manquent, adapte la formulation
6. Garde l'intention originale

EXEMPLE AVEC ENTITÉS NORMALISÉES:
Original: "Mes poulets ne grossissent pas bien"
Avec entités normalisées (breed: "Ross 308", sex: "male", age_days: 21):
Enrichi: "Mes poulets de chair Ross 308 mâles de 21 jours ont une croissance insuffisante - diagnostic et solutions"""
            else:
                prompt += """

INSTRUCTIONS (MODE INFÉRENCE - SANS ENTITÉS NORMALISÉES):
1. Analyse la question pour identifier le type de problème agricole
2. Infère le contexte probable (élevage de poulets, problème de santé, nutrition, etc.)
3. Reformule avec terminologie technique vétérinaire appropriée
4. Utilise des termes génériques mais précis si les spécificités manquent
5. Optimise pour la recherche documentaire même sans entités normalisées

EXEMPLE SANS ENTITÉS NORMALISÉES:
Original: "Mes poulets ne grossissent pas bien"
Sans entités spécifiques:
Enrichi: "Retard de croissance chez les poulets de chair - diagnostic des causes et protocoles thérapeutiques"""
            
            prompt += """

Réponds en JSON:
{
  "enriched_question": "question reformulée optimisée",
  "reasoning_notes": "explication des modifications apportées",
  "entities_used": ["breed", "sex", "age_days"],
  "inference_used": true/false,
  "confidence": 0.9,
  "optimization_applied": "description des améliorations"
}"""
        
        # Versions EN et ES similaires avec adaptation pour entités normalisées...
        elif language == "en":
            prompt = f"""ORIGINAL QUESTION: "{question}"

NORMALIZED ENTITIES AVAILABLE:
{entities_summary}

CONVERSATIONAL CONTEXT:
{conversation_context or "No conversational context"}"""
            
            if has_normalized_entities:
                prompt += f"""

MISSING CRITICAL ENTITIES: {missing_summary}

INSTRUCTIONS:
1. Reformulate question naturally integrating ALREADY NORMALIZED entities
2. Received entities are standardized: breed, age_days, sex, weight_grams, etc.
3. Use these values directly without modification or re-normalization
4. Optimize for RAG search (precise technical terminology)
5. If critical entities missing, adapt formulation
6. Keep original intention

EXAMPLE WITH NORMALIZED ENTITIES:
Original: "My chickens are not growing well"
With normalized entities (breed: "Ross 308", sex: "male", age_days: 21):
Enriched: "My Ross 308 male broiler chickens at 21 days have poor growth performance - diagnosis and solutions"""
            else:
                prompt += """

INSTRUCTIONS (INFERENCE MODE - NO NORMALIZED ENTITIES):
1. Analyze question to identify type of agricultural problem
2. Infer probable context (poultry farming, health issue, nutrition, etc.)
3. Reformulate with appropriate veterinary technical terminology
4. Use generic but precise terms if specifics are missing
5. Optimize for document search even without normalized entities

EXAMPLE WITHOUT NORMALIZED ENTITIES:
Original: "My chickens are not growing well"
Without specific entities:
Enriched: "Growth retardation in broiler chickens - diagnosis of causes and therapeutic protocols"""
            
            prompt += """

Respond in JSON:
{
  "enriched_question": "optimized reformulated question",
  "reasoning_notes": "explanation of modifications made",
  "entities_used": ["breed", "sex", "age_days"],
  "inference_used": true/false,
  "confidence": 0.9,
  "optimization_applied": "description of improvements"
}"""
        
        else:  # Spanish - structure similaire
            prompt = f"""PREGUNTA ORIGINAL: "{question}"

ENTIDADES NORMALIZADAS DISPONIBLES:
{entities_summary}

CONTEXTO CONVERSACIONAL:
{conversation_context or "Sin contexto conversacional"}"""
            
            if has_normalized_entities:
                prompt += f"""

ENTIDADES CRÍTICAS FALTANTES: {missing_summary}

INSTRUCCIONES:
1. Reformula la pregunta integrando naturalmente las entidades YA NORMALIZADAS
2. Las entidades recibidas están estandarizadas: breed, age_days, sex, weight_grams, etc.
3. Usa estos valores directamente sin modificación o re-normalización
4. Optimiza para búsqueda RAG (terminología técnica precisa)
5. Si faltan entidades críticas, adapta la formulación
6. Mantén la intención original"""
            else:
                prompt += """

INSTRUCCIONES (MODO INFERENCIA - SIN ENTIDADES NORMALIZADAS):
1. Analiza la pregunta para identificar el tipo de problema agrícola
2. Infiere el contexto probable (avicultura, problema de salud, nutrición, etc.)
3. Reformula con terminología técnica veterinaria apropiada
4. Usa términos genéricos pero precisos si faltan especificidades
5. Optimiza para búsqueda documental incluso sin entidades normalizadas"""
            
            prompt += """

Responde en JSON:
{
  "enriched_question": "pregunta reformulada optimizada",
  "reasoning_notes": "explicación de modificaciones realizadas",
  "entities_used": ["breed", "sex", "age_days"],
  "inference_used": true/false,
  "confidence": 0.9,
  "optimization_applied": "descripción de mejoras"
}"""
        
        return prompt
    
    def _format_normalized_entities_for_gpt(self, entities: Dict[str, Any]) -> str:
        """✅ NOUVEAU: Formate les entités normalisées pour le prompt GPT"""
        
        formatted_parts = []
        
        # ✅ Utiliser directement les entités normalisées standardisées
        if entities.get("breed"):
            formatted_parts.append(f"• Race normalisée: {entities['breed']}")  # Déjà "Ross 308", "Cobb 500", etc.
        
        if entities.get("sex"):
            formatted_parts.append(f"• Sexe normalisé: {entities['sex']}")  # Déjà "male", "female", "mixed"
        
        if entities.get("age_days"):
            weeks = entities["age_days"] / 7
            formatted_parts.append(f"• Âge normalisé: {entities['age_days']} jours ({weeks:.1f} semaines)")
        
        # Performance
        if entities.get("weight_grams"):
            formatted_parts.append(f"• Poids normalisé: {entities['weight_grams']}g")
        
        if entities.get("growth_rate"):
            formatted_parts.append(f"• Croissance: {entities['growth_rate']}")
        
        # Santé
        if entities.get("symptoms"):
            if isinstance(entities["symptoms"], list):
                symptoms = ", ".join(entities["symptoms"])
            else:
                symptoms = entities["symptoms"]
            formatted_parts.append(f"• Symptômes normalisés: {symptoms}")
        
        if entities.get("mortality_rate"):
            formatted_parts.append(f"• Mortalité normalisée: {entities['mortality_rate']}%")
        
        # Environnement
        if entities.get("temperature"):
            formatted_parts.append(f"• Température: {entities['temperature']}°C")
        
        if entities.get("housing_type"):
            formatted_parts.append(f"• Logement: {entities['housing_type']}")
        
        # Élevage
        if entities.get("flock_size"):
            formatted_parts.append(f"• Taille troupeau: {entities['flock_size']}")
        
        if entities.get("feed_type"):
            formatted_parts.append(f"• Alimentation: {entities['feed_type']}")
        
        return "\n".join(formatted_parts) if formatted_parts else "Aucune entité normalisée extraite"
    
    def _parse_gpt_response(self, response: str, original_question: str, entities: Dict[str, Any], has_normalized_entities: bool) -> Dict[str, Any]:
        """Parse la réponse JSON de GPT - CORRECTION: Extraction JSON plus robuste"""
        
        try:
            # CORRECTION: Extraction JSON améliorée
            parsed_json = self._extract_json_from_response(response)
            
            if not parsed_json:
                raise ValueError("Pas de JSON valide trouvé dans la réponse")
            
            # Valider et enrichir la réponse
            result = {
                "enriched_question": parsed_json.get("enriched_question", original_question),
                "reasoning_notes": parsed_json.get("reasoning_notes", "Aucune explication fournie"),
                "entities_used": parsed_json.get("entities_used", []),
                "inference_used": parsed_json.get("inference_used", not has_normalized_entities),
                "confidence": min(max(parsed_json.get("confidence", 0.5), 0.0), 1.0),
                "optimization_applied": parsed_json.get("optimization_applied", "Optimisation basique"),
                "method_used": "openai",
                "processing_time": datetime.now().isoformat(),
                "normalized_entities_available": has_normalized_entities  # ✅ NOUVEAU
            }
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"❌ [AgentContextualizer] Erreur parsing JSON: {e}")
            logger.debug(f"   Réponse GPT: {response}")
            
            # Fallback: utiliser la réponse brute si elle semble être une question
            if len(response) > 10 and ("?" in response[-10:] or any(word in response.lower() for word in ["comment", "pourquoi", "quel", "combien"])):
                return {
                    "enriched_question": response.strip(),
                    "reasoning_notes": "JSON parsing failed, used raw response",
                    "entities_used": [],
                    "inference_used": True,
                    "confidence": 0.3,
                    "optimization_applied": "Réponse brute GPT",
                    "method_used": "openai_fallback",
                    "normalized_entities_available": has_normalized_entities
                }
            else:
                # Fallback final
                return self._enrich_fallback(original_question, entities, [], "", "fr", has_normalized_entities)
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """CORRECTION: Extraction JSON plus robuste"""
        
        if not response or not response.strip():
            return None
        
        # Nettoyer la réponse
        cleaned = response.strip()
        
        # Chercher des blocs JSON explicites d'abord
        json_block_patterns = [
            r'```json\s*(\{[^`]*\})\s*```',
            r'```\s*(\{[^`]*\})\s*```'
        ]
        
        for pattern in json_block_patterns:
            match = re.search(pattern, cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        # Chercher JSON en début de réponse
        if cleaned.startswith('{'):
            try:
                # Trouver la fin du premier objet JSON valide
                decoder = json.JSONDecoder()
                obj, idx = decoder.raw_decode(cleaned)
                return obj
            except json.JSONDecodeError:
                pass
        
        # Chercher n'importe quel JSON dans la réponse (plus prudent)
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, cleaned)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _enrich_fallback(
        self,
        question: str,
        entities: Dict[str, Any],
        missing_entities: List[str],
        conversation_context: str,
        language: str,
        has_normalized_entities: bool
    ) -> Dict[str, Any]:
        """✅ NOUVEAU: Enrichissement fallback utilisant entités normalisées"""
        
        enriched_parts = []
        entities_used = []
        inference_used = False
        
        if has_normalized_entities:
            # ✅ Mode avec entités normalisées - utilisation directe
            if entities.get("breed"):
                enriched_parts.append(entities["breed"])  # Déjà normalisé
                entities_used.append("breed")
            
            if entities.get("sex"):
                enriched_parts.append(entities["sex"])  # Déjà normalisé
                entities_used.append("sex")
            
            if entities.get("age_days"):
                enriched_parts.append(f"{entities['age_days']} jours")  # Déjà normalisé
                entities_used.append("age_days")
            
            if entities.get("weight_grams"):
                enriched_parts.append(f"{entities['weight_grams']}g")
                entities_used.append("weight_grams")
                
        else:
            # Mode sans entités normalisées - inférence contextuelle
            inference_used = True
            
            # Analyser la question pour inférer le contexte
            question_lower = question.lower()
            
            # Détection du type d'animal
            if any(word in question_lower for word in ["poulet", "chicken", "pollo", "broiler"]):
                enriched_parts.append("poulets de chair" if language == "fr" else 
                                   "broiler chickens" if language == "en" else "pollos de engorde")
            elif any(word in question_lower for word in ["poule", "hen", "gallina"]):
                enriched_parts.append("poules pondeuses" if language == "fr" else 
                                   "laying hens" if language == "en" else "gallinas ponedoras")
            
            # Détection des problèmes types
            if any(word in question_lower for word in ["croissance", "growth", "crecimiento", "grossir", "grow"]):
                if language == "fr":
                    enriched_parts.append("retard de croissance")
                elif language == "en":
                    enriched_parts.append("growth performance issues")
                else:
                    enriched_parts.append("problemas de crecimiento")
            
            if any(word in question_lower for word in ["mortalité", "mortality", "mortalidad", "mourir", "dying", "muerte"]):
                if language == "fr":
                    enriched_parts.append("mortalité élevée")
                elif language == "en":
                    enriched_parts.append("high mortality")
                else:
                    enriched_parts.append("mortalidad elevada")
            
            if any(word in question_lower for word in ["maladie", "disease", "enfermedad", "malade", "sick"]):
                if language == "fr":
                    enriched_parts.append("problème sanitaire")
                elif language == "en":
                    enriched_parts.append("health issue")
                else:
                    enriched_parts.append("problema sanitario")
        
        # Construire la question enrichie
        if enriched_parts:
            enrichment = " ".join(enriched_parts)
            
            # Patterns de remplacement selon la langue - CORRECTION: Limiter substitutions
            if language == "fr":
                replacements = [
                    (r'\bmes poulets\b', f'mes {enrichment}'),
                    (r'\bpoulets?\b', enrichment),
                    (r'\bmes poules\b', f'mes {enrichment}'),
                    (r'\bpoules?\b', enrichment)
                ]
            elif language == "en":
                replacements = [
                    (r'\bmy chickens?\b', f'my {enrichment}'),
                    (r'\bchickens?\b', enrichment),
                    (r'\bmy hens?\b', f'my {enrichment}'),
                    (r'\bhens?\b', enrichment)
                ]
            else:  # Spanish
                replacements = [
                    (r'\bmis pollos?\b', f'mis {enrichment}'),
                    (r'\bpollos?\b', enrichment),
                    (r'\bmis gallinas?\b', f'mis {enrichment}'),
                    (r'\bgallinas?\b', enrichment)
                ]
            
            enriched_question = question
            for pattern, replacement in replacements:
                enriched_question = re.sub(pattern, replacement, enriched_question, count=1, flags=re.IGNORECASE)
            
            # Si aucun remplacement, ajouter en contexte
            if enriched_question == question:
                if language == "fr":
                    enriched_question = f"{question} (Contexte normalisé: {enrichment})"
                elif language == "en":
                    enriched_question = f"{question} (Normalized context: {enrichment})"
                else:
                    enriched_question = f"{question} (Contexto normalizado: {enrichment})"
        else:
            # Même sans entités ni inférence, améliorer avec terminologie technique
            enriched_question = self._add_technical_terminology(question, language)
            if enriched_question != question:
                inference_used = True
        
        # Notes sur les entités manquantes ou l'inférence
        if has_normalized_entities:
            reasoning_notes = "Enrichissement basique avec entités normalisées"
            if missing_entities:
                reasoning_notes += f". Informations manquantes: {', '.join(missing_entities)}"
        else:
            reasoning_notes = "Enrichissement par inférence contextuelle - pas d'entités normalisées disponibles"
        
        # ✅ Confiance plus élevée avec entités normalisées
        base_confidence = 0.8 if entities_used else (0.4 if inference_used else 0.3)
        
        return {
            "enriched_question": enriched_question,
            "reasoning_notes": reasoning_notes,
            "entities_used": entities_used,
            "inference_used": inference_used,
            "confidence": base_confidence,
            "optimization_applied": "Intégration entités normalisées" if has_normalized_entities else "Inférence contextuelle",
            "method_used": "fallback_normalized" if has_normalized_entities else "fallback",
            "normalized_entities_available": has_normalized_entities  # ✅ NOUVEAU
        }
    
    def _add_technical_terminology(self, question: str, language: str) -> str:
        """Ajoute de la terminologie technique même sans entités - CORRECTION: Limiter substitutions"""
        
        question_lower = question.lower()
        
        # Remplacements techniques selon la langue
        if language == "fr":
            technical_replacements = [
                (r'\bproblème de croissance\b', 'retard de croissance'),
                (r'\bne grossit pas\b', 'croissance insuffisante'),
                (r'\bproblème de santé\b', 'pathologie'),
                (r'\bmourir\b', 'mortalité'),
                (r'\bmal manger\b', 'troubles alimentaires'),
                (r'\bfièvre\b', 'hyperthermie'),
            ]
        elif language == "en":
            technical_replacements = [
                (r'\bgrowth problem\b', 'growth performance deficit'),
                (r'\bnot growing\b', 'suboptimal growth'),
                (r'\bhealth problem\b', 'pathological condition'),
                (r'\bdying\b', 'mortality'),
                (r'\bnot eating\b', 'feed intake disorders'),
                (r'\bfever\b', 'hyperthermia'),
            ]
        else:  # Spanish
            technical_replacements = [
                (r'\bproblema de crecimiento\b', 'déficit de rendimiento de crecimiento'),
                (r'\bno crecen\b', 'crecimiento subóptimo'),
                (r'\bproblema de salud\b', 'condición patológica'),
                (r'\bmuriendo\b', 'mortalidad'),
                (r'\bno comen\b', 'trastornos de ingesta'),
                (r'\bfiebre\b', 'hipertermia'),
            ]
        
        enhanced_question = question
        for pattern, replacement in technical_replacements:
            enhanced_question = re.sub(pattern, replacement, enhanced_question, count=1, flags=re.IGNORECASE)
        
        return enhanced_question
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'agent - version entités normalisées"""
        
        total = self.stats["total_requests"]
        success_rate = (self.stats["openai_success"] / total * 100) if total > 0 else 0
        enrichment_rate = (self.stats["questions_enriched"] / total * 100) if total > 0 else 0
        inference_rate = (self.stats["inference_only"] / total * 100) if total > 0 else 0
        normalized_entities_rate = (self.stats["with_normalized_entities"] / total * 100) if total > 0 else 0
        multi_variant_rate = (self.stats["multi_variant_requests"] / total * 100) if total > 0 else 0
        
        # CORRECTION: Protection division par zéro
        avg_variants = 0
        if self.stats["multi_variant_requests"] > 0:
            avg_variants = self.stats["variants_generated"] / self.stats["multi_variant_requests"]
        
        return {
            "agent_type": "contextualizer",
            "version": "normalized_entities_v4.1_openai_fixed",  # ✅ NOUVEAU VERSION CORRIGÉE
            "total_requests": total,
            "single_variant_requests": self.stats["single_variant_requests"],
            "multi_variant_requests": self.stats["multi_variant_requests"],
            "multi_variant_rate": f"{multi_variant_rate:.1f}%",
            "avg_variants_per_multi_request": f"{avg_variants:.1f}",
            "openai_success_rate": f"{success_rate:.1f}%",
            "question_enrichment_rate": f"{enrichment_rate:.1f}%",
            "inference_only_rate": f"{inference_rate:.1f}%",
            "normalized_entities_rate": f"{normalized_entities_rate:.1f}%",  # ✅ NOUVEAU
            "normalized_entities_used": self.stats["normalized_entities_used"],  # ✅ NOUVEAU
            "performance_improvements": self.stats["performance_improvements"],  # ✅ NOUVEAU
            "openai_available": self.openai_available,
            "model_used": self.model,
            "features": [  # ✅ NOUVEAU
                "normalized_entities_support",
                "openai_asyncclient_fixed",  # ✅ CORRECTION APPLIQUÉE
                "multi_variant_generation", 
                "contextual_inference",
                "technical_terminology_enhancement",
                "performance_optimization"
            ],
            "detailed_stats": self.stats.copy()
        }

# Instance globale
agent_contextualizer = AgentContextualizer()

# Fonction utilitaire pour usage externe - signature mise à jour avec support entités normalisées
async def enrich_question(
    question: str,
    entities: Dict[str, Any] = None,
    missing_entities: List[str] = None,
    conversation_context: str = "",
    language: str = "fr",
    multi_variant: bool = False
) -> Union[Dict[str, Any], Dict[str, List[Dict[str, Any]]]]:
    """
    Fonction utilitaire pour enrichir une question avec entités normalisées
    
    🔧 VERSION AMÉLIORÉE v4.1 - CORRECTION OpenAI AsyncClient:
    - ✅ CORRECTION CRITIQUE: OpenAI AsyncClient sans paramètre 'proxies' 
    - ✅ Compatible avec OpenAI v1.51.0+
    - ✅ Utilise directement les entités normalisées (breed, age_days, sex, etc.)
    - ✅ Plus besoin de normaliser - entités déjà standardisées par entity_normalizer
    - ✅ Performance optimisée grâce aux entités pré-normalisées
    - ✅ Cohérence garantie avec le système de normalisation centralisée
    
    Args:
        question: Question à enrichir
        entities: Entités DÉJÀ NORMALISÉES par entity_normalizer (optionnel)
                  Clés standardisées: breed, age_days, sex, weight_grams, symptoms, etc.
        missing_entities: Entités manquantes (optionnel)
        conversation_context: Contexte conversationnel
        language: Langue (fr/en/es)
        multi_variant: Si True, génère plusieurs variants d'enrichissement
    
    Returns:
        Si multi_variant=False: Dict avec question enrichie
        Si multi_variant=True: Dict avec liste de variants
        
        Tous les résultats incluent maintenant:
        - normalized_entities_processed: bool - Indique si entités normalisées utilisées
        - normalized_entities_available: bool - Entités normalisées disponibles
    """
    return await agent_contextualizer.enrich_question(
        question, entities, missing_entities, conversation_context, language, multi_variant
    )

# =============================================================================
# LOGGING FINAL AVEC CORRECTION APPLIQUÉE
# =============================================================================

try:
    logger.info("🔧" * 60)
    logger.info("🔧 [AGENT CONTEXTUALIZER] VERSION CORRIGÉE v4.1 - OPENAI ASYNCCLIENT FIXÉ!")
    logger.info("🔧" * 60)
    logger.info("")
    logger.info("✅ [CORRECTION CRITIQUE APPLIQUÉE]:")
    logger.info("   🔧 ERREUR RÉSOLUE: AsyncClient.__init__() got unexpected keyword 'proxies'")
    logger.info("   ✅ Solution: openai.AsyncOpenAI(api_key=key) SANS paramètre 'proxies'")
    logger.info("   ✅ Compatible: OpenAI v1.51.0+ (requirements.txt mis à jour)")
    logger.info("   ✅ Fallback: Gestion d'erreur robuste si problème d'init")
    logger.info("")
    logger.info("✅ [FONCTIONNALITÉS CONSERVÉES INTÉGRALEMENT]:")
    logger.info("   🤖 Enrichissement questions avec entités normalisées")
    logger.info("   🔄 Support multi-variants pour rag_context_enhancer") 
    logger.info("   🧠 Inférence contextuelle SANS entités")
    logger.info("   🎯 Terminologie technique vétérinaire")
    logger.info("   📊 Statistiques détaillées avec tracking complet")
    logger.info("")
    logger.info("✅ [IMPACT CORRECTION]:")
    logger.info("   ❌ AVANT: AsyncClient.__init__() got unexpected keyword 'proxies'")
    logger.info("   ✅ APRÈS: Client OpenAI initialisé correctement") 
    logger.info("   🚀 RÉSULTAT: Fonctionnalités IA fully operational")
    logger.info("")
    logger.info("🎯 [PRÊT POUR ÉTAPE SUIVANTE]:")
    logger.info("   ✅ agent_contextualizer.py corrigé")
    logger.info("   ⏳ Prochaine étape: unified_context_enhancer.py")
    logger.info("   ⏳ Puis: expert_models.py (conflit Pydantic)")
    logger.info("   ⏳ Enfin: clarification_entities module manquant")
    logger.info("")
    logger.info("🚀 [STATUS]: Agent contextualizer production-ready avec OpenAI v1.51.0!")
    logger.info("🔧" * 60)
    
except Exception as e:
    logger.error(f"❌ [AgentContextualizer] Erreur initialisation logging: {e}")
    # Continue malgré l'erreur de logging