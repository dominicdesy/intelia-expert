"""
app/api/v1/expert_concision_service.py - SERVICE DE CONCISION DES RÉPONSES

🚀 SERVICE INDÉPENDANT:
- Système de concision intelligent multi-niveaux
- Génération de toutes les versions de réponse
- Nettoyage avancé verbosité + références documents
- Configuration flexible par type de question
"""

import os
import logging
import time
import re
from typing import Optional, Dict, Any, List
from enum import Enum

from .expert_models import ConcisionLevel, ConcisionMetrics

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTÈME DE CONCISION DES RÉPONSES
# =============================================================================

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
    """Processeur de concision des réponses"""
    
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
        """Méthode unified pour appliquer la concision"""
        
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
        """Traite une réponse selon le niveau de concision demandé"""
        
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
        """Nettoie uniquement les références aux documents"""
        
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
# GÉNÉRATEUR DE VERSIONS DE RÉPONSE
# =============================================================================

class ResponseVersionsGenerator:
    """Générateur de toutes les versions de réponse pour le frontend"""
    
    def __init__(self, existing_processor: ResponseConcisionProcessor):
        self.existing_processor = existing_processor
        logger.info("🚀 [ResponseVersions] Générateur initialisé avec système existant")
    
    async def generate_all_response_versions(
        self, 
        original_response: str, 
        question: str, 
        context: Dict[str, Any],
        requested_level: ConcisionLevel = ConcisionLevel.CONCISE
    ) -> Dict[str, Any]:
        """Génère toutes les versions de réponse en utilisant le système existant"""
        
        start_time = time.time()
        
        try:
            logger.info("🚀 [ResponseVersions] Génération toutes versions")
            logger.info(f"   - Question: {question[:50]}...")
            logger.info(f"   - Niveau demandé: {requested_level}")
            logger.info(f"   - Réponse originale: {len(original_response)} caractères")
            
            versions = {}
            
            # Version détaillée = réponse originale
            versions["detailed"] = original_response
            
            # Version standard
            standard_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.STANDARD,
                context.get("language", "fr")
            )
            versions["standard"] = standard_response
            
            # Version concise
            concise_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.CONCISE,
                context.get("language", "fr")
            )
            versions["concise"] = concise_response
            
            # Version ultra-concise
            ultra_concise_response = self.existing_processor.apply_concision(
                original_response, 
                question, 
                ConcisionLevel.ULTRA_CONCISE,
                context.get("language", "fr")
            )
            versions["ultra_concise"] = ultra_concise_response
            
            # Sélectionner la version demandée
            selected_response = versions.get(requested_level.value, versions["concise"])
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculer métriques
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
            
            # Fallback versions
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

logger.info("✅ [Concision Service] Service de concision des réponses initialisé")
