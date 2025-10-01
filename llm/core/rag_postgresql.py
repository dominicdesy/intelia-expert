# -*- coding: utf-8 -*-
"""
rag_postgresql.py - PostgreSQL System Principal Refactorisé
Point d'entrée principal avec délégation vers modules spécialisés
VERSION REFACTORISÉE: Utilisation de ValidationCore centralisé + QueryInterpreter OpenAI
CORRECTION: Support du paramètre language pour détection automatique
"""

import logging
import time
import json
from typing import Dict, List, Any

from .data_models import RAGResult, RAGSource

# Import des modules refactorisés
from .rag_postgresql_config import POSTGRESQL_CONFIG
from .rag_postgresql_models import MetricResult, QueryType
from .rag_postgresql_router import QueryRouter
from .rag_postgresql_retriever import PostgreSQLRetriever
from .rag_postgresql_validator import PostgreSQLValidator
from .rag_postgresql_temporal import TemporalQueryProcessor

# Import du module de validation centralisé
from .validation_core import ValidationCore

logger = logging.getLogger(__name__)


class QueryInterpreter:
    """Interprète les requêtes utilisateur avec OpenAI pour extraction précise des métriques"""

    def __init__(self, openai_client):
        self.openai_client = openai_client
        self.enabled = openai_client is not None

        # Mapping des métriques avec patterns explicites
        self.metric_keywords = {
            "feed_conversion_ratio": [
                "feed conversion ratio",
                "fcr",
                "indice de conversion",
                "conversion alimentaire",
                "taux de conversion",
                "ic ",
                "ratio de conversion",
                "conversion ratio",
            ],
            "cumulative_feed_intake": [
                "cumulative feed intake",
                "total feed",
                "feed intake",
                "consommation cumulée",
                "consommation totale",
                "aliment total",
                "quantité d'aliment",
                "besoin en aliment",
            ],
            "body_weight": [
                "body weight",
                "poids vif",
                "poids corporel",
                "weight",
                "masse corporelle",
            ],
            "daily_gain": [
                "daily gain",
                "gain quotidien",
                "gain journalier",
                "average daily gain",
                "adg",
                "gmq",
            ],
            "mortality": ["mortality", "mortalité", "taux de mortalité", "death rate"],
        }

    async def interpret_query(
        self, query: str, fallback_entities: Dict = None
    ) -> Dict[str, Any]:
        """
        Utilise OpenAI pour interpréter précisément la requête

        Args:
            query: Requête utilisateur
            fallback_entities: Entités détectées par le système classique (fallback)

        Returns:
            {
                "metric": "feed_conversion_ratio" | "cumulative_feed_intake" | ...,
                "breed": "Ross 308",
                "age_days": 31,
                "sex": "male",
                "confidence": 0.95,
                "interpretation_source": "openai" | "fallback" | "hybrid"
            }
        """

        if not self.enabled:
            logger.warning("QueryInterpreter disabled - OpenAI client not available")
            return self._fallback_interpretation(query, fallback_entities)

        try:
            logger.info("🤖 QueryInterpreter: Analyzing query with OpenAI...")

            system_prompt = """Tu es un expert en aviculture qui extrait les informations précises des requêtes.

MÉTRIQUES POSSIBLES (IMPORTANT - ne confonds JAMAIS) :
- feed_conversion_ratio : FCR, indice de conversion, conversion alimentaire, ratio de conversion
- cumulative_feed_intake : consommation cumulée, total feed intake, quantité totale d'aliment
- body_weight : poids vif, body weight, poids corporel
- daily_gain : gain quotidien, average daily gain, ADG, GMQ
- mortality : mortalité, taux de mortalité, death rate

RÈGLES CRITIQUES ABSOLUES :
1. Si la requête contient "feed conversion", "FCR", "indice de conversion", "conversion alimentaire" ou "ratio de conversion" → TOUJOURS feed_conversion_ratio
2. Si la requête contient "feed intake", "consommation", "total feed" SANS mention de "conversion" → cumulative_feed_intake  
3. Si la requête mentionne "conversion" OU "ratio" → TOUJOURS feed_conversion_ratio (priorité absolue)
4. Si ambiguïté entre FCR et feed intake, privilégier feed_conversion_ratio si "conversion" apparaît

RACES COMMUNES :
- Ross 308, Ross 708, Cobb 500, Cobb 700, Hubbard

SEXE :
- male, female, as_hatched (mixte)

Réponds UNIQUEMENT en JSON strict :
{
  "metric": "nom_métrique_exact",
  "breed": "nom_race",
  "age_days": nombre_entier,
  "sex": "male|female|as_hatched",
  "confidence": nombre_entre_0_et_1,
  "reasoning": "explication_courte"
}"""

            user_message = f"""Analyse cette requête avicole et extrais les informations :

REQUÊTE: "{query}"

Identifie avec précision :
1. La métrique demandée (feed_conversion_ratio vs cumulative_feed_intake - ATTENTION à ne pas confondre !)
2. La race/souche (Ross 308, Cobb 500, etc.)
3. L'âge en jours
4. Le sexe (male/female/as_hatched)

Réponds en JSON."""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,  # Très bas pour cohérence et déterminisme
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            result["interpretation_source"] = "openai"

            # Validation de la métrique extraite
            detected_metric = result.get("metric", "")
            if detected_metric not in self.metric_keywords:
                logger.warning(
                    f"⚠️ Métrique inconnue d'OpenAI: {detected_metric}, fallback"
                )
                return self._fallback_interpretation(query, fallback_entities)

            logger.info(
                f"✅ OpenAI interpretation: metric={result.get('metric')}, confidence={result.get('confidence')}"
            )
            logger.debug(f"Full OpenAI result: {result}")

            return result

        except Exception as e:
            logger.error(f"❌ Erreur interprétation OpenAI: {e}", exc_info=True)
            return self._fallback_interpretation(query, fallback_entities)

    def _fallback_interpretation(
        self, query: str, fallback_entities: Dict = None
    ) -> Dict[str, Any]:
        """Interprétation de secours basée sur mots-clés + entités existantes"""

        logger.info("🔄 Using fallback interpretation (keyword-based)")

        query_lower = query.lower()
        detected_metric = None
        confidence = 0.5

        # Détection par mots-clés avec priorité
        for metric, keywords in self.metric_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected_metric = metric
                    confidence = 0.7
                    break
            if detected_metric:
                break

        # Si FCR détecté par fallback, haute confiance
        if detected_metric == "feed_conversion_ratio":
            confidence = 0.85

        result = {
            "metric": detected_metric,
            "confidence": confidence,
            "interpretation_source": "fallback",
        }

        # Merger avec les entités existantes si disponibles
        if fallback_entities:
            if "breed" in fallback_entities:
                result["breed"] = fallback_entities["breed"]
            if "age_days" in fallback_entities:
                result["age_days"] = fallback_entities["age_days"]
            if "sex" in fallback_entities:
                result["sex"] = fallback_entities["sex"]

            result["interpretation_source"] = "hybrid"

        logger.debug(f"Fallback interpretation result: {result}")
        return result


