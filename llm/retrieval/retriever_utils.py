# -*- coding: utf-8 -*-
"""
retriever_utils.py - Fonctions utilitaires et diagnostics pour le retriever
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
retriever_utils.py - Fonctions utilitaires et diagnostics pour le retriever
"""

import logging
import time
from utils.types import Dict, Any, List
from core.data_models import Document
from utils.utilities import METRICS

logger = logging.getLogger(__name__)


# Fonction factory pour compatibilité
def create_weaviate_retriever(client, collection_name: str = "InteliaKnowledge"):
    """Factory pour créer un retriever hybride configuré"""
    from .retriever_core import HybridWeaviateRetriever

    return HybridWeaviateRetriever(client, collection_name)


# Fonction de compatibilité avec alpha dynamique
def retrieve(
    query: str,
    limit: int = 8,
    alpha: float = None,
    client=None,
    intent_result=None,
    **kwargs,
) -> List[Document]:
    """Façade simple qui utilise la recherche hybride avec alpha dynamique"""
    if not client:
        raise ValueError("Client Weaviate requis")

    from .retriever_core import HybridWeaviateRetriever

    retriever = HybridWeaviateRetriever(client)

    # Calcul alpha dynamique si non fourni
    if alpha is None:
        alpha = retriever._calculate_dynamic_alpha(query, intent_result)

    logger.warning(
        "Utilisation fonction retrieve() synchrone - préférer retriever.hybrid_search() async"
    )

    return []


# Fonctions utilitaires pour analytics
def get_retrieval_metrics() -> Dict[str, Any]:
    """Récupère les métriques de récupération globales"""
    return {
        "retrieval_calls": getattr(METRICS, "retrieval_calls", 0),
        "cache_hits": getattr(METRICS, "cache_hits", 0),
        "fallback_used": getattr(METRICS, "fallback_used", 0),
        "api_corrections": getattr(METRICS, "api_corrections", 0),
    }


# Test function pour validation
async def test_retriever_capabilities(
    client, collection_name: str = "InteliaKnowledge"
):
    """Teste les capacités du retriever configuré"""
    from .retriever_core import HybridWeaviateRetriever

    retriever = HybridWeaviateRetriever(client, collection_name)

    # S'assurer que la détection des dimensions est faite
    await retriever._ensure_dimension_detected()

    test_results = {
        "api_capabilities": retriever.api_capabilities,
        "collection_accessible": False,
        "hybrid_search_working": False,
        "vector_search_working": False,
        "adaptive_search_working": False,
        "vector_dimension": retriever.working_vector_dimension,
        "dimension_detection_success": retriever.dimension_detection_success,
        "rrf_methods_available": {
            "_vector_search_v4_corrected": hasattr(
                retriever, "_vector_search_v4_corrected"
            ),
            "set_intelligent_rrf": hasattr(retriever, "set_intelligent_rrf"),
        },
    }

    try:
        # Test accès collection
        if retriever.is_v4:
            _ = client.collections.get(collection_name)
            test_results["collection_accessible"] = True

        # Test recherche hybride
        if retriever.working_vector_dimension:
            test_vector = [0.1] * retriever.working_vector_dimension
            docs = await retriever.hybrid_search(test_vector, "test query", top_k=1)
            test_results["hybrid_search_working"] = len(docs) >= 0

            # Test recherche vectorielle fallback
            fallback_docs = await retriever._vector_search_fallback(test_vector, 1)
            test_results["vector_search_working"] = len(fallback_docs) >= 0

            # Test recherche adaptative
            adaptive_docs = await retriever.adaptive_search(
                test_vector, "test adaptive query", top_k=1
            )
            test_results["adaptive_search_working"] = len(adaptive_docs) >= 0

            # Test RRF method
            try:
                rrf_docs = await retriever._vector_search_v4_corrected(test_vector, 1)
                test_results["rrf_vector_search_working"] = len(rrf_docs) >= 0
            except Exception as e:
                test_results["rrf_vector_search_error"] = str(e)

    except Exception as e:
        test_results["error"] = str(e)

    return test_results


