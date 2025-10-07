# -*- coding: utf-8 -*-
"""
comparison_handler.py - Wrapper de compatibilité vers ComparisonEngine
VERSION REFACTORISÉE: Délègue toute la logique au nouveau ComparisonEngine unifié

CHANGEMENTS:
- Supprimé: ~700 lignes de logique métier dupliquée
- Ajouté: Wrapper simple de ~100 lignes vers ComparisonEngine
- Conservation: Compatibilité totale avec l'API existante
"""

import logging
from utils.types import Dict, List, Any

# Import du nouveau moteur unifié
from ..comparison_engine import ComparisonEngine, ComparisonResult

logger = logging.getLogger(__name__)


class ComparisonHandler:
    """
    Wrapper legacy pour compatibilité avec le code existant

    Délègue toute la logique métier au ComparisonEngine unifié qui centralise:
    - comparison_handler.py (orchestration)
    - comparison_utils.py (extraction et parsing)
    - comparison_response_generator.py (génération réponses)

    Le MetricCalculator reste séparé pour les calculs mathématiques purs.
    """

    def __init__(self, postgresql_system):
        """
        Initialise le wrapper avec le moteur unifié

        Args:
            postgresql_system: Instance PostgreSQLSystem pour récupération données
        """
        # Délégation au moteur unifié
        self.engine = ComparisonEngine(postgresql_system)

        # Conserver référence pour compatibilité
        self.postgresql_system = postgresql_system

        logger.info("✅ ComparisonHandler initialisé (wrapper → ComparisonEngine)")

    async def handle_comparison_query(
        self, preprocessed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Point d'entrée principal - DÉLÈGUE au ComparisonEngine

        Args:
            preprocessed_data: Données preprocessées avec:
                - comparison_entities: List[Dict]
                - entities: Dict
                - normalized_query: str

        Returns:
            Dict au format harmonisé attendu par rag_engine_handlers:
            {
                "success": bool,
                "comparison": Dict,
                "results": List[Dict],
                "context": Dict,
                "metadata": Dict,
                "error": Optional[str],
                "fallback_used": bool,
            }
        """
        logger.debug("🎯 ComparisonHandler.handle_comparison_query() appelé")

        # Délégation au moteur
        result = await self.engine.compare(preprocessed_data)

        # Conversion ComparisonResult → format Dict attendu par les handlers
        return {
            "success": result.success,
            "comparison": result.comparison_data,
            "results": self._format_results_for_handlers(result),
            "context": (
                result.comparison_data.get("context", {})
                if result.comparison_data
                else {}
            ),
            "metadata": {
                "query_type": "comparative",
                "entities_compared": len(result.entities_compared),
                "preprocessing_applied": True,
                "dimension": result.dimension.value if result.dimension else None,
                "fallback_used": result.fallback_used,
            },
            "error": result.error,
            "fallback_used": result.fallback_used,
        }

    def _format_results_for_handlers(self, result: ComparisonResult) -> List[Dict]:
        """
        Formate les résultats pour compatibilité avec rag_engine_handlers.py

        Args:
            result: ComparisonResult du moteur

        Returns:
            Liste au format attendu: [{"entity": str, "data": List[Dict]}]
        """
        if not result.success or not result.comparison_data:
            return []

        # Format attendu par ComparativeQueryHandler dans rag_engine_handlers.py
        formatted = []

        # Pour chaque entité comparée, créer une structure document
        for i, entity_label in enumerate(result.entities_compared):
            # Extraire les données de cette entité depuis comparison_data
            value_key = f"value{i+1}"

            if value_key in result.comparison_data:
                formatted.append(
                    {
                        "entity": entity_label,
                        "data": [
                            {
                                "metric_name": result.comparison_data.get(
                                    "metric_name"
                                ),
                                "value_numeric": result.comparison_data.get(value_key),
                                "unit": result.comparison_data.get("unit", "g"),
                                "age_days": result.comparison_data.get("age_days"),
                                "sex": result.comparison_data.get("sex"),
                                "breed": (
                                    entity_label.split()[0]
                                    if " " in entity_label
                                    else entity_label
                                ),
                            }
                        ],
                    }
                )

        logger.debug(f"📊 Results formatés: {len(formatted)} entités")
        return formatted

    async def handle_comparative_query(
        self, query: str, preprocessed: Dict[str, Any], top_k: int = 12
    ) -> Dict[str, Any]:
        """
        Version alternative pour compatibilité - REDIRIGE vers handle_comparison_query

        Maintient la compatibilité avec l'ancien code tout en utilisant
        la nouvelle structure harmonisée.

        Args:
            query: Requête utilisateur
            preprocessed: Données preprocessées
            top_k: Nombre de résultats (unused, pour compatibilité)

        Returns:
            Dict au format harmonisé
        """
        logger.info("🔄 Redirecting handle_comparative_query → handle_comparison_query")

        # Construire preprocessed_data au format attendu
        preprocessed_data = {
            "normalized_query": query,
            "original_query": query,
            "entities": preprocessed.get("entities", {}),
            "comparison_entities": preprocessed.get("comparison_entities", []),
            "routing_hint": "postgresql",
            "is_comparative": True,
        }

        # Appeler la méthode principale harmonisée
        return await self.handle_comparison_query(preprocessed_data)

    async def generate_comparative_response(
        self,
        query: str,
        comparison_result: Dict[str, Any],
        language: str = "fr",
    ) -> str:
        """
        Génération de réponse - DÉLÈGUE au ComparisonEngine

        Args:
            query: Question originale
            comparison_result: Résultat de comparaison (format Dict legacy)
            language: Langue de réponse ('fr' ou 'en')

        Returns:
            Texte de réponse formaté
        """
        logger.debug(f"📝 Génération réponse comparative (langue={language})")

        # Convertir Dict legacy → ComparisonResult pour le moteur
        from .comparison_engine import ComparisonStatus

        # Déterminer le status
        if comparison_result.get("success"):
            status = ComparisonStatus.SUCCESS
        elif "insufficient" in comparison_result.get("error", "").lower():
            status = ComparisonStatus.INSUFFICIENT_DATA
        else:
            status = ComparisonStatus.ERROR

        engine_result = ComparisonResult(
            success=comparison_result.get("success", False),
            status=status,
            comparison_data=comparison_result.get("comparison"),
            entities_compared=self._extract_entity_labels(comparison_result),
            error=comparison_result.get("error"),
            metadata=comparison_result.get("metadata", {}),
            fallback_used=comparison_result.get("fallback_used", False),
        )

        # Délégation au moteur pour génération
        return await self.engine.generate_response(
            query,
            engine_result,
            language,
            use_openai=True,
        )

    def _extract_entity_labels(self, comparison_result: Dict) -> List[str]:
        """Extrait les labels des entités depuis le résultat legacy"""
        comparison = comparison_result.get("comparison", {})

        # Essayer d'extraire depuis comparison
        if "entity1" in comparison and "entity2" in comparison:
            return [comparison["entity1"], comparison["entity2"]]

        # Essayer d'extraire depuis label1/label2
        if "label1" in comparison and "label2" in comparison:
            return [comparison["label1"], comparison["label2"]]

        # Fallback
        return ["Entité 1", "Entité 2"]

    async def handle_temporal_comparison(
        self, query: str, age_start: int, age_end: int, entities: Dict
    ) -> Dict:
        """
        Gère les comparaisons temporelles entre deux âges

        NOTE: Cette méthode pourrait aussi être déléguée au ComparisonEngine
        Pour l'instant, conservée pour compatibilité maximale

        Args:
            query: Requête utilisateur
            age_start: Âge de début (jours)
            age_end: Âge de fin (jours)
            entities: Entités de base

        Returns:
            Dict avec résultat de comparaison temporelle
        """
        logger.info(f"⏱️ Comparaison temporelle: {age_start}j → {age_end}j")

        # Créer les entités pour chaque âge
        comparison_entities = [
            {**entities, "age_days": age_start, "_comparison_label": f"{age_start}j"},
            {**entities, "age_days": age_end, "_comparison_label": f"{age_end}j"},
        ]

        # Utiliser le moteur standard avec ces entités
        preprocessed_data = {
            "normalized_query": query,
            "original_query": query,
            "entities": entities,
            "comparison_entities": comparison_entities,
            "is_comparative": True,
            "query_type": "temporal_range",
        }

        result = await self.handle_comparison_query(preprocessed_data)

        # Enrichir avec métadonnées temporelles
        if result.get("success"):
            comparison = result.get("comparison", {})
            result["comparison_type"] = "temporal"
            result["start_age"] = age_start
            result["end_age"] = age_end
            result["evolution"] = self._determine_evolution(comparison)

        return result

    def _determine_evolution(self, comparison: Dict) -> str:
        """Détermine le type d'évolution (croissance/diminution/stable)"""
        if not comparison:
            return "unknown"

        difference = comparison.get("difference_absolute", 0)
        percent_change = comparison.get("difference_percent", 0)

        if abs(percent_change) < 1:
            return "stable"
        elif difference > 0:
            return "croissance"
        else:
            return "diminution"


# ============================================================================
# FONCTIONS SUPPRIMÉES (déplacées dans comparison_engine.py)
# ============================================================================

# Les fonctions suivantes ont été SUPPRIMÉES de ce fichier et déplacées
# dans comparison_engine.py pour centralisation:
#
# ❌ _preserve_critical_fields() → dans ComparisonEngine
# ❌ _build_results_structure() → dans ComparisonEngine._format_results()
# ❌ _fallback_relaxed_search() → dans ComparisonEngine._compare_with_fallback()
# ❌ _compare_entities() → dans ComparisonEngine._calculate_comparison()
# ❌ _extract_best_metric_with_units() → dans ComparisonEngine._extract_best_metric()
# ❌ _compare_metrics_with_unit_handling() → fusionné dans _calculate_comparison()
# ❌ _extract_context_from_entities() → dans ComparisonEngine._calculate_comparison()
# ❌ _create_error_response() → gestion directe dans ComparisonResult
#
# GAIN: ~700 lignes supprimées, logique centralisée, plus de duplication


# ============================================================================
# COMPATIBILITÉ ET MIGRATION
# ============================================================================

"""
GUIDE DE MIGRATION:

1. Code existant utilisant ComparisonHandler:
   - ✅ Aucun changement nécessaire
   - ✅ Toutes les méthodes publiques conservées
   - ✅ Signatures identiques

2. Avantages de la refactorisation:
   - ✅ Code 8x plus simple (~100 lignes vs ~800)
   - ✅ Logique centralisée dans ComparisonEngine
   - ✅ Plus de duplication avec comparison_utils/comparison_response_generator
   - ✅ Tests plus faciles (tester ComparisonEngine directement)
   - ✅ Maintenance simplifiée (un seul endroit pour bugs/features)

3. Modules supprimés après refactorisation:
   - ❌ comparison_utils.py → fusionné dans comparison_engine.py
   - ❌ comparison_response_generator.py → fusionné dans comparison_engine.py

4. Module conservé:
   - ✅ metric_calculator.py → calculs mathématiques purs
"""
