# -*- coding: utf-8 -*-
"""
query_router.py - Intelligent 100% Config-Driven Router
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
query_router.py - Intelligent 100% Config-Driven Router
Single entry point for ALL query processing

REPLACES:
- query_preprocessor.py
- rag_postgresql_validator.py
- query_classifier.py (partial)
- validation_core.py (partial)
- conversation_context.py (logic)

VERSION 1.0 - Simplified config-driven architecture
- Loads ALL patterns from config/*.json
- Manages conversational context (storage + merge)
- Extracts entities via compiled regex (no OpenAI)
- Validates completeness based on intents.json
- Routes to PostgreSQL/Weaviate/Hybrid
- ZERO hardcoding - everything from JSON files
"""

import re
import json
import time
import logging
from pathlib import Path
from utils.types import Dict, Optional, Tuple, List, Set, Any
from dataclasses import dataclass, field
from functools import lru_cache
from utils.mixins import SerializableMixin
from .hybrid_entity_extractor import create_hybrid_extractor

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class QueryRoute(SerializableMixin):
    """Routing result with all necessary information"""

    destination: str  # 'postgresql' | 'weaviate' | 'hybrid' | 'needs_clarification'
    entities: Dict[str, Any]
    route_reason: str
    needs_calculation: bool = False
    is_contextual: bool = False
    confidence: float = 1.0
    missing_fields: List[str] = field(default_factory=list)
    validation_details: Dict[str, Any] = field(default_factory=dict)
    query_type: str = "standard"  # Query type for logging/tracking
    detected_domain: str = None  # Detected domain (genetics, metrics, health, etc.)

    # to_dict() now inherited from SerializableMixin (removed 12 lines)


