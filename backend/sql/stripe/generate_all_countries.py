#!/usr/bin/env python3
"""
Script to generate SQL insert statements for all countries from REST Countries API
Automatically assigns tier levels based on economic classification
Fetches real-time exchange rates from Frankfurter API
"""

import json
import requests
from datetime import datetime

# Fetch all countries from REST Countries API
print("Fetching countries from REST Countries API...")
response = requests.get("https://restcountries.com/v3.1/all?fields=cca2,name,currencies,region,subregion")
countries_data = response.json()
print(f"Found {len(countries_data)} countries")

# Fetch real-time exchange rates from Frankfurter API (free, no API key required)
print("\nFetching real-time exchange rates from Frankfurter API...")
rates_data = None
try:
    rates_response = requests.get("https://api.frankfurter.app/latest?from=USD")
    rates_data = rates_response.json()
    # Convert to rate_to_usd (inverse the rates since they're FROM USD)
    exchange_rates = {}
    exchange_rates['USD'] = 1.0

    for currency, rate in rates_data['rates'].items():
        # Frankfurter gives us USD -> XXX rate, we need XXX -> USD rate
        # So we invert: if 1 USD = 1.35 CAD, then 1 CAD = 1/1.35 USD = 0.74 USD
        exchange_rates[currency] = round(1.0 / rate, 6)

    print(f"Fetched {len(exchange_rates)} exchange rates (last updated: {rates_data['date']})")
    print(f"Sample rates: CAD={exchange_rates.get('CAD', 'N/A')}, EUR={exchange_rates.get('EUR', 'N/A')}, GBP={exchange_rates.get('GBP', 'N/A')}")
except Exception as e:
    print(f"Warning: Could not fetch live exchange rates: {e}")
    print("Using fallback rates...")
    exchange_rates = {
        'USD': 1.0,
        'CAD': 0.74,
        'EUR': 1.08,
        'GBP': 1.27,
    }

# Tier 4 - Premium Markets (High GDP per capita, developed economies)
TIER_4_COUNTRIES = {
    'US', 'CA', 'GB', 'AU', 'CH', 'NO', 'LU', 'IE', 'IS', 'QA', 'KW', 'AE', 'SG', 'HK'
}

# Tier 3 - Developed Markets (Western Europe, Japan, South Korea, etc.)
TIER_3_COUNTRIES = {
    'FR', 'DE', 'NL', 'BE', 'AT', 'SE', 'DK', 'FI', 'JP', 'KR', 'NZ', 'TW', 'IT', 'ES', 'PT'
}

# Tier 2 - Intermediate Markets (Eastern Europe, Middle East, Latin America upper tier)
TIER_2_REGIONS = {'Eastern Europe', 'Southern Europe', 'Western Asia'}
TIER_2_COUNTRIES = {
    'CZ', 'HU', 'SK', 'SI', 'EE', 'LV', 'LT', 'GR', 'CL', 'ZA', 'TR', 'RU', 'SA', 'IL'
}

# Currency preferences for regions
CURRENCY_PREFERENCES = {
    'Europe': ('EUR', '€'),
    'Americas': ('USD', '$'),
    'Africa': ('USD', '$'),
    'Asia': ('USD', '$'),
    'Oceania': ('USD', '$'),
}

def get_tier_for_country(code, region, subregion):
    """Determine tier level for a country"""
    if code in TIER_4_COUNTRIES:
        return 4
    elif code in TIER_3_COUNTRIES:
        return 3
    elif code in TIER_2_COUNTRIES or subregion in TIER_2_REGIONS:
        return 2
    else:
        return 1  # Default: Tier 1 for emerging markets

