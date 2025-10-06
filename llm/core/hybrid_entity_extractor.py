# -*- coding: utf-8 -*-
"""
hybrid_entity_extractor.py - Multi-tier Entity Extraction System
Phase 1: Health Entities (Critical Priority)

Architecture:
- Tier 1: Regex (numeric entities - fast, deterministic)
- Tier 2: Keyword Matching (simple entities - medium)
- Tier 3: LLM NER (complex entities - comprehensive)
"""

import re
import logging
import os
import json
from typing import Dict, Any
import structlog

logger = logging.getLogger(__name__)
structured_logger = structlog.get_logger()


# ============================================================================
# TIER 1: REGEX EXTRACTORS (Numeric Entities)
# ============================================================================


class RegexNumericExtractor:
    """Extract numeric entities with units using regex patterns"""

    def __init__(self):
        # Temperature patterns
        self.temperature_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:°C|°F|degré|degree|celsius|fahrenheit)s?",
            re.IGNORECASE
        )

        # Humidity patterns
        self.humidity_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:HR|RH|humidité|humidite|humidity)?",
            re.IGNORECASE
        )

        # Mortality rate patterns
        self.mortality_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:mortalité|mortalite|mortality|mort|death)",
            re.IGNORECASE
        )

        # Weight patterns
        self.weight_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:kg|g|grammes?|kilogrammes?|lb|pounds?)\b",
            re.IGNORECASE
        )

        # FCR patterns
        self.fcr_regex = re.compile(
            r"(?:FCR|IC|indice)\s*(?:de|of)?\s*(?:conversion)?\s*(?::)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE
        )

        # Hatchability patterns
        self.hatchability_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:éclosion|eclosion|hatch|hatchability)",
            re.IGNORECASE
        )

        # Fertility patterns
        self.fertility_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:fertilité|fertilite|fertility|fertile)",
            re.IGNORECASE
        )

        # Nutrient value patterns
        self.nutrient_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:%|kcal/kg|g/kg|ppm)\s*(?:PB|CP|protéine|protein|lysine|méthionine|methionine|calcium|phosphore|phosphorus)",
            re.IGNORECASE
        )

        # Feed intake patterns
        self.feed_intake_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:g|kg|grammes?|kilogrammes?)/(?:jour|day|j|d)\b",
            re.IGNORECASE
        )

        # Farm size patterns
        self.farm_size_regex = re.compile(
            r"(\d+[\s,]*\d*)\s*(?:poulets|oiseaux|sujets|birds|chickens|places?)",
            re.IGNORECASE
        )

        logger.info("✅ RegexNumericExtractor initialized")

    def extract(self, query: str) -> Dict[str, Any]:
        """Extract all numeric entities from query"""

        entities = {}

        # Temperature
        temp_match = self.temperature_regex.search(query)
        if temp_match:
            value = float(temp_match.group(1).replace(',', '.'))
            entities["temperature"] = {
                "value": value,
                "unit": "celsius",  # Default, can parse from match if needed
                "raw": temp_match.group(0)
            }

        # Humidity
        humidity_match = self.humidity_regex.search(query)
        if humidity_match:
            value = float(humidity_match.group(1).replace(',', '.'))
            entities["humidity"] = {
                "value": value,
                "unit": "percent",
                "raw": humidity_match.group(0)
            }

        # Mortality rate
        mortality_match = self.mortality_regex.search(query)
        if mortality_match:
            value = float(mortality_match.group(1).replace(',', '.'))
            entities["mortality_rate"] = {
                "value": value,
                "unit": "percent",
                "raw": mortality_match.group(0)
            }

        # Weight
        weight_match = self.weight_regex.search(query)
        if weight_match:
            value = float(weight_match.group(1).replace(',', '.'))
            entities["target_weight"] = {
                "value": value,
                "unit": "kg",  # Simplified, can parse unit
                "raw": weight_match.group(0)
            }

        # FCR
        fcr_match = self.fcr_regex.search(query)
        if fcr_match:
            value = float(fcr_match.group(1).replace(',', '.'))
            entities["target_fcr"] = {
                "value": value,
                "unit": "ratio",
                "raw": fcr_match.group(0)
            }

        # Hatchability
        hatch_match = self.hatchability_regex.search(query)
        if hatch_match:
            value = float(hatch_match.group(1).replace(',', '.'))
            entities["hatchability"] = {
                "value": value,
                "unit": "percent",
                "raw": hatch_match.group(0)
            }

        # Fertility
        fert_match = self.fertility_regex.search(query)
        if fert_match:
            value = float(fert_match.group(1).replace(',', '.'))
            entities["fertility_rate"] = {
                "value": value,
                "unit": "percent",
                "raw": fert_match.group(0)
            }

        # Feed intake
        intake_match = self.feed_intake_regex.search(query)
        if intake_match:
            value = float(intake_match.group(1).replace(',', '.'))
            entities["feed_intake"] = {
                "value": value,
                "unit": "g_per_day",
                "raw": intake_match.group(0)
            }

        # Farm size
        size_match = self.farm_size_regex.search(query)
        if size_match:
            size_str = size_match.group(1).replace(',', '').replace(' ', '')
            entities["farm_size"] = {
                "value": int(size_str),
                "unit": "birds",
                "raw": size_match.group(0)
            }

        return entities


