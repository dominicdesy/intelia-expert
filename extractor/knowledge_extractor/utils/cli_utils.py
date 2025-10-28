"""
Utilitaires CLI pour validation et gestion des arguments
Module extrait du knowledge_extractor pour une meilleure modularité
"""

import sys
from pathlib import Path
from typing import Optional

# Configuration
MAX_FILE_SIZE_MB = 100


def validate_cli_args() -> Optional[str]:
    """Valide les arguments CLI de manière sécurisée"""
    if len(sys.argv) > 1:
        file_arg = sys.argv[1]

        # Vérification de l'extension
        if not file_arg.endswith(".json"):
            print("ERREUR: Seuls les fichiers .json sont acceptés")
            return None

        try:
            # Résolution sécurisée du chemin
            file_path = Path(file_arg).resolve()

            # Vérification d'existence
            if not file_path.exists():
                print(f"ERREUR: Fichier non trouvé: {file_arg}")
                return None

            # Vérification que c'est bien un fichier
            if not file_path.is_file():
                print(f"ERREUR: Chemin invalide (pas un fichier): {file_arg}")
                return None

            # Vérification de la taille
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                print(
                    f"ERREUR: Fichier trop volumineux: {size_mb:.1f}MB (limite: {MAX_FILE_SIZE_MB}MB)"
                )
                return None

            return str(file_path)

        except Exception as e:
            print(f"ERREUR: Impossible de valider le fichier: {e}")
            return None

    return None


def print_validation_report(validation_report: dict, interactive: bool = True) -> dict:
    """Affiche le rapport de validation et gère l'interaction utilisateur"""
    print("\nRapport de validation:")
    print(f"  - Total fichiers: {validation_report['total_files']}")
    print(f"  - Fichiers valides: {validation_report['valid_files']}")
    print(f"  - Fichiers problématiques: {validation_report['invalid_files']}")
    print(f"  - Chunks totaux détectés: {validation_report['total_chunks']}")
    print(f"  - Taille totale: {validation_report['total_size_mb']:.1f}MB")

    # Afficher les fichiers problématiques
    if validation_report["problematic_files"]:
        print("\nFichiers problématiques détectés:")
        for i, problematic in enumerate(validation_report["problematic_files"]):
            print(f"  - {problematic['file']}:")
            for issue in problematic["issues"]:
                print(f"    - {issue}")
                if "POSSIBLY_EMPTY_RESPONSE" in issue:
                    print(
                        "    Suggestion: Ce fichier semble avoir une réponse vide de l'API LLM"
                    )
            print(f"    Taille: {problematic['size_mb']:.1f}MB")

            # Debug pour fichiers tous problématiques
            if (
                validation_report["invalid_files"] == validation_report["total_files"]
                and validation_report["total_files"] > 10
                and i < 3
            ):
                file_details = validation_report["file_details"].get(
                    problematic["file"], {}
                )
                debug_info = file_details.get("debug_info", {})
                if debug_info:
                    print(
                        f"    Debug - Type racine: {debug_info.get('root_type', 'N/A')}"
                    )
                    print(
                        f"    Debug - Clés disponibles: {debug_info.get('all_keys', 'N/A')}"
                    )

        # Message spécial si TOUS les fichiers sont problématiques
        if (
            validation_report["invalid_files"] == validation_report["total_files"]
            and validation_report["total_files"] > 10
        ):
            print("\nANOMALIE DÉTECTÉE: 100% des fichiers sont marqués problématiques!")
            print("   Cela suggère un problème avec la logique de validation.")

    # Gestion interactive
    if interactive and validation_report["problematic_files"]:
        print("\nQue souhaitez-vous faire?")
        print(
            f"  1. Continuer avec les fichiers valides seulement ({validation_report['valid_files']} fichiers)"
        )
        print("  2. Arrêter et corriger les fichiers problématiques d'abord")
        print("  3. Continuer avec TOUS les fichiers (risqué)")

        try:
            choice = input("Votre choix (1/2/3): ").strip()

            if choice == "2":
                return {
                    "proceed": False,
                    "reason": "user_requested_stop",
                    "files_to_process": [],
                    "validation_report": validation_report,
                }
            elif choice == "3":
                return {
                    "proceed": True,
                    "reason": "user_force_all",
                    "files_to_process": [],  # Sera rempli par l'appelant
                    "validation_report": validation_report,
                }
            else:  # Choix 1 ou défaut
                return {
                    "proceed": True,
                    "reason": "valid_files_only",
                    "files_to_process": validation_report["valid_files_list"],
                    "validation_report": validation_report,
                }

        except KeyboardInterrupt:
            print("\nTraitement interrompu par l'utilisateur")
            return {
                "proceed": False,
                "reason": "user_interrupt",
                "files_to_process": [],
                "validation_report": validation_report,
            }

    # Mode non-interactif
    return {
        "proceed": True,
        "reason": "auto_valid_only",
        "files_to_process": validation_report["valid_files_list"],
        "validation_report": validation_report,
    }