def get_currency_for_country(code, currencies, region):
    """Get currency code and symbol for a country"""
    # Special cases with their own currencies
    CURRENCY_MAP = {
        'CA': ('CAD', 'CA$'),
        'GB': ('GBP', '£'),
        'AU': ('AUD', 'A$'),
        'CH': ('CHF', 'CHF'),
        'NO': ('NOK', 'kr'),
        'NZ': ('NZD', 'NZ$'),
        'JP': ('JPY', '¥'),
        'KR': ('KRW', '₩'),
        'IN': ('INR', '₹'),
        'BR': ('BRL', 'R$'),
        'MX': ('MXN', '$'),
        'ZA': ('ZAR', 'R'),
        'CN': ('CNY', '¥'),
        'RU': ('RUB', '₽'),
        'TR': ('TRY', '₺'),
        'IL': ('ILS', '₪'),
        'SA': ('SAR', 'SR'),
        'AE': ('AED', 'د.إ'),
        'QA': ('QAR', 'QR'),
        'KW': ('KWD', 'KD'),
        'SE': ('SEK', 'kr'),
        'DK': ('DKK', 'kr'),
        'PL': ('PLN', 'zł'),
        'CZ': ('CZK', 'Kč'),
        'HU': ('HUF', 'Ft'),
        'TH': ('THB', '฿'),
        'ID': ('IDR', 'Rp'),
        'MY': ('MYR', 'RM'),
        'SG': ('SGD', 'S$'),
        'HK': ('HKD', 'HK$'),
        'PH': ('PHP', '₱'),
        'VN': ('VND', '₫'),
        'AR': ('ARS', '$'),
        'CL': ('CLP', '$'),
        'CO': ('COP', '$'),
        'PE': ('PEN', 'S/'),
    }

    if code in CURRENCY_MAP:
        return CURRENCY_MAP[code]

    # Try to use the country's actual currency from API
    if currencies:
        try:
            first_currency = list(currencies.values())[0]
            curr_code = list(currencies.keys())[0]
            curr_symbol = first_currency.get('symbol', '$')

            # Use EUR for eurozone countries
            if curr_code == 'EUR':
                return ('EUR', '€')

            # For other currencies, check if it's a major one
            if curr_code in ['USD', 'GBP', 'CAD', 'AUD', 'EUR', 'CHF', 'JPY']:
                return (curr_code, curr_symbol)
        except:
            pass

    # Default: use regional preference
    return CURRENCY_PREFERENCES.get(region, ('USD', '$'))

# Process all countries
countries_by_tier = {1: [], 2: [], 3: [], 4: []}

for country in countries_data:
    code = country.get('cca2')
    name = country.get('name', {}).get('common', 'Unknown')
    currencies = country.get('currencies', {})
    region = country.get('region', 'Unknown')
    subregion = country.get('subregion', '')

    # Skip countries without valid code
    if not code or len(code) != 2:
        continue

    # Skip Antarctica and other non-standard regions
    if region in ['Antarctic']:
        continue

    tier = get_tier_for_country(code, region, subregion)
    currency_code, currency_symbol = get_currency_for_country(code, currencies, region)

    # Escape single quotes in country names
    name = name.replace("'", "''")
    currency_symbol = currency_symbol.replace("'", "''")

    countries_by_tier[tier].append({
        'code': code,
        'name': name,
        'tier': tier,
        'currency_code': currency_code,
        'currency_symbol': currency_symbol
    })

# Collect all unique currencies used by countries
used_currencies = set()
for tier in countries_by_tier.values():
    for country in tier:
        used_currencies.add(country['currency_code'])

# Map currency codes to friendly names
CURRENCY_NAMES = {
    'USD': 'US Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'CAD': 'Canadian Dollar',
    'AUD': 'Australian Dollar',
    'CHF': 'Swiss Franc',
    'JPY': 'Japanese Yen',
    'CNY': 'Chinese Yuan',
    'INR': 'Indian Rupee',
    'BRL': 'Brazilian Real',
    'MXN': 'Mexican Peso',
    'ZAR': 'South African Rand',
    'RUB': 'Russian Ruble',
    'TRY': 'Turkish Lira',
    'KRW': 'South Korean Won',
    'IDR': 'Indonesian Rupiah',
    'THB': 'Thai Baht',
    'MYR': 'Malaysian Ringgit',
    'SGD': 'Singapore Dollar',
    'HKD': 'Hong Kong Dollar',
    'NOK': 'Norwegian Krone',
    'SEK': 'Swedish Krona',
    'DKK': 'Danish Krone',
    'PLN': 'Polish Zloty',
    'CZK': 'Czech Koruna',
    'HUF': 'Hungarian Forint',
    'ILS': 'Israeli Shekel',
    'PHP': 'Philippine Peso',
    'VND': 'Vietnamese Dong',
    'AED': 'UAE Dirham',
    'SAR': 'Saudi Riyal',
    'QAR': 'Qatari Riyal',
    'KWD': 'Kuwaiti Dinar',
    'ARS': 'Argentine Peso',
    'CLP': 'Chilean Peso',
    'COP': 'Colombian Peso',
    'PEN': 'Peruvian Sol',
    'NZD': 'New Zealand Dollar',
}

