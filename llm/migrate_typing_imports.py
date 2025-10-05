#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration automatique des imports typing vers utils/types.py

Ce script:
1. Trouve tous les fichiers .py avec des imports typing
2. Remplace 'from typing import ...' par 'from utils.types import ...'
3. Créé un backup avant modification
4. Génère un rapport de migration

Usage:
    python migrate_typing_imports.py [--dry-run] [--path PATH]

Options:
    --dry-run    Affiche les changements sans les appliquer
    --path       Chemin à analyser (défaut: .)
"""

import re
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

# Types communément importés depuis typing
COMMON_TYPES = {
    "Dict",
    "List",
    "Any",
    "Optional",
    "Tuple",
    "Union",
    "Callable",
    "Awaitable",
    "Set",
    "Iterable",
    "TypeVar",
    "Generic",
    "Protocol",
    "Literal",
    "cast",
}

# Fichiers à exclure
EXCLUDE_FILES = {
    "utils/types.py",  # Le fichier source
    "migrate_typing_imports.py",  # Ce script
    "duplicate_analyzer.py",  # Analyseur
}

# Dossiers à exclure
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    "env",
    ".venv",
}


class TypingMigrator:
    """Migre les imports typing vers utils/types.py"""

    def __init__(self, root_path: str, dry_run: bool = False):
        self.root_path = Path(root_path)
        self.dry_run = dry_run
        self.stats = {
            "files_analyzed": 0,
            "files_modified": 0,
            "files_skipped": 0,
            "imports_replaced": 0,
            "errors": 0,
        }
        self.migration_log: List[Dict] = []

    def should_exclude(self, file_path: Path) -> bool:
        """Vérifie si le fichier doit être exclu"""
        # Exclure par nom de fichier
        relative_path = str(file_path.relative_to(self.root_path)).replace("\\", "/")
        if any(exclude in relative_path for exclude in EXCLUDE_FILES):
            return True

        # Exclure par dossier
        parts = file_path.parts
        if any(exclude in parts for exclude in EXCLUDE_DIRS):
            return True

        return False

    def find_python_files(self) -> List[Path]:
        """Trouve tous les fichiers Python"""
        python_files = []
        for file_path in self.root_path.rglob("*.py"):
            if not self.should_exclude(file_path):
                python_files.append(file_path)
        return python_files

    def analyze_file(self, file_path: Path) -> Tuple[bool, List[str], str]:
        """
        Analyse un fichier pour détecter les imports typing

        Returns:
            (needs_migration, typing_imports, new_content)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Pattern pour détecter: from typing import ...
            typing_import_pattern = r"^from typing import (.+)$"

            needs_migration = False
            typing_imports = []
            new_lines = []

            for line in content.split("\n"):
                match = re.match(typing_import_pattern, line.strip())

                if match:
                    # Extraire les imports
                    imports_str = match.group(1)

                    # Parser les imports (gérer les parenthèses multi-lignes)
                    if "(" in imports_str:
                        # Multi-line import - plus complexe
                        # Pour simplifier, on skip pour l'instant
                        new_lines.append(line)
                        self.stats["files_skipped"] += 1
                        continue

                    # Single line import
                    imports = [imp.strip() for imp in imports_str.split(",")]

                    # Séparer les types communs des autres
                    common_imports = []
                    other_imports = []

                    for imp in imports:
                        # Enlever les alias 'as'
                        base_import = imp.split(" as ")[0].strip()
                        if base_import in COMMON_TYPES:
                            common_imports.append(imp)
                        else:
                            other_imports.append(imp)

                    # Construire les nouvelles lignes
                    if common_imports:
                        new_line = (
                            f"from utils.types import {', '.join(common_imports)}"
                        )
                        new_lines.append(new_line)
                        typing_imports.extend(common_imports)
                        needs_migration = True

                    if other_imports:
                        # Garder les imports non-communs depuis typing
                        other_line = f"from typing import {', '.join(other_imports)}"
                        new_lines.append(other_line)
                else:
                    new_lines.append(line)

            new_content = "\n".join(new_lines)

            return needs_migration, typing_imports, new_content

        except Exception as e:
            print(f"❌ Erreur analyse {file_path}: {e}")
            self.stats["errors"] += 1
            return False, [], ""

    def migrate_file(self, file_path: Path) -> bool:
        """Migre un fichier"""
        self.stats["files_analyzed"] += 1

        needs_migration, typing_imports, new_content = self.analyze_file(file_path)

        if not needs_migration:
            return False

        # Log
        relative_path = file_path.relative_to(self.root_path)
        self.migration_log.append(
            {
                "file": str(relative_path),
                "imports": typing_imports,
                "status": "dry_run" if self.dry_run else "migrated",
            }
        )

        if self.dry_run:
            print(f"[DRY RUN] {relative_path}")
            print(f"   Imports a migrer: {', '.join(typing_imports)}")
            return True

        # Backup
        backup_path = file_path.with_suffix(".py.bak_typing")
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            print(f"❌ Erreur backup {file_path}: {e}")
            self.stats["errors"] += 1
            return False

        # Écrire le nouveau contenu
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"OK Migre: {relative_path}")
            print(f"   Imports: {', '.join(typing_imports)}")
            print(f"   Backup: {backup_path.name}")

            self.stats["files_modified"] += 1
            self.stats["imports_replaced"] += len(typing_imports)
            return True

        except Exception as e:
            print(f"❌ Erreur écriture {file_path}: {e}")
            # Restaurer le backup
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
            self.stats["errors"] += 1
            return False

    def run(self):
        """Exécute la migration"""
        print("=" * 70)
        print("MIGRATION DES IMPORTS TYPING -> utils/types.py")
        print("=" * 70)
        print()

        if self.dry_run:
            print("WARNING: MODE DRY-RUN - Aucune modification ne sera effectuee")
            print()

        # Trouver les fichiers
        python_files = self.find_python_files()
        print(f"{len(python_files)} fichiers Python trouves")
        print()

        # Migrer chaque fichier
        for file_path in python_files:
            self.migrate_file(file_path)

        # Rapport final
        print()
        print("=" * 70)
        print("RAPPORT DE MIGRATION")
        print("=" * 70)
        print(f"Fichiers analyses:  {self.stats['files_analyzed']}")
        print(f"Fichiers modifies:  {self.stats['files_modified']}")
        print(f"Fichiers ignores:   {self.stats['files_skipped']}")
        print(f"Imports remplaces:  {self.stats['imports_replaced']}")
        print(f"Erreurs:            {self.stats['errors']}")
        print()

        if self.stats["files_modified"] > 0:
            print("Fichiers modifies:")
            for entry in self.migration_log:
                if entry["status"] in ["migrated", "dry_run"]:
                    print(f"   - {entry['file']}: {', '.join(entry['imports'])}")
            print()

        if not self.dry_run and self.stats["files_modified"] > 0:
            print("Prochaines etapes:")
            print("   1. Verifier que le code fonctionne toujours")
            print("   2. Executer les tests")
            print("   3. Si tout fonctionne, supprimer les backups .bak_typing")
            print("   4. Commit les changements")
        elif self.dry_run:
            print("Pour appliquer les changements, executez:")
            print("   python migrate_typing_imports.py")


def main():
    parser = argparse.ArgumentParser(
        description="Migre les imports typing vers utils/types.py"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les changements sans les appliquer",
    )
    parser.add_argument(
        "--path", default=".", help="Chemin racine à analyser (défaut: .)"
    )

    args = parser.parse_args()

    migrator = TypingMigrator(args.path, dry_run=args.dry_run)
    migrator.run()


if __name__ == "__main__":
    main()
