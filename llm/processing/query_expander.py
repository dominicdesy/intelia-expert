# -*- coding: utf-8 -*-
"""
query_expander.py - Expanseur de requêtes avec synonymes du domaine
CORRIGÉ: Imports modulaires + logique sexe/as-hatched pour recherche élargie
"""

import logging
from utils.types import Dict, List, Any
from functools import lru_cache
import re

logger = logging.getLogger(__name__)

# Définition locale des aliases de lignées (remplace l'import inexistant)
LINE_ALIASES = {
    "ross308": ["ross 308", "r308", "ross-308"],
    "cobb500": ["cobb 500", "c500", "cobb-500"],
    "hubbard": ["hubbard classic", "classic"],
}


def _normalize_line(text: str) -> str:
    t = re.sub(r"\s+", "", text.lower())
    for norm, variants in LINE_ALIASES.items():
        if t == norm or any(re.sub(r"\s+|-", "", v.lower()) == t for v in variants):
            return norm
    return t


def _normalize_metric(metric: str) -> str:
    m = metric.strip().lower()
    return {"indice conversion": "fcr", "ic": "fcr", "poids": "weight"}.get(m, m)


def _normalize_age(age: str) -> str:
    a = (
        age.lower()
        .replace("jours", "j")
        .replace("jour", "j")
        .replace("days", "j")
        .replace("d", "j")
    )
    a = re.sub(r"[^0-9j]", "", a)
    return a


