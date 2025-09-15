# -*- coding: utf-8 -*-
"""
query_expander.py - Expanseur de requêtes avec synonymes du domaine
"""

import logging
from typing import Dict, List, Any, Tuple
from functools import lru_cache
import re

logger = logging.getLogger(__name__)

# NOTE: garde en sync avec IntentProcessor/Cache
LINE_ALIASES = {
    "ross308": ["ross 308", "r308", "ross-308"],
    "cobb500": ["cobb 500", "c500", "cobb-500"],
}

def _normalize_line(text: str) -> str:
    t = re.sub(r"\s+", "", text.lower())
    for norm, variants in LINE_ALIASES.items():
        if t == norm or any(re.sub(r"\s+|-", "", v.lower()) == t for v in variants):
            return norm
    return t

def _normalize_metric(metric: str) -> str:
    m = metric.strip().lower()
    return {"indice conversion":"fcr", "ic":"fcr", "poids":"weight"}.get(m, m)

def _normalize_age(age: str) -> str:
    a = age.lower().replace("jours","j").replace("jour","j").replace("days","j").replace("d","j")
    a = re.sub(r"[^0-9j]", "", a)
    return a

class QueryExpander:
    """Expanseur de requêtes avec synonymes du domaine - Version améliorée avec normalisation"""
    
    def __init__(self, vocabulary_extractor):
        self.vocab_extractor = vocabulary_extractor
        self.alias_mappings = vocabulary_extractor.alias_mappings
        self.metrics_vocabulary = vocabulary_extractor.metrics_vocabulary
        self.topic_defaults = vocabulary_extractor.topic_defaults
        self.expansion_cache = {}
        self.expansion_patterns = self._build_expansion_patterns()
    
    def _build_expansion_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Retourne un mapping structuré {category: {trigger_terms: [...], expansions: [...]}}
        """
        return {
            "weight": {
                "triggers": ["poids", "weight", "g", "kg"],
                "expansions": ["poids moyen", "poids cible", "croissance", "gain moyen quotidien"]
            },
            "fcr": {
                "triggers": ["fcr", "indice conversion", "ic"],
                "expansions": ["conversion alimentaire", "feed conversion ratio"]
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

def get_cache_normalized_expansions(query: str) -> Dict[str, Any]:
    """
    Produit des expansions + une clé cache normalisée cohérente avec EntityExtractor/IntentProcessor.
    """
    q = query.strip()
    patterns = _build_expansion_patterns()
    q_low = q.lower()
    expansions: List[str] = []
    categories_hit: List[str] = []

    for cat, obj in patterns.items():
        if any(t in q_low for t in obj["triggers"]):
            categories_hit.append(cat)
            expansions.extend(obj["expansions"])

    # heuristique simple pour extraire (line/metric/age)
    line = None
    if "ross" in q_low or "r308" in q_low:
        line = _normalize_line("ross308")
    elif "cobb" in q_low or "c500" in q_low:
        line = _normalize_line("cobb500")

    metric = None
    if any(t in q_low for t in ["fcr", "indice conversion", "ic"]):
        metric = _normalize_metric("fcr")
    elif any(t in q_low for t in ["poids", "weight"]):
        metric = _normalize_metric("weight")

    # âge (ex: 35j / 35 jours)
    m = re.search(r"(\d{1,3})\s*(j|jours|jour|d|days?)", q_low)
    age = _normalize_age(m.group(1) + "j") if m else ""

    cache_key = ":".join([p for p in [line or "", metric or "", age or ""] if p]) or q_low

    return {
        "expansions": sorted(set(expansions)),
        "categories": categories_hit,
        "cache_key_normalized": cache_key,
    }

def _build_expansion_patterns() -> Dict[str, Dict[str, List[str]]]:
    """
    Retourne un mapping structuré {category: {trigger_terms: [...], expansions: [...]}}
    """
    return {
        "weight": {
            "triggers": ["poids", "weight", "g", "kg"],
            "expansions": ["poids moyen", "poids cible", "croissance", "gain moyen quotidien"]
        },
        "fcr": {
            "triggers": ["fcr", "indice conversion", "ic"],
            "expansions": ["conversion alimentaire", "feed conversion ratio"]
        },
        "environment": {
            "triggers": ["température", "temperature", "ventilation"],
            "expansions": ["ambient", "target", "setting", "optimal", "climate"]
        },
        "production": {
            "triggers": ["production", "ponte", "laying"],
            "expansions": ["egg production", "rate", "peak", "persistency"]
        },
        "health": {
            "triggers": ["maladie", "disease", "symptom"],
            "expansions": ["diagnosis", "treatment", "prevention", "pathology"]
        }
    }