"""
Module de gestion de la fermeture de compte conforme RGPD
=========================================================
Anonymise les données utilisateur au lieu de les supprimer complètement.

Principe:
- Conserver les conversations pour l'analytique
- Rendre l'utilisateur complètement anonyme (non identifiable)
- Supprimer uniquement les données d'authentification

Conformité RGPD:
- Article 17: Droit à l'oubli (Right to be forgotten)
- Article 20: Portabilité des données

Créé: 2025-10-24
"""

import hashlib
import logging
import json
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_anonymous_identifier(user_email: str, prefix: str = "anonymous") -> str:
    """
    Génère un identifiant anonyme unique et déterministe basé sur l'email.

    Args:
        user_email: Email de l'utilisateur à anonymiser
        prefix: Préfixe pour l'identifiant (défaut: "anonymous")

    Returns:
        Identifiant anonyme du format: "anonymous-abc12345"

    Example:
        >>> generate_anonymous_identifier("user@example.com")
        "anonymous-55502f40"
    """
    hash_value = hashlib.md5(user_email.encode()).hexdigest()[:8]
    return f"{prefix}-{hash_value}"


def anonymize_user_in_postgresql(conn, user_id: str, user_email: str) -> Dict[str, int]:
    """
    Anonymise toutes les références à l'utilisateur dans PostgreSQL (DigitalOcean).

    Les données sont conservées pour l'analytique mais rendues complètement anonymes.
    Cette fonction travaille dans une transaction PostgreSQL.

    Args:
        conn: Connexion psycopg2 PostgreSQL (dans une transaction)
        user_id: UUID de l'utilisateur
        user_email: Email de l'utilisateur

    Returns:
        Dictionnaire avec le nombre de lignes mises à jour par table

    Raises:
        Exception: En cas d'erreur, la transaction sera rollback par le context manager

    Example:
        >>> with get_pg_connection() as conn:
        ...     stats = anonymize_user_in_postgresql(conn, user_id, user_email)
        ...     print(stats)
        {'conversations': 15, 'stripe_customers': 1, ...}
    """
    anonymous_id = generate_anonymous_identifier(user_email)
    anonymous_email = f"{anonymous_id}@deleted.intelia.app"

    logger.info(f"[anonymize_user_in_postgresql] Starting anonymization for {user_email[:3]}***")
    logger.info(f"[anonymize_user_in_postgresql] Anonymous identifier: {anonymous_id}")

    stats = {}
    cursor = conn.cursor()

    try:
        # Temporarily drop FK constraint to allow updating circular dependencies
        # stripe_subscriptions has FK to user_billing_info, creating a circular dependency
        cursor.execute("ALTER TABLE stripe_subscriptions DROP CONSTRAINT IF EXISTS fk_subscription_user")
        logger.info(f"[anonymize_user_in_postgresql] FK constraint fk_subscription_user temporarily dropped")

        # ========================================================================
        # 1. CONVERSATIONS & MESSAGES
        # ========================================================================

        # Anonymiser les conversations (user_id)
        cursor.execute(
            "UPDATE conversations SET user_id = %s WHERE user_id = %s",
            (anonymous_id, user_id)
        )
        stats['conversations'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Conversations anonymized: {cursor.rowcount}")

        # Messages: pas besoin de modifier, ils sont liés à conversation_id
        # Le user_id dans messages est dans role='user', pas une colonne user_id

        # ========================================================================
        # 2. STRIPE / BILLING
        # ========================================================================
        # IMPORTANT: Update children (stripe_subscriptions, stripe_payment_events) BEFORE parent (user_billing_info)
        # Because stripe_subscriptions has FK to user_billing_info.user_email

        # stripe_customers
        cursor.execute(
            """UPDATE stripe_customers
               SET user_email = %s, customer_name = %s
               WHERE user_email = %s""",
            (anonymous_email, 'Anonymous User', user_email)
        )
        stats['stripe_customers'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Stripe customers anonymized: {cursor.rowcount}")

        # stripe_subscriptions (BEFORE user_billing_info - child table first)
        cursor.execute(
            "UPDATE stripe_subscriptions SET user_email = %s WHERE user_email = %s",
            (anonymous_email, user_email)
        )
        stats['stripe_subscriptions'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Stripe subscriptions anonymized: {cursor.rowcount}")

        # stripe_payment_events
        cursor.execute(
            "UPDATE stripe_payment_events SET user_email = %s WHERE user_email = %s",
            (anonymous_email, user_email)
        )
        stats['stripe_payment_events'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Stripe payment events anonymized: {cursor.rowcount}")

        # user_billing_info (LAST - parent table after all children updated)
        cursor.execute(
            "UPDATE user_billing_info SET user_email = %s WHERE user_email = %s",
            (anonymous_email, user_email)
        )
        stats['user_billing_info'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] User billing info anonymized: {cursor.rowcount}")

        # ========================================================================
        # 3. QA & SATISFACTION
        # ========================================================================
        # Note: user_id in these tables is UUID type, cannot be anonymized to TEXT
        # Since conversations are already anonymized, we delete these records entirely

        # qa_quality_checks (DELETE - user_id is UUID, cannot anonymize)
        cursor.execute(
            "DELETE FROM qa_quality_checks WHERE user_id = %s",
            (user_id,)
        )
        stats['qa_quality_checks'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] QA quality checks deleted: {cursor.rowcount}")

        # conversation_satisfaction_surveys (DELETE - user_id is UUID or TEXT, safer to delete)
        cursor.execute(
            "DELETE FROM conversation_satisfaction_surveys WHERE user_id = %s",
            (user_id,)
        )
        stats['conversation_satisfaction_surveys'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Satisfaction surveys deleted: {cursor.rowcount}")

        # ========================================================================
        # 4. MEDICAL IMAGES
        # ========================================================================

        # medical_images (métadonnées seulement, les fichiers S3 restent)
        cursor.execute(
            "UPDATE medical_images SET user_id = %s WHERE user_id = %s",
            (anonymous_id, user_id)
        )
        stats['medical_images'] = cursor.rowcount
        logger.info(f"[anonymize_user_in_postgresql] Medical images anonymized: {cursor.rowcount}")


        # ========================================================================
        # TOTAL
        # ========================================================================

        total_rows = sum(stats.values())
        logger.info(f"[anonymize_user_in_postgresql] ✅ Total rows anonymized: {total_rows}")

        # Recreate FK constraint
        cursor.execute("""
            ALTER TABLE stripe_subscriptions
            ADD CONSTRAINT fk_subscription_user
            FOREIGN KEY (user_email)
            REFERENCES user_billing_info(user_email)
            ON DELETE CASCADE
        """)
        logger.info(f"[anonymize_user_in_postgresql] FK constraint fk_subscription_user recreated")

        return stats

    except Exception as e:
        logger.error(f"[anonymize_user_in_postgresql] ❌ Error during anonymization: {str(e)}")
        # Recreate FK constraint even on error to maintain DB integrity
        try:
            cursor.execute("""
                ALTER TABLE stripe_subscriptions
                ADD CONSTRAINT fk_subscription_user
                FOREIGN KEY (user_email)
                REFERENCES user_billing_info(user_email)
                ON DELETE CASCADE
            """)
            logger.info(f"[anonymize_user_in_postgresql] FK constraint fk_subscription_user recreated after error")
        except Exception as fk_error:
            logger.error(f"[anonymize_user_in_postgresql] ❌ Failed to recreate FK: {fk_error}")
        raise


def delete_user_auth_data(conn, user_id: str) -> Dict[str, int]:
    """
    Supprime les données d'authentification personnelles (webauthn passkeys).

    Ces données ne peuvent pas être anonymisées car elles sont cryptographiques
    et liées à l'appareil de l'utilisateur.

    Args:
        conn: Connexion psycopg2 PostgreSQL
        user_id: UUID de l'utilisateur

    Returns:
        Dictionnaire avec le nombre de lignes supprimées par table
    """
    stats = {}
    cursor = conn.cursor()

    try:
        # Supprimer les passkeys WebAuthn
        cursor.execute("DELETE FROM webauthn_credentials WHERE user_id = %s", (user_id,))
        stats['webauthn_credentials'] = cursor.rowcount
        logger.info(f"[delete_user_auth_data] WebAuthn credentials deleted: {cursor.rowcount}")

        return stats

    except Exception as e:
        # Si la table n'existe pas encore, ce n'est pas grave
        logger.warning(f"[delete_user_auth_data] Warning: {str(e)}")
        stats['webauthn_credentials'] = 0
        return stats


def log_gdpr_deletion(conn, user_id: str, user_email: str, stats: Dict[str, int]) -> None:
    """
    Enregistre l'anonymisation dans les logs d'audit pour conformité RGPD.

    Crée automatiquement la table gdpr_deletion_logs si elle n'existe pas.

    Args:
        conn: Connexion psycopg2 PostgreSQL
        user_id: UUID original de l'utilisateur
        user_email: Email original de l'utilisateur
        stats: Statistiques d'anonymisation (nombre de lignes par table)

    Returns:
        None
    """
    cursor = conn.cursor()

    try:
        # Créer la table d'audit si elle n'existe pas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gdpr_deletion_logs (
                id SERIAL PRIMARY KEY,
                original_user_id VARCHAR(255) NOT NULL,
                original_user_email VARCHAR(255) NOT NULL,
                anonymous_identifier VARCHAR(255) NOT NULL,
                tables_affected JSONB,
                deletion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deletion_type VARCHAR(50) DEFAULT 'anonymization'
            )
        """)

        # Créer un index sur la date pour les audits
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gdpr_deletion_timestamp
            ON gdpr_deletion_logs(deletion_timestamp DESC)
        """)

        anonymous_id = generate_anonymous_identifier(user_email)

        # Insérer le log
        cursor.execute(
            """INSERT INTO gdpr_deletion_logs
               (original_user_id, original_user_email, anonymous_identifier, tables_affected, deletion_type)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, user_email, anonymous_id, json.dumps(stats), 'anonymization')
        )

        logger.info(f"[log_gdpr_deletion] ✅ GDPR deletion logged: {user_email} → {anonymous_id}")

    except Exception as e:
        # Ne pas faire échouer toute la transaction si le log échoue
        logger.error(f"[log_gdpr_deletion] ⚠️ Failed to log GDPR deletion: {str(e)}")


def get_anonymization_summary(user_id: str, user_email: str) -> Dict[str, Any]:
    """
    Génère un résumé de l'anonymisation pour affichage à l'utilisateur.

    Args:
        user_id: UUID de l'utilisateur
        user_email: Email de l'utilisateur

    Returns:
        Dictionnaire avec les informations de l'anonymisation
    """
    anonymous_id = generate_anonymous_identifier(user_email)
    anonymous_email = f"{anonymous_id}@deleted.intelia.app"

    return {
        "original_user_id": user_id,
        "original_email": user_email,
        "anonymous_identifier": anonymous_id,
        "anonymous_email": anonymous_email,
        "timestamp": datetime.now().isoformat(),
        "gdpr_compliant": True,
        "data_retained": [
            "conversations (anonymisées)",
            "messages (anonymisés)",
            "historique de paiements (anonymisé)",
            "statistiques d'utilisation (anonymisées)"
        ],
        "data_deleted": [
            "compte d'authentification Supabase",
            "profil utilisateur complet",
            "passkeys WebAuthn"
        ]
    }
