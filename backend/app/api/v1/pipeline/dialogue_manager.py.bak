"""
DialogueManager - Version corrigée avec fallback intelligent + nettoyage temporel robuste
CONSERVE: Structure originale + tous les composants existants
CORRIGE: 
- Logique de clarification trop stricte → fallback intelligent (CONSERVÉ)
- Nettoyage temporel fragile → utilisation des fonctionnalités PostgreSQL natives
- ✅ CORRECTION CRITIQUE: PostgreSQL timestamp format error "invalid input syntax for type timestamp"
"""
import os
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from app.api.v1.pipeline.context_extractor import ContextExtractor
from app.api.v1.pipeline.clarification_manager import ClarificationManager
from app.api.v1.pipeline.postgres_memory import PostgresMemory as ConversationMemory
from app.api.v1.pipeline.rag_engine import RAGEngine
from app.api.v1.utils.config import COMPLETENESS_THRESHOLD
from app.api.v1.utils.response_generator import format_response

# Configuration logging pour debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DialogueManager:
    """
    Simplified orchestration:
      1. Extract context
      2. CORRIGÉ: Fallback intelligent au lieu de clarification systématique
      3. Retrieve & generate answer via RAG
      
    AMÉLIORATIONS APPLIQUÉES:
    - Nettoyage temporel robuste avec PostgreSQL natif
    - Conservation de toute la logique métier originale
    - Gestion d'erreurs améliorée pour le nettoyage
    - ✅ CORRECTION CRITIQUE: Gestion proper des timestamps Unix vs PostgreSQL
    """
    def __init__(self):
        self.extractor = ContextExtractor()
        self.clarifier = ClarificationManager()
        # Use managed Postgres for session memory
        self.memory = ConversationMemory(dsn=os.getenv("DATABASE_URL"))
        self.rag = RAGEngine()
        
        # ✅ CONSERVATION: Démarrage automatique nettoyage (avec améliorations)
        self._start_cleanup_task()

    def handle(self, session_id: str, question: str) -> Dict[str, Any]:
        """
        CORRIGÉ: Orchestration avec fallback intelligent au lieu de clarification systématique
        CONSERVÉ: Toute la logique métier originale
        """
        # 1. CONSERVATION: Load and update context (logique identique)
        context = self.memory.get(session_id) or {}
        extracted, score, missing = self.extractor.extract(question)
        context.update(extracted)
        
        # Logging pour debug (conservé)
        logger.info(f"Question: {question[:50]}...")
        logger.info(f"Score de complétude: {score:.2f}, seuil: {COMPLETENESS_THRESHOLD}")
        logger.info(f"Champs manquants: {missing}")
        logger.info(f"Contexte extrait: {extracted}")

        # 2. ✅ CORRIGÉ: Logique de fallback intelligent (conservée intégralement)
        if score < COMPLETENESS_THRESHOLD:
            logger.info(f"Score {score:.2f} < seuil {COMPLETENESS_THRESHOLD}")
            
            # Si score très bas (< 0.2), vraiment demander clarification
            if score < 0.2:
                logger.info("Score très bas (< 0.2), demande de clarification nécessaire")
                questions = self.clarifier.generate(missing)
                # ✅ AMÉLIORATION: Timestamp ISO 8601 au lieu de Unix pour compatibilité PostgreSQL
                context['last_interaction'] = datetime.utcnow().isoformat()
                self.memory.update(session_id, context)
                return {"type": "clarification", "questions": questions}
            
            # Si score moyen (0.2 à seuil), répondre avec avertissement
            else:
                logger.info(f"Score moyen ({score:.2f}), génération réponse avec avertissement")
                answer_data = self.rag.generate_answer(question, context)
                
                # CONSERVATION: Extraire la réponse du dict (logique identique)
                if isinstance(answer_data, dict):
                    response = format_response(answer_data.get("response", ""))
                    source_info = {
                        "source": answer_data.get("source"),
                        "documents_used": answer_data.get("documents_used", 0),
                        "warning": f"Réponse générale - précisez {', '.join(missing[:2])} pour plus de précision"
                    }
                else:
                    # Fallback si ancien format
                    response = format_response(answer_data)
                    source_info = {"warning": "Réponse générale"}
                
                # ✅ AMÉLIORATION: Timestamps ISO 8601 pour compatibilité PostgreSQL
                context['completed_at'] = datetime.utcnow().isoformat()
                context['last_interaction'] = datetime.utcnow().isoformat()
                self.memory.update(session_id, context)
                
                # CONSERVATION: Retourner info source
                result = {"type": "answer", "response": response}
                result.update(source_info)
                logger.info("Réponse générée avec avertissement")
                return result

        # 3. CONSERVATION: Si score >= seuil, générer réponse complète (logique identique)
        logger.info(f"Score suffisant ({score:.2f}), génération réponse complète")
        answer_data = self.rag.generate_answer(question, context)
        
        # CONSERVATION: Extraire la réponse du dict (logique identique)
        if isinstance(answer_data, dict):
            response = format_response(answer_data.get("response", ""))
            source_info = {
                "source": answer_data.get("source"),
                "documents_used": answer_data.get("documents_used", 0),
                "warning": answer_data.get("warning")
            }
        else:
            # Fallback si ancien format
            response = format_response(answer_data)
            source_info = {}
        
        # ✅ AMÉLIORATION: Timestamps ISO 8601 pour compatibilité PostgreSQL
        context['completed_at'] = datetime.utcnow().isoformat()
        context['last_interaction'] = datetime.utcnow().isoformat()
        self.memory.update(session_id, context)
        
        # CONSERVATION: Retourner info source
        result = {"type": "answer", "response": response}
        result.update(source_info)
        logger.info("Réponse complète générée")
        return result

    # ✅ CONSERVATION: Méthodes de nettoyage avec améliorations
    def _start_cleanup_task(self):
        """
        Démarre le nettoyage en arrière-plan
        CONSERVÉ: Structure originale
        AMÉLIORÉ: Gestion d'erreurs et configuration flexible
        """
        def cleanup_sessions():
            # ✅ AMÉLIORATION: Intervalle configurable
            cleanup_interval = int(os.getenv('CLEANUP_INTERVAL_MINUTES', '30')) * 60
            
            while True:
                try:
                    self._robust_cleanup()
                except Exception as e:
                    logger.error(f"Erreur nettoyage sessions: {e}")
                    # ✅ AMÉLIORATION: Attendre moins longtemps en cas d'erreur
                    time.sleep(min(cleanup_interval, 300))  # Max 5 minutes en cas d'erreur
                    continue
                
                time.sleep(cleanup_interval)
        
        cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
        cleanup_thread.start()
        logger.info(f"✅ Nettoyage sessions activé (intervalle: {os.getenv('CLEANUP_INTERVAL_MINUTES', '30')}min)")

    def _robust_cleanup(self):
        """
        ✅ CORRECTION CRITIQUE: Nettoyage PostgreSQL avec gestion proper des timestamps Unix
        
        PROBLÈME RÉSOLU: "invalid input syntax for type timestamp: '1754682356.620286'"
        CAUSE: Tentative de conversion directe timestamps Unix → PostgreSQL timestamp
        SOLUTION: Utilisation de TO_TIMESTAMP() pour les timestamps Unix + validation regex
        """
        if not self.memory.dsn:
            logger.warning("⚠️ DSN de base non configuré, nettoyage impossible")
            return
        
        try:
            import psycopg2
            
            # ✅ AMÉLIORATION: Configuration flexible des délais
            cleanup_hours = int(os.getenv('SESSION_CLEANUP_HOURS', '2'))
            completed_hours = int(os.getenv('COMPLETED_SESSION_CLEANUP_HOURS', '1'))
            
            with psycopg2.connect(self.memory.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # ✅ CORRECTION CRITIQUE: Requête corrigée pour gérer les deux formats
                    cleanup_query = """
                        DELETE FROM conversation_memory 
                        WHERE 
                            -- ✅ Sessions inactives (format ISO 8601)
                            (context->>'last_interaction' IS NOT NULL 
                             AND context->>'last_interaction' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
                             AND (context->>'last_interaction')::timestamp < (NOW() - INTERVAL %s))
                        OR
                            -- ✅ Sessions inactives (format Unix timestamp avec TO_TIMESTAMP)
                            (context->>'last_interaction' IS NOT NULL 
                             AND context->>'last_interaction' ~ '^[0-9]+\.?[0-9]*$'
                             AND TO_TIMESTAMP((context->>'last_interaction')::double precision) < (NOW() - INTERVAL %s))
                        OR
                            -- ✅ Sessions complétées (format ISO 8601)
                            (context->>'completed_at' IS NOT NULL 
                             AND context->>'completed_at' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
                             AND (context->>'completed_at')::timestamp < (NOW() - INTERVAL %s))
                        OR
                            -- ✅ Sessions complétées (format Unix timestamp avec TO_TIMESTAMP)
                            (context->>'completed_at' IS NOT NULL 
                             AND context->>'completed_at' ~ '^[0-9]+\.?[0-9]*$'
                             AND TO_TIMESTAMP((context->>'completed_at')::double precision) < (NOW() - INTERVAL %s))
                        OR
                            -- ✅ Sessions très anciennes (sécurité)
                            (created_at IS NOT NULL AND created_at < (NOW() - INTERVAL '24 hours'))
                    """
                    
                    # ✅ CORRECTION CRITIQUE: Paramètres avec format INTERVAL correct
                    cur.execute(cleanup_query, (
                        f'{cleanup_hours} hours',         # last_interaction ISO
                        f'{cleanup_hours} hours',         # last_interaction Unix
                        f'{completed_hours} hours',       # completed_at ISO
                        f'{completed_hours} hours'        # completed_at Unix
                    ))
                    
                    deleted = cur.rowcount
                    
                    if deleted > 0:
                        logger.info(f"🧹 Nettoyage PostgreSQL réussi: {deleted} sessions supprimées")
                        
                        # ✅ AMÉLIORATION: Statistiques détaillées
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_remaining,
                                COUNT(CASE WHEN context->>'last_interaction' IS NOT NULL THEN 1 END) as with_interaction,
                                COUNT(CASE WHEN context->>'completed_at' IS NOT NULL THEN 1 END) as completed
                            FROM conversation_memory
                        """)
                        
                        stats = cur.fetchone()
                        if stats:
                            logger.info(f"📊 Sessions restantes: {stats[0]} total, {stats[1]} avec interaction, {stats[2]} complétées")
                    
                    else:
                        logger.debug("🧹 Nettoyage PostgreSQL: aucune session à supprimer")
                    
                    # ✅ AMÉLIORATION: Optimisation de la base (optionnel)
                    if deleted > 100:
                        logger.debug("🔧 Optimisation table après nettoyage important...")
                        try:
                            cur.execute("VACUUM ANALYZE conversation_memory")
                            logger.debug("✅ Optimisation terminée")
                        except Exception as vacuum_error:
                            logger.debug(f"⚠️ Optimisation échouée (non critique): {vacuum_error}")
                        
        except psycopg2.Error as e:
            logger.error(f"❌ Erreur PostgreSQL lors du nettoyage: {e}")
            # ✅ AMÉLIORATION: Fallback vers nettoyage simple
            logger.info("🔄 Tentative fallback vers nettoyage simple...")
            self._simple_cleanup_fallback()
            
        except Exception as e:
            logger.error(f"❌ Erreur inattendue lors du nettoyage robuste: {e}")
            # ✅ NOUVEAU: Fallback ultime
            self._simple_cleanup_fallback()

    def _simple_cleanup_fallback(self):
        """
        ✅ NOUVEAU: Fallback simple qui évite les erreurs de timestamp
        Ne fait que nettoyer les sessions très anciennes via created_at
        """
        try:
            import psycopg2
            
            with psycopg2.connect(self.memory.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # ✅ Nettoyage simple basé uniquement sur created_at (plus sûr)
                    simple_cleanup_query = """
                        DELETE FROM conversation_memory 
                        WHERE created_at < (NOW() - INTERVAL '6 hours')
                    """
                    
                    cur.execute(simple_cleanup_query)
                    deleted = cur.rowcount
                    
                    if deleted > 0:
                        logger.info(f"🧹 Nettoyage simple réussi: {deleted} sessions anciennes supprimées")
                    else:
                        logger.debug("🧹 Nettoyage simple: aucune session ancienne à supprimer")
                        
        except Exception as e:
            logger.warning(f"⚠️ Nettoyage simple échoué: {e}")

    def _manual_cleanup_fallback(self):
        """
        ✅ CONSERVATION: Fallback vers l'ancien système en cas d'erreur
        MAIS DÉSACTIVÉ pour éviter les erreurs de timestamp
        """
        logger.info("⚠️ Fallback manuel désactivé pour éviter les erreurs de timestamp")
        logger.info("🔄 Utilisation du nettoyage simple à la place")
        self._simple_cleanup_fallback()

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        ✅ NOUVELLE FONCTIONNALITÉ: Statistiques de nettoyage pour monitoring
        """
        try:
            import psycopg2
            
            with psycopg2.connect(self.memory.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # Statistiques générales
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_sessions,
                            COUNT(CASE WHEN context->>'last_interaction' IS NOT NULL THEN 1 END) as with_last_interaction,
                            COUNT(CASE WHEN context->>'completed_at' IS NOT NULL THEN 1 END) as completed_sessions,
                            MIN(created_at) as oldest_session,
                            MAX(updated_at) as most_recent_update
                        FROM conversation_memory
                    """)
                    
                    general_stats = cur.fetchone()
                    
                    # Sessions par âge
                    cur.execute("""
                        SELECT 
                            COUNT(CASE WHEN created_at > (NOW() - INTERVAL '1 hour') THEN 1 END) as last_hour,
                            COUNT(CASE WHEN created_at > (NOW() - INTERVAL '1 day') THEN 1 END) as last_day,
                            COUNT(CASE WHEN created_at > (NOW() - INTERVAL '7 days') THEN 1 END) as last_week
                        FROM conversation_memory
                    """)
                    
                    age_stats = cur.fetchone()
                    
                    # ✅ NOUVEAU: Analyser les formats de timestamp
                    cur.execute("""
                        SELECT 
                            COUNT(CASE WHEN context->>'last_interaction' ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T' THEN 1 END) as iso_format,
                            COUNT(CASE WHEN context->>'last_interaction' ~ '^[0-9]+\.?[0-9]*$' THEN 1 END) as unix_format,
                            COUNT(CASE WHEN context->>'last_interaction' IS NOT NULL THEN 1 END) as total_with_timestamp
                        FROM conversation_memory
                    """)
                    
                    timestamp_stats = cur.fetchone()
                    
                    return {
                        "total_sessions": general_stats[0],
                        "with_last_interaction": general_stats[1],
                        "completed_sessions": general_stats[2],
                        "oldest_session": general_stats[3].isoformat() if general_stats[3] else None,
                        "most_recent_update": general_stats[4].isoformat() if general_stats[4] else None,
                        "sessions_last_hour": age_stats[0],
                        "sessions_last_day": age_stats[1],
                        "sessions_last_week": age_stats[2],
                        "timestamp_analysis": {
                            "iso_format_count": timestamp_stats[0],
                            "unix_format_count": timestamp_stats[1],
                            "total_with_timestamp": timestamp_stats[2]
                        },
                        "cleanup_config": {
                            "cleanup_interval_minutes": os.getenv('CLEANUP_INTERVAL_MINUTES', '30'),
                            "session_cleanup_hours": os.getenv('SESSION_CLEANUP_HOURS', '2'),
                            "completed_session_cleanup_hours": os.getenv('COMPLETED_SESSION_CLEANUP_HOURS', '1')
                        },
                        "fixes_applied": {
                            "timestamp_format_handling": "✅ Gestion Unix et ISO 8601",
                            "postgresql_compatibility": "✅ TO_TIMESTAMP() pour Unix",
                            "regex_validation": "✅ Validation format avant conversion",
                            "simple_fallback": "✅ Nettoyage simple en cas d'erreur"
                        }
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erreur récupération statistiques: {e}")
            return {"error": str(e)}

    def force_cleanup(self) -> Dict[str, Any]:
        """
        ✅ NOUVELLE FONCTIONNALITÉ: Nettoyage forcé pour administration
        """
        try:
            logger.info("🧹 Nettoyage forcé demandé...")
            self._robust_cleanup()
            return {
                "status": "success",
                "message": "Nettoyage forcé exécuté",
                "timestamp": datetime.utcnow().isoformat(),
                "fix_applied": "PostgreSQL timestamp format error corrigé"
            }
        except Exception as e:
            logger.error(f"❌ Erreur nettoyage forcé: {e}")
            return {
                "status": "error", 
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def cleanup_old_unix_timestamps(self) -> Dict[str, Any]:
        """
        ✅ NOUVELLE MÉTHODE: Nettoyage spécialisé pour les anciens timestamps Unix
        Utile pour nettoyer les données problématiques
        """
        try:
            import psycopg2
            
            with psycopg2.connect(self.memory.dsn) as conn:
                with conn.cursor() as cur:
                    
                    # Nettoyer les sessions avec timestamps Unix très anciens ou invalides
                    cleanup_query = """
                        DELETE FROM conversation_memory 
                        WHERE 
                            -- Unix timestamps trop anciens (avant 2020)
                            (context->>'last_interaction' ~ '^[0-9]+\.?[0-9]*$'
                             AND (context->>'last_interaction')::double precision < 1577836800)
                        OR
                            -- Unix timestamps trop récents (futur lointain)
                            (context->>'last_interaction' ~ '^[0-9]+\.?[0-9]*$'
                             AND (context->>'last_interaction')::double precision > 2147483647)
                        OR
                            -- Même chose pour completed_at
                            (context->>'completed_at' ~ '^[0-9]+\.?[0-9]*$'
                             AND (context->>'completed_at')::double precision < 1577836800)
                        OR
                            (context->>'completed_at' ~ '^[0-9]+\.?[0-9]*$'
                             AND (context->>'completed_at')::double precision > 2147483647)
                    """
                    
                    cur.execute(cleanup_query)
                    deleted = cur.rowcount
                    
                    return {
                        "status": "success",
                        "deleted_sessions": deleted,
                        "message": f"Nettoyé {deleted} sessions avec timestamps Unix invalides",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erreur nettoyage timestamps Unix: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }