# -*- coding: utf-8 -*-
"""
rag/extractors/base_extractor.py - Extracteur de base pour les données avicoles
Version 1.0 - Classe abstraite pour l'extraction de données JSON
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import hashlib

from ..models.enums import GeneticLine, MetricType, Sex
from ..models.json_models import JSONDocument, JSONTable
from ..models.extraction_models import (
    PerformanceRecord,
    ExtractionSession,
    parse_numeric_value,
    detect_metric_from_header,
    detect_age_from_context,
    detect_sex_from_context,
    detect_phase_from_age_and_genetic_line,
)


class BaseExtractor(ABC):
    """Extracteur de base pour les données de performance avicoles"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Configuration par défaut
        self.confidence_threshold = 0.5
        self.min_age_days = 0
        self.max_age_days = 500
        self.validation_enabled = True

        # Patterns communs à tous les extracteurs
        self.common_patterns = {
            "age_patterns": [
                r"(\d+)\s*(?:day|jour|día|tag|d|j)\b",
                r"week\s*(\d+)",
                r"(\d+)\s*(?:week|sem|wk|w)\b",
            ],
            "weight_patterns": [
                r"(?:live\s*weight|body\s*weight|weight|poids|bw|lw)",
                r"(?:peso|gewicht|masse)",
            ],
            "fcr_patterns": [
                r"(?:fcr|feed\s*conversion|conversion|ic|indice)",
                r"(?:feed\s*conv|f:g|feed:gain)",
            ],
            "mortality_patterns": [
                r"(?:mortality|mortalité|mort|death|dead)",
                r"(?:mortalidad|muerte|tot)",
            ],
        }

        # Statistiques d'extraction
        self.extraction_stats = {
            "documents_processed": 0,
            "tables_processed": 0,
            "records_extracted": 0,
            "records_validated": 0,
            "errors": 0,
        }

    @abstractmethod
    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        """Retourne les lignées génétiques supportées par cet extracteur"""
        pass

    @abstractmethod
    def extract_performance_data(
        self, json_document: JSONDocument
    ) -> List[PerformanceRecord]:
        """Extrait les données de performance depuis un document JSON"""
        pass

    def extract_from_json_data(
        self, json_data: Dict[str, Any]
    ) -> List[PerformanceRecord]:
        """Point d'entrée principal pour l'extraction depuis des données JSON brutes"""

        # Conversion en JSONDocument
        json_doc = JSONDocument.from_dict(json_data)

        # Validation préliminaire
        if not self._is_compatible_document(json_doc):
            self.logger.warning(
                f"Document incompatible avec l'extracteur {self.__class__.__name__}"
            )
            return []

        # Extraction
        self.extraction_stats["documents_processed"] += 1
        return self.extract_performance_data(json_doc)

    def _is_compatible_document(self, json_doc: JSONDocument) -> bool:
        """Vérifie si le document est compatible avec cet extracteur"""

        # Vérification lignée génétique
        if json_doc.metadata.genetic_line != GeneticLine.UNKNOWN:
            return json_doc.metadata.genetic_line in self.get_supported_genetic_lines()

        # Si lignée inconnue, tenter détection depuis le contenu
        detected_line = self._detect_genetic_line_from_content(
            json_doc.title, json_doc.text
        )
        return detected_line in self.get_supported_genetic_lines()

    def _detect_genetic_line_from_content(self, title: str, text: str) -> GeneticLine:
        """Détecte la lignée génétique depuis le contenu (à implémenter par sous-classe)"""
        from ..models.enums import GENETIC_LINE_PATTERNS

        content = f"{title} {text}".lower()

        for genetic_line, patterns in GENETIC_LINE_PATTERNS.items():
            if any(pattern in content for pattern in patterns):
                return genetic_line

        return GeneticLine.UNKNOWN

    def _extract_from_table(
        self, table: JSONTable, json_doc: JSONDocument
    ) -> List[PerformanceRecord]:
        """Extrait les données de performance depuis un tableau"""

        records = []
        self.extraction_stats["tables_processed"] += 1

        if not table.is_valid or not table.headers:
            self.logger.warning("Tableau invalide ou sans en-têtes")
            return records

        try:
            # Analyse des en-têtes pour détecter les métriques
            metric_columns = self._analyze_headers(table.headers)

            if not metric_columns:
                self.logger.debug("Aucune métrique détectée dans les en-têtes")
                return records

            # Traitement des lignes
            for row_idx, row in enumerate(table.rows):
                try:
                    row_records = self._extract_from_row(
                        row, table.headers, metric_columns, table, json_doc, row_idx
                    )
                    records.extend(row_records)
                except Exception as e:
                    self.logger.error(f"Erreur extraction ligne {row_idx}: {e}")
                    self.extraction_stats["errors"] += 1
                    continue

            # Mise à jour des statistiques du tableau
            table.has_performance_data = len(records) > 0
            table.detected_metrics = list(set(r.metric_type for r in records))
            table.extraction_confidence = self._calculate_table_confidence(records)

            self.logger.info(f"Table extraite: {len(records)} enregistrements")

        except Exception as e:
            self.logger.error(f"Erreur traitement tableau: {e}")
            self.extraction_stats["errors"] += 1

        return records

    def _analyze_headers(self, headers: List[str]) -> Dict[int, MetricType]:
        """Analyse les en-têtes pour détecter les colonnes de métriques"""

        metric_columns = {}

        for col_idx, header in enumerate(headers):
            # Détecter la métrique depuis l'en-tête
            detected_metric = detect_metric_from_header(header)

            if detected_metric:
                metric_columns[col_idx] = detected_metric
                self.logger.debug(
                    f"Métrique détectée: {header} -> {detected_metric.value}"
                )

        return metric_columns

    def _extract_from_row(
        self,
        row: List[str],
        headers: List[str],
        metric_columns: Dict[int, MetricType],
        table: JSONTable,
        json_doc: JSONDocument,
        row_idx: int,
    ) -> List[PerformanceRecord]:
        """Extrait les données de performance depuis une ligne de tableau"""

        records = []

        # Détecter l'âge depuis la ligne ou le contexte
        age_days = self._detect_age_from_row(row, headers, table.context)

        if age_days == 0:
            self.logger.debug(f"Âge non détecté pour ligne {row_idx}")
            return records

        # Détecter le sexe et la phase
        sex = self._detect_sex_from_row(row, headers, table.context)
        genetic_line = json_doc.metadata.genetic_line
        phase = detect_phase_from_age_and_genetic_line(age_days, genetic_line)

        # Extraire chaque métrique détectée
        for col_idx, metric_type in metric_columns.items():
            if col_idx >= len(row):
                continue

            cell_value = row[col_idx].strip()
            if not cell_value or cell_value == "-":
                continue

            try:
                # Parser la valeur numérique
                numeric_value, unit = parse_numeric_value(cell_value)

                if numeric_value <= 0:
                    continue

                # Créer l'enregistrement
                record = PerformanceRecord(
                    source_document_id=json_doc.content_hash,
                    genetic_line=genetic_line,
                    age_days=age_days,
                    sex=sex,
                    phase=phase,
                    metric_type=metric_type,
                    value_original=numeric_value,
                    unit_original=unit,
                    table_context=table.context,
                    column_header=headers[col_idx],
                    row_context=f"Row {row_idx + 1}: {' | '.join(row[:3])}",
                )

                # Normaliser l'unité
                record.normalize_unit()

                # Calculer la confiance
                record.extraction_confidence = self._calculate_extraction_confidence(
                    record, table, headers[col_idx]
                )

                # Validation finale
                if (
                    self.validation_enabled
                    and record.validation_passed
                    and record.is_plausible
                ):
                    records.append(record)
                    self.extraction_stats["records_validated"] += 1
                elif not self.validation_enabled:
                    records.append(record)

                self.extraction_stats["records_extracted"] += 1

            except Exception as e:
                self.logger.error(
                    f"Erreur extraction cellule [{row_idx}, {col_idx}]: {e}"
                )
                continue

        return records

    def _detect_age_from_row(
        self, row: List[str], headers: List[str], context: str
    ) -> int:
        """Détecte l'âge depuis une ligne de données"""

        # Chercher dans les colonnes qui pourraient contenir l'âge
        age_keywords = ["age", "day", "jour", "días", "week", "sem"]

        for i, (header, cell) in enumerate(zip(headers, row)):
            header_lower = header.lower()

            # Vérifier si l'en-tête indique une colonne d'âge
            if any(keyword in header_lower for keyword in age_keywords):
                try:
                    # Extraire l'âge depuis la cellule
                    age_match = re.search(r"(\d+)", cell)
                    if age_match:
                        age = int(age_match.group(1))

                        # Conversion semaines -> jours si nécessaire
                        if "week" in header_lower or "sem" in header_lower:
                            age *= 7

                        if self.min_age_days <= age <= self.max_age_days:
                            return age
                except (ValueError, AttributeError):
                    continue

        # Fallback: chercher dans le contexte ou l'en-tête de tableau
        return detect_age_from_context(context, " ".join(headers))

    def _detect_sex_from_row(
        self, row: List[str], headers: List[str], context: str
    ) -> Sex:
        """Détecte le sexe depuis une ligne de données"""

        # Chercher dans les colonnes
        for header, cell in zip(headers, row):
            combined = f"{header} {cell}".lower()

            if any(term in combined for term in ["male", "mâle", "macho", "cock"]):
                return Sex.MALE
            elif any(
                term in combined for term in ["female", "femelle", "hembra", "hen"]
            ):
                return Sex.FEMALE
            elif any(term in combined for term in ["mixed", "mixte", "as hatched"]):
                return Sex.MIXED

        # Fallback: chercher dans le contexte
        return detect_sex_from_context(context, " ".join(headers))

    def _calculate_extraction_confidence(
        self, record: PerformanceRecord, table: JSONTable, header: str
    ) -> float:
        """Calcule la confiance d'extraction pour un enregistrement"""

        confidence = 1.0

        # Réduction selon la qualité du contexte
        if not table.context or len(table.context.strip()) < 10:
            confidence -= 0.1

        # Réduction selon la clarté de l'en-tête
        header_lower = header.lower()
        if not any(
            pattern in header_lower
            for pattern_group in self.common_patterns.values()
            for pattern in pattern_group
        ):
            confidence -= 0.1

        # Réduction selon la plausibilité
        if not record.is_plausible:
            confidence -= 0.3

        # Bonus selon la lignée génétique détectée
        if record.genetic_line in self.get_supported_genetic_lines():
            confidence += 0.1

        return max(0.1, min(1.0, confidence))

    def _calculate_table_confidence(self, records: List[PerformanceRecord]) -> float:
        """Calcule la confiance moyenne pour un tableau"""

        if not records:
            return 0.0

        confidences = [r.extraction_confidence for r in records]
        return sum(confidences) / len(confidences)

    def _validate_record(self, record: PerformanceRecord) -> bool:
        """Validation spécifique d'un enregistrement (à surcharger)"""

        # Validation de base
        if record.age_days < self.min_age_days or record.age_days > self.max_age_days:
            return False

        if record.value_canonical <= 0:
            return False

        if record.extraction_confidence < self.confidence_threshold:
            return False

        return True

    def get_extraction_summary(self) -> Dict[str, Any]:
        """Retourne un résumé des statistiques d'extraction"""

        stats = self.extraction_stats.copy()

        # Calculs dérivés
        if stats["records_extracted"] > 0:
            stats["validation_rate"] = (
                stats["records_validated"] / stats["records_extracted"]
            )
        else:
            stats["validation_rate"] = 0.0

        if stats["tables_processed"] > 0:
            stats["avg_records_per_table"] = (
                stats["records_extracted"] / stats["tables_processed"]
            )
        else:
            stats["avg_records_per_table"] = 0.0

        stats["extractor_type"] = self.__class__.__name__
        stats["supported_genetic_lines"] = [
            gl.value for gl in self.get_supported_genetic_lines()
        ]

        return stats

    def reset_stats(self) -> None:
        """Remet à zéro les statistiques d'extraction"""

        for key in self.extraction_stats:
            self.extraction_stats[key] = 0

    def create_extraction_session(self) -> ExtractionSession:
        """Crée une nouvelle session d'extraction"""

        session = ExtractionSession(
            session_id=self._generate_session_id(),
            extractor_type=self.__class__.__name__,
            confidence_threshold=self.confidence_threshold,
        )

        return session

    def _generate_session_id(self) -> str:
        """Génère un ID unique pour la session"""

        import time

        timestamp = str(int(time.time()))
        extractor_name = self.__class__.__name__.lower()

        # Hash pour l'unicité
        content = f"{extractor_name}_{timestamp}"
        session_hash = hashlib.md5(content.encode()).hexdigest()[:8]

        return f"{extractor_name}_{session_hash}"

    # Méthodes utilitaires communes

    @staticmethod
    def clean_text(text: str) -> str:
        """Nettoie un texte pour l'analyse"""

        if not text:
            return ""

        # Suppression caractères spéciaux et normalisation
        cleaned = re.sub(r"[^\w\s\-\.\,]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip().lower()

    @staticmethod
    def extract_numbers_from_text(text: str) -> List[float]:
        """Extrait tous les nombres d'un texte"""

        if not text:
            return []

        # Pattern pour nombres (entiers et décimaux)
        number_pattern = r"\b\d+(?:\.\d+)?\b"
        matches = re.findall(number_pattern, text.replace(",", "."))

        numbers = []
        for match in matches:
            try:
                numbers.append(float(match))
            except ValueError:
                continue

        return numbers

    def log_extraction_progress(self, message: str, level: str = "info") -> None:
        """Log avec formatage standardisé"""

        prefix = f"[{self.__class__.__name__}]"
        formatted_message = f"{prefix} {message}"

        if level == "debug":
            self.logger.debug(formatted_message)
        elif level == "warning":
            self.logger.warning(formatted_message)
        elif level == "error":
            self.logger.error(formatted_message)
        else:
            self.logger.info(formatted_message)
