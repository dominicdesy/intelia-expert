# app/api/v1/stats_updater.py
"""
VERSION SIMPLE ET DIRECTE - UTILISE DATABASE_URL DIRECTEMENT
Corrige le problème de DSN en utilisant la même connexion que vos données réelles
"""

import os
import logging
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, Any
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class StatisticsUpdater:
    def __init__(self):
        # LOG DE DÉPLOIEMENT - VERSION SIMPLE V1.0
        print("=" * 80)
        print("STATS_UPDATER.PY - VERSION SIMPLE V1.0 - DÉPLOYÉE")
        print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("CORRECTION CRITIQUE: Utilise DATABASE_URL au lieu de analytics.dsn")
        print("Cette version devrait corriger le problème des statistiques à 0")
        print("=" * 80)
        
        # CORRECTION CRITIQUE: Utilise DATABASE_URL directement
        self.dsn = os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL manquant")
        
        logger.info("🚀 StatisticsUpdater VERSION SIMPLE V1.0 initialisé")
        logger.info(f"✅ DSN configuré depuis DATABASE_URL (longueur: {len(self.dsn)} chars)")
        logger.info("🔧 Cette version corrige le bug DSN analytics vs DATABASE_URL")
        
        self.last_update = None
        self.update_in_progress = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupère les stats directement depuis user_questions_complete"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Requête principale - IDENTIQUE à celle qui fonctionne manuellement
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_questions,
                            COUNT(*) FILTER (WHERE DATE(created_at) = CURRENT_DATE) as questions_today,
                            COUNT(*) FILTER (WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)) as questions_this_month,
                            COUNT(DISTINCT user_email) as unique_users,
                            AVG(processing_time_ms / 1000.0) as avg_response_time,
                            MIN(processing_time_ms / 1000.0) as min_response_time,
                            MAX(processing_time_ms / 1000.0) as max_response_time
                        FROM user_questions_complete 
                        WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
                        AND processing_time_ms IS NOT NULL
                    """)
                    
                    result = cur.fetchone()
                    
                    if result and result["total_questions"] > 0:
                        logger.info(f"✅ Stats récupérées: {result['total_questions']} questions, {result['unique_users']} utilisateurs")
                        
                        return {
                            "usageStats": {
                                "total_questions": result["total_questions"],
                                "questions_today": result["questions_today"], 
                                "questions_this_month": result["questions_this_month"],
                                "unique_users": result["unique_users"]
                            },
                            "performanceStats": {
                                "avg_response_time": float(result["avg_response_time"] or 0),
                                "min_response_time": float(result["min_response_time"] or 0),
                                "max_response_time": float(result["max_response_time"] or 0),
                                "response_time_count": result["total_questions"]
                            },
                            "systemStats": {
                                "system_health": {
                                    "uptime_hours": 24,
                                    "total_requests": result["total_questions"],
                                    "error_rate": 0
                                }
                            },
                            "billingStats": {
                                "total_revenue": 0.0,
                                "top_users": []
                            },
                            "meta": {
                                "collected_at": datetime.now().isoformat(),
                                "data_source": "user_questions_complete_direct",
                                "dsn_source": "DATABASE_URL"
                            }
                        }
                    else:
                        logger.warning("❌ Aucune donnée trouvée dans user_questions_complete")
                        return self._get_empty_stats()
                        
        except Exception as e:
            logger.error(f"❌ Erreur récupération stats: {e}")
            return self._get_empty_stats()
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Stats vides avec structure correcte"""
        return {
            "usageStats": {
                "total_questions": 0,
                "questions_today": 0,
                "questions_this_month": 0,
                "unique_users": 0
            },
            "performanceStats": {
                "avg_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "response_time_count": 0
            },
            "systemStats": {
                "system_health": {
                    "uptime_hours": 0,
                    "total_requests": 0,
                    "error_rate": 0
                }
            },
            "billingStats": {
                "total_revenue": 0.0,
                "top_users": []
            },
            "meta": {
                "collected_at": datetime.now().isoformat(),
                "data_source": "fallback_empty",
                "dsn_source": "DATABASE_URL"
            }
        }

    async def update_all_statistics(self) -> Dict[str, Any]:
        """Force une mise à jour des statistiques"""
        if self.update_in_progress:
            return {"status": "skipped", "reason": "already_in_progress"}
        
        self.update_in_progress = True
        try:
            stats = self.get_stats()
            self.last_update = datetime.now()
            
            return {
                "status": "success",
                "data": stats,
                "last_update": self.last_update.isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Erreur update_all_statistics: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self.update_in_progress = False

# Singleton global
_stats_updater_instance = None

def get_stats_updater():
    global _stats_updater_instance
    if _stats_updater_instance is None:
        _stats_updater_instance = StatisticsUpdater()
    return _stats_updater_instance

async def force_update_all():
    """Force une mise à jour immédiate"""
    updater = get_stats_updater()
    return await updater.update_all_statistics()