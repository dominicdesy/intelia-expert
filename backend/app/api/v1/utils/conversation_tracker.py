# app/api/v1/utils/conversation_tracker.py - NOUVEAU FICHIER
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import os

logger = logging.getLogger(__name__)

@dataclass
class ConversationMetrics:
    """Métriques d'une conversation"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_exchanges: int
    intent_accuracy: float
    context_completeness: float
    response_quality: float
    user_satisfaction: Optional[int]
    clarification_rounds: int
    successful_resolution: bool
    average_response_time: float
    dominant_intent: str
    species_identified: Optional[str]
    issues_encountered: List[str]

@dataclass 
class InteractionEvent:
    """Événement d'interaction dans une conversation"""
    timestamp: datetime
    event_type: str  # question, clarification, answer, feedback
    intent: str
    confidence: float
    context_completeness: float
    response_time_ms: Optional[int]
    user_feedback: Optional[int]
    metadata: Dict[str, Any]

class ConversationTracker:
    """
    Tracker pour analyser et améliorer les conversations.
    Collecte métriques, détecte patterns et identifie points d'amélioration.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("CONVERSATION_TRACKING_DB", "conversation_tracking.db")
        self.active_sessions: Dict[str, List[InteractionEvent]] = {}
        self.session_metrics: Dict[str, ConversationMetrics] = {}
        
        # Seuils de qualité
        self.quality_thresholds = {
            "intent_confidence_min": 0.7,
            "context_completeness_min": 0.6,
            "max_clarification_rounds": 3,
            "response_time_target_ms": 2000
        }
        
        self._init_database()

    def _init_database(self):
        """Initialise la base de données de tracking"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Table des métriques de conversation
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_id TEXT,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        total_exchanges INTEGER DEFAULT 0,
                        intent_accuracy REAL DEFAULT 0.0,
                        context_completeness REAL DEFAULT 0.0,
                        response_quality REAL DEFAULT 0.0,
                        user_satisfaction INTEGER,
                        clarification_rounds INTEGER DEFAULT 0,
                        successful_resolution BOOLEAN DEFAULT 0,
                        average_response_time REAL DEFAULT 0.0,
                        dominant_intent TEXT,
                        species_identified TEXT,
                        issues_encountered TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Table des événements d'interaction
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interaction_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        intent TEXT,
                        confidence REAL,
                        context_completeness REAL,
                        response_time_ms INTEGER,
                        user_feedback INTEGER,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES conversation_metrics (session_id)
                    )
                """)
                
                # Index pour performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON conversation_metrics(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON conversation_metrics(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON conversation_metrics(start_time)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON interaction_events(session_id)")
                
                logger.info("✅ Base de données de tracking initialisée")
                
        except Exception as e:
            logger.error("❌ Erreur initialisation DB tracking: %s", e)

    def start_conversation(self, session_id: str, user_id: str = None) -> None:
        """Démarre le tracking d'une nouvelle conversation"""
        
        now = datetime.utcnow()
        
        # Initialiser tracking en mémoire
        self.active_sessions[session_id] = []
        self.session_metrics[session_id] = ConversationMetrics(
            session_id=session_id,
            user_id=user_id or "anonymous",
            start_time=now,
            end_time=None,
            total_exchanges=0,
            intent_accuracy=0.0,
            context_completeness=0.0,
            response_quality=0.0,
            user_satisfaction=None,
            clarification_rounds=0,
            successful_resolution=False,
            average_response_time=0.0,
            dominant_intent="unknown",
            species_identified=None,
            issues_encountered=[]
        )
        
        logger.debug("🏁 Conversation tracking démarré: %s", session_id)

    def track_interaction(
        self,
        session_id: str,
        event_type: str,
        intent: str = "unknown",
        confidence: float = 0.0,
        context_completeness: float = 0.0,
        response_time_ms: Optional[int] = None,
        user_feedback: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Enregistre une interaction"""
        
        if session_id not in self.active_sessions:
            self.start_conversation(session_id)
        
        # Créer événement
        event = InteractionEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            intent=intent,
            confidence=confidence,
            context_completeness=context_completeness,
            response_time_ms=response_time_ms,
            user_feedback=user_feedback,
            metadata=metadata or {}
        )
        
        # Ajouter à la session
        self.active_sessions[session_id].append(event)
        
        # Mettre à jour métriques en temps réel
        self._update_session_metrics(session_id, event)
        
        logger.debug("📊 Interaction trackée: %s | %s | intent=%s", 
                    session_id, event_type, intent)

    def end_conversation(
        self, 
        session_id: str, 
        successful_resolution: bool = True,
        user_satisfaction: Optional[int] = None
    ) -> ConversationMetrics:
        """Termine et sauvegarde une conversation"""
        
        if session_id not in self.session_metrics:
            logger.warning("⚠️ Session inconnue pour fin: %s", session_id)
            return None
        
        # Finaliser métriques
        metrics = self.session_metrics[session_id]
        metrics.end_time = datetime.utcnow()
        metrics.successful_resolution = successful_resolution
        if user_satisfaction is not None:
            metrics.user_satisfaction = user_satisfaction
        
        # Calculs finaux
        self._finalize_session_metrics(session_id)
        
        # Sauvegarder en base
        self._persist_conversation(session_id)
        
        # Nettoyer mémoire
        final_metrics = self.session_metrics.pop(session_id, None)
        self.active_sessions.pop(session_id, None)
        
        logger.info("🏁 Conversation terminée: %s | résolution=%s | satisfaction=%s", 
                   session_id, successful_resolution, user_satisfaction)
        
        return final_metrics

    def _update_session_metrics(self, session_id: str, event: InteractionEvent) -> None:
        """Met à jour les métriques de session en temps réel"""
        
        metrics = self.session_metrics[session_id]
        events = self.active_sessions[session_id]
        
        # Compter échanges
        if event.event_type in ["question", "answer"]:
            metrics.total_exchanges += 0.5  # Question + réponse = 1 échange
        
        # Compter clarifications
        if event.event_type == "clarification":
            metrics.clarification_rounds += 1
        
        # Moyenne confiance intention
        intent_events = [e for e in events if e.confidence > 0]
        if intent_events:
            metrics.intent_accuracy = sum(e.confidence for e in intent_events) / len(intent_events)
        
        # Moyenne complétude contexte
        context_events = [e for e in events if e.context_completeness > 0]
        if context_events:
            metrics.context_completeness = sum(e.context_completeness for e in context_events) / len(context_events)
        
        # Temps de réponse moyen
        response_events = [e for e in events if e.response_time_ms is not None]
        if response_events:
            metrics.average_response_time = sum(e.response_time_ms for e in response_events) / len(response_events)
        
        # Intention dominante
        intent_counts = defaultdict(int)
        for e in events:
            if e.intent != "unknown":
                intent_counts[e.intent] += 1
        if intent_counts:
            metrics.dominant_intent = max(intent_counts, key=intent_counts.get)
        
        # Espèce identifiée
        for e in events:
            species = e.metadata.get("species") or e.metadata.get("inferred_species")
            if species:
                metrics.species_identified = species
                break
        
        # Issues rencontrées
        issues = set(metrics.issues_encountered)
        if event.confidence < self.quality_thresholds["intent_confidence_min"]:
            issues.add("low_intent_confidence")
        if event.context_completeness < self.quality_thresholds["context_completeness_min"]:
            issues.add("incomplete_context")
        if metrics.clarification_rounds > self.quality_thresholds["max_clarification_rounds"]:
            issues.add("excessive_clarifications")
        if event.response_time_ms and event.response_time_ms > self.quality_thresholds["response_time_target_ms"]:
            issues.add("slow_response")
        
        metrics.issues_encountered = list(issues)

    def _finalize_session_metrics(self, session_id: str) -> None:
        """Finalise les calculs de métriques"""
        
        metrics = self.session_metrics[session_id]
        events = self.active_sessions[session_id]
        
        if not events:
            return
        
        # Qualité de réponse basée sur feedback utilisateur et métriques
        quality_factors = []
        
        # Facteur feedback utilisateur
        feedback_events = [e for e in events if e.user_feedback is not None]
        if feedback_events:
            avg_feedback = sum(e.user_feedback for e in feedback_events) / len(feedback_events)
            quality_factors.append(max(0, avg_feedback))  # Normaliser feedback négatif
        
        # Facteur confiance intention
        if metrics.intent_accuracy > 0:
            quality_factors.append(metrics.intent_accuracy)
        
        # Facteur complétude contexte
        if metrics.context_completeness > 0:
            quality_factors.append(metrics.context_completeness)
        
        # Facteur efficacité (inverse des clarifications)
        if metrics.clarification_rounds == 0:
            efficiency = 1.0
        else:
            efficiency = max(0.2, 1.0 - (metrics.clarification_rounds * 0.2))
        quality_factors.append(efficiency)
        
        # Score qualité final
        if quality_factors:
            metrics.response_quality = sum(quality_factors) / len(quality_factors)
        
        # Ajuster total_exchanges (arrondir)
        metrics.total_exchanges = int(metrics.total_exchanges)

    def _persist_conversation(self, session_id: str) -> None:
        """Sauvegarde la conversation en base de données"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                metrics = self.session_metrics[session_id]
                events = self.active_sessions[session_id]
                
                # Insérer métriques
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_metrics
                    (session_id, user_id, start_time, end_time, total_exchanges,
                     intent_accuracy, context_completeness, response_quality,
                     user_satisfaction, clarification_rounds, successful_resolution,
                     average_response_time, dominant_intent, species_identified,
                     issues_encountered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.session_id,
                    metrics.user_id,
                    metrics.start_time.isoformat(),
                    metrics.end_time.isoformat() if metrics.end_time else None,
                    metrics.total_exchanges,
                    metrics.intent_accuracy,
                    metrics.context_completeness,
                    metrics.response_quality,
                    metrics.user_satisfaction,
                    metrics.clarification_rounds,
                    metrics.successful_resolution,
                    metrics.average_response_time,
                    metrics.dominant_intent,
                    metrics.species_identified,
                    json.dumps(metrics.issues_encountered)
                ))
                
                # Insérer événements
                for event in events:
                    conn.execute("""
                        INSERT INTO interaction_events
                        (session_id, timestamp, event_type, intent, confidence,
                         context_completeness, response_time_ms, user_feedback, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        event.timestamp.isoformat(),
                        event.event_type,
                        event.intent,
                        event.confidence,
                        event.context_completeness,
                        event.response_time_ms,
                        event.user_feedback,
                        json.dumps(event.metadata)
                    ))
                
                logger.debug("💾 Conversation sauvegardée: %s", session_id)
                
        except Exception as e:
            logger.error("❌ Erreur sauvegarde conversation %s: %s", session_id, e)

    def get_session_analytics(
        self, 
        days: int = 7,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Récupère les analytiques des sessions"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Construire filtre
                where_clauses = ["datetime(start_time) >= datetime('now', '-{} days')".format(days)]
                params = []
                
                if user_id:
                    where_clauses.append("user_id = ?")
                    params.append(user_id)
                
                where_clause = " AND ".join(where_clauses)
                
                # Métriques générales
                general_stats = conn.execute(f"""
                    SELECT 
                        COUNT(*) as total_conversations,
                        AVG(total_exchanges) as avg_exchanges,
                        AVG(intent_accuracy) as avg_intent_accuracy,
                        AVG(context_completeness) as avg_context_completeness,
                        AVG(response_quality) as avg_response_quality,
                        AVG(clarification_rounds) as avg_clarifications,
                        AVG(average_response_time) as avg_response_time,
                        SUM(CASE WHEN successful_resolution = 1 THEN 1 ELSE 0 END) as successful_resolutions,
                        AVG(CASE WHEN user_satisfaction IS NOT NULL THEN user_satisfaction END) as avg_satisfaction
                    FROM conversation_metrics 
                    WHERE {where_clause}
                """, params).fetchone()
                
                # Distribution par intention
                intent_distribution = conn.execute(f"""
                    SELECT dominant_intent, COUNT(*) as count
                    FROM conversation_metrics 
                    WHERE {where_clause} AND dominant_intent IS NOT NULL
                    GROUP BY dominant_intent
                    ORDER BY count DESC
                    LIMIT 10
                """, params).fetchall()
                
                # Issues fréquentes
                issue_analysis = self._analyze_frequent_issues(conn, where_clause, params)
                
                # Tendances temporelles
                temporal_trends = conn.execute(f"""
                    SELECT 
                        DATE(start_time) as date,
                        COUNT(*) as conversations,
                        AVG(response_quality) as avg_quality,
                        AVG(clarification_rounds) as avg_clarifications
                    FROM conversation_metrics 
                    WHERE {where_clause}
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    LIMIT 30
                """, params).fetchall()
                
                return {
                    "period_days": days,
                    "user_filter": user_id,
                    "general_stats": dict(general_stats) if general_stats else {},
                    "intent_distribution": [dict(row) for row in intent_distribution],
                    "frequent_issues": issue_analysis,
                    "temporal_trends": [dict(row) for row in temporal_trends],
                    "quality_metrics": self._calculate_quality_metrics(general_stats),
                    "recommendations": self._generate_recommendations(general_stats, issue_analysis)
                }
                
        except Exception as e:
            logger.error("❌ Erreur analytics: %s", e)
            return {"error": str(e)}

    def _analyze_frequent_issues(
        self, 
        conn, 
        where_clause: str, 
        params: List
    ) -> Dict[str, Any]:
        """Analyse les issues fréquentes"""
        
        # Récupérer toutes les issues
        rows = conn.execute(f"""
            SELECT issues_encountered 
            FROM conversation_metrics 
            WHERE {where_clause} AND issues_encountered IS NOT NULL
        """, params).fetchall()
        
        # Compter occurrences
        issue_counts = defaultdict(int)
        total_conversations = 0
        
        for row in rows:
            total_conversations += 1
            try:
                issues = json.loads(row[0])
                for issue in issues:
                    issue_counts[issue] += 1
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Calculer fréquences
        issue_frequencies = []
        for issue, count in issue_counts.items():
            frequency = (count / total_conversations) * 100 if total_conversations > 0 else 0
            issue_frequencies.append({
                "issue": issue,
                "count": count,
                "frequency_pct": round(frequency, 1)
            })
        
        # Trier par fréquence
        issue_frequencies.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "total_conversations_with_issues": total_conversations,
            "top_issues": issue_frequencies[:10],
            "issue_categories": self._categorize_issues(issue_frequencies)
        }

    def _categorize_issues(self, issue_frequencies: List[Dict]) -> Dict[str, List[Dict]]:
        """Catégorise les issues par type"""
        
        categories = {
            "intent_classification": [],
            "context_extraction": [],
            "performance": [],
            "user_experience": []
        }
        
        for issue in issue_frequencies:
            issue_name = issue["issue"]
            
            if "intent" in issue_name or "confidence" in issue_name:
                categories["intent_classification"].append(issue)
            elif "context" in issue_name or "incomplete" in issue_name:
                categories["context_extraction"].append(issue)
            elif "response" in issue_name or "slow" in issue_name:
                categories["performance"].append(issue)
            elif "clarification" in issue_name or "satisfaction" in issue_name:
                categories["user_experience"].append(issue)
            else:
                categories["user_experience"].append(issue)  # Défaut
        
        return categories

    def _calculate_quality_metrics(self, general_stats) -> Dict[str, Any]:
        """Calcule des métriques de qualité"""
        
        if not general_stats:
            return {}
        
        metrics = {}
        
        # Taux de succès
        total = general_stats["total_conversations"] or 1
        success_rate = (general_stats["successful_resolutions"] or 0) / total
        metrics["success_rate"] = round(success_rate * 100, 1)
        
        # Efficacité (inverse des clarifications)
        avg_clarifications = general_stats["avg_clarifications"] or 0
        efficiency = max(0, 1 - (avg_clarifications / 5))  # Normaliser sur 5 max
        metrics["efficiency_score"] = round(efficiency * 100, 1)
        
        # Score qualité global
        quality_components = []
        if general_stats["avg_intent_accuracy"]:
            quality_components.append(general_stats["avg_intent_accuracy"])
        if general_stats["avg_context_completeness"]:
            quality_components.append(general_stats["avg_context_completeness"])
        if general_stats["avg_response_quality"]:
            quality_components.append(general_stats["avg_response_quality"])
        
        if quality_components:
            overall_quality = sum(quality_components) / len(quality_components)
            metrics["overall_quality_score"] = round(overall_quality * 100, 1)
        
        # Performance temporelle
        avg_response_time = general_stats["avg_response_time"] or 0
        if avg_response_time > 0:
            time_score = max(0, 1 - (avg_response_time / 5000))  # 5s = score 0
            metrics["response_time_score"] = round(time_score * 100, 1)
        
        return metrics

    def _generate_recommendations(
        self, 
        general_stats, 
        issue_analysis: Dict[str, Any]
    ) -> List[str]:
        """Génère des recommandations d'amélioration"""
        
        recommendations = []
        
        if not general_stats:
            return recommendations
        
        # Recommandations basées sur métriques
        if general_stats["avg_intent_accuracy"] and general_stats["avg_intent_accuracy"] < 0.7:
            recommendations.append("Améliorer la classification d'intentions (précision < 70%)")
        
        if general_stats["avg_context_completeness"] and general_stats["avg_context_completeness"] < 0.6:
            recommendations.append("Optimiser l'extraction de contexte (complétude < 60%)")
        
        if general_stats["avg_clarifications"] and general_stats["avg_clarifications"] > 2:
            recommendations.append("Réduire le nombre de clarifications (moyenne > 2)")
        
        if general_stats["avg_response_time"] and general_stats["avg_response_time"] > 3000:
            recommendations.append("Améliorer les temps de réponse (moyenne > 3s)")
        
        # Recommandations basées sur issues fréquentes
        top_issues = issue_analysis.get("top_issues", [])
        
        for issue in top_issues[:3]:  # Top 3
            if issue["frequency_pct"] > 20:  # Si > 20% des conversations
                issue_name = issue["issue"]
                
                if issue_name == "low_intent_confidence":
                    recommendations.append("Améliorer la confiance de classification d'intentions")
                elif issue_name == "incomplete_context":
                    recommendations.append("Renforcer l'extraction d'informations contextuelles")
                elif issue_name == "excessive_clarifications":
                    recommendations.append("Optimiser les stratégies de clarification")
                elif issue_name == "slow_response":
                    recommendations.append("Optimiser les performances de génération de réponse")
        
        return recommendations[:5]  # Limiter à 5 recommandations

    def get_user_journey_analysis(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Analyse le parcours d'un utilisateur spécifique"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Conversations de l'utilisateur
                conversations = conn.execute("""
                    SELECT * FROM conversation_metrics 
                    WHERE user_id = ? 
                    AND datetime(start_time) >= datetime('now', '-{} days')
                    ORDER BY start_time DESC
                """.format(days), (user_id,)).fetchall()
                
                if not conversations:
                    return {"user_id": user_id, "conversations": [], "analysis": "Aucune conversation trouvée"}
                
                # Analyse d'évolution
                evolution = self._analyze_user_evolution(conversations)
                
                # Patterns d'usage
                usage_patterns = self._analyze_usage_patterns(conversations)
                
                # Préférences détectées
                preferences = self._detect_user_preferences(conn, user_id)
                
                return {
                    "user_id": user_id,
                    "period_days": days,
                    "total_conversations": len(conversations),
                    "evolution": evolution,
                    "usage_patterns": usage_patterns,
                    "preferences": preferences,
                    "recent_conversations": [dict(conv) for conv in conversations[:5]]
                }
                
        except Exception as e:
            logger.error("❌ Erreur analyse utilisateur %s: %s", user_id, e)
            return {"error": str(e)}

    def _analyze_user_evolution(self, conversations: List) -> Dict[str, Any]:
        """Analyse l'évolution d'un utilisateur"""
        
        if len(conversations) < 2:
            return {"trend": "insufficient_data"}
        
        # Trier par date croissante pour analyse temporelle
        sorted_convs = sorted(conversations, key=lambda x: x["start_time"])
        
        # Calculer tendances
        recent_half = sorted_convs[len(sorted_convs)//2:]
        early_half = sorted_convs[:len(sorted_convs)//2]
        
        def avg_metric(convs, metric):
            values = [c[metric] for c in convs if c[metric] is not None]
            return sum(values) / len(values) if values else 0
        
        evolution = {}
        
        # Évolution qualité
        early_quality = avg_metric(early_half, "response_quality")
        recent_quality = avg_metric(recent_half, "response_quality")
        evolution["quality_trend"] = "improving" if recent_quality > early_quality else "declining"
        
        # Évolution efficacité (moins de clarifications = meilleur)
        early_clarifications = avg_metric(early_half, "clarification_rounds")
        recent_clarifications = avg_metric(recent_half, "clarification_rounds")
        evolution["efficiency_trend"] = "improving" if recent_clarifications < early_clarifications else "declining"
        
        # Évolution engagement
        evolution["engagement_level"] = "high" if len(conversations) > 10 else "moderate" if len(conversations) > 3 else "low"
        
        return evolution

    def _analyze_usage_patterns(self, conversations: List) -> Dict[str, Any]:
        """Analyse les patterns d'usage"""
        
        patterns = {}
        
        # Intentions préférées
        intent_counts = defaultdict(int)
        for conv in conversations:
            if conv["dominant_intent"]:
                intent_counts[conv["dominant_intent"]] += 1
        
        if intent_counts:
            patterns["preferred_intents"] = [
                {"intent": intent, "count": count} 
                for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
        
        # Espèces fréquentes
        species_counts = defaultdict(int)
        for conv in conversations:
            if conv["species_identified"]:
                species_counts[conv["species_identified"]] += 1
        
        if species_counts:
            patterns["frequent_species"] = [
                {"species": species, "count": count}
                for species, count in sorted(species_counts.items(), key=lambda x: x[1], reverse=True)
            ]
        
        # Complexité moyenne
        avg_exchanges = sum(conv["total_exchanges"] for conv in conversations) / len(conversations)
        patterns["complexity_level"] = "high" if avg_exchanges > 3 else "medium" if avg_exchanges > 1.5 else "low"
        
        return patterns

    def _detect_user_preferences(self, conn, user_id: str) -> Dict[str, Any]:
        """Détecte les préférences utilisateur depuis les interactions"""
        
        # Récupérer événements détaillés
        events = conn.execute("""
            SELECT metadata FROM interaction_events ie
            JOIN conversation_metrics cm ON ie.session_id = cm.session_id
            WHERE cm.user_id = ?
            AND ie.metadata IS NOT NULL
            ORDER BY ie.timestamp DESC
            LIMIT 100
        """, (user_id,)).fetchall()
        
        preferences = {
            "response_style": "standard",
            "detail_level": "medium",
            "species_focus": None,
            "technical_level": "intermediate"
        }
        
        # Analyser métadonnées pour détecter préférences
        for event in events:
            try:
                metadata = json.loads(event[0])
                
                # Style de réponse préféré
                if metadata.get("ui_style", {}).get("style") == "minimal":
                    preferences["response_style"] = "concise"
                elif metadata.get("ui_style", {}).get("format") == "detailed":
                    preferences["response_style"] = "detailed"
                
                # Espèce de focus
                species = metadata.get("species") or metadata.get("inferred_species")
                if species:
                    preferences["species_focus"] = species
                    break  # Prendre la plus récente
                    
            except (json.JSONDecodeError, TypeError):
                continue
        
        return preferences

    def export_analytics(
        self, 
        format: str = "json",
        days: int = 30,
        include_events: bool = False
    ) -> Dict[str, Any]:
        """Exporte les analytiques pour analyse externe"""
        
        try:
            analytics = self.get_session_analytics(days=days)
            
            if include_events:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    
                    # Récupérer événements récents
                    events = conn.execute("""
                        SELECT ie.*, cm.user_id
                        FROM interaction_events ie
                        JOIN conversation_metrics cm ON ie.session_id = cm.session_id
                        WHERE datetime(ie.timestamp) >= datetime('now', '-{} days')
                        ORDER BY ie.timestamp DESC
                        LIMIT 1000
                    """.format(days)).fetchall()
                    
                    analytics["detailed_events"] = [dict(event) for event in events]
            
            # Ajouter métadonnées d'export
            analytics["export_metadata"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "format": format,
                "period_days": days,
                "include_events": include_events,
                "total_records": analytics.get("general_stats", {}).get("total_conversations", 0)
            }
            
            return analytics
            
        except Exception as e:
            logger.error("❌ Erreur export analytics: %s", e)
            return {"error": str(e)}

    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Nettoie les anciennes données"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Supprimer anciennes conversations
                cursor = conn.execute("""
                    DELETE FROM conversation_metrics 
                    WHERE datetime(start_time) < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                conversations_deleted = cursor.rowcount
                
                # Supprimer anciens événements (orphelins automatiquement nettoyés par FK)
                cursor = conn.execute("""
                    DELETE FROM interaction_events 
                    WHERE datetime(timestamp) < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                events_deleted = cursor.rowcount
                
                # Vacuum pour récupérer espace
                conn.execute("VACUUM")
                
                logger.info("🧹 Nettoyage: %d conversations, %d événements supprimés", 
                           conversations_deleted, events_deleted)
                
                return {
                    "conversations_deleted": conversations_deleted,
                    "events_deleted": events_deleted,
                    "days_kept": days_to_keep
                }
                
        except Exception as e:
            logger.error("❌ Erreur nettoyage: %s", e)
            return {"error": str(e)}

# Instance globale
_tracker = ConversationTracker()

def start_conversation_tracking(session_id: str, user_id: str = None) -> None:
    """Interface publique pour démarrer le tracking"""
    _tracker.start_conversation(session_id, user_id)

def track_conversation_event(
    session_id: str,
    event_type: str,
    intent: str = "unknown",
    confidence: float = 0.0,
    context_completeness: float = 0.0,
    response_time_ms: Optional[int] = None,
    user_feedback: Optional[int] = None,
    metadata: Dict[str, Any] = None
) -> None:
    """Interface publique pour tracker une interaction"""
    _tracker.track_interaction(
        session_id, event_type, intent, confidence, 
        context_completeness, response_time_ms, user_feedback, metadata
    )

def end_conversation_tracking(
    session_id: str,
    successful_resolution: bool = True,
    user_satisfaction: Optional[int] = None
) -> Optional[ConversationMetrics]:
    """Interface publique pour terminer le tracking"""
    return _tracker.end_conversation(session_id, successful_resolution, user_satisfaction)

def get_conversation_analytics(days: int = 7, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Interface publique pour les analytics"""
    return _tracker.get_session_analytics(days, user_id)

def get_user_analytics(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Interface publique pour analytics utilisateur"""
    return _tracker.get_user_journey_analysis(user_id, days)
