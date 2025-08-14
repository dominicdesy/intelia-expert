import json
import math
import os
import psycopg2
import asyncpg
import asyncio
import logging
from typing import Dict, Any, Optional

def sanitize_for_json(obj):
    """
    Nettoie récursivement un objet pour la sérialisation JSON
    Remplace NaN, Infinity par None tout en préservant les vraies valeurs
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None  # Convertir NaN/inf en None (valide JSON)
        return obj
    elif str(obj) in ['NaN', 'nan', 'inf', '-inf', 'Infinity', '-Infinity']:
        return None
    else:
        return obj

class PostgresMemory:
    """
    Conversation memory backend using a managed PostgreSQL instance.
    Ensures correct decoding of JSON and always closes connections.
    Includes automatic table creation/migration.
    
    ✨ NOUVEAUTÉ: Support pour opérations asynchrones pour optimiser les performances.
    Méthodes sync préservées pour compatibilité totale.
    """
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.logger = logging.getLogger(__name__)
        # Pool de connexions async pour de meilleures performances
        self._async_pool = None
        # Cache local pour éviter les reconnexions
        self._pool_initialized = False
        # Automatically ensure table exists on initialization
        self._ensure_table_exists()

    # ====================================================================
    # GESTION DU POOL ASYNC (NOUVEAU)
    # ====================================================================
    
    async def _get_async_pool(self):
        """
        Initialise et retourne le pool de connexions asyncpg.
        Lazy loading pour éviter les problèmes d'initialisation.
        """
        if not self._pool_initialized:
            try:
                # Conversion DSN de psycopg2 vers asyncpg si nécessaire
                dsn = self.dsn
                if dsn.startswith('postgres://'):
                    dsn = dsn.replace('postgres://', 'postgresql://', 1)
                
                self._async_pool = await asyncpg.create_pool(
                    dsn,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                self._pool_initialized = True
                self.logger.info("✅ Pool de connexions async initialisé")
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de l'initialisation du pool async: {e}")
                raise
        
        return self._async_pool

    async def close_async_pool(self):
        """
        Ferme proprement le pool de connexions async.
        À appeler lors de l'arrêt de l'application.
        """
        if self._async_pool:
            await self._async_pool.close()
            self._pool_initialized = False
            self.logger.info("🔒 Pool de connexions async fermé")

    # ====================================================================
    # MÉTHODES SYNCHRONES ORIGINALES (PRÉSERVÉES)
    # ====================================================================

    def _ensure_table_exists(self):
        """
        Vérifie si la table conversation_memory existe et la crée si nécessaire.
        Cette méthode est appelée automatiquement lors de l'initialisation.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Vérifier si la table existe
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'conversation_memory'
                        );
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        self.logger.info("🔧 Table conversation_memory n'existe pas, création en cours...")
                        
                        # Créer la table avec tous les paramètres optimaux
                        cur.execute("""
                            CREATE TABLE conversation_memory (
                                session_id VARCHAR(128) PRIMARY KEY,
                                user_id VARCHAR(128),
                                context JSONB NOT NULL DEFAULT '{}',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            );
                        """)
                        
                        # Créer les index optimisés selon le plan de performance
                        cur.execute("""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversation_memory_user_session 
                            ON conversation_memory(user_id, session_id);
                        """)
                        
                        cur.execute("""
                            CREATE INDEX idx_conversation_memory_updated_at 
                            ON conversation_memory(updated_at);
                        """)
                        
                        # Trigger pour mettre à jour updated_at automatiquement
                        cur.execute("""
                            CREATE OR REPLACE FUNCTION update_updated_at_column()
                            RETURNS TRIGGER AS $$
                            BEGIN
                                NEW.updated_at = CURRENT_TIMESTAMP;
                                RETURN NEW;
                            END;
                            $$ language 'plpgsql';
                        """)
                        
                        cur.execute("""
                            CREATE TRIGGER update_conversation_memory_updated_at 
                            BEFORE UPDATE ON conversation_memory 
                            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                        """)
                        
                        conn.commit()
                        self.logger.info("✅ Table conversation_memory créée avec succès avec indexes et triggers")
                        
                    else:
                        self.logger.info("✅ Table conversation_memory existe déjà")
                        
                        # Optionnel : vérifier que toutes les colonnes existent et les ajouter si nécessaire
                        self._check_and_add_missing_columns(cur, conn)
                        
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la vérification/création de la table: {e}")
            raise

    def _check_and_add_missing_columns(self, cur, conn):
        """
        Vérifie si les colonnes optionnelles existent et les ajoute si nécessaire.
        Migration progressive pour compatibilité avec des tables existantes.
        """
        try:
            # Vérifier les colonnes existantes
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'conversation_memory'
            """)
            
            existing_columns = {row[0] for row in cur.fetchall()}
            
            # Colonnes requises avec leurs définitions
            required_columns = {
                'user_id': 'VARCHAR(128)',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            # Ajouter les colonnes manquantes
            for column_name, column_def in required_columns.items():
                if column_name not in existing_columns:
                    self.logger.info(f"🔧 Ajout de la colonne manquante: {column_name}")
                    cur.execute(f"ALTER TABLE conversation_memory ADD COLUMN {column_name} {column_def}")
                    
            # Vérifier le type de la colonne context
            cur.execute("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'conversation_memory' AND column_name = 'context'
            """)
            
            context_type = cur.fetchone()
            if context_type and context_type[0] not in ['jsonb', 'json']:
                self.logger.warning("⚠️ La colonne 'context' n'est pas de type JSON/JSONB, conversion recommandée")
            
            conn.commit()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la vérification des colonnes: {e}")

    def get(self, session_id):
        """
        Get the context dict for a session_id. Always returns a dict.
        Improved with better error handling and JSONB support.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT context FROM conversation_memory WHERE session_id=%s", (session_id,))
                    row = cur.fetchone()
                    
                    if not row or not row[0]:
                        return {}
                    
                    val = row[0]
                    
                    # Si c'est déjà un dict (JSONB natif), le retourner directement
                    if isinstance(val, dict):
                        return val
                    
                    # Sinon, essayer de parser le JSON
                    try:
                        return json.loads(val) if val else {}
                    except (json.JSONDecodeError, TypeError) as e:
                        self.logger.warning(f"⚠️ Erreur de parsing JSON pour session {session_id}: {e}")
                        return {}
                        
        except psycopg2.Error as e:
            self.logger.error(f"❌ Erreur PostgreSQL lors de la récupération de session {session_id}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"❌ Erreur inattendue lors de la récupération de session {session_id}: {e}")
            return {}

    def update(self, session_id, context: dict, user_id: str = None):
        """
        Upsert the context dict for a session_id.
        Improved with better error handling and JSONB support.
        CORRIGÉ: Nettoie les valeurs NaN avant sérialisation JSON.
        """
        try:
            # ✅ NOUVEAU: Nettoyer le contexte avant sérialisation
            clean_context = sanitize_for_json(context)
            
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    # Essayer d'abord avec JSONB natif
                    try:
                        if user_id:
                            cur.execute("""
                                INSERT INTO conversation_memory (session_id, user_id, context)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (session_id) DO UPDATE SET 
                                    context = EXCLUDED.context,
                                    user_id = EXCLUDED.user_id
                            """, (session_id, user_id, json.dumps(clean_context)))
                        else:
                            cur.execute("""
                                INSERT INTO conversation_memory (session_id, context)
                                VALUES (%s, %s)
                                ON CONFLICT (session_id) DO UPDATE SET context = EXCLUDED.context
                            """, (session_id, json.dumps(clean_context)))
                        
                    except psycopg2.Error as e:
                        # Fallback en cas d'erreur avec JSONB
                        self.logger.warning(f"⚠️ Fallback vers JSON string pour session {session_id}: {e}")
                        ctx_json = json.dumps(clean_context)
                        cur.execute("""
                            INSERT INTO conversation_memory (session_id, context)
                            VALUES (%s, %s)
                            ON CONFLICT (session_id) DO UPDATE SET context = EXCLUDED.context
                        """, (session_id, ctx_json))
                    
                    conn.commit()
                    self.logger.debug(f"✅ Contexte mis à jour pour session {session_id}")
                    
        except psycopg2.Error as e:
            self.logger.error(f"❌ Erreur PostgreSQL lors de la mise à jour de session {session_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Erreur inattendue lors de la mise à jour de session {session_id}: {e}")
            raise

    def clear(self, session_id):
        """
        Delete the context for a session_id.
        Improved with better error handling.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM conversation_memory WHERE session_id=%s", (session_id,))
                    rows_affected = cur.rowcount
                    conn.commit()
                    
                    if rows_affected > 0:
                        self.logger.debug(f"✅ Session {session_id} supprimée")
                    else:
                        self.logger.debug(f"ℹ️ Session {session_id} n'existait pas")
                        
        except psycopg2.Error as e:
            self.logger.error(f"❌ Erreur PostgreSQL lors de la suppression de session {session_id}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Erreur inattendue lors de la suppression de session {session_id}: {e}")
            raise

    # ====================================================================
    # NOUVELLES MÉTHODES ASYNCHRONES (OPTIMISATION PERFORMANCE)
    # ====================================================================

    async def get_async(self, session_id: str) -> Dict[str, Any]:
        """
        🚀 Version async de get() pour optimisation de performance.
        Utilise le pool de connexions pour éviter la latence de connexion.
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT context FROM conversation_memory WHERE session_id = $1", 
                    session_id
                )
                
                if not row or not row['context']:
                    return {}
                
                val = row['context']
                
                # Si c'est déjà un dict (JSONB natif), le retourner directement
                if isinstance(val, dict):
                    return val
                
                # Sinon, essayer de parser le JSON
                try:
                    return json.loads(val) if val else {}
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(f"⚠️ Erreur de parsing JSON pour session {session_id}: {e}")
                    return {}
                    
        except Exception as e:
            self.logger.error(f"❌ Erreur async lors de la récupération de session {session_id}: {e}")
            return {}

    async def update_async(self, session_id: str, context: dict, user_id: str = None):
        """
        🚀 Version async de update() pour optimisation de performance.
        Gain estimé: 1-2s selon le plan d'optimisation.
        """
        try:
            # Nettoyer le contexte avant sérialisation
            clean_context = sanitize_for_json(context)
            
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                if user_id:
                    await conn.execute("""
                        INSERT INTO conversation_memory (session_id, user_id, context)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (session_id) DO UPDATE SET 
                            context = EXCLUDED.context,
                            user_id = EXCLUDED.user_id
                    """, session_id, user_id, json.dumps(clean_context))
                else:
                    await conn.execute("""
                        INSERT INTO conversation_memory (session_id, context)
                        VALUES ($1, $2)
                        ON CONFLICT (session_id) DO UPDATE SET context = EXCLUDED.context
                    """, session_id, json.dumps(clean_context))
                
                self.logger.debug(f"✅ Contexte mis à jour (async) pour session {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur async lors de la mise à jour de session {session_id}: {e}")
            raise

    async def clear_async(self, session_id: str):
        """
        🚀 Version async de clear() pour optimisation de performance.
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM conversation_memory WHERE session_id = $1", 
                    session_id
                )
                
                # Extraire le nombre de lignes affectées du résultat
                rows_affected = int(result.split()[-1]) if result else 0
                
                if rows_affected > 0:
                    self.logger.debug(f"✅ Session {session_id} supprimée (async)")
                else:
                    self.logger.debug(f"ℹ️ Session {session_id} n'existait pas (async)")
                    
        except Exception as e:
            self.logger.error(f"❌ Erreur async lors de la suppression de session {session_id}: {e}")
            raise

    async def save_context_async(self, session_id: str, inputs: dict, outputs: dict, user_id: str = None):
        """
        🚀 NOUVELLE MÉTHODE: save_context_async() requise par expert.py
        Utilisée dans asyncio.gather() pour paralléliser les opérations DB.
        """
        try:
            # Récupérer le contexte existant
            current_context = await self.get_async(session_id)
            
            # Ajouter les nouveaux inputs/outputs
            if 'history' not in current_context:
                current_context['history'] = []
            
            current_context['history'].append({
                'inputs': inputs,
                'outputs': outputs,
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Limiter l'historique pour éviter la croissance infinie
            if len(current_context['history']) > 50:
                current_context['history'] = current_context['history'][-50:]
            
            # Sauvegarder le contexte mis à jour
            await self.update_async(session_id, current_context, user_id)
            
            self.logger.debug(f"✅ Contexte sauvegardé (async) pour session {session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la sauvegarde async du contexte {session_id}: {e}")
            raise

    async def persist_conversation_async(self, session_id: str, conversation_data: dict):
        """
        🚀 NOUVELLE MÉTHODE: persist_conversation_async() pour persistance optimisée.
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                # Nettoyer les données de conversation
                clean_data = sanitize_for_json(conversation_data)
                
                await conn.execute("""
                    INSERT INTO conversation_memory (session_id, context)
                    VALUES ($1, $2)
                    ON CONFLICT (session_id) DO UPDATE SET 
                        context = conversation_memory.context || EXCLUDED.context
                """, session_id, json.dumps(clean_data))
                
                self.logger.debug(f"✅ Conversation persistée (async) pour session {session_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la persistance async de conversation {session_id}: {e}")
            raise

    # ====================================================================
    # MÉTHODES UTILITAIRES (PRÉSERVÉES ET AMÉLIORÉES)
    # ====================================================================

    def cleanup_old_sessions(self, days_old=7):
        """
        Supprime les sessions plus anciennes que X jours.
        Méthode utilitaire pour éviter l'accumulation de données.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM conversation_memory 
                        WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    """, (days_old,))
                    
                    rows_deleted = cur.rowcount
                    conn.commit()
                    
                    if rows_deleted > 0:
                        self.logger.info(f"🧹 Nettoyage: {rows_deleted} sessions anciennes supprimées")
                    
                    return rows_deleted
                    
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du nettoyage des anciennes sessions: {e}")
            return 0

    async def cleanup_old_sessions_async(self, days_old=7):
        """
        🚀 Version async du nettoyage pour les tâches de maintenance.
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM conversation_memory 
                    WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, days_old)
                
                # Extraire le nombre de lignes supprimées
                rows_deleted = int(result.split()[-1]) if result else 0
                
                if rows_deleted > 0:
                    self.logger.info(f"🧹 Nettoyage async: {rows_deleted} sessions anciennes supprimées")
                
                return rows_deleted
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du nettoyage async des anciennes sessions: {e}")
            return 0

    def get_stats(self):
        """
        Retourne des statistiques sur l'utilisation de la mémoire.
        Utile pour le monitoring.
        """
        try:
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_sessions,
                            COUNT(CASE WHEN updated_at > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 1 END) as active_last_hour,
                            COUNT(CASE WHEN updated_at > CURRENT_TIMESTAMP - INTERVAL '1 day' THEN 1 END) as active_last_day,
                            MIN(created_at) as oldest_session,
                            MAX(updated_at) as most_recent_activity
                        FROM conversation_memory
                    """)
                    
                    row = cur.fetchone()
                    if row:
                        return {
                            "total_sessions": row[0],
                            "active_last_hour": row[1],
                            "active_last_day": row[2],
                            "oldest_session": row[3].isoformat() if row[3] else None,
                            "most_recent_activity": row[4].isoformat() if row[4] else None
                        }
                    
                    return {"total_sessions": 0}
                    
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la récupération des statistiques: {e}")
            return {"error": str(e)}

    async def get_stats_async(self):
        """
        🚀 Version async des statistiques pour les dashboards en temps réel.
        """
        try:
            pool = await self._get_async_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        COUNT(CASE WHEN updated_at > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 1 END) as active_last_hour,
                        COUNT(CASE WHEN updated_at > CURRENT_TIMESTAMP - INTERVAL '1 day' THEN 1 END) as active_last_day,
                        MIN(created_at) as oldest_session,
                        MAX(updated_at) as most_recent_activity
                    FROM conversation_memory
                """)
                
                if row:
                    return {
                        "total_sessions": row['total_sessions'],
                        "active_last_hour": row['active_last_hour'],
                        "active_last_day": row['active_last_day'],
                        "oldest_session": row['oldest_session'].isoformat() if row['oldest_session'] else None,
                        "most_recent_activity": row['most_recent_activity'].isoformat() if row['most_recent_activity'] else None
                    }
                
                return {"total_sessions": 0}
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la récupération async des statistiques: {e}")
            return {"error": str(e)}

    # ====================================================================
    # MÉTHODES DE FERMETURE PROPRE
    # ====================================================================

    def __del__(self):
        """
        Fermeture propre du pool async lors de la destruction de l'objet.
        """
        if self._async_pool and not self._async_pool.is_closed():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close_async_pool())
            except:
                pass  # Ignore si pas de loop disponible