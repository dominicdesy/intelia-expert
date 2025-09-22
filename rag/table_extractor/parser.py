#!/usr/bin/env python3
"""
Parser Markdown robuste pour tableaux - VERSION CORRIGÉE
Ajout du décomposeur de ranges et normalisation pivot
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
from enum import Enum

from metadata import MetadataNormalizer, TableMetadata

# ============================================================================
# AJOUT CRITIQUE 1: DÉCOMPOSEUR DE RANGES
# ============================================================================

class RangeType(Enum):
    """Types de ranges détectés"""
    NUMERIC_RANGE = "numeric_range"      # "3-5"
    EXACT_VALUE = "exact_value"          # "5"
    TEMPORAL_RANGE = "temporal_range"    # "0-10 days"
    PERCENTAGE_RANGE = "percentage_range" # "85-90%"
    OPEN_ENDED = "open_ended"            # "> 267"
    CONTEXTUAL_TEXT = "contextual_text"  # "Based on production"

@dataclass
class DecomposedRange:
    """Range décomposé pour extraction optimisée"""
    original_value: str
    range_type: RangeType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    exact_value: Optional[float] = None
    unit: Optional[str] = None
    confidence: float = 1.0

class RangeDecomposer:
    """Décomposeur universel de ranges"""
    
    def __init__(self):
        self.numeric_range_pattern = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$")
        self.exact_value_pattern = re.compile(r"^(\d+(?:\.\d+)?)$")
        self.percentage_range_pattern = re.compile(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)%$")
        self.temporal_pattern = re.compile(r"^(\d+)-(\d+)\s*(days?|weeks?|months?)$")
        self.open_ended_pattern = re.compile(r"^>\s*(\d+)$")
    
    def decompose_range(self, value: str, column_context: str = "") -> DecomposedRange:
        """Décompose un range selon son type et contexte"""
        if not value or value.strip() == "":
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.CONTEXTUAL_TEXT,
                confidence=0.0
            )
        
        value = str(value).strip()
        
        # 1. Range numérique simple : "3-5"
        numeric_match = self.numeric_range_pattern.match(value)
        if numeric_match:
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.NUMERIC_RANGE,
                min_value=float(numeric_match.group(1)),
                max_value=float(numeric_match.group(2)),
                unit=self._extract_unit_from_context(column_context),
                confidence=1.0
            )
        
        # 2. Valeur exacte : "5"
        exact_match = self.exact_value_pattern.match(value)
        if exact_match:
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.EXACT_VALUE,
                exact_value=float(exact_match.group(1)),
                unit=self._extract_unit_from_context(column_context),
                confidence=1.0
            )
        
        # 3. Range pourcentage : "85-90%"
        percentage_match = self.percentage_range_pattern.match(value)
        if percentage_match:
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.PERCENTAGE_RANGE,
                min_value=float(percentage_match.group(1)),
                max_value=float(percentage_match.group(2)),
                unit="percentage",
                confidence=1.0
            )
        
        # 4. Range temporel : "0-10 days"
        temporal_match = self.temporal_pattern.match(value.lower())
        if temporal_match:
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.TEMPORAL_RANGE,
                min_value=float(temporal_match.group(1)),
                max_value=float(temporal_match.group(2)),
                unit=temporal_match.group(3),
                confidence=1.0
            )
        
        # 5. Range ouvert : "> 267"
        open_match = self.open_ended_pattern.match(value)
        if open_match:
            return DecomposedRange(
                original_value=value,
                range_type=RangeType.OPEN_ENDED,
                min_value=float(open_match.group(1)),
                unit="days",
                confidence=0.9
            )
        
        # 6. Fallback - texte contextuel
        return DecomposedRange(
            original_value=value,
            range_type=RangeType.CONTEXTUAL_TEXT,
            confidence=0.3
        )
    
    def _extract_unit_from_context(self, column_context: str) -> Optional[str]:
        """Extrait l'unité du contexte de la colonne"""
        if not column_context:
            return None
        
        unit_patterns = {
            r"\(g\)": "g",
            r"\(kg\)": "kg", 
            r"\(lb\)": "lb",
            r"\(%\)": "percentage",
            r"days": "days",
            r"weeks": "weeks"
        }
        
        for pattern, unit in unit_patterns.items():
            if re.search(pattern, column_context, re.IGNORECASE):
                return unit
        
        return None

# ============================================================================
# AJOUT CRITIQUE 2: DÉTECTEUR DE TABLES PIVOT
# ============================================================================