# Generate SQL file
current_date = datetime.now().strftime('%Y-%m-%d')
rates_date = rates_data.get('date', current_date) if rates_data else current_date

sql_output = """-- ============================================================================
-- ALL COUNTRIES FROM REST COUNTRIES API
-- Auto-generated script to insert all world countries
-- Total countries: {total}
-- Generated: {date}
-- Exchange rates from: Frankfurter API (European Central Bank)
-- ============================================================================

-- First, let's add all currencies with LIVE exchange rates
-- Source: https://api.frankfurter.app/latest?from=USD
-- Last updated: {rates_date}
INSERT INTO stripe_currency_rates (currency_code, currency_name, rate_to_usd) VALUES
""".format(
    total=sum(len(countries_by_tier[t]) for t in countries_by_tier),
    date=current_date,
    rates_date=rates_date
)

# Add currency rates dynamically
currency_values = []
for currency_code in sorted(used_currencies):
    rate = exchange_rates.get(currency_code, 1.0)  # Default to 1.0 if not found
    currency_name = CURRENCY_NAMES.get(currency_code, currency_code)
    # Format rate with proper decimal notation (avoid scientific notation like 6e-05)
    if rate < 0.001:
        rate_str = f"{rate:.8f}"  # Use 8 decimals for very small values
    else:
        rate_str = f"{rate:.6f}"  # Use 6 decimals for normal values
    currency_values.append(f"('{currency_code}', '{currency_name}', {rate_str})")

sql_output += ',\n'.join(currency_values)
sql_output += """
ON CONFLICT (currency_code) DO UPDATE SET
    rate_to_usd = EXCLUDED.rate_to_usd,
    last_updated = CURRENT_TIMESTAMP;

"""

# Add countries by tier
for tier in [1, 2, 3, 4]:
    tier_names = {
        1: 'Emerging Markets',
        2: 'Intermediate Markets',
        3: 'Developed Markets',
        4: 'Premium Markets'
    }

    tier_prices = {
        1: '8.99$ Pro / 9.99$ Elite',
        2: '10.99$ Pro / 15.99$ Elite',
        3: '15.99$ Pro / 23.99$ Elite',
        4: '19.99$ Pro / 31.99$ Elite'
    }

    countries = countries_by_tier[tier]
    if not countries:
        continue

    sql_output += f"\n-- TIER {tier} - {tier_names[tier]} ({tier_prices[tier]})\n"
    sql_output += "-- Total: {} countries\n".format(len(countries))
    sql_output += "INSERT INTO stripe_country_tiers (country_code, country_name, tier_level, currency_code, currency_symbol) VALUES\n"

    values = []
    for country in countries:
        values.append("('{}', '{}', {}, '{}', '{}')".format(
            country['code'],
            country['name'],
            country['tier'],
            country['currency_code'],
            country['currency_symbol']
        ))

    sql_output += ',\n'.join(values)
    sql_output += "\nON CONFLICT (country_code) DO UPDATE SET\n"
    sql_output += "    country_name = EXCLUDED.country_name,\n"
    sql_output += "    tier_level = EXCLUDED.tier_level,\n"
    sql_output += "    currency_code = EXCLUDED.currency_code,\n"
    sql_output += "    currency_symbol = EXCLUDED.currency_symbol,\n"
    sql_output += "    updated_at = CURRENT_TIMESTAMP;\n"

sql_output += """
-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count countries by tier
SELECT tier_level, COUNT(*) as country_count
FROM stripe_country_tiers
WHERE active = TRUE
GROUP BY tier_level
ORDER BY tier_level;

-- Show sample countries from each tier
SELECT tier_level, country_code, country_name, currency_code
FROM stripe_country_tiers
WHERE active = TRUE
ORDER BY tier_level, country_name
LIMIT 20;
"""

# Write to file
output_file = 'C:/intelia_gpt/intelia-expert/backend/sql/stripe/23_add_all_countries.sql'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(sql_output)

print(f"\nSQL file generated: {output_file}")
print(f"\nCountries by tier:")
for tier in [1, 2, 3, 4]:
    print(f"  Tier {tier}: {len(countries_by_tier[tier])} countries")
print(f"\nTotal: {sum(len(countries_by_tier[t]) for t in countries_by_tier)} countries")
