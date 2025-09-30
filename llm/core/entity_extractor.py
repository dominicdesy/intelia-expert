# -*- coding: utf-8 -*-
"""
entity_extractor.py - Extracteur d'entités centralisé
Remplace la logique éparpillée dans comparative_detector, query_preprocessor, etc.
Version 2.0 - Migration vers breeds_registry dynamique
"""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from utils.breeds_registry import get_breeds_registry

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types d'entités extraites"""

    BREED = "breed"
    AGE = "age"
    SEX = "sex"
    METRIC = "metric"
    GENETIC_LINE = "genetic_line"


class ConfidenceLevel(Enum):
    """Niveaux de confiance d'extraction"""

    HIGH = 0.9
    MEDIUM = 0.7
    LOW = 0.5
    VERY_LOW = 0.3


@dataclass
class ExtractedEntities:
    """Structure des entités extraites"""

    breed: Optional[str] = None
    age_days: Optional[int] = None
    sex: Optional[str] = None
    metric_type: Optional[str] = None
    genetic_line: Optional[str] = None

    # Métadonnées d'extraction
    confidence: float = 1.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    extraction_source: str = "pattern_matching"
    raw_matches: Dict[str, Any] = field(default_factory=dict)

    # Flags de qualité
    has_explicit_sex: bool = False
    has_explicit_age: bool = False
    has_explicit_breed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire standard"""
        return {
            "breed": self.breed,
            "age_days": self.age_days,
            "sex": self.sex,
            "metric_type": self.metric_type,
            "genetic_line": self.genetic_line,
            "confidence": self.confidence,
            "has_explicit_sex": self.has_explicit_sex,
            "has_explicit_age": self.has_explicit_age,
            "has_explicit_breed": self.has_explicit_breed,
        }

    def get_entity_count(self) -> int:
        """Retourne le nombre d'entités extraites"""
        return sum(
            [
                self.breed is not None,
                self.age_days is not None,
                self.sex is not None,
                self.metric_type is not None,
            ]
        )


