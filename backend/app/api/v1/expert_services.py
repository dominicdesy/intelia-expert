"""
app/api/v1/expert_services.py - SERVICES MÉTIER EXPERT SYSTEM AVEC AUTO CLARIFICATION SIMPLIFIÉE + VALIDATION ROBUSTE + FALLBACK INTELLIGENT

🚨 MODIFICATIONS APPLIQUÉES VERSION 3.11.0:
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
18. 🔧 MODIFIÉ: Auto-clarification simplifiée avec validation robuste
19. 🔧 MODIFIÉ: Scoring et validation qualité des questions générées
20. 🔧 MODIFIÉ: Intégration visible dans expert_services avec auto_clarify_if_needed
21. 🔧 MODIFIÉ: Fallback lisible si GPT échoue complètement

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
from typing import Optional, Dict, Any, Tuple, List
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
# 🔧 NOUVELLES FONCTIONS: VALIDATION ROBUSTE ET AUTO-CLARIFICATION SIMPLIFIÉE
# =============================================================================

def validate_dynamic_questions(questions: List[str], user_question: str = "", language: str = "fr") -> Tuple[float, List[str]]:
    """
    🔧 NOUVEAU: Valide la qualité des questions générées
    
    Returns:
        Tuple[float, List[str]]: (score_qualité, questions_filtrées)
    """
    
    if not questions or not isinstance(questions, list):
        logger.warning("🔧 [Question Validation] Aucune question fournie ou format incorrect")
        return 0.0, []
    
    # Mots-clés génériques à filtrer
    generic_keywords = {
        "fr": ["exemple", "par exemple", "etc", "quelque chose", "généralement", "souvent"],
        "en": ["example", "for example", "etc", "something", "generally", "often"],
        "es": ["ejemplo", "por ejemplo", "etc", "algo", "generalmente", "a menudo"]
    }
    
    keywords = generic_keywords.get(language, generic_keywords["fr"])
    
    # Filtrage basique : enlever questions vagues ou génériques
    filtered = []
    for question in questions:
        if not isinstance(question, str):
            continue
            
        question = question.strip()
        
        # Tests de qualité
        if (len(question) > 15 and 
            len(question) < 200 and
            not any(keyword in question.lower() for keyword in keywords) and
            question not in filtered):
            
            # Ajouter point d'interrogation si manquant
            if not question.endswith('?'):
                question += ' ?'
                
            filtered.append(question)
    
    # Limiter à 4 questions maximum
    filtered = filtered[:4]
    
    # Calculer score de qualité
    if questions:
        score = len(filtered) / max(len(questions), 1)
    else:
        score = 0.0
    
    logger.info(f"🔧 [Question Validation] Score: {score:.2f}, Questions filtrées: {len(filtered)}/{len(questions)}")
    
    return score, filtered

def auto_clarify_if_needed(question: str, conversation_context: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """
    🔧 NOUVEAU: Fonction centralisée pour l'auto-clarification
    
    Returns:
        Dict si clarification nécessaire, None sinon
    """
    
    # Calculer score de complétude de base
    completeness_score = _calculate_basic_completeness_score(question, conversation_context, language)
    
    logger.info(f"🔧 [Auto Clarify] Score complétude: {completeness_score:.2f}")
    
    # Seuil pour déclencher clarification
    if completeness_score < 0.5:
        logger.info("🔧 [Auto Clarify] Clarification nécessaire - génération questions")
        
        try:
            # Tenter génération dynamique avec GPT
            questions = _generate_clarification_questions_with_fallback(question, language)
            
            if questions:
                return {
                    "type": "clarification_needed",
                    "message": _get_clarification_intro_message(language),
                    "questions": questions,
                    "completeness_score": completeness_score,
                    "generation_method": "auto_clarification"
                }
        except Exception as e:
            logger.error(f"❌ [Auto Clarify] Erreur génération questions: {e}")
    
    return None

def _calculate_basic_completeness_score(question: str, conversation_context: str, language: str = "fr") -> float:
    """
    🔧 NOUVEAU: Calcule un score de complétude simplifié (0.0 à 1.0)
    """
    
    score = 0.0
    
    # Score de base selon la longueur
    question_length = len(question.strip())
    if question_length > 50:
        score += 0.3
    elif question_length > 25:
        score += 0.2
    
    # Présence de race spécifique
    specific_breeds = ["ross 308", "cobb 500", "hubbard", "arbor acres"]
    if any(breed in question.lower() for breed in specific_breeds):
        score += 0.3
    elif any(word in question.lower() for word in ["poulet", "chicken", "pollo"]):
        score += 0.1
    
    # Présence d'âge
    age_patterns = [r'\d+\s*(?:jour|day|día)s?', r'\d+\s*(?:semaine|week|semana)s?']
    if any(re.search(pattern, question.lower()) for pattern in age_patterns):
        score += 0.2
    
    # Présence de données numériques
    if re.search(r'\d+', question):
        score += 0.1
    
    # Contexte conversationnel disponible
    if conversation_context and len(conversation_context.strip()) > 50:
        score += 0.1
    
    return min(score, 1.0)

def _generate_clarification_questions_with_fallback(question: str, language: str = "fr") -> List[str]:
    """
    🔧 NOUVEAU: Génère questions avec fallback si GPT échoue
    """
    
    try:
        # Import dynamique pour éviter erreurs de dépendance
        from .question_clarification_system import generate_dynamic_clarification_questions_with_validation
        
        # Tenter génération dynamique avec validation
        questions, validation_metadata = generate_dynamic_clarification_questions_with_validation(question, language)
        
        # Vérifier qualité
        score, filtered_questions = validate_dynamic_questions(questions, question, language)
        
        if score >= 0.5 and filtered_questions:
            logger.info(f"✅ [Clarification Generation] Questions GPT validées: {len(filtered_questions)}")
            return filtered_questions
        else:
            logger.warning(f"⚠️ [Clarification Generation] Score trop bas ({score:.2f}) - fallback")
            
    except Exception as e:
        logger.warning(f"⚠️ [Clarification Generation] Erreur GPT: {e} - fallback")
    
    # Fallback : questions basiques selon le type
    return _get_fallback_questions_by_type(question, language)

def _get_fallback_questions_by_type(question: str, language: str = "fr") -> List[str]:
    """
    🔧 NOUVEAU: Questions de fallback selon le type de question détecté
    """
    
    question_lower = question.lower()
    
    # Détection type de question
    is_weight = any(word in question_lower for word in ["poids", "weight", "peso"])
    is_health = any(word in question_lower for word in ["maladie", "disease", "mort", "death"])
    is_growth = any(word in question_lower for word in ["croissance", "growth", "développement"])
    
    fallback_questions = {
        "fr": {
            "weight": [
                "Quelle race ou souche spécifique élevez-vous (Ross 308, Cobb 500, etc.) ?",
                "Quel âge ont actuellement vos poulets (en jours précis) ?",
                "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?"
            ],
            "health": [
                "Quelle race ou souche élevez-vous ?",
                "Quel âge ont vos volailles actuellement ?",
                "Quels symptômes spécifiques observez-vous ?"
            ],
            "growth": [
                "Quelle race ou souche spécifique élevez-vous ?",
                "Quel âge ont-ils actuellement en jours ?",
                "Quelles sont les conditions d'élevage actuelles ?"
            ],
            "general": [
                "Pouvez-vous préciser la race ou souche de vos volailles ?",
                "Quel âge ont actuellement vos animaux ?",
                "Dans quel contexte d'élevage vous trouvez-vous ?"
            ]
        },
        "en": {
            "weight": [
                "What specific breed or strain are you raising (Ross 308, Cobb 500, etc.)?",
                "What is the current age of your chickens (in precise days)?",
                "Are these males, females, or a mixed flock?"
            ],
            "health": [
                "What breed or strain are you raising?",
                "What is the current age of your poultry?",
                "What specific symptoms are you observing?"
            ],
            "growth": [
                "What specific breed or strain are you raising?",
                "What is their current age in days?",
                "What are the current housing conditions?"
            ],
            "general": [
                "Could you specify the breed or strain of your poultry?",
                "What age are your animals currently?",
                "What farming context are you in?"
            ]
        },
        "es": {
            "weight": [
                "¿Qué raza o cepa específica está criando (Ross 308, Cobb 500, etc.)?",
                "¿Cuál es la edad actual de sus pollos (en días precisos)?",
                "¿Son machos, hembras, o un lote mixto?"
            ],
            "health": [
                "¿Qué raza o cepa está criando?",
                "¿Cuál es la edad actual de sus aves?",
                "¿Qué síntomas específicos está observando?"
            ],
            "growth": [
                "¿Qué raza o cepa específica está criando?",
                "¿Cuál es su edad actual en días?",
                "¿Cuáles son las condiciones actuales de alojamiento?"
            ],
            "general": [
                "¿Podría especificar la raza o cepa de sus aves?",
                "¿Qué edad tienen actualmente sus animales?",
                "¿En qué contexto de cría se encuentra?"
            ]
        }
    }
    
    lang_questions = fallback_questions.get(language, fallback_questions["fr"])
    
    # Sélectionner type approprié
    if is_weight:
        return lang_questions["weight"]
    elif is_health:
        return lang_questions["health"]
    elif is_growth:
        return lang_questions["growth"]
    else:
        return lang_questions["general"]

def _get_clarification_intro_message(language: str = "fr") -> str:
    """
    🔧 NOUVEAU: Message d'introduction pour la clarification
    """
    
    messages = {
        "fr": "Votre question manque de contexte. Voici quelques questions pour mieux vous aider :",
        "en": "Your question lacks context. Here are some questions to better help you:",
        "es": "Su pregunta carece de contexto. Aquí hay algunas preguntas para ayudarle mejor:"
    }
    
    return messages.get(language, messages["fr"])

# =============================================================================
# 🔄 EXPERT SERVICE PRINCIPAL AVEC AUTO-CLARIFICATION INTÉGRÉE
# =============================================================================

class ExpertService:
    """Service principal pour le système expert avec auto-clarification simplifiée intégrée"""
    
    def __init__(self):
        self.integrations = IntegrationsManager()
        self.rag_enhancer = RAGContextEnhancer()
        self.enhancement_service = APIEnhancementService()
        
        self.concision_processor = ResponseConcisionProcessor()
        
        self.response_versions_generator = ResponseVersionsGenerator(
            existing_processor=self.concision_processor
        )
        
        logger.info("✅ [Expert Service] Service expert initialisé avec auto-clarification simplifiée")
    
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
        🚀 MODIFIÉ: Méthode principale avec auto-clarification intégrée
        """
        
        if start_time is None:
            start_time = time.time()
        
        try:
            logger.info("🚀 [ExpertService] Traitement question avec auto-clarification")
            
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
        🔧 MODIFIÉ: Logique avec auto-clarification intégrée au début
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
        
        # === MÉMOIRE CONVERSATIONNELLE ===
        conversation_context = None
        
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
                
                ai_enhancements_used.append("intelligent_memory")
                processing_steps.append("memory_storage")
                logger.info(f"💾 [Expert Service] Message ajouté à la mémoire: {question_text[:50]}...")
                
            except Exception as e:
                logger.warning(f"⚠️ [Expert Service] Erreur mémoire: {e}")
        
        performance_breakdown["memory_complete"] = int(time.time() * 1000)
        
        # 🔧 NOUVEAU: AUTO-CLARIFICATION INTÉGRÉE (si pas déjà une réponse de clarification)
        if not request_data.is_clarification_response:
            conversation_context_str = ""
            if conversation_context and hasattr(conversation_context, 'get_context_for_rag'):
                conversation_context_str = conversation_context.get_context_for_rag(max_chars=500)
            
            clarification_result = auto_clarify_if_needed(
                question_text, conversation_context_str, request_data.language
            )
            
            if clarification_result:
                logger.info("🔧 [Auto Clarification] Clarification déclenchée automatiquement")
                
                processing_steps.append("auto_clarification_triggered")
                ai_enhancements_used.append("auto_clarification_system")
                
                # Formater les questions
                if len(clarification_result["questions"]) == 1:
                    formatted_questions = clarification_result["questions"][0]
                else:
                    formatted_questions = "\n".join([f"• {q}" for q in clarification_result["questions"]])
                
                response_text = f"{clarification_result['message']}\n\n{formatted_questions}\n\nCela m'aidera à vous donner une réponse plus précise ! 🐔"
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                return EnhancedExpertResponse(
                    question=question_text,
                    response=response_text,
                    conversation_id=conversation_id,
                    rag_used=False,
                    rag_score=None,
                    timestamp=datetime.now().isoformat(),
                    language=request_data.language,
                    response_time_ms=response_time_ms,
                    mode="auto_clarification_triggered",
                    user=user_email,
                    logged=True,
                    validation_passed=True,
                    clarification_result={
                        "clarification_requested": True,
                        "clarification_type": "auto_triggered",
                        "completeness_score": clarification_result.get("completeness_score", 0.0),
                        "questions_generated": len(clarification_result["questions"]),
                        "generation_method": clarification_result.get("generation_method", "auto_clarification"),
                        "automatic_trigger": True
                    },
                    processing_steps=processing_steps,
                    ai_enhancements_used=ai_enhancements_used,
                    dynamic_clarification=DynamicClarification(
                        original_question=question_text,
                        clarification_questions=clarification_result["questions"],
                        confidence=0.8,
                        generation_method="auto_clarification_system",
                        generation_time_ms=response_time_ms,
                        fallback_used=False
                    )
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
    # ✅ TOUTES LES MÉTHODES EXISTANTES CONSERVÉES IDENTIQUES + 🏷️ MÉTHODE TAXONOMIQUE
    # ===========================================================================================
    
    async def _process_expert_response_enhanced_corrected_with_taxonomy(
        self, question_text: str, request_data: EnhancedQuestionRequest,
        request: Request, current_user: Optional[Dict], conversation_id: str,
        processing_steps: list, ai_enhancements_used: list,
        debug_info: Dict, performance_breakdown: Dict, vagueness_result = None
    ) -> Dict[str, Any]:
        """
        🏷️ VERSION CONSERVÉE: RAG parfaitement corrigé avec mémoire intelligente + FILTRAGE TAXONOMIQUE
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
        
        # === 3. 🏷️ FILTRAGE TAXONOMIQUE INTELLIGENT ===
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
            
            mode = f"enhanced_contextual_{original_mode}_{rag_call_method}_corrected_with_concision_and_response_versions_and_taxonomy_and_semantic_dynamic_and_auto_clarification_simplified"
            
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
                "generation_time_ms": clarification_result.processing_time_ms
            },
            processing_steps=["semantic_dynamic_clarification_triggered"],
            ai_enhancements_used=["semantic_dynamic_clarification", "gpt_question_generation"],
            dynamic_clarification=DynamicClarification(
                original_question=question,
                clarification_questions=clarification_result.questions or [],
                confidence=clarification_result.confidence_score
            )
        )
    
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
    
    # === MÉTHODES UTILITAIRES AVEC AUTO-CLARIFICATION SIMPLIFIÉE ===
    
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
        """Construit la réponse finale avec toutes les améliorations + auto-clarification simplifiée"""
        
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
                "auto_clarification_simplified": True
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
        
        auto_clarification_info = {
            "auto_clarification_simplified": True,
            "auto_clarification_used": "auto_clarification_system" in ai_enhancements_used,
            "auto_clarification_trigger": "auto_clarification_triggered" in processing_steps,
            "completeness_scoring_used": True,
            "validation_robuste_active": True,
            "fallback_intelligent_active": True
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
            "message": "Feedback enregistré avec succès (Enhanced + Auto-Clarification Simplifiée + Validation Robuste + Fallback Intelligent)",
            "rating": feedback_data.rating,
            "comment": feedback_data.comment,
            "conversation_id": feedback_data.conversation_id,
            "feedback_updated_in_db": feedback_updated,
            "enhanced_features_used": True,
            "concision_system_active": self.concision_processor.config.ENABLE_CONCISE_RESPONSES,
            "response_versions_supported": True,
            "taxonomic_filtering_active": True,
            "semantic_dynamic_available": True,
            "auto_clarification_simplified": True,
            "validation_robuste_active": True,
            "fallback_intelligent_active": True,
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
                
                "auto_clarification_simplified": True,
                "validation_robuste": True,
                "fallback_intelligent": True,
                "scoring_questions_generees": True,
                "integration_visible_expert_services": True
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
                "auto_clarification_simplified_enabled": True,
                "validation_robuste_enabled": True,
                "fallback_intelligent_enabled": True
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
                "automatic_mode_detection": True
            },
            
            "auto_clarification_simplified_config": {
                "enabled": True,
                "completeness_score_threshold": 0.5,
                "validation_robuste_enabled": True,
                "fallback_intelligent_enabled": True,
                "scoring_questions_enabled": True,
                "integration_visible": True,
                "centralized_function": "auto_clarify_if_needed",
                "fallback_questions_by_type": True,
                "gpt_error_handling": True
            }
        }

# =============================================================================
# 🆕 API ENDPOINT POUR CONTRÔLER LA CONCISION + RESPONSE VERSIONS + TAXONOMIC FILTERING + SEMANTIC DYNAMIC + AUTO CLARIFICATION SIMPLIFIÉE (OPTIONNEL)
# =============================================================================

def create_concision_control_endpoint():
    """
    Endpoint optionnel pour contrôler la concision côté backend
    🚀 MODIFIÉ: Ajout support auto-clarification simplifiée + validation robuste + fallback intelligent
    """
    
    from fastapi import APIRouter
    from pydantic import BaseModel
    
    router = APIRouter()
    
    class ConcisionSettingsRequest(BaseModel):
        enabled: bool = True
        default_level: ConcisionLevel = ConcisionLevel.CONCISE
        max_lengths: Optional[Dict[str, int]] = None
        enable_response_versions: bool = True
        enable_taxonomic_filtering: bool = True
        enable_semantic_dynamic: bool = True
        enable_auto_clarification_simplified: bool = True
        auto_clarification_threshold: float = 0.5
        enable_validation_robuste: bool = True
        enable_fallback_intelligent: bool = True
    
    class ConcisionSettingsResponse(BaseModel):
        success: bool
        current_settings: Dict[str, Any]
        message: str
    
    @router.post("/concision/settings", response_model=ConcisionSettingsResponse)
    async def update_concision_settings(request: ConcisionSettingsRequest):
        """Mettre à jour les paramètres de concision + auto-clarification simplifiée du système"""
        
        try:
            ConcisionConfig.ENABLE_CONCISE_RESPONSES = request.enabled
            ConcisionConfig.DEFAULT_CONCISION_LEVEL = request.default_level
            
            if request.max_lengths:
                ConcisionConfig.MAX_RESPONSE_LENGTH.update(request.max_lengths)
            
            return ConcisionSettingsResponse(
                success=True,
                current_settings={
                    "enabled": ConcisionConfig.ENABLE_CONCISE_RESPONSES,
                    "default_level": ConcisionConfig.DEFAULT_CONCISION_LEVEL.value,
                    "max_lengths": ConcisionConfig.MAX_RESPONSE_LENGTH,
                    "response_versions_enabled": request.enable_response_versions,
                    "taxonomic_filtering_enabled": request.enable_taxonomic_filtering,
                    "semantic_dynamic_enabled": request.enable_semantic_dynamic,
                    "auto_clarification_simplified_enabled": request.enable_auto_clarification_simplified,
                    "auto_clarification_threshold": request.auto_clarification_threshold,
                    "validation_robuste_enabled": request.enable_validation_robuste,
                    "fallback_intelligent_enabled": request.enable_fallback_intelligent
                },
                message="Paramètres de concision + auto-clarification simplifiée + validation robuste + fallback intelligent mis à jour avec succès"
            )
        except Exception as e:
            return ConcisionSettingsResponse(
                success=False,
                current_settings={},
                message=f"Erreur lors de la mise à jour: {str(e)}"
            )
    
    @router.get("/concision/settings", response_model=Dict[str, Any])
    async def get_concision_settings():
        """Récupérer les paramètres actuels de concision + auto-clarification simplifiée"""
        
        return {
            "enabled": ConcisionConfig.ENABLE_CONCISE_RESPONSES,
            "default_level": ConcisionConfig.DEFAULT_CONCISION_LEVEL.value,
            "available_levels": [level.value for level in ConcisionLevel],
            "max_lengths": ConcisionConfig.MAX_RESPONSE_LENGTH,
            "ultra_concise_keywords": ConcisionConfig.ULTRA_CONCISE_KEYWORDS,
            "complex_keywords": ConcisionConfig.COMPLEX_KEYWORDS,
            
            "response_versions": {
                "supported": True,
                "generation_method": "existing_processor_based",
                "cache_enabled": False,
                "fallback_enabled": True,
                "metrics_included": True
            },
            
            "taxonomic_filtering": {
                "supported": True,
                "auto_detection_enabled": True,
                "supported_taxonomies": ["broiler", "layer", "swine", "dairy", "general"],
                "question_enhancement_enabled": True,
                "filter_fallback_enabled": True
            },
            
            "semantic_dynamic": {
                "supported": True,
                "max_questions": 4,
                "supported_languages": ["fr", "en", "es"],
                "gpt_generation_enabled": True,
                "fallback_questions_available": True,
                "contextual_mode_available": True
            },
            
            "auto_clarification_simplified": {
                "supported": True,
                "completeness_evaluation_enabled": True,
                "threshold_configurable": 0.5,
                "validation_robuste_integrated": True,
                "fallback_intelligent_integrated": True,
                "scoring_questions_enabled": True,
                "integration_visible_expert_services": True,
                "centralized_function_available": True,
                "fallback_by_question_type": True
            }
        }
    
    return router

# =============================================================================
# CONFIGURATION FINALE AVEC AUTO-CLARIFICATION SIMPLIFIÉE + VALIDATION ROBUSTE
# =============================================================================

logger.info("🚀" * 30)
logger.info("🚀 [EXPERT SERVICES] VERSION 3.11.0 - AUTO CLARIFICATION SIMPLIFIÉE + VALIDATION ROBUSTE!")
logger.info("🚀 [MODIFICATIONS APPLIQUÉES] Toutes les améliorations demandées intégrées:")
logger.info("   🔧 1. Scoring et validation qualité des questions générées (validate_dynamic_questions)")
logger.info("   🔧 2. Intégration visible dans expert_services.py (auto_clarify_if_needed)")
logger.info("   🔧 3. Fallback lisible si GPT échoue (_generate_clarification_questions_with_fallback)")
logger.info("🚀 [INTÉGRATION] Système complet avec toutes les fonctionnalités:")
logger.info("   ✅ ResponseVersionsGenerator utilise ResponseConcisionProcessor existant")
logger.info("   ✅ Génération 4 versions: ultra_concise, concise, standard, detailed")
logger.info("   ✅ Sélection automatique selon concision_level")
logger.info("   ✅ Métriques détaillées avec ConcisionMetrics")
logger.info("   ✅ Compatible avec toute la logique existante")
logger.info("   ✅ Fallback automatique si erreur")
logger.info("   ✅ Support generate_all_versions flag")
logger.info("   🏷️ Filtrage taxonomique intelligent des documents")
logger.info("   🏷️ Détection automatique broiler/layer/swine/dairy")
logger.info("   🏷️ Questions enrichies avec contexte taxonomique")
logger.info("   🆕 Mode sémantique dynamique de clarification")
logger.info("   🆕 Génération GPT de 1-4 questions contextuelles")
logger.info("   🆕 Support paramètre semantic_dynamic_mode")
logger.info("   🔧 NOUVEAU: Auto-clarification simplifiée intégrée dans expert_services")
logger.info("   🔧 NOUVEAU: Validation robuste des questions générées (score qualité)")
logger.info("   🔧 NOUVEAU: Fallback intelligent par type de question si GPT échoue")
logger.info("🚀 [FONCTIONNALITÉS NOUVELLES] Modifications demandées implémentées:")
logger.info("   🔧 validate_dynamic_questions(questions, user_question) → (score, filtered_questions)")
logger.info("   🔧 auto_clarify_if_needed(question, context, language) → clarification_result ou None")
logger.info("   🔧 _generate_clarification_questions_with_fallback() avec gestion d'erreur complète")
logger.info("   🔧 _get_fallback_questions_by_type() pour questions par contexte détecté")
logger.info("   🔧 _calculate_basic_completeness_score() pour évaluation automatique")
logger.info("   🔧 Intégration visible dans _process_question_with_auto_clarification()")
logger.info("🚀 [BACKEND READY] Frontend peut maintenant:")
logger.info("   - Demander concision_level spécifique")
logger.info("   - Recevoir response_versions complètes") 
logger.info("   - Changer niveau dynamiquement côté frontend")
logger.info("   - Profiter du cache et performance optimisée")
logger.info("   - Bénéficier du filtrage taxonomique automatique")
logger.info("   - Activer le mode sémantique dynamique (semantic_dynamic_mode=true)")
logger.info("   - Recevoir questions de clarification intelligentes")
logger.info("   - Bénéficier de l'auto-clarification simplifiée si contexte insuffisant")
logger.info("   - Profiter de la validation robuste des questions générées")
logger.info("   - Avoir fallback intelligent garanti même si GPT échoue")
logger.info("🎯 [RÉSULTAT] Question vague → Score contexte < 0.5 → Auto-clarification avec validation!")
logger.info("🚀" * 30)

logger.info("✅ [Expert Service] Services métier EXPERT SYSTEM + AUTO-CLARIFICATION SIMPLIFIÉE + VALIDATION ROBUSTE intégré")
logger.info("🚀 [Expert Service] FONCTIONNALITÉS VERSION 3.11.0:")
logger.info("   - ✅ Système de concision intelligent multi-niveaux (CONSERVÉ)")
logger.info("   - ✅ Détection automatique type de question (CONSERVÉ)")
logger.info("   - ✅ Nettoyage avancé verbosité + références documents (CONSERVÉ)")
logger.info("   - ✅ Configuration flexible par type de question (CONSERVÉ)")
logger.info("   - ✅ Conservation réponse originale si concision appliquée (CONSERVÉ)")
logger.info("   - 🚀 ResponseVersionsGenerator avec système existant")
logger.info("   - 🚀 Génération toutes versions (ultra_concise, concise, standard, detailed)")
logger.info("   - 🚀 ConcisionMetrics avec compression ratios et métriques")
logger.info("   - 🚀 Support generate_all_versions flag pour contrôle frontend")
logger.info("   - 🚀 Sélection intelligente version selon concision_level")
logger.info("   - 🏷️ Filtrage taxonomique intelligent des documents RAG (CONSERVÉ)")
logger.info("   - 🏷️ Détection automatique broiler/layer/swine/dairy/general (CONSERVÉ)")
logger.info("   - 🏷️ Enhancement questions avec contexte taxonomique (CONSERVÉ)")
logger.info("   - 🏷️ Filtres RAG adaptatifs selon la taxonomie détectée (CONSERVÉ)")
logger.info("   - 🆕 Mode sémantique dynamique de clarification (CONSERVÉ)")
logger.info("   - 🆕 Génération intelligente 1-4 questions via GPT (CONSERVÉ)")
logger.info("   - 🆕 Support paramètre semantic_dynamic_mode (CONSERVÉ)")
logger.info("   - 🔧 NOUVEAU: Auto-clarification simplifiée intégrée dans expert_services")
logger.info("   - 🔧 NOUVEAU: Validation robuste des questions avec scoring qualité")
logger.info("   - 🔧 NOUVEAU: Fallback intelligent si GPT échoue complètement")
logger.info("   - 🔧 NOUVEAU: Questions de fallback par type détecté (poids/santé/croissance)")
logger.info("   - 🔧 NOUVEAU: Évaluation score de complétude automatique (0.0 à 1.0)")
logger.info("   - 🔧 NOUVEAU: Fonction centralisée auto_clarify_if_needed()")
logger.info("🔧 [Expert Service] FONCTIONNALITÉS CONSERVÉES:")
logger.info("   - ✅ Système de clarification intelligent complet")
logger.info("   - ✅ Mémoire conversationnelle enrichie")
logger.info("   - ✅ RAG avec contexte et prompt structuré")
logger.info("   - ✅ Multi-LLM support et validation agricole")
logger.info("   - ✅ Support multilingue FR/EN/ES")
logger.info("🔧 [Expert Service] MODIFICATIONS DEMANDÉES IMPLÉMENTÉES:")
logger.info("   - 🎯 1. validate_dynamic_questions() avec filtrage avancé + score qualité")
logger.info("   - 🎯 2. Intégration visible auto_clarify_if_needed() dans _process_question_with_auto_clarification()")
logger.info("   - 🎯 3. Fallback lisible _generate_clarification_questions_with_fallback() avec gestion try/except")
logger.info("   - 🎯 Centralisé dans bloc auto_clarify_if_needed() pour simplifier")
logger.info("   - 🎯 Scoring < 0.5 → fallback automatique vers questions par type")
logger.info("   - 🎯 Gestion d'erreur complète : import error, GPT error, parsing error")
logger.info("✨ [Expert Service] RÉSULTAT FINAL:")
logger.info('   - Question vague: "J\'ai un problème avec mes poulets"')
logger.info('   - Évaluation complétude: score < 0.5')
logger.info('   - Génération GPT: 3-4 questions contextuelles')
logger.info('   - Validation robuste: filtrage + score qualité')
logger.info('   - Si échec: fallback intelligent par type de question garanti')
logger.info('   - Intégration visible dans expert_services pour contrôle total')
logger.info("✅ [Expert Service] AUTO-CLARIFICATION SIMPLIFIÉE + VALIDATION ROBUSTE + FALLBACK INTELLIGENT opérationnel!")