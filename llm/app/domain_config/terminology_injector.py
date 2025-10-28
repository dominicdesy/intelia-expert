"""
Terminology Injector - Intelligent Contextual Terminology Injection

This module provides smart terminology injection into LLM prompts:
1. Keyword matching: Detects relevant terms in the query
2. Category loading: Loads only relevant category terms
3. Token limit: Ensures terminology doesn't exceed token budget
4. Relevance ranking: Prioritizes most relevant terms
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re

logger = logging.getLogger(__name__)


class TerminologyInjector:
    """
    Intelligent terminology injection system for LLM prompts
    """

    def __init__(self, extended_glossary_path: Path = None, value_chain_path: Path = None):
        """
        Initialize terminology injector

        Args:
            extended_glossary_path: Path to extended_glossary.json (1476 terms from PDFs)
            value_chain_path: Path to value_chain_terminology.json (100+ structured terms)
        """
        self.extended_glossary = {}
        self.value_chain_terms = {}
        self.category_index = {}  # category -> [term_keys]
        self.keyword_index = {}   # keyword -> [term_keys]

        # Load glossaries
        if extended_glossary_path and extended_glossary_path.exists():
            self._load_extended_glossary(extended_glossary_path)
        else:
            logger.warning(f"Extended glossary not found at {extended_glossary_path}")

        if value_chain_path and value_chain_path.exists():
            self._load_value_chain_terms(value_chain_path)
        else:
            logger.warning(f"Value chain terminology not found at {value_chain_path}")

        logger.info(f"[OK] TerminologyInjector initialized with {len(self.extended_glossary)} extended terms")

    def _load_extended_glossary(self, path: Path):
        """Load extended glossary from JSON"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.extended_glossary = data.get('terms', {})

            # Build category index
            for term_key, term_data in self.extended_glossary.items():
                category = term_data.get('category', 'general')
                if category not in self.category_index:
                    self.category_index[category] = []
                self.category_index[category].append(term_key)

            # Build keyword index (term words -> term_keys)
            for term_key, term_data in self.extended_glossary.items():
                term_text = term_data.get('term', '').lower()
                # Extract keywords (2+ character words)
                keywords = [w for w in re.findall(r'\b\w+\b', term_text) if len(w) >= 2]
                for keyword in keywords:
                    if keyword not in self.keyword_index:
                        self.keyword_index[keyword] = []
                    self.keyword_index[keyword].append(term_key)

            logger.info(f"Loaded {len(self.extended_glossary)} terms across {len(self.category_index)} categories")

        except Exception as e:
            logger.error(f"Error loading extended glossary: {e}")

    def _load_value_chain_terms(self, path: Path):
        """Load value chain terminology (structured with translations)"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Flatten all categories
                for category_key, category_terms in data.items():
                    if category_key == 'metadata':
                        continue
                    for term_key, term_data in category_terms.items():
                        self.value_chain_terms[f"vc_{term_key}"] = {
                            'term': term_key.replace('_', ' ').title(),
                            'en': term_data.get('en', ''),
                            'fr': term_data.get('fr', ''),
                            'description': term_data.get('description', ''),
                            'category': category_key
                        }

            # [FAST] OPTIMIZATION Phase 2: Build keyword index for O(1) value chain lookup (saves ~4ms)
            # Instead of linear search through 100+ terms, we index by keywords
            self.value_chain_index = {}
            for vc_key, vc_data in self.value_chain_terms.items():
                term_text = vc_data.get('term', '').lower()
                # Extract keywords (2+ character words)
                term_words = re.findall(r'\b\w{2,}\b', term_text)
                for word in term_words:
                    if word not in self.value_chain_index:
                        self.value_chain_index[word] = []
                    self.value_chain_index[word].append(vc_key)

            logger.info(f"Loaded {len(self.value_chain_terms)} value chain terms with keyword index")

        except Exception as e:
            logger.error(f"Error loading value chain terms: {e}")

    def detect_relevant_categories(self, query: str) -> List[str]:
        """
        Detect relevant categories based on query keywords

        Args:
            query: User query text

        Returns:
            List of relevant category names, ordered by relevance
        """
        query_lower = query.lower()
        category_scores = {}

        # Category detection keywords
        category_keywords = {
            'hatchery_incubation': [
                'hatch', 'incubat', 'egg storage', 'candling', 'setter', 'embryo',
                'chick quality', 'fertility', 'pip', 'breakout', 'fumigation'
            ],
            'processing_meat_quality': [
                'process', 'slaughter', 'carcass', 'yield', 'breast', 'meat',
                'stunning', 'eviscerat', 'scald', 'debon', 'chilling', 'ph'
            ],
            'layer_production_egg_quality': [
                'layer', 'laying', 'egg production', 'hen-day', 'haugh unit',
                'shell strength', 'yolk color', 'molt', 'point of lay', 'peak'
            ],
            'breeding_genetics': [
                'breeding', 'genetic', 'selection', 'heritab', 'crossbreed',
                'heterosis', 'pedigree', 'progeny', 'snp', 'genomic'
            ],
            'nutrition_feed': [
                'feed', 'nutrition', 'protein', 'energy', 'amino acid',
                'fcr', 'lysine', 'vitamin', 'mineral', 'calcium', 'ration'
            ],
            'health_disease': [
                'disease', 'health', 'virus', 'bacteria', 'vaccin', 'mortality',
                'coccidiosis', 'newcastle', 'influenza', 'biosecurity', 'antibiotic'
            ],
            'farm_management_equipment': [
                'ventilat', 'temperature', 'housing', 'litter', 'drinker',
                'feeder', 'density', 'stocking', 'lighting', 'ammonia'
            ],
            'anatomy_physiology': [
                'bone', 'muscle', 'organ', 'blood', 'respiratory', 'digestive',
                'intestine', 'gizzard', 'feather', 'cloaca'
            ]
        }

        # Score each category
        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                category_scores[category] = score

        # Sort by score (descending)
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

        return [cat for cat, score in sorted_categories]

    def find_matching_terms(self, query: str, max_terms: int = 20) -> List[Dict]:
        """
        Find terms matching the query

        Strategy:
        1. Direct keyword matching (highest priority)
        2. Category-based loading (medium priority)
        3. General relevant terms (low priority)

        Args:
            query: User query text
            max_terms: Maximum number of terms to return

        Returns:
            List of term dictionaries with relevance scores
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w{2,}\b', query_lower))

        matching_terms = {}  # term_key -> (term_data, score)

        # 1. Direct keyword matching (score: 10)
        for word in query_words:
            if word in self.keyword_index:
                for term_key in self.keyword_index[word]:
                    if term_key not in matching_terms:
                        matching_terms[term_key] = (self.extended_glossary[term_key], 10)
                    else:
                        # Increase score for multiple matches
                        current_data, current_score = matching_terms[term_key]
                        matching_terms[term_key] = (current_data, current_score + 5)

        # 2. Category-based loading (score: 5) - [FAST] OPTIMIZATION: Reduced from 20 to 10 per category
        relevant_categories = self.detect_relevant_categories(query)
        for category in relevant_categories[:2]:  # Top 2 categories only (reduced from 3)
            if category in self.category_index:
                for term_key in self.category_index[category][:10]:  # Max 10 per category (reduced from 20)
                    if term_key not in matching_terms:
                        matching_terms[term_key] = (self.extended_glossary[term_key], 5)

        # 3. Add value chain terms using indexed lookup ([FAST] saves ~4ms vs linear search)
        for word in query_words:
            if word in self.value_chain_index:
                for vc_key in self.value_chain_index[word]:
                    if vc_key not in matching_terms:
                        matching_terms[vc_key] = (self.value_chain_terms[vc_key], 8)

        # Sort by score and limit
        sorted_terms = sorted(matching_terms.items(), key=lambda x: x[1][1], reverse=True)
        top_terms = sorted_terms[:max_terms]

        # Return term data only
        return [term_data for term_key, (term_data, score) in top_terms]

    def format_terminology_for_prompt(
        self,
        query: str,
        max_tokens: int = 600,  # [FAST] OPTIMIZATION: Reduced from 1000 to 600 tokens (~400 token savings)
        language: str = 'en'
    ) -> str:
        """
        Format relevant terminology for injection into system prompt

        Args:
            query: User query text
            max_tokens: Maximum tokens to use for terminology (approx)
            language: Language for terminology (en/fr)

        Returns:
            Formatted terminology string ready for prompt injection
        """
        # Find matching terms ([FAST] OPTIMIZATION: Reduced from 50 to 20 terms)
        matching_terms = self.find_matching_terms(query, max_terms=20)

        if not matching_terms:
            return ""

        # Estimate: ~4 chars per token (rough approximation)
        max_chars = max_tokens * 4

        # Build terminology section
        lines = [
            "## Relevant Technical Terminology",
            "",
            "Use the following precise technical terms when responding:",
            ""
        ]

        current_chars = sum(len(line) for line in lines)
        terms_added = 0

        for term_data in matching_terms:
            term_name = term_data.get('term', '')
            definition = term_data.get('definition', '')

            # For value chain terms, use language-specific translations
            if 'en' in term_data and 'fr' in term_data:
                term_display = term_data.get(language, term_data.get('en', term_name))
                definition = term_data.get('description', definition)
            else:
                term_display = term_name

            # Format: "- **Term**: definition"
            term_line = f"- **{term_display}**: {definition}"

            # Check if we have space
            if current_chars + len(term_line) > max_chars:
                break

            lines.append(term_line)
            current_chars += len(term_line)
            terms_added += 1

        if terms_added == 0:
            return ""

        lines.append("")
        lines.append(f"_({terms_added} relevant terms loaded)_")
        lines.append("")

        result = '\n'.join(lines)
        logger.info(f"[BOOK] Injected {terms_added} terminology terms (~{len(result)} chars)")

        return result

    def get_terminology_stats(self) -> Dict:
        """Get statistics about loaded terminology"""
        return {
            'extended_glossary_terms': len(self.extended_glossary),
            'value_chain_terms': len(self.value_chain_terms),
            'total_terms': len(self.extended_glossary) + len(self.value_chain_terms),
            'categories': list(self.category_index.keys()),
            'indexed_keywords': len(self.keyword_index)
        }


# Singleton instance
_terminology_injector = None


def get_terminology_injector(
    extended_glossary_path: Path = None,
    value_chain_path: Path = None
) -> TerminologyInjector:
    """
    Get singleton instance of terminology injector

    Args:
        extended_glossary_path: Path to extended glossary (only used on first call)
        value_chain_path: Path to value chain terms (only used on first call)

    Returns:
        TerminologyInjector instance
    """
    global _terminology_injector

    if _terminology_injector is None:
        # Default paths if not provided
        if extended_glossary_path is None:
            config_dir = Path(__file__).parent / 'domains' / 'aviculture'
            extended_glossary_path = config_dir / 'extended_glossary.json'

        if value_chain_path is None:
            config_dir = Path(__file__).parent / 'domains' / 'aviculture'
            value_chain_path = config_dir / 'value_chain_terminology.json'

        _terminology_injector = TerminologyInjector(
            extended_glossary_path=extended_glossary_path,
            value_chain_path=value_chain_path
        )

    return _terminology_injector
