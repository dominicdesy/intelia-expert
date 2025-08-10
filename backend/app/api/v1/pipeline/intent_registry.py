# app/api/v1/pipeline/intent_registry.py - VERSION AMÉLIORÉE
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

"""
Intent Registry — universel, extensible et hiérarchique
- Classification par domaines avec scoring de confiance
- Détection d'intentions multiples et ambiguïtés
- Adaptation contextuelle selon extraction
- Support diagnostic et problèmes
"""

# NOUVELLE STRUCTURE HIÉRARCHIQUE
_INTENT_DOMAINS = {
    "performance": {
        "weight_target": {
            "signals": [
                r"\b(poids|weight)\s+(?:cible|target|optimal|recommandé|idéal)",
                r"\b(target|cible)\s+(?:weight|poids)",
                r"quel.*poids.*(?:à|pour|de)",
                r"combien.*(?:pèse|peser|poids)"
            ],
            "required_context": ["species", "line", "age_days", "sex"],
            "critical_context": ["line", "age_days"],
            "preferred_sources": ["performance_objectives", "breeding_manuals"],
            "answer_mode": "numeric_first",
            "urgency": "normal",
            "priority": 10
        },
        "fcr_target": {
            "signals": [
                r"\bfcr\b",
                r"\bindice\s+(?:de\s+)?consommation",
                r"\bfeed\s*conversion",
                r"\bconversion\s+alimentaire",
                r"consommation.*aliment"
            ],
            "required_context": ["species", "line", "age_days"],
            "critical_context": ["line", "age_days"],
            "preferred_sources": ["performance_objectives", "nutrition_specs"],
            "answer_mode": "numeric_first",
            "urgency": "normal",
            "priority": 9
        },
        "production_rate": {
            "signals": [
                r"\b(?:taux|pourcentage)\s+(?:de\s+)?ponte",
                r"\bproduction\s+rate",
                r"\bhen.*day.*production",
                r"combien.*œufs?.*jour",
                r"(\d+)\s*%.*ponte"
            ],
            "required_context": ["species", "line", "age_days"],
            "critical_context": ["line", "age_days"],
            "preferred_sources": ["layer_handbook", "performance_objectives"],
            "answer_mode": "numeric_first",
            "urgency": "normal",
            "priority": 9
        },
        "mortality_rate": {
            "signals": [
                r"\b(?:taux|pourcentage)\s+(?:de\s+)?mortalité",
                r"\bmortality\s+rate",
                r"combien.*mort",
                r"(\d+)\s*%.*mort"
            ],
            "required_context": ["species", "age_days"],
            "critical_context": ["age_days"],
            "preferred_sources": ["health_guides", "performance_objectives"],
            "answer_mode": "numeric_with_context",
            "urgency": "normal",
            "priority": 8
        }
    },
    
    "nutrition": {
        "protein_requirements": {
            "signals": [
                r"\b(?:taux|pourcentage)\s+(?:de\s+)?protéine",
                r"\bprotein\s+(?:level|requirement)",
                r"\blysine",
                r"\bacides?\s+aminés?",
                r"(\d+)\s*%.*protéine"
            ],
            "required_context": ["species", "phase"],
            "critical_context": ["phase"],
            "preferred_sources": ["nutrition_specs", "feeding_guides"],
            "answer_mode": "table_numeric",
            "urgency": "normal",
            "priority": 8
        },
        "energy_requirements": {
            "signals": [
                r"\bénergie",
                r"\bkcal.*kg",
                r"\benergy\s+density",
                r"(\d{4})\s*kcal"
            ],
            "required_context": ["species", "phase"],
            "critical_context": ["phase"],
            "preferred_sources": ["nutrition_specs", "feeding_guides"],
            "answer_mode": "table_numeric",
            "urgency": "normal",
            "priority": 7
        },
        "feed_consumption": {
            "signals": [
                r"\bconsommation\s+(?:d['\'])?aliment",
                r"\bfeed\s+(?:intake|consumption)",
                r"combien.*mange",
                r"g.*jour.*oiseau"
            ],
            "required_context": ["species", "age_days"],
            "critical_context": ["age_days"],
            "preferred_sources": ["feeding_guides", "nutrition_specs"],
            "answer_mode": "numeric_first",
            "urgency": "normal",
            "priority": 7
        }
    },
    
    "diagnosis": {
        "performance_issue": {
            "signals": [
                r"\bproblème",
                r"\bbaisse",
                r"\bdégradé",
                r"\banormal",
                r"\binquiétant",
                r"ne.*(?:grossis|pond|mange)",
                r"résultats.*(?:mauvais|décevants)"
            ],
            "required_context": ["species", "problem_type", "age_days"],
            "critical_context": ["problem_type"],
            "preferred_sources": ["diagnostic_guides", "troubleshooting"],
            "answer_mode": "diagnostic_steps",
            "urgency": "high",
            "priority": 12
        },
        "health_issue": {
            "signals": [
                r"\bmalade",
                r"\bmaladie",
                r"\binfection",
                r"\bsymptômes?",
                r"\bdiarrhée",
                r"\bmortalité\s+élevée",
                r"que\s+faire"
            ],
            "required_context": ["species", "symptoms", "age_days"],
            "critical_context": ["symptoms"],
            "preferred_sources": ["veterinary_guides", "pathology_atlas"],
            "answer_mode": "diagnostic_urgent",
            "urgency": "critical",
            "priority": 15
        },
        "production_drop": {
            "signals": [
                r"\bbaisse.*ponte",
                r"\bproduction.*baisse",
                r"\bmoins.*œufs?",
                r"ponte.*chut"
            ],
            "required_context": ["species", "age_days", "production_rate_pct"],
            "critical_context": ["production_rate_pct"],
            "preferred_sources": ["layer_troubleshooting", "production_guides"],
            "answer_mode": "diagnostic_steps",
            "urgency": "high",
            "priority": 12
        }
    },
    
    "environment": {
        "temperature_control": {
            "signals": [
                r"\btempérature",
                r"\bchauffage",
                r"\bfroid",
                r"\bchaud",
                r"(\d+)\s*°c"
            ],
            "required_context": ["species", "age_days"],
            "critical_context": ["age_days"],
            "preferred_sources": ["environmental_guides", "brooding_guides"],
            "answer_mode": "procedure_numeric",
            "urgency": "normal",
            "priority": 7
        },
        "ventilation": {
            "signals": [
                r"\bventilation",
                r"\baération",
                r"\bair.*flow",
                r"\bammoniaque",
                r"\bnh3",
                r"m³.*h"
            ],
            "required_context": ["species", "age_days", "effectif"],
            "critical_context": ["effectif"],
            "preferred_sources": ["ventilation_guides", "environmental_guides"],
            "answer_mode": "procedure_numeric",
            "urgency": "normal",
            "priority": 6
        },
        "lighting": {
            "signals": [
                r"\béclairage",
                r"\blumi[eè]re",
                r"\bphotop[ée]riode",
                r"\blux",
                r"\bheure.*lumi[eè]re"
            ],
            "required_context": ["species", "age_days"],
            "critical_context": ["age_days"],
            "preferred_sources": ["management_guides", "lighting_programs"],
            "answer_mode": "procedure",
            "urgency": "normal",
            "priority": 5
        }
    },
    
    "equipment": {
        "feeders": {
            "signals": [
                r"\bmangeoire",
                r"\bfeeder",
                r"\bassiette",
                r"\bcha[iî]ne",
                r"\bespace.*mange"
            ],
            "required_context": ["species", "age_days", "effectif"],
            "critical_context": ["effectif", "age_days"],
            "preferred_sources": ["equipment_manuals", "setup_guides"],
            "answer_mode": "procedure_numeric",
            "urgency": "normal",
            "priority": 6
        },
        "drinkers": {
            "signals": [
                r"\babreuvoir",
                r"\bdrinker",
                r"\bnipple",
                r"\bcloche",
                r"\beau.*point"
            ],
            "required_context": ["species", "age_days", "effectif"],
            "critical_context": ["effectif", "age_days"],
            "preferred_sources": ["equipment_manuals", "water_guides"],
            "answer_mode": "procedure_numeric",
            "urgency": "normal",
            "priority": 6
        }
    },
    
    "economics": {
        "cost_analysis": {
            "signals": [
                r"\bco[uû]t",
                r"\bprix",
                r"\béconomique",
                r"\brentabilité",
                r"€.*kg",
                r"€.*tonne"
            ],
            "required_context": ["species"],
            "critical_context": [],
            "preferred_sources": ["economic_guides", "cost_analysis"],
            "answer_mode": "numeric_with_breakdown",
            "urgency": "normal",
            "priority": 5
        },
        "iep_calculation": {
            "signals": [
                r"\biep\b",
                r"\bepef\b",
                r"\bindice.*efficacité",
                r"\bproduction\s+efficiency",
                r"\bindice.*europe"
            ],
            "required_context": ["species", "age_days", "fcr", "livability_pct"],
            "critical_context": ["fcr", "livability_pct"],
            "preferred_sources": ["performance_objectives", "kpi_guides"],
            "answer_mode": "calculation_with_formula",
            "urgency": "normal",
            "priority": 7
        }
    },
    
    "compliance": {
        "regulations": {
            "signals": [
                r"\blabel\s+rouge",
                r"\bbio",
                r"\bplein\s+air",
                r"\bréglement",
                r"\bnorme",
                r"\bcahier.*charges"
            ],
            "required_context": ["jurisdiction", "label"],
            "critical_context": ["label"],
            "preferred_sources": ["regulations", "label_specifications"],
            "answer_mode": "rules_and_requirements",
            "urgency": "normal",
            "priority": 6
        }
    }
}

