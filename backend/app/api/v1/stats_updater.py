# app/api/v1/stats_updater.py
# -*- coding: utf-8 -*-
"""
Version HYBRIDE - Garde les bonnes intégrations mais corrige la détection de table
OBJECTIF: Utiliser les mêmes données que /logging/questions + garder health.py et billing.py
"""

import asyncio
import logging
import time
import os
import gc
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import des gestionnaires existants
from app.api.v1.logging import get_analytics_manager
from app.api.v1.billing import get_billing_manager  
from app.api.v1.stats_cache import get_stats_cache

logger = logging.getLogger(__name__)

def get_memory_usage_percent():
    """Retourne le pourcentage d'utilisation mémoire système"""
    try:
        return psutil.virtual_memory().percent
    except Exception:
        return 0

def safe_str_conversion(value, max_length=100):
    """Conversion sécurisée en string avec limitation de longueur"""
    try:
        if value is None:
            return "None"
        str_value = str(value)
        return str_value[:max_length] if len(str_value) > max_length else str_value
    except Exception:
        return "conversion_error"

class StatisticsUpdater:
    """
    Version HYBRIDE qui utilise les bonnes données ET garde les intégrations
    """
    
    def __init__(self):
        logger.info("StatisticsUpdater HYBRIDE - Mêmes données que /logging/questions + intégrations")
        
        self.cache = get_stats_cache()
        self.analytics = get_analytics_manager()
        self.billing = get_billing_manager()
        self.last_update = None
        self.update_in_progress = False
        
        # Identifier la vraie table utilisée par analytics_manager
        self._correct_table_name = None
        
        self.collection_stats = {
            "total_collections": 0,
            "successful_collections": 0,
            "initialization_time": datetime.now().isoformat(),
            "version": "hybride_fixed"
        }
        
        logger.info("StatisticsUpdater HYBRIDE initialisé")
    
    async def update_all_statistics(self) -> Dict[str, Any]:
        """
        Fonction principale hybride
        """
        if self.update_in_progress:
            logger.warning("Mise à jour déjà en cours")
            return {"status": "skipped", "reason": "update_in_progress"}
        
        start_time = time.time()
        start_memory = get_memory_usage_percent()
        self.update_in_progress = True
        
        try:
            logger.info(f"DÉBUT collecte hybride (RAM: {start_memory}%)")
            
            # FORCER L'INVALIDATION DU CACHE
            try:
                self.cache.delete_cache("dashboard:main")
                self.cache.delete_cache("dashboard:snapshot")
                logger.info("Cache dashboard invalidé")
            except Exception as cache_error:
                logger.warning(f"Erreur invalidation cache: {cache_error}")
            
            # Collecte hybride avec toutes les intégrations
            dashboard_data = await self._collect_hybrid_stats()
            
            if dashboard_data.get("status") == "success":
                final_data = dashboard_data.get("data", {})
                
                self.cache.set_dashboard_snapshot(final_data, period_hours=24)
                self.cache.set_cache("dashboard:main", final_data, ttl_hours=1, source="hybrid_updater")
                
                self.collection_stats["successful_collections"] += 1
                
            self.collection_stats["total_collections"] += 1
            self.last_update = datetime.now()
            
            end_memory = get_memory_usage_percent()
            duration_ms = int((time.time() - start_time) * 1000)
            
            result = {
                "status": "completed" if dashboard_data.get("status") == "success" else "partial",
                "successful_updates": 1 if dashboard_data.get("status") == "success" else 0,
                "total_updates": 1,
                "errors": [] if dashboard_data.get("status") == "success" else [dashboard_data.get("error")],
                "duration_ms": duration_ms,
                "last_update": self.last_update.isoformat(),
                "memory_info": {
                    "start_memory_percent": start_memory,
                    "end_memory_percent": end_memory,
                    "memory_delta": end_memory - start_memory
                },
                "version": "hybride_fixed",
                "table_used": self._correct_table_name
            }
            
            self.cache.set_cache("system:last_update_summary", result, ttl_hours=25, source="hybrid_updater")
            
            logger.info(f"Collecte HYBRIDE terminée en {duration_ms}ms avec table: {self._correct_table_name}")
            return result
            
        except Exception as e:
            error_msg = safe_str_conversion(e)
            logger.error(f"Erreur collecte hybride: {error_msg}")
            
            return {
                "status": "failed",
                "error": error_msg,
                "duration_ms": int((time.time() - start_time) * 1000),
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            self.update_in_progress = False
    
    async def _collect_hybrid_stats(self) -> Dict[str, Any]:
        """
        Collecte hybride : utilise les bonnes données + intégrations health/billing
        """
        try:
            # Méthode 1: Utiliser analytics_manager pour identifier la vraie table
            if not self.analytics or not hasattr(self.analytics, 'dsn') or not self.analytics.dsn:
                logger.warning("Analytics manager non disponible")
                return {"status": "error", "error": "no_analytics_manager"}
            
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            with psycopg2.connect(self.analytics.dsn, connect_timeout=15) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # IDENTIFIER LA VRAIE TABLE
                    self._correct_table_name = self._find_correct_table(cur)
                    
                    if not self._correct_table_name:
                        logger.error("Impossible de trouver la table avec données")
                        return {"status": "error", "error": "no_data_table", "data": self._get_empty_stats()}
                    
                    logger.info(f"✅ Table identifiée: {self._correct_table_name}")
                    
                    # REQUÊTE PRINCIPALE AVEC LA BONNE TABLE
                    main_query = f"""
                        SELECT 
                            COUNT(*) as total_questions,
                            COUNT(*) FILTER (WHERE DATE(timestamp) = CURRENT_DATE) as questions_today,
                            COUNT(*) FILTER (WHERE timestamp >= DATE_TRUNC('week', CURRENT_DATE)) as questions_this_week,
                            COUNT(*) FILTER (WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)) as questions_this_month,
                            COUNT(DISTINCT user_email) as unique_users,
                            COUNT(DISTINCT user_email) FILTER (WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days') as active_users_week,
                            AVG(response_time) as avg_response_time,
                            MIN(response_time) as min_response_time,
                            MAX(response_time) as max_response_time,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time) as median_response_time,
                            AVG(confidence_score) * 100 as avg_confidence
                        FROM {self._correct_table_name} 
                        WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
                        AND response_time IS NOT NULL
                    """
                    
                    cur.execute(main_query)
                    main_result = cur.fetchone()
                    
                    if not main_result or main_result["total_questions"] == 0:
                        logger.warning(f"Aucune donnée dans {self._correct_table_name}")
                        return {"status": "success", "data": self._get_empty_stats()}
                    
                    # SOURCES DE RÉPONSES
                    source_distribution = self._calculate_source_distribution(cur)
                    
                    # TOP UTILISATEURS avec la bonne table
                    top_users = self._calculate_top_users(cur)
                    
                    # INTÉGRATION HEALTH.PY - CONSERVÉE
                    system_health_data = await self._get_system_health_data()
                    
                    # INTÉGRATION BILLING_OPENAI.PY - CONSERVÉE  
                    openai_costs = await self._get_real_openai_costs()
                    
                    # STATS DE FEEDBACK SÉCURISÉES
                    feedback_stats = self._get_safe_feedback_stats(cur)
                    
                    # STRUCTURE FINALE IDENTIQUE À LA VERSION PRÉCÉDENTE
                    final_dashboard_data = {
                        # Meta-informations
                        "meta": {
                            "collected_at": datetime.now().isoformat(),
                            "data_source": f"hybrid_corrected_{self._correct_table_name}",
                            "version": "hybride_fixed",
                            "table_used": self._correct_table_name
                        },
                        
                        # System Stats - INTÉGRATION HEALTH.PY CONSERVÉE
                        "systemStats": {
                            "system_health": {
                                "uptime_hours": system_health_data.get("uptime_hours", 0),
                                "total_requests": main_result["total_questions"] or 0,
                                "error_rate": system_health_data.get("error_rate", 0),
                                "rag_status": system_health_data.get("rag_status", {"global": False})
                            },
                            "billing_stats": {
                                "plans_available": 1,
                                "plan_names": ["free"]
                            },
                            "features_enabled": system_health_data.get("features_enabled", {
                                "analytics": True,
                                "billing": False,
                                "authentication": True,
                                "openai_fallback": True
                            })
                        },
                        
                        # Usage Stats - DONNÉES RÉELLES DE LA BONNE TABLE
                        "usageStats": {
                            "unique_users": main_result["unique_users"] or 0,
                            "unique_active_users": main_result["active_users_week"] or 0,
                            "total_questions": main_result["total_questions"] or 0,
                            "questions_today": main_result["questions_today"] or 0,
                            "questions_this_week": main_result["questions_this_week"] or 0,
                            "questions_this_month": main_result["questions_this_month"] or 0,
                            "source_distribution": source_distribution,
                            "monthly_breakdown": {
                                datetime.now().strftime("%Y-%m"): main_result["questions_this_month"] or 0
                            }
                        },
                        
                        # Performance Stats - CALCULÉES AVEC LES BONNES DONNÉES
                        "performanceStats": {
                            "avg_response_time": float(main_result["avg_response_time"] or 0),
                            "median_response_time": float(main_result["median_response_time"] or 0),
                            "min_response_time": float(main_result["min_response_time"] or 0),
                            "max_response_time": float(main_result["max_response_time"] or 0),
                            "response_time_count": main_result["total_questions"] or 0,
                            "openai_costs": openai_costs.get("costs", {}).get("total", 0),
                            "error_count": system_health_data.get("error_count", 0),
                            "cache_hit_rate": system_health_data.get("cache_hit_rate", 85.0),
                            "avg_confidence": float(main_result["avg_confidence"] or 0)
                        },
                        
                        # Billing Stats - TOP USERS AVEC BONNES DONNÉES
                        "billingStats": {
                            "total_revenue": 0.0,
                            "monthly_revenue": 0.0,
                            "plan_distribution": {"free": main_result["unique_users"] or 0},
                            "top_users": top_users
                        },
                        
                        # Feedback Stats - SÉCURISÉES
                        "feedbackStats": feedback_stats,
                        
                        # Cache info
                        "cache_info": {
                            "generated_at": datetime.now().isoformat(),
                            "ttl_hours": 1,
                            "source": "hybrid_updater"
                        }
                    }
                    
                    logger.info(f"✅ STATS HYBRIDES: {main_result['unique_users']} users, {main_result['total_questions']} questions, table={self._correct_table_name}")
                    return {"status": "success", "data": final_dashboard_data}
                    
        except Exception as e:
            error_msg = safe_str_conversion(e)
            logger.error(f"Erreur collecte hybride: {error_msg}")
            return {"status": "error", "error": error_msg, "data": self._get_empty_stats()}
    
    def _find_correct_table(self, cur) -> Optional[str]:
        """
        Trouve la table qui contient vraiment vos données
        Utilise la même logique que analytics_manager
        """
        # D'abord essayer la table par défaut utilisée par analytics_manager
        try:
            # Test avec la même structure que vos données de diagnostic
            cur.execute("""
                SELECT COUNT(*) as count, 
                       COUNT(DISTINCT user_email) as users,
                       AVG(response_time) as avg_time
                FROM user_questions 
                WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
                AND user_email IS NOT NULL
                AND response_time > 0
                LIMIT 1
            """)
            
            result = cur.fetchone()
            if result and result["count"] > 0 and result["users"] > 0:
                logger.info(f"✅ Table 'user_questions' trouvée: {result['count']} questions, {result['users']} users")
                return "user_questions"
                
        except Exception:
            pass
        
        # Essayer d'autres noms possibles
        possible_tables = ["questions", "user_questions_complete", "analytics_questions"]
        
        for table_name in possible_tables:
            try:
                cur.execute(f"""
                    SELECT COUNT(*) as count, 
                           COUNT(DISTINCT user_email) as users
                    FROM {table_name} 
                    WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
                    AND user_email IS NOT NULL
                    LIMIT 1
                """)
                
                result = cur.fetchone()
                if result and result["count"] > 0 and result["users"] > 0:
                    logger.info(f"✅ Table '{table_name}' trouvée: {result['count']} questions, {result['users']} users")
                    return table_name
                    
            except Exception:
                continue
        
        logger.error("❌ Aucune table trouvée avec des données")
        return None
    
    def _calculate_source_distribution(self, cur) -> Dict[str, int]:
        """Distribution des sources - utilise la bonne table"""
        source_distribution = {}
        
        try:
            cur.execute(f"""
                SELECT 
                    response_source, 
                    COUNT(*) as count
                FROM {self._correct_table_name} 
                WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY response_source
                ORDER BY count DESC
                LIMIT 10
            """)
            
            sources = cur.fetchall()
            for row in sources:
                source = row["response_source"] or "unknown"
                if source == "rag":
                    source_distribution["rag_retriever"] = row["count"]
                elif source == "openai_fallback":
                    source_distribution["openai_fallback"] = row["count"]
                elif source in ["table_lookup", "perfstore"]:
                    source_distribution["perfstore"] = source_distribution.get("perfstore", 0) + row["count"]
                else:
                    source_distribution[source] = row["count"]
                    
        except Exception as e:
            logger.warning(f"Erreur distribution sources: {e}")
            
        return source_distribution
    
    def _calculate_top_users(self, cur):
        """Top utilisateurs - utilise la bonne table"""
        top_users = []
        
        try:
            cur.execute(f"""
                SELECT 
                    user_email,
                    COUNT(*) as question_count
                FROM {self._correct_table_name} 
                WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
                    AND user_email IS NOT NULL 
                GROUP BY user_email
                ORDER BY question_count DESC
                LIMIT 10
            """)
            
            top_users_raw = cur.fetchall()
            for row in top_users_raw:
                user_data = {
                    "email": row["user_email"][:50],
                    "question_count": row["question_count"],
                    "plan": "free"
                }
                top_users.append(user_data)
                
            logger.info(f"✅ Top users calculés: {len(top_users)} utilisateurs")
                
        except Exception as e:
            logger.warning(f"Erreur calcul top users: {e}")
            
        return top_users
    
    async def _get_system_health_data(self) -> Dict[str, Any]:
        """
        INTÉGRATION HEALTH.PY - CONSERVÉE de la version précédente
        """
        try:
            response = requests.get(
                "http://localhost:8000/api/v1/health/detailed",
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                
                system_health = {
                    "uptime_hours": health_data.get("uptime_hours", 0),
                    "error_rate": health_data.get("error_rate_percent", 0),
                    "cache_hit_rate": health_data.get("cache_hit_rate", 85.0),
                    "error_count": health_data.get("error_count_24h", 0),
                    "rag_status": {
                        "global": health_data.get("rag_configured", False),
                        "broiler": health_data.get("rag_broiler_ready", False),
                        "layer": health_data.get("rag_layer_ready", False)
                    },
                    "features_enabled": {
                        "analytics": health_data.get("analytics_ready", False),
                        "billing": health_data.get("billing_ready", False),
                        "authentication": health_data.get("auth_ready", False),
                        "openai_fallback": health_data.get("openai_configured", False)
                    }
                }
                
                logger.info(f"✅ Health.py intégré: uptime={system_health['uptime_hours']}h")
                return system_health
                
        except Exception as e:
            logger.warning(f"Erreur intégration health.py: {e}")
            
        # Fallback si health.py indisponible
        return {
            "uptime_hours": 0,
            "error_rate": 0,
            "cache_hit_rate": 85.0,
            "error_count": 0,
            "rag_status": {"global": False},
            "features_enabled": {"analytics": True, "billing": False, "authentication": True, "openai_fallback": True}
        }
    
    async def _get_real_openai_costs(self) -> Dict[str, Any]:
        """
        INTÉGRATION BILLING_OPENAI.PY - CONSERVÉE de la version précédente
        """
        try:
            response = requests.get(
                "http://localhost:8000/api/v1/billing/openai-usage/current-month-light",
                timeout=15
            )
            
            if response.status_code == 200:
                billing_data = response.json()
                
                costs_data = {
                    "success": True,
                    "costs": {
                        "total": billing_data.get("total_cost", 0),
                        "input_tokens": billing_data.get("total_input_tokens", 0),
                        "output_tokens": billing_data.get("total_output_tokens", 0),
                        "requests": billing_data.get("total_requests", 0)
                    }
                }
                
                logger.info(f"✅ Billing OpenAI intégré: ${costs_data['costs']['total']:.2f}")
                return costs_data
                
        except Exception as e:
            logger.warning(f"Erreur intégration billing_openai.py: {e}")
            
        return {"success": False, "costs": {"total": 0}}
    
    def _get_safe_feedback_stats(self, cur) -> Dict[str, Any]:
        """Stats feedback sécurisées - ne crash jamais"""
        feedback_stats = {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "with_comments": 0,
            "satisfaction_rate": 0.0
        }
        
        try:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total_feedback,
                    COUNT(*) FILTER (WHERE feedback IS NOT NULL) as with_feedback,
                    COUNT(*) FILTER (WHERE feedback_comment IS NOT NULL AND feedback_comment != '') as with_comments
                FROM {self._correct_table_name}
                WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
            """)
            
            result = cur.fetchone()
            if result:
                feedback_stats["total"] = result["total_feedback"] or 0
                feedback_stats["with_comments"] = result["with_comments"] or 0
                
        except Exception as e:
            logger.info(f"Stats feedback non disponibles: {e}")
            
        return feedback_stats
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Données vides avec structure correcte"""
        return {
            "meta": {
                "collected_at": datetime.now().isoformat(),
                "data_source": "fallback_empty",
                "version": "hybride_fixed"
            },
            "systemStats": {
                "system_health": {"uptime_hours": 0, "total_requests": 0, "error_rate": 0},
                "billing_stats": {"plans_available": 0},
                "features_enabled": {"analytics": False}
            },
            "usageStats": {
                "unique_users": 0, "unique_active_users": 0, "total_questions": 0, 
                "questions_today": 0, "questions_this_month": 0
            },
            "performanceStats": {
                "avg_response_time": 0, "min_response_time": 0, "max_response_time": 0
            },
            "billingStats": {"total_revenue": 0, "top_users": []},
            "feedbackStats": {"total": 0, "satisfaction_rate": 0}
        }
    
    def get_update_status(self) -> Dict[str, Any]:
        """Statut de la dernière mise à jour"""
        try:
            cached_summary = self.cache.get_cache("system:last_update_summary")
            
            if cached_summary:
                return cached_summary["data"]
            else:
                return {
                    "status": "never_updated",
                    "message": "Version hybride - jamais exécutée",
                    "update_in_progress": self.update_in_progress,
                    "last_update": self.last_update.isoformat() if self.last_update else None,
                    "version": "hybride_fixed",
                    "detected_table": self._correct_table_name
                }
                
        except Exception as e:
            error_msg = safe_str_conversion(e)
            logger.error(f"Erreur récupération statut: {error_msg}")
            return {"status": "error", "error": error_msg}

    async def force_update_component(self, component: str) -> Dict[str, Any]:
        """Force la mise à jour"""
        try:
            logger.info(f"Force update hybride: {component}")
            return await self.update_all_statistics()
            
        except Exception as e:
            error_msg = safe_str_conversion(e)
            logger.error(f"Erreur force update: {error_msg}")
            return {"status": "error", "error": error_msg}

# Singleton global
_stats_updater_instance = None

def get_stats_updater():
    """Récupère l'instance singleton hybride"""
    global _stats_updater_instance
    if _stats_updater_instance is None:
        logger.info("Création instance StatisticsUpdater HYBRIDE")
        _stats_updater_instance = StatisticsUpdater()
    return _stats_updater_instance

# Fonctions utilitaires
async def run_update_cycle():
    """Exécute un cycle de mise à jour hybride"""
    try:
        updater = get_stats_updater()
        result = await updater.update_all_statistics()
        logger.info(f"Cycle hybride terminé: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        error_msg = safe_str_conversion(e)
        logger.error(f"Erreur cycle hybride: {error_msg}")
        return {
            "status": "failed",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }

async def force_update_all():
    """Force une mise à jour immédiate hybride"""
    try:
        updater = get_stats_updater()
        result = await updater.update_all_statistics()
        logger.info(f"Force update hybride terminé: {result.get('status', 'unknown')}")
        return result
    except Exception as e:
        error_msg = safe_str_conversion(e)
        logger.error(f"Erreur force update hybride: {error_msg}")
        return {
            "status": "failed",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }