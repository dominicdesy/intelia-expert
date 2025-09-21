# -*- coding: utf-8 -*-

"""

rag/models/enums.py - Énumérations pour le système RAG avicole
Version 1.0 - Fondations du système d'extraction JSON

"""


from enum import Enum


class GeneticLine(Enum):
    """Lignées génétiques supportées par le système"""

    # Lignées Ross (Aviagen)
    ROSS_308 = "ross_308"
    ROSS_708 = "ross_708"

    # Lignées Cobb (Cobb-Vantress)
    COBB_500 = "cobb_500"
    COBB_700 = "cobb_700"

    # Lignées Hubbard (Hubbard)
    HUBBARD_CLASSIC = "hubbard_classic"
    HUBBARD_FLEX = "hubbard_flex"

    # Lignées pondeuses
    ISA_BROWN = "isa_brown"
    LOHMANN_BROWN = "lohmann_brown"
    HY_LINE = "hy_line"

    # Lignées alternatives/biologiques
    FREEDOM_RANGER = "freedom_ranger"
    RANGER_CLASSIC = "ranger_classic"

    # Lignées expérimentales ou inconnues
    UNKNOWN = "unknown"
    MIXED = "mixed"  # Pour documents multi-lignées

    @property
    def is_broiler(self) -> bool:
        """Indique si c'est une lignée de chair"""
        return self in {
            self.ROSS_308,
            self.ROSS_708,
            self.COBB_500,
            self.COBB_700,
            self.HUBBARD_CLASSIC,
            self.HUBBARD_FLEX,
            self.FREEDOM_RANGER,
            self.RANGER_CLASSIC,
        }

    @property
    def is_layer(self) -> bool:
        """Indique si c'est une lignée pondeuse"""
        return self in {self.ISA_BROWN, self.LOHMANN_BROWN, self.HY_LINE}

    @property
    def company(self) -> str:
        """Retourne la compagnie de sélection"""
        if self in {self.ROSS_308, self.ROSS_708}:
            return "Aviagen"
        elif self in {self.COBB_500, self.COBB_700}:
            return "Cobb-Vantress"
        elif self in {self.HUBBARD_CLASSIC, self.HUBBARD_FLEX}:
            return "Hubbard"
        elif self in {self.ISA_BROWN}:
            return "Hendrix Genetics"
        elif self in {self.LOHMANN_BROWN}:
            return "Lohmann"
        elif self in {self.HY_LINE}:
            return "Hy-Line"
        elif self in {self.FREEDOM_RANGER, self.RANGER_CLASSIC}:
            return "Redbro"
        else:
            return "Unknown"


class MetricType(Enum):
    """Types de métriques de performance avicoles"""

    # Métriques de croissance
    WEIGHT_G = "weight_g"  # Poids vif en grammes
    WEIGHT_KG = "weight_kg"  # Poids vif en kilogrammes
    WEIGHT_LB = "weight_lb"  # Poids vif en livres
    DAILY_GAIN = "daily_gain"  # Gain moyen quotidien

    # Métriques d'alimentation
    FEED_INTAKE_G = "feed_intake_g"  # Consommation d'aliment (g)
    FEED_INTAKE_KG = "feed_intake_kg"  # Consommation d'aliment (kg)
    FCR = "fcr"  # Indice de consommation
    FEED_EFFICIENCY = "feed_efficiency"  # Efficacité alimentaire

    # Métriques de survie
    MORTALITY_RATE = "mortality_rate"  # Taux de mortalité (%)
    LIVABILITY = "livability"  # Viabilité (%)
    CULLING_RATE = "culling_rate"  # Taux de réforme (%)

    # Métriques pondeuses
    EGG_PRODUCTION = "egg_production"  # Production d'œufs (%)
    EGG_WEIGHT = "egg_weight"  # Poids des œufs (g)
    EGG_MASS = "egg_mass"  # Masse d'œufs (g/poule/jour)
    FEED_PER_DOZEN = "feed_per_dozen"  # Aliment par douzaine d'œufs

    # Métriques de qualité
    BREAST_YIELD = "breast_yield"  # Rendement en blanc (%)
    CARCASS_YIELD = "carcass_yield"  # Rendement carcasse (%)
    UNIFORMITY = "uniformity"  # Uniformité du lot (%)

    # Métriques environnementales
    WATER_INTAKE = "water_intake"  # Consommation d'eau
    TEMPERATURE = "temperature"  # Température ambiante
    HUMIDITY = "humidity"  # Humidité relative

    # Métriques sanitaires
    LESION_SCORE = "lesion_score"  # Score de lésions
    FOOTPAD_SCORE = "footpad_score"  # Score de dermatite plantaire
    HOCK_BURN_SCORE = "hock_burn_score"  # Score de brûlures de jarret

    @property
    def category(self) -> str:
        """Catégorie de la métrique"""
        if self in {self.WEIGHT_G, self.WEIGHT_KG, self.WEIGHT_LB, self.DAILY_GAIN}:
            return "croissance"
        elif self in {
            self.FEED_INTAKE_G,
            self.FEED_INTAKE_KG,
            self.FCR,
            self.FEED_EFFICIENCY,
        }:
            return "alimentation"
        elif self in {self.MORTALITY_RATE, self.LIVABILITY, self.CULLING_RATE}:
            return "survie"
        elif self in {
            self.EGG_PRODUCTION,
            self.EGG_WEIGHT,
            self.EGG_MASS,
            self.FEED_PER_DOZEN,
        }:
            return "ponte"
        elif self in {self.BREAST_YIELD, self.CARCASS_YIELD, self.UNIFORMITY}:
            return "qualite"
        elif self in {self.WATER_INTAKE, self.TEMPERATURE, self.HUMIDITY}:
            return "environnement"
        elif self in {self.LESION_SCORE, self.FOOTPAD_SCORE, self.HOCK_BURN_SCORE}:
            return "sante"
        else:
            return "autre"

    @property
    def unit(self) -> str:
        """Unité canonique de la métrique"""
        if "weight" in self.value:
            if "kg" in self.value:
                return "kg"
            elif "lb" in self.value:
                return "lb"
            else:
                return "g"
        elif "rate" in self.value or self.value in {
            "livability",
            "egg_production",
            "uniformity",
        }:
            return "%"
        elif "feed_intake" in self.value:
            if "kg" in self.value:
                return "kg"
            else:
                return "g"
        elif self.value == "fcr":
            return "ratio"
        elif "score" in self.value:
            return "score"
        elif self.value == "temperature":
            return "°C"
        elif self.value == "humidity":
            return "%"
        elif self.value == "water_intake":
            return "L"
        else:
            return "unité"


