#!/usr/bin/env python3
"""
Extracteur de connaissances intelligent hybride - VERSION CORRIGEE
Avec validation préalable des fichiers pour détecter les problèmes avant traitement
"""

import asyncio
import logging
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Imports externes
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Imports des modules spécialisés optimisés
from core.llm_client import LLMClient
from core.document_analyzer import DocumentAnalyzer
from core.content_segmenter import ContentSegmenter
from core.knowledge_enricher import KnowledgeEnricher
from core.intent_manager import IntentManager
from core.models import KnowledgeChunk
from weaviate_integration.ingester import WeaviateIngester
from weaviate_integration.validator import ContentValidator
from utils.statistics import ExtractionStatistics

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
if load_dotenv is not None:
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
        Path.cwd().parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Variables d'environnement chargées depuis: {env_path}")
            break
else:
    logger.warning("python-dotenv non disponible")


class FileValidator:
    """Validateur de fichiers JSON avant traitement"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.FileValidator")

    def validate_json_file(self, file_path: str) -> Dict[str, Any]:
        """Valide un fichier JSON et diagnostique les problèmes"""

        result = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "valid": False,
            "exists": False,
            "readable": False,
            "valid_json": False,
            "empty": False,
            "size_bytes": 0,
            "issues": [],
            "content_preview": "",
            "structure": {},
            "chunks_count": 0,
            "debug_info": {},
        }

        try:
            # 1. Vérifier l'existence du fichier
            path = Path(file_path)
            if not path.exists():
                result["issues"].append("FILE_NOT_FOUND")
                return result

            result["exists"] = True
            result["size_bytes"] = path.stat().st_size

            # 2. Vérifier si le fichier est vide
            if result["size_bytes"] == 0:
                result["empty"] = True
                result["issues"].append("EMPTY_FILE")
                return result

            # 3. Tenter de lire le fichier
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                result["readable"] = True
                result["content_preview"] = (
                    content[:200] + "..." if len(content) > 200 else content
                )

            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        content = f.read()
                    result["readable"] = True
                    result["issues"].append("ENCODING_ISSUE")
                    result["content_preview"] = (
                        content[:200] + "..." if len(content) > 200 else content
                    )
                except Exception as e:
                    result["issues"].append(f"READ_ERROR: {e}")
                    return result
            except Exception as e:
                result["issues"].append(f"READ_ERROR: {e}")
                return result

            # 4. Vérifier si le contenu est vide après nettoyage
            if not content.strip():
                result["empty"] = True
                result["issues"].append("EMPTY_CONTENT")
                return result

            # 5. Tenter de parser le JSON
            try:
                data = json.loads(content)
                result["valid_json"] = True

                # DEBUG: Afficher la structure racine
                result["debug_info"]["root_type"] = type(data).__name__

                # Analyser la structure
                if isinstance(data, dict):
                    result["structure"] = {
                        "type": "object",
                        "keys": list(data.keys())[:10],
                        "total_keys": len(data.keys()) if hasattr(data, "keys") else 0,
                    }

                    # DEBUG: Afficher toutes les clés principales
                    result["debug_info"]["all_keys"] = list(data.keys())

                    # Vérifier la présence de chunks avec différentes clés possibles
                    chunk_keys = ["chunks", "segments", "content", "data", "extracts"]
                    chunks_found = None
                    chunks_key_used = None

                    for key in chunk_keys:
                        if key in data:
                            chunks_found = data[key]
                            chunks_key_used = key
                            break

                    if chunks_found is not None:
                        result["debug_info"]["chunks_key_used"] = chunks_key_used

                        if isinstance(chunks_found, list):
                            result["chunks_count"] = len(chunks_found)
                            result["debug_info"]["chunks_list_length"] = len(
                                chunks_found
                            )

                            if len(chunks_found) == 0:
                                result["issues"].append("NO_CHUNKS")
                            else:
                                # Examiner la structure des premiers chunks
                                sample_size = min(3, len(chunks_found))
                                valid_chunks = 0
                                chunk_structures = []

                                for i, chunk in enumerate(chunks_found[:sample_size]):
                                    chunk_info = {
                                        "index": i,
                                        "type": type(chunk).__name__,
                                        "keys": (
                                            list(chunk.keys())
                                            if isinstance(chunk, dict)
                                            else None
                                        ),
                                        "has_content": False,
                                        "content_key": None,
                                    }

                                    if isinstance(chunk, dict):
                                        # Chercher toutes les clés possibles pour le contenu
                                        content_keys = [
                                            "content",
                                            "text",
                                            "body",
                                            "chunk_content",
                                            "segment_content",
                                            "data",
                                        ]

                                        for content_key in content_keys:
                                            if content_key in chunk:
                                                content_value = chunk[content_key]
                                                if (
                                                    content_value
                                                    and str(content_value).strip()
                                                ):
                                                    chunk_info["has_content"] = True
                                                    chunk_info["content_key"] = (
                                                        content_key
                                                    )
                                                    valid_chunks += 1
                                                    break
                                    elif isinstance(chunk, str):
                                        # CORRECTION: Gérer les chunks qui sont directement des strings
                                        if chunk and chunk.strip():
                                            chunk_info["has_content"] = True
                                            chunk_info["content_key"] = "direct_string"
                                            valid_chunks += 1

                                    chunk_structures.append(chunk_info)

                                result["debug_info"][
                                    "chunk_structures"
                                ] = chunk_structures
                                result["debug_info"][
                                    "valid_chunks_found"
                                ] = valid_chunks

                                # Validation finale
                                if valid_chunks == 0:
                                    result["issues"].append("INVALID_CHUNKS")
                                elif valid_chunks < sample_size * 0.5:
                                    result["issues"].append("SOME_INVALID_CHUNKS")
                        else:
                            result["issues"].append("CHUNKS_NOT_LIST")
                            result["debug_info"]["chunks_type"] = type(
                                chunks_found
                            ).__name__
                    else:
                        result["issues"].append("NO_CHUNKS_KEY")
                        result["debug_info"]["available_keys"] = list(data.keys())[:10]

                elif isinstance(data, list):
                    result["structure"] = {"type": "array", "length": len(data)}
                    result["chunks_count"] = len(data)
                    result["debug_info"]["direct_array"] = True

                    # Si c'est directement un array, traiter comme des chunks
                    if len(data) > 0:
                        sample_chunk = data[0]
                        if isinstance(sample_chunk, dict):
                            result["debug_info"]["first_chunk_keys"] = list(
                                sample_chunk.keys()
                            )
                else:
                    result["structure"] = {"type": type(data).__name__}
                    result["issues"].append("UNEXPECTED_ROOT_TYPE")

                # Déterminer si le fichier est valide (plus permissif maintenant)
                critical_issues = [
                    "FILE_NOT_FOUND",
                    "EMPTY_FILE",
                    "READ_ERROR",
                    "EMPTY_CONTENT",
                    "NO_CHUNKS",
                    "INVALID_CHUNKS",
                ]

                has_critical_issues = any(
                    any(critical in issue for critical in critical_issues)
                    for issue in result["issues"]
                )

                result["valid"] = not has_critical_issues

            except json.JSONDecodeError as e:
                result["issues"].append(f"INVALID_JSON: {e}")
                if "line 1 column 1" in str(e):
                    result["issues"].append("POSSIBLY_EMPTY_RESPONSE")

        except Exception as e:
            result["issues"].append(f"VALIDATION_ERROR: {e}")

        return result

    def validate_files_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Valide un batch de fichiers et retourne un rapport consolidé"""

        results = {
            "total_files": len(file_paths),
            "valid_files": 0,
            "invalid_files": 0,
            "total_chunks": 0,
            "problematic_files": [],
            "valid_files_list": [],
            "file_details": {},
        }

        self.logger.info(f"Validation de {len(file_paths)} fichiers...")

        for file_path in file_paths:
            validation = self.validate_json_file(file_path)
            file_name = Path(file_path).name

            results["file_details"][file_name] = validation

            if validation["valid"]:
                results["valid_files"] += 1
                results["valid_files_list"].append(file_path)
                results["total_chunks"] += validation["chunks_count"]
            else:
                results["invalid_files"] += 1
                results["problematic_files"].append(
                    {
                        "file": file_name,
                        "path": file_path,
                        "issues": validation["issues"],
                        "size_bytes": validation["size_bytes"],
                    }
                )

        return results


