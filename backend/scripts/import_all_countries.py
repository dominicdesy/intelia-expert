#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour importer tous les pays depuis REST Countries API
et les assigner aux bons tiers de pricing
"""

import os
import sys
import requests
import psycopg2
from psycopg2.extras import execute_batch

# Ajouter le chemin du backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")

# Classification des pays par tier économique
TIER_4_PREMIUM = [
    'CH', 'NO', 'LU', 'IS', 'IE', 'AU', 'QA', 'KW', 'US', 'CA', 'GB'
]

TIER_3_DEVELOPED = [
    'AT', 'BE', 'DK', 'FI', 'FR', 'DE', 'IT', 'NL', 'SE', 'ES', 'PT', 'GR',
    'JP', 'KR', 'SG', 'HK', 'NZ', 'AE', 'SA', 'IL', 'CZ', 'SI', 'SK', 'EE',
    'CY', 'MT', 'BH', 'OM'
]

TIER_2_INTERMEDIATE = [
    'PL', 'HU', 'RO', 'BG', 'HR', 'LT', 'LV', 'TR', 'MX', 'BR', 'AR', 'CL',
    'UY', 'CR', 'PA', 'RU', 'CN', 'TH', 'MY', 'PH', 'ID', 'VN', 'IN', 'ZA',
    'EG', 'MA', 'TN', 'JO', 'LB', 'CO', 'PE', 'EC', 'DO', 'GT', 'HN', 'SV',
    'NI', 'PY', 'BO', 'VE', 'RS', 'BA', 'MK', 'AL', 'ME', 'UA', 'BY', 'KZ',
    'GE', 'AM', 'AZ'
]

# Tier 1 = Tous les autres pays (émergents)

# Mapping devise par pays (les principaux)
CURRENCY_MAPPING = {
    'USD': ['US', 'EC', 'SV', 'PA', 'ZW'],  # Pays utilisant USD
    'EUR': [
        'AT', 'BE', 'CY', 'EE', 'FI', 'FR', 'DE', 'GR', 'IE', 'IT', 'LV', 'LT',
        'LU', 'MT', 'NL', 'PT', 'SK', 'SI', 'ES'
    ],
    'CAD': ['CA'],
    'GBP': ['GB'],
    'CHF': ['CH'],
    'AUD': ['AU'],
    'NOK': ['NO'],
}

# Symboles de devises
CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'CAD': 'CA$',
    'GBP': '£',
    'CHF': 'CHF',
    'AUD': 'A$',
    'NOK': 'kr',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
    'BRL': 'R$',
    'MXN': 'MX$',
    'ZAR': 'R',
    'SEK': 'kr',
    'DKK': 'kr',
}

def get_currency_for_country(country_code, country_currencies):
    """Détermine la devise à utiliser pour un pays"""
    # Vérifier si le pays utilise USD, EUR, CAD directement
    for currency, countries in CURRENCY_MAPPING.items():
        if country_code in countries:
            return currency

    # Sinon, utiliser la devise native du pays
    if country_currencies and len(country_currencies) > 0:
        # Prendre la première devise
        native_currency = list(country_currencies.keys())[0]

        # Si c'est une devise majeure, l'utiliser
        if native_currency in ['USD', 'EUR', 'CAD', 'GBP', 'CHF', 'AUD']:
            return native_currency

    # Par défaut, utiliser USD
    return 'USD'

def get_tier_for_country(country_code):
    """Détermine le tier de pricing pour un pays"""
    if country_code in TIER_4_PREMIUM:
        return 4
    elif country_code in TIER_3_DEVELOPED:
        return 3
    elif country_code in TIER_2_INTERMEDIATE:
        return 2
    else:
        return 1  # Tier 1 par défaut (marchés émergents)

def fetch_all_countries():
    """Récupère tous les pays depuis REST Countries API"""
    print("Fetching countries from REST Countries API...")

    try:
        response = requests.get(
            'https://restcountries.com/v3.1/all',
            params={'fields': 'cca2,name,currencies'},
            timeout=10
        )
        response.raise_for_status()
        countries = response.json()

        print(f"[OK] Fetched {len(countries)} countries")
        return countries

    except Exception as e:
        print(f"[ERROR] Error fetching countries: {e}")
        sys.exit(1)

def import_countries_to_db():
    """Importe tous les pays dans la base de données"""

    # Fetch countries from API
    countries_data = fetch_all_countries()

    # Préparer les données pour insertion
    countries_to_insert = []

    for country in countries_data:
        country_code = country.get('cca2')
        country_name = country.get('name', {}).get('common', 'Unknown')
        currencies = country.get('currencies', {})

        if not country_code:
            continue

        tier_level = get_tier_for_country(country_code)
        currency = get_currency_for_country(country_code, currencies)
        currency_symbol = CURRENCY_SYMBOLS.get(currency, currency)

        countries_to_insert.append({
            'country_code': country_code,
            'country_name': country_name,
            'tier_level': tier_level,
            'currency_code': currency,
            'currency_symbol': currency_symbol,
        })

    print(f"\nClassification:")
    tier_counts = {}
    for c in countries_to_insert:
        tier = c['tier_level']
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier in sorted(tier_counts.keys()):
        print(f"  Tier {tier}: {tier_counts[tier]} pays")

    # Insérer dans la base de données
    print(f"\n[DATABASE] Inserting {len(countries_to_insert)} countries into database...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Préparer la requête d'insertion
        insert_query = """
            INSERT INTO stripe_country_tiers
            (country_code, country_name, tier_level, currency_code, currency_symbol, active)
            VALUES (%(country_code)s, %(country_name)s, %(tier_level)s, %(currency_code)s, %(currency_symbol)s, TRUE)
            ON CONFLICT (country_code)
            DO UPDATE SET
                country_name = EXCLUDED.country_name,
                tier_level = EXCLUDED.tier_level,
                currency_code = EXCLUDED.currency_code,
                currency_symbol = EXCLUDED.currency_symbol
        """

        execute_batch(cur, insert_query, countries_to_insert, page_size=100)

        conn.commit()

        # Vérifier le résultat
        cur.execute("SELECT COUNT(*) FROM stripe_country_tiers WHERE active = TRUE")
        total = cur.fetchone()[0]

        print(f"[OK] Successfully imported! Total active countries: {total}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"[ERROR] Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("IMPORT ALL COUNTRIES TO STRIPE PRICING TIERS")
    print("=" * 60)

    if not DATABASE_URL:
        print("[ERROR] DATABASE_URL environment variable not set!")
        sys.exit(1)

    import_countries_to_db()

    print("\n[OK] Import completed successfully!")
    print("[INFO] Redemarrez le backend pour voir les changements dans l'interface admin")