class Sex(Enum):
    """Sexe des animaux"""

    MALE = "male"  # Mâles
    FEMALE = "female"  # Femelles
    MIXED = "mixed"  # Lot mixte
    UNKNOWN = "unknown"  # Non spécifié

    @property
    def french(self) -> str:
        """Traduction française"""
        translations = {
            self.MALE: "mâle",
            self.FEMALE: "femelle",
            self.MIXED: "mixte",
            self.UNKNOWN: "non spécifié",
        }
        return translations[self]


class Phase(Enum):
    """Phases d'élevage"""

    # Phases chair
    STARTER = "starter"  # Démarrage (0-10j)
    GROWER = "grower"  # Croissance (11-24j)
    FINISHER = "finisher"  # Finition (25j-abattage)
    WHOLE_CYCLE = "whole_cycle"  # Cycle complet

    # Phases pondeuses
    REARING = "rearing"  # Élevage (0-18 semaines)
    PRE_LAY = "pre_lay"  # Pré-ponte (16-20 semaines)
    PEAK = "peak"  # Pic de ponte (20-40 semaines)
    POST_PEAK = "post_peak"  # Post-pic (40+ semaines)

    # Phases reproductrices
    BREEDING = "breeding"  # Reproduction

    # Phases spéciales
    UNKNOWN = "unknown"  # Non spécifié

    @property
    def is_broiler_phase(self) -> bool:
        """Indique si c'est une phase de chair"""
        return self in {self.STARTER, self.GROWER, self.FINISHER, self.WHOLE_CYCLE}

    @property
    def is_layer_phase(self) -> bool:
        """Indique si c'est une phase pondeuse"""
        return self in {self.REARING, self.PRE_LAY, self.PEAK, self.POST_PEAK}


class DocumentType(Enum):
    """Types de documents avicoles"""

    # Guides techniques
    PERFORMANCE_GUIDE = "performance_guide"  # Guide de performance
    NUTRITION_MANUAL = "nutrition_manual"  # Manuel nutritionnel
    MANAGEMENT_GUIDE = "management_guide"  # Guide d'élevage
    HOUSING_MANUAL = "housing_manual"  # Manuel de logement

    # Standards et objectifs
    BREED_STANDARD = "breed_standard"  # Standard de race
    PERFORMANCE_TARGETS = "performance_targets"  # Objectifs de performance
    SPECIFICATIONS = "specifications"  # Spécifications techniques

    # Données expérimentales
    TRIAL_REPORT = "trial_report"  # Rapport d'essai
    RESEARCH_DATA = "research_data"  # Données de recherche
    FIELD_STUDY = "field_study"  # Étude terrain

    # Documentation commerciale
    PRODUCT_SHEET = "product_sheet"  # Fiche produit
    TECHNICAL_BULLETIN = "technical_bulletin"  # Bulletin technique
    COMPANY_BROCHURE = "company_brochure"  # Brochure commerciale

    # Autres
    UNKNOWN = "unknown"  # Type inconnu
    MIXED = "mixed"  # Document mixte

    @property
    def category(self) -> str:
        """Catégorie du document"""
        if self in {
            self.PERFORMANCE_GUIDE,
            self.NUTRITION_MANUAL,
            self.MANAGEMENT_GUIDE,
            self.HOUSING_MANUAL,
        }:
            return "guide"
        elif self in {
            self.BREED_STANDARD,
            self.PERFORMANCE_TARGETS,
            self.SPECIFICATIONS,
        }:
            return "standard"
        elif self in {self.TRIAL_REPORT, self.RESEARCH_DATA, self.FIELD_STUDY}:
            return "recherche"
        elif self in {
            self.PRODUCT_SHEET,
            self.TECHNICAL_BULLETIN,
            self.COMPANY_BROCHURE,
        }:
            return "commercial"
        else:
            return "autre"


