#!/usr/bin/env python3
"""
Script pour remplacer le texte hardcodé dans CountryPricingManager.tsx
"""
import re
from pathlib import Path

file_path = Path("frontend/app/admin/subscriptions/components/CountryPricingManager.tsx")

replacements = {
    '"A-Z"': 't("admin.pricing.sortAZ")',
    '                Pays': '                {t("admin.pricing.country")}',
    '                Tier': '                {t("admin.pricing.tier")}',
    '                Actions': '                {t("admin.plans.actions")}',
    '                        <option value={1}>Tier 1</option>': '                        <option value={1}>{t("admin.pricing.tierLevel", { level: 1 })}</option>',
    '                        <option value={2}>Tier 2</option>': '                        <option value={2}>{t("admin.pricing.tierLevel", { level: 2 })}</option>',
    '                        <option value={3}>Tier 3</option>': '                        <option value={3}>{t("admin.pricing.tierLevel", { level: 3 })}</option>',
    '                        <option value={4}>Tier 4</option>': '                        <option value={4}>{t("admin.pricing.tierLevel", { level: 4 })}</option>',
    '"Sauvegarder"': 't("admin.pricing.save")',
    '"Annuler"': 't("admin.pricing.cancel")',
    '                      Tier {country.tier_level}': '                      {t("admin.pricing.tierLevel", { level: country.tier_level })}',
    '                              title="Prix marketing calculé automatiquement depuis le tier"': '                              title={t("admin.pricing.marketingPriceTooltip")}',
    '                              title="Prix personnalisé défini manuellement"': '                              title={t("admin.pricing.customPriceTooltip")}',
    '                          ✏️  Modifier...': '                          {t("admin.pricing.editButton")}',
    '                        title="Supprimer ce pays"': '                        title={t("admin.pricing.deleteButton")}',
    '            ? `Aucun pays trouvé pour "${searchTerm}"`': '            ? t("admin.pricing.noCountriesFound", { search: searchTerm })',
    '            : "Aucun pays configuré"}': '            : t("admin.pricing.noCountries")}',
    '              Tier 1 (Marchés émergents)': '              {t("admin.pricing.tier1")}',
    '              Tier 2 (Intermédiaire)': '              {t("admin.pricing.tier2")}',
    '              Tier 3 (Développés)': '              {t("admin.pricing.tier3")}',
    '              Tier 4 (Premium)': '              {t("admin.pricing.tier4")}',
    '              <span>Prix marketing automatique</span>': '              <span>{t("admin.pricing.marketingPrice")}</span>',
    '              <span>Prix personnalisé</span>': '              <span>{t("admin.pricing.customPrice")}</span>',
    '          Vous pouvez personnaliser n\'importe quel prix en cliquant sur "Modifier" (devient "Custom").': '          {t("admin.pricing.customizeNote")}',
}

print(f"Processing {file_path}...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

original_content = content
replaced_count = 0

for old_text, new_text in replacements.items():
    if old_text in content:
        content = content.replace(old_text, new_text)
        replaced_count += 1
        print(f"  [OK] Replaced: {old_text[:60]}...")

if content != original_content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n[OK] Made {replaced_count} replacements")
else:
    print("  No changes needed")
