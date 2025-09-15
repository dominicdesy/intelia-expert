# -*- coding: utf-8 -*-
"""
intent_processor.py - Processeur d'intentions métier pour Intelia Expert - Version Intégrée
Améliorations: intégration Redis, seuils adaptatifs, fallback sémantique, normalisation clés
"""

import os
import json
import logging
import re
import time
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types d'intentions métier - Étendu"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    GENERAL_POULTRY = "general_poultry"
    OUT_OF_DOMAIN = "out_of_domain"

@dataclass
class IntentResult:
    """Résultat de classification d'intention - Version améliorée avec métriques intégration"""
    intent_type: IntentType
    confidence: float
    detected_entities: Dict[str, str]
    expanded_query: str
    metadata: Dict[str, Any]
    processing_time: float = 0.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    vocabulary_coverage: Dict[str, Any] = field(default_factory=dict)
    expansion_quality: Dict[str, Any] = field(default_factory=dict)
    cache_key_normalized: str = ""  # Nouveau: clé normalisée pour Redis
    semantic_fallback_candidates: List[str] = field(default_factory=list)  # Nouveau: fallback sémantique

class PoultryVocabularyExtractor:
    """Extracteur de vocabulaire spécialisé - Version avec seuils adaptatifs"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.poultry_keywords = self._build_vocabulary()
        self.alias_mappings = self._build_alias_mappings()
        self.specialized_terms = self._build_specialized_terms()
        self.metrics_vocabulary = self._build_metrics_vocabulary()
        self.topic_defaults = self._load_topic_defaults()
        
        # Nouveaux: patterns de haute confiance pour seuils adaptatifs
        self.high_confidence_patterns = self._build_high_confidence_patterns()
        self.genetic_terms = self._extract_genetic_vocabulary()
        
        # Statistiques de couverture
        self.coverage_stats = {
            "total_keywords": len(self.poultry_keywords),
            "alias_mappings": len(self.alias_mappings),
            "specialized_terms": len(self.specialized_terms),
            "metrics_covered": len(self.metrics_vocabulary),
            "topic_defaults": len(self.topic_defaults),
            "high_confidence_patterns": len(self.high_confidence_patterns),
            "genetic_terms": len(self.genetic_terms)
        }
        
        logger.info(f"Vocabulaire avicole étendu: {self.coverage_stats}")
    
    def _build_high_confidence_patterns(self) -> Dict[str, float]:
        """Patterns de haute confiance pour seuils adaptatifs OOD"""
        return {
            # Combinaisons genetics + metrics = très haute confiance
            "genetics_metrics": 0.95,
            "specific_line_age": 0.90,
            "technical_metrics": 0.85,
            "environment_technical": 0.80,
            "protocol_specific": 0.85
        }
    
    def _extract_genetic_vocabulary(self) -> Set[str]:
        """Extrait le vocabulaire génétique pour détection haute confiance"""
        genetic_terms = set()
        
        # Lignées depuis aliases
        for line_type, line_aliases in self.intents_config.get("aliases", {}).get("line", {}).items():
            genetic_terms.add(line_type.lower())
            genetic_terms.update([alias.lower() for alias in line_aliases])
        
        # Termes génétiques étendus
        genetic_terms.update([
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann', 'hyline', 'dekalb', 
            'bovans', 'shaver', 'novogen', 'hisex', 'nick', 'ranger', 'sasso',
            'parent', 'stock', 'breeding', 'strain', 'line', 'genetic'
        ])
        
        return genetic_terms
    
    def _build_vocabulary(self) -> Set[str]:
        """Construit le vocabulaire complet - Version avec normalisation clés"""
        keywords = set()
        
        aliases = self.intents_config.get("aliases", {})
        
        # Lignées de volailles (coverage complète du fichier intents.json)
        for line_type, line_aliases in aliases.get("line", {}).items():
            keywords.add(line_type.lower())
            keywords.update([alias.lower() for alias in line_aliases])
            # Ajout: variantes normalisées pour clés cache
            keywords.add(self._normalize_for_cache_key(line_type))
            for alias in line_aliases:
                keywords.add(self._normalize_for_cache_key(alias))
        
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
        
        # Sexes
        for sex, sex_aliases in aliases.get("sex", {}).items():
            keywords.add(sex.lower())
            keywords.update([alias.lower() for alias in sex_aliases])
        
        # Métriques techniques depuis tous les intents
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = intent_config.get("metrics", {})
            keywords.update([metric.lower().replace('_', ' ') for metric in metrics.keys()])
            keywords.update([metric.lower().replace('_', '') for metric in metrics.keys()])
        
        # Vocabulaire spécialisé étendu pour améliorer la couverture
        extended_poultry_terms = {
            # Termes de base
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            
            # Environnement et équipement
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'tunnel', 'natural', 'mechanical', 'pad', 'cooling', 'heating', 'inlet',
            'static', 'pressure', 'lux', 'lighting', 'hours', 'intensity',
            
            # Lignées et génétique (avec variantes normalisées)
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann', 'hyline', 'dekalb', 'bovans',
            'shaver', 'novogen', 'hisex', 'nick', 'ranger', 'sasso', 'freedom',
            'classic', 'flex', 'color', 'brown', 'white', 'parent', 'stock',
            # Variantes normalisées pour cache
            'ross308', 'ross 308', 'r308', 'cobb500', 'cobb 500', 'c500',
            
            # Stades et âges
            'poussin', 'chick', 'œuf', 'egg', 'day-old', 'starter', 'grower', 'finisher',
            'breeding', 'reproduction', 'ponte', 'laying', 'pullet', 'rearing',
            
            # Nutrition et performance
            'feed conversion', 'conversion', 'welfare', 'bien-être', 'animal',
            'density', 'densité', 'housing', 'logement', 'epef', 'uniformity',
            'daily', 'gain', 'intake', 'cumulative', 'stocking', 'feeder', 'nipple',
            
            # Composition nutritionnelle
            'protein', 'energy', 'lysine', 'methionine', 'calcium', 'phosphorus',
            'sodium', 'chloride', 'potassium', 'fiber', 'starch', 'fat', 'oil',
            'metabolizable', 'digestible', 'crude', 'available', 'kcal', 'meg',
            
            # Pathologie et santé
            'vaccine', 'virus', 'bacteria', 'parasite', 'antibiotic', 'treatment',
            'diagnosis', 'pathology', 'immune', 'immunity', 'stress', 'welfare',
            
            # Économie
            'cost', 'price', 'margin', 'profit', 'roi', 'budget', 'economics',
            'efficiency', 'optimization', 'investment', 'return'
        }
        keywords.update(extended_poultry_terms)
        
        logger.info(f"Vocabulaire avicole construit: {len(keywords)} termes")
        return keywords
    
    def _normalize_for_cache_key(self, term: str) -> str:
        """Normalise un terme pour les clés de cache Redis"""
        # Enlever espaces, tirets, points
        normalized = re.sub(r'[\s\-\.]+', '', term.lower())
        
        # Variantes fréquentes
        normalized = normalized.replace('r-', 'r').replace('c-', 'c')
        
        # Garde-fou: minimum 3 caractères pour éviter collisions
        if len(normalized) < 3:
            return term.lower()
        
        return normalized
    
    def _build_metrics_vocabulary(self) -> Dict[str, Dict[str, Any]]:
        """Construit un index des métriques avec métadonnées"""
        metrics_vocab = {}
        
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = intent_config.get("metrics", {})
            for metric_name, metric_config in metrics.items():
                
                # Variantes du nom de métrique
                variants = [
                    metric_name,
                    metric_name.replace('_', ' '),
                    metric_name.replace('_', ''),
                    metric_name.lower(),
                    metric_name.lower().replace('_', ' '),
                    metric_name.lower().replace('_', '')
                ]
                
                metric_info = {
                    "canonical_name": metric_name,
                    "intent": intent_name,
                    "unit": metric_config.get("unit", ""),
                    "requires": metric_config.get("requires", []),
                    "requires_one_of": metric_config.get("requires_one_of", []),
                    "variants": variants,
                    "is_technical": metric_name in ['fcr', 'epef', 'uniformity', 'mortality'],  # Nouveau
                    "confidence_boost": 1.5 if metric_name in ['fcr', 'epef'] else 1.0  # Nouveau
                }
                
                for variant in variants:
                    metrics_vocab[variant.lower()] = metric_info
        
        return metrics_vocab
    
    def _load_topic_defaults(self) -> Dict[str, str]:
        """Charge les defaults par topic pour améliorer la classification"""
        return self.intents_config.get("defaults_by_topic", {})
    
    def _build_alias_mappings(self) -> Dict[str, str]:
        """Construit les mappings alias -> terme canonique"""
        mappings = {}
        
        for category, items in self.intents_config.get("aliases", {}).items():
            for canonical, aliases in items.items():
                canonical_lower = canonical.lower()
                canonical_normalized = self._normalize_for_cache_key(canonical)
                
                mappings[canonical_lower] = canonical_lower
                mappings[canonical_normalized] = canonical_lower  # Nouveau: mapping normalisé
                
                for alias in aliases:
                    alias_lower = alias.lower()
                    alias_normalized = self._normalize_for_cache_key(alias)
                    
                    mappings[alias_lower] = canonical_lower
                    mappings[alias_normalized] = canonical_lower  # Nouveau
        
        return mappings
    
    def _build_specialized_terms(self) -> Dict[str, float]:
        """Construit un dictionnaire de termes spécialisés avec scores de spécificité améliorés"""
        specialized = {}
        
        # Termes très spécifiques (score élevé) - Étendu
        high_specificity = [
            'ross', 'cobb', 'hubbard', 'fcr', 'epef', 'biosécurité', 'couvoir',
            'isa', 'lohmann', 'hyline', 'dekalb', 'bovans', 'shaver', 'novogen',
            'tunnel', 'pad', 'cooling', 'static pressure', 'nipple', 'uniformity',
            'ross308', 'cobb500', 'r308', 'c500'  # Nouveaux: variantes normalisées
        ]
        for term in high_specificity:
            specialized[term] = 2.0
        
        # Termes modérément spécifiques - Étendu
        medium_specificity = [
            'poulet', 'chicken', 'aviculture', 'poultry', 'poussin', 'chick',
            'broiler', 'layer', 'breeding', 'vaccination', 'mortality', 'density',
            'starter', 'grower', 'finisher', 'temperature', 'ventilation', 'lighting'
        ]
        for term in medium_specificity:
            specialized[term] = 1.5
        
        # Termes généraux mais dans le domaine - Étendu
        low_specificity = [
            'élevage', 'production', 'croissance', 'growth', 'farming', 'feed',
            'water', 'weight', 'performance', 'management', 'health', 'nutrition'
        ]
        for term in low_specificity:
            specialized[term] = 1.0
        
        return specialized
    
    @lru_cache(maxsize=2000)
    def is_poultry_related(self, text: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Détermine si un texte est lié à l'aviculture - Version avec seuils adaptatifs"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        if not words:
            return False, 0.0, {"reason": "no_words_found"}
        
        # Analyse de couverture vocabulaire
        vocab_matches = []
        vocab_score = 0.0
        
        for word in words:
            if word in self.poultry_keywords:
                specificity = self.specialized_terms.get(word, 1.0)
                vocab_score += specificity
                vocab_matches.append({
                    "word": word,
                    "specificity": specificity,
                    "canonical": self.alias_mappings.get(word, word)
                })
        
        # Détection de métriques spécialisées avec boost
        metrics_detected = []
        metrics_score = 0.0
        technical_metrics_found = False
        
        for phrase in [text_lower] + [' '.join(words[i:i+3]) for i in range(len(words)-2)]:
            for metric_variant, metric_info in self.metrics_vocabulary.items():
                if metric_variant in phrase:
                    metrics_detected.append(metric_info["canonical_name"])
                    confidence_boost = metric_info.get("confidence_boost", 1.0)
                    metrics_score += 1.5 * confidence_boost
                    if metric_info.get("is_technical", False):
                        technical_metrics_found = True
        
        # Nouveau: Détection de patterns haute confiance
        high_confidence_detected = self._detect_high_confidence_patterns(text_lower, words)
        genetics_detected = any(term in text_lower for term in self.genetic_terms)
        
        # Score de couverture par domaine
        domain_coverage = self._analyze_domain_coverage(text_lower, words)
        
        # Normalisation et calcul final
        normalized_vocab_score = vocab_score / len(words) if words else 0.0
        normalized_metrics_score = min(1.0, metrics_score / 10.0)
        domain_bonus = sum(domain_coverage.values()) * 0.1
        
        # Nouveau: Bonus pour patterns haute confiance
        high_confidence_bonus = 0.0
        if high_confidence_detected:
            high_confidence_bonus = 0.3
        elif genetics_detected and technical_metrics_found:
            high_confidence_bonus = 0.25
        elif genetics_detected and len(metrics_detected) > 0:
            high_confidence_bonus = 0.2
        
        # Score final avec facteurs multiples
        final_score = min(1.0, normalized_vocab_score + normalized_metrics_score + 
                         domain_bonus + high_confidence_bonus)
        
        # Nouveau: Seuils adaptatifs basés sur la confiance
        base_threshold = self._get_adaptive_threshold(
            high_confidence_detected, genetics_detected, technical_metrics_found, len(metrics_detected)
        )
        
        is_poultry = final_score >= base_threshold
        
        # Métriques détaillées pour debug et monitoring
        coverage_details = {
            "vocab_matches": vocab_matches,
            "metrics_detected": list(set(metrics_detected)),
            "domain_coverage": domain_coverage,
            "high_confidence_patterns": high_confidence_detected,
            "genetics_detected": genetics_detected,
            "technical_metrics": technical_metrics_found,
            "scores": {
                "vocab_score": normalized_vocab_score,
                "metrics_score": normalized_metrics_score,
                "domain_bonus": domain_bonus,
                "high_confidence_bonus": high_confidence_bonus,
                "final_score": final_score
            },
            "threshold_used": base_threshold,
            "text_length": len(words),
            "coverage_ratio": len(vocab_matches) / len(words) if words else 0.0,
            "adaptive_factors": {
                "high_confidence": high_confidence_detected,
                "genetics_present": genetics_detected,
                "technical_metrics": technical_metrics_found,
                "metrics_count": len(metrics_detected)
            }
        }
        
        logger.debug(f"Classification vocabulaire: '{text[:50]}...' -> {is_poultry} "
                    f"(score: {final_score:.3f}, seuil: {base_threshold:.3f})")
        
        return is_poultry, final_score, coverage_details
    
    def _detect_high_confidence_patterns(self, text_lower: str, words: List[str]) -> bool:
        """Détecte des patterns de très haute confiance pour seuils adaptatifs"""
        # Pattern genetics + metrics
        has_genetics = any(term in text_lower for term in self.genetic_terms)
        has_metrics = any(variant in text_lower for variant in self.metrics_vocabulary.keys())
        
        if has_genetics and has_metrics:
            return True
        
        # Pattern lignée spécifique + âge
        line_patterns = ['ross 308', 'cobb 500', 'hubbard', 'isa brown']
        age_patterns = [r'\d+\s*(?:jour|day|semaine|week|j|d)']
        
        has_specific_line = any(pattern in text_lower for pattern in line_patterns)
        has_age = any(re.search(pattern, text_lower) for pattern in age_patterns)
        
        if has_specific_line and has_age:
            return True
        
        # Pattern technique spécialisé
        technical_patterns = ['fcr', 'epef', 'biosécurité', 'tunnel ventilation', 'static pressure']
        if any(pattern in text_lower for pattern in technical_patterns):
            return True
        
        return False
    
    def _get_adaptive_threshold(self, high_confidence: bool, genetics: bool, 
                               technical_metrics: bool, metrics_count: int) -> float:
        """Calcule un seuil adaptatif basé sur les indicateurs de confiance"""
        
        # Seuil très bas pour patterns haute confiance
        if high_confidence:
            return 0.05
        
        # Seuil bas pour genetics + metrics
        if genetics and technical_metrics:
            return 0.08
        
        # Seuil réduit pour genetics seul ou metrics multiples
        if genetics or metrics_count >= 2:
            return 0.10
        
        # Seuil normal pour vocabulaire générique
        return 0.12
    
    def _analyze_domain_coverage(self, text_lower: str, words: List[str]) -> Dict[str, float]:
        """Analyse la couverture par domaine spécialisé"""
        domains = {
            "genetics": ["ross", "cobb", "hubbard", "isa", "lohmann", "line", "strain"],
            "nutrition": ["feed", "protein", "energy", "lysine", "calcium", "fcr"],
            "environment": ["temperature", "ventilation", "humidity", "lighting", "tunnel"],
            "performance": ["weight", "gain", "mortality", "uniformity", "epef", "production"],
            "health": ["vaccination", "disease", "antibiotic", "biosecurity", "diagnosis"],
            "economics": ["cost", "price", "margin", "profit", "efficiency", "roi"]
        }
        
        coverage = {}
        for domain, keywords in domains.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            coverage[domain] = min(1.0, matches / len(keywords))
        
        return coverage
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de couverture - Nouveau pour health-check"""
        return {
            **self.coverage_stats,
            "cache_info": {
                "hits": self.is_poultry_related.cache_info().hits,
                "misses": self.is_poultry_related.cache_info().misses,
                "maxsize": self.is_poultry_related.cache_info().maxsize,
                "currsize": self.is_poultry_related.cache_info().currsize
            }
        }
    
    def generate_semantic_fallback_candidates(self, entities: Dict[str, str]) -> List[str]:
        """Génère des candidats de fallback sémantique pour le cache Redis"""
        candidates = []
        
        # Fallback 1: lignée + métrique (sans âge)
        if "line" in entities and "metrics" in entities:
            line_normalized = self._normalize_for_cache_key(entities["line"])
            metrics = entities["metrics"].split(",")[0]  # Première métrique
            candidates.append(f"{line_normalized}_{metrics}")
        
        # Fallback 2: lignée seule
        if "line" in entities:
            line_normalized = self._normalize_for_cache_key(entities["line"])
            candidates.append(f"{line_normalized}_general")
        
        # Fallback 3: métrique + type site
        if "metrics" in entities and "site_type" in entities:
            metrics = entities["metrics"].split(",")[0]
            candidates.append(f"{entities['site_type']}_{metrics}")
        
        return candidates[:3]  # Limite à 3 candidats

class QueryExpander:
    """Expanseur de requêtes avec synonymes du domaine - Version améliorée avec normalisation"""
    
    def __init__(self, vocabulary_extractor: PoultryVocabularyExtractor):
        self.vocab_extractor = vocabulary_extractor
        self.alias_mappings = vocabulary_extractor.alias_mappings
        self.metrics_vocabulary = vocabulary_extractor.metrics_vocabulary
        self.topic_defaults = vocabulary_extractor.topic_defaults
        self.expansion_cache = {}
        self.expansion_patterns = self._build_expansion_patterns()
    
    def _build_expansion_patterns(self) -> Dict[str, List[str]]:
        """Construit des patterns d'expansion contextuels"""
        return {
            "weight_terms": {
                "triggers": ["poids", "weight", "gramme", "kg"],
                "expansions": ["body weight", "gain", "croissance", "target", "average"]
            },
            "fcr_terms": {
                "triggers": ["fcr", "conversion", "indice"],
                "expansions": ["feed conversion ratio", "efficiency", "performance", "optimal"]
            },
            "environment_terms": {
                "triggers": ["température", "temperature", "ventilation"],
                "expansions": ["ambient", "target", "setting", "optimal", "climate"]
            },
            "production_terms": {
                "triggers": ["production", "ponte", "laying"],
                "expansions": ["egg production", "rate", "peak", "persistency"]
            },
            "health_terms": {
                "triggers": ["maladie", "disease", "symptom"],
                "expansions": ["diagnosis", "treatment", "prevention", "pathology"]
            }
        }
    
    @lru_cache(maxsize=1000)
    def expand_query(self, query: str, max_expansions: int = 7) -> str:
        """Enrichit une requête avec des synonymes et termes liés - Version améliorée avec normalisation"""
        query_lower = query.lower()
        expansion_terms = set()
        expansion_quality = {"method": [], "terms_added": 0, "coverage_improved": False}
        
        # 1. Expansion par alias (existant amélioré avec normalisation)
        for alias, canonical in self.alias_mappings.items():
            if alias in query_lower and alias != canonical:
                expansion_terms.add(canonical)
                expansion_quality["method"].append("alias_mapping")
                
                # Ajouter des alias du même groupe
                related_aliases = [k for k, v in self.alias_mappings.items() 
                                 if v == canonical and k != alias][:2]
                expansion_terms.update(related_aliases)
        
        # 2. Expansion par métriques détectées (nouveau)
        for metric_variant, metric_info in self.metrics_vocabulary.items():
            if metric_variant in query_lower:
                # Ajouter d'autres variantes de la même métrique
                expansion_terms.update(metric_info["variants"][:3])
                expansion_quality["method"].append("metrics_expansion")
        
        # 3. Expansion contextuelle par patterns (amélioré)
        for pattern_name, pattern_config in self.expansion_patterns.items():
            triggers = pattern_config["triggers"]
            if any(trigger in query_lower for trigger in triggers):
                expansions = pattern_config["expansions"][:3]  # Limité
                expansion_terms.update(expansions)
                expansion_quality["method"].append(f"pattern_{pattern_name}")
        
        # 4. Expansion par défauts de topic (nouveau)
        for topic, default_site in self.topic_defaults.items():
            if topic in query_lower and default_site not in query_lower:
                # Ajouter le contexte par défaut si manquant
                expansion_terms.add(default_site.replace('_', ' '))
                expansion_quality["method"].append("topic_default")
        
        # 5. Expansion nutritionnelle spécialisée (nouveau)
        nutrition_expansions = self._get_nutrition_expansions(query_lower)
        if nutrition_expansions:
            expansion_terms.update(nutrition_expansions[:2])
            expansion_quality["method"].append("nutrition_specialized")
        
        # 6. Nouveau: Expansion pour normalisation de clés cache
        cache_normalized_terms = self._get_cache_normalized_expansions(query_lower)
        if cache_normalized_terms:
            expansion_terms.update(cache_normalized_terms)
            expansion_quality["method"].append("cache_normalization")
        
        # Limiter et optimiser les expansions
        expansion_terms = list(expansion_terms)[:max_expansions]
        expansion_quality["terms_added"] = len(expansion_terms)
        expansion_quality["coverage_improved"] = len(expansion_terms) > 0
        
        if expansion_terms:
            expanded_query = query + " " + " ".join(expansion_terms)
            logger.debug(f"Requête expansée: '{query}' -> +{len(expansion_terms)} termes")
            return expanded_query
        
        return query
    
    def _get_cache_normalized_expansions(self, query_lower: str) -> List[str]:
        """Génère des expansions pour améliorer la normalisation des clés cache"""
        expansions = []
        
        # Variantes fréquentes des lignées pour améliorer hit-rate cache
        line_variants = {
            'ross 308': ['ross308', 'r308', 'r-308'],
            'cobb 500': ['cobb500', 'c500', 'c-500'],
            'hubbard flex': ['hubbardflex', 'hflex'],
            'isa brown': ['isabrown', 'isa']
        }
        
        for canonical, variants in line_variants.items():
            if canonical in query_lower:
                expansions.extend(variants[:2])  # Limite à 2 variantes
            elif any(variant in query_lower for variant in variants):
                expansions.append(canonical)
                expansions.extend([v for v in variants if v not in query_lower][:1])
        
        return expansions
    
    def _get_nutrition_expansions(self, query_lower: str) -> List[str]:
        """Expansions spécialisées pour la nutrition"""
        expansions = []
        
        if any(term in query_lower for term in ["protein", "protéine", "cp"]):
            expansions.extend(["crude protein", "digestible", "amino acid"])
        
        if any(term in query_lower for term in ["energy", "énergie", "me"]):
            expansions.extend(["metabolizable energy", "kcal", "meg"])
        
        if any(term in query_lower for term in ["calcium", "phosphorus"]):
            expansions.extend(["mineral", "bone", "shell quality"])
        
        return expansions
    
    def get_expansion_quality(self, original_query: str, expanded_query: str) -> Dict[str, Any]:
        """Évalue la qualité de l'expansion - Nouveau pour métriques"""
        return {
            "original_length": len(original_query.split()),
            "expanded_length": len(expanded_query.split()),
            "expansion_ratio": len(expanded_query) / len(original_query) if original_query else 1.0,
            "terms_added": len(expanded_query.split()) - len(original_query.split()),
            "cache_hit": expanded_query in self.expansion_cache,
            "normalization_applied": self._has_normalization_applied(original_query, expanded_query)
        }
    
    def _has_normalization_applied(self, original: str, expanded: str) -> bool:
        """Vérifie si une normalisation a été appliquée"""
        normalization_indicators = ['ross308', 'cobb500', 'r308', 'c500']
        return any(indicator in expanded.lower() for indicator in normalization_indicators)

class EntityExtractor:
    """Extracteur d'entités métier - Version robuste avec normalisation cache"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.universal_slots = intents_config.get("universal_slots", {})
        
        # Patterns regex optimisés et étendus
        self.age_pattern = re.compile(r'\b(\d+)\s*(jour|day|semaine|week|j|sem|d|days|weeks)\b', re.IGNORECASE)
        self.weight_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(g|gramme|kg|kilogramme|gram|grams)\b', re.IGNORECASE)
        self.percentage_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*%\b')
        self.temperature_pattern = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(?:°C|celsius|degré|degrees?)\b', re.IGNORECASE)
        self.flock_size_pattern = re.compile(r'\b(\d+(?:[\s,]\d{3})*)\s*(?:bird|birds|poulet|poulets|head)\b', re.IGNORECASE)
        
    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extrait les entités métier avec validation renforcée et normalisation"""
        entities = {}
        text_lower = text.lower()
        
        try:
            # Extractions existantes améliorées
            entities.update(self._extract_lines(text_lower))
            entities.update(self._extract_ages(text))
            entities.update(self._extract_site_types(text_lower))
            entities.update(self._extract_metrics(text_lower))
            entities.update(self._extract_phases(text_lower))
            entities.update(self._extract_numeric_values(text))
            
            # Nouvelles extractions
            entities.update(self._extract_bird_types(text_lower))
            entities.update(self._extract_sex(text_lower))
            entities.update(self._extract_flock_size(text))
            entities.update(self._extract_environment_type(text_lower))
            
            # Nouveau: Normalisation pour clés cache
            entities = self._normalize_entities_for_cache(entities)
            
            # Validation et nettoyage
            entities = self._validate_entities(entities)
            
        except Exception as e:
            logger.error(f"Erreur extraction entités: {e}")
        
        return entities
    
    def _normalize_entities_for_cache(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Normalise les entités pour améliorer les clés de cache"""
        if "line" in entities:
            line = entities["line"]
            # Normalisation des lignées courantes
            if "ross 308" in line.lower():
                entities["line_normalized"] = "ross308"
            elif "cobb 500" in line.lower():
                entities["line_normalized"] = "cobb500"
            elif "hubbard" in line.lower():
                entities["line_normalized"] = "hubbard"
            else:
                entities["line_normalized"] = re.sub(r'[\s\-\.]+', '', line.lower())
        
        return entities
    
    def _extract_bird_types(self, text: str) -> Dict[str, str]:
        """Extrait les types d'oiseaux"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("bird_type", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"bird_type": canonical}
        return {}
    
    def _extract_sex(self, text: str) -> Dict[str, str]:
        """Extrait le sexe des oiseaux"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("sex", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"sex": canonical}
        return {}
    
    def _extract_flock_size(self, text: str) -> Dict[str, str]:
        """Extrait la taille du troupeau"""
        matches = self.flock_size_pattern.findall(text)
        if matches:
            try:
                size_str = matches[0].replace(' ', '').replace(',', '')
                size = int(size_str)
                if 100 <= size <= 1000000:  # Validation réaliste
                    return {"flock_size": str(size)}
            except ValueError:
                pass
        return {}
    
    def _extract_environment_type(self, text: str) -> Dict[str, str]:
        """Extrait le type d'environnement d'élevage"""
        env_types = {
            "tunnel": ["tunnel", "tunnelisé"],
            "natural": ["natural", "naturel", "fenêtres"],
            "mechanical": ["mécanique", "mechanical", "extracteur"]
        }
        
        for env_type, keywords in env_types.items():
            if any(keyword in text for keyword in keywords):
                return {"environment": env_type}
        return {}
    
    def _validate_entities(self, entities: Dict[str, str]) -> Dict[str, str]:
        """Valide les entités extraites selon les universal_slots"""
        validated = {}
        
        for key, value in entities.items():
            slot_config = self.universal_slots.get(key)
            if not slot_config:
                validated[key] = value  # Garde les entités non définies
                continue
            
            # Validation par type
            if slot_config.get("type") == "int":
                try:
                    int_val = int(value)
                    min_val = slot_config.get("min", float('-inf'))
                    max_val = slot_config.get("max", float('inf'))
                    if min_val <= int_val <= max_val:
                        validated[key] = value
                except ValueError:
                    logger.warning(f"Valeur invalide pour {key}: {value}")
            
            # Validation par enum
            elif "enum" in slot_config:
                if value in slot_config["enum"]:
                    validated[key] = value
                else:
                    logger.warning(f"Valeur enum invalide pour {key}: {value}")
            
            else:
                validated[key] = value
        
        return validated
    
    def _extract_lines(self, text: str) -> Dict[str, str]:
        """Extrait les lignées avec correspondance floue améliorée et normalisation"""
        line_aliases = self.intents_config.get("aliases", {}).get("line", {})
        
        # Stratégie multi-niveaux pour améliorer la détection
        for canonical, aliases in line_aliases.items():
            canonical_lower = canonical.lower()
            
            # 1. Correspondance exacte
            if canonical_lower in text:
                return {"line": canonical}
            
            # 2. Correspondance par alias
            for alias in aliases:
                if alias.lower() in text:
                    return {"line": canonical}
            
            # 3. Nouveau: Correspondance par variantes normalisées
            canonical_normalized = re.sub(r'[\s\-\.]+', '', canonical_lower)
            if canonical_normalized in text.replace(' ', '').replace('-', ''):
                return {"line": canonical}
            
            # 4. Correspondance par mots-clés décomposés (ex: "ross" + "308")
            canonical_words = canonical_lower.split()
            if len(canonical_words) > 1:
                matches = sum(1 for word in canonical_words if word in text)
                if matches == len(canonical_words):
                    return {"line": canonical}
            
            # 5. Correspondance floue pour codes numériques
            numbers = re.findall(r'\d+', canonical)
            if numbers:
                for num in numbers:
                    if num in text:
                        # Vérifier le contexte pour éviter faux positifs
                        context = text[max(0, text.find(num)-15):text.find(num)+25]
                        brand_words = ['ross', 'cobb', 'hubbard', 'isa', 'lohmann']
                        if any(brand in context for brand in brand_words):
                            return {"line": canonical}
        
        return {}
    
    def _extract_ages(self, text: str) -> Dict[str, str]:
        """Extrait les informations d'âge avec validation étendue"""
        entities = {}
        
        matches = self.age_pattern.findall(text)
        for number_str, unit in matches:
            try:
                age_value = int(number_str)
                
                # Validation étendue selon le contexte
                unit_lower = unit.lower()
                
                if unit_lower in ['jour', 'day', 'j', 'd', 'days']:
                    if 0 <= age_value <= 600:  # Validation broilers + layers
                        entities["age_days"] = str(age_value)
                        entities["age_weeks"] = str(max(1, age_value // 7))
                elif unit_lower in ['semaine', 'week', 'sem', 'weeks']:
                    if 0 <= age_value <= 100:  # Validation étendue layers
                        entities["age_weeks"] = str(age_value)
                        entities["age_days"] = str(age_value * 7)
                
                break  # Premier âge trouvé
                
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
        """Extrait les métriques avec matching amélioré"""
        detected_metrics = []
        
        # Utiliser le vocabulaire de métriques construit
        vocab_extractor = getattr(self, '_vocab_extractor', None)
        if vocab_extractor and hasattr(vocab_extractor, 'metrics_vocabulary'):
            for metric_variant, metric_info in vocab_extractor.metrics_vocabulary.items():
                if metric_variant in text.lower():
                    detected_metrics.append(metric_info["canonical_name"])
        else:
            # Fallback vers l'ancienne méthode
            for intent_config in self.intents_config.get("intents", {}).values():
                metrics = intent_config.get("metrics", {})
                for metric_name in metrics.keys():
                    metric_lower = metric_name.lower()
                    
                    if metric_lower in text or metric_lower.replace('_', ' ') in text:
                        detected_metrics.append(metric_name)
        
        if detected_metrics:
            return {"metrics": ",".join(detected_metrics[:5])}  # Limite étendue
        return {}
    
    def _extract_phases(self, text: str) -> Dict[str, str]:
        """Extrait les phases d'élevage"""
        for canonical, aliases in self.intents_config.get("aliases", {}).get("phase", {}).items():
            if canonical.lower() in text or any(alias.lower() in text for alias in aliases):
                return {"phase": canonical}
        return {}
    
    def _extract_numeric_values(self, text: str) -> Dict[str, str]:
        """Extrait les valeurs numériques avec contexte étendu"""
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
    """Classificateur d'intentions - Version avec scoring optimisé et intégration guardrails"""
    
    def __init__(self, intents_config: dict):
        self.intents_config = intents_config
        self.intent_keywords = self._build_intent_keywords()
        self.intent_patterns = self._build_intent_patterns()
        self.intent_metrics = self._build_intent_metrics()
    
    def _build_intent_metrics(self) -> Dict[str, Set[str]]:
        """Construit l'association intentions -> métriques"""
        intent_metrics = {}
        
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = set(intent_config.get("metrics", {}).keys())
            intent_metrics[intent_name] = metrics
        
        return intent_metrics
    
    def _build_intent_keywords(self) -> Dict[str, Set[str]]:
        """Construit les mots-clés par intention - Version étendue"""
        keywords = {}
        
        # Mots-clés étendus pour metric_query
        keywords[IntentType.METRIC_QUERY.value] = {
            'poids', 'weight', 'fcr', 'conversion', 'consommation', 'eau', 'water',
            'performance', 'production', 'croissance', 'growth', 'optimal', 'target',
            'gramme', 'kg', 'litre', 'pourcentage', 'combien', 'how much', 'quelle',
            'indice', 'ratio', 'efficiency', 'rendement', 'objectif', 'standard',
            'uniformity', 'gain', 'intake', 'daily', 'weekly', 'cumulative',
            'epef', 'mortality', 'density', 'stocking', 'feeder', 'nipple'
        }
        
        # Environment_setting étendu
        keywords[IntentType.ENVIRONMENT_SETTING.value] = {
            'température', 'temperature', 'ventilation', 'climatisation', 'chauffage',
            'humidité', 'humidity', 'air', 'climat', 'ambiance', 'réglage', 'setting',
            'environnement', 'environment', 'conditions', 'atmosph', 'tunnel', 'pad',
            'cooling', 'heating', 'inlet', 'pressure', 'static', 'lighting', 'lux',
            'intensity', 'hours', 'photoperiod', 'dimming', 'co2', 'nh3', 'dust'
        }
        
        # Protocol_query étendu
        keywords[IntentType.PROTOCOL_QUERY.value] = {
            'vaccination', 'protocole', 'protocol', 'traitement', 'treatment',
            'biosécurité', 'biosecurity', 'prévention', 'prevention', 'vaccin',
            'programme', 'program', 'schedule', 'planning', 'sanitaire', 'vaccine',
            'antibiotic', 'medication', 'withdrawal', 'timing', 'injection'
        }
        
        # Diagnosis_triage étendu
        keywords[IntentType.DIAGNOSIS_TRIAGE.value] = {
            'maladie', 'disease', 'symptôme', 'symptom', 'diagnostic', 'diagnosis',
            'mortalité', 'mortality', 'problème', 'problem', 'signes', 'signs',
            'pathologie', 'infection', 'virus', 'bacteria', 'parasite', 'sick',
            'health', 'clinical', 'lesion', 'postmortem', 'necropsy', 'lab'
        }
        
        # Economics_cost étendu
        keywords[IntentType.ECONOMICS_COST.value] = {
            'coût', 'cost', 'prix', 'price', 'économique', 'economic', 'rentabilité',
            'profit', 'marge', 'margin', 'budget', 'finance', 'euros', 'dollars',
            'investment', 'investissement', 'return', 'roi', 'amortissement',
            'efficiency', 'optimization', 'feed cost', 'energy cost', 'labor'
        }
        
        return keywords
    
    def classify_intent(self, text: str, entities: Dict[str, str], 
                       explain_score: Optional[float] = None) -> Tuple[IntentType, Dict[str, float]]:
        """Classifie l'intention avec scoring multimodal amélioré et intégration explain_score"""
        text_lower = text.lower()
        scores = {}
        score_breakdown = {}
        
        for intent_type, keywords in self.intent_keywords.items():
            # Score basique par mots-clés
            keyword_score = sum(1 for keyword in keywords if keyword in text_lower)
            
            # Score par patterns regex
            pattern_score = 0
            if intent_type in self.intent_patterns:
                for pattern in self.intent_patterns[intent_type]:
                    if re.search(pattern, text_lower):
                        pattern_score += 2
            
            # Score par entités (existant amélioré)
            entity_score = 0
            if intent_type == IntentType.METRIC_QUERY.value:
                if "metrics" in entities:
                    entity_score += 5  # Bonus augmenté
                if any(key in entities for key in ["weight_value", "percentage_value", "temperature_value"]):
                    entity_score += 3
                if any(key in entities for key in ["age_days", "age_weeks", "line"]):
                    entity_score += 2
                # Nouveau: bonus pour lignée normalisée
                if "line_normalized" in entities:
                    entity_score += 1
            
            elif intent_type == IntentType.ENVIRONMENT_SETTING.value:
                if "temperature_value" in entities:
                    entity_score += 4
                if "site_type" in entities:
                    entity_score += 2
                if "environment" in entities:
                    entity_score += 3
            
            elif intent_type == IntentType.ECONOMICS_COST.value:
                if any(word in text_lower for word in ['coût', 'cost', 'prix', 'économ']):
                    entity_score += 3
                if "flock_size" in entities:
                    entity_score += 2
            
            # Nouveau: Score par métriques spécialisées
            metrics_score = 0
            if intent_type in self.intent_metrics:
                intent_specific_metrics = self.intent_metrics[intent_type]
                detected_metrics = entities.get("metrics", "").split(",")
                matching_metrics = [m for m in detected_metrics if m in intent_specific_metrics]
                metrics_score = len(matching_metrics) * 3
            
            # Nouveau: Bonus explain_score pour evidence_support (intégration guardrails)
            explain_bonus = 0
            if explain_score is not None and explain_score > 0.7:
                explain_bonus = 2  # Bonus si forte évidence retriever
            
            total_score = keyword_score + pattern_score + entity_score + metrics_score + explain_bonus
            scores[intent_type] = total_score
            
            score_breakdown[intent_type] = {
                "keyword_score": keyword_score,
                "pattern_score": pattern_score,
                "entity_score": entity_score,
                "metrics_score": metrics_score,
                "explain_bonus": explain_bonus,
                "total_score": total_score
            }
        
        # Retourner l'intention avec le meilleur score
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            return IntentType(best_intent), score_breakdown
        
        return IntentType.GENERAL_POULTRY, score_breakdown
    
    def _build_intent_patterns(self) -> Dict[str, List[str]]:
        """Construit des patterns regex étendus"""
        patterns = {}
        
        patterns[IntentType.METRIC_QUERY.value] = [
            r'\b(?:combien|how much|quelle?\s+(?:est|is))\b',
            r'\b(?:poids|weight|fcr)\s+(?:de|of|à|at)\b',
            r'\b\d+\s*(?:g|kg|%|litres?|days?|jours?|weeks?|semaines?)\b',
            r'\b(?:optimal|target|objectif|cible)\b'
        ]
        
        patterns[IntentType.ENVIRONMENT_SETTING.value] = [
            r'\b(?:température|temperature|ventilation)\s+(?:optimale?|optimal|recommended)\b',
            r'\b(?:comment|how)\s+(?:régler|set|ajuster|adjust)\b',
            r'\b(?:ambiance|climate|setting)\b'
        ]
        
        patterns[IntentType.DIAGNOSIS_TRIAGE.value] = [
            r'\b(?:mes|my)\s+(?:poulets?|chickens?)\s+(?:sont|are)\b',
            r'\b(?:symptômes?|symptoms?|signes?|signs?)\s+(?:de|of)\b',
            r'\b(?:diagnostic|diagnosis|problème|problem)\b'
        ]
        
        return patterns

class IntentProcessor:
    """Processeur principal - Version avec intégration Redis et seuils adaptatifs"""
    
    def __init__(self, intents_file_path: str):
        self.intents_config = self._load_intents_config(intents_file_path)
        self.vocabulary_extractor = PoultryVocabularyExtractor(self.intents_config)
        self.query_expander = QueryExpander(self.vocabulary_extractor)
        self.entity_extractor = EntityExtractor(self.intents_config)
        self.intent_classifier = IntentClassifier(self.intents_config)
        
        # Injection de vocab_extractor dans entity_extractor pour métriques
        self.entity_extractor._vocab_extractor = self.vocabulary_extractor
        
        # Statistiques étendues pour monitoring
        self.processing_stats = {
            "total_queries": 0,
            "avg_processing_time": 0.0,
            "cache_hits": 0,
            "domain_coverage_avg": 0.0,
            "expansion_success_rate": 0.0,
            "entity_extraction_avg": 0.0,
            "intent_confidence_avg": 0.0,
            "errors_count": 0,
            "adaptive_threshold_usage": {"high_confidence": 0, "normal": 0, "strict": 0},
            "semantic_fallback_attempts": 0,
            "guardrails_evidence_boost": 0,
            "last_reset": time.time()
        }
        
        logger.info(f"IntentProcessor Enhanced initialisé - Couverture: {self.get_coverage_summary()}")
    
    def _load_intents_config(self, file_path: str) -> dict:
        """Charge la configuration avec résolution automatique du chemin"""
        try:
            # Résolution automatique du chemin relatif (fix pour Docker)
            if not os.path.isabs(file_path):
                base_dir = Path(__file__).parent.resolve()
                file_path = base_dir / file_path
            
            if not Path(file_path).exists():
                logger.error(f"Fichier intents.json introuvable: {file_path}")
                return self._get_fallback_config()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validation étendue
            validation_result = self._validate_config(config)
            if not validation_result["valid"]:
                logger.warning(f"Configuration invalide: {validation_result['errors']}")
            
            logger.info(f"Configuration chargée: {file_path} (v{config.get('version', 'unknown')})")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans intents.json: {e}")
            return self._get_fallback_config()
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return self._get_fallback_config()
    
    def _validate_config(self, config: dict) -> Dict[str, Any]:
        """Valide la structure de configuration"""
        errors = []
        required_keys = ["aliases", "intents", "universal_slots"]
        
        for key in required_keys:
            if key not in config:
                errors.append(f"Clé manquante: {key}")
        
        # Validation des aliases
        if "aliases" in config:
            alias_categories = ["line", "site_type", "bird_type", "phase"]
            for category in alias_categories:
                if category not in config["aliases"]:
                    errors.append(f"Catégorie alias manquante: {category}")
        
        # Validation des intents
        if "intents" in config:
            for intent_name, intent_config in config["intents"].items():
                if "metrics" not in intent_config:
                    errors.append(f"Métriques manquantes pour intent: {intent_name}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
    
    def _get_fallback_config(self) -> dict:
        """Configuration de fallback minimale"""
        return {
            "version": "fallback",
            "aliases": {
                "line": {"ross 308": ["ross", "r308", "ross308"]},
                "site_type": {"broiler_farm": ["broiler"]},
                "bird_type": {"broiler": ["chicken"]},
                "phase": {"starter": ["start"]}
            },
            "intents": {
                "metric_query": {"metrics": {"body_weight": {"unit": "g"}}}
            },
            "universal_slots": {},
            "defaults_by_topic": {}
        }
    
    def process_query(self, query: str, explain_score: Optional[float] = None) -> IntentResult:
        """Traite une requête avec métriques complètes et intégration explain_score"""
        start_time = time.time()
        self.processing_stats["total_queries"] += 1
        
        try:
            # 1. Classification domaine avec seuils adaptatifs
            is_poultry, vocab_confidence, vocab_details = self.vocabulary_extractor.is_poultry_related(query)
            
            # Mise à jour stats seuils adaptatifs
            adaptive_factors = vocab_details.get("adaptive_factors", {})
            if adaptive_factors.get("high_confidence", False):
                self.processing_stats["adaptive_threshold_usage"]["high_confidence"] += 1
            elif vocab_details.get("threshold_used", 0.12) < 0.12:
                self.processing_stats["adaptive_threshold_usage"]["strict"] += 1
            else:
                self.processing_stats["adaptive_threshold_usage"]["normal"] += 1
            
            if not is_poultry:
                processing_time = time.time() - start_time
                self._update_processing_stats(processing_time, vocab_confidence, 0, 0, vocab_confidence)
                
                return IntentResult(
                    intent_type=IntentType.OUT_OF_DOMAIN,
                    confidence=1.0 - vocab_confidence,
                    detected_entities={},
                    expanded_query=query,
                    metadata={
                        "classification_method": "vocabulary_extractor",
                        "vocab_details": vocab_details,
                        "processing_time": processing_time,
                        "fallback_reason": "low_domain_coverage",
                        "adaptive_threshold": vocab_details.get("threshold_used", 0.12)
                    },
                    processing_time=processing_time,
                    confidence_breakdown={"vocab_confidence": vocab_confidence},
                    vocabulary_coverage=vocab_details,
                    expansion_quality={}
                )
            
            # 2. Extraction d'entités avec normalisation
            entities = self.entity_extractor.extract_entities(query)
            
            # 3. Expansion de requête avec métriques qualité
            expanded_query = self.query_expander.expand_query(query)
            expansion_quality = self.query_expander.get_expansion_quality(query, expanded_query)
            
            # 4. Classification d'intention avec explain_score
            intent_type, classification_breakdown = self.intent_classifier.classify_intent(
                query, entities, explain_score
            )
            
            # Mise à jour stats guardrails
            if explain_score is not None and explain_score > 0.7:
                self.processing_stats["guardrails_evidence_boost"] += 1
            
            # 5. Génération clé cache normalisée et fallback sémantique
            cache_key_normalized = self._generate_cache_key(entities)
            semantic_fallback_candidates = self.vocabulary_extractor.generate_semantic_fallback_candidates(entities)
            
            if semantic_fallback_candidates:
                self.processing_stats["semantic_fallback_attempts"] += 1
            
            # 6. Calcul de confiance finale optimisé
            confidence_components = self._calculate_confidence(
                vocab_confidence, entities, classification_breakdown, expansion_quality, explain_score
            )
            
            processing_time = time.time() - start_time
            
            # 7. Mise à jour statistiques avec nouvelles métriques
            self._update_processing_stats(
                processing_time, 
                vocab_confidence, 
                len(entities), 
                expansion_quality["expansion_ratio"], 
                confidence_components["final_confidence"]
            )
            
            # 8. Construction du résultat avec métriques complètes
            result = IntentResult(
                intent_type=intent_type,
                confidence=confidence_components["final_confidence"],
                detected_entities=entities,
                expanded_query=expanded_query,
                metadata={
                    "vocab_details": vocab_details,
                    "classification_breakdown": classification_breakdown,
                    "confidence_components": confidence_components,
                    "entities_count": len(entities),
                    "expansion_applied": expanded_query != query,
                    "processing_time": processing_time,
                    "config_version": self.intents_config.get("version", "unknown"),
                    "adaptive_threshold": vocab_details.get("threshold_used", 0.12),
                    "explain_score_used": explain_score,
                    "guardrails_boost": explain_score is not None and explain_score > 0.7
                },
                processing_time=processing_time,
                confidence_breakdown=confidence_components,
                vocabulary_coverage=vocab_details.get("domain_coverage", {}),
                expansion_quality=expansion_quality,
                cache_key_normalized=cache_key_normalized,
                semantic_fallback_candidates=semantic_fallback_candidates
            )
            
            logger.debug(f"Requête traitée: '{query[:50]}...' -> {intent_type.value} "
                        f"(conf: {confidence_components['final_confidence']:.3f}, "
                        f"cache_key: {cache_key_normalized})")
            return result
            
        except Exception as e:
            self.processing_stats["errors_count"] += 1
            processing_time = time.time() - start_time
            logger.error(f"Erreur traitement requête: {e}")
            
            return IntentResult(
                intent_type=IntentType.GENERAL_POULTRY,
                confidence=0.5,
                detected_entities={},
                expanded_query=query,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time
                },
                processing_time=processing_time
            )
    
    def _generate_cache_key(self, entities: Dict[str, str]) -> str:
        """Génère une clé de cache normalisée pour Redis"""
        key_parts = []
        
        # Priorité: lignée normalisée > métriques > âge > site
        if "line_normalized" in entities:
            key_parts.append(entities["line_normalized"])
        elif "line" in entities:
            normalized_line = self.vocabulary_extractor._normalize_for_cache_key(entities["line"])
            key_parts.append(normalized_line)
        
        if "metrics" in entities:
            # Prendre la première métrique principale
            first_metric = entities["metrics"].split(",")[0]
            key_parts.append(first_metric.lower().replace("_", ""))
        
        if "age_days" in entities:
            # Arrondir à la semaine pour améliorer hit-rate
            age_days = int(entities["age_days"])
            age_weeks = max(1, age_days // 7)
            key_parts.append(f"w{age_weeks}")
        
        if "site_type" in entities:
            key_parts.append(entities["site_type"])
        
        cache_key = "_".join(key_parts) if key_parts else "general"
        
        # Garde-fou: longueur maximum
        if len(cache_key) > 100:
            cache_key = cache_key[:100]
        
        return cache_key
    
    def _calculate_confidence(self, vocab_conf: float, entities: Dict, 
                            classification: Dict, expansion: Dict, 
                            explain_score: Optional[float] = None) -> Dict[str, float]:
        """Calcule la confiance finale avec facteurs multiples et explain_score"""
        
        # Confiance vocabulaire pondérée
        vocab_weight = min(0.95, vocab_conf + 0.15)
        
        # Confiance entités avec bonus normalisation
        entity_bonus = min(0.2, len(entities) * 0.05)
        if "line_normalized" in entities:
            entity_bonus += 0.03  # Bonus pour normalisation cache
        
        # Confiance classification
        best_score = max(
            breakdown.get("total_score", 0) 
            for breakdown in classification.values()
        )
        classification_conf = min(0.25, best_score * 0.03)
        
        # Confiance expansion avec bonus normalisation
        expansion_bonus = min(0.1, expansion.get("expansion_ratio", 1.0) * 0.05)
        if expansion.get("normalization_applied", False):
            expansion_bonus += 0.02
        
        # Nouveau: Bonus explain_score (intégration guardrails)
        explain_bonus = 0.0
        if explain_score is not None:
            if explain_score > 0.8:
                explain_bonus = 0.15  # Fort bonus si très haute évidence
            elif explain_score > 0.6:
                explain_bonus = 0.08  # Bonus modéré
        
        final_confidence = min(0.98, vocab_weight + entity_bonus + classification_conf + 
                              expansion_bonus + explain_bonus)
        
        return {
            "vocab_confidence": vocab_weight,
            "entity_bonus": entity_bonus, 
            "classification_confidence": classification_conf,
            "expansion_bonus": expansion_bonus,
            "explain_bonus": explain_bonus,
            "final_confidence": final_confidence
        }
    
    def _update_processing_stats(self, processing_time: float, domain_coverage: float, 
                                entities_count: int, expansion_ratio: float, confidence: float):
        """Met à jour les statistiques de traitement étendues"""
        total = self.processing_stats["total_queries"]
        
        # Moyennes mobiles
        self.processing_stats["avg_processing_time"] = (
            (self.processing_stats["avg_processing_time"] * (total - 1) + processing_time) / total
        )
        
        self.processing_stats["domain_coverage_avg"] = (
            (self.processing_stats["domain_coverage_avg"] * (total - 1) + domain_coverage) / total
        )
        
        self.processing_stats["expansion_success_rate"] = (
            (self.processing_stats["expansion_success_rate"] * (total - 1) + (1 if expansion_ratio > 1.0 else 0)) / total
        )
        
        self.processing_stats["entity_extraction_avg"] = (
            (self.processing_stats["entity_extraction_avg"] * (total - 1) + entities_count) / total
        )
        
        self.processing_stats["intent_confidence_avg"] = (
            (self.processing_stats["intent_confidence_avg"] * (total - 1) + confidence) / total
        )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes - API pour health-check"""
        base_stats = {
            **self.processing_stats,
            "uptime_seconds": time.time() - self.processing_stats["last_reset"],
            "error_rate": self.processing_stats["errors_count"] / max(1, self.processing_stats["total_queries"]),
        }
        
        # Statistiques vocabulaire
        vocab_stats = self.vocabulary_extractor.get_coverage_stats()
        
        # Statistiques configuration
        config_stats = {
            "config_version": self.intents_config.get("version", "unknown"),
            "intents_count": len(self.intents_config.get("intents", {})),
            "total_metrics": sum(
                len(intent.get("metrics", {})) 
                for intent in self.intents_config.get("intents", {}).values()
            ),
            "alias_categories": len(self.intents_config.get("aliases", {}))
        }
        
        return {
            "processing": base_stats,
            "vocabulary": vocab_stats,
            "configuration": config_stats,
            "health_status": self._get_health_status(base_stats, vocab_stats)
        }
    
    def _get_health_status(self, processing_stats: Dict, vocab_stats: Dict) -> Dict[str, Any]:
        """Évalue l'état de santé du système"""
        issues = []
        
        # Vérifications santé
        if processing_stats["error_rate"] > 0.05:
            issues.append(f"Taux d'erreur élevé: {processing_stats['error_rate']:.1%}")
        
        if processing_stats["avg_processing_time"] > 2.0:
            issues.append(f"Temps de traitement élevé: {processing_stats['avg_processing_time']:.2f}s")
        
        if vocab_stats["total_keywords"] < 100:
            issues.append(f"Vocabulaire limité: {vocab_stats['total_keywords']} termes")
        
        if processing_stats["domain_coverage_avg"] < 0.3:
            issues.append(f"Couverture domaine faible: {processing_stats['domain_coverage_avg']:.1%}")
        
        # Status global
        if not issues:
            status = "healthy"
        elif len(issues) <= 2:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "issues": issues,
            "last_check": time.time(),
            "adaptive_thresholds": processing_stats["adaptive_threshold_usage"],
            "fallback_usage": processing_stats["semantic_fallback_attempts"],
            "guardrails_integration": processing_stats["guardrails_evidence_boost"]
        }
    
    def get_coverage_summary(self) -> Dict[str, int]:
        """Retourne un résumé de la couverture - Utile pour logs de démarrage"""
        return {
            "keywords": len(self.vocabulary_extractor.poultry_keywords),
            "aliases": len(self.vocabulary_extractor.alias_mappings),
            "metrics": len(self.vocabulary_extractor.metrics_vocabulary),
            "intents": len(self.intents_config.get("intents", {})),
            "entities": len(self.intents_config.get("universal_slots", {})),
            "genetic_terms": len(self.vocabulary_extractor.genetic_terms),
            "high_confidence_patterns": len(self.vocabulary_extractor.high_confidence_patterns)
        }
    
    def get_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé - Version améliorée avec intégration cache/guardrails"""
        intent_type = intent_result.intent_type
        entities = intent_result.detected_entities
        
        prompts = {
            IntentType.METRIC_QUERY: self._build_metric_prompt(entities, intent_result),
            IntentType.ENVIRONMENT_SETTING: self._build_environment_prompt(entities, intent_result),
            IntentType.DIAGNOSIS_TRIAGE: self._build_diagnosis_prompt(entities, intent_result),
            IntentType.ECONOMICS_COST: self._build_economics_prompt(entities, intent_result),
            IntentType.PROTOCOL_QUERY: self._build_protocol_prompt(entities, intent_result)
        }
        
        base_prompt = prompts.get(intent_type)
        
        # Enrichissement contextuel avec entités et métriques
        if base_prompt and entities:
            entity_context = self._build_entity_context(entities)
            expansion_context = self._build_expansion_context(intent_result.expansion_quality)
            cache_context = self._build_cache_context(intent_result)
            
            if entity_context:
                base_prompt += f"\n\nContexte détecté: {entity_context}"
            if expansion_context:
                base_prompt += f"\nExpansion appliquée: {expansion_context}"
            if cache_context:
                base_prompt += f"\nCache: {cache_context}"
        
        return base_prompt
    
    def _build_cache_context(self, intent_result: IntentResult) -> str:
        """Construit le contexte cache pour le prompt"""
        context_parts = []
        
        if intent_result.cache_key_normalized:
            context_parts.append(f"clé={intent_result.cache_key_normalized}")
        
        if intent_result.semantic_fallback_candidates:
            fallback_count = len(intent_result.semantic_fallback_candidates)
            context_parts.append(f"fallback={fallback_count}")
        
        explain_score = intent_result.metadata.get("explain_score_used")
        if explain_score is not None:
            context_parts.append(f"evidence={explain_score:.2f}")
        
        return " | ".join(context_parts)
    
    def _build_entity_context(self, entities: Dict[str, str]) -> str:
        """Construit un contexte enrichi à partir des entités"""
        context_parts = []
        
        if "line" in entities:
            context_parts.append(f"Lignée: {entities['line']}")
        if "line_normalized" in entities:
            context_parts.append(f"(norm: {entities['line_normalized']})")
        if "age_days" in entities:
            context_parts.append(f"Âge: {entities['age_days']} jours")
        if "site_type" in entities:
            context_parts.append(f"Type d'élevage: {entities['site_type']}")
        if "bird_type" in entities:
            context_parts.append(f"Type d'oiseau: {entities['bird_type']}")
        if "weight_value" in entities:
            unit = entities.get("weight_unit", "g")
            context_parts.append(f"Poids: {entities['weight_value']}{unit}")
        if "temperature_value" in entities:
            context_parts.append(f"Température: {entities['temperature_value']}°C")
        if "flock_size" in entities:
            context_parts.append(f"Taille troupeau: {entities['flock_size']}")
        if "environment" in entities:
            context_parts.append(f"Environnement: {entities['environment']}")
        
        return " | ".join(context_parts)
    
    def _build_expansion_context(self, expansion_quality: Dict[str, Any]) -> str:
        """Construit le contexte d'expansion pour le prompt"""
        if expansion_quality.get("terms_added", 0) > 0:
            ratio = expansion_quality.get("expansion_ratio", 1.0)
            normalization = " (norm)" if expansion_quality.get("normalization_applied", False) else ""
            return f"{expansion_quality['terms_added']} termes ajoutés (ratio: {ratio:.1f}){normalization}"
        return ""
    
    # Méthodes de construction de prompts (existantes, conservées avec améliorations)
    def _build_metric_prompt(self, entities: Dict[str, str], intent_result: IntentResult) -> str:
        """Prompt spécialisé pour les métriques avec contexte cache"""
        base_prompt = """Tu es un expert en performances avicoles. 
Fournis des données précises avec références aux standards de l'industrie.
Inclus les valeurs cibles, les plages normales et les facteurs d'influence."""
        
        if "metrics" in entities:
            metrics_list = entities["metrics"].split(",")
            base_prompt += f"\nMétriques spécifiques à traiter: {', '.join(metrics_list)}"
        
        # Ajout contexte haute confiance si détecté
        adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
        if adaptive_factors.get("high_confidence", False):
            base_prompt += "\nContexte haute confiance détecté - données techniques précises attendues."
        
        return base_prompt
    
    def _build_environment_prompt(self, entities: Dict[str, str], intent_result: IntentResult) -> str:
        """Prompt pour l'environnement d'élevage"""
        return """Tu es un expert en ambiance et climat d'élevage avicole.
Fournis des paramètres techniques précis, des courbes de température,
et des recommandations de réglage selon l'âge et la saison.
Inclus les plages optimales et les ajustements selon les conditions."""
    
    def _build_diagnosis_prompt(self, entities: Dict[str, str], intent_result: IntentResult) -> str:
        """Prompt pour le diagnostic"""
        return """Tu es un vétérinaire spécialisé en aviculture.
Utilise une approche méthodique de diagnostic différentiel,
considère l'épidémiologie et propose des examens complémentaires.
Fournis des diagnostics différentiels et des plans d'action."""
    
    def _build_economics_prompt(self, entities: Dict[str, str], intent_result: IntentResult) -> str:
        """Prompt pour l'économie"""
        return """Tu es un expert en économie de l'élevage avicole.
Fournis des analyses de coûts détaillées, des calculs de rentabilité
et des comparaisons avec les standards du marché.
Inclus les facteurs de variation et les optimisations possibles."""
    
    def _build_protocol_prompt(self, entities: Dict[str, str], intent_result: IntentResult) -> str:
        """Prompt pour les protocoles"""
        return """Tu es un expert en protocoles vétérinaires et biosécurité avicole.
Fournis des protocoles détaillés, des calendriers de vaccination
et des mesures de prévention spécifiques.
Inclus les adaptations selon l'âge et le type d'élevage."""

# Fonctions utilitaires pour l'intégration - Version intégrée Redis/Guardrails

def create_intent_processor(intents_file_path: Optional[str] = None) -> IntentProcessor:
    """
    Factory pour créer un processeur d'intentions avec résolution automatique du chemin.
    
    Args:
        intents_file_path: Chemin vers intents.json (optionnel, résolution auto si None)
    
    Returns:
        IntentProcessor: Instance configurée et prête à l'emploi
        
    Note:
        La factory résout automatiquement le chemin relatif pour éviter les problèmes
        de déploiement Docker (WORKDIR). Si intents.json n'est pas trouvé,
        une configuration de fallback est utilisée.
    """
    if intents_file_path is None:
        # Résolution automatique du chemin - Compatible Docker
        base_dir = Path(__file__).parent.resolve()
        intents_file_path = base_dir / "intents.json"
        
        logger.info(f"Résolution automatique du chemin: {intents_file_path}")
    
    processor = IntentProcessor(str(intents_file_path))
    
    # Log de vérification pour le déploiement
    stats = processor.get_processing_stats()
    logger.info(f"IntentProcessor créé - Santé: {stats['health_status']['status']}")
    
    return processor

def process_query_with_intents(processor: IntentProcessor, query: str, 
                              explain_score: Optional[float] = None) -> IntentResult:
    """
    Interface simple pour traiter une requête avec gestion d'erreurs robuste et intégration explain_score.
    
    Args:
        processor: Instance du processeur d'intentions
        query: Requête utilisateur à traiter
        explain_score: Score d'évidence du retriever pour guardrails (optionnel)
        
    Returns:
        IntentResult: Résultat du traitement avec métriques complètes
    """
    try:
        return processor.process_query(query, explain_score)
    except Exception as e:
        logger.error(f"Erreur critique dans process_query_with_intents: {e}")
        
        # Fallback gracieux
        return IntentResult(
            intent_type=IntentType.GENERAL_POULTRY,
            confidence=0.3,
            detected_entities={},
            expanded_query=query,
            metadata={
                "error": "critical_processing_error",
                "error_details": str(e),
                "fallback_applied": True
            },
            processing_time=0.0
        )

def get_intent_processor_health(processor: IntentProcessor) -> Dict[str, Any]:
    """
    Retourne l'état de santé du processeur pour monitoring/health-check avec métriques étendues.
    
    Args:
        processor: Instance du processeur d'intentions
        
    Returns:
        Dict: Métriques de santé complètes pour exposition dans get_status()
        
    Usage:
        # Dans votre moteur principal:
        health_data = get_intent_processor_health(intent_processor)
        # Exposer dans l'endpoint /status ou équivalent
    """
    try:
        stats = processor.get_processing_stats()
        coverage = processor.get_coverage_summary()
        
        return {
            "intent_processor": {
                "status": stats["health_status"]["status"],
                "uptime_seconds": stats["processing"]["uptime_seconds"],
                "total_queries": stats["processing"]["total_queries"],
                "error_rate": stats["processing"]["error_rate"],
                "avg_response_time": stats["processing"]["avg_processing_time"],
                "vocabulary_loaded": stats["vocabulary"]["total_keywords"] > 0,
                "config_version": stats["configuration"]["config_version"],
                "coverage_summary": coverage,
                "cache_performance": stats["vocabulary"]["cache_info"],
                "adaptive_thresholds": stats["health_status"]["adaptive_thresholds"],
                "semantic_fallback": stats["health_status"]["fallback_usage"],
                "guardrails_integration": stats["health_status"]["guardrails_integration"],
                "last_health_check": time.time()
            }
        }
    except Exception as e:
        logger.error(f"Erreur health check intent processor: {e}")
        return {
            "intent_processor": {
                "status": "error",
                "error": str(e),
                "last_health_check": time.time()
            }
        }

def get_cache_key_from_intent(intent_result: IntentResult) -> str:
    """
    Extrait la clé de cache normalisée d'un résultat d'intention pour Redis.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        str: Clé de cache normalisée pour Redis
        
    Usage:
        # Dans redis_cache_manager.py ou rag_engine.py:
        cache_key = get_cache_key_from_intent(intent_result)
        # Utiliser pour lookup Redis avec fallback sémantique
    """
    return intent_result.cache_key_normalized or "general"

def get_semantic_fallback_keys(intent_result: IntentResult) -> List[str]:
    """
    Extrait les clés de fallback sémantique pour cache Redis en mode STRICT.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        List[str]: Liste des clés de fallback sémantique
        
    Usage:
        # Dans redis_cache_manager.py pour mode STRICT:
        fallback_keys = get_semantic_fallback_keys(intent_result)
        for key in fallback_keys:
            if cache_hit := await redis.get(key):
                return cache_hit  # avec TTL plus court
    """
    return intent_result.semantic_fallback_candidates

def should_use_strict_threshold(intent_result: IntentResult) -> bool:
    """
    Détermine si un seuil strict doit être appliqué pour le filtre OOD.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        bool: True si seuil strict recommandé, False sinon
        
    Usage:
        # Dans rag_engine.py pour filtrage OOD adaptatif:
        if should_use_strict_threshold(intent_result):
            ood_threshold = 0.85  # Seuil plus strict
        else:
            ood_threshold = 0.70  # Seuil normal
    """
    adaptive_factors = intent_result.vocabulary_coverage.get("adaptive_factors", {})
    
    # Seuil strict si pas de patterns haute confiance
    if not adaptive_factors.get("high_confidence", False):
        if not adaptive_factors.get("genetics_present", False):
            if len(intent_result.detected_entities) <= 1:
                return True
    
    return False

def get_guardrails_context(intent_result: IntentResult) -> Dict[str, Any]:
    """
    Génère le contexte pour les guardrails basé sur l'analyse d'intention.
    
    Args:
        intent_result: Résultat du traitement d'intention
        
    Returns:
        Dict: Contexte enrichi pour guardrails
        
    Usage:
        # Dans rag_engine.py pour guardrails:
        guardrails_context = get_guardrails_context(intent_result)
        # Passer à evaluate_guardrails() pour améliorer evidence_support
    """
    return {
        "intent_confidence": intent_result.confidence,
        "intent_type": intent_result.intent_type.value,
        "entities_detected": len(intent_result.detected_entities),
        "technical_context": intent_result.vocabulary_coverage.get("adaptive_factors", {}),
        "domain_coverage": intent_result.vocabulary_coverage.get("domain_coverage", {}),
        "explain_score_used": intent_result.metadata.get("explain_score_used"),
        "high_confidence_indicators": {
            "genetics_present": intent_result.vocabulary_coverage.get("adaptive_factors", {}).get("genetics_present", False),
            "technical_metrics": intent_result.vocabulary_coverage.get("adaptive_factors", {}).get("technical_metrics", False),
            "specific_entities": "line" in intent_result.detected_entities and "metrics" in intent_result.detected_entities
        }
    }

# Fonctions de test et debug

def test_query_processing(processor: IntentProcessor, test_queries: List[str]) -> Dict[str, Any]:
    """
    Teste le processeur sur une liste de requêtes pour validation avec métriques intégration.
    
    Args:
        processor: Instance du processeur
        test_queries: Liste de requêtes de test
        
    Returns:
        Dict: Résultats des tests avec métriques
    """
    results = []
    
    for i, query in enumerate(test_queries):
        start_time = time.time()
        # Test avec explain_score simulé
        explain_score = 0.8 if i % 2 == 0 else None
        result = processor.process_query(query, explain_score)
        
        results.append({
            "query": query,
            "intent": result.intent_type.value,
            "confidence": result.confidence,
            "entities_count": len(result.detected_entities),
            "expanded": result.expanded_query != query,
            "cache_key": result.cache_key_normalized,
            "fallback_candidates": len(result.semantic_fallback_candidates),
            "explain_score": explain_score,
            "processing_time": time.time() - start_time
        })
    
    # Statistiques globales
    avg_confidence = sum(r["confidence"] for r in results) / len(results)
    avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
    expansion_rate = sum(1 for r in results if r["expanded"]) / len(results)
    cache_key_diversity = len(set(r["cache_key"] for r in results)) / len(results)
    
    return {
        "results": results,
        "summary": {
            "total_queries": len(test_queries),
            "avg_confidence": avg_confidence,
            "avg_processing_time": avg_processing_time,
            "expansion_rate": expansion_rate,
            "cache_key_diversity": cache_key_diversity,
            "intent_distribution": {
                intent: sum(1 for r in results if r["intent"] == intent)
                for intent in set(r["intent"] for r in results)
            },
            "integration_metrics": {
                "fallback_candidates_avg": sum(r["fallback_candidates"] for r in results) / len(results),
                "explain_score_usage": sum(1 for r in results if r["explain_score"] is not None) / len(results)
            }
        }
    }

# Exemples de requêtes de test pour validation avec variantes normalisées
SAMPLE_TEST_QUERIES = [
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "Température de démarrage pour poussins en tunnel",
    "Programme de vaccination pour reproducteur",
    "Mes poulets ont des signes respiratoires",
    "Coût alimentaire par kg de poids vif produit",
    "Consommation d'eau à 28 jours",
    "Densité optimale en élevage au sol",
    "Protocole biosécurité couvoir",
    "Performance EPEF Ross 308 standard",
    # Nouveaux: tests normalisation
    "Ross-308 35j FCR",
    "C-500 poids 42 jours",
    "Hubbard Flex vaccination",
    "ISA Brown ponte pic"
]

if __name__ == "__main__":
    # Test de base si le module est exécuté directement
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Validation config
        validation = validate_intents_config("intents.json")
        print(f"Validation config: {'✓ Valide' if validation['valid'] else '✗ Erreurs'}")
        
        if validation["errors"]:
            print(f"Erreurs: {validation['errors']}")
        if validation["warnings"]:
            print(f"Avertissements: {validation['warnings']}")
        
        # Test processeur
        processor = create_intent_processor()
        health = get_intent_processor_health(processor)
        print(f"Santé processeur: {health['intent_processor']['status']}")
        
        # Test sur requêtes échantillon avec intégration
        test_results = test_query_processing(processor, SAMPLE_TEST_QUERIES[:5])
        print(f"Tests: {test_results['summary']['avg_confidence']:.2f} confiance moyenne")
        print(f"Cache diversity: {test_results['summary']['cache_key_diversity']:.2f}")
        print(f"Fallback candidates: {test_results['summary']['integration_metrics']['fallback_candidates_avg']:.1f}")
        
    except Exception as e:
        print(f"Erreur test: {e}")