class QueryExpander:
    """Expanseur de requêtes avec synonymes du domaine - Version améliorée avec normalisation et logique sexe/as-hatched"""

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
                "expansions": [
                    "poids moyen",
                    "poids cible",
                    "croissance",
                    "gain moyen quotidien",
                ],
            },
            "fcr": {
                "triggers": ["fcr", "indice conversion", "ic"],
                "expansions": ["conversion alimentaire", "feed conversion ratio"],
            },
            "environment_terms": {
                "triggers": ["température", "temperature", "ventilation"],
                "expansions": ["ambient", "target", "setting", "optimal", "climate"],
            },
            "production_terms": {
                "triggers": ["production", "ponte", "laying"],
                "expansions": ["egg production", "rate", "peak", "persistency"],
            },
            "health_terms": {
                "triggers": ["maladie", "disease", "symptom"],
                "expansions": ["diagnosis", "treatment", "prevention", "pathology"],
            },
            # NOUVEAU: Patterns pour expansion sexe/as-hatched
            "sex_terms": {
                "triggers": ["male", "mâle", "female", "femelle", "coq", "poule"],
                "expansions": ["as-hatched", "mixed", "both sexes", "sexes mélangés"],
            },
        }

    @lru_cache(maxsize=1000)
    def expand_query(self, query: str, max_expansions: int = 7) -> str:
        """Enrichit une requête avec des synonymes et termes liés - Version améliorée avec normalisation et logique sexe"""
        query_lower = query.lower()
        expansion_terms = set()
        expansion_quality = {"method": [], "terms_added": 0, "coverage_improved": False}

        # 1. Expansion par alias (existant amélioré avec normalisation)
        for alias, canonical in self.alias_mappings.items():
            if alias in query_lower and alias != canonical:
                expansion_terms.add(canonical)
                expansion_quality["method"].append("alias_mapping")

                # Ajouter des alias du même groupe
                related_aliases = [
                    k
                    for k, v in self.alias_mappings.items()
                    if v == canonical and k != alias
                ][:2]
                expansion_terms.update(related_aliases)

        # 2. NOUVEAU: Expansion sexe/as-hatched intelligente
        sex_expansions = self._get_sex_expansions(query_lower)
        if sex_expansions:
            expansion_terms.update(sex_expansions)
            expansion_quality["method"].append("sex_fallback_expansion")

        # 3. Expansion par métriques détectées (existant)
        for metric_variant, metric_info in self.metrics_vocabulary.items():
            if metric_variant in query_lower:
                # Ajouter d'autres variantes de la même métrique
                expansion_terms.update(metric_info["variants"][:3])
                expansion_quality["method"].append("metrics_expansion")

        # 4. Expansion contextuelle par patterns (amélioré)
        for pattern_name, pattern_config in self.expansion_patterns.items():
            triggers = pattern_config["triggers"]
            if any(trigger in query_lower for trigger in triggers):
                expansions = pattern_config["expansions"][:3]  # Limité
                expansion_terms.update(expansions)
                expansion_quality["method"].append(f"pattern_{pattern_name}")

        # 5. Expansion par défauts de topic (existant)
        for topic, default_site in self.topic_defaults.items():
            if topic in query_lower and default_site not in query_lower:
                # Ajouter le contexte par défaut si manquant
                expansion_terms.add(default_site.replace("_", " "))
                expansion_quality["method"].append("topic_default")

        # 6. Expansion nutritionnelle spécialisée (existant)
        nutrition_expansions = self._get_nutrition_expansions(query_lower)
        if nutrition_expansions:
            expansion_terms.update(nutrition_expansions[:2])
            expansion_quality["method"].append("nutrition_specialized")

        # 7. Expansion pour normalisation de clés cache (existant)
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
            logger.debug(
                f"Requête expansée: '{query}' -> +{len(expansion_terms)} termes"
            )
            return expanded_query

        return query

    def _get_sex_expansions(self, query_lower: str) -> List[str]:
        """
        NOUVELLE MÉTHODE: Gère l'expansion sexe/as-hatched

        Logique:
        1. Si sexe spécifique détecté -> ajouter aussi "as-hatched" pour élargir les résultats
        2. Si aucun sexe détecté -> ajouter termes as-hatched par défaut
        3. Si as-hatched déjà présent -> ajouter variantes
        """
        expansions = []

        # Patterns de détection sexe
        male_patterns = ["male", "mâle", "mâles", "masculin", "coq", "coqs", "rooster"]
        female_patterns = [
            "female",
            "femelle",
            "femelles",
            "féminin",
            "poule",
            "poules",
            "hen",
        ]
        as_hatched_patterns = [
            "as-hatched",
            "ashatched",
            "mixed",
            "mixte",
            "mélangé",
            "non sexé",
        ]

        # Détection de ce qui est présent dans la requête
        has_male = any(pattern in query_lower for pattern in male_patterns)
        has_female = any(pattern in query_lower for pattern in female_patterns)
        has_as_hatched = any(pattern in query_lower for pattern in as_hatched_patterns)

        if has_male:
            # Si male spécifié, ajouter aussi as-hatched pour élargir
            expansions.extend(["as-hatched", "mixed", "both sexes"])
            logger.debug("Sexe male détecté, ajout termes as-hatched pour élargir")

        elif has_female:
            # Si female spécifié, ajouter aussi as-hatched pour élargir
            expansions.extend(["as-hatched", "mixed", "both sexes"])
            logger.debug("Sexe female détecté, ajout termes as-hatched pour élargir")

        elif has_as_hatched:
            # Si as-hatched déjà présent, ajouter variantes
            expansions.extend(
                ["mixed sex", "sexes mélangés", "straight run", "non sexé"]
            )
            logger.debug("As-hatched détecté, ajout variantes")

        else:
            # AMÉLIORATION: Aucun sexe détecté -> expansion neutre
            expansions.extend(["weight", "performance", "growth"])
            logger.debug("Aucun sexe détecté, expansion termes génériques")

        return expansions[:3]  # Limiter à 3 termes

    def build_sex_aware_query_variants(self, entities: Dict[str, str]) -> List[str]:
        """
        NOUVELLE MÉTHODE: Construit des variantes de requête selon la logique sexe

        Args:
            entities: Entités extraites par EntityExtractor (incluant sex et sex_specified)

        Returns:
            Liste de variantes de requête pour couvrir les cas sexe/as-hatched
        """
        sex = entities.get("sex", "as_hatched")
        sex_specified = entities.get("sex_specified", "false") == "true"

        query_variants = []

        if sex_specified and sex in ["male", "female"]:
            # Sexe spécifique demandé
            query_variants.append(f"sex:{sex}")
            # Ajouter aussi as-hatched comme fallback
            query_variants.append("sex:as_hatched")
            query_variants.append("sex:mixed")

        else:
            # Pas de sexe spécifique ou as-hatched demandé
            query_variants.append("sex:as_hatched")
            query_variants.append("sex:mixed")
            # Ajouter aussi les sexes spécifiques comme options
            query_variants.append("sex:male")
            query_variants.append("sex:female")

        logger.debug(f"Variantes de requête sexe générées: {query_variants}")
        return query_variants

    def _get_cache_normalized_expansions(self, query_lower: str) -> List[str]:
        """Génère des expansions pour améliorer la normalisation des clés cache"""
        expansions = []

        # Variantes fréquentes des lignées pour améliorer hit-rate cache
        line_variants = {
            "ross 308": ["ross308", "r308", "r-308"],
            "cobb 500": ["cobb500", "c500", "c-500"],
            "hubbard flex": ["hubbardflex", "hflex"],
            "isa brown": ["isabrown", "isa"],
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

    def get_expansion_quality(
        self, original_query: str, expanded_query: str
    ) -> Dict[str, Any]:
        """Évalue la qualité de l'expansion - Nouveau pour métriques"""
        return {
            "original_length": len(original_query.split()),
            "expanded_length": len(expanded_query.split()),
            "expansion_ratio": (
                len(expanded_query) / len(original_query) if original_query else 1.0
            ),
            "terms_added": len(expanded_query.split()) - len(original_query.split()),
            "cache_hit": expanded_query in self.expansion_cache,
            "normalization_applied": self._has_normalization_applied(
                original_query, expanded_query
            ),
            "sex_expansion_applied": self._has_sex_expansion_applied(expanded_query),
        }

    def _has_normalization_applied(self, original: str, expanded: str) -> bool:
        """Vérifie si une normalisation a été appliquée"""
        normalization_indicators = ["ross308", "cobb500", "r308", "c500"]
        return any(
            indicator in expanded.lower() for indicator in normalization_indicators
        )

    def _has_sex_expansion_applied(self, expanded_query: str) -> bool:
        """NOUVEAU: Vérifie si l'expansion sexe/as-hatched a été appliquée"""
        sex_expansion_indicators = ["as-hatched", "mixed", "both sexes", "straight run"]
        return any(
            indicator in expanded_query.lower()
            for indicator in sex_expansion_indicators
        )


def get_cache_normalized_expansions(query: str) -> Dict[str, Any]:
    """
    Produit des expansions + une clé cache normalisée cohérente avec EntityExtractor/IntentProcessor.
    MODIFIÉ: Inclut maintenant la logique sexe/as-hatched
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

    # Détection sexe pour normalisation cache
    sex_detected = None
    if any(term in q_low for term in ["male", "mâle", "coq"]):
        sex_detected = "male"
    elif any(term in q_low for term in ["female", "femelle", "poule"]):
        sex_detected = "female"
    elif any(term in q_low for term in ["as-hatched", "mixed", "mixte"]):
        sex_detected = "as_hatched"
    else:
        sex_detected = None

    # Heuristique simple pour extraire (line/metric/age)
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

    # Âge (ex: 35j / 35 jours)
    m = re.search(r"(\d{1,3})\s*(j|jours|jour|d|days?)", q_low)
    age = _normalize_age(m.group(1) + "j") if m else ""

    # Inclure sexe seulement s'il est explicitement détecté
    sex_part = sex_detected if sex_detected else ""
    cache_key = (
        ":".join([p for p in [line or "", metric or "", age or "", sex_part] if p])
        or q_low
    )

    return {
        "expansions": sorted(set(expansions)),
        "categories": categories_hit,
        "cache_key_normalized": cache_key,
        "sex_detected": sex_detected,  # NOUVEAU
        "sex_fallback_applied": sex_detected == "as_hatched",  # NOUVEAU
    }


def _build_expansion_patterns() -> Dict[str, Dict[str, List[str]]]:
    """
    Retourne un mapping structuré {category: {trigger_terms: [...], expansions: [...]}}
    MODIFIÉ: Inclut maintenant les patterns sexe
    """
    return {
        "weight": {
            "triggers": ["poids", "weight", "g", "kg"],
            "expansions": [
                "poids moyen",
                "poids cible",
                "croissance",
                "gain moyen quotidien",
            ],
        },
        "fcr": {
            "triggers": ["fcr", "indice conversion", "ic"],
            "expansions": ["conversion alimentaire", "feed conversion ratio"],
        },
        "environment": {
            "triggers": ["température", "temperature", "ventilation"],
            "expansions": ["ambient", "target", "setting", "optimal", "climate"],
        },
        "production": {
            "triggers": ["production", "ponte", "laying"],
            "expansions": ["egg production", "rate", "peak", "persistency"],
        },
        "health": {
            "triggers": ["maladie", "disease", "symptom"],
            "expansions": ["diagnosis", "treatment", "prevention", "pathology"],
        },
        # NOUVEAU: Patterns pour sexe/as-hatched
        "sex": {
            "triggers": [
                "male",
                "mâle",
                "female",
                "femelle",
                "coq",
                "poule",
                "as-hatched",
                "mixed",
            ],
            "expansions": [
                "as-hatched",
                "mixed sex",
                "both sexes",
                "straight run",
                "sexes mélangés",
            ],
        },
    }
