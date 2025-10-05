# -*- coding: utf-8 -*-
"""
entity_extractor.py - Extracteur d'entités centralisé
Remplace la logique éparpillée dans comparative_detector, query_preprocessor, etc.
Version 3.0 - Améliorations robustesse + support breeds_registry complet
"""

import re
import logging
from utils.types import Dict, Any, List, Optional, Set, Tuple
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

    Fonctionnalités v3.0:
    - Extraction breed, age, sex, metric avec patterns dynamiques depuis breeds_registry
    - Support complet des 51 races + tous aliases
    - Détection robuste dans phrases complètes
    - Conversion automatique semaines → jours
    - Gestion aliases complexes (avec /, -, etc.)
    - Limites d'âge adaptatives (broilers vs layers)
    - Validation complète via breeds_registry
    """

    # Patterns centralisés - Sex (statiques)
    SEX_PATTERNS = {
        "male": [
            r"\bm[aâ]les?\b",
            r"\bmale\b",
            r"\bcoq(?:s)?\b",
            r"\bmasculin\b",
            r"\brooster(?:s)?\b",
        ],
        "female": [
            r"\bfemelles?\b",
            r"\bfemale\b",
            r"\bpoule(?:s)?\b",
            r"\bf[ée]minin\b",
            r"\bhen(?:s)?\b",
        ],
        "mixed": [
            r"\bmixte\b",
            r"\bmixed\b",
            r"\bas[\s\-_]?hatched\b",
            r"\bsexes?\s+m[ée]lang[ée]s?\b",
        ],
    }

    # Patterns semaines (pour conversion automatique)
    WEEK_PATTERNS = [
        r"(\d+)\s*semaines?",
        r"(\d+)\s*weeks?",
        r"(\d+)\s*sem\b",
        r"(\d+)\s*w\b",
        r"(\d+)(?:e|ème|eme)?\s+semaine",
    ]

    # Patterns age en jours
    AGE_PATTERNS = [
        r"(\d+)\s*(?:jours?|days?|j)\b",
        r"à\s+(\d+)\s*(?:jours?|j)\b",
        r"age\s+(?:de\s+)?(\d+)",
        r"\b(\d+)\s*j\b",
        r"(\d+)(?:e|ème|eme)?\s+jour",
        r"day\s+(\d+)",
        r"\bD(\d+)\b",  # Format D35
    ]

    # Patterns métriques
    METRIC_PATTERNS = {
        "weight": [
            "poids",
            "weight",
            "body weight",
            "poids vif",
            "masse",
            "bw",
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
            "viabilité",
            "viability",
        ],
        "gain": [
            "gain",
            "croissance",
            "growth",
            "gmq",
            "daily gain",
            "gain quotidien",
            "adg",
        ],
        "feed_intake": [
            "consommation",
            "feed intake",
            "aliment",
            "ingéré",
            "intake",
        ],
        "production": [
            "production",
            "ponte",
            "laying",
            "œufs",
            "eggs",
            "egg production",
        ],
        "water": [
            "eau",
            "water",
            "hydratation",
            "water consumption",
        ],
    }

    # Mots-clés pour détection pondeuses/reproducteurs
    LAYER_KEYWORDS = [
        "ponte",
        "poule",
        "layer",
        "production",
        "œuf",
        "egg",
        "pondeuse",
        "laying",
    ]

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
            f"EntityExtractor v3.0 initialisé avec breeds_registry "
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

        # Compilation semaines (PRIORITÉ sur jours)
        self.compiled_weeks = [re.compile(p, re.IGNORECASE) for p in self.WEEK_PATTERNS]

        # Compilation age (statique)
        self.compiled_age = [re.compile(p, re.IGNORECASE) for p in self.AGE_PATTERNS]

        logger.debug(
            f"Patterns compilés: {len(self.compiled_breed)} breeds, "
            f"{len(self.compiled_sex)} sexes, "
            f"{len(self.compiled_weeks)} week patterns, "
            f"{len(self.compiled_age)} age patterns"
        )

    def _build_breed_patterns_from_registry(self):
        """
        Construit les patterns de breeds depuis le breeds_registry
        Version améliorée avec gestion aliases complexes
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
            f"Patterns de breeds générés pour {len(self.compiled_breed)} races "
            f"avec {sum(len(p) for p in self.compiled_breed.values())} patterns totaux"
        )

    def _create_pattern_from_text(self, text: str) -> str:
        """
        Crée un pattern regex flexible depuis un texte
        Version améliorée pour gérer aliases complexes

        Args:
            text: Texte source (ex: "ross 308", "308/308 FF", "cobb-500")

        Returns:
            Pattern regex string
        """
        # Cas spécial 1: Aliases avec slash (308/308 FF)
        if "/" in text:
            # "308/308 FF" → "308[\s/]*308[\s]*FF"
            parts = text.split("/")
            escaped_parts = [re.escape(part.strip()) for part in parts]
            pattern = r"[\s/]*".join(escaped_parts)
            # Utiliser lookahead/lookbehind au lieu de \b
            return r"(?<!\w)" + pattern + r"(?!\w)"

        # Cas spécial 2: Nombres seuls (308, 500, 700)
        if text.isdigit() and len(text) == 3:
            # Éviter de matcher "2308" ou "5000"
            return r"(?<!\d)" + re.escape(text) + r"(?!\d)"

        # Cas standard: Échapper et rendre flexible
        escaped = re.escape(text)

        # Remplacer les espaces par des patterns flexibles
        # Permet "ross 308", "ross308", "ross-308"
        pattern = escaped.replace(r"\ ", r"[\s\-_]*")

        # Remplacer tirets échappés par patterns flexibles
        pattern = pattern.replace(r"\-", r"[\s\-_]*")

        # Utiliser lookahead/lookbehind pour plus de flexibilité
        # Meilleur que \b pour gérer tirets et caractères spéciaux
        return r"(?<!\w)" + pattern + r"(?!\w)"

    def _get_max_age_for_query(self, query: str) -> int:
        """
        Détermine la limite d'âge maximale selon le contexte
        Version 3.0: Adaptatif selon type d'oiseau

        Args:
            query: Requête utilisateur

        Returns:
            Limite max en jours (100 pour broilers, 600 pour layers)
        """
        query_lower = query.lower()

        # Détecter si contexte pondeuse/reproducteur
        if any(keyword in query_lower for keyword in self.LAYER_KEYWORDS):
            logger.debug("Contexte pondeuse détecté → limite 600 jours")
            return 600

        # Détecter via breed si disponible
        for breed in self.breeds_registry.get_all_breeds():
            if breed.lower() in query_lower:
                species = self.breeds_registry.get_species(breed)
                if species in ["layer", "breeder"]:
                    logger.debug(f"Breed {breed} ({species}) → limite 600 jours")
                    return 600

        # Défaut: broilers
        return 100

    def extract(
        self, query: str, entities_hint: Dict[str, Any] = None
    ) -> ExtractedEntities:
        """
        Extraction complète des entités depuis une requête
        Version 3.0: Support phrases complètes + validation renforcée

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

        # Extraction age avec conversion semaines (si pas déjà défini)
        if not entities.age_days:
            age_result = self._extract_age_with_unit_conversion(query_lower, query)
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
            f"Extraction complétée: {entities.get_entity_count()} entités, "
            f"confiance={entities.confidence:.2f}"
        )

        return entities

    def _extract_breed(self, query: str) -> Dict[str, Any]:
        """
        Extrait la souche avec confiance en utilisant breeds_registry
        Version 3.0: Support phrases complètes + aliases complexes

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        # Trier races par longueur décroissante pour matcher les plus spécifiques
        sorted_breeds = sorted(
            self.compiled_breed.items(), key=lambda x: len(x[0]), reverse=True
        )

        for breed_name, patterns in sorted_breeds:
            for idx, pattern in enumerate(patterns):
                match = pattern.search(query)
                if match:
                    # Normaliser via breeds_registry pour obtenir le nom canonique
                    matched_text = match.group(0)
                    normalized = self.breeds_registry.normalize_breed_name(matched_text)

                    # Confiance basée sur la spécificité du pattern
                    # Pattern 0 = canonique (0.98), aliases (0.95 → 0.85)
                    confidence = 0.98 if idx == 0 else max(0.95 - (idx * 0.05), 0.75)

                    logger.debug(
                        f"Breed détecté: '{matched_text}' → '{normalized or breed_name}' "
                        f"(confiance={confidence:.2f})"
                    )

                    return {
                        "value": normalized or breed_name,
                        "confidence": confidence,
                        "explicit": True,
                        "match_text": matched_text,
                    }

        return {
            "value": None,
            "confidence": 0.0,
            "explicit": False,
            "match_text": None,
        }

    def _extract_age_with_unit_conversion(
        self, query: str, original_query: str = None
    ) -> Dict[str, Any]:
        """
        Extrait l'âge avec conversion automatique semaines → jours
        Version 3.0: Limites adaptatives + meilleure détection

        Priorité de détection:
        1. SEMAINES d'abord (3 semaines → 21 jours)
        2. JOURS ensuite (si pas de semaines détectées)

        Args:
            query: Requête en minuscules
            original_query: Requête originale (pour détection contexte)

        Returns:
            Dict avec 'value', 'confidence', 'explicit', 'match_text'
        """
        # Déterminer limite max selon contexte
        max_age = self._get_max_age_for_query(original_query or query)

        # 1️⃣ PRIORITÉ 1: Chercher SEMAINES d'abord
        for idx, pattern in enumerate(self.compiled_weeks):
            match = pattern.search(query)
            if match:
                try:
                    weeks = int(match.group(1))

                    # Validation plausibilité (0-85 semaines pour layers)
                    max_weeks = 85 if max_age == 600 else 20
                    if 0 <= weeks <= max_weeks:
                        days = weeks * 7
                        logger.info(
                            f"Conversion automatique: {weeks} semaine(s) → {days} jours"
                        )

                        return {
                            "value": days,
                            "confidence": 0.95,
                            "explicit": True,
                            "match_text": f"{match.group(0)} (converti: {days}j)",
                        }
                    else:
                        logger.warning(
                            f"Nombre de semaines hors plage: {weeks} "
                            f"(max: {max_weeks})"
                        )

                except (ValueError, IndexError) as e:
                    logger.debug(f"Erreur parsing semaines: {e}")
                    continue

        # 2️⃣ PRIORITÉ 2: Chercher JOURS si pas de semaines trouvées
        for idx, pattern in enumerate(self.compiled_age):
            match = pattern.search(query)
            if match:
                try:
                    age_value = int(match.group(1))

                    # Validation avec limite adaptative
                    if 0 <= age_value <= max_age:
                        confidence = 0.95 if idx == 0 else 0.9
                        logger.debug(f"Âge détecté: {age_value} jours (max={max_age})")

                        return {
                            "value": age_value,
                            "confidence": confidence,
                            "explicit": True,
                            "match_text": match.group(0),
                        }
                    else:
                        logger.warning(
                            f"Âge hors plage détecté: {age_value} "
                            f"(max={max_age}, contexte={'layer' if max_age == 600 else 'broiler'})"
                        )

                except (ValueError, IndexError) as e:
                    logger.debug(f"Erreur parsing age: {e}")
                    continue

        # 3️⃣ Aucun âge trouvé
        return {
            "value": None,
            "confidence": 0.0,
            "explicit": False,
            "match_text": None,
        }

    def _extract_age(self, query: str) -> Dict[str, Any]:
        """
        DÉPRÉCIÉ: Utiliser _extract_age_with_unit_conversion() à la place

        Méthode conservée pour compatibilité ascendante.
        Redirige vers la nouvelle méthode avec conversion.
        """
        logger.warning(
            "_extract_age() est déprécié, utiliser _extract_age_with_unit_conversion()"
        )
        return self._extract_age_with_unit_conversion(query)

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
                    confidence = 0.9 if idx == 0 else max(0.8 - (idx * 0.05), 0.5)

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
            Nom de la lignée génétique (ex: "Broiler", "Layer")
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
        Version 3.0: Évite duplications avec tracking positions
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
            # Tracking des positions déjà matchées pour éviter duplications
            matched_positions: Set[Tuple[int, int]] = set()

            # 1. Chercher semaines D'ABORD
            for pattern in self.compiled_weeks:
                for match in pattern.finditer(query_lower):
                    span = match.span()
                    if span not in matched_positions:
                        try:
                            weeks = int(match.group(1))
                            max_age = self._get_max_age_for_query(query)
                            max_weeks = 85 if max_age == 600 else 20

                            if 0 <= weeks <= max_weeks:
                                days = weeks * 7
                                if days not in values:
                                    values.append(days)
                                    matched_positions.add(span)
                                    logger.debug(
                                        f"Multi-age: {weeks}w → {days}d "
                                        f"(pos {span})"
                                    )
                        except (ValueError, IndexError):
                            continue

            # 2. Chercher jours ENSUITE (skip si position déjà matchée)
            for pattern in self.compiled_age:
                for match in pattern.finditer(query_lower):
                    span = match.span()
                    # Vérifier overlap avec positions déjà matchées
                    overlaps = any(
                        span[0] <= pos[1] and span[1] >= pos[0]
                        for pos in matched_positions
                    )

                    if not overlaps:
                        try:
                            age = int(match.group(1))
                            max_age = self._get_max_age_for_query(query)

                            if 0 <= age <= max_age and age not in values:
                                values.append(age)
                                matched_positions.add(span)
                                logger.debug(f"Multi-age: {age}d (pos {span})")
                        except (ValueError, IndexError):
                            continue

        return sorted(values) if entity_type == EntityType.AGE else values

    def validate_extraction(self, entities: ExtractedEntities) -> Dict[str, Any]:
        """
        Valide les entités extraites en utilisant breeds_registry
        Version 3.0: Validation renforcée

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

        # Validation âge avec limites adaptatives
        if entities.age_days is not None:
            if entities.age_days < 0:
                errors.append(f"Âge négatif: {entities.age_days}")
            elif entities.age_days > 600:
                errors.append(f"Âge hors limites: {entities.age_days} jours (max: 600)")
            elif entities.age_days > 100:
                # Vérifier si contexte pondeuse
                if entities.breed:
                    species = self.breeds_registry.get_species(entities.breed)
                    if species == "broiler":
                        warnings.append(
                            f"Âge inhabituel pour broiler: {entities.age_days} jours "
                            f"(max recommandé: 100)"
                        )
                else:
                    warnings.append(
                        f"Âge élevé: {entities.age_days} jours "
                        f"(attendu <100 pour broilers)"
                    )

        # Validation confiance
        if entities.confidence < 0.3:
            warnings.append(
                f"Confiance faible ({entities.confidence:.2f}) - vérifier la requête"
            )

        # Validation cohérence breed + genetic_line via registry
        if entities.breed and entities.genetic_line:
            expected_species = self.breeds_registry.get_species(entities.breed)
            if expected_species:
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
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")

    print("=" * 70)
    print("INITIALISATION ENTITY EXTRACTOR v3.0")
    print("=" * 70)

    extractor = EntityExtractor()

    # Résumé breeds_registry
    print(f"\nBreeds Registry: {len(extractor.breeds_registry.get_all_breeds())} races")
    summary = extractor.breeds_registry.get_breeds_summary()
    print(f"  - Broilers: {summary['broilers']}")
    print(f"  - Layers: {summary['layers']}")
    print(f"  - Breeders: {summary['breeders']}")
    print(f"  - Total aliases: {summary['aliases_total']}")

    print("\n" + "=" * 70)
    print("TESTS CRITIQUES - VERSION 3.0")
    print("=" * 70)

    critical_tests = {
        "Test 11 - Phrase longue": "J'élève du Cobb 500 dans mon exploitation et j'aimerais connaître le poids",
        "Test 12 - Conversion semaines": "Poids à 3 semaines pour Ross 308",
        "Alias complexe avec /": "Performance 308/308 FF mâles à 35 jours",
        "Race rare slow-growing": "Croissance Sasso X44 à 56 jours",
        "Nouvelle race Arbor Acres": "FCR Arbor Acres à 42 jours",
        "Alias numérique seul": "Poids 500 à 35j",
        "Pondeuse âge élevé": "Production ISA Brown à 200 jours",
        "Multiple âges": "Comparer 2 semaines et 35 jours",
        "Format D35": "Poids Ross 308 D35",
        "Alias JA87": "Performance Hubbard JA87",
    }

    for test_name, query in critical_tests.items():
        print(f"\n{test_name}:")
        print(f"  Query: {query}")

        entities = extractor.extract(query)
        validation = extractor.validate_extraction(entities)

        print(f"  Breed: {entities.breed} {'✓' if entities.breed else '✗'}")
        print(f"  Age: {entities.age_days} {'✓' if entities.age_days else '✗'}")

        if entities.raw_matches.get("age") and "converti" in str(
            entities.raw_matches.get("age")
        ):
            print(f"  Age (raw): {entities.raw_matches['age']}")

        print(f"  Sex: {entities.sex}")
        print(f"  Metric: {entities.metric_type}")
        print(f"  Confidence: {entities.confidence:.2f}")

        status = "PASS" if validation["is_valid"] else "FAIL"
        print(f"  Status: {status}")

        if validation["errors"]:
            print(f"  Errors: {validation['errors']}")
        if validation["warnings"]:
            print(f"  Warnings: {validation['warnings']}")

    print("\n" + "=" * 70)
    print("TEST EXTRACTION MULTIPLES AGES")
    print("=" * 70)

    multi_queries = [
        "Comparer 2 semaines et 35 jours",
        "Performance de 3 à 6 semaines",
        "Entre 14 jours et 4 semaines",
    ]

    for query in multi_queries:
        print(f"\nQuery: {query}")
        ages = extractor.extract_multiple_values(query, EntityType.AGE)
        print(f"  Ages extraits: {ages}")

    print("\n" + "=" * 70)
    print("TEST COMPARAISON BREEDS")
    print("=" * 70)

    comp_query = "Comparer Ross 308 et Cobb 500"
    print(f"\nQuery: {comp_query}")
    breeds = extractor.extract_multiple_values(comp_query, EntityType.BREED)
    print(f"  Breeds extraits: {breeds}")

    if len(breeds) == 2:
        compatible, reason = extractor.breeds_registry.are_comparable(
            breeds[0], breeds[1]
        )
        print(f"  Comparables: {compatible} ({reason})")

    print("\n" + "=" * 70)
    print("TESTS TERMINÉS - Entity Extractor v3.0")
    print("=" * 70)
