#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour ingérer tous les fichiers Excel vers PostgreSQL
"""

import sys
import asyncio
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ajouter le répertoire postgreSQL_converter au path
sys.path.insert(0, str(Path(__file__).parent.parent / "rag" / "postgreSQL_converter"))

from converter import IntelligentExcelConverter
from config import DATABASE_CONFIG, validate_database_config


async def main():
    print("=" * 70)
    print("INGESTION EXCEL VERS POSTGRESQL")
    print("=" * 70)
    print()

    # Validation configuration
    try:
        validate_database_config()
    except ValueError as e:
        print(f"❌ Erreur configuration: {e}")
        sys.exit(1)

    # Liste des fichiers Excel à ingérer (SANS Hyline)
    excel_files = [
        "C:/intelia_gpt/intelia-expert/rag/documents/PerformanceMetrics/Cobb500-Broiler-Performance-Nutrition-Supplement2022.xlsx",
        "C:/intelia_gpt/intelia-expert/rag/documents/PerformanceMetrics/RossxRoss308-BroilerPerformanceObjectives2022.xlsx",
    ]

    print(f"📁 Fichiers à ingérer: {len(excel_files)}")
    for i, f in enumerate(excel_files, 1):
        filename = Path(f).name
        print(f"   {i}. {filename}")
    print()

    converter = IntelligentExcelConverter(DATABASE_CONFIG)

    try:
        await converter.initialize()
        print("✅ Convertisseur initialisé\n")

        success_count = 0
        failed_count = 0
        failed_files = []

        for i, file_path in enumerate(excel_files, 1):
            filename = Path(file_path).name
            print(f"[{i}/{len(excel_files)}] {filename}")
            print("-" * 70)

            try:
                if not Path(file_path).exists():
                    print(f"   ⚠️  Fichier non trouvé: {file_path}")
                    failed_count += 1
                    failed_files.append((filename, "Fichier non trouvé"))
                    continue

                success = await converter.convert_file(file_path)
                if success:
                    print(f"   ✅ Succès\n")
                    success_count += 1
                else:
                    print(f"   ❌ Échec\n")
                    failed_count += 1
                    failed_files.append((filename, "Conversion échouée"))

            except Exception as e:
                print(f"   ❌ Erreur: {e}\n")
                failed_count += 1
                failed_files.append((filename, str(e)))

        print("=" * 70)
        print("RAPPORT FINAL")
        print("=" * 70)
        print(f"✅ Succès: {success_count}")
        print(f"❌ Échecs: {failed_count}")
        print(f"📊 Total: {len(excel_files)}")

        if failed_files:
            print("\n❌ Fichiers en échec:")
            for filename, reason in failed_files:
                print(f"   • {filename}: {reason}")

        print()

    finally:
        await converter.close()
        print("✅ Connexion fermée")


if __name__ == "__main__":
    asyncio.run(main())
