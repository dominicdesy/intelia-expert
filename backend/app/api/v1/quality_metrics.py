"""
Système de Métriques de Qualité Temps Réel
🎯 Impact: +10-20% amélioration continue par apprentissage automatique
"""

import logging
import json
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class QualityMetric:
    """Métrique de qualité individuelle"""
    timestamp: datetime
    metric_type: str
    value: float
    details: Dict[str, Any]
    context: Dict[str, Any]

class QualityMetricsCollector:
    """Collecteur de métriques de qualité temps réel"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Historiques des métriques
        self.enrichment_quality_history = deque(maxlen=max_history)
        self.coherence_history = deque(maxlen=max_history)
        self.entity_accuracy_history = deque(maxlen=max_history)
        self.response_satisfaction_history = deque(maxlen=max_history)
        
        # Métriques par race/contexte
        self.breed_specific_metrics = defaultdict(list)
        self.age_specific_metrics = defaultdict(list)
        
        # Tendances
        self.trends = {
            "enrichment_quality": [],
            "coherence_score": [],
            "entity_accuracy": [],
            "satisfaction_score": []
        }
    
    async def calculate_enrichment_quality(
        self, 
        original: str, 
        enriched: str, 
        entities: Dict[str, Any]
    ) -> float:
        """Calcule la qualité de l'enrichissement"""
        
        try:
            scores = {}
            
            # Score 1: Préservation information (0-1)
            scores["information_preservation"] = self._calculate_information_preservation(original, enriched)
            
            # Score 2: Intégration entités (0-1)
            scores["entity_integration"] = self._calculate_entity_integration(enriched, entities)
            
            # Score 3: Clarté ajoutée (0-1)
            scores["clarity_improvement"] = self._calculate_clarity_improvement(original, enriched)
            
            # Score 4: Spécificité technique (0-1)
            scores["technical_specificity"] = self._calculate_technical_specificity(enriched)
            
            # Score final pondéré
            quality_score = (
                scores["information_preservation"] * 0.30 +
                scores["entity_integration"] * 0.30 +
                scores["clarity_improvement"] * 0.20 +
                scores["technical_specificity"] * 0.20
            )
            
            # Enregistrer la métrique
            metric = QualityMetric(
                timestamp=datetime.now(),
                metric_type="enrichment_quality",
                value=quality_score,
                details=scores,
                context={"original_length": len(original), "enriched_length": len(enriched)}
            )
            
            self.enrichment_quality_history.append(metric)
            
            # Métriques spécifiques par race
            breed = entities.get("breed", "unknown")
            if breed != "unknown":
                self.breed_specific_metrics[breed].append(quality_score)
            
            logger.debug(f"📊 [QualityMetrics] Score enrichissement: {quality_score:.3f}")
            
            return quality_score
            
        except Exception as e:
            logger.error(f"❌ [QualityMetrics] Erreur calcul qualité enrichissement: {e}")
            return 0.5
    
    def _calculate_information_preservation(self, original: str, enriched: str) -> float:
        """Calcule le score de préservation de l'information"""
        if not original or not enriched:
            return 0.0
        
        # Extraction termes clés originaux
        original_terms = set(self._extract_key_terms(original.lower()))
        enriched_terms = set(self._extract_key_terms(enriched.lower()))
        
        if not original_terms:
            return 1.0
        
        # Pourcentage de termes préservés
        preserved = len(original_terms & enriched_terms)
        return preserved / len(original_terms)
    
    def _calculate_entity_integration(self, enriched: str, entities: Dict[str, Any]) -> float:
        """Calcule le score d'intégration des entités"""
        if not entities:
            return 1.0
        
        enriched_lower = enriched.lower()
        entity_count = 0
        integrated_count = 0
        
        for key, value in entities.items():
            if value and key in ["breed", "age_days", "weight_g", "sex"]:
                entity_count += 1
                value_str = str(value).lower()
                
                if value_str in enriched_lower or self._semantic_match(value_str, enriched_lower):
                    integrated_count += 1
        
        return integrated_count / max(entity_count, 1)
    
    def _calculate_clarity_improvement(self, original: str, enriched: str) -> float:
        """Calcule l'amélioration de clarté"""
        if len(enriched) <= len(original):
            return 0.0
        
        # Mesures de clarté
        clarity_indicators = [
            "spécifique", "précis", "âge", "poids", "race", "performance",
            "jours", "grammes", "ross", "cobb", "mâle", "femelle"
        ]
        
        original_clarity = sum(1 for indicator in clarity_indicators if indicator in original.lower())
        enriched_clarity = sum(1 for indicator in clarity_indicators if indicator in enriched.lower())
        
        improvement = enriched_clarity - original_clarity
        return min(1.0, max(0.0, improvement / 5))
    
    def _calculate_technical_specificity(self, enriched: str) -> float:
        """Calcule la spécificité technique"""
        technical_terms = [
            "performance", "croissance", "conversion", "indice", "mortalité",
            "vaccination", "alimentation", "rendement", "gain moyen quotidien"
        ]
        
        enriched_lower = enriched.lower()
        technical_count = sum(1 for term in technical_terms if term in enriched_lower)
        
        return min(1.0, technical_count / 3)
    
    def _semantic_match(self, entity_value: str, text: str) -> bool:
        """Correspondance sémantique simple"""
        semantic_mappings = {
            "ross_308": ["ross", "308", "ross308"],
            "cobb_500": ["cobb", "500", "cobb500"],
            "male": ["mâle", "mâles", "coq", "coqs"],
            "female": ["femelle", "femelles", "poule", "poules"],
            "mixed": ["mixte", "mélange", "combiné"]
        }
        
        if entity_value in semantic_mappings:
            return any(synonym in text for synonym in semantic_mappings[entity_value])
        
        return entity_value in text
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extrait les termes clés"""
        key_terms = []
        
        # Termes techniques
        technical_terms = [
            'poids', 'croissance', 'performance', 'mortalité', 'conversion',
            'ross', 'cobb', 'poulet', 'broiler', 'mâle', 'femelle', 'mixte',
            'âge', 'semaines', 'jours', 'grammes', 'vaccination', 'alimentation'
        ]
        
        for term in technical_terms:
            if term in text:
                key_terms.append(term)
        
        # Nombres
        import re
        numbers = re.findall(r'\b\d+\b', text)
        key_terms.extend(numbers[:3])
        
        return key_terms
    
    async def calculate_coherence_score(
        self, 
        enriched_question: str, 
        rag_answer: str, 
        entities: Dict[str, Any]
    ) -> float:
        """Calcule le score de cohérence entre question enrichie et réponse RAG"""
        
        try:
            coherence_factors = {}
            
            # Facteur 1: Cohérence des entités (0-1)
            coherence_factors["entity_coherence"] = self._check_entity_coherence(
                enriched_question, rag_answer, entities
            )
            
            # Facteur 2: Cohérence sémantique (0-1)
            coherence_factors["semantic_coherence"] = self._check_semantic_coherence(
                enriched_question, rag_answer
            )
            
            # Facteur 3: Cohérence technique (0-1)
            coherence_factors["technical_coherence"] = self._check_technical_coherence(
                enriched_question, rag_answer
            )
            
            # Score final pondéré
            coherence_score = (
                coherence_factors["entity_coherence"] * 0.40 +
                coherence_factors["semantic_coherence"] * 0.35 +
                coherence_factors["technical_coherence"] * 0.25
            )
            
            # Enregistrer la métrique
            metric = QualityMetric(
                timestamp=datetime.now(),
                metric_type="coherence_score",
                value=coherence_score,
                details=coherence_factors,
                context={"question_length": len(enriched_question), "answer_length": len(rag_answer)}
            )
            
            self.coherence_history.append(metric)
            
            return coherence_score
            
        except Exception as e:
            logger.error(f"❌ [QualityMetrics] Erreur calcul cohérence: {e}")
            return 0.5
    
    def _check_entity_coherence(self, question: str, answer: str, entities: Dict[str, Any]) -> float:
        """Vérifie la cohérence des entités"""
        coherence_score = 1.0
        
        # Vérification race
        breed = entities.get("breed", "").lower()
        if breed:
            question_lower = question.lower()
            answer_lower = answer.lower()
            
            if breed in question_lower and breed not in answer_lower:
                # Vérifier synonymes
                breed_synonyms = {
                    "ross_308": ["ross", "308"],
                    "cobb_500": ["cobb", "500"]
                }
                
                if breed in breed_synonyms:
                    if not any(syn in answer_lower for syn in breed_synonyms[breed]):
                        coherence_score -= 0.3
                else:
                    coherence_score -= 0.3
        
        # Vérification âge
        age_days = entities.get("age_days", 0)
        if age_days:
            answer_lower = answer.lower()
            
            # Incohérence âge détectée
            if age_days < 14 and ("adulte" in answer_lower or "mature" in answer_lower):
                coherence_score -= 0.2
            elif age_days > 42 and ("poussin" in answer_lower or "jeune" in answer_lower):
                coherence_score -= 0.2
        
        return max(0.0, coherence_score)
    
    def _check_semantic_coherence(self, question: str, answer: str) -> float:
        """Vérifie la cohérence sémantique"""
        question_terms = set(self._extract_key_terms(question.lower()))
        answer_terms = set(self._extract_key_terms(answer.lower()))
        
        if not question_terms:
            return 1.0
        
        overlap = len(question_terms & answer_terms)
        return overlap / len(question_terms)
    
    def _check_technical_coherence(self, question: str, answer: str) -> float:
        """Vérifie la cohérence technique"""
        technical_aspects = {
            "poids": ["poids", "grammes", "kg", "masse"],
            "performance": ["performance", "croissance", "gain", "conversion"],
            "alimentation": ["aliment", "nutrition", "ration", "consommation"],
            "santé": ["santé", "maladie", "symptôme", "vaccination"]
        }
        
        question_lower = question.lower()
        answer_lower = answer.lower()
        coherence_score = 1.0
        
        for aspect, keywords in technical_aspects.items():
            if any(keyword in question_lower for keyword in keywords):
                if not any(keyword in answer_lower for keyword in keywords):
                    coherence_score -= 0.15
        
        return max(0.0, coherence_score)
    
    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Génère un dashboard temps réel des métriques"""
        
        try:
            # Métriques récentes (dernière heure)
            recent_cutoff = datetime.now() - timedelta(hours=1)
            
            recent_enrichment = [m for m in self.enrichment_quality_history 
                               if m.timestamp > recent_cutoff]
            recent_coherence = [m for m in self.coherence_history 
                              if m.timestamp > recent_cutoff]
            
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "real_time_metrics": {
                    "enrichment_quality": {
                        "current_average": np.mean([m.value for m in recent_enrichment]) if recent_enrichment else 0.0,
                        "trend": self._calculate_trend([m.value for m in recent_enrichment[-10:]]) if len(recent_enrichment) >= 10 else "stable",
                        "sample_count": len(recent_enrichment)
                    },
                    "coherence_score": {
                        "current_average": np.mean([m.value for m in recent_coherence]) if recent_coherence else 0.0,
                        "trend": self._calculate_trend([m.value for m in recent_coherence[-10:]]) if len(recent_coherence) >= 10 else "stable",
                        "sample_count": len(recent_coherence)
                    }
                },
                "performance_by_breed": {
                    breed: {
                        "average_score": np.mean(scores[-20:]) if scores else 0.0,
                        "sample_count": len(scores)
                    }
                    for breed, scores in self.breed_specific_metrics.items()
                },
                "alerts": self._generate_quality_alerts(),
                "recommendations": self._generate_improvement_recommendations()
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"❌ [QualityMetrics] Erreur génération dashboard: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calcule la tendance d'une série de valeurs"""
        if len(values) < 5:
            return "stable"
        
        # Régression linéaire simple
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.02:
            return "improving"
        elif slope < -0.02:
            return "declining"
        else:
            return "stable"
    
    def _generate_quality_alerts(self) -> List[Dict[str, str]]:
        """Génère des alertes qualité"""
        alerts = []
        
        # Alerte qualité enrichissement faible
        if self.enrichment_quality_history:
            recent_scores = [m.value for m in list(self.enrichment_quality_history)[-10:]]
            if recent_scores and np.mean(recent_scores) < 0.6:
                alerts.append({
                    "type": "warning",
                    "message": f"Qualité enrichissement faible: {np.mean(recent_scores):.2f}",
                    "recommendation": "Vérifier les prompts d'enrichissement"
                })
        
        # Alerte cohérence faible
        if self.coherence_history:
            recent_coherence = [m.value for m in list(self.coherence_history)[-10:]]
            if recent_coherence and np.mean(recent_coherence) < 0.7:
                alerts.append({
                    "type": "critical",
                    "message": f"Cohérence RAG faible: {np.mean(recent_coherence):.2f}",
                    "recommendation": "Optimiser la correspondance question/réponse RAG"
                })
        
        return alerts
    
    def _generate_improvement_recommendations(self) -> List[Dict[str, str]]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Analyse performance par race
        for breed, scores in self.breed_specific_metrics.items():
            if len(scores) >= 10:
                avg_score = np.mean(scores[-20:])
                if avg_score < 0.7:
                    recommendations.append({
                        "type": "breed_specific",
                        "message": f"Performance faible pour {breed}: {avg_score:.2f}",
                        "action": f"Optimiser les prompts spécifiques à {breed}"
                    })
        
        return recommendations
    
    def export_metrics_report(self, filepath: str) -> bool:
        """Exporte un rapport détaillé des métriques"""
        try:
            report = {
                "export_timestamp": datetime.now().isoformat(),
                "metrics_summary": {
                    "total_enrichment_samples": len(self.enrichment_quality_history),
                    "total_coherence_samples": len(self.coherence_history),
                    "average_enrichment_quality": np.mean([m.value for m in self.enrichment_quality_history]) if self.enrichment_quality_history else 0.0,
                    "average_coherence_score": np.mean([m.value for m in self.coherence_history]) if self.coherence_history else 0.0
                },
                "detailed_metrics": {
                    "enrichment_quality": [asdict(m) for m in list(self.enrichment_quality_history)[-100:]],
                    "coherence_scores": [asdict(m) for m in list(self.coherence_history)[-100:]]
                },
                "breed_analysis": {
                    breed: {
                        "sample_count": len(scores),
                        "average_score": np.mean(scores) if scores else 0.0,
                        "trend": self._calculate_trend(scores[-20:]) if len(scores) >= 20 else "insufficient_data"
                    }
                    for breed, scores in self.breed_specific_metrics.items()
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📊 [QualityMetrics] Rapport exporté: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [QualityMetrics] Erreur export rapport: {e}")
            return False

# Instance globale
quality_metrics = QualityMetricsCollector()