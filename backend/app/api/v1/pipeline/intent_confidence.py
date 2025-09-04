# app/api/v1/pipeline/intent_confidence.py - NOUVEAU FICHIER
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class IntentCandidate:
    """Candidat d'intention avec métadonnées"""
    intent: str
    confidence: float
    evidence: List[str]
    domain: str
    ambiguity_factors: List[str]
    context_support: float

class IntentConfidenceAnalyzer:
    """
    Analyseur de confiance pour classification d'intentions.
    Gère les ambiguïtés, intentions multiples et scoring de confiance.
    """
    
    def __init__(self):
        # Patterns d'ambiguïté communs
        self.ambiguity_patterns = {
            "multiple_species": [
                r"\b(broiler|chair)\b.*\b(pondeuse|layer)\b",
                r"\b(pondeuse|layer)\b.*\b(broiler|chair)\b"
            ],
            "vague_terms": [
                r"\bmes\s+(?:poulets?|poules?|oiseaux)\b",
                r"\b(?:ça|cela)\s+(?:va|marche|fonctionne)\b",
                r"\bcomment\s+(?:faire|ça)\b"
            ],
            "temporal_ambiguity": [
                r"\bmaintenant\b",
                r"\bactuel(?:lement)?\b",
                r"\ben\s+ce\s+moment\b"
            ],
            "quantitative_ambiguity": [
                r"\b(?:beaucoup|peu|assez|trop)\b",
                r"\b(?:normal|correct|bon)\b"
            ]
        }
        
        # Patterns de confiance élevée
        self.high_confidence_patterns = {
            "specific_breeds": r"\b(ross\s*30[8|5|7]|cobb\s*[5|7]0+|isa\s*brown|lohmann|hy-?line)\b",
            "specific_metrics": r"\b(fcr|iep|epef)\b",
            "specific_ages": r"\b(?:à|age)\s*(?:de\s*)?(\d{1,3})\s*(?:jours?|j|semaines?)\b",
            "specific_weights": r"\b(\d{3,4})\s*g(?:rammes?)?\b",
            "specific_problems": r"\b(mortalité|diarrhée|boiterie|picage)\b"
        }
        
        # Mapping domaines pour regroupement
        self.domain_mapping = {
            "performance": ["weight_target", "fcr_target", "production_rate", "mortality_rate"],
            "nutrition": ["protein_requirements", "energy_requirements", "feed_consumption"],
            "diagnosis": ["performance_issue", "health_issue", "production_drop"],
            "environment": ["temperature_control", "ventilation", "lighting"],
            "equipment": ["feeders", "drinkers"],
            "economics": ["cost_analysis", "iep_calculation"],
            "compliance": ["regulations"]
        }

    def analyze_intent_confidence(
        self, 
        question: str, 
        context: Dict[str, Any],
        intent_candidates: Dict[str, float]
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyse la confiance des intentions candidates
        
        Args:
            question: Question de l'utilisateur
            context: Contexte extrait
            intent_candidates: Dict {intent: score}
            
        Returns:
            (best_intent, confidence, analysis_details)
        """
        
        if not intent_candidates:
            return "general.unknown", 0.1, {"reason": "no_candidates"}
        
        # 1. Analyser chaque candidat
        analyzed_candidates = []
        for intent, base_score in intent_candidates.items():
            candidate = self._analyze_single_intent(intent, base_score, question, context)
            analyzed_candidates.append(candidate)
        
        # 2. Détecter ambiguïtés
        ambiguity_analysis = self._detect_ambiguities(question, analyzed_candidates)
        
        # 3. Calculer scores finaux
        final_candidates = self._calculate_final_scores(
            analyzed_candidates, ambiguity_analysis, context
        )
        
        # 4. Sélectionner meilleur candidat
        best_candidate = max(final_candidates, key=lambda x: x.confidence)
        
        # 5. Calculer confiance globale
        global_confidence = self._calculate_global_confidence(
            best_candidate, final_candidates, ambiguity_analysis
        )
        
        # 6. Construire analyse détaillée
        analysis = {
            "candidates": [
                {
                    "intent": c.intent,
                    "confidence": c.confidence,
                    "evidence": c.evidence[:3],  # Limiter pour éviter verbosité
                    "domain": c.domain
                } for c in final_candidates[:3]
            ],
            "ambiguity": ambiguity_analysis,
            "confidence_factors": self._explain_confidence(best_candidate, global_confidence),
            "context_support": best_candidate.context_support,
            "evidence_strength": len(best_candidate.evidence)
        }
        
        logger.debug("🎯 Intent confiance: %s (%.2f) | ambiguïté=%s", 
                    best_candidate.intent, global_confidence, 
                    ambiguity_analysis.get("level", "none"))
        
        return best_candidate.intent, global_confidence, analysis

    def _analyze_single_intent(
        self, 
        intent: str, 
        base_score: float, 
        question: str, 
        context: Dict[str, Any]
    ) -> IntentCandidate:
        """Analyse un candidat d'intention individuel"""
        
        domain = self._get_domain(intent)
        evidence = []
        ambiguity_factors = []
        
        # Analyser evidence textuelle
        text_evidence = self._extract_text_evidence(intent, question)
        evidence.extend(text_evidence)
        
        # Support contextuel
        context_support = self._calculate_context_support(intent, context)
        
        # Facteurs d'ambiguïté
        ambiguity_factors = self._detect_intent_ambiguity_factors(intent, question, context)
        
        # Ajustements de confiance
        confidence_adjustments = self._calculate_confidence_adjustments(
            intent, question, context, evidence, ambiguity_factors
        )
        
        final_confidence = min(1.0, base_score + confidence_adjustments)
        
        return IntentCandidate(
            intent=intent,
            confidence=final_confidence,
            evidence=evidence,
            domain=domain,
            ambiguity_factors=ambiguity_factors,
            context_support=context_support
        )

    def _extract_text_evidence(self, intent: str, question: str) -> List[str]:
        """Extrait les évidences textuelles pour une intention"""
        
        evidence = []
        q_lower = question.lower()
        
        # Evidence pour performance
        if "weight_target" in intent:
            if re.search(r"\bpoids\s+(?:cible|target|optimal)\b", q_lower):
                evidence.append("mention explicite poids cible")
            if re.search(r"\bquel.*poids\b", q_lower):
                evidence.append("question directe sur poids")
        
        elif "fcr" in intent:
            if re.search(r"\bfcr\b", q_lower):
                evidence.append("mention explicite FCR")
            if re.search(r"\bindice.*consommation\b", q_lower):
                evidence.append("mention indice consommation")
        
        # Evidence pour diagnostic
        elif "health_issue" in intent:
            if re.search(r"\b(?:malade|maladie|symptôme)\b", q_lower):
                evidence.append("termes médicaux")
            if re.search(r"\bque\s+faire\b", q_lower):
                evidence.append("demande d'action urgente")
        
        elif "performance_issue" in intent:
            if re.search(r"\bproblème.*(?:croissance|performance)\b", q_lower):
                evidence.append("problème de performance")
            if re.search(r"\b(?:baisse|dégradé|anormal)\b", q_lower):
                evidence.append("termes de dégradation")
        
        # Evidence pour nutrition
        elif "protein" in intent:
            if re.search(r"\bprotéine\b", q_lower):
                evidence.append("mention protéine")
            if re.search(r"\b\d+\s*%.*protéine\b", q_lower):
                evidence.append("pourcentage protéine spécifique")
        
        # Evidence spécifique/précision
        if re.search(self.high_confidence_patterns["specific_breeds"], q_lower):
            evidence.append("lignée spécifique mentionnée")
        
        if re.search(self.high_confidence_patterns["specific_ages"], q_lower):
            evidence.append("âge précis mentionné")
        
        return evidence

    def _calculate_context_support(self, intent: str, context: Dict[str, Any]) -> float:
        """Calcule le support contextuel pour une intention"""
        
        if not context:
            return 0.0
        
        support = 0.0
        
        # Support selon présence de champs pertinents
        try:
            from ..pipeline.intent_registry import get_intent_spec
            spec = get_intent_spec(intent)
            required = spec.get("required_context", [])
            
            if required:
                present = sum(1 for field in required if field in context and context[field])
                support = present / len(required)
        except ImportError:
            # Fallback simple
            key_fields = ["species", "line", "age_days", "sex"]
            present = sum(1 for field in key_fields if field in context and context[field])
            support = present / len(key_fields)
        
        return support

    def _detect_intent_ambiguity_factors(
        self, 
        intent: str, 
        question: str, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Détecte les facteurs d'ambiguïté pour une intention"""
        
        factors = []
        q_lower = question.lower()
        
        # Ambiguïtés générales
        for pattern_type, patterns in self.ambiguity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, q_lower):
                    factors.append(f"ambiguïté_{pattern_type}")
        
        # Ambiguïtés spécifiques à l'intention
        if "performance" in intent:
            if not any(term in q_lower for term in ["poids", "fcr", "croissance", "performance"]):
                factors.append("intention_performance_implicite")
        
        elif "diagnosis" in intent:
            if not any(term in q_lower for term in ["problème", "symptôme", "maladie", "baisse"]):
                factors.append("diagnostic_sans_symptômes_explicites")
        
        # Manque de spécificité
        if not context.get("species") and "général" not in intent:
            factors.append("espèce_non_spécifiée")
        
        if not context.get("age_days") and intent.startswith(("performance", "nutrition")):
            factors.append("âge_non_spécifié")
        
        return factors

    def _calculate_confidence_adjustments(
        self,
        intent: str,
        question: str,
        context: Dict[str, Any],
        evidence: List[str],
        ambiguity_factors: List[str]
    ) -> float:
        """Calcule les ajustements de confiance"""
        
        adjustment = 0.0
        
        # Bonus pour evidence forte
        if len(evidence) >= 3:
            adjustment += 0.15
        elif len(evidence) >= 2:
            adjustment += 0.10
        elif len(evidence) >= 1:
            adjustment += 0.05
        
        # Bonus spécificité
        if "lignée spécifique mentionnée" in evidence:
            adjustment += 0.10
        if "âge précis mentionné" in evidence:
            adjustment += 0.08
        
        # Malus ambiguïté
        ambiguity_penalty = len(ambiguity_factors) * 0.05
        adjustment -= ambiguity_penalty
        
        # Bonus contexte riche
        context_richness = len([v for v in context.values() if v]) / max(len(context), 1)
        if context_richness > 0.7:
            adjustment += 0.08
        
        # Bonus cohérence intention-contexte
        if intent.startswith("performance") and context.get("line"):
            adjustment += 0.05
        if intent.startswith("diagnosis") and context.get("problem_type"):
            adjustment += 0.10
        
        return adjustment

    def _detect_ambiguities(
        self, 
        question: str, 
        candidates: List[IntentCandidate]
    ) -> Dict[str, Any]:
        """Détecte les ambiguïtés globales"""
        
        analysis = {
            "level": "none",
            "type": [],
            "competing_intents": [],
            "resolution_suggestions": []
        }
        
        if len(candidates) <= 1:
            return analysis
        
        # Analyser distribution des scores
        scores = [c.confidence for c in candidates]
        top_score = max(scores)
        second_score = sorted(scores, reverse=True)[1] if len(scores) > 1 else 0
        
        score_gap = top_score - second_score
        
        # Déterminer niveau d'ambiguïté
        if score_gap < 0.05:
            analysis["level"] = "very_high"
        elif score_gap < 0.15:
            analysis["level"] = "high"
        elif score_gap < 0.30:
            analysis["level"] = "medium"
        else:
            analysis["level"] = "low"
        
        # Analyser types d'ambiguïté
        domains = [c.domain for c in candidates[:3]]
        if len(set(domains)) > 1:
            analysis["type"].append("cross_domain")
            analysis["competing_intents"] = [c.intent for c in candidates[:3]]
        
        # Suggestions de résolution
        if analysis["level"] in ["high", "very_high"]:
            analysis["resolution_suggestions"] = [
                "Clarifier l'objectif principal",
                "Préciser l'espèce et l'âge",
                "Spécifier le type de problème si applicable"
            ]
        
        return analysis

    def _calculate_final_scores(
        self,
        candidates: List[IntentCandidate],
        ambiguity_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[IntentCandidate]:
        """Calcule les scores finaux avec ajustements globaux"""
        
        # Ajustements selon ambiguïté globale
        ambiguity_level = ambiguity_analysis.get("level", "none")
        
        for candidate in candidates:
            # Pénalité ambiguïté globale
            if ambiguity_level == "very_high":
                candidate.confidence *= 0.7
            elif ambiguity_level == "high":
                candidate.confidence *= 0.8
            elif ambiguity_level == "medium":
                candidate.confidence *= 0.9
            
            # Bonus pour domaines prioritaires selon contexte
            if context.get("problem_detected") and candidate.domain == "diagnosis":
                candidate.confidence *= 1.2
            
            # Normaliser
            candidate.confidence = min(1.0, candidate.confidence)
        
        return sorted(candidates, key=lambda x: x.confidence, reverse=True)

    def _calculate_global_confidence(
        self,
        best_candidate: IntentCandidate,
        all_candidates: List[IntentCandidate],
        ambiguity_analysis: Dict[str, Any]
    ) -> float:
        """Calcule la confiance globale de la classification"""
        
        base_confidence = best_candidate.confidence
        
        # Ajustements selon distribution
        if len(all_candidates) > 1:
            second_best = all_candidates[1].confidence
            dominance = base_confidence - second_best
            
            if dominance > 0.4:
                dominance_bonus = 0.1
            elif dominance > 0.2:
                dominance_bonus = 0.05
            else:
                dominance_bonus = 0.0
            
            base_confidence += dominance_bonus
        
        # Pénalité ambiguïté
        ambiguity_penalty = {
            "very_high": 0.3,
            "high": 0.2,
            "medium": 0.1,
            "low": 0.0,
            "none": 0.0
        }.get(ambiguity_analysis.get("level", "none"), 0.0)
        
        final_confidence = max(0.1, base_confidence - ambiguity_penalty)
        
        return min(1.0, final_confidence)

    def _explain_confidence(
        self, 
        best_candidate: IntentCandidate, 
        global_confidence: float
    ) -> Dict[str, Any]:
        """Explique les facteurs de confiance"""
        
        return {
            "evidence_count": len(best_candidate.evidence),
            "context_support": best_candidate.context_support,
            "ambiguity_factors": len(best_candidate.ambiguity_factors),
            "domain": best_candidate.domain,
            "confidence_level": self._categorize_confidence(global_confidence)
        }

    def _categorize_confidence(self, confidence: float) -> str:
        """Catégorise le niveau de confiance"""
        if confidence >= 0.8:
            return "very_high"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        elif confidence >= 0.2:
            return "low"
        else:
            return "very_low"

    def _get_domain(self, intent: str) -> str:
        """Récupère le domaine d'une intention"""
        if '.' in intent:
            return intent.split('.')[0]
        
        # Fallback mapping
        for domain, intents in self.domain_mapping.items():
            if any(intent_part in intent for intent_part in intents):
                return domain
        
        return "general"

    def suggest_clarifications_for_ambiguity(
        self, 
        ambiguity_analysis: Dict[str, Any],
        competing_candidates: List[IntentCandidate]
    ) -> List[str]:
        """Suggère des clarifications pour résoudre l'ambiguïté"""
        
        suggestions = []
        
        if ambiguity_analysis.get("level") in ["high", "very_high"]:
            # Suggestions basées sur domaines en compétition
            domains = [c.domain for c in competing_candidates[:3]]
            
            if "performance" in domains and "diagnosis" in domains:
                suggestions.extend([
                    "Cherchez-vous des valeurs cibles ou à résoudre un problème ?",
                    "S'agit-il d'une situation normale ou d'un problème observé ?"
                ])
            
            elif "performance" in domains and "nutrition" in domains:
                suggestions.extend([
                    "Voulez-vous des objectifs de performance ou des spécifications nutritionnelles ?",
                    "Cherchez-vous des cibles ou des formulations ?"
                ])
            
            # Suggestions génériques
            if len(suggestions) == 0:
                suggestions.extend([
                    "Pouvez-vous préciser l'objectif de votre question ?",
                    "S'agit-il d'une demande d'information ou d'un problème à résoudre ?"
                ])
        
        return suggestions[:2]  # Limiter à 2 suggestions

# Instance globale
_analyzer = IntentConfidenceAnalyzer()

def analyze_intent_confidence(
    question: str,
    context: Dict[str, Any],
    intent_candidates: Dict[str, float]
) -> Tuple[str, float, Dict[str, Any]]:
    """Interface publique pour l'analyse de confiance"""
    return _analyzer.analyze_intent_confidence(question, context, intent_candidates)

def get_ambiguity_clarifications(
    ambiguity_analysis: Dict[str, Any],
    candidates: List[Dict[str, Any]]
) -> List[str]:
    """Obtient des clarifications pour résoudre l'ambiguïté"""
    # Convertir dict en IntentCandidate pour compatibilité
    intent_candidates = []
    for c in candidates:
        candidate = IntentCandidate(
            intent=c.get("intent", ""),
            confidence=c.get("confidence", 0.0),
            evidence=c.get("evidence", []),
            domain=c.get("domain", "general"),
            ambiguity_factors=[],
            context_support=0.0
        )
        intent_candidates.append(candidate)
    
    return _analyzer.suggest_clarifications_for_ambiguity(ambiguity_analysis, intent_candidates)
