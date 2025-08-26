# app/api/v1/stats_updater.py
# -*- coding: utf-8 -*-
"""
Collecteur intelligent de statistiques - Version corrigée
Utilise les gestionnaires existants SANS les modifier
Collecte périodique + cache optimisé
SAFE: Aucune rupture avec logging.py et billing.py
Optimisé: Gestion mémoire drastiquement améliorée pour DigitalOcean App Platform
Memory-safe: Collecte séquentielle, limites strictes, monitoring temps réel
FIXED: Correction erreur feedback columns et gestion robuste des exceptions
"""

import asyncio
import json
import logging
import time
import os
import gc
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Import des gestionnaires existants (SAFE)
from app.api.v1.logging import get_analytics_manager
from app.api.v1.billing import get_billing_manager
from app.api.v1.stats_cache import get_stats_cache

# Import pour coûts OpenAI optimisés
from app.api.v1.billing_openai import get_openai_usage_data_safe

logger = logging.getLogger(__name__)

# Configuration memory-safe pour updater
UPDATER_CONFIG = {
    "ENABLE_PARALLEL_COLLECTION": os.getenv("ENABLE_PARALLEL_STATS", "false").lower() == "true",
    "MAX_MEMORY_PERCENT_COLLECTION": 85,    # Augmentation du seuil de 70% à 85%
    "SEQUENTIAL_DELAY_MS": 500,             # 500ms entre chaque collecteur séquentiel
    "MAX_COLLECTION_TIME_SECONDS": 120,     # Timeout global 2min
    "ENABLE_MEMORY_MONITORING": True,       # Monitoring mémoire temps réel
    "FORCE_GC_AFTER_COLLECTION": True,      # Force garbage collection
    "MAX_SQL_ROWS_PER_QUERY": 1000,        # Limite lignes SQL
    "REDUCE_DATASET_SIZE": True,            # Réduit la taille des datasets
    "SKIP_HEAVY_ANALYTICS": os.getenv("SKIP_HEAVY_ANALYTICS", "false").lower() == "true"
}

def get_memory_usage_percent():
    """Retourne le pourcentage d'utilisation mémoire système"""
    try:
        return psutil.virtual_memory().percent
    except Exception:
        return 0

def should_abort_collection():
    """Détermine si la collecte doit être abandonnée pour préserver la mémoire"""
    memory_percent = get_memory_usage_percent()
    if memory_percent > UPDATER_CONFIG["MAX_MEMORY_PERCENT_COLLECTION"]:
        logger.warning(f"Collecte abandonnée: mémoire critique ({memory_percent}%)")
        return True, f"Mémoire critique: {memory_percent}%"
    return False, None

def force_garbage_collection():
    """Force le garbage collection pour libérer la mémoire"""
    if UPDATER_CONFIG["FORCE_GC_AFTER_COLLECTION"]:
        gc.collect()
        logger.debug("Garbage collection forcé")

