#!/usr/bin/env python3
"""
Extracteur de connaissances intelligent hybride - VERSION REFACTORISÉE
Architecture modulaire avec séparation des responsabilités
"""

import asyncio
import logging
import time
import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Imports externes avec gestion d'erreur
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Imports des modules spécialisés avec validation
try:
    from core.llm_client import LLMClient
    from core.document_analyzer import DocumentAnalyzer
    from core.content_segmenter import ContentSegmenter
    from core.knowledge_enricher import KnowledgeEnricher
    from core.intent_manager import IntentManager
    from core.models import KnowledgeChunk
    from core.file_validator import FileValidator
    from core.processing_cache import ProcessingCache
    from weaviate_integration.ingester import WeaviateIngester
    from weaviate_integration.validator import ContentValidator
    from utils.statistics import ExtractionStatistics
    from utils.cli_utils import (
        validate_cli_args,
        print_validation_report,
        print_final_report,
    )
except ImportError as e:
    print(f"ERREUR: Module manquant - {e}")
    print(
        "Vérifiez que tous les modules requis sont présents dans core/, weaviate_integration/ et utils/"
    )
    sys.exit(1)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration sécurisée
MAX_FILE_SIZE_MB = 100
BATCH_PAUSE_SECONDS = 2


# Chargement sécurisé des variables d'environnement
def load_environment_variables():
    """Charge les variables d'environnement de manière sécurisée"""
    if load_dotenv is None:
        logger.warning("python-dotenv non disponible")
        return

    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
        Path.cwd().parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Variables d'environnement chargées depuis: {env_path}")
            return

    logger.warning("Aucun fichier .env trouvé")


# Chargement des variables
load_environment_variables()


