#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour effacer complètement la base PostgreSQL et la recréer proprement
"""

import sys
import asyncio
import asyncpg
from pathlib import Path
from dotenv import load_dotenv
import os

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Charger .env depuis rag/
env_path = Path(__file__).parent.parent / "rag" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Variables d'environnement chargées depuis: {env_path}")
else:
    print(f"ERREUR: Fichier .env non trouvé: {env_path}")
    sys.exit(1)


async def drop_all_tables(conn):
    """Supprime toutes les tables dans l'ordre correct (dépendances)"""

    drop_sql = """
    -- Supprimer les index
    DROP INDEX IF EXISTS idx_metrics_document_sheet;
    DROP INDEX IF EXISTS idx_metrics_category;
    DROP INDEX IF EXISTS idx_metrics_age;
    DROP INDEX IF EXISTS idx_metrics_key;
    DROP INDEX IF EXISTS idx_metrics_name;
    DROP INDEX IF EXISTS idx_metrics_unit;
    DROP INDEX IF EXISTS idx_documents_data_type;
    DROP INDEX IF EXISTS idx_documents_unit_system;
    DROP INDEX IF EXISTS idx_documents_metadata_gin;

    -- Supprimer les tables (ordre inverse des dépendances)
    DROP TABLE IF EXISTS metrics CASCADE;
    DROP TABLE IF EXISTS data_categories CASCADE;
    DROP TABLE IF EXISTS documents CASCADE;
    DROP TABLE IF EXISTS strains CASCADE;
    DROP TABLE IF EXISTS breeds CASCADE;
    DROP TABLE IF EXISTS companies CASCADE;
    """

    await conn.execute(drop_sql)
    print("✅ Toutes les tables supprimées")


async def create_tables(conn):
    """Recrée les tables avec le schéma complet"""

    create_sql = """
    -- Table des compagnies
    CREATE TABLE IF NOT EXISTS companies (
        id SERIAL PRIMARY KEY,
        company_name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Table des breeds
    CREATE TABLE IF NOT EXISTS breeds (
        id SERIAL PRIMARY KEY,
        company_id INTEGER REFERENCES companies(id),
        breed_name VARCHAR(100) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(company_id, breed_name)
    );

    -- Table des strains
    CREATE TABLE IF NOT EXISTS strains (
        id SERIAL PRIMARY KEY,
        breed_id INTEGER REFERENCES breeds(id),
        strain_name VARCHAR(100) NOT NULL,
        species VARCHAR(50) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(breed_id, strain_name)
    );

    -- Table des documents avec support data_type et unit_system
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        strain_id INTEGER REFERENCES strains(id),
        housing_system VARCHAR(200),
        feather_color VARCHAR(50),
        sex VARCHAR(10),
        data_type VARCHAR(50),
        unit_system VARCHAR(10),
        file_hash VARCHAR(64) UNIQUE,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(filename, file_hash)
    );

    -- Table des catégories étendues
    CREATE TABLE IF NOT EXISTS data_categories (
        id SERIAL PRIMARY KEY,
        category_name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Table des métriques
    CREATE TABLE IF NOT EXISTS metrics (
        id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
        category_id INTEGER REFERENCES data_categories(id),
        sheet_name VARCHAR(100) NOT NULL,
        metric_key VARCHAR(200) NOT NULL,
        metric_name VARCHAR(200),
        value_text TEXT,
        value_numeric DECIMAL(15,6),
        unit VARCHAR(50),
        age_min INTEGER,
        age_max INTEGER,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Index pour performance
    CREATE INDEX IF NOT EXISTS idx_metrics_document_sheet ON metrics(document_id, sheet_name);
    CREATE INDEX IF NOT EXISTS idx_metrics_category ON metrics(category_id);
    CREATE INDEX IF NOT EXISTS idx_metrics_age ON metrics(age_min, age_max);
    CREATE INDEX IF NOT EXISTS idx_metrics_key ON metrics(metric_key);
    CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
    CREATE INDEX IF NOT EXISTS idx_metrics_unit ON metrics(unit);
    CREATE INDEX IF NOT EXISTS idx_documents_data_type ON documents(data_type);
    CREATE INDEX IF NOT EXISTS idx_documents_unit_system ON documents(unit_system);

    -- Index GIN pour recherche dans métadonnées JSONB
    CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING GIN (metadata);

    -- Insertion des catégories étendues
    INSERT INTO data_categories (category_name, description)
    VALUES
        ('performance', 'Performance and production metrics'),
        ('nutrition', 'Nutritional requirements and feed data'),
        ('pharmaceutical', 'Pharmaceutical and veterinary data'),
        ('carcass', 'Carcass yield and processing data'),
        ('environment', 'Environmental conditions and housing'),
        ('health', 'Health and mortality data'),
        ('economics', 'Economic and cost data'),
        ('other', 'Other miscellaneous data')
    ON CONFLICT (category_name) DO NOTHING;
    """

    await conn.execute(create_sql)
    print("✅ Toutes les tables recréées")


async def verify_schema(conn):
    """Vérifie que le schéma est bien créé"""

    tables = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    print("\n📋 Tables créées:")
    for table in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
        print(f"   - {table['table_name']}: {count} enregistrements")

    # Vérifier les catégories
    categories = await conn.fetch("SELECT category_name FROM data_categories ORDER BY id")
    print(f"\n📂 Catégories ({len(categories)}):")
    for cat in categories:
        print(f"   - {cat['category_name']}")


async def main():
    print("=" * 70)
    print("RESET COMPLET DE LA BASE POSTGRESQL")
    print("=" * 70)
    print()
    print("⚠️  ATTENTION: Cette opération va:")
    print("   1. SUPPRIMER toutes les tables existantes")
    print("   2. EFFACER toutes les données")
    print("   3. RECRÉER le schéma vide")
    print()

    response = input("Êtes-vous sûr de vouloir continuer? (yes/no): ")

    if response.lower() not in ['yes', 'y', 'oui']:
        print("\n❌ Opération annulée.")
        return

    # Configuration PostgreSQL
    config = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME"),
        "ssl": os.getenv("DB_SSL", "require"),
    }

    print("\n🔄 Connexion à PostgreSQL...")
    print(f"   Host: {config['host']}")
    print(f"   Database: {config['database']}")

    try:
        conn = await asyncpg.connect(**config)

        print("\n🗑️  Suppression de toutes les tables...")
        await drop_all_tables(conn)

        print("\n🔨 Recréation des tables...")
        await create_tables(conn)

        print("\n🔍 Vérification du schéma...")
        await verify_schema(conn)

        await conn.close()

        print("\n" + "=" * 70)
        print("✅ BASE DE DONNÉES RÉINITIALISÉE AVEC SUCCÈS")
        print("=" * 70)
        print()
        print("🚀 Prochaine étape:")
        print("   Relancer l'ingestion des données Excel/JSON vers PostgreSQL")
        print()

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