class PivotDetector:
    """Détecteur de structures pivot multi-dimensionnelles"""
    
    def __init__(self):
        self.phase_indicators = ["starter", "grower", "developer", "finisher"]
        self.age_range_pattern = r"\d+-\d+"
    
    def is_pivot_table(self, headers: List[str]) -> bool:
        """Détermine si un tableau est une structure pivot"""
        headers_lower = [h.lower() for h in headers]
        
        pivot_score = 0
        for header in headers_lower:
            # Phases d'alimentation
            if any(phase in header for phase in self.phase_indicators):
                pivot_score += 2
            # Ranges d'âge
            if re.search(self.age_range_pattern, header):
                pivot_score += 1
            # Indicateurs sexe
            if any(word in header for word in ["male", "female", "mixed"]):
                pivot_score += 1
        
        return pivot_score >= 3
    
    def identify_pivot_columns(self, headers: List[str]) -> Tuple[List[str], List[str]]:
        """Identifie les colonnes de dimension vs valeur dans un pivot"""
        dimension_cols = []
        value_cols = []
        
        for header in headers:
            header_lower = header.lower()
            
            # Colonnes de dimension (descriptives)
            if any(dim in header_lower for dim in ["nutrient", "unit", "protein", "energy"]):
                dimension_cols.append(header)
            # Colonnes de valeur (phases/âges)
            elif any(phase in header_lower for phase in self.phase_indicators):
                value_cols.append(header)
            elif re.search(self.age_range_pattern, header):
                value_cols.append(header)
            else:
                # Par défaut, considérer comme dimension
                dimension_cols.append(header)
        
        return dimension_cols, value_cols

# ============================================================================
# AJOUT CRITIQUE 3: PROCESSEUR DE DONNÉES AVANCÉ
# ============================================================================

@dataclass
class ProcessedTableData:
    """Données de table traitées avec décomposition"""
    title: str
    headers: List[str]
    raw_rows: List[List[str]]
    processed_records: List[Dict[str, Any]]
    metadata: TableMetadata
    is_pivot: bool = False

class AdvancedDataProcessor:
    """Processeur avancé pour normalisation des données"""
    
    def __init__(self):
        self.range_decomposer = RangeDecomposer()
        self.pivot_detector = PivotDetector()
        self.logger = logging.getLogger(__name__)
    
    def process_table_data(self, table_data, metadata: TableMetadata) -> ProcessedTableData:
        """Traite les données d'un tableau avec décomposition avancée"""
        
        # Détection pivot
        is_pivot = self.pivot_detector.is_pivot_table(table_data.headers)
        
        if is_pivot:
            processed_records = self._process_pivot_table(table_data)
        else:
            processed_records = self._process_standard_table(table_data)
        
        return ProcessedTableData(
            title=table_data.title,
            headers=table_data.headers,
            raw_rows=table_data.rows,
            processed_records=processed_records,
            metadata=metadata,
            is_pivot=is_pivot
        )
    
    def _process_pivot_table(self, table_data) -> List[Dict[str, Any]]:
        """Traite une table pivot en enregistrements individuels"""
        records = []
        
        dimension_cols, value_cols = self.pivot_detector.identify_pivot_columns(table_data.headers)
        
        for row in table_data.rows:
            # Extraire les dimensions communes
            base_record = {}
            for i, col in enumerate(dimension_cols):
                if i < len(row):
                    base_record[self._clean_column_name(col)] = row[i]
            
            # Créer un enregistrement par colonne de valeur
            for i, value_col in enumerate(value_cols):
                value_idx = len(dimension_cols) + i
                if value_idx < len(row) and row[value_idx]:
                    record = base_record.copy()
                    
                    # Extraire info de phase du header
                    phase_info = self._extract_phase_info(value_col)
                    record.update(phase_info)
                    
                    # Décomposer la valeur
                    value_decomposed = self.range_decomposer.decompose_range(
                        str(row[value_idx]), value_col
                    )
                    record.update(self._range_to_dict(value_decomposed, "value"))
                    
                    records.append(record)
        
        return records
    
    def _process_standard_table(self, table_data) -> List[Dict[str, Any]]:
        """Traite une table standard avec décomposition des ranges"""
        records = []
        
        for row in table_data.rows:
            record = {}
            for i, header in enumerate(table_data.headers):
                if i < len(row):
                    value = row[i]
                    clean_header = self._clean_column_name(header)
                    
                    # Décomposer les ranges dans toutes les colonnes
                    if self._contains_range(str(value)):
                        decomposed = self.range_decomposer.decompose_range(str(value), header)
                        record.update(self._range_to_dict(decomposed, clean_header))
                    else:
                        record[clean_header] = value
            
            records.append(record)
        
        return records
    
    def _extract_phase_info(self, column_header: str) -> Dict[str, Any]:
        """Extrait les informations de phase depuis un header"""
        phase_info = {}
        header_lower = column_header.lower()
        
        # Nom de phase
        if "starter" in header_lower:
            phase_info["phase_name"] = "starter"
        elif "grower" in header_lower:
            phase_info["phase_name"] = "grower"
        elif "finisher" in header_lower:
            phase_info["phase_name"] = "finisher"
        else:
            phase_info["phase_name"] = "unknown"
        
        # Range d'âge
        age_range_match = re.search(r"(\d+)-(\d+)", column_header)
        if age_range_match:
            phase_info["age_min_days"] = int(age_range_match.group(1))
            phase_info["age_max_days"] = int(age_range_match.group(2))
        
        return phase_info
    
    def _contains_range(self, value: str) -> bool:
        """Détermine si une valeur contient un range à décomposer"""
        return ("-" in value and re.search(r"\d+-\d+", value)) or ">" in value
    
    def _range_to_dict(self, decomposed: DecomposedRange, prefix: str) -> Dict[str, Any]:
        """Convertit un range décomposé en dictionnaire"""
        result = {
            f"{prefix}_original": decomposed.original_value,
            f"{prefix}_type": decomposed.range_type.value,
            f"{prefix}_confidence": decomposed.confidence
        }
        
        if decomposed.min_value is not None:
            result[f"{prefix}_min"] = decomposed.min_value
        if decomposed.max_value is not None:
            result[f"{prefix}_max"] = decomposed.max_value
        if decomposed.exact_value is not None:
            result[f"{prefix}_value"] = decomposed.exact_value
        if decomposed.unit:
            result[f"{prefix}_unit"] = decomposed.unit
        
        return result
    
    def _clean_column_name(self, header: str) -> str:
        """Nettoie un nom de colonne pour utilisation comme clé"""
        clean = header.lower().strip()
        clean = re.sub(r"\s+", "_", clean)
        clean = re.sub(r"[^\w_]", "", clean)
        clean = re.sub(r"_+", "_", clean)
        clean = clean.strip("_")
        return clean if clean else "unknown"

