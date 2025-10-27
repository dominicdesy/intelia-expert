# -*- coding: utf-8 -*-
"""
rag_json_system.py - Système de recherche JSON avicole
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
rag_json_system.py - Système de recherche JSON avicole
Extrait du fichier principal pour modularité
"""

import logging
import time
from utils.types import Dict, List, Optional, Any

try:
    from rag.extractors.json_extractor import JSONExtractor
    from rag.extractors.table_extractor import TableExtractor
    from rag.extractors.genetic_line_extractor import GeneticLineExtractor
    from rag.models.validation import JSONValidator, ValidationRequest
    from rag.models.ingestion import IngestionPipeline, IngestionRequest
    from rag.core.hybrid_search import HybridSearchEngine
    from rag.core.document_processor import DocumentProcessor
    from rag.core.cache_manager import EnhancedCacheManager

    JSON_EXTRACTORS_AVAILABLE = True
except ImportError:
    JSON_EXTRACTORS_AVAILABLE = False

from .data_models import RAGResult, RAGSource, Document
from config.config import RAG_SIMILARITY_TOP_K
from .base import InitializableMixin

logger = logging.getLogger(__name__)


class JSONSystem(InitializableMixin):
    """Système de recherche JSON avicole"""

    def __init__(self):
        super().__init__()

        # Extracteurs spécialisés
        self.json_extractor = None
        self.table_extractor = None
        self.genetic_line_extractor = None

        # Validateur et pipeline
        self.json_validator = None
        self.ingestion_pipeline = None

        # Moteur de recherche hybride
        self.hybrid_search_engine = None
        self.document_processor = None
        self.enhanced_cache_manager = None

        # Statistiques
        self.json_stats = {
            "validations": 0,
            "ingestions": 0,
            "searches": 0,
            "table_extractions": 0,
            "genetic_line_detections": 0,
            "performance_metrics_processed": 0,
        }

    async def initialize(self):
        """Initialise le système JSON"""

        if not JSON_EXTRACTORS_AVAILABLE:
            raise ImportError("Extracteurs JSON non disponibles")

        try:
            logger.info("🔧 Initialisation système RAG JSON...")

            # Extracteurs spécialisés
            self.json_extractor = JSONExtractor()
            self.table_extractor = TableExtractor()
            self.genetic_line_extractor = GeneticLineExtractor()

            # Validateur JSON
            self.json_validator = JSONValidator()

            # Pipeline d'ingestion
            self.ingestion_pipeline = IngestionPipeline(
                json_extractor=self.json_extractor,
                table_extractor=self.table_extractor,
                genetic_line_extractor=self.genetic_line_extractor,
                validator=self.json_validator,
            )

            # Cache amélioré
            try:
                self.enhanced_cache_manager = EnhancedCacheManager()
                await self.enhanced_cache_manager.initialize()
                logger.info("✅ Cache JSON activé")
            except Exception as e:
                logger.warning(f"Cache JSON échoué: {e}")
                self.enhanced_cache_manager = None

            # Processeur de documents
            self.document_processor = DocumentProcessor(
                extractors={
                    "json": self.json_extractor,
                    "table": self.table_extractor,
                    "genetic_line": self.genetic_line_extractor,
                }
            )

            await super().initialize()
            logger.info("✅ Système RAG JSON initialisé")

        except Exception as e:
            logger.error(f"❌ Erreur initialisation système JSON: {e}")
            raise

    def set_weaviate_client(self, weaviate_client):
        """Configure le client Weaviate pour le moteur hybride"""
        if self.enhanced_cache_manager:
            try:
                self.hybrid_search_engine = HybridSearchEngine(
                    weaviate_client=weaviate_client,
                    cache_manager=self.enhanced_cache_manager,
                )
                logger.info("✅ Moteur de recherche hybride JSON configuré")
            except Exception as e:
                logger.warning(f"Moteur hybride JSON échoué: {e}")

    async def validate_json_document(
        self, json_data: Dict[str, Any], strict_mode: bool = False
    ) -> Dict[str, Any]:
        """Valide un document JSON selon les schémas avicoles"""

        if not self.is_initialized or not self.json_validator:
            return {"valid": False, "error": "Système JSON non disponible"}

        try:
            self.json_stats["validations"] += 1

            validation_request = ValidationRequest(
                json_data=json_data, strict_mode=strict_mode, auto_enrich=True
            )

            result = await self.json_validator.validate_document(validation_request)

            logger.info(
                f"Validation JSON: {'✅ Valide' if result.is_valid else '❌ Invalide'}"
            )

            return {
                "valid": result.is_valid,
                "enriched_data": result.enriched_data,
                "metadata": result.metadata,
                "errors": result.errors,
                "warnings": result.warnings,
            }

        except Exception as e:
            logger.error(f"Erreur validation JSON: {e}")
            return {"valid": False, "error": str(e)}

    async def ingest_json_documents(
        self, json_files: List[Dict[str, Any]], batch_size: int = 5
    ) -> Dict[str, Any]:
        """Ingère des documents JSON dans le système"""

        if not self.is_initialized or not self.ingestion_pipeline:
            return {"success": False, "error": "Système JSON non disponible"}

        try:
            self.json_stats["ingestions"] += 1

            ingestion_request = IngestionRequest(
                json_files=json_files, batch_size=batch_size, force_reprocess=False
            )

            result = await self.ingestion_pipeline.process_documents(ingestion_request)

            logger.info(
                f"Ingestion JSON: {result.processed_count}/{result.total_count} documents traités"
            )

            return {
                "success": True,
                "processed_count": result.processed_count,
                "total_count": result.total_count,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error(f"Erreur ingestion JSON: {e}")
            return {"success": False, "error": str(e)}

    async def search_enhanced(
        self,
        query: str,
        genetic_line: Optional[str] = None,
        performance_metrics: Optional[List[str]] = None,
        age_range: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """Recherche avancée dans les documents JSON avec filtres avicoles"""

        if not self.is_initialized or not self.hybrid_search_engine:
            logger.warning(
                "Recherche JSON non disponible, utilisation du système classique"
            )
            return []

        try:
            self.json_stats["searches"] += 1

            # Construction des filtres avicoles
            filters = {}
            if genetic_line:
                filters["genetic_line"] = genetic_line
            if performance_metrics:
                filters["performance_metrics"] = performance_metrics
            if age_range:
                filters["age_range"] = age_range

            # Recherche hybride spécialisée
            results = await self.hybrid_search_engine.search_with_filters(
                query=query, filters=filters, top_k=RAG_SIMILARITY_TOP_K
            )

            logger.info(f"Recherche JSON: {len(results)} résultats trouvés")

            return results

        except Exception as e:
            logger.error(f"Erreur recherche JSON: {e}")
            return []

    async def generate_response_from_results(
        self,
        query: str,
        json_results: List[Dict[str, Any]],
        language: str,
        conversation_context: List[Dict],
        start_time: float,
    ) -> RAGResult:
        """Génère une réponse basée sur les résultats JSON"""

        try:
            # Conversion des résultats JSON en Documents pour compatibilité
            documents = []
            for result in json_results:
                doc = Document(
                    content=result.get("content", ""),
                    metadata=result.get("metadata", {}),
                    score=result.get("score", 0.8),
                )
                documents.append(doc)

            # Pour l'instant, génération simple - pourrait utiliser un générateur dédié
            response_text = self._generate_simple_response_from_json(
                query, json_results
            )

            return RAGResult(
                source=RAGSource.RAG_SUCCESS,
                answer=response_text,
                confidence=0.9,  # Confiance élevée pour résultats JSON
                metadata={
                    "json_system_used": True,
                    "json_results_count": len(json_results),
                    "genetic_lines_detected": list(
                        set(
                            r.get("metadata", {}).get("genetic_line")
                            for r in json_results
                            if r.get("metadata", {}).get("genetic_line")
                        )
                    ),
                    "processing_time": time.time() - start_time,
                    "system_version": "5.1_json_primary",
                },
            )

        except Exception as e:
            logger.error(f"Erreur génération réponse JSON: {e}")
            return RAGResult(
                source=RAGSource.GENERATION_FAILED,
                metadata={"error": str(e), "json_system_used": True},
            )

    def _generate_simple_response_from_json(
        self, query: str, json_results: List[Dict[str, Any]]
    ) -> str:
        """Génération simple de réponse depuis JSON (fallback)"""

        if not json_results:
            return "Aucun résultat trouvé dans la base de données avicole."

        # Extraction des données pertinentes
        response_parts = []

        for i, result in enumerate(json_results[:3], 1):  # Top 3 résultats
            content = result.get("content", "")
            metadata = result.get("metadata", {})

            # Extraction info génétique si disponible
            genetic_info = ""
            if metadata.get("genetic_line"):
                genetic_info = f" ({metadata['genetic_line']})"

            response_parts.append(
                f"**Résultat {i}**{genetic_info}:\n{content[:200]}..."
            )

        response = "\n\n".join(response_parts)

        if len(json_results) > 3:
            response += (
                f"\n\n*Et {len(json_results) - 3} autres résultats disponibles.*"
            )

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du système JSON"""

        return {
            "json_system_initialized": self.is_initialized,
            "extractors_available": JSON_EXTRACTORS_AVAILABLE,
            "hybrid_search_configured": bool(self.hybrid_search_engine),
            "enhanced_cache_enabled": bool(self.enhanced_cache_manager),
            "statistics": self.json_stats.copy(),
            "components": {
                "json_extractor": bool(self.json_extractor),
                "table_extractor": bool(self.table_extractor),
                "genetic_line_extractor": bool(self.genetic_line_extractor),
                "json_validator": bool(self.json_validator),
                "ingestion_pipeline": bool(self.ingestion_pipeline),
                "document_processor": bool(self.document_processor),
            },
        }

    async def close(self):
        """Fermeture propre du système JSON"""

        if self.enhanced_cache_manager:
            try:
                await self.enhanced_cache_manager.close()
                logger.info("Cache JSON fermé")
            except Exception as e:
                logger.warning(f"Erreur fermeture cache JSON: {e}")

        await super().close()
        logger.info("Système JSON fermé")
