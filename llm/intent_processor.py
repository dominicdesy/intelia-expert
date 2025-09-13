# -*- coding: utf-8 -*-
"""
intent_processor.py - Processeur d'intentions métier pour Intelia Expert - Version Améliorée
Utilise intents.json pour améliorer la classification et l'expansion de requêtes
Améliorations : meilleure gestion d'erreurs, scoring optimisé, cache pour performance
"""

import os
import json
import logging
import re
import time
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types d'intentions métier"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    GENERAL_POULTRY = "general_poultry"
    OUT_OF_DOMAIN = "out_of_domain"

@dataclass
class IntentResult:
    """Résultat de classification d'intention - version améliorée"""
    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, str]
    expanded_query: str
    metadata: Dict
    processing_time: float = 0.0  # Nouveau
    confidence_breakdown: Dict[str, float] = None  # Nouveau pour debugging
    
    def __post_init__(self):
        if self.confidence_breakdown is None:
            self.confidence_breakdown = {}

class PoultryVocabularyExtractor:
    """Extracteur de vocabulaire spécialisé depuis intents.json - Version optimisée"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.poultry_keywords = self._build_vocabulary()
        self.alias_mappings = self._build_alias_mappings()
        self.specialized_terms = self._build_specialized_terms()
        
    def _build_vocabulary(self) -> Set[str]:
        """Construit le vocabulaire complet du domaine avicole - version optimisée"""
        keywords = set()
        
        aliases = self.intents_config.get("aliases", {})
        
        # Lignées de volailles
        for line_type, line_aliases in aliases.get("line", {}).items():
            keywords.add(line_type.lower())
            keywords.update([alias.lower() for alias in line_aliases])
        
        # Types d'élevage et sites
        for site_type, site_aliases in aliases.get("site_type", {}).items():
            keywords.add(site_type.lower())
            keywords.update([alias.lower() for alias in site_aliases])
        
        # Types d'oiseaux
        for bird_type, bird_aliases in aliases.get("bird_type", {}).items():
            keywords.add(bird_type.lower())
            keywords.update([alias.lower() for alias in bird_aliases])
        
        # Phases d'élevage
        for phase, phase_aliases in aliases.get("phase", {}).items():
            keywords.add(phase.lower())
            keywords.update([alias.lower() for alias in phase_aliases])
        
        # Métriques techniques
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = intent_config.get("metrics", {})
            keywords.update([metric.lower() for metric in metrics.keys()])
        
        # Mots-clés additionnels du domaine (étendus)
        additional_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann', 'poussin', 'chick', 'œuf', 'egg',
            'breeding', 'reproduction', 'ponte', 'laying', 'feed conversion', 'conversion',
            'welfare', 'bien-être', 'animal', 'density', 'densité', 'housing', 'logement'
        }
        keywords.update(additional_keywords)
        
        logger.info(f"Vocabulaire avicole construit: {len(keywords)} termes")
        return keywords
    
    def _build_alias_mappings(self) -> Dict[str, str]:
        """Construit les mappings alias -> terme canonique - version optimisée"""
        mappings = {}
        
        for category, items in self.intents_config.get("aliases", {}).items():
            for canonical, aliases in items.items():
                canonical_lower = canonical.lower()
                mappings[canonical_lower] = canonical_lower
                for alias in aliases:
                    mappings[alias.lower()] = canonical_lower
        
        return mappings
    
    def _build_specialized_terms(self) -> Dict[str, float]:
        """Construit un dictionnaire de termes spécialisés avec scores de spécificité"""
        specialized = {}
        
        # Termes très spécifiques (score élevé)
        high_specificity = ['ross', 'cobb', 'hubbard', 'fcr', 'epef', 'biosécurité', 'couvoir']
        for term in high_specificity:
            specialized[term] = 2.0
        
        # Termes modérément spécifiques
        medium_specificity = ['poulet', 'chicken', 'aviculture', 'poultry', 'poussin', 'chick']
        for term in medium_specificity:
            specialized[term] = 1.5
        
        # Termes généraux mais dans le domaine
        low_specificity = ['élevage', 'production', 'croissance', 'growth', 'farming']
        for term in low_specificity:
            specialized[term] = 1.0
        
        return specialized
    
    @lru_cache(maxsize=1000)  # Cache pour optimiser les requêtes répétées
    def is_poultry_related(self, text: str) -> Tuple[bool, float, Dict[str, float]]:
        """Détermine si un texte est lié à l'aviculture - version améliorée avec cache"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        if not words:
            return False, 0.0, {}
        
        # Compter les mots du vocabulaire avicole avec pondération
        vocab_score = 0.0
        found_terms = {}
        
        for word in words:
            if word in self.poultry_keywords:
                # Appliquer le score de spécificité si disponible
                specificity = self.specialized_terms.get(word, 1.0)
                vocab_score += specificity
                found_terms[word] = specificity
        
        # Normaliser par le nombre de mots
        normalized_score = vocab_score / len(words) if words else 0.0
        
        # Bonus si des termes très spécifiques sont détectés
        high_specificity_bonus = 0.0
        for term in ['ross', 'cobb', 'hubbard', 'broiler', 'layer', 'fcr', 'aviculture']:
            if term in text_lower:
                high_specificity_bonus += 0.2
        
        final_score = min(1.0, normalized_score + high_specificity_bonus)
        
        # Seuil adaptatif selon la longueur du texte
        threshold = 0.15 if len(words) > 10 else 0.1
        is_poultry = final_score >= threshold or high_specificity_bonus > 0.3
        
        score_details = {
            "vocab_score": normalized_score,
            "specificity_bonus": high_specificity_bonus,
            "final_score": final_score,
            "found_terms": found_terms,
            "threshold_used": threshold
        }
        
        logger.debug(f"Classification vocabulaire optimisée: '{text[:50]}...' -> {is_poultry} (score: {final_score:.3f})")
        
        return is_poultry, final_score, score_details

