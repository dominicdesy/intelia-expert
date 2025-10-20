#!/usr/bin/env python3
"""
Validation script to ensure all countries have corresponding exchange rates
"""

import re

# Read the generated SQL file
with open('C:/intelia_gpt/intelia-expert/backend/sql/stripe/23_add_all_countries.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Extract all currencies from the rates table
rates_pattern = r"\('([A-Z]{3})',\s*'[^']+',\s*[\d.]+\)"
currencies_in_rates = set(re.findall(rates_pattern, sql_content))

# Extract all countries with their currencies
countries_pattern = r"\('([A-Z]{2})',\s*'([^']+)',\s*\d+,\s*'([A-Z]{3})',\s*'[^']+'\)"
countries_data = re.findall(countries_pattern, sql_content)

# Build a set of currencies used by countries
currencies_used_by_countries = set()
countries_by_currency = {}

for country_code, country_name, currency_code in countries_data:
    currencies_used_by_countries.add(currency_code)
    if currency_code not in countries_by_currency:
        countries_by_currency[currency_code] = []
    countries_by_currency[currency_code].append(f"{country_name} ({country_code})")

# Find missing currencies (used by countries but not in rates table)
missing_currencies = currencies_used_by_countries - currencies_in_rates

# Find unused currencies (in rates table but not used by any country)
unused_currencies = currencies_in_rates - currencies_used_by_countries

print("="*80)
print("VALIDATION REPORT: Countries vs Exchange Rates")
print("="*80)

print(f"\nTotal countries found: {len(countries_data)}")
print(f"Total unique currencies used by countries: {len(currencies_used_by_countries)}")
print(f"Total currencies in rates table: {len(currencies_in_rates)}")

print("\n" + "-"*80)
print("CURRENCIES USED BY COUNTRIES:")
print("-"*80)
for currency in sorted(currencies_used_by_countries):
    count = len(countries_by_currency[currency])
    status = "[OK]" if currency in currencies_in_rates else "[MISSING]"
    print(f"{status} {currency}: {count} countries")
    if currency not in currencies_in_rates:
        # Show which countries are affected
        for country in countries_by_currency[currency][:5]:  # Show first 5
            print(f"    - {country}")
        if len(countries_by_currency[currency]) > 5:
            print(f"    ... and {len(countries_by_currency[currency]) - 5} more")

if missing_currencies:
    print("\n" + "="*80)
    print("WARNING: MISSING EXCHANGE RATES")
    print("="*80)
    print(f"\nThe following {len(missing_currencies)} currencies are used by countries but have NO exchange rate:")
    for currency in sorted(missing_currencies):
        print(f"\n  {currency}:")
        for country in countries_by_currency[currency]:
            print(f"    - {country}")
    print("\nACTION REQUIRED: Add these currencies to the exchange rates API or assign USD fallback")
else:
    print("\n" + "="*80)
    print("SUCCESS: All countries have corresponding exchange rates!")
    print("="*80)

if unused_currencies:
    print("\n" + "-"*80)
    print("INFO: Unused currencies in rates table")
    print("-"*80)
    print(f"\nThese {len(unused_currencies)} currencies are in the rates table but not used by any country:")
    for currency in sorted(unused_currencies):
        print(f"  - {currency}")
    print("\nThese can be safely removed or kept for future use.")

print("\n" + "="*80)
print("VALIDATION COMPLETE")
print("="*80)
