# -*- coding: utf-8 -*-
"""
rag/models/extraction_models.py - Modèles pour l'extraction de données de performance
Version 1.0 - Structures pour les enregistrements de performance avicole
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import re

from .enums import GeneticLine, MetricType, Sex, Phase, ConfidenceLevel


@dataclass
class PerformanceRecord:
    """Enregistrement de performance avicole extrait"""

    # Identifiants
    source_document_id: str = ""
    extraction_id: str = ""

    # Caractéristiques biologiques
    genetic_line: GeneticLine = GeneticLine.UNKNOWN
    age_days: int = 0
    sex: Sex = Sex.UNKNOWN
    phase: Phase = Phase.UNKNOWN

    # Métrique et valeurs
    metric_type: MetricType = MetricType.WEIGHT_G
    value_canonical: float = 0.0  # Valeur normalisée
    unit_canonical: str = ""  # Unité canonique
    value_original: float = 0.0  # Valeur originale
    unit_original: str = ""  # Unité originale

    # Contexte d'extraction
    table_context: str = ""
    column_header: str = ""
    row_context: str = ""

    # Qualité et confiance
    extraction_confidence: float = 1.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH
    validation_passed: bool = True
    validation_notes: str = ""

    # Métadonnées temporelles
    extraction_timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validation et normalisation post-initialisation"""
        # Mise à jour du niveau de confiance
        self.confidence_level = ConfidenceLevel.from_score(self.extraction_confidence)

        # Validation de base
        self._validate_values()

        # Génération de l'ID d'extraction si manquant
        if not self.extraction_id:
            self.extraction_id = self._generate_extraction_id()

    def _validate_values(self) -> None:
        """Validation des valeurs selon les contraintes métier"""

        # Validation âge
        if self.age_days < 0 or self.age_days > 500:
            self.validation_passed = False
            self.validation_notes += "Âge invalide; "

        # Validation valeur selon métrique
        if self.metric_type == MetricType.WEIGHT_G:
            if self.value_canonical < 0 or self.value_canonical > 5000:
                self.validation_passed = False
                self.validation_notes += "Poids invalide; "

        elif self.metric_type == MetricType.FCR:
            if self.value_canonical < 0.5 or self.value_canonical > 5.0:
                self.validation_passed = False
                self.validation_notes += "FCR invalide; "

        elif self.metric_type in [MetricType.MORTALITY_RATE, MetricType.LIVABILITY]:
            if self.value_canonical < 0 or self.value_canonical > 100:
                self.validation_passed = False
                self.validation_notes += "Pourcentage invalide; "

        # Validation cohérence lignée/phase
        if self.genetic_line.is_layer and self.phase.is_broiler_phase:
            self.validation_passed = False
            self.validation_notes += "Incohérence lignée/phase; "

    def _generate_extraction_id(self) -> str:
        """Génère un ID unique pour l'extraction"""
        components = [
            self.source_document_id[:8],
            self.genetic_line.value[:4],
            str(self.age_days),
            self.metric_type.value[:4],
            str(int(self.extraction_timestamp.timestamp()))[-6:],
        ]
        return "_".join(components)

    @property
    def business_key(self) -> str:
        """Clé métier pour l'unicité en base"""
        return f"{self.genetic_line.value}_{self.age_days}_{self.sex.value}_{self.phase.value}_{self.metric_type.value}_{self.value_canonical}"

    @property
    def is_plausible(self) -> bool:
        """Vérifie la plausibilité biologique de la valeur"""

        # Règles de plausibilité par métrique
        if self.metric_type == MetricType.WEIGHT_G:
            # Courbes de croissance typiques
            if self.genetic_line.is_broiler:
                expected_weight = self._estimate_broiler_weight()
                return (
                    abs(self.value_canonical - expected_weight) / expected_weight < 0.5
                )

        elif self.metric_type == MetricType.FCR:
            # FCR typiques par âge et lignée
            if self.genetic_line.is_broiler:
                return 0.8 <= self.value_canonical <= 2.5

        return True  # Par défaut, considérer comme plausible

    def _estimate_broiler_weight(self) -> float:
        """Estimation du poids pour validation de plausibilité"""
        # Courbe de croissance simplifiée (Gompertz)
        if self.genetic_line in [GeneticLine.ROSS_308, GeneticLine.COBB_500]:
            # Paramètres moyens pour broilers standards
            if self.sex == Sex.MALE:
                return min(3000, 45 * self.age_days * (1 + 0.02 * self.age_days))
            else:
                return min(2500, 40 * self.age_days * (1 + 0.018 * self.age_days))

        return 50 * self.age_days  # Estimation générique

    def normalize_unit(self) -> None:
        """Normalise l'unité vers l'unité canonique"""

        if self.unit_original == self.unit_canonical:
            self.value_canonical = self.value_original
            return

        # Conversions de poids
        if self.metric_type in [
            MetricType.WEIGHT_G,
            MetricType.WEIGHT_KG,
            MetricType.WEIGHT_LB,
        ]:
            if self.unit_original.lower() in ["kg", "kilo"]:
                self.value_canonical = self.value_original * 1000
                self.unit_canonical = "g"
            elif self.unit_original.lower() in ["lb", "pound"]:
                self.value_canonical = self.value_original * 453.592
                self.unit_canonical = "g"
            else:
                self.value_canonical = self.value_original
                self.unit_canonical = "g"

        # Conversions d'aliment
        elif self.metric_type in [MetricType.FEED_INTAKE_G, MetricType.FEED_INTAKE_KG]:
            if self.unit_original.lower() in ["kg", "kilo"]:
                self.value_canonical = self.value_original * 1000
                self.unit_canonical = "g"
            else:
                self.value_canonical = self.value_original
                self.unit_canonical = "g"

        else:
            # Pas de conversion nécessaire
            self.value_canonical = self.value_original
            self.unit_canonical = self.unit_original

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour stockage"""
        return {
            "source_document_id": self.source_document_id,
            "extraction_id": self.extraction_id,
            "genetic_line": self.genetic_line.value,
            "age_days": self.age_days,
            "sex": self.sex.value,
            "phase": self.phase.value,
            "metric_type": self.metric_type.value,
            "value_canonical": self.value_canonical,
            "unit_canonical": self.unit_canonical,
            "value_original": self.value_original,
            "unit_original": self.unit_original,
            "table_context": self.table_context,
            "column_header": self.column_header,
            "row_context": self.row_context,
            "extraction_confidence": self.extraction_confidence,
            "confidence_level": self.confidence_level.value,
            "validation_passed": self.validation_passed,
            "validation_notes": self.validation_notes,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "business_key": self.business_key,
            "is_plausible": self.is_plausible,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceRecord":
        """Création depuis un dictionnaire"""
        return cls(
            source_document_id=data.get("source_document_id", ""),
            extraction_id=data.get("extraction_id", ""),
            genetic_line=GeneticLine(data.get("genetic_line", "unknown")),
            age_days=data.get("age_days", 0),
            sex=Sex(data.get("sex", "unknown")),
            phase=Phase(data.get("phase", "unknown")),
            metric_type=MetricType(data.get("metric_type", "weight_g")),
            value_canonical=data.get("value_canonical", 0.0),
            unit_canonical=data.get("unit_canonical", ""),
            value_original=data.get("value_original", 0.0),
            unit_original=data.get("unit_original", ""),
            table_context=data.get("table_context", ""),
            column_header=data.get("column_header", ""),
            row_context=data.get("row_context", ""),
            extraction_confidence=data.get("extraction_confidence", 1.0),
            validation_passed=data.get("validation_passed", True),
            validation_notes=data.get("validation_notes", ""),
            extraction_timestamp=datetime.fromisoformat(
                data.get("extraction_timestamp", datetime.now().isoformat())
            ),
        )


@dataclass
class ExtractionSession:
    """Session d'extraction pour un document ou batch de documents"""

    session_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # Statistiques
    documents_processed: int = 0
    records_extracted: int = 0
    records_validated: int = 0
    errors_count: int = 0

    # Configuration utilisée
    extractor_type: str = ""
    extractor_version: str = "1.0"
    confidence_threshold: float = 0.5

    # Résultats
    extraction_results: List[PerformanceRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Durée de la session en secondes"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Taux de succès de validation"""
        if self.records_extracted == 0:
            return 0.0
        return self.records_validated / self.records_extracted

    @property
    def avg_confidence(self) -> float:
        """Confiance moyenne des extractions"""
        if not self.extraction_results:
            return 0.0
        confidences = [r.extraction_confidence for r in self.extraction_results]
        return sum(confidences) / len(confidences)

    def add_result(self, record: PerformanceRecord) -> None:
        """Ajoute un résultat d'extraction"""
        self.extraction_results.append(record)
        self.records_extracted += 1
        if record.validation_passed:
            self.records_validated += 1

    def add_error(self, error: str) -> None:
        """Ajoute une erreur"""
        self.errors.append(error)
        self.errors_count += 1

    def add_warning(self, warning: str) -> None:
        """Ajoute un avertissement"""
        self.warnings.append(warning)

    def finalize(self) -> None:
        """Finalise la session"""
        self.end_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour rapports"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "statistics": {
                "documents_processed": self.documents_processed,
                "records_extracted": self.records_extracted,
                "records_validated": self.records_validated,
                "errors_count": self.errors_count,
                "success_rate": self.success_rate,
                "avg_confidence": self.avg_confidence,
            },
            "configuration": {
                "extractor_type": self.extractor_type,
                "extractor_version": self.extractor_version,
                "confidence_threshold": self.confidence_threshold,
            },
            "results_summary": {
                "total_results": len(self.extraction_results),
                "valid_results": len(
                    [r for r in self.extraction_results if r.validation_passed]
                ),
                "plausible_results": len(
                    [r for r in self.extraction_results if r.is_plausible]
                ),
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


# Fonctions utilitaires pour l'extraction


def parse_numeric_value(value_str: str) -> tuple[float, str]:
    """Parse une valeur numérique avec son unité"""

    if not value_str or value_str.strip() == "":
        return 0.0, ""

    # Nettoyage de base
    cleaned = value_str.strip().replace(",", ".")

    # Patterns pour extraire nombre + unité
    patterns = [
        r"^([\d.]+)\s*([a-zA-Z%°]+)?",  # 123.45 kg
        r"^([\d.]+)$",  # 123.45
    ]

    for pattern in patterns:
        match = re.match(pattern, cleaned)
        if match:
            try:
                number = float(match.group(1))
                unit = (
                    match.group(2) if len(match.groups()) > 1 and match.group(2) else ""
                )
                return number, unit.strip()
            except ValueError:
                continue

    return 0.0, ""


def detect_metric_from_header(header: str) -> Optional[MetricType]:
    """Détecte le type de métrique depuis un en-tête de colonne"""

    header_lower = header.lower().strip()

    # Mappings des patterns vers métriques
    metric_patterns = {
        MetricType.WEIGHT_G: [
            "weight",
            "poids",
            "body weight",
            "live weight",
            "bw",
            "lw",
            "body wt",
            "live wt",
            "peso",
            "gewicht",
        ],
        MetricType.FCR: [
            "fcr",
            "feed conversion",
            "conversion",
            "ic",
            "indice conversion",
            "conv",
            "feed conv",
            "f:g",
            "feed:gain",
        ],
        MetricType.FEED_INTAKE_G: [
            "feed intake",
            "feed consumption",
            "consommation",
            "consumption",
            "feed",
            "aliment",
            "cum feed",
            "cumulative feed",
        ],
        MetricType.MORTALITY_RATE: [
            "mortality",
            "mortalité",
            "mort",
            "death",
            "dead",
            "mortalidad",
        ],
        MetricType.LIVABILITY: [
            "livability",
            "viability",
            "viabilité",
            "survival",
            "survie",
        ],
        MetricType.EGG_PRODUCTION: [
            "egg production",
            "ponte",
            "laying",
            "production",
            "lay",
        ],
        MetricType.EGG_WEIGHT: ["egg weight", "poids oeuf", "egg wt", "peso huevo"],
    }

    # Recherche du pattern correspondant
    for metric_type, patterns in metric_patterns.items():
        if any(pattern in header_lower for pattern in patterns):
            return metric_type

    return None


def detect_age_from_context(context: str, header: str) -> int:
    """Détecte l'âge depuis le contexte ou l'en-tête"""

    combined_text = f"{context} {header}".lower()

    # Patterns pour détecter l'âge
    age_patterns = [
        r"(\d+)\s*(?:day|jour|día|tag)",
        r"(\d+)\s*d\b",
        r"(\d+)\s*j\b",
        r"week\s*(\d+)",
        r"semaine\s*(\d+)",
        r"(\d+)\s*(?:week|sem|wk)",
        r"(\d+)\s*w\b",
    ]

    for pattern in age_patterns:
        match = re.search(pattern, combined_text)
        if match:
            age = int(match.group(1))
            # Conversion semaines -> jours si nécessaire
            if "week" in pattern or "sem" in pattern or "w" in pattern:
                age *= 7

            # Validation âge plausible
            if 0 <= age <= 500:
                return age

    return 0


def detect_sex_from_context(context: str, header: str) -> Sex:
    """Détecte le sexe depuis le contexte"""

    combined_text = f"{context} {header}".lower()

    # Patterns pour détecter le sexe
    if any(term in combined_text for term in ["male", "mâle", "macho", "cock", "coq"]):
        return Sex.MALE
    elif any(
        term in combined_text
        for term in ["female", "femelle", "hembra", "hen", "poule"]
    ):
        return Sex.FEMALE
    elif any(term in combined_text for term in ["mixed", "mixte", "mix", "as hatched"]):
        return Sex.MIXED

    return Sex.UNKNOWN


def detect_phase_from_age_and_genetic_line(
    age_days: int, genetic_line: GeneticLine
) -> Phase:
    """Détecte la phase d'élevage selon l'âge et la lignée"""

    if genetic_line.is_broiler:
        if age_days <= 10:
            return Phase.STARTER
        elif age_days <= 24:
            return Phase.GROWER
        elif age_days <= 50:
            return Phase.FINISHER
        else:
            return Phase.WHOLE_CYCLE

    elif genetic_line.is_layer:
        if age_days <= 126:  # 18 semaines
            return Phase.REARING
        elif age_days <= 140:  # 20 semaines
            return Phase.PRE_LAY
        elif age_days <= 280:  # 40 semaines
            return Phase.PEAK
        else:
            return Phase.POST_PEAK

    return Phase.UNKNOWN


# Classes d'aide pour les patterns de reconnaissance


@dataclass
class ExtractionPattern:
    """Pattern pour l'extraction automatique"""

    name: str
    genetic_line: GeneticLine
    metric_type: MetricType
    header_patterns: List[str]
    context_patterns: List[str] = field(default_factory=list)
    confidence_boost: float = 0.1

    def matches_header(self, header: str) -> bool:
        """Vérifie si l'en-tête correspond au pattern"""
        header_lower = header.lower()
        return any(pattern in header_lower for pattern in self.header_patterns)

    def matches_context(self, context: str) -> bool:
        """Vérifie si le contexte correspond au pattern"""
        if not self.context_patterns:
            return True

        context_lower = context.lower()
        return any(pattern in context_lower for pattern in self.context_patterns)


# Patterns prédéfinis pour différentes lignées
ROSS_EXTRACTION_PATTERNS = [
    ExtractionPattern(
        name="ross_weight",
        genetic_line=GeneticLine.ROSS_308,
        metric_type=MetricType.WEIGHT_G,
        header_patterns=["live weight", "body weight", "bw", "weight"],
        context_patterns=["ross", "308"],
    ),
    ExtractionPattern(
        name="ross_fcr",
        genetic_line=GeneticLine.ROSS_308,
        metric_type=MetricType.FCR,
        header_patterns=["fcr", "feed conversion", "conversion"],
        context_patterns=["ross", "308"],
    ),
]

COBB_EXTRACTION_PATTERNS = [
    ExtractionPattern(
        name="cobb_weight",
        genetic_line=GeneticLine.COBB_500,
        metric_type=MetricType.WEIGHT_G,
        header_patterns=["bw", "body weight", "live weight", "weight"],
        context_patterns=["cobb", "500"],
    ),
    ExtractionPattern(
        name="cobb_fcr",
        genetic_line=GeneticLine.COBB_500,
        metric_type=MetricType.FCR,
        header_patterns=["feed conv", "fcr", "conversion"],
        context_patterns=["cobb", "500"],
    ),
]
