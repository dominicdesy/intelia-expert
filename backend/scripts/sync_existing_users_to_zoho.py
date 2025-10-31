"""
Script de synchronisation des utilisateurs existants vers Zoho Campaigns
Version: 1.0.0
Date: 2025-10-31

Ce script synchronise TOUS les utilisateurs existants de la base de données
vers Zoho Campaigns. Utilisez-le une seule fois après la configuration initiale.

Usage:
    python scripts/sync_existing_users_to_zoho.py [--dry-run] [--limit N]

Options:
    --dry-run    Affiche ce qui serait fait sans exécuter
    --limit N    Limite à N utilisateurs (pour tester)

Prérequis:
    - Variables d'environnement Zoho configurées
    - Connexion à la base de données Supabase
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour importer les modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import logging
from supabase import create_client, Client
from app.services.zoho_campaigns_service import zoho_campaigns_service

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_all_users(supabase: Client, limit: int = None):
    """
    Récupère tous les utilisateurs de la base de données

    Args:
        supabase: Client Supabase
        limit: Limite optionnelle du nombre d'utilisateurs

    Returns:
        Liste des utilisateurs
    """
    logger.info("Récupération des utilisateurs depuis Supabase...")

    try:
        query = supabase.table('users').select(
            'email, first_name, last_name, country, company_name, '
            'phone, language, production_type, category, created_at'
        ).order('created_at', desc=False)

        if limit:
            query = query.limit(limit)

        response = query.execute()

        if response.data:
            logger.info(f"✅ {len(response.data)} utilisateurs récupérés")
            return response.data
        else:
            logger.warning("Aucun utilisateur trouvé")
            return []

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des utilisateurs: {e}")
        return []


async def sync_user_to_zoho(user: dict, dry_run: bool = False):
    """
    Synchronise un utilisateur vers Zoho Campaigns

    Args:
        user: Dictionnaire contenant les données utilisateur
        dry_run: Si True, affiche seulement ce qui serait fait

    Returns:
        Tuple (success: bool, message: str)
    """
    email = user.get('email')

    if dry_run:
        logger.info(f"[DRY-RUN] Synchroniserait: {email}")
        return True, "Dry run - pas d'action réelle"

    try:
        result = await zoho_campaigns_service.sync_new_user(
            email=email,
            first_name=user.get('first_name'),
            last_name=user.get('last_name'),
            country=user.get('country'),
            company_name=user.get('company_name'),
            phone=user.get('phone'),
            language=user.get('language'),
            production_type=user.get('production_type'),
            category=user.get('category')
        )

        if result.get('success'):
            if result.get('already_exists'):
                return True, "Déjà existant dans Zoho"
            else:
                return True, "Ajouté à Zoho"
        elif result.get('skipped'):
            return False, "Zoho non configuré"
        else:
            return False, result.get('error', 'Erreur inconnue')

    except Exception as e:
        return False, f"Exception: {str(e)}"


async def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='Synchronise les utilisateurs existants vers Zoho Campaigns'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Affiche ce qui serait fait sans exécuter'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limite le nombre d\'utilisateurs à synchroniser'
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("Script de synchronisation Zoho Campaigns")
    logger.info("="*80)

    if args.dry_run:
        logger.info("⚠️ MODE DRY-RUN ACTIVÉ - Aucune modification ne sera faite")

    if args.limit:
        logger.info(f"⚠️ LIMITE: Seulement {args.limit} utilisateurs seront traités")

    # Vérifier la configuration Zoho
    if not zoho_campaigns_service.is_configured():
        logger.error("❌ Service Zoho Campaigns non configuré!")
        logger.error("Variables d'environnement requises:")
        logger.error("  - ZOHO_CLIENT_ID")
        logger.error("  - ZOHO_CLIENT_SECRET")
        logger.error("  - ZOHO_REFRESH_TOKEN")
        logger.error("  - ZOHO_CAMPAIGNS_LIST_KEY")
        sys.exit(1)

    logger.info("✅ Configuration Zoho validée")
    logger.info(f"   Région: {zoho_campaigns_service.region}")
    logger.info(f"   Liste: {zoho_campaigns_service.list_key}")

    # Connexion à Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        logger.error("❌ Configuration Supabase manquante!")
        logger.error("Variables requises: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    supabase = create_client(supabase_url, supabase_key)
    logger.info("✅ Connexion Supabase établie")

    # Récupérer les utilisateurs
    users = await fetch_all_users(supabase, limit=args.limit)

    if not users:
        logger.warning("Aucun utilisateur à synchroniser")
        sys.exit(0)

    # Statistiques
    total = len(users)
    success_count = 0
    already_exists_count = 0
    error_count = 0

    logger.info("")
    logger.info(f"Démarrage de la synchronisation de {total} utilisateurs...")
    logger.info("")

    # Synchroniser chaque utilisateur
    for i, user in enumerate(users, 1):
        email = user.get('email', 'N/A')
        logger.info(f"[{i}/{total}] {email}")

        success, message = await sync_user_to_zoho(user, dry_run=args.dry_run)

        if success:
            if "Déjà existant" in message:
                already_exists_count += 1
                logger.info(f"  ℹ️  {message}")
            else:
                success_count += 1
                logger.info(f"  ✅ {message}")
        else:
            error_count += 1
            logger.error(f"  ❌ {message}")

        # Petite pause pour respecter les rate limits Zoho (200 req/min)
        if not args.dry_run and i < total:
            await asyncio.sleep(0.35)  # ~170 req/min pour être sûr

    # Résumé
    logger.info("")
    logger.info("="*80)
    logger.info("RÉSUMÉ DE LA SYNCHRONISATION")
    logger.info("="*80)
    logger.info(f"Total traités:        {total}")
    logger.info(f"✅ Nouveaux ajoutés:  {success_count}")
    logger.info(f"ℹ️  Déjà existants:    {already_exists_count}")
    logger.info(f"❌ Erreurs:           {error_count}")
    logger.info("="*80)

    if args.dry_run:
        logger.info("")
        logger.info("⚠️ C'était un DRY-RUN - Aucune modification n'a été faite")
        logger.info("   Relancez sans --dry-run pour exécuter réellement")


if __name__ == "__main__":
    asyncio.run(main())