class EntityExtractor:
    """
    Extracteur d'entités unifié pour toutes les requêtes avicoles

    Fonctionnalités:
    - Extraction breed, age, sex, metric avec patterns dynamiques depuis breeds_registry
    - Détection de confiance par entité
    - Support multi-patterns pour robustesse
    - Normalisation automatique des valeurs

    Version 2.0: Utilise breeds_registry au lieu de patterns hardcodés
    """

    # Patterns centralisés - Sex (statiques, pas de races)
    SEX_PATTERNS = {
        "male": [
            r"\bm[aâ]les?\b",
            r"\bmale\b",
            r"\bcoq(?:s)?\b",
            r"\bmasculin\b",
        ],
        "female": [
            r"\bfemelles?\b",
            r"\bfemale\b",
            r"\bpoule(?:s)?\b",
            r"\bf[ée]minin\b",
        ],
        "mixed": [
            r"\bmixte\b",
            r"\bmixed\b",
            r"\bas\s*hatched\b",
        ],
    }

    # Patterns centralisés - Age (statiques)
    AGE_PATTERNS = [
        r"(\d+)\s*(?:jours?|days?|j)\b",
        r"à\s+(\d+)\s*(?:jours?|j)\b",
        r"age\s+(?:de\s+)?(\d+)",
        r"\b(\d+)\s*j\b",
        r"(\d+)(?:e|ème|eme)?\s+jour",
    ]

    # Patterns centralisés - Metrics (statiques)
    METRIC_PATTERNS = {
        "weight": [
            "poids",
            "weight",
            "body weight",
            "poids vif",
            "masse",
        ],
        "fcr": [
            "fcr",
            "ic",
            "indice de consommation",
            "conversion alimentaire",
            "feed conversion",
            "conversion",
        ],
        "mortality": [
            "mortalité",
            "mortality",
            "mort",
            "décès",
            "pertes",
        ],
        "gain": [
            "gain",
            "croissance",
            "growth",
            "gmq",
            "daily gain",
            "gain quotidien",
        ],
        "feed_intake": [
            "consommation",
            "feed intake",
            "aliment",
            "ingéré",
        ],
        "production": [
            "production",
            "ponte",
            "laying",
            "œufs",
            "eggs",
        ],
    }

    def __init__(self, intents_config_path: str = "config/intents.json"):
        """
        Initialise l'extracteur avec breeds_registry

        Args:
            intents_config_path: Chemin vers intents.json
        """
        # Charger le breeds_registry
        self.breeds_registry = get_breeds_registry(intents_config_path)

        # Compiler les patterns
        self._compile_patterns()

        logger.info(
            f"EntityExtractor initialisé avec breeds_registry "
            f"({len(self.breeds_registry.get_all_breeds())} races)"
        )

    def _compile_patterns(self):
        """Compile tous les patterns regex pour performance"""

        # Compilation breeds depuis breeds_registry
        self.compiled_breed = {}
        self._build_breed_patterns_from_registry()

        # Compilation sex (statique)
        self.compiled_sex = {}
        for sex_value, patterns in self.SEX_PATTERNS.items():
            self.compiled_sex[sex_value] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

        # Compilation age (statique)
        self.compiled_age = [re.compile(p, re.IGNORECASE) for p in self.AGE_PATTERNS]

        logger.debug(
            f"Patterns compilés: {len(self.compiled_breed)} breeds, "
            f"{len(self.compiled_sex)} sexes, {len(self.compiled_age)} age patterns"
        )

    def _build_breed_patterns_from_registry(self):
        """
        Construit les patterns de breeds depuis le breeds_registry
        Remplace les patterns hardcodés
        """
        for breed in self.breeds_registry.get_all_breeds():
            # Récupérer tous les aliases pour cette race
            aliases = self.breeds_registry.get_aliases(breed)

            # Créer des patterns regex pour chaque alias
            patterns = []

            # Pattern pour le nom canonique
            canonical_pattern = self._create_pattern_from_text(breed)
            patterns.append(re.compile(canonical_pattern, re.IGNORECASE))

            # Patterns pour les aliases
            for alias in aliases:
                alias_pattern = self._create_pattern_from_text(alias)
                patterns.append(re.compile(alias_pattern, re.IGNORECASE))

            # Stocker les patterns compilés
            self.compiled_breed[breed] = patterns

        logger.debug(
            f"Patterns de breeds générés pour {len(self.compiled_breed)} races"
        )

    def _create_pattern_from_text(self, text: str) -> str:
        """
        Crée un pattern regex flexible depuis un texte

        Args:
            text: Texte source (ex: "ross 308", "cobb500")

        Returns:
            Pattern regex string
        """
        # Échapper les caractères spéciaux
        escaped = re.escape(text)

        # Remplacer les espaces par des patterns flexibles
        # "ross 308" -> "ross\s*308" (permet "ross308", "ross 308", "ross-308")
        pattern = escaped.replace(r"\ ", r"[\s\-_]*")

        # Ajouter des word boundaries pour éviter les faux positifs
        pattern = r"\b" + pattern + r"\b"

        return pattern

    def extract(
        self, query: str, entities_hint: Dict[str, Any] = None
    ) -> ExtractedEntities:
        """
        Extraction complète des entités depuis une requête

        Args:
            query: Requête utilisateur
            entities_hint: Entités déjà connues (optionnel, pour enrichissement)

        Returns:
            ExtractedEntities avec tous les champs détectés et confiance
        """
        query_lower = query.lower()
        entities = ExtractedEntities()

        # Utiliser hints si fournis
        if entities_hint:
            if "breed" in entities_hint and entities_hint["breed"]:
                entities.breed = entities_hint["breed"]
                entities.has_explicit_breed = True
            if "age_days" in entities_hint and entities_hint["age_days"]:
                entities.age_days = entities_hint["age_days"]
                entities.has_explicit_age = True
            if "sex" in entities_hint and entities_hint["sex"]:
                entities.sex = entities_hint["sex"]
                entities.has_explicit_sex = True

        # Extraction breed (si pas déjà défini)
        if not entities.breed:
            breed_result = self._extract_breed(query_lower)
            entities.breed = breed_result["value"]
            entities.confidence_breakdown["breed"] = breed_result["confidence"]
            entities.has_explicit_breed = breed_result["explicit"]
            if breed_result["value"]:
                entities.raw_matches["breed"] = breed_result["match_text"]

        # Extraction age (si pas déjà défini)
        if not entities.age_days:
            age_result = self._extract_age(query_lower)
            entities.age_days = age_result["value"]
            entities.confidence_breakdown["age"] = age_result["confidence"]
            entities.has_explicit_age = age_result["explicit"]
            if age_result["value"]:
                entities.raw_matches["age"] = age_result["match_text"]

        # Extraction sex (si pas déjà défini)
        if not entities.sex:
            sex_result = self._extract_sex(query_lower)
            entities.sex = sex_result["value"]
            entities.confidence_breakdown["sex"] = sex_result["confidence"]
            entities.has_explicit_sex = sex_result["explicit"]
            if sex_result["value"]:
                entities.raw_matches["sex"] = sex_result["match_text"]

        # Extraction metric
        metric_result = self._extract_metric(query_lower)
        entities.metric_type = metric_result["value"]
        entities.confidence_breakdown["metric"] = metric_result["confidence"]
        if metric_result["value"]:
            entities.raw_matches["metric"] = metric_result["match_text"]

        # Extraction genetic line (dérivé du breed via registry)
        if entities.breed:
            entities.genetic_line = self._derive_genetic_line(entities.breed)

        # Calcul confiance globale
        entities.confidence = self._calculate_overall_confidence(entities)

        logger.debug(
            f"Extraction completée: {entities.get_entity_count()} entités, "
            f"confiance={entities.confidence:.2f}"
        )

        return entities

    def _extract_breed(self, query: str) -> Dict[str, Any]:
        """
        Extrait la souche avec confiance en utilisant breeds_registry

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        for breed_name, patterns in self.compiled_breed.items():
            for idx, pattern in enumerate(patterns):
                match = pattern.search(query)
                if match:
                    # Normaliser via breeds_registry pour obtenir le nom canonique
                    normalized = self.breeds_registry.normalize_breed_name(
                        match.group(0)
                    )

                    # Confiance basée sur la spécificité du pattern
                    confidence = 0.95 if idx == 0 else 0.85 - (idx * 0.1)

                    return {
                        "value": normalized or breed_name,
                        "confidence": max(confidence, 0.6),
                        "explicit": True,
                        "match_text": match.group(0),
                    }

        return {
            "value": None,
            "confidence": 0.0,
            "explicit": False,
            "match_text": None,
        }

    def _extract_age(self, query: str) -> Dict[str, Any]:
        """
        Extrait l'âge en jours avec confiance

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        for idx, pattern in enumerate(self.compiled_age):
            match = pattern.search(query)
            if match:
                try:
                    age_value = int(match.group(1))

                    # Validation plausibilité (0-100 jours)
                    if 0 <= age_value <= 100:
                        confidence = 0.95 if idx == 0 else 0.9
                        return {
                            "value": age_value,
                            "confidence": confidence,
                            "explicit": True,
                            "match_text": match.group(0),
                        }
                    else:
                        logger.warning(f"Âge hors plage détecté: {age_value}")

                except (ValueError, IndexError) as e:
                    logger.debug(f"Erreur parsing age: {e}")
                    continue

        return {
            "value": None,
            "confidence": 0.0,
            "explicit": False,
            "match_text": None,
        }

    def _extract_sex(self, query: str) -> Dict[str, Any]:
        """
        Extrait le sexe avec confiance

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        for sex_value, patterns in self.compiled_sex.items():
            for idx, pattern in enumerate(patterns):
                match = pattern.search(query)
                if match:
                    confidence = 0.95 if idx == 0 else 0.85
                    return {
                        "value": sex_value,
                        "confidence": confidence,
                        "explicit": True,
                        "match_text": match.group(0),
                    }

        return {
            "value": None,
            "confidence": 0.0,
            "explicit": False,
            "match_text": None,
        }

    def _extract_metric(self, query: str) -> Dict[str, Any]:
        """
        Extrait le type de métrique avec confiance

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        best_match = None
        best_confidence = 0.0
        match_text = None

        for metric_key, keywords in self.METRIC_PATTERNS.items():
            for idx, keyword in enumerate(keywords):
                if keyword in query:
                    # Confiance basée sur position dans liste (plus spécifique = plus haut)
                    confidence = 0.9 if idx == 0 else 0.8 - (idx * 0.05)
                    confidence = max(confidence, 0.5)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = metric_key
                        match_text = keyword

        return {
            "value": best_match,
            "confidence": best_confidence,
            "explicit": best_match is not None,
            "match_text": match_text,
        }

    def _derive_genetic_line(self, breed: str) -> str:
        """
        Dérive la lignée génétique du breed via breeds_registry

        Args:
            breed: Nom de breed normalisé

        Returns:
            Nom de la lignée génétique (ex: "broiler", "layer")
        """
        # Utiliser get_species pour obtenir le type
        species = self.breeds_registry.get_species(breed)

        if species:
            return species.capitalize()

        # Fallback: utiliser le breed lui-même
        return breed.capitalize() if breed else "Unknown"

    def _calculate_overall_confidence(self, entities: ExtractedEntities) -> float:
        """
        Calcule la confiance globale basée sur:
        - Nombre d'entités trouvées
        - Confiance individuelle de chaque entité
        """
        breakdown = entities.confidence_breakdown

        if not breakdown:
            return 0.0

        # Moyenne pondérée des confidences
        weights = {
            "breed": 0.3,
            "age": 0.25,
            "sex": 0.25,
            "metric": 0.2,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for entity_type, confidence in breakdown.items():
            weight = weights.get(entity_type, 0.1)
            weighted_sum += confidence * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # Confiance de base
        base_confidence = weighted_sum / total_weight

        # Bonus si plusieurs entités trouvées
        entity_count = entities.get_entity_count()
        bonus = min(0.1 * (entity_count - 1), 0.2)

        return min(base_confidence + bonus, 1.0)

    def extract_multiple_values(self, query: str, entity_type: EntityType) -> List[Any]:
        """
        Extrait potentiellement plusieurs valeurs d'un même type
        Utile pour requêtes comparatives (ex: "mâle et femelle")

        Args:
            query: Requête utilisateur
            entity_type: Type d'entité à extraire

        Returns:
            Liste de valeurs extraites
        """
        query_lower = query.lower()
        values = []

        if entity_type == EntityType.SEX:
            for sex_value, patterns in self.compiled_sex.items():
                for pattern in patterns:
                    if pattern.search(query_lower):
                        if sex_value not in values:
                            values.append(sex_value)
                        break

        elif entity_type == EntityType.BREED:
            for breed_name, patterns in self.compiled_breed.items():
                for pattern in patterns:
                    if pattern.search(query_lower):
                        # Normaliser via registry
                        normalized = self.breeds_registry.normalize_breed_name(
                            breed_name
                        )
                        if normalized and normalized not in values:
                            values.append(normalized)
                        break

        elif entity_type == EntityType.AGE:
            # Extraction de multiples âges
            for pattern in self.compiled_age:
                for match in pattern.finditer(query_lower):
                    try:
                        age = int(match.group(1))
                        if 0 <= age <= 100 and age not in values:
                            values.append(age)
                    except (ValueError, IndexError):
                        continue

        return values

    def validate_extraction(self, entities: ExtractedEntities) -> Dict[str, Any]:
        """
        Valide les entités extraites en utilisant breeds_registry

        Returns:
            Dict avec 'is_valid', 'errors', 'warnings'
        """
        errors = []
        warnings = []

        # Validation breed via registry
        if entities.breed:
            is_valid, canonical = self.breeds_registry.validate_breed(entities.breed)
            if not is_valid:
                errors.append(f"Race non reconnue: {entities.breed}")
            elif canonical != entities.breed:
                warnings.append(f"Race normalisée: {entities.breed} -> {canonical}")

        # Validation âge
        if entities.age_days is not None:
            if entities.age_days < 0:
                errors.append(f"Âge négatif: {entities.age_days}")
            elif entities.age_days > 100:
                warnings.append(f"Âge inhabituel: {entities.age_days} jours")

        # Validation confiance
        if entities.confidence < 0.3:
            warnings.append(
                f"Confiance faible ({entities.confidence:.2f}) - vérifier la requête"
            )

        # Validation cohérence breed + genetic_line via registry
        if entities.breed:
            expected_species = self.breeds_registry.get_species(entities.breed)
            if expected_species and entities.genetic_line:
                if expected_species.lower() != entities.genetic_line.lower():
                    warnings.append(
                        f"Incohérence breed/species: {entities.breed} "
                        f"(attendu: {expected_species}, trouvé: {entities.genetic_line})"
                    )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "confidence": entities.confidence,
        }


