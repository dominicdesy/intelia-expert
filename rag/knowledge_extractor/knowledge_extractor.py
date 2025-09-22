#!/usr/bin/env python3
"""
Extracteur de connaissances intelligent hybride
Version optimisée avec traitement intelligent et cache des résultats
"""

import asyncio
import logging
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta

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

# =============================================================================
# GESTIONNAIRE DE CACHE INTELLIGENT
# =============================================================================


class ProcessingCache:
    """Gestionnaire de cache pour éviter les retraitements inutiles"""

    def __init__(self, cache_dir: str = "processing_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.cache_dir / "processing_cache.json"
        self.reports_dir = self.cache_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialisation du logger
        self.logger = logging.getLogger(f"{__name__}.ProcessingCache")
        
        self.cache_data = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Charge le cache existant"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.logger.info(f"Cache chargé: {len(cache_data.get('processed_files', {}))} fichiers")
                    return cache_data
            except Exception as e:
                self.logger.warning(f"Erreur chargement cache: {e}")
        else:
            self.logger.info("Nouveau cache créé")
        
        return {
            "processed_files": {},
            "last_update": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def _save_cache(self):
        """Sauvegarde le cache"""
        try:
            self.cache_data["last_update"] = datetime.now().isoformat()
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Cache sauvegardé: {self.cache_file}")
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde cache: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Calcule le hash d'un fichier pour détecter les modifications"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def should_process_file(
        self, 
        file_path: str, 
        min_conformity: float = 0.85,
        max_age_days: int = 30
    ) -> Dict[str, Any]:
        """
        Détermine si un fichier doit être traité
        
        Returns:
            Dict avec 'should_process' (bool) et 'reason' (str)
        """
        file_key = str(Path(file_path).resolve())
        current_hash = self.get_file_hash(file_path)
        
        # Debug: afficher l'état du cache
        self.logger.debug(f"Vérification cache pour: {Path(file_path).name}")
        self.logger.debug(f"File key: {file_key}")
        self.logger.debug(f"Cache keys: {len(self.cache_data['processed_files'])} entries")
        
        # Fichier jamais traité
        if file_key not in self.cache_data["processed_files"]:
            self.logger.debug(f"Fichier non trouvé dans cache: {Path(file_path).name}")
            return {
                "should_process": True,
                "reason": "Fichier jamais traité",
                "status": "new"
            }
        
        file_info = self.cache_data["processed_files"][file_key]
        
        self.logger.debug(f"Fichier trouvé dans cache: {Path(file_path).name}")
        self.logger.debug(f"Hash actuel: {current_hash[:8]}...")
        self.logger.debug(f"Hash cache: {file_info.get('file_hash', 'N/A')[:8]}...")
        self.logger.debug(f"Dernier succès: {file_info.get('success', False)}")
        self.logger.debug(f"Conformité: {file_info.get('final_conformity_score', 0.0):.1%}")
        
        # Fichier modifié
        if file_info.get("file_hash") != current_hash:
            return {
                "should_process": True,
                "reason": "Fichier modifié depuis le dernier traitement",
                "status": "modified"
            }
        
        # Échec précédent
        if not file_info.get("success", False):
            return {
                "should_process": True,
                "reason": "Échec lors du traitement précédent",
                "status": "failed_retry"
            }
        
        # Conformité insuffisante
        conformity = file_info.get("final_conformity_score", 0.0)
        if conformity < min_conformity:
            return {
                "should_process": True,
                "reason": f"Conformité insuffisante: {conformity:.1%} < {min_conformity:.1%}",
                "status": "low_conformity"
            }
        
        # Traitement trop ancien
        last_processed = file_info.get("last_processed")
        if last_processed:
            try:
                last_date = datetime.fromisoformat(last_processed.replace('Z', '+00:00'))
                age_days = (datetime.now() - last_date.replace(tzinfo=None)).days
                if age_days > max_age_days:
                    return {
                        "should_process": True,
                        "reason": f"Traitement trop ancien: {age_days} jours",
                        "status": "outdated"
                    }
            except Exception:
                pass
        
        # Injection partielle
        injection_success = file_info.get("injection_success", 0)
        segments_created = file_info.get("segments_created", 0)
        if segments_created > 0 and injection_success / segments_created < 0.8:
            return {
                "should_process": True,
                "reason": f"Injection partielle: {injection_success}/{segments_created}",
                "status": "partial_injection"
            }
        
        # Fichier OK, pas besoin de retraitement
        self.logger.debug(f"Fichier à jour: {Path(file_path).name} - Conformité: {conformity:.1%}")
        return {
            "should_process": False,
            "reason": f"Fichier OK (conformité: {conformity:.1%}, {injection_success} chunks)",
            "status": "up_to_date"
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
        
        self.logger.info(
            f"💾 Cache mis à jour: {Path(file_path).name} - "
            f"Succès: {processing_record['success']}, "
            f"Conformité: {processing_record['final_conformity_score']:.1%}"
        )
        
        self._save_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        processed = self.cache_data["processed_files"]
        
        if not processed:
            return {"total_files": 0}
        
        successful = sum(1 for info in processed.values() if info.get("success"))
        failed = len(processed) - successful
        
        conformities = [
            info.get("final_conformity_score", 0.0) 
            for info in processed.values() 
            if info.get("success")
        ]
        
        return {
            "total_files": len(processed),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(processed) if processed else 0,
            "avg_conformity": sum(conformities) / len(conformities) if conformities else 0,
            "total_chunks": sum(info.get("injection_success", 0) for info in processed.values()),
        }


# =============================================================================
# EXTRACTEUR PRINCIPAL OPTIMISÉ AVEC INTELLIGENCE
# =============================================================================


class IntelligentKnowledgeExtractor:
    """Extracteur de connaissances intelligent avec cache et traitement sélectif"""

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

        # Composants spécialisés optimisés
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

        # Statistiques avancées
        self.stats = ExtractionStatistics()

        self.logger.info(
            f"Extracteur intelligent initialisé - LLM: {self.llm_client.provider}, "
            f"Cache: {'activé' if cache_enabled else 'désactivé'}, "
            f"Force: {force_reprocess}"
        )

    def discover_files_to_process(
        self, 
        knowledge_dir: str,
        min_conformity: float = None,
        max_age_days: int = 30
    ) -> Dict[str, List[str]]:
        """
        Découvre et catégorise les fichiers à traiter
        
        Returns:
            Dict avec les catégories de fichiers
        """
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
            "force_reprocess": []
        }
        
        # Debug: afficher les clés du cache
        if self.cache_enabled:
            cache_keys = list(self.cache.cache_data["processed_files"].keys())
            self.logger.info(f"🔍 Clés dans le cache ({len(cache_keys)}):")
            for i, key in enumerate(cache_keys[:3]):  # Affiche les 3 premières
                self.logger.info(f"  {i+1}. {key}")
            if len(cache_keys) > 3:
                self.logger.info(f"  ... et {len(cache_keys) - 3} autres")
        
        for json_file in json_files:
            if self.force_reprocess:
                categories["force_reprocess"].append(str(json_file))
                continue
                
            if not self.cache_enabled:
                categories["new"].append(str(json_file))
                continue
            
            # Debug: afficher la clé générée pour ce fichier
            file_key = str(Path(json_file).resolve())
            self.logger.debug(f"🔑 Fichier: {json_file.name} -> Clé: {file_key}")
            
            decision = self.cache.should_process_file(
                str(json_file), 
                min_conformity, 
                max_age_days
            )
            
            status = decision.get("status", "new")
            if status in categories:
                categories[status].append(str(json_file))
            else:
                categories["new"].append(str(json_file))
        
        return categories

    async def process_document(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, Any]:
        """Traite un document complet avec analyse avancée"""
        try:
            self.logger.info(f"📄 Traitement: {Path(json_file).name}")

            # 1. Analyse contexte document avec LLM spécialisé
            document_context = self.document_analyzer.analyze_document(
                json_file, txt_file
            )

            # 2. Normalisation lignée génétique avec intent manager
            document_context.genetic_line = self.intent_manager.normalize_genetic_line(
                f"{document_context.genetic_line} {document_context.raw_analysis}"
            )

            # 3. Segmentation sémantique avancée
            segments = self.content_segmenter.create_semantic_segments(
                json_file, txt_file, document_context
            )

            if not segments:
                self.logger.warning(f"Aucun segment créé pour {json_file}")
                result = self._empty_result()
                if self.cache_enabled:
                    self.cache.record_processing_result(json_file, result)
                return result

            self.logger.info(f"🔍 Segments créés: {len(segments)}")

            # 4. Enrichissement métadonnées avec analyse LLM + intents
            knowledge_chunks = await self._create_knowledge_chunks(
                segments, document_context, json_file
            )

            # 5. Filtrage qualité avancé
            validated_chunks = self._quality_filter(knowledge_chunks)

            # 6. Injection Weaviate avec métadonnées enrichies
            injection_results = await self.weaviate_ingester.ingest_batch(
                validated_chunks
            )

            # 7. Attente indexation adaptative
            if injection_results["success_count"] > 0:
                wait_time = min(40, max(20, injection_results["success_count"] * 0.8))
                self.logger.info(f"⏳ Attente indexation: {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # 8. Validation avec pagination corrigée
            validation_results = await self._validate_with_corrected_retry(
                validated_chunks, json_file, max_retries=2
            )

            # 9. Sauvegarde rapport détaillé
            report_path = self._save_report(
                json_file,
                document_context,
                segments,
                injection_results,
                validation_results,
            )

            # 10. Mise à jour statistiques
            self._update_statistics(segments, injection_results, validation_results)

            result = self._build_result(
                json_file,
                segments,
                validated_chunks,
                injection_results,
                validation_results,
                report_path,
            )

            # 11. Enregistrement dans le cache
            if self.cache_enabled:
                self.cache.record_processing_result(json_file, result)

            self.logger.info(
                f"✅ Traitement terminé: {result['injection_success']}/{result['segments_created']} "
                f"chunks - Conformité: {result['final_conformity_score']:.1%}"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Erreur traitement document: {e}")
            self.stats.increment_errors()
            error_result = self._error_result(str(e))
            if self.cache_enabled:
                self.cache.record_processing_result(json_file, error_result)
            return error_result

    async def process_batch_intelligent(
        self,
        knowledge_dir: str,
        min_conformity: float = None,
        max_age_days: int = 30,
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """
        Traitement intelligent par batch avec prioritisation
        """
        if min_conformity is None:
            min_conformity = self.conformity_threshold
            
        # Découverte des fichiers
        categories = self.discover_files_to_process(
            knowledge_dir, min_conformity, max_age_days
        )
        
        if "error" in categories:
            return {"error": categories["error"]}
        
        # Prioritisation des traitements
        priority_order = [
            "failed_retry",      # Échecs précédents (priorité haute)
            "modified",          # Fichiers modifiés
            "low_conformity",    # Conformité insuffisante
            "partial_injection", # Injections partielles
            "new",              # Nouveaux fichiers
            "outdated",         # Fichiers anciens
            "force_reprocess"   # Retraitement forcé
        ]
        
        files_to_process = []
        processing_reasons = {}
        
        for priority in priority_order:
            for file_path in categories.get(priority, []):
                files_to_process.append(file_path)
                processing_reasons[file_path] = priority
        
        up_to_date_count = len(categories.get("up_to_date", []))
        
        self.logger.info(
            f"📊 Découverte intelligente:\n"
            f"  - À traiter: {len(files_to_process)} fichiers\n"
            f"  - À jour: {up_to_date_count} fichiers\n"
            f"  - Nouveaux: {len(categories.get('new', []))}\n"
            f"  - Modifiés: {len(categories.get('modified', []))}\n"
            f"  - Échecs à reprendre: {len(categories.get('failed_retry', []))}\n"
            f"  - Conformité faible: {len(categories.get('low_conformity', []))}"
        )
        
        # Debug: afficher le détail des catégories si verbose
        if self.logger.isEnabledFor(logging.DEBUG):
            for category, files in categories.items():
                if files:
                    self.logger.debug(f"Catégorie '{category}': {len(files)} fichiers")
                    for file_path in files[:3]:  # Limite à 3 exemples
                        self.logger.debug(f"  - {Path(file_path).name}")
        
        if not files_to_process:
            return {
                "status": "no_processing_needed",
                "up_to_date": up_to_date_count,
                "message": "Tous les fichiers sont à jour"
            }
        
        # Traitement par batch
        results = {
            "processed": [],
            "skipped": up_to_date_count,
            "errors": [],
            "summary": {}
        }
        
        start_time = time.time()
        
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            batch_start = time.time()
            
            self.logger.info(
                f"\n📦 Batch {i//batch_size + 1}/{(len(files_to_process)-1)//batch_size + 1}: "
                f"{len(batch)} fichiers"
            )
            
            # Traitement séquentiel du batch
            for j, file_path in enumerate(batch):
                reason = processing_reasons.get(file_path, "unknown")
                self.logger.info(
                    f"  [{j+1}/{len(batch)}] {Path(file_path).name} "
                    f"(raison: {reason})"
                )
                
                try:
                    result = await self.process_document(file_path)
                    result["processing_reason"] = reason
                    results["processed"].append(result)
                    
                    # Pause entre fichiers
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_info = {
                        "file": file_path,
                        "error": str(e),
                        "processing_reason": reason
                    }
                    results["errors"].append(error_info)
                    self.logger.error(f"Erreur: {e}")
            
            batch_duration = time.time() - batch_start
            self.logger.info(f"  Batch terminé en {batch_duration:.1f}s")
            
            # Pause entre batches
            if i + batch_size < len(files_to_process):
                await asyncio.sleep(3)
        
        # Compilation des résultats
        total_duration = time.time() - start_time
        successful = len([r for r in results["processed"] if r.get("injection_success", 0) > 0])
        
        results["summary"] = {
            "total_duration_minutes": total_duration / 60,
            "files_processed": len(results["processed"]),
            "files_successful": successful,
            "files_failed": len(results["errors"]),
            "files_skipped": up_to_date_count,
            "success_rate": successful / len(files_to_process) if files_to_process else 0,
            "tokens_saved": up_to_date_count * 1000,  # Estimation
        }
        
        # Statistiques du cache
        if self.cache_enabled:
            cache_stats = self.cache.get_cache_stats()
            results["cache_stats"] = cache_stats
        
        return results

    # Méthodes existantes (inchangées)
    async def _create_knowledge_chunks(self, segments, document_context, json_file):
        """Crée les chunks de connaissance avec enrichissement avancé"""
        knowledge_chunks = []
        timestamp = datetime.now().isoformat()

        for i, segment in enumerate(segments):
            try:
                # Enrichissement avec analyse LLM + intents
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
                self.logger.error(f"❌ Erreur enrichissement segment {i}: {e}")
                self.stats.increment_errors()
                continue

        return knowledge_chunks

    async def _validate_with_corrected_retry(self, chunks, source_file, max_retries=2):
        """Validation avec pagination corrigée et retry intelligent"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (attempt * 4) + (attempt * 1.0)
                    self.logger.info(
                        f"🔄 Retry validation #{attempt + 1} dans {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)

                # Utilise la validation paginée corrigée
                validation_results = (
                    await self.content_validator.comprehensive_validation(
                        chunks, source_file
                    )
                )

                method_3_success = validation_results.get("validation_stats", {}).get(
                    "method_3_success", 0
                )
                total_chunks = len(chunks)

                if method_3_success / total_chunks >= 0.8:  # 80% minimum
                    self.logger.info(
                        f"✅ Validation partielle acceptée: {method_3_success}/{total_chunks} chunks"
                    )
                    validation_results["conformity_score"] = (
                        method_3_success / total_chunks
                    )
                    return validation_results

                if attempt == max_retries - 1:
                    self.logger.warning(
                        f"⚠️ Validation échoué après {max_retries} tentatives"
                    )
                    partial_score = (
                        method_3_success / total_chunks if total_chunks > 0 else 0
                    )
                    validation_results["conformity_score"] = partial_score
                    validation_results["partial_success"] = True
                    return validation_results

            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"❌ Erreur validation finale: {e}")
                    return {
                        "conformity_score": 0.0,
                        "error": str(e),
                        "requires_correction": True,
                    }

        return validation_results

    def _quality_filter(self, knowledge_chunks):
        """Filtre qualité avancé avec critères spécialisés"""
        validated = []

        for chunk in knowledge_chunks:
            if self._meets_advanced_quality_criteria(
                chunk
            ) and not self._is_duplicate_content(chunk, validated):
                validated.append(chunk)

        self.logger.info(
            f"🔍 Filtrage avancé: {len(validated)}/{len(knowledge_chunks)} chunks validés"
        )
        return validated

    def _meets_advanced_quality_criteria(self, chunk):
        """Critères de qualité avancés basés sur les métadonnées enrichies"""
        return (
            50 <= chunk.word_count <= 500
            and chunk.metadata.confidence_score >= 0.3
            and chunk.content
            and len(chunk.content.strip()) >= 100
            and (len(chunk.metadata.applicable_metrics) > 0
            or len(chunk.metadata.actionable_recommendations) > 0)  # Au moins une valeur ajoutée
        )

    def _is_duplicate_content(self, chunk, existing_chunks):
        """Détection de contenu dupliqué optimisée"""
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

    def _update_statistics(self, segments, injection_results, validation_results):
        """Met à jour les statistiques avec détails avancés"""
        self.stats.increment_documents()
        self.stats.add_chunks_created(len(segments))
        self.stats.add_chunks_injected(injection_results["success_count"])

        if validation_results.get("requires_correction"):
            self.stats.increment_validation_failures()

    def _save_report(
        self,
        json_file,
        document_context,
        segments,
        injection_results,
        validation_results,
    ):
        """Sauvegarde rapport détaillé avec métadonnées enrichies"""
        def serialize_obj(obj):
            if hasattr(obj, "__dict__"):
                return {k: serialize_obj(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, list):
                return [serialize_obj(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: serialize_obj(v) for k, v in obj.items()}
            else:
                return obj

        report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": json_file,
            "document_analysis": serialize_obj(document_context),
            "segmentation_summary": {
                "total_segments": len(segments),
                "avg_word_count": (
                    sum(s.get("word_count", 0) for s in segments) / len(segments)
                    if segments
                    else 0
                ),
                "segment_types": list(
                    set(s.get("segment_type", "unknown") for s in segments)
                ),
            },
            "injection_results": serialize_obj(injection_results),
            "validation_results": serialize_obj(validation_results),
            "extraction_stats": serialize_obj(self.stats.get_stats()),
            "optimizations_applied": {
                "advanced_llm_analysis": True,
                "intent_based_enrichment": True,
                "genetic_line_normalization": True,
                "paginated_validation": True,
                "quality_filtering_enhanced": True,
                "intelligent_caching": self.cache_enabled,
            },
        }

        report_filename = f"report_{Path(json_file).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.output_dir / report_filename

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
        """Construit le résultat final avec métadonnées enrichies"""
        return {
            "document": Path(json_file).name,
            "segments_created": len(segments),
            "chunks_validated": len(chunks),
            "injection_success": injection_results["success_count"],
            "injection_errors": injection_results["error_count"],
            "final_conformity_score": validation_results.get("conformity_score", 0.0),
            "corrections_applied": validation_results.get(
                "corrections_attempted", False
            ),
            "partial_success": validation_results.get("partial_success", False),
            "report_path": report_path,
            "optimization_level": "intelligent",
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
            "report_path": "",
            "optimization_level": "intelligent",
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
            "report_path": "",
            "optimization_level": "intelligent",
        }

    def close(self):
        """Ferme les connexions"""
        if hasattr(self.weaviate_ingester, "close"):
            self.weaviate_ingester.close()

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
            self.logger.warning(f"🧹 Nettoyage cache: {len(files_to_remove)} fichiers inexistants supprimés")
            for file_path in files_to_remove:
                del cache_data[file_path]
            self.cache._save_cache()
        
        # Détection d'incohérence majeure
        if existing_files < len(cache_data) * 0.5:  # Plus de 50% des fichiers manquants
            self.logger.warning(
                f"⚠️ Cache incohérent détecté: {existing_files}/{len(cache_data)} fichiers existent"
            )
            if existing_files == 0:
                self.logger.warning("🔄 Cache complètement obsolète - Considérer --force pour reconstruire")

    def get_extraction_statistics(self):
        """Retourne les statistiques détaillées"""
        stats = self.stats.get_detailed_stats()
        if self.cache_enabled:
            stats["cache"] = self.cache.get_cache_stats()
        return stats


# =============================================================================
# FONCTION PRINCIPALE INTELLIGENTE
# =============================================================================


async def main():
    """Extraction intelligente avec traitement sélectif"""

    print("=== EXTRACTION INTELLIGENTE AVEC CACHE ===")

    # Configuration
    knowledge_dir = Path("C:/intelia_gpt/intelia-expert/rag/documents/Knowledge")
    if not knowledge_dir.exists():
        print(f"Erreur: Répertoire {knowledge_dir} non trouvé")
        return

    # Options de traitement
    import sys
    force_reprocess = "--force" in sys.argv
    disable_cache = "--no-cache" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    min_conformity = 0.85
    max_age_days = 30
    batch_size = 5
    
    # Configuration du logging selon verbosité
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print("🔍 Mode verbose activé")

    print(f"Configuration:")
    print(f"  - Répertoire: {knowledge_dir}")
    print(f"  - Seuil conformité: {min_conformity:.1%}")
    print(f"  - Âge max: {max_age_days} jours")
    print(f"  - Force reprocess: {force_reprocess}")
    print(f"  - Cache activé: {not disable_cache}")
    print(f"  - Verbose: {verbose}")

    # Configuration LLM
    try:
        llm_client = LLMClient.create_auto(provider="openai", model="gpt-4")
        print("🤖 LLM configuré: openai/gpt-4")
    except Exception as e:
        print(f"Erreur configuration: {e}")
        return

    # Instance intelligente
    extractor = IntelligentKnowledgeExtractor(
        llm_client=llm_client,
        conformity_threshold=min_conformity,
        output_dir="intelligent_results",
        cache_enabled=not disable_cache,
        force_reprocess=force_reprocess,
    )

    # Affichage de l'état initial du cache
    if not disable_cache:
        cache_stats = extractor.cache.get_cache_stats()
        print(f"\n💾 État initial du cache:")
        print(f"  - Fichiers en cache: {cache_stats.get('total_files', 0)}")
        print(f"  - Succès précédents: {cache_stats.get('successful', 0)}")
        print(f"  - Taux de succès global: {cache_stats.get('success_rate', 0):.1%}")

    try:
        start_time = time.time()
        
        # Traitement intelligent par batch
        results = await extractor.process_batch_intelligent(
            str(knowledge_dir),
            min_conformity=min_conformity,
            max_age_days=max_age_days,
            batch_size=batch_size
        )

        # Affichage des résultats
        print(f"\n{'='*60}")
        print("RAPPORT FINAL - TRAITEMENT INTELLIGENT")
        print("=" * 60)

        if "error" in results:
            print(f"❌ Erreur: {results['error']}")
            return

        if results.get("status") == "no_processing_needed":
            print("✅ Aucun traitement nécessaire")
            print(f"📁 Fichiers à jour: {results.get('up_to_date', 0)}")
            if extractor.cache_enabled:
                cache_stats = extractor.cache.get_cache_stats()
                print(f"📊 Cache: {cache_stats.get('total_files', 0)} fichiers, "
                      f"{cache_stats.get('success_rate', 0):.1%} succès")
            return

        summary = results.get("summary", {})
        processed = results.get("processed", [])
        errors = results.get("errors", [])

        print(f"⏱️  Durée totale: {summary.get('total_duration_minutes', 0):.1f} minutes")
        print(f"📁 Fichiers traités: {summary.get('files_processed', 0)}")
        print(f"✅ Succès: {summary.get('files_successful', 0)}")
        print(f"❌ Échecs: {summary.get('files_failed', 0)}")
        print(f"⏭️  Ignorés (à jour): {summary.get('files_skipped', 0)}")
        print(f"📈 Taux de succès: {summary.get('success_rate', 0):.1%}")
        print(f"💰 Tokens économisés: ~{summary.get('tokens_saved', 0):,}")

        # Détails par catégorie
        if processed:
            print(f"\n📊 Détails par raison de traitement:")
            reasons = {}
            for result in processed:
                reason = result.get("processing_reason", "unknown")
                if reason not in reasons:
                    reasons[reason] = {"count": 0, "success": 0}
                reasons[reason]["count"] += 1
                if result.get("injection_success", 0) > 0:
                    reasons[reason]["success"] += 1

            for reason, stats in reasons.items():
                success_rate = stats["success"] / stats["count"] if stats["count"] > 0 else 0
                print(f"  - {reason}: {stats['success']}/{stats['count']} "
                      f"({success_rate:.1%})")

        # Statistiques du cache
        if "cache_stats" in results:
            cache_stats = results["cache_stats"]
            print(f"\n💾 Statistiques du cache:")
            print(f"  - Total fichiers: {cache_stats.get('total_files', 0)}")
            print(f"  - Chunks totaux: {cache_stats.get('total_chunks', 0)}")
            print(f"  - Conformité moyenne: {cache_stats.get('avg_conformity', 0):.1%}")

        # Erreurs détaillées
        if errors:
            print(f"\n❌ Détails des erreurs:")
            for error in errors[:5]:  # Limite à 5 erreurs
                print(f"  - {Path(error['file']).name}: {error['error'][:100]}...")

        print(f"\n🚀 Optimisations:")
        print(f"  - Cache intelligent: Évite les retraitements inutiles")
        print(f"  - Prioritisation: Traite d'abord les échecs et conformité faible")
        print(f"  - Détection modifications: Hash des fichiers")
        print(f"  - Traitement par batch: Optimise les ressources")

    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
    finally:
        extractor.close()


if __name__ == "__main__":
    import sys
    asyncio.run(main())