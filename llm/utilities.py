# -*- coding: utf-8 -*-
"""
utilities.py - Fonctions utilitaires et collecteur de métriques
"""

import os
import re
import statistics
from collections import defaultdict
from typing import Dict, Set
from config import (
    LANG_DETECTION_MIN_LENGTH, FRENCH_HINTS, ENGLISH_HINTS, FRENCH_CHARS
)
from imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

class MetricsCollector:
    """Collecteur de métriques enrichi avec statistiques intent et cache sémantique"""
    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)
        # NOUVEAU: Stats intent et cache sémantique
        self.intent_stats = defaultdict(int)
        self.semantic_cache_stats = defaultdict(int)
        self.ood_stats = defaultdict(int)
        self.api_corrections = defaultdict(int)

    def inc(self, key: str, n: int = 1): 
        self.counters[key] += n
    
    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100: 
            self.last_100_lat = self.last_100_lat[-100:]

    def cache_hit(self, cache_type: str):
        self.cache_stats[f"{cache_type}_hits"] += 1
    
    def cache_miss(self, cache_type: str):
        self.cache_stats[f"{cache_type}_misses"] += 1
    
    # NOUVEAU: Métriques intent
    def intent_detected(self, intent_type: str, confidence: float):
        self.intent_stats[f"intent_{intent_type}"] += 1
        self.intent_stats["total_intents"] += 1
        self.intent_stats["avg_confidence"] = (
            (self.intent_stats.get("avg_confidence", 0.0) * (self.intent_stats["total_intents"] - 1) + confidence) 
            / self.intent_stats["total_intents"]
        )
    
    # NOUVEAU: Métriques cache sémantique
    def semantic_cache_hit(self, cache_type: str):
        self.semantic_cache_stats[f"semantic_{cache_type}_hits"] += 1
    
    def semantic_fallback_used(self):
        self.semantic_cache_stats["fallback_hits"] += 1
    
    # NOUVEAU: Métriques OOD
    def ood_filtered(self, score: float, reason: str):
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_total"] += 1
        self.ood_stats["avg_ood_score"] = (
            (self.ood_stats.get("avg_ood_score", 0.0) * (self.ood_stats["ood_total"] - 1) + score) 
            / self.ood_stats["ood_total"]
        )
    
    # NOUVEAU: Corrections API
    def api_correction_applied(self, correction_type: str):
        self.api_corrections[correction_type] += 1

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (sorted(self.last_100_lat)[int(0.95*len(self.last_100_lat))-1]
               if len(self.last_100_lat) >= 20 else p50)
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "intent_stats": dict(self.intent_stats),
            "semantic_cache_stats": dict(self.semantic_cache_stats),
            "ood_stats": dict(self.ood_stats),
            "api_corrections": dict(self.api_corrections),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat)
        }

    def as_json(self) -> dict:
        """Export JSON des métriques pour l'app"""
        return {
            "cache": self.cache_stats,
            "ood": self.ood_stats,
            "guardrails": self.api_corrections,  # Mapping des corrections vers guardrails
        }

# Instance globale
METRICS = MetricsCollector()

def get_all_metrics_json(METRICS: MetricsCollector, extra: dict | None = None) -> dict:
    """Fonction d'export JSON consolidée des métriques avec données supplémentaires"""
    data = METRICS.as_json()
    if extra:
        data.update(extra)
    return data

def detect_language_enhanced(text: str, default: str = "fr") -> str:
    """Détection de langue optimisée pour requêtes courtes et techniques"""
    if len(text) < LANG_DETECTION_MIN_LENGTH:
        # Pour requêtes courtes: détection basique
        s = f" {text.lower()} "
        
        # Vérifier caractères spéciaux français
        if any(ch in text.lower() for ch in FRENCH_CHARS):
            return "fr"
        
        # Compter mots indicateurs
        fr = sum(1 for w in FRENCH_HINTS if w in s)
        en = sum(1 for w in ENGLISH_HINTS if w in s)
        
        if fr > en + 1: return "fr"
        if en > fr + 1: return "en"
        
        # Patterns techniques français
        if re.search(r'\d+\s*[gj]', text.lower()):  # "35j", "2500g"
            return "fr"
        
        return default
    else:
        # Pour requêtes longues: utiliser langdetect si disponible
        try:
            import langdetect
            detected = langdetect.detect(text)
            return detected if detected in ["fr", "en"] else default
        except:
            # Fallback vers méthode basique
            s = f" {text.lower()} "
            fr = sum(1 for w in FRENCH_HINTS if w in s)
            en = sum(1 for w in ENGLISH_HINTS if w in s)
            if fr > en + 1: return "fr"
            if en > fr + 1: return "en"
            if any(ch in s for ch in FRENCH_CHARS): return "fr"
            return default

def build_where_filter(intent_result) -> Dict:
    """Construire where filter par entités"""
    if not intent_result or not hasattr(intent_result, 'detected_entities'):
        return None
    
    entities = intent_result.detected_entities
    where_conditions = []
    
    if "line" in entities:
        where_conditions.append({
            "path": ["geneticLine"],
            "operator": "Like",
            "valueText": f"*{entities['line']}*"
        })
    
    if "species" in entities:
        where_conditions.append({
            "path": ["species"],
            "operator": "Like", 
            "valueText": f"*{entities['species']}*"
        })
    
    if "phase" in entities:
        where_conditions.append({
            "path": ["phase"],
            "operator": "Like",
            "valueText": f"*{entities['phase']}*"
        })
    
    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            if age_days <= 7:
                age_band = "0-7j"
            elif age_days <= 21:
                age_band = "8-21j"
            elif age_days <= 35:
                age_band = "22-35j"
            else:
                age_band = "36j+"
            
            where_conditions.append({
                "path": ["age_band"],
                "operator": "Equal",
                "valueText": age_band
            })
    
    if not where_conditions:
        return None
    
    if len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {
            "operator": "And",
            "operands": where_conditions
        }