#!/usr/bin/env python3
"""
Script principal pour l'extraction de tableaux
Usage: python main.py [options] input_file
"""

import argparse
import sys
from pathlib import Path
import logging

from parser import MarkdownTableParser
from metadata import MetadataNormalizer
from exporter import SimpleTableExporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleTableExtractor:
    """Extracteur principal - Interface simple"""

    def __init__(self, intents_file: str = "intents.json", output_dir: str = "output"):
        self.normalizer = MetadataNormalizer(intents_file)
        self.parser = MarkdownTableParser(self.normalizer)
        self.exporter = SimpleTableExporter(output_dir)
        self.logger = logging.getLogger(__name__)

    def extract_from_files(self, json_file: str, txt_file: str = None):
        """Extrait les tableaux depuis les fichiers JSON/TXT"""

        # Lire le contenu
        text_content = self._read_source_content(json_file, txt_file)

        if not text_content:
            self.logger.warning(f"No content found in {json_file}")
            return []

        # Extraire les tableaux
        tables = self.parser.extract_tables_from_text(text_content, json_file)

        # Exporter chaque tableau
        exported_files = []
        for table in tables:
            files = self.exporter.export_table(table)
            exported_files.append(files)

            self.logger.info(f"Exported: {table.title} -> {Path(files['csv']).name}")

        return exported_files

    def _read_source_content(self, json_file: str, txt_file: str = None) -> str:
        """Lit le contenu depuis JSON ou TXT"""
        import json

        # Priorité au TXT s'il existe
        if txt_file and Path(txt_file).exists():
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                self.logger.warning(f"Cannot read TXT file: {e}")

        # Sinon, lire depuis JSON
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extraire le texte du JSON
            if isinstance(data, dict):
                if "text" in data:
                    return data["text"]
                elif "chunks" in data and isinstance(data["chunks"], list):
                    return "\n".join(
                        chunk for chunk in data["chunks"] if isinstance(chunk, str)
                    )

            return str(data)

        except Exception as e:
            self.logger.error(f"Cannot read JSON file: {e}")
            return ""


def main():
    """Interface en ligne de commande avec mode interactif"""
    parser = argparse.ArgumentParser(description="Extracteur de tableaux simplifié")
    parser.add_argument(
        "input", nargs="?", help="Fichier JSON à traiter (optionnel en mode interactif)"
    )
    parser.add_argument(
        "--output", "-o", help="Répertoire de sortie (optionnel en mode interactif)"
    )
    parser.add_argument(
        "--intents", default="intents.json", help="Fichier intents.json"
    )
    parser.add_argument("--txt", help="Fichier TXT correspondant (optionnel)")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Mode interactif"
    )

    args = parser.parse_args()

    # Mode interactif si aucun argument ou flag --interactive
    if args.interactive or (not args.input and not args.output):
        input_file, output_dir, txt_file = get_interactive_inputs()
    else:
        # Mode ligne de commande classique
        if not args.input:
            print("Erreur: Fichier d'entrée requis")
            sys.exit(1)
        if not args.output:
            print("Erreur: Répertoire de sortie requis (--output)")
            sys.exit(1)

        input_file = args.input
        output_dir = args.output
        txt_file = args.txt

    # Vérifier que le fichier d'entrée existe
    if not Path(input_file).exists():
        print(f"Erreur: Fichier {input_file} non trouvé")
        sys.exit(1)

    # Chercher OBLIGATOIREMENT le fichier TXT correspondant
    if not txt_file:
        potential_txt = Path(input_file).with_suffix(".txt")
        if potential_txt.exists():
            txt_file = str(potential_txt)
            print(f"Fichier TXT trouvé automatiquement: {txt_file}")
        else:
            print(f"ATTENTION: Aucun fichier TXT trouvé pour {Path(input_file).name}")
            print("Le fichier TXT est recommandé pour une extraction optimale")

            # Chercher dans le même répertoire
            txt_files = list(Path(input_file).parent.glob("*.txt"))
            if txt_files:
                print("Fichiers TXT disponibles dans le répertoire:")
                for i, txt in enumerate(txt_files):
                    print(f"  {i+1}. {txt.name}")

                choice = input(
                    "Voulez-vous utiliser un de ces fichiers? (numéro ou Entrée pour continuer): "
                ).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(txt_files):
                    txt_file = str(txt_files[int(choice) - 1])
                    print(f"Utilisation du fichier: {Path(txt_file).name}")
    else:
        print(f"Fichier TXT spécifié: {txt_file}")

    # Initialiser l'extracteur
    try:
        extractor = SimpleTableExtractor(args.intents, output_dir)
    except Exception as e:
        print(f"Erreur initialisation: {e}")
        sys.exit(1)

    # Traiter le fichier
    try:
        print("\nExtraction en cours...")
        print(f"Fichier source: {input_file}")
        print(f"Répertoire de sortie: {output_dir}")

        exported = extractor.extract_from_files(input_file, txt_file)

        print(f"\n✅ Extraction terminée - {len(exported)} tableau(x) extrait(s):")
        for files in exported:
            print(f"  📄 CSV: {Path(files['csv']).name}")
            if "xlsx" in files:
                print(f"  📊 XLSX: {Path(files['xlsx']).name}")
            print(f"  📋 Metadata: {Path(files['metadata']).name}")
            print()

        print(f"📁 Tous les fichiers sauvegardés dans: {extractor.exporter.output_dir}")

    except Exception as e:
        print(f"❌ Erreur extraction: {e}")
        sys.exit(1)


