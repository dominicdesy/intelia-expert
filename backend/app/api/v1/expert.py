"""
app/api/v1/expert_services.py - SERVICES MÉTIER EXPERT SYSTEM COMPLETS AVEC AUTO-CLARIFICATION INTÉGRÉE

🚨 VERSION COMPLÈTE 4.0.0 - TOUTES AMÉLIORATIONS INTÉGRÉES:
1. ✅ Système de concision des réponses intégré (CONSERVÉ)
2. ✅ Nettoyage avancé verbosité + références documents (CONSERVÉ)
3. ✅ Configuration flexible par type de question (CONSERVÉ)
4. ✅ Détection automatique niveau de concision requis (CONSERVÉ)
5. ✅ Conservation de toutes les fonctionnalités existantes (CONSERVÉ)
6. 🚀 ResponseVersionsGenerator intégré (CONSERVÉ)
7. 🚀 Génération de toutes les versions (ultra_concise, concise, standard, detailed) (CONSERVÉ)
8. 🚀 Support ConcisionMetrics avec métriques détaillées (CONSERVÉ)
9. 🚀 Sélection automatique selon concision_level (CONSERVÉ)
10. 🚀 Support generate_all_versions flag pour frontend (CONSERVÉ)
11. 🏷️ Filtrage taxonomique intelligent des documents RAG (CONSERVÉ)
12. 🏷️ Détection automatique broiler/layer/swine/dairy/general (CONSERVÉ)
13. 🏷️ Enhancement questions avec contexte taxonomique (CONSERVÉ)
14. 🏷️ Filtres RAG adaptatifs selon la taxonomie détectée (CONSERVÉ)
15. 🆕 Mode sémantique dynamique de clarification intégré (CONSERVÉ)
16. 🆕 Génération intelligente de questions contextuelles via GPT (CONSERVÉ)
17. 🆕 Support paramètre semantic_dynamic_mode dans les requêtes (CONSERVÉ)
18. 🔧 NOUVEAU: Déclenchement automatique clarification si contexte faible
19. 🔧 NOUVEAU: Score de complétude contexte avec seuils intelligents
20. 🔧 NOUVEAU: Validation automatique questions GPT générées avec fallback robuste
21. 🔧 NOUVEAU: Intégration complète dans process_expert_question
22. 🔧 NOUVEAU: Gestion d'erreurs complète avec fallback adaptatif

FONCTIONNALITÉS CONSERVÉES:
- ✅ Système de clarification intelligent complet
- ✅ Mémoire conversationnelle
- ✅ RAG avec contexte enrichi
- ✅ Multi-LLM support
- ✅ Validation agricole
- ✅ Support multilingue
"""

import os
import logging
import uuid
import time
import re
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from enum import Enum

from fastapi import HTTPException, Request

from .expert_models import (
    EnhancedQuestionRequest, EnhancedExpertResponse, FeedbackRequest,
    ValidationResult, ProcessingContext, VaguenessResponse, ResponseFormat,
    ConcisionLevel, ConcisionMetrics, DynamicClarification
)
from .expert_utils import (
    get_user_id_from_request, 
    build_enriched_question_from_clarification,
    get_enhanced_topics_by_language,
    save_conversation_auto_enhanced,
    extract_breed_and_sex_from_clarification,
    build_enriched_question_with_breed_sex,
    validate_clarification_completeness
)
from .expert_integrations import IntegrationsManager
from .api_enhancement_service import APIEnhancementService
from .prompt_templates import build_structured_prompt, extract_context_from_entities, validate_prompt_context, build_clarification_prompt
from .concision_service import concision_service

logger = logging.getLogger(__name__)

# =============================================================================
# 🆕 SYSTÈME DE CONCISION DES RÉPONSES (CONSERVÉ IDENTIQUE)
# =============================================================================

class ConcisionLevel(Enum):
    """Niveaux de concision disponibles"""
    ULTRA_CONCISE = "ultra_concise"
    CONCISE = "concise"
    STANDARD = "standard"
    DETAILED = "detailed"

class ConcisionConfig:
    """Configuration du système de concision"""
    
    ENABLE_CONCISE_RESPONSES = True
    DEFAULT_CONCISION_LEVEL = ConcisionLevel.CONCISE
    
    MAX_RESPONSE_LENGTH = {
        "weight_question": 80,
        "temperature_question": 60,
        "measurement_question": 70,
        "general_question": 150,
        "complex_question": 300
    }
    
    ULTRA_CONCISE_KEYWORDS = [
        "poids", "weight", "peso",
        "température", "temperature", "temperatura",
        "combien", "how much", "cuánto",
        "quel est", "what is", "cuál es"
    ]
    
    COMPLEX_KEYWORDS = [
        "comment", "how to", "cómo",
        "pourquoi", "why", "por qué", 
        "expliquer", "explain", "explicar",
        "procédure", "procedure", "procedimiento",
        "protocole", "protocol", "protocolo"
    ]

