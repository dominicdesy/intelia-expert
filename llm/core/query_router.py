# -*- coding: utf-8 -*-
"""
query_router.py - Router Intelligent 100% Config-Driven
Point d'entrée unique pour TOUT le traitement de requêtes

REMPLACE:
- query_preprocessor.py
- rag_postgresql_validator.py
- query_classifier.py (partiel)
- validation_core.py (partiel)
- conversation_context.py (logique)

VERSION 1.0 - Architecture simplifiée config-driven
- Charge TOUS les patterns depuis config/*.json
- Gère le contexte conversationnel (stockage + merge)
- Extrait entités via regex compilés (pas d'OpenAI)
- Valide complétude basée sur intents.json
- Route vers PostgreSQL/Weaviate/Hybrid
- ZÉRO hardcoding - tout vient des fichiers JSON
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

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class QueryRoute(SerializableMixin):
    """Résultat du routing avec toutes les informations nécessaires"""

    destination: str  # 'postgresql' | 'weaviate' | 'hybrid' | 'needs_clarification'
    entities: Dict[str, Any]
    route_reason: str
    needs_calculation: bool = False
    is_contextual: bool = False
    confidence: float = 1.0
    missing_fields: List[str] = field(default_factory=list)
    validation_details: Dict[str, Any] = field(default_factory=dict)

    # to_dict() now inherited from SerializableMixin (removed 12 lines)


@dataclass
class ConversationContext:
    """Contexte conversationnel stocké"""

    entities: Dict[str, Any]
    query: str
    timestamp: float
    language: str

    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Vérifie si le contexte a expiré (5 min par défaut)"""
        return (time.time() - self.timestamp) > timeout_seconds


# ============================================================================
# CONFIG MANAGER - Charge et indexe TOUS les fichiers JSON
# ============================================================================


