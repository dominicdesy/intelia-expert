# app/api/v1/stats_cache.py
# -*- coding: utf-8 -*-
"""
🚀 SYSTÈME DE CACHE STATISTIQUES - VERSION ULTRA-LÉGÈRE
CORRECTIF URGENT: Out of Memory - Suppression de tous les imports lourds
✨ MINIMAL: Seules les fonctionnalités essentielles conservées
🛡️ MEMORY-SAFE: Aucun thread, aucun pool, aucun monitoring lourd
"""

import json
import logging
import os
import decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

def decimal_safe_json_encoder(obj):
    """Converter JSON pour gérer les types Decimal de PostgreSQL"""
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def safe_json_dumps(data):
    """Sérialisation JSON sécurisée SIMPLE"""
    try:
        return json.dumps(data, default=decimal_safe_json_encoder, separators=(',', ':'))
    except Exception as e:
        logger.error(f"❌ Erreur sérialisation JSON: {e}")
        return json.dumps({"error": "JSON_SERIALIZATION_ERROR"})

class StatisticsCache:
    """
    🛡️ Gestionnaire de cache ULTRA-LÉGER pour éviter Out of Memory
    - Connexions directes uniquement (pas de pool)
    - Pas de monitoring mémoire
    - Pas de threads persistants
    - Migration automatique des colonnes manquantes
    """
    
    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL manquant pour le cache statistiques")
        
        # Créer les tables de cache (version simple)
        self._ensure_cache_tables()
        
        # Migration automatique des colonnes
        self._migration_feedback_success = self._ensure_user_questions_feedback_columns()
        self._migration_cache_stats_success = self._ensure_existing_tables_migration()
        
        logger.info("✅ Système de cache statistiques initialisé (ULTRA-LÉGER)")

    def _ensure_user_questions_feedback_columns(self):
        """🔧 MIGRATION AUTOMATIQUE: Version ultra-légère"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Vérification simple
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'user_questions_complete'
                        )
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    if not table_exists:
                        # Créer la table si elle n'existe pas
                        cur.execute("""
                            CREATE TABLE user_questions_complete (
                                id SERIAL PRIMARY KEY,
                                user_email VARCHAR(255),
                                question_text TEXT,
                                response_text TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                processing_time_ms INTEGER DEFAULT 0,
                                response_confidence DECIMAL(3,2) DEFAULT NULL,
                                response_source VARCHAR(50) DEFAULT NULL,
                                status VARCHAR(20) DEFAULT 'completed',
                                feedback INTEGER DEFAULT NULL CHECK (feedback IN (-1, 0, 1)),
                                feedback_comment TEXT DEFAULT NULL
                            )
                        """)
                        conn.commit()
                        logger.info("✅ Table user_questions_complete créée")
                        return True
                    
                    # Migration simple des colonnes feedback
                    try:
                        cur.execute("ALTER TABLE user_questions_complete ADD COLUMN IF NOT EXISTS feedback INTEGER CHECK (feedback IN (-1, 0, 1))")
                        cur.execute("ALTER TABLE user_questions_complete ADD COLUMN IF NOT EXISTS feedback_comment TEXT")
                        conn.commit()
                        logger.info("✅ Migration feedback terminée (ultra-légère)")
                    except Exception:
                        pass  # Ignore si déjà présent
                    
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Erreur migration feedback: {e}")
            return False

    def _ensure_existing_tables_migration(self):
        """🔧 MIGRATION AUTOMATIQUE: Ajoute data_size_kb aux tables existantes - ULTRA-LÉGER"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Tables à migrer (CORRECTIF: inclure statistics_cache)
                    tables_to_migrate = [
                        'statistics_cache',           # ← TABLE PRINCIPALE !
                        'dashboard_stats_snapshot',
                        'questions_cache', 
                        'openai_costs_cache'
                    ]
                    
                    migrations_applied = []
                    
                    for table_name in tables_to_migrate:
                        try:
                            # Vérifier si la table existe
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.tables 
                                    WHERE table_name = %s
                                )
                            """, (table_name,))
                            
                            if cur.fetchone()[0]:
                                # Table existe - ajouter data_size_kb si manquante
                                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS data_size_kb REAL DEFAULT 0")
                                migrations_applied.append(table_name)
                                logger.info(f"🔧 Colonne data_size_kb ajoutée à {table_name}")
                        except Exception as table_error:
                            logger.info(f"ℹ️ Table {table_name} skip: {table_error}")
                    
                    conn.commit()
                    
                    if migrations_applied:
                        logger.info(f"✅ Migration data_size_kb terminée: {migrations_applied}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Erreur migration data_size_kb: {e}")
            return False
    
    def _ensure_cache_tables(self):
        """🛡️ Crée les tables de cache ULTRA-LÉGÈRES"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # Table principale simplifiée
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS statistics_cache (
                            id SERIAL PRIMARY KEY,
                            cache_key VARCHAR(200) UNIQUE NOT NULL,
                            data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
                            data_size_kb REAL DEFAULT 0
                        );
                    """)
                    
                    # Table dashboard simplifiée
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS dashboard_stats_lite (
                            id SERIAL PRIMARY KEY,
                            total_users INTEGER DEFAULT 0,
                            total_questions INTEGER DEFAULT 0,
                            questions_today INTEGER DEFAULT 0,
                            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
                            is_current BOOLEAN DEFAULT FALSE,
                            data_size_kb REAL DEFAULT 0
                        );
                    """)
                    
                    # Index minimaux
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_stats_cache_expires ON statistics_cache(expires_at)")
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"❌ Erreur création tables cache: {e}")

    # ==================== MÉTHODES ESSENTIELLES SEULEMENT ====================
    
    def set_cache(self, key: str, data: Any, ttl_hours: int = 1) -> bool:
        """Stocke des données dans le cache - VERSION LÉGÈRE"""
        try:
            json_data = safe_json_dumps(data)
            data_size_kb = len(json_data.encode('utf-8')) / 1024
            
            # Limite simple
            if data_size_kb > 200:  # 200KB max
                logger.warning(f"⚠️ Cache entry trop large ({data_size_kb:.1f}KB) pour {key}")
                return False
            
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statistics_cache (cache_key, data, expires_at, data_size_kb)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (cache_key) 
                        DO UPDATE SET data = EXCLUDED.data, expires_at = EXCLUDED.expires_at, data_size_kb = EXCLUDED.data_size_kb
                    """, (key, json_data, expires_at, data_size_kb))
                    conn.commit()
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur set cache {key}: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Récupère des données depuis le cache - VERSION LÉGÈRE"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT data FROM statistics_cache 
                        WHERE cache_key = %s AND expires_at > NOW()
                    """, (key,))
                    
                    result = cur.fetchone()
                    if result:
                        return {"data": result["data"]}
                    return None
                        
        except Exception as e:
            logger.error(f"❌ Erreur get cache {key}: {e}")
            return None
    
    def invalidate_cache(self, pattern: str = None, key: str = None) -> int:
        """Invalide le cache - VERSION LÉGÈRE"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    if key:
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key = %s", (key,))
                    elif pattern:
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key LIKE %s", (pattern.replace("*", "%"),))
                    else:
                        cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                    
                    deleted_count = cur.rowcount
                    conn.commit()
                    return deleted_count
                    
        except Exception as e:
            logger.error(f"❌ Erreur invalidation cache: {e}")
            return 0

    def set_dashboard_snapshot(self, stats: Dict[str, Any]) -> bool:
        """Stocke un snapshot dashboard ULTRA-LÉGER"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Nettoyer les anciens
                    cur.execute("UPDATE dashboard_stats_lite SET is_current = FALSE")
                    
                    # Insérer le nouveau
                    cur.execute("""
                        INSERT INTO dashboard_stats_lite (
                            total_users, total_questions, questions_today, is_current
                        ) VALUES (%s, %s, %s, TRUE)
                    """, (
                        int(stats.get('total_users', 0)),
                        int(stats.get('total_questions', 0)), 
                        int(stats.get('questions_today', 0))
                    ))
                    
                    conn.commit()
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde dashboard: {e}")
            return False
    
    def get_dashboard_snapshot(self) -> Optional[Dict[str, Any]]:
        """Récupère le snapshot dashboard ULTRA-LÉGER"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM dashboard_stats_lite 
                        WHERE is_current = TRUE
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """)
                    
                    result = cur.fetchone()
                    if result:
                        return dict(result)
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erreur récupération dashboard: {e}")
            return None

    def cleanup_expired_cache(self) -> int:
        """Nettoie le cache expiré - VERSION LÉGÈRE"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                    cleaned = cur.rowcount
                    
                    # Garder seulement le plus récent dashboard
                    cur.execute("""
                        DELETE FROM dashboard_stats_lite 
                        WHERE id NOT IN (
                            SELECT id FROM dashboard_stats_lite 
                            ORDER BY generated_at DESC 
                            LIMIT 1
                        )
                    """)
                    cleaned += cur.rowcount
                    
                    conn.commit()
                    return cleaned
                        
        except Exception as e:
            logger.error(f"❌ Erreur cleanup: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du système de cache - VERSION ULTRA-SÉCURISÉE"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    stats = {}
                    
                    # Cache générique avec gestion d'erreur robuste
                    try:
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                                COALESCE(AVG(data_size_kb), 0) as avg_size_kb
                            FROM statistics_cache
                        """)
                        result = cur.fetchone()
                        if result:
                            stats['general_cache'] = dict(result)
                    except Exception as cache_error:
                        logger.warning(f"⚠️ Stats cache générique: {cache_error}")
                        stats['general_cache'] = {'total': 0, 'valid': 0, 'avg_size_kb': 0, 'note': 'Migration en cours'}
                    
                    # Dashboard snapshots
                    try:
                        cur.execute("SELECT COUNT(*) as total FROM dashboard_stats_lite")
                        result = cur.fetchone()
                        stats['dashboard_snapshots'] = dict(result) if result else {'total': 0}
                    except Exception:
                        stats['dashboard_snapshots'] = {'total': 0, 'note': 'Non disponible'}
                    
                    stats['migration_status'] = {
                        'feedback_columns_migrated': self._migration_feedback_success,
                        'cache_stats_migrated': self._migration_cache_stats_success,
                        'ultra_light_mode': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    stats['last_updated'] = datetime.now().isoformat()
                    return stats
                    
        except Exception as e:
            logger.error(f"❌ Erreur stats cache: {e}")
            return {
                "error": str(e), 
                "ultra_light_mode": True,
                "timestamp": datetime.now().isoformat()
            }

    # ==================== MÉTHODES COMPATIBILITÉ ====================
    
    def set_openai_costs(self, start_date: str, end_date: str, period_type: str, costs_data: Dict[str, Any]) -> bool:
        """Cache les coûts OpenAI - VERSION ULTRA-LÉGÈRE"""
        cache_key = f"openai_costs:{start_date}:{end_date}:{period_type}"
        essential_costs = {
            "total_cost": costs_data.get('total_cost', 0),
            "total_tokens": costs_data.get('total_tokens', 0),
            "period": f"{start_date} to {end_date}"
        }
        return self.set_cache(cache_key, essential_costs, ttl_hours=4)

    def get_openai_costs(self, start_date: str, end_date: str, period_type: str) -> Optional[Dict[str, Any]]:
        """Récupère les coûts OpenAI - VERSION ULTRA-LÉGÈRE"""
        cache_key = f"openai_costs:{start_date}:{end_date}:{period_type}"
        cached_result = self.get_cache(cache_key)
        if cached_result:
            return cached_result.get("data")
        return None

# ==================== SINGLETON GLOBAL ====================

_stats_cache_instance = None

def get_stats_cache() -> StatisticsCache:
    """Récupère l'instance singleton du cache statistiques ULTRA-LÉGER"""
    global _stats_cache_instance
    if _stats_cache_instance is None:
        _stats_cache_instance = StatisticsCache()
    return _stats_cache_instance

# ==================== FONCTIONS UTILITAIRES ====================

def is_cache_available() -> bool:
    """Vérifie si le système de cache est disponible"""
    try:
        cache = get_stats_cache()
        return cache.dsn is not None
    except:
        return False

def force_cache_refresh() -> Dict[str, Any]:
    """Force une actualisation du cache - VERSION LÉGÈRE"""
    try:
        cache = get_stats_cache()
        cleaned = cache.cleanup_expired_cache()
        invalidated = cache.invalidate_cache(pattern="dashboard_*")
        
        return {
            "status": "success",
            "cache_invalidated": invalidated,
            "entries_cleaned": cleaned,
            "ultra_light_mode": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}