# -*- coding: utf-8 -*-
"""
config.py - Configuration and patterns for guardrails system
"""

from utils.types import Dict, List
from .models import VerificationLevel

# Patterns suspects multilingues (potentielles hallucinations)
HALLUCINATION_PATTERNS = [
    # Français
    r"selon moi|à mon avis|je pense que|il me semble|personnellement",
    r"généralement|habituellement|en général|typiquement|souvent",
    r"il est recommandé|il faut|vous devriez|on conseille|il vaut mieux",
    r"dans la plupart des cas|parfois|quelquefois|peut-être",
    r"environ|approximativement|autour de|près de|à peu près",
    r"probablement|vraisemblablement|sans doute|apparemment",
    # Anglais
    r"i think|i believe|in my opinion|personally|it seems to me",
    r"usually|typically|generally|commonly|often",
    r"it is recommended|you should|one should|it's better to",
    r"in most cases|sometimes|probably|likely|apparently",
    r"approximately|around|about|roughly|nearly",
    # Expressions vagues
    r"comme vous le savez|comme on dit|il paraît que",
    r"on dit que|d'après ce qu'on sait|il semblerait",
]

# Indicateurs de support documentaire renforcés
EVIDENCE_INDICATORS = [
    # Références explicites
    r"selon le document|d'après les données|les résultats montrent",
    r"d'après l'étude|selon l'analyse|les mesures indiquent",
    r"tableau \d+|figure \d+|source\s*:|référence\s*:",
    r"page \d+|section \d+|annexe \d+",
    # Termes scientifiques
    r"étude de|essai|test|mesure|observation|expérience",
    r"recherche|analyse|évaluation|examen|investigation",
    r"protocole|méthodologie|procédure|standard",
    # Données quantitatives avec contexte
    r"les données montrent|les chiffres révèlent|l'analyse démontre",
    r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|semaine|°C|kcal)\s+(?:mesurés?|observés?|enregistrés?)",
]

# Vocabulaire métier aviculture enrichi et organisé
DOMAIN_KEYWORDS = {
    "performance": [
        "fcr",
        "ic",
        "indice",
        "conversion",
        "poids",
        "gain",
        "croissance",
        "rendement",
        "efficacité",
        "productivité",
        "performance",
        "résultats",
        "vitesse",
        "développement",
        "évolution",
        "progression",
    ],
    "sante": [
        "mortalité",
        "morbidité",
        "maladie",
        "pathologie",
        "infection",
        "vaccination",
        "vaccin",
        "prophylaxie",
        "traitement",
        "santé",
        "viabilité",
        "résistance",
        "immunité",
        "symptômes",
        "diagnostic",
    ],
    "nutrition": [
        "aliment",
        "alimentation",
        "nutrition",
        "nutritionnel",
        "protéine",
        "énergie",
        "calories",
        "digestibilité",
        "nutriment",
        "vitamines",
        "minéraux",
        "calcium",
        "phosphore",
        "acides",
        "aminés",
        "fibres",
    ],
    "reproduction": [
        "ponte",
        "œuf",
        "œufs",
        "fertility",
        "fertilité",
        "éclosabilité",
        "couvaison",
        "incubation",
        "éclosion",
        "reproduction",
        "couvoir",
        "hatchabilité",
        "embryon",
        "poussin",
        "poussins",
    ],
    "technique": [
        "ventilation",
        "température",
        "densité",
        "éclairage",
        "logement",
        "bâtiment",
        "poulailler",
        "équipement",
        "installation",
        "système",
        "automatisation",
        "contrôle",
        "régulation",
        "ambiance",
    ],
    "genetique": [
        "lignée",
        "souche",
        "race",
        "ross",
        "cobb",
        "hubbard",
        "isa",
        "lohmann",
        "hy-line",
        "hybride",
        "sélection",
        "amélioration",
        "génétique",
        "héritabilité",
        "consanguinité",
    ],
}

# Seuils de validation adaptatifs par niveau
VALIDATION_THRESHOLDS: Dict[VerificationLevel, Dict[str, float]] = {
    VerificationLevel.MINIMAL: {
        "evidence_min": 0.2,
        "hallucination_max": 0.8,
        "consistency_min": 0.1,
        "max_violations": 1,
        "max_warnings": 5,
    },
    VerificationLevel.STANDARD: {
        "evidence_min": 0.4,
        "hallucination_max": 0.7,
        "consistency_min": 0.3,
        "max_violations": 0,
        "max_warnings": 3,
    },
    VerificationLevel.STRICT: {
        "evidence_min": 0.6,
        "hallucination_max": 0.5,
        "consistency_min": 0.5,
        "max_violations": 0,
        "max_warnings": 2,
    },
    VerificationLevel.CRITICAL: {
        "evidence_min": 0.8,
        "hallucination_max": 0.3,
        "consistency_min": 0.7,
        "max_violations": 0,
        "max_warnings": 1,
    },
}


def get_patterns() -> Dict[str, List[str]]:
    """Get all patterns configuration"""
    return {
        "hallucination": HALLUCINATION_PATTERNS,
        "evidence": EVIDENCE_INDICATORS,
    }


def get_domain_keywords() -> Dict[str, List[str]]:
    """Get domain-specific keywords"""
    return DOMAIN_KEYWORDS


def get_thresholds(level: VerificationLevel) -> Dict[str, float]:
    """Get validation thresholds for a specific level"""
    return VALIDATION_THRESHOLDS.get(
        level, VALIDATION_THRESHOLDS[VerificationLevel.STANDARD]
    )


__all__ = [
    "HALLUCINATION_PATTERNS",
    "EVIDENCE_INDICATORS",
    "DOMAIN_KEYWORDS",
    "VALIDATION_THRESHOLDS",
    "get_patterns",
    "get_domain_keywords",
    "get_thresholds",
]
