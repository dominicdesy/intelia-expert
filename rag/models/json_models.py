# -*- coding: utf-8 -*-

"""

rag/models/json_models.py - Modèles pour les données JSON avicoles
Version 1.0 - Structures de données pour l'ingestion et la validation

"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

from .enums import GeneticLine, MetricType, DocumentType, ExtractionStatus


@dataclass
class JSONMetadata:
    """Métadonnées enrichies pour les documents JSON"""

    # Métadonnées de base
    genetic_line: GeneticLine = GeneticLine.UNKNOWN
    document_type: DocumentType = DocumentType.UNKNOWN
    language: str = "fr"
    region: str = "global"

    # Informations temporelles
    effective_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    # Source et qualité
    source: str = "unknown"
    version: str = "1.0"
    quality_score: float = 1.0

    # Flags d'enrichissement automatique
    auto_detected_genetic_line: bool = False
    auto_detected_document_type: bool = False
    auto_detected_language: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour stockage"""
        return {
            "genetic_line": self.genetic_line.value,
            "document_type": self.document_type.value,
            "language": self.language,
            "region": self.region,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "source": self.source,
            "version": self.version,
            "quality_score": self.quality_score,
            "auto_detected_genetic_line": self.auto_detected_genetic_line,
            "auto_detected_document_type": self.auto_detected_document_type,
            "auto_detected_language": self.auto_detected_language,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONMetadata":
        """Création depuis un dictionnaire"""
        return cls(
            genetic_line=GeneticLine(data.get("genetic_line", "unknown")),
            document_type=DocumentType(data.get("document_type", "unknown")),
            language=data.get("language", "fr"),
            region=data.get("region", "global"),
            effective_date=(
                datetime.fromisoformat(data["effective_date"])
                if data.get("effective_date")
                else None
            ),
            last_updated=(
                datetime.fromisoformat(data["last_updated"])
                if data.get("last_updated")
                else None
            ),
            source=data.get("source", "unknown"),
            version=data.get("version", "1.0"),
            quality_score=data.get("quality_score", 1.0),
            auto_detected_genetic_line=data.get("auto_detected_genetic_line", False),
            auto_detected_document_type=data.get("auto_detected_document_type", False),
            auto_detected_language=data.get("auto_detected_language", False),
        )


@dataclass
class JSONTable:
    """Structure pour les tableaux dans les documents JSON"""

    # Structure du tableau
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)

    # Métadonnées contextuelles
    context: str = ""
    title: str = ""

    # Informations de traitement
    has_performance_data: bool = False
    detected_metrics: List[MetricType] = field(default_factory=list)
    extraction_confidence: float = 1.0

    def __post_init__(self):
        """Validation post-initialisation"""
        if self.rows and self.headers:
            # Vérifier cohérence headers/rows
            expected_cols = len(self.headers)
            for i, row in enumerate(self.rows):
                if len(row) != expected_cols:
                    # Padding ou truncation si nécessaire
                    if len(row) < expected_cols:
                        self.rows[i] = row + [""] * (expected_cols - len(row))
                    else:
                        self.rows[i] = row[:expected_cols]

    @property
    def shape(self) -> tuple:
        """Dimensions du tableau (lignes, colonnes)"""
        return (len(self.rows), len(self.headers))

    @property
    def is_valid(self) -> bool:
        """Vérifie si le tableau est valide"""
        return (
            bool(self.headers)
            and bool(self.rows)
            and all(len(row) == len(self.headers) for row in self.rows)
        )

    def get_column(self, header: str) -> List[str]:
        """Récupère une colonne par son nom"""
        try:
            index = self.headers.index(header)
            return [row[index] for row in self.rows]
        except ValueError:
            return []

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "headers": self.headers,
            "rows": self.rows,
            "context": self.context,
            "title": self.title,
            "has_performance_data": self.has_performance_data,
            "detected_metrics": [m.value for m in self.detected_metrics],
            "extraction_confidence": self.extraction_confidence,
            "shape": self.shape,
            "is_valid": self.is_valid,
        }


@dataclass
class JSONFigure:
    """Structure pour les figures/images dans les documents JSON"""

    # Informations de base
    title: str = ""
    caption: str = ""
    alt_text: str = ""

    # Localisation
    url: Optional[str] = None
    path: Optional[str] = None

    # Métadonnées
    figure_type: str = "chart"  # chart, table, diagram, photo
    has_data: bool = False
    extracted_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        return {
            "title": self.title,
            "caption": self.caption,
            "alt_text": self.alt_text,
            "url": self.url,
            "path": self.path,
            "figure_type": self.figure_type,
            "has_data": self.has_data,
            "extracted_data": self.extracted_data,
        }