def print_final_report(results: dict):
    """Affiche le rapport final des résultats"""
    print(f"\n{'='*60}")
    print("RAPPORT FINAL - TRAITEMENT INTELLIGENT CORRIGÉ AVEC VALIDATION")
    print("=" * 60)

    if "error" in results:
        print(f"Erreur: {results['error']}")
        return

    if results.get("status") == "stopped_by_validation":
        print("Traitement arrêté suite à la validation préalable")
        print(f"Raison: {results['reason']}")
        return

    if results.get("status") == "no_valid_files":
        print("Aucun fichier valide trouvé après validation")
        return

    if results.get("status") == "no_processing_needed":
        print("Aucun traitement nécessaire")
        print(f"Fichiers à jour: {results.get('up_to_date', 0)}")
        return

    summary = results.get("summary", {})
    processed = results.get("processed", [])
    errors = results.get("errors", [])
    validation_report = results.get("validation_report", {})

    print(f"Fichiers traités: {summary.get('files_processed', 0)}")
    print(f"Succès: {summary.get('files_successful', 0)}")
    print(f"Échecs: {summary.get('files_failed', 0)}")
    print(f"Ignorés (à jour): {summary.get('files_skipped', 0)}")
    print(f"Exclus par validation: {summary.get('files_excluded_by_validation', 0)}")
    print(f"Taux de succès: {summary.get('success_rate', 0):.1%}")

    # Détails de la validation préalable
    print("\nValidation préalable:")
    print(f"  - Fichiers valides: {validation_report.get('valid_files', 0)}")
    print(f"  - Fichiers problématiques: {validation_report.get('invalid_files', 0)}")
    print(f"  - Chunks totaux détectés: {validation_report.get('total_chunks', 0)}")
    print(
        f"  - Taille totale traitée: {validation_report.get('total_size_mb', 0):.1f}MB"
    )

    if validation_report.get("problematic_files"):
        print("\nFichiers problématiques exclus:")
        for problematic in validation_report["problematic_files"][:3]:
            print(f"  - {problematic['file']}: {len(problematic['issues'])} problèmes")

    # Détails par catégorie
    if processed:
        print("\nDétails par raison de traitement:")
        reasons = {}
        for result in processed:
            reason = result.get("processing_reason", "unknown")
            if reason not in reasons:
                reasons[reason] = {"count": 0, "success": 0, "avg_coverage": 0}
            reasons[reason]["count"] += 1
            if result.get("injection_success", 0) > 0:
                reasons[reason]["success"] += 1
            reasons[reason]["avg_coverage"] += result.get("chunk_coverage_ratio", 0)

        for reason, stats in reasons.items():
            success_rate = (
                stats["success"] / stats["count"] if stats["count"] > 0 else 0
            )
            avg_coverage = (
                stats["avg_coverage"] / stats["count"] if stats["count"] > 0 else 0
            )
            print(
                f"  - {reason}: {stats['success']}/{stats['count']} "
                f"({success_rate:.1%}, couverture moy: {avg_coverage:.1%})"
            )

    # Statistiques du cache
    if "cache_stats" in results:
        cache_stats = results["cache_stats"]
        print("\nStatistiques du cache:")
        print(f"  - Total fichiers: {cache_stats.get('total_files', 0)}")
        print(f"  - Succès: {cache_stats.get('successful', 0)}")
        print(f"  - Taux de succès: {cache_stats.get('success_rate', 0):.1%}")

    # Erreurs détaillées
    if errors:
        print("\nDétails des erreurs:")
        for error in errors[:5]:
            print(f"  - {Path(error['file']).name}: {error['error'][:100]}...")

    print("\nAméliorations CORRIGÉES appliquées:")
    print("  - Validation préalable: Détection fichiers problématiques")
    print("  - Retry automatique LLM: 3 tentatives avec réparation JSON")
    print("  - Préservation chunks volumineux: Limite étendue à 3000 mots")
    print("  - Validation par source_file: Récupération précise")
    print("  - Critères qualité assouplis: Préserve plus de contenu")
    print("  - Cache intelligent: Évite les retraitements inutiles")
    print("  - Mode interactif: Gestion des problèmes en temps réel")
    print("  - Gestion mémoire sécurisée: Protection contre les gros fichiers")
    print("  - Validation CLI robuste: Contrôle des arguments d'entrée")
    print("  - Fermeture propre des connexions: Évite les fuites de ressources")
    print("  - Nettoyage automatique du cache: Suppression des entrées obsolètes")
