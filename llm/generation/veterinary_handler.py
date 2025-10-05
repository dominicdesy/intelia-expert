# -*- coding: utf-8 -*-
"""
veterinary_handler.py - Veterinary query detection and disclaimer management
Extracted from generators.py for better modularity and maintainability
"""

import logging
from typing import List, Dict, Union

# Import message handler for veterinary disclaimers
try:
    from config.messages import get_message

    MESSAGES_AVAILABLE = True
except ImportError:
    MESSAGES_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# LOAD VETERINARY TERMS FROM CENTRALIZED CONFIG
# ============================================================================


def _load_veterinary_keywords():
    """
    Load veterinary keywords from centralized JSON configuration.

    Returns:
        List of all veterinary keywords (flattened from all categories and languages)
    """
    try:
        import os
        import json

        VETERINARY_TERMS_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
            "veterinary_terms.json",
        )

        with open(VETERINARY_TERMS_PATH, "r", encoding="utf-8") as f:
            vet_terms_data = json.load(f)

        # Flatten all terms into single list for detection
        keywords = []

        # Extract metadata
        metadata = vet_terms_data.get("metadata", {})
        total_expected = metadata.get("total_terms", 0)

        # Extract all categories (diseases, symptoms, treatments, etc.)
        for category_name, category_data in vet_terms_data.items():
            if category_name == "metadata":
                continue

            # Each category has language keys (fr, en, de, etc.)
            if isinstance(category_data, dict):
                for lang_code, terms_list in category_data.items():
                    if isinstance(terms_list, list):
                        keywords.extend(terms_list)

        # Remove duplicates and convert to lowercase for matching
        keywords = list(set([kw.lower() for kw in keywords]))

        logger.info(
            f"✅ Loaded {len(keywords)} veterinary terms from config "
            f"(expected: {total_expected}, unique: {len(keywords)})"
        )

        return keywords

    except FileNotFoundError:
        logger.error(
            f"❌ veterinary_terms.json not found at {VETERINARY_TERMS_PATH}, "
            f"using minimal fallback"
        )
        return _get_fallback_keywords()
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse veterinary_terms.json: {e}, using fallback")
        return _get_fallback_keywords()
    except Exception as e:
        logger.error(f"❌ Error loading veterinary_terms.json: {e}, using fallback")
        return _get_fallback_keywords()


def _get_fallback_keywords():
    """
    Minimal fallback keywords if config file cannot be loaded.

    Returns:
        List of essential veterinary keywords
    """
    logger.warning("⚠️ Using minimal fallback veterinary keywords")
    return [
        # Critical terms only
        "disease",
        "maladie",
        "sick",
        "malade",
        "treatment",
        "traitement",
        "antibiotic",
        "antibiotique",
        "vaccine",
        "vaccin",
        "mortality",
        "mortalité",
        "symptom",
        "symptôme",
        "infection",
        "virus",
        "bacteria",
        "bactérie",
        "parasite",
        "diagnostic",
        "diagnosis",
    ]


# Load keywords at module level (executed once at import)
VETERINARY_KEYWORDS = _load_veterinary_keywords()


class VeterinaryHandler:
    """
    Handler for veterinary-related queries and disclaimers.

    This class provides methods to:
    - Detect whether a query is veterinary-related
    - Retrieve appropriate disclaimers in multiple languages
    """

    @staticmethod
    def is_veterinary_query(query: str, context_docs: List) -> bool:
        """
        Detects if the question concerns a veterinary topic.

        This method analyzes both the user's query and the retrieved context documents
        to determine if the question is veterinary-related and requires a disclaimer.

        Args:
            query: User's question
            context_docs: Retrieved context documents (can be Document objects or dicts)

        Returns:
            True if this is a veterinary question requiring a disclaimer, False otherwise

        Examples:
            >>> VeterinaryHandler.is_veterinary_query("My chickens are sick", [])
            True
            >>> VeterinaryHandler.is_veterinary_query("What is the target weight?", [])
            False
        """
        query_lower = query.lower()

        # Use centralized veterinary keywords from config
        # (loaded from config/veterinary_terms.json)
        veterinary_keywords = VETERINARY_KEYWORDS

        # Check in the query
        has_vet_keywords = any(
            keyword in query_lower for keyword in veterinary_keywords
        )

        # If no keywords in the query, check in the documents
        if not has_vet_keywords and context_docs:
            try:
                # Examine the first 3 documents (500 chars each)
                doc_content = " ".join(
                    [
                        str(VeterinaryHandler._get_doc_content(doc))[:500]
                        for doc in context_docs[:3]
                    ]
                ).lower()

                # Check presence of veterinary terms in the docs
                has_vet_content = any(
                    keyword in doc_content
                    for keyword in veterinary_keywords[:20]  # Top 20 keywords
                )
            except Exception as e:
                logger.debug(f"Error checking veterinary content: {e}")
                has_vet_content = False
        else:
            has_vet_content = False

        result = has_vet_keywords or has_vet_content

        if result:
            logger.info(f"🏥 Veterinary question detected: '{query[:50]}...'")

        return result

    @staticmethod
    def get_veterinary_disclaimer(language: str = "fr") -> str:
        """
        Returns the veterinary disclaimer from languages.json.

        This method retrieves the appropriate disclaimer message based on the
        specified language, with fallback to English if the language is not available.

        Args:
            language: Language code (fr, en, es, de, it, pt, nl, pl, hi, id, th, zh)

        Returns:
            Disclaimer text with line break, or empty string if not available

        Examples:
            >>> VeterinaryHandler.get_veterinary_disclaimer("fr")
            '\\n\\n**Important**: Ces informations sont fournies à titre éducatif...'
            >>> VeterinaryHandler.get_veterinary_disclaimer("en")
            '\\n\\n**Important**: This information is provided for educational purposes...'
        """
        if not MESSAGES_AVAILABLE:
            logger.warning("⚠️ Messages not available, no veterinary disclaimer")
            return ""

        try:
            disclaimer = get_message("veterinary_disclaimer", language)
            # Add double line break before the disclaimer
            return f"\n\n{disclaimer}"
        except Exception as e:
            logger.warning(
                f"⚠️ Error retrieving veterinary_disclaimer for {language}: {e}"
            )
            # Minimal fallback in English
            return "\n\n**Important**: This information is provided for educational purposes. For health concerns, consult a qualified veterinarian."

    @staticmethod
    def _get_doc_content(doc: Union[Dict, object]) -> str:
        """
        Extracts content from a document (dict or Document object).

        Internal helper method to handle both dict and object representations
        of documents uniformly.

        Args:
            doc: Document (object or dict)

        Returns:
            Document content as string
        """
        if isinstance(doc, dict):
            content = doc.get("content", "")
            if not content:
                logger.warning(
                    f"⚠️ Document dict with empty content: {doc.get('metadata', {})}"
                )
            return content
        return getattr(doc, "content", "")
