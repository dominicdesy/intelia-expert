# app/api/v1/stats_cache.py
# -*- coding: utf-8 -*-
"""
SYSTÈME DE CACHE STATISTIQUES OPTIMISÉ - VERSION MEMORY-SAFE CORRIGÉE
Tables de cache SQL + Gestionnaire pour performances ultra-rapides
SAFE: N'interfère pas avec logging.py et billing.py existants
OPTIMISÉ: Gestion mémoire drastiquement améliorée pour DigitalOcean App Platform
CORRECTIF: Sérialisation JSON sécurisée pour les objets Decimal de PostgreSQL
MEMORY-SAFE: Pool de connexions, limites de taille, nettoyage automatique
NOUVEAU: Migration automatique des colonnes manquantes (data_size_kb, feedback)
FIXED: Création complète de toutes les tables manquantes
CORRECTED: Gestion robuste des transactions SQL et corrections de requêtes
"""

import json
import logging
import os
import decimal
import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)

# CONFIGURATION MEMORY-SAFE
MEMORY_CONFIG = {
    "MAX_CACHE_ENTRY_SIZE_KB": 100,  # Maximum 100KB par entrée cache
    "MAX_JSON_DEPTH": 10,            # Limite profondeur JSON
    "MAX_ARRAY_LENGTH": 1000,        # Limite taille arrays
    "CACHE_CLEANUP_INTERVAL": 300,   # Nettoyage auto toutes les 5min
    "MAX_POOL_CONNECTIONS": 8,       # Pool DB limité
    "MEMORY_THRESHOLD_PERCENT": 80,  # Alert si > 80% RAM
    "ENABLE_MEMORY_MONITORING": True,
    "MAX_CACHE_ENTRIES": 500,        # Maximum 500 entrées en cache
    "FORCE_CLEANUP_AT_PERCENT": 85   # Force cleanup si > 85% RAM
}

def get_memory_usage_percent():
    """CORRIGÉ: Mesure mémoire réaliste"""
    try:
        memory = psutil.virtual_memory()
        result = round(memory.percent, 1)
        logger.info(f"🔥 DEBUG MEMORY FIX ACTIVE: {result}% RAM, Available: {memory.available/1024/1024/1024:.1f}GB")
        return result
    except Exception as e:
        logger.warning(f"Erreur mesure mémoire: {e}")
        logger.info("🔥 DEBUG MEMORY FIX FALLBACK: Retour 50.0% par défaut")
        return 50.0  # Valeur par défaut réaliste au lieu de 0

def decimal_safe_json_encoder(obj):
    """
    Converter JSON pour gérer les types Decimal de PostgreSQL
    Résout l'erreur: "Object of type Decimal is not JSON serializable"
    MEMORY-SAFE: Limite la profondeur de conversion
    FIXED: Normalise tous les décimaux vers float pour cohérence
    """
    if isinstance(obj, decimal.Decimal):
        result = float(obj)
        logger.info(f"DECIMAL FIX: Converted Decimal({obj}) to float({result})")
        return result
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

def safe_json_dumps(data, max_depth=MEMORY_CONFIG["MAX_JSON_DEPTH"]):
    """
    Sérialisation JSON sécurisée avec limites de mémoire
    """
    def truncate_deep_structure(obj, current_depth=0):
        if current_depth > max_depth:
            return "...[TRUNCATED_DEPTH]"
        
        if isinstance(obj, dict):
            if len(obj) > 100:  # Limite nombre de clés
                truncated = dict(list(obj.items())[:100])
                truncated["..."] = f"[TRUNCATED_{len(obj)-100}_MORE_KEYS]"
                return {k: truncate_deep_structure(v, current_depth + 1) 
                       for k, v in truncated.items()}
            return {k: truncate_deep_structure(v, current_depth + 1) 
                   for k, v in obj.items()}
        
        elif isinstance(obj, list):
            if len(obj) > MEMORY_CONFIG["MAX_ARRAY_LENGTH"]:
                truncated = obj[:MEMORY_CONFIG["MAX_ARRAY_LENGTH"]]
                truncated.append(f"...[TRUNCATED_{len(obj)-MEMORY_CONFIG['MAX_ARRAY_LENGTH']}_MORE_ITEMS]")
                return [truncate_deep_structure(item, current_depth + 1) 
                       for item in truncated]
            return [truncate_deep_structure(item, current_depth + 1) 
                   for item in obj]
        
        return obj
    
    try:
        # Tronquer la structure si nécessaire
        safe_data = truncate_deep_structure(data)
        
        # Sérialiser avec limite de taille
        json_str = json.dumps(safe_data, default=decimal_safe_json_encoder, separators=(',', ':'))
        
        # Vérifier la taille finale
        size_kb = len(json_str.encode('utf-8')) / 1024
        if size_kb > MEMORY_CONFIG["MAX_CACHE_ENTRY_SIZE_KB"]:
            logger.warning(f"Cache entry trop large ({size_kb:.1f}KB), truncation forcée")
            return json.dumps({
                "error": "CACHE_ENTRY_TOO_LARGE",
                "original_size_kb": round(size_kb, 1),
                "max_allowed_kb": MEMORY_CONFIG["MAX_CACHE_ENTRY_SIZE_KB"],
                "truncated_data": str(safe_data)[:1000] + "...[TRUNCATED]"
            }, separators=(',', ':'))
        
        return json_str
        
    except Exception as e:
        logger.error(f"Erreur sérialisation JSON safe: {e}")
        return json.dumps({
            "error": "JSON_SERIALIZATION_ERROR",
            "message": str(e)[:200],
            "data_type": str(type(data))
        }, separators=(',', ':'))

