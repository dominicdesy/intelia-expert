# -*- coding: utf-8 -*-
"""
config.py - Configuration constants for OOD detection

This module contains all configuration constants used by the OOD detector,
including adaptive thresholds, language adjustments, fallback terms, and
pattern matching rules.
"""

import json
import os
from pathlib import Path
from utils.types import Dict, List

# ===== ADAPTIVE THRESHOLDS =====

ADAPTIVE_THRESHOLDS: Dict[str, float] = {
    "technical_query": 0.10,  # Lower threshold for technical queries with metrics
    "numeric_query": 0.15,  # Slightly higher for queries with numeric data
    "standard_query": 0.20,  # Standard threshold for typical queries
    "generic_query": 0.30,  # Higher threshold for generic queries
    "suspicious_query": 0.50,  # Very high threshold for suspicious content
}
"""
Adaptive thresholds for different query types.

These thresholds determine the minimum score required for a query to be
considered in-domain based on the query's characteristics:
- Technical queries (with metrics/specifications) get lower thresholds
- Generic queries require higher scores to be accepted
- Suspicious queries are held to very high standards
"""

# ===== LANGUAGE ADJUSTMENTS =====

LANGUAGE_ADJUSTMENTS: Dict[str, float] = {
    "fr": 1.0,  # French - base reference (no adjustment)
    "en": 0.95,  # English - slight reduction
    "es": 0.90,  # Spanish - moderate reduction
    "it": 0.90,  # Italian - moderate reduction
    "pt": 0.90,  # Portuguese - moderate reduction
    "de": 0.85,  # German - larger reduction
    "nl": 0.85,  # Dutch - larger reduction
    "pl": 0.80,  # Polish - larger reduction
    "hi": 0.70,  # Hindi - more permissive for non-Latin scripts
    "th": 0.70,  # Thai - more permissive for non-Latin scripts
    "zh": 0.70,  # Chinese - more permissive for non-Latin scripts
    "id": 0.85,  # Indonesian - moderate reduction
}
"""
Language-specific threshold multipliers.

These multipliers adjust the base threshold according to the detected language.
Languages with non-Latin scripts (Hindi, Thai, Chinese) get more permissive
thresholds to account for reduced vocabulary coverage and translation challenges.

The multiplier is applied to the base threshold: adjusted_threshold = base_threshold * multiplier
"""

# ===== FALLBACK BLOCKED TERMS =====

FALLBACK_BLOCKED_TERMS: Dict[str, List[str]] = {
    "adult_content": ["porn", "sex", "nude", "adult", "xxx"],
    "crypto_finance": ["bitcoin", "crypto", "blockchain", "trading", "forex"],
    "politics": ["election", "politics", "vote", "government"],
    "entertainment": ["movie", "film", "netflix", "game", "gaming"],
    "sports": ["football", "soccer", "basketball", "tennis"],
    "technology": ["iphone", "android", "computer", "software", "app"],
}
"""
Fallback blocked terms when blocked_terms.json is unavailable.

These critical terms are categorized by domain and used as a last resort
to block clearly off-topic or inappropriate queries when the main
blocked terms configuration file cannot be loaded.
"""

# ===== FALLBACK UNIVERSAL TERMS =====

FALLBACK_UNIVERSAL_TERMS = {
    # Genetic lines (multilingual)
    "ross",
    "cobb",
    "hubbard",
    "isa",
    "aviagen",
    "peterson",
    # Universal metrics
    "fcr",
    "adr",
    "adg",
    "epef",
    "eef",
    # Generic poultry terms
    "broiler",
    "poultry",
    "chicken",
    "pullet",
    "hen",
    "poulet",
    "volaille",
    "aviculture",
    "élevage",
    "pollo",
    "ave",
    "crianza",
    "avicultura",
    "frango",
    "franga",
    "avicultura",
    "鸡",
    "家禽",
    "养殖",
    "饲养",
    "دجاج",
    "دواجن",
    "تربية",
}
"""
Universal multilingual poultry terms for fallback analysis.

These terms are recognized across languages and scripts, including:
- Genetic line names (brand names, same in all languages)
- Universal metrics (FCR, ADG, etc.)
- Poultry-related words in major languages (French, English, Spanish,
  Portuguese, Chinese, Arabic, etc.)

Used when translation service is unavailable to still provide
basic domain detection capabilities.
"""

# ===== TECHNICAL PATTERNS =====

TECHNICAL_PATTERNS: List[tuple] = [
    (
        r"\b(?:fcr|ic|indice|feed.conversion|料肉比|फसीआर)\b",
        "conversion_metric",
    ),
    (r"\b(?:ross|cobb|hubbard|isa|罗斯|科宝|रॉस|कॉब)\s*\d*\b", "genetic_line"),
    (
        r"\b\d+\s*(?:jour|day|semaine|week|dia|tag|วัน|天|दिन|hari)s?\b",
        "age_specification",
    ),
    (
        r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|gram|克|公斤|ग्राम|किलो)\b",
        "weight_measure",
    ),
    (r"\b\d+[.,]?\d*\s*%\b", "percentage_value"),
]
"""
Technical pattern matchers for multilingual query analysis.

Each tuple contains:
1. A regex pattern to match technical indicators
2. A label describing the type of technical indicator

These patterns recognize:
- Feed conversion metrics in multiple languages
- Genetic line names with optional numeric suffixes
- Age specifications in various languages and scripts
- Weight measurements across different unit systems
- Percentage values
"""

# ===== WEIGHT MULTIPLIERS =====

