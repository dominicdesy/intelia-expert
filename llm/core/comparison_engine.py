# -*- coding: utf-8 -*-
"""
comparison_engine.py - Moteur de comparaison unifié
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
comparison_engine.py - Moteur de comparaison unifié
Version 3.0 - Templates EN avec traduction LLM robuste
Fusionne: comparison_handler + comparison_utils + comparison_response_generator
Utilise: metric_calculator (conservé pour calculs purs)
"""

import logging
from utils.types import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from utils.breeds_registry import get_breeds_registry
from utils.mixins import SerializableMixin
from utils.llm_translator import get_llm_translator

logger = logging.getLogger(__name__)

# Instance globale du traducteur LLM
_translator = None

def _get_translator():
    """Récupère l'instance singleton du traducteur"""
    global _translator
    if _translator is None:
        _translator = get_llm_translator()
    return _translator


def _translate(text_en: str, language: str) -> str:
    """Traduit un texte EN vers la langue cible via LLM"""
    if language == "en":
        return text_en

    translator = _get_translator()
    return translator.translate(
        text=text_en,
        target_language=language,
        source_language="en"
    )


class ComparisonStatus(Enum):
    """Statuts de comparaison"""

    SUCCESS = "success"
    INSUFFICIENT_DATA = "insufficient_data"
    INCOMPATIBLE_METRICS = "incompatible_metrics"
    INCOMPATIBLE_SPECIES = "incompatible_species"
    ERROR = "error"


class ComparisonDimension(Enum):
    """Dimensions de comparaison"""

    SEX = "sex"
    BREED = "breed"
    AGE = "age"
    PHASE = "phase"