class ExtractionStatus(Enum):
    """Statut d'extraction des données"""

    PENDING = "pending"  # En attente
    PROCESSING = "processing"  # En cours de traitement
    SUCCESS = "success"  # Extraction réussie
    FAILED = "failed"  # Échec d'extraction
    PARTIAL = "partial"  # Extraction partielle
    VALIDATION_ERROR = "validation_error"  # Erreur de validation
    SKIPPED = "skipped"  # Ignoré (déjà traité)

    @property
    def is_complete(self) -> bool:
        """Indique si l'extraction est terminée"""
        return self in {
            self.SUCCESS,
            self.FAILED,
            self.PARTIAL,
            self.VALIDATION_ERROR,
            self.SKIPPED,
        }

    @property
    def is_success(self) -> bool:
        """Indique si l'extraction a réussi"""
        return self in {self.SUCCESS, self.PARTIAL}


class ConfidenceLevel(Enum):
    """Niveaux de confiance d'extraction"""

    VERY_HIGH = "very_high"  # 0.9-1.0 - Extraction très fiable
    HIGH = "high"  # 0.7-0.9 - Extraction fiable
    MEDIUM = "medium"  # 0.5-0.7 - Extraction moyennement fiable
    LOW = "low"  # 0.3-0.5 - Extraction peu fiable
    VERY_LOW = "very_low"  # 0.0-0.3 - Extraction très peu fiable

    @property
    def min_score(self) -> float:
        """Score minimum pour ce niveau"""
        thresholds = {
            self.VERY_HIGH: 0.9,
            self.HIGH: 0.7,
            self.MEDIUM: 0.5,
            self.LOW: 0.3,
            self.VERY_LOW: 0.0,
        }
        return thresholds[self]

    @property
    def max_score(self) -> float:
        """Score maximum pour ce niveau"""
        thresholds = {
            self.VERY_HIGH: 1.0,
            self.HIGH: 0.9,
            self.MEDIUM: 0.7,
            self.LOW: 0.5,
            self.VERY_LOW: 0.3,
        }
        return thresholds[self]

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Détermine le niveau de confiance à partir d'un score"""
        if score >= 0.9:
            return cls.VERY_HIGH
        elif score >= 0.7:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.3:
            return cls.LOW
        else:
            return cls.VERY_LOW


# Mappings utiles pour la détection automatique
GENETIC_LINE_PATTERNS = {
    GeneticLine.ROSS_308: [
        "ross 308",
        "ross308",
        "r308",
        "r-308",
        "ross broiler",
        "broiler ross 308",
    ],
    GeneticLine.ROSS_708: ["ross 708", "ross708", "r708", "r-708"],
    GeneticLine.COBB_500: [
        "cobb 500",
        "cobb500",
        "c500",
        "c-500",
        "cobb broiler",
        "broiler cobb 500",
    ],
    GeneticLine.COBB_700: ["cobb 700", "cobb700", "c700", "c-700"],
    GeneticLine.HUBBARD_CLASSIC: ["hubbard classic", "classic hubbard", "hubbard"],
    GeneticLine.HUBBARD_FLEX: ["hubbard flex", "flex hubbard", "hubbard f"],
    GeneticLine.ISA_BROWN: ["isa brown", "isa", "brown isa"],
    GeneticLine.LOHMANN_BROWN: ["lohmann brown", "lohmann", "brown lohmann"],
    GeneticLine.HY_LINE: ["hy-line", "hyline", "hy line"],
    GeneticLine.FREEDOM_RANGER: ["freedom ranger", "ranger", "freedom"],
}

METRIC_PATTERNS = {
    MetricType.WEIGHT_G: ["weight", "poids", "body weight", "live weight", "bw", "lw"],
    MetricType.FCR: ["fcr", "feed conversion", "conversion", "ic", "indice conversion"],
    MetricType.FEED_INTAKE_G: [
        "feed intake",
        "consumption",
        "consommation",
        "feed",
        "aliment",
    ],
    MetricType.MORTALITY_RATE: ["mortality", "mortalité", "mort", "death", "viability"],
    MetricType.EGG_PRODUCTION: ["egg production", "ponte", "laying", "production"],
}
