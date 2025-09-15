# -*- coding: utf-8 -*-
"""
intent_processor.py - Point d'entrée principal pour le processeur d'intentions
Maintient la compatibilité avec les imports existants
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

# Imports des modules internes
from .intent_types import IntentType, IntentResult
from .vocabulary_extractor import PoultryVocabularyExtractor
from .query_expander import QueryExpander, _normalize_line, _normalize_metric, _normalize_age
from .entity_extractor import EntityExtractor
from .intent_classifier import IntentClassifier

logger = logging.getLogger(__name__)

class IntentProcessor:
    """Processeur principal - Version modulaire avec intégration Redis et seuils adaptatifs"""
    
    def __init__(self, intents_file_path: str):
        self.intents_config = self._load_intents_config(intents_file_path)
        self.vocabulary_extractor = PoultryVocabularyExtractor(self.intents_config)
        self.query_expander = QueryExpander(self.vocabulary_extractor)
        self.entity_extractor = EntityExtractor(self.intents_config)
        self.intent_classifier = IntentClassifier(self.intents_config)
        
        # Injection de vocab_extractor dans entity_extractor pour métriques
        self.entity_extractor._vocab_extractor = self.vocabulary_extractor
        
        # Statistiques étendues pour monitoring
        self.processing_stats = {
            "total_queries": 0,
            "avg_processing_time": 0.0,
            "cache_hits": 0,
            "domain_coverage_avg": 0.0,
            "expansion_success_rate": 0.0,
            "entity_extraction_avg": 0.0,
            "intent_confidence_avg": 0.0,
            "errors_count": 0,
            "entity_extractor_errors": 0,
            "adaptive_threshold_usage": {"high_confidence": 0, "normal": 0, "strict": 0},
            "semantic_fallback_attempts": 0,
            "guardrails_evidence_boost": 0,
            "last_reset": time.time()
        }
        
        logger.info(f"IntentProcessor Enhanced initialisé - Couverture: {self.get_coverage_summary()}")
    
    def _load_intents_config(self, file_path: str) -> dict:
        """Charge la configuration avec résolution automatique du chemin"""
        try:
            # Résolution automatique du chemin relatif (fix pour Docker)
            if not os.path.isabs(file_path):
                base_dir = Path(__file__).parent.resolve()
                file_path = base_dir / file_path
            
            if not Path(file_path).exists():
                logger.error(f"Fichier intents.json introuvable: {file_path}")
                return self._get_fallback_config()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validation étendue
            validation_result = self._validate_config(config)
            if not validation_result["valid"]:
                logger.warning(f"Configuration invalide: {validation_result['errors']}")
            
            logger.info(f"Configuration chargée: {file_path} (v{config.get('version', 'unknown')})")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON dans intents.json: {e}")
            return self._get_fallback_config()
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return self._get_fallback_config()
    
    def _validate_config(self, config: dict) -> Dict[str, Any]:
        """Valide la structure de configuration"""
        errors = []
        required_keys = ["aliases", "intents", "universal_slots"]
        
        for key in required_keys:
            if key not in config:
                errors.append(f"Clé manquante: {key}")
        
        # Validation des aliases
        if "aliases" in config:
            alias_categories = ["line", "site_type", "bird_type", "phase"]
            for category in alias_categories:
                if category not in config["aliases"]:
                    errors.append(f"Catégorie alias manquante: {category}")
        
        # Validation des intents
        if "intents" in config:
            for intent_name, intent_config in config["intents"].items():
                if "metrics" not in intent_config:
                    errors.append(f"Métriques manquantes pour intent: {intent_name}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": []
        }
    
    def _get_fallback_config(self) -> dict:
        """Configuration de fallback minimale"""
        return {
            "version": "fallback",
            "aliases": {
                "line": {"ross 308": ["ross", "r308", "ross308"]},
                "site_type": {"broiler_farm": ["broiler"]},
                "bird_type": {"broiler": ["chicken"]},
                "phase": {"starter": ["start"]}
            },
            "intents": {
                "metric_query": {"metrics": {"body_weight": {"unit": "g"}}}
            },
            "universal_slots": {},
            "defaults_by_topic": {}
        }
    
    def process_query(self, query: str, explain_score: Optional[float] = None) -> IntentResult:
        """Traite une requête avec métriques complètes et intégration explain_score"""
        start_time = time.time()
        self.processing_stats["total_queries"] += 1
        
        try:
            # 1. Classification domaine avec seuils adaptatifs
            is_poultry, vocab_confidence, vocab_details = self.vocabulary_extractor.is_poultry_related(query)
            
            # Mise à jour stats seuils adaptatifs
            adaptive_factors = vocab_details.get("adaptive_factors", {})
            if adaptive_factors.get("high_confidence", False):
                self.processing_stats["adaptive_threshold_usage"]["high_confidence"] += 1
            elif vocab_details.get("threshold_used", 0.12) < 0.12:
                self.processing_stats["adaptive_threshold_usage"]["strict"] += 1
            else:
                self.processing_stats["adaptive_threshold_usage"]["normal"] += 1
            
            if not is_poultry:
                processing_time = time.time() - start_time
                self._update_processing_stats(processing_time, vocab_confidence, 0, 0, vocab_confidence)
                
                return IntentResult(
                    intent_type=IntentType.OUT_OF_DOMAIN,
                    confidence=1.0 - vocab_confidence,
                    detected_entities={},
                    expanded_query=query,
                    metadata={
                        "classification_method": "vocabulary_extractor",
                        "vocab_details": vocab_details,
                        "processing_time": processing_time,
                        "fallback_reason": "low_domain_coverage",
                        "adaptive_threshold": vocab_details.get("threshold_used", 0.12)
                    },
                    processing_time=processing_time,
                    confidence_breakdown={"vocab_confidence": vocab_confidence},
                    vocabulary_coverage=vocab_details,
                    expansion_quality={}
                )
            
            # 2. Extraction d'entités avec normalisation (robuste)
            try:
                entities = self.entity_extractor.extract_entities(query)
            except Exception as e:
                self.processing_stats["entity_extractor_errors"] = self.processing_stats.get("entity_extractor_errors", 0) + 1
                logger.warning(f"Erreur extraction entités: {e}")
                entities = {}
            
            # 3. Expansion de requête avec métriques qualité
            expanded_query = self.query_expander.expand_query(query)
            expansion_quality = self.query_expander.get_expansion_quality(query, expanded_query)
            
            # 4. Classification d'intention avec explain_score
            intent_type, classification_breakdown = self.intent_classifier.classify_intent(
                query, entities, explain_score
            )
            
            # Mise à jour stats guardrails
            if explain_score is not None and explain_score > 0.7:
                self.processing_stats["guardrails_evidence_boost"] += 1
            
            # 5. Génération clé cache normalisée et fallback sémantique
            cache_key_normalized = self._generate_cache_key(entities)
            semantic_fallback_candidates = self.vocabulary_extractor.generate_semantic_fallback_candidates(entities)
            
            if semantic_fallback_candidates:
                self.processing_stats["semantic_fallback_attempts"] += 1
            
            # 6. Calcul de confiance finale optimisé
            confidence_components = self._calculate_confidence(
                vocab_confidence, entities, classification_breakdown, expansion_quality, explain_score
            )
            
            processing_time = time.time() - start_time
            
            # 7. Mise à jour statistiques avec nouvelles métriques
            self._update_processing_stats(
                processing_time, 
                vocab_confidence, 
                len(entities), 
                expansion_quality["expansion_ratio"], 
                confidence_components["final_confidence"]
            )
            
            # 8. Construction du résultat avec métriques complètes
            result = IntentResult(
                intent_type=intent_type,
                confidence=confidence_components["final_confidence"],
                detected_entities=entities,
                expanded_query=expanded_query,
                metadata={
                    "vocab_details": vocab_details,
                    "classification_breakdown": classification_breakdown,
                    "confidence_components": confidence_components,
                    "entities_count": len(entities),
                    "expansion_applied": expanded_query != query,
                    "processing_time": processing_time,
                    "config_version": self.intents_config.get("version", "unknown"),
                    "adaptive_threshold": vocab_details.get("threshold_used", 0.12),
                    "explain_score_used": explain_score,
                    "guardrails_boost": explain_score is not None and explain_score > 0.7
                },
                processing_time=processing_time,
                confidence_breakdown=confidence_components,
                vocabulary_coverage=vocab_details.get("domain_coverage", {}),
                expansion_quality=expansion_quality,
                cache_key_normalized=cache_key_normalized,
                semantic_fallback_candidates=semantic_fallback_candidates
            )
            
            logger.debug(f"Requête traitée: '{query[:50]}...' -> {intent_type.value} "
                        f"(conf: {confidence_components['final_confidence']:.3f}, "
                        f"cache_key: {cache_key_normalized})")
            return result
            
        except Exception as e:
            self.processing_stats["errors_count"] += 1
            processing_time = time.time() - start_time
            logger.error(f"Erreur traitement requête: {e}")
            
            return IntentResult(
                intent_type=IntentType.GENERAL_POULTRY,
                confidence=0.5,
                detected_entities={},
                expanded_query=query,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time
                },
                processing_time=processing_time
            )
    
    def _generate_cache_key(self, entities: Dict[str, Any]) -> str:
        """Génère une clé de cache normalisée avec fonctions communes"""
        line = entities.get("line_normalized") or entities.get("line") or ""
        if line:
            line = _normalize_line(line)
        
        metric = entities.get("metric") or entities.get("metrics") or ""
        if metric:
            metric = _normalize_metric(metric)
        
        age = entities.get("age_days") or entities.get("age") or ""
        if age:
            age = _normalize_age(str(age))
        
        parts = [p for p in [line, metric, age] if p]
        return ":".join(parts).lower()
    
    def _calculate_confidence(self, vocab_conf: float, entities: Dict, 
                            classification: Dict, expansion: Dict, 
                            explain_score: Optional[float] = None) -> Dict[str, float]:
        """Calcule la confiance finale avec facteurs multiples et explain_score"""
        
        # Confiance vocabulaire pondérée
        vocab_weight = min(0.95, vocab_conf + 0.15)
        
        # Confiance entités avec bonus normalisation
        entity_bonus = min(0.2, len(entities) * 0.05)
        if "line_normalized" in entities:
            entity_bonus += 0.03  # Bonus pour normalisation cache
        
        # Confiance classification
        best_score = max(
            breakdown.get("total_score", 0) 
            for breakdown in classification.values()
        )
        classification_conf = min(0.25, best_score * 0.03)
        
        # Confiance expansion avec bonus normalisation
        expansion_bonus = min(0.1, expansion.get("expansion_ratio", 1.0) * 0.05)
        if expansion.get("normalization_applied", False):
            expansion_bonus += 0.02
        
        # Nouveau: Bonus explain_score (intégration guardrails)
        explain_bonus = 0.0
        if explain_score is not None:
            if explain_score > 0.8:
                explain_bonus = 0.15  # Fort bonus si très haute évidence
            elif explain_score > 0.6:
                explain_bonus = 0.08  # Bonus modéré
        
        final_confidence = min(0.98, vocab_weight + entity_bonus + classification_conf + 
                              expansion_bonus + explain_bonus)
        
        return {
            "vocab_confidence": vocab_weight,
            "entity_bonus": entity_bonus, 
            "classification_confidence": classification_conf,
            "expansion_bonus": expansion_bonus,
            "explain_bonus": explain_bonus,
            "final_confidence": final_confidence
        }
    
    def _update_processing_stats(self, processing_time: float, domain_coverage: float, 
                                entities_count: int, expansion_ratio: float, confidence: float):
        """Met à jour les statistiques de traitement étendues"""
        total = self.processing_stats["total_queries"]
        
        # Moyennes mobiles
        self.processing_stats["avg_processing_time"] = (
            (self.processing_stats["avg_processing_time"] * (total - 1) + processing_time) / total
        )
        
        self.processing_stats["domain_coverage_avg"] = (
            (self.processing_stats["domain_coverage_avg"] * (total - 1) + domain_coverage) / total
        )
        
        self.processing_stats["expansion_success_rate"] = (
            (self.processing_stats["expansion_success_rate"] * (total - 1) + (1 if expansion_ratio > 1.0 else 0)) / total
        )
        
        self.processing_stats["entity_extraction_avg"] = (
            (self.processing_stats["entity_extraction_avg"] * (total - 1) + entities_count) / total
        )
        
        self.processing_stats["intent_confidence_avg"] = (
            (self.processing_stats["intent_confidence_avg"] * (total - 1) + confidence) / total
        )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Expose les stats pour /metrics"""
        return dict(self.processing_stats)
    
    def get_full_processing_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes - API pour health-check"""
        base_stats = {
            **self.processing_stats,
            "uptime_seconds": time.time() - self.processing_stats["last_reset"],
            "error_rate": self.processing_stats["errors_count"] / max(1, self.processing_stats["total_queries"]),
        }
        
        # Statistiques vocabulaire
        vocab_stats = self.vocabulary_extractor.get_coverage_stats()
        
        # Statistiques configuration
        config_stats = {
            "config_version": self.intents_config.get("version", "unknown"),
            "intents_count": len(self.intents_config.get("intents", {})),
            "total_metrics": sum(
                len(intent.get("metrics", {})) 
                for intent in self.intents_config.get("intents", {}).values()
            ),
            "alias_categories": len(self.intents_config.get("aliases", {}))
        }
        
        return {
            "processing": base_stats,
            "vocabulary": vocab_stats,
            "configuration": config_stats,
            "health_status": self._get_health_status(base_stats, vocab_stats)
        }
    
    def _get_health_status(self, processing_stats: Dict, vocab_stats: Dict) -> Dict[str, Any]:
        """Évalue l'état de santé du système"""
        issues = []
        
        # Vérifications santé
        if processing_stats["error_rate"] > 0.05:
            issues.append(f"Taux d'erreur élevé: {processing_stats['error_rate']:.1%}")
        
        if processing_stats["avg_processing_time"] > 2.0:
            issues.append(f"Temps de traitement élevé: {processing_stats['avg_processing_time']:.2f}s")
        
        if vocab_stats["total_keywords"] < 100:
            issues.append(f"Vocabulaire limité: {vocab_stats['total_keywords']} termes")
        
        if processing_stats["domain_coverage_avg"] < 0.3:
            issues.append(f"Couverture domaine faible: {processing_stats['domain_coverage_avg']:.1%}")
        
        # Status global
        if not issues:
            status = "healthy"
        elif len(issues) <= 2:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "issues": issues,
            "last_check": time.time(),
            "adaptive_thresholds": processing_stats["adaptive_threshold_usage"],
            "fallback_usage": processing_stats["semantic_fallback_attempts"],
            "guardrails_integration": processing_stats["guardrails_evidence_boost"]
        }
    
    def get_coverage_summary(self) -> Dict[str, int]:
        """Retourne un résumé de la couverture - Utile pour logs de démarrage"""
        return {
            "keywords": len(self.vocabulary_extractor.poultry_keywords),
            "aliases": len(self.vocabulary_extractor.alias_mappings),
            "metrics": len(self.vocabulary_extractor.metrics_vocabulary),
            "intents": len(self.intents_config.get("intents", {})),
            "entities": len(self.intents_config.get("universal_slots", {})),
            "genetic_terms": len(self.vocabulary_extractor.genetic_terms),
            "high_confidence_patterns": len(self.vocabulary_extractor.high_confidence_patterns)
        }
    
    def get_specialized_prompt(self, intent_result: IntentResult) -> Optional[str]:
        """Génère un prompt spécialisé - Version améliorée avec intégration cache/guardrails"""
        from .prompt_builder import PromptBuilder
        builder = PromptBuilder(self.intents_config)
        return builder.build_specialized_prompt(intent_result)


# Import des fonctions utilitaires pour maintenir la compatibilité
from .utils import (
    create_intent_processor,
    process_query_with_intents,
    get_intent_processor_health,
    get_cache_key_from_intent,
    get_semantic_fallback_keys,
    should_use_strict_threshold,
    get_guardrails_context,
    test_query_processing,
    SAMPLE_TEST_QUERIES
)

# Exports pour maintenir la compatibilité
__all__ = [
    'IntentProcessor',
    'IntentType', 
    'IntentResult',
    'create_intent_processor',
    'process_query_with_intents',
    'get_intent_processor_health',
    'get_cache_key_from_intent',
    'get_semantic_fallback_keys',
    'should_use_strict_threshold',
    'get_guardrails_context',
    'test_query_processing',
    'SAMPLE_TEST_QUERIES'
]