@dataclass
class ComparisonResult(SerializableMixin):
    """Résultat structuré d'une comparaison"""

    success: bool
    status: ComparisonStatus

    # Données de comparaison
    comparison_data: Optional[Dict[str, Any]] = None
    entities_compared: List[str] = field(default_factory=list)
    dimension: Optional[ComparisonDimension] = None

    # Métadonnées
    metric_name: Optional[str] = None
    unit: Optional[str] = None
    better_entity: Optional[str] = None

    # Erreurs
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Contexte
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Override to rename comparison_data -> comparison"""
        result = super().to_dict()
        # Rename for backward compatibility
        if "comparison_data" in result:
            result["comparison"] = result.pop("comparison_data")
        return result


class ComparisonEngine:
    """
    Moteur unifié pour toutes les comparaisons avicoles

    Remplace:
    - comparison_handler.py (orchestration)
    - comparison_utils.py (extraction et parsing)
    - comparison_response_generator.py (génération réponses)

    Utilise:
    - metric_calculator.py (calculs mathématiques purs - CONSERVÉ)
    - breeds_registry (validation compatibilité species)
    """

    # ========================================================================
    # CONFIGURATION - PRIORITÉS DE MÉTRIQUES
    # ========================================================================

    METRIC_PRIORITIES = [
        "body_weight",
        "feed_conversion_ratio",
        "daily_gain",
        "feed_intake",
        "mortality",
        "livability",
        "production",
    ]

    # ========================================================================
    # CONFIGURATION - MEILLEUR = PLUS HAUT OU PLUS BAS
    # ========================================================================

    HIGHER_IS_BETTER = {
        "body_weight": True,
        "daily_gain": True,
        "livability": True,
        "production": True,
        "uniformity": True,
    }

    LOWER_IS_BETTER = {
        "feed_conversion_ratio": True,
        "fcr": True,
        "mortality": True,
        "cost": True,
    }

    def __init__(self, postgresql_system=None):
        """
        Initialise le moteur de comparaison

        Args:
            postgresql_system: Instance PostgreSQLSystem pour récupération données
        """
        self.postgresql_system = postgresql_system

        # Charger le registre des races pour validation species
        self.breeds_registry = get_breeds_registry()

        # Import du calculateur (module séparé conservé)
        try:
            from .metric_calculator import MetricCalculator

            self.calculator = MetricCalculator()
        except ImportError:
            logger.warning("MetricCalculator non disponible - calculs limités")
            self.calculator = None

        logger.info(
            f"ComparisonEngine initialisé "
            f"(breeds_registry: {len(self.breeds_registry.get_all_breeds())} races)"
        )

    async def compare(self, preprocessed_data: Dict[str, Any]) -> ComparisonResult:
        """
        Point d'entrée principal pour les comparaisons

        Args:
            preprocessed_data: Données preprocessées avec:
                - comparison_entities: List[Dict] (entités à comparer)
                - query: str (requête originale)
                - entities: Dict (entités générales)

        Returns:
            ComparisonResult structuré avec toutes les données
        """
        comparison_entities = preprocessed_data.get("comparison_entities", [])

        # Validation de base
        if len(comparison_entities) < 2:
            return ComparisonResult(
                success=False,
                status=ComparisonStatus.INSUFFICIENT_DATA,
                error="Besoin d'au moins 2 entités pour comparaison",
            )

        # ====================================================================
        # NOUVEAU: VALIDATION SPECIES AVANT COMPARAISON
        # ====================================================================
        if len(comparison_entities) >= 2:
            breed1 = comparison_entities[0].get("breed")
            breed2 = comparison_entities[1].get("breed")

            if breed1 and breed2:
                # Vérifier la compatibilité des espèces via le registry
                compatible, reason = self.breeds_registry.are_comparable(breed1, breed2)

                if not compatible:
                    logger.warning(
                        f"Tentative de comparaison entre espèces incompatibles: "
                        f"{breed1} vs {breed2} - {reason}"
                    )

                    # Récupérer les informations des races pour le message d'erreur
                    breed1_info = self.breeds_registry.get_breed(breed1)
                    breed2_info = self.breeds_registry.get_breed(breed2)

                    error_message = f"Cannot compare different species: {reason}"
                    if breed1_info and breed2_info:
                        error_message = (
                            f"Cannot compare {breed1_info['name']} ({breed1_info['species']}) "
                            f"with {breed2_info['name']} ({breed2_info['species']}). "
                            "Please compare breeds from the same species."
                        )

                    return ComparisonResult(
                        success=False,
                        status=ComparisonStatus.INCOMPATIBLE_SPECIES,
                        error=error_message,
                        entities_compared=[breed1, breed2],
                        metadata={
                            "breed1": breed1,
                            "breed2": breed2,
                            "species1": (
                                breed1_info["species"] if breed1_info else "unknown"
                            ),
                            "species2": (
                                breed2_info["species"] if breed2_info else "unknown"
                            ),
                            "incompatibility_reason": reason,
                        },
                    )
                else:
                    # Log de validation réussie
                    breed1_info = self.breeds_registry.get_breed(breed1)
                    breed2_info = self.breeds_registry.get_breed(breed2)
                    if breed1_info and breed2_info:
                        logger.info(
                            f"Species validation OK: {breed1_info['name']} vs {breed2_info['name']} "
                            f"(both {breed1_info['species']})"
                        )
        # ====================================================================

        logger.info(
            f"Début comparaison: {len(comparison_entities)} entités, "
            f"dimension: {self._detect_comparison_dimension(comparison_entities)}"
        )

        try:
            # 1. Récupérer données pour chaque entité
            entity_results = await self._fetch_all_entities_data(comparison_entities)

            if len(entity_results) < 2:
                # Tentative avec critères assouplis
                return await self._compare_with_fallback(
                    comparison_entities, preprocessed_data
                )

            # 2. Calculer comparaison
            comparison_data = self._calculate_comparison(
                entity_results, preprocessed_data
            )

            # 3. Déterminer dimension de comparaison
            dimension = self._detect_comparison_dimension(comparison_entities)

            # 4. Identifier meilleure entité
            better_entity = self._determine_better_entity(comparison_data)

            # 5. Structurer résultat
            return ComparisonResult(
                success=True,
                status=ComparisonStatus.SUCCESS,
                comparison_data=comparison_data,
                entities_compared=[r["label"] for r in entity_results],
                dimension=dimension,
                metric_name=comparison_data.get("metric_name"),
                unit=comparison_data.get("unit"),
                better_entity=better_entity,
                metadata={
                    "query_type": "comparative",
                    "entities_count": len(entity_results),
                    "data_sources": [r["entity_set"] for r in entity_results],
                },
            )

        except Exception as e:
            logger.error(f"Erreur comparaison: {e}", exc_info=True)
            return ComparisonResult(
                success=False,
                status=ComparisonStatus.ERROR,
                error=str(e),
            )

    async def _fetch_all_entities_data(
        self, comparison_entities: List[Dict[str, Any]]
    ) -> List[Dict]:
        """
        Récupère données pour toutes les entités à comparer

        Args:
            comparison_entities: Liste d'entités

        Returns:
            Liste de résultats avec données
        """
        entity_results = []

        for entity_set in comparison_entities:
            result = await self._fetch_entity_data(entity_set)
            if result:
                entity_results.append(result)
            else:
                logger.warning(f"Aucune donnée pour entité: {entity_set}")

        logger.info(
            f"Données récupérées: {len(entity_results)}/{len(comparison_entities)} entités"
        )

        return entity_results

    async def _fetch_entity_data(self, entity_set: Dict[str, Any]) -> Optional[Dict]:
        """
        Récupère données pour une entité spécifique

        Args:
            entity_set: Dict avec breed, age_days, sex, etc.

        Returns:
            Dict avec label, data, entity_set ou None
        """
        if not self.postgresql_system:
            logger.warning("PostgreSQL système non disponible")
            return None

        try:
            # Construction query pour logging
            query_desc = self._build_entity_description(entity_set)

            # Récupération via PostgreSQL
            result = await self.postgresql_system.search_metrics(
                query=f"Métrique pour {query_desc}",
                entities=entity_set,
                top_k=12,
                strict_sex_match=True,
            )

            # Validation résultat
            if result and hasattr(result, "context_docs") and result.context_docs:
                return {
                    "label": self._build_entity_label(entity_set),
                    "data": result.context_docs,
                    "entity_set": entity_set,
                    "result_object": result,
                }
            else:
                logger.debug(f"Résultat vide pour: {query_desc}")
                return None

        except Exception as e:
            logger.error(f"Erreur fetch entity {entity_set}: {e}")
            return None

    def _build_entity_label(self, entity_set: Dict) -> str:
        """
        Construit un label lisible pour l'entité

        Args:
            entity_set: Dict avec entités

        Returns:
            Label formaté (ex: "Cobb 500 mâle 21j")
        """
        parts = []

        if entity_set.get("breed"):
            # Utiliser le nom officiel depuis le registry si possible
            breed_info = self.breeds_registry.get_breed(entity_set["breed"])
            if breed_info:
                parts.append(breed_info["name"])
            else:
                parts.append(entity_set["breed"].upper())

        if entity_set.get("sex"):
            sex_label = {
                "male": "mâle",
                "female": "femelle",
                "mixed": "mixte",
            }.get(entity_set["sex"], entity_set["sex"])
            parts.append(sex_label)

        if entity_set.get("age_days"):
            parts.append(f"{entity_set['age_days']}j")

        # Utiliser label de comparaison si fourni
        if entity_set.get("_comparison_label"):
            return entity_set["_comparison_label"]

        return " ".join(parts) if parts else "Entité"

    def _build_entity_description(self, entity_set: Dict) -> str:
        """Construit description pour logs"""
        return self._build_entity_label(entity_set)

    def _calculate_comparison(
        self,
        entity_results: List[Dict],
        preprocessed_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calcule la comparaison entre entités

        Args:
            entity_results: Résultats avec données
            preprocessed_data: Données préprocessées

        Returns:
            Dict avec données de comparaison complètes
        """
        if len(entity_results) < 2:
            raise ValueError("Besoin de 2 entités minimum")

        # Extraction métriques
        metric1 = self._extract_best_metric(entity_results[0]["data"])
        metric2 = self._extract_best_metric(entity_results[1]["data"])

        if not metric1 or not metric2:
            raise ValueError("Métriques manquantes pour comparaison")

        # Validation cohérence
        if metric1.get("metric_name") != metric2.get("metric_name"):
            logger.warning(
                f"Métriques différentes: {metric1.get('metric_name')} vs {metric2.get('metric_name')}"
            )

        metric_name = metric1.get("metric_name", "unknown")

        # Extraction valeurs
        value1 = self._extract_numeric_value(metric1)
        value2 = self._extract_numeric_value(metric2)

        # Validation valeurs
        if value1 is None or value2 is None:
            raise ValueError("Valeurs numériques manquantes")

        if value1 == 0 or value2 == 0:
            raise ValueError("Valeur nulle détectée - comparaison impossible")

        # Calcul différences
        difference_absolute = value1 - value2
        difference_percent = (difference_absolute / value2) * 100 if value2 != 0 else 0

        # Déterminer meilleur
        is_lower_better = self._is_lower_better_metric(metric_name)
        if is_lower_better:
            better_label = (
                entity_results[0]["label"]
                if value1 < value2
                else entity_results[1]["label"]
            )
        else:
            better_label = (
                entity_results[0]["label"]
                if value1 > value2
                else entity_results[1]["label"]
            )

        # Construction résultat complet
        return {
            "metric_name": metric_name,
            "label1": entity_results[0]["label"],
            "label2": entity_results[1]["label"],
            "value1": value1,
            "value2": value2,
            "difference_absolute": difference_absolute,
            "difference_percent": difference_percent,
            "better": better_label,
            "is_lower_better": is_lower_better,
            "unit": metric1.get("unit", ""),
            "age_days": entity_results[0]["entity_set"].get("age_days"),
            "sex": entity_results[0]["entity_set"].get("sex"),
            "context": {
                "metric_full": metric1,
                "entity1_data": entity_results[0],
                "entity2_data": entity_results[1],
            },
        }

    def _extract_best_metric(self, docs: List) -> Optional[Dict]:
        """
        Extrait la meilleure métrique d'une liste de documents

        Args:
            docs: Liste de documents/métriques

        Returns:
            Dict avec métrique ou None
        """
        # Conversion docs en dicts si nécessaire
        docs_as_dicts = []
        for doc in docs:
            if isinstance(doc, dict):
                docs_as_dicts.append(doc)
            elif hasattr(doc, "__dict__"):
                docs_as_dicts.append(doc.__dict__)
            elif hasattr(doc, "to_dict"):
                docs_as_dicts.append(doc.to_dict())
            else:
                logger.warning(f"Document format inconnu: {type(doc)}")

        # DEBUG: Log des docs convertis
        logger.debug(f"📊 _extract_best_metric: {len(docs_as_dicts)} docs convertis")
        if docs_as_dicts:
            first_doc_keys = list(docs_as_dicts[0].keys()) if docs_as_dicts[0] else []
            logger.debug(f"📊 Clés du premier doc: {first_doc_keys}")
            logger.debug(f"📊 Premier doc complet: {docs_as_dicts[0]}")

        # Recherche par priorité (matching partiel pour "body_weight for males" etc.)
        for metric_name in self.METRIC_PRIORITIES:
            for doc_dict in docs_as_dicts:
                # ✅ FIX: Les métriques PostgreSQL ont metric_name dans metadata, pas à la racine
                metadata = doc_dict.get("metadata", {})
                doc_metric = metadata.get("metric_name", "").lower()
                priority_metric = metric_name.lower()

                # Matching partiel: commence par ou contient la priorité
                if doc_metric.startswith(priority_metric) or priority_metric in doc_metric:
                    logger.debug(f"Métrique sélectionnée: {metadata.get('metric_name')} (priorité: {metric_name})")
                    # Retourner les metadata (pas le doc entier avec "content" et "score")
                    return metadata

        # Fallback: premier doc disponible avec valeur numérique
        for doc_dict in docs_as_dicts:
            metadata = doc_dict.get("metadata", {})
            if metadata.get("value_numeric") is not None:
                logger.debug(f"Métrique fallback: {metadata.get('metric_name')}")
                return metadata

        logger.warning("Aucune métrique valide trouvée")
        return None

    def _extract_numeric_value(self, metric: Dict) -> Optional[float]:
        """Extrait la valeur numérique d'une métrique"""
        value = metric.get("value_numeric")

        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                logger.warning(f"Conversion valeur impossible: {value}")

        return None

    def _is_lower_better_metric(self, metric_name: str) -> bool:
        """
        Détermine si une valeur plus basse est meilleure

        Args:
            metric_name: Nom de la métrique

        Returns:
            True si plus bas = meilleur
        """
        metric_lower = metric_name.lower()

        # Vérification explicite LOWER is better
        if any(kw in metric_lower for kw in self.LOWER_IS_BETTER.keys()):
            return True

        # Vérification explicite HIGHER is better
        if any(kw in metric_lower for kw in self.HIGHER_IS_BETTER.keys()):
            return False

        # Par défaut: HIGHER is better
        logger.debug(f"Métrique {metric_name}: higher is better (défaut)")
        return False

    def _determine_better_entity(self, comparison_data: Dict) -> str:
        """Détermine quelle entité est meilleure"""
        return comparison_data.get("better", comparison_data.get("label1"))

    def _detect_comparison_dimension(
        self, comparison_entities: List[Dict]
    ) -> Optional[ComparisonDimension]:
        """
        Détecte la dimension de comparaison (sexe, breed, âge)

        Args:
            comparison_entities: Liste d'entités à comparer

        Returns:
            ComparisonDimension ou None
        """
        if len(comparison_entities) < 2:
            return None

        entity1 = comparison_entities[0]
        entity2 = comparison_entities[1]

        # Comparaison SEX
        if (
            entity1.get("sex") != entity2.get("sex")
            and entity1.get("breed") == entity2.get("breed")
            and entity1.get("age_days") == entity2.get("age_days")
        ):
            return ComparisonDimension.SEX

        # Comparaison BREED
        if (
            entity1.get("breed") != entity2.get("breed")
            and entity1.get("sex") == entity2.get("sex")
            and entity1.get("age_days") == entity2.get("age_days")
        ):
            return ComparisonDimension.BREED

        # Comparaison AGE
        if (
            entity1.get("age_days") != entity2.get("age_days")
            and entity1.get("breed") == entity2.get("breed")
            and entity1.get("sex") == entity2.get("sex")
        ):
            return ComparisonDimension.AGE

        return None

    async def _compare_with_fallback(
        self,
        comparison_entities: List[Dict],
        preprocessed_data: Dict[str, Any],
    ) -> ComparisonResult:
        """
        Tentative de comparaison avec critères assouplis

        Args:
            comparison_entities: Entités à comparer
            preprocessed_data: Données preprocessées

        Returns:
            ComparisonResult avec fallback
        """
        logger.info("Tentative comparaison avec fallback (critères assouplis)")

        try:
            # Relaxer les critères de recherche
            entity_results = []
            for entity_set in comparison_entities:
                # Retirer strict_sex_match
                relaxed_entity = entity_set.copy()

                result = await self.postgresql_system.search_metrics(
                    query=f"Métrique {self._build_entity_label(entity_set)}",
                    entities=relaxed_entity,
                    top_k=20,  # Plus de résultats
                    strict_sex_match=False,  # Critères assouplis
                )

                if result and hasattr(result, "context_docs") and result.context_docs:
                    entity_results.append(
                        {
                            "label": self._build_entity_label(entity_set),
                            "data": result.context_docs,
                            "entity_set": entity_set,
                        }
                    )

            if len(entity_results) >= 2:
                comparison_data = self._calculate_comparison(
                    entity_results, preprocessed_data
                )

                return ComparisonResult(
                    success=True,
                    status=ComparisonStatus.SUCCESS,
                    comparison_data=comparison_data,
                    entities_compared=[r["label"] for r in entity_results],
                    fallback_used=True,
                    warnings=["Résultats avec critères assouplis"],
                    metadata={"fallback": "relaxed_criteria"},
                )

        except Exception as e:
            logger.error(f"Erreur fallback: {e}")

        return ComparisonResult(
            success=False,
            status=ComparisonStatus.INSUFFICIENT_DATA,
            error="Données insuffisantes même avec critères assouplis",
        )

    async def generate_response(
        self,
        query: str,
        comparison_result: ComparisonResult,
        language: str = "fr",
        use_openai: bool = True,
    ) -> str:
        """
        Génère réponse textuelle pour la comparaison

        Args:
            query: Question originale
            comparison_result: Résultat de comparaison
            language: Langue de réponse ('fr' ou 'en')
            use_openai: Utiliser OpenAI pour enrichissement

        Returns:
            Texte de réponse formaté
        """
        if not comparison_result.success:
            return self._generate_error_response(comparison_result, language)

        data = comparison_result.comparison_data

        # Ensure data is not None (should never happen if success=True, but type safety)
        if data is None:
            logger.error("comparison_data is None despite success=True")
            return self._generate_error_response(comparison_result, language)

        # Tentative enrichissement OpenAI
        if use_openai:
            try:
                enhanced = await self._generate_openai_response(query, data, language)
                if enhanced:
                    return enhanced
            except Exception as e:
                logger.warning(f"Enrichissement OpenAI échoué: {e}")

        # Fallback sur template
        return self._generate_template_response(data, language)

    def _generate_template_response(self, data: Dict[str, Any], language: str) -> str:
        """Génère réponse basée sur template (avec traduction)"""

        # Template EN avec traduction dynamique
        intro = _translate("To answer your question about the comparison between", language)
        diff_label = _translate("Difference", language)
        better_label = _translate("Better performance", language)

        response = f"""{intro} **{data['label1']}** et **{data['label2']}** :

**{data['metric_name']}** :
- {data['label1']} : {data['value1']:.2f} {data['unit']}
- {data['label2']} : {data['value2']:.2f} {data['unit']}

**{diff_label}** : {abs(data['difference_absolute']):.2f} {data['unit']} ({abs(data['difference_percent']):.1f}%)

**{better_label}** : {data['better']}"""

        return response

    async def _generate_openai_response(
        self,
        query: str,
        data: Dict[str, Any],
        language: str,
    ) -> Optional[str]:
        """Génère réponse enrichie via OpenAI"""

        # Vérifier disponibilité OpenAI
        if not self.postgresql_system:
            return None

        try:
            from openai import AsyncOpenAI
            import os

            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            system_prompt = f"""Tu es un expert en aviculture qui génère des réponses comparatives claires.

RÈGLES CRITIQUES:
1. Reformule la question au début pour donner le contexte
2. Utilise les noms corrects: "Cobb 500", "Ross 308" (majuscules)
3. Présente les deux entités de manière identique, SANS mettre l'une en gras
4. Pour FCR et mortalité: valeur PLUS BASSE est MEILLEURE
5. Pour poids et production: valeur PLUS HAUTE est MEILLEURE
6. Fournis interprétation concise de l'écart
7. NE termine PAS par "Impact pratique" ou "Recommandations"

Langue: {language}"""

            user_prompt = f"""Génère réponse concise pour cette comparaison:

Données:
- Métrique: {data['metric_name']}
- {data['label1']}: {data['value1']:.3f} {data['unit']}
- {data['label2']}: {data['value2']:.3f} {data['unit']}
- Différence: {abs(data['difference_absolute']):.3f} ({abs(data['difference_percent']):.1f}%)
- Meilleur: {data['better']}
- Type: {"moins est mieux" if data['is_lower_better'] else "plus est mieux"}"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Erreur OpenAI: {e}")
            return None

    def _generate_error_response(self, result: ComparisonResult, language: str) -> str:
        """Génère message d'erreur lisible (avec traduction)"""

        if result.status == ComparisonStatus.INSUFFICIENT_DATA:
            msg = _translate("Unable to compare: insufficient data.", language)
            return f"{msg} {result.error or ''}"
        elif result.status == ComparisonStatus.INCOMPATIBLE_METRICS:
            msg = _translate("Unable to compare: incompatible metrics.", language)
            return f"{msg} {result.error or ''}"
        elif result.status == ComparisonStatus.INCOMPATIBLE_SPECIES:
            msg = _translate("Unable to compare: different species.", language)
            return f"{msg} {result.error or ''}"
        else:
            error_label = _translate("Comparison error", language)
            unknown = _translate("Unknown error", language)
            return f"{error_label}: {result.error or unknown}"


