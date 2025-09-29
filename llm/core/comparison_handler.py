# -*- coding: utf-8 -*-
"""
comparison_handler.py - Gestion des requêtes comparatives
VERSION CORRIGÉE : Validation renforcée, gestion d'erreur améliorée, fallback intelligent
"""

import logging
from typing import Dict, List, Any, Optional
from .metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class ComparisonHandler:
    """Gère les requêtes comparatives avec requêtes multiples et calculs"""

    def __init__(self, postgresql_system):
        """
        Args:
            postgresql_system: Instance de PostgreSQLSystem pour exécuter les requêtes
        """
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()

    def _parse_multiple_entities_from_preprocessing(
        self, preprocessed: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        CORRECTION: Parse les entités multiples depuis le preprocessing

        Problème détecté: Le preprocessing extrait "Ross 308, Cobb 500" mais
        le ComparisonHandler ne le parse pas correctement
        """
        entities_list = []

        # Récupérer les entités de base du preprocessing
        base_entities = preprocessed.get("entities", {})
        logger.debug(f"Base entities from preprocessing: {base_entities}")

        # Vérifier chaque champ pour des valeurs multiples séparées par des virgules
        comparison_found = False

        for field, value in base_entities.items():
            if isinstance(value, str) and "," in value:
                # Parser les valeurs multiples
                values = [v.strip() for v in value.split(",")]
                logger.debug(f"Field {field} has multiple values: {values}")

                if len(values) > 1:
                    comparison_found = True
                    # Créer une entité pour chaque valeur
                    for val in values:
                        entity_set = base_entities.copy()
                        entity_set[field] = val
                        entity_set["_comparison_label"] = val
                        entity_set["_comparison_dimension"] = field
                        entities_list.append(entity_set)
                    break  # Une seule dimension de comparaison à la fois

        # Si aucune comparaison détectée, utiliser les entités de base
        if not comparison_found:
            entities_list = [base_entities]
            logger.debug("No multiple entities found, using base entities")

        logger.info(f"Parsed {len(entities_list)} entity sets for comparison")
        return entities_list

    def handle_comparison_query(
        self, preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gère les requêtes comparatives avec support des entités séparées"""

        # Récupérer les entités de comparaison du preprocessing
        comparison_entities = preprocessed_data.get("comparison_entities", [])
        base_entities = preprocessed_data.get("entities", {})

        logger.debug(f"Entités de comparaison reçues: {len(comparison_entities)}")

        # NOUVEAU: Utiliser les entités séparées du preprocessing si disponibles
        if comparison_entities and len(comparison_entities) >= 2:
            entity_sets = comparison_entities
            logger.info(
                f"Utilisation des entités de comparaison du preprocessing: {len(entity_sets)} sets"
            )
        else:
            # Fallback: analyse traditionnelle des entités de base
            entity_sets = self._parse_comparison_entities(base_entities)
            logger.info(f"Analyse traditionnelle: {len(entity_sets)} sets")

        # Validation minimum pour comparaison
        if len(entity_sets) < 2:
            logger.warning(
                f"Comparaison nécessite au moins 2 entités, trouvé: {len(entity_sets)}"
            )
            return self._create_error_response(
                "Comparaison impossible avec une seule entité"
            )

        logger.info(f"Proceeding with comparison of {len(entity_sets)} entities")

        # Exécuter les requêtes pour chaque entité
        results = []
        for i, entity_set in enumerate(entity_sets):
            entity_name = self._generate_entity_name(entity_set, i)
            logger.debug(f"Executing query for {entity_name}")

            # CORRECTION: Assurer que strict_sex_match est activé pour comparaisons de sexe
            strict_sex_match = entity_set.get("explicit_sex_request", False)

            try:
                docs = await self.postgresql_system.search_metrics(
                    preprocessed_data.get("normalized_query", ""),
                    entity_set,
                    top_k=12,
                    strict_sex_match=strict_sex_match,  # IMPORTANT: Utiliser le flag
                )

                if docs and hasattr(docs, "context_docs") and docs.context_docs:
                    logger.debug(
                        f"Found {len(docs.context_docs)} results for {entity_name}"
                    )
                    results.append(
                        {
                            "entity_name": entity_name,
                            "entity_set": entity_set,
                            "docs": docs.context_docs,
                        }
                    )
                else:
                    logger.warning(f"No results found for {entity_name}")

            except Exception as e:
                logger.error(f"Query failed for {entity_name}: {e}")
                continue

        if len(results) < 2:
            return self._create_error_response(
                f"Données insuffisantes: {len(results)} entité(s) trouvée(s)"
            )

        # Comparaison des résultats
        try:
            comparison_result = self._compare_entities(results, preprocessed_data)
            return self._format_comparison_response(
                comparison_result, preprocessed_data
            )

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return self._create_error_response(f"Erreur de comparaison: {str(e)}")

    async def handle_comparative_query(
        self, query: str, preprocessed: Dict[str, Any], top_k: int = 12
    ) -> Dict[str, Any]:
        """
        CORRECTION: Version corrigée qui parse correctement les entités multiples

        Args:
            query: Requête utilisateur originale
            preprocessed: Résultat du preprocessing avec comparative_info
            top_k: Nombre de résultats par requête (augmenté à 12)

        Returns:
            {
                'results': List[Dict] | Dict[str, Any],  # Nouveau format ou ancien
                'comparison': ComparisonResult,
                'success': bool,
                'error': Optional[str],
                'context': Dict,
                'metadata': Dict  # NOUVEAU: métadonnées enrichies
            }
        """
        logger.info("Handling comparative query with preprocessed data")

        # NOUVEAU: Vérifier si c'est vraiment comparatif ou temporel
        if self._is_temporal_range_query(query):
            logger.info("Query detected as temporal range, not comparative")
            return {
                "success": False,
                "error": "Query is temporal, not comparative",
                "suggestion": "Use temporal handler instead",
                "query_type": "temporal",
                "results": [],
                "comparison": None,
            }

        # CORRECTION: Parser les entités depuis le preprocessing
        comparison_entities = self._parse_multiple_entities_from_preprocessing(
            preprocessed
        )

        if len(comparison_entities) < 2:
            logger.warning(
                f"Comparaison nécessite au moins 2 entités, trouvé: {len(comparison_entities)}"
            )
            return {
                "success": False,
                "error": "Comparaison impossible avec une seule entité",
                "entities_found": comparison_entities,
                "suggestion": "Vérifiez que votre requête contient bien 2 éléments à comparer",
                "results": [],
                "comparison": None,
            }

        # Continuer avec le reste de la logique existante...
        logger.info(
            f"Proceeding with comparison of {len(comparison_entities)} entities"
        )

        # VALIDATION DE COHÉRENCE
        validation_result = self._validate_comparison_entities(comparison_entities)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Entités de comparaison invalides: {validation_result['reason']}",
                "entities": comparison_entities,
                "results": [],
                "comparison": None,
            }

        # EXÉCUTION DES REQUÊTES AVEC GESTION D'ERREUR
        results = {}
        successful_queries = 0

        for i, entity_set in enumerate(comparison_entities):
            entity_key = self._generate_entity_key(entity_set)
            logger.debug(f"Executing query for {entity_key}")

            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities={
                        k: v for k, v in entity_set.items() if not k.startswith("_")
                    },
                    top_k=top_k,
                    strict_sex_match=True,  # Mode strict pour comparaisons
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    results[entity_key] = result
                    successful_queries += 1
                    logger.debug(
                        f"Found {len(result.context_docs)} results for {entity_key}"
                    )
                else:
                    logger.warning(f"Empty context_docs for {entity_key}")
                    results[entity_key] = None

            except Exception as e:
                logger.error(f"Error querying {entity_key}: {e}")
                results[entity_key] = None

        # VÉRIFICATION DES RÉSULTATS
        if successful_queries < 2:
            logger.warning(f"Insufficient results: found {successful_queries}, need 2")

            # FALLBACK: Essayer avec strict_sex_match=False
            if successful_queries == 0:
                logger.info("Trying fallback with relaxed sex matching...")
                return await self._fallback_relaxed_search(
                    query, comparison_entities, top_k
                )

            return {
                "success": False,
                "error": f"Insufficient results: found {successful_queries}, need 2",
                "details": {
                    "successful_entities": [
                        k for k, v in results.items() if v is not None
                    ],
                    "failed_entities": [k for k, v in results.items() if v is None],
                    "suggestion": "Vérifiez que les données existent pour les entités demandées",
                },
                "results": [],
                "comparison": None,
            }

        # ANALYSE ET COMPARAISON
        try:
            # Convertir vers l'ancien format pour compatibilité avec le reste du code
            old_format_results = self._convert_to_old_format(
                results, comparison_entities
            )

            if len(old_format_results) < 2:
                return {
                    "success": False,
                    "error": f"Insufficient results after conversion: found {len(old_format_results)}, need 2",
                    "results": old_format_results,
                    "comparison": None,
                }

            # Calculer la comparaison avec l'ancien format
            comparison = self.calculator.calculate_comparison(old_format_results)

            # Extraire le contexte commun (âge, sexe, etc.)
            context = self._extract_common_context(
                old_format_results, comparison_entities
            )

            comparative_info = preprocessed.get("comparative_info", {})

            logger.info(
                f"Comparison successful: {comparison.label1} vs {comparison.label2}"
            )

            return {
                "success": True,
                "results": old_format_results,
                "comparison": comparison,
                "operation": comparative_info.get("operation"),
                "comparison_type": comparative_info.get("type"),
                "context": context,
                "metadata": {
                    "entities_compared": len(comparison_entities),
                    "successful_queries": successful_queries,
                    "query_type": "comparative",
                    "fallback_used": False,
                },
            }

        except Exception as e:
            logger.error(f"Error in comparison analysis: {e}")
            return {
                "success": False,
                "error": f"Erreur dans l'analyse comparative: {str(e)}",
                "raw_results": {
                    k: len(v.context_docs) if v else 0 for k, v in results.items()
                },
                "results": [],
                "comparison": None,
            }

    def _validate_comparison_entities(self, entities: List[Dict]) -> Dict[str, Any]:
        """Validation des entités de comparaison"""

        if not entities or len(entities) < 2:
            return {"valid": False, "reason": "Au moins 2 entités requises"}

        # Vérifier que toutes les entités ont les champs requis de base
        for i, entity in enumerate(entities):
            # Nettoyer les métadonnées internes
            clean_entity = {k: v for k, v in entity.items() if not k.startswith("_")}

            # Au minimum, nous devons avoir quelque chose à comparer
            if not clean_entity:
                return {
                    "valid": False,
                    "reason": f"Entité {i+1} est vide après nettoyage",
                }

        return {"valid": True, "reason": "Entités valides"}

    def _generate_entity_key(self, entity_set: Dict[str, Any]) -> str:
        """Génère une clé unique pour identifier un jeu d'entités"""

        # Utiliser le label de comparaison si disponible
        if "_comparison_label" in entity_set:
            return entity_set["_comparison_label"]

        # Sinon, construire une clé à partir des attributs principaux
        key_parts = []

        for field in ["breed", "sex", "age_days", "line", "species"]:
            if field in entity_set and entity_set[field]:
                key_parts.append(f"{field}:{entity_set[field]}")

        return "_".join(key_parts) if key_parts else f"entity_{hash(str(entity_set))}"

    async def _fallback_relaxed_search(
        self, query: str, comparison_entities: List[Dict], top_k: int
    ) -> Dict[str, Any]:
        """Recherche de secours avec critères assouplis"""

        logger.info("Executing fallback search with relaxed criteria")

        results = {}
        successful_queries = 0

        for entity_set in comparison_entities:
            # Copier et assouplir les critères
            relaxed_entity = {
                k: v for k, v in entity_set.items() if not k.startswith("_")
            }

            # Assouplir le critère de sexe si présent
            if "sex" in relaxed_entity:
                relaxed_entity["sex"] = "as_hatched"  # Mode permissif

            entity_key = self._generate_entity_key(
                entity_set
            )  # Garder la clé originale

            try:
                result = await self.postgresql_system.search_metrics(
                    query=query,
                    entities=relaxed_entity,
                    top_k=top_k,
                    strict_sex_match=False,
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    results[entity_key] = result
                    successful_queries += 1

            except Exception as e:
                logger.error(f"Fallback search failed for {entity_key}: {e}")

        if successful_queries >= 2:
            # Convertir et analyser comme dans la méthode principale
            old_format_results = self._convert_to_old_format(
                results, comparison_entities
            )

            if len(old_format_results) >= 2:
                try:
                    comparison = self.calculator.calculate_comparison(
                        old_format_results
                    )
                    context = self._extract_common_context(
                        old_format_results, comparison_entities
                    )

                    return {
                        "success": True,
                        "results": old_format_results,
                        "comparison": comparison,
                        "context": context,
                        "metadata": {
                            "entities_compared": len(comparison_entities),
                            "successful_queries": successful_queries,
                            "query_type": "comparative",
                            "fallback_used": True,
                        },
                        "fallback_used": True,
                        "note": "Résultats avec critères assouplis",
                    }
                except Exception as e:
                    logger.error(f"Error in fallback comparison: {e}")

        return {
            "success": False,
            "error": "Aucun résultat même avec critères assouplis",
            "suggestion": "Vérifiez l'existence des données pour ces souches/âges",
            "results": [],
            "comparison": None,
        }

    def _convert_to_old_format(
        self, results: Dict[str, Any], comparison_entities: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Convertit le nouveau format de résultats vers l'ancien format pour compatibilité"""

        old_format_results = []

        for i, entity_set in enumerate(comparison_entities):
            entity_key = self._generate_entity_key(entity_set)
            result = results.get(entity_key)

            if result and hasattr(result, "context_docs"):
                # Extraire le label de comparaison
                comparison_label = entity_set.get("_comparison_label", entity_key)
                comparison_dimension = entity_set.get(
                    "_comparison_dimension", "unknown"
                )

                # Convertir les documents en format exploitable
                metrics = self._extract_metrics_from_docs(result.context_docs)

                if metrics:
                    # Sélectionner le meilleur résultat
                    clean_entities = {
                        k: v for k, v in entity_set.items() if not k.startswith("_")
                    }
                    best_metric = self._select_best_metric(metrics, clean_entities)

                    old_format_result = {
                        comparison_dimension: comparison_label,
                        "label": comparison_label,
                        "data": [best_metric],
                        "all_metrics": metrics,
                        "entity_set": clean_entities,
                    }

                    old_format_results.append(old_format_result)

        return old_format_results

    def _extract_common_context(
        self, results: List[Dict], comparison_entities: List[Dict]
    ) -> Dict[str, Any]:
        """
        Extrait le contexte commun aux deux résultats (âge, sexe si comparaison de souches, etc.)

        Args:
            results: Résultats des deux requêtes
            comparison_entities: Entités de comparaison originales

        Returns:
            Dict avec age_days, sex, breed, comparison_dimension, etc.
        """
        context = {}

        if not results or len(results) == 0:
            return context

        # Extraire depuis les entity_sets
        if results[0].get("entity_set"):
            first_entity_set = results[0]["entity_set"]

            # Âge (commun aux deux)
            if "age_days" in first_entity_set:
                context["age_days"] = first_entity_set["age_days"]

            # Sexe (si comparaison de souches, le sexe est commun)
            if "sex" in first_entity_set:
                # Vérifier si c'est la dimension de comparaison
                comparison_dimension = (
                    comparison_entities[0].get("_comparison_dimension")
                    if comparison_entities
                    else None
                )
                if comparison_dimension != "sex":
                    # Le sexe est commun (on compare autre chose)
                    context["sex"] = first_entity_set["sex"]

        # Extraire depuis les métadonnées des résultats
        if results[0].get("data") and len(results[0]["data"]) > 0:
            first_metric = results[0]["data"][0]
            metadata = first_metric.get("metadata", {})

            if "age_min" in metadata and "age_days" not in context:
                context["age_days"] = metadata["age_min"]

        logger.debug(f"Extracted context: {context}")
        return context

    async def _execute_single_query(
        self, query: str, entities: Dict[str, Any], top_k: int
    ) -> Optional[Dict[str, Any]]:
        """
        Exécute une requête PostgreSQL avec un jeu d'entités spécifique

        Args:
            query: Requête originale
            entities: Jeu d'entités pour cette requête
            top_k: Nombre de résultats

        Returns:
            {
                'sex': str,  # ou autre label
                'label': str,
                'data': List[Dict],
                'entity_set': Dict  # NOUVEAU: pour extraire le contexte
            }
        """
        try:
            # Extraire le label de comparaison
            comparison_label = entities.get("_comparison_label", "unknown")
            comparison_dimension = entities.get("_comparison_dimension", "sex")

            # Créer une copie sans les métadonnées internes
            clean_entities = {
                k: v for k, v in entities.items() if not k.startswith("_")
            }

            logger.debug(
                f"Executing query for {comparison_dimension}={comparison_label}"
            )

            # Appel au système PostgreSQL avec strict_sex_match=True
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=clean_entities,
                top_k=top_k,
                strict_sex_match=True,
            )

            # Vérifier si on a des résultats
            if not result or not hasattr(result, "context_docs"):
                logger.warning(f"No results for {comparison_label}")
                return None

            context_docs = result.context_docs
            if not context_docs or len(context_docs) == 0:
                logger.warning(f"Empty context_docs for {comparison_label}")
                return None

            # Convertir les documents en format exploitable
            metrics = self._extract_metrics_from_docs(context_docs)

            if not metrics:
                logger.warning(f"No metrics extracted for {comparison_label}")
                return None

            # Sélectionner le meilleur résultat
            best_metric = self._select_best_metric(metrics, entities)

            return {
                comparison_dimension: comparison_label,
                "label": comparison_label,
                "data": [best_metric],
                "all_metrics": metrics,
                "entity_set": clean_entities,  # GARDÉ pour extraction de contexte
            }

        except Exception as e:
            logger.error(f"Error executing single query: {e}")
            return None

    def _extract_metrics_from_docs(
        self, context_docs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Extrait les métriques des documents de contexte avec gestion des unités"""
        metrics = []

        # Debug: inspecter le premier document
        if context_docs and len(context_docs) > 0:
            first_doc = context_docs[0]
            logger.debug(f"First doc type: {type(first_doc)}")
            if isinstance(first_doc, dict):
                logger.debug(f"First doc keys: {list(first_doc.keys())}")
                if "metadata" in first_doc:
                    logger.debug(f"Metadata keys: {list(first_doc['metadata'].keys())}")
                if "content" in first_doc:
                    logger.debug(f"Content preview: {first_doc['content'][:200]}")

        for doc in context_docs:
            if not isinstance(doc, dict):
                logger.warning(f"Skipping non-dict doc: {type(doc)}")
                continue

            # Utiliser la nouvelle méthode d'extraction améliorée
            parsed_metric = self._parse_metric_from_content(doc.get("content", ""))
            if parsed_metric:
                # Enrichir avec les métadonnées du document
                metadata = doc.get("metadata", {})
                sheet_name = metadata.get("sheet_name", "").lower()

                # Détecter le système d'unité basé sur le nom de la feuille
                if "imperial" in sheet_name:
                    parsed_metric["unit_system"] = "imperial"
                else:
                    parsed_metric["unit_system"] = "metric"

                # Maintenir la compatibilité avec l'ancien format
                metric_dict = {
                    "value_numeric": parsed_metric.get("value", 0),
                    "unit": parsed_metric.get("unit", ""),
                    "metric_name": parsed_metric.get(
                        "metric_name", metadata.get("metric_name", "")
                    ),
                    "metadata": metadata,
                    "age": parsed_metric.get("age", 0),
                    "unit_system": parsed_metric.get("unit_system", "metric"),
                    "likely_unit_error": parsed_metric.get("likely_unit_error", False),
                    "probable_unit": parsed_metric.get("probable_unit", ""),
                }

                metrics.append(metric_dict)
                logger.debug(
                    f"Extracted: {metric_dict['metric_name']} = {metric_dict['value_numeric']} {metric_dict['unit']} (system: {metric_dict['unit_system']})"
                )

        logger.info(
            f"Successfully extracted {len(metrics)} metrics from {len(context_docs)} docs"
        )
        return metrics

    def _extract_best_metric(
        self, docs: List[Dict], target_age: int = None
    ) -> Optional[Dict]:
        """Extrait la meilleure métrique en gérant les unités conflictuelles"""

        if not docs:
            return None

        # NOUVEAU: Séparer les données par type d'unité
        metric_data = []
        imperial_data = []

        for doc in docs:
            content = doc.get("content", "")
            sheet_name = doc.get("metadata", {}).get("sheet_name", "").lower()

            # Parser la métrique
            parsed_metric = self._parse_metric_from_content(content)
            if not parsed_metric:
                continue

            # Classer par type d'unité
            if "imperial" in sheet_name:
                imperial_data.append(parsed_metric)
            else:
                metric_data.append(parsed_metric)

        logger.debug(
            f"Données trouvées - Métriques: {len(metric_data)}, Impériales: {len(imperial_data)}"
        )

        # PRIORITÉ: Utiliser les données métriques d'abord
        if metric_data:
            best_metric = self._select_best_metric_by_age(metric_data, target_age)
            logger.debug(f"Sélection métrique (système métrique): {best_metric}")
            return best_metric

        # FALLBACK: Utiliser les données impériales si pas de métriques
        elif imperial_data:
            best_metric = self._select_best_metric_by_age(imperial_data, target_age)
            logger.warning(f"Utilisation données impériales en fallback: {best_metric}")
            # NOUVEAU: Marquer comme impérial pour traitement spécial
            if best_metric:
                best_metric["unit_system"] = "imperial"
            return best_metric

        # Aucune donnée valide trouvée
        logger.warning("Aucune métrique valide trouvée")
        return None

    def _select_best_metric_by_age(
        self, metrics: List[Dict], target_age: int = None
    ) -> Optional[Dict]:
        """Sélectionne la meilleure métrique selon la proximité d'âge"""

        if not metrics:
            return None

        if not target_age:
            # Si pas d'âge cible, prendre la première métrique valide
            return metrics[0]

        # Trier par proximité d'âge
        def age_distance(metric):
            metric_age = metric.get("age", 0)
            if metric_age == 0:
                return float("inf")  # Penaliser les âges manquants
            return abs(metric_age - target_age)

        sorted_metrics = sorted(metrics, key=age_distance)
        best_metric = sorted_metrics[0]

        # Validation de la proximité (tolérance max 3 jours)
        if age_distance(best_metric) <= 3:
            logger.debug(
                f"Métrique sélectionnée: âge {best_metric.get('age')} (cible: {target_age})"
            )
            return best_metric
        else:
            logger.warning(f"Aucune métrique proche trouvée pour âge {target_age}")
            return sorted_metrics[0]  # Retourner quand même la plus proche

    def _parse_metric_from_content(self, content: str) -> Optional[Dict]:
        """Parse le contenu pour extraire les informations de métrique"""

        if not content:
            return None

        try:
            import re

            # Pattern amélioré pour extraire les informations
            patterns = {
                "metric_name": r"\*\*(.*?)\*\*",
                "strain": r"Strain:\s*(.+)",
                "sex": r"Sex:\s*(.+)",
                "value": r"Value:\s*([\d.]+)",
                "unit": r"Value:.*?(grams?|kg|pounds?|lbs?)",
                "age": r"Age:\s*(\d+)\s*days?",
            }

            extracted = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()

            # Validation et conversion
            if "value" in extracted:
                try:
                    extracted["value"] = float(extracted["value"])
                except (ValueError, TypeError):
                    logger.warning(f"Valeur non numérique: {extracted.get('value')}")
                    return None

            if "age" in extracted:
                try:
                    extracted["age"] = int(extracted["age"])
                except (ValueError, TypeError):
                    extracted["age"] = 0

            # NOUVEAU: Détection automatique du système d'unité basé sur la valeur
            if extracted.get("value") and extracted.get("unit"):
                value = extracted["value"]
                unit = extracted["unit"].lower()

                # Heuristique pour détecter les unités incohérentes
                if (
                    "gram" in unit and value < 10
                ):  # Probablement des livres mal étiquetées
                    extracted["likely_unit_error"] = True
                    extracted["probable_unit"] = "pounds"
                elif (
                    "pound" in unit and value > 100
                ):  # Probablement des grammes mal étiquetés
                    extracted["likely_unit_error"] = True
                    extracted["probable_unit"] = "grams"

            return extracted

        except Exception as e:
            logger.error(f"Erreur parsing métrique: {e}")
            return None

    def _select_best_metric(
        self, metrics: List[Dict], entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sélectionne la meilleure métrique selon les critères avec gestion des unités"""
        if not metrics:
            return {}

        # Extraire l'âge cible si disponible
        target_age = entities.get("age_days")

        # Utiliser la nouvelle méthode de sélection par âge
        if target_age:
            best_metric = self._select_best_metric_by_age(metrics, target_age)
            if best_metric:
                # Convertir vers le format attendu
                return {
                    "value_numeric": best_metric.get(
                        "value_numeric", best_metric.get("value", 0)
                    ),
                    "unit": best_metric.get("unit", ""),
                    "metric_name": best_metric.get("metric_name", ""),
                    "metadata": best_metric.get("metadata", {}),
                    "unit_system": best_metric.get("unit_system", "metric"),
                    "age": best_metric.get("age", 0),
                }

        # Prendre la première (déjà triée par pertinence) comme fallback
        best = metrics[0]

        logger.debug(
            f"Selected best metric: {best.get('metric_name')} = "
            f"{best.get('value_numeric')} {best.get('unit')}"
        )

        return best

    def _compare_metrics_with_unit_handling(
        self, metric1: Dict, metric2: Dict, entities: Dict
    ) -> Dict:
        """Compare deux métriques en gérant les différences d'unités"""

        # Vérifier les systèmes d'unités
        unit_system1 = metric1.get("unit_system", "metric")
        unit_system2 = metric2.get("unit_system", "metric")

        value1 = metric1.get("value_numeric", metric1.get("value", 0))
        value2 = metric2.get("value_numeric", metric2.get("value", 0))

        # NOUVEAU: Conversion automatique si systèmes différents
        if unit_system1 != unit_system2:
            logger.warning(
                "Systèmes d'unités différents détectés, tentative de conversion"
            )

            # Convertir les livres en grammes si nécessaire
            if unit_system1 == "imperial" and value1 < 20:  # Probablement en livres
                value1 = value1 * 453.6  # Conversion livres -> grammes
                logger.debug(
                    f"Conversion impérial->métrique: {metric1.get('value_numeric', metric1.get('value'))} lbs -> {value1} g"
                )

            if unit_system2 == "imperial" and value2 < 20:  # Probablement en livres
                value2 = value2 * 453.6  # Conversion livres -> grammes
                logger.debug(
                    f"Conversion impérial->métrique: {metric2.get('value_numeric', metric2.get('value'))} lbs -> {value2} g"
                )

        # Calcul de la différence
        difference = abs(value2 - value1)
        percentage = (difference / value1 * 100) if value1 > 0 else 0

        # Déterminer le meilleur selon le type de métrique
        metric_name = metric1.get("metric_name", "").lower()
        higher_is_better = self._is_higher_better_metric(metric_name)

        if higher_is_better:
            better_entity = (
                entities.get("entity2_name")
                if value2 > value1
                else entities.get("entity1_name")
            )
        else:
            better_entity = (
                entities.get("entity1_name")
                if value1 < value2
                else entities.get("entity2_name")
            )

        return {
            "metric_name": metric1.get("metric_name"),
            "value1": value1,
            "value2": value2,
            "difference": difference,
            "percentage_diff": percentage,
            "better_entity": better_entity,
            "unit_conversion_applied": unit_system1 != unit_system2,
            "confidence": "high" if unit_system1 == unit_system2 else "medium",
        }

    def _is_higher_better_metric(self, metric_name: str) -> bool:
        """Détermine si une valeur plus élevée est meilleure pour cette métrique"""
        metric_name_lower = metric_name.lower()

        # Métriques où plus élevé = meilleur
        higher_better_keywords = [
            "weight",
            "poids",
            "production",
            "yield",
            "rendement",
            "growth",
            "croissance",
            "gain",
            "efficiency",
        ]

        # Métriques où plus bas = meilleur
        lower_better_keywords = [
            "conversion",
            "fcr",
            "mortality",
            "mortalité",
            "cost",
            "coût",
        ]

        if any(keyword in metric_name_lower for keyword in higher_better_keywords):
            return True
        elif any(keyword in metric_name_lower for keyword in lower_better_keywords):
            return False
        else:
            # Par défaut, assumer que plus élevé = meilleur
            return True

    def _validate_comparison_consistency(self, comparison_result: Dict) -> Dict:
        """Valide la cohérence du résultat de comparaison"""

        # Vérifications de cohérence
        warnings = []

        # Vérifier les valeurs aberrantes
        value1 = comparison_result.get("value1", 0)
        value2 = comparison_result.get("value2", 0)

        if value1 <= 0 or value2 <= 0:
            warnings.append("Valeurs nulles ou négatives détectées")

        # Vérifier les différences extrêmes
        percentage_diff = comparison_result.get("percentage_diff", 0)
        if percentage_diff > 50:
            warnings.append(f"Différence très importante: {percentage_diff:.1f}%")

        # Vérifier la cohérence des unités
        if comparison_result.get("unit_conversion_applied", False):
            warnings.append("Conversion d'unités appliquée, vérifier la cohérence")

        comparison_result["validation_warnings"] = warnings
        comparison_result["is_reliable"] = len(warnings) == 0

        return comparison_result

    async def generate_comparative_response(
        self, query: str, comparison_result: Dict[str, Any], language: str = "fr"
    ) -> str:
        """
        Génère une réponse naturelle pour une comparaison
        VERSION AMÉLIORÉE : Utilise OpenAI pour une réponse professionnelle

        Args:
            query: Requête originale
            comparison_result: Résultat de handle_comparative_query
            language: Langue de la réponse

        Returns:
            Texte de réponse formatté et enrichi par OpenAI
        """
        if not comparison_result.get("success"):
            error = comparison_result.get("error", "Unknown error")
            if language == "fr":
                return f"Impossible de comparer: {error}"
            else:
                return f"Cannot compare: {error}"

        comparison = comparison_result["comparison"]
        results = comparison_result["results"]
        context = comparison_result.get("context", {})

        # Extraire le nom de métrique
        metric_name = "métrique"
        if results and len(results) > 0:
            first_result = results[0]
            if "data" in first_result and len(first_result["data"]) > 0:
                metric_data = first_result["data"][0]
                metric_name = metric_data.get("metric_name", metric_name)

        # Construire les données structurées pour OpenAI
        comparison_data = {
            "metric_name": metric_name,
            "label1": comparison.label1,
            "value1": comparison.value1,
            "label2": comparison.label2,
            "value2": comparison.value2,
            "difference_absolute": comparison.absolute_difference,
            "difference_percent": comparison.relative_difference_pct,
            "better": comparison.better_label,
            "unit": comparison.unit,
            "age_days": context.get("age_days"),
            "sex": context.get("sex"),
            "is_lower_better": self.calculator._is_lower_better(
                comparison.metric_name or metric_name
            ),
        }

        # Prompt système pour OpenAI
        if language == "fr":
            system_prompt = """Tu es un expert en aviculture qui rédige des réponses professionnelles et claires pour comparer des performances entre souches.

Règles importantes :
1. TOUJOURS reformuler la question au début de la réponse pour donner le contexte
2. Utilise les noms corrects : "Cobb 500", "Ross 308" (avec majuscules)
3. Présente les deux souches de manière identique, SANS mettre l'une en gras
4. Traduis les métriques techniques en français : "feed_conversion_ratio" → "conversion alimentaire (FCR)"
5. Pour le FCR et la mortalité : une valeur PLUS BASSE est MEILLEURE
6. Pour le poids et la production : une valeur PLUS HAUTE est MEILLEURE
7. Fournis une interprétation concise de l'écart
8. NE termine PAS avec une section "Impact pratique" ou "Recommandations"

Format attendu :
- Reformulation de la question en une ligne
- Valeurs comparées avec unités (format : "Souche : valeur (unité)" sur deux lignes distinctes, sans gras)
- Différence avec pourcentage en gras
- Interprétation : qui est meilleur et pourquoi en 1-2 phrases maximum
- Pas de conclusion ou d'impact pratique

Exemple de format :
"Pour comparer la conversion alimentaire entre un Cobb 500 mâle et un Ross 308 mâle à 17 jours :

Cobb 500 : 1,081 (FCR)

Ross 308 : 1,065 (FCR)

**Différence : 0,016 (1,5%)**

Le Ross 308 présente une meilleure conversion alimentaire..."
"""

            user_prompt = f"""Génère une réponse concise pour cette comparaison :

Données :
- Métrique : {comparison_data['metric_name']}
- {comparison_data['label1']} : {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']} : {comparison_data['value2']:.3f} {comparison_data['unit']}
- Différence : {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Meilleur : {comparison_data['better']}
- Contexte : {'mâles' if comparison_data['sex'] == 'male' else 'femelles' if comparison_data['sex'] == 'female' else 'sexes mélangés'} à {comparison_data['age_days']} jours
- Type métrique : {"plus bas = meilleur" if comparison_data['is_lower_better'] else "plus haut = meilleur"}"""

        else:  # English
            system_prompt = """You are a poultry expert writing professional and clear responses comparing strain performances.

Important rules:
1. ALWAYS rephrase the question at the beginning to provide context
2. Use proper names: "Cobb 500", "Ross 308" (capitalized)
3. Present both strains identically, WITHOUT bolding one
4. Translate technical metrics: "feed_conversion_ratio" → "feed conversion ratio (FCR)"
5. For FCR and mortality: LOWER value is BETTER
6. For weight and production: HIGHER value is BETTER
7. Provide concise interpretation of the difference
8. DO NOT end with "Practical impact" or "Recommendations" section

Expected format:
- Rephrase the question in one line
- Compared values with units (format: "Strain: value (unit)" on two separate lines, no bold)
- Difference with percentage in bold
- Interpretation: who is better and why in 1-2 sentences max
- No conclusion or practical impact

Example format:
"To compare feed conversion between a Cobb 500 male and a Ross 308 male at 17 days:

Cobb 500: 1.081 (FCR)

Ross 308: 1.065 (FCR)

**Difference: 0.016 (1.5%)**

The Ross 308 shows better feed conversion..."
"""

            user_prompt = f"""Generate a concise response for this comparison:

Data:
- Metric: {comparison_data['metric_name']}
- {comparison_data['label1']}: {comparison_data['value1']:.3f} {comparison_data['unit']}
- {comparison_data['label2']}: {comparison_data['value2']:.3f} {comparison_data['unit']}
- Difference: {abs(comparison_data['difference_absolute']):.3f} ({abs(comparison_data['difference_percent']):.1f}%)
- Better: {comparison_data['better']}
- Context: {'males' if comparison_data['sex'] == 'male' else 'females' if comparison_data['sex'] == 'female' else 'mixed'} at {comparison_data['age_days']} days
- Metric type: {"lower is better" if comparison_data['is_lower_better'] else "higher is better"}"""

        try:
            # Appel OpenAI pour génération de réponse de qualité
            if hasattr(self.postgresql_system, "postgres_retriever"):
                retriever = self.postgresql_system.postgres_retriever
                if hasattr(retriever, "query_normalizer"):
                    # Utiliser le client OpenAI déjà existant
                    from openai import AsyncOpenAI
                    import os

                    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                    response = await client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,  # Un peu de créativité mais pas trop
                        max_tokens=500,
                    )

                    enhanced_response = response.choices[0].message.content.strip()
                    logger.info("Réponse comparative enrichie par OpenAI")
                    return enhanced_response

        except Exception as e:
            logger.warning(
                f"Erreur enrichissement OpenAI: {e}, utilisation template de base"
            )
            # Fallback sur le template basique
            pass

        # Fallback : utiliser le formatter basique si OpenAI échoue
        terminology = None
        if hasattr(self.postgresql_system, "postgres_retriever"):
            retriever = self.postgresql_system.postgres_retriever
            if hasattr(retriever, "query_normalizer"):
                terminology = retriever.query_normalizer.terminology

        formatted_text = self.calculator.format_comparison_text(
            comparison=comparison,
            metric_name=metric_name,
            language=language,
            terminology=terminology,
            context=context,
        )

    def _generate_entity_name(self, entity_set: Dict[str, Any], index: int) -> str:
        """Génère un nom descriptif pour l'entité"""

        parts = []

        # Ajouter la race si présente
        if entity_set.get("breed"):
            parts.append(entity_set["breed"])

        # Ajouter le sexe de manière explicite
        sex = entity_set.get("sex", "as_hatched")
        if sex == "male":
            parts.append("mâle")
        elif sex == "female":
            parts.append("femelle")
        elif sex != "as_hatched":
            parts.append(sex)

        # Ajouter l'âge si présent
        if entity_set.get("age_days"):
            parts.append(f"{entity_set['age_days']} jours")

        # Si aucune partie spécifique, utiliser un nom générique
        if not parts:
            return f"Entité {index + 1}"

        return " ".join(parts)

    def _compare_entities(
        self, results: List[Dict], preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare les entités avec gestion améliorée des systèmes d'unités"""

        if len(results) < 2:
            raise ValueError(f"Impossible de comparer {len(results)} entité(s)")

        entity1 = results[0]
        entity2 = results[1]

        # Extraire les métriques avec gestion des unités
        metric1 = self._extract_best_metric_with_units(
            entity1["docs"], preprocessed_data
        )
        metric2 = self._extract_best_metric_with_units(
            entity2["docs"], preprocessed_data
        )

        if not metric1 or not metric2:
            raise ValueError("Impossible d'extraire les métriques pour comparaison")

        # Comparaison avec gestion des unités
        comparison = self._compare_metrics_with_unit_handling(
            metric1,
            metric2,
            {
                "entity1_name": entity1["entity_name"],
                "entity2_name": entity2["entity_name"],
            },
        )

        # Ajouter contexte
        comparison["entity1"] = entity1["entity_name"]
        comparison["entity2"] = entity2["entity_name"]
        comparison["context"] = self._extract_context_from_entities(results)

        return comparison

    def _extract_best_metric_with_units(
        self, docs: List[Dict], preprocessed_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """Extrait la meilleure métrique en gérant les unités et priorités"""

        target_age = preprocessed_data.get("entities", {}).get("age_days")

        # Séparer par système d'unité
        metric_docs = []
        imperial_docs = []

        for doc in docs:
            sheet_name = doc.get("metadata", {}).get("sheet_name", "").lower()
            if "imperial" in sheet_name:
                imperial_docs.append(doc)
            else:
                metric_docs.append(doc)

        # Priorité aux données métriques
        primary_docs = metric_docs if metric_docs else imperial_docs

        if not primary_docs:
            return None

        # Extraire et sélectionner la meilleure métrique
        metrics = []
        for doc in primary_docs:
            parsed = self._parse_metric_from_content(doc.get("content", ""))
            if parsed:
                # Marquer le système d'unité
                parsed["unit_system"] = (
                    "imperial"
                    if "imperial"
                    in doc.get("metadata", {}).get("sheet_name", "").lower()
                    else "metric"
                )
                metrics.append(parsed)

        if not metrics:
            return None

        # Sélectionner par proximité d'âge si spécifié
        if target_age:
            best_metric = self._select_best_metric_by_age(metrics, int(target_age))
        else:
            best_metric = metrics[0]  # Premier résultat

        return best_metric

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Crée une réponse d'erreur standardisée"""
        return {
            "success": False,
            "error": error_message,
            "results": [],
            "comparison": None,
        }

    def _format_comparison_response(
        self, comparison_result: Dict[str, Any], preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Formate la réponse de comparaison"""
        return {
            "success": True,
            "comparison": comparison_result,
            "results": comparison_result,
            "metadata": {
                "query_type": "comparative",
                "entities_compared": 2,
                "preprocessing_applied": True,
            },
        }

    def _extract_context_from_entities(self, results: List[Dict]) -> Dict[str, Any]:
        """Extrait le contexte commun des entités comparées"""
        context = {}

        if results and len(results) > 0:
            first_entity = results[0].get("entity_set", {})

            # Extraire les informations communes
            if "age_days" in first_entity:
                context["age_days"] = first_entity["age_days"]

            if "sex" in first_entity:
                context["sex"] = first_entity["sex"]

            if "breed" in first_entity:
                context["breed"] = first_entity["breed"]

        return context

    def _parse_comparison_entities(
        self, base_entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse les entités de base pour détecter les comparaisons (fallback)"""
        # Utiliser la méthode existante _parse_multiple_entities_from_preprocessing
        # avec un format compatible
        preprocessed_format = {"entities": base_entities}
        return self._parse_multiple_entities_from_preprocessing(preprocessed_format)

    async def handle_temporal_comparison(
        self, query: str, age_start: int, age_end: int, entities: Dict
    ) -> Dict:
        """
        Gère les comparaisons temporelles entre deux âges

        Args:
            query: Requête utilisateur originale
            age_start: Âge de début en jours
            age_end: Âge de fin en jours
            entities: Entités communes (breed, sex, etc.)

        Returns:
            Dict avec les résultats de comparaison temporelle
        """
        try:
            logger.info(f"Handling temporal comparison: {age_start} -> {age_end} days")

            # Requête pour âge de début
            entities_start = entities.copy()
            entities_start["age_days"] = age_start
            result_start = await self.postgresql_system.search_metrics(
                query=f"Métrique à {age_start} jours",
                entities=entities_start,
                top_k=12,
                strict_sex_match=True,
            )

            # Requête pour âge de fin
            entities_end = entities.copy()
            entities_end["age_days"] = age_end
            result_end = await self.postgresql_system.search_metrics(
                query=f"Métrique à {age_end} jours",
                entities=entities_end,
                top_k=12,
                strict_sex_match=True,
            )

            # Vérification des résultats
            if not (
                result_start
                and hasattr(result_start, "context_docs")
                and result_start.context_docs
            ):
                logger.warning(f"No results for age {age_start} days")
                return {
                    "success": False,
                    "error": f"Aucun résultat trouvé pour {age_start} jours",
                    "comparison_type": "temporal",
                }

            if not (
                result_end
                and hasattr(result_end, "context_docs")
                and result_end.context_docs
            ):
                logger.warning(f"No results for age {age_end} days")
                return {
                    "success": False,
                    "error": f"Aucun résultat trouvé pour {age_end} jours",
                    "comparison_type": "temporal",
                }

            # Extraction des métriques
            metric_start = self._extract_metric_value(result_start.context_docs[0])
            metric_end = self._extract_metric_value(result_end.context_docs[0])

            if metric_start is None or metric_end is None:
                return {
                    "success": False,
                    "error": "Impossible d'extraire les valeurs numériques",
                    "comparison_type": "temporal",
                }

            # Calcul différence et évolution
            difference = metric_end - metric_start
            percent_change = (
                (difference / metric_start * 100) if metric_start != 0 else 0
            )

            # Déterminer le type d'évolution
            evolution = "stable"
            if (
                abs(percent_change) > 1
            ):  # Seuil de 1% pour considérer un changement significatif
                evolution = "croissance" if difference > 0 else "diminution"

            # Extraire les métadonnées pour contexte
            start_doc = result_start.context_docs[0]
            start_metadata = start_doc.get("metadata", {})
            metric_name = start_metadata.get("metric_name", "métrique")
            unit = self._extract_unit_from_doc(start_doc)

            logger.info(
                f"Temporal comparison successful: {metric_start} -> {metric_end} ({percent_change:.1f}%)"
            )

            return {
                "success": True,
                "comparison_type": "temporal",
                "start_age": age_start,
                "end_age": age_end,
                "start_value": metric_start,
                "end_value": metric_end,
                "difference": difference,
                "percent_change": percent_change,
                "evolution": evolution,
                "metric_name": metric_name,
                "unit": unit,
                "entities": entities,
                "metadata": {
                    "age_range": f"{age_start}-{age_end} jours",
                    "evolution_type": evolution,
                    "significant_change": abs(percent_change) > 1,
                },
            }

        except Exception as e:
            logger.error(f"Error in temporal comparison: {e}")
            return {
                "success": False,
                "error": f"Erreur dans la comparaison temporelle: {str(e)}",
                "comparison_type": "temporal",
            }

    def _extract_metric_value(self, document: Dict) -> Optional[float]:
        """
        Extrait la valeur numérique d'un document

        Args:
            document: Document de contexte

        Returns:
            Valeur numérique ou None si extraction échoue
        """
        try:
            # Essayer d'abord via metadata
            metadata = document.get("metadata", {})
            if "value_numeric" in metadata:
                return float(metadata["value_numeric"])

            # Sinon parser le content
            content = document.get("content", "")
            if content:
                import re

                value_match = re.search(r"Value:\s*([0-9.]+)", content)
                if value_match:
                    return float(value_match.group(1))

            logger.warning("Could not extract numeric value from document")
            return None

        except (ValueError, TypeError) as e:
            logger.warning(f"Error extracting metric value: {e}")
            return None

    def _extract_unit_from_doc(self, document: Dict) -> str:
        """
        Extrait l'unité d'un document

        Args:
            document: Document de contexte

        Returns:
            Unité ou chaîne vide
        """
        try:
            # Essayer metadata
            metadata = document.get("metadata", {})
            if "unit" in metadata:
                return metadata["unit"]

            # Parser le content pour l'unité
            content = document.get("content", "")
            if content:
                import re

                unit_match = re.search(r"Value:\s*[0-9.]+\s*(\w+)", content)
                if unit_match:
                    return unit_match.group(1)

            return ""

        except Exception as e:
            logger.warning(f"Error extracting unit: {e}")
            return ""

    def _is_temporal_range_query(self, query: str) -> bool:
        """
        Détecte si la requête concerne une plage temporelle plutôt qu'une comparaison

        Args:
            query: Requête utilisateur

        Returns:
            True si la requête est temporelle, False si comparative
        """
        import re

        query_lower = query.lower()

        # Patterns spécifiques aux requêtes temporelles
        temporal_patterns = [
            r"entre\s+\d+\s+et\s+\d+\s+jours?",
            r"de\s+\d+\s+à\s+\d+\s+jours?",
            r"du\s+jour\s+\d+\s+au\s+jour\s+\d+",
            r"évolu(e|tion).*entre\s+\d+",
            r"gain.*entre\s+\d+",
            r"croissance.*entre\s+\d+",
            r"progression.*entre\s+\d+",
            r"variation.*entre\s+\d+",
            r"changement.*entre\s+\d+",
            r"développement.*entre\s+\d+",
            r"courbe.*entre\s+\d+",
            r"tendance.*entre\s+\d+",
            # Patterns anglais
            r"between\s+\d+\s+and\s+\d+\s+days?",
            r"from\s+\d+\s+to\s+\d+\s+days?",
            r"evolution.*between\s+\d+",
            r"growth.*between\s+\d+",
        ]

        # Vérifier chaque pattern
        for pattern in temporal_patterns:
            if re.search(pattern, query_lower):
                logger.debug(f"Temporal pattern detected: {pattern}")
                return True

        # Patterns additionnels pour évolution temporelle
        evolution_keywords = [
            "évolution",
            "evolution",
            "gain",
            "croissance",
            "growth",
            "progression",
            "développement",
            "development",
            "courbe",
            "curve",
        ]
        age_ranges = re.findall(r"\d+.*\d+.*jours?|\d+.*\d+.*days?", query_lower)

        if any(keyword in query_lower for keyword in evolution_keywords) and age_ranges:
            logger.debug("Evolution keywords + age ranges detected")
            return True

        # Si on trouve "entre X et Y" avec des nombres, probablement temporel
        between_pattern = r"entre\s+\d+.*\d+"
        if re.search(between_pattern, query_lower):
            logger.debug("Generic 'entre X et Y' pattern detected")
            return True

        logger.debug("No temporal patterns detected, treating as comparative")
        return False


# Tests unitaires
if __name__ == "__main__":
    import asyncio

    async def test_comparison_handler():
        """Test avec des données mockées"""

        # Mock PostgreSQL System
        class MockPostgreSQLSystem:
            async def search_metrics(
                self, query, entities, top_k, strict_sex_match=False
            ):
                # Simuler des résultats différents selon le sexe
                sex = entities.get("sex", "male")

                class MockResult:
                    def __init__(self, sex_val):
                        self.context_docs = [
                            {
                                "content": f"Value: {'1.081' if sex_val == 'male' else '1.045'} ratio",
                                "metadata": {
                                    "value_numeric": (
                                        1.081 if sex_val == "male" else 1.045
                                    ),
                                    "unit": "ratio",
                                    "metric_name": "feed_conversion_ratio for 17",
                                    "age_min": 17,
                                },
                            }
                        ]

                return MockResult(sex)

        mock_system = MockPostgreSQLSystem()
        handler = ComparisonHandler(mock_system)

        # Simuler un preprocessing comparatif
        preprocessed = {
            "comparative_info": {
                "is_comparative": True,
                "type": "difference",
                "operation": "subtract",
            },
            "comparison_entities": [
                {
                    "sex": "male",
                    "age_days": 17,
                    "_comparison_label": "Cobb 500",
                    "_comparison_dimension": "breed",
                },
                {
                    "sex": "male",
                    "age_days": 17,
                    "_comparison_label": "Ross 308",
                    "_comparison_dimension": "breed",
                },
            ],
        }

        result = await handler.handle_comparative_query(
            "Quelle est la différence de FCR entre Cobb 500 et Ross 308 mâle à 17 jours ?",
            preprocessed,
        )

        print("Comparison Result:")
        print(f"  Success: {result['success']}")
        if result["success"]:
            comp = result["comparison"]
            print(f"  {comp.label1}: {comp.value1}")
            print(f"  {comp.label2}: {comp.value2}")
            print(f"  Difference: {comp.absolute_difference:.3f}")
            print(f"  Context: {result.get('context')}")

            # Générer la réponse
            response = await handler.generate_comparative_response(
                "Test query", result, "fr"
            )
            print("\nGenerated Response:")
            print(response)

    asyncio.run(test_comparison_handler())
