"""
Configuration des connexions aux bases de données
=================================================
- PostgreSQL (DigitalOcean): conversations, messages, analytics, billing
- Supabase: auth.users, public.users, invitations
"""

import os
import logging
from typing import Optional
import psycopg2
import psycopg2.pool
from contextlib import contextmanager
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ============================================================================
# POSTGRESQL (DigitalOcean) - Données applicatives
# ============================================================================

_pg_pool: Optional[psycopg2.pool.SimpleConnectionPool] = None


def init_postgresql_pool():
    """Initialise le pool de connexions PostgreSQL"""
    global _pg_pool

    if _pg_pool is not None:
        logger.info("PostgreSQL pool already initialized")
        return _pg_pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    try:
        _pg_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=database_url
        )
        logger.info("✅ PostgreSQL connection pool initialized (2-20 connections)")
        return _pg_pool
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL pool: {e}")
        raise


def get_postgresql_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Retourne le pool PostgreSQL (initialise si nécessaire)"""
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = init_postgresql_pool()
    return _pg_pool


@contextmanager
def get_pg_connection():
    """
    Context manager pour obtenir une connexion PostgreSQL du pool.

    Usage:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM conversations")
    """
    pool = get_postgresql_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
        conn.commit()  # Auto-commit si pas d'erreur
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"PostgreSQL transaction error: {e}")
        raise
    finally:
        if conn:
            pool.putconn(conn)


def close_postgresql_pool():
    """Ferme le pool de connexions PostgreSQL"""
    global _pg_pool
    if _pg_pool:
        _pg_pool.closeall()
        _pg_pool = None
        logger.info("PostgreSQL pool closed")


# ============================================================================
# SUPABASE - Authentification et Profils
# ============================================================================

_supabase_client: Optional[Client] = None


def init_supabase_client() -> Client:
    """Initialise le client Supabase"""
    global _supabase_client

    if _supabase_client is not None:
        logger.info("Supabase client already initialized")
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY")
    )

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_ANON_KEY) environment variables must be set")

    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized")
        return _supabase_client
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise


def get_supabase_client() -> Client:
    """Retourne le client Supabase (initialise si nécessaire)"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = init_supabase_client()
    return _supabase_client


# ============================================================================
# UTILITAIRES
# ============================================================================

def get_user_from_supabase(user_id: str) -> Optional[dict]:
    """
    Récupère les informations utilisateur depuis Supabase.

    Args:
        user_id: UUID de l'utilisateur (auth_user_id)

    Returns:
        dict avec email, first_name, last_name, user_type, plan ou None
    """
    try:
        logger.info(f"🔍 [SUPABASE] Fetching user from Supabase for user_id: {user_id}")
        supabase = get_supabase_client()
        logger.info(f"🔍 [SUPABASE] Supabase client URL: {supabase.supabase_url}")

        # Essayer d'abord par auth_user_id (cas le plus probable)
        response = supabase.table("users").select("*").eq("auth_user_id", user_id).execute()
        logger.info(f"🔍 [SUPABASE] Query by auth_user_id response: {response}")

        # Si aucun résultat, essayer par id (fallback)
        if not response.data or len(response.data) == 0:
            logger.info(f"🔍 [SUPABASE] No user found by auth_user_id, trying by id")
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            logger.info(f"🔍 [SUPABASE] Query by id response: {response}")

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            logger.info(f"✅ [SUPABASE] User data found: {user_data}")
            return user_data
        else:
            logger.warning(f"❌ [SUPABASE] No data found for user_id: {user_id}")
            return None
    except Exception as e:
        logger.error(f"❌ [SUPABASE] Error fetching user from Supabase for {user_id}: {e}")
        logger.error(f"❌ [SUPABASE] Error type: {type(e).__name__}")
        logger.error(f"❌ [SUPABASE] Error details: {str(e)}")
        return None