# ============================================================================
# TIER 2: KEYWORD EXTRACTORS (Simple Entities)
# ============================================================================


class KeywordExtractor:
    """Extract simple entities using keyword matching"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.keywords = self._load_keywords()
        logger.info("✅ KeywordExtractor initialized")

    def _load_keywords(self) -> Dict:
        """Load keyword patterns for different entity types"""

        keywords = {
            "production_phase": {
                "fr": {
                    "starter": ["démarrage", "starter", "0-10j", "phase 1"],
                    "grower": ["croissance", "grower", "10-24j", "phase 2"],
                    "finisher": ["finition", "finisher", "24j+", "phase 3"],
                    "laying": ["ponte", "laying", "production"]
                },
                "en": {
                    "starter": ["starter", "start", "0-10d", "phase 1"],
                    "grower": ["grower", "growth", "10-24d", "phase 2"],
                    "finisher": ["finisher", "finish", "24d+", "phase 3"],
                    "laying": ["laying", "lay", "production"]
                }
            },
            "housing_type": {
                "fr": ["sol", "cages", "volière", "plein air", "free range", "cage"],
                "en": ["floor", "cage", "aviary", "free range", "barn"]
            },
            "bedding_type": {
                "fr": ["paille", "copeaux", "litière", "sciure"],
                "en": ["straw", "shavings", "wood shavings", "sawdust", "litter"]
            },
            "ventilation_mode": {
                "fr": ["tunnel", "statique", "dynamique", "minimum", "ventilation"],
                "en": ["tunnel", "static", "dynamic", "minimum", "ventilation"]
            }
        }

        return keywords

    def extract(self, query: str, language: str = "fr") -> Dict[str, Any]:
        """Extract keyword-based entities"""

        entities = {}
        query_lower = query.lower()

        # Production phase
        phase_keywords = self.keywords.get("production_phase", {}).get(language, {})
        for phase, keywords in phase_keywords.items():
            if any(kw in query_lower for kw in keywords):
                entities["production_phase"] = phase
                break

        # Housing type
        housing_keywords = self.keywords.get("housing_type", {}).get(language, [])
        for housing in housing_keywords:
            if housing in query_lower:
                entities["housing_type"] = housing
                break

        # Bedding type
        bedding_keywords = self.keywords.get("bedding_type", {}).get(language, [])
        for bedding in bedding_keywords:
            if bedding in query_lower:
                entities["bedding_type"] = bedding
                break

        # Ventilation mode
        vent_keywords = self.keywords.get("ventilation_mode", {}).get(language, [])
        for vent in vent_keywords:
            if vent in query_lower:
                entities["ventilation_mode"] = vent
                break

        return entities


# ============================================================================
# TIER 3: LLM NER EXTRACTOR (Complex Entities)
# ============================================================================


class LLMNERExtractor:
    """Extract complex entities using LLM-based Named Entity Recognition"""

    def __init__(self):
        # Check for OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY not found - LLM NER will be disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ LLMNERExtractor initialized")

        # Entity schemas by domain
        self.entity_schemas = {
            "health": {
                "disease_name": "Disease names (e.g., coccidiosis, gumboro, newcastle, colibacillosis)",
                "symptom": "Symptoms (e.g., diarrhea, lameness, bloody feces, respiratory issues)",
                "pathogen": "Pathogens (e.g., E. coli, Eimeria, Newcastle virus, Salmonella)",
                "clinical_sign": "Clinical signs (e.g., lesions, blood in feces, swelling, pale combs)",
                "treatment_type": "Treatment types (e.g., antibiotic, anticoccidial, antiparasitic)",
                "medication": "Medication names (e.g., amprolium, salinomycin, enrofloxacin)",
                "vaccine_name": "Vaccine names (e.g., Gumboro, Newcastle, Bronchitis)",
                "vaccination_route": "Vaccination routes (e.g., spray, drinking water, injection, in ovo)"
            },
            "nutrition": {
                "nutrient": "Nutrients (e.g., protein, lysine, methionine, calcium, phosphorus)",
                "ingredient": "Feed ingredients (e.g., corn, soybean, wheat, fish meal)",
                "additive": "Feed additives (e.g., enzyme, probiotic, organic acid, coccidiostat)",
                "feed_form": "Feed forms (e.g., mash, crumbles, pellets)"
            },
            "environment": {
                "ammonia_level": "Ammonia levels (e.g., NH3 25 ppm, ammonia 10 ppm)",
                "co2_level": "CO2 levels (e.g., CO2 3000 ppm)"
            }
        }

    def extract(
        self,
        query: str,
        language: str,
        domain: str,
        existing_entities: Dict = None
    ) -> Dict[str, Any]:
        """
        Extract complex entities using GPT-4o-mini

        Args:
            query: User query
            language: Query language
            domain: Detected domain (health, nutrition, etc.)
            existing_entities: Entities already extracted by Tier 1 & 2

        Returns:
            Dict of extracted entities
        """

        if not self.enabled:
            logger.debug("LLM NER disabled (no API key)")
            return {}

        # Get entity schema for domain
        schema = self.entity_schemas.get(domain)
        if not schema:
            logger.debug(f"No LLM NER schema for domain: {domain}")
            return {}

        try:
            import openai

            # Build prompt
            prompt = self._build_extraction_prompt(
                query, language, schema, existing_entities
            )

            # Call OpenAI
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=500
            )

            # Parse response
            entities = json.loads(response.choices[0].message.content)

            # Structured logging
            structured_logger.info(
                "llm_ner_extraction",
                domain=domain,
                entities_extracted=list(entities.keys()),
                entity_count=sum(len(v) if isinstance(v, list) else 1 for v in entities.values())
            )

            return entities

        except Exception as e:
            logger.error(f"LLM NER extraction failed: {e}", exc_info=True)
            structured_logger.error(
                "llm_ner_extraction_failed",
                domain=domain,
                error=str(e)
            )
            return {}

    def _build_extraction_prompt(
        self,
        query: str,
        language: str,
        schema: Dict,
        existing_entities: Dict
    ) -> str:
        """Build extraction prompt for LLM"""

        entity_descriptions = "\n".join(
            f"- {entity_type}: {description}"
            for entity_type, description in schema.items()
        )

        prompt = f"""Extract poultry domain entities from this query.