class PostgreSQLSystem:
    """Système PostgreSQL principal avec architecture modulaire et interprétation OpenAI"""

    def __init__(self):
        # Modules core
        self.query_router = None
        self.postgres_retriever = None
        self.postgres_validator = None
        self.temporal_processor = None

        # 🆕 NOUVEAU: Query Interpreter avec OpenAI
        self.query_interpreter = None

        # Validation centralisée
        self.validator = ValidationCore()

        # État
        self.is_initialized = False
        self.openai_client = None

    async def initialize(self):
        """Initialisation modulaire du système PostgreSQL"""
        if self.is_initialized:
            return

        try:
            # Initialiser les modules core
            await self._initialize_core_modules()

            self.is_initialized = True
            logger.info("PostgreSQL System initialisé avec modules + QueryInterpreter")

        except Exception as e:
            logger.error(f"PostgreSQL System initialization error: {e}")
            self.is_initialized = False
            raise

    async def _initialize_core_modules(self):
        """Initialise les modules core"""
        self.query_router = QueryRouter()

        self.postgres_retriever = PostgreSQLRetriever(POSTGRESQL_CONFIG)
        await self.postgres_retriever.initialize()

        self.postgres_validator = PostgreSQLValidator()
        self.temporal_processor = TemporalQueryProcessor(self.postgres_retriever)

        # Initialiser OpenAI si disponible
        try:
            import openai
            import os

            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
            if OPENAI_API_KEY:
                self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

                # 🆕 Initialiser le QueryInterpreter avec le client OpenAI
                self.query_interpreter = QueryInterpreter(self.openai_client)

                logger.info("OpenAI client initialized")
                logger.info("✅ QueryInterpreter initialized with OpenAI")
            else:
                logger.warning("OPENAI_API_KEY not found - QueryInterpreter disabled")
                self.query_interpreter = QueryInterpreter(None)

        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")
            self.query_interpreter = QueryInterpreter(None)

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Route une requête"""
        if not self.query_router:
            return QueryType.KNOWLEDGE
        return self.query_router.route_query(query, intent_result)

    async def search_metrics(
        self,
        query: str,
        intent_result=None,
        top_k: int = 12,
        entities: Dict[str, Any] = None,
        strict_sex_match: bool = False,
        language: str = "en",  # ✅ AJOUTÉ: Paramètre language avec défaut anglais
    ) -> RAGResult:
        """
        Recherche de métriques avec validation centralisée + interprétation OpenAI
        VERSION REFACTORISÉE: Utilisation de ValidationCore + QueryInterpreter

        Args:
            query: Requête utilisateur
            intent_result: Résultat d'analyse d'intention (optionnel)
            top_k: Nombre maximum de résultats
            entities: Entités extraites (breed, age, sex, etc.)
            strict_sex_match: Forcer correspondance exacte du sexe
            language: Langue de réponse détectée automatiquement (en, fr, es, etc.)
        """

        if not self.is_initialized or not self.postgres_retriever:
            logger.warning("PostgreSQL retriever non initialisé")
            return RAGResult(
                source=RAGSource.ERROR, answer="Système de métriques non disponible."
            )

        start_time = time.time()

        try:
            # 🔍 LOG: Entités entrantes
            logger.debug(f"🔍 search_metrics INPUT entities: {entities}")
            logger.debug(
                f"🔍 INPUT - 'sex' present: {'sex' in (entities or {})}, value: {(entities or {}).get('sex')}"
            )
            logger.debug(f"🌍 search_metrics language parameter: {language}")

            # 🆕 ÉTAPE 1: Interprétation OpenAI de la requête
            if self.query_interpreter:
                logger.info("🤖 Step 1: OpenAI Query Interpretation")

                interpreted = await self.query_interpreter.interpret_query(
                    query, fallback_entities=entities
                )

                if interpreted and interpreted.get("confidence", 0) > 0.6:
                    # Enrichir/corriger les entités avec l'interprétation OpenAI
                    entities = entities or {}

                    # Merge intelligent : OpenAI override si haute confiance
                    if interpreted.get("confidence", 0) > 0.8:
                        logger.info(
                            f"✅ High confidence OpenAI interpretation (>{0.8}), using OpenAI entities"
                        )

                        if "metric" in interpreted and interpreted["metric"]:
                            entities["metric"] = interpreted["metric"]
                            logger.info(f"  → metric: {interpreted['metric']}")

                        if "breed" in interpreted and interpreted["breed"]:
                            entities["breed"] = interpreted["breed"]
                            logger.info(f"  → breed: {interpreted['breed']}")

                        if "age_days" in interpreted and interpreted["age_days"]:
                            # ✅ FIX: Garder age_days comme int si déjà int, sinon convertir
                            age_value = interpreted["age_days"]
                            entities["age_days"] = (
                                age_value
                                if isinstance(age_value, int)
                                else int(age_value)
                            )
                            logger.info(f"  → age_days: {entities['age_days']}")

                        if "sex" in interpreted and interpreted["sex"]:
                            # Préserver sex si explicitement demandé
                            if not entities.get("explicit_sex_request"):
                                entities["sex"] = interpreted["sex"]
                                logger.info(f"  → sex: {interpreted['sex']}")
                    else:
                        logger.info(
                            f"⚠️ Medium confidence OpenAI ({interpreted.get('confidence')}), hybrid merge"
                        )
                        # Merge partiel : seulement metric si manquant
                        if "metric" in interpreted and "metric" not in entities:
                            entities["metric"] = interpreted["metric"]

                    # Ajouter metadata d'interprétation
                    entities["_openai_interpretation"] = {
                        "confidence": interpreted.get("confidence"),
                        "source": interpreted.get("interpretation_source"),
                        "reasoning": interpreted.get("reasoning", ""),
                    }

                    logger.info(f"✅ Entities enriched by OpenAI: {entities}")

            # ÉTAPE 2: Validation des entités avec ValidationCore
            logger.info("🔍 Step 2: Entity Validation")
            validation_result = self.validator.validate_entities(entities or {})

            logger.debug(
                f"🔍 Validation result: valid={validation_result.is_valid}, confidence={validation_result.confidence}"
            )

            # Si validation échoue ET qu'on n'autorise pas les requêtes partielles
            if not validation_result.is_valid and not validation_result.allow_partial:
                error_message = "Validation échouée: " + ", ".join(
                    validation_result.errors
                )

                if validation_result.suggestions:
                    error_message += "\n\nSuggestions: " + ", ".join(
                        validation_result.suggestions
                    )

                return RAGResult(
                    source=RAGSource.ERROR,
                    answer=error_message,
                    metadata={
                        "validation_errors": validation_result.errors,
                        "suggestions": validation_result.suggestions,
                        "processing_time": time.time() - start_time,
                    },
                )

            # 🔧 ÉTAPE 3: Merge intelligent des entités
            logger.info("🔧 Step 3: Entity Merge Strategy")
            original_entities = entities or {}
            validated_entities = original_entities.copy()

            # Préserver les champs critiques
            critical_keys_to_preserve = [
                "sex",
                "explicit_sex_request",
                "_comparison_label",
                "_comparison_dimension",
            ]

            for key in critical_keys_to_preserve:
                if key in original_entities and original_entities[key] is not None:
                    validated_entities[key] = original_entities[key]
                    logger.debug(
                        f"🔍 PRESERVED critical key '{key}': {original_entities[key]}"
                    )

            entities = validated_entities

            # ÉTAPE 4: Vérification de disponibilité des données
            if self.postgres_validator:
                try:
                    availability_check = (
                        self.postgres_validator.check_data_availability_flexible(
                            entities
                        )
                    )

                    if availability_check and isinstance(availability_check, dict):
                        if not availability_check.get(
                            "available", True
                        ) and availability_check.get("alternatives"):
                            return RAGResult(
                                source=RAGSource.NO_RESULTS,
                                answer=availability_check.get(
                                    "helpful_response", "Données non disponibles"
                                ),
                                metadata={
                                    "processing_time": time.time() - start_time,
                                    "alternatives": availability_check.get(
                                        "alternatives", []
                                    ),
                                },
                            )
                except Exception as availability_error:
                    logger.warning(
                        f"Erreur vérification disponibilité: {availability_error}"
                    )

            # ÉTAPE 5: Détection de requête temporelle
            if self.temporal_processor:
                try:
                    temporal_range = self.temporal_processor.detect_temporal_range(
                        query, entities
                    )
                    if temporal_range:
                        logger.info(
                            f"Temporal range query detected: {temporal_range['age_min']}-{temporal_range['age_max']} days"
                        )
                        return await self.search_metrics_range(
                            query=query,
                            entities=entities,
                            age_min=temporal_range["age_min"],
                            age_max=temporal_range["age_max"],
                            top_k=top_k,
                            strict_sex_match=strict_sex_match,
                            language=language,  # ✅ TRANSMISSION DU LANGUAGE
                        )
                except Exception as temporal_error:
                    logger.warning(f"Erreur détection temporelle: {temporal_error}")

            # ÉTAPE 6: Exécution de la requête PostgreSQL
            logger.info("🔍 Step 6: PostgreSQL Query Execution")
            logger.debug(
                f"🔍 CALLING postgres_retriever.search_metrics with entities: {entities}"
            )

            metric_results = await self.postgres_retriever.search_metrics(
                query=query,
                entities=entities,
                top_k=top_k,
                strict_sex_match=strict_sex_match,
            )

            if not metric_results:
                return RAGResult(
                    source=RAGSource.NO_RESULTS,
                    answer="Aucune métrique trouvée pour cette requête.",
                    metadata={"processing_time": time.time() - start_time},
                )

            # ÉTAPE 7: Conversion et génération de réponse
            documents = self._convert_metrics_to_documents(metric_results)
            answer_text = await self._generate_response(
                query,
                documents,
                metric_results,
                entities,
                language,  # ✅ TRANSMISSION DU LANGUAGE
            )
            avg_confidence = sum(m.confidence for m in metric_results) / len(
                metric_results
            )

            logger.info(f"✅ PostgreSQL SUCCESS: {len(documents)} documents retrieved")

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=answer_text,
                context_docs=[doc.to_dict() for doc in documents],
                confidence=avg_confidence,
                metadata={
                    "source_type": "metrics",
                    "data_source": "postgresql",
                    "metric_count": len(metric_results),
                    "openai_interpretation": entities.get("_openai_interpretation"),
                    "validation_passed": validation_result.is_valid,
                    "processing_time": time.time() - start_time,
                },
            )

        except Exception as e:
            logger.error(f"PostgreSQL search error: {e}", exc_info=True)
            return RAGResult(
                source=RAGSource.ERROR,
                answer="Erreur lors de la recherche de métriques.",
                metadata={"error": str(e), "processing_time": time.time() - start_time},
            )

    async def search_metrics_range(
        self,
        query: str,
        entities: Dict[str, str],
        age_min: int,
        age_max: int,
        top_k: int = 12,
        strict_sex_match: bool = False,
        language: str = "en",  # ✅ AJOUTÉ: Paramètre language
    ) -> RAGResult:
        """Recherche optimisée pour plages temporelles"""

        if not self.temporal_processor:
            return await self.search_metrics(
                query,
                entities=entities,
                top_k=top_k,
                strict_sex_match=strict_sex_match,
                language=language,  # ✅ TRANSMISSION DU LANGUAGE
            )

        return await self.temporal_processor.search_metrics_range(
            query, entities, age_min, age_max, top_k, strict_sex_match
        )

    def _convert_metrics_to_documents(self, metric_results: List[MetricResult]) -> List:
        """Convertit les métriques en documents"""
        from .data_models import Document

        documents = []
        for metric in metric_results:
            try:
                content = self._format_metric_content(metric)
                doc = Document(
                    content=content,
                    metadata={
                        "strain": metric.strain,
                        "metric_name": metric.metric_name,
                        "sex": metric.sex,
                        "source_type": "metrics",
                    },
                    score=metric.confidence,
                    source_type="metrics",
                    retrieval_method="postgresql",
                )
                documents.append(doc)
            except Exception as e:
                logger.error(f"Document creation error: {e}")
                continue
        return documents

    def _format_metric_content(self, metric: MetricResult) -> str:
        """Formate une métrique en texte"""
        parts = [f"**{metric.metric_name}**", f"Strain: {metric.strain}"]

        if metric.sex:
            parts.append(f"Sex: {metric.sex}")

        if metric.value_numeric is not None:
            parts.append(f"Value: {metric.value_numeric} {metric.unit or ''}")

        if metric.age_min is not None:
            if metric.age_min == metric.age_max:
                parts.append(f"Age: {metric.age_min} days")
            else:
                parts.append(f"Age: {metric.age_min}-{metric.age_max} days")

        return "\n".join(parts)

    async def _generate_response(
        self,
        query: str,
        documents: List,
        metric_results: List[MetricResult],
        entities: Dict,
        language: str = "en",  # ✅ AJOUTÉ: Paramètre language avec défaut anglais
    ) -> str:
        """
        Génère une réponse enrichie avec EnhancedResponseGenerator

        Args:
            query: Requête utilisateur
            documents: Documents contextuels
            metric_results: Résultats métriques
            entities: Entités extraites
            language: Langue de réponse (en, fr, es, etc.)
        """

        if not metric_results:
            return f"Aucune donnée trouvée pour '{query}'."

        # Log pour debug
        logger.debug(f"🌍 _generate_response received language: {language}")

        # Utiliser le générateur enrichi si OpenAI disponible
        if self.openai_client:
            try:
                from generation.generators import create_enhanced_generator

                logger.info(
                    "🎨 Utilisation EnhancedResponseGenerator pour réponse de qualité"
                )

                # ✅ CORRECTION: Utiliser le paramètre language au lieu de "fr" hardcodé
                generator = create_enhanced_generator(
                    openai_client=self.openai_client,
                    cache_manager=None,
                    language=language,  # ✅ CORRIGÉ
                )

                # Générer réponse enrichie avec contexte
                # ✅ CORRECTION: Utiliser le paramètre language au lieu de "fr" hardcodé
                response = await generator.generate_response(
                    query=query,
                    context_docs=documents,
                    conversation_context="",
                    language=language,  # ✅ CORRIGÉ
                    intent_result=None,
                )

                logger.info("✅ Réponse générée par EnhancedResponseGenerator")
                return response

            except Exception as e:
                logger.warning(f"⚠️ Fallback sur génération basique: {e}")
                # Continuer avec fallback ci-dessous

        # Fallback : génération basique si OpenAI indisponible
        return self._generate_basic_response(metric_results, entities)

    def _generate_basic_response(
        self,
        metric_results: List[MetricResult],
        entities: Dict,
    ) -> str:
        """Génération basique de secours (fallback)"""

        best_metric = metric_results[0]

        # Formater le nom de la métrique
        metric_display_names = {
            "feed_conversion_ratio": "Feed Conversion Ratio (FCR)",
            "body_weight": "Poids vif",
            "daily_gain": "Gain quotidien",
            "feed_intake": "Consommation alimentaire cumulée",
            "mortality": "Mortalité",
        }

        metric_base = (
            best_metric.metric_name.split(" for ")[0]
            if " for " in best_metric.metric_name
            else best_metric.metric_name
        )
        metric_display = metric_display_names.get(metric_base, metric_base)

        # Formater la valeur
        if best_metric.value_numeric is not None:
            if "conversion" in metric_base.lower() or "fcr" in metric_base.lower():
                value_str = f"{best_metric.value_numeric:.2f}"
            elif "weight" in metric_base.lower() or "gain" in metric_base.lower():
                value_str = f"{best_metric.value_numeric:.0f}g"
            else:
                value_str = f"{best_metric.value_numeric:.2f}"

            if best_metric.unit and best_metric.unit not in value_str:
                value_str += f" {best_metric.unit}"
        else:
            value_str = best_metric.value_text or "N/A"

        # Sexe et âge
        sex_info = ""
        if best_metric.sex and best_metric.sex != "as_hatched":
            sex_labels = {"male": "mâles", "female": "femelles"}
            sex_info = f" ({sex_labels.get(best_metric.sex, best_metric.sex)})"

        age_info = ""
        if best_metric.age_min is not None:
            age_info = (
                f" à {best_metric.age_min} jours"
                if best_metric.age_min == best_metric.age_max
                else f" entre {best_metric.age_min}-{best_metric.age_max} jours"
            )

        breed_display = best_metric.strain.replace("/", " ")

        return f"**{metric_display}** pour Ross {breed_display}{sex_info}{age_info} : **{value_str}**"

    async def close(self):
        """Fermeture du système"""
        if self.postgres_retriever:
            await self.postgres_retriever.close()
        self.is_initialized = False

    def get_normalization_status(self) -> Dict[str, Any]:
        """Retourne le statut du système avec tous les modules"""
        if not self.postgres_retriever:
            return {"available": False}

        return {
            "available": True,
            "modules": {
                "query_router": bool(self.query_router),
                "postgres_retriever": bool(self.postgres_retriever),
                "postgres_validator": bool(self.postgres_validator),
                "temporal_processor": bool(self.temporal_processor),
                "validation_core": bool(self.validator),
                "query_interpreter": bool(self.query_interpreter),
            },
            "query_interpreter": {
                "enabled": (
                    self.query_interpreter.enabled if self.query_interpreter else False
                ),
                "description": "Interprétation intelligente des requêtes via OpenAI GPT-4",
                "features": [
                    "Distinction précise FCR vs Feed Intake",
                    "Extraction race/souche automatique",
                    "Détection âge et sexe",
                    "Score de confiance de l'interprétation",
                    "Fallback keyword-based si OpenAI indisponible",
                ],
                "status": (
                    "active"
                    if (self.query_interpreter and self.query_interpreter.enabled)
                    else "disabled"
                ),
            },
            "language_support": {
                "enabled": True,
                "description": "Support automatique de la langue détectée",
                "supported_languages": [
                    "en",
                    "fr",
                    "es",
                    "de",
                    "it",
                    "pt",
                    "nl",
                    "pl",
                    "zh",
                    "hi",
                    "th",
                    "id",
                ],
                "default": "en",
            },
            "sex_aware_search": True,
            "openai_enabled": self.openai_client is not None,
            "strict_sex_match_supported": True,
            "validation_centralized": {
                "applied": True,
                "description": "Validation centralisée via ValidationCore",
                "status": "active",
            },
            "temporal_optimization": {
                "applied": True,
                "description": "Optimisation SQL pour plages temporelles",
                "status": "active",
            },
            "implementation_phase": "modular_architecture_with_openai_interpreter_and_language_support",
            "version": "v10.1_language_detection_fixed",
        }
