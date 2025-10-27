#!/usr/bin/env python3
"""
Script pour ajouter les traductions admin manquantes
"""
import json
from pathlib import Path

ADMIN_TRANSLATIONS = {
    # Country Pricing Manager
    "admin.pricing.loadError": {
        "en": "Error loading countries",
        "fr": "Erreur lors du chargement des pays"
    },
    "admin.pricing.updateError": {
        "en": "Error updating",
        "fr": "Erreur lors de la mise à jour"
    },
    "admin.pricing.deleteConfirm": {
        "en": "Are you sure you want to delete {country} ({code})?",
        "fr": "Êtes-vous sûr de vouloir supprimer {country} ({code}) ?"
    },
    "admin.pricing.deleteError": {
        "en": "Error deleting",
        "fr": "Erreur lors de la suppression"
    },
    "admin.pricing.deleteSuccess": {
        "en": "{country} deleted successfully",
        "fr": "{country} supprimé avec succès"
    },
    "admin.pricing.tierUpdated": {
        "en": "Tier changed for {code}: Tier {oldTier} → Tier {newTier}",
        "fr": "Tier modifié pour {code}: Tier {oldTier} → Tier {newTier}"
    },
    "admin.pricing.tierUpdateError": {
        "en": "Error updating tier",
        "fr": "Erreur lors de la mise à jour du tier"
    },
    "admin.pricing.title": {
        "en": "Country Pricing Management",
        "fr": "Gestion des Prix par Pays"
    },
    "admin.pricing.countriesConfigured": {
        "en": "{count} countries configured • Currencies: CAD, USD, EUR",
        "fr": "{count} pays configurés • Devises: CAD, USD, EUR"
    },
    "admin.pricing.sortAZ": {
        "en": "A-Z",
        "fr": "A-Z"
    },
    "admin.pricing.sortTier": {
        "en": "Tier",
        "fr": "Tier"
    },
    "admin.pricing.refresh": {
        "en": "🔄 Refresh",
        "fr": "🔄 Actualiser"
    },
    "admin.pricing.searchPlaceholder": {
        "en": "Search country (e.g.: Canada, FR)...",
        "fr": "Rechercher un pays (ex: Canada, FR)..."
    },
    "admin.pricing.country": {
        "en": "Country",
        "fr": "Pays"
    },
    "admin.pricing.tier": {
        "en": "Tier",
        "fr": "Tier"
    },
    "admin.pricing.currency": {
        "en": "Currency",
        "fr": "Devise"
    },
    "admin.pricing.tierLevel": {
        "en": "Tier {level}",
        "fr": "Tier {level}"
    },
    "admin.pricing.save": {
        "en": "Save",
        "fr": "Sauvegarder"
    },
    "admin.pricing.cancel": {
        "en": "Cancel",
        "fr": "Annuler"
    },
    "admin.pricing.edit": {
        "en": "Edit",
        "fr": "Modifier"
    },
    "admin.pricing.editButton": {
        "en": "✏️  Edit...",
        "fr": "✏️  Modifier..."
    },
    "admin.pricing.deleteButton": {
        "en": "Delete this country",
        "fr": "Supprimer ce pays"
    },
    "admin.pricing.noCountriesFound": {
        "en": "No countries found for \"{search}\"",
        "fr": "Aucun pays trouvé pour \"{search}\""
    },
    "admin.pricing.noCountries": {
        "en": "No countries configured",
        "fr": "Aucun pays configuré"
    },
    "admin.pricing.tier1": {
        "en": "Tier 1 (Emerging Markets)",
        "fr": "Tier 1 (Marchés émergents)"
    },
    "admin.pricing.tier2": {
        "en": "Tier 2 (Intermediate)",
        "fr": "Tier 2 (Intermédiaire)"
    },
    "admin.pricing.tier3": {
        "en": "Tier 3 (Developed)",
        "fr": "Tier 3 (Développés)"
    },
    "admin.pricing.tier4": {
        "en": "Tier 4 (Premium)",
        "fr": "Tier 4 (Premium)"
    },
    "admin.pricing.marketingPrice": {
        "en": "Automatic marketing price",
        "fr": "Prix marketing automatique"
    },
    "admin.pricing.customPrice": {
        "en": "Custom price",
        "fr": "Prix personnalisé"
    },
    "admin.pricing.marketingPriceTooltip": {
        "en": "Marketing price calculated automatically from tier",
        "fr": "Prix marketing calculé automatiquement depuis le tier"
    },
    "admin.pricing.customPriceTooltip": {
        "en": "Custom price set manually",
        "fr": "Prix personnalisé défini manuellement"
    },
    "admin.pricing.customizeNote": {
        "en": "You can customize any price by clicking 'Edit' (becomes 'Custom').",
        "fr": "Vous pouvez personnaliser n'importe quel prix en cliquant sur \"Modifier\" (devient \"Custom\")."
    },

    # Subscription Plans Manager
    "admin.plans.loadError": {
        "en": "Error loading plans",
        "fr": "Erreur lors du chargement des plans"
    },
    "admin.plans.updateError": {
        "en": "Error updating",
        "fr": "Erreur lors de la mise à jour"
    },
    "admin.plans.priceUpdated": {
        "en": "Price updated for {plan}: ${oldPrice} → ${newPrice}",
        "fr": "Prix modifié pour {plan}: ${oldPrice} → ${newPrice}"
    },
    "admin.plans.recalculateConfirm": {
        "en": "Do you want to automatically recalculate prices for all countries based on the new base price?",
        "fr": "Voulez-vous recalculer automatiquement les prix pour tous les pays basé sur le nouveau prix de base ?"
    },
    "admin.plans.recalculateError": {
        "en": "Error recalculating",
        "fr": "Erreur lors du recalcul"
    },
    "admin.plans.recalculateSuccess": {
        "en": "Prices recalculated for {count} countries",
        "fr": "Prix recalculés pour {count} pays"
    },
    "admin.plans.quotaUpdated": {
        "en": "Quota updated for {plan}: {oldQuota} → {newQuota} questions",
        "fr": "Quota modifié pour {plan}: {oldQuota} → {newQuota} questions"
    },
    "admin.plans.nameUpdated": {
        "en": "Name updated for {plan}: {oldName} → {newName}",
        "fr": "Nom modifié pour {plan}: {oldName} → {newName}"
    },
    "admin.plans.title": {
        "en": "Subscription Plans Management",
        "fr": "Gestion des Plans d'Abonnement"
    },
    "admin.plans.subtitle": {
        "en": "Modify quotas and display names for each subscription tier",
        "fr": "Modifier les quotas et les noms d'affichage pour chaque niveau d'abonnement"
    },
    "admin.plans.plan": {
        "en": "Plan",
        "fr": "Plan"
    },
    "admin.plans.displayName": {
        "en": "Display Name",
        "fr": "Nom d'affichage"
    },
    "admin.plans.quota": {
        "en": "Quota",
        "fr": "Quota"
    },
    "admin.plans.basePriceUSD": {
        "en": "Base Price USD",
        "fr": "Prix de base USD"
    },
    "admin.plans.status": {
        "en": "Status",
        "fr": "Statut"
    },
    "admin.plans.actions": {
        "en": "Actions",
        "fr": "Actions"
    },
    "admin.plans.questions": {
        "en": "{quota} questions",
        "fr": "{quota} questions"
    },
    "admin.plans.active": {
        "en": "Active",
        "fr": "Actif"
    },
    "admin.plans.inactive": {
        "en": "Inactive",
        "fr": "Inactif"
    },
    "admin.plans.editQuota": {
        "en": "Edit quota",
        "fr": "Modifier le quota"
    },
    "admin.plans.editName": {
        "en": "Edit name",
        "fr": "Modifier le nom"
    },
    "admin.plans.quotaButton": {
        "en": "📊 Quota",
        "fr": "📊 Quota"
    },
    "admin.plans.nameButton": {
        "en": "✏️ Name",
        "fr": "✏️ Nom"
    },
    "admin.plans.noPlans": {
        "en": "No plans found",
        "fr": "Aucun plan trouvé"
    },
    "admin.plans.tierPricing": {
        "en": "Pricing by Tier (Tier 1-4)",
        "fr": "Prix par Tier (Tier 1-4)"
    },
    "admin.plans.tierPricingSubtitle": {
        "en": "Set USD prices for each tier level. Other currencies auto-convert.",
        "fr": "Définir les prix USD pour chaque niveau de tier. Les autres devises se convertissent automatiquement."
    },
    "admin.plans.tierEmerging": {
        "en": "(Emerging)",
        "fr": "(Émergent)"
    },
    "admin.plans.tierIntermediate": {
        "en": "(Intermediate)",
        "fr": "(Intermédiaire)"
    },
    "admin.plans.tierDeveloped": {
        "en": "(Developed)",
        "fr": "(Développés)"
    },
    "admin.plans.tierPremium": {
        "en": "(Premium)",
        "fr": "(Premium)"
    },
    "admin.plans.clickToEdit": {
        "en": "Click to edit",
        "fr": "Cliquer pour modifier"
    },
    "admin.plans.usdPricingNote": {
        "en": "All prices are in USD. Other currencies convert automatically based on the tier assigned to each country.",
        "fr": "Tous les prix sont en USD. Les autres devises se convertissent automatiquement selon le tier assigné à chaque pays."
    },

    # Quality Issues Tab
    "admin.quality.loadError": {
        "en": "Loading error",
        "fr": "Erreur de chargement"
    },
    "admin.quality.analyzeConfirm": {
        "en": "Run analysis on 50 Q&As? Estimated cost: ~$0.10",
        "fr": "Lancer une analyse de 50 Q&A? Coût estimé: ~$0.10"
    },
    "admin.quality.analysisComplete": {
        "en": "CoT Analysis complete! {issues} issues found in {total} Q&As ({percent}%)",
        "fr": "Analyse CoT terminée! {issues} problèmes détectés sur {total} Q&A ({percent}%)"
    },
    "admin.quality.analyzeError": {
        "en": "Error during CoT analysis: {error}",
        "fr": "Erreur lors de l'analyse CoT: {error}"
    },
    "admin.quality.markedFalsePositive": {
        "en": "Marked as false positive",
        "fr": "Marqué comme faux positif"
    },
    "admin.quality.markedReviewed": {
        "en": "Reviewed and confirmed",
        "fr": "Revu et confirmé"
    },
    "admin.quality.markError": {
        "en": "Error: {error}",
        "fr": "Erreur: {error}"
    },
    "admin.quality.deleteConfirm": {
        "en": "Are you sure you want to delete this Q&A?",
        "fr": "Êtes-vous sûr de vouloir supprimer cette Q&A ?"
    },
    "admin.quality.deleteError": {
        "en": "Error deleting Q&A: {error}",
        "fr": "Erreur lors de la suppression de la Q&A: {error}"
    },

    # Questions Tab
    "admin.questions.noQuestionsToExport": {
        "en": "❌ No questions to export in the selection",
        "fr": "❌ Aucune question à exporter dans la sélection"
    },

    # Currency Selector
    "admin.currency.loadError": {
        "en": "Error loading currencies",
        "fr": "Erreur de chargement des devises"
    },

    # Admin History Log
    "admin.history.loadError": {
        "en": "Error loading history",
        "fr": "Erreur lors du chargement de l'historique"
    },

    # Page Components (signup)
    "signup.passwordsMatch": {
        "en": "Passwords match",
        "fr": "Les mots de passe correspondent"
    },
    "signup.passwordsMismatch": {
        "en": "Passwords do not match",
        "fr": "Les mots de passe ne correspondent pas"
    },
    "signup.loading": {
        "en": "Loading...",
        "fr": "Chargement..."
    },
    "signup.acceptTerms": {
        "en": "By continuing, you accept our",
        "fr": "En continuant, vous acceptez nos"
    },
    "signup.and": {
        "en": " and our ",
        "fr": " et notre "
    },
    "signup.searchCountry": {
        "en": "Search for a country...",
        "fr": "Rechercher un pays..."
    },

    # Base components
    "components.close": {
        "en": "Close",
        "fr": "Fermer"
    },
    "components.delete": {
        "en": "Delete",
        "fr": "Supprimer"
    },
    "components.selectImage": {
        "en": "Select an image to upload",
        "fr": "Sélectionner une image à télécharger"
    },
    "components.toggleBilling": {
        "en": "Toggle billing cycle",
        "fr": "Basculer le cycle de facturation"
    },
    "components.subscriptionPlans": {
        "en": "Subscription plans",
        "fr": "Plans d'abonnement"
    },
    "components.cachedData": {
        "en": "Cached data",
        "fr": "Données en cache"
    }
}

def add_translations_to_file(file_path, lang_code):
    """Ajouter les traductions manquantes à un fichier de langue"""
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    added_count = 0
    for key, translations in ADMIN_TRANSLATIONS.items():
        if key not in data:
            if lang_code in translations:
                data[key] = translations[lang_code]
            elif lang_code == "fr":
                data[key] = translations["fr"]
            else:
                data[key] = translations["en"]
            added_count += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  Added {added_count} new translations to {file_path.name}")
    return added_count

def main():
    locales_dir = Path("frontend/public/locales")

    # Process en.json and fr.json
    for lang in ["en", "fr"]:
        file_path = locales_dir / f"{lang}.json"
        if file_path.exists():
            add_translations_to_file(file_path, lang)

    # Process other languages with English fallback
    other_langs = ["ar", "de", "es", "hi", "id", "it", "ja", "nl", "pl", "pt", "th", "tr", "vi", "zh"]
    for lang in other_langs:
        file_path = locales_dir / f"{lang}.json"
        if file_path.exists():
            add_translations_to_file(file_path, lang)

    print("\nDone!")

if __name__ == "__main__":
    main()
