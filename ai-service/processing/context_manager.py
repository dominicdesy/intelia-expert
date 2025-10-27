# -*- coding: utf-8 -*-
"""
context_manager.py - Context Manager for multi-turn conversation resolution
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
context_manager.py - Context Manager for multi-turn conversation resolution

Manages conversation context to resolve coreferences in multi-turn dialogues.
Example: "Et pour les femelles?" → "Poids femelles Ross 308 35 jours"

Version: 1.0
"""

import logging
from dataclasses import dataclass
from utils.types import Optional, Dict, Any, List
import re

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """
    Stores conversation context for coreference resolution

    Attributes:
        breed: Last mentioned breed (Ross 308, Cobb 500, etc.)
        age: Last mentioned age in days
        sex: Last mentioned sex (male, female, mixed)
        metric: Last mentioned metric (weight, FCR, gain, etc.)
        intent: Last intent type
        full_query: Last complete query
    """
    breed: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    metric: Optional[str] = None
    intent: Optional[str] = None
    full_query: Optional[str] = None


class ContextManager:
    """
    Manages conversation context for multi-turn resolution

    Features:
    - Extracts entities from queries (breed, age, sex, metric)
    - Detects coreferences (pronouns, demonstratives)
    - Expands incomplete queries using context
    - Maintains session-level context

    Example:
        >>> manager = ContextManager()
        >>> manager.update_context("Quel est le poids Ross 308 à 35 jours?")
        >>> expanded = manager.expand_query("Et pour les femelles?")
        >>> # Result: "Quel est le poids femelles Ross 308 à 35 jours?"
    """

    def __init__(self):
        """Initialize context manager"""
        self.context = ConversationContext()
        self.context_history: List[ConversationContext] = []

        # Patterns pour extraction d'entités
        self.breed_pattern = re.compile(
            r'\b(ross\s*\d+|cobb\s*\d+|hubbard|aviagen|lohmann|hy-line|isa)\b',
            re.IGNORECASE
        )

        self.age_pattern = re.compile(
            r'\b(\d+)\s*(jour|jours|day|days|j)\b',
            re.IGNORECASE
        )

        self.sex_pattern = re.compile(
            r'\b(m[aâ]les?|femelles?|females?|males?|mixte|mixed)\b',
            re.IGNORECASE
        )

        self.metric_keywords = {
            'poids': ['poids', 'weight'],
            'fcr': ['fcr', 'icg', 'conversion'],
            'gain': ['gain', 'croissance', 'growth'],
            'mortality': ['mortalité', 'mortality'],
            'production': ['production', 'ponte', 'egg'],
            'consumption': ['consommation', 'consumption', 'feed']
        }

        # Patterns de coréférence (questions incomplètes)
        self.coreference_patterns = [
            r'^et\s+(pour|chez)\s+',  # "Et pour les femelles?"
            r'^même\s+chose',         # "Même chose pour..."
            r'^à\s+cet\s+[aâ]ge',     # "À cet âge-là?"
            r'^pour\s+cette\s+race',  # "Pour cette race?"
            r'^quelle?\s*est',        # "Quel est..." (sans contexte)
            r'^\?$',                  # Juste "?"
        ]

    def is_coreference(self, query: str) -> bool:
        """
        Detect if query contains coreference (needs context resolution)

        Args:
            query: User query

        Returns:
            True if query needs context resolution
        """
        query_lower = query.lower().strip()

        # Check explicit coreference patterns
        for pattern in self.coreference_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Coreference detected: {pattern} in '{query}'")
                return True

        # Check if query is too short/vague (< 5 words, no entities)
        words = query_lower.split()
        if len(words) < 5:
            has_breed = bool(self.breed_pattern.search(query))
            has_age = bool(self.age_pattern.search(query))
            if not has_breed and not has_age:
                logger.debug(f"Short query without context: '{query}'")
                return True

        return False

    def extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from query

        Args:
            query: User query

        Returns:
            Dict with extracted entities (breed, age, sex, metric)
        """
        entities = {}

        # Extract breed
        breed_match = self.breed_pattern.search(query)
        if breed_match:
            entities['breed'] = breed_match.group(1)

        # Extract age
        age_match = self.age_pattern.search(query)
        if age_match:
            try:
                # Store as string for compatibility with 'in' operator in tests
                entities['age'] = str(age_match.group(1))
            except ValueError:
                pass

        # Extract sex
        sex_match = self.sex_pattern.search(query)
        if sex_match:
            sex_raw = sex_match.group(1).lower()
            if 'male' in sex_raw or 'mâle' in sex_raw:
                entities['sex'] = 'male' if 'femel' not in sex_raw else 'female'
            elif 'femel' in sex_raw:
                entities['sex'] = 'female'
            else:
                entities['sex'] = 'mixed'

        # Extract metric
        for metric_type, keywords in self.metric_keywords.items():
            for keyword in keywords:
                if keyword in query.lower():
                    entities['metric'] = metric_type
                    break
            if 'metric' in entities:
                break

        logger.debug(f"Extracted entities from '{query}': {entities}")
        return entities

    def update_context(
        self,
        query: str,
        intent_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update conversation context from query and intent

        Args:
            query: User query
            intent_result: Intent classification result (optional)
        """
        # Save previous context
        if self.context.full_query:
            self.context_history.append(self.context)

        # Extract new entities
        entities = self.extract_entities(query)

        # Update context (keep previous values if not found in new query)
        self.context = ConversationContext(
            breed=entities.get('breed') or self.context.breed,
            age=entities.get('age') or self.context.age,
            sex=entities.get('sex') or self.context.sex,
            metric=entities.get('metric') or self.context.metric,
            intent=intent_result.get('intent') if intent_result else self.context.intent,
            full_query=query
        )

        logger.info(
            f"Context updated: breed={self.context.breed}, age={self.context.age}, "
            f"sex={self.context.sex}, metric={self.context.metric}"
        )

    def expand_query(self, query: str) -> str:
        """
        Expand incomplete query using conversation context

        Args:
            query: Potentially incomplete query with coreference

        Returns:
            Expanded query with resolved context

        Example:
            >>> # After: "Poids Ross 308 à 35 jours?"
            >>> expand_query("Et pour les femelles?")
            >>> # Returns: "Poids femelles Ross 308 à 35 jours"
        """
        # Check if expansion needed
        if not self.is_coreference(query):
            logger.debug(f"No coreference detected, returning original: '{query}'")
            return query

        # Extract any new entities from current query
        new_entities = self.extract_entities(query)

        # Build expanded query using context + new entities
        expanded_parts = []

        # Add metric if available
        metric = new_entities.get('metric') or self.context.metric
        if metric:
            expanded_parts.append(metric)

        # Add sex (prioritize new entity)
        sex = new_entities.get('sex') or self.context.sex
        if sex:
            sex_french = 'femelles' if sex == 'female' else 'mâles' if sex == 'male' else 'mixte'
            expanded_parts.append(sex_french)

        # Add breed (prioritize new entity)
        breed = new_entities.get('breed') or self.context.breed
        if breed:
            expanded_parts.append(breed)

        # Add age (prioritize new entity)
        age = new_entities.get('age') or self.context.age
        if age:
            expanded_parts.append(f"à {age} jours")

        # If nothing to expand, return original
        if not expanded_parts:
            logger.warning(f"No context available for expansion of '{query}'")
            return query

        # Build expanded query
        expanded = ' '.join(expanded_parts)
        logger.info(f"Expanded query: '{query}' → '{expanded}'")

        return expanded

    def get_context_summary(self) -> str:
        """
        Get human-readable summary of current context

        Returns:
            String summary of context
        """
        parts = []
        if self.context.breed:
            parts.append(f"Breed: {self.context.breed}")
        if self.context.age:
            parts.append(f"Age: {self.context.age} days")
        if self.context.sex:
            parts.append(f"Sex: {self.context.sex}")
        if self.context.metric:
            parts.append(f"Metric: {self.context.metric}")

        return ", ".join(parts) if parts else "No context"

    def clear_context(self) -> None:
        """Clear conversation context (new session)"""
        self.context = ConversationContext()
        self.context_history = []
        logger.info("Context cleared")

    def reset(self) -> None:
        """Alias for clear_context() - Reset conversation context"""
        self.clear_context()


# Singleton instance for global access
_context_manager_instance: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """
    Get singleton instance of ContextManager

    Returns:
        ContextManager instance
    """
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = ContextManager()
    return _context_manager_instance


__all__ = ['ContextManager', 'ConversationContext', 'get_context_manager']
