#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour identifier les tables PostgreSQL contenant des données de test à nettoyer

Usage:
    python scripts/check_database_test_data.py
"""

import os
import asyncio
import asyncpg
from typing import List, Dict, Any


async def check_test_data():
    """Vérifie quelles tables contiennent des données de test"""

    # Récupérer les credentials depuis les variables d'environnement
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "intelia_db")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "")

    if not db_password:
        print("❌ POSTGRES_PASSWORD non défini dans les variables d'environnement")
        return

    try:
        # Connexion à PostgreSQL
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )

        print(f"✅ Connecté à PostgreSQL: {db_host}:{db_port}/{db_name}")
        print("=" * 80)

        # Lister toutes les tables
        tables_query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """

        tables = await conn.fetch(tables_query)

        print(f"\n📊 Tables trouvées ({len(tables)}):\n")

        for table_row in tables:
            table_name = table_row['table_name']

            # Compter les lignes
            count_query = f"SELECT COUNT(*) as count FROM {table_name};"
            count_result = await conn.fetchrow(count_query)
            row_count = count_result['count']

            # Obtenir les colonnes
            columns_query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
            """
            columns = await conn.fetch(columns_query)
            column_names = [col['column_name'] for col in columns]

            # Vérifier si c'est une table de test/log
            is_test_table = any(keyword in table_name.lower()
                              for keyword in ['query', 'question', 'chat', 'message',
                                            'conversation', 'history', 'log', 'test'])

            marker = "🔴" if is_test_table else "⚪"

            print(f"{marker} {table_name}")
            print(f"   Lignes: {row_count:,}")
            print(f"   Colonnes: {', '.join(column_names[:5])}" +
                  (f" (+{len(column_names)-5} more)" if len(column_names) > 5 else ""))

            # Si la table a des données et semble être de test, montrer un échantillon
            if is_test_table and row_count > 0:
                sample_query = f"SELECT * FROM {table_name} LIMIT 3;"
                try:
                    samples = await conn.fetch(sample_query)
                    if samples:
                        print(f"   Échantillon (3 premières lignes):")
                        for i, sample in enumerate(samples, 1):
                            print(f"     {i}. {dict(sample)}")
                except Exception as e:
                    print(f"   ⚠️ Erreur échantillon: {e}")

            print()

        print("=" * 80)
        print("\n🔍 Résumé:")
        print(f"   Total tables: {len(tables)}")
        test_tables = [t['table_name'] for t in tables
                      if any(k in t['table_name'].lower()
                            for k in ['query', 'question', 'chat', 'message',
                                    'conversation', 'history', 'log', 'test'])]
        print(f"   Tables de test potentielles (🔴): {len(test_tables)}")
        if test_tables:
            print(f"   Noms: {', '.join(test_tables)}")

        await conn.close()

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


def generate_cleanup_sql(table_names: List[str]) -> str:
    """Génère le SQL pour nettoyer les tables de test"""

    sql = "-- Script de nettoyage des données de test\n"
    sql += "-- ⚠️  ATTENTION: Cette opération est IRRÉVERSIBLE\n"
    sql += "-- Généré le: " + str(asyncio.get_event_loop().time()) + "\n\n"
    sql += "BEGIN;\n\n"

    for table_name in table_names:
        sql += f"-- Nettoyer {table_name}\n"
        sql += f"DELETE FROM {table_name};\n"
        sql += f"-- SELECT COUNT(*) FROM {table_name}; -- Vérification\n\n"

    sql += "COMMIT;\n"
    sql += "-- ROLLBACK; -- Décommenter pour annuler\n"

    return sql


if __name__ == "__main__":
    print("🔍 Vérification des données de test dans PostgreSQL\n")
    asyncio.run(check_test_data())

    print("\n" + "=" * 80)
    print("💡 Pour nettoyer les tables de test:")
    print("   1. Identifier les tables à nettoyer ci-dessus")
    print("   2. Utiliser DBeaver avec les commandes SQL appropriées")
    print("   3. Exemple: DELETE FROM table_name WHERE condition;")
    print("\n⚠️  ATTENTION: Toujours faire un backup avant de supprimer des données!")