class IntelligentKnowledgeExtractor:
    """Extracteur de connaissances intelligent avec architecture modulaire"""

    def __init__(
        self,
        output_dir: str = "extracted_knowledge",
        llm_client: LLMClient = None,
        collection_name: str = "InteliaExpertKnowledge",
        auto_correct: bool = True,
        conformity_threshold: float = 0.95,
        cache_enabled: bool = True,
        force_reprocess: bool = False,
        max_file_size_mb: int = MAX_FILE_SIZE_MB,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self.auto_correct = auto_correct
        self.conformity_threshold = conformity_threshold
        self.force_reprocess = force_reprocess
        self.max_file_size_mb = max_file_size_mb

        # Modules spécialisés
        self.file_validator = FileValidator(max_file_size_mb)

        # Cache intelligent
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache = ProcessingCache(self.output_dir / "cache")
        else:
            self.cache = None

        # Configuration des composants
        self._setup_components(llm_client, collection_name)

        self.logger.info(
            f"Extracteur intelligent initialisé - LLM: {self.llm_client.provider}, "
            f"Cache: {'activé' if cache_enabled else 'désactivé'}, "
            f"Force: {force_reprocess}"
        )

    def _setup_components(self, llm_client: LLMClient, collection_name: str):
        """Configure tous les composants de l'extracteur"""
        # Client LLM
        if llm_client is None:
            try:
                self.llm_client = LLMClient(provider="mock")
            except Exception as e:
                self.logger.error(f"Impossible de créer le client LLM: {e}")
                raise
        else:
            self.llm_client = llm_client

        # Composants spécialisés
        try:
            self.intent_manager = IntentManager()
            self.document_analyzer = DocumentAnalyzer(self.llm_client)
            self.content_segmenter = ContentSegmenter()
            self.knowledge_enricher = KnowledgeEnricher(
                self.llm_client, self.intent_manager
            )
            self.weaviate_ingester = WeaviateIngester(collection_name)
            self.content_validator = ContentValidator(
                self.weaviate_ingester.client, collection_name
            )
            self.stats = ExtractionStatistics()
        except Exception as e:
            self.logger.error(f"Erreur initialisation composants: {e}")
            raise

    def discover_files_to_process(
        self, knowledge_dir: str, min_conformity: float = None, max_age_days: int = 30
    ) -> Dict[str, List[str]]:
        """Découvre et catégorise les fichiers à traiter"""
        knowledge_path = Path(knowledge_dir)
        if not knowledge_path.exists():
            return {"error": [f"Répertoire {knowledge_dir} non trouvé"]}

        json_files = list(knowledge_path.glob("*.json"))
        if not json_files:
            return {"error": ["Aucun fichier JSON trouvé"]}

        if min_conformity is None:
            min_conformity = self.conformity_threshold

        categories = {
            "new": [],
            "modified": [],
            "failed_retry": [],
            "low_conformity": [],
            "outdated": [],
            "partial_injection": [],
            "up_to_date": [],
            "force_reprocess": [],
        }

        for json_file in json_files:
            if self.force_reprocess:
                categories["force_reprocess"].append(str(json_file))
                continue

            if not self.cache_enabled:
                categories["new"].append(str(json_file))
                continue

            decision = self.cache.should_process_file(
                str(json_file), min_conformity, max_age_days
            )
            status = decision.get("status", "new")
            if status in categories:
                categories[status].append(str(json_file))
            else:
                categories["new"].append(str(json_file))

        return categories

    async def validate_files_before_processing(
        self, file_paths: List[str], interactive: bool = True
    ) -> Dict[str, Any]:
        """Valide tous les fichiers avant traitement"""
        self.logger.info("=== VALIDATION PRÉALABLE DES FICHIERS ===")

        validation_report = self.file_validator.validate_files_batch(file_paths)

        # Utilise le module CLI pour l'affichage et l'interaction
        validation_decision = print_validation_report(validation_report, interactive)

        if validation_decision["reason"] == "user_force_all":
            validation_decision["files_to_process"] = file_paths

        if validation_report["problematic_files"] and not interactive:
            self.logger.warning(
                f"Mode non-interactif: exclusion de {validation_report['invalid_files']} fichiers problématiques"
            )

        return validation_decision

    async def process_document(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, Any]:
        """Traite un document complet avec analyse avancée"""
        try:
            self.logger.info(f"Traitement: {Path(json_file).name}")

            # Chargement sécurisé du fichier
            try:
                # Valider le fichier mais ne pas stocker les données si pas utilisées
                self.file_validator.safe_json_load(json_file)
            except Exception as e:
                self.logger.error(f"Erreur chargement fichier: {e}")
                return self._error_result(f"Chargement impossible: {e}")

            # Analyse contexte document
            document_context = self.document_analyzer.analyze_document(
                json_file, txt_file
            )
            document_context.genetic_line = self.intent_manager.normalize_genetic_line(
                f"{document_context.genetic_line} {document_context.raw_analysis}"
            )

            # Segmentation sémantique
            segments = self.content_segmenter.create_semantic_segments(
                json_file, txt_file, document_context
            )

            if not segments:
                self.logger.warning(f"Aucun segment créé pour {json_file}")
                result = self._empty_result()
                if self.cache_enabled:
                    self.cache.record_processing_result(json_file, result)
                return result

            self.logger.info(f"Segments créés: {len(segments)}")

            # Enrichissement métadonnées
            knowledge_chunks = await self._create_knowledge_chunks(
                segments, document_context, json_file
            )

            # Filtrage qualité
            validated_chunks = self._quality_filter(knowledge_chunks)

            # Injection Weaviate
            injection_results = await self.weaviate_ingester.ingest_batch(
                validated_chunks
            )

            # Attente indexation
            if injection_results["success_count"] > 0:
                wait_time = min(40, max(20, injection_results["success_count"] * 0.8))
                self.logger.info(f"Attente indexation: {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Validation avec retry
            validation_results = await self._validate_with_retry(
                validated_chunks, json_file, max_retries=2
            )

            # Sauvegarde rapport
            report_path = self._save_report(
                json_file,
                document_context,
                segments,
                injection_results,
                validation_results,
            )

            # Mise à jour statistiques
            self._update_statistics(segments, injection_results, validation_results)

            result = self._build_result(
                json_file,
                segments,
                validated_chunks,
                injection_results,
                validation_results,
                report_path,
            )

            if self.cache_enabled:
                self.cache.record_processing_result(json_file, result)

            self.logger.info(
                f"Traitement terminé: {result['injection_success']}/{result['segments_created']} chunks - "
                f"Conformité: {result['final_conformity_score']:.1%}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Erreur traitement document: {e}")
            self.stats.increment_errors()
            error_result = self._error_result(str(e))
            if self.cache_enabled:
                self.cache.record_processing_result(json_file, error_result)
            return error_result

    async def process_batch_intelligent_with_validation(
        self,
        knowledge_dir: str,
        min_conformity: float = None,
        max_age_days: int = 30,
        batch_size: int = 5,
        interactive: bool = True,
    ) -> Dict[str, Any]:
        """Traitement intelligent par batch avec validation préalable"""
        if min_conformity is None:
            min_conformity = self.conformity_threshold

        # Découverte des fichiers
        categories = self.discover_files_to_process(
            knowledge_dir, min_conformity, max_age_days
        )

        if "error" in categories:
            return {"error": categories["error"]}

        # Compilation des fichiers à traiter
        priority_order = [
            "failed_retry",
            "modified",
            "low_conformity",
            "partial_injection",
            "new",
            "outdated",
            "force_reprocess",
        ]
        files_to_process = []
        processing_reasons = {}

        for priority in priority_order:
            for file_path in categories.get(priority, []):
                files_to_process.append(file_path)
                processing_reasons[file_path] = priority

        up_to_date_count = len(categories.get("up_to_date", []))

        if not files_to_process:
            return {"status": "no_processing_needed", "up_to_date": up_to_date_count}

        # Validation préalable
        validation_decision = await self.validate_files_before_processing(
            files_to_process, interactive
        )

        if not validation_decision["proceed"]:
            return {
                "status": "stopped_by_validation",
                "reason": validation_decision["reason"],
                "validation_report": validation_decision["validation_report"],
            }

        approved_files = validation_decision["files_to_process"]

        if not approved_files:
            return {
                "status": "no_valid_files",
                "validation_report": validation_decision["validation_report"],
            }

        # Traitement par batch
        results = await self._process_files_batch(
            approved_files, processing_reasons, batch_size, up_to_date_count
        )

        results["validation_report"] = validation_decision["validation_report"]

        if self.cache_enabled:
            results["cache_stats"] = self.cache.get_cache_stats()

        return results

    async def _process_files_batch(
        self,
        files: List[str],
        processing_reasons: Dict[str, str],
        batch_size: int,
        up_to_date_count: int,
    ) -> Dict[str, Any]:
        """Traite un batch de fichiers"""
        results = {
            "processed": [],
            "skipped": up_to_date_count,
            "errors": [],
            "summary": {},
        }

        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]

            self.logger.info(
                f"\nBatch {i//batch_size + 1}/{(len(files)-1)//batch_size + 1}: {len(batch)} fichiers"
            )

            for j, file_path in enumerate(batch):
                reason = processing_reasons.get(file_path, "unknown")
                self.logger.info(
                    f"  [{j+1}/{len(batch)}] {Path(file_path).name} (raison: {reason})"
                )

                try:
                    result = await self.process_document(file_path)
                    result["processing_reason"] = reason
                    results["processed"].append(result)
                    await asyncio.sleep(1)

                except Exception as e:
                    error_info = {
                        "file": file_path,
                        "error": str(e),
                        "processing_reason": reason,
                    }
                    results["errors"].append(error_info)
                    self.logger.error(f"Erreur: {e}")

            # Pause entre batches
            if i + batch_size < len(files):
                await asyncio.sleep(BATCH_PAUSE_SECONDS)

        # Compilation des résultats
        successful = len(
            [r for r in results["processed"] if r.get("injection_success", 0) > 0]
        )

        results["summary"] = {
            "files_processed": len(results["processed"]),
            "files_successful": successful,
            "files_failed": len(results["errors"]),
            "files_skipped": up_to_date_count,
            "files_excluded_by_validation": 0,  # Sera mis à jour par l'appelant
            "success_rate": successful / len(files) if files else 0,
            "validation_applied": True,
        }

        return results

    def cleanup_cache_if_needed(self):
        """Nettoie le cache des fichiers inexistants"""
        if not self.cache_enabled:
            return

        removed_count = self.cache.cleanup_missing_files()

        if removed_count > 0:
            self.logger.info(
                f"Cache nettoyé: {removed_count} fichiers obsolètes supprimés"
            )

    def close(self):
        """Ferme proprement toutes les connexions"""
        try:
            if hasattr(self, "weaviate_ingester") and self.weaviate_ingester:
                if hasattr(self.weaviate_ingester, "close"):
                    self.weaviate_ingester.close()
                elif (
                    hasattr(self.weaviate_ingester, "client")
                    and self.weaviate_ingester.client
                ):
                    self.weaviate_ingester.client.close()
                self.logger.info("Connexion Weaviate fermée")

            if hasattr(self, "llm_client") and self.llm_client:
                if hasattr(self.llm_client, "close"):
                    self.llm_client.close()

            self.logger.info("Extracteur fermé proprement")

        except Exception as e:
            self.logger.error(f"Erreur fermeture extracteur: {e}")

    # Méthodes utilitaires
    async def _create_knowledge_chunks(self, segments, document_context, json_file):
        """Crée les chunks de connaissance avec enrichissement"""
        knowledge_chunks = []
        timestamp = datetime.now().isoformat()

        for i, segment in enumerate(segments):
            try:
                metadata = self.knowledge_enricher.enrich_chunk(
                    segment, document_context
                )
                chunk_id = self._generate_chunk_id(json_file, i, segment)

                chunk = KnowledgeChunk(
                    chunk_id=chunk_id,
                    content=segment["content"],
                    word_count=segment.get(
                        "word_count", len(segment["content"].split())
                    ),
                    document_context=document_context,
                    metadata=metadata,
                    source_file=json_file,
                    extraction_timestamp=timestamp,
                )
                knowledge_chunks.append(chunk)

            except Exception as e:
                self.logger.error(f"Erreur enrichissement segment {i}: {e}")
                continue

        return knowledge_chunks

    def _quality_filter(self, knowledge_chunks):
        """Filtre qualité avec critères assouplis"""
        validated = []
        for chunk in knowledge_chunks:
            if self._meets_quality_criteria(chunk) and not self._is_duplicate_content(
                chunk, validated
            ):
                validated.append(chunk)

        self.logger.info(
            f"Filtrage: {len(validated)}/{len(knowledge_chunks)} chunks validés"
        )
        return validated

    def _meets_quality_criteria(self, chunk):
        """Critères de qualité assouplis"""
        return (
            20 <= chunk.word_count <= 3000
            and chunk.metadata.confidence_score >= 0.2
            and chunk.content
            and len(chunk.content.strip()) >= 50
        )

    def _is_duplicate_content(self, chunk, existing_chunks):
        """Détection de contenu dupliqué"""
        chunk_words = set(chunk.content.lower().split())
        for existing in existing_chunks:
            existing_words = set(existing.content.lower().split())
            intersection = len(chunk_words & existing_words)
            union = len(chunk_words | existing_words)
            similarity = intersection / union if union > 0 else 0
            if similarity > 0.8:
                return True
        return False

    def _generate_chunk_id(self, json_file, index, segment):
        """Génère un ID unique pour un chunk"""
        filename = Path(json_file).stem
        content_hash = hashlib.md5(segment["content"].encode()).hexdigest()[:8]
        return f"{filename}_{index:03d}_{content_hash}"

    async def _validate_with_retry(self, chunks, source_file, max_retries=2):
        """Validation avec retry automatique"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (attempt * 4) + 2.0
                    await asyncio.sleep(wait_time)

                validation_results = (
                    await self.content_validator.comprehensive_validation(
                        chunks, source_file
                    )
                )
                chunk_coverage_ratio = validation_results.get("chunk_coverage_ratio", 0)

                if chunk_coverage_ratio >= 0.90:
                    return validation_results

                if attempt == max_retries - 1:
                    validation_results["partial_success"] = True
                    return validation_results

            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        "conformity_score": 0.0,
                        "error": str(e),
                        "chunk_coverage_ratio": 0.0,
                    }

    def _update_statistics(self, segments, injection_results, validation_results):
        """Met à jour les statistiques"""
        self.stats.increment_documents()
        self.stats.add_chunks_created(len(segments))
        self.stats.add_chunks_injected(injection_results["success_count"])

    def _save_report(
        self,
        json_file,
        document_context,
        segments,
        injection_results,
        validation_results,
    ):
        """Sauvegarde rapport détaillé"""
        report_filename = f"report_{Path(json_file).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.output_dir / report_filename

        report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": json_file,
            "document_context": {
                "genetic_line": document_context.genetic_line,
                "document_type": document_context.document_type,
                "species": document_context.species,
                "confidence_score": document_context.confidence_score,
            },
            "segments_created": len(segments),
            "injection_results": injection_results,
            "validation_results": validation_results,
            "optimizations_applied": {
                "advanced_llm_analysis": True,
                "intent_based_enrichment": True,
                "genetic_line_normalization": True,
                "paginated_validation": True,
                "quality_filtering_enhanced": True,
                "intelligent_caching": True,
                "security_validation": True,
                "memory_management": True,
            },
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(report_path)

    def _build_result(
        self,
        json_file,
        segments,
        chunks,
        injection_results,
        validation_results,
        report_path,
    ):
        """Construit le résultat final"""
        return {
            "document": Path(json_file).name,
            "segments_created": len(segments),
            "chunks_validated": len(chunks),
            "injection_success": injection_results["success_count"],
            "injection_errors": injection_results["error_count"],
            "final_conformity_score": validation_results.get("conformity_score", 0.0),
            "chunk_coverage_ratio": validation_results.get("chunk_coverage_ratio", 0.0),
            "partial_success": validation_results.get("partial_success", False),
            "report_path": report_path,
        }

    def _empty_result(self):
        """Résultat vide"""
        return {
            "document": "",
            "segments_created": 0,
            "chunks_validated": 0,
            "injection_success": 0,
            "injection_errors": 0,
            "final_conformity_score": 0.0,
            "chunk_coverage_ratio": 0.0,
            "partial_success": False,
            "report_path": "",
        }

    def _error_result(self, error_msg):
        """Résultat d'erreur"""
        return {
            "document": "",
            "error": error_msg,
            "segments_created": 0,
            "chunks_validated": 0,
            "injection_success": 0,
            "injection_errors": 1,
            "final_conformity_score": 0.0,
            "chunk_coverage_ratio": 0.0,
            "partial_success": False,
            "report_path": "",
        }

    def get_extraction_statistics(self):
        """Retourne les statistiques détaillées"""
        stats = self.stats.get_detailed_stats()
        if self.cache_enabled:
            stats["cache"] = self.cache.get_cache_stats()
        return stats


# =============================================================================
# FONCTIONS PRINCIPALES
# =============================================================================


async def process_single_file(file_path: str):
    """Traite un seul fichier spécifique pour les tests"""
    print("=== TRAITEMENT FICHIER UNIQUE - VERSION MODULAIRE ===")
    print(f"Fichier: {Path(file_path).name}")

    # Validation préalable
    validator = FileValidator()
    validation = validator.validate_json_file(file_path)

    print("\nValidation préalable:")
    print(f"  - Fichier valide: {validation['valid']}")
    print(f"  - Taille: {validation['size_mb']:.1f}MB")
    print(f"  - Chunks détectés: {validation['chunks_count']}")

    if validation["issues"]:
        print(f"  - Problèmes détectés: {', '.join(validation['issues'])}")
        if not validation["valid"]:
            response = input(
                "Fichier problématique détecté. Continuer quand même? (y/N): "
            )
            if response.lower() != "y":
                print("Traitement annulé")
                return

    try:
        llm_client = LLMClient.create_auto(provider="openai", model="gpt-4")
        print("LLM configuré: openai/gpt-4")
    except Exception as e:
        print(f"Erreur configuration LLM: {e}")
        return

    extractor = IntelligentKnowledgeExtractor(
        llm_client=llm_client,
        conformity_threshold=0.95,
        output_dir="single_file_test_modular",
        cache_enabled=False,
        force_reprocess=True,
        max_file_size_mb=MAX_FILE_SIZE_MB,
    )

    try:
        start_time = time.time()
        result = await extractor.process_document(file_path)
        duration = time.time() - start_time

        print("\n=== RÉSULTATS ===")
        print(f"Durée: {duration:.1f}s")
        print(f"Segments créés: {result['segments_created']}")
        print(f"Chunks injectés: {result['injection_success']}")
        print(f"Erreurs: {result['injection_errors']}")
        print(f"Conformité: {result['final_conformity_score']:.1%}")
        print(f"Couverture chunks: {result.get('chunk_coverage_ratio', 0):.1%}")
        print(f"Rapport: {result['report_path']}")

        return result

    except Exception as e:
        print(f"Erreur traitement: {e}")
    finally:
        extractor.close()


async def main():
    """Extraction intelligente avec architecture modulaire"""

    # Vérifier si un fichier spécifique est demandé
    single_file_path = validate_cli_args()
    if single_file_path:
        await process_single_file(single_file_path)
        return

    print("=== EXTRACTION INTELLIGENTE MODULAIRE ===")

    # Configuration
    knowledge_dir = Path("C:/intelia_gpt/intelia-expert/rag/documents/Knowledge")
    if not knowledge_dir.exists():
        print(f"Erreur: Répertoire {knowledge_dir} non trouvé")
        return

    # Options de traitement
    force_reprocess = "--force" in sys.argv
    disable_cache = "--no-cache" in sys.argv
    non_interactive = "--non-interactive" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    min_conformity = 0.95
    max_age_days = 30
    batch_size = 5

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("Configuration:")
    print(f"  - Répertoire: {knowledge_dir}")
    print(f"  - Seuil conformité: {min_conformity:.1%}")
    print(f"  - Cache activé: {not disable_cache}")
    print(f"  - Mode interactif: {not non_interactive}")
    print("  - Architecture: Modulaire")

    # Configuration LLM
    try:
        llm_client = LLMClient.create_auto(provider="openai", model="gpt-4")
        print("LLM configuré: openai/gpt-4")
    except Exception as e:
        print(f"Erreur configuration LLM: {e}")
        return

    # Instance modulaire
    extractor = IntelligentKnowledgeExtractor(
        llm_client=llm_client,
        conformity_threshold=min_conformity,
        output_dir="intelligent_results_modular",
        cache_enabled=not disable_cache,
        force_reprocess=force_reprocess,
        max_file_size_mb=MAX_FILE_SIZE_MB,
    )

    # Affichage cache
    if not disable_cache:
        cache_stats = extractor.cache.get_cache_stats()
        print(
            f"\nÉtat cache: {cache_stats.get('total_files', 0)} fichiers, "
            f"{cache_stats.get('success_rate', 0):.1%} succès"
        )

    try:
        extractor.cleanup_cache_if_needed()

        # Traitement principal
        results = await extractor.process_batch_intelligent_with_validation(
            str(knowledge_dir),
            min_conformity=min_conformity,
            max_age_days=max_age_days,
            batch_size=batch_size,
            interactive=not non_interactive,
        )

        # Affichage des résultats avec le module CLI
        print_final_report(results)

    except Exception as e:
        print(f"Erreur fatale: {e}")
        import traceback

        traceback.print_exc()

    finally:
        extractor.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur")
    except Exception as e:
        print(f"ERREUR FATALE: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