def verify_user_exists(user_id: str) -> bool:
    """Vérifie si un utilisateur existe dans Supabase"""
    user = get_user_from_supabase(user_id)
    return user is not None


def get_user_conversations_count(user_id: str) -> int:
    """
    Compte le nombre de conversations d'un utilisateur dans PostgreSQL.

    Args:
        user_id: UUID de l'utilisateur

    Returns:
        Nombre de conversations actives
    """
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = %s AND status = 'active'",
                    (user_id,)
                )
                return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Error counting conversations: {e}")
        return 0


# ============================================================================
# HEALTH CHECK
# ============================================================================

def check_databases_health() -> dict:
    """Vérifie la santé des connexions aux bases de données"""
    health = {
        "postgresql": {"status": "unknown", "error": None},
        "supabase": {"status": "unknown", "error": None}
    }

    # Test PostgreSQL
    try:
        with get_pg_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        health["postgresql"]["status"] = "healthy"
    except Exception as e:
        health["postgresql"]["status"] = "unhealthy"
        health["postgresql"]["error"] = str(e)

    # Test Supabase
    try:
        supabase = get_supabase_client()
        # Simple query pour tester la connexion
        supabase.table("users").select("id").limit(1).execute()
        health["supabase"]["status"] = "healthy"
    except Exception as e:
        health["supabase"]["status"] = "unhealthy"
        health["supabase"]["error"] = str(e)

    return health


# ============================================================================
# INITIALISATION AU DÉMARRAGE
# ============================================================================

def init_all_databases():
    """Initialise toutes les connexions aux bases de données"""
    logger.info("🚀 Initializing database connections...")

    try:
        # Initialiser PostgreSQL
        pg_pool = init_postgresql_pool()
        logger.info(f"✅ PostgreSQL pool: {pg_pool.minconn}-{pg_pool.maxconn} connections")

        # Initialiser Supabase
        supabase = init_supabase_client()
        logger.info(f"✅ Supabase client: {supabase.supabase_url}")

        # Health check
        health = check_databases_health()
        logger.info(f"📊 Database health: {health}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize databases: {e}")
        return False


def close_all_databases():
    """Ferme toutes les connexions aux bases de données"""
    logger.info("🔒 Closing database connections...")
    close_postgresql_pool()
    # Supabase n'a pas besoin de fermeture explicite
    logger.info("✅ All database connections closed")


# ============================================================================
# DOCUMENTATION
# ============================================================================

"""
USAGE EXAMPLES:
==============

1. Sauvegarder une conversation (PostgreSQL):
----------------------------------------------
from app.core.database import get_pg_connection
from psycopg2.extras import RealDictCursor

with get_pg_connection() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            '''
            INSERT INTO conversations (session_id, user_id, question, response)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            ''',
            (session_id, user_id, question, response)
        )
        conversation_id = cur.fetchone()['id']


2. Récupérer un utilisateur (Supabase):
---------------------------------------
from app.core.database import get_user_from_supabase

user = get_user_from_supabase(user_id)
if user:
    print(f"User: {user['email']} ({user['first_name']} {user['last_name']})")


3. Query cross-database (User info + Conversations):
---------------------------------------------------
from app.core.database import get_user_from_supabase, get_pg_connection

# 1. Get user from Supabase
user = get_user_from_supabase(user_id)

# 2. Get conversations from PostgreSQL
with get_pg_connection() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        conversations = cur.fetchall()

# 3. Combine data
result = {
    "user": user,
    "conversations": conversations
}


4. Health check:
---------------
from app.core.database import check_databases_health

health = check_databases_health()
print(f"PostgreSQL: {health['postgresql']['status']}")
print(f"Supabase: {health['supabase']['status']}")


5. Initialisation au démarrage de l'app:
----------------------------------------
from app.core.database import init_all_databases, close_all_databases

# Dans main.py ou app startup
@app.on_event("startup")
async def startup_event():
    init_all_databases()

@app.on_event("shutdown")
async def shutdown_event():
    close_all_databases()
"""