@dataclass
class ConversationContext:
    """Stored conversational context"""

    entities: Dict[str, Any]
    query: str
    timestamp: float
    language: str

    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Checks if context has expired (default 5 min)"""
        return (time.time() - self.timestamp) > timeout_seconds


# ============================================================================
# CONFIG MANAGER - Loads and indexes ALL JSON files
# ============================================================================


class ConfigManager:
    """
    Centralized manager for ALL configurations
    Loads and indexes JSON files for O(1) access

    Single source of truth for:
    - Breeds and aliases
    - Sex variants
    - Metrics and keywords
    - Routing keywords (PostgreSQL vs Weaviate)
    - Multilingual contextual patterns
    - Age ranges and phases
    - Species mapping (broiler/layer/breeder)
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.intents = {}
        self.entity_descriptions = {}
        self.system_prompts = {}
        self.languages = {}
        self.universal_terms = {}
        self.domain_keywords = {}

        # Index for fast lookup
        self.breed_index = {}
        self.sex_index = {}
        self.metric_index = {}
        self.routing_keywords = {"postgresql": [], "weaviate": []}

        # Load and index configs
        self._load_all_configs()
        self._build_indexes()

    def _load_all_configs(self) -> None:
        """Loads ALL configuration files"""

        # 1. INTENTS.JSON - Main source of truth
        intents_path = self.config_dir / "intents.json"
        if intents_path.exists():
            with open(intents_path, "r", encoding="utf-8") as f:
                self.intents = json.load(f)
            logger.info(f"✅ intents.json loaded: {intents_path}")
        else:
            logger.error(f"❌ intents.json missing: {intents_path}")
            raise FileNotFoundError(f"Critical configuration missing: {intents_path}")

        # 2. ENTITY_DESCRIPTIONS.JSON (optionnel)
        desc_path = self.config_dir / "entity_descriptions.json"
        if desc_path.exists():
            with open(desc_path, "r", encoding="utf-8") as f:
                self.entity_descriptions = json.load(f)
            logger.info("✅ entity_descriptions.json loaded")

        # 3. SYSTEM_PROMPTS.JSON (optional)
        prompts_path = self.config_dir / "system_prompts.json"
        if prompts_path.exists():
            with open(prompts_path, "r", encoding="utf-8") as f:
                self.system_prompts = json.load(f)
            logger.info("✅ system_prompts.json loaded")

        # 4. LANGUAGES.JSON (optional)
        lang_path = self.config_dir / "languages.json"
        if lang_path.exists():
            with open(lang_path, "r", encoding="utf-8") as f:
                self.languages = json.load(f)
            logger.info("✅ languages.json loaded")

        # 5. UNIVERSAL_TERMS par langue
        lang_codes = [
            "en",
            "fr",
            "es",
            "de",
            "hi",
            "id",
            "it",
            "nl",
            "pl",
            "pt",
            "th",
            "zh",
        ]
        for lang_code in lang_codes:
            term_path = self.config_dir / f"universal_terms_{lang_code}.json"
            if term_path.exists():
                with open(term_path, "r", encoding="utf-8") as f:
                    self.universal_terms[lang_code] = json.load(f)

        logger.info(f"✅ {len(self.universal_terms)} universal_terms files loaded")

        # 6. DOMAIN_KEYWORDS.JSON (new)
        domain_path = self.config_dir / "domain_keywords.json"
        if domain_path.exists():
            with open(domain_path, "r", encoding="utf-8") as f:
                self.domain_keywords = json.load(f)
            logger.info("✅ domain_keywords.json loaded")
        else:
            logger.warning(f"domain_keywords.json not found: {domain_path}")

    def _build_indexes(self) -> None:
        """Builds indexes for fast O(1) lookup"""

        # INDEX BREEDS - All aliases from intents.json
        line_aliases = self.intents.get("aliases", {}).get("line", {})
        for canonical, aliases in line_aliases.items():
            # Canonical name
            self.breed_index[canonical.lower()] = canonical
            # All aliases
            if isinstance(aliases, list):
                for alias in aliases:
                    self.breed_index[alias.lower()] = canonical

        # INDEX SEX
        sex_aliases = self.intents.get("aliases", {}).get("sex", {})
        for canonical, aliases in sex_aliases.items():
            if isinstance(aliases, list):
                for alias in aliases:
                    self.sex_index[alias.lower()] = canonical

        # INDEX METRICS
        metric_aliases = self.intents.get("aliases", {}).get("metric", {})
        for category, keywords in metric_aliases.items():
            if isinstance(keywords, list):
                for keyword in keywords:
                    self.metric_index[keyword.lower()] = category

        # INDEX ROUTING KEYWORDS depuis universal_terms
        for lang_code, lang_terms in self.universal_terms.items():
            domains = lang_terms.get("domains", {})

            # PostgreSQL keywords (numeric metrics)
            metrics_domain = domains.get("metrics", {})
            if metrics_domain:
                for metric_key, metric_data in metrics_domain.items():
                    if isinstance(metric_data, dict) and "variants" in metric_data:
                        self.routing_keywords["postgresql"].extend(
                            metric_data["variants"]
                        )

            # Also check performance_metrics domain
            perf_metrics = domains.get("performance_metrics", {})
            if perf_metrics:
                for metric_key, metric_data in perf_metrics.items():
                    if isinstance(metric_data, dict) and "variants" in metric_data:
                        self.routing_keywords["postgresql"].extend(
                            metric_data["variants"]
                        )

            # Weaviate keywords (health, environment)
            health_domain = domains.get("health", {})
            if health_domain:
                for health_key, health_data in health_domain.items():
                    if isinstance(health_data, dict) and "variants" in health_data:
                        self.routing_keywords["weaviate"].extend(
                            health_data["variants"]
                        )

            environment_domain = domains.get("environment", {})
            if environment_domain:
                for env_key, env_data in environment_domain.items():
                    if isinstance(env_data, dict) and "variants" in env_data:
                        self.routing_keywords["weaviate"].extend(env_data["variants"])

        # Deduplicate
        self.routing_keywords["postgresql"] = list(
            set(self.routing_keywords["postgresql"])
        )
        self.routing_keywords["weaviate"] = list(set(self.routing_keywords["weaviate"]))

        # ✅ NEW: Species index
        self.species_index = self._build_species_index()
        logger.info(f"✅ Species index built: {len(self.species_index)} mappings")

        logger.info(
            f"✅ Indexes built: {len(self.breed_index)} breeds, "
            f"{len(self.sex_index)} sex variants, "
            f"{len(self.metric_index)} metrics, "
            f"{len(self.routing_keywords['postgresql'])} PG keywords, "
            f"{len(self.routing_keywords['weaviate'])} Weaviate keywords"
        )

    def _build_species_index(self) -> Dict[str, str]:
        """
        Builds variant → database_value index for species

        Returns:
            {"broiler": "broiler", "meat chicken": "broiler",
             "layer": "layer", ...}
        """
        index = {}

        # Load from universal_terms if available
        for lang_code, lang_terms in self.universal_terms.items():
            # ✅ FIX: Access domains.species
            domains = lang_terms.get("domains", {})
            species_terms = domains.get("species", {})

            if not species_terms:
                continue

            for species_key, data in species_terms.items():
                if not isinstance(data, dict):
                    continue

                database_value = data.get("database_value", species_key)
                canonical = data.get("canonical", species_key)
                variants = data.get("variants", [])

                # Add canonical
                if canonical:
                    index[canonical.lower()] = database_value

                # Add all variants
                if isinstance(variants, list):
                    for variant in variants:
                        if variant:
                            index[variant.lower()] = database_value

        if not index:
            logger.warning("⚠️ No species terms found in universal_terms")
        else:
            logger.debug(f"Species index: {len(index)} variants mapped")

        return index

    def get_species_from_text(self, text: str) -> Optional[str]:
        """
        Detects species in text via index

        Args:
            text: Text to analyze

        Returns:
            Species database_value ("broiler", "layer", "breeder") or None
        """
        if not hasattr(self, "species_index"):
            logger.warning("Species index not initialized")
            return None

        text_lower = text.lower()

        # Look for exact match first
        for variant, database_value in self.species_index.items():
            if variant in text_lower:
                return database_value

        return None

    @lru_cache(maxsize=1000)
    def get_breed_canonical(self, breed_text: str) -> Optional[str]:
        """Returns canonical breed name"""
        return self.breed_index.get(breed_text.lower())

    @lru_cache(maxsize=100)
    def get_sex_canonical(self, sex_text: str) -> Optional[str]:
        """Returns canonical sex"""
        return self.sex_index.get(sex_text.lower())

    @lru_cache(maxsize=100)
    def get_metric_category(self, metric_text: str) -> Optional[str]:
        """Returns metric category"""
        return self.metric_index.get(metric_text.lower())

    def get_age_range(self, phase: str) -> Optional[Tuple[int, int]]:
        """Returns age range for a phase"""
        age_ranges = self.intents.get("age_ranges", {})
        range_data = age_ranges.get(phase)
        if isinstance(range_data, list) and len(range_data) == 2:
            return tuple(range_data)
        return None

    def get_contextual_patterns(self, language: str) -> List[str]:
        """
        Returns contextual patterns for a language from universal_terms

        Extracts all variants from contextual_references to build
        regex patterns for contextual detection
        """
        lang_terms = self.universal_terms.get(language, {})
        contextual = lang_terms.get("domains", {}).get("contextual_references", {})

        # Extract all variants from all keys (same, and_for, females, etc.)
        patterns = []
        for key, term_data in contextual.items():
            if isinstance(term_data, dict) and "variants" in term_data:
                variants = term_data["variants"]
                # Convert variants to regex patterns with word boundaries
                for variant in variants:
                    # Escape special regex chars, then add word boundaries
                    escaped = re.escape(variant)
                    patterns.append(rf"\b{escaped}\b")

        if patterns:
            logger.debug(
                f"✅ Loaded {len(patterns)} contextual patterns for {language}"
            )

        return patterns

    def should_route_to_postgresql(self, query: str, language: str = None) -> bool:
        """Determines if query should route to PostgreSQL"""
        query_lower = query.lower()
        pg_keywords = self.routing_keywords.get("postgresql", [])
        return any(kw in query_lower for kw in pg_keywords)

    def should_route_to_weaviate(self, query: str, language: str = None) -> bool:
        """Determines if query should route to Weaviate"""
        query_lower = query.lower()
        wv_keywords = self.routing_keywords.get("weaviate", [])
        return any(kw in query_lower for kw in wv_keywords)

    def get_all_breeds(self) -> Set[str]:
        """Returns all canonical breed names"""
        line_aliases = self.intents.get("aliases", {}).get("line", {})
        return set(line_aliases.keys())

    def get_species(self, breed: str) -> Optional[str]:
        """Returns species of a breed (broiler/layer/breeder)"""
        breed_registry = self.intents.get("breed_registry", {})
        species_mapping = breed_registry.get("species_mapping", {})
        return species_mapping.get(breed)


