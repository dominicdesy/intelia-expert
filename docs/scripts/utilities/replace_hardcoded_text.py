#!/usr/bin/env python3
"""
Script pour remplacer le texte hardcodé par des clés de traduction
"""
import re
from pathlib import Path

# Mapping du texte français vers les clés de traduction
REPLACEMENTS = {
    # Shared conversation page - error states
    '"Cette conversation partagée n\'existe pas ou a été supprimée"': 't("shared.notFound")',
    '"Ce lien de partage a expiré"': 't("shared.expired")',
    '"Impossible de charger la conversation"': 't("shared.loadError")',
    '"Une erreur est survenue"': 't("shared.error")',
    '"Chargement de la conversation..."': 't("shared.loading")',
    '"Conversation indisponible"': 't("shared.unavailable")',
    '"Retour à l\'accueil"': 't("shared.backToHome")',

    # Shared conversation page - header
    '"Intelia Cognito"': 't("shared.title")',
    '"Conversation partagée"': 't("shared.subtitle")',
    '"Essayer gratuitement →"': 't("shared.tryFree")',

    # Shared conversation page - conversation info
    'Conversation partagée par {name}': 'shared.sharedBy',  # Special case: needs interpolation
    '{count} vue{s}': 'shared.viewCount',  # Special case
    'Expire le {date}': 'shared.expiresOn',  # Special case

    # Shared conversation page - messages
    '"Question"': 't("shared.question")',
    '"Réponse"': 't("shared.answer")',

    # Shared conversation page - CTA
    '"Impressionné par la qualité des réponses ?"': 't("shared.impressed")',
    '"Créez votre compte gratuit et posez vos propres questions à Intelia Cognito, votre assistant IA spécialisé."': 't("shared.createFreeAccount")',
    '"Créer un compte gratuit"': 't("shared.createAccount")',
    '"Se connecter"': 't("shared.signIn")',
    '"Cette conversation a été générée par"': 't("shared.generatedBy")',
    '"Les données personnelles ont été anonymisées pour protéger la vie privée de l\'utilisateur."': 't("shared.dataAnonymized")',

    # Admin subscriptions page
    '"Accès refusé"': 't("admin.accessDenied")',
    '"Erreur lors du chargement des statistiques"': 't("admin.subscriptions.loadError")',
    '"Vue d\'ensemble"': 't("admin.subscriptions.tabs.overview")',
    '"Gestion des plans"': 't("admin.subscriptions.tabs.plans")',
    '"Prix par pays"': 't("admin.subscriptions.tabs.pricing")',
    '"Historique"': 't("admin.subscriptions.tabs.history")',
    '"Chargement des statistiques..."': 't("admin.subscriptions.loading")',
    '"Gestion des Abonnements"': 't("admin.subscriptions.title")',
    '"Administration complète des plans, prix et quotas"': 't("admin.subscriptions.subtitle")',
    '"← Retour"': 't("admin.subscriptions.back")',
    '"Total Abonnements"': 't("admin.subscriptions.totalSubscriptions")',
    '"Abonnements Actifs"': 't("admin.subscriptions.activeSubscriptions")',
    '"Revenu Mensuel"': 't("admin.subscriptions.monthlyRevenue")',
    '"Répartition par Plan"': 't("admin.subscriptions.planBreakdown")',
    '"Plan"': 't("admin.subscriptions.plan")',
    '"Abonnés"': 't("admin.subscriptions.subscribers")',
    '"%"': 't("admin.subscriptions.percentage")',
    '"Actions Rapides"': 't("admin.subscriptions.quickActions")',
    '"Ouvrir Stripe Dashboard"': 't("admin.subscriptions.openStripeDashboard")',
    '"Actualiser les données"': 't("admin.subscriptions.refreshData")',
    '"Exporter les données"': 't("admin.subscriptions.exportData")',
    '"Export à venir..."': 't("admin.subscriptions.exportComing")',
}

def replace_in_file(file_path):
    """Remplacer le texte hardcodé dans un fichier"""
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    replaced_count = 0

    for old_text, new_text in REPLACEMENTS.items():
        if old_text in content:
            content = content.replace(old_text, new_text)
            replaced_count += 1
            print(f"  Replaced: {old_text[:50]}...")

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Made {replaced_count} replacements in {file_path.name}")
        return replaced_count
    else:
        print(f"  No changes needed in {file_path.name}")
        return 0

def main():
    files_to_process = [
        Path("frontend/app/shared/[token]/page.tsx"),
        Path("frontend/app/admin/subscriptions/page.tsx"),
    ]

    total_replacements = 0
    for file_path in files_to_process:
        if file_path.exists():
            count = replace_in_file(file_path)
            total_replacements += count
        else:
            print(f"⚠ File not found: {file_path}")

    print(f"\nTotal replacements: {total_replacements}")

if __name__ == "__main__":
    main()