class ConfigManager:
    """
    Gestionnaire centralisé de TOUTES les configurations
    Charge et indexe les fichiers JSON pour accès O(1)

    Source unique de vérité pour:
    - Breeds (races) et aliases
    - Sex variants
    - Metrics et keywords
    - Routing keywords (PostgreSQL vs Weaviate)
    - Patterns contextuels multilingues
    - Age ranges et phases
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

        # Index pour recherche rapide
        self.breed_index = {}
        self.sex_index = {}
        self.metric_index = {}
        self.routing_keywords = {"postgresql": [], "weaviate": []}

        # Chargement + indexation
        self._load_all_configs()
        self._build_indexes()

    def _load_all_configs(self):
        """Charge TOUS les fichiers de configuration"""

        # 1. INTENTS.JSON - Source de vérité principale
        intents_path = self.config_dir / "intents.json"
        if intents_path.exists():
            with open(intents_path, "r", encoding="utf-8") as f:
                self.intents = json.load(f)
            logger.info(f"✅ intents.json chargé: {intents_path}")
        else:
            logger.error(f"❌ intents.json manquant: {intents_path}")
            raise FileNotFoundError(f"Configuration critique manquante: {intents_path}")

        # 2. ENTITY_DESCRIPTIONS.JSON (optionnel)
        desc_path = self.config_dir / "entity_descriptions.json"
        if desc_path.exists():
            with open(desc_path, "r", encoding="utf-8") as f:
                self.entity_descriptions = json.load(f)
            logger.info("✅ entity_descriptions.json chargé")

        # 3. SYSTEM_PROMPTS.JSON (optionnel)
        prompts_path = self.config_dir / "system_prompts.json"
        if prompts_path.exists():
            with open(prompts_path, "r", encoding="utf-8") as f:
                self.system_prompts = json.load(f)
            logger.info("✅ system_prompts.json chargé")

        # 4. LANGUAGES.JSON (optionnel)
        lang_path = self.config_dir / "languages.json"
        if lang_path.exists():
            with open(lang_path, "r", encoding="utf-8") as f:
                self.languages = json.load(f)
            logger.info("✅ languages.json chargé")

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

        logger.info(f"✅ {len(self.universal_terms)} fichiers universal_terms chargés")

        # 6. DOMAIN_KEYWORDS.JSON (nouveau)
        domain_path = self.config_dir / "domain_keywords.json"
        if domain_path.exists():
            with open(domain_path, "r", encoding="utf-8") as f:
                self.domain_keywords = json.load(f)
            logger.info("✅ domain_keywords.json chargé")
        else:
            logger.warning(f"domain_keywords.json non trouvé: {domain_path}")

    def _build_indexes(self):
        """Construit des index pour recherche rapide O(1)"""

        # INDEX BREEDS - Tous les aliases depuis intents.json
        line_aliases = self.intents.get("aliases", {}).get("line", {})
        for canonical, aliases in line_aliases.items():
            # Nom canonique
            self.breed_index[canonical.lower()] = canonical
            # Tous les aliases
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
            # PostgreSQL keywords (métriques chiffrées)
            if "metrics" in lang_terms and "keywords" in lang_terms["metrics"]:
                self.routing_keywords["postgresql"].extend(
                    lang_terms["metrics"]["keywords"]
                )

            # Weaviate keywords (santé, environnement)
            if "health" in lang_terms and "keywords" in lang_terms["health"]:
                self.routing_keywords["weaviate"].extend(
                    lang_terms["health"]["keywords"]
                )
            if "environment" in lang_terms and "keywords" in lang_terms["environment"]:
                self.routing_keywords["weaviate"].extend(
                    lang_terms["environment"]["keywords"]
                )

        # Dédupliquer
        self.routing_keywords["postgresql"] = list(
            set(self.routing_keywords["postgresql"])
        )
        self.routing_keywords["weaviate"] = list(set(self.routing_keywords["weaviate"]))

        # ✅ NOUVEAU: Index des espèces
        self.species_index = self._build_species_index()
        logger.info(f"✅ Species index built: {len(self.species_index)} mappings")

        logger.info(
            f"✅ Index construits: {len(self.breed_index)} breeds, "
            f"{len(self.sex_index)} sex variants, "
            f"{len(self.metric_index)} metrics, "
            f"{len(self.routing_keywords['postgresql'])} PG keywords, "
            f"{len(self.routing_keywords['weaviate'])} Weaviate keywords"
        )

    def _build_species_index(self) -> Dict[str, str]:
        """
        Construit index variant → database_value pour species

        Returns:
            {"broiler": "broiler", "meat chicken": "broiler",
             "pondeuse": "layer", ...}
        """
        index = {}

        # Charger depuis universal_terms si disponible
        for lang_code, lang_terms in self.universal_terms.items():
            # ✅ CORRECTION: Accéder à domains.species
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

                # Ajouter canonical
                if canonical:
                    index[canonical.lower()] = database_value

                # Ajouter toutes les variantes
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
        Détecte l'espèce dans un texte via l'index

        Args:
            text: Texte à analyser

        Returns:
            database_value de l'espèce ("broiler", "layer", "breeder") ou None
        """
        if not hasattr(self, "species_index"):
            logger.warning("Species index not initialized")
            return None

        text_lower = text.lower()

        # Chercher correspondance exacte d'abord
        for variant, database_value in self.species_index.items():
            if variant in text_lower:
                return database_value

        return None

    @lru_cache(maxsize=1000)
    def get_breed_canonical(self, breed_text: str) -> Optional[str]:
        """Retourne le nom canonique d'une race"""
        return self.breed_index.get(breed_text.lower())

    @lru_cache(maxsize=100)
    def get_sex_canonical(self, sex_text: str) -> Optional[str]:
        """Retourne le sexe canonique"""
        return self.sex_index.get(sex_text.lower())

    @lru_cache(maxsize=100)
    def get_metric_category(self, metric_text: str) -> Optional[str]:
        """Retourne la catégorie de métrique"""
        return self.metric_index.get(metric_text.lower())

    def get_age_range(self, phase: str) -> Optional[Tuple[int, int]]:
        """Retourne la tranche d'âge pour une phase"""
        age_ranges = self.intents.get("age_ranges", {})
        range_data = age_ranges.get(phase)
        if isinstance(range_data, list) and len(range_data) == 2:
            return tuple(range_data)
        return None

    def get_contextual_patterns(self, language: str) -> List[str]:
        """Retourne les patterns contextuels pour une langue"""
        lang_terms = self.universal_terms.get(language, {})
        contextual = lang_terms.get("contextual_references", {})
        return contextual.get("patterns", [])

    def should_route_to_postgresql(self, query: str, language: str = None) -> bool:
        """Détermine si la query doit aller vers PostgreSQL"""
        query_lower = query.lower()
        pg_keywords = self.routing_keywords.get("postgresql", [])
        return any(kw in query_lower for kw in pg_keywords)

    def should_route_to_weaviate(self, query: str, language: str = None) -> bool:
        """Détermine si la query doit aller vers Weaviate"""
        query_lower = query.lower()
        wv_keywords = self.routing_keywords.get("weaviate", [])
        return any(kw in query_lower for kw in wv_keywords)

    def get_all_breeds(self) -> Set[str]:
        """Retourne tous les noms canoniques de races"""
        line_aliases = self.intents.get("aliases", {}).get("line", {})
        return set(line_aliases.keys())

    def get_species(self, breed: str) -> Optional[str]:
        """Retourne l'espèce d'une race (broiler/layer/breeder)"""
        breed_registry = self.intents.get("breed_registry", {})
        species_mapping = breed_registry.get("species_mapping", {})
        return species_mapping.get(breed)