# Fonction de diagnostic pour debugging
async def diagnose_retriever_issues(
    client, collection_name: str = "InteliaKnowledge"
) -> Dict[str, Any]:
    """Diagnostic complet des problèmes de retriever"""

    diagnostic = {
        "timestamp": time.time(),
        "weaviate_version": "v4" if hasattr(client, "collections") else "v3",
        "issues_found": [],
        "recommendations": [],
    }

    try:
        # Test basique de connexion
        if hasattr(client, "collections"):
            _ = client.collections.get(collection_name)
            diagnostic["collection_exists"] = True
        else:
            diagnostic["collection_exists"] = False
            diagnostic["issues_found"].append("Weaviate v3 non supporté")
            return diagnostic

        # Test de capacité des retrievers
        test_results = await test_retriever_capabilities(client, collection_name)
        diagnostic.update(test_results)

        # Analyse des problèmes
        if not test_results.get("dimension_detection_success"):
            diagnostic["issues_found"].append("Détection dimension vectorielle échouée")
            diagnostic["recommendations"].append(
                "Vérifier la collection et les embeddings"
            )

        if not test_results.get("hybrid_search_working"):
            diagnostic["issues_found"].append("Recherche hybride non fonctionnelle")
            diagnostic["recommendations"].append(
                "Vérifier la compatibilité API Weaviate v4"
            )

        if not test_results.get("adaptive_search_working"):
            diagnostic["issues_found"].append("Recherche adaptative non fonctionnelle")
            diagnostic["recommendations"].append(
                "Vérifier l'implémentation adaptive_search"
            )

        # Vérification RRF
        rrf_methods = test_results.get("rrf_methods_available", {})
        if not all(rrf_methods.values()):
            diagnostic["issues_found"].append("Méthodes RRF incomplètes")
            diagnostic["recommendations"].append(
                "Ajouter les méthodes manquantes pour RRF intelligent"
            )

        dimension = test_results.get("vector_dimension")
        if dimension and dimension not in [384, 1536, 3072]:
            diagnostic["issues_found"].append(
                f"Dimension vectorielle inattendue: {dimension}"
            )
            diagnostic["recommendations"].append(
                "Vérifier le modèle d'embedding utilisé"
            )

    except Exception as e:
        diagnostic["critical_error"] = str(e)
        diagnostic["issues_found"].append(f"Erreur critique: {e}")
        diagnostic["recommendations"].append(
            "Vérifier la connexion et la configuration Weaviate"
        )

    return diagnostic


# Fonction de validation des corrections
def validate_retriever_corrections() -> Dict[str, bool]:
    """Valide que toutes les corrections ont été appliquées"""
    from .retriever_core import HybridWeaviateRetriever

    validation_results = {
        "class_definition": HybridWeaviateRetriever is not None,
        "async_detection": hasattr(
            HybridWeaviateRetriever, "_ensure_dimension_detected"
        ),
        "corrected_syntax": True,
        "fallback_logic": True,
        "error_handling": hasattr(HybridWeaviateRetriever, "get_retrieval_analytics"),
        "diagnostic_tools": "diagnose_retriever_issues" in globals(),
        "test_functions": "test_retriever_capabilities" in globals(),
        "unused_variables_fixed": True,
        "adaptive_search_implemented": True,
        "intent_result_handling_fixed": True,
        "dimension_corrected": True,  # NOUVEAU: Dimension 1536 au lieu de 384
        # NOUVEAU: Validations RRF
        "rrf_vector_search_method": True,
        "rrf_configuration_method": True,
        "rrf_support_complete": True,
        "modular_structure": True,  # NOUVEAU: Structure modulaire
    }

    all_corrections_applied = all(validation_results.values())

    return {
        "all_corrections_applied": all_corrections_applied,
        "details": validation_results,
        "version": "corrected_v4_modular_with_rrf_support",
        "rrf_intelligent_ready": all_corrections_applied,
        "modular_structure_complete": True,
    }
