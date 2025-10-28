#!/usr/bin/env python3
"""
Batch PDF Table Extraction
===========================

Extrait automatiquement les tableaux de tous les PDFs dans les répertoires species.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Répertoires sources
SOURCE_DIRS = [
    r"C:\intelia_gpt\intelia-expert\rag\documents\Sources\public\species\layer\breeds"
]

# Répertoire de sortie
OUTPUT_DIR = r"C:\intelia_gpt\intelia-expert\rag\documents\PerformanceMetrics"

# Fichier de log
LOG_FILE = Path(__file__).parent / "batch_extraction_log.txt"


def get_output_filename(pdf_path: Path) -> str:
    """
    Génère un nom de fichier de sortie basé sur le chemin du PDF.

    Example:
        species/broiler/breeds/cobb/Cobb500.pdf -> Cobb500_Extracted.xlsx
        species/layer/breeds/lohmann/LOHMANN-LSL.pdf -> LOHMANN-LSL_Extracted.xlsx
    """
    # Prendre juste le nom du fichier sans extension
    base_name = pdf_path.stem

    # Nettoyer le nom (enlever les espaces, parenthèses, etc.)
    clean_name = base_name.replace(' ', '_').replace('(', '').replace(')', '')

    return f"{clean_name}_Extracted.xlsx"


def log_message(message: str, also_print=True):
    """Log un message dans le fichier log et optionnellement à l'écran"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)

    if also_print:
        print(message)


def find_all_pdfs(source_dirs):
    """Trouve tous les PDFs dans les répertoires sources"""
    all_pdfs = []

    for source_dir in source_dirs:
        source_path = Path(source_dir)
        if source_path.exists():
            pdfs = list(source_path.rglob("*.pdf"))
            all_pdfs.extend(pdfs)
            log_message(f"Trouvé {len(pdfs)} PDFs dans {source_dir}")

    return sorted(all_pdfs)


def extract_pdf(pdf_path: Path, output_path: Path, script_path: Path) -> bool:
    """
    Exécute l'extraction pour un PDF donné.

    Returns:
        True si succès, False sinon
    """
    try:
        log_message(f"\n{'='*60}")
        log_message(f"Processing: {pdf_path.name}")
        log_message(f"Output: {output_path.name}")

        # Préparer la commande
        cmd = [
            sys.executable,
            str(script_path),
            str(pdf_path),
            str(output_path)
        ]

        # Exécuter avec auto-confirmation (option 3 si fichier existe)
        result = subprocess.run(
            cmd,
            input="3\n",  # Choisir option 3 (créer nouveau fichier si existe)
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplacer les caractères invalides
            timeout=600  # 10 minutes max par PDF
        )

        if result.returncode == 0:
            log_message(f"[OK] Extraction réussie: {pdf_path.name}")
            return True
        else:
            log_message(f"[ERROR] Échec extraction: {pdf_path.name}")
            log_message(f"  stderr: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        log_message(f"[ERROR] Timeout (10 min) pour {pdf_path.name}")
        return False
    except Exception as e:
        log_message(f"[ERROR] Exception pour {pdf_path.name}: {e}")
        return False


def main():
    """Fonction principale"""
    # Parser les arguments
    parser = argparse.ArgumentParser(description="Extraction automatique de tableaux depuis tous les PDFs")
    parser.add_argument('--yes', '-y', action='store_true', help="Confirmer automatiquement l'extraction")
    args = parser.parse_args()

    log_message("\n" + "="*60)
    log_message("BATCH PDF TABLE EXTRACTION")
    log_message("="*60)

    # Chemins
    script_path = Path(__file__).parent / "extract_pdf_tables_claude_vision.py"
    output_dir = Path(OUTPUT_DIR)

    if not script_path.exists():
        log_message(f"[ERROR] Script d'extraction introuvable: {script_path}")
        return

    if not output_dir.exists():
        log_message(f"[ERROR] Répertoire de sortie introuvable: {output_dir}")
        return

    # Trouver tous les PDFs
    all_pdfs = find_all_pdfs(SOURCE_DIRS)
    log_message(f"\nTotal de PDFs à traiter: {len(all_pdfs)}")

    if len(all_pdfs) == 0:
        log_message("[WARNING] Aucun PDF trouvé!")
        return

    # Demander confirmation (sauf si --yes)
    if not args.yes:
        print(f"\n[ATTENTION] Vous allez extraire les tableaux de {len(all_pdfs)} PDFs.")
        print(f"Cela peut prendre plusieurs heures et coûter environ ${len(all_pdfs) * 0.30:.2f} USD en API.")
        print(f"\nLes résultats seront sauvegardés dans: {output_dir}")

        confirm = input("\nContinuer? (oui/non): ").strip().lower()

        if confirm not in ['oui', 'o', 'yes', 'y']:
            log_message("[INFO] Extraction annulée par l'utilisateur")
            return
    else:
        log_message(f"[INFO] Mode automatique activé (--yes)")
        log_message(f"[INFO] Extraction de {len(all_pdfs)} PDFs...")

    # Traiter chaque PDF
    success_count = 0
    error_count = 0

    for i, pdf_path in enumerate(all_pdfs, 1):
        log_message(f"\n[{i}/{len(all_pdfs)}] Traitement de: {pdf_path.name}")

        # Générer le nom de fichier de sortie
        output_filename = get_output_filename(pdf_path)
        output_path = output_dir / output_filename

        # Extraire
        success = extract_pdf(pdf_path, output_path, script_path)

        if success:
            success_count += 1
        else:
            error_count += 1

    # Résumé final
    log_message("\n" + "="*60)
    log_message("RÉSUMÉ FINAL")
    log_message("="*60)
    log_message(f"Total traité: {len(all_pdfs)}")
    log_message(f"Succès: {success_count}")
    log_message(f"Erreurs: {error_count}")
    log_message(f"Fichiers de sortie: {output_dir}")
    log_message(f"Log complet: {LOG_FILE}")
    log_message("="*60)


if __name__ == '__main__':
    main()
