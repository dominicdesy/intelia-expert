# -*- coding: utf-8 -*-
"""
rag/extractors/ross_extractor.py - Extracteur spécialisé pour les lignées Ross
Version 2.0 - Adaptation complète pour fichiers JSON textuels avec conservation de toute la logique originale
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# CORRECTION: Imports robustes avec fallbacks
try:
    from .base_extractor import BaseExtractor
    from ..models.enums import GeneticLine, MetricType, Sex, Phase
    from ..models.extraction_models import PerformanceRecord
except ImportError:
    try:
        from base_extractor import BaseExtractor
        from models.enums import GeneticLine, MetricType, Sex, Phase
        from models.extraction_models import PerformanceRecord
    except ImportError:
        # Fallback avec définitions minimales depuis base_extractor corrigé
        from base_extractor import BaseExtractor, GeneticLine, MetricType, Sex, PerformanceRecord
        
        class Phase:
            STARTER = "starter"
            GROWER = "grower"
            FINISHER = "finisher"
            WHOLE_CYCLE = "whole_cycle"
            UNKNOWN = "unknown"

@dataclass
class TextTable:
    """Structure temporaire pour représenter un tableau trouvé dans le texte"""

    headers: List[str]
    rows: List[List[str]]
    context: str
    start_pos: int
    end_pos: int


class RossExtractor(BaseExtractor):
    """Extracteur spécialisé pour les lignées Ross (308, 708) - Version JSON textuel complète"""

    def __init__(self, genetic_line: GeneticLine = GeneticLine.ROSS_308):
        super().__init__()

        if genetic_line not in [GeneticLine.ROSS_308, GeneticLine.ROSS_708]:
            raise ValueError(f"Lignée non supportée: {genetic_line}")

        self.genetic_line = genetic_line

        # Mappings spécifiques Ross (conservés de l'original)
        self.ross_metric_mappings = {
            # Poids
            "live weight (g)": MetricType.WEIGHT_G,
            "live weight (lb)": MetricType.WEIGHT_G,
            "body weight (g)": MetricType.WEIGHT_G,
            "body weight (lb)": MetricType.WEIGHT_G,
            "weight (g)": MetricType.WEIGHT_G,
            "weight (kg)": MetricType.WEIGHT_KG,
            "bw (g)": MetricType.WEIGHT_G,
            "bw (kg)": MetricType.WEIGHT_KG,
            "live wt (g)": MetricType.WEIGHT_G,
            "body wt (g)": MetricType.WEIGHT_G,
            # Consommation d'aliment
            "cumulative feed (g)": MetricType.FEED_INTAKE_G,
            "cumulative feed (kg)": MetricType.FEED_INTAKE_KG,
            "feed consumption (g)": MetricType.FEED_INTAKE_G,
            "feed intake (g)": MetricType.FEED_INTAKE_G,
            "cum feed (g)": MetricType.FEED_INTAKE_G,
            "feed (g)": MetricType.FEED_INTAKE_G,
            "cum. intake (g)": MetricType.FEED_INTAKE_G,
            "daily intake (g)": MetricType.FEED_INTAKE_G,
            # FCR
            "fcr": MetricType.FCR,
            "feed conversion ratio": MetricType.FCR,
            "feed conversion": MetricType.FCR,
            "feed:gain": MetricType.FCR,
            "f:g": MetricType.FCR,
            "conversion": MetricType.FCR,
            # Mortalité
            "mortality (%)": MetricType.MORTALITY_RATE,
            "cumulative mortality (%)": MetricType.MORTALITY_RATE,
            "mort (%)": MetricType.MORTALITY_RATE,
            "livability (%)": MetricType.LIVABILITY,
            "viability (%)": MetricType.LIVABILITY,
            "survival (%)": MetricType.LIVABILITY,
            # Gain quotidien
            "daily gain (g)": MetricType.DAILY_GAIN,
            "daily weight gain (g)": MetricType.DAILY_GAIN,
            "adg (g)": MetricType.DAILY_GAIN,
            "avg daily gain (g)": MetricType.DAILY_GAIN,
            "av. daily gain (g)": MetricType.DAILY_GAIN,
        }

        # Patterns spécifiques Ross pour détecter les contextes (conservés)
        self.ross_context_patterns = {
            "performance_guide": [
                "ross 308 performance",
                "ross performance objectives",
                "broiler performance",
                "performance targets",
            ],
            "nutrition": [
                "ross 308 nutrition",
                "feeding programme",
                "feed specifications",
                "nutritional requirements",
            ],
            "management": [
                "ross 308 management",
                "broiler management",
                "husbandry guide",
                "production guide",
            ],
        }

        # Seuils de validation spécifiques Ross (conservés intégralement)
        self.ross_validation_thresholds = {
            MetricType.WEIGHT_G: {
                "min": 30,  # 30g minimum (poussin)
                "max": 3500,  # 3.5kg maximum
                "daily_max_gain": 120,  # Gain quotidien max 120g
            },
            MetricType.FCR: {
                "min": 0.8,
                "max": 2.5,
                "optimal_range": (1.4, 1.9),  # FCR optimal Ross 308
            },
            MetricType.MORTALITY_RATE: {
                "min": 0,
                "max": 15,  # Max 15% mortalité acceptable
                "warning_threshold": 5,  # Alerte si > 5%
            },
            MetricType.LIVABILITY: {"min": 85, "max": 100},  # Min 85% viabilité
        }

    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        """Lignées supportées par cet extracteur"""
        return [GeneticLine.ROSS_308, GeneticLine.ROSS_708]

    def extract_performance_data(self, json_document: dict) -> List[PerformanceRecord]:
        """Extraction spécialisée pour Ross avec validation renforcée - Adaptée pour JSON textuel"""

        records = []

        # Adaptation : extraction du titre depuis le JSON
        title = json_document.get("source_file", "Unknown Document")
        self.log_extraction_progress(f"Début extraction Ross pour: {title}")

        # Vérifier si le document contient des données de performance
        if not json_document.get("metadata", {}).get(
            "contains_performance_tables", False
        ):
            self.log_extraction_progress(
                "Document ne contient pas de tableaux de performance"
            )
            return records

        # Extraire le texte principal
        text_content = json_document.get("text", "")
        if not text_content:
            self.log_extraction_progress("Aucun contenu textuel trouvé")
            return records

        # Validation de la lignée (conservée)
        detected_line = self._detect_ross_genetic_line_from_text(text_content, title)
        if detected_line == GeneticLine.UNKNOWN:
            self.log_extraction_progress("Lignée Ross non confirmée", "warning")
        else:
            # Mettre à jour la lignée détectée
            json_document.setdefault("metadata", {})[
                "genetic_line"
            ] = detected_line.value
            json_document["metadata"]["auto_detected_genetic_line"] = True

        # Extraire les tableaux du texte
        tables = self._extract_tables_from_text(text_content)

        # Traitement des tableaux (logique conservée et adaptée)
        for table_idx, table in enumerate(tables):
            try:
                self.log_extraction_progress(
                    f"Traitement tableau {table_idx + 1}/{len(tables)}"
                )

                # Pré-filtrage des tableaux Ross (adapté)
                if not self._is_ross_performance_table_text(table):
                    self.log_extraction_progress(
                        f"Tableau {table_idx + 1} ignoré (pas de données Ross)", "debug"
                    )
                    continue

                table_records = self._extract_from_text_table(table, json_document)

                # Post-traitement spécifique Ross (conservé)
                validated_records = self._post_process_ross_records(
                    table_records, table_idx
                )

                records.extend(validated_records)

                self.log_extraction_progress(
                    f"Tableau {table_idx + 1}: {len(validated_records)} enregistrements validés"
                )

            except Exception as e:
                self.log_extraction_progress(
                    f"Erreur tableau {table_idx + 1}: {e}", "error"
                )
                self.extraction_stats["errors"] += 1
                continue

        # Validation finale du lot (conservée)
        final_records = self._final_validation_ross(records)

        # Mise à jour des statistiques du document
        json_document["performance_records_extracted"] = len(final_records)
        json_document["extraction_status"] = "success" if final_records else "no_data"

        self.log_extraction_progress(
            f"Extraction terminée: {len(final_records)} enregistrements finaux"
        )

        return final_records

    def _extract_tables_from_text(self, text: str) -> List[TextTable]:
        """Extrait les tableaux markdown du texte"""

        tables = []
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Détecter le début d'un tableau markdown
            if "|" in line and len(line.split("|")) >= 3:
                table_start = i
                headers = [cell.strip() for cell in line.split("|")[1:-1]]

                # Ignorer la ligne de séparation (---|---|---)
                if i + 1 < len(lines) and "---" in lines[i + 1]:
                    i += 2
                else:
                    i += 1

                # Extraire les lignes de données
                rows = []
                while i < len(lines) and "|" in lines[i] and "---" not in lines[i]:
                    row_data = [cell.strip() for cell in lines[i].split("|")[1:-1]]
                    if len(row_data) == len(headers):
                        rows.append(row_data)
                    i += 1

                # Créer l'objet tableau si des données trouvées
                if rows:
                    # Contexte = paragraphes précédents
                    context = ""
                    for j in range(max(0, table_start - 5), table_start):
                        if lines[j].strip() and not lines[j].startswith("#"):
                            context += lines[j] + " "

                    table = TextTable(
                        headers=headers,
                        rows=rows,
                        context=context.strip(),
                        start_pos=table_start,
                        end_pos=i,
                    )
                    tables.append(table)
            else:
                i += 1

        return tables

    def _detect_ross_genetic_line_from_text(
        self, text_content: str, title: str
    ) -> GeneticLine:
        """Détection spécialisée de la lignée Ross (conservée et adaptée)"""

        content = f"{title} {text_content}".lower()

        # Patterns spécifiques Ross avec priorité (conservés)
        ross_patterns = [
            (
                GeneticLine.ROSS_308,
                [
                    "ross 308",
                    "ross-308",
                    "ross308",
                    "r308",
                    "r-308",
                    "ross broiler 308",
                    "broiler ross 308",
                ],
            ),
            (
                GeneticLine.ROSS_708,
                [
                    "ross 708",
                    "ross-708",
                    "ross708",
                    "r708",
                    "r-708",
                    "ross broiler 708",
                ],
            ),
        ]

        # Score de détection (conservé)
        best_score = 0
        detected_line = GeneticLine.UNKNOWN

        for genetic_line, patterns in ross_patterns:
            score = 0
            for pattern in patterns:
                count = content.count(pattern)
                if count > 0:
                    # Score basé sur la fréquence et la spécificité
                    pattern_score = count * len(pattern)  # Plus long = plus spécifique
                    score += pattern_score

            if score > best_score:
                best_score = score
                detected_line = genetic_line

        # Seuil minimum pour confirmer la détection (conservé)
        if best_score >= 10:  # Au moins 2 occurrences d'un pattern de 5 caractères
            self.log_extraction_progress(
                f"Lignée Ross détectée: {detected_line.value} (score: {best_score})"
            )
            return detected_line

        return GeneticLine.UNKNOWN

    def _is_ross_performance_table_text(self, table: TextTable) -> bool:
        """Vérifie si un tableau textuel contient des données de performance Ross (adapté)"""

        if not table.headers or len(table.headers) < 2:
            return False

        headers_text = " ".join(table.headers).lower()
        context_text = table.context.lower()
        combined_text = f"{headers_text} {context_text}"

        # Indicateurs de performance Ross (conservés)
        performance_indicators = [
            "age",
            "day",
            "jour",
            "weight",
            "poids",
            "bw",
            "fcr",
            "conversion",
            "feed",
            "aliment",
            "mortality",
            "mortalité",
            "livability",
        ]

        # Au moins 2 indicateurs requis
        indicators_found = sum(
            1 for indicator in performance_indicators if indicator in combined_text
        )

        # Indicateurs Ross spécifiques (bonus) (conservés)
        ross_indicators = [
            "ross",
            "308",
            "708",
            "broiler",
            "performance",
            "objectives",
            "targets",
            "standards",
        ]

        ross_found = sum(
            1 for indicator in ross_indicators if indicator in combined_text
        )

        # Critères de sélection (conservés)
        has_performance_data = indicators_found >= 2
        has_ross_context = ross_found >= 1
        has_numeric_data = any(
            any(char.isdigit() for char in cell) for row in table.rows for cell in row
        )

        return (
            has_performance_data
            and has_numeric_data
            and (has_ross_context or table.context.strip() == "")
        )

    def _extract_from_text_table(
        self, table: TextTable, json_doc: dict
    ) -> List[PerformanceRecord]:
        """Extraction spécialisée pour tableaux textuels Ross (adaptée avec logique complète)"""

        records = []

        # Analyse des en-têtes avec mappings Ross (conservée)
        metric_columns = self._analyze_ross_headers_text(table.headers)

        if not metric_columns:
            self.log_extraction_progress("Aucune métrique Ross détectée", "debug")
            return records

        # Détection de la colonne âge (conservée et adaptée)
        age_column = self._find_age_column(table.headers)

        # Traitement des lignes (logique conservée et adaptée)
        for row_idx, row in enumerate(table.rows):
            if len(row) != len(table.headers):
                continue  # Ligne incomplète

            try:
                # Extraction de l'âge (adaptée)
                age_days = self._extract_age_from_ross_row_text(
                    row, table.headers, age_column, table.context
                )

                if age_days == 0:
                    continue

                # Extraction des métriques (adaptée avec logique complète)
                row_records = self._extract_metrics_from_ross_row_text(
                    row,
                    table.headers,
                    metric_columns,
                    age_days,
                    table,
                    json_doc,
                    row_idx,
                )

                records.extend(row_records)

            except Exception as e:
                self.log_extraction_progress(
                    f"Erreur ligne {row_idx + 1}: {e}", "error"
                )
                continue

        return records

    def _analyze_ross_headers_text(self, headers: List[str]) -> Dict[int, MetricType]:
        """Analyse spécialisée des en-têtes Ross pour texte (conservée et adaptée)"""

        metric_columns = {}

        for col_idx, header in enumerate(headers):
            header_clean = header.strip().lower()

            # Recherche exacte dans les mappings Ross
            if header_clean in self.ross_metric_mappings:
                metric_type = self.ross_metric_mappings[header_clean]
                metric_columns[col_idx] = metric_type
                self.log_extraction_progress(
                    f"Métrique Ross détectée: '{header}' -> {metric_type.value}",
                    "debug",
                )
                continue

            # Recherche par patterns partiels (conservée)
            for pattern, metric_type in self.ross_metric_mappings.items():
                if self._header_matches_pattern(header_clean, pattern):
                    metric_columns[col_idx] = metric_type
                    self.log_extraction_progress(
                        f"Métrique Ross (pattern): '{header}' -> {metric_type.value}",
                        "debug",
                    )
                    break

        return metric_columns

    def _header_matches_pattern(self, header: str, pattern: str) -> bool:
        """Vérifie si un en-tête correspond à un pattern Ross (conservée)"""

        # Mots clés essentiels du pattern
        pattern_words = pattern.split()
        header_words = header.split()

        # Au moins 50% des mots du pattern doivent être présents
        matches = sum(
            1
            for word in pattern_words
            if any(word in header_word for header_word in header_words)
        )

        return matches >= len(pattern_words) * 0.5

    def _find_age_column(self, headers: List[str]) -> Optional[int]:
        """Trouve la colonne contenant l'âge (conservée)"""

        age_keywords = [
            "age",
            "day",
            "days",
            "jour",
            "jours",
            "día",
            "días",
            "week",
            "weeks",
            "semaine",
            "semanas",
        ]

        for col_idx, header in enumerate(headers):
            header_lower = header.lower()
            if any(keyword in header_lower for keyword in age_keywords):
                return col_idx

        return None

    def _extract_age_from_ross_row_text(
        self,
        row: List[str],
        headers: List[str],
        age_column: Optional[int],
        context: str,
    ) -> int:
        """Extraction spécialisée de l'âge pour Ross depuis texte (adaptée)"""

        # Méthode 1: Colonne âge explicite
        if age_column is not None and age_column < len(row):
            age_text = row[age_column].strip()
            age_match = re.search(r"(\d+)", age_text)
            if age_match:
                age = int(age_match.group(1))

                # Conversion semaines -> jours si nécessaire
                header_lower = headers[age_column].lower()
                if "week" in header_lower or "sem" in header_lower:
                    age *= 7

                if 0 <= age <= 70:  # Ross: max 70 jours typique
                    return age

        # Méthode 2: Recherche dans toute la ligne (conservée)
        for cell in row:
            if not cell.strip():
                continue

            # Patterns âge Ross
            age_patterns = [r"(\d+)\s*(?:day|jour|d|j)\b", r"(\d+)\s*(?:week|sem|w)\b"]

            for pattern in age_patterns:
                match = re.search(pattern, cell.lower())
                if match:
                    age = int(match.group(1))

                    # Conversion semaines
                    if "week" in pattern or "sem" in pattern:
                        age *= 7

                    if 0 <= age <= 70:
                        return age

        # Méthode 3: Recherche dans le contexte (conservée)
        context_age = self._extract_age_from_context(context)
        if context_age > 0:
            return context_age

        return 0

    def _extract_age_from_context(self, context: str) -> int:
        """Extrait l'âge depuis le contexte du tableau (conservée)"""

        if not context:
            return 0

        # Patterns pour âge dans le contexte
        patterns = [
            r"(\d+)\s*(?:day|jour|días|d|j)\b",
            r"at\s*(\d+)\s*(?:day|jour)",
            r"(\d+)\s*(?:week|sem|semana)\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, context.lower())
            if match:
                age = int(match.group(1))

                if "week" in pattern or "sem" in pattern:
                    age *= 7

                if 0 <= age <= 70:
                    return age

        return 0

    def _extract_metrics_from_ross_row_text(
        self,
        row: List[str],
        headers: List[str],
        metric_columns: Dict[int, MetricType],
        age_days: int,
        table: TextTable,
        json_doc: dict,
        row_idx: int,
    ) -> List[PerformanceRecord]:
        """Extraction des métriques depuis une ligne Ross textuelle (adaptée avec logique complète)"""

        records = []

        # Détecter le sexe (adapté)
        sex = self._detect_sex_from_ross_row_text(row, headers, table.context)

        # Détecter la phase d'élevage (conservée)
        phase = self._detect_ross_phase(age_days)

        # Extraire chaque métrique (logique conservée et adaptée)
        for col_idx, metric_type in metric_columns.items():
            if col_idx >= len(row):
                continue

            cell_value = row[col_idx].strip()
            if not cell_value or cell_value in ["-", "N/A", "n/a", ""]:
                continue

            try:
                # Parser la valeur numérique (adapté)
                numeric_value, unit = self._parse_numeric_value_text(cell_value)

                if numeric_value <= 0:
                    continue

                # Validation préliminaire Ross (conservée)
                if not self._is_valid_ross_value(metric_type, numeric_value, age_days):
                    self.log_extraction_progress(
                        f"Valeur Ross invalide: {metric_type.value}={numeric_value} à {age_days}j",
                        "debug",
                    )
                    continue

                # Créer l'enregistrement Ross (adapté)
                record = PerformanceRecord(
                    source_document_id=json_doc.get("source_file", "unknown"),
                    genetic_line=self.genetic_line,
                    age_days=age_days,
                    sex=sex,
                    phase=phase,
                    metric_type=metric_type,
                    value_original=numeric_value,
                    unit_original=unit,
                    table_context=table.context,
                    column_header=headers[col_idx],
                    row_context=f"Ross Row {row_idx + 1}: Age {age_days}d",
                )

                # Normalisation et calcul confiance (conservé)
                record.normalize_unit()
                record.extraction_confidence = self._calculate_ross_confidence(
                    record, table, headers[col_idx], age_days
                )

                records.append(record)

            except Exception as e:
                self.log_extraction_progress(
                    f"Erreur métrique Ross [{row_idx}, {col_idx}]: {e}", "error"
                )
                continue

        return records

    def _parse_numeric_value_text(self, cell_value: str) -> Tuple[float, str]:
        """Parse une valeur numérique depuis le texte (nouvelle méthode)"""

        # Nettoyer la valeur
        clean_value = cell_value.strip()

        # Extraire le nombre
        numeric_match = re.search(r"(\d+\.?\d*)", clean_value)
        if not numeric_match:
            return 0.0, "unknown"

        numeric_value = float(numeric_match.group(1))

        # Détecter l'unité
        unit = "unknown"
        if "kg" in clean_value.lower():
            unit = "kg"
        elif "lb" in clean_value.lower():
            unit = "lb"
        elif "g" in clean_value.lower():
            unit = "g"
        elif "%" in clean_value:
            unit = "%"
        elif "." in numeric_match.group(1) and numeric_value < 10:
            unit = "ratio"  # Probable FCR

        return numeric_value, unit

    def _detect_sex_from_ross_row_text(
        self, row: List[str], headers: List[str], context: str
    ) -> Sex:
        """Détection du sexe spécifique Ross depuis texte (adaptée)"""

        # Recherche dans les en-têtes et cellules
        for header, cell in zip(headers, row):
            combined = f"{header} {cell}".lower()

            # Patterns Ross spécifiques (conservés)
            if any(term in combined for term in ["male", "mâle", "cock", "coq"]):
                return Sex.MALE
            elif any(
                term in combined for term in ["female", "femelle", "hen", "poule"]
            ):
                return Sex.FEMALE
            elif any(
                term in combined
                for term in ["mixed", "mixte", "as hatched", "straight run"]
            ):
                return Sex.MIXED

        # Recherche dans le contexte (conservée)
        context_lower = context.lower()
        if any(term in context_lower for term in ["male", "mâle", "cock"]):
            return Sex.MALE
        elif any(term in context_lower for term in ["female", "femelle", "hen"]):
            return Sex.FEMALE
        elif any(term in context_lower for term in ["mixed", "mixte", "as hatched"]):
            return Sex.MIXED

        return Sex.MIXED  # Par défaut pour données mixtes

    def _detect_ross_phase(self, age_days: int) -> Phase:
        """Détection de la phase d'élevage Ross (conservée)"""

        # Phases standards Ross 308/708
        if age_days <= 10:
            return Phase.STARTER
        elif age_days <= 22:
            return Phase.GROWER
        elif age_days <= 35:
            return Phase.FINISHER
        elif age_days <= 70:
            return Phase.WHOLE_CYCLE
        else:
            return Phase.UNKNOWN

    def _is_valid_ross_value(
        self, metric_type: MetricType, value: float, age_days: int
    ) -> bool:
        """Validation spécifique Ross des valeurs (conservée intégralement)"""

        if metric_type not in self.ross_validation_thresholds:
            return value > 0  # Validation générique

        thresholds = self.ross_validation_thresholds[metric_type]

        # Validation de base
        if value < thresholds["min"] or value > thresholds["max"]:
            return False

        # Validations spécifiques par métrique (conservées)
        if metric_type == MetricType.WEIGHT_G:
            # Courbe de croissance Ross approximative
            expected_weight = self._estimate_ross_weight(age_days)
            tolerance = 0.6  # ±60% tolérance

            return (
                (expected_weight * (1 - tolerance))
                <= value
                <= (expected_weight * (1 + tolerance))
            )

        elif metric_type == MetricType.FCR:
            # FCR Ross selon l'âge
            if age_days <= 7:
                return 0.8 <= value <= 1.5
            elif age_days <= 21:
                return 1.0 <= value <= 1.8
            elif age_days <= 35:
                return 1.3 <= value <= 2.2
            else:
                return 1.4 <= value <= 2.5

        elif metric_type == MetricType.MORTALITY_RATE:
            # Mortalité cumulative acceptable Ross
            max_mortality_by_age = min(15, age_days * 0.15)  # Max 0.15% par jour
            return value <= max_mortality_by_age

        return True

    def _estimate_ross_weight(self, age_days: int) -> float:
        """Estimation du poids Ross selon l'âge (conservée intégralement)"""

        # Courbe de croissance Ross 308 mâle (approximation)
        if age_days <= 0:
            return 40  # Poids poussin
        elif age_days <= 7:
            return 40 + (age_days * 20)  # ~180g à 7j
        elif age_days <= 14:
            return 180 + ((age_days - 7) * 40)  # ~460g à 14j
        elif age_days <= 21:
            return 460 + ((age_days - 14) * 55)  # ~845g à 21j
        elif age_days <= 28:
            return 845 + ((age_days - 21) * 70)  # ~1335g à 28j
        elif age_days <= 35:
            return 1335 + ((age_days - 28) * 80)  # ~1895g à 35j
        elif age_days <= 42:
            return 1895 + ((age_days - 35) * 85)  # ~2490g à 42j
        else:
            return 2490 + ((age_days - 42) * 70)  # Croissance ralentie

    def _calculate_ross_confidence(
        self, record: PerformanceRecord, table: TextTable, header: str, age_days: int
    ) -> float:
        """Calcul de confiance spécifique Ross (conservé et adapté)"""

        confidence = 1.0

        # Bonus pour les en-têtes Ross explicites (conservé)
        header_lower = header.lower()
        if any(term in header_lower for term in ["ross", "308", "708"]):
            confidence += 0.1

        # Bonus pour valeurs dans les plages optimales Ross (conservé)
        if record.metric_type == MetricType.FCR:
            optimal_min, optimal_max = self.ross_validation_thresholds[MetricType.FCR][
                "optimal_range"
            ]
            if optimal_min <= record.value_canonical <= optimal_max:
                confidence += 0.1

        # Bonus pour âges standards Ross (conservé)
        if age_days in [7, 14, 21, 28, 35, 42]:  # Âges de mesure standards
            confidence += 0.05

        # Malus pour contexte peu clair (adapté)
        if not table.context or len(table.context) < 20:
            confidence -= 0.1

        # Malus si valeur à la limite de validité (conservé)
        if not self._is_plausible_value(record):
            confidence -= 0.2

        return max(0.2, min(1.0, confidence))

    def _is_plausible_value(self, record: PerformanceRecord) -> bool:
        """Vérifie la plausibilité biologique d'une valeur (nouvelle méthode)"""

        # Validation basique selon le type de métrique
        if record.metric_type == MetricType.WEIGHT_G:
            return 30 <= record.value_canonical <= 5000
        elif record.metric_type == MetricType.FCR:
            return 0.5 <= record.value_canonical <= 4.0
        elif record.metric_type == MetricType.MORTALITY_RATE:
            return 0 <= record.value_canonical <= 20

        return record.value_canonical > 0

    def _post_process_ross_records(
        self, records: List[PerformanceRecord], table_idx: int
    ) -> List[PerformanceRecord]:
        """Post-traitement spécifique Ross (conservé intégralement)"""

        validated_records = []

        for record in records:
            # Validation finale Ross
            if self._final_validate_ross_record(record):
                validated_records.append(record)
            else:
                self.log_extraction_progress(
                    f"Enregistrement Ross rejeté: {record.metric_type.value}={record.value_canonical} "
                    f"à {record.age_days}j",
                    "debug",
                )

        # Détection des doublons par âge/métrique (conservée)
        validated_records = self._remove_ross_duplicates(validated_records)

        return validated_records

    def _final_validate_ross_record(self, record: PerformanceRecord) -> bool:
        """Validation finale spécifique Ross (conservée)"""

        # Validation héritée
        if not hasattr(record, "validation_passed") or not record.validation_passed:
            # Validation basique si pas d'attribut validation_passed
            if not self._is_plausible_value(record):
                return False

        # Seuil de confiance Ross
        if record.extraction_confidence < 0.3:
            return False

        # Validation cohérence lignée
        if record.genetic_line not in self.get_supported_genetic_lines():
            return False

        # Validation plausibilité biologique
        if not self._is_plausible_value(record):
            return False

        return True

    def _remove_ross_duplicates(
        self, records: List[PerformanceRecord]
    ) -> List[PerformanceRecord]:
        """Suppression des doublons pour Ross (conservée intégralement)"""

        # Grouper par âge + métrique
        groups = {}
        for record in records:
            key = (record.age_days, record.metric_type, record.sex)
            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        # Garder le meilleur de chaque groupe
        final_records = []
        for group in groups.values():
            if len(group) == 1:
                final_records.append(group[0])
            else:
                # Garder celui avec la meilleure confiance
                best_record = max(group, key=lambda r: r.extraction_confidence)
                final_records.append(best_record)

        return final_records

    def _final_validation_ross(
        self, records: List[PerformanceRecord]
    ) -> List[PerformanceRecord]:
        """Validation finale du lot d'enregistrements Ross (conservée intégralement)"""

        if not records:
            return records

        # Vérifier la cohérence du lot
        genetic_lines = set(r.genetic_line for r in records)
        if len(genetic_lines) > 1:
            self.log_extraction_progress(
                f"Incohérence détectée: plusieurs lignées dans le lot: {genetic_lines}",
                "warning",
            )

        # Statistiques finales
        metrics_count = {}
        for record in records:
            metric = record.metric_type
            if metric not in metrics_count:
                metrics_count[metric] = 0
            metrics_count[metric] += 1

        self.log_extraction_progress(f"Résumé extraction Ross: {dict(metrics_count)}")

        return records

    def log_extraction_progress(self, message: str, level: str = "info"):
        """Log des progrès d'extraction (conservé)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level.upper()}] RossExtractor: {message}")