WEIGHT_MULTIPLIERS: Dict = {
    "HIGH": 1.0,  # High relevance words get full weight
    "MEDIUM": 0.6,  # Medium relevance words get 60% weight
    "LOW": 0.3,  # Low relevance words get 30% weight
    "GENERIC": 0.1,  # Generic words get minimal weight
}
"""
Weight multipliers for domain relevance levels.

These multipliers are used to calculate the weighted score when
domain words are found. Higher relevance words contribute more
to the final score. The weighted score formula is:
    weighted_score = sum(word_count * multiplier for each level)
"""

# ===== ACRONYM EXPANSIONS =====

def _load_acronym_expansions() -> Dict[str, str]:
    """
    Load acronym expansions from poultry_terminology.json.

    Returns a dictionary mapping acronyms (lowercase) to their full forms
    in French and English for query normalization.

    Falls back to hardcoded acronyms if JSON file is unavailable.
    """
    try:
        # Get path to poultry_terminology.json (relative to this config file)
        config_dir = Path(__file__).parent.parent.parent / "config"
        terminology_file = config_dir / "poultry_terminology.json"

        if not terminology_file.exists():
            raise FileNotFoundError(f"Terminology file not found: {terminology_file}")

        with open(terminology_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        expansions = {}
        acronyms = data.get("acronyms", {})

        for key, value in acronyms.items():
            if key.startswith("_"):  # Skip comment fields
                continue

            # Get all acronym variants
            acronym_variants = value.get("acronym", [])
            full_forms = value.get("full_form", {})

            # Get French and English full forms
            fr_form = full_forms.get("fr", "")
            en_form = full_forms.get("en", "")

            # Map each acronym variant to both French and English forms
            for variant in acronym_variants:
                variant_lower = variant.lower()
                # Prefer French form, fallback to English
                if fr_form:
                    expansions[variant_lower] = fr_form.lower()
                elif en_form:
                    expansions[variant_lower] = en_form.lower()

        return expansions

    except Exception as e:
        # Fallback to hardcoded acronyms if loading fails
        print(f"Warning: Could not load acronyms from JSON ({e}). Using fallback acronyms.")
        return {
            "ic": "indice conversion",
            "fcr": "feed conversion ratio",
            "pv": "poids vif",
            "gmq": "gain moyen quotidien",
        }

# Load acronym expansions at module initialization
ACRONYM_EXPANSIONS: Dict[str, str] = _load_acronym_expansions()
"""
Acronym to full-text expansions for query normalization.

Loaded from llm/config/poultry_terminology.json "acronyms" section.
Common poultry industry acronyms are expanded to their full forms
during query normalization to improve matching against the domain
vocabulary. This helps recognize queries that use abbreviated terms.

Examples:
- "IC" → "indice de consommation" (conversion index)
- "FCR" → "feed conversion ratio"
- "PV" → "poids vif" (live weight)
- "GMQ" → "gain moyen quotidien" (average daily gain)
- "ADG" → "average daily gain"
- "EPEF" → "european production efficiency factor"

Falls back to hardcoded acronyms if JSON file is unavailable.
"""

# ===== GENERIC QUERY WORDS =====

GENERIC_QUERY_WORDS = {
    # French
    "comment",
    "quoi",
    "pourquoi",
    "quand",
    "où",
    "combien",
    "quel",
    "quelle",
    "que",
    "qui",
    "meilleur",
    "optimal",
    "idéal",
    # English
    "how",
    "what",
    "why",
    "when",
    "where",
    "how much",
    "which",
    "who",
    "best",
    "ideal",
    # Hindi
    "कैसे",
    "क्या",
    "क्यों",
    "कब",
    "कहाँ",
    "कितना",
    "कौन",
    "कौन सा",
    # Chinese
    "如何",
    "什么",
    "为什么",
    "什么时候",
    "哪里",
    "多少",
    "哪个",
    "谁",
    # Thai
    "อย่างไร",
    "อะไร",
    "ทำไม",
    "เมื่อไหร่",
    "ที่ไหน",
    "เท่าไหร่",
    "ไหน",
    "ใคร",
}
"""
Generic query words (question words, common terms) across multiple languages.
Used for building the GENERIC relevance vocabulary.

These are common question words and generic terms that appear in queries
but don't specifically indicate domain relevance. They get minimal weight
in domain scoring.
"""

# ===== FALLBACK VOCABULARY EXTENSIONS =====

FALLBACK_HIGH_PRIORITY_TERMS = {
    "ross",
    "cobb",
    "hubbard",
    "isa",
    "aviagen",
    "peterson",
    "fcr",
    "adr",
    "adg",
    "epef",
    "eef",
    "conversion",
    "broiler",
    "poulet",
    "pollo",
    "frango",
    "鸡",
    "دجاج",
    "poultry",
    "volaille",
    "avicultura",
    "aviculture",
}
"""
High-priority domain terms for fallback vocabulary.
These terms strongly indicate poultry domain relevance.
"""

FALLBACK_MEDIUM_PRIORITY_TERMS = {
    "feed",
    "nutrition",
    "alimentation",
    "pienso",
    "ração",
    "weight",
    "poids",
    "peso",
    "waga",
    "重量",
    "وزن",
    "mortality",
    "mortalité",
    "mortalidad",
    "मृत्यु दर",
    "housing",
    "élevage",
    "crianza",
    "alojamiento",
}
"""
Medium-priority domain terms for fallback vocabulary.
These terms moderately indicate poultry domain relevance.
"""

# ===== NON-LATIN SCRIPT LANGUAGES =====

NON_LATIN_SCRIPT_LANGUAGES = {
    "hi",  # Hindi
    "th",  # Thai
    "zh",  # Chinese
    "ar",  # Arabic
    "ja",  # Japanese
    "ko",  # Korean
}
"""
Languages using non-Latin scripts.
Require special handling for normalization and pattern matching.
"""
