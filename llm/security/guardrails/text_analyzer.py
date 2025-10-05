# -*- coding: utf-8 -*-
"""
text_analyzer.py - Text analysis utilities for guardrails

This module provides text analysis utilities extracted from advanced_guardrails.py
for cleaner code organization and reusability.

Classes:
    TextAnalyzer: Static utility methods for text analysis, normalization, and matching
"""

import re
import logging
from utils.types import Dict, List, Any

logger = logging.getLogger(__name__)


class TextAnalyzer:
    """
    Text analysis utilities for guardrails verification.

    This class provides static methods for text processing tasks including:
    - Text normalization and comparison
    - Fuzzy matching
    - Entity variant detection
    - Numeric coherence checking
    - Claim and context extraction
    - Comparison element extraction
    """

    # Domain keywords for aviculture/poultry context
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

    @staticmethod
    def _fuzzy_match(claim: str, content: str) -> bool:
        """
        Perform fuzzy matching between a claim and content.

        Uses normalized text comparison with segment-based matching.
        Considers a match successful if more than 60% of significant segments
        (length > 3) from the claim are found in the content.

        Args:
            claim: The claim text to match
            content: The content text to search in

        Returns:
            bool: True if fuzzy match succeeds (>60% segment overlap), False otherwise

        Example:
            >>> TextAnalyzer._fuzzy_match("Ross 308 broiler", "ross 308 poulet de chair")
            True
        """
        claim_norm = TextAnalyzer._normalize_text(claim)
        content_norm = TextAnalyzer._normalize_text(content)

        # Extract significant segments (words longer than 3 characters)
        claim_segments = [seg for seg in claim_norm.split() if len(seg) > 3]

        if not claim_segments:
            return False

        # Count matching segments
        matches = sum(1 for seg in claim_segments if seg in content_norm)
        return (matches / len(claim_segments)) > 0.6

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize text for comparison purposes.

        Performs the following normalizations:
        - Converts to lowercase
        - Removes French accents (é→e, è→e, à→a, etc.)
        - Removes excessive punctuation
        - Normalizes whitespace

        Args:
            text: The text to normalize

        Returns:
            str: Normalized text suitable for comparison

        Example:
            >>> TextAnalyzer._normalize_text("Température élevée: 32°C!")
            'temperature elevee 32 c'
        """
        # Convert to lowercase
        normalized = text.lower()

        # Remove French accents using simple character mapping
        accent_map = {
            "é": "e",
            "è": "e",
            "ê": "e",
            "ë": "e",
            "à": "a",
            "â": "a",
            "ä": "a",
            "ù": "u",
            "û": "u",
            "ü": "u",
            "ô": "o",
            "ö": "o",
            "î": "i",
            "ï": "i",
            "ç": "c",
        }

        for accented, simple in accent_map.items():
            normalized = normalized.replace(accented, simple)

        # Remove excessive punctuation, keeping numbers, dots, commas, percent, and hyphens
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    @staticmethod
    def _find_entity_variants(entity: str, text: str) -> bool:
        """
        Search for entity variants in text.

        Looks for common variants and synonyms of poultry-related entities
        such as breed names, sex designations, and age groups.

        Args:
            entity: The entity to search for
            text: The text to search in

        Returns:
            bool: True if any variant of the entity is found in text

        Example:
            >>> TextAnalyzer._find_entity_variants("ross", "lignée ross 308")
            True
            >>> TextAnalyzer._find_entity_variants("male", "coq de souche cobb")
            True
        """
        variants_map = {
            "ross": ["ross 308", "ross308"],
            "cobb": ["cobb 500", "cobb500"],
            "male": ["mâle", "coq", "mâles"],
            "female": ["femelle", "poule", "femelles"],
            "chick": ["poussin", "poussins", "young"],
        }

        variants = variants_map.get(entity.lower(), [])
        return any(variant in text.lower() for variant in variants)

    @staticmethod
    def _check_numeric_coherence(response: str) -> Dict[str, Any]:
        """
        Check coherence of numeric values in response.

        Verifies that numeric values are within reasonable ranges for
        poultry contexts:
        - Weights in kg should be < 10kg for chickens
        - Weights in g should be < 10,000g
        - Percentages should be <= 100%

        Args:
            response: The response text containing numeric values

        Returns:
            Dict with keys:
                - is_coherent (bool): True if all values are coherent
                - issues (List[str]): List of detected coherence issues

        Example:
            >>> result = TextAnalyzer._check_numeric_coherence("Le poulet pèse 15kg")
            >>> result['is_coherent']
            False
            >>> "trop élevé" in result['issues'][0]
            True
        """
        try:
            # Extract values with context
            weight_values = re.findall(
                r"(\d+[.,]?\d*)\s*(?:g|kg)", response, re.IGNORECASE
            )
            percentage_values = re.findall(
                r"(\d+[.,]?\d*)\s*%", response, re.IGNORECASE
            )

            issues = []
            is_coherent = True

            # Check weight values (order of magnitude validation)
            for weight_str in weight_values:
                try:
                    weight = float(weight_str.replace(",", "."))
                    if (
                        "kg" in response.lower() and weight > 10
                    ):  # Chicken weight > 10kg is suspect
                        issues.append(
                            f"Poids suspect: {weight}kg (trop élevé pour volaille)"
                        )
                        is_coherent = False
                    elif "g" in response.lower() and weight > 10000:  # > 10kg in grams
                        issues.append(f"Poids suspect: {weight}g (trop élevé)")
                        is_coherent = False
                except ValueError:
                    continue

            # Check percentages
            for pct_str in percentage_values:
                try:
                    pct = float(pct_str.replace(",", "."))
                    if pct > 100:
                        issues.append(f"Pourcentage invalide: {pct}%")
                        is_coherent = False
                except ValueError:
                    continue

            return {"is_coherent": is_coherent, "issues": issues}

        except Exception as e:
            logger.warning(f"Erreur vérification cohérence numérique: {e}")
            return {"is_coherent": True, "issues": []}

    @staticmethod
    def _extract_claim_context(claim: str, response: str) -> str:
        """
        Extract context around a claim in a response.

        Retrieves approximately 50 characters before and after the claim
        to provide contextual information for verification.

        Args:
            claim: The claim text to find
            response: The full response text

        Returns:
            str: Context string (±50 chars around claim), or original claim if not found

        Example:
            >>> response = "Les poulets Ross 308 atteignent un poids optimal de 2.5kg en 42 jours."
            >>> TextAnalyzer._extract_claim_context("poids optimal", response)
            'Ross 308 atteignent un poids optimal de 2.5kg en 42 jours'
        """
        try:
            claim_pos = response.lower().find(claim.lower())
            if claim_pos == -1:
                return claim

            # Extract context of ±50 characters
            start = max(0, claim_pos - 50)
            end = min(len(response), claim_pos + len(claim) + 50)

            return response[start:end]

        except Exception:
            return claim

    @staticmethod
    def _extract_comparison_elements(claim: str) -> List[str]:
        """
        Extract elements from a comparative claim.

        Identifies and extracts the elements being compared in French
        comparative constructions like "plus...que", "supérieur à", etc.

        Args:
            claim: The comparative claim text

        Returns:
            List[str]: List of extracted comparison elements (trimmed strings)

        Example:
            >>> TextAnalyzer._extract_comparison_elements("Ross est plus performant que Cobb")
            ['Ross', 'performant', 'Cobb']
            >>> TextAnalyzer._extract_comparison_elements("FCR supérieur à 1.8")
            ['FCR', '1.8']
        """
        try:
            # Patterns to extract compared elements
            patterns = [
                r"(\w+)\s+(?:plus|moins)\s+(\w+)\s+que\s+(\w+)",
                r"(\w+)\s+(?:supérieur|inférieur)\s+à\s+(\w+)",
                r"(\w+)\s+(?:mieux|pire)\s+que\s+(\w+)",
            ]

            elements = []
            for pattern in patterns:
                matches = re.findall(pattern, claim, re.IGNORECASE)
                for match in matches:
                    elements.extend(match)

            return [elem.strip() for elem in elements if elem.strip()]

        except Exception:
            return []

    @staticmethod
    def _extract_key_elements(text: str) -> List[str]:
        """
        Extract key elements from text (numbers, technical terms, etc.).

        Identifies important elements for text analysis:
        - Numbers with units (g, kg, %, j, °C, kcal)
        - Technical poultry terms from domain keywords
        - Genetic line names (Ross, Cobb, Hubbard, ISA)

        Args:
            text: The text to analyze

        Returns:
            List[str]: List of key elements found in the text

        Example:
            >>> elements = TextAnalyzer._extract_key_elements("Ross 308 atteint 2.5kg en 42j avec FCR de 1.65")
            >>> "ross 308" in [e.lower() for e in elements]
            True
            >>> any("2.5" in e for e in elements)
            True
        """
        key_elements = []

        # Numbers with units
        numbers = re.findall(
            r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)", text, re.IGNORECASE
        )
        key_elements.extend(numbers)

        # Technical poultry terms
        for category_terms in TextAnalyzer.DOMAIN_KEYWORDS.values():
            for term in category_terms:
                if term.lower() in text.lower():
                    key_elements.append(term)

        # Genetic lines
        genetic_lines = re.findall(
            r"(?:ross|cobb|hubbard|isa)\s*\d*", text, re.IGNORECASE
        )
        key_elements.extend(genetic_lines)

        return key_elements
