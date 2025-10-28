"""
Aviculture Domain Configuration

This module provides domain-specific configuration for the LLM service
when handling aviculture/poultry-related queries.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AvicultureConfig:
    """
    Aviculture-specific configuration for LLM service

    Phase 1: Embedded configuration for aviculture domain
    Phase 2+: Template for multi-domain plugin architecture
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize aviculture configuration

        Args:
            config_dir: Path to config directory (defaults to this file's directory)
        """
        if config_dir is None:
            config_dir = Path(__file__).parent

        self.config_dir = config_dir
        self.domain = "aviculture"

        # Load configuration files
        self.system_prompts = self._load_json("system_prompts.json")
        self.terminology = self._load_json("poultry_terminology.json")
        self.value_chain_terminology = self._load_json("value_chain_terminology.json")
        self.veterinary_terms = self._load_json("veterinary_terms.json")
        self.languages = self._load_json("languages.json")

        # Aviculture-specific breed keywords
        self.breed_keywords = [
            "ross", "cobb", "hubbard", "isa", "lohmann", "hy-line",
            "aviagen", "novogen", "dekalb", "shaver", "bovans",
        ]

        # Layer-specific breeds
        self.layer_breeds = [
            "hy-line", "lohmann", "isa brown", "dekalb", "shaver",
            "hisex", "bovans", "hendrix", "novogen",
        ]

        # Domain-specific metrics (extended)
        self.metric_keywords = [
            "weight", "poids", "fcr", "feed conversion", "indice de conversion",
            "egg production", "ponte", "mortality", "mortalité",
            "haugh unit", "shell strength", "breast yield", "carcass yield",
            "hatchability", "hen-day", "laying persistency",
        ]

        # Hatchery keywords
        self.hatchery_keywords = [
            "hatchery", "incubation", "incubateur", "setter", "hatcher",
            "candling", "mirage", "egg storage", "hatchability", "éclosabilité",
            "embryo", "pip", "chick quality", "breakout", "fumigation",
        ]

        # Processing keywords
        self.processing_keywords = [
            "processing", "slaughter", "abattage", "stunning", "étourdissement",
            "evisceration", "scalding", "carcass yield", "breast yield",
            "meat quality", "pH", "drip loss", "woody breast", "white striping",
            "chilling", "deboning", "haccp",
        ]

        # Layer production keywords
        self.layer_keywords = [
            "layer", "pondeuse", "egg", "œuf", "laying", "ponte",
            "haugh unit", "shell strength", "yolk color", "hen-day",
            "point of lay", "peak production", "molt", "mue",
            "egg weight", "persistency",
        ]

        # Breeding & genetics keywords
        self.breeding_keywords = [
            "breeding", "génétique", "heritability", "héritabilité",
            "selection", "sélection", "crossbreeding", "hybrid", "heterosis",
            "breeding value", "genetic gain", "genomic selection",
            "inbreeding", "pedigree", "progeny test",
        ]

        # Aviculture-specific keywords (from llm_router) - extended
        self.aviculture_keywords = [
            "poulet", "poule", "pondeuse", "broiler", "poussin", "volaille",
            "aviculture", "élevage", "mortalité", "ponte", "aliment", "eau",
            "nutrition", "santé", "maladie", "vaccin", "température", "ventilation",
            # Hatchery terms
            "incubation", "hatchery", "couvoir", "éclosion",
            # Processing terms
            "abattage", "processing", "rendement", "yield",
            # Layer terms
            "œuf", "egg", "coquille", "shell",
            # Breeding terms
            "génétique", "sélection", "breeding",
        ]

        logger.info(f"Aviculture configuration loaded from {config_dir}")

    def _load_json(self, filename: str) -> Dict:
        """Load JSON configuration file"""
        file_path = self.config_dir / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return {}

    def get_system_prompt(self, query_type: str = "general_poultry", language: str = "en") -> str:
        """
        Get system prompt for a specific query type

        Args:
            query_type: Type of query (general_poultry, nutrition_query, health_diagnosis, etc.)
            language: Response language code (fr, en, es, etc.)

        Returns:
            Formatted system prompt with language directive
        """
        # Get base prompts
        expert_identity = self.system_prompts.get("base_prompts", {}).get("expert_identity", "")
        response_guidelines = self.system_prompts.get("base_prompts", {}).get("response_guidelines", "")

        # Get specialized prompt
        specialized = self.system_prompts.get("specialized_prompts", {}).get(
            query_type,
            self.system_prompts.get("specialized_prompts", {}).get("general_poultry", "")
        )

        # Combine prompts
        full_prompt = f"{expert_identity}\n\n{response_guidelines}\n\n{specialized}"

        # Format with language name
        language_names = {
            "fr": "French", "en": "English", "es": "Spanish",
            "de": "German", "it": "Italian", "pt": "Portuguese",
            "ar": "Arabic", "zh": "Chinese", "ja": "Japanese",
            "ko": "Korean", "th": "Thai", "vi": "Vietnamese"
        }
        language_name = language_names.get(language, "English")

        return full_prompt.format(language_name=language_name)

    def get_formatting_rules(self) -> List[str]:
        """
        Get response formatting rules for this domain

        Returns:
            List of formatting rule identifiers
        """
        return [
            "remove_markdown_headers",
            "add_veterinary_disclaimer",
            "use_metric_units",
            "remove_source_mentions",
            "clean_verbatim_copying"
        ]

    def get_requirements(self) -> Dict[str, str]:
        """
        Get domain-specific requirements for LLM generation

        Returns:
            Dictionary of requirement levels
        """
        return {
            "factuality": "high",  # Aviculture requires precise technical data
            "cost_sensitivity": "medium",  # Balance cost vs quality
            "latency_tolerance": "low",  # Users expect fast responses
            "max_tokens_default": 1500,  # Technical responses can be detailed
            "temperature": 0.7,  # Balanced creativity/precision
        }

    def is_domain_query(self, query: str, intent_result: Optional[Dict] = None) -> bool:
        """
        Check if query belongs to aviculture domain

        Args:
            query: User query text
            intent_result: Optional intent classification result

        Returns:
            True if query is aviculture-related
        """
        query_lower = query.lower()

        # Check for breed names (strong indicator)
        if any(breed in query_lower for breed in self.breed_keywords):
            logger.debug(f"🐔 Breed name detected in query → aviculture")
            return True

        # Check for performance metrics with age indicators
        has_metric = any(metric in query_lower for metric in self.metric_keywords)
        has_age = any(age_term in query_lower for age_term in ["day", "days", "week", "weeks", "jours", "jour", "semaine"])
        if has_metric and has_age:
            logger.debug(f"🐔 Metric + age detected in query → aviculture")
            return True

        # Check aviculture keywords
        if any(keyword in query_lower for keyword in self.aviculture_keywords):
            logger.debug(f"🐔 Aviculture keyword detected")
            return True

        # Check domain from intent result
        if intent_result:
            domain = intent_result.get("domain", "")
            intent_type = intent_result.get("intent", "")

            if domain in ["aviculture", "poultry", "livestock", "genetics_performance",
                         "nutrition", "health", "housing"]:
                logger.debug(f"🐔 Domain '{domain}' detected → aviculture")
                return True

            if intent_type in ["performance_query", "genetics_query", "nutrition_query", "health_query"]:
                logger.debug(f"🐔 Intent '{intent_type}' detected → aviculture")
                return True

        return False

    def get_provider_preferences(self) -> Dict[str, float]:
        """
        Get provider preferences for this domain

        Returns:
            Dictionary mapping provider names to preference scores (0-1)
        """
        return {
            "intelia_llama": 0.9,  # Preferred for aviculture
            "deepseek": 0.6,  # Good for simple queries
            "claude": 0.8,  # Good for complex synthesis
            "gpt4o": 0.7,  # Fallback
        }

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return self.system_prompts.get("metadata", {}).get("languages_supported", ["en", "fr"])

    def validate_query(self, query: str) -> Dict[str, any]:
        """
        Validate query and provide suggestions

        Args:
            query: User query text

        Returns:
            Validation result with suggestions
        """
        result = {
            "valid": True,
            "suggestions": [],
            "missing_info": []
        }

        # Check for minimum query length
        if len(query.strip()) < 5:
            result["valid"] = False
            result["suggestions"].append("Query is too short. Please provide more details.")

        # Check for breed mention in performance queries
        if any(metric in query.lower() for metric in self.metric_keywords):
            if not any(breed in query.lower() for breed in self.breed_keywords):
                result["missing_info"].append("breed")
                result["suggestions"].append(
                    "Consider specifying the breed (e.g., Ross 308, Cobb 500) for accurate performance data."
                )

        return result

    def get_message(self, message_type: str, language: str = "en") -> str:
        """
        Get system message in specified language

        Args:
            message_type: Type of message (e.g., "welcome", "error_generic")
            language: Language code (defaults to "en")

        Returns:
            Localized message string
        """
        messages = self.languages.get("messages", {})
        language_messages = messages.get(language, messages.get("en", {}))
        return language_messages.get(message_type, "")

    def get_veterinary_disclaimer(self, language: str = "en") -> str:
        """Get veterinary disclaimer in specified language"""
        return self.get_message("veterinary_disclaimer", language)

    def is_veterinary_query(self, query: str, language: str = "en") -> bool:
        """
        Detect if query contains veterinary terminology

        Args:
            query: User query text
            language: Query language

        Returns:
            True if query contains veterinary terms
        """
        query_lower = query.lower()

        # Get veterinary terms for language
        vet_terms = self.veterinary_terms

        # Check all veterinary categories
        for category in ["diseases", "symptoms", "treatments", "pathogens", "diagnosis",
                        "veterinary_questions", "health_issues"]:
            terms = vet_terms.get(category, {}).get(language, [])
            if any(term in query_lower for term in terms):
                return True

        return False

    def get_terminology_translation(self, term_key: str, language: str = "en") -> str:
        """
        Get terminology translation

        Args:
            term_key: Terminology key (e.g., "broiler", "feed_conversion_ratio")
            language: Target language code

        Returns:
            Translated term or empty string if not found
        """
        terminology = self.terminology.get("terminology", {})
        term_data = terminology.get(term_key, {})
        return term_data.get(language, "")


# Singleton instance for easy access
_aviculture_config = None

def get_aviculture_config() -> AvicultureConfig:
    """Get singleton instance of aviculture configuration"""
    global _aviculture_config
    if _aviculture_config is None:
        _aviculture_config = AvicultureConfig()
    return _aviculture_config
