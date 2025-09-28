# -*- coding: utf-8 -*-
"""
query_validator.py - Validation de complétude des requêtes
Vérifie si une requête contient toutes les entités nécessaires
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Résultat de validation"""

    is_complete: bool
    missing_entities: List[str]
    clarification_message: str
    confidence: float = 1.0


class QueryValidator:
    """Validateur de complétude des requêtes utilisateur"""

    # Entités requises par type de requête (ASSOUPLIES)
    REQUIRED_ENTITIES = {
        "comparative": ["breed"],  # Assouplir: age non obligatoire
        "metric": ["breed"],  # Assouplir: age non obligatoire
        "temporal_reverse": ["breed", "metric_type"],  # Pas d'âge requis
        "document": [],  # Très permissif
        "general": [],  # Très permissif
        "performance_query": ["breed"],  # Ancien système maintenu pour compatibilité
        "comparison_query": ["breed"],  # Ancien système maintenu pour compatibilité
        "calculation_query": ["breed"],  # Ancien système maintenu pour compatibilité
        "nutrition_query": ["breed"],  # Age optionnel pour nutrition
        "carcass_query": ["breed"],  # Assouplir: weight non obligatoire
    }

    # Métriques nécessitant un âge
    AGE_DEPENDENT_METRICS = {
        "body_weight",
        "weight",
        "poids",
        "feed_conversion_ratio",
        "fcr",
        "ic",
        "conversion",
        "daily_gain",
        "gain",
        "croissance",
        "feed_intake",
        "intake",
        "consommation",
    }

    def __init__(self):
        """Initialise le validateur"""
        pass

    def validate_query_completeness(
        self, query: str, entities: Dict[str, str], query_type: str = "metric"
    ) -> Dict[str, Any]:
        """
        Validation assouplie pour les requêtes

        Args:
            query: Requête originale de l'utilisateur
            entities: Entités extraites par EntityExtractor
            query_type: Type de requête détecté

        Returns:
            Dict avec clés: valid, complete, missing_entities, warnings, suggestion
        """
        # CORRECTION: Normaliser les entités age_days → age
        normalized_entities = entities.copy()
        if "age_days" in entities and "age" not in entities:
            normalized_entities["age"] = entities["age_days"]

        # Si query_type n'est pas fourni, le détecter
        if query_type == "metric":
            query_type = self._detect_query_type(query)

        # Entités essentielles pour différents types de requêtes
        requirements = self.REQUIRED_ENTITIES.get(query_type, ["breed"])

        missing = []
        for req in requirements:
            if not normalized_entities.get(req):
                missing.append(req)

        # NOUVEAU: Validation contextuelle intelligente
        warnings = []
        if not missing:
            # Vérification de cohérence plutôt que de complétude
            coherence_issues = self._check_entity_coherence(normalized_entities)
            if coherence_issues:
                warnings = coherence_issues

        result = {
            "valid": len(missing) == 0,
            "complete": len(missing) == 0,
            "missing_entities": missing,
            "warnings": warnings,
            "is_complete": len(missing) == 0,  # Pour compatibilité avec ancien système
            "confidence": 0.8 if missing else 1.0,
            "clarification_message": (
                self.generate_clarification_prompt(missing, query) if missing else ""
            ),
        }

        if missing:
            result["suggestion"] = self._generate_completion_suggestion(missing)

        return result

    def _check_entity_coherence(self, entities: Dict[str, str]) -> List[str]:
        """Vérifications de cohérence plutôt que de complétude"""
        warnings = []

        # Vérifier les âges aberrants
        if entities.get("age_days"):
            try:
                age = int(entities["age_days"])
                if age > 100:
                    warnings.append(f"Âge élevé détecté: {age} jours")
                elif age < 0:
                    warnings.append(f"Âge négatif: {age} jours")
            except ValueError:
                warnings.append(f"Âge invalide: {entities['age_days']}")

        # Vérifier les souches connues
        if entities.get("breed"):
            known_breeds = ["cobb 500", "ross 308", "500", "308", "cobb", "ross"]
            breed_lower = entities["breed"].lower()
            if not any(kb in breed_lower for kb in known_breeds):
                warnings.append(f"Souche non reconnue: {entities['breed']}")

        # Vérifier cohérence poids/âge pour carcasse
        if (
            entities.get("weight")
            and not entities.get("age_days")
            and not entities.get("age")
        ):
            warnings.append(
                "Poids spécifié sans âge - calculs de rendement peuvent être imprécis"
            )

        return warnings

    def _generate_completion_suggestion(self, missing_entities: List[str]) -> str:
        """Génère une suggestion pour compléter les entités manquantes"""
        suggestions = {
            "breed": "Spécifiez une souche (ex: Cobb 500, Ross 308)",
            "age": "Indiquez l'âge en jours",
            "metric_type": "Précisez la métrique recherchée",
            "weight": "Indiquez le poids vif",
            "sex": "Spécifiez le sexe (mâle/femelle/mixte)",
        }

        if len(missing_entities) == 1:
            entity = missing_entities[0]
            return suggestions.get(entity, f"Spécifiez {entity}")
        else:
            return "Spécifiez: " + ", ".join(
                [suggestions.get(e, e) for e in missing_entities]
            )

    def _detect_query_type(self, query: str) -> str:
        """Détecte le type de requête basé sur le contenu"""
        query_lower = query.lower()

        if any(
            word in query_lower
            for word in ["compare", "comparaison", "vs", "versus", "différence"]
        ):
            return "comparative"
        elif any(word in query_lower for word in ["nutrition", "aliment", "régime"]):
            return "nutrition_query"
        elif any(word in query_lower for word in ["rendement", "carcasse", "abattage"]):
            return "carcass_query"
        elif any(word in query_lower for word in ["calcul", "calculer"]):
            return "calculation_query"
        elif any(word in query_lower for word in ["document", "rapport", "fichier"]):
            return "document"
        else:
            return "metric"

    def identify_missing_entities(
        self, entities: Dict[str, str], query_type: str, query: str
    ) -> List[str]:
        """
        Identifie les entités manquantes pour une requête

        Args:
            entities: Entités extraites (déjà normalisées)
            query_type: Type de requête
            query: Requête originale

        Returns:
            Liste d'entités manquantes
        """
        missing = []

        # CORRECTION: Vérifier si la question nécessite vraiment breed+age
        if not self._should_require_breed_and_age(query):
            # Questions générales : pas besoin de breed/age spécifiques
            return missing

        required = self.REQUIRED_ENTITIES.get(query_type, ["breed"])

        # Vérifier entités de base (entities déjà normalisées dans validate_query_completeness)
        for entity in required:
            if entity not in entities or not entities[entity]:
                missing.append(entity)

        # Vérifier si métrique nécessite un âge (plus souple maintenant)
        if self._query_needs_age(query) and "age" not in entities:
            # Ne plus ajouter age comme manquant automatiquement
            # Juste un warning si nécessaire
            pass

        # Cas spécial: comparaison nécessite deux valeurs
        if "comparison" in query_type.lower() or self._is_comparative(query):
            if not self._has_comparison_dimension(entities):
                # Ne plus bloquer, juste suggérer
                pass

        return missing

    def _should_require_breed_and_age(self, query: str) -> bool:
        """Détermine si la question nécessite vraiment breed+age spécifiques"""
        query_lower = query.lower()

        # Patterns pour questions générales qui ne nécessitent pas breed/age
        general_question_patterns = [
            "comment calculer",
            "qu'est-ce que",
            "symptômes",
            "température optimale",
            "température idéale",
            "définition",
            "expliquer",
            "pourquoi",
            "comment faire",
            "que signifie",
            "principe",
            "méthode",
            "technique",
            "procédure",
            "facteurs",
            "causes",
            "prévention",
            "traitement",
        ]

        # Si c'est une question générale, pas besoin de breed/age
        if any(pattern in query_lower for pattern in general_question_patterns):
            return False

        # Si la question mentionne explicitement une souche ou un âge, alors les exiger
        specific_patterns = [
            "ross",
            "cobb",
            "hubbard",  # souches
            "jour",
            "jours",
            "semaine",
            "semaines",  # âges
            "mâle",
            "femelle",
            "male",
            "female",  # sexes
        ]

        if any(pattern in query_lower for pattern in specific_patterns):
            return True

        # Par défaut, pour les questions ambiguës, ne pas exiger breed/age
        return False

    def _query_needs_age(self, query: str) -> bool:
        """Vérifie si la requête nécessite un âge"""
        query_lower = query.lower()

        # Vérifier présence de métriques dépendantes de l'âge
        for metric in self.AGE_DEPENDENT_METRICS:
            if metric in query_lower:
                return True

        # Patterns nécessitant un âge
        age_patterns = [
            "poids",
            "weight",
            "conversion",
            "fcr",
            "ic",
            "gain",
            "consommation",
            "intake",
        ]

        return any(pattern in query_lower for pattern in age_patterns)

    def _is_comparative(self, query: str) -> bool:
        """Détecte si c'est une requête comparative"""
        query_lower = query.lower()

        comparative_keywords = [
            "compare",
            "comparaison",
            "différence",
            "vs",
            "versus",
            "mieux",
            "meilleur",
            "plus",
            "moins",
            "entre",
            "et",
        ]

        return any(keyword in query_lower for keyword in comparative_keywords)

    def _has_comparison_dimension(self, entities: Dict[str, str]) -> bool:
        """Vérifie si les entités contiennent une dimension de comparaison claire"""

        # Si plusieurs souches mentionnées
        if "breed" in entities and "," in str(entities.get("breed", "")):
            return True

        # Si sexes multiples
        if "sex" in entities and "," in str(entities.get("sex", "")):
            return True

        # Si plusieurs âges
        if "age_days" in entities and "," in str(entities.get("age_days", "")):
            return True

        return False

    def generate_clarification_prompt(
        self, missing_entities: List[str], original_query: str
    ) -> str:
        """
        Génère un message de clarification pour les entités manquantes

        Args:
            missing_entities: Liste d'entités manquantes
            original_query: Requête originale

        Returns:
            Message de clarification
        """
        if not missing_entities:
            return ""

        # Messages de clarification par entité
        clarifications = {
            "breed": "Quelle souche vous intéresse? (Ross 308, Cobb 500, etc.)",
            "age": "À quel âge (en jours)?",
            "sex": "Quel sexe? (mâle, femelle, ou mixte)",
            "weight": "Quel poids vif?",
            "metric_type": "Quelle métrique vous intéresse?",
            "comparison_dimension": "Que souhaitez-vous comparer exactement?",
        }

        # Construire message
        if len(missing_entities) == 1:
            entity = missing_entities[0]
            return f"Pour répondre précisément à votre question, j'ai besoin d'une information supplémentaire: {clarifications.get(entity, entity)}?"
        else:
            messages = [clarifications.get(e, e) for e in missing_entities]
            return (
                "Pour répondre précisément, j'ai besoin de clarifications:\n- "
                + "\n- ".join(messages)
            )

    def validate_entity_values(self, entities: Dict[str, str]) -> Dict[str, bool]:
        """
        Valide les valeurs des entités extraites

        Args:
            entities: Entités extraites

        Returns:
            Dict avec validation par entité
        """
        validation = {}

        # Validation âge
        if "age_days" in entities:
            try:
                age = int(entities["age_days"])
                validation["age_days"] = 0 <= age <= 100  # Plage raisonnable
            except ValueError:
                validation["age_days"] = False

        # Validation souche
        if "breed" in entities:
            valid_breeds = ["308/308 FF", "500", "ross 308", "cobb 500", "ross", "cobb"]
            breed_lower = entities["breed"].lower()
            validation["breed"] = any(vb in breed_lower for vb in valid_breeds)

        # Validation sexe
        if "sex" in entities:
            valid_sex = [
                "male",
                "female",
                "as_hatched",
                "mixed",
                "mâle",
                "femelle",
                "mixte",
            ]
            validation["sex"] = entities["sex"].lower() in valid_sex

        return validation

    def is_ambiguous_query(self, query: str, entities: Dict[str, str]) -> bool:
        """
        Détecte si une requête est trop ambiguë

        Args:
            query: Requête utilisateur
            entities: Entités extraites

        Returns:
            True si ambiguë
        """
        query_lower = query.lower()

        # Patterns ambigus
        ambiguous_patterns = [
            "le meilleur poulet",
            "quel poulet",
            "lequel",
            "combien",
            "performances",
            "données",
        ]

        # Si requête très courte avec pattern ambigu
        if len(query.split()) < 5:
            if any(pattern in query_lower for pattern in ambiguous_patterns):
                # Et peu d'entités extraites
                if len(entities) < 2:
                    return True

        # Si aucune entité principale (plus souple maintenant)
        if "breed" not in entities and "strain" not in entities:
            # Ne plus considérer comme ambigu automatiquement
            # Peut être une question générale valide
            return False

        return False
