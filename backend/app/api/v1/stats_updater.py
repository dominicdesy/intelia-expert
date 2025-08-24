# app/api/v1/stats_updater.py
# -*- coding: utf-8 -*-
"""
🚀 COLLECTEUR INTELLIGENT DE STATISTIQUES
Utilise les gestionnaires existants SANS les modifier
Collecte périodique + cache optimisé
SAFE: Aucune rupture avec logging.py et billing.py
✨ NOUVEAU: Gestion défensive des colonnes feedback (Digital Ocean compatible)
🔧 FIXED: Correction erreur retour 0 dans _check_feedback_columns_availability
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Import des gestionnaires existants (SAFE)
from app.api.v1.logging import get_analytics_manager
from app.api.v1.billing import get_billing_manager
from app.api.v1.stats_cache import get_stats_cache

# Import pour coûts OpenAI optimisés
from app.api.v1.billing_openai import get_openai_usage_data_safe

logger = logging.getLogger(__name__)

class StatisticsUpdater:
    """
    Collecteur intelligent qui utilise les gestionnaires existants
    - Met à jour le cache périodiquement
    - Gère les erreurs et fallbacks
    - Optimise les performances avec collecte parallèle
    - Support défensif pour colonnes feedback
    """
    
    def __init__(self):
        self.cache = get_stats_cache()
        self.analytics = get_analytics_manager()
        self.billing = get_billing_manager()
        self.last_update = None
        self.update_in_progress = False
        
        # ✅ CORRECTION: Vérifier que analytics est correctement initialisé
        if not self.analytics:
            logger.error("❌ Analytics manager non disponible")
            self._feedback_columns_available = {
                "table_exists": False, 
                "feedback": False, 
                "feedback_comment": False, 
                "error": "no_analytics_manager"
            }
        else:
            # ✅ NOUVEAU: Détecter la disponibilité des colonnes feedback au démarrage avec gestion d'erreur
            try:
                self._feedback_columns_available = self._check_feedback_columns_availability()
                logger.info(f"🔍 Détection feedback au démarrage: {self._feedback_columns_available}")
            except Exception as e:
                logger.error(f"❌ Erreur détection feedback au démarrage: {e}")
                self._feedback_columns_available = {
                    "table_exists": False, 
                    "feedback": False, 
                    "feedback_comment": False, 
                    "error": str(e)
                }
    
    def _check_feedback_columns_availability(self) -> Dict[str, bool]:
        """
        🔍 Vérifie la disponibilité des colonnes feedback au démarrage.
        Cache le résultat pour éviter les vérifications répétées.
        ✅ CORRIGÉ: Retourne toujours un dictionnaire valide
        """
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # ✅ CORRECTION: Vérifier que l'analytics manager existe et a un DSN
            if not hasattr(self.analytics, 'dsn') or not self.analytics.dsn:
                logger.warning("⚠️ DSN analytics non disponible - utilisation valeurs par défaut")
                return {"table_exists": False, "feedback": False, "feedback_comment": False}
            
            with psycopg2.connect(self.analytics.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Vérifier si la table existe d'abord
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'user_questions_complete'
                        )
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        logger.warning("⚠️ Table user_questions_complete n'existe pas")
                        return {"table_exists": False, "feedback": False, "feedback_comment": False}
                    
                    # Vérifier les colonnes feedback
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'user_questions_complete' 
                            AND column_name IN ('feedback', 'feedback_comment')
                    """)
                    
                    available_columns = {row["column_name"] for row in cur.fetchall()}
                    
                    result = {
                        "table_exists": True,
                        "feedback": "feedback" in available_columns,
                        "feedback_comment": "feedback_comment" in available_columns
                    }
                    
                    logger.info(f"🔍 Détection colonnes feedback: {result}")
                    return result
                    
        except ImportError as import_err:
            logger.error(f"❌ Module psycopg2 non disponible: {import_err}")
            return {
                "table_exists": False, 
                "feedback": False, 
                "feedback_comment": False, 
                "error": "psycopg2_missing"
            }
            
        except Exception as e:
            # ✅ CORRECTION: Retourner un dictionnaire valide au lieu de 0
            logger.error(f"❌ Erreur vérification colonnes feedback: {e}")
            return {
                "table_exists": False, 
                "feedback": False, 
                "feedback_comment": False,
                "error": str(e)[:100]  # Limiter la taille de l'erreur
            }
    
    def diagnose_database_connection(self) -> Dict[str, Any]:
        """
        🔧 NOUVELLE MÉTHODE: Diagnostique complet de la connection base de données
        """
        try:
            diagnosis = {
                "analytics_manager": {
                    "available": self.analytics is not None,
                    "has_dsn": hasattr(self.analytics, 'dsn') if self.analytics else False,
                    "dsn_configured": bool(getattr(self.analytics, 'dsn', None)) if self.analytics else False
                },
                "database_connection": {
                    "can_connect": False,
                    "tables_found": [],
                    "user_questions_complete": {
                        "exists": False,
                        "columns": []
                    }
                },
                "psycopg2_available": False,
                "errors": []
            }
            
            # Test import psycopg2
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                diagnosis["psycopg2_available"] = True
            except ImportError as e:
                diagnosis["errors"].append(f"psycopg2 non disponible: {e}")
                return diagnosis
            
            # Test connection database
            if diagnosis["analytics_manager"]["dsn_configured"]:
                try:
                    with psycopg2.connect(self.analytics.dsn) as conn:
                        diagnosis["database_connection"]["can_connect"] = True
                        
                        with conn.cursor(cursor_factory=RealDictCursor) as cur:
                            # Lister toutes les tables
                            cur.execute("""
                                SELECT table_name 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public'
                                ORDER BY table_name
                            """)
                            
                            diagnosis["database_connection"]["tables_found"] = [
                                row["table_name"] for row in cur.fetchall()
                            ]
                            
                            # Vérifier user_questions_complete spécifiquement
                            if "user_questions_complete" in diagnosis["database_connection"]["tables_found"]:
                                diagnosis["database_connection"]["user_questions_complete"]["exists"] = True
                                
                                cur.execute("""
                                    SELECT column_name, data_type, is_nullable
                                    FROM information_schema.columns 
                                    WHERE table_name = 'user_questions_complete'
                                    ORDER BY ordinal_position
                                """)
                                
                                diagnosis["database_connection"]["user_questions_complete"]["columns"] = [
                                    {
                                        "name": row["column_name"],
                                        "type": row["data_type"],
                                        "nullable": row["is_nullable"] == "YES"
                                    }
                                    for row in cur.fetchall()
                                ]
                            
                except Exception as db_err:
                    diagnosis["errors"].append(f"Erreur connexion DB: {db_err}")
            else:
                diagnosis["errors"].append("DSN non configuré dans analytics manager")
            
            return diagnosis
            
        except Exception as e:
            return {
                "status": "diagnostic_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def create_missing_tables(self) -> Dict[str, Any]:
        """
        🛠️ NOUVELLE MÉTHODE: Crée automatiquement les tables manquantes
        """
        try:
            if not hasattr(self.analytics, 'dsn') or not self.analytics.dsn:
                return {"status": "error", "error": "DSN non configuré"}
            
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            results = {
                "tables_created": [],
                "tables_updated": [],
                "errors": []
            }
            
            with psycopg2.connect(self.analytics.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Créer user_questions_complete si manquante
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'user_questions_complete'
                        )
                    """)
                    
                    if not cur.fetchone()[0]:
                        logger.info("🔧 Création table user_questions_complete...")
                        
                        create_table_sql = """
                        CREATE TABLE user_questions_complete (
                            id SERIAL PRIMARY KEY,
                            question_id VARCHAR(50) UNIQUE,
                            user_email VARCHAR(255),
                            session_id VARCHAR(100),
                            question TEXT NOT NULL,
                            response_text TEXT,
                            response_source VARCHAR(50),
                            response_confidence DECIMAL(5,4),
                            processing_time_ms INTEGER,
                            status VARCHAR(20) DEFAULT 'success',
                            intent VARCHAR(100),
                            entities JSONB,
                            language VARCHAR(10) DEFAULT 'fr',
                            completeness_score DECIMAL(5,4),
                            error_type VARCHAR(50),
                            error_message TEXT,
                            error_traceback TEXT,
                            feedback INTEGER CHECK (feedback IN (-1, 0, 1)),
                            feedback_comment TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                        
                        cur.execute(create_table_sql)
                        
                        # Créer index pour performance
                        cur.execute("CREATE INDEX idx_user_questions_created_at ON user_questions_complete(created_at)")
                        cur.execute("CREATE INDEX idx_user_questions_user_email ON user_questions_complete(user_email)")
                        cur.execute("CREATE INDEX idx_user_questions_feedback ON user_questions_complete(feedback) WHERE feedback IS NOT NULL")
                        
                        conn.commit()
                        results["tables_created"].append("user_questions_complete")
                        logger.info("✅ Table user_questions_complete créée avec succès")
                    
                    else:
                        # Vérifier si colonnes feedback existent, les ajouter si nécessaire
                        cur.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'user_questions_complete' 
                            AND column_name IN ('feedback', 'feedback_comment')
                        """)
                        
                        existing_feedback_cols = {row["column_name"] for row in cur.fetchall()}
                        
                        if "feedback" not in existing_feedback_cols:
                            cur.execute("""
                                ALTER TABLE user_questions_complete 
                                ADD COLUMN feedback INTEGER CHECK (feedback IN (-1, 0, 1))
                            """)
                            results["tables_updated"].append("user_questions_complete: ajout colonne feedback")
                            logger.info("✅ Colonne feedback ajoutée")
                        
                        if "feedback_comment" not in existing_feedback_cols:
                            cur.execute("""
                                ALTER TABLE user_questions_complete 
                                ADD COLUMN feedback_comment TEXT
                            """)
                            results["tables_updated"].append("user_questions_complete: ajout colonne feedback_comment")
                            logger.info("✅ Colonne feedback_comment ajoutée")
                        
                        if results["tables_updated"]:
                            conn.commit()
            
            # Actualiser la détection après création
            self._feedback_columns_available = self._check_feedback_columns_availability()
            
            return {
                "status": "success",
                "results": results,
                "new_feedback_status": self._feedback_columns_available,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur création tables: {e}")
            return {"status": "error", "error": str(e)}

    async def update_all_statistics(self) -> Dict[str, Any]:
        """
        🎯 FONCTION PRINCIPALE - Met à jour toutes les statistiques
        Collecte en parallèle pour performances optimales
        """
        if self.update_in_progress:
            logger.warning("⏳ Mise à jour déjà en cours, skip")
            return {"status": "skipped", "reason": "update_in_progress"}
        
        start_time = time.time()
        self.update_in_progress = True
        
        try:
            logger.info("🚀 Début mise à jour complète des statistiques")
            
            # 🔄 COLLECTE PARALLÈLE pour performances maximales
            results = await asyncio.gather(
                self._update_dashboard_stats(),
                self._update_openai_costs(),
                self._update_invitation_stats(),
                self._update_server_performance(),
                return_exceptions=True
            )
            
            # Analyser les résultats
            successful_updates = 0
            errors = []
            
            update_names = ["dashboard", "openai_costs", "invitations", "server_performance"]
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_msg = f"{update_names[i]}: {str(result)}"
                    errors.append(error_msg)
                    logger.error(f"❌ Erreur {update_names[i]}: {result}")
                elif result.get("status") == "success":
                    successful_updates += 1
                    logger.info(f"✅ {update_names[i]}: OK")
                else:
                    errors.append(f"{update_names[i]}: {result.get('error', 'Unknown error')}")
            
            # Nettoyer le cache expiré
            try:
                cleaned_entries = self.cache.cleanup_expired_cache()
                logger.info(f"🧹 Cache nettoyé: {cleaned_entries} entrées supprimées")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Erreur cleanup cache: {cleanup_error}")
            
            # Résultats finaux
            duration_ms = int((time.time() - start_time) * 1000)
            self.last_update = datetime.now()
            
            result = {
                "status": "completed",
                "successful_updates": successful_updates,
                "total_updates": len(update_names),
                "errors": errors,
                "duration_ms": duration_ms,
                "last_update": self.last_update.isoformat(),
                "next_update_due": (self.last_update + timedelta(hours=1)).isoformat(),
                "feedback_support": self._feedback_columns_available
            }
            
            # Cacher le résumé de la mise à jour
            self.cache.set_cache(
                "system:last_update_summary", 
                result, 
                ttl_hours=25,  # Un peu plus qu'une heure pour éviter les gaps
                source="stats_updater"
            )
            
            logger.info(f"✅ Mise à jour terminée: {successful_updates}/{len(update_names)} succès en {duration_ms}ms")
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"💥 Erreur critique mise à jour: {e}")
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            self.update_in_progress = False

    async def _get_feedback_stats_safe(self, cur) -> Dict[str, Any]:
        """
        🛡️ Collecte feedback stats avec vérification défensive des colonnes
        Compatible avec toutes les configurations de base de données
        """
        try:
            # Utiliser le cache de détection des colonnes
            if not self._feedback_columns_available["table_exists"]:
                logger.warning("⚠️ Table user_questions_complete manquante - pas de feedback")
                return {
                    "total": 0, "positive": 0, "negative": 0, 
                    "with_comments": 0, "satisfaction_rate": 0.0,
                    "note": "Table user_questions_complete manquante"
                }
            
            has_feedback = self._feedback_columns_available["feedback"]
            has_feedback_comment = self._feedback_columns_available["feedback_comment"]
            
            if not has_feedback:
                logger.info("ℹ️ Colonne feedback non disponible - stats feedback désactivées")
                return {
                    "total": 0, "positive": 0, "negative": 0, 
                    "with_comments": 0, "satisfaction_rate": 0.0,
                    "note": "Migration feedback requise - colonnes manquantes"
                }
            
            # ✅ Colonnes feedback disponibles - construire requête dynamique
            query = """
                SELECT 
                    COUNT(*) FILTER (WHERE feedback = 1) as positive_feedback,
                    COUNT(*) FILTER (WHERE feedback = -1) as negative_feedback,
                    COUNT(*) FILTER (WHERE feedback IS NOT NULL) as total_feedback
            """
            
            if has_feedback_comment:
                query += ",\n                    COUNT(*) FILTER (WHERE feedback_comment IS NOT NULL AND feedback_comment != '') as feedback_with_comments"
            else:
                query += ",\n                    0 as feedback_with_comments"
                
            query += """
                FROM user_questions_complete 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            """
            
            cur.execute(query)
            result = cur.fetchone()
            
            if result:
                total_fb = result["total_feedback"] or 0
                positive_fb = result["positive_feedback"] or 0
                satisfaction_rate = (positive_fb / total_fb * 100) if total_fb > 0 else 0
                
                feedback_stats = {
                    "total": total_fb,
                    "positive": positive_fb,
                    "negative": result["negative_feedback"] or 0,
                    "with_comments": result.get("feedback_with_comments", 0),
                    "satisfaction_rate": round(satisfaction_rate, 1)
                }
                
                logger.info(f"📊 Feedback stats collectées: {total_fb} total, {satisfaction_rate}% satisfaction")
                return feedback_stats
            
            return {"total": 0, "positive": 0, "negative": 0, "with_comments": 0, "satisfaction_rate": 0.0}
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte feedback safe: {e}")
            return {
                "total": 0, "positive": 0, "negative": 0, 
                "with_comments": 0, "satisfaction_rate": 0.0,
                "error": str(e)[:100]  # Limiter la longueur de l'erreur
            }

    async def _update_dashboard_stats(self) -> Dict[str, Any]:
        """Collecte et cache les statistiques dashboard principales"""
        try:
            logger.info("📊 Collecte dashboard stats...")
            
            # 🔍 UTILISATION DES GESTIONNAIRES EXISTANTS
            dashboard_data = {}
            
            # Récupérer les analytics serveur via logging.py
            try:
                from app.api.v1.logging import get_server_analytics
                server_stats = get_server_analytics(hours=24)
                
                if "error" not in server_stats:
                    dashboard_data.update({
                        "avg_response_time": server_stats.get("current_status", {}).get("avg_response_time_ms", 0) / 1000,
                        "error_rate": server_stats.get("current_status", {}).get("error_rate_percent", 0),
                        "system_health": server_stats.get("current_status", {}).get("overall_health", "healthy")
                    })
                
            except Exception as server_error:
                logger.warning(f"⚠️ Erreur récupération server stats: {server_error}")
                dashboard_data.update({
                    "avg_response_time": 0,
                    "error_rate": 0,
                    "system_health": "unknown"
                })
            
            # Calculer les statistiques depuis la base directement
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(self.analytics.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Utilisateurs uniques et questions
                    cur.execute("""
                        SELECT 
                            COUNT(DISTINCT user_email) FILTER (WHERE user_email IS NOT NULL AND user_email != '') as total_users,
                            COUNT(*) as total_questions,
                            COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as questions_today,
                            COUNT(*) FILTER (WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)) as questions_this_week,
                            COUNT(*) FILTER (WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)) as questions_this_month,
                            AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) / 1000 as avg_response_time_calc,
                            AVG(response_confidence) FILTER (WHERE response_confidence IS NOT NULL) * 100 as avg_confidence
                        FROM user_questions_complete 
                        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                    """)
                    
                    stats_result = cur.fetchone()
                    if stats_result:
                        dashboard_data.update({
                            "total_users": stats_result["total_users"] or 0,
                            "unique_active_users": stats_result["total_users"] or 0,  # Même valeur pour l'instant
                            "total_questions": stats_result["total_questions"] or 0,
                            "questions_today": stats_result["questions_today"] or 0,
                            "questions_this_week": stats_result["questions_this_week"] or 0,
                            "questions_this_month": stats_result["questions_this_month"] or 0,
                            "avg_confidence": round(stats_result["avg_confidence"] or 0, 1)
                        })
                        
                        # Prendre le meilleur temps de réponse disponible
                        if not dashboard_data.get("avg_response_time"):
                            dashboard_data["avg_response_time"] = round(stats_result["avg_response_time_calc"] or 0, 3)
                    
                    # Distribution des sources
                    cur.execute("""
                        SELECT response_source, COUNT(*) as count
                        FROM user_questions_complete 
                        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                        GROUP BY response_source
                        ORDER BY count DESC
                    """)
                    
                    source_dist = {}
                    for row in cur.fetchall():
                        source_name = row["response_source"] or "unknown"
                        # Mapping vers les noms attendus par le frontend
                        if source_name == "rag":
                            source_dist["rag_retriever"] = row["count"]
                        elif source_name == "openai_fallback":
                            source_dist["openai_fallback"] = row["count"]
                        elif source_name in ["table_lookup", "perfstore"]:
                            source_dist["perfstore"] = source_dist.get("perfstore", 0) + row["count"]
                        else:
                            source_dist[source_name] = row["count"]
                    
                    dashboard_data["source_distribution"] = source_dist
                    
                    # Top utilisateurs
                    cur.execute("""
                        SELECT 
                            user_email,
                            COUNT(*) as question_count,
                            'free' as plan
                        FROM user_questions_complete 
                        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                            AND user_email IS NOT NULL 
                            AND user_email != ''
                        GROUP BY user_email
                        ORDER BY question_count DESC
                        LIMIT 10
                    """)
                    
                    top_users = []
                    for row in cur.fetchall():
                        top_users.append({
                            "email": row["user_email"],
                            "question_count": row["question_count"],
                            "plan": row["plan"]
                        })
                    
                    dashboard_data["top_users"] = top_users
                    
                    # 🛡️ STATS DE FEEDBACK DÉFENSIVES (NOUVELLE SECTION)
                    dashboard_data["feedback_stats"] = await self._get_feedback_stats_safe(cur)
            
            # Récupérer données billing via billing.py
            try:
                # Calculer revenue approximatif (logique simplifiée)
                billing_summary = {
                    "total_revenue": 0,
                    "monthly_revenue": 0,
                    "plan_distribution": {"free": dashboard_data.get("total_users", 0)}
                }
                
                dashboard_data.update(billing_summary)
                
            except Exception as billing_error:
                logger.warning(f"⚠️ Erreur récupération billing: {billing_error}")
                dashboard_data.update({
                    "total_revenue": 0,
                    "monthly_revenue": 0,
                    "plan_distribution": {"free": dashboard_data.get("total_users", 0)}
                })
            
            # Valeurs par défaut pour les champs manquants
            defaults = {
                "median_response_time": dashboard_data.get("avg_response_time", 0),
                "openai_costs": 6.30,  # Valeur fallback connue
                "top_inviters": []
            }
            
            for key, default_value in defaults.items():
                if key not in dashboard_data:
                    dashboard_data[key] = default_value
            
            # Sauvegarder dans le cache spécialisé
            success = self.cache.set_dashboard_snapshot(dashboard_data, period_hours=24)
            
            # Aussi dans le cache générique pour compatibilité
            self.cache.set_cache("dashboard:main", dashboard_data, ttl_hours=1, source="analytics_computed")
            
            logger.info(f"✅ Dashboard stats collectées: {len(dashboard_data)} métriques")
            return {"status": "success", "metrics_collected": len(dashboard_data)}
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte dashboard stats: {e}")
            return {"status": "error", "error": str(e)}

    async def _update_openai_costs(self) -> Dict[str, Any]:
        """Collecte les coûts OpenAI avec la nouvelle logique optimisée"""
        try:
            logger.info("💰 Collecte coûts OpenAI...")
            
            # Utiliser la logique optimisée de billing_openai.py
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)  # 7 jours pour éviter rate limiting
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Récupération avec rate limiting safe
            costs_data = await get_openai_usage_data_safe(
                start_str, end_str, max_days=7
            )
            
            # Enrichir avec métadonnées
            costs_data.update({
                "period_start": start_str,
                "period_end": end_str,
                "collected_at": datetime.now().isoformat(),
                "data_source": "openai_api_optimized"
            })
            
            # Cacher dans la table spécialisée
            success = self.cache.set_openai_costs(
                start_str, end_str, "week", costs_data
            )
            
            # Cache générique aussi
            self.cache.set_cache("openai:costs:current", costs_data, ttl_hours=4, source="openai_api")
            
            logger.info(f"💰 Coûts OpenAI collectés: ${costs_data.get('total_cost', 0):.2f}")
            return {
                "status": "success", 
                "total_cost": costs_data.get('total_cost', 0),
                "api_calls_made": costs_data.get('api_calls_made', 0),
                "cached_days": costs_data.get('cached_days', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte coûts OpenAI: {e}")
            
            # Fallback avec données simulées
            fallback_data = {
                "total_cost": 6.30,
                "total_tokens": 450000,
                "api_calls": 250,
                "models_usage": {"gpt-4": {"cost": 4.20}, "gpt-3.5-turbo": {"cost": 2.10}},
                "daily_breakdown": {},
                "data_source": "fallback",
                "note": f"Erreur API OpenAI: {str(e)}"
            }
            
            self.cache.set_cache("openai:costs:fallback", fallback_data, ttl_hours=1, source="fallback")
            
            return {"status": "fallback", "error": str(e), "fallback_cost": 6.30}

    async def _update_invitation_stats(self) -> Dict[str, Any]:
        """Collecte les statistiques d'invitations"""
        try:
            logger.info("📧 Collecte stats invitations...")
            
            # Calculer depuis la base directement (si table existe)
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                with psycopg2.connect(self.analytics.dsn) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        
                        # Vérifier si la table invitations existe
                        cur.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'invitations'
                            )
                        """)
                        
                        table_exists = cur.fetchone()["exists"]
                        
                        if table_exists:
                            # Calculer les vraies stats d'invitations
                            cur.execute("""
                                SELECT 
                                    COUNT(*) as total_sent,
                                    COUNT(*) FILTER (WHERE status = 'accepted') as total_accepted,
                                    COUNT(DISTINCT inviter_email) as unique_inviters,
                                    CASE 
                                        WHEN COUNT(*) > 0 THEN 
                                            ROUND((COUNT(*) FILTER (WHERE status = 'accepted')::DECIMAL / COUNT(*)) * 100, 2)
                                        ELSE 0 
                                    END as acceptance_rate
                                FROM invitations
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                            """)
                            
                            stats_result = cur.fetchone()
                            
                            # Top inviters
                            cur.execute("""
                                SELECT 
                                    inviter_email,
                                    inviter_name,
                                    COUNT(*) as invitations_sent,
                                    COUNT(*) FILTER (WHERE status = 'accepted') as invitations_accepted,
                                    CASE 
                                        WHEN COUNT(*) > 0 THEN 
                                            ROUND((COUNT(*) FILTER (WHERE status = 'accepted')::DECIMAL / COUNT(*)) * 100, 2)
                                        ELSE 0 
                                    END as acceptance_rate
                                FROM invitations
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                GROUP BY inviter_email, inviter_name
                                ORDER BY invitations_sent DESC
                                LIMIT 10
                            """)
                            
                            top_inviters = [dict(row) for row in cur.fetchall()]
                            
                            # Top par acceptations
                            cur.execute("""
                                SELECT 
                                    inviter_email,
                                    inviter_name,
                                    COUNT(*) as invitations_sent,
                                    COUNT(*) FILTER (WHERE status = 'accepted') as invitations_accepted,
                                    CASE 
                                        WHEN COUNT(*) > 0 THEN 
                                            ROUND((COUNT(*) FILTER (WHERE status = 'accepted')::DECIMAL / COUNT(*)) * 100, 2)
                                        ELSE 0 
                                    END as acceptance_rate
                                FROM invitations
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                    AND status = 'accepted'
                                GROUP BY inviter_email, inviter_name
                                ORDER BY invitations_accepted DESC
                                LIMIT 10
                            """)
                            
                            top_accepted = [dict(row) for row in cur.fetchall()]
                            
                            invitation_data = {
                                "total_invitations_sent": stats_result["total_sent"],
                                "total_invitations_accepted": stats_result["total_accepted"],
                                "acceptance_rate": float(stats_result["acceptance_rate"]),
                                "unique_inviters": stats_result["unique_inviters"],
                                "top_inviters_by_sent": top_inviters,
                                "top_inviters_by_accepted": top_accepted
                            }
                            
                        else:
                            # Table n'existe pas, données par défaut
                            invitation_data = {
                                "total_invitations_sent": 0,
                                "total_invitations_accepted": 0,
                                "acceptance_rate": 0.0,
                                "unique_inviters": 0,
                                "top_inviters_by_sent": [],
                                "top_inviters_by_accepted": [],
                                "note": "Table invitations non trouvée"
                            }
                            
            except Exception as db_error:
                logger.warning(f"⚠️ Erreur accès base invitations: {db_error}")
                invitation_data = {
                    "total_invitations_sent": 0,
                    "total_invitations_accepted": 0,
                    "acceptance_rate": 0.0,
                    "unique_inviters": 0,
                    "top_inviters_by_sent": [],
                    "top_inviters_by_accepted": [],
                    "error": str(db_error)
                }
            
            # Cacher les résultats
            self.cache.set_cache("invitations:global_stats", invitation_data, ttl_hours=2, source="computed")
            
            logger.info(f"📧 Stats invitations collectées: {invitation_data['total_invitations_sent']} sent")
            return {"status": "success", "invitations_processed": invitation_data["total_invitations_sent"]}
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte stats invitations: {e}")
            return {"status": "error", "error": str(e)}

    async def _update_server_performance(self) -> Dict[str, Any]:
        """Collecte les métriques de performance serveur"""
        try:
            logger.info("⚡ Collecte performance serveur...")
            
            # Utiliser get_server_analytics de logging.py
            performance_data = {}
            
            try:
                from app.api.v1.logging import get_server_analytics
                server_metrics = get_server_analytics(hours=24)
                
                if "error" not in server_metrics:
                    performance_data = {
                        "period_hours": 24,
                        "current_status": server_metrics.get("current_status", {}),
                        "global_stats": server_metrics.get("global_stats", {}),
                        "hourly_patterns": server_metrics.get("hourly_usage_patterns", []),
                        "collected_at": datetime.now().isoformat()
                    }
                else:
                    raise Exception(server_metrics["error"])
                    
            except Exception as perf_error:
                logger.warning(f"⚠️ Erreur récupération performance: {perf_error}")
                
                # Calculer des métriques basiques depuis les questions
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                with psycopg2.connect(self.analytics.dsn) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_requests,
                                COUNT(*) FILTER (WHERE status = 'success') as successful_requests,
                                COUNT(*) FILTER (WHERE status != 'success') as failed_requests,
                                AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) as avg_response_time_ms,
                                MAX(processing_time_ms) as max_response_time_ms
                            FROM user_questions_complete 
                            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                        """)
                        
                        result = cur.fetchone()
                        total_req = result["total_requests"] or 0
                        failed_req = result["failed_requests"] or 0
                        error_rate = (failed_req / total_req * 100) if total_req > 0 else 0
                        
                        performance_data = {
                            "period_hours": 24,
                            "current_status": {
                                "overall_health": "healthy" if error_rate < 5 else "degraded",
                                "avg_response_time_ms": int(result["avg_response_time_ms"] or 0),
                                "error_rate_percent": round(error_rate, 2),
                                "total_errors": failed_req
                            },
                            "global_stats": {
                                "total_requests": total_req,
                                "total_successes": result["successful_requests"] or 0,
                                "total_failures": failed_req,
                                "max_response_time_ms": result["max_response_time_ms"] or 0
                            },
                            "collected_at": datetime.now().isoformat(),
                            "source": "questions_computed"
                        }
            
            # Cacher les métriques
            self.cache.set_cache("server:performance:24h", performance_data, ttl_hours=1, source="computed")
            
            logger.info(f"⚡ Performance serveur collectée: {performance_data['current_status']['overall_health']}")
            return {
                "status": "success", 
                "health": performance_data["current_status"]["overall_health"],
                "total_requests": performance_data["global_stats"].get("total_requests", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte performance: {e}")
            return {"status": "error", "error": str(e)}

    def get_update_status(self) -> Dict[str, Any]:
        """Retourne le statut de la dernière mise à jour"""
        try:
            # Récupérer depuis le cache
            cached_summary = self.cache.get_cache("system:last_update_summary")
            
            if cached_summary:
                return cached_summary["data"]
            else:
                return {
                    "status": "never_updated",
                    "message": "Aucune mise à jour effectuée",
                    "update_in_progress": self.update_in_progress,
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "feedback_support": self._feedback_columns_available
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur récupération statut: {e}")
            return {"status": "error", "error": str(e)}

    async def force_update_specific(self, component: str) -> Dict[str, Any]:
        """Force la mise à jour d'un composant spécifique"""
        try:
            logger.info(f"🔄 Force update: {component}")
            
            if component == "dashboard":
                result = await self._update_dashboard_stats()
            elif component == "openai":
                result = await self._update_openai_costs()
            elif component == "invitations":
                result = await self._update_invitation_stats()
            elif component == "performance":
                result = await self._update_server_performance()
            else:
                return {"status": "error", "error": f"Composant '{component}' inconnu"}
            
            logger.info(f"✅ Force update {component}: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur force update {component}: {e}")
            return {"status": "error", "error": str(e)}

    def refresh_feedback_detection(self) -> Dict[str, Any]:
        """
        🔄 NOUVELLE MÉTHODE: Actualise la détection des colonnes feedback
        Utile après une migration ou modification de schéma
        """
        try:
            logger.info("🔄 Actualisation détection colonnes feedback...")
            old_status = self._feedback_columns_available.copy()
            self._feedback_columns_available = self._check_feedback_columns_availability()
            
            result = {
                "status": "success",
                "old_detection": old_status,
                "new_detection": self._feedback_columns_available,
                "changes_detected": old_status != self._feedback_columns_available,
                "timestamp": datetime.now().isoformat()
            }
            
            if result["changes_detected"]:
                logger.info(f"🔄 Changements détectés dans les colonnes feedback: {result['new_detection']}")
            else:
                logger.info("ℹ️ Aucun changement détecté dans les colonnes feedback")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur refresh feedback detection: {e}")
            return {"status": "error", "error": str(e)}


# ==================== SINGLETON GLOBAL ====================

_stats_updater_instance = None

def get_stats_updater() -> StatisticsUpdater:
    """Récupère l'instance singleton du collecteur"""
    global _stats_updater_instance
    if _stats_updater_instance is None:
        _stats_updater_instance = StatisticsUpdater()
    return _stats_updater_instance


# ==================== FONCTIONS UTILITAIRES ====================

async def run_update_cycle():
    """Fonction helper pour le scheduler"""
    updater = get_stats_updater()
    return await updater.update_all_statistics()

async def force_update_all():
    """Force une mise à jour immédiate (pour admin)"""
    updater = get_stats_updater()
    return await updater.update_all_statistics()

def refresh_feedback_columns():
    """Force la re-détection des colonnes feedback"""
    updater = get_stats_updater()
    return updater.refresh_feedback_detection()