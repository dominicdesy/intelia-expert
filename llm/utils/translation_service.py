# -*- coding: utf-8 -*-
"""
translation_service.py - Universal hybrid translation service
Combines local dictionary and Google Translate with intelligent caching and dynamic loading
"""

import json
import logging
import time
import re
from utils.types import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from cachetools import TTLCache
import threading

# Conditional Google Cloud Translate import
try:
    from google.cloud import translate_v2 as translate

    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    translate = None

logger = logging.getLogger(__name__)

# Constants for dynamic loading
FALLBACK_LANGUAGE = "en"
DICTIONARY_PREFIX = "universal_terms"
EXCLUSIONS_FILENAME = "technical_exclusions.json"


@dataclass
class TranslationResult:
    """Translation result with metadata"""

    text: str
    source: str  # "local", "google", "fallback", "excluded"
    confidence: float
    language: str
    cached: bool = False
    processing_time_ms: int = 0
    exclusion_reason: Optional[str] = None


@dataclass
class CacheStats:
    """Translation cache statistics"""

    hits: int = 0
    misses: int = 0
    google_calls: int = 0
    local_hits: int = 0
    cache_size: int = 0
    hit_rate: float = 0.0
    technical_terms_excluded: int = 0
    terms_translated: int = 0


class UniversalTranslationService:
    """
    Hybrid translation service with 3-tier architecture: Cache → Local Dictionary → Google API
    Supports dynamic dictionary loading per language with technical term exclusion
    """

    def __init__(
        self,
        dict_path: str,
        supported_languages: Set[str],
        google_api_key: Optional[str] = None,
        cache_size: int = 10000,
        cache_ttl: int = 86400,
        enable_google_fallback: bool = False,
        confidence_threshold: float = 0.7,
        enable_technical_exclusion: bool = True,
    ):
        self.dict_path = Path(dict_path)
        self.supported_languages = supported_languages
        self.google_api_key = google_api_key
        self.enable_google_fallback = (
            enable_google_fallback and GOOGLE_TRANSLATE_AVAILABLE
        )
        self.confidence_threshold = confidence_threshold
        self.enable_technical_exclusion = enable_technical_exclusion

        # Load exclusions from JSON
        self.exclusions = self._load_technical_exclusions()

        # 2-tier cache
        self._memory_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

        # Language dictionaries with dynamic loading
        self._language_dictionaries: Dict[str, Dict[str, Any]] = {}
        self._dictionary_lock = threading.Lock()

        # Google Client with lazy loading
        self._google_client = None
        self._google_client_lock = threading.Lock()

        # Stats and monitoring
        self.stats = CacheStats()
        self._stats_lock = threading.Lock()

        # Initial validation
        self._validate_setup()

    def _load_technical_exclusions(self) -> Dict[str, Set[str]]:
        """
        Load technical exclusions from JSON with fallback to defaults
        """
        exclusions_file = self.dict_path / EXCLUSIONS_FILENAME

        if not exclusions_file.exists():
            logger.warning(
                f"File {EXCLUSIONS_FILENAME} not found: {exclusions_file}, "
                "using default exclusions"
            )
            return self._get_default_exclusions()

        try:
            with open(exclusions_file, "r", encoding="utf-8") as f:
                data = json.load(f)

                exclusions = {
                    "exact": set(data.get("exact_terms", [])),
                    "partial": set(data.get("partial_terms", [])),
                    "extensions": set(data.get("file_extensions", [])),
                    "database": set(data.get("database_terms", [])),
                    "api": set(data.get("api_technical", [])),
                }

                logger.info(
                    f"Exclusions loaded from JSON: {len(exclusions['exact'])} exact terms, "
                    f"{len(exclusions['partial'])} partial terms, "
                    f"{len(exclusions['extensions'])} extensions, "
                    f"{len(exclusions['database'])} DB terms, "
                    f"{len(exclusions['api'])} API terms"
                )

                return exclusions

        except Exception as e:
            logger.error(f"Error loading exclusions from JSON: {e}")
            return self._get_default_exclusions()

    def _get_default_exclusions(self) -> Dict[str, Set[str]]:
        """
        Minimal default exclusions if JSON file is absent
        """
        logger.info("Using default exclusions (fallback)")
        return {
            "exact": {
                # Technical data/file terms
                "weight_curves",
                "growth_curves",
                "fcr_curves",
                "mortality_curves",
                "performance_data",
                "breeding_data",
                "nutrition_data",
                "feed_data",
                # Genetic line identifiers
                "ross308",
                "ross_308",
                "cobb500",
                "cobb_500",
                "hubbard_flex",
                "isa_brown",
                "dekalb_white",
                "novogen_brown",
                "bovans_white",
                # Poultry technical terms
                "broiler_performance",
                "layer_performance",
                "breeder_performance",
                "feed_conversion_ratio",
                "average_daily_gain",
                "body_weight_gain",
                "egg_production_rate",
                "fertility_rate",
                "hatchability_rate",
                "livability_rate",
                "uniformity_index",
                "european_production_index",
                # Metric identifiers
                "epef",
                "eef",
                "fcr",
                "adg",
                "bwg",
                "epr",
                "fr",
                "hr",
                "lr",
                "ui",
                "epi",
                # Technical file/extension names
                "broiler_objectives",
                "layer_standards",
                "breeder_targets",
                # Technical codes and references
                "ap_male",
                "ap_female",
                "straight_run",
                "parent_stock",
                "ps",
                "commercial_strain",
                "genetic_line",
                "selection_line",
            },
            "partial": {
                # Technical prefixes
                "ross",
                "cobb",
                "hubbard",
                "isa",
                "dekalb",
                "novogen",
                "bovans",
                "aviagen",
                "hendrix",
                "petersons",
                "grimaud",
                "group",
                # Technical suffixes
                "_data",
                "_curves",
                "_performance",
                "_objectives",
                "_standards",
                "_targets",
                "_index",
                "_ratio",
                "_rate",
                "_gain",
                "_weight",
                # Product codes
                "308",
                "500",
                "flex",
                "brown",
                "white",
                "plus",
                "max",
                "elite",
            },
            "extensions": {"xlsx", "json", "csv", "pdf", "docx", "txt", "xml"},
            "database": {
                "database",
                "table",
                "query",
                "insert",
                "update",
                "select",
                "join",
                "postgresql",
                "weaviate",
                "redis",
                "cache",
                "index",
                "schema",
            },
            "api": {"api", "endpoint", "rest", "token"},
        }

    def _is_technical_term(self, term: str) -> Tuple[bool, str]:
        """
        Check if term is technical and should not be translated
        """
        if not self.enable_technical_exclusion:
            return False, ""

        term_lower = term.lower().strip()

        # Exact exclusion
        if term_lower in self.exclusions["exact"]:
            return True, f"exact_match: {term_lower}"

        # Partial exclusion
        for partial in self.exclusions["partial"]:
            if partial in term_lower:
                return True, f"partial_match: {partial}"

        # File extensions
        if term_lower in self.exclusions["extensions"]:
            return True, "file_extension"

        # Database terms
        if term_lower in self.exclusions["database"]:
            return True, "database_term"

        # API terms
        if term_lower in self.exclusions["api"]:
            return True, "api_term"

        # Special poultry patterns (e.g. "ross308", "cobb500")
        if re.match(r"^[a-z]+\d+$", term_lower):
            return True, "genetic_line_pattern"

        # Technical compound words (e.g. "feed_conversion", "body_weight")
        if "_" in term_lower:
            parts = term_lower.split("_")
            if any(part in self.exclusions["exact"] for part in parts):
                return True, "technical_compound"

        # Short technical codes (2-4 capital letters)
        if re.match(r"^[A-Z]{2,4}$", term) and len(term) <= 4:
            return True, "technical_code"

        return False, ""

    def _validate_setup(self) -> None:
        """
        Validate initial configuration with environment variable handling
        """
        if not self.dict_path.exists():
            logger.warning(f"Dictionary directory not found: {self.dict_path}")
            self.dict_path.mkdir(parents=True, exist_ok=True)

        if self.enable_google_fallback:
            if not GOOGLE_TRANSLATE_AVAILABLE:
                logger.error(
                    "Google Translate requested but google-cloud-translate not installed"
                )
                self.enable_google_fallback = False
            else:
                # Check API key from environment variables
                import os

                api_key = self.google_api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")

                if not api_key:
                    logger.debug("Google Translate enabled but no API key found")
                    self.enable_google_fallback = False
                elif api_key.startswith("AIza"):
                    logger.debug("Google Translate API key detected")
                elif os.path.isfile(api_key):
                    logger.debug("Google service account file detected")
                else:
                    logger.debug(f"Unrecognized API key format: {api_key[:10]}...")
                    self.enable_google_fallback = False

        logger.info(
            f"Translation service initialized - Directory: {self.dict_path}, Google: {self.enable_google_fallback}, Technical exclusions: {self.enable_technical_exclusion}"
        )

    def _load_language_dictionary(self, language: str) -> Dict[str, Any]:
        """
        Load dictionary for specific language with fallback
        """
        # Check if already loaded
        if language in self._language_dictionaries:
            return self._language_dictionaries[language]

        with self._dictionary_lock:
            # Double-check after lock acquisition
            if language in self._language_dictionaries:
                return self._language_dictionaries[language]

            # Build file path
            file_path = self.dict_path / f"{DICTIONARY_PREFIX}_{language}.json"

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    dictionary_data = json.load(f)
                    self._language_dictionaries[language] = dictionary_data
                    logger.info(
                        f"Dictionary {language} loaded: {len(dictionary_data.get('domains', {}))} domains"
                    )
                    return dictionary_data

            except FileNotFoundError:
                logger.warning(f"Dictionary {language} not found: {file_path}")

                # Fallback to default language
                if language != FALLBACK_LANGUAGE:
                    logger.info(f"Fallback to {FALLBACK_LANGUAGE} dictionary")
                    try:
                        fallback_dict = self._load_language_dictionary(
                            FALLBACK_LANGUAGE
                        )
                        self._language_dictionaries[language] = fallback_dict
                        return fallback_dict
                    except Exception as e:
                        logger.error(f"Fallback error to {FALLBACK_LANGUAGE}: {e}")

                # Empty dictionary as last resort
                empty_dict = {
                    "domains": {},
                    "metadata": {
                        "language": language,
                        "loaded_at": time.time(),
                        "source": "empty_fallback",
                    },
                }
                self._language_dictionaries[language] = empty_dict
                return empty_dict

            except Exception as e:
                logger.error(f"Error loading dictionary {language}: {e}")
                empty_dict = {
                    "domains": {},
                    "metadata": {
                        "language": language,
                        "error": str(e),
                        "source": "error_fallback",
                    },
                }
                self._language_dictionaries[language] = empty_dict
                return empty_dict

    def _get_language_dictionary(self, language: str) -> Dict[str, Any]:
        """Retrieves dictionary for a language (with lazy loading)"""
        if language not in self._language_dictionaries:
            return self._load_language_dictionary(language)
        return self._language_dictionaries[language]

    @property
    def google_client(self):
        """CORRECTION: Google Client with new compatible API"""
        if not self.enable_google_fallback:
            return None

        if self._google_client is None:
            with self._google_client_lock:
                if self._google_client is None:
                    try:
                        import os

                        # CORRECTION: Retrieve key from environment variables
                        api_key = self.google_api_key or os.getenv(
                            "GOOGLE_TRANSLATE_API_KEY"
                        )

                        if api_key and api_key.startswith("AIza"):
                            # CRITICAL CORRECTION: New compatible method
                            logger.debug(
                                "Configuring Google Translate with direct API key"
                            )

                            # Using direct REST API to avoid version issues
                            import requests

                            class SimpleGoogleTranslateClient:
                                def __init__(self, api_key):
                                    self.api_key = api_key
                                    self.base_url = "https://translation.googleapis.com/language/translate/v2"

                                def translate(
                                    self,
                                    text,
                                    target_language="en",
                                    source_language=None,
                                ):
                                    """Translation via Google REST API"""
                                    params = {
                                        "q": text,
                                        "target": target_language,
                                        "key": self.api_key,
                                        "format": "text",
                                    }
                                    if source_language and source_language != "auto":
                                        params["source"] = source_language

                                    try:
                                        response = requests.get(
                                            self.base_url, params=params, timeout=10
                                        )
                                        response.raise_for_status()

                                        result = response.json()
                                        if (
                                            "data" in result
                                            and "translations" in result["data"]
                                        ):
                                            translated_text = result["data"][
                                                "translations"
                                            ][0]["translatedText"]
                                            return {
                                                "translatedText": translated_text,
                                                "detectedSourceLanguage": result[
                                                    "data"
                                                ]["translations"][0].get(
                                                    "detectedSourceLanguage"
                                                ),
                                            }
                                    except Exception as e:
                                        logger.warning(
                                            f"Google Translate API error: {e}"
                                        )
                                        return None

                                    return None

                            self._google_client = SimpleGoogleTranslateClient(api_key)
                            logger.info(
                                "Google Translate client initialisé avec clé API (REST)"
                            )

                        elif api_key and os.path.isfile(api_key):
                            # JSON service account file (standard method)
                            logger.debug(
                                "Configuring Google Translate with service account"
                            )
                            try:
                                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key
                                self._google_client = translate.Client()
                                logger.info(
                                    "Google Translate client initialisé avec service account"
                                )
                            except Exception as e:
                                logger.debug(f"Service account error: {e}")
                                self.enable_google_fallback = False
                                return None

                        else:
                            # No valid key found
                            if api_key:
                                logger.debug(
                                    f"Format de clé API non reconnu: {api_key[:10]}..."
                                )
                            else:
                                logger.debug("Aucune clé Google Translate trouvée")
                            logger.info(
                                "Google Translate désactivé - fonctionnement en mode local"
                            )
                            self.enable_google_fallback = False
                            return None

                    except Exception as e:
                        logger.debug(f"Google Translate initialization error: {e}")
                        logger.info(
                            "Google Translate non disponible - fonctionnement en mode local"
                        )
                        self.enable_google_fallback = False

        return self._google_client

    def _update_stats(self, source: str, cached: bool = False) -> None:
        """Updates statistics thread-safe"""
        with self._stats_lock:
            if cached:
                self.stats.hits += 1
            else:
                self.stats.misses += 1

            if source == "local":
                self.stats.local_hits += 1
            elif source == "google":
                self.stats.google_calls += 1
            elif source == "excluded":
                self.stats.technical_terms_excluded += 1
            else:
                self.stats.terms_translated += 1

            self.stats.cache_size = len(self._memory_cache)
            total_requests = self.stats.hits + self.stats.misses
            self.stats.hit_rate = (
                self.stats.hits / total_requests if total_requests > 0 else 0.0
            )

    def _get_from_cache(self, key: str) -> Optional[TranslationResult]:
        """Retrieves from memory cache"""
        if key in self._memory_cache:
            result = self._memory_cache[key]
            result.cached = True
            self._update_stats(result.source, cached=True)
            return result
        return None

    def _cache_result(self, key: str, result: TranslationResult) -> None:
        """Caches a result"""
        self._memory_cache[key] = result

    def _search_local_dictionary(
        self,
        term: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[TranslationResult]:
        """
        REWRITTEN METHOD: Search with one language per file via common canonical keys

        Logic:
        1. Load source language dictionary (or all if not specified)
        2. Find term in canonical or variants
        3. Retrieve common canonical key
        4. Load target language dictionary
        5. Find same canonical in target language
        6. Return canonical or first variant of target language
        """
        start_time = time.time()
        term_lower = term.lower().strip()

        # Determine languages to examine for search
        search_languages = []
        if source_lang and source_lang != "auto":
            search_languages.append(source_lang)
        else:
            search_languages.extend(self.supported_languages)

        # Step 1: Find canonical in source language
        found_canonical = None
        found_domain = None
        found_confidence = 0.9

        for search_lang in search_languages:
            source_dict = self._get_language_dictionary(search_lang)
            domains_data = source_dict.get("domains", {})

            # Search by domain if specified
            domains_to_search = [domain] if domain else domains_data.keys()

            for domain_key in domains_to_search:
                if domain_key not in domains_data:
                    continue

                domain_data = domains_data[domain_key]

                # Iterate through all domain terms
                for canonical_key, term_data in domain_data.items():
                    if not isinstance(term_data, dict):
                        continue

                    # Check canonical itself
                    canonical = term_data.get("canonical", canonical_key)
                    if canonical.lower() == term_lower:
                        found_canonical = canonical_key
                        found_domain = domain_key
                        found_confidence = term_data.get("confidence", 0.9)
                        break

                    # Check in variants
                    variants = term_data.get("variants", [])
                    if isinstance(variants, list):
                        for variant in variants:
                            if variant.lower() == term_lower:
                                found_canonical = canonical_key
                                found_domain = domain_key
                                found_confidence = term_data.get("confidence", 0.9)
                                break

                if found_canonical:
                    break

            if found_canonical:
                break

        # If term not found in source dictionaries
        if not found_canonical:
            return None

        # Step 2: Load target language dictionary
        target_dict = self._get_language_dictionary(target_lang)
        target_domains = target_dict.get("domains", {})

        # Step 3: Find same canonical in target language
        if found_domain not in target_domains:
            logger.debug(
                f"Domaine {found_domain} non trouvé dans langue cible {target_lang}"
            )
            return None

        target_domain_data = target_domains[found_domain]

        if found_canonical not in target_domain_data:
            logger.debug(
                f"Canonical {found_canonical} non trouvé dans {target_lang}/{found_domain}"
            )
            return None

        target_term_data = target_domain_data[found_canonical]

        # Step 4: Retrieve translation (canonical or first variant)
        target_canonical = target_term_data.get("canonical", found_canonical)
        target_variants = target_term_data.get("variants", [])

        # Choose best term to return
        if (
            target_variants
            and isinstance(target_variants, list)
            and len(target_variants) > 0
        ):
            translated_text = target_variants[0]
        else:
            translated_text = target_canonical

        processing_time = int((time.time() - start_time) * 1000)

        return TranslationResult(
            text=translated_text,
            source="local",
            confidence=found_confidence,
            language=target_lang,
            processing_time_ms=processing_time,
        )

    def _translate_with_google(
        self, term: str, target_lang: str, source_lang: str = "auto"
    ) -> Optional[TranslationResult]:
        """Translation via Google Translate with error handling"""
        if not self.google_client:
            return None

        start_time = time.time()

        try:
            # Normalize Google language codes
            google_target = self._normalize_google_lang_code(target_lang)
            google_source = (
                self._normalize_google_lang_code(source_lang)
                if source_lang != "auto"
                else "auto"
            )

            # Google API call
            result = self.google_client.translate(
                term,
                target_language=google_target,
                source_language=google_source if google_source != "auto" else None,
            )

            if not result:
                return None

            processing_time = int((time.time() - start_time) * 1000)

            # Extract result
            translated_text = result.get("translatedText", term)

            # Basic confidence score (Google doesn't provide explicit score)
            confidence = 0.8  # Google default confidence

            # Heuristic adjustments
            if translated_text.lower() == term.lower():
                confidence = 0.6  # No change = less reliable
            elif len(translated_text) < 2:
                confidence = 0.5  # Result too short

            self._update_stats("google")

            return TranslationResult(
                text=translated_text,
                source="google",
                confidence=confidence,
                language=target_lang,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.warning(f"Google Translate error {term} -> {target_lang}: {e}")
            return None

    def _normalize_google_lang_code(self, lang_code: str) -> str:
        """
        Normalize language codes for Google Translate
        """
        google_mappings = {
            "zh": "zh-cn",
            "hi": "hi",
            "th": "th",
            "id": "id",
        }

        return google_mappings.get(lang_code, lang_code)

    def translate_term(
        self,
        term: str,
        target_language: str,
        source_language: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> TranslationResult:
        """
        Translate term with intelligent fallback:
        1. Technical exclusion check
        2. Memory cache
        3. Local dictionary
        4. Google Translate (if enabled)
        5. Fallback (original term)
        """

        # Validate input
        if not term or not term.strip():
            return TranslationResult(
                text="", source="fallback", confidence=0.0, language=target_language
            )

        # Check technical exclusion first
        is_technical, exclusion_reason = self._is_technical_term(term)
        if is_technical:
            self._update_stats("excluded")
            logger.debug(
                f"Technical term excluded from translation: '{term}' (reason: {exclusion_reason})"
            )

            return TranslationResult(
                text=term,
                source="excluded",
                confidence=1.0,
                language=source_language or "en",
                exclusion_reason=exclusion_reason,
            )

        if target_language not in self.supported_languages:
            logger.warning(f"Unsupported language: {target_language}")
            return TranslationResult(
                text=term, source="fallback", confidence=0.0, language=target_language
            )

        # Generate cache key
        cache_key = f"{term.lower()}:{target_language}:{source_language or 'auto'}:{domain or 'general'}"

        # Check cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        # Search local dictionary
        local_result = self._search_local_dictionary(
            term, target_language, source_language, domain
        )
        if local_result and local_result.confidence >= self.confidence_threshold:
            self._cache_result(cache_key, local_result)
            self._update_stats("local")
            return local_result

        # Google Translate fallback
        if self.enable_google_fallback:
            google_result = self._translate_with_google(
                term, target_language, source_language
            )
            if google_result and google_result.confidence >= self.confidence_threshold:
                self._cache_result(cache_key, google_result)
                return google_result

        # Final fallback with original term
        fallback_result = TranslationResult(
            text=term, source="fallback", confidence=0.3, language=target_language
        )

        # Cache fallbacks to avoid retries
        self._cache_result(cache_key, fallback_result)
        self._update_stats("fallback")

        return fallback_result

    def translate_list(
        self,
        terms: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> List[TranslationResult]:
        """
        Batch translation with sequential processing
        """
        if not terms:
            return []

        results = []

        for term in terms:
            result = self.translate_term(term, target_language, source_language, domain)
            results.append(result)

        return results

    def reload_exclusions(self) -> bool:
        """
        Reload exclusions from JSON file
        """
        try:
            self.exclusions = self._load_technical_exclusions()
            logger.info("Technical exclusions reloaded successfully from JSON")
            return True
        except Exception as e:
            logger.error(f"Error reloading exclusions: {e}")
            return False

    def get_domain_terms(self, domain: str, language: str) -> List[str]:
        """
        Retrieve all terms from domain for language
        """
        lang_dict = self._get_language_dictionary(language)
        domain_data = lang_dict.get("domains", {}).get(domain, {})
        terms = []

        for term_key, term_data in domain_data.items():
            if isinstance(term_data, dict):
                canonical = term_data.get("canonical", term_key)
                variants = term_data.get("variants", [])
                terms.append(canonical)
                if isinstance(variants, list):
                    terms.extend(variants)

        return list(set(terms))

    def get_available_domains(self, language: Optional[str] = None) -> List[str]:
        """
        Return list of available domains for language
        """
        if language:
            lang_dict = self._get_language_dictionary(language)
            return list(lang_dict.get("domains", {}).keys())
        else:
            # Aggregate domains from all loaded languages
            all_domains = set()
            for lang in self.supported_languages:
                if lang in self._language_dictionaries:
                    lang_dict = self._language_dictionaries[lang]
                    all_domains.update(lang_dict.get("domains", {}).keys())
            return list(all_domains)

    def get_loaded_languages(self) -> List[str]:
        """
        Return list of languages with loaded dictionaries
        """
        return list(self._language_dictionaries.keys())

    def preload_languages(self, languages: List[str]) -> Dict[str, bool]:
        """
        Preload dictionaries for multiple languages
        """
        results = {}
        for lang in languages:
            if lang in self.supported_languages:
                try:
                    self._load_language_dictionary(lang)
                    results[lang] = True
                    logger.info(f"Dictionary {lang} preloaded")
                except Exception as e:
                    logger.error(f"Preload error {lang}: {e}")
                    results[lang] = False
            else:
                results[lang] = False
                logger.warning(f"Unsupported language for preload: {lang}")

        return results

    def get_cache_stats(self) -> CacheStats:
        """
        Return cache statistics with technical exclusions
        """
        with self._stats_lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                google_calls=self.stats.google_calls,
                local_hits=self.stats.local_hits,
                cache_size=self.stats.cache_size,
                hit_rate=self.stats.hit_rate,
                technical_terms_excluded=self.stats.technical_terms_excluded,
                terms_translated=self.stats.terms_translated,
            )

    def get_exclusion_stats(self) -> Dict[str, Any]:
        """
        Detailed statistics of technical exclusions
        """
        with self._stats_lock:
            total_processed = (
                self.stats.hits
                + self.stats.misses
                + self.stats.technical_terms_excluded
            )

            return {
                "technical_terms_excluded": self.stats.technical_terms_excluded,
                "terms_translated": self.stats.terms_translated,
                "total_processed": total_processed,
                "exclusion_rate_pct": round(
                    self.stats.technical_terms_excluded / max(1, total_processed) * 100,
                    2,
                ),
                "translation_rate_pct": round(
                    self.stats.terms_translated / max(1, total_processed) * 100, 2
                ),
                "cache_hit_rate_pct": round(
                    self.stats.hits / max(1, total_processed) * 100, 2
                ),
                "technical_exclusion_enabled": self.enable_technical_exclusion,
            }

    def clear_cache(self) -> None:
        """
        Clear memory cache
        """
        self._memory_cache.clear()
        logger.info("Translation cache cleared")

    def reload_language_dictionary(self, language: str) -> bool:
        """
        Reload dictionary for specific language
        """
        try:
            with self._dictionary_lock:
                # Remove old dictionary from cache
                if language in self._language_dictionaries:
                    del self._language_dictionaries[language]

                # Reload
                self._load_language_dictionary(language)

                # Clear memory cache for this language
                keys_to_remove = [
                    k for k in self._memory_cache.keys() if f":{language}:" in k
                ]
                for key in keys_to_remove:
                    del self._memory_cache[key]

                logger.info(f"Dictionary {language} reloaded")
                return True
        except Exception as e:
            logger.error(f"Error reloading dictionary {language}: {e}")
            return False

    def reload_all_dictionaries(self) -> Dict[str, bool]:
        """
        Reload all loaded dictionaries
        """
        loaded_languages = list(self._language_dictionaries.keys())
        results = {}

        for lang in loaded_languages:
            results[lang] = self.reload_language_dictionary(lang)

        return results

    def add_validated_term(
        self,
        term: str,
        translations: Dict[str, List[str]],
        domain: str,
        language: str,
        confidence: float = 0.9,
    ) -> bool:
        """
        Add validated term to dictionary for specific language
        """
        try:
            # Load language dictionary
            lang_dict = self._get_language_dictionary(language)

            # Update in-memory dictionary
            if "domains" not in lang_dict:
                lang_dict["domains"] = {}

            if domain not in lang_dict["domains"]:
                lang_dict["domains"][domain] = {}

            lang_dict["domains"][domain][term] = {
                "canonical": term,
                "domain": domain,
                "confidence": confidence,
                "translations": translations,
                "source": "manual_validation",
                "added_at": time.time(),
            }

            logger.info(
                f"Term added: {term} in domain {domain} (language: {language})"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding term {term} (language: {language}): {e}")
            return False

    def is_healthy(self) -> bool:
        """
        Check service health status
        """
        try:
            dict_path_ok = self.dict_path.exists()

            google_ok = True
            if self.enable_google_fallback:
                google_ok = self.google_client is not None

            at_least_one_dict = len(self._language_dictionaries) > 0

            return dict_path_ok and google_ok and at_least_one_dict

        except Exception:
            return False


# Factory function
def create_translation_service(
    dict_path: str,
    supported_languages: Set[str],
    google_api_key: Optional[str] = None,
    enable_google_fallback: bool = False,
    cache_size: int = 10000,
    cache_ttl: int = 86400,
    confidence_threshold: float = 0.7,
    enable_technical_exclusion: bool = True,
) -> UniversalTranslationService:
    """
    Factory to create translation service with technical exclusion
    """
    return UniversalTranslationService(
        dict_path=dict_path,
        supported_languages=supported_languages,
        google_api_key=google_api_key,
        cache_size=cache_size,
        cache_ttl=cache_ttl,
        enable_google_fallback=enable_google_fallback,
        confidence_threshold=confidence_threshold,
        enable_technical_exclusion=enable_technical_exclusion,
    )


# Global instance (singleton pattern)
_global_translation_service: Optional[UniversalTranslationService] = None
_service_lock = threading.Lock()


def get_translation_service() -> Optional[UniversalTranslationService]:
    """
    Retrieve global translation service instance
    """
    return _global_translation_service


def init_global_translation_service(**kwargs) -> UniversalTranslationService:
    """
    Initialize global translation service with technical exclusion
    """
    global _global_translation_service

    with _service_lock:
        if _global_translation_service is None:
            _global_translation_service = create_translation_service(**kwargs)

        return _global_translation_service


# Utility function to check if term should be translated
def should_translate_term(term: str) -> bool:
    """
    Check if term should be translated or preserved as technical term
    """

    temp_service = UniversalTranslationService(
        dict_path="", supported_languages={"fr", "en"}, enable_technical_exclusion=True
    )

    is_technical, _ = temp_service._is_technical_term(term)
    return not is_technical
