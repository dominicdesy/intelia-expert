# -*- coding: utf-8 -*-
"""
query_preprocessor.py - Préprocesseur de requêtes avec OpenAI
Version ENRICHIE avec détection patterns calculatoires, temporels, économiques
et amélioration de la détection du sexe avec correspondance stricte
🟠 CORRECTION: Ne plus écraser "male, female" pour les comparaisons
"""

import logging
import re
from openai import AsyncOpenAI
import json
from typing import Dict, Any, List, Optional

from .comparative_detector import ComparativeQueryDetector

logger = logging.getLogger(__name__)


class LocalEntityExtractor:
    """Extraction locale sans LLM pour requêtes simples"""

    BREED_PATTERNS = {
        r"(?:cobb|500)": "Cobb 500",
        r"(?:ross|308)": "Ross 308",
        r"(?:hubbard|ja87)": "Hubbard JA87",
    }

    METRIC_PATTERNS = {
        r"(?:poids|weight|masse)": "weight",
        r"(?:fcr|conversion|indice)": "fcr",
        r"(?:mortalité|mortality)": "mortality",
        r"(?:production|ponte)": "production",
    }

    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extraction rapide des entités communes"""
        entities = {"sex": "as_hatched"}
        query_lower = query.lower()

        # Breed detection
        for pattern, breed in self.BREED_PATTERNS.items():
            if re.search(pattern, query_lower):
                entities["breed"] = breed
                break

        # Age detection - patterns multiples
        age_patterns = [
            r"(\d+)\s*jours?",
            r"(\d+)\s*j\b",
            r"à \s+(\d+)\s*jours?",
            r"de\s+(\d+)\s*jours?",
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, query_lower)
            if age_match:
                entities["age_days"] = int(age_match.group(1))
                break

        # Metric detection
        for pattern, metric in self.METRIC_PATTERNS.items():
            if re.search(pattern, query_lower):
                entities["metric_type"] = metric
                break

        # Sex detection
        if re.search(r"\b(?:male|mâle|m)\b", query_lower):
            entities["sex"] = "male"
        elif re.search(r"\b(?:female|femelle|f)\b", query_lower):
            entities["sex"] = "female"

        return entities

    def is_extraction_sufficient(self, entities: Dict) -> bool:
        """Vérifie si l'extraction locale est suffisante"""
        # Considérer suffisant si on a breed + (age ou metric)
        has_breed = entities.get("breed") is not None
        has_age = entities.get("age_days") is not None
        has_metric = entities.get("metric_type") is not None

        return has_breed and (has_age or has_metric)