def get_interactive_inputs():
    """Interface interactive pour saisir les paramètres"""
    print("=== EXTRACTEUR DE TABLEAUX - MODE INTERACTIF ===\n")

    # Demander le fichier source
    while True:
        input_file = input("📁 Fichier JSON source (ou répertoire): ").strip()
        if not input_file:
            print("❌ Le fichier source est obligatoire")
            continue

        input_path = Path(input_file)
        if input_path.exists():
            if input_path.is_file():
                print(f"✅ Fichier trouvé: {input_path.name}")
                break
            elif input_path.is_dir():
                # Chercher des fichiers JSON dans le répertoire
                json_files = list(input_path.glob("*.json"))
                if json_files:
                    print(
                        f"📂 Répertoire trouvé avec {len(json_files)} fichier(s) JSON"
                    )
                    # Pour l'instant, prendre le premier fichier JSON
                    input_file = str(json_files[0])
                    print(f"✅ Utilisation du fichier: {Path(input_file).name}")
                    break
                else:
                    print("❌ Aucun fichier JSON trouvé dans ce répertoire")
                    continue
        else:
            print("❌ Fichier ou répertoire non trouvé")
            continue

    # Demander le répertoire de sortie
    while True:
        output_dir = input("📤 Répertoire de sortie: ").strip()
        if not output_dir:
            print("❌ Le répertoire de sortie est obligatoire")
            continue

        output_path = Path(output_dir)
        try:
            # Tester la création du répertoire
            output_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Répertoire de sortie: {output_path.resolve()}")
            break
        except Exception as e:
            print(f"❌ Impossible de créer le répertoire: {e}")
            continue

    # TOUJOURS chercher le fichier TXT correspondant - OBLIGATOIRE pour qualité optimale
    txt_file = None
    potential_txt = Path(input_file).with_suffix(".txt")

    if potential_txt.exists():
        txt_file = str(potential_txt)
        print(f"📄 Fichier TXT trouvé et sera utilisé: {potential_txt.name}")
    else:
        # Chercher dans le même répertoire avec patterns similaires
        input_stem = Path(input_file).stem
        parent_dir = Path(input_file).parent

        # Chercher des TXT avec nom similaire
        similar_txts = list(parent_dir.glob(f"{input_stem}*.txt"))
        if not similar_txts:
            # Chercher tous les TXT du répertoire
            similar_txts = list(parent_dir.glob("*.txt"))

        if similar_txts:
            print("📄 Fichiers TXT disponibles (RECOMMANDÉ pour qualité optimale):")
            for i, txt in enumerate(similar_txts):
                print(f"  {i+1}. {txt.name}")

            while True:
                choice = input(
                    "Sélectionner un fichier TXT (numéro, ou Entrée pour continuer sans): "
                ).strip()
                if not choice:
                    print(
                        "⚠️  ATTENTION: Extraction sans TXT - qualité peut être réduite"
                    )
                    break
                elif choice.isdigit() and 1 <= int(choice) <= len(similar_txts):
                    txt_file = str(similar_txts[int(choice) - 1])
                    print(f"✅ Fichier TXT sélectionné: {Path(txt_file).name}")
                    break
                else:
                    print("❌ Sélection invalide, essayez encore")
        else:
            print(
                "⚠️  Aucun fichier TXT trouvé - qualité d'extraction peut être réduite"
            )

    return input_file, output_dir, txt_file


if __name__ == "__main__":
    main()
