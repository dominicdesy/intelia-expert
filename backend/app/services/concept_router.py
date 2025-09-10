# rag/concept_router.py
"""
Router intelligent pour classifier les requêtes utilisateur
Détermine si une question nécessite le PerfStore, RAG vectoriel, ou clarification
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QueryRoute(Enum):
    """Routes possibles pour une requête"""
    PERF_STORE = "perf_store"  # Lookup déterministe des données de performance
    RAG_VECTOR = "rag_vector"  # Recherche vectorielle contextuelle
    HYBRID = "hybrid"  # Combinaison PerfStore + RAG
    CLARIFICATION = "clarification"  # Question ambiguë nécessitant clarification

@dataclass
class QueryIntent:
    """Intention détectée pour une requête"""
    route: QueryRoute
    confidence: float
    detected_concepts: Dict[str, float]
    filters: Dict[str, Any]
    clarification_needed: Optional[str] = None
    reasoning: str = ""

class ConceptDetector:
    """
    Détecteur de concepts aviaires dans les requêtes
    Approche adaptive sans hardcoding excessif
    """
    
    def __init__(self):
        # Concepts de base pour la classification
        self.performance_concepts = {
            "weight": ["weight", "poids", "bw", "body weight", "live weight", "masse"],
            "growth": ["growth", "gain", "croissance", "adg", "daily gain", "gain quotidien"],
            "fcr": ["fcr", "feed conversion", "conversion alimentaire", "ic", "indice consommation"],
            "mortality": ["mortality", "mortalité", "mort", "death", "viabilité", "viability"],
            "feed_intake": ["intake", "consommation", "consumption", "ingestion"],
            "targets": ["target", "objectif", "goal", "standard", "norme", "specification"],
            "performance": ["performance", "résultat", "result", "efficacité"]
        }
        
        self.nutrition_concepts = {
            "protein": ["protein", "protéine", "crude protein", "cp"],
            "energy": ["energy", "énergie", "me", "metabolizable energy", "kcal"],
            "amino_acids": ["lysine", "methionine", "threonine", "tryptophan", "acides aminés"],
            "minerals": ["calcium", "phosphorus", "sodium", "phosphore", "minéraux"],
            "vitamins": ["vitamin", "vitamine", "vit", "supplement"],
            "feed": ["feed", "aliment", "diet", "ration", "formulation"]
        }
        
        self.health_concepts = {
            "disease": ["disease", "maladie", "pathology", "pathologie", "infection"],
            "vaccine": ["vaccine", "vaccin", "vaccination", "immunization"],
            "treatment": ["treatment", "traitement", "medication", "médicament", "antibiotic"],
            "biosecurity": ["biosecurity", "biosécurité", "hygiene", "hygiène", "disinfection"],
            "welfare": ["welfare", "bien-être", "stress", "comfort", "confort"]
        }
        
        self.management_concepts = {
            "housing": ["housing", "logement", "cage", "aviary", "volière", "density"],
            "environment": ["temperature", "température", "humidity", "humidité", "ventilation"],
            "lighting": ["light", "lumière", "éclairage", "photoperiod", "photopériode"],
            "water": ["water", "eau", "drinking", "abreuvement", "nipple"]
        }
        
        self.species_indicators = {
            "broiler": ["broiler", "poulet de chair", "chair", "meat", "viande"],
            "layer": ["layer", "pondeuse", "laying", "ponte", "egg", "oeuf"],
            "breeder": ["breeder", "reproducteur", "parent", "breeding", "reproduction"],
            "duck": ["duck", "canard", "waterfowl"],
            "turkey": ["turkey", "dinde", "dindon"]
        }
        
        self.line_indicators = {
            "ross": ["ross", "308", "708", "ap95"],
            "cobb": ["cobb", "500", "700"],
            "hubbard": ["hubbard", "jv", "classic"],
            "lohmann": ["lohmann", "brown", "classic", "lite"],
            "hyline": ["hyline", "hy-line", "w36", "w80", "brown"],
            "isabrown": ["isa", "brown", "warren"]
        }
    
    def detect_concepts(self, query: str) -> Dict[str, float]:
        """
        Détecte les concepts présents dans une requête
        
        Returns:
            Dict avec scores de confiance pour chaque catégorie de concept
        """
        query_lower = query.lower()
        
        concept_scores = {
            "performance": self._score_concept_category(query_lower, self.performance_concepts),
            "nutrition": self._score_concept_category(query_lower, self.nutrition_concepts),
            "health": self._score_concept_category(query_lower, self.health_concepts),
            "management": self._score_concept_category(query_lower, self.management_concepts),
            "species_specific": self._score_concept_category(query_lower, self.species_indicators),
            "line_specific": self._score_concept_category(query_lower, self.line_indicators)
        }
        
        # Détection de questions numériques/quantitatives
        concept_scores["quantitative"] = self._detect_quantitative_intent(query_lower)
        
        # Détection de demandes de comparaison
        concept_scores["comparison"] = self._detect_comparison_intent(query_lower)
        
        return concept_scores
    
    def _score_concept_category(self, query: str, concept_dict: Dict[str, List[str]]) -> float:
        """Score une catégorie de concepts"""
        total_matches = 0
        total_concepts = len(concept_dict)
        
        for concept, keywords in concept_dict.items():
            if any(keyword in query for keyword in keywords):
                total_matches += 1
        
        return total_matches / total_concepts if total_concepts > 0 else 0.0
    
    def _detect_quantitative_intent(self, query: str) -> float:
        """Détecte les intentions quantitatives (données chiffrées)"""
        quantitative_patterns = [
            r'\d+\s*(g|kg|lb|gram|kilo)',  # Poids avec unités
            r'\d+\s*(day|days|week|weeks|jour|jours|semaine)',  # Âge
            r'\d+\s*%',  # Pourcentages
            r'combien|how much|how many|quel.*poids|what.*weight',  # Questions quantitatives
            r'target|objectif|standard|norme|specification',  # Références aux standards
            r'compare|comparer|versus|vs|différence|écart'  # Comparaisons
        ]
        
        matches = sum(1 for pattern in quantitative_patterns if re.search(pattern, query))
        return min(matches / 3, 1.0)  # Normaliser sur 3 patterns max
    
    def _detect_comparison_intent(self, query: str) -> float:
        """Détecte les intentions de comparaison"""
        comparison_patterns = [
            r'compare|comparer|comparison|comparaison',
            r'versus|vs|contre|against',
            r'différence|difference|écart|gap',
            r'meilleur|better|best|optimal',
            r'which|quel|lequel|quelle'
        ]
        
        matches = sum(1 for pattern in comparison_patterns if re.search(pattern, query))
        return min(matches / 2, 1.0)

class ConceptRouter:
    """
    Router principal pour classifier les requêtes utilisateur
    Détermine la route optimale basée sur l'analyse conceptuelle
    """
    
    def __init__(self):
        self.concept_detector = ConceptDetector()
    
    def analyze_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryIntent:
        """
        Analyse une requête et détermine la route optimale
        
        Args:
            query: Requête utilisateur
            context: Contexte optionnel (historique conversation, filtres actifs)
            
        Returns:
            QueryIntent avec route recommandée et métadonnées
        """
        # Détection des concepts
        concepts = self.concept_detector.detect_concepts(query)
        
        # Extraction des filtres implicites
        filters = self._extract_filters(query, concepts)
        
        # Détermination de la route
        route_decision = self._determine_route(concepts, filters, context)
        
        return QueryIntent(
            route=route_decision["route"],
            confidence=route_decision["confidence"],
            detected_concepts=concepts,
            filters=filters,
            clarification_needed=route_decision.get("clarification"),
            reasoning=route_decision["reasoning"]
        )
    
    def _determine_route(self, 
                        concepts: Dict[str, float], 
                        filters: Dict[str, Any],
                        context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Détermine la route optimale basée sur l'analyse conceptuelle
        """
        # Score quantitatif élevé + performance → PerfStore direct
        if concepts["quantitative"] > 0.6 and concepts["performance"] > 0.4:
            return {
                "route": QueryRoute.PERF_STORE,
                "confidence": 0.8,
                "reasoning": "Question quantitative sur performance → lookup direct PerfStore"
            }
        
        # Question très spécifique (espèce + lignée + métrique) → PerfStore
        if (concepts["species_specific"] > 0.5 and 
            concepts["line_specific"] > 0.3 and 
            concepts["performance"] > 0.3):
            return {
                "route": QueryRoute.PERF_STORE,
                "confidence": 0.75,
                "reasoning": "Question spécifique (espèce+lignée+performance) → PerfStore"
            }
        
        # Comparaison avec données chiffrées → Hybride
        if concepts["comparison"] > 0.5 and concepts["quantitative"] > 0.4:
            return {
                "route": QueryRoute.HYBRID,
                "confidence": 0.7,
                "reasoning": "Comparaison avec données quantitatives → PerfStore + RAG contextuel"
            }
        
        # Questions générales avec contexte → RAG vectoriel
        if concepts["performance"] > 0.3 or concepts["nutrition"] > 0.3 or concepts["health"] > 0.3:
            return {
                "route": QueryRoute.RAG_VECTOR,
                "confidence": 0.6,
                "reasoning": "Question contextuelle → recherche vectorielle RAG"
            }
        
        # Question ambiguë → Clarification
        max_concept_score = max(concepts.values())
        if max_concept_score < 0.3:
            return {
                "route": QueryRoute.CLARIFICATION,
                "confidence": 0.8,
                "clarification": self._generate_clarification(concepts, filters),
                "reasoning": "Question ambiguë → clarification nécessaire"
            }
        
        # Fallback → RAG vectoriel
        return {
            "route": QueryRoute.RAG_VECTOR,
            "confidence": 0.4,
            "reasoning": "Route par défaut → recherche vectorielle RAG"
        }
    
    def _extract_filters(self, query: str, concepts: Dict[str, float]) -> Dict[str, Any]:
        """
        Extrait les filtres implicites de la requête
        """
        query_lower = query.lower()
        filters = {}
        
        # Extraction espèce
        for species, keywords in self.concept_detector.species_indicators.items():
            if any(keyword in query_lower for keyword in keywords):
                filters["species"] = species
                break
        
        # Extraction lignée
        for line, keywords in self.concept_detector.line_indicators.items():
            if any(keyword in query_lower for keyword in keywords):
                filters["line"] = line
                break
        
        # Extraction sexe
        if any(word in query_lower for word in ["male", "mâle", "coq", "rooster"]):
            filters["sex"] = "male"
        elif any(word in query_lower for word in ["female", "femelle", "hen", "poule"]):
            filters["sex"] = "female"
        
        # Extraction âge
        age_match = re.search(r'(\d+)\s*(day|days|jour|jours|week|weeks|semaine)', query_lower)
        if age_match:
            age_value = int(age_match.group(1))
            unit = age_match.group(2)
            
            if "week" in unit or "semaine" in unit:
                age_days = age_value * 7
            else:
                age_days = age_value
            
            filters["age_days"] = age_days
        
        # Extraction métriques spécifiques
        metrics = []
        for metric_category, keywords_dict in self.concept_detector.performance_concepts.items():
            if any(keyword in query_lower for keyword in keywords_dict):
                metrics.append(metric_category)
        
        if metrics:
            filters["metrics"] = metrics
        
        return filters
    
    def _generate_clarification(self, concepts: Dict[str, float], filters: Dict[str, Any]) -> str:
        """
        Génère une question de clarification intelligente
        """
        if not filters.get("species"):
            return "De quelle espèce parlez-vous ? (poulet de chair, pondeuse, reproducteur, etc.)"
        
        if concepts["performance"] > 0.2 and not filters.get("metrics"):
            return "Quelles données de performance vous intéressent ? (poids, gain, FCR, mortalité, etc.)"
        
        if concepts["quantitative"] > 0.3 and not filters.get("age_days"):
            return "Pour quel âge souhaitez-vous ces informations ?"
        
        return "Pouvez-vous préciser votre question ? Par exemple, l'espèce, l'âge, ou le type d'information recherché."

# Factory function
def create_concept_router() -> ConceptRouter:
    """
    Factory pour créer un router configuré
    """
    return ConceptRouter()