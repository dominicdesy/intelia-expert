# -*- coding: utf-8 -*-
"""
translation_service.py - Service de traduction universel hybride
Combine dictionnaire local + Google Translate avec cache intelligent
"""

import json
import logging
import time
from typing import Dict, List, Optional, Set, Any
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


@dataclass
class TranslationResult:
    """Résultat d'une traduction avec métadonnées"""

    text: str
    source: str  # "local", "google", "fallback"
    confidence: float
    language: str
    cached: bool = False
    processing_time_ms: int = 0


@dataclass
class CacheStats:
    """Statistiques du cache de traduction"""

    hits: int = 0
    misses: int = 0
    google_calls: int = 0
    local_hits: int = 0
    cache_size: int = 0
    hit_rate: float = 0.0


class UniversalTranslationService:
    """
    Service de traduction hybride avec dictionnaire local + Google Translate
    Architecture à 3 niveaux: Cache → Dictionnaire local → Google API
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
    ):

        self.dict_path = Path(dict_path)
        self.supported_languages = supported_languages
        self.google_api_key = google_api_key
        self.enable_google_fallback = (
            enable_google_fallback and GOOGLE_TRANSLATE_AVAILABLE
        )
        self.confidence_threshold = confidence_threshold

        # Cache 2-niveaux
        self._memory_cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        self._local_dict: Dict[str, Any] = {}

        # Google Client (lazy loading)
        self._google_client = None
        self._google_client_lock = threading.Lock()

        # Stats et monitoring
        self.stats = CacheStats()
        self._stats_lock = threading.Lock()

        # Chargement dictionnaire
        self._load_universal_dictionary()

        # Validation initiale
        self._validate_setup()

    def _validate_setup(self) -> None:
        """Valide la configuration initiale"""
        if not self.dict_path.exists():
            logger.warning(f"Dictionnaire universel non trouvé: {self.dict_path}")

        if self.enable_google_fallback:
            if not GOOGLE_TRANSLATE_AVAILABLE:
                logger.error(
                    "Google Translate demandé mais google-cloud-translate non installé"
                )
                self.enable_google_fallback = False
            elif not self.google_api_key:
                logger.warning("Google Translate activé mais API key manquante")
                self.enable_google_fallback = False

        logger.info(
            f"Service traduction initialisé - Local: {bool(self._local_dict)}, Google: {self.enable_google_fallback}"
        )

    def _load_universal_dictionary(self) -> None:
        """Charge le dictionnaire universel depuis JSON"""
        try:
            if self.dict_path.exists():
                with open(self.dict_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._local_dict = data
                    logger.info(
                        f"Dictionnaire chargé: {len(data.get('domains', {}))} domaines"
                    )
            else:
                logger.warning(f"Fichier dictionnaire non trouvé: {self.dict_path}")
                self._local_dict = {
                    "domains": {},
                    "metadata": {"languages": list(self.supported_languages)},
                }
        except Exception as e:
            logger.error(f"Erreur chargement dictionnaire: {e}")
            self._local_dict = {
                "domains": {},
                "metadata": {"languages": list(self.supported_languages)},
            }

    @property
    def google_client(self):
        """Google Client avec lazy loading thread-safe"""
        if not self.enable_google_fallback:
            return None

        if self._google_client is None:
            with self._google_client_lock:
                if self._google_client is None and self.google_api_key:
                    try:
                        # Configuration credentials
                        import os

                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
                            self.google_api_key
                        )
                        self._google_client = translate.Client()
                        logger.info("Google Translate client initialisé")
                    except Exception as e:
                        logger.error(f"Erreur initialisation Google client: {e}")
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
        self, term: str, target_lang: str, domain: Optional[str] = None
    ) -> Optional[TranslationResult]:
        """Recherche dans le dictionnaire local avec logique de domaine"""
        start_time = time.time()

        # Normalisation du terme
        term_lower = term.lower().strip()

        # Recherche par domaine si spécifié
        domains_to_search = (
            [domain] if domain else self._local_dict.get("domains", {}).keys()
        )

        for domain_key in domains_to_search:
            domain_data = self._local_dict.get("domains", {}).get(domain_key, {})

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
                                        text=target_variants[0],  # Première variante
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
        Traduit un terme avec logique de fallback intelligente
        1. Cache mémoire
        2. Dictionnaire local
        3. Google Translate (si activé)
        4. Fallback (terme original)
        """

        # Validation entrée
        if not term or not term.strip():
            return TranslationResult(
                text="", source="fallback", confidence=0.0, language=target_language
            )

        if target_language not in self.supported_languages:
            logger.warning(f"Langue non supportée: {target_language}")
            return TranslationResult(
                text=term, source="fallback", confidence=0.0, language=target_language
            )

        # Clé de cache
        cache_key = f"{term.lower()}:{target_language}:{domain or 'general'}"

        # 1. Vérification cache
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        # 2. Recherche dictionnaire local
        local_result = self._search_local_dictionary(term, target_language, domain)
        if local_result and local_result.confidence >= self.confidence_threshold:
            self._cache_result(cache_key, local_result)
            self._update_stats("local")
            return local_result

        # 3. Google Translate fallback
        if self.enable_google_fallback:
            google_result = self._translate_with_google(
                term, target_language, source_language
            )
            if google_result and google_result.confidence >= self.confidence_threshold:
                self._cache_result(cache_key, google_result)
                return google_result

        # 4. Fallback - terme original avec score minimal
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

    def get_domain_terms(self, domain: str, language: str) -> List[str]:
        """Récupère tous les termes d'un domaine pour une langue"""
        domain_data = self._local_dict.get("domains", {}).get(domain, {})
        terms = []

        for term_key, term_data in domain_data.items():
            if isinstance(term_data, dict):
                translations = term_data.get("translations", {})
                lang_variants = translations.get(language, [])
                terms.extend(lang_variants)

        return list(set(terms))  # Dédoublonnage

    def get_available_domains(self) -> List[str]:
        """Retourne la liste des domaines disponibles"""
        return list(self._local_dict.get("domains", {}).keys())

    def get_cache_stats(self) -> CacheStats:
        """Retourne les statistiques du cache"""
        with self._stats_lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                google_calls=self.stats.google_calls,
                local_hits=self.stats.local_hits,
                cache_size=self.stats.cache_size,
                hit_rate=self.stats.hit_rate,
            )

    def clear_cache(self) -> None:
        """Vide le cache mémoire"""
        self._memory_cache.clear()
        logger.info("Cache traduction vidé")

    def reload_dictionary(self) -> bool:
        """Recharge le dictionnaire depuis le fichier"""
        try:
            self._load_universal_dictionary()
            self.clear_cache()  # Vider le cache après rechargement
            logger.info("Dictionnaire rechargé")
            return True
        except Exception as e:
            logger.error(f"Erreur rechargement dictionnaire: {e}")
            return False

    def add_validated_term(
        self,
        term: str,
        translations: Dict[str, List[str]],
        domain: str,
        confidence: float = 0.9,
    ) -> bool:
        """Ajoute un terme validé au dictionnaire local"""
        try:
            # Mise à jour du dictionnaire en mémoire
            if "domains" not in self._local_dict:
                self._local_dict["domains"] = {}

            if domain not in self._local_dict["domains"]:
                self._local_dict["domains"][domain] = {}

            self._local_dict["domains"][domain][term] = {
                "canonical": term,
                "domain": domain,
                "confidence": confidence,
                "translations": translations,
                "source": "manual_validation",
            }

            logger.info(f"Terme ajouté: {term} dans domaine {domain}")
            return True

        except Exception as e:
            logger.error(f"Erreur ajout terme {term}: {e}")
            return False

    def is_healthy(self) -> bool:
        """Vérifie l'état de santé du service"""
        try:
            # Test dictionnaire local
            local_ok = bool(self._local_dict.get("domains"))

            # Test Google si activé
            google_ok = True
            if self.enable_google_fallback:
                google_ok = self.google_client is not None

            return local_ok and google_ok

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
) -> UniversalTranslationService:
    """Factory pour créer le service de traduction"""
    return UniversalTranslationService(
        dict_path=dict_path,
        supported_languages=supported_languages,
        google_api_key=google_api_key,
        cache_size=cache_size,
        cache_ttl=cache_ttl,
        enable_google_fallback=enable_google_fallback,
        confidence_threshold=confidence_threshold,
    )


# ===== INSTANCE GLOBALE (SINGLETON PATTERN) =====
_global_translation_service: Optional[UniversalTranslationService] = None
_service_lock = threading.Lock()


def get_translation_service() -> Optional[UniversalTranslationService]:
    """Récupère l'instance globale du service de traduction"""
    return _global_translation_service


def init_global_translation_service(**kwargs) -> UniversalTranslationService:
    """Initialise le service global de traduction"""
    global _global_translation_service

    with _service_lock:
        if _global_translation_service is None:
            _global_translation_service = create_translation_service(**kwargs)

        return _global_translation_service