class QueryExpander:
    """Expanseur de requêtes avec synonymes du domaine - Version améliorée"""
    
    def __init__(self, vocabulary_extractor: PoultryVocabularyExtractor):
        self.vocab_extractor = vocabulary_extractor
        self.alias_mappings = vocabulary_extractor.alias_mappings
        self.expansion_cache = {}  # Cache pour les expansions courantes
    
    @lru_cache(maxsize=500)
    def expand_query(self, query: str, max_expansions: int = 5) -> str:
        """Enrichit une requête avec des synonymes et termes liés - avec cache"""
        query_lower = query.lower()
        expansion_terms = set()
        
        # Détecter les alias dans la requête et ajouter les formes canoniques
        for alias, canonical in self.alias_mappings.items():
            if alias in query_lower and alias != canonical:
                expansion_terms.add(canonical)
                
                # Ajouter quelques alias supplémentaires du même groupe
                related_aliases = [k for k, v in self.alias_mappings.items() 
                                 if v == canonical and k != alias][:2]
                expansion_terms.update(related_aliases)
        
        # Expansion contextuelle basée sur les entités détectées
        if any(term in query_lower for term in ['poids', 'weight', 'gramme']):
            expansion_terms.update(['body weight', 'gain', 'croissance'])
        
        if any(term in query_lower for term in ['fcr', 'conversion']):
            expansion_terms.update(['feed conversion ratio', 'efficiency', 'indice'])
        
        # Limiter le nombre d'expansions pour éviter la pollution
        expansion_terms = list(expansion_terms)[:max_expansions]
        
        if expansion_terms:
            expanded_query = query + " " + " ".join(expansion_terms)
            logger.debug(f"Requête expansée: '{query}' -> '{expanded_query}'")
            return expanded_query
        
        return query