# Classification par ordre de priorité (pour évaluation séquentielle)
_EVALUATION_ORDER = [
    "diagnosis.health_issue",
    "diagnosis.performance_issue", 
    "diagnosis.production_drop",
    "performance.weight_target",
    "performance.fcr_target",
    "performance.production_rate",
    "performance.mortality_rate",
    "nutrition.protein_requirements",
    "nutrition.energy_requirements",
    "nutrition.feed_consumption",
    "economics.iep_calculation",
    "environment.temperature_control",
    "equipment.feeders",
    "equipment.drinkers",
    "environment.ventilation",
    "environment.lighting",
    "economics.cost_analysis",
    "compliance.regulations"
]

class IntentClassifier:
    """Classificateur d'intentions hiérarchique avec scoring de confiance"""
    
    def __init__(self):
        self.domains = _INTENT_DOMAINS
        self.evaluation_order = _EVALUATION_ORDER
        
    def classify_with_confidence(self, question: str, context: Dict[str, Any] = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classifie l'intention avec score de confiance et métadonnées
        
        Returns:
            - intention (str): meilleure intention détectée
            - confidence (float): score 0-1
            - metadata (dict): détails classification
        """
        ctx = context or {}
        q_lower = question.lower().strip()
        
        scores = {}
        matches = {}
        
        # Évaluer chaque intention dans l'ordre de priorité
        for intent_full in self.evaluation_order:
            domain, intent = intent_full.split('.', 1)
            config = self.domains[domain][intent]
            
            score = self._calculate_intent_score(q_lower, ctx, config, intent_full)
            if score > 0:
                scores[intent_full] = score
                matches[intent_full] = self._extract_matches(q_lower, config["signals"])
        
        # Détection spéciale pour intentions générales
        if not scores:
            general_score = self._detect_general_patterns(q_lower, ctx)
            if general_score > 0:
                scores["general.question"] = general_score
        
        if not scores:
            return "general.unknown", 0.3, {"reason": "no_patterns_matched"}
        
        # Sélectionner meilleure intention
        best_intent, best_score = max(scores.items(), key=lambda x: x[1])
        
        # Calculer confiance finale
        confidence = self._calculate_final_confidence(best_score, scores, ctx)
        
        # Métadonnées enrichies
        metadata = {
            "domain": best_intent.split('.')[0] if '.' in best_intent else "general",
            "all_scores": scores,
            "pattern_matches": matches.get(best_intent, []),
            "context_completeness": self._assess_context_completeness(best_intent, ctx),
            "ambiguity_level": self._calculate_ambiguity(scores),
            "urgency": self._get_urgency(best_intent)
        }
        
        logger.debug("🎯 Intent: %s (conf=%.2f, scores=%s)", best_intent, confidence, scores)
        
        return best_intent, confidence, metadata
    
    def _calculate_intent_score(self, question: str, context: Dict[str, Any], 
                               config: Dict[str, Any], intent_full: str) -> float:
        """Calcule le score pour une intention donnée"""
        score = 0.0
        
        # Score des patterns textuels
        pattern_score = 0.0
        total_patterns = len(config["signals"])
        
        for pattern in config["signals"]:
            try:
                if re.search(pattern, question, re.IGNORECASE):
                    pattern_score += 1.0
            except re.error as e:
                logger.warning("Regex error in %s: %s", intent_full, e)
        
        # Normaliser score patterns
        if total_patterns > 0:
            pattern_score = pattern_score / total_patterns
        
        # Bonus pour patterns multiples
        if pattern_score > 0.5:
            pattern_score += 0.2
        
        score += pattern_score * 0.7  # 70% du score
        
        # Score contextuel
        context_score = self._score_context_match(context, config)
        score += context_score * 0.3  # 30% du score
        
        # Bonus de priorité (intentions plus importantes)
        priority_bonus = config.get("priority", 5) / 15.0  # Normaliser 0-1
        score += priority_bonus * 0.1
        
        # Malus si contexte critique manquant
        critical_context = config.get("critical_context", [])
        missing_critical = sum(1 for field in critical_context 
                             if field not in context or not context[field])
        if critical_context and missing_critical > 0:
            penalty = (missing_critical / len(critical_context)) * 0.3
            score = max(0, score - penalty)
        
        return min(score, 1.0)
    
    def _score_context_match(self, context: Dict[str, Any], config: Dict[str, Any]) -> float:
        """Score la correspondance du contexte avec les exigences"""
        required = config.get("required_context", [])
        critical = config.get("critical_context", [])
        
        if not required and not critical:
            return 0.5  # Score neutre si pas d'exigences
        
        all_required = set(required + critical)
        present = sum(1 for field in all_required if field in context and context[field])
        
        if not all_required:
            return 0.5
        
        base_score = present / len(all_required)
        
        # Bonus pour champs critiques présents
        if critical:
            critical_present = sum(1 for field in critical 
                                 if field in context and context[field])
            critical_bonus = (critical_present / len(critical)) * 0.3
            base_score += critical_bonus
        
        return min(base_score, 1.0)
    
    def _extract_matches(self, question: str, patterns: List[str]) -> List[str]:
        """Extrait les correspondances textuelles"""
        matches = []
        for pattern in patterns:
            try:
                found = re.findall(pattern, question, re.IGNORECASE)
                if found:
                    matches.extend([str(m) for m in found if m])
            except re.error:
                pass
        return matches[:5]  # Limiter pour éviter verbosité
    
    def _detect_general_patterns(self, question: str, context: Dict[str, Any]) -> float:
        """Détection de patterns généraux pour questions non classifiées"""
        general_patterns = [
            r"\bcomment\b",
            r"\bpourquoi\b", 
            r"\bquel(?:le)?\b",
            r"\bcombien\b",
            r"\bquand\b",
            r"\boù\b"
        ]
        
        matches = sum(1 for pattern in general_patterns 
                     if re.search(pattern, question, re.IGNORECASE))
        
        return min(matches * 0.3, 0.8)  # Score modéré pour général
    
    def _calculate_final_confidence(self, best_score: float, all_scores: Dict[str, float], 
                                   context: Dict[str, Any]) -> float:
        """Calcule la confiance finale en tenant compte des ambiguïtés"""
        base_confidence = best_score
        
        # Pénalité pour ambiguïté (plusieurs scores élevés)
        high_scores = [s for s in all_scores.values() if s > 0.5]
        if len(high_scores) > 1:
            ambiguity_penalty = (len(high_scores) - 1) * 0.1
            base_confidence = max(0.3, base_confidence - ambiguity_penalty)
        
        # Bonus pour contexte riche
        context_richness = len([v for v in context.values() if v]) / max(len(context), 1)
        if context_richness > 0.7:
            base_confidence += 0.1
        
        # Bonus pour détection urgence
        urgent_keywords = ["urgent", "problème", "malade", "mortalité", "baisse"]
        if any(kw in str(context.values()).lower() for kw in urgent_keywords):
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _assess_context_completeness(self, intent: str, context: Dict[str, Any]) -> float:
        """Évalue la complétude du contexte pour l'intention"""
        if '.' not in intent:
            return 0.5
        
        domain, intent_name = intent.split('.', 1)
        config = self.domains.get(domain, {}).get(intent_name, {})
        required = config.get("required_context", [])
        
        if not required:
            return 1.0
        
        present = sum(1 for field in required if field in context and context[field])
        return present / len(required)
    
    def _calculate_ambiguity(self, scores: Dict[str, float]) -> str:
        """Calcule le niveau d'ambiguïté"""
        if not scores:
            return "none"
        
        sorted_scores = sorted(scores.values(), reverse=True)
        
        if len(sorted_scores) == 1:
            return "none"
        elif len(sorted_scores) == 2:
            diff = sorted_scores[0] - sorted_scores[1]
            if diff < 0.1:
                return "high"
            elif diff < 0.3:
                return "medium"
            else:
                return "low"
        else:
            # 3+ intentions
            top_scores = sorted_scores[:3]
            if max(top_scores) - min(top_scores) < 0.2:
                return "very_high"
            else:
                return "high"
    
    def _get_urgency(self, intent: str) -> str:
        """Récupère le niveau d'urgence de l'intention"""
        if '.' not in intent:
            return "normal"
        
        domain, intent_name = intent.split('.', 1)
        config = self.domains.get(domain, {}).get(intent_name, {})
        return config.get("urgency", "normal")

# ================== FONCTIONS PUBLIQUES COMPATIBLES ==================

def infer_intent(text: str, context: Dict[str, Any] = None, fallback: str = "general") -> str:
    """Fonction de compatibilité - retourne seulement l'intention"""
    classifier = IntentClassifier()
    intent, _, _ = classifier.classify_with_confidence(text, context)
    return intent if intent != "general.unknown" else fallback

def infer_intent_with_confidence(text: str, context: Dict[str, Any] = None) -> Tuple[str, float, Dict[str, Any]]:
    """Nouvelle fonction complète avec confiance et métadonnées"""
    classifier = IntentClassifier()
    return classifier.classify_with_confidence(text, context)

def get_intent_spec(name: str) -> Dict[str, Any]:
    """Récupère la spécification complète d'une intention"""
    if '.' not in name:
        # Fallback pour ancien format
        return {
            "required_context": [],
            "preferred_sources": ["general_guides"],
            "answer_mode": "standard",
            "urgency": "normal",
            "priority": 5
        }
    
    domain, intent = name.split('.', 1)
    return _INTENT_DOMAINS.get(domain, {}).get(intent, {})

def derive_answer_mode(name: str) -> str:
    """Dérive le mode de réponse de l'intention"""
    spec = get_intent_spec(name)
    return str(spec.get("answer_mode", "standard"))

def required_slots(name: str) -> List[str]:
    """Retourne les slots requis pour l'intention"""
    spec = get_intent_spec(name)
    return list(spec.get("required_context", []))

def critical_slots(name: str) -> List[str]:
    """Retourne les slots critiques pour l'intention"""
    spec = get_intent_spec(name)
    return list(spec.get("critical_context", []))

def preferred_sources(name: str) -> List[str]:
    """Retourne les sources préférées pour l'intention"""
    spec = get_intent_spec(name)
    return list(spec.get("preferred_sources", []))

def looks_numeric_first(name: str) -> bool:
    """Détermine si la réponse doit commencer par une valeur numérique"""
    mode = derive_answer_mode(name)
    return any(x in mode for x in ["numeric", "calculation", "table_numeric"])

def is_urgent_intent(name: str) -> bool:
    """Détermine si l'intention est urgente"""
    spec = get_intent_spec(name)
    urgency = spec.get("urgency", "normal")
    return urgency in ["high", "critical"]

def get_intent_priority(name: str) -> int:
    """Retourne la priorité numérique de l'intention"""
    spec = get_intent_spec(name)
    return int(spec.get("priority", 5))

def get_all_intents_by_domain() -> Dict[str, List[str]]:
    """Retourne toutes les intentions groupées par domaine"""
    result = {}
    for domain, intents in _INTENT_DOMAINS.items():
        result[domain] = [f"{domain}.{intent}" for intent in intents.keys()]
    return result

def suggest_related_intents(current_intent: str, context: Dict[str, Any] = None) -> List[str]:
    """Suggère des intentions connexes basées sur le contexte"""
    if '.' not in current_intent:
        return []
    
    domain, _ = current_intent.split('.', 1)
    ctx = context or {}
    
    suggestions = []
    
    # Suggestions dans le même domaine
    domain_intents = _INTENT_DOMAINS.get(domain, {})
    for intent_name in domain_intents:
        full_intent = f"{domain}.{intent_name}"
        if full_intent != current_intent:
            suggestions.append(full_intent)
    
    # Suggestions cross-domain basées sur contexte
    if domain == "performance" and ctx.get("species") == "broiler":
        suggestions.extend([
            "nutrition.protein_requirements",
            "nutrition.feed_consumption",
            "economics.cost_analysis"
        ])
    elif domain == "diagnosis":
        suggestions.extend([
            "environment.temperature_control",
            "environment.ventilation",
            "nutrition.feed_consumption"
        ])
    
    return suggestions[:5]

# ================== MAPPING POUR COMPATIBILITÉ ==================

# Mapping ancien système vers nouveau pour rétrocompatibilité
_LEGACY_MAPPING = {
    "nutrition": "nutrition.protein_requirements",
    "poids_cible": "performance.weight_target", 
    "performance": "performance.weight_target",
    "sante": "diagnosis.health_issue",
    "alimentation": "nutrition.feed_consumption",
    "anomaly": "diagnosis.performance_issue",
    "diagnosis": "diagnosis.health_issue",
    "iep": "economics.iep_calculation",
    "costing": "economics.cost_analysis",
    "feeders": "equipment.feeders",
    "drinkers": "equipment.drinkers",
    "tunnel_airflow": "environment.ventilation",
    "general": "general.question"
}

def map_legacy_intent(old_intent: str) -> str:
    """Mappe les anciennes intentions vers les nouvelles"""
    return _LEGACY_MAPPING.get(old_intent, f"general.{old_intent}")

def classify_question(question: Any) -> str:
    """Fonction de compatibilité avec l'ancien système"""
    if isinstance(question, str):
        intent = infer_intent(question)
        # Retourner format ancien si nécessaire
        if '.' in intent:
            domain, intent_name = intent.split('.', 1)
            # Mapping inverse pour compatibilité
            legacy_map = {v: k for k, v in _LEGACY_MAPPING.items()}
            return legacy_map.get(intent, intent_name)
        return intent
    
    return "general"