# ============================================================================
# MODIFICATION DU PARSER PRINCIPAL
# ============================================================================

@dataclass
class TableData:
    """Structure simple pour un tableau extrait"""
    title: str
    headers: List[str]
    rows: List[List[str]]
    metadata: TableMetadata

class MarkdownTableParser:
    """Parser Markdown robuste et simple - VERSION AMÉLIORÉE"""

    def __init__(self, metadata_normalizer: MetadataNormalizer):
        self.logger = logging.getLogger(__name__)
        self.normalizer = metadata_normalizer
        # AJOUT CRITIQUE: Processeur avancé
        self.data_processor = AdvancedDataProcessor()

    def extract_tables_from_text(self, text: str, source_file: str) -> List[ProcessedTableData]:
        """Extrait tous les tableaux d'un texte Markdown avec traitement avancé"""
        raw_tables = []
        lines = text.split("\n")

        i = 0
        while i < len(lines):
            if self._is_table_line(lines[i]):
                table_data, end_index = self._extract_single_table(
                    lines, i, source_file, text
                )
                if table_data:
                    raw_tables.append(table_data)
                i = end_index
            else:
                i += 1

        # TRAITEMENT AVANCÉ des tables extraites
        processed_tables = []
        for table_data in raw_tables:
            try:
                processed = self.data_processor.process_table_data(table_data, table_data.metadata)
                processed_tables.append(processed)
            except Exception as e:
                self.logger.error(f"Erreur traitement table '{table_data.title}': {e}")
                continue

        self.logger.info(
            f"Extracted {len(processed_tables)} tables from {Path(source_file).name}"
        )
        return processed_tables

    def _is_table_line(self, line: str) -> bool:
        """Détecte si une ligne fait partie d'un tableau Markdown"""
        line = line.strip()
        return line.startswith("|") and line.endswith("|") and line.count("|") >= 3

    def _extract_single_table(
        self, lines: List[str], start_index: int, source_file: str, full_text: str
    ) -> Tuple[Optional[TableData], int]:
        """Extrait un seul tableau à partir de l'index donné"""
        # Trouver le titre du tableau
        title = self._find_table_title(lines, start_index)

        # Extraire toutes les lignes du tableau
        table_lines = []
        i = start_index

        while i < len(lines) and self._is_table_line(lines[i]):
            table_lines.append(lines[i].strip())
            i += 1

        if len(table_lines) < 2:
            return None, i

        # Parser le tableau
        headers, rows = self._parse_table_content(table_lines)

        if not headers or len(rows) == 0:
            return None, i

        # Créer les métadonnées normalisées
        metadata = self.normalizer.create_metadata(
            title, full_text[:1000], source_file, headers
        )

        # Créer l'objet TableData
        table_data = TableData(
            title=title, headers=headers, rows=rows, metadata=metadata
        )

        return table_data, i

    # Le reste des méthodes (_find_table_title, _parse_table_content, etc.) 
    # reste identique à la version originale...
    
    def _find_table_title(self, lines: List[str], table_start: int) -> str:
        """Trouve le titre du tableau en regardant les lignes précédentes"""
        for i in range(table_start - 1, max(0, table_start - 6), -1):
            line = lines[i].strip()

            if not line:
                continue

            # Titre de section (## ou ###)
            if line.startswith("#"):
                return re.sub(r"^#+\s*", "", line).strip()

            # Ligne qui pourrait être un titre
            if (
                len(line) < 100
                and not self._is_table_line(line)
                and not line.startswith("!")
                and not line.startswith("*")
            ):
                return line.strip()

        return "Table"

    def _parse_table_content(
        self, table_lines: List[str]
    ) -> Tuple[List[str], List[List[str]]]:
        """Parse le contenu du tableau Markdown - LOGIQUE AMÉLIORÉE"""
        if len(table_lines) < 2:
            return [], []

        # Parser la ligne d'en-tête
        raw_headers = self._parse_table_row(table_lines[0])

        if not raw_headers:
            return [], []

        # Nettoyer et simplifier les headers - AMÉLIORATION
        headers = self._clean_headers_advanced(raw_headers)

        # Parser les lignes de données (ignorer la ligne de séparation)
        rows = []
        for line in table_lines[2:]:  # Skip header et separator
            if line.strip():
                row = self._parse_table_row(line)
                if row and len(row) >= len(headers):
                    # Prendre seulement les colonnes utiles
                    clean_row = row[: len(headers)]
                    rows.append(clean_row)

        return headers, rows

    def _parse_table_row(self, line: str) -> List[str]:
        """Parse une ligne individuelle de tableau"""
        line = line.strip()

        # Enlever les | de début et fin
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        # Séparer par | et nettoyer chaque cellule
        cells = []
        for cell in line.split("|"):
            cell = cell.strip()
            # Enlever le formatage Markdown de base
            cell = re.sub(r"[*_`]", "", cell)
            # Nettoyer les caractères d'échappement
            cell = cell.replace("\\", "")
            cells.append(cell)

        return cells

    def _clean_headers_advanced(self, raw_headers: List[str]) -> List[str]:
        """Nettoie et simplifie les headers - VERSION AMÉLIORÉE"""
        
        # Détection spéciale pour Table 1 (ratios acides aminés)
        if (
            len(raw_headers) >= 7
            and "Table" in raw_headers[0]
            and any("Age Fed" in str(header) for header in raw_headers)
        ):
            return self._process_amino_acid_table_headers(raw_headers)
        
        # Détection pour tables de performance
        if any("Weight" in str(h) for h in raw_headers) and any("FCR" in str(h) for h in raw_headers):
            return self._process_performance_table_headers(raw_headers)
        
        # Cas général - nettoyer les headers existants
        return self._clean_headers_generic(raw_headers)
    
    def _process_amino_acid_table_headers(self, raw_headers: List[str]) -> List[str]:
        """Traite spécifiquement les headers de table d'acides aminés"""
        headers = ["amino_acid", "unit"]
        
        for header in raw_headers[2:]:  # Skip "Table 1" et description
            if "Age Fed" in header or "days" in header:
                age_match = re.search(r"(\d+)-?(\d*)", header)
                if age_match:
                    start = age_match.group(1)
                    end = age_match.group(2) if age_match.group(2) else start
                    if ">" in header:
                        headers.append(f"age_over_{start}")
                    else:
                        headers.append(f"age_{start}_{end}")
                else:
                    clean = re.sub(r"[^\w]", "_", header.lower())
                    headers.append(clean)
        
        return headers
    
    def _process_performance_table_headers(self, raw_headers: List[str]) -> List[str]:
        """Traite spécifiquement les headers de performance"""
        mapping = {
            "Day": "age_days",
            "Weight (g)": "weight_g", 
            "Daily Gain (g)": "daily_gain_g",
            "Av. Daily Gain (g)": "avg_daily_gain_g",
            "Daily Intake (g)": "daily_intake_g",
            "Cum. Intake (g)": "cumulative_intake_g",
            "FCR": "fcr"
        }
        
        headers = []
        for header in raw_headers:
            clean_header = mapping.get(header, self._clean_single_header(header))
            headers.append(clean_header)
        
        return headers
    
    def _clean_headers_generic(self, raw_headers: List[str]) -> List[str]:
        """Nettoyage générique des headers"""
        clean_headers = []
        for header in raw_headers:
            if not header.strip():
                continue
            clean = self._clean_single_header(header)
            if clean:
                clean_headers.append(clean)
        return clean_headers
    
    def _clean_single_header(self, header: str) -> str:
        """Nettoie un header individuel"""
        clean = header.lower().strip()
        clean = re.sub(r"\s+", "_", clean)
        clean = re.sub(r"[^\w_]", "", clean)
        clean = re.sub(r"_+", "_", clean)
        clean = clean.strip("_")
        return clean