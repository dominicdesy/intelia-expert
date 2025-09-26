# -*- coding: utf-8 -*-
"""
translation_service.py - Service de traduction universel hybride
Combine dictionnaire local + Google Translate avec cache intelligent
Version avec chargement dynamique des dictionnaires par langue
CORRECTION: Gestion variable d'environnement pour clé API Google
CORRECTION CRITIQUE: Chargement des exclusions techniques depuis JSON au lieu de constantes hardcodées
"""

import json
import logging
import time
import re
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from cachetools import TTLCache
import threading

# Import conditionnel Google Cloud Translate
try:
    from google.cloud import translate_v2 as translate

    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    translate = None

logger = logging.getLogger(__name__)

# Constantes pour le chargement dynamique
FALLBACK_LANGUAGE = "en"
DICTIONARY_PREFIX = "universal_terms"
EXCLUSIONS_FILENAME = "technical_exclusions.json"


@dataclass
class TranslationResult:
    """Résultat d'une traduction avec métadonnées"""

    text: str
    source: str  # "local", "google", "fallback", "excluded"
    confidence: float
    language: str
    cached: bool = False
    processing_time_ms: int = 0
    exclusion_reason: Optional[str] = None


@dataclass
class CacheStats:
    """Statistiques du cache de traduction"""

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
    Service de traduction hybride avec dictionnaire local + Google Translate
    Architecture à 3 niveaux: Cache → Dictionnaire local → Google API
    Chargement dynamique des dictionnaires par langue
    NOUVEAU: Exclusion automatique des termes techniques depuis fichier JSON externe
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

        # NOUVEAU: Charger les exclusions depuis JSON
        self.exclusions = self._load_technical_exclusions()

        # Cache 2-niveaux
        self._memory_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

        # Dictionnaires par langue (chargement dynamique)
        self._language_dictionaries: Dict[str, Dict[str, Any]] = {}
        self._dictionary_lock = threading.Lock()

        # Google Client (lazy loading)
        self._google_client = None
        self._google_client_lock = threading.Lock()

        # Stats et monitoring
        self.stats = CacheStats()
        self._stats_lock = threading.Lock()

        # Validation initiale
        self._validate_setup()

    def _load_technical_exclusions(self) -> Dict[str, Set[str]]:
        """
        NOUVELLE MÉTHODE: Charge les exclusions techniques depuis JSON
        Retourne un dictionnaire avec différentes catégories d'exclusions
        """
        exclusions_file = self.dict_path / EXCLUSIONS_FILENAME

        if not exclusions_file.exists():
            logger.warning(
                f"Fichier {EXCLUSIONS_FILENAME} non trouvé: {exclusions_file}, "
                "utilisation des exclusions par défaut"
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
                    f"Exclusions chargées depuis JSON: {len(exclusions['exact'])} termes exacts, "
                    f"{len(exclusions['partial'])} termes partiels, "
                    f"{len(exclusions['extensions'])} extensions, "
                    f"{len(exclusions['database'])} termes DB, "
                    f"{len(exclusions['api'])} termes API"
                )

                return exclusions

        except Exception as e:
            logger.error(f"Erreur chargement exclusions depuis JSON: {e}")
            return self._get_default_exclusions()

    def _get_default_exclusions(self) -> Dict[str, Set[str]]:
        """Exclusions minimales par défaut si le fichier JSON est absent"""
        logger.info("Utilisation des exclusions par défaut (fallback)")
        return {
            "exact": {
                # Termes de données/fichiers techniques
                "weight_curves",
                "growth_curves",
                "fcr_curves",
                "mortality_curves",
                "performance_data",
                "breeding_data",
                "nutrition_data",
                "feed_data",
                # Identifiants lignées génétiques
                "ross308",
                "ross_308",
                "cobb500",
                "cobb_500",
                "hubbard_flex",
                "isa_brown",
                "dekalb_white",
                "novogen_brown",
                "bovans_white",
                # Termes techniques avicoles
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
                # Identifiants de métriques
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
                # Noms de fichiers/extensions techniques
                "broiler_objectives",
                "layer_standards",
                "breeder_targets",
                # Codes et références techniques
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
                # Préfixes techniques
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
                # Suffixes techniques
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
                # Codes produits
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
        MÉTHODE MODIFIÉE: Vérifie si un terme est technique et ne doit PAS être traduit
        Utilise les exclusions chargées depuis JSON au lieu des constantes
        """
        if not self.enable_technical_exclusion:
            return False, ""

        term_lower = term.lower().strip()

        # 1. Exclusion exacte
        if term_lower in self.exclusions["exact"]:
            return True, f"exact_match: {term_lower}"

        # 2. Exclusion partielle
        for partial in self.exclusions["partial"]:
            if partial in term_lower:
                return True, f"partial_match: {partial}"

        # 3. Extensions de fichiers
        if term_lower in self.exclusions["extensions"]:
            return True, "file_extension"

        # 4. Termes de base de données
        if term_lower in self.exclusions["database"]:
            return True, "database_term"

        # 5. Termes API
        if term_lower in self.exclusions["api"]:
            return True, "api_term"

        # 6. Patterns spéciaux avicoles

        # Format "lignée + nombre" (ex: "ross308", "cobb500")
        if re.match(r"^[a-z]+\d+$", term_lower):
            return True, "genetic_line_pattern"

        # Format "mot_technique" (ex: "feed_conversion", "body_weight")
        if "_" in term_lower:
            parts = term_lower.split("_")
            if any(part in self.exclusions["exact"] for part in parts):
                return True, "technical_compound"

        # Codes courts techniques (2-4 lettres majuscules)
        if re.match(r"^[A-Z]{2,4}$", term) and len(term) <= 4:
            return True, "technical_code"

        return False, ""

    def _validate_setup(self) -> None:
        """CORRECTION: Valide la configuration initiale avec gestion variable d'environnement"""
        if not self.dict_path.exists():
            logger.warning(f"Répertoire dictionnaires non trouvé: {self.dict_path}")
            # Créer le répertoire s'il n'existe pas
            self.dict_path.mkdir(parents=True, exist_ok=True)

        if self.enable_google_fallback:
            if not GOOGLE_TRANSLATE_AVAILABLE:
                logger.error(
                    "Google Translate demandé mais google-cloud-translate non installé"
                )
                self.enable_google_fallback = False
            else:
                # CORRECTION: Vérifier la clé depuis variables d'environnement
                import os

                api_key = self.google_api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")

                if not api_key:
                    logger.debug("Google Translate activé mais aucune clé API trouvée")
                    self.enable_google_fallback = False
                elif api_key.startswith("AIza"):
                    logger.debug("Clé API Google Translate détectée")
                elif os.path.isfile(api_key):
                    logger.debug("Fichier service account Google détecté")
                else:
                    logger.debug(f"Format de clé API non reconnu: {api_key[:10]}...")
                    self.enable_google_fallback = False

        logger.info(
            f"Service traduction initialisé - Répertoire: {self.dict_path}, Google: {self.enable_google_fallback}, Exclusions techniques: {self.enable_technical_exclusion}"
        )

    def _load_language_dictionary(self, language: str) -> Dict[str, Any]:
        """Charge le dictionnaire pour une langue spécifique avec fallback"""
        # Vérifier si déjà chargé
        if language in self._language_dictionaries:
            return self._language_dictionaries[language]

        with self._dictionary_lock:
            # Double-check après acquisition du verrou
            if language in self._language_dictionaries:
                return self._language_dictionaries[language]

            # Construire le chemin du fichier
            file_path = self.dict_path / f"{DICTIONARY_PREFIX}_{language}.json"

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    dictionary_data = json.load(f)
                    self._language_dictionaries[language] = dictionary_data
                    logger.info(
                        f"Dictionnaire {language} chargé: {len(dictionary_data.get('domains', {}))} domaines"
                    )
                    return dictionary_data

            except FileNotFoundError:
                logger.warning(f"Dictionnaire {language} non trouvé: {file_path}")

                # Fallback vers langue par défaut si différente
                if language != FALLBACK_LANGUAGE:
                    logger.info(f"Fallback vers dictionnaire {FALLBACK_LANGUAGE}")
                    try:
                        fallback_dict = self._load_language_dictionary(
                            FALLBACK_LANGUAGE
                        )
                        # Mettre en cache pour éviter les re-tentatives
                        self._language_dictionaries[language] = fallback_dict
                        return fallback_dict
                    except Exception as e:
                        logger.error(f"Erreur fallback vers {FALLBACK_LANGUAGE}: {e}")

                # Dictionnaire vide en dernier recours
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
                logger.error(f"Erreur chargement dictionnaire {language}: {e}")
                # Dictionnaire vide en cas d'erreur
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
        """Récupère le dictionnaire pour une langue (avec chargement lazy)"""
        if language not in self._language_dictionaries:
            return self._load_language_dictionary(language)
        return self._language_dictionaries[language]

    @property
    def google_client(self):
        """CORRECTION: Google Client avec nouvelle API compatible"""
        if not self.enable_google_fallback:
            return None

        if self._google_client is None:
            with self._google_client_lock:
                if self._google_client is None:
                    try:
                        import os

                        # CORRECTION: Récupérer la clé depuis les variables d'environnement
                        api_key = self.google_api_key or os.getenv(
                            "GOOGLE_TRANSLATE_API_KEY"
                        )

                        if api_key and api_key.startswith("AIza"):
                            # CORRECTION CRITIQUE: Nouvelle méthode compatible
                            logger.debug(
                                "Configuration Google Translate avec clé API directe"
                            )

                            # Utilisation de l'API REST directe pour éviter les problèmes de version
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
                                    """Traduction via API REST Google"""
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
                                            f"Erreur API Google Translate: {e}"
                                        )
                                        return None

                                    return None

                            self._google_client = SimpleGoogleTranslateClient(api_key)
                            logger.info(
                                "Google Translate client initialisé avec clé API (REST)"
                            )

                        elif api_key and os.path.isfile(api_key):
                            # Fichier de service account JSON (méthode standard)
                            logger.debug(
                                "Configuration Google Translate avec service account"
                            )
                            try:
                                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key
                                self._google_client = translate.Client()
                                logger.info(
                                    "Google Translate client initialisé avec service account"
                                )
                            except Exception as e:
                                logger.debug(f"Erreur service account: {e}")
                                self.enable_google_fallback = False
                                return None

                        else:
                            # Pas de clé valide trouvée
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
                        logger.debug(f"Erreur initialisation Google Translate: {e}")
                        logger.info(
                            "Google Translate non disponible - fonctionnement en mode local"
                        )
                        self.enable_google_fallback = False

        return self._google_client

    def _update_stats(self, source: str, cached: bool = False) -> None:
        """Met à jour les statistiques thread-safe"""
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
        """Récupère depuis le cache mémoire"""
        if key in self._memory_cache:
            result = self._memory_cache[key]
            result.cached = True
            self._update_stats(result.source, cached=True)
            return result
        return None

    def _cache_result(self, key: str, result: TranslationResult) -> None:
        """Met en cache un résultat"""
        self._memory_cache[key] = result

    def _search_local_dictionary(
        self,
        term: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[TranslationResult]:
        """Recherche dans le dictionnaire local avec logique de domaine et langue source"""
        start_time = time.time()

        # Normalisation du terme
        term_lower = term.lower().strip()

        # Déterminer les langues à examiner pour la recherche
        search_languages = []
        if source_lang and source_lang != "auto":
            search_languages.append(source_lang)
        else:
            # Rechercher dans toutes les langues supportées
            search_languages.extend(self.supported_languages)

        # Recherche dans les dictionnaires des langues sources potentielles
        for search_lang in search_languages:
            lang_dict = self._get_language_dictionary(search_lang)
            domains_data = lang_dict.get("domains", {})

            # Recherche par domaine si spécifié
            domains_to_search = [domain] if domain else domains_data.keys()

            for domain_key in domains_to_search:
                if domain_key not in domains_data:
                    continue

                domain_data = domains_data[domain_key]

                for term_key, term_data in domain_data.items():
                    if not isinstance(term_data, dict):
                        continue

                    translations = term_data.get("translations", {})

                    # Recherche dans toutes les langues du terme
                    for lang, variants in translations.items():
                        if isinstance(variants, list):
                            for variant in variants:
                                if variant.lower() == term_lower:
                                    # Trouvé! Récupérer la traduction cible
                                    target_variants = translations.get(target_lang, [])
                                    if target_variants:
                                        processing_time = int(
                                            (time.time() - start_time) * 1000
                                        )
                                        confidence = term_data.get("confidence", 0.9)

                                        return TranslationResult(
                                            text=target_variants[
                                                0
                                            ],  # Première variante
                                            source="local",
                                            confidence=confidence,
                                            language=target_lang,
                                            processing_time_ms=processing_time,
                                        )

        return None

    def _translate_with_google(
        self, term: str, target_lang: str, source_lang: str = "auto"
    ) -> Optional[TranslationResult]:
        """Traduction via Google Translate avec gestion d'erreurs"""
        if not self.google_client:
            return None

        start_time = time.time()

        try:
            # Normalisation codes langues Google
            google_target = self._normalize_google_lang_code(target_lang)
            google_source = (
                self._normalize_google_lang_code(source_lang)
                if source_lang != "auto"
                else "auto"
            )

            # Appel API Google
            result = self.google_client.translate(
                term,
                target_language=google_target,
                source_language=google_source if google_source != "auto" else None,
            )

            if not result:
                return None

            processing_time = int((time.time() - start_time) * 1000)

            # Extraction résultat
            translated_text = result.get("translatedText", term)

            # Score de confiance basique (Google ne fournit pas de score explicite)
            confidence = 0.8  # Confiance par défaut Google

            # Ajustements heuristiques
            if translated_text.lower() == term.lower():
                confidence = 0.6  # Pas de changement = moins fiable
            elif len(translated_text) < 2:
                confidence = 0.5  # Résultat trop court

            self._update_stats("google")

            return TranslationResult(
                text=translated_text,
                source="google",
                confidence=confidence,
                language=target_lang,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.warning(f"Erreur Google Translate {term} -> {target_lang}: {e}")
            return None

    def _normalize_google_lang_code(self, lang_code: str) -> str:
        """Normalise les codes langue pour Google Translate"""
        # Mappings spéciaux
        google_mappings = {
            "zh": "zh-cn",  # Chinois simplifié par défaut
            "hi": "hi",  # Hindi
            "th": "th",  # Thaï
            "id": "id",  # Indonésien
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
        Traduit un terme avec logique de fallback intelligente et exclusion technique
        1. Vérification exclusion technique (NOUVEAU)
        2. Cache mémoire
        3. Dictionnaire local (chargement dynamique par langue)
        4. Google Translate (si activé)
        5. Fallback (terme original)
        """

        # Validation entrée
        if not term or not term.strip():
            return TranslationResult(
                text="", source="fallback", confidence=0.0, language=target_language
            )

        # CORRECTION CRITIQUE: Vérifier exclusion technique EN PREMIER
        is_technical, exclusion_reason = self._is_technical_term(term)
        if is_technical:
            self._update_stats("excluded")
            logger.debug(
                f"Terme technique exclu de la traduction: '{term}' (raison: {exclusion_reason})"
            )

            return TranslationResult(
                text=term,  # Retourner le terme original non traduit
                source="excluded",
                confidence=1.0,  # Confiance maximale pour exclusion
                language=source_language or "en",  # Garder langue source
                exclusion_reason=exclusion_reason,
            )

        if target_language not in self.supported_languages:
            logger.warning(f"Langue non supportée: {target_language}")
            return TranslationResult(
                text=term, source="fallback", confidence=0.0, language=target_language
            )

        # Clé de cache
        cache_key = f"{term.lower()}:{target_language}:{source_language or 'auto'}:{domain or 'general'}"

        # 2. Vérification cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        # 3. Recherche dictionnaire local (avec chargement dynamique)
        local_result = self._search_local_dictionary(
            term, target_language, source_language, domain
        )
        if local_result and local_result.confidence >= self.confidence_threshold:
            self._cache_result(cache_key, local_result)
            self._update_stats("local")
            return local_result

        # 4. Google Translate fallback
        if self.enable_google_fallback:
            google_result = self._translate_with_google(
                term, target_language, source_language
            )
            if google_result and google_result.confidence >= self.confidence_threshold:
                self._cache_result(cache_key, google_result)
                return google_result

        # 5. Fallback - terme original avec score minimal
        fallback_result = TranslationResult(
            text=term, source="fallback", confidence=0.3, language=target_language
        )

        # Cache même les fallbacks pour éviter les re-tentatives
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
        """Traduction batch avec optimisations"""
        if not terms:
            return []

        results = []

        # Traduction séquentielle (optimisations possibles: async batch)
        for term in terms:
            result = self.translate_term(term, target_language, source_language, domain)
            results.append(result)

        return results

    def reload_exclusions(self) -> bool:
        """
        NOUVELLE MÉTHODE: Recharge les exclusions depuis le fichier JSON
        Utile après modification du fichier technical_exclusions.json
        """
        try:
            self.exclusions = self._load_technical_exclusions()
            logger.info("Exclusions techniques rechargées avec succès depuis JSON")
            return True
        except Exception as e:
            logger.error(f"Erreur rechargement exclusions: {e}")
            return False

    def get_domain_terms(self, domain: str, language: str) -> List[str]:
        """Récupère tous les termes d'un domaine pour une langue"""
        lang_dict = self._get_language_dictionary(language)
        domain_data = lang_dict.get("domains", {}).get(domain, {})
        terms = []

        for term_key, term_data in domain_data.items():
            if isinstance(term_data, dict):
                translations = term_data.get("translations", {})
                lang_variants = translations.get(language, [])
                terms.extend(lang_variants)

        return list(set(terms))  # Déduplication

    def get_available_domains(self, language: Optional[str] = None) -> List[str]:
        """Retourne la liste des domaines disponibles pour une langue"""
        if language:
            lang_dict = self._get_language_dictionary(language)
            return list(lang_dict.get("domains", {}).keys())
        else:
            # Agréger les domaines de toutes les langues chargées
            all_domains = set()
            for lang in self.supported_languages:
                if lang in self._language_dictionaries:
                    lang_dict = self._language_dictionaries[lang]
                    all_domains.update(lang_dict.get("domains", {}).keys())
            return list(all_domains)

    def get_loaded_languages(self) -> List[str]:
        """Retourne la liste des langues dont le dictionnaire est chargé"""
        return list(self._language_dictionaries.keys())

    def preload_languages(self, languages: List[str]) -> Dict[str, bool]:
        """Précharge les dictionnaires pour plusieurs langues"""
        results = {}
        for lang in languages:
            if lang in self.supported_languages:
                try:
                    self._load_language_dictionary(lang)
                    results[lang] = True
                    logger.info(f"Dictionnaire {lang} préchargé")
                except Exception as e:
                    logger.error(f"Erreur préchargement {lang}: {e}")
                    results[lang] = False
            else:
                results[lang] = False
                logger.warning(f"Langue non supportée pour préchargement: {lang}")

        return results

    def get_cache_stats(self) -> CacheStats:
        """Retourne les statistiques du cache avec exclusions techniques"""
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
        """NOUVEAU: Statistiques détaillées des exclusions techniques"""
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
        """Vide le cache mémoire"""
        self._memory_cache.clear()
        logger.info("Cache traduction vidé")

    def reload_language_dictionary(self, language: str) -> bool:
        """Recharge le dictionnaire d'une langue spécifique"""
        try:
            with self._dictionary_lock:
                # Supprimer l'ancien dictionnaire du cache
                if language in self._language_dictionaries:
                    del self._language_dictionaries[language]

                # Recharger
                self._load_language_dictionary(language)

                # Vider le cache mémoire pour cette langue
                keys_to_remove = [
                    k for k in self._memory_cache.keys() if f":{language}:" in k
                ]
                for key in keys_to_remove:
                    del self._memory_cache[key]

                logger.info(f"Dictionnaire {language} rechargé")
                return True
        except Exception as e:
            logger.error(f"Erreur rechargement dictionnaire {language}: {e}")
            return False

    def reload_all_dictionaries(self) -> Dict[str, bool]:
        """Recharge tous les dictionnaires chargés"""
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
        """Ajoute un terme validé au dictionnaire d'une langue spécifique"""
        try:
            # Charger le dictionnaire de la langue si nécessaire
            lang_dict = self._get_language_dictionary(language)

            # Mise à jour du dictionnaire en mémoire
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
                f"Terme ajouté: {term} dans domaine {domain} (langue: {language})"
            )
            return True

        except Exception as e:
            logger.error(f"Erreur ajout terme {term} (langue: {language}): {e}")
            return False

    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service"""
        try:
            # Test répertoire dictionnaires
            dict_path_ok = self.dict_path.exists()

            # Test Google si activé
            google_ok = True
            if self.enable_google_fallback:
                google_ok = self.google_client is not None

            # Test chargement au moins une langue
            at_least_one_dict = len(self._language_dictionaries) > 0

            return dict_path_ok and google_ok and at_least_one_dict

        except Exception:
            return False


# ===== FACTORY FUNCTION =====
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
    """Factory pour créer le service de traduction avec exclusion technique"""
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


# ===== INSTANCE GLOBALE (SINGLETON PATTERN) =====
_global_translation_service: Optional[UniversalTranslationService] = None
_service_lock = threading.Lock()


def get_translation_service() -> Optional[UniversalTranslationService]:
    """Récupère l'instance globale du service de traduction"""
    return _global_translation_service


def init_global_translation_service(**kwargs) -> UniversalTranslationService:
    """Initialise le service global de traduction avec exclusion technique"""
    global _global_translation_service

    with _service_lock:
        if _global_translation_service is None:
            _global_translation_service = create_translation_service(**kwargs)

        return _global_translation_service


# CORRECTION CRITIQUE: Fonction utilitaire pour éviter la traduction des termes techniques
def should_translate_term(term: str) -> bool:
    """Vérifie rapidement si un terme doit être traduit ou préservé"""

    temp_service = UniversalTranslationService(
        dict_path="", supported_languages={"fr", "en"}, enable_technical_exclusion=True
    )

    is_technical, _ = temp_service._is_technical_term(term)
    return not is_technical
