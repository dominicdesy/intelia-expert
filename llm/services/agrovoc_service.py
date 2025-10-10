# -*- coding: utf-8 -*-
"""
AGROVOC Service - Hybrid 3-Level Poultry Term Detection

Level 1: AGROVOC Cache (10 languages: fr, en, es, de, it, pt, pl, hi, th, zh)
Level 2: Manual Terms (for nl, id + modern terms not in AGROVOC)
Level 3: Universal Fallback (basic poultry terms)

This service provides scalable poultry term detection using FAO's AGROVOC
agricultural vocabulary as the primary source, with manual fallback for:
- Languages not supported by AGROVOC (Dutch, Indonesian)
- Modern meat quality defects not yet in AGROVOC (spaghetti breast, white striping, etc.)
"""

import json
import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


class AGROVOCService:
    """Service for detecting poultry-related terms using AGROVOC + manual fallback"""

    # Languages supported by AGROVOC (10/12)
    AGROVOC_LANGUAGES = {'fr', 'en', 'es', 'de', 'it', 'pt', 'pl', 'hi', 'th', 'zh'}

    # Languages requiring manual fallback (2/12)
    MANUAL_LANGUAGES = {'nl', 'id'}

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize AGROVOC service

        Args:
            cache_path: Path to agrovoc_poultry_cache.json (default: llm/agrovoc_poultry_cache.json)
        """
        self.cache_path = cache_path or self._get_default_cache_path()
        self.agrovoc_cache = self._load_cache()
        self.manual_terms = self._build_manual_terms()
        self.universal_terms = self._build_universal_terms()

        logger.info(f"AGROVOCService initialized with {len(self.agrovoc_cache)} cached terms")

    def _get_default_cache_path(self) -> str:
        """Get default path to AGROVOC cache"""
        # Cache is in llm/agrovoc_poultry_cache.json
        llm_dir = Path(__file__).parent.parent
        return str(llm_dir / "agrovoc_poultry_cache.json")

    def _load_cache(self) -> dict:
        """Load AGROVOC cache from JSON file"""
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                logger.info(f"Loaded {len(cache)} terms from AGROVOC cache")
                return cache
        except FileNotFoundError:
            logger.warning(f"AGROVOC cache not found at {self.cache_path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading AGROVOC cache: {e}")
            return {}

    def _build_manual_terms(self) -> dict:
        """
        Build manual term dictionary for:
        1. Dutch (nl) and Indonesian (id) - not supported by AGROVOC
        2. Modern meat quality defects - not yet in AGROVOC database

        Returns:
            Dictionary with format {"language:term": True}
        """
        manual_terms = {}

        # Dutch (nl) - manual poultry terms
        dutch_terms = [
            "pluimvee", "kip", "kippen", "kippenvlees", "broiler", "leghen",
            "braadkip", "hoenderij", "pluimveehouderij", "eierproductie",
            "vleesproductie", "fokkerij", "uitbroeden", "kuiken", "kuikens",
        ]
        for term in dutch_terms:
            manual_terms[f"nl:{term.lower()}"] = True

        # Indonesian (id) - manual poultry terms
        indonesian_terms = [
            "unggas", "ayam", "daging ayam", "broiler", "petelur",
            "ayam pedaging", "ayam petelur", "peternakan", "penetasan",
            "produksi telur", "produksi daging", "pembibitan",
        ]
        for term in indonesian_terms:
            manual_terms[f"id:{term.lower()}"] = True

        # Modern meat quality defects (all languages - not in AGROVOC)
        # These are recent research terms (2010s-2020s)
        modern_defects = {
            'en': ['spaghetti breast', 'white striping', 'wooden breast', 'deep pectoral myopathy'],
            'fr': ['poitrine spaghetti', 'stries blanches', 'poitrine en bois'],
            'es': ['pechuga espagueti', 'estriado blanco', 'pechuga de madera'],
            'de': ['spaghetti-brust', 'weiße streifen', 'holzbrust'],
            'it': ['petto spaghetti', 'striature bianche', 'petto di legno'],
            'pt': ['peito espaguete', 'estrias brancas', 'peito lenhoso'],
            'nl': ['spaghetti borst', 'witte strepen', 'houten borst'],
            'pl': ['pierś spaghetti', 'białe prążki', 'drewniana pierś'],
            'id': ['dada spaghetti', 'garis putih', 'dada kayu'],
        }

        for lang, terms in modern_defects.items():
            for term in terms:
                manual_terms[f"{lang}:{term.lower()}"] = True

        logger.info(f"Built {len(manual_terms)} manual terms (nl, id + modern defects)")
        return manual_terms

    def _build_universal_terms(self) -> Set[str]:
        """
        Build universal fallback terms (language-agnostic basics)

        These are very common terms that should be recognized in any language
        variant (chicken, poulet, pollo, etc.)
        """
        universal = {
            # English
            "poultry", "chicken", "chickens", "broiler", "broilers", "layer", "layers",
            "hen", "hens", "rooster", "roosters", "bird", "birds", "chick", "chicks",

            # French
            "volaille", "volailles", "poulet", "poulets", "poule", "poules",
            "poussin", "poussins", "coq", "coqs",

            # Spanish
            "ave", "aves", "pollo", "pollos", "gallina", "gallinas",

            # German
            "geflügel", "huhn", "hühner", "hähnchen",

            # Italian
            "pollame", "pollo", "polli", "gallina", "galline",

            # Portuguese
            "ave", "aves", "frango", "frangos", "galinha", "galinhas",

            # Dutch
            "kip", "kippen", "pluimvee",

            # Polish
            "drób", "kurczak", "kurczaki", "kura", "kury",

            # Indonesian
            "ayam", "unggas",

            # Hindi (transliterated)
            "murgi", "kukut",

            # Thai (transliterated)
            "gai",

            # Chinese (transliterated)
            "ji", "jia qin",
        }

        logger.info(f"Built {len(universal)} universal fallback terms")
        return universal

    def is_poultry_term(self, term: str, language: str) -> bool:
        """
        Check if term is poultry-related using 3-level detection

        Args:
            term: Term to check (case-insensitive)
            language: Language code (en, fr, es, etc.)

        Returns:
            True if term is poultry-related, False otherwise

        Detection levels:
            1. AGROVOC cache (if language in AGROVOC_LANGUAGES)
            2. Manual terms (for nl, id, or modern defects)
            3. Universal fallback (basic terms in any language)
        """
        if not term or not language:
            return False

        term_lower = term.lower().strip()
        cache_key = f"{language}:{term_lower}"

        # Level 1: AGROVOC cache (10 languages)
        if language in self.AGROVOC_LANGUAGES:
            if cache_key in self.agrovoc_cache:
                logger.debug(f"✅ AGROVOC match: {cache_key}")
                return True

        # Level 2: Manual terms (nl, id + modern defects)
        if cache_key in self.manual_terms:
            logger.debug(f"✅ Manual match: {cache_key}")
            return True

        # Level 3: Universal fallback (basic terms)
        if term_lower in self.universal_terms:
            logger.debug(f"✅ Universal match: {term_lower}")
            return True

        return False

    def detect_poultry_terms_in_query(self, query: str, language: str) -> bool:
        """
        Check if query contains ANY poultry-related terms

        Args:
            query: Query string
            language: Language code

        Returns:
            True if query contains at least one poultry term
        """
        if not query:
            return False

        query_lower = query.lower()
        words = query_lower.split()

        # Check single words
        for word in words:
            # Remove punctuation
            word_clean = word.strip(".,!?;:()[]{}\"'")
            if self.is_poultry_term(word_clean, language):
                logger.debug(f"🐔 Poultry term detected in query: '{word_clean}'")
                return True

        # Check multi-word terms (bigrams and trigrams)
        for i in range(len(words) - 1):
            # Bigrams
            bigram = f"{words[i]} {words[i+1]}"
            bigram_clean = bigram.strip(".,!?;:()[]{}\"'")
            if self.is_poultry_term(bigram_clean, language):
                logger.debug(f"🐔 Poultry term detected in query: '{bigram_clean}'")
                return True

            # Trigrams
            if i < len(words) - 2:
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                trigram_clean = trigram.strip(".,!?;:()[]{}\"'")
                if self.is_poultry_term(trigram_clean, language):
                    logger.debug(f"🐔 Poultry term detected in query: '{trigram_clean}'")
                    return True

        return False

    def get_stats(self) -> dict:
        """Get statistics about loaded terms"""
        stats = {
            'agrovoc_terms': len(self.agrovoc_cache),
            'manual_terms': len(self.manual_terms),
            'universal_terms': len(self.universal_terms),
            'total_terms': len(self.agrovoc_cache) + len(self.manual_terms) + len(self.universal_terms),
            'agrovoc_languages': sorted(self.AGROVOC_LANGUAGES),
            'manual_languages': sorted(self.MANUAL_LANGUAGES),
        }

        # Terms per language (AGROVOC)
        agrovoc_by_lang = {}
        for key in self.agrovoc_cache.keys():
            lang = key.split(':')[0]
            agrovoc_by_lang[lang] = agrovoc_by_lang.get(lang, 0) + 1
        stats['agrovoc_by_language'] = agrovoc_by_lang

        # Manual terms per language
        manual_by_lang = {}
        for key in self.manual_terms.keys():
            lang = key.split(':')[0]
            manual_by_lang[lang] = manual_by_lang.get(lang, 0) + 1
        stats['manual_by_language'] = manual_by_lang

        return stats


# Singleton instance
_agrovoc_service_instance = None


def get_agrovoc_service() -> AGROVOCService:
    """Get singleton AGROVOCService instance"""
    global _agrovoc_service_instance
    if _agrovoc_service_instance is None:
        _agrovoc_service_instance = AGROVOCService()
    return _agrovoc_service_instance