# ============================================================================
# QUERY ROUTER - Single entry point
# ============================================================================


class QueryRouter:
    """
    Intelligent 100% config-driven router

    Responsibilities:
    1. Load/store conversational context
    2. Detect contextual references
    3. Extract entities (compiled regex from config)
    4. Merge entities with context if needed
    5. Validate completeness
    6. Route to appropriate destination
    """

    def __init__(self, config_dir: str = "config"):
        self.config = ConfigManager(config_dir)
        self.context_store: Dict[str, ConversationContext] = {}

        # Compile regex patterns from config
        self._compile_patterns()

        # Initialize hybrid entity extractor
        self.hybrid_extractor = create_hybrid_extractor(config_dir)

        # Initialize LLM Query Classifier (replaces fragile patterns)
        from core.llm_query_classifier import get_llm_query_classifier

        self.llm_classifier = get_llm_query_classifier()

        logger.info(
            "✅ QueryRouter initialized (100% config-driven + hybrid extraction + LLM classification)"
        )

    def _compile_patterns(self) -> None:
        """Compiles regex from configs for performance"""

        # BREEDS - Dynamic pattern from index
        if self.config.breed_index:
            # Sort by descending length to match longest first
            breed_aliases = sorted(
                self.config.breed_index.keys(), key=len, reverse=True
            )
            breed_pattern = "|".join(re.escape(alias) for alias in breed_aliases)
            self.breed_regex = re.compile(rf"\b({breed_pattern})\b", re.IGNORECASE)
        else:
            self.breed_regex = None

        # COMPARISON - Pattern to detect multi-breed comparisons
        self.comparison_regex = re.compile(
            r"\b(vs\.?|versus|compar[ae]|compare[zr]?|et|and|ou|or)\b", re.IGNORECASE
        )

        # AGE - Universal multi-language pattern
        self.age_regex = re.compile(
            r"\b(\d+)\s*(jour|day|semaine|week|día|días|tag|tage|settimana|settimane|"
            r"semana|semanas|j\b|d\b|sem|wk|w\b)s?\b",
            re.IGNORECASE,
        )

        # WEEKS - Priority over days (conversion x7)
        self.weeks_regex = re.compile(
            r"\b(\d+)\s*(semaine|week|semana|settimana|woche|wk|w\b)s?\b", re.IGNORECASE
        )

        # SEX - Dynamic pattern from index
        if self.config.sex_index:
            sex_aliases = sorted(self.config.sex_index.keys(), key=len, reverse=True)
            sex_pattern = "|".join(re.escape(alias) for alias in sex_aliases)
            self.sex_regex = re.compile(rf"\b({sex_pattern})\b", re.IGNORECASE)
        else:
            self.sex_regex = None

        logger.debug("✅ Regex patterns compiled from config")

    def detect_domain(self, query: str, language: str = "fr") -> str:
        """
        Detects query domain for prompt selection

        Args:
            query: User question
            language: Language (fr/en)

        Returns:
            Detected domain prompt_key or 'general_poultry'
        """
        if (
            not self.config.domain_keywords
            or "domains" not in self.config.domain_keywords
        ):
            return "general_poultry"

        query_lower = query.lower()
        domain_scores = {}

        # Count matched keywords per domain
        for domain_name, domain_data in self.config.domain_keywords["domains"].items():
            keywords = domain_data.get("keywords", {}).get(language, [])
            if not keywords:
                keywords = domain_data.get("keywords", {}).get("fr", [])

            matches = sum(1 for kw in keywords if kw.lower() in query_lower)
            if matches > 0:
                domain_scores[domain_name] = {
                    "score": matches,
                    "prompt_key": domain_data.get("prompt_key", "general_poultry"),
                }

        # No match: fallback
        if not domain_scores:
            logger.debug(
                f"No domain detected for '{query}', fallback to general_poultry"
            )
            return "general_poultry"

        # Take domain with most matches
        best_domain = max(domain_scores.items(), key=lambda x: x[1]["score"])
        prompt_key = best_domain[1]["prompt_key"]

        logger.info(
            f"Domain detected: {best_domain[0]} (score={best_domain[1]['score']}) → prompt={prompt_key}"
        )

        # Apply priority rules if multiple domains
        if len(domain_scores) > 1:
            prompt_key = self._apply_priority_rules(domain_scores, prompt_key)

        return prompt_key

    def _apply_priority_rules(
        self, domain_scores: Dict[str, Any], current_prompt: str
    ) -> str:
        """
        Applies priority rules between domains

        Args:
            domain_scores: Scores by domain
            current_prompt: Currently selected prompt

        Returns:
            Adjusted prompt according to priority rules
        """
        priority_rules = self.config.domain_keywords.get("priority_rules", {}).get(
            "rules", []
        )

        for rule in priority_rules:
            condition = rule.get("condition", "")
            domains_in_condition = [d.strip() for d in condition.split("+")]

            # Check if both domains are present
            if all(d in domain_scores for d in domains_in_condition):
                priority_domain = rule.get("priority")
                if priority_domain in domain_scores:
                    new_prompt = domain_scores[priority_domain]["prompt_key"]
                    logger.info(
                        f"Priority applied: {condition} → {priority_domain} ({rule.get('reason')})"
                    )
                    return new_prompt

        return current_prompt

    def route(
        self,
        query: str,
        user_id: str,
        language: str = "fr",
        preextracted_entities: Dict[str, Any] = None,
        override_domain: str = None,
    ) -> QueryRoute:
        """
        SINGLE entry point - does EVERYTHING in one pass

        Args:
            query: User query
            user_id: User/tenant identifier
            language: Detected language
            preextracted_entities: Already extracted entities from context (optional)
            override_domain: Forced domain (for reuse after clarification)

        Returns:
            QueryRoute with destination + complete entities
        """

        start_time = time.time()

        # 🆕 STEP 0: Detect explicit product syntax (nano:, compass:, etc.)
        explicit_product = None
        cleaned_query = query
        product_prefix_pattern = r'^(nano|compass|unity|farmhub|cognito)\s*:\s*'
        product_match = re.match(product_prefix_pattern, query.lower(), re.IGNORECASE)

        if product_match:
            explicit_product = product_match.group(1).lower()
            # Clean query: remove "nano: " prefix
            cleaned_query = re.sub(product_prefix_pattern, '', query, flags=re.IGNORECASE).strip()
            logger.info(f"📦 Syntaxe explicite détectée: {explicit_product}: → query nettoyée")
            logger.debug(f"   Original: '{query}'")
            logger.debug(f"   Cleaned: '{cleaned_query}'")

            # Use cleaned query for all subsequent processing
            query = cleaned_query

        # Load conversation context if available
        previous_context = self.context_store.get(user_id)

        # Clean expired contexts
        if previous_context and previous_context.is_expired():
            logger.info(f"🗑️ Contexte expiré pour {user_id}, suppression")
            del self.context_store[user_id]
            previous_context = None

        # Detect contextual references
        is_contextual = self._is_contextual(query, language)

        # Detect multi-breed comparisons
        is_comparative = self._is_comparative(query)

        # Detect domain for hybrid extraction (reuse forced domain after clarification)
        if override_domain:
            detected_domain = override_domain
            logger.info(f"♻️ Domaine forcé (clarification): {detected_domain}")
        else:
            detected_domain = self.detect_domain(query, language)

        # ⚡ Optimize entity extraction: use pre-extracted entities as base when available
        # This saves ~30ms by avoiding duplicate extraction from context
        if preextracted_entities:
            # Use pre-extracted entities as base, only extract new entities from current query
            entities = preextracted_entities.copy()
            logger.debug(
                f"⚡ Using {len(preextracted_entities)} pre-extracted entities as base"
            )

            # Extract only new entities from current query (not already in context)
            query_entities = self._extract_entities(query, language)

            # Merge query entities (query takes precedence for explicit values)
            for key, value in query_entities.items():
                if value:  # Only override if query has explicit value
                    entities[key] = value
                    logger.debug(f"   Query overrides {key}={value}")
        else:
            # No pre-extracted entities, extract from scratch
            entities = self._extract_entities(query, language)

        # Extract advanced entities (numeric, health, etc.)
        hybrid_entities = self.hybrid_extractor.extract_all(
            query=query,
            language=language,
            domain=detected_domain,
            existing_entities=entities,
        )
        # Merge hybrid entities without overriding basic entities
        for key, value in hybrid_entities.items():
            if key not in entities or not entities[key]:
                entities[key] = value

        # 🆕 Inject explicit product if detected via syntax (highest priority)
        if explicit_product:
            entities["intelia_product"] = explicit_product
            logger.info(f"📦 Produit Intelia injecté dans entities: {explicit_product}")

        # Extract multi-breed entities for comparisons
        comparison_entities = []
        if is_comparative:
            all_breeds = self._extract_all_breeds(query)

            if len(all_breeds) >= 2:
                logger.info(f"🔀 Comparaison multi-races détectée: {all_breeds}")

                # Create comparison entity for each breed
                for breed in all_breeds:
                    comp_entity = {
                        "breed": breed,
                        "_comparison_label": breed,
                    }

                    # Inherit age, sex, metric from main entities
                    if entities.get("age_days"):
                        comp_entity["age_days"] = entities["age_days"]
                    if entities.get("sex"):
                        comp_entity["sex"] = entities["sex"]
                    if entities.get("metric_type"):
                        comp_entity["metric_type"] = entities["metric_type"]

                    comparison_entities.append(comp_entity)

                # Store in entities for transmission
                entities["comparison_entities"] = comparison_entities
                entities["is_comparative"] = True
                logger.info(
                    f"📊 {len(comparison_entities)} entités comparatives créées"
                )
            else:
                logger.debug(
                    f"⚠️ Pattern comparatif détecté mais < 2 breeds: {all_breeds}"
                )
                is_comparative = False

        # ⚡ Pre-extracted entities already merged above (lines 607-619), skip redundant merge

        # Merge with conversation context if contextual query
        if is_contextual and previous_context:
            original_entities = entities.copy()
            entities = self._merge_with_context(entities, previous_context.entities)
            logger.info(f"✅ Contexte mergé pour {user_id}")
            logger.debug(f"   Original: {original_entities}")
            logger.debug(f"   Previous: {previous_context.entities}")
            logger.debug(f"   Merged: {entities}")

        # Validate entity completeness
        is_complete, missing, validation_details = self._validate_completeness(
            entities, query, language
        )

        if not is_complete:
            # Extract LLM-generated clarification message if available
            llm_clarification = validation_details.get("clarification_message")
            if llm_clarification:
                logger.info("✅ Using LLM-generated clarification message")
                validation_details["generated_clarification"] = llm_clarification

            return QueryRoute(
                destination="needs_clarification",
                entities=entities,
                route_reason="missing_required_fields",
                missing_fields=missing,
                validation_details=validation_details,
                is_contextual=is_contextual,
                confidence=0.5,
                query_type="clarification_needed",
                detected_domain=detected_domain,
            )

        # Intelligent routing based on LLM intent
        intent = validation_details.get("llm_intent", "general_knowledge")

        # Route to calculation handler for multi-step calculations
        if intent == "calculation_query":
            destination = "calculation"
            reason = "calculation_query_detected"
            logger.info(
                f"🧮 Routing vers calculation handler: {entities.get('calculation_type')}"
            )
        # Route to comparative handler for multi-breed comparisons
        elif is_comparative and entities.get("comparison_entities"):
            destination = "comparative"
            reason = "multi_breed_comparison_detected"
            logger.info(
                f"🔀 Routing vers comparative: {len(entities['comparison_entities'])} breeds"
            )
        else:
            destination, reason = self._determine_destination(
                query, entities, language, validation_details
            )

        # Store conversation context
        self.context_store[user_id] = ConversationContext(
            entities=entities, query=query, timestamp=time.time(), language=language
        )

        processing_time = time.time() - start_time

        logger.info(
            f"✅ Route: {destination} | Domain: {detected_domain} | Contextuel: {is_contextual} | "
            f"Temps: {processing_time:.3f}s"
        )

        # Add domain to validation_details for use by generators
        validation_details["detected_domain"] = detected_domain

        # Determine query_type based on destination and domain
        query_type = self._determine_query_type(destination, detected_domain, entities)

        return QueryRoute(
            destination=destination,
            entities=entities,
            route_reason=reason,
            is_contextual=is_contextual,
            validation_details=validation_details,
            confidence=1.0,
            query_type=query_type,
            detected_domain=detected_domain,  # 🆕 Inclure domaine dans route
        )

    def _is_contextual(self, query: str, language: str) -> bool:
        """
        Detects contextual references using patterns from universal_terms configuration
        """
        # Retrieve patterns from universal_terms
        patterns = self.config.get_contextual_patterns(language)

        if not patterns:
            logger.warning(
                f"⚠️ No contextual patterns loaded for language '{language}'. "
                f"Check config/universal_terms_{language}.json"
            )
            return False

        query_lower = query.lower()
        for pattern in patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug(f"🔗 Référence contextuelle détectée: '{pattern}'")
                return True

        return False

    def _is_comparative(self, query: str) -> bool:
        """
        Detects multi-entity comparison queries with strict validation for generic conjunctions

        Returns True if comparison pattern detected with breeds on both sides of keyword
        """
        if not self.comparison_regex:
            return False

        query_lower = query.lower()

        # Detect comparison pattern
        comparison_match = self.comparison_regex.search(query_lower)

        if not comparison_match:
            return False

        keyword = comparison_match.group().lower()

        # Strict validation for generic conjunctions to avoid false positives
        if keyword in ["et", "and", "ou", "or"]:
            # Extract all breeds in query
            all_breeds = self._extract_all_breeds(query)

            # Less than 2 breeds means false positive
            if len(all_breeds) < 2:
                logger.debug(f"⚠️ '{keyword}' détecté mais < 2 breeds → pas comparatif")
                return False

            # Verify breeds exist on both sides of comparison keyword
            keyword_pos = query_lower.find(keyword)
            text_before = query_lower[:keyword_pos]
            text_after = query_lower[keyword_pos + len(keyword) :]

            breeds_before = sum(1 for b in all_breeds if b.lower() in text_before)
            breeds_after = sum(1 for b in all_breeds if b.lower() in text_after)

            if breeds_before == 0 or breeds_after == 0:
                logger.debug(
                    f"⚠️ Breeds pas de part et d'autre de '{keyword}' → pas comparatif"
                )
                return False

        logger.debug(f"🔀 Pattern comparatif validé: '{keyword}'")
        return True

    def _extract_all_breeds(self, query: str) -> List[str]:
        """
        Extracts all breed mentions for comparative queries

        Returns list of canonical breed names found in query
        """
        if not self.breed_regex:
            return []

        breeds_found = []

        # Find all occurrences, not just first match
        for match in self.breed_regex.finditer(query):
            breed_text = match.group(1)
            canonical = self.config.get_breed_canonical(breed_text)
            if canonical and canonical not in breeds_found:
                breeds_found.append(canonical)
                logger.debug(
                    f"🔍 Breed {len(breeds_found)}: '{breed_text}' → '{canonical}'"
                )

        return breeds_found

    def _extract_entities(self, query: str, language: str) -> Dict[str, Any]:
        """Extraction via compiled regex - NO OpenAI calls"""

        entities = {}
        query_lower = query.lower()

        # BREED
        if self.breed_regex:
            breed_match = self.breed_regex.search(query)
            if breed_match:
                breed_text = breed_match.group(1)
                canonical = self.config.get_breed_canonical(breed_text)
                if canonical:
                    entities["breed"] = canonical
                    entities["has_explicit_breed"] = True
                    logger.debug(f"🔍 Breed: '{breed_text}' → '{canonical}'")

        # AGE - Vérifier semaines AVANT jours
        if self.weeks_regex:
            weeks_match = self.weeks_regex.search(query)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                days = weeks * 7
                entities["age_days"] = days
                entities["has_explicit_age"] = True
                logger.debug(f"📅 Age: {weeks} semaines → {days} jours")

        # AGE - Si pas de semaines, chercher jours
        if "age_days" not in entities and self.age_regex:
            age_match = self.age_regex.search(query)
            if age_match:
                value = int(age_match.group(1))
                unit = age_match.group(2).lower()

                # Conversion si semaines
                if any(
                    week_kw in unit
                    for week_kw in ["semaine", "week", "semana", "woche", "wk", "w"]
                ):
                    value *= 7

                entities["age_days"] = value
                entities["has_explicit_age"] = True
                logger.debug(f"📅 Age: {value} jours")

        # SEX
        if self.sex_regex:
            sex_match = self.sex_regex.search(query)
            if sex_match:
                sex_text = sex_match.group(1)
                canonical = self.config.get_sex_canonical(sex_text)
                if canonical:
                    entities["sex"] = canonical
                    entities["has_explicit_sex"] = True
                    logger.debug(f"⚥ Sex: '{sex_text}' → '{canonical}'")

        # METRIC (détection basique par keywords)
        for metric_kw in self.config.metric_index.keys():
            if metric_kw in query_lower:
                metric_category = self.config.get_metric_category(metric_kw)
                if metric_category:
                    entities["metric_type"] = metric_category
                    logger.debug(f"📊 Metric: '{metric_kw}' → '{metric_category}'")
                    break

        # Calculer confidence
        entities["confidence"] = self._calculate_confidence(entities)

        return entities

    def _calculate_confidence(self, entities: Dict[str, Any]) -> float:
        """Calculates extraction confidence"""
        score = 0.0

        if entities.get("breed"):
            score += 0.4
        if entities.get("age_days"):
            score += 0.3
        if entities.get("sex"):
            score += 0.2
        if entities.get("metric_type"):
            score += 0.1

        return min(score, 1.0)

    def _merge_with_context(
        self, new_entities: Dict[str, Any], previous_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligent merge: new values OVERRIDE old

        Logic:
        - If new entity present → use new
        - If new entity absent → inherit from old
        """

        merged = previous_entities.copy()

        # Override avec nouvelles valeurs non-None
        for key, value in new_entities.items():
            if value is not None and value != "":
                merged[key] = value

        return merged

    def _validate_completeness(
        self, entities: Dict[str, Any], query: str, language: str
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validation based on LLM classification (replaces fragile regex patterns)

        Returns:
            (is_complete, missing_fields, validation_details)
        """

        missing = []
        validation_details = {}

        # 🚀 UTILISER LLM CLASSIFIER au lieu de patterns regex
        try:
            classification = self.llm_classifier.classify(query, language)

            intent = classification.get("intent", "general_knowledge")
            requirements = classification.get("requirements", {})
            routing = classification.get("routing", {})

            # 🆕 FUSIONNER entités LLM (priorité) avec entités regex (fallback)
            # Le LLM comprend le contexte naturel ("18th day", "at day 18", etc.)
            # tandis que regex ne matche que des patterns fixes
            llm_entities = classification.get("entities", {})
            if llm_entities:
                logger.debug(f"🤖 LLM extracted entities: {llm_entities}")

                # LLM entities take priority over regex entities
                if llm_entities.get("age_days") is not None:
                    entities["age_days"] = llm_entities["age_days"]
                    entities["has_explicit_age"] = True
                    logger.info(
                        f"✅ LLM age extraction: {llm_entities['age_days']} days"
                    )

                if llm_entities.get("breed"):
                    entities["breed"] = llm_entities["breed"]
                    entities["has_explicit_breed"] = True
                    logger.debug(f"✅ LLM breed extraction: {llm_entities['breed']}")

                if llm_entities.get("sex"):
                    entities["sex"] = llm_entities["sex"]
                    entities["has_explicit_sex"] = True
                    logger.debug(f"✅ LLM sex extraction: {llm_entities['sex']}")

                if llm_entities.get("metric"):
                    entities["metric_type"] = llm_entities["metric"]
                    logger.debug(f"✅ LLM metric extraction: {llm_entities['metric']}")

                # Nouvelles entités pour calculs
                if llm_entities.get("target_weight") is not None:
                    entities["target_weight"] = llm_entities["target_weight"]
                    logger.debug(
                        f"✅ LLM target_weight extraction: {llm_entities['target_weight']}g"
                    )

                if llm_entities.get("age_end") is not None:
                    entities["age_end"] = llm_entities["age_end"]
                    logger.info(
                        f"✅ LLM age_end extraction: {llm_entities['age_end']} days"
                    )

                if llm_entities.get("calculation_type"):
                    entities["calculation_type"] = llm_entities["calculation_type"]
                    logger.debug(
                        f"✅ LLM calculation_type: {llm_entities['calculation_type']}"
                    )

            # Log classification
            logger.info(
                f"🤖 LLM Classification: intent={intent}, "
                f"target={routing.get('target', 'unknown')}, "
                f"needs_breed={requirements.get('needs_breed', False)}, "
                f"needs_age={requirements.get('needs_age', False)}"
            )

            # Vérifier les requirements
            if requirements.get("needs_breed", False) and not entities.get("breed"):
                missing.append("breed")

            if requirements.get("needs_age", False) and not entities.get("age_days"):
                missing.append("age")

            if requirements.get("needs_sex", False) and not entities.get("sex"):
                missing.append("sex")

            # Build validation details
            validation_details["validation_type"] = f"llm_{intent}"
            validation_details["required_fields"] = [
                field
                for field, needed in requirements.items()
                if needed and field.startswith("needs_")
            ]
            validation_details["llm_routing_target"] = routing.get("target", "weaviate")
            validation_details["llm_confidence"] = routing.get("confidence", 0.5)
            validation_details["llm_intent"] = intent

            # 🆕 Add LLM-generated clarification message
            if "clarification_message" in classification:
                validation_details["clarification_message"] = classification[
                    "clarification_message"
                ]

        except Exception as e:
            logger.error(f"❌ LLM classification failed: {e}")

            # FALLBACK: Use old pattern-based logic
            logger.warning("⚠️ Falling back to pattern-based validation")

            # Déterminer si requête nécessite données PostgreSQL
            needs_postgresql = self.config.should_route_to_postgresql(query, language)

            if needs_postgresql:
                # Requêtes PostgreSQL nécessitent: breed + age
                if not entities.get("breed"):
                    missing.append("breed")
                if not entities.get("age_days"):
                    missing.append("age")

                validation_details["validation_type"] = "postgresql_metrics"
                validation_details["required_fields"] = ["breed", "age"]
            else:
                # Requêtes Weaviate/guides: détecter ambiguïté
                ambiguity_detected = self._detect_weaviate_ambiguity(
                    query, entities, language
                )

                if ambiguity_detected:
                    missing.extend(ambiguity_detected)
                    validation_details["validation_type"] = "weaviate_ambiguous"
                    validation_details["required_fields"] = ambiguity_detected
                else:
                    validation_details["validation_type"] = "weaviate_flexible"
                    validation_details["required_fields"] = []

        is_complete = len(missing) == 0

        validation_details["is_complete"] = is_complete
        validation_details["missing_count"] = len(missing)
        validation_details["entities_count"] = len(
            [k for k in entities if entities.get(k)]
        )

        return (is_complete, missing, validation_details)

    def _detect_weaviate_ambiguity(
        self, query: str, entities: Dict[str, Any], language: str
    ) -> List[str]:
        """
        Detects if a Weaviate question is too ambiguous

        Returns:
            List of missing fields or []
        """
        query_lower = query.lower()
        missing = []

        # Santé/diagnostic: besoin symptômes + âge
        health_keywords = [
            "maladie",
            "malade",
            "symptôme",
            "mort",
            "mortalité",
            "disease",
            "sick",
            "mortality",
            "diagnostic",
        ]
        if any(kw in query_lower for kw in health_keywords):
            # Question très vague (< 6 mots)
            if len(query_lower.split()) < 6:
                if not entities.get("age_days"):
                    missing.append("age")
                # Pas besoin de breed obligatoire pour Weaviate, mais mentionner si manque symptôme détaillé
                if (
                    "symptom" not in query_lower
                    and "fèces" not in query_lower
                    and "lésion" not in query_lower
                ):
                    missing.append("symptom")

        # Nutrition: besoin phase de production
        nutrition_keywords = [
            "aliment",
            "ration",
            "formule",
            "nutrition",
            "feed",
            "diet",
        ]
        if any(kw in query_lower for kw in nutrition_keywords):
            if len(query_lower.split()) < 6:
                if not entities.get("age_days"):
                    missing.append("production_phase")

        # Environnement: besoin âge
        environment_keywords = [
            "température",
            "ventilation",
            "ambiance",
            "humidité",
            "temperature",
            "climate",
        ]
        if any(kw in query_lower for kw in environment_keywords):
            if len(query_lower.split()) < 7 and not entities.get("age_days"):
                missing.append("age")

        # Traitement/protocole: besoin âge
        protocol_keywords = [
            "protocole",
            "vaccin",
            "traitement",
            "antibiotique",
            "protocol",
            "vaccine",
            "treatment",
        ]
        if any(kw in query_lower for kw in protocol_keywords):
            if not entities.get("age_days"):
                missing.append("age")

        return missing

    def _determine_destination(
        self,
        query: str,
        entities: Dict[str, Any],
        language: str,
        validation_details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Intelligent routing based on LLM classifier (priority) then keyword fallback

        Args:
            query: User question
            entities: Extracted entities
            language: Detected language
            validation_details: Validation details containing llm_routing_target

        Returns:
            (destination, reason)
        """

        # 🆕 PRIORITÉ 0: Produit Intelia détecté → toujours Weaviate
        if entities.get("intelia_product"):
            product = entities["intelia_product"]
            logger.info(f"📦 Produit Intelia détecté ({product}) → routing Weaviate prioritaire")
            return ("weaviate", f"intelia_product_{product}")

        # 🆕 PRIORITÉ 1: Utiliser routing LLM si disponible
        if validation_details:
            llm_target = validation_details.get("llm_routing_target")
            llm_confidence = validation_details.get("llm_confidence", 0.0)
            llm_intent = validation_details.get("llm_intent", "")

            # Si LLM a une recommandation claire (confidence > 0.6), la respecter
            if llm_target and llm_confidence > 0.6:
                if llm_target == "weaviate":
                    logger.info(
                        f"🤖 LLM routing (confidence={llm_confidence:.2f}): weaviate for {llm_intent}"
                    )
                    return ("weaviate", f"llm_classifier_{llm_intent}")
                elif llm_target == "postgresql":
                    logger.info(
                        f"🤖 LLM routing (confidence={llm_confidence:.2f}): postgresql for {llm_intent}"
                    )
                    return ("postgresql", f"llm_classifier_{llm_intent}")

        # FALLBACK: Keyword-based routing (ancien comportement)
        logger.debug(
            "⚠️ Fallback to keyword-based routing (LLM routing not available or low confidence)"
        )

        # PostgreSQL: métriques chiffrées
        if self.config.should_route_to_postgresql(query, language):
            return ("postgresql", "metrics_and_performance_data")

        # Weaviate: santé, environnement, guides
        if self.config.should_route_to_weaviate(query, language):
            return ("weaviate", "health_environment_guides")

        # Hybride: pas assez d'indices clairs
        return ("hybrid", "ambiguous_requires_both_sources")

    def _determine_query_type(
        self, destination: str, detected_domain: str, entities: Dict[str, Any]
    ) -> str:
        """
        Determines query type for logging/tracking

        Args:
            destination: Routed destination (postgresql/weaviate/hybrid/calculation)
            detected_domain: Detected domain (genetics_performance, health, etc.)
            entities: Extracted entities

        Returns:
            Query type (metric_query, health_query, comparison, calculation, etc.)
        """
        # Si calcul multi-étapes détecté
        if destination == "calculation":
            return "calculation"

        # Si comparaison détectée dans entities
        if entities.get("is_comparative") or entities.get("comparison_entities"):
            return "comparison"

        # Basé sur le domaine détecté
        if detected_domain in ["genetics_performance", "metric_query", "metrics"]:
            return "metric_query"
        elif detected_domain in ["health_diagnostic", "health", "biosecurity_health"]:
            return "health_query"
        elif detected_domain in ["environment_management", "environment"]:
            return "environment_query"
        elif detected_domain in ["nutrition_feeding", "nutrition"]:
            return "nutrition_query"

        # Par défaut basé sur destination
        if destination == "postgresql":
            return "performance_query"
        elif destination == "weaviate":
            return "knowledge_query"
        else:
            return "standard"

    def clear_context(self, user_id: str) -> None:
        """Clears user's conversational context"""
        if user_id in self.context_store:
            del self.context_store[user_id]
            logger.info(f"🗑️ Contexte effacé pour {user_id}")

    def get_context(self, user_id: str) -> Optional[ConversationContext]:
        """Retrieves conversational context"""
        return self.context_store.get(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """Router statistics"""
        active_contexts = sum(
            1 for ctx in self.context_store.values() if not ctx.is_expired()
        )

        return {
            "total_contexts": len(self.context_store),
            "active_contexts": active_contexts,
            "breeds_known": len(self.config.breed_index),
            "sex_variants": len(self.config.sex_index),
            "metrics_categories": len(set(self.config.metric_index.values())),
            "routing_keywords_pg": len(self.config.routing_keywords["postgresql"]),
            "routing_keywords_wv": len(self.config.routing_keywords["weaviate"]),
            "species_mappings": len(self.config.species_index),
        }


# ============================================================================
# FACTORY & TESTS
# ============================================================================


def create_query_router(config_dir: str = "config") -> QueryRouter:
    """Factory to create a QueryRouter instance"""
    return QueryRouter(config_dir)


def test_query_router() -> None:
    """Integrated unit tests"""

    print("=" * 70)
    print("TESTS QUERY ROUTER")
    print("=" * 70)

    router = QueryRouter("config")

    # Test 1: Query simple
    print("\n🔍 Test 1: Query simple avec breed + age + sex")
    route = router.route(
        query="Quel est le poids cible pour des mâles Ross 308 à 35 jours ?",
        user_id="test_user_1",
        language="fr",
    )
    print(f"   Destination: {route.destination}")
    print(f"   Entities: {route.entities}")
    print(f"   Route reason: {route.route_reason}")
    print("   ✅" if route.destination == "postgresql" else "   ❌ Expected postgresql")

    # Test 2: Query contextuelle
    print("\n🔍 Test 2: Query contextuelle (référence 'femelles')")
    route2 = router.route(
        query="Et pour les femelles au même âge ?", user_id="test_user_1", language="fr"
    )
    print(f"   Destination: {route2.destination}")
    print(f"   Entities: {route2.entities}")
    print(f"   Is contextual: {route2.is_contextual}")
    print(
        "   ✅"
        if route2.entities.get("breed") == "ross 308"
        else "   ❌ Breed not inherited"
    )
    print(
        "   ✅" if route2.entities.get("sex") == "female" else "   ❌ Sex not updated"
    )

    # Test 3: Query incomplète
    print("\n🔍 Test 3: Query incomplète (manque breed)")
    route3 = router.route(
        query="Quel est le poids à 28 jours ?", user_id="test_user_2", language="fr"
    )
    print(f"   Destination: {route3.destination}")
    print(f"   Missing: {route3.missing_fields}")
    print(
        "   ✅"
        if route3.destination == "needs_clarification"
        else "   ❌ Should need clarification"
    )

    # Test 4: Conversion semaines
    print("\n🔍 Test 4: Conversion semaines → jours")
    route4 = router.route(
        query="Poids Ross 308 à 5 semaines", user_id="test_user_3", language="fr"
    )
    print(f"   Age extracted: {route4.entities.get('age_days')} jours")
    print(
        "   ✅" if route4.entities.get("age_days") == 35 else "   ❌ Expected 35 days"
    )

    # Test 5: Query santé (Weaviate)
    print("\n🔍 Test 5: Query santé → Weaviate")
    route5 = router.route(
        query="Traitement coccidiose Ross 308 15 jours",
        user_id="test_user_4",
        language="fr",
    )
    print(f"   Destination: {route5.destination}")
    print(f"   Route reason: {route5.route_reason}")
    # Peut être hybrid si keyword 'traitement' pas dans universal_terms

    # Stats
    print("\n📊 Statistiques:")
    stats = router.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 70)
    print("TESTS TERMINÉS")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    test_query_router()
