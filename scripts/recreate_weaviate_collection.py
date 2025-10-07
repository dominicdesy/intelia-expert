#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour recréer la collection Weaviate avec le nouveau schéma (25 propriétés)
Utilise la méthode recreate_collection() de l'ingester
"""

import sys
import logging
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent / "rag" / "knowledge_extractor"))

# Charger les variables d'environnement depuis rag/.env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "rag" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logging.info(f"Variables d'environnement chargées depuis: {env_path}")
else:
    logging.warning(f"Fichier .env non trouvé: {env_path}")

from weaviate_integration.ingester import WeaviateIngester

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("RECRÉATION COLLECTION WEAVIATE AVEC NOUVEAU SCHÉMA")
    print("=" * 60)
    print()
    print("⚠️  ATTENTION: Cette opération va:")
    print("   1. SUPPRIMER la collection existante 'InteliaExpertKnowledge'")
    print("   2. RECRÉER avec le nouveau schéma (25 propriétés)")
    print("   3. Inclure les nouveaux champs: sex, age_min_days, age_max_days,")
    print("      company, breed, unit_system")
    print()
    print("📊 Vous devrez ensuite RE-EXTRAIRE tous vos documents PDF")
    print("   pour populer les nouveaux champs.")
    print()

    response = input("Êtes-vous sûr de vouloir continuer? (yes/no): ")

    if response.lower() not in ['yes', 'y', 'oui']:
        print("\n❌ Opération annulée.")
        return

    print("\n🔄 Connexion à Weaviate...")
    try:
        ingester = WeaviateIngester(collection_name="InteliaExpertKnowledge")

        print("🗑️  Suppression et recréation de la collection...")
        ingester.recreate_collection()

        print("\n✅ Collection recréée avec succès!")
        print("\n📋 Nouveau schéma: 25 propriétés")
        print("   - Propriétés originales (19)")
        print("   - Nouveaux champs alignés PostgreSQL:")
        print("     • sex (TEXT)")
        print("     • age_min_days (INT)")
        print("     • age_max_days (INT)")
        print("     • company (TEXT)")
        print("     • breed (TEXT)")
        print("     • unit_system (TEXT)")

        print("\n🚀 Prochaine étape:")
        print("   cd C:\\intelia_gpt\\intelia-expert\\rag\\knowledge_extractor")
        print("   python knowledge_extractor.py --force")

        ingester.close()

    except Exception as e:
        logger.error(f"Erreur lors de la recréation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