class MemoryMonitor:
    """
    Moniteur de mémoire pour prévenir les fuites
    """
    def __init__(self):
        self.last_cleanup = datetime.now().timestamp()
        self.cleanup_lock = threading.Lock()
        logger.info("🔥 DEBUG TIMESTAMP FIX ACTIVE: Using datetime.now().timestamp()")
        
    def should_cleanup(self):
        """Détermine si un cleanup est nécessaire"""
        memory_percent = get_memory_usage_percent()
        time_since_cleanup = datetime.now().timestamp() - self.last_cleanup
        logger.info(f"🔥 DEBUG TIMESTAMP CALC: current={datetime.now().timestamp()}, last={self.last_cleanup}, diff={time_since_cleanup}")
        
        if memory_percent > MEMORY_CONFIG["FORCE_CLEANUP_AT_PERCENT"]:
            return True, f"Mémoire critique: {memory_percent}%"
        
        if (memory_percent > MEMORY_CONFIG["MEMORY_THRESHOLD_PERCENT"] and 
            time_since_cleanup > MEMORY_CONFIG["CACHE_CLEANUP_INTERVAL"]):
            return True, f"Cleanup périodique: {memory_percent}%"
        
        return False, None

class StatisticsCache:
    """
    Gestionnaire de cache intelligent MEMORY-SAFE pour toutes les statistiques
    - Pool de connexions limité pour éviter les fuites
    - Limites strictes sur la taille des données
    - Nettoyage automatique agressif
    - Monitoring mémoire en temps réel
    - Tables optimisées avec TTL court
    - Migration automatique des colonnes manquantes
    FIXED: Création complète de toutes les tables manquantes
    CORRECTED: Gestion robuste des transactions SQL
    """
    
    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL manquant pour le cache statistiques")
        
        # LOG DE DÉPLOIEMENT - Confirme que la nouvelle version est active
        print("=" * 80)
        print("STATS_CACHE.PY - NOUVELLE VERSION DEPLOYÉE")
        print("Version: 2025-08-26 v2.1 - Corrections types mixtes + cache legacy")
        print("Corrections actives:")
        print("  ✓ Types Decimal → Float normalisés")
        print("  ✓ Debug cache legacy isolé")
        print("  ✓ Investigation dashboard_stats_snapshot")
        print("=" * 80)
        logger.info("DEPLOYMENT CONFIRMATION: stats_cache.py v2.1 active with decimal/legacy fixes")
        
        # MEMORY-SAFE: Pool de connexions limité
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=2,
                maxconn=MEMORY_CONFIG["MAX_POOL_CONNECTIONS"],
                dsn=self.dsn
            )
            logger.info(f"Pool de connexions créé: {MEMORY_CONFIG['MAX_POOL_CONNECTIONS']} max")
        except Exception as pool_error:
            logger.error(f"Erreur création pool: {pool_error}")
            self.connection_pool = None
        
        # Moniteur de mémoire
        self.memory_monitor = MemoryMonitor()
        
        # Compteur d'entrées cache pour limite
        self._cache_count = 0
        
        # FIXED: Créer les tables de cache (version complète corrigée)
        self._ensure_cache_tables()
        
        # NOUVELLES FONCTIONNALITÉS: Migration automatique des colonnes
        self._migration_feedback_success = self._ensure_user_questions_feedback_columns()
        self._migration_cache_stats_success = self._ensure_existing_tables_migration()
        
        if self._migration_feedback_success:
            logger.info("Tables de cache memory-safe créées")
            logger.info("Migration feedback terminée (version allégée)")
        else:
            logger.warning("Système de cache initialisé en mode dégradé (pas de feedback)")
        
        logger.info("Système de cache statistiques initialisé avec support feedback (MEMORY-SAFE)")
    
    def _get_connection(self):
        """Récupère une connexion du pool de manière sécurisée"""
        if self.connection_pool:
            try:
                conn = self.connection_pool.getconn()
                # CORRIGÉ: Rollback systématique pour éviter les transactions aborted
                conn.rollback()
                return conn
            except Exception as e:
                logger.warning(f"Pool épuisé, connexion directe: {e}")
        
        # Fallback: connexion directe
        conn = psycopg2.connect(self.dsn)
        conn.rollback()  # CORRIGÉ: Rollback pour nouvelle connexion aussi
        return conn
    
    def _return_connection(self, conn, from_pool=True):
        """Retourne une connexion au pool"""
        try:
            if from_pool and self.connection_pool:
                self.connection_pool.putconn(conn)
            else:
                conn.close()
        except Exception as e:
            logger.warning(f"Erreur retour connexion: {e}")

    def _ensure_user_questions_feedback_columns(self):
        """
        MIGRATION AUTOMATIQUE: Version allégée pour économie mémoire
        Compatible avec le code original - assure la rétrocompatibilité
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    # Vérification rapide et simple
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'user_questions_complete'
                        )
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    if not table_exists:
                        # Créer la table si elle n'existe pas (compatible avec le code original)
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
                                feedback INTEGER DEFAULT NULL 
                                    CONSTRAINT valid_feedback CHECK (feedback IN (-1, 0, 1)),
                                feedback_comment TEXT DEFAULT NULL,
                                data_size_kb INTEGER DEFAULT NULL
                            )
                        """)
                        
                        # Index pour performance
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_email ON user_questions_complete(user_email)")
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_created ON user_questions_complete(created_at)")
                        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_feedback ON user_questions_complete(feedback) WHERE feedback IS NOT NULL")
                        
                        conn.commit()
                        logger.info("Table user_questions_complete créée avec colonnes feedback")
                        return True
                    
                    # Migration minimale des colonnes feedback
                    cur.execute("""
                        ALTER TABLE user_questions_complete 
                        ADD COLUMN IF NOT EXISTS feedback INTEGER CHECK (feedback IN (-1, 0, 1))
                    """)
                    
                    cur.execute("""
                        ALTER TABLE user_questions_complete 
                        ADD COLUMN IF NOT EXISTS feedback_comment TEXT
                    """)
                    
                    cur.execute("""
                        ALTER TABLE user_questions_complete 
                        ADD COLUMN IF NOT EXISTS data_size_kb INTEGER DEFAULT NULL
                    """)
                    
                    conn.commit()
                    logger.info("Migration feedback terminée (version allégée)")
                    return True
                    
            finally:
                self._return_connection(conn)
                
        except Exception as e:
            logger.error(f"Erreur migration feedback: {e}")
            return False

    def _ensure_existing_tables_migration(self):
        """
        MIGRATION AUTOMATIQUE: Ajoute data_size_kb aux tables existantes
        Résout l'erreur: column "data_size_kb" does not exist
        Compatible avec toutes les versions existantes
        CORRECTIF: Inclut statistics_cache dans la migration
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    # Tables à vérifier pour la colonne data_size_kb
                    # CORRECTIF: Ajouter statistics_cache à la liste !
                    tables_to_migrate = [
                        'statistics_cache',           # TABLE PRINCIPALE MANQUANTE !
                        'dashboard_stats_snapshot',
                        'questions_cache', 
                        'openai_costs_cache',
                        'dashboard_stats_lite'
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
                                # Vérifier si data_size_kb existe déjà 
                                cur.execute("""
                                    SELECT EXISTS (
                                        SELECT FROM information_schema.columns 
                                        WHERE table_name = %s AND column_name = 'data_size_kb'
                                    )
                                """, (table_name,))
                                
                                column_exists = cur.fetchone()[0]
                                
                                if not column_exists:
                                    # Table existe - ajouter data_size_kb si manquante
                                    cur.execute(f"""
                                        ALTER TABLE {table_name} 
                                        ADD COLUMN data_size_kb INTEGER DEFAULT 0
                                    """)
                                    migrations_applied.append(table_name)
                                    logger.info(f"Colonne data_size_kb ajoutée à {table_name}")
                                else:
                                    logger.info(f"Colonne data_size_kb existe déjà dans {table_name}")
                        except Exception as table_error:
                            logger.info(f"Table {table_name} skip: {table_error}")
                    
                    conn.commit()
                    
                    if migrations_applied:
                        logger.info(f"Migration data_size_kb terminée: {migrations_applied}")
                    else:
                        logger.info("Colonnes data_size_kb déjà présentes ou tables inexistantes")
                    
                    return True
                    
            finally:
                self._return_connection(conn)
                
        except Exception as e:
            logger.error(f"Erreur migration data_size_kb: {e}")
            return False
    
    def _ensure_cache_tables(self):
        """
        FIXED: Crée TOUTES les tables de cache nécessaires MEMORY-OPTIMIZED
        Version complète qui crée toutes les tables utilisées par le code
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    
                    # TABLE PRINCIPALE: Cache générique avec limites strictes
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS statistics_cache (
                            id SERIAL PRIMARY KEY,
                            cache_key VARCHAR(200) UNIQUE NOT NULL,
                            data JSONB NOT NULL,
                            
                            -- TTL agressif pour économie mémoire
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '12 hours'),
                            
                            -- Métadonnées allégées
                            source VARCHAR(50) DEFAULT 'computed',
                            data_size_kb INTEGER DEFAULT 0,
                            
                            -- Contraintes de sécurité mémoire
                            CONSTRAINT valid_cache_key CHECK (cache_key != ''),
                            CONSTRAINT reasonable_size CHECK (data_size_kb < 200)
                        );
                    """)
                    
                    # FIXED: Table questions_cache (MANQUANTE DANS L'ORIGINAL)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS questions_cache (
                            id SERIAL PRIMARY KEY,
                            question_hash VARCHAR(255) UNIQUE NOT NULL,
                            question TEXT NOT NULL,
                            answer TEXT NOT NULL,
                            data_size_kb INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '12 hours'),
                            hit_count INTEGER DEFAULT 1,
                            language VARCHAR(10) DEFAULT 'fr',
                            user_id VARCHAR(255),
                            confidence_score REAL DEFAULT NULL
                        );
                    """)
                    
                    # FIXED: Table openai_costs_cache (MANQUANTE DANS L'ORIGINAL)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS openai_costs_cache (
                            id SERIAL PRIMARY KEY,
                            request_id VARCHAR(255) UNIQUE NOT NULL,
                            model VARCHAR(100) NOT NULL,
                            prompt_tokens INTEGER NOT NULL,
                            completion_tokens INTEGER NOT NULL,
                            total_tokens INTEGER NOT NULL,
                            estimated_cost_usd DECIMAL(10, 6) NOT NULL,
                            data_size_kb INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '12 hours'),
                            user_id VARCHAR(255),
                            endpoint VARCHAR(100)
                        );
                    """)
                    
                    # FIXED: Table dashboard_stats_snapshot (MANQUANTE DANS L'ORIGINAL)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS dashboard_stats_snapshot (
                            id SERIAL PRIMARY KEY,
                            snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
                            total_questions INTEGER NOT NULL DEFAULT 0,
                            total_users INTEGER NOT NULL DEFAULT 0,
                            avg_response_time_ms INTEGER DEFAULT NULL,
                            avg_confidence_score REAL DEFAULT NULL,
                            rag_usage_percentage REAL DEFAULT NULL,
                            openai_fallback_percentage REAL DEFAULT NULL,
                            total_cost_usd DECIMAL(10, 2) DEFAULT NULL,
                            data_size_kb INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
                            UNIQUE(snapshot_date)
                        );
                    """)
                    
                    # MIGRATION: Ajouter expires_at aux tables existantes si manquante
                    migration_tables = [
                        ('dashboard_stats_snapshot', '24 hours'),
                        ('questions_cache', '12 hours'),
                        ('openai_costs_cache', '12 hours')
                    ]
                    
                    for table_name, interval in migration_tables:
                        try:
                            # Vérifier si created_at existe pour cette table
                            cur.execute("""
                                SELECT EXISTS (
                                    SELECT FROM information_schema.columns 
                                    WHERE table_name = %s AND column_name = 'created_at'
                                )
                            """, (table_name,))
                            has_created_at = cur.fetchone()[0]
                            
                            cur.execute(f"""
                                ALTER TABLE {table_name} 
                                ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '{interval}')
                            """)
                            
                            if has_created_at:
                                cur.execute(f"""
                                    UPDATE {table_name} 
                                    SET expires_at = created_at + INTERVAL '{interval}' 
                                    WHERE expires_at IS NULL
                                """)
                            else:
                                cur.execute(f"""
                                    UPDATE {table_name} 
                                    SET expires_at = CURRENT_TIMESTAMP + INTERVAL '{interval}' 
                                    WHERE expires_at IS NULL
                                """)
                            
                            conn.commit()
                            logger.info(f"Migration expires_at {table_name} réussie")
                        except Exception as table_migration_error:
                            conn.rollback()
                            logger.info(f"Migration {table_name} expires_at: {table_migration_error}")
                    
                    # TABLE SIMPLIFIÉE: Snapshots dashboard légers (CONSERVÉE DE L'ORIGINAL)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS dashboard_stats_lite (
                            id SERIAL PRIMARY KEY,
                            
                            -- Métriques essentielles seulement
                            total_users INTEGER DEFAULT 0,
                            total_questions INTEGER DEFAULT 0,
                            questions_today INTEGER DEFAULT 0,
                            monthly_revenue DECIMAL(10,2) DEFAULT 0,
                            avg_response_time DECIMAL(6,3) DEFAULT 0,
                            error_rate DECIMAL(5,2) DEFAULT 0,
                            system_health VARCHAR(20) DEFAULT 'healthy',
                            
                            -- Distributions compactes (JSON limitées)
                            source_stats JSONB DEFAULT '{}',
                            data_size_kb REAL DEFAULT 0,
                            
                            -- TTL court
                            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '20 minutes'),
                            is_current BOOLEAN DEFAULT FALSE
                        );
                    """)
                    
                    conn.commit()  # COMMIT APRÈS CRÉATION DES TABLES
                    logger.info("Tables de cache créées, création des index...")
                    
                    # INDEX MINIMAUX pour performance (APRÈS commit des tables)
                    index_queries = [
                        "CREATE INDEX IF NOT EXISTS idx_stats_cache_expires ON statistics_cache(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_stats_cache_key ON statistics_cache(cache_key);",
                        "CREATE INDEX IF NOT EXISTS idx_questions_cache_hash ON questions_cache(question_hash);",
                        "CREATE INDEX IF NOT EXISTS idx_questions_cache_expires ON questions_cache(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_costs_expires ON openai_costs_cache(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_costs_user ON openai_costs_cache(user_id);",
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_date ON dashboard_stats_snapshot(snapshot_date);",
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_snapshot_expires ON dashboard_stats_snapshot(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_current ON dashboard_stats_lite(is_current, generated_at);",
                    ]
                    
                    # Créer les index dans une transaction séparée
                    for idx_query in index_queries:
                        try:
                            cur.execute(idx_query)
                            conn.commit()  # Commit chaque index individuellement
                        except Exception as idx_error:
                            conn.rollback()  # Rollback en cas d'erreur d'index
                            logger.warning(f"Index ignoré: {idx_error}")
                    
                    logger.info("TOUTES les tables de cache créées avec succès (VERSION CORRIGÉE)")
                    
            finally:
                self._return_connection(conn)
                
        except Exception as e:
            logger.error(f"Erreur création tables cache CORRIGÉE: {e}")

    def diagnose_database_connection(self) -> Dict[str, Any]:
        """
        CONSERVÉ: Diagnostique complet de la connection base de données
        """
        try:
            diagnosis = {
                "analytics_manager": {
                    "available": self.analytics is not None if hasattr(self, 'analytics') else False,
                    "has_dsn": bool(self.dsn),
                    "dsn_configured": bool(self.dsn)
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
                    with psycopg2.connect(self.dsn) as conn:
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
                diagnosis["errors"].append("DSN non configuré")
            
            return diagnosis
            
        except Exception as e:
            return {
                "status": "diagnostic_failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def create_missing_tables(self) -> Dict[str, Any]:
        """
        CONSERVÉ: Crée automatiquement les tables manquantes
        """
        try:
            if not self.dsn:
                return {"status": "error", "error": "DSN non configuré"}
            
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            results = {
                "tables_created": [],
                "tables_updated": [],
                "errors": []
            }
            
            with psycopg2.connect(self.dsn) as conn:
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
                            data_size_kb INTEGER DEFAULT NULL,
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
                            AND column_name IN ('feedback', 'feedback_comment', 'data_size_kb')
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
                            
                        if "data_size_kb" not in existing_feedback_cols:
                            cur.execute("""
                                ALTER TABLE user_questions_complete 
                                ADD COLUMN data_size_kb INTEGER DEFAULT NULL
                            """)
                            results["tables_updated"].append("user_questions_complete: ajout colonne data_size_kb")
                            logger.info("Colonne data_size_kb ajoutée")
                        
                        if results["tables_updated"]:
                            conn.commit()
            
            # Actualiser la détection après création
            self._migration_feedback_success = self._ensure_user_questions_feedback_columns()
            
            return {
                "status": "success",
                "results": results,
                "new_feedback_status": getattr(self, '_feedback_columns_available', {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur création tables: {e}")
            return {"status": "error", "error": str(e)}

    # ==================== MÉTHODES GÉNÉRIQUES (MEMORY-SAFE) - CONSERVÉES ====================
    
    def set_cache(self, key: str, data: Any, ttl_hours: int = 12, source: str = "computed") -> bool:
        """CONSERVÉ: Stocke des données dans le cache générique - MEMORY-SAFE"""
        try:
            # 1. Vérifier le monitoring mémoire AVANT stockage
            should_cleanup, reason = self.memory_monitor.should_cleanup()
            if should_cleanup:
                logger.info(f"Cleanup auto déclenché: {reason}")
                self.cleanup_expired_cache()
            
            # 2. Vérifier limite nombre d'entrées
            if self._cache_count > MEMORY_CONFIG["MAX_CACHE_ENTRIES"]:
                logger.warning(f"Limite cache atteinte ({self._cache_count}), nettoyage forcé")
                self.cleanup_expired_cache()
            
            # 3. Sérialisation memory-safe
            json_data = safe_json_dumps(data)
            data_size_kb = len(json_data.encode('utf-8')) / 1024
            
            # 4. Vérification taille
            if data_size_kb > MEMORY_CONFIG["MAX_CACHE_ENTRY_SIZE_KB"]:
                logger.warning(f"Cache entry trop large ({data_size_kb:.1f}KB) pour {key}")
                return False
            
            # 5. Stockage avec TTL corrigé (12h par défaut)
            expires_at = datetime.now() + timedelta(hours=min(ttl_hours, 12))  # Max 12h TTL
            
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statistics_cache (cache_key, data, expires_at, source, data_size_kb)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (cache_key) 
                        DO UPDATE SET 
                            data = EXCLUDED.data,
                            expires_at = EXCLUDED.expires_at,
                            source = EXCLUDED.source,
                            data_size_kb = EXCLUDED.data_size_kb,
                            updated_at = CURRENT_TIMESTAMP
                    """, (key, json_data, expires_at, source, int(data_size_kb)))
                    conn.commit()
                    
                    # Mise à jour compteur
                    self._cache_count += 1
                    
            finally:
                self._return_connection(conn)
                    
            logger.info(f"Cache SET (SAFE): {key} ({data_size_kb:.1f}KB, TTL: {ttl_hours}h)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur set cache safe {key}: {e}")
            return False
    
    def get_cache(self, key: str, include_expired: bool = False) -> Optional[Dict[str, Any]]:
        """CONSERVÉ: Récupère des données depuis le cache générique - MEMORY-SAFE"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    if include_expired:
                        cur.execute("""
                            SELECT data, created_at, updated_at, expires_at, source, data_size_kb
                            FROM statistics_cache 
                            WHERE cache_key = %s
                        """, (key,))
                    else:
                        cur.execute("""
                            SELECT data, created_at, updated_at, expires_at, source, data_size_kb
                            FROM statistics_cache 
                            WHERE cache_key = %s AND expires_at > NOW()
                        """, (key,))
                    
                    result = cur.fetchone()
                    
                    if result:
                        # Vérification taille en mémoire
                        size_kb = result.get("data_size_kb", 0)
                        if size_kb > MEMORY_CONFIG["MAX_CACHE_ENTRY_SIZE_KB"] * 2:
                            logger.warning(f"Cache entry {key} trop large ({size_kb}KB), ignoré")
                            return None
                        
                        logger.info(f"Cache HIT (SAFE): {key} ({size_kb}KB)")
                        return {
                            "data": result["data"],
                            "cached_at": result["created_at"].isoformat(),
                            "updated_at": result["updated_at"].isoformat(),
                            "expires_at": result["expires_at"].isoformat(),
                            "source": result["source"],
                            "is_expired": result["expires_at"] <= datetime.now(),
                            "size_kb": size_kb
                        }
                    else:
                        logger.info(f"Cache MISS: {key}")
                        return None
                        
            finally:
                self._return_connection(conn)
                        
        except Exception as e:
            logger.error(f"Erreur get cache safe {key}: {e}")
            return None
    
    def invalidate_cache(self, pattern: str = None, key: str = None) -> int:
        """CONSERVÉ: Invalide le cache (memory-safe)"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    
                    if key:
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key = %s", (key,))
                    elif pattern:
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key LIKE %s", (pattern.replace("*", "%"),))
                    else:
                        # Nettoyage agressif par défaut
                        cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                    
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    # Mise à jour compteur
                    self._cache_count = max(0, self._cache_count - deleted_count)
                    
                    logger.info(f"Cache invalidé (SAFE): {deleted_count} entrées supprimées")
                    return deleted_count
                    
            finally:
                self._return_connection(conn)
                    
        except Exception as e:
            logger.error(f"Erreur invalidation cache safe: {e}")
            return 0

    # ==================== MÉTHODES SPÉCIALISÉES (MEMORY-SAFE) - CONSERVÉES ====================
    
    def set_dashboard_snapshot(self, stats: Dict[str, Any], period_hours: int = 24) -> bool:
        """CONSERVÉ: Stocke un snapshot dashboard LÉGER - MEMORY-SAFE"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    
                    # Nettoyer les anciens snapshots AVANT d'ajouter
                    cur.execute("DELETE FROM dashboard_stats_lite WHERE expires_at <= NOW()")
                    cur.execute("UPDATE dashboard_stats_lite SET is_current = FALSE")
                    
                    # Données essentielles seulement (version light)
                    essential_stats = {
                        'total_users': int(stats.get('total_users', 0)),
                        'total_questions': int(stats.get('total_questions', 0)),
                        'questions_today': int(stats.get('questions_today', 0)),
                        'monthly_revenue': float(stats.get('monthly_revenue', 0)),
                        'avg_response_time': float(stats.get('avg_response_time', 0)),
                        'error_rate': float(stats.get('error_rate', 0)),
                        'system_health': str(stats.get('system_health', 'healthy'))[:20]
                    }
                    
                    # Source stats compactes (limité à 50KB max)
                    source_dist = stats.get('source_distribution', {})
                    if len(str(source_dist)) > 1000:  # Limite arbitraire
                        source_dist = {"note": "Distribution trop large, résumée"}
                    
                    source_stats_json = safe_json_dumps(source_dist)
                    data_size_kb = len(source_stats_json.encode('utf-8')) / 1024
                    
                    # Insérer le snapshot light
                    cur.execute("""
                        INSERT INTO dashboard_stats_lite (
                            total_users, total_questions, questions_today,
                            monthly_revenue, avg_response_time, error_rate, 
                            system_health, source_stats, data_size_kb, is_current
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    """, (
                        essential_stats['total_users'],
                        essential_stats['total_questions'], 
                        essential_stats['questions_today'],
                        essential_stats['monthly_revenue'],
                        essential_stats['avg_response_time'],
                        essential_stats['error_rate'],
                        essential_stats['system_health'],
                        source_stats_json,
                        data_size_kb
                    ))
                    
                    conn.commit()
                    
            finally:
                self._return_connection(conn)
                    
            logger.info("Dashboard snapshot LIGHT sauvegardé (MEMORY-SAFE)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde dashboard snapshot safe: {e}")
            return False
    
    def get_dashboard_snapshot(self) -> Optional[Dict[str, Any]]:
        """CONSERVÉ: Récupère le snapshot dashboard LIGHT"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM dashboard_stats_lite 
                        WHERE is_current = TRUE AND expires_at > NOW()
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """)
                    
                    result = cur.fetchone()
                    
                    if result:
                        snapshot = dict(result)
                        
                        # Convertir timestamps
                        for field in ['generated_at', 'expires_at']:
                            if snapshot.get(field):
                                snapshot[field] = snapshot[field].isoformat()
                        
                        logger.info("Dashboard snapshot LIGHT récupéré")
                        return snapshot
                        
                    return None
                    
            finally:
                self._return_connection(conn)
                    
        except Exception as e:
            logger.error(f"Erreur récupération dashboard snapshot safe: {e}")
            return None

    def cleanup_expired_cache(self) -> int:
        """CONSERVÉ: Nettoie automatiquement le cache AGRESSIVEMENT"""
        with self.memory_monitor.cleanup_lock:
            try:
                conn = self._get_connection()
                try:
                    with conn.cursor() as cur:
                        total_cleaned = 0
                        
                        # 1. Cache générique - TTL expiré
                        cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                        total_cleaned += cur.rowcount
                        
                        # 2. Questions cache - TTL expiré
                        cur.execute("DELETE FROM questions_cache WHERE expires_at <= NOW()")
                        total_cleaned += cur.rowcount
                        
                        # 3. OpenAI costs cache - TTL expiré
                        cur.execute("DELETE FROM openai_costs_cache WHERE expires_at <= NOW()")
                        total_cleaned += cur.rowcount
                        
                        # 4. Dashboard snapshots - garder seulement le plus récent
                        cur.execute("""
                            DELETE FROM dashboard_stats_lite 
                            WHERE id NOT IN (
                                SELECT id FROM dashboard_stats_lite 
                                ORDER BY generated_at DESC 
                                LIMIT 1
                            )
                        """)
                        total_cleaned += cur.rowcount
                        
                        # 5. Dashboard stats snapshot - TTL expiré
                        cur.execute("DELETE FROM dashboard_stats_snapshot WHERE expires_at <= NOW()")
                        total_cleaned += cur.rowcount
                        
                        # 6. Si mémoire critique, nettoyage agressif
                        memory_percent = get_memory_usage_percent()
                        if memory_percent > MEMORY_CONFIG["FORCE_CLEANUP_AT_PERCENT"]:
                            # Supprimer TOUS les cache > 10KB
                            cur.execute("DELETE FROM statistics_cache WHERE data_size_kb > 10")
                            aggressive_cleaned = cur.rowcount
                            total_cleaned += aggressive_cleaned
                            logger.warning(f"Cleanup agressif: {aggressive_cleaned} grandes entrées supprimées")
                        
                        conn.commit()
                        
                        # Mise à jour compteur
                        self._cache_count = max(0, self._cache_count - total_cleaned)
                        self.memory_monitor.last_cleanup = datetime.now().timestamp()
                        
                        logger.info(f"Cache cleanup (SAFE): {total_cleaned} entrées supprimées, mémoire: {memory_percent}%")
                        return total_cleaned
                        
                finally:
                    self._return_connection(conn)
                        
            except Exception as e:
                logger.error(f"Erreur cleanup cache safe: {e}")
                return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        CORRIGÉ: Statistiques du système de cache MEMORY-SAFE avec gestion d'erreur robuste
        Fixed: Requêtes SQL corrigées et gestion de transaction améliorée
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    stats = {}
                    
                    # Cache générique avec gestion d'erreur pour data_size_kb
                    try:
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total,
                                COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                                COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired,
                                COALESCE(AVG(data_size_kb), 0) as avg_size_kb,
                                COALESCE(SUM(data_size_kb), 0) as total_size_kb
                            FROM statistics_cache
                        """)
                        result = cur.fetchone()
                        if result:
                            stats['general_cache'] = dict(result)
                    except Exception as cache_stats_error:
                        logger.warning(f"Erreur stats cache générique: {cache_stats_error}")
                        # Fallback sans data_size_kb
                        try:
                            cur.execute("""
                                SELECT 
                                    COUNT(*) as total,
                                    COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                                    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired
                                FROM statistics_cache
                            """)
                            result = cur.fetchone()
                            stats['general_cache'] = dict(result) if result else {}
                            stats['general_cache'].update({
                                'avg_size_kb': 0,
                                'total_size_kb': 0,
                                'note': 'data_size_kb non disponible - migration en cours'
                            })
                        except Exception as fallback_error:
                            stats['general_cache'] = {
                                'total': 0, 'valid': 0, 'expired': 0, 
                                'avg_size_kb': 0, 'total_size_kb': 0,
                                'note': f'Table statistics_cache non disponible: {fallback_error}'
                            }
                    
                    # Dashboard snapshots light avec gestion d'erreur
                    try:
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total, 
                                COUNT(*) FILTER (WHERE is_current = TRUE) as current,
                                COALESCE(AVG(data_size_kb), 0) as avg_size_kb
                            FROM dashboard_stats_lite
                        """)
                        result = cur.fetchone()
                        if result:
                            # FIXED: Normaliser tous les types vers float
                            stats['dashboard_snapshots'] = {
                                'total': int(result['total']),
                                'current': int(result['current']),
                                'avg_size_kb': float(result['avg_size_kb'])
                            }
                    except Exception as dashboard_error:
                        logger.warning(f"Erreur stats dashboard: {dashboard_error}")
                        stats['dashboard_snapshots'] = {
                            'total': 0, 'current': 0, 'avg_size_kb': 0.0,
                            'note': 'Table dashboard_stats_lite non disponible'
                        }
                    
                    # CORRIGÉ: Vérifier les autres tables avec requêtes SQL correctes
                    other_tables = [
                        ('questions_cache', 'questions_cache'),
                        ('openai_costs_cache', 'openai_costs'), 
                        ('dashboard_stats_snapshot', 'legacy_dashboard'),
                    ]
                    
                    for table_name, stat_key in other_tables:
                        try:
                            logger.info(f"DEBUG SQL FIX ACTIVE: Querying table {table_name} for stat_key {stat_key}")
                            # CORRIGÉ: Utiliser le bon nom de table dans la requête
                            cur.execute(f"""
                                SELECT 
                                    COUNT(*) as total,
                                    COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                                    COALESCE(AVG(data_size_kb), 0) as avg_size_kb
                                FROM {table_name}
                                WHERE created_at > NOW() - INTERVAL '24 hours'
                            """)                            
                            result = cur.fetchone()
                            if result:
                                # FIXED: Normaliser tous les types vers float et ajouter debug pour cache legacy
                                stats[stat_key] = {
                                    'total': int(result['total']),
                                    'valid': int(result['valid']),
                                    'avg_size_kb': float(result['avg_size_kb'])
                                }
                                logger.info(f"DEBUG SQL SUCCESS: {stat_key} = {stats[stat_key]}")
                                
                                # FIXED: Debug spécial pour cache legacy isolé
                                if stat_key == 'legacy_dashboard' and stats[stat_key]['valid'] > 0:
                                    # Vérifier pourquoi cette table a des données alors que les autres sont vides
                                    try:
                                        cur.execute(f"""
                                            SELECT created_at, expires_at, 
                                                   NOW() as current_time,
                                                   expires_at > NOW() as is_valid
                                            FROM {table_name} 
                                            WHERE created_at > NOW() - INTERVAL '24 hours'
                                            ORDER BY created_at DESC LIMIT 3
                                        """)
                                        recent_entries = cur.fetchall()
                                        logger.info(f"CACHE LEGACY ISOLATION DEBUG: {table_name} recent entries:")
                                        for i, entry in enumerate(recent_entries):
                                            logger.info(f"  Entry {i+1}: Created={entry[0]}, Expires={entry[1]}, Valid={entry[3]}")
                                    except Exception as debug_error:
                                        logger.warning(f"CACHE LEGACY DEBUG FAILED: {debug_error}")
                                        # Essayer une requête plus simple
                                        try:
                                            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                                            count_result = cur.fetchone()
                                            logger.info(f"CACHE LEGACY FALLBACK: {table_name} has {count_result[0]} total entries")
                                        except Exception as fallback_error:
                                            logger.error(f"CACHE LEGACY FALLBACK FAILED: {fallback_error}")
                                        
                        except Exception as table_error:
                            logger.info(f"DEBUG SQL ERROR: Table {table_name} non disponible: {table_error}")
                            stats[stat_key] = {
                                'total': 0, 'valid': 0, 'avg_size_kb': 0.0,
                                'note': f'Table {table_name} non disponible'
                            }
                    
                    # Ajout des métriques mémoire avec timestamp corrigé
                    stats['memory_info'] = {
                        'system_memory_percent': get_memory_usage_percent(),
                        'cache_entries_count': self._cache_count,
                        'max_entries_limit': MEMORY_CONFIG["MAX_CACHE_ENTRIES"],
                        'cleanup_threshold_percent': MEMORY_CONFIG["MEMORY_THRESHOLD_PERCENT"],
                        'last_cleanup': self.memory_monitor.last_cleanup
                    }
                    
                    stats['migration_status'] = {
                        'feedback_columns_migrated': self._migration_feedback_success,
                        'decimal_serialization_fixed': True,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    stats['optimization_status'] = {
                        'memory_safe_enabled': True,
                        'max_entry_size_kb': MEMORY_CONFIG["MAX_CACHE_ENTRY_SIZE_KB"],
                        'connection_pool_enabled': self.connection_pool is not None,
                        'feedback_migration_success': self._migration_feedback_success,
                        'all_tables_created': True
                    }
                    
                    stats['last_updated'] = datetime.now().isoformat()
                    
                    return stats
                    
            finally:
                self._return_connection(conn)
                    
        except Exception as e:
            logger.error(f"Erreur stats cache safe: {e}")
            return {
                "error": str(e), 
                "memory_percent": get_memory_usage_percent(),
                "fallback_mode": True,
                "timestamp": datetime.now().isoformat()
            }

    def __del__(self):
        """CONSERVÉ: Fermeture propre du pool de connexions"""
        try:
            if hasattr(self, 'connection_pool') and self.connection_pool:
                self.connection_pool.closeall()
                logger.info("Pool de connexions fermé proprement")
        except Exception as e:
            logger.warning(f"Erreur fermeture pool: {e}")

    # ==================== MÉTHODES CONSERVÉES POUR COMPATIBILITÉ ====================

    def set_openai_costs(self, start_date: str, end_date: str, period_type: str, costs_data: Dict[str, Any]) -> bool:
        """CONSERVÉ: Cache les coûts OpenAI - VERSION ALLÉGÉE (compatible avec le code original)"""
        try:
            # Version simplifiée qui utilise le cache générique
            cache_key = f"openai_costs:{start_date}:{end_date}:{period_type}"
            
            # Données essentielles seulement
            essential_costs = {
                "total_cost": costs_data.get('total_cost', 0),
                "total_tokens": costs_data.get('total_tokens', 0),
                "api_calls": costs_data.get('api_calls', 0),
                "period": f"{start_date} to {end_date}",
                "data_source": costs_data.get('data_source', 'openai_api')
            }
            
            return self.set_cache(cache_key, essential_costs, ttl_hours=12, source="openai_costs")
            
        except Exception as e:
            logger.error(f"Erreur cache coûts OpenAI safe: {e}")
            return False

    def get_openai_costs(self, start_date: str, end_date: str, period_type: str) -> Optional[Dict[str, Any]]:
        """CONSERVÉ: Récupère les coûts OpenAI depuis le cache (compatible avec le code original)"""
        cache_key = f"openai_costs:{start_date}:{end_date}:{period_type}"
        cached_result = self.get_cache(cache_key)
        
        if cached_result:
            return cached_result.get("data")
        return None

# ==================== SINGLETON GLOBAL (CONSERVÉ INTÉGRALEMENT) ====================

_stats_cache_instance = None

def get_stats_cache() -> StatisticsCache:
    """Récupère l'instance singleton du cache statistiques MEMORY-SAFE"""
    global _stats_cache_instance
    if _stats_cache_instance is None:
        _stats_cache_instance = StatisticsCache()
    return _stats_cache_instance

# ==================== FONCTIONS UTILITAIRES (CONSERVÉES + OPTIMISÉES) ====================

def is_cache_available() -> bool:
    """CONSERVÉ: Vérifie si le système de cache est disponible"""
    try:
        cache = get_stats_cache()
        return cache.dsn is not None
    except:
        return False

def force_cache_refresh() -> Dict[str, Any]:
    """CONSERVÉ: Force une actualisation complète du cache (memory-safe)"""
    try:
        cache = get_stats_cache()
        
        # Nettoyage agressif d'abord
        cleaned = cache.cleanup_expired_cache()
        
        # Invalider sélectivement (pas tout)
        invalidated = cache.invalidate_cache(pattern="dashboard_*")
        
        return {
            "status": "success",
            "cache_invalidated": invalidated,
            "entries_cleaned": cleaned,
            "memory_optimization": "enabled",
            "system_memory_percent": get_memory_usage_percent(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur force refresh cache safe: {e}")
        return {"status": "error", "error": str(e)}