# Factory function
def create_comparison_engine(postgresql_system=None) -> ComparisonEngine:
    """Factory pour créer une instance ComparisonEngine"""
    return ComparisonEngine(postgresql_system=postgresql_system)


# Tests unitaires
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=== TESTS COMPARISON ENGINE ===\n")

    # Test sans PostgreSQL (structure seulement)
    engine = ComparisonEngine(postgresql_system=None)

    # Test détection dimension
    test_entities = [
        {"breed": "cobb500", "sex": "male", "age_days": 21},
        {"breed": "cobb500", "sex": "female", "age_days": 21},
    ]

    dimension = engine._detect_comparison_dimension(test_entities)
    print(f"✅ Dimension détectée: {dimension}")

    # Test labels
    label1 = engine._build_entity_label(test_entities[0])
    label2 = engine._build_entity_label(test_entities[1])
    print(f"✅ Labels: {label1} vs {label2}")

    # Test is_lower_better
    print(
        f"✅ FCR (lower better): {engine._is_lower_better_metric('feed_conversion_ratio')}"
    )
    print(
        f"✅ Weight (higher better): {not engine._is_lower_better_metric('body_weight')}"
    )

    # Test validation species
    print("\n=== TEST VALIDATION SPECIES ===")
    test_comparison_same_species = [
        {"breed": "cobb500", "sex": "male", "age_days": 21},
        {"breed": "ross308", "sex": "male", "age_days": 21},
    ]

    # Simuler une comparaison pour vérifier la validation
    print("Test: Cobb500 vs Ross308 (même espèce - poulet)")
    compatible1, reason1 = engine.breeds_registry.are_comparable("cobb500", "ross308")
    print(f"  Compatible: {compatible1} - {reason1 if not compatible1 else 'OK'}")

    # Test avec espèces différentes (si disponibles)
    try:
        print("\nTest: Cobb500 vs BUT6 (espèces différentes)")
        compatible2, reason2 = engine.breeds_registry.are_comparable("cobb500", "but6")
        print(f"  Compatible: {compatible2} - {reason2 if not compatible2 else 'OK'}")
    except Exception as e:
        print(f"  Note: {e}")

    print("\n✅ ComparisonEngine structurellement valide avec validation species")
    print("Note: Tests complets nécessitent PostgreSQLSystem fonctionnel")