# ============================================================================
# QUERY ROUTER - Point d'entrée unique
# ============================================================================


class QueryRouter:
    """
    Router intelligent 100% config-driven

    Responsabilités:
    1. Charger/stocker contexte conversationnel
    2. Détecter références contextuelles
    3. Extraire entités (regex compilés depuis config)
    4. Merger entités avec contexte si nécessaire
    5. Valider complétude
    6. Router vers destination appropriée
    """

    def __init__(self, config_dir: str = "config"):
        self.config = ConfigManager(config_dir)
        self.context_store: Dict[str, ConversationContext] = {}

        # Compiler les patterns regex depuis config
        self._compile_patterns()

        logger.info("✅ QueryRouter initialisé (100% config-driven)")

    def _compile_patterns(self):
        """Compile les regex depuis les configs pour performance"""

        # BREEDS - Pattern dynamique depuis index
        if self.config.breed_index:
            # Trier par longueur décroissante pour matcher les plus longs d'abord
            breed_aliases = sorted(
                self.config.breed_index.keys(), key=len, reverse=True
            )
            breed_pattern = "|".join(re.escape(alias) for alias in breed_aliases)
            self.breed_regex = re.compile(rf"\b({breed_pattern})\b", re.IGNORECASE)
        else:
            self.breed_regex = None

        # AGE - Pattern universel multi-langues
        self.age_regex = re.compile(
            r"\b(\d+)\s*(jour|day|semaine|week|día|días|tag|tage|settimana|settimane|"
            r"semana|semanas|j\b|d\b|sem|wk|w\b)s?\b",
            re.IGNORECASE,
        )

        # SEMAINES - Priorité sur jours (conversion x7)
        self.weeks_regex = re.compile(
            r"\b(\d+)\s*(semaine|week|semana|settimana|woche|wk|w\b)s?\b", re.IGNORECASE
        )

        # SEX - Pattern dynamique depuis index
        if self.config.sex_index:
            sex_aliases = sorted(self.config.sex_index.keys(), key=len, reverse=True)
            sex_pattern = "|".join(re.escape(alias) for alias in sex_aliases)
            self.sex_regex = re.compile(rf"\b({sex_pattern})\b", re.IGNORECASE)
        else:
            self.sex_regex = None

        logger.debug("✅ Patterns regex compilés depuis config")

    def detect_domain(self, query: str, language: str = "fr") -> str:
        """
        Détecte le domaine de la query pour sélection du prompt

        Args:
            query: Question de l'utilisateur
            language: Langue (fr/en)

        Returns:
            prompt_key du domaine détecté ou 'general_poultry'
        """
        if not self.domain_keywords or "domains" not in self.domain_keywords:
            return "general_poultry"

        query_lower = query.lower()
        domain_scores = {}

        # Compter les keywords matchés par domaine
        for domain_name, domain_data in self.domain_keywords["domains"].items():
            keywords = domain_data.get("keywords", {}).get(language, [])
            if not keywords:
                keywords = domain_data.get("keywords", {}).get("fr", [])

            matches = sum(1 for kw in keywords if kw.lower() in query_lower)
            if matches > 0:
                domain_scores[domain_name] = {
                    "score": matches,
                    "prompt_key": domain_data.get("prompt_key", "general_poultry"),
                }

        # Pas de match: fallback
        if not domain_scores:
            logger.debug(f"Aucun domaine détecté pour '{query}', fallback general_poultry")
            return "general_poultry"

        # Prendre le domaine avec le plus de matches
        best_domain = max(domain_scores.items(), key=lambda x: x[1]["score"])
        prompt_key = best_domain[1]["prompt_key"]

        logger.info(
            f"Domaine détecté: {best_domain[0]} (score={best_domain[1]['score']}) → prompt={prompt_key}"
        )

        # Appliquer règles de priorité si plusieurs domaines
        if len(domain_scores) > 1:
            prompt_key = self._apply_priority_rules(domain_scores, prompt_key)

        return prompt_key

    def _apply_priority_rules(
        self, domain_scores: Dict, current_prompt: str
    ) -> str:
        """
        Applique les règles de priorité entre domaines

        Args:
            domain_scores: Scores par domaine
            current_prompt: Prompt actuellement sélectionné

        Returns:
            Prompt ajusté selon règles de priorité
        """
        priority_rules = self.domain_keywords.get("priority_rules", {}).get("rules", [])

        for rule in priority_rules:
            condition = rule.get("condition", "")
            domains_in_condition = [d.strip() for d in condition.split("+")]

            # Vérifier si les 2 domaines sont présents
            if all(d in domain_scores for d in domains_in_condition):
                priority_domain = rule.get("priority")
                if priority_domain in domain_scores:
                    new_prompt = domain_scores[priority_domain]["prompt_key"]
                    logger.info(
                        f"Priorité appliquée: {condition} → {priority_domain} ({rule.get('reason')})"
                    )
                    return new_prompt

        return current_prompt

    def route(self, query: str, user_id: str, language: str = "fr") -> QueryRoute:
        """
        Point d'entrée UNIQUE - fait TOUT en une passe

        Args:
            query: Requête utilisateur
            user_id: Identifiant utilisateur/tenant
            language: Langue détectée

        Returns:
            QueryRoute avec destination + entités complètes
        """

        start_time = time.time()

        # 1. CONTEXTE: Charger si existe
        previous_context = self.context_store.get(user_id)

        # Nettoyer contextes expirés
        if previous_context and previous_context.is_expired():
            logger.info(f"🗑️ Contexte expiré pour {user_id}, suppression")
            del self.context_store[user_id]
            previous_context = None

        # 2. DÉTECTION CONTEXTUELLE
        is_contextual = self._is_contextual(query, language)

        # 3. EXTRACTION ENTITÉS
        entities = self._extract_entities(query, language)

        # 4. MERGE si contextuel
        if is_contextual and previous_context:
            original_entities = entities.copy()
            entities = self._merge_with_context(entities, previous_context.entities)
            logger.info(f"✅ Contexte mergé pour {user_id}")
            logger.debug(f"   Original: {original_entities}")
            logger.debug(f"   Previous: {previous_context.entities}")
            logger.debug(f"   Merged: {entities}")

        # 5. VALIDATION COMPLÉTUDE
        is_complete, missing, validation_details = self._validate_completeness(
            entities, query, language
        )

        if not is_complete:
            return QueryRoute(
                destination="needs_clarification",
                entities=entities,
                route_reason="missing_required_fields",
                missing_fields=missing,
                validation_details=validation_details,
                is_contextual=is_contextual,
                confidence=0.5,
            )

        # 6. ROUTING INTELLIGENT
        destination, reason = self._determine_destination(query, entities, language)

        # 6.5. DÉTECTION DOMAINE pour sélection prompt
        detected_domain = self.detect_domain(query, language)

        # 7. STOCKAGE CONTEXTE (si succès)
        self.context_store[user_id] = ConversationContext(
            entities=entities, query=query, timestamp=time.time(), language=language
        )

        processing_time = time.time() - start_time

        logger.info(
            f"✅ Route: {destination} | Domain: {detected_domain} | Contextuel: {is_contextual} | "
            f"Temps: {processing_time:.3f}s"
        )

        # Ajouter domain dans validation_details pour utilisation par generators
        validation_details["detected_domain"] = detected_domain

        return QueryRoute(
            destination=destination,
            entities=entities,
            route_reason=reason,
            is_contextual=is_contextual,
            validation_details=validation_details,
            confidence=1.0,
        )

    def _is_contextual(self, query: str, language: str) -> bool:
        """Détection de références contextuelles via universal_terms"""

        # Récupérer patterns depuis config
        patterns = self.config.get_contextual_patterns(language)

        if not patterns:
            # Fallback patterns multilingues si universal_terms incomplet
            fallback_patterns = {
                "fr": [
                    r"\bmême\b",
                    r"\bau même\b",
                    r"\bet pour\b",
                    r"\bfemelles?\b",
                    r"\bmâles?\b",
                ],
                "en": [
                    r"\bsame\b",
                    r"\bat the same\b",
                    r"\bwhat about\b",
                    r"\bfemales?\b",
                    r"\bmales?\b",
                ],
                "es": [
                    r"\bmismo\b",
                    r"\bal mismo\b",
                    r"\by para\b",
                    r"\bhembras?\b",
                    r"\bmachos?\b",
                ],
            }
            patterns = fallback_patterns.get(language, fallback_patterns["en"])

        query_lower = query.lower()
        for pattern in patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"🔗 Référence contextuelle détectée: '{pattern}'")
                return True

        return False

    def _extract_entities(self, query: str, language: str) -> Dict[str, Any]:
        """Extraction via regex compilés - PAS d'appel OpenAI"""

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

    def _calculate_confidence(self, entities: Dict) -> float:
        """Calcule la confiance d'extraction"""
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
        Merge intelligent: nouvelles valeurs OVERRIDE anciennes

        Logique:
        - Si nouvelle entité présente → utiliser nouvelle
        - Si nouvelle entité absente → hériter de l'ancienne
        """

        merged = previous_entities.copy()

        # Override avec nouvelles valeurs non-None
        for key, value in new_entities.items():
            if value is not None and value != "":
                merged[key] = value

        return merged

    def _validate_completeness(
        self, entities: Dict[str, Any], query: str, language: str
    ) -> Tuple[bool, List[str], Dict]:
        """
        Validation basée sur intents.json et type de requête

        Returns:
            (is_complete, missing_fields, validation_details)
        """

        missing = []
        validation_details = {}

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
            ambiguity_detected = self._detect_weaviate_ambiguity(query, entities, language)

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
        Détecte si une question Weaviate est trop ambiguë

        Returns:
            Liste des champs manquants ou []
        """
        query_lower = query.lower()
        missing = []

        # Santé/diagnostic: besoin symptômes + âge
        health_keywords = ["maladie", "malade", "symptôme", "mort", "mortalité", "disease", "sick", "mortality", "diagnostic"]
        if any(kw in query_lower for kw in health_keywords):
            # Question très vague (< 6 mots)
            if len(query_lower.split()) < 6:
                if not entities.get("age_days"):
                    missing.append("age")
                # Pas besoin de breed obligatoire pour Weaviate, mais mentionner si manque symptôme détaillé
                if "symptom" not in query_lower and "fèces" not in query_lower and "lésion" not in query_lower:
                    missing.append("symptom")

        # Nutrition: besoin phase de production
        nutrition_keywords = ["aliment", "ration", "formule", "nutrition", "feed", "diet"]
        if any(kw in query_lower for kw in nutrition_keywords):
            if len(query_lower.split()) < 6:
                if not entities.get("age_days"):
                    missing.append("production_phase")

        # Environnement: besoin âge
        environment_keywords = ["température", "ventilation", "ambiance", "humidité", "temperature", "climate"]
        if any(kw in query_lower for kw in environment_keywords):
            if len(query_lower.split()) < 7 and not entities.get("age_days"):
                missing.append("age")

        # Traitement/protocole: besoin âge
        protocol_keywords = ["protocole", "vaccin", "traitement", "antibiotique", "protocol", "vaccine", "treatment"]
        if any(kw in query_lower for kw in protocol_keywords):
            if not entities.get("age_days"):
                missing.append("age")

        return missing

    def _determine_destination(
        self, query: str, entities: Dict[str, Any], language: str
    ) -> Tuple[str, str]:
        """
        Routing intelligent basé sur keywords depuis universal_terms

        Returns:
            (destination, reason)
        """

        # PostgreSQL: métriques chiffrées
        if self.config.should_route_to_postgresql(query, language):
            return ("postgresql", "metrics_and_performance_data")

        # Weaviate: santé, environnement, guides
        if self.config.should_route_to_weaviate(query, language):
            return ("weaviate", "health_environment_guides")

        # Hybride: pas assez d'indices clairs
        return ("hybrid", "ambiguous_requires_both_sources")

    def clear_context(self, user_id: str):
        """Efface le contexte conversationnel d'un utilisateur"""
        if user_id in self.context_store:
            del self.context_store[user_id]
            logger.info(f"🗑️ Contexte effacé pour {user_id}")

    def get_context(self, user_id: str) -> Optional[ConversationContext]:
        """Récupère le contexte conversationnel"""
        return self.context_store.get(user_id)

    def get_stats(self) -> Dict:
        """Statistiques du router"""
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
    """Factory pour créer une instance QueryRouter"""
    return QueryRouter(config_dir)


def test_query_router():
    """Tests unitaires intégrés"""

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