Query (in {language}): "{query}"

Already extracted entities (DO NOT extract these again):
{json.dumps(existing_entities or {}, indent=2)}

Extract ONLY these entity types:
{entity_descriptions}

Return ONLY new entities not already extracted, in JSON format:
{{
  "entity_type": ["value1", "value2"],
  ...
}}

If a value is numeric (e.g., "25 ppm"), extract just the text value "25 ppm".
If no new entities found, return empty object: {{}}
"""

        return prompt


# ============================================================================
# HYBRID ENTITY EXTRACTOR (Main Class)
# ============================================================================


class HybridEntityExtractor:
    """
    Multi-tier entity extraction system

    Tier 1: Regex (numeric entities - fast, cheap, deterministic)
    Tier 2: Keywords (simple entities - medium speed, zero cost)
    Tier 3: LLM NER (complex entities - slow, costs $0.00015/query)
    """

    def __init__(self, config_dir: str = "config"):
        self.regex_extractor = RegexNumericExtractor()
        self.keyword_extractor = KeywordExtractor(config_dir)
        self.llm_extractor = LLMNERExtractor()

        # Configuration thresholds
        self.llm_enabled_domains = ["health", "nutrition", "environment"]
        self.min_query_length_for_llm = 10  # words

        logger.info("✅ HybridEntityExtractor initialized")

    def extract_all(
        self,
        query: str,
        language: str = "fr",
        domain: str = None,
        existing_entities: Dict = None
    ) -> Dict[str, Any]:
        """
        Extract all entities using tiered approach

        Args:
            query: User query
            language: Query language
            domain: Detected domain (optional, improves LLM targeting)
            existing_entities: Entities already extracted (e.g., by query_router)

        Returns:
            Dict of all extracted entities
        """

        all_entities = existing_entities.copy() if existing_entities else {}

        # TIER 1: Regex extraction (always run - fast)
        regex_entities = self.regex_extractor.extract(query)
        all_entities.update(regex_entities)

        # TIER 2: Keyword extraction (always run - fast)
        keyword_entities = self.keyword_extractor.extract(query, language)
        all_entities.update(keyword_entities)

        # TIER 3: LLM NER (conditional - expensive)
        should_use_llm = self._should_use_llm(query, domain, all_entities)

        if should_use_llm:
            llm_entities = self.llm_extractor.extract(
                query, language, domain, existing_entities=all_entities
            )

            # Merge (don't override existing entities)
            for key, value in llm_entities.items():
                if key not in all_entities or not all_entities[key]:
                    all_entities[key] = value

        # Structured logging
        structured_logger.info(
            "hybrid_extraction_completed",
            total_entities=len(all_entities),
            regex_count=len(regex_entities),
            keyword_count=len(keyword_entities),
            llm_used=should_use_llm,
            domain=domain
        )

        return all_entities

    def _should_use_llm(
        self,
        query: str,
        domain: str,
        extracted_entities: Dict
    ) -> bool:
        """
        Decide whether to use expensive LLM NER

        Triggers:
        - Domain is health, nutrition, or environment (high value)
        - Query is complex (> 10 words)
        - Few entities extracted so far (< 2)
        """

        # Check domain
        if domain not in self.llm_enabled_domains:
            return False

        # Check query complexity
        word_count = len(query.split())
        if word_count < self.min_query_length_for_llm:
            return False

        # Check if we already have enough entities
        if len(extracted_entities) >= 3:
            return False

        return True


# ============================================================================
# FACTORY
# ============================================================================


def create_hybrid_extractor(config_dir: str = "config") -> HybridEntityExtractor:
    """Factory to create HybridEntityExtractor instance"""
    return HybridEntityExtractor(config_dir)
