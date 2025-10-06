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
            re.IGNORECASE,
        )

        # Humidity patterns
        self.humidity_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:HR|RH|humidité|humidite|humidity)?",
            re.IGNORECASE,
        )

        # Mortality rate patterns (supports both "5% mortalité" and "mortalité élevée : 5%")
        self.mortality_regex = re.compile(
            r"(?:(?:mortalité|mortalite|mortality|mort|death)\b.*?(\d+(?:[.,]\d+)?)\s*%)|(?:(\d+(?:[.,]\d+)?)\s*%\s*(?:mortalité|mortalite|mortality|mort|death))",
            re.IGNORECASE,
        )

        # Weight patterns
        self.weight_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:kg|g|grammes?|kilogrammes?|lb|pounds?)\b",
            re.IGNORECASE,
        )

        # FCR patterns (supports "FCR 1.65" and "FCR actuel 1.65")
        self.fcr_regex = re.compile(
            r"(?:FCR|IC|indice)\b.*?(\d+(?:[.,]\d+))", re.IGNORECASE
        )

        # Hatchability patterns
        self.hatchability_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:éclosion|eclosion|hatch|hatchability)",
            re.IGNORECASE,
        )

        # Fertility patterns
        self.fertility_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*%\s*(?:fertilité|fertilite|fertility|fertile)",
            re.IGNORECASE,
        )

        # Nutrient value patterns
        self.nutrient_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:%|kcal/kg|g/kg|ppm)\s*(?:PB|CP|protéine|protein|lysine|méthionine|methionine|calcium|phosphore|phosphorus)",
            re.IGNORECASE,
        )

        # Feed intake patterns
        self.feed_intake_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:g|kg|grammes?|kilogrammes?)/(?:jour|day|j|d)\b",
            re.IGNORECASE,
        )

        # Farm size patterns
        self.farm_size_regex = re.compile(
            r"(\d+[\s,]*\d*)\s*(?:poulets|oiseaux|sujets|birds|chickens|places?)",
            re.IGNORECASE,
        )

        # Carcass yield patterns
        self.carcass_yield_regex = re.compile(
            r"(?:rendement|yield|carcass)\s*(?:carcasse)?\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*%",
            re.IGNORECASE,
        )

        # Breast yield patterns
        self.breast_yield_regex = re.compile(
            r"(?:filet|breast|blanc)\s*(?:yield)?\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*%",
            re.IGNORECASE,
        )

        # Nutrient value patterns (protein, energy, etc.)
        self.nutrient_value_regex = re.compile(
            r"(\d+(?:[.,]\d+)?)\s*(?:%|kcal/kg|g/kg|ppm|mg/kg)\s*(?:PB|CP|protéine|protein|lysine|méthionine|methionine|calcium|phosphore|phosphorus|énergie|energy|EM|ME)",
            re.IGNORECASE,
        )

        # Lighting program patterns
        self.lighting_regex = re.compile(
            r"(\d+)\s*(?:L|light|lumière)\s*:\s*(\d+)\s*(?:D|dark|obscurité)|(\d+)\s*(?:heures|hours|h)\s*(?:de\s*)?(?:lumière|light)",
            re.IGNORECASE,
        )

        # Ammonia level patterns
        self.ammonia_regex = re.compile(
            r"(?:NH3|ammoniac|ammonia)\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*ppm",
            re.IGNORECASE,
        )

        # Age in weeks patterns (for slaughter age, etc.)
        self.age_weeks_regex = re.compile(
            r"(\d+)\s*(?:semaines|weeks|sem|wk|w)\b", re.IGNORECASE
        )

        # Cost patterns
        self.cost_regex = re.compile(
            r"(?:coût|cost|prix|price)\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*(?:€|EUR|€/kg|\$|USD|\$/lb|CAD)",
            re.IGNORECASE,
        )

        # Margin/profit patterns
        self.margin_regex = re.compile(
            r"(?:marge|margin|profit|bénéfice)\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*(?:%|€|\$)",
            re.IGNORECASE,
        )

        # ROI patterns
        self.roi_regex = re.compile(
            r"(?:ROI|retour)\s*(?:sur investissement)?\s*(?::)?\s*(\d+(?:[.,]\d+)?)\s*%",
            re.IGNORECASE,
        )

        logger.info("✅ RegexNumericExtractor initialized with Phase 2 entities")

    def extract(self, query: str) -> Dict[str, Any]:
        """Extract all numeric entities from query"""

        entities = {}

        # Temperature
        temp_match = self.temperature_regex.search(query)
        if temp_match:
            value = float(temp_match.group(1).replace(",", "."))
            entities["temperature"] = {
                "value": value,
                "unit": "celsius",  # Default, can parse from match if needed
                "raw": temp_match.group(0),
            }

        # Mortality rate (CHECK BEFORE HUMIDITY - more specific pattern)
        mortality_match = self.mortality_regex.search(query)
        if mortality_match:
            # Regex has two alternative patterns, so check which group matched
            value_str = mortality_match.group(1) or mortality_match.group(2)
            value = float(value_str.replace(",", "."))
            entities["mortality_rate"] = {
                "value": value,
                "unit": "percent",
                "raw": mortality_match.group(0),
            }

        # Humidity (CHECK AFTER MORTALITY to avoid conflicts)
        humidity_match = self.humidity_regex.search(query)
        if humidity_match:
            # Only skip if this is the same match as mortality
            is_same_match = (
                "mortality_rate" in entities
                and humidity_match.group(0) == entities["mortality_rate"]["raw"]
            )
            if not is_same_match:
                value = float(humidity_match.group(1).replace(",", "."))
                entities["humidity"] = {
                    "value": value,
                    "unit": "percent",
                    "raw": humidity_match.group(0),
                }

        # Weight
        weight_match = self.weight_regex.search(query)
        if weight_match:
            value = float(weight_match.group(1).replace(",", "."))
            entities["target_weight"] = {
                "value": value,
                "unit": "kg",  # Simplified, can parse unit
                "raw": weight_match.group(0),
            }

        # FCR
        fcr_match = self.fcr_regex.search(query)
        if fcr_match:
            value = float(fcr_match.group(1).replace(",", "."))
            entities["target_fcr"] = {
                "value": value,
                "unit": "ratio",
                "raw": fcr_match.group(0),
            }

        # Hatchability
        hatch_match = self.hatchability_regex.search(query)
        if hatch_match:
            value = float(hatch_match.group(1).replace(",", "."))
            entities["hatchability"] = {
                "value": value,
                "unit": "percent",
                "raw": hatch_match.group(0),
            }

        # Fertility
        fert_match = self.fertility_regex.search(query)
        if fert_match:
            value = float(fert_match.group(1).replace(",", "."))
            entities["fertility_rate"] = {
                "value": value,
                "unit": "percent",
                "raw": fert_match.group(0),
            }

        # Feed intake
        intake_match = self.feed_intake_regex.search(query)
        if intake_match:
            value = float(intake_match.group(1).replace(",", "."))
            entities["feed_intake"] = {
                "value": value,
                "unit": "g_per_day",
                "raw": intake_match.group(0),
            }

        # Farm size
        size_match = self.farm_size_regex.search(query)
        if size_match:
            size_str = size_match.group(1).replace(",", "").replace(" ", "")
            entities["farm_size"] = {
                "value": int(size_str),
                "unit": "birds",
                "raw": size_match.group(0),
            }

        # Carcass yield
        carcass_match = self.carcass_yield_regex.search(query)
        if carcass_match:
            value = float(carcass_match.group(1).replace(",", "."))
            entities["carcass_yield"] = {
                "value": value,
                "unit": "percent",
                "raw": carcass_match.group(0),
            }

        # Breast yield
        breast_match = self.breast_yield_regex.search(query)
        if breast_match:
            value = float(breast_match.group(1).replace(",", "."))
            entities["breast_yield"] = {
                "value": value,
                "unit": "percent",
                "raw": breast_match.group(0),
            }

        # Nutrient value
        nutrient_match = self.nutrient_value_regex.search(query)
        if nutrient_match:
            value = float(nutrient_match.group(1).replace(",", "."))
            entities["nutrient_value"] = {
                "value": value,
                "raw": nutrient_match.group(0),
            }

        # Lighting program
        lighting_match = self.lighting_regex.search(query)
        if lighting_match:
            if lighting_match.group(1) and lighting_match.group(2):
                # Format: "16L:8D"
                light_hours = int(lighting_match.group(1))
                dark_hours = int(lighting_match.group(2))
                entities["lighting_program"] = {
                    "light_hours": light_hours,
                    "dark_hours": dark_hours,
                    "format": f"{light_hours}L:{dark_hours}D",
                    "raw": lighting_match.group(0),
                }
            elif lighting_match.group(3):
                # Format: "16 heures de lumière"
                light_hours = int(lighting_match.group(3))
                entities["lighting_program"] = {
                    "light_hours": light_hours,
                    "dark_hours": 24 - light_hours,
                    "format": f"{light_hours}L:{24-light_hours}D",
                    "raw": lighting_match.group(0),
                }

        # Ammonia level
        ammonia_match = self.ammonia_regex.search(query)
        if ammonia_match:
            value = float(ammonia_match.group(1).replace(",", "."))
            entities["ammonia_level"] = {
                "value": value,
                "unit": "ppm",
                "raw": ammonia_match.group(0),
            }

        # Cost
        cost_match = self.cost_regex.search(query)
        if cost_match:
            value = float(cost_match.group(1).replace(",", "."))
            entities["cost"] = {"value": value, "raw": cost_match.group(0)}

        # Margin
        margin_match = self.margin_regex.search(query)
        if margin_match:
            value = float(margin_match.group(1).replace(",", "."))
            entities["margin"] = {"value": value, "raw": margin_match.group(0)}

        # ROI
        roi_match = self.roi_regex.search(query)
        if roi_match:
            value = float(roi_match.group(1).replace(",", "."))
            entities["roi"] = {
                "value": value,
                "unit": "percent",
                "raw": roi_match.group(0),
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
                    "laying": ["ponte", "laying", "production"],
                },
                "en": {
                    "starter": ["starter", "start", "0-10d", "phase 1"],
                    "grower": ["grower", "growth", "10-24d", "phase 2"],
                    "finisher": ["finisher", "finish", "24d+", "phase 3"],
                    "laying": ["laying", "lay", "production"],
                },
            },
            "housing_type": {
                "fr": ["sol", "cages", "volière", "plein air", "free range", "cage"],
                "en": ["floor", "cage", "aviary", "free range", "barn"],
            },
            "bedding_type": {
                "fr": ["paille", "copeaux", "litière", "sciure"],
                "en": ["straw", "shavings", "wood shavings", "sawdust", "litter"],
            },
            "ventilation_mode": {
                "fr": ["tunnel", "statique", "dynamique", "minimum", "ventilation"],
                "en": ["tunnel", "static", "dynamic", "minimum", "ventilation"],
            },
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
                "vaccination_route": "Vaccination routes (e.g., spray, drinking water, injection, in ovo)",
            },
            "nutrition": {
                "nutrient": "Nutrients (e.g., protein, lysine, methionine, calcium, phosphorus, energy)",
                "ingredient": "Feed ingredients (e.g., corn, soybean meal, wheat, fish meal, rapeseed)",
                "additive": "Feed additives (e.g., enzyme, probiotic, organic acid, coccidiostat, vitamin premix)",
                "feed_form": "Feed forms (e.g., mash, crumbles, pellets, meal)",
            },
            "environment": {
                "co2_level": "CO2 levels (e.g., CO2 3000 ppm, carbon dioxide 2500 ppm)"
            },
            "hatchery": {
                "incubation_day": "Incubation days (e.g., E18, day 18, transfer day 18, J18)",
                "egg_type": "Egg types (e.g., hatching egg, fertile egg, breeder egg)",
                "chick_quality": "Chick quality indicators (e.g., quality A, grade 1, Tona score 95)",
                "sexing_method": "Sexing methods (e.g., mechanical sexing, vent sexing, feather sexing, in-ovo)",
                "incubator_type": "Incubator types (e.g., setter, hatcher, multi-stage, single-stage)",
            },
            "processing": {
                "slaughter_age": "Slaughter age references (e.g., processing age 42 days, slaughter at 6 weeks)",
                "live_weight": "Live weight at processing (e.g., live weight 2.5 kg, body weight 2800g)",
                "meat_quality": "Meat quality indicators (e.g., PSE, DFD, pH 5.8, quality A)",
                "stunning_method": "Stunning methods (e.g., electrical stunning, gas stunning, controlled atmosphere)",
            },
            "economics": {
                "contract_type": "Contract types (e.g., integration, independent, contract farming)",
                "payment_term": "Payment terms (e.g., net 30, net 60, upon delivery, 30 days)",
            },
            "temporal": {
                "time_period": "Time periods (e.g., last 7 days, past week, yesterday, this month)",
                "trend_direction": "Trend directions (e.g., increasing, decreasing, stable, rising, falling)",
                "comparison_operator": "Comparison operators (e.g., higher than, lower than, versus, compared to)",
                "date": "Dates (e.g., January 15, 2025-01-15, last Monday, next week)",
                "season": "Seasons (e.g., summer, winter, hot season, cold period)",
                "duration": "Durations (e.g., for 3 days, over 2 weeks, during 5 days)",
            },
            "geographic": {
                "region": "Regions (e.g., Quebec, Brittany, Midwest, Southeast Asia)",
                "country": "Countries (e.g., France, USA, Brazil, Thailand, China)",
                "climate_zone": "Climate zones (e.g., tropical, temperate, continental, hot humid)",
                "altitude": "Altitude references (e.g., altitude 500m, 1000m above sea level, high altitude)",
            },
            "regulatory": {
                "certification": "Certifications (e.g., Label Rouge, organic, halal, kosher, GlobalGAP)",
                "standard": "Standards (e.g., HACCP, ISO 22000, EU regulation, FDA approved)",
                "welfare_label": "Welfare labels (e.g., animal welfare approved, free range certified)",
                "regulation": "Regulations (e.g., EU directive, FDA regulation, French norm)",
            },
        }

    def extract(
        self, query: str, language: str, domain: str, existing_entities: Dict = None
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
                max_tokens=500,
            )

            # Parse response
            entities = json.loads(response.choices[0].message.content)

            # Structured logging
            structured_logger.info(
                "llm_ner_extraction",
                domain=domain,
                entities_extracted=list(entities.keys()),
                entity_count=sum(
                    len(v) if isinstance(v, list) else 1 for v in entities.values()
                ),
            )

            return entities

        except Exception as e:
            logger.error(f"LLM NER extraction failed: {e}", exc_info=True)
            structured_logger.error(
                "llm_ner_extraction_failed", domain=domain, error=str(e)
            )
            return {}

    def _build_extraction_prompt(
        self, query: str, language: str, schema: Dict, existing_entities: Dict
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
        self.llm_enabled_domains = [
            "health",
            "nutrition",
            "environment",
            "hatchery",
            "processing",
            "economics",
            "temporal",
            "geographic",
            "regulatory",
        ]
        self.min_query_length_for_llm = 8  # words (lowered to catch more queries)

        logger.info("✅ HybridEntityExtractor initialized")

    def extract_all(
        self,
        query: str,
        language: str = "fr",
        domain: str = None,
        existing_entities: Dict = None,
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
            domain=domain,
        )

        return all_entities

    def _should_use_llm(
        self, query: str, domain: str, extracted_entities: Dict
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