class QueryPreprocessor:
    """
    Préprocesse les requêtes utilisateur avec :
    - Correction des fautes de frappe
    - Normalisation de la terminologie
    - Extraction des métadonnées structurées
    - Détection des requêtes comparatives
    - Détection patterns calculatoires, temporels, optimisation, économiques
    - Amélioration de la détection du sexe avec correspondance stricte
    🟠 CORRECTION: Protection des comparaisons de sexe
    """

    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self._is_initialized = False
        self.comparative_detector = ComparativeQueryDetector()
        self.local_extractor = LocalEntityExtractor()
        self._cache = {}  # Cache pour éviter reprocessing

    async def initialize(self):
        """Initialisation et validation du preprocessor"""
        if not self.client:
            raise ValueError("OpenAI client is required for QueryPreprocessor")

        try:
            logger.info(
                "Initialisation du Query Preprocessor avec détection enrichie..."
            )
            self._is_initialized = True
            logger.info("Query Preprocessor initialisé avec succès")
            return self
        except Exception as e:
            logger.error(f"Erreur initialisation QueryPreprocessor: {e}")
            raise

    async def close(self):
        """Fermeture propre du preprocessor"""
        self._is_initialized = False
        self._cache.clear()  # Nettoyer le cache
        logger.debug("Query Preprocessor fermé")

    def extract_local_entities(self, query: str) -> Dict[str, Any]:
        """Extraction d'entités avec détection de sexe explicite améliorée"""

        entities = {}

        # Extraction du sexe avec détection explicite
        sex_info = self._extract_sex_with_explicit_detection(query)
        entities.update(sex_info)

        # Extraction de la race
        breed = self._extract_breed(query)
        if breed:
            entities["breed"] = breed

        # Extraction de l'âge
        age = self._extract_age_days(query)
        if age:
            entities["age_days"] = age

        # Extraction du type de métrique
        metric_type = self._extract_metric_type(query)
        if metric_type:
            entities["metric_type"] = metric_type

        return entities

    def _extract_sex_with_explicit_detection(self, query: str) -> Dict[str, Any]:
        """Extraction du sexe avec détection des demandes explicites"""

        result = {}
        query_lower = query.lower()

        # Patterns pour détection explicite
        explicit_female_patterns = [
            r"\bfemelle\b",
            r"\bfemale\b",
            r"\bpoule\b",
            r"\bpoulette\b",
        ]
        explicit_male_patterns = [r"\bmâle\b", r"\bmale\b", r"\bcoq\b", r"\bcockerel\b"]

        # Vérification des patterns explicites
        is_explicit_female = any(
            re.search(pattern, query_lower) for pattern in explicit_female_patterns
        )
        is_explicit_male = any(
            re.search(pattern, query_lower) for pattern in explicit_male_patterns
        )

        if is_explicit_female:
            result["sex"] = "female"
            result["explicit_sex_request"] = True
            logger.debug(f"Sexe femelle détecté explicitement dans: {query}")
        elif is_explicit_male:
            result["sex"] = "male"
            result["explicit_sex_request"] = True
            logger.debug(f"Sexe mâle détecté explicitement dans: {query}")
        else:
            # Patterns implicites plus faibles
            if re.search(r"\bof?\s+female\b|\bfemelle?\b", query_lower):
                result["sex"] = "female"
                result["explicit_sex_request"] = False
            elif re.search(r"\bof?\s+male\b|\bmâle?\b", query_lower):
                result["sex"] = "male"
                result["explicit_sex_request"] = False
            else:
                result["sex"] = "as_hatched"
                result["explicit_sex_request"] = False

        return result

    def _extract_breed(self, query: str) -> Optional[str]:
        """Extraction de la race/souche"""
        query_lower = query.lower()

        for pattern, breed in self.local_extractor.BREED_PATTERNS.items():
            if re.search(pattern, query_lower):
                return breed
        return None

    def _extract_age_days(self, query: str) -> Optional[int]:
        """Extraction de l'âge en jours"""
        query_lower = query.lower()

        age_patterns = [
            r"(\d+)\s*jours?",
            r"(\d+)\s*j\b",
            r"à \s+(\d+)\s*jours?",
            r"de\s+(\d+)\s*jours?",
            r"day\s+(\d+)",
            r"(\d+)\s+days?",
        ]

        for pattern in age_patterns:
            age_match = re.search(pattern, query_lower)
            if age_match:
                try:
                    age = int(age_match.group(1))
                    if 0 <= age <= 150:  # Validation range
                        return age
                except ValueError:
                    continue
        return None

    def _extract_metric_type(self, query: str) -> Optional[str]:
        """Extraction du type de métrique"""
        query_lower = query.lower()

        for pattern, metric in self.local_extractor.METRIC_PATTERNS.items():
            if re.search(pattern, query_lower):
                return metric
        return None

    async def preprocess_query(
        self, query: str, language: str = "fr"
    ) -> Dict[str, Any]:
        """
        AMÉLIORÉ: Preprocessing avec cache, extraction locale et classification améliorée
        avec gestion des demandes strictes

        Returns:
            {
                "normalized_query": str,
                "query_type": str,
                "entities": Dict,
                "routing": str,
                "confidence": float,
                "is_comparative": bool,
                "is_temporal_range": bool,
                "comparative_info": Dict,
                "requires_calculation": bool,
                "comparison_entities": List[Dict],
                "query_patterns": Dict,
                "strict_requirements": Dict
            }
        """

        # Cache check
        if query in self._cache:
            logger.debug(f"Cache hit pour: {query}")
            return self._cache[query]

        # Stocker la requête pour utilisation dans les corrections
        self._current_query = query

        try:
            # 1. Classification détaillée du type de requête (priorité haute)
            detailed_query_type = self._classify_detailed_query_type(query)
            logger.debug(f"Type de requête classifié: {detailed_query_type}")

            # 2. Essayer extraction locale d'abord (rapide) - NOUVELLE VERSION
            local_entities = self.extract_local_entities(query)
            logger.debug(f"Entités locales extraites: {local_entities}")

            # 3. Détection comparative (basée sur la classification)
            comparative_info = self.comparative_detector.detect(query)
            # Override si classification détecte comparaison
            if detailed_query_type == "comparative":
                comparative_info["is_comparative"] = True
                comparative_info["type"] = "comparative_detected"
            logger.debug(f"Détection comparative: {comparative_info}")

            # 4. Détection des patterns spéciaux
            query_patterns = self._detect_query_patterns(query)
            logger.debug(f"Patterns détectés: {query_patterns}")

            # 5. NOUVEAU: Analyser les demandes strictes
            strict_requirements = self._analyze_strict_requirements(
                query, local_entities
            )
            logger.debug(f"Exigences strictes: {strict_requirements}")

            # 6. Si extraction locale suffisante ET requête simple, utiliser directement
            if (
                self.local_extractor.is_extraction_sufficient(local_entities)
                and detailed_query_type in ["standard", "metric"]
                and not comparative_info["is_comparative"]
            ):

                logger.info(f"Utilisation extraction locale pour: {query}")
                result = self._build_local_result(
                    query,
                    local_entities,
                    query_patterns,
                    comparative_info,
                    detailed_query_type,
                    strict_requirements,
                )
                self._cache[query] = result
                return result

            # 7. Sinon, utiliser OpenAI pour cas complexes
            system_prompt = self._get_system_prompt(
                language, comparative_info["is_comparative"]
            )

            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query},
                    ],
                    temperature=0.1,
                    max_tokens=300,
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices[0].message.content)

                # Validation
                if "normalized_query" not in result:
                    logger.warning(
                        "Preprocessing incomplet, utilisation query originale"
                    )
                    result["normalized_query"] = query

                if "entities" not in result:
                    result["entities"] = {}

                # Post-traitement intelligent
                enhanced_result = self._enhance_openai_result(
                    result, query, comparative_info
                )

            except Exception as e:
                logger.warning(f"OpenAI normalization failed: {e}")
                enhanced_result = self._fallback_preprocessing(
                    query, comparative_info, query_patterns, strict_requirements
                )

            # 8. Validation et correction des entités - 🟠 CORRECTION ICI
            enhanced_result["entities"] = self._validate_and_fix_entities(
                enhanced_result["entities"],
                is_comparative=comparative_info.get("is_comparative", False),
            )
            logger.debug(f"Entités après validation: {enhanced_result['entities']}")

            # 9. Enrichir avec les informations de classification
            enhanced_result["query_type"] = detailed_query_type
            enhanced_result["routing"] = self._determine_routing(
                detailed_query_type, enhanced_result.get("routing")
            )
            enhanced_result["is_comparative"] = comparative_info["is_comparative"]
            enhanced_result["is_temporal_range"] = (
                detailed_query_type == "temporal_range"
            )
            enhanced_result["comparative_info"] = comparative_info
            enhanced_result["requires_calculation"] = (
                comparative_info["is_comparative"]
                or detailed_query_type == "temporal_range"
            )

            # 10. Ajouter les patterns détectés et les exigences strictes
            enhanced_result["query_patterns"] = query_patterns
            enhanced_result["strict_requirements"] = strict_requirements

            # 11. Si comparaison détectée, créer les entités multiples
            if comparative_info["is_comparative"]:
                enhanced_result["comparison_entities"] = (
                    self._build_comparison_entities(
                        comparative_info, enhanced_result["entities"]
                    )
                )
                logger.info(
                    f"Requête comparative détectée: {comparative_info['type']}, "
                    f"{len(enhanced_result['comparison_entities'])} jeux d'entités à rechercher"
                )

            # 12. Cache du résultat
            self._cache[query] = enhanced_result

            logger.info(
                f"Query preprocessed: '{query}' -> '{enhanced_result['normalized_query']}' (type: {detailed_query_type})"
            )
            logger.debug(f"Routing suggestion: {enhanced_result.get('routing')}")
            logger.debug(f"Entities detected: {enhanced_result['entities']}")
            logger.debug(f"Patterns: {query_patterns}")

            return enhanced_result

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON OpenAI: {e}")
            return self._fallback_preprocessing(
                query, comparative_info, query_patterns, strict_requirements
            )

        except Exception as e:
            logger.error(f"Erreur preprocessing OpenAI: {e}")
            return self._fallback_preprocessing(
                query, comparative_info, query_patterns, strict_requirements
            )
        finally:
            # Nettoyer la variable temporaire
            self._current_query = ""

    def _analyze_strict_requirements(
        self, query: str, entities: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Analyse si la requête nécessite des correspondances strictes"""

        strict_requirements = {
            "strict_sex_match": False,
            "strict_age_match": False,
            "strict_breed_match": False,
            "exclude_imperial_units": True,  # Par défaut, exclure les unités impériales
        }

        # Détection de demande de sexe stricte
        if entities.get("explicit_sex_request", False):
            strict_requirements["strict_sex_match"] = True
            logger.debug("Demande de correspondance sexe stricte détectée")

        # Mots-clés indiquant une demande précise
        precision_keywords = [
            "exactement",
            "précisément",
            "spécifiquement",
            "uniquement",
            "seulement",
            "exactly",
            "specifically",
            "only",
            "precisely",
        ]

        query_lower = query.lower()
        if any(keyword in query_lower for keyword in precision_keywords):
            strict_requirements.update(
                {
                    "strict_sex_match": True,
                    "strict_age_match": True,
                    "strict_breed_match": True,
                }
            )
            logger.debug("Demande de correspondance stricte détectée via mots-clés")

        # Détection d'âge précis (ex: "à 28 jours" vs "vers 28 jours")
        precise_age_patterns = [
            r"à \s+(\d+)\s+jours?",
            r"at\s+(\d+)\s+days?",
            r"day\s+(\d+)",
            r"jour\s+(\d+)",
        ]

        if any(re.search(pattern, query_lower) for pattern in precise_age_patterns):
            strict_requirements["strict_age_match"] = True
            logger.debug("Demande d'âge précis détectée")

        return strict_requirements

    def _normalize_query_text(self, query: str) -> str:
        """Normalise le texte de la requête"""

        # Corrections orthographiques communes
        corrections = {
            "IC": "conversion alimentaire",
            "FCR": "conversion alimentaire",
            "poid": "poids",
            "convertion": "conversion",
            "aliment": "alimentaire",
        }

        normalized = query
        for wrong, correct in corrections.items():
            normalized = re.sub(
                rf"\b{re.escape(wrong)}\b", correct, normalized, flags=re.IGNORECASE
            )

        # Nettoyage basique
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def should_use_strict_matching(self, preprocessing_result: Dict[str, Any]) -> bool:
        """Détermine si les requêtes doivent utiliser la correspondance stricte"""

        strict_reqs = preprocessing_result.get("strict_requirements", {})

        # Si une demande stricte est détectée
        if any(strict_reqs.values()):
            return True

        # Si c'est une requête comparative, moins strict par défaut
        if preprocessing_result.get("comparative_info", {}).get(
            "is_comparative", False
        ):
            return False

        # Par défaut, modérément strict
        return preprocessing_result.get("entities", {}).get(
            "explicit_sex_request", False
        )

    # ========================================================================
    # MÉTHODE MODIFIÉE: Classification détaillée des requêtes
    # ========================================================================

    def _classify_detailed_query_type(self, query: str) -> str:
        """
        Classification détaillée des types de requêtes avec priorité hiérarchique
        MODIFICATION: "meilleur" déplacé vers optimization au lieu de comparative

        Returns:
            - "temporal_range": requêtes d'évolution temporelle (entre X et Y jours)
            - "comparative": requêtes de comparaison (vs, différence explicite)
            - "recommendation": requêtes de conseil/recommandation
            - "calculation": requêtes de calcul/projection
            - "optimization": requêtes d'optimisation (inclut "meilleur")
            - "standard": requêtes métriques simples
            - "document": requêtes documentaires/explicatives
            - "general": requêtes générales
        """
        query_lower = query.lower()

        # 1. PRIORITÉ HAUTE: Requêtes temporelles (évolution dans le temps)
        temporal_patterns = [
            r"évolu\w*",  # évolution, évolue
            r"entre\s+\d+\s+et\s+\d+",  # "entre 21 et 42 jours"
            r"de\s+\d+\s+à\s+\d+",  # "de 21 à 42 jours"
            r"from\s+\d+\s+to\s+\d+",  # "from 21 to 42 days"
            r"progression",  # progression
            r"courbe",  # courbe de croissance
            r"suivi",  # suivi dans le temps
        ]
        if any(re.search(pattern, query_lower) for pattern in temporal_patterns):
            return "temporal_range"

        # 2. PRIORITÉ HAUTE: Requêtes comparatives (mots-clés EXPLICITES uniquement)
        # MODIFICATION: Retrait de "meilleur" qui est une requête d'optimization
        comparative_patterns = [
            r"\bdifférence\b",  # différence
            r"\bcompare\w*\b",  # compare, comparaison
            r"\bversus\b|\bvs\b",  # versus, vs
            r"\bentre\s+\w+\s+et\s+\w+\b",  # "entre Cobb et Ross"
            r"\bmieux\b",  # mieux
            r"\bplus\s+\w+\s+que\b",  # "plus lourd que"
            r"\bmoins\s+\w+\s+que\b",  # "moins que"
        ]
        if any(re.search(pattern, query_lower) for pattern in comparative_patterns):
            return "comparative"

        # 3. Requêtes de recommandation/conseil
        recommendation_patterns = [
            r"\brecommande\w*\b",  # recommande, recommandation
            r"\bconseil\w*\b",  # conseil, conseille
            r"\bsuggère\w*\b",  # suggère, suggestion
            r"\bchoisir\b",  # choisir
            r"\bquel\w*\s+\w+\s+choisir\b",  # "quelle souche choisir"
            r"\bque\s+me\s+\w+\b",  # "que me conseillez"
        ]
        if any(re.search(pattern, query_lower) for pattern in recommendation_patterns):
            return "recommendation"

        # 4. Requêtes de calcul/projection
        calculation_patterns = [
            r"\bcalcul\w*\b",  # calcul, calculer
            r"\bprojection\b",  # projection
            r"\bprojette\w*\b",  # projette
            r"\bestim\w*\b",  # estime, estimation
            r"\btotal\w*\b",  # total, totaux
            r"\bsomme\b",  # somme
            r"\bcombien\b",  # combien
        ]
        if any(re.search(pattern, query_lower) for pattern in calculation_patterns):
            return "calculation"

        # 5. Requêtes d'optimisation
        # MODIFICATION: Ajout de "meilleur", "choisir", "recommande"
        optimization_patterns = [
            r"\boptimal\w*\b",  # optimal, optimiser
            r"\bidéal\w*\b",  # idéal, idéale
            r"\bmeilleur\w*\b",  # meilleur, meilleure (DÉPLACÉ ICI)
            r"\bchoisir\b",  # choisir (AJOUTÉ)
            r"\brecommande\w*\b",  # recommande (AJOUTÉ pour renforcer)
            r"\bperfect\w*\b",  # perfect, perfection
            r"\bmaximis\w*\b",  # maximiser
            r"\bminimiis\w*\b",  # minimiser
            r"\baméliorer\b",  # améliorer
        ]
        if any(re.search(pattern, query_lower) for pattern in optimization_patterns):
            return "optimization"

        # 6. Requêtes documentaires/explicatives
        document_patterns = [
            r"\bcomment\b",  # comment
            r"\bpourquoi\b",  # pourquoi
            r"\bexplique\w*\b",  # explique, explication
            r"\bqu'?est-ce\s+que\b",  # qu'est-ce que
            r"\bmaladie\w*\b",  # maladie, maladies
            r"\bsymptôme\w*\b",  # symptôme, symptômes
            r"\btraitement\w*\b",  # traitement
            r"\bguide\b",  # guide
            r"\bprocédure\w*\b",  # procédure
        ]
        if any(re.search(pattern, query_lower) for pattern in document_patterns):
            return "document"

        # 7. Requêtes métriques standard (avec entités spécifiques)
        metric_patterns = [
            r"\b(?:poids|weight|fcr|conversion|mortalité|mortality)\b",
            r"\b(?:cobb|ross|hubbard)\b",  # Breeds mentionnées
            r"\b\d+\s*(?:jours?|days?|j)\b",  # Âges mentionnés
        ]
        if any(re.search(pattern, query_lower) for pattern in metric_patterns):
            return "standard"

        # 8. Par défaut: requête générale
        return "general"

    def _determine_routing(
        self, query_type: str, existing_routing: Optional[str] = None
    ) -> str:
        """
        Détermine le routage optimal basé sur le type de requête classifié
        """
        # Si un routage existe déjà et semble approprié, le conserver
        if existing_routing in ["postgresql", "weaviate"]:
            return existing_routing

        # Routage basé sur la classification
        routing_map = {
            "temporal_range": "postgresql",  # Données temporelles → DB
            "comparative": "postgresql",  # Comparaisons → DB
            "recommendation": "postgresql",  # Recommandations basées sur données
            "calculation": "postgresql",  # Calculs → DB
            "optimization": "postgresql",  # Optimisation → DB
            "standard": "postgresql",  # Métriques → DB
            "document": "weaviate",  # Documents → Vector DB
            "general": "weaviate",  # Général → Vector DB
        }

        return routing_map.get(query_type, "postgresql")  # PostgreSQL par défaut

    # ========================================================================
    # MÉTHODE MISE À JOUR: Construction de résultat local
    # ========================================================================

    def _build_local_result(
        self,
        query: str,
        local_entities: Dict,
        query_patterns: Dict,
        comparative_info: Dict,
        query_type: str,
        strict_requirements: Dict,
    ) -> Dict[str, Any]:
        """
        Construit un résultat complet à partir de l'extraction locale avec classification
        """
        # Validation et enrichissement des entités locales
        validated_entities = self._validate_and_fix_entities(
            local_entities, is_comparative=comparative_info.get("is_comparative", False)
        )

        # Routage intelligent basé sur le type de requête
        routing = self._determine_routing(query_type)

        # Normalisation du texte de la requête
        normalized_query = self._normalize_query_text(query)

        return {
            "normalized_query": normalized_query,
            "query_type": query_type,
            "entities": validated_entities,
            "routing": routing,
            "confidence": 0.8,  # Confiance élevée pour extraction locale réussie
            "is_comparative": comparative_info["is_comparative"]
            or query_type == "comparative",
            "is_temporal_range": query_type == "temporal_range",
            "comparative_info": comparative_info,
            "requires_calculation": (
                comparative_info["is_comparative"]
                or query_type in ["temporal_range", "calculation", "comparative"]
            ),
            "comparison_entities": (
                [validated_entities] if not comparative_info["is_comparative"] else []
            ),
            "query_patterns": query_patterns,
            "strict_requirements": strict_requirements,
            "preprocessing_method": "local_extraction",
            "processing_time_saved": True,
        }

    # ========================================================================
    # NOUVELLES MÉTHODES: Post-traitement et enrichissement
    # ========================================================================

    def _enhance_openai_result(
        self, openai_result: Dict, original_query: str, comparative_info: Dict
    ) -> Dict:
        """
        NOUVEAU: Post-traitement pour enrichir le résultat OpenAI
        """
        enhanced = openai_result.copy()

        # Enrichir pour requêtes de recommandation
        if any(
            word in original_query.lower()
            for word in ["meilleur", "recommande", "conseil"]
        ):
            if not enhanced.get("entities", {}).get("breed"):
                # Suggérer breeds populaires pour recommandations
                enhanced.setdefault("entities", {})[
                    "breed"
                ] = "Cobb 500, Ross 308, Hubbard JA87"
                enhanced["query_type"] = "recommendation"

        # Enrichir pour requêtes de comparaison
        if comparative_info["is_comparative"] and not enhanced.get("entities", {}).get(
            "breed"
        ):
            # Pour les comparaisons sans breed spécifique
            enhanced.setdefault("entities", {})["breed"] = "Cobb 500, Ross 308"
            enhanced["routing"] = "postgresql"  # Forcer PostgreSQL pour comparaisons

        # Enrichir le routage
        if not enhanced.get("routing"):
            # Routage intelligent basé sur le contenu
            if any(
                word in original_query.lower()
                for word in ["poids", "fcr", "conversion", "mortalité", "production"]
            ):
                enhanced["routing"] = "postgresql"
            elif any(
                word in original_query.lower()
                for word in ["comment", "pourquoi", "explique", "maladie"]
            ):
                enhanced["routing"] = "weaviate"
            else:
                # Défaut: PostgreSQL pour données numériques
                enhanced["routing"] = "postgresql"

        return enhanced

    # ========================================================================
    # 🟠 MÉTHODE CORRIGÉE: Validation des entités
    # ========================================================================

    def _validate_and_fix_entities(
        self, entities: Dict[str, Any], is_comparative: bool = False
    ) -> Dict[str, Any]:
        """
        🟠 CORRECTION CRITIQUE: Ne pas écraser les valeurs multiples pour les comparaisons

        Args:
            entities: Entités à valider
            is_comparative: True si c'est une requête comparative

        Returns:
            Entités validées
        """
        if not entities:
            entities = {}

        corrected = {}
        corrections_applied = []

        # 🟠 CORRECTION: Gestion spéciale pour les comparaisons
        sex_value = entities.get("sex")

        if is_comparative and isinstance(sex_value, str) and "," in sex_value:
            # GARDER les valeurs multiples pour les comparaisons
            corrected["sex"] = sex_value
            logger.debug(f"✅ Comparaison de sexe préservée: {sex_value}")
        elif sex_value is None or str(sex_value).lower() == "none":
            corrected["sex"] = "as_hatched"
            corrections_applied.append("sex 'None' → 'as_hatched'")
        else:
            # Normaliser les valeurs de sexe simples
            sex_lower = str(sex_value).lower()
            if sex_lower in ["m", "male", "mâle", "males"]:
                corrected["sex"] = "male"
            elif sex_lower in ["f", "female", "femelle", "females"]:
                corrected["sex"] = "female"
            elif sex_lower in ["as_hatched", "as-hatched", "mixed", "mixte"]:
                corrected["sex"] = "as_hatched"
            else:
                corrected["sex"] = "as_hatched"
                corrections_applied.append(f"sex '{sex_value}' → 'as_hatched'")

        # Préserver l'information explicit_sex_request si elle existe
        if entities.get("explicit_sex_request") is not None:
            corrected["explicit_sex_request"] = entities["explicit_sex_request"]

        # Correction breed - NOUVEAU: Suggestions pour requêtes générales
        if entities.get("breed"):
            corrected["breed"] = entities["breed"]
        else:
            # NOUVEAU: Pour requêtes générales, suggérer breeds populaires
            query_context = getattr(self, "_current_query", "").lower()
            if any(
                word in query_context
                for word in ["meilleur", "recommande", "compare", "différence"]
            ):
                # Pour requêtes comparatives/recommandations, suggérer plusieurs races
                corrected["breed"] = "Cobb 500, Ross 308"  # Breeds les plus populaires
                corrections_applied.append("breed suggéré pour requête générale")
            # Sinon, laisser vide pour validation flexible

        # Correction âge
        if entities.get("age_days"):
            age_val = entities["age_days"]
            if isinstance(age_val, str) and age_val.lower() in ["as_hatched", "none"]:
                corrected["age_days"] = None
                corrections_applied.append(f"age_days '{age_val}' → None")
            else:
                try:
                    corrected["age_days"] = int(age_val)
                except (ValueError, TypeError):
                    corrected["age_days"] = None
                    corrections_applied.append(f"age_days '{age_val}' → None (invalid)")
        else:
            # NOUVEAU: Suggestion d'âge pour certains contextes
            query_context = getattr(self, "_current_query", "").lower()
            if any(word in query_context for word in ["abattage", "finition", "final"]):
                corrected["age_days"] = 42  # Âge d'abattage standard
                corrections_applied.append("age_days suggéré (42j pour finition)")
            elif any(
                word in query_context for word in ["démarrage", "starter", "début"]
            ):
                corrected["age_days"] = 21  # Phase démarrage
                corrections_applied.append("age_days suggéré (21j pour démarrage)")

        # Correction metric_type - NOUVEAU: Détection améliorée
        if entities.get("metric_type"):
            # Normaliser les types de métriques
            metric = str(entities["metric_type"]).lower()
            metric_mapping = {
                "poids": "weight",
                "weight": "weight",
                "masse": "weight",
                "fcr": "fcr",
                "conversion": "fcr",
                "ic": "fcr",
                "indice": "fcr",
                "mortalité": "mortality",
                "mortality": "mortality",
                "production": "production",
                "ponte": "production",
                "œuf": "production",
                "alimentation": "feed",
                "feed": "feed",
            }
            corrected["metric_type"] = metric_mapping.get(metric, metric)
        else:
            # NOUVEAU: Détecter métrique depuis le contexte de la requête
            query_context = getattr(self, "_current_query", "").lower()
            if any(word in query_context for word in ["poids", "weight", "masse"]):
                corrected["metric_type"] = "weight"
                corrections_applied.append("metric_type détecté: weight")
            elif any(word in query_context for word in ["fcr", "conversion", "indice"]):
                corrected["metric_type"] = "fcr"
                corrections_applied.append("metric_type détecté: fcr")
            elif any(word in query_context for word in ["mortalité", "mortality"]):
                corrected["metric_type"] = "mortality"
                corrections_applied.append("metric_type détecté: mortality")

        # Copier autres entités non modifiées
        for key, value in entities.items():
            if key not in corrected:
                corrected[key] = value

        # Log des corrections
        if corrections_applied:
            original_keys = list(entities.keys()) if entities else []
            corrected_keys = list(corrected.keys())
            logger.info(f"Entités corrigées: {original_keys} → {corrected_keys}")
            for correction in corrections_applied:
                logger.debug(f"Correction: {correction}")

        return corrected

    # ========================================================================
    # MÉTHODES CORRIGÉES: Détection de patterns spéciaux
    # ========================================================================

    def _detect_query_patterns(self, query: str) -> Dict[str, Any]:
        """
        Version corrigée avec patterns d'âge robustes

        Détecte les patterns spéciaux dans la requête

        Returns:
            {
                "is_calculation": bool,
                "is_temporal_reverse": bool,
                "is_optimization": bool,
                "is_economic": bool,
                "is_planning": bool,
                "extracted_age": int,
                "calculation_type": str,
                "flock_size": int,
                "target_value": float
            }
        """

        # NOUVEAUX patterns d'âge plus robustes
        age_patterns = [
            r"à \s+(\d+)\s+jours?",  # "à 42 jours"
            r"(\d+)\s+jours?",  # "42 jours"
            r"de\s+(\d+)\s+jours?",  # "de 42 jours"
            r"(\d+)\s*j\b",  # "42j"
            r"day\s+(\d+)",  # "day 42"
            r"(\d+)\s+days?",  # "42 days"
            r"(\d+)-?jours?",  # "42-jours"
            r"(\d+)\s+semaines?",  # "6 semaines" → *7
        ]

        query_lower = query.lower()
        extracted_age = None

        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    age = int(match.group(1))
                    # Conversion semaines → jours si nécessaire
                    if "semaine" in pattern:
                        age = age * 7
                    if 0 <= age <= 150:  # Validation range
                        extracted_age = age
                        logger.debug(
                            f"Age détecté: {age} jours via pattern '{pattern}'"
                        )
                        break
                except ValueError:
                    continue

        patterns = {
            "is_calculation": self._is_calculation_query(query_lower),
            "is_temporal_reverse": self._is_temporal_reverse_query(query_lower),
            "is_optimization": self._is_optimization_query(query_lower),
            "is_economic": self._is_economic_query(query_lower),
            "is_planning": self._is_planning_query(query_lower),
            "extracted_age": extracted_age,
        }

        # Extraire informations additionnelles
        if patterns["is_calculation"]:
            patterns["calculation_type"] = self._identify_calculation_type(query_lower)

        if patterns["is_planning"]:
            patterns["flock_size"] = self._extract_flock_size(query)

        if patterns["is_temporal_reverse"]:
            patterns["target_value"] = self._extract_target_value(query)

        return patterns

    def _is_calculation_query(self, query_lower: str) -> bool:
        """Détecte requêtes nécessitant des calculs"""
        calculation_keywords = [
            "projette",
            "projection",
            "calcul",
            "calculer",
            "total",
            "totaux",
            "somme",
            "entre",
            "de X à Y",
            "from X to Y",
            "combien",
            "how much",
            "how many",
        ]
        return any(keyword in query_lower for keyword in calculation_keywords)

    def _is_temporal_reverse_query(self, query_lower: str) -> bool:
        """Détecte requêtes de recherche inversée (valeur → âge)"""
        reverse_patterns = [
            "quel âge",
            "à quel âge",
            "combien de jours",
            "quand atteint",
            "when reach",
            "at what age",
            "pour atteindre",
            "to reach",
        ]
        return any(pattern in query_lower for pattern in reverse_patterns)

    def _is_optimization_query(self, query_lower: str) -> bool:
        """Détecte requêtes d'optimisation"""
        optimization_keywords = [
            "optimal",
            "optimis",
            "meilleur",
            "best",
            "maximis",
            "minimis",
            "maximize",
            "minimize",
            "idéal",
            "ideal",
        ]
        return any(keyword in query_lower for keyword in optimization_keywords)

    def _is_economic_query(self, query_lower: str) -> bool:
        """Détecte requêtes économiques"""
        economic_keywords = [
            "coût",
            "cout",
            "cost",
            "prix",
            "price",
            "rentabilité",
            "rentabilite",
            "profitability",
            "marge",
            "margin",
            "roi",
            "€",
            "$",
            "dollar",
            "euro",
        ]
        return any(keyword in query_lower for keyword in economic_keywords)

    def _is_planning_query(self, query_lower: str) -> bool:
        """Détecte requêtes de planification de troupeau"""
        planning_patterns = [
            r"\d+[\s,]?\d{3}.*poulet",
            r"\d+[\s,]?\d{3}.*bird",
            r"pour \d+.*oiseaux",
            r"for \d+.*chickens",
        ]
        return any(re.search(pattern, query_lower) for pattern in planning_patterns)

    def _identify_calculation_type(self, query_lower: str) -> str:
        """Identifie le type de calcul demandé"""
        if "projection" in query_lower or "projette" in query_lower:
            return "projection"
        elif "total" in query_lower or "somme" in query_lower:
            return "total"
        elif "entre" in query_lower or "from" in query_lower:
            return "range_calculation"
        elif "taux" in query_lower or "rate" in query_lower:
            return "rate_calculation"
        else:
            return "general_calculation"

    def _extract_flock_size(self, query: str) -> Optional[int]:
        """Extrait la taille du troupeau"""
        numbers = re.findall(r"\b(\d{1,3}(?:[,\s]\d{3})*|\d+)\b", query)
        for num_str in numbers:
            num = int(num_str.replace(",", "").replace(" ", ""))
            if num > 100:  # Probablement taille de troupeau
                return num
        return None

    def _extract_target_value(self, query: str) -> Optional[float]:
        """Extrait valeur cible pour recherche inversée"""
        # Chercher patterns comme "2000g", "3kg", "1.5"
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:kg|g|grammes?|kilos?)",
            r"(\d+(?:\.\d+)?)\s*(?=\s|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    # ========================================================================
    # MÉTHODE CORRIGÉE: Construction des entités de comparaison
    # ========================================================================

    def _build_comparison_entities(
        self, comparative_info: Dict[str, Any], base_entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Construit les jeux d'entités pour comparaisons"""

        entity_sets = []

        if not comparative_info.get("entities"):
            logger.debug(
                "Aucune entité comparative détectée, utilisation entités de base"
            )
            return [base_entities]

        # Traiter chaque dimension de comparaison
        for comp_entity in comparative_info["entities"]:
            dimension = comp_entity.get("dimension")
            values = comp_entity.get("values", [])

            logger.debug(f"Traitement dimension {dimension} avec valeurs: {values}")

            # CORRECTION: Pour les comparaisons de sexe, créer des entités séparées
            if dimension == "sex" and len(values) >= 2:
                for sex_value in values:
                    entity_set = base_entities.copy()
                    entity_set["sex"] = sex_value
                    # IMPORTANT: Marquer comme demande explicite de sexe
                    entity_set["explicit_sex_request"] = True
                    entity_sets.append(entity_set)
                    logger.debug(f"Entité créée pour sexe: {sex_value}")

            # Pour les autres dimensions (breed, age, etc.)
            elif dimension == "breed" and len(values) >= 2:
                for breed_value in values:
                    entity_set = base_entities.copy()
                    entity_set["breed"] = breed_value.strip()
                    entity_sets.append(entity_set)
                    logger.debug(f"Entité créée pour race: {breed_value}")

            elif dimension == "age_days" and len(values) >= 2:
                for age_value in values:
                    entity_set = base_entities.copy()
                    try:
                        entity_set["age_days"] = int(age_value)
                        entity_sets.append(entity_set)
                        logger.debug(f"Entité créée pour âge: {age_value}")
                    except (ValueError, TypeError):
                        logger.warning(f"Âge invalide ignoré: {age_value}")

        # Si aucune entité de comparaison n'a été créée, retourner les entités de base
        if not entity_sets:
            logger.warning(
                "Aucune entité de comparaison valide, utilisation entités de base"
            )
            entity_sets = [base_entities]

        logger.info(f"Jeux d'entités construits: {len(entity_sets)}")
        return entity_sets

    # ========================================================================
    # MÉTHODE CORRIGÉE: Prompts système améliorés
    # ========================================================================

    def _get_system_prompt(self, language: str, is_comparative: bool) -> str:
        """Prompts spécialisés selon le type de requête"""

        comparative_instructions = ""
        if is_comparative:
            comparative_instructions = """
ATTENTION: Cette requête demande une COMPARAISON ou un CALCUL.
- Extrais TOUTES les valeurs à comparer (ex: mâle ET femelle, Ross ET Cobb)
- Identifie les dimensions de comparaison (sexe, âge, souche)
- Pour "Ross 308 vs Cobb 500" → breed: "Ross 308, Cobb 500"
- Pour "mâle vs femelle" → sex: "male, female"  
- Pour "21 jours vs 42 jours" → age_days: "21, 42"
- Ne privilégie pas une valeur par rapport à l'autre
"""

        if language == "fr":
            return f"""Tu es un assistant expert en aviculture qui normalise les requêtes utilisateur.

{comparative_instructions}

Tâches:
1. Corriger les fautes de frappe et orthographe
2. Normaliser la terminologie avicole (ex: "conversion aliment" → "conversion alimentaire")
3. Extraire les entités structurées:
   - breed: race/souche (ex: "Cobb 500", "Ross 308", "Cobb 500, Ross 308" pour comparaisons)
   - sex: sexe ("male", "female", "male, female" pour comparaisons, ou "as_hatched" si non spécifié)
   - age_days: âge en jours (nombre entier ou "21, 42" pour comparaisons)
   - metric_type: type de métrique (ex: "feed_conversion", "body_weight", "mortality")
4. Suggérer le routage optimal:
   - "postgresql" pour métriques chiffrées
   - "weaviate" pour documents/guides
5. Déterminer le type de requête:
   - "metric" pour données chiffrées
   - "document" pour guides/docs
   - "general" pour questions générales

IMPORTANT: 
- Si le sexe n'est PAS explicitement mentionné, utiliser "as_hatched"
- Pour les comparaisons, extraire TOUTES les entités mentionnées
- Pour "à 42 jours", extraire age_days: 42
- Pour "Ross vs Cobb", extraire breed: "Ross 308, Cobb 500"

Réponds en JSON:
{{
    "normalized_query": "requête corrigée",
    "query_type": "metric|document|general",
    "entities": {{
        "breed": "...",
        "sex": "male|female|as_hatched|male, female",
        "age_days": 17,
        "metric_type": "..."
    }},
    "routing": "postgresql|weaviate",
    "confidence": 0.95
}}"""

        else:  # English
            return f"""You are a poultry expert assistant that normalizes user queries.

{comparative_instructions}

Tasks:
1. Fix typos and spelling errors
2. Normalize poultry terminology
3. Extract structured entities:
   - breed: breed/strain name (ex: "Cobb 500, Ross 308" for comparisons)
   - sex: "male", "female", "male, female" for comparisons, or "as_hatched" if not specified
   - age_days: age in days (integer or "21, 42" for comparisons)
   - metric_type: metric type
4. Suggest optimal routing:
   - "postgresql" for numeric metrics
   - "weaviate" for documents/guides
5. Determine query type

IMPORTANT:
- If sex is NOT explicitly mentioned, use "as_hatched"
- For comparisons, extract ALL mentioned entities
- For "at 42 days", extract age_days: 42
- For "Ross vs Cobb", extract breed: "Ross 308, Cobb 500"

Respond in JSON:
{{
    "normalized_query": "corrected query",
    "query_type": "metric|document|general",
    "entities": {{...}},
    "routing": "postgresql|weaviate",
    "confidence": 0.95
}}"""

    def _fallback_preprocessing(
        self,
        query: str,
        comparative_info: Dict,
        query_patterns: Dict,
        strict_requirements: Dict,
    ) -> Dict[str, Any]:
        """
        AMÉLIORÉ: Preprocessing de secours avec détection locale
        """
        logger.warning("Utilisation du preprocessing de secours")

        # Détection locale de base
        detected_entities = {"sex": "as_hatched"}

        query_lower = query.lower()

        # Détection breed locale
        if any(word in query_lower for word in ["cobb", "500"]):
            detected_entities["breed"] = "Cobb 500"
        elif any(word in query_lower for word in ["ross", "308"]):
            detected_entities["breed"] = "Ross 308"
        elif any(word in query_lower for word in ["hubbard", "ja87"]):
            detected_entities["breed"] = "Hubbard JA87"

        # Détection âge locale
        import re

        age_match = re.search(r"(\d+)\s*(?:jours?|days?|j)", query_lower)
        if age_match:
            detected_entities["age_days"] = int(age_match.group(1))

        # Détection métrique locale
        if any(word in query_lower for word in ["poids", "weight"]):
            detected_entities["metric_type"] = "weight"
        elif any(word in query_lower for word in ["fcr", "conversion"]):
            detected_entities["metric_type"] = "fcr"

        # Routage local
        routing = "postgresql" if detected_entities.get("breed") else "weaviate"

        # CORRECTION: Construction des entités de comparaison dans le fallback
        comparison_entities = []
        if comparative_info.get("is_comparative", False):
            comparison_entities = self._build_comparison_entities(
                comparative_info, detected_entities
            )

        return {
            "normalized_query": self._normalize_query_text(query),
            "query_type": "general",
            "entities": detected_entities,
            "routing": routing,
            "confidence": 0.5,  # Confidence réduite pour fallback
            "is_comparative": comparative_info["is_comparative"],
            "comparative_info": comparative_info,
            "requires_calculation": comparative_info["is_comparative"],
            "comparison_entities": comparison_entities,
            "query_patterns": query_patterns,
            "strict_requirements": strict_requirements,
            "preprocessing_fallback": True,
        }

    def get_status(self) -> Dict[str, Any]:
        """Status du preprocessor"""
        return {
            "initialized": self._is_initialized,
            "comparative_detection": True,
            "pattern_detection": True,
            "local_extraction": True,
            "cache_enabled": True,
            "cache_size": len(self._cache),
            "strict_matching_support": True,
            "sex_explicit_detection": True,
            "supported_comparisons": list(
                self.comparative_detector.COMPARATIVE_PATTERNS.keys()
            ),
            "supported_patterns": [
                "calculation",
                "temporal_reverse",
                "optimization",
                "economic",
                "planning",
            ],
            "client_available": self.client is not None,
        }