class EntityExtractor:
    """Extracteur d'entités métier - Version améliorée avec regex optimisés"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        # Patterns regex optimisés
        self.age_pattern = re.compile(r'\b(\d+)\s*(jour|day|semaine|week|j|sem|d)\b', re.IGNORECASE)
        self.weight_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(g|gramme|kg|kilogramme|gram)\b', re.IGNORECASE)
        self.percentage_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%\b')
        self.temperature_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(?:°C|celsius|degré)\b', re.IGNORECASE)
        
    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extrait les entités métier d'un texte - version optimisée"""
        entities = {}
        text_lower = text.lower()
        
        try:
            # Extraction des lignées avec gestion d'erreurs
            entities.update(self._extract_lines(text_lower))
            
            # Extraction des âges avec validation
            entities.update(self._extract_ages(text))
            
            # Extraction des types de site
            entities.update(self._extract_site_types(text_lower))
            
            # Extraction des métriques avec patterns améliorés
            entities.update(self._extract_metrics(text_lower))
            
            # Extraction des phases
            entities.update(self._extract_phases(text_lower))
            
            # Nouvelles extractions améliorées
            entities.update(self._extract_numeric_values(text))
            
        except Exception as e:
            logger.error(f"Erreur extraction entités: {e}")
        
        return entities
    
    def _extract_lines(self, text: str) -> Dict[str, str]:
        """Extrait les lignées de volailles avec correspondance floue"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("line", {}).items():
            # Correspondance exacte d'abord
            if canonical.lower() in text:
                return {"line": canonical}
            
            # Correspondance par alias
            for alias in aliases:
                if alias.lower() in text:
                    return {"line": canonical}
            
            # Correspondance floue pour les codes (ex: "308" pour "ross 308")
            if any(char.isdigit() for char in canonical):
                numbers = re.findall(r'\d+', canonical)
                if numbers and any(num in text for num in numbers):
                    # Vérifier le contexte pour éviter les faux positifs
                    for num in numbers:
                        context = text[max(0, text.find(num)-10):text.find(num)+20]
                        if any(brand in context for brand in ['ross', 'cobb', 'hubbard']):
                            return {"line": canonical}
        
        return {}
    
    def _extract_ages(self, text: str) -> Dict[str, str]:
        """Extrait les informations d'âge avec validation améliorée"""
        entities = {}
        
        matches = self.age_pattern.findall(text)
        for number_str, unit in matches:
            try:
                age_value = int(number_str)
                
                # Validation des valeurs d'âge réalistes
                if age_value < 0 or age_value > 600:  # Plus de 600 jours peu probable
                    continue
                
                unit_lower = unit.lower()
                
                if unit_lower in ['jour', 'day', 'j', 'd']:
                    entities["age_days"] = str(age_value)
                    entities["age_weeks"] = str(max(1, age_value // 7))
                elif unit_lower in ['semaine', 'week', 'sem']:
                    entities["age_weeks"] = str(age_value)
                    entities["age_days"] = str(age_value * 7)
                
                break  # Prendre seulement le premier âge trouvé
                
            except ValueError:
                continue
        
        return entities
    
    def _extract_site_types(self, text: str) -> Dict[str, str]:
        """Extrait les types de site d'élevage"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("site_type", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"site_type": canonical}
        return {}
    
    def _extract_metrics(self, text: str) -> Dict[str, str]:
        """Extrait les métriques mentionnées avec matching amélioré"""
        detected_metrics = []
        
        for intent_config in self.intents_config.get("intents", {}).values():
            metrics = intent_config.get("metrics", {})
            for metric_name in metrics.keys():
                metric_lower = metric_name.lower()
                
                # Correspondance directe
                if metric_lower in text:
                    detected_metrics.append(metric_name)
                    continue
                
                # Correspondance par mots-clés décomposés
                metric_keywords = metric_lower.replace('_', ' ').split()
                if len(metric_keywords) > 1:
                    matches = sum(1 for keyword in metric_keywords if keyword in text)
                    if matches >= len(metric_keywords) // 2:  # Au moins la moitié des mots
                        detected_metrics.append(metric_name)
        
        if detected_metrics:
            return {"metrics": ",".join(detected_metrics[:3])}  # Limite à 3 métriques
        return {}
    
    def _extract_phases(self, text: str) -> Dict[str, str]:
        """Extrait les phases d'élevage"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("phase", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"phase": canonical}
        return {}
    
    def _extract_numeric_values(self, text: str) -> Dict[str, str]:
        """Nouvelle méthode: extrait les valeurs numériques avec contexte"""
        entities = {}
        
        # Poids
        weight_matches = self.weight_pattern.findall(text)
        if weight_matches:
            value, unit = weight_matches[0]
            entities["weight_value"] = value.replace(',', '.')
            entities["weight_unit"] = unit.lower()
        
        # Pourcentages
        percentage_matches = self.percentage_pattern.findall(text)
        if percentage_matches:
            entities["percentage_value"] = percentage_matches[0].replace(',', '.')
        
        # Températures
        temp_matches = self.temperature_pattern.findall(text)
        if temp_matches:
            entities["temperature_value"] = temp_matches[0].replace(',', '.')
        
        return entities

class IntentClassifier:
    """Classificateur d'intentions métier - Version optimisée"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.intent_keywords = self._build_intent_keywords()
        self.intent_patterns = self._build_intent_patterns()
    
    def _build_intent_keywords(self) -> Dict[str, Set[str]]:
        """Construit les mots-clés associés à chaque type d'intention - étendu"""
        keywords = {}
        
        # Mots-clés pour metric_query (étendus)
        keywords[IntentType.METRIC_QUERY.value] = {
            'poids', 'weight', 'fcr', 'conversion', 'consommation', 'eau', 'water',
            'performance', 'production', 'croissance', 'growth', 'optimal', 'target',
            'gramme', 'kg', 'litre', 'pourcentage', 'combien', 'how much', 'quelle',
            'indice', 'ratio', 'efficiency', 'rendement', 'objectif', 'standard'
        }
        
        # Mots-clés pour environment_setting (étendus)
        keywords[IntentType.ENVIRONMENT_SETTING.value] = {
            'température', 'temperature', 'ventilation', 'climatisation', 'chauffage',
            'humidité', 'humidity', 'air', 'climat', 'ambiance', 'réglage', 'setting',
            'environnement', 'environment', 'conditions', 'atmosph', 'tunnel', 'pad'
        }
        
        # Mots-clés pour protocol_query (étendus)
        keywords[IntentType.PROTOCOL_QUERY.value] = {
            'vaccination', 'protocole', 'protocol', 'traitement', 'treatment',
            'biosécurité', 'biosecurity', 'prévention', 'prevention', 'vaccin',
            'programme', 'program', 'schedule', 'planning', 'sanitaire'
        }
        
        # Mots-clés pour diagnosis_triage (étendus)
        keywords[IntentType.DIAGNOSIS_TRIAGE.value] = {
            'maladie', 'disease', 'symptôme', 'symptom', 'diagnostic', 'diagnosis',
            'mortalité', 'mortality', 'problème', 'problem', 'signes', 'signs',
            'pathologie', 'infection', 'virus', 'bacteria', 'parasite', 'sick'
        }
        
        # Mots-clés pour economics_cost (étendus)
        keywords[IntentType.ECONOMICS_COST.value] = {
            'coût', 'cost', 'prix', 'price', 'économique', 'economic', 'rentabilité',
            'profit', 'marge', 'margin', 'budget', 'finance', 'euros', 'dollars',
            'investment', 'investissement', 'return', 'roi', 'amortissement'
        }
        
        return keywords
    
    def _build_intent_patterns(self) -> Dict[str, List[str]]:
        """Construit des patterns regex pour chaque intention"""
        patterns = {}
        
        patterns[IntentType.METRIC_QUERY.value] = [
            r'\b(?:combien|how much|quelle?\s+(?:est|is))\b',
            r'\b(?:poids|weight|fcr)\s+(?:de|of|à|at)\b',
            r'\b\d+\s*(?:g|kg|%|litres?|days?|jours?)\b'
        ]
        
        patterns[IntentType.ENVIRONMENT_SETTING.value] = [
            r'\b(?:température|temperature|ventilation)\s+(?:optimale?|optimal|recommended)\b',
            r'\b(?:comment|how)\s+(?:régler|set|ajuster|adjust)\b'
        ]
        
        patterns[IntentType.DIAGNOSIS_TRIAGE.value] = [
            r'\b(?:mes|my)\s+(?:poulets?|chickens?)\s+(?:sont|are)\b',
            r'\b(?:symptômes?|symptoms?|signes?|signs?)\s+(?:de|of)\b'
        ]
        
        return patterns
    
    def classify_intent(self, text: str, entities: Dict[str, str]) -> Tuple[IntentType, Dict[str, float]]:
        """Classifie l'intention d'une requête avec scoring détaillé"""
        text_lower = text.lower()
        scores = {}
        score_breakdown = {}
        
        # Calculer les scores pour chaque intention
        for intent_type, keywords in self.intent_keywords.items():
            keyword_score = sum(1 for keyword in keywords if keyword in text_lower)
            pattern_score = 0
            
            # Vérifier les patterns regex si disponibles
            if intent_type in self.intent_patterns:
                for pattern in self.intent_patterns[intent_type]:
                    if re.search(pattern, text_lower):
                        pattern_score += 2  # Bonus pour match de pattern
            
            # Bonus basé sur les entités extraites
            entity_score = 0
            if intent_type == IntentType.METRIC_QUERY.value and "metrics" in entities:
                entity_score += 3
            elif intent_type == IntentType.METRIC_QUERY.value and any(key in entities for key in ["weight_value", "percentage_value"]):
                entity_score += 2
            elif intent_type == IntentType.ENVIRONMENT_SETTING.value and "temperature_value" in entities:
                entity_score += 2
            elif intent_type == IntentType.ENVIRONMENT_SETTING.value and "site_type" in entities:
                entity_score += 1
            elif intent_type == IntentType.ECONOMICS_COST.value and any(word in text_lower for word in ['coût', 'cost', 'prix']):
                entity_score += 2
            
            total_score = keyword_score + pattern_score + entity_score
            scores[intent_type] = total_score
            score_breakdown[intent_type] = {
                "keyword_score": keyword_score,
                "pattern_score": pattern_score,
                "entity_score": entity_score,
                "total_score": total_score
            }
        
        # Retourner l'intention avec le score le plus élevé
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            return IntentType(best_intent), score_breakdown
        
        # Fallback vers intention générale si aucune spécifique détectée
        return IntentType.GENERAL_POULTRY, score_breakdown

class IntentProcessor:
    """Processeur principal d'intentions métier - Version améliorée"""
    
    def __init__(self, intents_file_path: str):
        self.intents_config = self._load_intents_config(intents_file_path)
        self.vocabulary_extractor = PoultryVocabularyExtractor(self.intents_config)
        self.query_expander = QueryExpander(self.vocabulary_extractor)
        self.entity_extractor = EntityExtractor(self.intents_config)
        self.intent_classifier = IntentClassifier(self.intents_config)
        
        # Statistiques de performance
        self.processing_stats = {
            "total_queries": 0,
            "avg_processing_time": 0.0,
            "cache_hits": 0
        }
        
        logger.info(f"IntentProcessor Enhanced initialisé avec {len(self.vocabulary_extractor.poultry_keywords)} termes")
    
    def _load_intents_config(self, file_path: str) -> dict:
        """Charge la configuration des intentions avec gestion d'erreurs robuste"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Fichier intents.json introuvable: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validation basique de la structure
            required_keys = ["aliases", "intents"]
            for key in required_keys:
                if key not in config:
                    logger.warning(f"Clé manquante dans intents.json: {key}")
                    config[key] = {}
            
            logger.info(f"Configuration intentions chargée: {file_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans intents.json: {e}")
            return {}
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return {}
    
    def process_query(self, query: str) -> IntentResult:
        """Traite une requête complètement - version optimisée"""
        start_time = time.time()
        self.processing_stats["total_queries"] += 1
        
        try:
            # 1. Vérification du domaine avicole avec scoring détaillé
            is_poultry, vocab_confidence, vocab_details = self.vocabulary_extractor.is_poultry_related(query)
            
            if not is_poultry:
                processing_time = time.time() - start_time
                return IntentResult(
                    intent_type=IntentType.OUT_OF_DOMAIN,
                    confidence=1.0 - vocab_confidence,
                    detected_entities={},
                    expanded_query=query,
                    metadata={
                        "classification_method": "vocabulary_extractor",
                        "vocab_details": vocab_details,
                        "processing_time": processing_time
                    },
                    processing_time=processing_time,
                    confidence_breakdown={"vocab_confidence": vocab_confidence}
                )
            
            # 2. Extraction d'entités avec gestion d'erreurs
            entities = self.entity_extractor.extract_entities(query)
            
            # 3. Classification d'intention avec scoring détaillé
            intent_type, classification_breakdown = self.intent_classifier.classify_intent(query, entities)
            
            # 4. Expansion de la requête
            expanded_query = self.query_expander.expand_query(query)
            
            # 5. Calcul de la confiance finale avec facteurs multiples
            base_confidence = min(0.95, vocab_confidence + 0.2)  # Bonus pour cohérence
            
            # Ajustement selon la classification
            best_classification_score = max(
                breakdown.get("total_score", 0) 
                for breakdown in classification_breakdown.values()
            )
            classification_confidence = min(0.3, best_classification_score * 0.05)
            
            final_confidence = min(0.95, base_confidence + classification_confidence)
            
            processing_time = time.time() - start_time
            
            # Mise à jour des statistiques
            self._update_processing_stats(processing_time)
            
            result = IntentResult(
                intent_type=intent_type,
                confidence=final_confidence,
                detected_entities=entities,
                expanded_query=expanded_query,
                metadata={
                    "vocab_details": vocab_details,
                    "classification_breakdown": classification_breakdown,
                    "entities_extracted": len(entities),
                    "query_expanded": expanded_query != query,
                    "processing_time": processing_time,
                    "original_query_length": len(query),
                    "expansion_added": len(expanded_query) - len(query)
                },
                processing_time=processing_time,
                confidence_breakdown={
                    "vocab_confidence": vocab_confidence,
                    "classification_confidence": classification_confidence,
                    "final_confidence": final_confidence
                }
            )
            
            logger.debug(f"Requête traitée (optimisé): '{query}' -> {intent_type.value} (conf: {final_confidence:.3f})")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Erreur traitement requête: {e}")
            
            # Retour d'erreur gracieux
            return IntentResult(
                intent_type=IntentType.GENERAL_POULTRY,
                confidence=0.5,
                detected_entities={},
                expanded_query=query,
                metadata={
                    "error": str(e),
                    "processing_time": processing_time
                },
                processing_time=processing_time
            )
    
    def _update_processing_stats(self, processing_time: float):
        """Met à jour les statistiques de traitement"""
        total = self.processing_stats["total_queries"]
        current_avg = self.processing_stats["avg_processing_time"]
        
        # Moyenne mobile
        self.processing_stats["avg_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé selon le type d'intention - version améliorée"""
        intent_type = intent_result.intent_type
        entities = intent_result.detected_entities
        
        prompts = {
            IntentType.METRIC_QUERY: self._build_metric_prompt(entities),
            IntentType.ENVIRONMENT_SETTING: self._build_environment_prompt(entities),
            IntentType.DIAGNOSIS_TRIAGE: self._build_diagnosis_prompt(entities),
            IntentType.ECONOMICS_COST: self._build_economics_prompt(entities),
            IntentType.PROTOCOL_QUERY: self._build_protocol_prompt(entities)
        }
        
        base_prompt = prompts.get(intent_type)
        
        # Enrichir avec le contexte des entités détectées
        if base_prompt and entities:
            entity_context = self._build_entity_context(entities)
            if entity_context:
                base_prompt += f"\n\nContexte détecté: {entity_context}"
        
        return base_prompt
    
    def _build_entity_context(self, entities: Dict[str, str]) -> str:
        """Construit un contexte à partir des entités détectées"""
        context_parts = []
        
        if "line" in entities:
            context_parts.append(f"Lignée: {entities['line']}")
        if "age_days" in entities:
            context_parts.append(f"Âge: {entities['age_days']} jours")
        if "site_type" in entities:
            context_parts.append(f"Type d'élevage: {entities['site_type']}")
        if "weight_value" in entities:
            unit = entities.get("weight_unit", "g")
            context_parts.append(f"Poids: {entities['weight_value']}{unit}")
        if "temperature_value" in entities:
            context_parts.append(f"Température: {entities['temperature_value']}°C")
        
        return " | ".join(context_parts)
    
    def _build_metric_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour les questions de métriques - amélioré"""
        base_prompt = """Tu es un expert en performances avicoles. 
Fournis des données précises et des références aux standards de l'industrie.
Inclus les valeurs cibles, les plages normales et les facteurs d'influence."""
        
        if "metrics" in entities:
            metrics_list = entities["metrics"].split(",")
            base_prompt += f"\nMétriques spécifiques à traiter: {', '.join(metrics_list)}"
        
        return base_prompt
    
    def _build_environment_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour l'environnement d'élevage"""
        return """Tu es un expert en ambiance et climat d'élevage avicole.
Fournis des paramètres techniques précis, des courbes de température,
et des recommandations de réglage selon l'âge et la saison.
Inclus les plages optimales et les ajustements selon les conditions."""
    
    def _build_diagnosis_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour le diagnostic"""
        return """Tu es un vétérinaire spécialisé en aviculture.
Utilise une approche méthodique de diagnostic différentiel,
considère l'épidémiologie et propose des examens complémentaires.
Fournis des diagnostics différentiels et des plans d'action."""
    
    def _build_economics_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour l'économie"""
        return """Tu es un expert en économie de l'élevage avicole.
Fournis des analyses de coûts détaillées, des calculs de rentabilité
et des comparaisons avec les standards du marché.
Inclus les facteurs de variation et les optimisations possibles."""
    
    def _build_protocol_prompt(self, entities: Dict[str, str]) -> str:
        """Construit un prompt spécialisé pour les protocoles"""
        return """Tu es un expert en protocoles vétérinaires et biosécurité avicole.
Fournis des protocoles détaillés, des calendriers de vaccination
et des mesures de prévention spécifiques.
Inclus les adaptations selon l'âge et le type d'élevage."""
    
    def get_processing_stats(self) -> Dict:
        """Retourne les statistiques de traitement"""
        return {
            **self.processing_stats,
            "vocabulary_size": len(self.vocabulary_extractor.poultry_keywords),
            "alias_mappings_count": len(self.vocabulary_extractor.alias_mappings),
            "specialized_terms_count": len(self.vocabulary_extractor.specialized_terms)
        }

# Fonctions utilitaires pour l'intégration (préservées et améliorées)
def create_intent_processor(intents_file_path: str = None) -> IntentProcessor:
    """Factory pour créer un processeur d'intentions avec path par défaut"""
    if intents_file_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        intents_file_path = os.path.join(base_dir, "intents.json")
    
    return IntentProcessor(intents_file_path)

def process_query_with_intents(processor: IntentProcessor, query: str) -> IntentResult:
    """Interface simple pour traiter une requête"""
    return processor.process_query(query)