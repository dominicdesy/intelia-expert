# -*- coding: utf-8 -*-
"""
rag/core/json_processor.py - Processeur principal pour l'ingestion et traitement JSON
Version 1.0 - Pipeline complet de validation, enrichissement et extraction
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..models.enums import GeneticLine, DocumentType, ExtractionStatus
from ..models.json_models import (
    JSONDocument,
    JSONMetadata,
    JSONTable,
    JSONFigure,
    ProcessingResult,
    validate_json_structure,
    detect_genetic_line_from_content,
    detect_document_type_from_content,
)
from ..models.extraction_models import PerformanceRecord
from ..extractors.extractor_factory import get_extractor_factory


class JSONProcessor:
    """Processeur principal pour l'ingestion et le traitement des documents JSON avicoles"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.config = {
            "auto_enrichment_enabled": True,
            "validation_strict": True,
            "extraction_enabled": True,
            "min_confidence_threshold": 0.3,
            "max_processing_time_seconds": 300,
            "batch_size": 10,
        }

        # Statistiques globales
        self.stats = {
            "documents_processed": 0,
            "documents_successful": 0,
            "documents_failed": 0,
            "total_records_extracted": 0,
            "total_processing_time": 0.0,
            "enrichments_applied": 0,
            "validation_errors": 0,
        }

        # Cache des traitements
        self.processing_cache = {}

        # Factory d'extracteurs
        self.extractor_factory = get_extractor_factory()

    async def process_json_document(
        self, json_data: Dict[str, Any], source_id: Optional[str] = None
    ) -> ProcessingResult:
        """Traite un document JSON complet avec validation, enrichissement et extraction"""

        start_time = time.time()

        try:
            self.logger.info(
                f"Début traitement document: {json_data.get('title', 'Sans titre')}"
            )

            # Étape 1: Validation de base
            validation_errors = await self._validate_json_structure(json_data)
            if validation_errors and self.config["validation_strict"]:
                return self._create_error_result(validation_errors, start_time)

            # Étape 2: Conversion en JSONDocument
            document = await self._convert_to_json_document(json_data, source_id)

            # Étape 3: Enrichissement automatique
            if self.config["auto_enrichment_enabled"]:
                await self._enrich_document(document)

            # Étape 4: Extraction des données de performance
            extraction_records = []
            if self.config["extraction_enabled"]:
                extraction_records = await self._extract_performance_data(document)

            # Étape 5: Finalisation
            processing_time = time.time() - start_time
            result = self._create_success_result(
                document, extraction_records, validation_errors, processing_time
            )

            # Mise à jour des statistiques
            self._update_stats(result, processing_time)

            self.logger.info(
                f"Document traité avec succès: {len(extraction_records)} enregistrements extraits "
                f"en {processing_time:.2f}s"
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Erreur traitement document: {e}")
            return self._create_error_result([str(e)], start_time)

    async def process_json_batch(
        self, json_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Traite un lot de documents JSON en parallèle"""

        start_time = time.time()

        self.logger.info(f"Début traitement par lots: {len(json_documents)} documents")

        # Traitement en parallèle par petits groupes
        results = []
        batch_size = self.config["batch_size"]

        for i in range(0, len(json_documents), batch_size):
            batch = json_documents[i : i + batch_size]

            # Traitement parallèle du batch
            tasks = [
                self.process_json_document(doc, f"batch_{i//batch_size}_{j}")
                for j, doc in enumerate(batch)
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Gestion des exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_result = ProcessingResult(
                        document=JSONDocument(title=f"Document {i+j+1}"),
                        success=False,
                        errors=[str(result)],
                        processing_time_ms=0,
                    )
                    results.append(error_result)
                else:
                    results.append(result)

        # Compilation des résultats
        total_time = time.time() - start_time
        batch_summary = self._compile_batch_results(results, total_time)

        self.logger.info(
            f"Traitement par lots terminé: {batch_summary['successful']}/{len(json_documents)} "
            f"documents traités avec succès en {total_time:.2f}s"
        )

        return batch_summary

    async def _validate_json_structure(self, json_data: Dict[str, Any]) -> List[str]:
        """Validation de la structure JSON de base"""

        errors = validate_json_structure(json_data)

        # Validations supplémentaires spécifiques
        if "metadata" in json_data:
            metadata = json_data["metadata"]
            if not isinstance(metadata, dict):
                errors.append("Le champ 'metadata' doit être un objet")

        # Validation des tableaux
        if "tables" in json_data:
            for i, table in enumerate(json_data["tables"]):
                if "headers" in table and "rows" in table:
                    headers_count = len(table["headers"])
                    for j, row in enumerate(table["rows"]):
                        if len(row) != headers_count:
                            errors.append(
                                f"Tableau {i+1}, ligne {j+1}: "
                                f"nombre de cellules ({len(row)}) != nombre d'en-têtes ({headers_count})"
                            )

        if errors:
            self.stats["validation_errors"] += len(errors)

        return errors

    async def _convert_to_json_document(
        self, json_data: Dict[str, Any], source_id: Optional[str]
    ) -> JSONDocument:
        """Convertit les données JSON brutes en JSONDocument structuré"""

        # Métadonnées de base
        metadata = JSONMetadata()
        if "metadata" in json_data:
            metadata = JSONMetadata.from_dict(json_data["metadata"])

        # Document principal
        document = JSONDocument(
            title=json_data.get("title", ""),
            text=json_data.get("text", ""),
            metadata=metadata,
            file_size_bytes=len(json.dumps(json_data, ensure_ascii=False)),
            processing_timestamp=datetime.now(),
            extraction_status=ExtractionStatus.PROCESSING,
        )

        # Génération du hash de contenu
        content_for_hash = f"{document.title}{document.text}"
        document.content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()[
            :16
        ]

        # Traitement des tableaux
        if "tables" in json_data:
            for table_data in json_data["tables"]:
                table = JSONTable(
                    headers=table_data.get("headers", []),
                    rows=table_data.get("rows", []),
                    context=table_data.get("context", ""),
                    title=table_data.get("title", ""),
                )
                document.add_table(table)

        # Traitement des figures
        if "figures" in json_data:
            for figure_data in json_data["figures"]:
                figure = JSONFigure(
                    title=figure_data.get("title", ""),
                    caption=figure_data.get("caption", ""),
                    alt_text=figure_data.get("alt_text", ""),
                    url=figure_data.get("url"),
                    path=figure_data.get("path"),
                    figure_type=figure_data.get("type", "chart"),
                )
                document.add_figure(figure)

        return document

    async def _enrich_document(self, document: JSONDocument) -> None:
        """Enrichissement automatique du document"""

        enrichments_applied = []

        # Enrichissement 1: Détection de la lignée génétique
        if document.metadata.genetic_line == GeneticLine.UNKNOWN:
            detected_line = detect_genetic_line_from_content(
                document.title, document.text
            )
            if detected_line != GeneticLine.UNKNOWN:
                document.metadata.genetic_line = detected_line
                document.metadata.auto_detected_genetic_line = True
                enrichments_applied.append(
                    f"genetic_line_detected:{detected_line.value}"
                )
                self.logger.debug(f"Lignée génétique détectée: {detected_line.value}")

        # Enrichissement 2: Détection du type de document
        if document.metadata.document_type == DocumentType.UNKNOWN:
            detected_type = detect_document_type_from_content(
                document.title, document.text
            )
            if detected_type != DocumentType.UNKNOWN:
                document.metadata.document_type = detected_type
                document.metadata.auto_detected_document_type = True
                enrichments_applied.append(
                    f"document_type_detected:{detected_type.value}"
                )
                self.logger.debug(f"Type de document détecté: {detected_type.value}")

        # Enrichissement 3: Détection de la langue
        if not document.metadata.language or document.metadata.language == "fr":
            detected_language = await self._detect_language(
                document.title, document.text
            )
            if detected_language and detected_language != document.metadata.language:
                document.metadata.language = detected_language
                document.metadata.auto_detected_language = True
                enrichments_applied.append(f"language_detected:{detected_language}")
                self.logger.debug(f"Langue détectée: {detected_language}")

        # Enrichissement 4: Analyse des tableaux
        for table in document.tables:
            await self._enrich_table(table, document.metadata.genetic_line)

        # Enrichissement 5: Score de qualité
        document.metadata.quality_score = self._calculate_quality_score(document)
        enrichments_applied.append(
            f"quality_score:{document.metadata.quality_score:.2f}"
        )

        # Mise à jour des statistiques
        self.stats["enrichments_applied"] += len(enrichments_applied)

        self.logger.info(f"Enrichissements appliqués: {enrichments_applied}")

    async def _detect_language(self, title: str, text: str) -> str:
        """Détection simple de la langue"""

        content = f"{title} {text}".lower()

        # Patterns simples pour détecter la langue
        language_patterns = {
            "fr": [
                "poids",
                "indice",
                "conversion",
                "mortalité",
                "aliment",
                "performance",
            ],
            "en": [
                "weight",
                "conversion",
                "feed",
                "mortality",
                "performance",
                "intake",
            ],
            "es": ["peso", "conversión", "mortalidad", "alimento", "consumo"],
            "de": ["gewicht", "futter", "sterblichkeit", "leistung"],
        }

        scores = {}
        for lang, patterns in language_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content)
            if score > 0:
                scores[lang] = score

        if scores:
            detected_lang = max(scores, key=scores.get)
            if scores[detected_lang] >= 2:  # Au moins 2 mots détectés
                return detected_lang

        return "fr"  # Défaut français

    async def _enrich_table(self, table: JSONTable, genetic_line: GeneticLine) -> None:
        """Enrichissement spécifique d'un tableau"""

        if not table.headers:
            return

        # Détecter les métriques de performance
        from ..models.extraction_models import detect_metric_from_header

        detected_metrics = []
        for header in table.headers:
            metric = detect_metric_from_header(header)
            if metric:
                detected_metrics.append(metric)

        table.detected_metrics = detected_metrics
        table.has_performance_data = len(detected_metrics) > 0

        # Score de confiance basé sur la richesse des données
        if table.has_performance_data and table.rows:
            # Compter les cellules non vides
            non_empty_cells = sum(
                1
                for row in table.rows
                for cell in row
                if cell and cell.strip() and cell.strip() != "-"
            )
            total_cells = len(table.headers) * len(table.rows)

            if total_cells > 0:
                data_density = non_empty_cells / total_cells
                table.extraction_confidence = min(1.0, data_density + 0.3)

        self.logger.debug(
            f"Tableau enrichi: {len(detected_metrics)} métriques détectées, "
            f"confiance: {table.extraction_confidence:.2f}"
        )

    def _calculate_quality_score(self, document: JSONDocument) -> float:
        """Calcule un score de qualité global pour le document"""

        score = 0.0

        # Qualité du contenu textuel (30%)
        if document.title and len(document.title) > 10:
            score += 0.15
        if document.text and len(document.text) > 100:
            score += 0.15

        # Métadonnées complètes (25%)
        metadata_completeness = 0
        if document.metadata.genetic_line != GeneticLine.UNKNOWN:
            metadata_completeness += 1
        if document.metadata.document_type != DocumentType.UNKNOWN:
            metadata_completeness += 1
        if document.metadata.source and document.metadata.source != "unknown":
            metadata_completeness += 1
        if document.metadata.language:
            metadata_completeness += 1

        score += (metadata_completeness / 4) * 0.25

        # Qualité des tableaux (35%)
        if document.tables:
            table_scores = []
            for table in document.tables:
                table_score = 0
                if table.is_valid:
                    table_score += 0.4
                if table.has_performance_data:
                    table_score += 0.3
                if table.context and len(table.context) > 10:
                    table_score += 0.2
                if len(table.detected_metrics) > 0:
                    table_score += 0.1

                table_scores.append(table_score)

            avg_table_score = sum(table_scores) / len(table_scores)
            score += avg_table_score * 0.35

        # Richesse des données (10%)
        total_data_points = sum(
            len(table.headers) * len(table.rows) for table in document.tables
        )

        if total_data_points > 20:
            score += 0.1
        elif total_data_points > 10:
            score += 0.05

        return min(1.0, score)

    async def _extract_performance_data(
        self, document: JSONDocument
    ) -> List[PerformanceRecord]:
        """Extraction des données de performance via les extracteurs spécialisés"""

        try:
            # Utiliser le factory pour l'extraction
            records = self.extractor_factory.extract_from_document(document)

            # Filtrer selon le seuil de confiance
            filtered_records = [
                record
                for record in records
                if record.extraction_confidence
                >= self.config["min_confidence_threshold"]
            ]

            # Mise à jour du document
            document.performance_records_extracted = len(filtered_records)

            if filtered_records:
                document.extraction_status = ExtractionStatus.SUCCESS
            else:
                document.extraction_status = (
                    ExtractionStatus.FAILED if records else ExtractionStatus.PARTIAL
                )

            self.logger.info(
                f"Extraction terminée: {len(filtered_records)}/{len(records)} enregistrements "
                f"validés (seuil confiance: {self.config['min_confidence_threshold']})"
            )

            return filtered_records

        except Exception as e:
            self.logger.error(f"Erreur extraction performance: {e}")
            document.extraction_status = ExtractionStatus.FAILED
            return []

    def _create_success_result(
        self,
        document: JSONDocument,
        records: List[PerformanceRecord],
        warnings: List[str],
        processing_time: float,
    ) -> ProcessingResult:
        """Crée un résultat de succès"""

        # Enrichissements appliqués
        enrichments = []
        if document.metadata.auto_detected_genetic_line:
            enrichments.append("genetic_line_auto_detected")
        if document.metadata.auto_detected_document_type:
            enrichments.append("document_type_auto_detected")
        if document.metadata.auto_detected_language:
            enrichments.append("language_auto_detected")

        return ProcessingResult(
            document=document,
            success=True,
            errors=[],
            warnings=warnings,
            processing_time_ms=processing_time * 1000,
            tables_processed=len(document.tables),
            tables_with_data=sum(
                1 for table in document.tables if table.has_performance_data
            ),
            performance_records_found=len(records),
            enrichments_applied=enrichments,
        )

    def _create_error_result(
        self, errors: List[str], start_time: float
    ) -> ProcessingResult:
        """Crée un résultat d'erreur"""

        processing_time = time.time() - start_time

        return ProcessingResult(
            document=JSONDocument(title="Document en erreur"),
            success=False,
            errors=errors,
            processing_time_ms=processing_time * 1000,
        )

    def _update_stats(self, result: ProcessingResult, processing_time: float) -> None:
        """Met à jour les statistiques globales"""

        self.stats["documents_processed"] += 1
        self.stats["total_processing_time"] += processing_time

        if result.success:
            self.stats["documents_successful"] += 1
            self.stats["total_records_extracted"] += result.performance_records_found
            self.stats["enrichments_applied"] += len(result.enrichments_applied)
        else:
            self.stats["documents_failed"] += 1

    def _compile_batch_results(
        self, results: List[ProcessingResult], total_time: float
    ) -> Dict[str, Any]:
        """Compile les résultats d'un traitement par lots"""

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_records = sum(r.performance_records_found for r in results)

        # Répartition par lignée génétique
        genetic_line_distribution = {}
        for result in results:
            if result.success:
                line = result.document.metadata.genetic_line.value
                if line not in genetic_line_distribution:
                    genetic_line_distribution[line] = 0
                genetic_line_distribution[line] += 1

        # Erreurs communes
        common_errors = {}
        for result in results:
            for error in result.errors:
                if error not in common_errors:
                    common_errors[error] = 0
                common_errors[error] += 1

        return {
            "total_documents": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(results) if results else 0,
            "total_records_extracted": total_records,
            "avg_records_per_document": total_records / successful if successful else 0,
            "total_processing_time": total_time,
            "avg_processing_time_per_document": (
                total_time / len(results) if results else 0
            ),
            "genetic_line_distribution": genetic_line_distribution,
            "common_errors": common_errors,
            "extractor_factory_stats": self.extractor_factory.get_usage_stats(),
            "processor_stats": self.get_stats(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du processeur"""

        stats = self.stats.copy()

        if stats["documents_processed"] > 0:
            stats["success_rate"] = (
                stats["documents_successful"] / stats["documents_processed"]
            )
            stats["avg_processing_time"] = (
                stats["total_processing_time"] / stats["documents_processed"]
            )
            stats["avg_records_per_document"] = (
                stats["total_records_extracted"] / stats["documents_successful"]
                if stats["documents_successful"]
                else 0
            )
        else:
            stats["success_rate"] = 0
            stats["avg_processing_time"] = 0
            stats["avg_records_per_document"] = 0

        return stats

    def reset_stats(self) -> None:
        """Remet à zéro les statistiques"""

        for key in self.stats:
            self.stats[key] = 0

        self.logger.info("Statistiques du processeur remises à zéro")

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Met à jour la configuration du processeur"""

        old_config = self.config.copy()
        self.config.update(new_config)

        self.logger.info(f"Configuration mise à jour: {old_config} -> {self.config}")


# Instance globale du processeur
_json_processor_instance = None


def get_json_processor() -> JSONProcessor:
    """Récupère l'instance globale du processeur JSON"""
    global _json_processor_instance

    if _json_processor_instance is None:
        _json_processor_instance = JSONProcessor()

    return _json_processor_instance


# Fonctions utilitaires pour usage simple


async def process_single_json(json_data: Dict[str, Any]) -> ProcessingResult:
    """Traite un seul document JSON"""
    processor = get_json_processor()
    return await processor.process_json_document(json_data)


async def process_json_batch(json_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Traite un lot de documents JSON"""
    processor = get_json_processor()
    return await processor.process_json_batch(json_documents)


async def validate_and_enrich_json(json_data: Dict[str, Any]) -> JSONDocument:
    """Valide et enrichit un document JSON sans extraction"""
    processor = get_json_processor()

    # Désactiver temporairement l'extraction
    original_config = processor.config.copy()
    processor.config["extraction_enabled"] = False

    try:
        result = await processor.process_json_document(json_data)
        return result.document
    finally:
        processor.config = original_config


# Exports
__all__ = [
    "JSONProcessor",
    "get_json_processor",
    "process_single_json",
    "process_json_batch",
    "validate_and_enrich_json",
]