class ResponseConcisionProcessor:
    """Processeur de concision des réponses (CONSERVÉ IDENTIQUE)"""
    
    def __init__(self):
        self.config = ConcisionConfig()
        logger.info("✅ [Concision] Processeur de concision initialisé")
    
    def detect_question_type(self, question: str) -> str:
        """Détecte le type de question pour appliquer les bonnes règles"""
        
        question_lower = question.lower().strip()
        
        weight_keywords = ["poids", "weight", "peso", "grammes", "grams", "gramos", "kg"]
        if any(word in question_lower for word in weight_keywords):
            return "weight_question"
        
        temp_keywords = ["température", "temperature", "temperatura", "°c", "degré", "degree"]
        if any(word in question_lower for word in temp_keywords):
            return "temperature_question"
        
        measurement_keywords = ["taille", "size", "tamaño", "longueur", "length", "hauteur", "height"]
        if any(word in question_lower for word in measurement_keywords):
            return "measurement_question"
        
        if any(word in question_lower for word in self.config.COMPLEX_KEYWORDS):
            return "complex_question"
        
        return "general_question"
    
    def detect_optimal_concision_level(self, question: str, user_preference: Optional[ConcisionLevel] = None) -> ConcisionLevel:
        """Détecte le niveau de concision optimal pour une question"""
        
        if user_preference:
            return user_preference
        
        question_lower = question.lower().strip()
        
        if any(keyword in question_lower for keyword in self.config.ULTRA_CONCISE_KEYWORDS):
            return ConcisionLevel.ULTRA_CONCISE
        
        if any(keyword in question_lower for keyword in self.config.COMPLEX_KEYWORDS):
            return ConcisionLevel.DETAILED
        
        return self.config.DEFAULT_CONCISION_LEVEL
    
    def apply_concision(
        self, 
        response: str, 
        question: str, 
        concision_level: ConcisionLevel,
        language: str = "fr"
    ) -> str:
        """
        🚀 Méthode unified pour appliquer la concision
        Utilisée par ResponseVersionsGenerator
        """
        
        if not self.config.ENABLE_CONCISE_RESPONSES:
            return response
        
        logger.info(f"🎯 [Concision] Application niveau {concision_level.value}")
        
        if concision_level == ConcisionLevel.ULTRA_CONCISE:
            return self._extract_essential_info(response, question, language)
        elif concision_level == ConcisionLevel.CONCISE:
            return self._make_concise(response, question, language)
        elif concision_level == ConcisionLevel.STANDARD:
            return self._remove_excessive_advice(response, language)
        else:
            return self._clean_document_references_only(response)
    
    def process_response(
        self, 
        response: str, 
        question: str, 
        concision_level: Optional[ConcisionLevel] = None,
        language: str = "fr"
    ) -> str:
        """Traite une réponse selon le niveau de concision demandé (MÉTHODE CONSERVÉE)"""
        
        if not self.config.ENABLE_CONCISE_RESPONSES:
            return response
        
        level = concision_level or self.detect_optimal_concision_level(question)
        
        return self.apply_concision(response, question, level, language)
    
    def _extract_essential_info(self, response: str, question: str, language: str = "fr") -> str:
        """Extrait uniquement l'information essentielle (mode ultra-concis)"""
        
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["poids", "weight", "peso"]):
            weight_patterns = [
                r'(?:entre\s+)?(\d+(?:-\d+|[^\d]*\d+)?)\s*(?:grammes?|g\b)',
                r'(\d+)\s*(?:à|to|a)\s*(\d+)\s*(?:grammes?|g\b)',
                r'(\d+)\s*(?:grammes?|g\b)'
            ]
            
            for pattern in weight_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    if len(match.groups()) >= 2:
                        return f"{match.group(1)}-{match.group(2)}g"
                    else:
                        value = match.group(1)
                        if "entre" in response.lower() or "-" in value:
                            return f"{value}g"
                        else:
                            return f"~{value}g"
        
        if any(word in question_lower for word in ["température", "temperature"]):
            temp_patterns = [
                r'(\d+(?:-\d+)?)\s*(?:°C|degrés?|degrees?)',
                r'(\d+)\s*(?:à|to|a)\s*(\d+)\s*(?:°C|degrés?)'
            ]
            
            for pattern in temp_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    if len(match.groups()) >= 2:
                        return f"{match.group(1)}-{match.group(2)}°C"
                    else:
                        return f"{match.group(1)}°C"
        
        sentences = response.split('.')
        for sentence in sentences:
            if re.search(r'\d+', sentence) and len(sentence.strip()) > 10:
                return sentence.strip() + '.'
        
        if sentences:
            return sentences[0].strip() + '.'
        
        return response
    
    def _make_concise(self, response: str, question: str, language: str = "fr") -> str:
        """Rend concis (enlève conseils mais garde info principale)"""
        
        cleaned = self._clean_document_references_only(response)
        
        verbose_patterns = [
            r'\.?\s*Il est essentiel de[^.]*\.',
            r'\.?\s*Assurez-vous de[^.]*\.',
            r'\.?\s*N\'hésitez pas à[^.]*\.',
            r'\.?\s*Pour garantir[^.]*\.',
            r'\.?\s*Il est important de[^.]*\.',
            r'\.?\s*Veillez à[^.]*\.',
            r'\.?\s*Il convient de[^.]*\.',
            r'\.?\s*À ce stade[^.]*\.',
            r'\.?\s*En cas de doute[^.]*\.',
            r'\.?\s*pour favoriser le bien-être[^.]*\.',
            r'\.?\s*en termes de[^.]*\.',
            r'\.?\s*It is essential to[^.]*\.',
            r'\.?\s*Make sure to[^.]*\.',
            r'\.?\s*Don\'t hesitate to[^.]*\.',
            r'\.?\s*To ensure[^.]*\.',
            r'\.?\s*It is important to[^.]*\.',
            r'\.?\s*Be sure to[^.]*\.',
            r'\.?\s*At this stage[^.]*\.',
            r'\.?\s*Es esencial[^.]*\.',
            r'\.?\s*Asegúrese de[^.]*\.',
            r'\.?\s*No dude en[^.]*\.',
            r'\.?\s*Para garantizar[^.]*\.',
            r'\.?\s*Es importante[^.]*\.',
            r'\.?\s*En esta etapa[^.]*\.',
        ]
        
        for pattern in verbose_patterns:
            cleaned = re.sub(pattern, '.', cleaned, flags=re.IGNORECASE)
        
        cleaned = re.sub(r'\.+', '.', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        if any(word in question.lower() for word in ['poids', 'weight', 'peso']) and len(cleaned) > 100:
            weight_sentence = self._extract_weight_sentence(cleaned)
            if weight_sentence:
                return weight_sentence
        
        return cleaned
    
    def _remove_excessive_advice(self, response: str, language: str = "fr") -> str:
        """Enlève seulement les conseils excessifs (mode standard)"""
        
        cleaned = self._clean_document_references_only(response)
        
        excessive_patterns = [
            r'\.?\s*N\'hésitez pas à[^.]*\.',
            r'\.?\s*Pour des conseils plus personnalisés[^.]*\.',
            r'\.?\s*Don\'t hesitate to[^.]*\.',
            r'\.?\s*For more personalized advice[^.]*\.',
            r'\.?\s*No dude en[^.]*\.',
            r'\.?\s*Para consejos más personalizados[^.]*\.',
        ]
        
        for pattern in excessive_patterns:
            cleaned = re.sub(pattern, '.', cleaned, flags=re.IGNORECASE)
        
        return re.sub(r'\.+', '.', cleaned).replace(r'\s+', ' ').strip()
    
    def _clean_document_references_only(self, response_text: str) -> str:
        """Nettoie uniquement les références aux documents (version originale)"""
        
        if not response_text:
            return response_text
        
        patterns_to_remove = [
            r'selon le document \d+,?\s*',
            r'd\'après le document \d+,?\s*',
            r'le document \d+ indique que\s*',
            r'comme mentionné dans le document \d+,?\s*',
            r'tel que décrit dans le document \d+,?\s*',
            r'according to document \d+,?\s*',
            r'as stated in document \d+,?\s*',
            r'document \d+ indicates that\s*',
            r'as mentioned in document \d+,?\s*',
            r'según el documento \d+,?\s*',
            r'como se indica en el documento \d+,?\s*',
            r'el documento \d+ menciona que\s*',
            r'\(document \d+\)',
            r'\[document \d+\]',
            r'source:\s*document \d+',
            r'ref:\s*document \d+'
        ]
        
        cleaned_response = response_text
        
        for pattern in patterns_to_remove:
            cleaned_response = re.sub(
                pattern, 
                '', 
                cleaned_response, 
                flags=re.IGNORECASE
            )
        
        cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
        cleaned_response = cleaned_response.strip()
        
        if cleaned_response and cleaned_response[0].islower():
            cleaned_response = cleaned_response[0].upper() + cleaned_response[1:]
        
        return cleaned_response
    
    def _extract_weight_sentence(self, text: str) -> Optional[str]:
        """Extrait la phrase principale contenant l'information de poids"""
        
        weight_patterns = [
            r'[^.]*\d+[^.]*(?:grammes?|g\b|kg|livres?|pounds?)[^.]*\.',
            r'[^.]*(?:entre|between|entre)\s+\d+[^.]*\d+[^.]*\.',
            r'[^.]*(?:poids|weight|peso)[^.]*\d+[^.]*\.'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sentence = match.group(0).strip()
                sentence = re.sub(r'^\W+', '', sentence)
                if sentence and sentence[0].islower():
                    sentence = sentence[0].upper() + sentence[1:]
                return sentence
        
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip() + '.'
            return first_sentence
        
        return None

# =============================================================================
# 🚀 RESPONSE VERSIONS GENERATOR (CONSERVÉ IDENTIQUE)
# =============================================================================

class ResponseVersionsGenerator:
    """Générateur de toutes les versions de réponse pour le frontend"""
    
    def __init__(self, existing_processor: ResponseConcisionProcessor):
        self.existing_processor = existing_processor
        self.concision_service = concision_service
        logger.info("🚀 [ResponseVersions] Générateur initialisé avec système existant")
    
    async def generate_all_response_versions(
        self, 
        original_response: str, 
        question: str, 
        context: Dict[str, Any],
        requested_level: ConcisionLevel = ConcisionLevel.CONCISE
    ) -> Dict[str, Any]:
        """
        Génère toutes les versions de réponse en utilisant le système existant + nouveau
        """
        start_time = time.time()
        
        try:
            logger.info("🚀 [ResponseVersions] Génération toutes versions")
            logger.info(f"   - Question: {question[:50]}...")
            logger.info(f"   - Niveau demandé: {requested_level}")
            logger.info(f"   - Réponse originale: {len(original_response)} caractères")
            
            versions = {}
            
            versions["detailed"] = original_response
            
            standard_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.STANDARD,
                context.get("language", "fr")
            )
            versions["standard"] = standard_response
            
            concise_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.CONCISE,
                context.get("language", "fr")
            )
            versions["concise"] = concise_response
            
            ultra_concise_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.ULTRA_CONCISE,
                context.get("language", "fr")
            )
            versions["ultra_concise"] = ultra_concise_response
            
            selected_response = versions.get(requested_level.value, versions["concise"])
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            metrics = ConcisionMetrics(
                generation_time_ms=generation_time_ms,
                versions_generated=len(versions),
                cache_hit=False,
                fallback_used=False,
                compression_ratios={
                    level: len(content) / len(original_response) 
                    for level, content in versions.items()
                    if content and len(original_response) > 0
                },
                quality_scores={}
            )
            
            logger.info("✅ [ResponseVersions] Versions générées avec système existant:")
            for level, content in versions.items():
                logger.info(f"   - {level}: {len(content)} caractères")
            
            return {
                "response_versions": versions,
                "selected_response": selected_response,
                "concision_metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"❌ [ResponseVersions] Erreur génération: {e}")
            
            fallback_versions = {
                "ultra_concise": original_response[:50] + "..." if len(original_response) > 50 else original_response,
                "concise": original_response,
                "standard": original_response,
                "detailed": original_response
            }
            
            return {
                "response_versions": fallback_versions,
                "selected_response": fallback_versions.get(requested_level.value, original_response),
                "concision_metrics": ConcisionMetrics(
                    generation_time_ms=int((time.time() - start_time) * 1000),
                    versions_generated=len(fallback_versions),
                    cache_hit=False,
                    fallback_used=True,
                    compression_ratios={},
                    quality_scores={}
                )
            }

# =============================================================================
# 🔄 RAG CONTEXT ENHANCER (CONSERVÉ IDENTIQUE)
# =============================================================================

class RAGContextEnhancer:
    """Améliore le contexte conversationnel pour optimiser les requêtes RAG"""
    
    def __init__(self):
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se développent)',
                r'\b(qu\'?est-ce que|quel est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development)',
                r'\b(they)\s+(weigh|grow|develop)',
                r'\b(what is|how much is)\s+(their|its)',
                r'\b(how much do they)\s+(weigh|measure)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se desarrollan)',
                r'\b(cuál es|cuánto es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)'
            ]
        }
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr"
    ) -> Tuple[str, Dict[str, any]]:
        """Améliore une question pour le RAG en utilisant le contexte conversationnel"""
        
        enhancement_info = {
            "pronoun_detected": False,
            "context_entities_used": [],
            "question_enriched": False,
            "original_question": question
        }
        
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            enhancement_info["pronoun_detected"] = True
            logger.info(f"🔍 [RAG Context] Pronoms détectés dans: '{question}'")
        
        context_entities = self._extract_context_entities(conversation_context)
        if context_entities:
            enhancement_info["context_entities_used"] = list(context_entities.keys())
            logger.info(f"📊 [RAG Context] Entités contextuelles: {context_entities}")
        
        enriched_question = question
        
        if has_pronouns and context_entities:
            enriched_question = self._build_enriched_question(
                question, context_entities, language
            )
            enhancement_info["question_enriched"] = True
            logger.info(f"✨ [RAG Context] Question enrichie: '{enriched_question}'")
        
        if context_entities or has_pronouns:
            technical_context = self._build_technical_context(context_entities, language)
            if technical_context:
                enriched_question += f"\n\nContexte technique: {technical_context}"
        
        return enriched_question, enhancement_info
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte si la question contient des pronoms/références contextuelles"""
        
        patterns = self.pronoun_patterns.get(language, self.pronoun_patterns["fr"])
        question_lower = question.lower()
        
        for pattern in patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                logger.debug(f"🎯 [RAG Context] Pattern trouvé: {pattern}")
                return True
        
        return False
    
    def _extract_context_entities(self, context: str) -> Dict[str, str]:
        """Extrait les entités importantes du contexte conversationnel"""
        
        if not context:
            return {}
        
        entities = {}
        context_lower = context.lower()
        
        breed_patterns = [
            r'race[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'breed[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
            r'poulets?\s+(ross\s*308|cobb\s*500)',
            r'chickens?\s+(ross\s*308|cobb\s*500)'
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["breed"] = match.group(1).strip()
                break
        
        sex_patterns = [
            r'sexe[:\s]+([a-zA-Z\s]+?)(?:\n|,|\.|\s|$)',
            r'sex[:\s]+([a-zA-Z\s]+?)(?:\n|,|\.|\s|$)',
            r'\b(mâles?|femelles?|males?|females?|mixte|mixed)\b'
        ]
        
        for pattern in sex_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["sex"] = match.group(1).strip()
                break
        
        age_patterns = [
            r'âge[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'age[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'(\d+)\s*(?:jour|day)s?',
            r'(\d+)\s*(?:semaine|week)s?'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["age"] = match.group(1).strip()
                break
        
        return entities
    
    def _build_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie en remplaçant les pronoms par les entités contextuelles"""
        
        enriched = question
        
        templates = {
            "fr": {
                "breed_sex_age": "Pour des {breed} {sex} de {age}",
                "breed_age": "Pour des {breed} de {age}",
                "breed_sex": "Pour des {breed} {sex}",
                "breed_only": "Pour des {breed}",
                "age_only": "Pour des poulets de {age}"
            },
            "en": {
                "breed_sex_age": "For {breed} {sex} chickens at {age}",
                "breed_age": "For {breed} chickens at {age}",
                "breed_sex": "For {breed} {sex} chickens",
                "breed_only": "For {breed} chickens", 
                "age_only": "For chickens at {age}"
            },
            "es": {
                "breed_sex_age": "Para pollos {breed} {sex} de {age}",
                "breed_age": "Para pollos {breed} de {age}",
                "breed_sex": "Para pollos {breed} {sex}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        context_prefix = ""
        if "breed" in context_entities and "sex" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_sex_age"].format(
                breed=context_entities["breed"],
                sex=context_entities["sex"],
                age=context_entities["age"]
            )
        elif "breed" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_age"].format(
                breed=context_entities["breed"],
                age=context_entities["age"]
            )
        elif "breed" in context_entities and "sex" in context_entities:
            context_prefix = template_set["breed_sex"].format(
                breed=context_entities["breed"],
                sex=context_entities["sex"]
            )
        elif "breed" in context_entities:
            context_prefix = template_set["breed_only"].format(
                breed=context_entities["breed"]
            )
        elif "age" in context_entities:
            context_prefix = template_set["age_only"].format(age=context_entities["age"])
        
        if context_prefix:
            if any(word in question.lower() for word in ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]):
                enriched = f"{context_prefix}, {question.lower()}"
            else:
                enriched = f"{context_prefix}: {question}"
        
        return enriched
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        context_parts = []
        
        if "breed" in entities:
            context_parts.append(f"Race: {entities['breed']}")
        
        if "sex" in entities:
            context_parts.append(f"Sexe: {entities['sex']}")
        
        if "age" in entities:
            context_parts.append(f"Âge: {entities['age']}")
        
        return " | ".join(context_parts)

# =============================================================================
# 🔧 NOUVEAU: SYSTÈME AUTO-CLARIFICATION INTÉGRÉ
# =============================================================================

