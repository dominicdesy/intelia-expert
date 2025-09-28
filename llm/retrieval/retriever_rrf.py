# -*- coding: utf-8 -*-
"""
retriever_rrf.py - Support pour RRF (Reciprocal Rank Fusion) intelligent
"""

import logging
from typing import List
from core.data_models import Document
from utils.imports_and_dependencies import wvc

logger = logging.getLogger(__name__)


class RRFMixin:
    """Mixin contenant les méthodes pour le RRF intelligent"""

    async def _vector_search_v4_corrected(
        self, query_vector: List[float], top_k: int, where_filter: dict = None
    ) -> List[Document]:
        """Recherche vectorielle pure pour RRF intelligent"""
        try:
            if not self.client:
                logger.error("Client Weaviate non disponible")
                return []

            # S'assurer de la bonne dimension
            adjusted_vector = self._adjust_vector_dimension(query_vector)

            collection = self.client.collections.get(self.collection_name)

            # Construire les paramètres de requête
            search_params = {
                "limit": top_k,
                "return_metadata": wvc.query.MetadataQuery(score=True),
            }

            # Ajouter le filtre where si fourni
            if where_filter and self.api_capabilities.get("hybrid_with_where", True):
                v4_filter = self._to_v4_filter(where_filter)
                if v4_filter is not None:
                    search_params["where"] = v4_filter

            # Exécuter la requête vectorielle
            result = collection.query.near_vector(adjusted_vector, **search_params)

            # Convertir en Documents
            documents = []
            for obj in result.objects:
                try:
                    metadata = getattr(obj, "metadata", {})
                    properties = getattr(obj, "properties", {})

                    score = float(getattr(metadata, "score", 0.0))

                    doc = Document(
                        content=properties.get("content", ""),
                        metadata={
                            "title": properties.get("title", ""),
                            "source": properties.get("source", ""),
                            "geneticLine": properties.get("geneticLine", ""),
                            "species": properties.get("species", ""),
                            "phase": properties.get("phase", ""),
                            "age_band": properties.get("age_band", ""),
                            "search_type": "vector_pure",
                            "weaviate_id": str(getattr(obj, "uuid", "")),
                            **properties,
                        },
                        score=score,
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Erreur conversion objet Weaviate vectoriel: {e}")
                    continue

            logger.debug(
                f"Recherche vectorielle pure: {len(documents)} documents trouvés"
            )
            return documents

        except Exception as e:
            logger.error(f"Erreur recherche vectorielle v4 corrigée: {e}")
            return []

    def set_intelligent_rrf(self, intelligent_rrf):
        """Configure le RRF intelligent pour ce retriever"""
        self.intelligent_rrf = intelligent_rrf
        logger.info("✅ RRF Intelligent lié au retriever")
