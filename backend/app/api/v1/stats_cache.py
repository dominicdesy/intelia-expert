# app/api/v1/stats_cache.py
# -*- coding: utf-8 -*-
"""
🚀 SYSTÈME DE CACHE STATISTIQUES OPTIMISÉ
Tables de cache SQL + Gestionnaire pour performances ultra-rapides
SAFE: N'interfère pas avec logging.py et billing.py existants
✨ NOUVEAU: Migration automatique des colonnes feedback (Digital Ocean compatible)
🔧 CORRECTIF: Sérialisation JSON sécurisée pour les objets Decimal de PostgreSQL
"""

import json
import logging
import os
import decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# ✅ CORRECTIF CRITIQUE: Converter pour sérialisation JSON sécurisée
def decimal_safe_json_encoder(obj):
    """
    Converter JSON pour gérer les types Decimal de PostgreSQL
    Résout l'erreur: "Object of type Decimal is not JSON serializable"
    """
    if isinstance(obj, decimal.Decimal):
        # Convertir Decimal en float pour JSON
        return float(obj)
    # Pour d'autres types non-sérialisables, lever TypeError
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class StatisticsCache:
    """
    Gestionnaire de cache intelligent pour toutes les statistiques
    - Stockage optimisé en base SQL
    - TTL automatique 
    - Gestion des erreurs et fallbacks
    - Migration automatique des colonnes feedback
    - Sérialisation JSON sécurisée pour les objets Decimal
    """
    
    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL manquant pour le cache statistiques")
        
        # Créer les tables de cache
        self._ensure_cache_tables()
        
        # 🔧 NOUVELLE FONCTIONNALITÉ: Migration automatique feedback
        self._migration_feedback_success = self._ensure_user_questions_feedback_columns()
        
        if self._migration_feedback_success:
            logger.info("✅ Système de cache statistiques initialisé avec support feedback")
        else:
            logger.warning("⚠️ Système de cache initialisé en mode dégradé (pas de feedback)")
    
    def _ensure_user_questions_feedback_columns(self):
        """
        🔧 MIGRATION AUTOMATIQUE: Assure que user_questions_complete a les colonnes feedback.
        Pattern identique à postgres_memory.py - Compatible Digital Ocean App Platform.
        
        S'exécute automatiquement au démarrage de l'application.
        Zero risk: Ne touche à rien si les colonnes existent déjà.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # 🔍 Étape 1: Vérifier si user_questions_complete existe
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'user_questions_complete'
                        )
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        logger.warning("⚠️ Table user_questions_complete n'existe pas - skip migration feedback")
                        return False
                    
                    # 🔍 Étape 2: Vérifier colonnes existantes
                    cur.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'user_questions_complete'
                    """)
                    
                    existing_columns = {row[0] for row in cur.fetchall()}
                    logger.info(f"📋 Colonnes détectées dans user_questions_complete: {sorted(existing_columns)}")
                    
                    # 🔧 Étape 3: Définir colonnes feedback requises
                    feedback_columns = {
                        'feedback': 'INTEGER DEFAULT NULL CONSTRAINT valid_feedback_range CHECK (feedback IN (-1, 0, 1))',
                        'feedback_comment': 'TEXT DEFAULT NULL'
                    }
                    
                    # 🚀 Étape 4: Ajouter colonnes manquantes
                    migrations_applied = []
                    for column_name, column_definition in feedback_columns.items():
                        if column_name not in existing_columns:
                            logger.info(f"🔧 Migration: Ajout colonne {column_name}")
                            
                            try:
                                cur.execute(f"""
                                    ALTER TABLE user_questions_complete 
                                    ADD COLUMN IF NOT EXISTS {column_name} {column_definition}
                                """)
                                migrations_applied.append(column_name)
                                
                            except Exception as col_error:
                                logger.error(f"❌ Erreur ajout colonne {column_name}: {col_error}")
                                # Continue avec les autres colonnes
                    
                    # 📊 Étape 5: Créer index de performance (si feedback ajouté)
                    if 'feedback' in migrations_applied:
                        try:
                            cur.execute("""
                                CREATE INDEX IF NOT EXISTS idx_user_questions_complete_feedback 
                                ON user_questions_complete(feedback) 
                                WHERE feedback IS NOT NULL
                            """)
                            logger.info("📊 Index feedback créé pour performances")
                        except Exception as idx_error:
                            logger.warning(f"⚠️ Index feedback non créé: {idx_error}")
                    
                    # ✅ Commit final
                    conn.commit()
                    
                    if migrations_applied:
                        logger.info(f"✅ Migration feedback terminée avec succès: {migrations_applied}")
                        return True
                    else:
                        logger.info("✅ Colonnes feedback déjà présentes - pas de migration nécessaire")
                        return True
                        
        except Exception as e:
            logger.error(f"❌ Erreur migration feedback colonnes: {e}")
            # 🛡️ IMPORTANT: Ne pas faire échouer l'initialisation
            # L'application peut fonctionner en mode dégradé sans feedback
            return False
    
    def _ensure_cache_tables(self):
        """Crée les tables de cache optimisées avec gestion robuste des erreurs"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # 🏆 CRÉER TOUTES LES TABLES D'ABORD (partie sûre)
                    tables_sql = [
                        """
                        CREATE TABLE IF NOT EXISTS statistics_cache (
                            id SERIAL PRIMARY KEY,
                            cache_key VARCHAR(200) UNIQUE NOT NULL,
                            data JSONB NOT NULL,
                            
                            -- Gestion TTL
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
                            
                            -- Métadonnées pour monitoring
                            source VARCHAR(100) DEFAULT 'computed',
                            update_duration_ms INTEGER DEFAULT 0,
                            update_status VARCHAR(20) DEFAULT 'success',
                            errors JSONB DEFAULT '[]',
                            
                            -- Index pour performance
                            CONSTRAINT valid_cache_key CHECK (cache_key != '')
                        );
                        """,
                        
                        """
                        CREATE TABLE IF NOT EXISTS dashboard_stats_snapshot (
                            id SERIAL PRIMARY KEY,
                            snapshot_type VARCHAR(50) DEFAULT 'hourly',
                            
                            -- KPIs principaux (pré-calculés)
                            total_users INTEGER DEFAULT 0,
                            unique_active_users INTEGER DEFAULT 0,
                            total_questions INTEGER DEFAULT 0,
                            questions_today INTEGER DEFAULT 0,
                            questions_this_week INTEGER DEFAULT 0,
                            questions_this_month INTEGER DEFAULT 0,
                            
                            -- Métriques financières
                            total_revenue DECIMAL(12,2) DEFAULT 0,
                            monthly_revenue DECIMAL(10,2) DEFAULT 0,
                            openai_costs DECIMAL(10,6) DEFAULT 0,
                            
                            -- Performance système
                            avg_response_time DECIMAL(8,3) DEFAULT 0,
                            median_response_time DECIMAL(8,3) DEFAULT 0,
                            error_rate DECIMAL(5,2) DEFAULT 0,
                            system_health VARCHAR(20) DEFAULT 'healthy',
                            
                            -- Distributions (JSON optimisé frontend)
                            source_distribution JSONB DEFAULT '{}',
                            plan_distribution JSONB DEFAULT '{}',
                            feedback_stats JSONB DEFAULT '{}',
                            
                            -- Top utilisateurs (pré-formaté)
                            top_users JSONB DEFAULT '[]',
                            top_inviters JSONB DEFAULT '[]',
                            
                            -- Période couverte
                            period_start TIMESTAMP NOT NULL,
                            period_end TIMESTAMP NOT NULL,
                            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            -- Flag pour savoir quel snapshot utiliser
                            is_current BOOLEAN DEFAULT FALSE,
                            
                            -- Index performance
                            UNIQUE(snapshot_type, period_start, period_end)
                        );
                        """,
                        
                        """
                        CREATE TABLE IF NOT EXISTS questions_cache (
                            id SERIAL PRIMARY KEY,
                            
                            -- Clé de cache basée sur filtres + pagination
                            cache_key VARCHAR(300) UNIQUE NOT NULL,
                            
                            -- Pagination
                            page INTEGER NOT NULL,
                            limit_per_page INTEGER DEFAULT 20,
                            total_questions INTEGER NOT NULL,
                            total_pages INTEGER NOT NULL,
                            
                            -- Données optimisées pour frontend
                            questions_data JSONB NOT NULL,
                            pagination_info JSONB NOT NULL,
                            
                            -- Filtres appliqués (pour invalidation ciblée)
                            filters_applied JSONB DEFAULT '{}',
                            
                            -- TTL plus court pour questions (données plus volatiles)
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '15 minutes'),
                            
                            -- Contraintes
                            CONSTRAINT positive_page CHECK (page > 0),
                            CONSTRAINT positive_limit CHECK (limit_per_page > 0)
                        );
                        """,
                        
                        """
                        CREATE TABLE IF NOT EXISTS openai_costs_cache (
                            id SERIAL PRIMARY KEY,
                            
                            -- Période des coûts
                            start_date DATE NOT NULL,
                            end_date DATE NOT NULL,
                            period_type VARCHAR(20) NOT NULL, -- 'week', 'month', 'custom'
                            
                            -- Coûts calculés
                            total_cost_usd DECIMAL(12,6) DEFAULT 0,
                            total_tokens BIGINT DEFAULT 0,
                            total_api_calls INTEGER DEFAULT 0,
                            
                            -- Breakdown par modèle (JSON)
                            models_usage JSONB DEFAULT '{}',
                            daily_breakdown JSONB DEFAULT '{}',
                            cost_by_purpose JSONB DEFAULT '{}',
                            
                            -- Métadonnées de récupération
                            data_source VARCHAR(50) DEFAULT 'openai_api',
                            api_calls_made INTEGER DEFAULT 0,
                            cached_days INTEGER DEFAULT 0,
                            retrieval_errors JSONB DEFAULT '[]',
                            
                            -- TTL plus long (données coûteuses à récupérer)
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '4 hours'),
                            
                            -- Index
                            UNIQUE(start_date, end_date, period_type)
                        );
                        """,
                        
                        """
                        CREATE TABLE IF NOT EXISTS invitations_cache (
                            id SERIAL PRIMARY KEY,
                            cache_type VARCHAR(50) DEFAULT 'global_stats',
                            
                            -- Stats globales pré-calculées
                            total_invitations_sent INTEGER DEFAULT 0,
                            total_invitations_accepted INTEGER DEFAULT 0,
                            acceptance_rate DECIMAL(5,2) DEFAULT 0,
                            unique_inviters INTEGER DEFAULT 0,
                            
                            -- Top performers (JSON pré-formaté)
                            top_inviters_by_sent JSONB DEFAULT '[]',
                            top_inviters_by_accepted JSONB DEFAULT '[]',
                            recent_activity JSONB DEFAULT '[]',
                            
                            -- Période analysée
                            period_days INTEGER DEFAULT 30,
                            analyzed_until TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            -- Cache metadata
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '2 hours'),
                            
                            UNIQUE(cache_type, period_days)
                        );
                        """,
                        
                        """
                        CREATE TABLE IF NOT EXISTS analytics_cache (
                            id SERIAL PRIMARY KEY,
                            metric_type VARCHAR(100) NOT NULL, -- 'user_analytics', 'server_performance', etc.
                            metric_key VARCHAR(200), -- user_email pour user_analytics, null pour global
                            
                            -- Période couverte
                            period_start TIMESTAMP,
                            period_end TIMESTAMP,
                            period_days INTEGER DEFAULT 30,
                            
                            -- Données calculées
                            computed_data JSONB NOT NULL,
                            
                            -- Métriques de qualité
                            data_completeness DECIMAL(5,2) DEFAULT 100, -- % de données disponibles
                            calculation_errors JSONB DEFAULT '[]',
                            
                            -- Cache TTL
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
                            
                            -- Index composé pour requêtes rapides
                            UNIQUE(metric_type, metric_key, period_start, period_end)
                        );
                        """
                    ]
                    
                    # Exécuter chaque table individuellement pour éviter les rollbacks
                    tables_created = 0
                    for i, table_sql in enumerate(tables_sql):
                        try:
                            cur.execute(table_sql)
                            conn.commit()  # Commit après chaque table
                            tables_created += 1
                        except Exception as table_error:
                            logger.error(f"❌ Erreur création table {i}: {table_error}")
                            conn.rollback()  # Rollback si erreur
                            # Continue avec les autres tables
                    
                    logger.info(f"✅ Tables de cache créées: {tables_created}/{len(tables_sql)}")
                    
        except Exception as e:
            logger.error(f"❌ Erreur générale création tables cache: {e}")
            # Ne pas lever l'exception - continuer le démarrage
            
        # 🔍 CRÉER LES INDEX DANS UNE TRANSACTION SÉPARÉE (pour éviter les échecs)
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Index simples SANS prédicats WHERE problématiques
                    safe_indexes = [
                        "CREATE INDEX IF NOT EXISTS idx_stats_cache_key_expires ON statistics_cache(cache_key, expires_at DESC);",
                        "CREATE INDEX IF NOT EXISTS idx_stats_cache_expires ON statistics_cache(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_stats_cache_source ON statistics_cache(source, created_at DESC);",
                        
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_current ON dashboard_stats_snapshot(is_current, generated_at DESC);",
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_period ON dashboard_stats_snapshot(period_start, period_end);",
                        "CREATE INDEX IF NOT EXISTS idx_dashboard_type ON dashboard_stats_snapshot(snapshot_type, generated_at DESC);",
                        
                        "CREATE INDEX IF NOT EXISTS idx_questions_cache_key ON questions_cache(cache_key, expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_questions_filters ON questions_cache USING GIN(filters_applied);",
                        "CREATE INDEX IF NOT EXISTS idx_questions_page ON questions_cache(page, limit_per_page);",
                        
                        "CREATE INDEX IF NOT EXISTS idx_openai_period ON openai_costs_cache(start_date, end_date, period_type);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_expires ON openai_costs_cache(expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_openai_type ON openai_costs_cache(period_type, start_date DESC);",
                        
                        "CREATE INDEX IF NOT EXISTS idx_invitations_type ON invitations_cache(cache_type, expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_invitations_period ON invitations_cache(period_days, analyzed_until);",
                        
                        "CREATE INDEX IF NOT EXISTS idx_analytics_metric ON analytics_cache(metric_type, metric_key, expires_at);",
                        "CREATE INDEX IF NOT EXISTS idx_analytics_period ON analytics_cache(period_start, period_end);"
                    ]
                    
                    created_indexes = 0
                    for index_sql in safe_indexes:
                        try:
                            cur.execute(index_sql)
                            created_indexes += 1
                        except Exception as idx_error:
                            logger.warning(f"⚠️ Index ignoré: {idx_error}")
                            # Continue sans lever d'exception
                    
                    conn.commit()
                    logger.info(f"✅ Index de performance créés: {created_indexes}/{len(safe_indexes)}")
                    
        except Exception as idx_error:
            logger.warning(f"⚠️ Erreur création index (non-critique): {idx_error}")
            # Ne pas lever d'exception - les tables fonctionnent sans index

    # ==================== MÉTHODES GÉNÉRIQUES (CORRIGÉES POUR DECIMAL) ====================
    
    def set_cache(self, key: str, data: Any, ttl_hours: int = 1, source: str = "computed") -> bool:
        """Stocke des données dans le cache générique - ✅ CORRIGÉ POUR DECIMAL"""
        try:
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO statistics_cache (cache_key, data, expires_at, source, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (cache_key) 
                        DO UPDATE SET 
                            data = EXCLUDED.data,
                            expires_at = EXCLUDED.expires_at,
                            source = EXCLUDED.source,
                            updated_at = CURRENT_TIMESTAMP
                    """, (key, json.dumps(data, default=decimal_safe_json_encoder), expires_at, source))
                    #              ↑↑↑ CORRECTIF APPLIQUÉ ↑↑↑
                    conn.commit()
                    
            logger.info(f"✅ Cache SET: {key} (TTL: {ttl_hours}h)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur set cache {key}: {e}")
            return False
    
    def get_cache(self, key: str, include_expired: bool = False) -> Optional[Dict[str, Any]]:
        """Récupère des données depuis le cache générique"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    if include_expired:
                        cur.execute("""
                            SELECT data, created_at, updated_at, expires_at, source
                            FROM statistics_cache 
                            WHERE cache_key = %s
                        """, (key,))
                    else:
                        # ✅ Utilisation de NOW() au lieu de CURRENT_TIMESTAMP pour cohérence
                        cur.execute("""
                            SELECT data, created_at, updated_at, expires_at, source
                            FROM statistics_cache 
                            WHERE cache_key = %s AND expires_at > NOW()
                        """, (key,))
                    
                    result = cur.fetchone()
                    
                    if result:
                        logger.info(f"📦 Cache HIT: {key}")
                        return {
                            "data": result["data"],
                            "cached_at": result["created_at"].isoformat(),
                            "updated_at": result["updated_at"].isoformat(),
                            "expires_at": result["expires_at"].isoformat(),
                            "source": result["source"],
                            "is_expired": result["expires_at"] <= datetime.now()
                        }
                    else:
                        logger.info(f"🔍 Cache MISS: {key}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Erreur get cache {key}: {e}")
            return None
    
    def invalidate_cache(self, pattern: str = None, key: str = None) -> int:
        """Invalide le cache (par clé exacte ou pattern)"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    if key:
                        # Invalidation par clé exacte
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key = %s", (key,))
                        
                    elif pattern:
                        # Invalidation par pattern (ex: "dashboard_*")
                        cur.execute("DELETE FROM statistics_cache WHERE cache_key LIKE %s", (pattern.replace("*", "%"),))
                    
                    else:
                        # Invalider tout le cache expiré
                        cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                    
                    deleted_count = cur.rowcount
                    conn.commit()
                    
                    logger.info(f"🗑️ Cache invalidé: {deleted_count} entrées supprimées")
                    return deleted_count
                    
        except Exception as e:
            logger.error(f"❌ Erreur invalidation cache: {e}")
            return 0

    # ==================== MÉTHODES SPÉCIALISÉES (CORRIGÉES POUR DECIMAL) ====================
    
    def set_dashboard_snapshot(self, stats: Dict[str, Any], period_hours: int = 24) -> bool:
        """Stocke un snapshot complet du dashboard - ✅ CORRIGÉ POUR DECIMAL"""
        try:
            now = datetime.now()
            period_start = now - timedelta(hours=period_hours)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # Marquer les anciens snapshots comme non-current
                    cur.execute("UPDATE dashboard_stats_snapshot SET is_current = FALSE")
                    
                    # Insérer le nouveau snapshot
                    cur.execute("""
                        INSERT INTO dashboard_stats_snapshot (
                            snapshot_type, total_users, unique_active_users, total_questions,
                            questions_today, questions_this_week, questions_this_month,
                            total_revenue, monthly_revenue, openai_costs, avg_response_time,
                            median_response_time, error_rate, system_health,
                            source_distribution, plan_distribution, feedback_stats,
                            top_users, top_inviters, period_start, period_end,
                            is_current
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    """, (
                        'hourly',
                        stats.get('total_users', 0),
                        stats.get('unique_active_users', 0),
                        stats.get('total_questions', 0),
                        stats.get('questions_today', 0),
                        stats.get('questions_this_week', 0),
                        stats.get('questions_this_month', 0),
                        stats.get('total_revenue', 0),
                        stats.get('monthly_revenue', 0),
                        stats.get('openai_costs', 0),
                        stats.get('avg_response_time', 0),
                        stats.get('median_response_time', 0),
                        stats.get('error_rate', 0),
                        stats.get('system_health', 'healthy'),
                        # ✅ CORRECTIFS APPLIQUÉS: decimal_safe_json_encoder
                        json.dumps(stats.get('source_distribution', {}), default=decimal_safe_json_encoder),
                        json.dumps(stats.get('plan_distribution', {}), default=decimal_safe_json_encoder),
                        json.dumps(stats.get('feedback_stats', {}), default=decimal_safe_json_encoder),
                        json.dumps(stats.get('top_users', []), default=decimal_safe_json_encoder),
                        json.dumps(stats.get('top_inviters', []), default=decimal_safe_json_encoder),
                        period_start,
                        now
                    ))
                    
                    conn.commit()
                    
            logger.info(f"✅ Dashboard snapshot sauvegardé (période: {period_hours}h)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde dashboard snapshot: {e}")
            return False
    
    def get_dashboard_snapshot(self) -> Optional[Dict[str, Any]]:
        """Récupère le snapshot dashboard le plus récent"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM dashboard_stats_snapshot 
                        WHERE is_current = TRUE 
                        ORDER BY generated_at DESC 
                        LIMIT 1
                    """)
                    
                    result = cur.fetchone()
                    
                    if result:
                        snapshot = dict(result)
                        
                        # Parser les JSON fields
                        json_fields = ['source_distribution', 'plan_distribution', 'feedback_stats', 'top_users', 'top_inviters']
                        for field in json_fields:
                            if snapshot.get(field):
                                snapshot[field] = snapshot[field]  # Déjà parsé par RealDictCursor
                        
                        # Convertir timestamps
                        for field in ['period_start', 'period_end', 'generated_at']:
                            if snapshot.get(field):
                                snapshot[field] = snapshot[field].isoformat()
                        
                        logger.info("📊 Dashboard snapshot récupéré")
                        return snapshot
                        
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erreur récupération dashboard snapshot: {e}")
            return None

    def set_openai_costs(self, start_date: str, end_date: str, period_type: str, costs_data: Dict[str, Any]) -> bool:
        """Cache les coûts OpenAI - ✅ CORRIGÉ POUR DECIMAL"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO openai_costs_cache (
                            start_date, end_date, period_type, total_cost_usd, total_tokens,
                            total_api_calls, models_usage, daily_breakdown, cost_by_purpose,
                            data_source, api_calls_made, cached_days, retrieval_errors
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (start_date, end_date, period_type)
                        DO UPDATE SET
                            total_cost_usd = EXCLUDED.total_cost_usd,
                            total_tokens = EXCLUDED.total_tokens,
                            total_api_calls = EXCLUDED.total_api_calls,
                            models_usage = EXCLUDED.models_usage,
                            daily_breakdown = EXCLUDED.daily_breakdown,
                            cost_by_purpose = EXCLUDED.cost_by_purpose,
                            data_source = EXCLUDED.data_source,
                            api_calls_made = EXCLUDED.api_calls_made,
                            cached_days = EXCLUDED.cached_days,
                            retrieval_errors = EXCLUDED.retrieval_errors,
                            created_at = CURRENT_TIMESTAMP,
                            expires_at = CURRENT_TIMESTAMP + INTERVAL '4 hours'
                    """, (
                        start_date, end_date, period_type,
                        costs_data.get('total_cost', 0),
                        costs_data.get('total_tokens', 0),
                        costs_data.get('api_calls', 0),
                        # ✅ CORRECTIFS APPLIQUÉS: decimal_safe_json_encoder
                        json.dumps(costs_data.get('models_usage', {}), default=decimal_safe_json_encoder),
                        json.dumps(costs_data.get('daily_breakdown', {}), default=decimal_safe_json_encoder),
                        json.dumps(costs_data.get('cost_by_purpose', {}), default=decimal_safe_json_encoder),
                        costs_data.get('data_source', 'openai_api'),
                        costs_data.get('api_calls_made', 0),
                        costs_data.get('cached_days', 0),
                        json.dumps(costs_data.get('errors', []), default=decimal_safe_json_encoder)
                    ))
                    conn.commit()
                    
            logger.info(f"💰 Coûts OpenAI cachés: {start_date} - {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur cache coûts OpenAI: {e}")
            return False

    def cleanup_expired_cache(self) -> int:
        """Nettoie automatiquement le cache expiré"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # Nettoyer chaque table de cache
                    tables_cleaned = 0
                    
                    # Cache générique - ✅ Utilisation de NOW()
                    cur.execute("DELETE FROM statistics_cache WHERE expires_at <= NOW()")
                    tables_cleaned += cur.rowcount
                    
                    # Cache questions (TTL court)
                    cur.execute("DELETE FROM questions_cache WHERE expires_at <= NOW()")
                    tables_cleaned += cur.rowcount
                    
                    # Anciens snapshots dashboard (garder seulement les 5 derniers)
                    cur.execute("""
                        DELETE FROM dashboard_stats_snapshot 
                        WHERE id NOT IN (
                            SELECT id FROM dashboard_stats_snapshot 
                            ORDER BY generated_at DESC 
                            LIMIT 5
                        )
                    """)
                    tables_cleaned += cur.rowcount
                    
                    # Coûts OpenAI expirés
                    cur.execute("DELETE FROM openai_costs_cache WHERE expires_at <= NOW()")
                    tables_cleaned += cur.rowcount
                    
                    # Cache invitations
                    cur.execute("DELETE FROM invitations_cache WHERE expires_at <= NOW()")
                    tables_cleaned += cur.rowcount
                    
                    # Analytics détaillés
                    cur.execute("DELETE FROM analytics_cache WHERE expires_at <= NOW()")
                    tables_cleaned += cur.rowcount
                    
                    conn.commit()
                    
                    logger.info(f"🧹 Cache cleanup: {tables_cleaned} entrées supprimées")
                    return tables_cleaned
                    
        except Exception as e:
            logger.error(f"❌ Erreur cleanup cache: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du système de cache pour monitoring"""
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    stats = {}
                    
                    # Cache générique - ✅ Utilisation de NOW()
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                            COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired
                        FROM statistics_cache
                    """)
                    stats['general_cache'] = dict(cur.fetchone() or {})
                    
                    # Dashboard snapshots
                    cur.execute("""
                        SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_current = TRUE) as current
                        FROM dashboard_stats_snapshot
                    """)
                    stats['dashboard_snapshots'] = dict(cur.fetchone() or {})
                    
                    # Questions cache
                    cur.execute("""
                        SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE expires_at > NOW()) as valid
                        FROM questions_cache
                    """)
                    stats['questions_cache'] = dict(cur.fetchone() or {})
                    
                    # OpenAI costs
                    cur.execute("""
                        SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE expires_at > NOW()) as valid
                        FROM openai_costs_cache
                    """)
                    stats['openai_costs'] = dict(cur.fetchone() or {})
                    
                    # Taille totale (approximative)
                    cur.execute("""
                        SELECT 
                            pg_size_pretty(pg_total_relation_size('statistics_cache')) as general_size,
                            pg_size_pretty(pg_total_relation_size('dashboard_stats_snapshot')) as dashboard_size,
                            pg_size_pretty(pg_total_relation_size('questions_cache')) as questions_size
                    """)
                    size_info = cur.fetchone()
                    stats['sizes'] = dict(size_info) if size_info else {}
                    
                    # ✨ NOUVEAU: Statut migration feedback
                    stats['migration_status'] = {
                        'feedback_columns_migrated': self._migration_feedback_success,
                        'decimal_serialization_fixed': True,  # ✅ NOUVEAU FLAG
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    stats['last_updated'] = datetime.now().isoformat()
                    
                    return stats
                    
        except Exception as e:
            logger.error(f"❌ Erreur stats cache: {e}")
            return {"error": str(e)}


# ==================== SINGLETON GLOBAL (CONSERVÉ INTÉGRALEMENT) ====================

_stats_cache_instance = None

def get_stats_cache() -> StatisticsCache:
    """Récupère l'instance singleton du cache statistiques"""
    global _stats_cache_instance
    if _stats_cache_instance is None:
        _stats_cache_instance = StatisticsCache()
    return _stats_cache_instance


# ==================== FONCTIONS UTILITAIRES (CONSERVÉES INTÉGRALEMENT) ====================

def is_cache_available() -> bool:
    """Vérifie si le système de cache est disponible"""
    try:
        cache = get_stats_cache()
        return cache.dsn is not None
    except:
        return False

def force_cache_refresh() -> Dict[str, Any]:
    """Force une actualisation complète du cache (pour admin)"""
    try:
        cache = get_stats_cache()
        
        # Invalider tout le cache
        invalidated = cache.invalidate_cache(pattern="*")
        
        # Nettoyer les données expirées
        cleaned = cache.cleanup_expired_cache()
        
        return {
            "status": "success",
            "cache_invalidated": invalidated,
            "entries_cleaned": cleaned,
            "migration_status": cache._migration_feedback_success,
            "decimal_fix_applied": True,  # ✅ NOUVEAU FLAG
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur force refresh cache: {e}")
        return {"status": "error", "error": str(e)}