class AutoClarificationSystem:
    """
    🔧 NOUVEAU: Système d'auto-clarification basé sur le score de contexte
    """
    
    def __init__(self):
        self.context_threshold = 0.7  # Seuil pour déclencher clarification
        self.enable_auto_clarification = True
        
        logger.info("🔧 [Auto Clarification] Système initialisé")
        logger.info(f"🔧 [Auto Clarification] Seuil contexte: {self.context_threshold}")
    
    def auto_clarify_if_needed(
        self, 
        question: str, 
        context_score: float, 
        language: str = "fr"
    ) -> Optional[Dict[str, Any]]:
        """
        🔧 NOUVEAU: Détermine si une clarification automatique est nécessaire
        
        Args:
            question: Question de l'utilisateur
            context_score: Score de complétude du contexte (0.0 à 1.0)
            language: Langue de la question
            
        Returns:
            Dict avec clarification si nécessaire, None sinon
        """
        
        if not self.enable_auto_clarification:
            return None
        
        if context_score >= self.context_threshold:
            logger.info(f"✅ [Auto Clarification] Contexte suffisant ({context_score:.2f} >= {self.context_threshold})")
            return None
        
        logger.info(f"🤔 [Auto Clarification] Contexte insuffisant ({context_score:.2f} < {self.context_threshold})")
        
        # Analyser le type de question pour générer clarifications appropriées
        question_analysis = self._analyze_question_for_clarification(question, language)
        
        if question_analysis["needs_clarification"]:
            logger.info(f"🎯 [Auto Clarification] Déclenchement automatique - Type: {question_analysis['type']}")
            
            return {
                "type": "auto_clarification_needed",
                "message": self._build_clarification_message(question_analysis, language),
                "questions": question_analysis["questions"],
                "context_score": context_score,
                "trigger_reason": f"context_score_below_threshold_{context_score:.2f}",
                "automatic_trigger": True
            }
        
        return None
    
    def _analyze_question_for_clarification(self, question: str, language: str) -> Dict[str, Any]:
        """Analyse une question pour déterminer le type de clarification nécessaire"""
        
        question_lower = question.lower()
        
        # Détection questions de poids/performance
        if any(word in question_lower for word in ["poids", "weight", "peso", "performance", "croissance", "growth"]):
            return {
                "needs_clarification": True,
                "type": "performance_question",
                "questions": self._get_performance_clarification_questions(language),
                "priority": "high"
            }
        
        # Détection questions de santé
        if any(word in question_lower for word in ["maladie", "disease", "mort", "death", "problème", "problem"]):
            return {
                "needs_clarification": True,
                "type": "health_question", 
                "questions": self._get_health_clarification_questions(language),
                "priority": "high"
            }
        
        # Détection questions d'environnement
        if any(word in question_lower for word in ["température", "temperature", "environnement", "environment"]):
            return {
                "needs_clarification": True,
                "type": "environment_question",
                "questions": self._get_environment_clarification_questions(language),
                "priority": "medium"
            }
        
        # Question générale - clarification basique
        return {
            "needs_clarification": True,
            "type": "general_question",
            "questions": self._get_general_clarification_questions(language),
            "priority": "medium"
        }
    
    def _get_performance_clarification_questions(self, language: str) -> List[str]:
        """Questions de clarification pour les questions de performance"""
        
        questions = {
            "fr": [
                "Quelle race ou souche spécifique élevez-vous (Ross 308, Cobb 500, etc.) ?",
                "Quel âge ont actuellement vos volailles (en jours précis) ?",
                "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?"
            ],
            "en": [
                "What specific breed or strain are you raising (Ross 308, Cobb 500, etc.)?",
                "What is the current age of your poultry (in precise days)?",
                "Are these males, females, or a mixed flock?"
            ],
            "es": [
                "¿Qué raza o cepa específica está criando (Ross 308, Cobb 500, etc.)?",
                "¿Cuál es la edad actual de sus aves (en días precisos)?",
                "¿Son machos, hembras, o un lote mixto?"
            ]
        }
        
        return questions.get(language, questions["fr"])
    
    def _get_health_clarification_questions(self, language: str) -> List[str]:
        """Questions de clarification pour les questions de santé"""
        
        questions = {
            "fr": [
                "Quelle race ou souche élevez-vous ?",
                "Quel âge ont vos volailles ?",
                "Quels symptômes spécifiques observez-vous ?",
                "Depuis combien de temps observez-vous ce problème ?"
            ],
            "en": [
                "What breed or strain are you raising?",
                "What age are your poultry?",
                "What specific symptoms are you observing?",
                "How long have you been observing this problem?"
            ],
            "es": [
                "¿Qué raza o cepa está criando?",
                "¿Qué edad tienen sus aves?",
                "¿Qué síntomas específicos está observando?",
                "¿Desde cuándo observa este problema?"
            ]
        }
        
        return questions.get(language, questions["fr"])
    
    def _get_environment_clarification_questions(self, language: str) -> List[str]:
        """Questions de clarification pour les questions d'environnement"""
        
        questions = {
            "fr": [
                "Quelle race ou souche élevez-vous ?",
                "Quel âge ont vos volailles ?",
                "Quelles sont les conditions actuelles (température, humidité) ?",
                "Quel type de bâtiment utilisez-vous ?"
            ],
            "en": [
                "What breed or strain are you raising?",
                "What age are your poultry?",
                "What are the current conditions (temperature, humidity)?",
                "What type of housing are you using?"
            ],
            "es": [
                "¿Qué raza o cepa está criando?",
                "¿Qué edad tienen sus aves?",
                "¿Cuáles son las condiciones actuales (temperatura, humedad)?",
                "¿Qué tipo de alojamiento está usando?"
            ]
        }
        
        return questions.get(language, questions["fr"])
    
    def _get_general_clarification_questions(self, language: str) -> List[str]:
        """Questions de clarification générales"""
        
        questions = {
            "fr": [
                "Pouvez-vous préciser la race ou souche de vos volailles ?",
                "Quel âge ont actuellement vos animaux ?",
                "Dans quel contexte d'élevage vous trouvez-vous ?",
                "Y a-t-il des symptômes ou problèmes spécifiques observés ?"
            ],
            "en": [
                "Could you specify the breed or strain of your poultry?",
                "What age are your animals currently?",
                "What farming context are you in?",
                "Are there any specific symptoms or problems observed?"
            ],
            "es": [
                "¿Podría especificar la raza o cepa de sus aves?",
                "¿Qué edad tienen actualmente sus animales?",
                "¿En qué contexto de cría se encuentra?",
                "¿Hay algún síntoma o problema específico observado?"
            ]
        }
        
        return questions.get(language, questions["fr"])
    
    def _build_clarification_message(self, question_analysis: Dict[str, Any], language: str) -> str:
        """Construit le message de clarification selon le type de question"""
        
        messages = {
            "fr": {
                "performance_question": "🤔 Votre question concerne la performance. Pour vous donner une réponse précise, j'ai besoin de quelques détails :",
                "health_question": "🤔 Votre question concerne la santé. Pour mieux vous aider, pouvez-vous préciser :",
                "environment_question": "🤔 Votre question concerne l'environnement. Pour une réponse adaptée, j'aurais besoin de :",
                "general_question": "🤔 Pour mieux comprendre votre situation et vous aider efficacement :"
            },
            "en": {
                "performance_question": "🤔 Your question is about performance. To give you a precise answer, I need some details:",
                "health_question": "🤔 Your question is about health. To better help you, could you specify:",
                "environment_question": "🤔 Your question is about environment. For a tailored answer, I would need:",
                "general_question": "🤔 To better understand your situation and help you effectively:"
            },
            "es": {
                "performance_question": "🤔 Su pregunta es sobre rendimiento. Para darle una respuesta precisa, necesito algunos detalles:",
                "health_question": "🤔 Su pregunta es sobre salud. Para ayudarle mejor, ¿podría especificar:",
                "environment_question": "🤔 Su pregunta es sobre ambiente. Para una respuesta adaptada, necesitaría:",
                "general_question": "🤔 Para entender mejor su situación y ayudarle efectivamente:"
            }
        }
        
        question_type = question_analysis["type"]
        lang_messages = messages.get(language, messages["fr"])
        
        return lang_messages.get(question_type, lang_messages["general_question"])