# Factory function
def create_entity_extractor(
    intents_config_path: str = "llm/config/intents.json",
) -> EntityExtractor:
    """Factory pour créer une instance EntityExtractor"""
    return EntityExtractor(intents_config_path)


# Tests unitaires
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    extractor = EntityExtractor()

    test_queries = [
        "Quel est le poids d'un Cobb 500 mâle à 21 jours ?",
        "FCR du Ross 308 femelle à 35j",
        "Différence de mortalité entre mâle et femelle",
        "Croissance d'un poulet de 0 à 42 jours",
        "Comparer ross308 et cobb500",
        "ISA Brown pondeuse",
    ]

    print("=" * 70)
    print("🧪 TESTS ENTITY EXTRACTOR - VERSION BREEDS_REGISTRY")
    print("=" * 70)

    # Test 1: Résumé breeds_registry
    print(
        f"\n📊 Breeds Registry: {len(extractor.breeds_registry.get_all_breeds())} races chargées"
    )
    summary = extractor.breeds_registry.get_breeds_summary()
    print(f"  - Broilers: {summary['broilers']}")
    print(f"  - Layers: {summary['layers']}")
    print(f"  - Breeders: {summary['breeders']}")

    print("\n" + "=" * 70)
    print("EXTRACTION TESTS")
    print("=" * 70)

    for query in test_queries:
        print(f"\n Query: {query}")
        entities = extractor.extract(query)
        print(f"  Breed: {entities.breed}")
        print(f"  Age: {entities.age_days}")
        print(f"  Sex: {entities.sex}")
        print(f"  Metric: {entities.metric_type}")
        print(f"  Genetic Line: {entities.genetic_line}")
        print(f"  Confidence: {entities.confidence:.2f}")
        print(f"  Count: {entities.get_entity_count()}")

        validation = extractor.validate_extraction(entities)
        status = "✅" if validation["is_valid"] else "❌"
        print(f"  {status} Valid: {validation['is_valid']}")

        if validation["errors"]:
            print(f"  ❌ Errors: {validation['errors']}")
        if validation["warnings"]:
            print(f"  ⚠️  Warnings: {validation['warnings']}")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS - Entity Extractor avec Breeds Registry")
    print("=" * 70)
