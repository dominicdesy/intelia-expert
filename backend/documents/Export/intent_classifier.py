# -*- coding: utf-8 -*-
"""
intent_classifier.py - Classificateur d'intentions métier
"""

import re
import logging
import os
import json
from typing import Dict, Set, Tuple, Optional

# Toujours depuis le package local pour éviter les doubles définitions
from .intent_types import IntentType, IntentResult

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Classificateur d'intentions - Version avec scoring optimisé et intégration guardrails"""
    
    def __init__(self, intents_config: dict = None, vocab=None, guardrails=None, weights: dict = None):
        # Charge des poids configurables (JSON ou env) sinon défauts
        if weights:
            self.weights = weights
        else:
            cfg_path = os.getenv("INTENT_WEIGHTS_FILE", "")
            if cfg_path and os.path.exists(cfg_path):
                try:
                    self.weights = json.load(open(cfg_path, "r", encoding="utf-8"))
                except Exception:
                    self.weights = {"keyword": 1.0, "entity": 5.0, "explain_bonus": 2.0, "regex": 2.5}
            else:
                self.weights = {"keyword": 1.0, "entity": 5.0, "explain_bonus": 2.0, "regex": 2.5}
        
        self.intents_config = intents_config or {}
        self.vocab = vocab
        self.guardrails = guardrails
        self.intent_keywords = self._build_intent_keywords()
        self.intent_patterns = self._build_intent_patterns()
        self.intent_metrics = self._build_intent_metrics()
    
    def _build_intent_metrics(self) -> Dict[str, Set[str]]:
        """Construit l'association intentions -> métriques"""
        intent_metrics = {}
        
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = set(intent_config.get("metrics", {}).keys())
            intent_metrics[intent_name] = metrics
        
        return intent_metrics
    
    def _build_intent_keywords(self) -> Dict[str, Set[str]]:
        """Construit les mots-clés par intention - Version étendue"""
        keywords = {}
        
        # Mots-clés étendus pour metric_query
        keywords[IntentType.METRIC_QUERY.value] = {
            'poids', 'weight', 'fcr', 'conversion', 'consommation', 'eau', 'water',
            'performance', 'production', 'croissance', 'growth', 'optimal', 'target',
            'gramme', 'kg', 'litre', 'pourcentage', 'combien', 'how much', 'quelle',
            'indice', 'ratio', 'efficiency', 'rendement', 'objectif', 'standard',
            'uniformity', 'gain', 'intake', 'daily', 'weekly', 'cumulative',
            'epef', 'mortality', 'density', 'stocking', 'feeder', 'nipple'
        }
        
        # Environment_setting étendu
        keywords[IntentType.ENVIRONMENT_SETTING.value] = {
            'température', 'temperature', 'ventilation', 'climatisation', 'chauffage',
            'humidité', 'humidity', 'air', 'climat', 'ambiance', 'réglage', 'setting',
            'environnement', 'environment', 'conditions', 'atmosph', 'tunnel', 'pad',
            'cooling', 'heating', 'inlet', 'pressure', 'static', 'lighting', 'lux',
            'intensity', 'hours', 'photoperiod', 'dimming', 'co2', 'nh3', 'dust'
        }
        
        # Protocol_query étendu
        keywords[IntentType.PROTOCOL_QUERY.value] = {
            'vaccination', 'protocole', 'protocol', 'traitement', 'treatment',
            'biosécurité', 'biosecurity', 'prévention', 'prevention', 'vaccin',
            'programme', 'program', 'schedule', 'planning', 'sanitaire', 'vaccine',
            'antibiotic', 'medication', 'withdrawal', 'timing', 'injection'
        }
        
        # Diagnosis_triage étendu
        keywords[IntentType.DIAGNOSIS_TRIAGE.value] = {
            'maladie', 'disease', 'symptôme', 'symptom', 'diagnostic', 'diagnosis',
            'mortalité', 'mortality', 'problème', 'problem', 'signes', 'signs',
            'pathologie', 'infection', 'virus', 'bacteria', 'parasite', 'sick',
            'health', 'clinical', 'lesion', 'postmortem', 'necropsy', 'lab'
        }
        
        # Economics_cost étendu
        keywords[IntentType.ECONOMICS_COST.value] = {
            'coût', 'cost', 'prix', 'price', 'économique', 'economic', 'rentabilité',
            'profit', 'marge', 'margin', 'budget', 'finance', 'euros', 'dollars',
            'investment', 'investissement', 'return', 'roi', 'amortissement',
            'efficiency', 'optimization', 'feed cost', 'energy cost', 'labor'
        }
        
        return keywords
    
    def classify_intent(self, text: str, entities: Dict[str, str] = None, 
                       explain_score: Optional[float] = None) -> Tuple[IntentType, Dict[str, float]]:
        """Classifie l'intention avec scoring multimodal amélioré et intégration explain_score"""
        text_lower = text.lower()
        entities = entities or {}
        scores = {}
        score_breakdown = {}
        
        for intent_type, keywords in self.intent_keywords.items():
            # Score basique par mots-clés (avec poids configurables)
            keyword_matches = sum(1 for keyword in keywords if keyword in text_lower)
            keyword_score = keyword_matches * self.weights.get("keyword", 1.0)
            
            # Score par patterns regex (avec poids configurables)
            pattern_score = 0
            if intent_type in self.intent_patterns:
                pattern_matches = sum(1 for pattern in self.intent_patterns[intent_type] 
                                    if re.search(pattern, text_lower))
                pattern_score = pattern_matches * self.weights.get("regex", 2.5)
            
            # Score par entités (avec poids configurables)
            entity_score = 0
            if intent_type == IntentType.METRIC_QUERY.value:
                if "metrics" in entities:
                    entity_score += 1  # Base multiplié par weight plus tard
                if any(key in entities for key in ["weight_value", "percentage_value", "temperature_value"]):
                    entity_score += 0.6
                if any(key in entities for key in ["age_days", "age_weeks", "line"]):
                    entity_score += 0.4
                # Bonus pour lignée normalisée
                if "line_normalized" in entities:
                    entity_score += 0.2
            
            elif intent_type == IntentType.ENVIRONMENT_SETTING.value:
                if "temperature_value" in entities:
                    entity_score += 0.8
                if "site_type" in entities:
                    entity_score += 0.4
                if "environment" in entities:
                    entity_score += 0.6
            
            elif intent_type == IntentType.ECONOMICS_COST.value:
                if any(word in text_lower for word in ['coût', 'cost', 'prix', 'économ']):
                    entity_score += 0.6
                if "flock_size" in entities:
                    entity_score += 0.4
            
            # Appliquer le poids des entités
            entity_score *= self.weights.get("entity", 5.0)
            
            # Score par métriques spécialisées
            metrics_score = 0
            if intent_type in self.intent_metrics:
                intent_specific_metrics = self.intent_metrics[intent_type]
                detected_metrics = entities.get("metrics", "").split(",")
                matching_metrics = [m for m in detected_metrics if m in intent_specific_metrics]
                metrics_score = len(matching_metrics) * 3
            
            # Bonus explain_score pour evidence_support (intégration guardrails)
            explain_bonus = 0
            if explain_score is not None and explain_score > 0.7:
                explain_bonus = self.weights.get("explain_bonus", 2.0)
            
            total_score = keyword_score + pattern_score + entity_score + metrics_score + explain_bonus
            scores[intent_type] = total_score
            
            score_breakdown[intent_type] = {
                "keyword_score": keyword_score,
                "pattern_score": pattern_score,
                "entity_score": entity_score,
                "metrics_score": metrics_score,
                "explain_bonus": explain_bonus,
                "total_score": total_score
            }
        
        # Retourner l'intention avec le meilleur score
        if max(scores.values()) > 0:
            best_intent = max(scores, key=scores.get)
            return IntentType(best_intent), score_breakdown
        
        return IntentType.GENERAL_POULTRY, score_breakdown
    
    def _build_intent_patterns(self) -> Dict[str, list[str]]:
        """Construit des patterns regex étendus"""
        patterns = {}
        
        patterns[IntentType.METRIC_QUERY.value] = [
            r'\b(?:combien|how much|quelle?\s+(?:est|is))\b',
            r'\b(?:poids|weight|fcr)\s+(?:de|of|à|at)\b',
            r'\b\d+\s*(?:g|kg|%|litres?|days?|jours?|weeks?|semaines?)\b',
            r'\b(?:optimal|target|objectif|cible)\b'
        ]
        
        patterns[IntentType.ENVIRONMENT_SETTING.value] = [
            r'\b(?:température|temperature|ventilation)\s+(?:optimale?|optimal|recommended)\b',
            r'\b(?:comment|how)\s+(?:régler|set|ajuster|adjust)\b',
            r'\b(?:ambiance|climate|setting)\b'
        ]
        
        patterns[IntentType.DIAGNOSIS_TRIAGE.value] = [
            r'\b(?:mes|my)\s+(?:poulets?|chickens?)\s+(?:sont|are)\b',
            r'\b(?:symptômes?|symptoms?|signes?|signs?)\s+(?:de|of)\b',
            r'\b(?:diagnostic|diagnosis|problème|problem)\b'
        ]
        
        return patterns
    
    def get_weights_config(self) -> dict:
        """Retourne la configuration actuelle des poids"""
        return self.weights.copy()
    
    def update_weights(self, new_weights: dict) -> None:
        """Met à jour les poids de scoring"""
        self.weights.update(new_weights)
        logger.info(f"Weights updated: {self.weights}")