# =============================================================================
# 🔄 EXPERT SERVICE PRINCIPAL AVEC TOUTES LES INTÉGRATIONS
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec toutes les améliorations intégrées"""
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        self.rag_enhancer = RAGContextEnhancer()
        self.enhancement_service = APIEnhancementService()
        
        self.concision_processor = ResponseConcisionProcessor()
        
        self.response_versions_generator = ResponseVersionsGenerator(
            existing_processor=self.concision_processor
        )
        
        # 🔧 NOUVEAU: Système d'auto-clarification
        self.auto_clarification = AutoClarificationSystem()
        
        logger.info("✅ [Expert Service] Service expert initialisé avec TOUTES les améliorations")
        logger.info("   - ✅ Système de concision des réponses")
        logger.info("   - 🚀 Générateur de versions de réponse")
        logger.info("   - 🏷️ Filtrage taxonomique")
        logger.info("   - 🆕 Mode sémantique dynamique")
        logger.info("   - 🔧 Auto-clarification intégrée")
    
    def get_current_user_dependency(self):
        """Retourne la dépendance pour l'authentification"""
        return self.integrations.get_current_user_dependency()
    
    async def process_expert_question(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None
    ) -> EnhancedExpertResponse:
        """
        🚀 MÉTHODE PRINCIPALE COMPLÈTEMENT RÉÉCRITE avec auto-clarification intégrée
        ✅ CONSERVE toute la logique existante + ajoute auto-clarification
        """
        
        if start_time is None:
            start_time = time.time()
        
        try:
            logger.info("🚀 [ExpertService] Traitement question avec auto-clarification intégrée")
            
            concision_level = getattr(request_data, 'concision_level', ConcisionLevel.CONCISE)
            generate_all_versions = getattr(request_data, 'generate_all_versions', True)
            semantic_dynamic_mode = getattr(request_data, 'semantic_dynamic_mode', False)
            
            logger.info(f"🚀 [ResponseVersions] Paramètres: level={concision_level}, generate_all={generate_all_versions}")
            logger.info(f"🆕 [Semantic Dynamic] Mode: {semantic_dynamic_mode}")
            
            base_response = await self._process_question_with_auto_clarification(
                request_data, request, current_user, start_time, semantic_dynamic_mode
            )
            
            if generate_all_versions and base_response.response:
                try:
                    logger.info("🚀 [ResponseVersions] Génération de toutes les versions")
                    
                    versions_result = await self.response_versions_generator.generate_all_response_versions(
                        original_response=base_response.response,
                        question=request_data.text,
                        context={
                            "language": request_data.language,
                            "user_id": current_user.get("id") if current_user else None,
                            "conversation_id": request_data.conversation_id
                        },
                        requested_level=concision_level
                    )
                    
                    base_response.response_versions = versions_result["response_versions"]
                    base_response.response = versions_result["selected_response"]
                    base_response.concision_metrics = versions_result["concision_metrics"]
                    
                    logger.info("✅ [ResponseVersions] Versions ajoutées à la réponse")
                    
                except Exception as e:
                    logger.warning(f"⚠️ [ResponseVersions] Erreur génération versions: {e}")
                    base_response.response_versions = None
            else:
                logger.info("🚀 [ResponseVersions] Génération versions désactivée")
                base_response.response_versions = None
            
            return base_response
            
        except Exception as e:
            logger.error(f"❌ [ExpertService] Erreur traitement avec auto-clarification: {e}")
            raise
    
    async def _process_question_with_auto_clarification(
        self,
        request_data: EnhancedQuestionRequest,
        request: Request,
        current_user: Optional[Dict[str, Any]] = None,
        start_time: float = None,
        semantic_dynamic_mode: bool = False
    ) -> EnhancedExpertResponse:
        """
        🔧 NOUVELLE MÉTHODE: Traitement avec auto-clarification intégrée
        """
        
        processing_steps = []
        ai_enhancements_used = []
        debug_info = {}
        performance_breakdown = {"start": int(time.time() * 1000)}
        
        processing_steps.append("initialization")
        
        # === AUTHENTIFICATION ===
        if current_user is None and self.integrations.auth_available:
            raise HTTPException(status_code=401, detail="Authentification requise")
        
        user_id = self._extract_user_id(current_user, request_data, request)
        user_email = current_user.get("email") if current_user else None
        request_ip = request.client.host if request.client else "unknown"
        
        processing_steps.append("authentication")
        performance_breakdown["auth_complete"] = int(time.time() * 1000)
        
        # === GESTION CONVERSATION ID ===
        conversation_id = self._get_or_create_conversation_id(request_data)
        
        # === VALIDATION QUESTION ===
        question_text = request_data.text.strip()
        if not question_text:
            raise HTTPException(status_code=400, detail="Question text is required")
        
        processing_steps.append("question_validation")
        
        # === MÉMOIRE CONVERSATIONNELLE + 🔧 ÉVALUATION CONTEXTE ===
        conversation_context = None
        context_score = 0.0  # 🔧 NOUVEAU: Score de complétude du contexte
        
        if self.integrations.intelligent_memory_available:
            try:
                conversation_context = self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=question_text,
                    role="user",
                    language=request_data.language,
                    message_type="clarification_response" if request_data.is_clarification_response else "question"
                )
                
                # 🔧 NOUVEAU: Calculer score de contexte
                context_score = self._calculate_context_completeness_score(
                    question_text, conversation_context, request_data.language
                )
                
                ai_enhancements_used.append("intelligent_memory")
                processing_steps.append("memory_storage")
                logger.info(f"💾 [Expert Service] Message ajouté à la mémoire: {question_text[:50]}...")
                logger.info(f"📊 [Context Score] Score complétude contexte: {context_score:.2f}")
                
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur mémoire: {e}")
        
        performance_breakdown["memory_complete"] = int(time.time() * 1000)
        
        # 🔧 NOUVEAU: Vérification auto-clarification AVANT validation agricole
        if not request_data.is_clarification_response:
            auto_clarification_result = self.auto_clarification.auto_clarify_if_needed(
                question_text, context_score, request_data.language
            )
            
            if auto_clarification_result:
                logger.info(f"🤔 [Auto Clarification] Déclenchement automatique: {auto_clarification_result['trigger_reason']}")
                
                processing_steps.append("automatic_clarification_triggered")
                ai_enhancements_used.append("auto_clarification_context_based")
                
                return self._create_auto_clarification_response(
                    question_text, auto_clarification_result, request_data.language, 
                    conversation_id, context_score, start_time, processing_steps, ai_enhancements_used
                )
        
        # === VALIDATION AGRICOLE ===
        validation_result = await self._validate_agricultural_question(
            question_text, request_data.language, user_id, request_ip, conversation_id
        )
        
        processing_steps.append("agricultural_validation")
        performance_breakdown["validation_complete"] = int(time.time() * 1000)
        
        if not validation_result.is_valid:
            return self._create_rejection_response(
                question_text, validation_result, conversation_id, 
                user_email, request_data.language, start_time,
                processing_steps, ai_enhancements_used, None
            )
        
        # === SYSTÈME DE CLARIFICATION INTELLIGENT + SÉMANTIQUE DYNAMIQUE ===
        clarification_result = await self._handle_clarification_corrected_with_semantic_dynamic(
            request_data, question_text, user_id, conversation_id,
            processing_steps, ai_enhancements_used, semantic_dynamic_mode
        )
        
        if clarification_result:
            return clarification_result
        
        # Détection vagueness après clarifications spécialisées
        vagueness_result = None
        if request_data.enable_vagueness_detection:
            vagueness_result = self.enhancement_service.detect_vagueness(
                question_text, request_data.language
            )
            
            ai_enhancements_used.append("vagueness_detection")
            performance_breakdown["vagueness_check"] = int(time.time() * 1000)
            
            if vagueness_result.is_vague and vagueness_result.vagueness_score > 0.6:
                logger.info(f"🎯 [Expert Service] Question floue détectée (score: {vagueness_result.vagueness_score})")
                return self._create_vagueness_response(
                    vagueness_result, question_text, conversation_id, 
                    request_data.language, start_time, processing_steps, ai_enhancements_used
                )
        
        performance_breakdown["clarification_complete"] = int(time.time() * 1000)
        
        # === TRAITEMENT EXPERT AVEC RAG-FIRST + AMÉLIORATIONS + TAXONOMIC FILTERING ===
        expert_result = await self._process_expert_response_enhanced_corrected_with_taxonomy(
            question_text, request_data, request, current_user,
            conversation_id, processing_steps, ai_enhancements_used,
            debug_info, performance_breakdown, vagueness_result
        )
        
        # ✅ CONSERVÉ: APPLICATION DU SYSTÈME DE CONCISION EXISTANT
        if expert_result["answer"] and self.concision_processor.config.ENABLE_CONCISE_RESPONSES:
            
            user_concision_preference = getattr(request_data, 'concision_level', None)
            
            original_answer = expert_result["answer"]
            processed_answer = self.concision_processor.process_response(
                response=original_answer,
                question=question_text,
                concision_level=user_concision_preference,
                language=request_data.language
            )
            
            if processed_answer != original_answer:
                expert_result["answer"] = processed_answer
                expert_result["original_answer"] = original_answer
                expert_result["concision_applied"] = True
                ai_enhancements_used.append("response_concision")
                processing_steps.append("concision_processing")
                
                logger.info(f"✂️ [Expert Service] Concision appliquée: {len(original_answer)} → {len(processed_answer)} chars")
            else:
                expert_result["concision_applied"] = False
        
        performance_breakdown["concision_complete"] = int(time.time() * 1000)
        
        # === ENREGISTREMENT RÉPONSE ===
        if self.integrations.intelligent_memory_available and expert_result["answer"]:
            try:
                self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=expert_result["answer"],
                    role="assistant",
                    language=request_data.language,
                    message_type="response"
                )
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur enregistrement réponse: {e}")
        
        processing_steps.append("response_storage")
        performance_breakdown["final"] = int(time.time() * 1000)
        
        # === CONSTRUCTION RÉPONSE FINALE AMÉLIORÉE ===
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return self._build_final_enhanced_response(
            question_text, expert_result["answer"], conversation_id,
            user_email, request_data.language, response_time_ms,
            expert_result, validation_result, conversation_context,
            processing_steps, ai_enhancements_used, request_data,
            debug_info, performance_breakdown
        )
    
    # ===========================================================================================
    # 🔧 NOUVELLES MÉTHODES POUR AUTO-CLARIFICATION
    # ===========================================================================================
    
    def _calculate_context_completeness_score(
        self, 
        question: str, 
        conversation_context, 
        language: str = "fr"
    ) -> float:
        """
        🔧 NOUVEAU: Calcule un score de complétude du contexte (0.0 à 1.0)
        """
        
        score = 0.0
        
        # Score de base selon la longueur et détail de la question
        question_length = len(question.strip())
        if question_length > 50:
            score += 0.2
        elif question_length > 25:
            score += 0.1
        
        # Détection d'informations spécifiques dans la question
        question_lower = question.lower()
        
        # Présence de race spécifique (+0.3)
        specific_breeds = ["ross 308", "cobb 500", "hubbard", "arbor acres", "isa"]
        if any(breed in question_lower for breed in specific_breeds):
            score += 0.3
        elif any(word in question_lower for word in ["poulet", "chicken", "pollo"]):
            score += 0.1  # Race générique
        
        # Présence d'âge (+0.2)
        age_patterns = [r'\d+\s*(?:jour|day|día)s?', r'\d+\s*(?:semaine|week|semana)s?']
        if any(re.search(pattern, question_lower) for pattern in age_patterns):
            score += 0.2
        
        # Présence de données numériques (+0.1)
        if re.search(r'\d+', question):
            score += 0.1
        
        # Contexte conversationnel disponible (+0.2)
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            entities = conversation_context.consolidated_entities.to_dict()
            if entities:
                score += 0.2
                
                # Bonus pour entités spécifiques
                if entities.get('breed') and entities.get('breed') != 'generic':
                    score += 0.1
                if entities.get('age_days') or entities.get('age_weeks'):
                    score += 0.1
        
        # Limiter le score à 1.0
        return min(score, 1.0)
    
    def _create_auto_clarification_response(
        self,
        question: str,
        clarification_result: Dict[str, Any],
        language: str,
        conversation_id: str,
        context_score: float,
        start_time: float,
        processing_steps: list,
        ai_enhancements_used: list
    ) -> EnhancedExpertResponse:
        """
        🔧 NOUVEAU: Crée une réponse d'auto-clarification
        """
        
        # Construire le message avec les questions
        message = clarification_result["message"]
        questions = clarification_result["questions"]
        
        if len(questions) == 1:
            formatted_questions = questions[0]
        else:
            formatted_questions = "\n".join([f"• {q}" for q in questions])
        
        outro_messages = {
            "fr": "\n\nCes précisions m'aideront à vous donner une réponse plus précise et utile ! 🐔",
            "en": "\n\nThese details will help me give you a more precise and useful answer! 🐔",
            "es": "\n\n¡Estos detalles me ayudarán a darle una respuesta más precisa y útil! 🐔"
        }
        
        outro = outro_messages.get(language, outro_messages["fr"])
        response_text = f"{message}\n\n{formatted_questions}{outro}"
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=question,
            response=response_text,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="automatic_context_based_clarification",
            user=None,
            logged=True,
            validation_passed=True,
            clarification_result={
                "clarification_requested": True,
                "clarification_type": "automatic_context_based",
                "context_score": context_score,
                "questions_generated": len(questions),
                "trigger_reason": clarification_result["trigger_reason"],
                "automatic_trigger": True,
                "question_type": clarification_result.get("type", "unknown")
            },
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used,
            dynamic_clarification=DynamicClarification(
                original_question=question,
                clarification_questions=questions,
                confidence=0.9,
                generation_method="automatic_context_evaluation",
                generation_time_ms=response_time_ms,
                fallback_used=False
            )
        )
    
    # ===========================================================================================
    # ✅ TOUTES LES MÉTHODES EXISTANTES CONSERVÉES IDENTIQUES
    # ===========================================================================================
    
    async def _handle_clarification_corrected_with_semantic_dynamic(
        self, request_data, question_text, user_id, conversation_id, 
        processing_steps, ai_enhancements_used, semantic_dynamic_mode: bool = False
    ):
        """
        ✅ SYSTÈME DE CLARIFICATION PARFAITEMENT CORRIGÉ + MODE SÉMANTIQUE DYNAMIQUE
        🆕 NOUVEAU: Support du mode sémantique dynamique
        """
        
        # 1. ✅ TRAITEMENT DES RÉPONSES DE CLARIFICATION CORRIGÉ
        if request_data.is_clarification_response:
            return await self._process_clarification_response_corrected(
                request_data, question_text, conversation_id,
                processing_steps, ai_enhancements_used
            )
        
        # 🆕 NOUVEAU: Vérifier si mode sémantique dynamique activé
        if semantic_dynamic_mode and self.integrations.enhanced_clarification_available:
            logger.info(f"🆕 [Semantic Dynamic] Mode activé pour: '{question_text[:50]}...'")
            
            try:
                from .question_clarification_system import analyze_question_for_clarification_semantic_dynamic
                
                clarification_result = await analyze_question_for_clarification_semantic_dynamic(
                    question=question_text,
                    language=request_data.language,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    conversation_context={}
                )
                
                if clarification_result.needs_clarification:
                    logger.info(f"🆕 [Semantic Dynamic] {len(clarification_result.questions)} questions générées")
                    processing_steps.append("semantic_dynamic_clarification_triggered")
                    ai_enhancements_used.append("semantic_dynamic_clarification")
                    
                    return self._create_semantic_dynamic_clarification_response(
                        question_text, clarification_result, request_data.language, conversation_id
                    )
                else:
                    logger.info(f"✅ [Semantic Dynamic] Question claire, pas de clarification nécessaire")
                
            except Exception as e:
                logger.error(f"❌ [Semantic Dynamic] Erreur mode sémantique: {e}")
        
        # 2. DÉTECTION QUESTIONS NÉCESSITANT CLARIFICATION (mode normal)
        clarification_needed = self._detect_performance_question_needing_clarification(
            question_text, request_data.language
        )
        
        if not clarification_needed:
            return None
        
        logger.info(f"🎯 [Expert Service] Clarification nécessaire: {clarification_needed['type']}")
        processing_steps.append("automatic_clarification_triggered")
        ai_enhancements_used.append("smart_performance_clarification")
        
        # 3. ✅ SAUVEGARDE FORCÉE AVEC MÉMOIRE INTELLIGENTE
        if self.integrations.intelligent_memory_available:
            try:
                from .conversation_memory_enhanced import mark_question_for_clarification
                
                question_id = mark_question_for_clarification(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    original_question=question_text,
                    language=request_data.language
                )
                
                logger.info(f"💾 [Expert Service] Question originale marquée: {question_id}")
                processing_steps.append("original_question_marked")
                ai_enhancements_used.append("intelligent_memory_clarification_marking")
                
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur marquage question: {e}")
                self.integrations.add_message_to_conversation(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    message=f"ORIGINAL_QUESTION_FOR_CLARIFICATION: {question_text}",
                    role="system",
                    language=request_data.language,
                    message_type="original_question_marker"
                )
        
        # 4. Générer la demande de clarification
        clarification_response = self._generate_performance_clarification_response(
            question_text, clarification_needed, request_data.language, conversation_id
        )
        
        return clarification_response
    
    def _create_semantic_dynamic_clarification_response(
        self, question: str, clarification_result, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """🆕 NOUVEAU: Crée une réponse de clarification sémantique dynamique"""
        
        # Formater les questions de clarification
        if clarification_result.questions:
            if len(clarification_result.questions) == 1:
                response_text = f"❓ Pour mieux comprendre votre situation et vous aider efficacement :\n\n{clarification_result.questions[0]}"
            else:
                formatted_questions = "\n".join([f"• {q}" for q in clarification_result.questions])
                response_text = f"❓ Pour mieux comprendre votre situation et vous aider efficacement :\n\n{formatted_questions}"
            
            response_text += "\n\nCela me permettra de vous donner les conseils les plus pertinents ! 🐔"
        else:
            response_text = "❓ Pouvez-vous préciser votre question pour que je puisse mieux vous aider ?"
        
        return EnhancedExpertResponse(
            question=question,
            response=response_text,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=int(clarification_result.processing_time_ms),
            mode="semantic_dynamic_clarification",
            user=None,
            logged=True,
            validation_passed=True,
            clarification_result={
                "clarification_requested": True,
                "clarification_type": "semantic_dynamic",
                "questions_generated": len(clarification_result.questions) if clarification_result.questions else 0,
                "confidence": clarification_result.confidence_score,
                "model_used": clarification_result.model_used,
                "generation_time_ms": clarification_result.processing_time_ms,
                "validation_score": clarification_result.validation_score,
                "fallback_used": clarification_result.fallback_used,
                "gpt_failed": clarification_result.gpt_failed
            },
            processing_steps=["semantic_dynamic_clarification_triggered"],
            ai_enhancements_used=["semantic_dynamic_clarification", "gpt_question_generation"],
            dynamic_clarification=DynamicClarification(
                original_question=question,
                clarification_questions=clarification_result.questions or [],
                confidence=clarification_result.confidence_score
            )
        )
    
    async def _process_expert_response_enhanced_corrected_with_taxonomy(
        self, question_text: str, request_data: EnhancedQuestionRequest,
        request: Request, current_user: Optional[Dict], conversation_id: str,
        processing_steps: list, ai_enhancements_used: list,
        debug_info: Dict, performance_breakdown: Dict, vagueness_result = None
    ) -> Dict[str, Any]:
        """
        🏷️ NOUVELLE VERSION: RAG parfaitement corrigé avec mémoire intelligente + FILTRAGE TAXONOMIQUE
        """
        
        # === 1. RÉCUPÉRATION FORCÉE DU CONTEXTE CONVERSATIONNEL ===
        conversation_context_str = ""
        extracted_entities = {}
        
        if self.integrations.intelligent_memory_available:
            try:
                context_obj = self.integrations.get_conversation_context(conversation_id)
                if context_obj:
                    conversation_context_str = context_obj.get_context_for_rag(max_chars=800)
                    
                    if request_data.is_clarification_response or request_data.original_question:
                        if request_data.original_question:
                            conversation_context_str = f"Question originale: {request_data.original_question}. " + conversation_context_str
                        
                        if hasattr(context_obj, 'messages'):
                            for msg in reversed(context_obj.messages[-5:]):
                                if msg.role == "user" and any(word in msg.message.lower() for word in ["ross", "cobb", "hubbard", "mâle", "femelle", "male", "female"]):
                                    conversation_context_str += f" | Clarification: {msg.message}"
                                    break
                    
                    if hasattr(context_obj, 'consolidated_entities'):
                        extracted_entities = context_obj.consolidated_entities.to_dict()
                    
                    logger.info(f"🧠 [Expert Service] Contexte enrichi récupéré: {conversation_context_str[:150]}...")
                    ai_enhancements_used.append("intelligent_memory_context_retrieval")
                else:
                    logger.warning(f"⚠️ [Expert Service] Aucun contexte trouvé pour: {conversation_id}")
                    
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur récupération contexte: {e}")
        
        performance_breakdown["context_retrieved"] = int(time.time() * 1000)
        
        # === 2. AMÉLIORATION INTELLIGENTE DE LA QUESTION ===
        enriched_question, enhancement_info = self.rag_enhancer.enhance_question_for_rag(
            question=question_text,
            conversation_context=conversation_context_str,
            language=request_data.language
        )
        
        if request_data.original_question and request_data.is_clarification_response:
            logger.info(f"✨ [Expert Service] Question déjà enrichie par clarification: {question_text[:100]}...")
            ai_enhancements_used.append("clarification_based_enrichment")
        
        if enhancement_info["question_enriched"]:
            ai_enhancements_used.append("intelligent_question_enhancement")
            logger.info(f"✨ [Expert Service] Question améliorée: {enriched_question[:150]}...")
        
        if enhancement_info["pronoun_detected"]:
            ai_enhancements_used.append("contextual_pronoun_resolution")
            logger.info(f"🎯 [Expert Service] Pronoms contextuels résolus: {enhancement_info['context_entities_used']}")
        
        processing_steps.append("intelligent_question_enhancement")
        performance_breakdown["question_enhanced"] = int(time.time() * 1000)
        
        # === 3. 🏷️ NOUVEAU: FILTRAGE TAXONOMIQUE INTELLIGENT ===
        from .api_enhancement_service import infer_taxonomy_from_entities, enhance_rag_query_with_taxonomy
        
        taxonomy = infer_taxonomy_from_entities(extracted_entities)
        enhanced_question_with_taxonomy, rag_filters = enhance_rag_query_with_taxonomy(
            enriched_question, extracted_entities, request_data.language
        )
        
        logger.info(f"🏷️ [Taxonomy Filter] Taxonomie détectée: {taxonomy}")
        if rag_filters:
            logger.info(f"🏷️ [Taxonomy Filter] Filtres RAG: {rag_filters}")
            ai_enhancements_used.append("taxonomic_document_filtering")
        
        processing_steps.append("taxonomic_analysis_and_filtering")
        performance_breakdown["taxonomy_analysis"] = int(time.time() * 1000)
        
        # === 4. VÉRIFICATION RAG DISPONIBLE ===
        app = request.app
        process_rag = getattr(app.state, 'process_question_with_rag', None)
        
        if not process_rag:
            logger.error("❌ [Expert Service] Système RAG indisponible - Erreur critique")
            raise HTTPException(
                status_code=503, 
                detail="Service RAG indisponible - Le système expert nécessite l'accès à la base documentaire"
            )
        
        # === 5. APPEL RAG AVEC CONTEXTE FORCÉ + FILTRAGE TAXONOMIQUE ===
        try:
            logger.info("🔍 [Expert Service] Appel RAG avec contexte intelligent + taxonomie...")
            
            if request_data.debug_mode:
                debug_info["original_question"] = question_text
                debug_info["enriched_question"] = enriched_question
                debug_info["enriched_question_with_taxonomy"] = enhanced_question_with_taxonomy
                debug_info["conversation_context"] = conversation_context_str
                debug_info["enhancement_info"] = enhancement_info
                debug_info["taxonomy_detected"] = taxonomy
                debug_info["rag_filters"] = rag_filters
            
            result = None
            rag_call_method = "unknown"
            
            rag_context = extract_context_from_entities(extracted_entities)
            rag_context["lang"] = request_data.language
            rag_context["taxonomy"] = taxonomy
            
            # Tentative 1: Avec paramètre context + filtres taxonomiques si supporté
            try:
                structured_question = build_structured_prompt(
                    documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                    question=enhanced_question_with_taxonomy,
                    context=rag_context
                )
                
                logger.debug(f"🔍 [Prompt Final RAG] Contexte: {rag_context}")
                logger.debug(f"🏷️ [Prompt Final RAG] Taxonomie: {taxonomy}")
                logger.debug(f"🔍 [Prompt Final RAG]\n{structured_question[:500]}...")
                
                rag_params = {
                    "question": structured_question,
                    "user": current_user,
                    "language": request_data.language,
                    "speed_mode": request_data.speed_mode,
                    "context": conversation_context_str
                }
                
                if rag_filters:
                    try:
                        rag_params["filters"] = rag_filters
                        result = await process_rag(**rag_params)
                        rag_call_method = "context_parameter_structured_with_taxonomy"
                        logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte + filtres taxonomiques")
                    except TypeError:
                        del rag_params["filters"]
                        result = await process_rag(**rag_params)
                        rag_call_method = "context_parameter_structured_taxonomy_fallback"
                        logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte (filtres taxonomiques non supportés)")
                else:
                    result = await process_rag(**rag_params)
                    rag_call_method = "context_parameter_structured"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte")
                    
            except TypeError as te:
                logger.info(f"ℹ️ [Expert Service] Paramètre context non supporté: {te}")
                
                if conversation_context_str:
                    structured_question = build_structured_prompt(
                        documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                        question=enhanced_question_with_taxonomy,
                        context=rag_context
                    )
                    
                    logger.debug(f"🔍 [Prompt Final RAG - Injecté + Taxonomie]\n{structured_question[:500]}...")
                    
                    contextual_question = f"{structured_question}\n\nContexte: {conversation_context_str}"
                    result = await process_rag(
                        question=contextual_question,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode
                    )
                    rag_call_method = "context_injected_structured_with_taxonomy"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + contexte injecté + taxonomie")
                else:
                    structured_question = build_structured_prompt(
                        documents="[DOCUMENTS_WILL_BE_INSERTED_BY_RAG]",
                        question=enhanced_question_with_taxonomy,
                        context=rag_context
                    )
                    
                    logger.debug(f"🔍 [Prompt Final RAG - Seul + Taxonomie]\n{structured_question[:500]}...")
                    
                    result = await process_rag(
                        question=structured_question,
                        user=current_user,
                        language=request_data.language,
                        speed_mode=request_data.speed_mode
                    )
                    rag_call_method = "structured_with_taxonomy_only"
                    logger.info("✅ [Expert Service] RAG appelé avec prompt structuré + taxonomie seul")
            
            performance_breakdown["rag_complete"] = int(time.time() * 1000)
            
            # === 6. TRAITEMENT RÉSULTAT RAG ===
            answer = str(result.get("response", ""))
            
            answer = self.concision_processor._clean_document_references_only(answer)
            
            rag_score = result.get("score", 0.0)
            original_mode = result.get("mode", "rag_processing")
            
            quality_check = self._validate_rag_response_quality(
                answer, enhanced_question_with_taxonomy, enhancement_info
            )
            
            if not quality_check["valid"]:
                logger.warning(f"⚠️ [Expert Service] Qualité RAG insuffisante: {quality_check['reason']}")
                ai_enhancements_used.append("quality_validation_failed")
            
            logger.info(f"✅ [Expert Service] RAG réponse reçue: {len(answer)} caractères, score: {rag_score}")
            
            mode = f"enhanced_contextual_{original_mode}_{rag_call_method}_corrected_with_concision_and_response_versions_and_taxonomy_and_semantic_dynamic_and_auto_clarification"
            
            processing_steps.append("mandatory_rag_with_intelligent_context_and_taxonomy")
            
            return {
                "answer": answer,
                "rag_used": True,
                "rag_score": rag_score,
                "mode": mode,
                "context_used": bool(conversation_context_str),
                "question_enriched": enhancement_info["question_enriched"] or bool(request_data.original_question),
                "enhancement_info": enhancement_info,
                "quality_check": quality_check,
                "extracted_entities": extracted_entities,
                "rag_call_method": rag_call_method,
                "taxonomy_used": taxonomy,
                "taxonomy_filters_applied": bool(rag_filters)
            }
            
        except Exception as rag_error:
            logger.error(f"❌ [Expert Service] Erreur critique RAG: {rag_error}")
            processing_steps.append("rag_error")
            
            error_details = {
                "error": "Erreur RAG",
                "message": "Impossible d'interroger la base documentaire",
                "question_original": question_text,
                "question_enriched": enriched_question,
                "question_with_taxonomy": enhanced_question_with_taxonomy,
                "context_available": bool(conversation_context_str),
                "taxonomy_detected": taxonomy,
                "technical_error": str(rag_error)
            }
            
            raise HTTPException(status_code=503, detail=error_details)
    
    # ===========================================================================================
    # ✅ TOUTES LES AUTRES MÉTHODES EXISTANTES CONSERVÉES IDENTIQUES
    # ===========================================================================================
    
    async def _process_clarification_response_corrected(
        self, request_data, question_text, conversation_id, 
        processing_steps, ai_enhancements_used
    ):
        """✅ TRAITEMENT DES RÉPONSES DE CLARIFICATION - VERSION CORRIGÉE FINALE (CONSERVÉ)"""
        
        original_question = request_data.original_question
        clarification_context = request_data.clarification_context
        
        if (not original_question or not clarification_context) and self.integrations.intelligent_memory_available:
            try:
                from .conversation_memory_enhanced import find_original_question
                
                original_msg = find_original_question(conversation_id)
                
                if original_msg:
                    original_question = original_msg.message
                    clarification_context = {
                        "missing_information": ["breed", "sex"],
                        "clarification_type": "performance_breed_sex"
                    }
                    logger.info(f"✅ [Expert Service] Question originale récupérée: {original_question}")
                    ai_enhancements_used.append("intelligent_memory_original_question_recovery")
                else:
                    logger.warning("⚠️ [Expert Service] Question originale non trouvée dans la mémoire")
                    
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur récupération question originale: {e}")
        
        if not original_question:
            logger.warning("⚠️ [Expert Service] Fallback: création question par défaut")
            original_question = "Quel est le poids de référence pour ces poulets ?"
            clarification_context = {
                "missing_information": ["breed", "sex"],
                "clarification_type": "performance_breed_sex_fallback"
            }
        
        missing_info = clarification_context.get("missing_information", [])
        
        validation = validate_clarification_completeness(
            question_text, missing_info, request_data.language
        )
        
        if not validation["is_complete"]:
            logger.info(f"🔄 [Expert Service] Clarification incomplète: {validation['still_missing']}")
            return self._generate_follow_up_clarification(
                question_text, validation, request_data.language, conversation_id
            )
        
        breed = validation["extracted_info"].get("breed")
        sex = validation["extracted_info"].get("sex")
        
        age_info = self._extract_age_from_original_question(original_question, request_data.language)
        
        enriched_original_question = self._build_complete_enriched_question(
            original_question, breed, sex, age_info, request_data.language
        )
        
        logger.info(f"✅ [Expert Service] Question COMPLÈTEMENT enrichie: {enriched_original_question}")
        
        request_data.text = enriched_original_question
        request_data.is_clarification_response = False
        request_data.original_question = original_question
        
        processing_steps.append("clarification_processed_successfully_with_age")
        ai_enhancements_used.append("breed_sex_age_extraction_complete")
        ai_enhancements_used.append("complete_question_enrichment")
        ai_enhancements_used.append("forced_question_replacement_with_age")
        
        return None
    
    def _detect_performance_question_needing_clarification(
        self, question: str, language: str = "fr"
    ) -> Optional[Dict[str, Any]]:
        """Détection améliorée des questions techniques nécessitant race/sexe (CONSERVÉ)"""
        
        question_lower = question.lower()
        
        weight_age_patterns = {
            "fr": [
                r'(?:poids|pèse)\s+.*?(\d+)\s*(?:jour|semaine)s?',
                r'(\d+)\s*(?:jour|semaine)s?.*?(?:poids|pèse)',
                r'(?:quel|combien)\s+.*?(?:poids|pèse).*?(\d+)',
                r'(?:croissance|développement).*?(\d+)\s*(?:jour|semaine)',
                r'(\d+)\s*(?:jour|semaine).*?(?:normal|référence|standard)'
            ],
            "en": [
                r'(?:weight|weigh)\s+.*?(\d+)\s*(?:day|week)s?',
                r'(\d+)\s*(?:day|week)s?.*?(?:weight|weigh)',
                r'(?:what|how much)\s+.*?(?:weight|weigh).*?(\d+)',
                r'(?:growth|development).*?(\d+)\s*(?:day|week)',
                r'(\d+)\s*(?:day|week).*?(?:normal|reference|standard)'
            ],
            "es": [
                r'(?:peso|pesa)\s+.*?(\d+)\s*(?:día|semana)s?',
                r'(\d+)\s*(?:día|semana)s?.*?(?:peso|pesa)',
                r'(?:cuál|cuánto)\s+.*?(?:peso|pesa).*?(\d+)',
                r'(?:crecimiento|desarrollo).*?(\d+)\s*(?:día|semana)',
                r'(\d+)\s*(?:día|semana).*?(?:normal|referencia|estándar)'
            ]
        }
        
        patterns = weight_age_patterns.get(language, weight_age_patterns["fr"])
        
        age_detected = None
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                age_detected = match.group(1)
                break
        
        if not age_detected:
            return None
        
        breed_patterns = [
            r'\b(ross\s*308|ross\s*708|cobb\s*500|cobb\s*700|hubbard|arbor\s*acres)\b',
            r'\b(broiler|poulet|chicken|pollo)\s+(ross|cobb|hubbard)',
            r'\brace\s*[:\-]?\s*(ross|cobb|hubbard)'
        ]
        
        sex_patterns = [
            r'\b(mâle|male|macho)s?\b',
            r'\b(femelle|female|hembra)s?\b',
            r'\b(coq|hen|poule|gallina)\b',
            r'\b(mixte|mixed|misto)\b'
        ]
        
        has_breed = any(re.search(pattern, question_lower, re.IGNORECASE) for pattern in breed_patterns)
        has_sex = any(re.search(pattern, question_lower, re.IGNORECASE) for pattern in sex_patterns)
        
        if not has_breed and not has_sex:
            return {
                "type": "performance_question_missing_breed_sex",
                "age_detected": age_detected,
                "question_type": "weight_performance",
                "missing_info": ["breed", "sex"],
                "confidence": 0.95
            }
        
        elif not has_breed or not has_sex:
            missing = []
            if not has_breed:
                missing.append("breed")
            if not has_sex:
                missing.append("sex")
            
            return {
                "type": "performance_question_partial_info",
                "age_detected": age_detected,
                "question_type": "weight_performance", 
                "missing_info": missing,
                "confidence": 0.8
            }
        
        return None

    def _generate_performance_clarification_response(
        self, question: str, clarification_info: Dict, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """Génère la demande de clarification optimisée (CONSERVÉ)"""
        
        age = clarification_info.get("age_detected", "X")
        missing_info = clarification_info.get("missing_info", [])
        
        clarification_messages = {
            "fr": {
                "both_missing": f"Pour vous donner le poids de référence exact d'un poulet de {age} jours, j'ai besoin de :\n\n• **Race/souche** : Ross 308, Cobb 500, Hubbard, etc.\n• **Sexe** : Mâles, femelles, ou troupeau mixte\n\nPouvez-vous préciser ces informations ?",
                "breed_missing": f"Pour le poids exact à {age} jours, quelle est la **race/souche** (Ross 308, Cobb 500, Hubbard, etc.) ?",
                "sex_missing": f"Pour le poids exact à {age} jours, s'agit-il de **mâles, femelles, ou d'un troupeau mixte** ?"
            },
            "en": {
                "both_missing": f"To give you the exact reference weight for a {age}-day chicken, I need:\n\n• **Breed/strain**: Ross 308, Cobb 500, Hubbard, etc.\n• **Sex**: Males, females, or mixed flock\n\nCould you specify this information?",
                "breed_missing": f"For the exact weight at {age} days, what is the **breed/strain** (Ross 308, Cobb 500, Hubbard, etc.)?",
                "sex_missing": f"For the exact weight at {age} days, are these **males, females, or a mixed flock**?"
            },
            "es": {
                "both_missing": f"Para darle el peso de referencia exacto de un pollo de {age} días, necesito:\n\n• **Raza/cepa**: Ross 308, Cobb 500, Hubbard, etc.\n• **Sexo**: Machos, hembras, o lote mixto\n\n¿Podría especificar esta información?",
                "breed_missing": f"Para el peso exacto a los {age} días, ¿cuál es la **raza/cepa** (Ross 308, Cobb 500, Hubbard, etc.)?",
                "sex_missing": f"Para el peso exacto a los {age} días, ¿son **machos, hembras, o un lote mixto**?"
            }
        }
        
        messages = clarification_messages.get(language, clarification_messages["fr"])
        
        if len(missing_info) >= 2:
            response_text = messages["both_missing"]
        elif "breed" in missing_info:
            response_text = messages["breed_missing"]
        else:
            response_text = messages["sex_missing"]
        
        examples = {
            "fr": "\n\n**Exemples de réponses :**\n• \"Ross 308 mâles\"\n• \"Cobb 500 femelles\"\n• \"Hubbard troupeau mixte\"",
            "en": "\n\n**Example responses:**\n• \"Ross 308 males\"\n• \"Cobb 500 females\"\n• \"Hubbard mixed flock\"",
            "es": "\n\n**Ejemplos de respuestas:**\n• \"Ross 308 machos\"\n• \"Cobb 500 hembras\"\n• \"Hubbard lote mixto\""
        }
        
        response_text += examples.get(language, examples["fr"])
        
        return EnhancedExpertResponse(
            question=question,
            response=response_text,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=50,
            mode="smart_performance_clarification_corrected",
            user=None,
            logged=True,
            validation_passed=True,
            clarification_result={
                "clarification_requested": True,
                "clarification_type": "performance_breed_sex",
                "missing_information": missing_info,
                "age_detected": age,
                "confidence": clarification_info.get("confidence", 0.9)
            },
            processing_steps=["smart_clarification_triggered"],
            ai_enhancements_used=["performance_question_detection", "targeted_clarification"]
        )
    
    def _generate_follow_up_clarification(
        self, question: str, validation: Dict, language: str, conversation_id: str
    ) -> EnhancedExpertResponse:
        """Génère une clarification de suivi si première réponse incomplète (CONSERVÉ)"""
        
        still_missing = validation["still_missing"]
        
        messages = {
            "fr": {
                "breed": "Il me manque encore la **race/souche**. Ross 308, Cobb 500, ou autre ?",
                "sex": "Il me manque encore le **sexe**. Mâles, femelles, ou troupeau mixte ?",  
                "both": "Il me manque encore la **race et le sexe**. Exemple : \"Ross 308 mâles\""
            },
            "en": {
                "breed": "I still need the **breed/strain**. Ross 308, Cobb 500, or other?",
                "sex": "I still need the **sex**. Males, females, or mixed flock?",
                "both": "I still need the **breed and sex**. Example: \"Ross 308 males\""
            },
            "es": {
                "breed": "Aún necesito la **raza/cepa**. ¿Ross 308, Cobb 500, u otra?",
                "sex": "Aún necesito el **sexo**. ¿Machos, hembras, o lote mixto?",
                "both": "Aún necesito la **raza y sexo**. Ejemplo: \"Ross 308 machos\""
            }
        }
        
        lang_messages = messages.get(language, messages["fr"])
        
        if len(still_missing) >= 2:
            message = lang_messages["both"]
        elif "breed" in still_missing:
            message = lang_messages["breed"]
        else:
            message = lang_messages["sex"]
        
        return EnhancedExpertResponse(
            question=question,
            response=message,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=30,
            mode="follow_up_clarification_corrected",
            user=None,
            logged=True,
            validation_passed=True,
            clarification_result={
                "clarification_requested": True,
                "clarification_type": "follow_up_incomplete",
                "still_missing_information": still_missing,
                "confidence": validation["confidence"]
            },
            processing_steps=["follow_up_clarification_triggered"],
            ai_enhancements_used=["incomplete_clarification_handling"]
        )
    
    # === MÉTHODES D'ENRICHISSEMENT COMPLET (CONSERVÉES IDENTIQUES) ===
    
    def _extract_age_from_original_question(self, original_question: str, language: str = "fr") -> Dict[str, Any]:
        """Extrait l'âge depuis la question originale (CONSERVÉ)"""
        
        age_info = {"days": None, "weeks": None, "text": None, "detected": False}
        
        if not original_question:
            return age_info
        
        question_lower = original_question.lower()
        
        age_patterns = {
            "fr": [
                (r'(\d+)\s*jours?', "days"),
                (r'(\d+)\s*semaines?', "weeks"),
                (r'de\s+(\d+)\s*jours?', "days"),
                (r'de\s+(\d+)\s*semaines?', "weeks"),
                (r'à\s+(\d+)\s*jours?', "days"),
                (r'à\s+(\d+)\s*semaines?', "weeks")
            ],
            "en": [
                (r'(\d+)\s*days?', "days"),
                (r'(\d+)\s*weeks?', "weeks"),
                (r'of\s+(\d+)\s*days?', "days"),
                (r'of\s+(\d+)\s*weeks?', "weeks"),
                (r'at\s+(\d+)\s*days?', "days"),
                (r'at\s+(\d+)\s*weeks?', "weeks")
            ],
            "es": [
                (r'(\d+)\s*días?', "days"),
                (r'(\d+)\s*semanas?', "weeks"),
                (r'de\s+(\d+)\s*días?', "days"),
                (r'de\s+(\d+)\s*semanas?', "weeks"),
                (r'a\s+(\d+)\s*días?', "days"),
                (r'a\s+(\d+)\s*semanas?', "weeks")
            ]
        }
        
        patterns = age_patterns.get(language, age_patterns["fr"])
        
        for pattern, unit in patterns:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                
                if unit == "days":
                    age_info["days"] = value
                    age_info["weeks"] = round(value / 7, 1)
                    age_info["text"] = f"{value} jour{'s' if value > 1 else ''}"
                else:
                    age_info["weeks"] = value
                    age_info["days"] = value * 7
                    age_info["text"] = f"{value} semaine{'s' if value > 1 else ''}"
                
                age_info["detected"] = True
                
                logger.info(f"🕐 [Age Extraction] Âge détecté: {age_info['text']} ({age_info['days']} jours)")
                break
        
        if not age_info["detected"]:
            logger.warning(f"⚠️ [Age Extraction] Aucun âge détecté dans: {original_question}")
        
        return age_info

    def _build_complete_enriched_question(
        self, 
        original_question: str, 
        breed: Optional[str], 
        sex: Optional[str], 
        age_info: Dict[str, Any], 
        language: str = "fr"
    ) -> str:
        """Construit une question complètement enrichie (CONSERVÉ)"""
        
        templates = {
            "fr": {
                "complete": "Pour des poulets {breed} {sex} de {age}",
                "breed_age": "Pour des poulets {breed} de {age}",
                "sex_age": "Pour des poulets {sex} de {age}",
                "breed_sex": "Pour des poulets {breed} {sex}",
                "age_only": "Pour des poulets de {age}",
                "breed_only": "Pour des poulets {breed}",
                "sex_only": "Pour des poulets {sex}"
            },
            "en": {
                "complete": "For {breed} {sex} chickens at {age}",
                "breed_age": "For {breed} chickens at {age}",
                "sex_age": "For {sex} chickens at {age}",
                "breed_sex": "For {breed} {sex} chickens",
                "age_only": "For chickens at {age}",
                "breed_only": "For {breed} chickens",
                "sex_only": "For {sex} chickens"
            },
            "es": {
                "complete": "Para pollos {breed} {sex} de {age}",
                "breed_age": "Para pollos {breed} de {age}",
                "sex_age": "Para pollos {sex} de {age}",
                "breed_sex": "Para pollos {breed} {sex}",
                "age_only": "Para pollos de {age}",
                "breed_only": "Para pollos {breed}",
                "sex_only": "Para pollos {sex}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        context_prefix = ""
        age_text = age_info.get("text") if age_info.get("detected") else None
        
        if breed and sex and age_text:
            context_prefix = template_set["complete"].format(
                breed=breed, sex=sex, age=age_text
            )
            logger.info(f"🌟 [Complete Enrichment] Contexte COMPLET: {context_prefix}")
            
        elif breed and age_text:
            context_prefix = template_set["breed_age"].format(
                breed=breed, age=age_text
            )
            logger.info(f"🏷️ [Breed+Age] Contexte: {context_prefix}")
            
        elif sex and age_text:
            context_prefix = template_set["sex_age"].format(
                sex=sex, age=age_text
            )
            logger.info(f"⚧ [Sex+Age] Contexte: {context_prefix}")
            
        elif breed and sex:
            context_prefix = template_set["breed_sex"].format(
                breed=breed, sex=sex
            )
            logger.info(f"🏷️⚧ [Breed+Sex] Contexte: {context_prefix}")
            
        elif age_text:
            context_prefix = template_set["age_only"].format(age=age_text)
            logger.info(f"🕐 [Age Only] Contexte: {context_prefix}")
            
        elif breed:
            context_prefix = template_set["breed_only"].format(breed=breed)
            logger.info(f"🏷️ [Breed Only] Contexte: {context_prefix}")
            
        elif sex:
            context_prefix = template_set["sex_only"].format(sex=sex)
            logger.info(f"⚧ [Sex Only] Contexte: {context_prefix}")
        
        if context_prefix:
            original_lower = original_question.lower().strip()
            
            if "quel est" in original_lower or "what is" in original_lower or "cuál es" in original_lower:
                enriched_question = f"{context_prefix}, {original_lower}"
            elif "comment" in original_lower or "how" in original_lower or "cómo" in original_lower:
                enriched_question = f"{context_prefix}: {original_question}"
            else:
                enriched_question = f"{context_prefix}: {original_question}"
            
            logger.info(f"✨ [Final Enrichment] Question finale: {enriched_question}")
            return enriched_question
        
        else:
            logger.warning("⚠️ [Enrichment] Pas d'enrichissement possible, question originale conservée")
            return original_question
    
    # === MÉTHODES UTILITAIRES AVEC TOUTES LES AMÉLIORATIONS ===
    
    def _create_vagueness_response(
        self, vagueness_result, question_text: str, conversation_id: str,
        language: str, start_time: float, processing_steps: list, ai_enhancements_used: list
    ) -> EnhancedExpertResponse:
        """Crée une réponse spécialisée pour questions floues (CONSERVÉ)"""
        
        clarification_messages = {
            "fr": f"Votre question semble manquer de précision. {vagueness_result.suggested_clarification or 'Pouvez-vous être plus spécifique ?'}",
            "en": f"Your question seems to lack precision. {vagueness_result.suggested_clarification or 'Could you be more specific?'}",
            "es": f"Su pregunta parece carecer de precisión. {vagueness_result.suggested_clarification or '¿Podría ser más específico?'}"
        }
        
        response_message = clarification_messages.get(language, clarification_messages["fr"])
        
        if vagueness_result.question_clarity in ["very_unclear", "unclear"]:
            examples = {
                "fr": "\n\nExemples de questions précises:\n• Quel est le poids normal d'un Ross 308 de 21 jours?\n• Comment traiter la mortalité élevée chez des poulets de 3 semaines?\n• Quelle température maintenir pour des poussins de 7 jours?",
                "en": "\n\nExamples of precise questions:\n• What is the normal weight of a 21-day Ross 308?\n• How to treat high mortality in 3-week-old chickens?\n• What temperature to maintain for 7-day chicks?",
                "es": "\n\nEjemplos de preguntas precisas:\n• ¿Cuál es el peso normal de un Ross 308 de 21 días?\n• ¿Cómo tratar la alta mortalidad en pollos de 3 semanas?\n• ¿Qué temperatura mantener para pollitos de 7 días?"
            }
            response_message += examples.get(language, examples["fr"])
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=question_text,
            response=response_message,
            conversation_id=conversation_id,
            rag_used=False,
            rag_score=None,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="vagueness_clarification",
            user=None,
            logged=True,
            validation_passed=True,
            vagueness_detection=vagueness_result,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used
        )
    
    def _build_final_enhanced_response(
        self, question_text: str, answer: str, conversation_id: str,
        user_email: Optional[str], language: str, response_time_ms: int,
        expert_result: Dict, validation_result: ValidationResult,
        conversation_context: Any, processing_steps: list,
        ai_enhancements_used: list, request_data: EnhancedQuestionRequest,
        debug_info: Dict, performance_breakdown: Dict
    ) -> EnhancedExpertResponse:
        """Construit la réponse finale avec toutes les améliorations"""
        
        extracted_entities = expert_result.get("extracted_entities")
        confidence_overall = None
        conversation_state = None
        
        if conversation_context and hasattr(conversation_context, 'consolidated_entities'):
            if not extracted_entities:
                extracted_entities = conversation_context.consolidated_entities.to_dict()
            confidence_overall = conversation_context.consolidated_entities.confidence_overall
            conversation_state = conversation_context.conversation_urgency
        
        final_debug_info = None
        final_performance = None
        
        if request_data.debug_mode:
            final_debug_info = {
                **debug_info,
                "total_processing_time_ms": response_time_ms,
                "ai_enhancements_count": len(ai_enhancements_used),
                "processing_steps_count": len(processing_steps),
                "concision_applied": expert_result.get("concision_applied", False),
                "response_versions_support": True,
                "taxonomy_used": expert_result.get("taxonomy_used"),
                "taxonomy_filters_applied": expert_result.get("taxonomy_filters_applied", False),
                "semantic_dynamic_available": True,
                "auto_clarification_available": True,
                "auto_clarification_used": "auto_clarification_context_based" in ai_enhancements_used
            }
            
            final_performance = performance_breakdown
        
        concision_info = {
            "concision_applied": expert_result.get("concision_applied", False),
            "original_response_available": "original_answer" in expert_result,
            "detected_question_type": None,
            "applied_concision_level": None,
            "response_versions_supported": True
        }
        
        if expert_result.get("concision_applied"):
            concision_info["detected_question_type"] = self.concision_processor.detect_question_type(question_text)
            concision_info["applied_concision_level"] = self.concision_processor.detect_optimal_concision_level(question_text).value
        
        taxonomy_info = {
            "taxonomy_detected": expert_result.get("taxonomy_used", "general"),
            "taxonomy_filters_applied": expert_result.get("taxonomy_filters_applied", False),
            "taxonomy_enhanced_question": bool(expert_result.get("taxonomy_used") != "general")
        }
        
        semantic_dynamic_info = {
            "semantic_dynamic_available": getattr(request_data, 'semantic_dynamic_mode', False),
            "semantic_dynamic_used": "semantic_dynamic_clarification" in ai_enhancements_used,
            "dynamic_questions_generated": any("semantic_dynamic" in step for step in processing_steps)
        }
        
        # 🔧 NOUVEAU: Informations auto-clarification
        auto_clarification_info = {
            "auto_clarification_available": True,
            "auto_clarification_used": "auto_clarification_context_based" in ai_enhancements_used,
            "context_score_evaluated": any("context" in step for step in processing_steps),
            "automatic_trigger": "automatic_clarification_triggered" in processing_steps
        }
            
        return EnhancedExpertResponse(
            question=str(question_text),
            response=str(answer),
            conversation_id=conversation_id,
            rag_used=expert_result["rag_used"],
            rag_score=expert_result["rag_score"],
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode=expert_result["mode"],
            user=user_email,
            logged=True,
            validation_passed=True,
            validation_confidence=validation_result.confidence,
            reprocessed_after_clarification=request_data.is_clarification_response,
            conversation_state=conversation_state,
            extracted_entities=extracted_entities,
            confidence_overall=confidence_overall,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used,
            
            document_relevance=expert_result.get("document_relevance"),
            context_coherence=expert_result.get("context_coherence"),
            vagueness_detection=None,
            fallback_details=None,
            response_format_applied=request_data.expected_response_format.value,
            quality_metrics=expert_result.get("quality_metrics"),
            debug_info=final_debug_info,
            performance_breakdown=final_performance,
            
            concision_info=concision_info,
            original_response=expert_result.get("original_answer"),
            
            response_versions=None,
            concision_metrics=None,
            
            taxonomy_info=taxonomy_info,
            
            semantic_dynamic_info=semantic_dynamic_info,
            
            # 🔧 NOUVEAU: Auto-clarification info
            auto_clarification_info=auto_clarification_info
        )
    
    # === MÉTHODES UTILITAIRES IDENTIQUES (CONSERVÉES) ===
    
    def _extract_user_id(self, current_user: Optional[Dict], request_data: EnhancedQuestionRequest, request: Request) -> str:
        if current_user:
            return current_user.get("user_id") or request_data.user_id or "authenticated_user"
        return request_data.user_id or get_user_id_from_request(request)
    
    def _get_or_create_conversation_id(self, request_data: EnhancedQuestionRequest) -> str:
        if request_data.conversation_id and request_data.conversation_id.strip():
            conversation_id = request_data.conversation_id.strip()
            logger.info(f"🔄 [Expert Service] CONTINUATION: {conversation_id}")
            return conversation_id
        else:
            conversation_id = str(uuid.uuid4())
            logger.info(f"🆕 [Expert Service] NOUVELLE: {conversation_id}")
            return conversation_id
    
    def _validate_rag_response_quality(
        self, answer: str, enriched_question: str, enhancement_info: Dict
    ) -> Dict[str, any]:
        """Valide la qualité de la réponse RAG (CONSERVÉ)"""
        
        if not answer or len(answer.strip()) < 20:
            return {
                "valid": False,
                "reason": "Réponse trop courte",
                "answer_length": len(answer) if answer else 0
            }
        
        negative_responses = [
            "je ne sais pas", "i don't know", "no sé",
            "pas d'information", "no information", "sin información"
        ]
        
        answer_lower = answer.lower()
        for negative in negative_responses:
            if negative in answer_lower:
                return {
                    "valid": False,
                    "reason": f"Réponse négative détectée: {negative}",
                    "answer_length": len(answer)
                }
        
        if any(word in enriched_question.lower() for word in ["poids", "weight", "peso"]):
            if not re.search(r'\d+', answer):
                return {
                    "valid": False,
                    "reason": "Question numérique mais pas de chiffres dans la réponse",
                    "answer_length": len(answer)
                }
        
        return {
            "valid": True,
            "reason": "Réponse valide",
            "answer_length": len(answer)
        }
    
    # === AUTRES MÉTHODES CONSERVÉES ===
    
    async def _validate_agricultural_question(self, question: str, language: str, user_id: str, request_ip: str, conversation_id: str) -> ValidationResult:
        if not self.integrations.agricultural_validator_available:
            return ValidationResult(is_valid=False, rejection_message="Service temporairement indisponible")
        
        try:
            enriched_question = question
            if self.integrations.intelligent_memory_available:
                try:
                    rag_context = self.integrations.get_context_for_rag(conversation_id)
                    if rag_context:
                        enriched_question = f"{question}\n\nContexte: {rag_context}"
                except Exception:
                    pass
            
            validation_result = self.integrations.validate_agricultural_question(
                question=enriched_question, language=language, user_id=user_id, request_ip=request_ip
            )
            
            return ValidationResult(
                is_valid=validation_result.is_valid,
                rejection_message=validation_result.reason or "Question hors domaine agricole",
                confidence=validation_result.confidence
            )
            
        except Exception as e:
            logger.error(f"❌ [Expert Service] Erreur validateur: {e}")
            return ValidationResult(is_valid=False, rejection_message="Erreur de validation")
    
    def _create_rejection_response(self, question_text, validation_result, conversation_id, user_email, language, start_time, processing_steps, ai_enhancements_used, vagueness_result=None):
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return EnhancedExpertResponse(
            question=str(question_text),
            response=str(validation_result.rejection_message),
            conversation_id=conversation_id,
            rag_used=False,
            timestamp=datetime.now().isoformat(),
            language=language,
            response_time_ms=response_time_ms,
            mode="enhanced_agricultural_validation_rejected",
            user=user_email,
            logged=True,
            validation_passed=False,
            validation_confidence=validation_result.confidence,
            processing_steps=processing_steps,
            ai_enhancements_used=ai_enhancements_used,
            vagueness_detection=vagueness_result
        )
    
    async def process_feedback(self, feedback_data: FeedbackRequest) -> Dict[str, Any]:
        feedback_updated = False
        
        if feedback_data.conversation_id and self.integrations.logging_available:
            try:
                rating_numeric = {"positive": 1, "negative": -1, "neutral": 0}.get(feedback_data.rating, 0)
                feedback_updated = await self.integrations.update_feedback(feedback_data.conversation_id, rating_numeric)
            except Exception as e:
                logger.error(f"❌ [Expert Service] Erreur feedback: {e}")
        
        return {
            "success": True,
            "message": "Feedback enregistré avec succès (Version Complète 4.0.0 - Auto-Clarification Intégrée)",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "enhanced_features_used": True,
            "concision_system_active": self.concision_processor.config.ENABLE_CONCISE_RESPONSES,
            "response_versions_supported": True,
            "taxonomic_filtering_active": True,
            "semantic_dynamic_available": True,
            "auto_clarification_available": True,
            "auto_clarification_active": self.auto_clarification.enable_auto_clarification,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_suggested_topics(self, language: str) -> Dict[str, Any]:
        lang = language.lower() if language else "fr"
        if lang not in ["fr", "en", "es"]:
            lang = "fr"
        
        topics_by_language = get_enhanced_topics_by_language()
        topics = topics_by_language.get(lang, topics_by_language["fr"])
        
        return {
            "topics": topics,
            "language": lang,
            "count": len(topics),
            "enhanced_features": {
                "vagueness_detection_available": True,
                "context_coherence_available": True,
                "detailed_rag_scoring_available": True,
                "quality_metrics_available": True,
                "smart_clarification_available": True,
                "intelligent_memory_available": self.integrations.intelligent_memory_available,
                
                "response_concision_available": True,
                "concision_levels": [level.value for level in ConcisionLevel],
                "auto_concision_detection": True,
                "concision_enabled": self.concision_processor.config.ENABLE_CONCISE_RESPONSES,
                
                "response_versions_available": True,
                "multiple_concision_levels_generation": True,
                "dynamic_level_switching_support": True,
                "concision_metrics_available": True,
                
                "taxonomic_filtering_available": True,
                "supported_taxonomies": ["broiler", "layer", "swine", "dairy", "general"],
                "automatic_taxonomy_detection": True,
                "taxonomy_based_document_filtering": True,
                
                "semantic_dynamic_clarification_available": True,
                "gpt_question_generation": True,
                "contextual_clarification_questions": True,
                "intelligent_clarification_mode": True,
                
                # 🔧 NOUVEAU: Auto-clarification features
                "auto_clarification_available": True,
                "context_completeness_scoring": True,
                "automatic_trigger_threshold": self.auto_clarification.context_threshold,
                "smart_question_evaluation": True,
                "auto_clarification_types": ["performance", "health", "environment", "general"]
            },
            "system_status": {
                "validation_enabled": self.integrations.is_agricultural_validation_enabled(),
                "enhanced_clarification_enabled": self.integrations.is_enhanced_clarification_enabled(),
                "intelligent_memory_enabled": self.integrations.intelligent_memory_available,
                "api_enhancements_enabled": True,
                "concision_processor_enabled": True,
                "response_versions_generator_enabled": True,
                "taxonomic_filtering_enabled": True,
                "semantic_dynamic_clarification_enabled": True,
                "auto_clarification_enabled": self.auto_clarification.enable_auto_clarification
            },
            
            "concision_config": {
                "default_level": self.concision_processor.config.DEFAULT_CONCISION_LEVEL.value,
                "auto_detect_enabled": True,
                "max_lengths": self.concision_processor.config.MAX_RESPONSE_LENGTH,
                "ultra_concise_keywords": self.concision_processor.config.ULTRA_CONCISE_KEYWORDS,
                "complex_keywords": self.concision_processor.config.COMPLEX_KEYWORDS,
                
                "response_versions_generation": {
                    "enabled": True,
                    "supported_levels": [level.value for level in ConcisionLevel],
                    "metrics_included": True,
                    "cache_supported": False,
                    "fallback_strategy": "simple_truncation"
                }
            },
            
            "taxonomic_config": {
                "enabled": True,
                "supported_categories": {
                    "broiler": ["ross", "cobb", "hubbard", "indian river"],
                    "layer": ["lohmann", "isa", "dekalb", "hy-line", "bovans", "h&n", "shaver"],
                    "swine": ["gestation_day", "parity"],
                    "dairy": ["days_in_milk", "milk_yield_liters"]
                },
                "auto_detection_enabled": True,
                "filter_fallback_enabled": True,
                "question_enhancement_enabled": True
            },
            
            "semantic_dynamic_config": {
                "enabled": True,
                "max_questions_generated": 4,
                "supported_languages": ["fr", "en", "es"],
                "gpt_model_used": "gpt-4o-mini",
                "fallback_questions_available": True,
                "context_aware_generation": True,
                "automatic_mode_detection": True,
                "validation_enabled": True
            },
            
            # 🔧 NOUVEAU: Config auto-clarification
            "auto_clarification_config": {
                "enabled": self.auto_clarification.enable_auto_clarification,
                "context_score_threshold": self.auto_clarification.context_threshold,
                "evaluation_criteria": ["question_length", "specific_breeds", "age_info", "numeric_data", "conversational_context"],
                "automatic_trigger": True,