@dataclass
class JSONDocument:
    """Structure principale pour un document JSON avicole"""

    # Contenu principal
    title: str = ""
    text: str = ""

    # Structures données
    metadata: JSONMetadata = field(default_factory=JSONMetadata)
    tables: List[JSONTable] = field(default_factory=list)
    figures: List[JSONFigure] = field(default_factory=list)

    # Informations de traitement
    content_hash: str = ""
    file_size_bytes: int = 0
    processing_timestamp: datetime = field(default_factory=datetime.now)
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING

    # Statistiques
    tables_count: int = 0
    figures_count: int = 0
    performance_records_extracted: int = 0

    def __post_init__(self):
        """Mise à jour automatique des compteurs"""
        self.tables_count = len(self.tables)
        self.figures_count = len(self.figures)

    @property
    def has_performance_data(self) -> bool:
        """Indique si le document contient des données de performance"""
        return any(table.has_performance_data for table in self.tables)

    @property
    def detected_metrics(self) -> List[MetricType]:
        """Liste toutes les métriques détectées dans le document"""
        all_metrics = []
        for table in self.tables:
            all_metrics.extend(table.detected_metrics)
        return list(set(all_metrics))  # Éliminer doublons

    @property
    def avg_extraction_confidence(self) -> float:
        """Confiance moyenne d'extraction pour les tableaux"""
        if not self.tables:
            return 1.0
        confidences = [t.extraction_confidence for t in self.tables]
        return sum(confidences) / len(confidences)

    def add_table(self, table: JSONTable) -> None:
        """Ajoute un tableau et met à jour les compteurs"""
        self.tables.append(table)
        self.tables_count = len(self.tables)

    def add_figure(self, figure: JSONFigure) -> None:
        """Ajoute une figure et met à jour les compteurs"""
        self.figures.append(figure)
        self.figures_count = len(self.figures)

    def to_dict(self) -> Dict[str, Any]:
        """Conversion complète en dictionnaire"""
        return {
            "title": self.title,
            "text": self.text,
            "metadata": self.metadata.to_dict(),
            "tables": [table.to_dict() for table in self.tables],
            "figures": [figure.to_dict() for figure in self.figures],
            "content_hash": self.content_hash,
            "file_size_bytes": self.file_size_bytes,
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "extraction_status": self.extraction_status.value,
            "tables_count": self.tables_count,
            "figures_count": self.figures_count,
            "performance_records_extracted": self.performance_records_extracted,
            "has_performance_data": self.has_performance_data,
            "detected_metrics": [m.value for m in self.detected_metrics],
            "avg_extraction_confidence": self.avg_extraction_confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONDocument":
        """Création depuis un dictionnaire JSON"""
        doc = cls(
            title=data.get("title", ""),
            text=data.get("text", ""),
            content_hash=data.get("content_hash", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            processing_timestamp=datetime.fromisoformat(
                data.get("processing_timestamp", datetime.now().isoformat())
            ),
            extraction_status=ExtractionStatus(
                data.get("extraction_status", "pending")
            ),
            performance_records_extracted=data.get("performance_records_extracted", 0),
        )

        # Reconstruire métadonnées
        if "metadata" in data:
            doc.metadata = JSONMetadata.from_dict(data["metadata"])

        # Reconstruire tableaux
        for table_data in data.get("tables", []):
            table = JSONTable(
                headers=table_data.get("headers", []),
                rows=table_data.get("rows", []),
                context=table_data.get("context", ""),
                title=table_data.get("title", ""),
                has_performance_data=table_data.get("has_performance_data", False),
                detected_metrics=[
                    MetricType(m) for m in table_data.get("detected_metrics", [])
                ],
                extraction_confidence=table_data.get("extraction_confidence", 1.0),
            )
            doc.add_table(table)

        # Reconstruire figures
        for figure_data in data.get("figures", []):
            figure = JSONFigure(
                title=figure_data.get("title", ""),
                caption=figure_data.get("caption", ""),
                alt_text=figure_data.get("alt_text", ""),
                url=figure_data.get("url"),
                path=figure_data.get("path"),
                figure_type=figure_data.get("figure_type", "chart"),
                has_data=figure_data.get("has_data", False),
                extracted_data=figure_data.get("extracted_data", {}),
            )
            doc.add_figure(figure)

        return doc

    @classmethod
    def from_json_string(cls, json_str: str) -> "JSONDocument":
        """Création depuis une chaîne JSON"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_json_string(self, indent: int = 2) -> str:
        """Sérialisation en JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def validate(self) -> List[str]:
        """Validation du document et retour des erreurs"""
        errors = []

        # Validation de base
        if not self.title.strip():
            errors.append("Le titre est requis")

        if not self.text.strip():
            errors.append("Le contenu textuel est requis")

        if len(self.title) < 5:
            errors.append("Le titre doit contenir au moins 5 caractères")

        if len(self.text) < 50:
            errors.append("Le contenu doit contenir au moins 50 caractères")

        # Validation des tableaux
        for i, table in enumerate(self.tables):
            if not table.is_valid:
                errors.append(f"Tableau {i+1} invalide: structure incohérente")

        # Validation des métadonnées
        if self.metadata.genetic_line == GeneticLine.UNKNOWN:
            errors.append("La lignée génétique doit être spécifiée")

        if self.metadata.quality_score < 0 or self.metadata.quality_score > 1:
            errors.append("Le score de qualité doit être entre 0 et 1")

        return errors


@dataclass
class ProcessingResult:
    """Résultat du traitement d'un document JSON"""

    document: JSONDocument
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0

    # Statistiques détaillées
    tables_processed: int = 0
    tables_with_data: int = 0
    performance_records_found: int = 0
    enrichments_applied: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Indique si des erreurs sont présentes"""
        return bool(self.errors)

    @property
    def has_warnings(self) -> bool:
        """Indique si des avertissements sont présents"""
        return bool(self.warnings)

    @property
    def data_extraction_rate(self) -> float:
        """Taux de tableaux avec données extraites"""
        if self.tables_processed == 0:
            return 0.0
        return self.tables_with_data / self.tables_processed

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "document": self.document.to_dict(),
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "processing_time_ms": self.processing_time_ms,
            "statistics": {
                "tables_processed": self.tables_processed,
                "tables_with_data": self.tables_with_data,
                "performance_records_found": self.performance_records_found,
                "data_extraction_rate": self.data_extraction_rate,
                "enrichments_applied": self.enrichments_applied,
            },
        }


# Fonctions utilitaires pour la validation


def validate_json_structure(data: Dict[str, Any]) -> List[str]:
    """Valide la structure JSON de base"""
    errors = []

    required_fields = ["title", "text"]
    for required_field in required_fields:
        if required_field not in data:
            errors.append(f"Champ requis manquant: {required_field}")
        elif not isinstance(data[required_field], str):
            errors.append(f"Le champ '{required_field}' doit être une chaîne")
        elif not data[required_field].strip():
            errors.append(f"Le champ '{required_field}' ne peut pas être vide")

    # Validation optionnelle des tableaux
    if "tables" in data:
        if not isinstance(data["tables"], list):
            errors.append("Le champ 'tables' doit être une liste")
        else:
            for i, table in enumerate(data["tables"]):
                if not isinstance(table, dict):
                    errors.append(f"Tableau {i+1}: doit être un objet")
                    continue

                if "headers" in table and not isinstance(table["headers"], list):
                    errors.append(f"Tableau {i+1}: 'headers' doit être une liste")

                if "rows" in table and not isinstance(table["rows"], list):
                    errors.append(f"Tableau {i+1}: 'rows' doit être une liste")

    return errors


def detect_genetic_line_from_content(title: str, text: str) -> GeneticLine:
    """Détecte automatiquement la lignée génétique depuis le contenu"""
    content = f"{title} {text}".lower()

    from .enums import GENETIC_LINE_PATTERNS

    for genetic_line, patterns in GENETIC_LINE_PATTERNS.items():
        if any(pattern in content for pattern in patterns):
            return genetic_line

    return GeneticLine.UNKNOWN


def detect_document_type_from_content(title: str, text: str) -> DocumentType:
    """Détecte automatiquement le type de document"""
    content = f"{title} {text}".lower()

    # Patterns pour détecter le type
    type_patterns = {
        DocumentType.PERFORMANCE_GUIDE: [
            "performance",
            "guide",
            "objectifs",
            "standards",
            "targets",
        ],
        DocumentType.NUTRITION_MANUAL: [
            "nutrition",
            "feeding",
            "aliment",
            "diet",
            "nutritional",
        ],
        DocumentType.MANAGEMENT_GUIDE: [
            "management",
            "élevage",
            "housing",
            "environnement",
            "welfare",
        ],
        DocumentType.TRIAL_REPORT: [
            "trial",
            "essai",
            "experiment",
            "study",
            "research",
            "test",
        ],
        DocumentType.PRODUCT_SHEET: [
            "product",
            "specification",
            "spec",
            "fiche",
            "commercial",
        ],
    }

    for doc_type, patterns in type_patterns.items():
        if any(pattern in content for pattern in patterns):
            return doc_type

    return DocumentType.UNKNOWN
