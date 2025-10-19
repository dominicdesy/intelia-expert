#!/usr/bin/env python3
"""
Script de nettoyage: Suppression de toutes les questions et conversations
Date: 2025-10-19

ATTENTION: Cette opération est IRRÉVERSIBLE !
"""

import sys
import os

# Ajouter le chemin du backend au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import get_pg_connection
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_all_questions():
    """
    Supprime toutes les conversations et messages de la base de données.
    """
    try:
        with get_pg_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:

                # Comptage AVANT suppression
                cur.execute("SELECT COUNT(*) as count FROM conversations")
                conversations_before = cur.fetchone()["count"]

                cur.execute("SELECT COUNT(*) as count FROM messages")
                messages_before = cur.fetchone()["count"]

                logger.info("=" * 70)
                logger.info("AVANT SUPPRESSION:")
                logger.info(f"  - Conversations: {conversations_before}")
                logger.info(f"  - Messages: {messages_before}")
                logger.info("=" * 70)

                # Confirmation
                print("\n⚠️  ATTENTION: Vous allez supprimer TOUTES les questions et conversations !")
                print(f"   - {conversations_before} conversations")
                print(f"   - {messages_before} messages")

                response = input("\n✋ Êtes-vous sûr de vouloir continuer ? (tapez 'OUI' en majuscules): ")

                if response != "OUI":
                    logger.info("❌ Opération annulée par l'utilisateur")
                    return False

                # Suppression
                logger.info("🗑️  Suppression en cours...")
                cur.execute("TRUNCATE TABLE conversations CASCADE")
                conn.commit()

                # Comptage APRÈS suppression
                cur.execute("SELECT COUNT(*) as count FROM conversations")
                conversations_after = cur.fetchone()["count"]

                cur.execute("SELECT COUNT(*) as count FROM messages")
                messages_after = cur.fetchone()["count"]

                logger.info("=" * 70)
                logger.info("APRÈS SUPPRESSION:")
                logger.info(f"  - Conversations: {conversations_after}")
                logger.info(f"  - Messages: {messages_after}")
                logger.info("=" * 70)

                if conversations_after == 0 and messages_after == 0:
                    logger.info("✅ Nettoyage réussi ! Base de données propre.")
                    return True
                else:
                    logger.error("❌ Erreur: Des données restent après le nettoyage")
                    return False

    except Exception as e:
        logger.error(f"❌ Erreur lors du nettoyage: {e}")
        return False


if __name__ == "__main__":
    logger.info("🧹 Script de nettoyage de la base de données")
    logger.info("🔗 Connexion à DigitalOcean PostgreSQL...")

    success = cleanup_all_questions()

    if success:
        logger.info("🎉 Opération terminée avec succès !")
        sys.exit(0)
    else:
        logger.error("💥 Échec de l'opération")
        sys.exit(1)
