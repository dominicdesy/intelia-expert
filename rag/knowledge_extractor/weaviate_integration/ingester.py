"""
Ingesteur Weaviate v4 avec schéma corrigé et complet
Version finale - Synchronisé avec models.py pour résoudre les problèmes de métadonnées
"""

import os
import logging
from typing import List, Dict, Any
from core.models import KnowledgeChunk


class WeaviateIngester:
    """Ingesteur Weaviate v4 avec schéma complet synchronisé"""

    def __init__(self, collection_name: str = "InteliaExpertKnowledge"):
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)
        self.client = None
        self._setup_weaviate_client()

    def _setup_weaviate_client(self):
        """Configure le client Weaviate v4 avec paramètres optimisés"""
        try:
            import weaviate

            weaviate_url = os.getenv(
                "WEAVIATE_URL", "https://intelia-expert-rag-9rhqrfcv.weaviate.network"
            )
            api_key = os.getenv("WEAVIATE_API_KEY")

            if not api_key:
                raise ValueError("WEAVIATE_API_KEY manquante dans .env")

            # Configuration v4 correcte
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(api_key),
                headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")},
            )

            self.logger.info(f"Client Weaviate v4 configuré: {weaviate_url}")
            self._ensure_collection_exists()

        except ImportError:
            raise ImportError("pip install weaviate-client requis")
        except Exception as e:
            self.logger.error(f"Erreur configuration Weaviate: {e}")
            raise

    def _ensure_collection_exists(self):
        """Vérifie et crée la collection si nécessaire"""
        try:
            if not self.client.collections.exists(self.collection_name):
                self.logger.info(f"Création collection {self.collection_name}")
                self._create_collection_v4()
            else:
                self.logger.info(f"Collection {self.collection_name} existe")
                # Optionnel: vérifier la compatibilité du schéma existant
                self._validate_existing_schema()

        except Exception as e:
            self.logger.error(f"Erreur vérification collection: {e}")

    def _create_collection_v4(self):
        """Crée la collection avec schéma COMPLET synchronisé avec models.py"""
        try:
            from weaviate.classes.config import Configure, Property, DataType

            self.client.collections.create(
                name=self.collection_name,
                properties=[
                    # Contenu principal (vectorisé)
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="Contenu textuel principal du chunk",
                    ),
                    # Métadonnées de document (DocumentContext)
                    Property(
                        name="genetic_line",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Lignée génétique (ross 308, cobb 500, etc.)",
                    ),
                    Property(
                        name="document_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de document (management_guide, performance_table, etc.)",
                    ),
                    Property(
                        name="species",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Espèce (broilers, layers, etc.)",
                    ),
                    Property(
                        name="target_audience",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Public cible du document",
                    ),
                    # Métadonnées de chunk (ChunkMetadata)
                    Property(
                        name="intent_category",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Catégorie d'intention (metric_query, environment_setting, etc.)",
                    ),
                    Property(
                        name="content_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de contenu du chunk",
                    ),
                    Property(
                        name="technical_level",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Niveau technique du contenu",
                    ),
                    Property(
                        name="detected_phase",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Phase détectée (starter, grower, finisher)",
                    ),
                    Property(
                        name="detected_bird_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type d'oiseau détecté",
                    ),
                    Property(
                        name="detected_site_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de site détecté",
                    ),
                    # Listes/Arrays
                    Property(
                        name="age_applicability",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Âges applicables du contenu",
                    ),
                    Property(
                        name="applicable_metrics",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Métriques applicables",
                    ),
                    Property(
                        name="actionable_recommendations",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Recommandations actionnables",
                    ),
                    Property(
                        name="followup_themes",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Thèmes de suivi suggérés",
                    ),
                    # Métriques numériques
                    Property(
                        name="confidence_score",
                        data_type=DataType.NUMBER,
                        skip_vectorization=True,
                        description="Score de confiance de l'analyse",
                    ),
                    Property(
                        name="word_count",
                        data_type=DataType.INT,
                        skip_vectorization=True,
                        description="Nombre de mots du chunk",
                    ),
                    # Identifiants et métadonnées système
                    Property(
                        name="chunk_id",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Identifiant unique du chunk",
                    ),
                    Property(
                        name="source_file",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Fichier source d'origine",
                    ),
                    Property(
                        name="extraction_timestamp",
                        data_type=DataType.DATE,
                        skip_vectorization=True,
                        description="Timestamp d'extraction RFC3339",
                    ),
                ],
                # Configuration vectorielle - syntaxe v4 corrigée
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small", vectorize_collection_name=False
                ),
            )

            self.logger.info(
                f"Collection {self.collection_name} créée avec schéma complet (19 propriétés)"
            )

        except Exception as e:
            self.logger.error(f"Erreur création collection: {e}")
            raise

    def _validate_existing_schema(self):
        """Valide que le schéma existant est compatible avec models.py"""
        try:
            collection = self.client.collections.get(self.collection_name)
            schema = collection.config.get()

            # Propriétés critiques qui doivent exister
            required_properties = {
                "genetic_line",
                "intent_category",
                "confidence_score",
                "target_audience",
                "content_type",
                "detected_phase",
                "applicable_metrics",
                "actionable_recommendations",
            }

            existing_properties = {prop.name for prop in schema.properties}
            missing_properties = required_properties - existing_properties

            if missing_properties:
                self.logger.warning(
                    f"Propriétés manquantes dans le schéma existant: {missing_properties}. "
                    "Considérez recréer la collection pour éviter les erreurs de métadonnées."
                )
            else:
                self.logger.info("Schéma existant compatible avec models.py")

        except Exception as e:
            self.logger.warning(f"Impossible de valider le schéma existant: {e}")

    async def ingest_batch(
        self, knowledge_chunks: List[KnowledgeChunk]
    ) -> Dict[str, Any]:
        """Ingère un batch de chunks avec validation stricte des données"""
        results = {
            "success": [],
            "errors": [],
            "total_processed": len(knowledge_chunks),
            "success_count": 0,
            "error_count": 0,
        }

        if not knowledge_chunks:
            self.logger.warning("Aucun chunk à ingérer")
            return results

        try:
            collection = self.client.collections.get(self.collection_name)

            # Préparation des objets avec validation renforcée
            objects_to_insert = []

            for chunk in knowledge_chunks:
                try:
                    obj = chunk.to_weaviate_object()

                    # Validation stricte des données critiques
                    if self._validate_object_complete(obj, chunk.chunk_id):
                        # Nettoyage et formatage final
                        cleaned_obj = self._clean_object_for_weaviate(obj)
                        objects_to_insert.append(cleaned_obj)

                        self.logger.debug(
                            f"Chunk {chunk.chunk_id} préparé: "
                            f"genetic_line='{obj.get('genetic_line')}', "
                            f"intent_category='{obj.get('intent_category')}'"
                        )
                    else:
                        results["errors"].append(
                            {
                                "chunk_id": chunk.chunk_id,
                                "error": "Validation complète échouée",
                                "genetic_line": obj.get("genetic_line", "N/A"),
                                "intent_category": obj.get("intent_category", "N/A"),
                            }
                        )
                        results["error_count"] += 1

                except Exception as e:
                    self.logger.error(f"Erreur préparation chunk {chunk.chunk_id}: {e}")
                    results["errors"].append(
                        {"chunk_id": chunk.chunk_id, "error": str(e)}
                    )
                    results["error_count"] += 1

            # Insertion par batch avec retry
            if objects_to_insert:
                self.logger.info(
                    f"Insertion de {len(objects_to_insert)} chunks avec schéma complet"
                )

                success_count = await self._insert_with_retry(
                    collection, objects_to_insert, results
                )
                results["success_count"] = success_count

                self.logger.info(
                    f"Ingestion terminée: {results['success_count']} succès, "
                    f"{results['error_count']} erreurs"
                )
            else:
                self.logger.error("Aucun objet valide à insérer après validation")

        except Exception as e:
            self.logger.error(f"Erreur ingestion batch: {e}")
            results["errors"].append({"error": str(e), "type": "batch_error"})
            results["error_count"] += 1

        return results

    def _validate_object_complete(self, obj: Dict[str, Any], chunk_id: str) -> bool:
        """Validation permissive d'un objet avant insertion - CORRECTION: Accepte plus de chunks"""
        try:
            # Vérifications de base SEULEMENT
            if not obj.get("content") or len(obj["content"].strip()) < 10:
                self.logger.warning(f"Contenu insuffisant pour {chunk_id}")
                return False

            if not obj.get("chunk_id"):
                self.logger.warning(f"chunk_id manquant pour {chunk_id}")
                return False

            # CORRECTION: Validation assouplie - Accepter "unknown" et "general"
            genetic_line = obj.get("genetic_line", "")
            if not genetic_line:  # Seulement si complètement vide
                self.logger.warning(f"genetic_line vide pour {chunk_id}")
                return False

            intent_category = obj.get("intent_category", "")
            if not intent_category:  # Seulement si complètement vide
                self.logger.warning(f"intent_category vide pour {chunk_id}")
                return False

            # Vérification types de données (gardées)
            if not isinstance(obj.get("confidence_score", 0), (int, float)):
                self.logger.warning(f"confidence_score invalide pour {chunk_id}")
                return False

            if not isinstance(obj.get("word_count", 0), int):
                self.logger.warning(f"word_count invalide pour {chunk_id}")
                return False

            # Vérification listes (gardées)
            for list_field in [
                "age_applicability",
                "applicable_metrics",
                "actionable_recommendations",
                "followup_themes",
            ]:
                if list_field in obj and not isinstance(obj[list_field], list):
                    self.logger.warning(
                        f"{list_field} n'est pas une liste pour {chunk_id}"
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Erreur validation objet {chunk_id}: {e}")
            return False

    def _clean_object_for_weaviate(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Nettoie et formate un objet pour Weaviate"""
        cleaned = {}

        for key, value in obj.items():
            if value is None:
                # Remplacer None par des valeurs par défaut appropriées
                if key in [
                    "genetic_line",
                    "document_type",
                    "species",
                    "intent_category",
                ]:
                    cleaned[key] = "unknown"
                elif key in [
                    "age_applicability",
                    "applicable_metrics",
                    "actionable_recommendations",
                    "followup_themes",
                ]:
                    cleaned[key] = []
                elif key == "confidence_score":
                    cleaned[key] = 0.0
                elif key == "word_count":
                    cleaned[key] = 0
                else:
                    cleaned[key] = ""
            elif isinstance(value, list):
                # S'assurer que les listes contiennent des strings
                cleaned[key] = [str(item) for item in value if item is not None]
            else:
                cleaned[key] = value

        return cleaned

    async def _insert_with_retry(
        self, collection, objects_to_insert, results, max_retries=2
    ):
        """Insertion avec retry automatique et logging détaillé"""
        import asyncio

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = attempt * 1.5
                    self.logger.info(
                        f"Retry insertion #{attempt + 1} dans {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)

                response = collection.data.insert_many(objects_to_insert)

                # Traitement des résultats avec logging détaillé
                success_count = 0
                if hasattr(response, "uuids") and response.uuids:
                    success_count = len(response.uuids)
                    results["success"] = [
                        {"uuid": str(uuid)} for uuid in response.uuids
                    ]
                    self.logger.info(
                        f"Insertion réussie: {success_count} objets avec UUIDs"
                    )

                # Gestion des erreurs d'insertion
                if hasattr(response, "errors") and response.errors:
                    for error in response.errors:
                        self.logger.error(f"Erreur insertion Weaviate: {error}")
                        results["errors"].append(
                            {"error": str(error), "type": "weaviate_insertion_error"}
                        )
                        results["error_count"] += 1

                return success_count

            except Exception as e:
                error_msg = str(e)
                if attempt == max_retries:
                    self.logger.error(
                        f"Insertion échouée après {max_retries + 1} tentatives: {error_msg}"
                    )
                    results["errors"].append(
                        {
                            "error": f"Insertion finale échouée: {error_msg}",
                            "type": "final_insertion_failure",
                        }
                    )
                else:
                    self.logger.warning(f"Tentative {attempt + 1} échouée: {error_msg}")

        return 0

    async def validate_injection(self, chunk_ids: List[str]) -> Dict[str, Any]:
        """Valide que les chunks ont été correctement injectés avec métadonnées"""
        validation_results = {
            "validated_count": 0,
            "missing_count": 0,
            "metadata_issues_count": 0,
            "validation_success_rate": 0.0,
            "missing_chunks": [],
            "metadata_issues": [],
        }

        try:
            collection = self.client.collections.get(self.collection_name)

            for chunk_id in chunk_ids:
                try:
                    # Récupération avec métadonnées complètes
                    response = collection.query.fetch_objects(
                        where={
                            "path": ["chunk_id"],
                            "operator": "Equal",
                            "valueText": chunk_id,
                        },
                        limit=1,
                    )

                    if response.objects:
                        obj = response.objects[0]
                        properties = obj.properties

                        # Vérification métadonnées critiques
                        genetic_line = properties.get("genetic_line", "")
                        intent_category = properties.get("intent_category", "")

                        if genetic_line == "unknown" or intent_category == "general":
                            validation_results["metadata_issues_count"] += 1
                            validation_results["metadata_issues"].append(
                                {
                                    "chunk_id": chunk_id,
                                    "genetic_line": genetic_line,
                                    "intent_category": intent_category,
                                }
                            )
                        else:
                            validation_results["validated_count"] += 1
                    else:
                        validation_results["missing_count"] += 1
                        validation_results["missing_chunks"].append(chunk_id)

                except Exception as chunk_error:
                    self.logger.error(
                        f"Erreur validation chunk {chunk_id}: {chunk_error}"
                    )
                    validation_results["missing_count"] += 1
                    validation_results["missing_chunks"].append(chunk_id)

            total = len(chunk_ids)
            validation_results["validation_success_rate"] = (
                validation_results["validated_count"] / total if total > 0 else 0
            )

            self.logger.info(
                f"Validation injection: {validation_results['validated_count']}/{total} OK, "
                f"{validation_results['metadata_issues_count']} avec problèmes métadonnées"
            )

        except Exception as e:
            self.logger.error(f"Erreur validation injection globale: {e}")

        return validation_results

    def recreate_collection(self):
        """Supprime et recrée la collection avec le nouveau schéma"""
        try:
            if self.client.collections.exists(self.collection_name):
                self.logger.info(
                    f"Suppression collection existante {self.collection_name}"
                )
                self.client.collections.delete(self.collection_name)

            self.logger.info(f"Recréation collection {self.collection_name}")
            self._create_collection_v4()

        except Exception as e:
            self.logger.error(f"Erreur recréation collection: {e}")
            raise

    def close(self):
        """Ferme la connexion Weaviate"""
        if self.client:
            try:
                self.client.close()
                self.logger.info("Connexion Weaviate fermée")
            except Exception as e:
                self.logger.error(f"Erreur fermeture connexion: {e}")