class ProcessingCache:
    """Gestionnaire de cache pour éviter les retraitements inutiles"""

    def __init__(self, cache_dir: str = "processing_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "processing_cache.json"
        self.reports_dir = self.cache_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.ProcessingCache")
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict:
        """Charge le cache existant"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.logger.info(
                        f"Cache chargé: {len(cache_data.get('processed_files', {}))} fichiers"
                    )
                    return cache_data
            except Exception as e:
                self.logger.warning(f"Erreur chargement cache: {e}")
        else:
            self.logger.info("Nouveau cache créé")

        return {
            "processed_files": {},
            "last_update": datetime.now().isoformat(),
            "version": "1.0",
        }

    def _save_cache(self):
        """Sauvegarde le cache"""
        try:
            self.cache_data["last_update"] = datetime.now().isoformat()
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Cache sauvegardé: {self.cache_file}")
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache: {e}")

    def get_file_hash(self, file_path: str) -> str:
        """Calcule le hash d'un fichier pour détecter les modifications"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""

    def should_process_file(
        self, file_path: str, min_conformity: float = 0.95, max_age_days: int = 30
    ) -> Dict[str, Any]:
        """Détermine si un fichier doit être traité"""
        file_key = str(Path(file_path).resolve())
        current_hash = self.get_file_hash(file_path)

        # Fichier jamais traité
        if file_key not in self.cache_data["processed_files"]:
            return {
                "should_process": True,
                "reason": "Fichier jamais traité",
                "status": "new",
            }

        file_info = self.cache_data["processed_files"][file_key]

        # Fichier modifié
        if file_info.get("file_hash") != current_hash:
            return {
                "should_process": True,
                "reason": "Fichier modifié",
                "status": "modified",
            }

        # Échec précédent
        if not file_info.get("success", False):
            return {
                "should_process": True,
                "reason": "Échec précédent",
                "status": "failed_retry",
            }

        # Conformité insuffisante
        conformity = file_info.get("final_conformity_score", 0.0)
        if conformity < min_conformity:
            return {
                "should_process": True,
                "reason": f"Conformité insuffisante: {conformity:.1%}",
                "status": "low_conformity",
            }

        # Traitement trop ancien
        last_processed = file_info.get("last_processed")
        if last_processed:
            try:
                last_date = datetime.fromisoformat(
                    last_processed.replace("Z", "+00:00")
                )
                age_days = (datetime.now() - last_date.replace(tzinfo=None)).days
                if age_days > max_age_days:
                    return {
                        "should_process": True,
                        "reason": f"Traitement ancien: {age_days} jours",
                        "status": "outdated",
                    }
            except Exception:
                pass

        return {
            "should_process": False,
            "reason": f"Fichier OK (conformité: {conformity:.1%})",
            "status": "up_to_date",
        }

    def record_processing_result(self, file_path: str, result: Dict[str, Any]):
        """Enregistre le résultat d'un traitement"""
        file_key = str(Path(file_path).resolve())
        file_hash = self.get_file_hash(file_path)

        processing_record = {
            "file_hash": file_hash,
            "last_processed": datetime.now().isoformat(),
            "success": result.get("injection_success", 0) > 0,
            "segments_created": result.get("segments_created", 0),
            "injection_success": result.get("injection_success", 0),
            "injection_errors": result.get("injection_errors", 0),
            "final_conformity_score": result.get("final_conformity_score", 0.0),
            "partial_success": result.get("partial_success", False),
            "report_path": result.get("report_path", ""),
            "error": result.get("error"),
        }

        self.cache_data["processed_files"][file_key] = processing_record
        self._save_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        processed = self.cache_data["processed_files"]
        if not processed:
            return {"total_files": 0}

        successful = sum(1 for info in processed.values() if info.get("success"))
        return {
            "total_files": len(processed),
            "successful": successful,
            "failed": len(processed) - successful,
            "success_rate": successful / len(processed) if processed else 0,
        }


class IntelligentKnowledgeExtractor:
    """Extracteur de connaissances intelligent avec cache et traitement sélectif - VERSION CORRIGEE"""

    def __init__(
        self,
        output_dir: str = "extracted_knowledge",
        llm_client: LLMClient = None,
        collection_name: str = "InteliaExpertKnowledge",
        auto_correct: bool = True,
        conformity_threshold: float = 0.95,
        cache_enabled: bool = True,
        force_reprocess: bool = False,
    ):

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self.auto_correct = auto_correct
        self.conformity_threshold = conformity_threshold
        self.force_reprocess = force_reprocess

        # Validateur de fichiers
        self.file_validator = FileValidator()

        # Cache intelligent
        self.cache_enabled = cache_enabled
        if cache_enabled:
            self.cache = ProcessingCache(self.output_dir / "cache")
        else:
            self.cache = None

        # Client LLM optimisé
        if llm_client is None:
            self.llm_client = LLMClient(provider="mock")
        else:
            self.llm_client = llm_client

        # Composants spécialisés optimisés - VERSIONS CORRIGEES
        self.intent_manager = IntentManager()
        self.document_analyzer = DocumentAnalyzer(self.llm_client)
        self.content_segmenter = (
            ContentSegmenter()
        )  # VERSION CORRIGEE avec limites étendues
        self.knowledge_enricher = KnowledgeEnricher(
            self.llm_client, self.intent_manager
        )
        self.weaviate_ingester = WeaviateIngester(collection_name)
        self.content_validator = (
            ContentValidator(  # VERSION CORRIGEE avec filtrage par source_file
                self.weaviate_ingester.client, collection_name
            )
        )

        # Statistiques avancées
        self.stats = ExtractionStatistics()

        self.logger.info(
            f"Extracteur intelligent initialisé - LLM: {self.llm_client.provider}, "
            f"Cache: {'activé' if cache_enabled else 'désactivé'}, "
            f"Force: {force_reprocess} - VERSION CORRIGEE avec validation préalable"
        )

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
        """NOUVELLE MÉTHODE: Valide tous les fichiers avant traitement"""

        self.logger.info("=== VALIDATION PRÉALABLE DES FICHIERS ===")

        validation_report = self.file_validator.validate_files_batch(file_paths)

        print("\nRapport de validation:")
        print(f"  - Total fichiers: {validation_report['total_files']}")
        print(f"  - Fichiers valides: {validation_report['valid_files']}")
        print(f"  - Fichiers problématiques: {validation_report['invalid_files']}")
        print(f"  - Chunks totaux détectés: {validation_report['total_chunks']}")

        # Afficher les fichiers problématiques
        if validation_report["problematic_files"]:
            print("\n⚠️  FICHIERS PROBLÉMATIQUES DÉTECTÉS:")
            for i, problematic in enumerate(validation_report["problematic_files"]):
                print(f"  ❌ {problematic['file']}:")
                for issue in problematic["issues"]:
                    print(f"    - {issue}")
                    if "POSSIBLY_EMPTY_RESPONSE" in issue:
                        print(
                            "    💡 Suggestion: Ce fichier semble avoir une réponse vide de l'API LLM"
                        )
                print(f"    📊 Taille: {problematic['size_bytes']} bytes")

                # NOUVEAU: Afficher debug pour les premiers fichiers si tous sont problématiques
                if (
                    validation_report["invalid_files"]
                    == validation_report["total_files"]
                    and i < 3
                ):
                    file_details = validation_report["file_details"].get(
                        problematic["file"], {}
                    )
                    debug_info = file_details.get("debug_info", {})
                    if debug_info:
                        print(
                            f"    🔍 Debug - Type racine: {debug_info.get('root_type', 'N/A')}"
                        )
                        print(
                            f"    🔍 Debug - Clés disponibles: {debug_info.get('all_keys', 'N/A')}"
                        )
                        print(
                            f"    🔍 Debug - Clé chunks utilisée: {debug_info.get('chunks_key_used', 'N/A')}"
                        )
                        if "chunk_structures" in debug_info:
                            print(
                                f"    🔍 Debug - Structure chunks: {debug_info['chunk_structures']}"
                            )

        # NOUVEAU: Message spécial si TOUS les fichiers sont problématiques
        if (
            validation_report["invalid_files"] == validation_report["total_files"]
            and validation_report["total_files"] > 10
        ):
            print(
                "\n🚨 ANOMALIE DÉTECTÉE: 100% des fichiers sont marqués problématiques!"
            )
            print("   Cela suggère un problème avec la logique de validation.")
            print("   Examinant la structure des premiers fichiers pour diagnostic...")

            for file_name, details in list(validation_report["file_details"].items())[
                :2
            ]:
                print(f"\n📋 Diagnostic détaillé - {file_name}:")
                debug_info = details.get("debug_info", {})
                for key, value in debug_info.items():
                    print(f"    {key}: {value}")

        # Demander confirmation si mode interactif et fichiers problématiques
        if interactive and validation_report["problematic_files"]:
            print("\n🤔 Que souhaitez-vous faire?")
            print("\n🤔 Que souhaitez-vous faire?")
            print(
                f"  1. Continuer avec les fichiers valides seulement ({validation_report['valid_files']} fichiers)"
            )
            print("  2. Arrêter et corriger les fichiers problématiques d'abord")
            print("  3. Continuer avec TOUS les fichiers (risqué)")

            try:
                choice = input("Votre choix (1/2/3): ").strip()

                if choice == "2":
                    print(
                        "🛑 Traitement arrêté. Corrigez les fichiers problématiques et relancez."
                    )
                    return {
                        "proceed": False,
                        "reason": "user_requested_stop",
                        "files_to_process": [],
                        "validation_report": validation_report,
                    }
                elif choice == "3":
                    print(
                        "⚠️  Continuer avec TOUS les fichiers (y compris problématiques)"
                    )
                    return {
                        "proceed": True,
                        "reason": "user_force_all",
                        "files_to_process": file_paths,
                        "validation_report": validation_report,
                    }
                else:  # Choix 1 ou par défaut
                    print(
                        f"✅ Continuer avec {validation_report['valid_files']} fichiers valides"
                    )
                    return {
                        "proceed": True,
                        "reason": "valid_files_only",
                        "files_to_process": validation_report["valid_files_list"],
                        "validation_report": validation_report,
                    }

            except KeyboardInterrupt:
                print("\n🛑 Traitement interrompu par l'utilisateur")
                return {
                    "proceed": False,
                    "reason": "user_interrupt",
                    "files_to_process": [],
                    "validation_report": validation_report,
                }

        # Mode non-interactif: continuer avec fichiers valides seulement
        if validation_report["problematic_files"]:
            self.logger.warning(
                f"Mode non-interactif: exclusion de {validation_report['invalid_files']} fichiers problématiques"
            )

        return {
            "proceed": True,
            "reason": "auto_valid_only",
            "files_to_process": validation_report["valid_files_list"],
            "validation_report": validation_report,
        }

    async def process_document(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, Any]:
        """Traite un document complet avec analyse avancée"""
        try:
            self.logger.info(f"Traitement CORRIGE: {Path(json_file).name}")

            # Analyse contexte document avec LLM spécialisé (avec retry intégré)
            document_context = self.document_analyzer.analyze_document(
                json_file, txt_file
            )
            document_context.genetic_line = self.intent_manager.normalize_genetic_line(
                f"{document_context.genetic_line} {document_context.raw_analysis}"
            )

            # Segmentation sémantique avancée
            segments = self.content_segmenter.create_semantic_segments(
                json_file, txt_file, document_context
            )

            if not segments:
                self.logger.warning(f"Aucun segment créé pour {json_file}")
                result = self._empty_result()
                if self.cache_enabled:
                    self.cache.record_processing_result(json_file, result)
                return result

            self.logger.info(f"Segments créés: {len(segments)} (VERSION CORRIGEE)")

            # Enrichissement métadonnées avec analyse LLM + intents
            knowledge_chunks = await self._create_knowledge_chunks(
                segments, document_context, json_file
            )

            # Filtrage qualité avancé
            validated_chunks = self._quality_filter_corrected(knowledge_chunks)

            # Injection Weaviate avec métadonnées enrichies
            injection_results = await self.weaviate_ingester.ingest_batch(
                validated_chunks
            )

            # Attente indexation adaptative
            if injection_results["success_count"] > 0:
                wait_time = min(40, max(20, injection_results["success_count"] * 0.8))
                self.logger.info(f"⏳ Attente indexation: {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Validation CORRIGEE avec filtrage par source_file
            validation_results = await self._validate_with_corrected_method(
                validated_chunks, json_file, max_retries=2
            )

            # Sauvegarde rapport détaillé
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

            # Enregistrement dans le cache
            if self.cache_enabled:
                self.cache.record_processing_result(json_file, result)

            self.logger.info(
                f"Traitement CORRIGE terminé: {result['injection_success']}/{result['segments_created']} chunks - Conformité: {result['final_conformity_score']:.1%}"
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

        # Compilation de tous les fichiers à traiter
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

        # VALIDATION PRÉALABLE DES FICHIERS
        validation_decision = await self.validate_files_before_processing(
            files_to_process, interactive
        )

        if not validation_decision["proceed"]:
            return {
                "status": "stopped_by_validation",
                "reason": validation_decision["reason"],
                "validation_report": validation_decision["validation_report"],
            }

        # Utiliser les fichiers approuvés par la validation
        approved_files = validation_decision["files_to_process"]

        self.logger.info(
            f"Fichiers approuvés pour traitement: {len(approved_files)}/{len(files_to_process)}"
        )

        if not approved_files:
            return {
                "status": "no_valid_files",
                "validation_report": validation_decision["validation_report"],
            }

        # Traitement par batch des fichiers validés
        results = {
            "processed": [],
            "skipped": up_to_date_count,
            "errors": [],
            "summary": {},
        }

        for i in range(0, len(approved_files), batch_size):
            batch = approved_files[i : i + batch_size]

            self.logger.info(
                f"\nBatch VALIDE {i//batch_size + 1}/{(len(approved_files)-1)//batch_size + 1}: {len(batch)} fichiers"
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
                    await asyncio.sleep(1)  # Pause entre fichiers

                except Exception as e:
                    error_info = {
                        "file": file_path,
                        "error": str(e),
                        "processing_reason": reason,
                    }
                    results["errors"].append(error_info)
                    self.logger.error(f"Erreur: {e}")

            # Pause entre batches
            if i + batch_size < len(approved_files):
                await asyncio.sleep(3)

        # Compilation des résultats avec validation
        successful = len(
            [r for r in results["processed"] if r.get("injection_success", 0) > 0]
        )

        results["summary"] = {
            "files_processed": len(results["processed"]),
            "files_successful": successful,
            "files_failed": len(results["errors"]),
            "files_skipped": up_to_date_count,
            "files_excluded_by_validation": len(files_to_process) - len(approved_files),
            "success_rate": successful / len(approved_files) if approved_files else 0,
            "validation_applied": True,
        }

        results["validation_report"] = validation_decision["validation_report"]

        if self.cache_enabled:
            results["cache_stats"] = self.cache.get_cache_stats()

        return results

    # Méthodes utilitaires (simplifiées pour l'exemple)
    async def _create_knowledge_chunks(self, segments, document_context, json_file):
        """Crée les chunks de connaissance avec enrichissement avancé"""
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

    def _quality_filter_corrected(self, knowledge_chunks):
        """Filtre qualité CORRIGÉ avec critères assouplis"""
        validated = []
        for chunk in knowledge_chunks:
            if self._meets_corrected_quality_criteria(
                chunk
            ) and not self._is_duplicate_content(chunk, validated):
                validated.append(chunk)

        self.logger.info(
            f"Filtrage CORRIGÉ: {len(validated)}/{len(knowledge_chunks)} chunks validés"
        )
        return validated

    def _meets_corrected_quality_criteria(self, chunk):
        """Critères de qualité CORRIGÉS"""
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

    async def _validate_with_corrected_method(self, chunks, source_file, max_retries=2):
        """Validation CORRIGEE avec filtrage par source_file"""
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

        # Simplified report for example
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": json_file,
            "segments_created": len(segments),
            "injection_results": injection_results,
            "validation_results": validation_results,
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
            "report_path": "",
        }

    def _cleanup_cache_if_needed(self):
        """Nettoie le cache des fichiers inexistants et détecte les incohérences"""
        if not self.cache_enabled:
            return

        cache_data = self.cache.cache_data["processed_files"]
        files_to_remove = []
        existing_files = 0

        for file_path in cache_data.keys():
            if Path(file_path).exists():
                existing_files += 1
            else:
                files_to_remove.append(file_path)

        # Nettoyage des fichiers inexistants
        if files_to_remove:
            self.logger.warning(
                f"Nettoyage cache: {len(files_to_remove)} fichiers inexistants supprimés"
            )
            for file_path in files_to_remove:
                del cache_data[file_path]
            self.cache._save_cache()

        # Détection d'incohérence majeure
        if existing_files < len(cache_data) * 0.5:  # Plus de 50% des fichiers manquants
            self.logger.warning(
                f"Cache incohérent détecté: {existing_files}/{len(cache_data)} fichiers existent"
            )
            if existing_files == 0:
                self.logger.warning(
                    "Cache complètement obsolète - Considérer --force pour reconstruire"
                )

    def get_extraction_statistics(self):
        """Retourne les statistiques détaillées"""
        stats = self.stats.get_detailed_stats()
        if self.cache_enabled:
            stats["cache"] = self.cache.get_cache_stats()
        return stats


# =============================================================================
# FONCTION POUR TRAITEMENT FICHIER UNIQUE AVEC VALIDATION
# =============================================================================


async def process_single_file(file_path: str):
    """Traite un seul fichier spécifique pour les tests - VERSION CORRIGEE avec validation"""

    if not Path(file_path).exists():
        print(f"Erreur: Fichier {file_path} non trouvé")
        return

    print("=== TRAITEMENT FICHIER UNIQUE - VERSION CORRIGEE AVEC VALIDATION ===")
    print(f"Fichier: {Path(file_path).name}")
    print("Corrections appliquées:")
    print("  - Validation préalable du fichier")
    print("  - Retry automatique LLM")
    print("  - Préservation chunks volumineux (20-3000 mots)")
    print("  - Validation avec filtrage par source_file")
    print("  - Critères de qualité assouplis")

    # Validation préalable du fichier
    validator = FileValidator()
    validation = validator.validate_json_file(file_path)

    print("\nValidation préalable:")
    print(f"  - Fichier valide: {validation['valid']}")
    print(f"  - Taille: {validation['size_bytes']} bytes")
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
        print("LLM configuré: openai/gpt-4 (avec retry automatique)")
    except Exception as e:
        print(f"Erreur configuration LLM: {e}")
        return

    extractor = IntelligentKnowledgeExtractor(
        llm_client=llm_client,
        conformity_threshold=0.95,
        output_dir="single_file_test_corrected",
        cache_enabled=False,  # Désactiver le cache pour test
        force_reprocess=True,
    )

    try:
        start_time = time.time()
        result = await extractor.process_document(file_path)
        duration = time.time() - start_time

        print("\n=== RÉSULTATS CORRIGÉS ===")
        print(f"Durée: {duration:.1f}s")
        print(f"Segments créés: {result['segments_created']}")
        print(f"Chunks injectés: {result['injection_success']}")
        print(f"Erreurs: {result['injection_errors']}")
        print(f"Conformité: {result['final_conformity_score']:.1%}")
        print(f"Couverture chunks: {result.get('chunk_coverage_ratio', 0):.1%}")
        print(f"Rapport: {result['report_path']}")

        # Analyse des améliorations
        coverage_ratio = result.get("chunk_coverage_ratio", 0)
        if coverage_ratio >= 0.9:
            print(f"\nCORRECTION RÉUSSIE - Couverture excellente: {coverage_ratio:.1%}")
        elif coverage_ratio >= 0.7:
            print(
                f"\nAMÉLIORATION PARTIELLE - Couverture acceptable: {coverage_ratio:.1%}"
            )
        else:
            print(
                f"\nCORRECTION INSUFFISANTE - Couverture faible: {coverage_ratio:.1%}"
            )

        return result

    except Exception as e:
        print(f"Erreur traitement: {e}")
    finally:
        extractor.close()


# =============================================================================
# FONCTION PRINCIPALE INTELLIGENTE CORRIGÉE AVEC VALIDATION
# =============================================================================


async def main():
    """Extraction intelligente avec traitement sélectif et validation préalable - VERSION CORRIGEE"""
    import sys

    # Vérifier si un fichier spécifique est demandé
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        file_path = sys.argv[1]
        await process_single_file(file_path)
        return

    print("=== EXTRACTION INTELLIGENTE AVEC CACHE ET VALIDATION - VERSION CORRIGEE ===")

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
    min_conformity = 0.95  # CORRECTION: Seuil réaliste
    max_age_days = 30
    batch_size = 5

    # Configuration du logging selon verbosité
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print("Mode verbose activé")

    print("Configuration CORRIGEE avec validation:")
    print(f"  - Répertoire: {knowledge_dir}")
    print(f"  - Seuil conformité: {min_conformity:.1%}")
    print(f"  - Âge max: {max_age_days} jours")
    print(f"  - Force reprocess: {force_reprocess}")
    print(f"  - Cache activé: {not disable_cache}")
    print(f"  - Mode interactif: {not non_interactive}")
    print("  - Validation préalable: ACTIVÉE")
    print(
        "  - Corrections appliquées: Préservation contenu + Validation réelle + Retry LLM"
    )

    # Configuration LLM
    try:
        llm_client = LLMClient.create_auto(provider="openai", model="gpt-4")
        print("LLM configuré: openai/gpt-4 (avec retry automatique)")
    except Exception as e:
        print(f"Erreur configuration: {e}")
        return

    # Instance intelligente CORRIGEE avec validation
    extractor = IntelligentKnowledgeExtractor(
        llm_client=llm_client,
        conformity_threshold=min_conformity,
        output_dir="intelligent_results_corrected",
        cache_enabled=not disable_cache,
        force_reprocess=force_reprocess,
    )

    # Affichage de l'état initial du cache
    if not disable_cache:
        cache_stats = extractor.cache.get_cache_stats()
        print("\nÉtat initial du cache:")
        print(f"  - Fichiers en cache: {cache_stats.get('total_files', 0)}")
        print(f"  - Succès précédents: {cache_stats.get('successful', 0)}")
        print(f"  - Taux de succès global: {cache_stats.get('success_rate', 0):.1%}")

    try:
        # Nettoyage du cache si nécessaire
        extractor._cleanup_cache_if_needed()

        # Traitement intelligent par batch CORRIGE avec validation
        results = await extractor.process_batch_intelligent_with_validation(
            str(knowledge_dir),
            min_conformity=min_conformity,
            max_age_days=max_age_days,
            batch_size=batch_size,
            interactive=not non_interactive,
        )

        # Affichage des résultats
        print(f"\n{'='*60}")
        print("RAPPORT FINAL - TRAITEMENT INTELLIGENT CORRIGE AVEC VALIDATION")
        print("=" * 60)

        if "error" in results:
            print(f"Erreur: {results['error']}")
            return

        if results.get("status") == "stopped_by_validation":
            print("Traitement arrêté suite à la validation préalable")
            print(f"Raison: {results['reason']}")
            return

        if results.get("status") == "no_valid_files":
            print("Aucun fichier valide trouvé après validation")
            return

        if results.get("status") == "no_processing_needed":
            print("Aucun traitement nécessaire")
            print(f"Fichiers à jour: {results.get('up_to_date', 0)}")
            if extractor.cache_enabled:
                cache_stats = extractor.cache.get_cache_stats()
                print(
                    f"Cache: {cache_stats.get('total_files', 0)} fichiers, "
                    f"{cache_stats.get('success_rate', 0):.1%} succès"
                )
            return

        summary = results.get("summary", {})
        processed = results.get("processed", [])
        errors = results.get("errors", [])
        validation_report = results.get("validation_report", {})

        print(f"Fichiers traités: {summary.get('files_processed', 0)}")
        print(f"Succès: {summary.get('files_successful', 0)}")
        print(f"Échecs: {summary.get('files_failed', 0)}")
        print(f"Ignorés (à jour): {summary.get('files_skipped', 0)}")
        print(
            f"Exclus par validation: {summary.get('files_excluded_by_validation', 0)}"
        )
        print(f"Taux de succès: {summary.get('success_rate', 0):.1%}")

        # Détails de la validation préalable
        print("\nValidation préalable:")
        print(f"  - Fichiers valides: {validation_report.get('valid_files', 0)}")
        print(
            f"  - Fichiers problématiques: {validation_report.get('invalid_files', 0)}"
        )
        print(f"  - Chunks totaux détectés: {validation_report.get('total_chunks', 0)}")

        if validation_report.get("problematic_files"):
            print("\nFichiers problématiques exclus:")
            for problematic in validation_report["problematic_files"][:3]:
                print(
                    f"  - {problematic['file']}: {len(problematic['issues'])} problèmes"
                )

        # Détails par catégorie
        if processed:
            print("\nDétails par raison de traitement:")
            reasons = {}
            for result in processed:
                reason = result.get("processing_reason", "unknown")
                if reason not in reasons:
                    reasons[reason] = {"count": 0, "success": 0, "avg_coverage": 0}
                reasons[reason]["count"] += 1
                if result.get("injection_success", 0) > 0:
                    reasons[reason]["success"] += 1
                reasons[reason]["avg_coverage"] += result.get("chunk_coverage_ratio", 0)

            for reason, stats in reasons.items():
                success_rate = (
                    stats["success"] / stats["count"] if stats["count"] > 0 else 0
                )
                avg_coverage = (
                    stats["avg_coverage"] / stats["count"] if stats["count"] > 0 else 0
                )
                print(
                    f"  - {reason}: {stats['success']}/{stats['count']} "
                    f"({success_rate:.1%}, couverture moy: {avg_coverage:.1%})"
                )

        # Statistiques du cache
        if "cache_stats" in results:
            cache_stats = results["cache_stats"]
            print("\nStatistiques du cache:")
            print(f"  - Total fichiers: {cache_stats.get('total_files', 0)}")
            print(f"  - Chunks totaux: {cache_stats.get('total_chunks', 0)}")
            print(f"  - Conformité moyenne: {cache_stats.get('avg_conformity', 0):.1%}")

        # Erreurs détaillées
        if errors:
            print("\nDétails des erreurs:")
            for error in errors[:5]:  # Limite à 5 erreurs
                print(f"  - {Path(error['file']).name}: {error['error'][:100]}...")

        print("\nAméliorations CORRIGEES:")
        print("  - Validation préalable: Détection fichiers problématiques")
        print("  - Retry automatique LLM: 3 tentatives avec réparation JSON")
        print("  - Préservation chunks volumineux: Limite étendue à 3000 mots")
        print("  - Validation par source_file: Récupération précise")
        print("  - Suppression validation simplifiée: Validation réelle toujours")
        print("  - Critères qualité assouplis: Préserve plus de contenu")
        print("  - Cache intelligent: Évite les retraitements inutiles")
        print("  - Mode interactif: Gestion des problèmes en temps réel")

    except Exception as e:
        print(f"Erreur fatale: {e}")

    finally:
        # Fermeture sécurisée
        if extractor and hasattr(extractor, 'close'):
            extractor.close()
        elif extractor and hasattr(extractor, 'weaviate_ingester'):
            # Fermeture directe de Weaviate si pas de méthode close
            if hasattr(extractor.weaviate_ingester, 'close'):
                extractor.weaviate_ingester.close()
                print("✅ Connexion Weaviate fermée")

if __name__ == "__main__":
    asyncio.run(main())