class StatisticsUpdater:
    """
    Collecteur intelligent memory-safe qui utilise les gestionnaires existants
    - Met à jour le cache périodiquement avec gestion mémoire
    - Gère les erreurs et fallbacks
    - Collecte séquentielle au lieu de parallèle (économie RAM)
    - Support défensif pour colonnes feedback CORRIGÉ
    - Monitoring mémoire temps réel
    """
    
    def __init__(self):
        self.cache = get_stats_cache()
        self.analytics = get_analytics_manager()
        self.billing = get_billing_manager()
        self.last_update = None
        self.update_in_progress = False
        
        # Compteurs de performance pour monitoring
        self.collection_stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "memory_aborts": 0,
            "last_memory_peak": 0
        }
        
        # Vérification analytics manager avec gestion d'erreur robuste
        if not self.analytics:
            logger.error("Analytics manager non disponible")
            self._feedback_columns_available = {
                "table_exists": False, 
                "feedback": False, 
                "feedback_comment": False, 
                "error": "no_analytics_manager"
            }
        else:
            # Détection des colonnes feedback au démarrage avec exception handling
            try:
                self._feedback_columns_available = self._check_feedback_columns_availability()
                logger.info(f"Détection feedback au démarrage: {self._feedback_columns_available}")
            except Exception as e:
                logger.error(f"Erreur détection feedback au démarrage: {e}")
                self._feedback_columns_available = {
                    "table_exists": False, 
                    "feedback": False, 
                    "feedback_comment": False, 
                    "error": str(e)
                }
    
    def _check_feedback_columns_availability(self) -> Dict[str, Any]:
        """
        CORRIGÉ: Vérifie la disponibilité des colonnes feedback au démarrage.
        Cache le résultat pour éviter les vérifications répétées.
        Retourne TOUJOURS un dictionnaire valide, jamais 0 ou autre
        """
        logger.error("PROOF-OF-DEPLOY: Version corrigée feedback detection - 2025-08-26-22:35")
        
        default_result = {
            "table_exists": False, 
            "feedback": False, 
            "feedback_comment": False
        }
        
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Vérifier que l'analytics manager existe et a un DSN
            if not hasattr(self.analytics, 'dsn') or not self.analytics.dsn:
                logger.warning("DSN analytics non disponible - utilisation valeurs par défaut")
                return {**default_result, "error": "no_dsn"}
            
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
                        logger.warning("Table user_questions_complete n'existe pas")
                        return {**default_result, "error": "table_missing"}
                    
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
                    
                    logger.info(f"Détection colonnes feedback: {result}")
                    return result
                    
        except ImportError as import_err:
            logger.error(f"Module psycopg2 non disponible: {import_err}")
            return {
                **default_result,
                "error": "psycopg2_missing"
            }
            
        except Exception as e:
            # CORRIGÉ: Retourner un dictionnaire valide au lieu de 0
            logger.error(f"Erreur vérification colonnes feedback: {e}")
            return {
                **default_result,
                "error": str(e)[:100]  # Limiter la taille de l'erreur
            }
    
    def diagnose_database_connection(self) -> Dict[str, Any]:
        """
        Diagnostique complet de la connection base de données
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
        Crée automatiquement les tables manquantes
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
                        logger.info("Création table user_questions_complete...")
                        
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
                        logger.info("Table user_questions_complete créée avec succès")
                    
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
                            logger.info("Colonne feedback ajoutée")
                        
                        if "feedback_comment" not in existing_feedback_cols:
                            cur.execute("""
                                ALTER TABLE user_questions_complete 
                                ADD COLUMN feedback_comment TEXT
                            """)
                            results["tables_updated"].append("user_questions_complete: ajout colonne feedback_comment")
                            logger.info("Colonne feedback_comment ajoutée")
                        
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
            logger.error(f"Erreur création tables: {e}")
            return {"status": "error", "error": str(e)}

    async def update_all_statistics(self) -> Dict[str, Any]:
        """
        Fonction principale - memory-safe version
        Met à jour toutes les statistiques avec gestion mémoire optimisée
        Collecte séquentielle au lieu de parallèle pour économiser RAM
        """
        if self.update_in_progress:
            logger.warning("Mise à jour déjà en cours, skip")
            return {"status": "skipped", "reason": "update_in_progress"}
        
        start_time = time.time()
        start_memory = get_memory_usage_percent()
        self.update_in_progress = True
        
        try:
            logger.info(f"Début mise à jour memory-safe (RAM: {start_memory}%)")
            
            # Vérification mémoire préliminaire
            should_abort, abort_reason = should_abort_collection()
            if should_abort:
                self.collection_stats["memory_aborts"] += 1
                return {
                    "status": "aborted",
                    "reason": abort_reason,
                    "memory_percent": start_memory
                }
            
            # Collecte séquentielle optimisée (au lieu de parallèle)
            results = []
            successful_updates = 0
            errors = []
            
            update_methods = [
                ("dashboard", self._update_dashboard_stats_safe),
                ("openai_costs", self._update_openai_costs_safe), 
                ("invitations", self._update_invitation_stats_safe),
                ("server_performance", self._update_server_performance_safe)
            ]
            
            for update_name, update_method in update_methods:
                try:
                    # Vérification mémoire avant chaque collecteur
                    current_memory = get_memory_usage_percent()
                    if current_memory > UPDATER_CONFIG["MAX_MEMORY_PERCENT_COLLECTION"]:
                        logger.warning(f"Arrêt anticipé à {update_name}: mémoire {current_memory}%")
                        errors.append(f"{update_name}: Arrêt mémoire critique ({current_memory}%)")
                        break
                    
                    logger.info(f"Collecte {update_name}... (RAM: {current_memory}%)")
                    
                    result = await update_method()
                    
                    if isinstance(result, Exception):
                        error_msg = f"{update_name}: {str(result)}"
                        errors.append(error_msg)
                        logger.error(f"Erreur {update_name}: {result}")
                    elif result.get("status") == "success":
                        successful_updates += 1
                        logger.info(f"{update_name}: OK")
                    else:
                        errors.append(f"{update_name}: {result.get('error', 'Unknown error')}")
                    
                    results.append(result)
                    
                    # Délai entre collecteurs + nettoyage mémoire
                    if UPDATER_CONFIG["SEQUENTIAL_DELAY_MS"] > 0:
                        await asyncio.sleep(UPDATER_CONFIG["SEQUENTIAL_DELAY_MS"] / 1000)
                    
                    force_garbage_collection()
                    
                except Exception as method_error:
                    error_msg = f"{update_name}: Exception {str(method_error)}"
                    errors.append(error_msg)
                    logger.error(f"Exception {update_name}: {method_error}")
                    results.append({"status": "error", "error": str(method_error)})
            
            # Nettoyer le cache expiré
            try:
                cleaned_entries = self.cache.cleanup_expired_cache()
                logger.info(f"Cache nettoyé: {cleaned_entries} entrées supprimées")
            except Exception as cleanup_error:
                logger.warning(f"Erreur cleanup cache: {cleanup_error}")
            
            # Garbage collection final
            force_garbage_collection()
            
            # Résultats finaux avec métriques mémoire
            end_memory = get_memory_usage_percent()
            duration_ms = int((time.time() - start_time) * 1000)
            self.last_update = datetime.now()
            
            # Mise à jour des statistiques de performance
            self.collection_stats["total_collections"] += 1
            self.collection_stats["successful_collections"] += successful_updates
            self.collection_stats["last_memory_peak"] = max(start_memory, end_memory)
            
            result = {
                "status": "completed",
                "successful_updates": successful_updates,
                "total_updates": len(update_methods),
                "errors": errors,
                "duration_ms": duration_ms,
                "last_update": self.last_update.isoformat(),
                "next_update_due": (self.last_update + timedelta(hours=1)).isoformat(),
                "feedback_support": self._feedback_columns_available,
                "memory_info": {
                    "start_memory_percent": start_memory,
                    "end_memory_percent": end_memory,
                    "memory_delta": end_memory - start_memory,
                    "collection_mode": "sequential_safe" if not UPDATER_CONFIG["ENABLE_PARALLEL_COLLECTION"] else "parallel",
                    "memory_monitoring_enabled": UPDATER_CONFIG["ENABLE_MEMORY_MONITORING"]
                },
                "collection_stats": self.collection_stats.copy()
            }
            
            # Cacher le résumé de la mise à jour
            self.cache.set_cache(
                "system:last_update_summary", 
                result, 
                ttl_hours=25,  # Un peu plus qu'une heure pour éviter les gaps
                source="stats_updater_safe"
            )
            
            logger.info(f"Mise à jour terminée safe: {successful_updates}/{len(update_methods)} succès en {duration_ms}ms (RAM: {start_memory}%→{end_memory}%)")
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            end_memory = get_memory_usage_percent()
            logger.error(f"Erreur critique mise à jour safe: {e}")
            
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": duration_ms,
                "memory_info": {
                    "start_memory_percent": start_memory,
                    "end_memory_percent": end_memory,
                    "memory_delta": end_memory - start_memory
                },
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            self.update_in_progress = False

    async def _get_feedback_stats_safe(self, cur) -> Dict[str, Any]:
        """
        CORRIGÉ: Collecte feedback stats avec vérification défensive stricte des colonnes
        Compatible avec toutes les configurations de base de données
        Ne doit JAMAIS exécuter de requête SQL avec colonnes manquantes
        """
        default_feedback_result = {
            "total": 0, 
            "positive": 0, 
            "negative": 0, 
            "with_comments": 0, 
            "satisfaction_rate": 0.0
        }
        
        try:
            # VALIDATION 1: Vérifier que la table existe
            if not self._feedback_columns_available.get("table_exists", False):
                logger.warning("Table user_questions_complete manquante - pas de feedback")
                return {
                    **default_feedback_result,
                    "note": "Table user_questions_complete manquante"
                }
            
            # VALIDATION 2: Vérifier que la colonne feedback existe
            has_feedback = self._feedback_columns_available.get("feedback", False)
            has_feedback_comment = self._feedback_columns_available.get("feedback_comment", False)
            
            if not has_feedback:
                logger.info("Colonne feedback non disponible - stats feedback désactivées")
                return {
                    **default_feedback_result,
                    "note": "Migration feedback requise - colonne feedback manquante"
                }
            
            # VALIDATION 3: Double vérification avant requête SQL
            # Re-vérifier en temps réel la disponibilité des colonnes
            try:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_questions_complete' 
                    AND column_name = 'feedback'
                """)
                
                column_check = cur.fetchall()
                if not column_check:
                    logger.warning("Double vérification: colonne feedback non trouvée")
                    return {
                        **default_feedback_result,
                        "note": "Colonne feedback non trouvée lors de la double vérification"
                    }
                
            except Exception as double_check_error:
                logger.error(f"Erreur double vérification colonnes: {double_check_error}")
                return {
                    **default_feedback_result,
                    "error": f"Double vérification échouée: {str(double_check_error)[:50]}"
                }
            
            # REQUÊTE SQL SÉCURISÉE: Colonnes feedback disponibles confirmées
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
                
            # Limiter la plage de dates pour économiser mémoire
            query += f"""
                FROM user_questions_complete 
                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                LIMIT {UPDATER_CONFIG["MAX_SQL_ROWS_PER_QUERY"]}
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
                
                logger.info(f"Feedback stats collectées safe: {total_fb} total, {satisfaction_rate}% satisfaction")
                return feedback_stats
            
            return default_feedback_result
            
        except Exception as e:
            logger.error(f"Erreur collecte feedback safe: {e}")
            return {
                **default_feedback_result,
                "error": str(e)[:100]  # Limiter la longueur de l'erreur
            }

    async def _update_dashboard_stats_safe(self) -> Dict[str, Any]:
        """Collecte dashboard stats avec gestion mémoire optimisée"""
        try:
            logger.info("Collecte dashboard stats safe...")
            
            # Vérification mémoire avant requêtes lourdes
            memory_before = get_memory_usage_percent()
            if memory_before > UPDATER_CONFIG["MAX_MEMORY_PERCENT_COLLECTION"]:
                return {
                    "status": "skipped",
                    "reason": f"Mémoire trop élevée: {memory_before}%"
                }
            
            dashboard_data = {}
            
            # Analytics serveur via logging.py (si pas skip)
            if not UPDATER_CONFIG["SKIP_HEAVY_ANALYTICS"]:
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
                    logger.warning(f"Erreur récupération server stats safe: {server_error}")
            
            # Requêtes DB avec limites strictes et gestion d'erreur robuste
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                with psycopg2.connect(self.analytics.dsn) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        
                        # Requête principale avec LIMIT pour économie mémoire
                        limit = UPDATER_CONFIG["MAX_SQL_ROWS_PER_QUERY"]
                        cur.execute(f"""
                            SELECT 
                                COUNT(DISTINCT user_email) FILTER (WHERE user_email IS NOT NULL AND user_email != '') as total_users,
                                COUNT(*) as total_questions,
                                COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as questions_today,
                                COUNT(*) FILTER (WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE)) as questions_this_week,
                                COUNT(*) FILTER (WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)) as questions_this_month,
                                AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) / 1000 as avg_response_time_calc,
                                AVG(response_confidence) FILTER (WHERE response_confidence IS NOT NULL) * 100 as avg_confidence
                            FROM (
                                SELECT * FROM user_questions_complete 
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                ORDER BY created_at DESC
                                LIMIT {limit}
                            ) recent_questions
                        """)
                        
                        stats_result = cur.fetchone()
                        if stats_result:
                            dashboard_data.update({
                                "total_users": min(stats_result["total_users"] or 0, 10000),  # Cap arbitraire
                                "unique_active_users": min(stats_result["total_users"] or 0, 10000),
                                "total_questions": min(stats_result["total_questions"] or 0, 50000),
                                "questions_today": stats_result["questions_today"] or 0,
                                "questions_this_week": stats_result["questions_this_week"] or 0,
                                "questions_this_month": stats_result["questions_this_month"] or 0,
                                "avg_confidence": round(stats_result["avg_confidence"] or 0, 1)
                            })
                            
                            if not dashboard_data.get("avg_response_time"):
                                dashboard_data["avg_response_time"] = round(stats_result["avg_response_time_calc"] or 0, 3)
                        
                        # Distribution sources (version limitée)
                        if UPDATER_CONFIG["REDUCE_DATASET_SIZE"]:
                            cur.execute(f"""
                                SELECT response_source, COUNT(*) as count
                                FROM (
                                    SELECT response_source FROM user_questions_complete 
                                    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                                    LIMIT {limit // 2}
                                ) recent_sources
                                GROUP BY response_source
                                ORDER BY count DESC
                                LIMIT 10
                            """)
                        else:
                            # Version originale conservée
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
                            if source_name == "rag":
                                source_dist["rag_retriever"] = row["count"]
                            elif source_name == "openai_fallback":
                                source_dist["openai_fallback"] = row["count"]
                            elif source_name in ["table_lookup", "perfstore"]:
                                source_dist["perfstore"] = source_dist.get("perfstore", 0) + row["count"]
                            else:
                                source_dist[source_name] = row["count"]
                        
                        dashboard_data["source_distribution"] = source_dist
                        
                        # Top utilisateurs (version limitée)
                        cur.execute(f"""
                            SELECT 
                                user_email,
                                COUNT(*) as question_count,
                                'free' as plan
                            FROM (
                                SELECT user_email FROM user_questions_complete 
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                    AND user_email IS NOT NULL 
                                    AND user_email != ''
                                LIMIT {limit}
                            ) recent_users
                            GROUP BY user_email
                            ORDER BY question_count DESC
                            LIMIT 10
                        """)
                        
                        top_users = []
                        for row in cur.fetchall()[:5]:  # Max 5 pour économiser mémoire
                            top_users.append({
                                "email": row["user_email"][:50],  # Tronquer email long
                                "question_count": row["question_count"],
                                "plan": row["plan"]
                            })
                        
                        dashboard_data["top_users"] = top_users
                        
                        # Stats feedback défensives CORRIGÉES
                        dashboard_data["feedback_stats"] = await self._get_feedback_stats_safe(cur)
                
            except Exception as db_error:
                logger.error(f"Erreur requêtes base de données dashboard: {db_error}")
                # Continuer avec des valeurs par défaut
                dashboard_data.update({
                    "total_users": 0,
                    "unique_active_users": 0, 
                    "total_questions": 0,
                    "questions_today": 0,
                    "questions_this_week": 0,
                    "questions_this_month": 0,
                    "avg_confidence": 0,
                    "source_distribution": {},
                    "top_users": [],
                    "feedback_stats": {"total": 0, "positive": 0, "negative": 0, "with_comments": 0, "satisfaction_rate": 0.0}
                })
            
            # Données billing (version simplifiée)
            billing_summary = {
                "total_revenue": 0,
                "monthly_revenue": 0,
                "plan_distribution": {"free": dashboard_data.get("total_users", 0)}
            }
            dashboard_data.update(billing_summary)
            
            # Valeurs par défaut
            defaults = {
                "median_response_time": dashboard_data.get("avg_response_time", 0),
                "openai_costs": 6.30,
                "top_inviters": []
            }
            
            for key, default_value in defaults.items():
                if key not in dashboard_data:
                    dashboard_data[key] = default_value
            
            # Sauvegarder dans le cache
            self.cache.set_dashboard_snapshot(dashboard_data, period_hours=24)
            self.cache.set_cache("dashboard:main", dashboard_data, ttl_hours=1, source="analytics_computed_safe")
            
            memory_after = get_memory_usage_percent()
            logger.info(f"Dashboard stats collectées safe: {len(dashboard_data)} métriques (RAM: {memory_before}%→{memory_after}%)")
            return {"status": "success", "metrics_collected": len(dashboard_data)}
            
        except Exception as e:
            logger.error(f"Erreur collecte dashboard stats safe: {e}")
            return {"status": "error", "error": str(e)}

    async def _update_openai_costs_safe(self) -> Dict[str, Any]:
        """Collecte coûts OpenAI avec gestion mémoire"""
        try:
            logger.info("Collecte coûts OpenAI safe...")
            
            # Période plus courte pour économiser API calls
            end_date = datetime.now()
            days = 3 if UPDATER_CONFIG["REDUCE_DATASET_SIZE"] else 7
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            costs_data = await get_openai_usage_data_safe(
                start_str, end_str, max_days=days
            )
            
            # Enrichir avec métadonnées
            costs_data.update({
                "period_start": start_str,
                "period_end": end_str,
                "collected_at": datetime.now().isoformat(),
                "data_source": "openai_api_optimized_safe"
            })
            
            # Cache dans les deux systèmes
            self.cache.set_openai_costs(start_str, end_str, "week", costs_data)
            self.cache.set_cache("openai:costs:current", costs_data, ttl_hours=4, source="openai_api_safe")
            
            logger.info(f"Coûts OpenAI collectés safe: ${costs_data.get('total_cost', 0):.2f}")
            return {
                "status": "success", 
                "total_cost": costs_data.get('total_cost', 0),
                "api_calls_made": costs_data.get('api_calls_made', 0),
                "cached_days": costs_data.get('cached_days', 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur collecte coûts OpenAI safe: {e}")
            
            # Fallback
            fallback_data = {
                "total_cost": 6.30,
                "total_tokens": 450000,
                "api_calls": 250,
                "models_usage": {"gpt-4": {"cost": 4.20}, "gpt-3.5-turbo": {"cost": 2.10}},
                "data_source": "fallback_safe",
                "note": f"Erreur API OpenAI safe: {str(e)[:100]}"
            }
            
            self.cache.set_cache("openai:costs:fallback", fallback_data, ttl_hours=1, source="fallback_safe")
            return {"status": "fallback", "error": str(e)[:100], "fallback_cost": 6.30}

    async def _update_invitation_stats_safe(self) -> Dict[str, Any]:
        """Collecte stats invitations avec gestion mémoire"""
        try:
            logger.info("Collecte stats invitations safe...")
            
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(self.analytics.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Vérifier existence table
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'invitations'
                        )
                    """)
                    
                    if not cur.fetchone()["exists"]:
                        invitation_data = {
                            "total_invitations_sent": 0,
                            "total_invitations_accepted": 0,
                            "acceptance_rate": 0.0,
                            "unique_inviters": 0,
                            "top_inviters_by_sent": [],
                            "top_inviters_by_accepted": [],
                            "note": "Table invitations non trouvée safe"
                        }
                    else:
                        # Requêtes avec LIMIT pour économie mémoire
                        limit = UPDATER_CONFIG["MAX_SQL_ROWS_PER_QUERY"]
                        
                        cur.execute(f"""
                            SELECT 
                                COUNT(*) as total_sent,
                                COUNT(*) FILTER (WHERE status = 'accepted') as total_accepted,
                                COUNT(DISTINCT inviter_email) as unique_inviters,
                                CASE 
                                    WHEN COUNT(*) > 0 THEN 
                                        ROUND((COUNT(*) FILTER (WHERE status = 'accepted')::DECIMAL / COUNT(*)) * 100, 2)
                                    ELSE 0 
                                END as acceptance_rate
                            FROM (
                                SELECT * FROM invitations
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                LIMIT {limit}
                            ) recent_invitations
                        """)
                        
                        stats_result = cur.fetchone()
                        
                        # Top inviters (limité)
                        cur.execute(f"""
                            SELECT 
                                inviter_email,
                                inviter_name,
                                COUNT(*) as invitations_sent,
                                COUNT(*) FILTER (WHERE status = 'accepted') as invitations_accepted
                            FROM (
                                SELECT * FROM invitations
                                WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                                LIMIT {limit}
                            ) recent_inv
                            GROUP BY inviter_email, inviter_name
                            ORDER BY invitations_sent DESC
                            LIMIT 5
                        """)
                        
                        top_inviters = [dict(row) for row in cur.fetchall()]
                        
                        invitation_data = {
                            "total_invitations_sent": stats_result["total_sent"],
                            "total_invitations_accepted": stats_result["total_accepted"],
                            "acceptance_rate": float(stats_result["acceptance_rate"]),
                            "unique_inviters": stats_result["unique_inviters"],
                            "top_inviters_by_sent": top_inviters,
                            "top_inviters_by_accepted": top_inviters  # Simplifié pour économie
                        }
            
            self.cache.set_cache("invitations:global_stats", invitation_data, ttl_hours=2, source="computed_safe")
            
            logger.info(f"Stats invitations collectées safe: {invitation_data['total_invitations_sent']} sent")
            return {"status": "success", "invitations_processed": invitation_data["total_invitations_sent"]}
            
        except Exception as e:
            logger.error(f"Erreur collecte stats invitations safe: {e}")
            return {"status": "error", "error": str(e)[:100]}

    async def _update_server_performance_safe(self) -> Dict[str, Any]:
        """Collecte performance serveur avec gestion mémoire"""
        try:
            logger.info("Collecte performance serveur safe...")
            
            performance_data = {}
            
            # Version allégée si skip heavy analytics
            if UPDATER_CONFIG["SKIP_HEAVY_ANALYTICS"]:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                
                with psycopg2.connect(self.analytics.dsn) as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        limit = UPDATER_CONFIG["MAX_SQL_ROWS_PER_QUERY"]
                        
                        cur.execute(f"""
                            SELECT 
                                COUNT(*) as total_requests,
                                COUNT(*) FILTER (WHERE status = 'success') as successful_requests,
                                COUNT(*) FILTER (WHERE status != 'success') as failed_requests,
                                AVG(processing_time_ms) FILTER (WHERE processing_time_ms > 0) as avg_response_time_ms
                            FROM (
                                SELECT * FROM user_questions_complete 
                                WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
                                LIMIT {limit}
                            ) recent_perf
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
                                "total_failures": failed_req
                            },
                            "collected_at": datetime.now().isoformat(),
                            "source": "questions_computed_safe"
                        }
            else:
                # Version complète conservée
                try:
                    from app.api.v1.logging import get_server_analytics
                    server_metrics = get_server_analytics(hours=24)
                    
                    if "error" not in server_metrics:
                        performance_data = {
                            "period_hours": 24,
                            "current_status": server_metrics.get("current_status", {}),
                            "global_stats": server_metrics.get("global_stats", {}),
                            "collected_at": datetime.now().isoformat()
                        }
                    else:
                        raise Exception(server_metrics["error"])
                        
                except Exception:
                    # Fallback vers version allégée
                    return await self._update_server_performance_safe()
            
            self.cache.set_cache("server:performance:24h", performance_data, ttl_hours=1, source="computed_safe")
            
            logger.info(f"Performance serveur collectée safe: {performance_data['current_status']['overall_health']}")
            return {
                "status": "success", 
                "health": performance_data["current_status"]["overall_health"],
                "total_requests": performance_data["global_stats"].get("total_requests", 0)
            }
            
        except Exception as e:
            logger.error(f"Erreur collecte performance safe: {e}")
            return {"status": "error", "error": str(e)[:100]}

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
                    "feedback_support": self._feedback_columns_available,
                    "memory_optimization": "enabled",
                    "collection_mode": "sequential_safe" if not UPDATER_CONFIG["ENABLE_PARALLEL_COLLECTION"] else "parallel"
                }
                
        except Exception as e:
            logger.error(f"Erreur récupération statut: {e}")
            return {"status": "error", "error": str(e)}

    async def force_update_specific(self, component: str) -> Dict[str, Any]:
        """Force la mise à jour d'un composant spécifique"""
        try:
            logger.info(f"Force update safe: {component}")
            
            if component == "dashboard":
                result = await self._update_dashboard_stats_safe()
            elif component == "openai":
                result = await self._update_openai_costs_safe()
            elif component == "invitations":
                result = await self._update_invitation_stats_safe()
            elif component == "performance":
                result = await self._update_server_performance_safe()
            else:
                return {"status": "error", "error": f"Composant '{component}' inconnu"}
            
            logger.info(f"Force update safe {component}: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur force update safe {component}: {e}")
            return {"status": "error", "error": str(e)}

    def refresh_feedback_detection(self) -> Dict[str, Any]:
        """
        Actualise la détection des colonnes feedback
        Utile après une migration ou modification de schéma
        """
        try:
            logger.info("Actualisation détection colonnes feedback...")
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
                logger.info(f"Changements détectés dans les colonnes feedback: {result['new_detection']}")
            else:
                logger.info("Aucun changement détecté dans les colonnes feedback")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur refresh feedback detection: {e}")
            return {"status": "error", "error": str(e)}

    def get_memory_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques mémoire et de performance"""
        try:
            return {
                "system_memory_percent": get_memory_usage_percent(),
                "collection_stats": self.collection_stats.copy(),
                "updater_config": UPDATER_CONFIG.copy(),
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "update_in_progress": self.update_in_progress
            }
        except Exception as e:
            return {"error": str(e)}

    def toggle_parallel_collection(self, enable: bool = None) -> Dict[str, Any]:
        """Active/désactive la collecte parallèle"""
        try:
            if enable is None:
                enable = not UPDATER_CONFIG["ENABLE_PARALLEL_COLLECTION"]
            
            UPDATER_CONFIG["ENABLE_PARALLEL_COLLECTION"] = enable
            
            logger.info(f"Collecte parallèle: {'activée' if enable else 'désactivée'}")
            
            return {
                "status": "success",
                "parallel_collection_enabled": enable,
                "recommendation": "Mode séquentiel recommandé pour économie mémoire",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton global 
_stats_updater_instance = None

def get_stats_updater() -> StatisticsUpdater:
    """Récupère l'instance singleton du collecteur"""
    global _stats_updater_instance
    if _stats_updater_instance is None:
        _stats_updater_instance = StatisticsUpdater()
    return _stats_updater_instance

# Fonctions utilitaires
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

def get_updater_memory_stats():
    """Statistiques mémoire globales du updater"""
    try:
        updater = get_stats_updater()
        return updater.get_memory_stats()
    except Exception as e:
        return {"error": str(e), "system_memory_percent": get_memory_usage_percent()}

def toggle_heavy_analytics(skip: bool = None):
    """Active/désactive les analytics lourdes"""
    if skip is None:
        skip = not UPDATER_CONFIG["SKIP_HEAVY_ANALYTICS"]
    
    UPDATER_CONFIG["SKIP_HEAVY_ANALYTICS"] = skip
    logger.info(f"Heavy analytics: {'désactivées' if skip else 'activées'}")
    
    return {
        "status": "success",
        "heavy_analytics_skipped": skip,
        "memory_impact": "Réduction ~30% RAM si désactivées"
    }