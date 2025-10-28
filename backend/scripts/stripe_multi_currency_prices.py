#!/usr/bin/env python3
"""
Stripe Multi-Currency Price Creation Script
Version: 1.0.0
Date: 2025-10-28

This script creates Stripe prices for all supported currencies.
It should be run once to set up multi-currency pricing.

Usage:
    python stripe_multi_currency_prices.py --mode production
    python stripe_multi_currency_prices.py --mode test

Requirements:
    - Stripe API key in environment variable STRIPE_API_KEY or STRIPE_TEST_KEY
    - Products already created in Stripe (Pro, Elite)
"""

import os
import sys
import stripe
import argparse
from typing import Dict, List

# ============================================================================
# CONFIGURATION
# ============================================================================

# Supported currencies (16 currencies covering 87-90% of global market)
SUPPORTED_CURRENCIES = [
    "USD", "EUR", "CNY", "INR", "BRL", "IDR", "MXN", "JPY",
    "TRY", "GBP", "ZAR", "THB", "MYR", "PHP", "PLN", "VND"
]

# Base prices in USD (monthly)
BASE_PRICES_USD = {
    "pro": 18.00,
    "elite": 28.00,
    "pro_yearly": 183.60,  # 18 * 12 * 0.85 (15% discount)
    "elite_yearly": 285.60,  # 28 * 12 * 0.85 (15% discount)
}

# Currency exchange rates (approximate, update periodically)
# These are relative to USD
EXCHANGE_RATES = {
    "USD": 1.00,
    "EUR": 0.92,    # Euro
    "CNY": 7.25,    # Chinese Yuan
    "INR": 83.00,   # Indian Rupee
    "BRL": 4.98,    # Brazilian Real
    "IDR": 15600,   # Indonesian Rupiah
    "MXN": 17.00,   # Mexican Peso
    "JPY": 149.50,  # Japanese Yen
    "TRY": 28.50,   # Turkish Lira
    "GBP": 0.79,    # British Pound
    "ZAR": 18.50,   # South African Rand
    "THB": 35.00,   # Thai Baht
    "MYR": 4.68,    # Malaysian Ringgit
    "PHP": 56.00,   # Philippine Peso
    "PLN": 4.05,    # Polish Zloty
    "VND": 24500,   # Vietnamese Dong
}

# Minimum charge per currency (Stripe requirements)
# https://stripe.com/docs/currencies#minimum-and-maximum-charge-amounts
MINIMUM_AMOUNTS = {
    "USD": 0.50, "EUR": 0.50, "GBP": 0.30, "CNY": 3.00,
    "INR": 0.50, "BRL": 0.50, "IDR": 7000, "MXN": 10,
    "JPY": 50, "TRY": 1.50, "ZAR": 10, "THB": 20,
    "MYR": 2, "PHP": 25, "PLN": 2, "VND": 12000
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def convert_price(usd_price: float, target_currency: str) -> int:
    """
    Convert USD price to target currency and return in cents/smallest unit.

    Args:
        usd_price: Price in USD (e.g., 18.00)
        target_currency: Target currency code (e.g., "EUR")

    Returns:
        Price in smallest currency unit (cents, pence, etc.)
    """
    rate = EXCHANGE_RATES.get(target_currency, 1.00)
    converted = usd_price * rate

    # Zero-decimal currencies (no cents): JPY, VND, etc.
    zero_decimal_currencies = ["BIF", "CLP", "DJF", "GNF", "JPY", "KMF",
                               "KRW", "MGA", "PYG", "RWF", "UGX",
                               "VND", "VUV", "XAF", "XOF", "XPF"]

    if target_currency in zero_decimal_currencies:
        # Round to nearest whole number
        return int(round(converted))
    else:
        # Convert to cents (multiply by 100)
        return int(round(converted * 100))

def ensure_minimum_amount(amount: int, currency: str) -> int:
    """
    Ensure price meets Stripe minimum amount requirement.

    Args:
        amount: Price in smallest unit
        currency: Currency code

    Returns:
        Adjusted amount if below minimum
    """
    minimum = MINIMUM_AMOUNTS.get(currency, 50)  # Default 50 cents
    return max(amount, minimum)

def format_price_display(amount: int, currency: str) -> str:
    """
    Format price for display (e.g., "$18.00", "€16.56").

    Args:
        amount: Price in smallest unit
        currency: Currency code

    Returns:
        Formatted price string
    """
    zero_decimal = currency in ["JPY", "VND"]

    if zero_decimal:
        return f"{amount:,} {currency}"
    else:
        return f"{amount / 100:.2f} {currency}"

# ============================================================================
# STRIPE PRICE CREATION
# ============================================================================

def get_or_create_product(plan_name: str, mode: str = "test") -> str:
    """
    Get existing Stripe product ID or create new product.

    Args:
        plan_name: Plan name ("pro" or "elite")
        mode: "test" or "production"

    Returns:
        Stripe product ID
    """
    product_names = {
        "pro": "Pro Plan",
        "elite": "Elite Plan"
    }

    try:
        # Search for existing product
        products = stripe.Product.list(limit=100)
        for product in products.auto_paging_iter():
            if product.name == product_names.get(plan_name):
                print(f"✓ Found existing product: {product.name} ({product.id})")
                return product.id

        # Create new product if not found
        print(f"Creating new product: {product_names.get(plan_name)}...")
        product = stripe.Product.create(
            name=product_names.get(plan_name),
            description=f"Intelia Expert {plan_name.capitalize()} Subscription",
            metadata={"plan": plan_name}
        )
        print(f"✓ Created product: {product.name} ({product.id})")
        return product.id

    except stripe.error.StripeError as e:
        print(f"✗ Error creating product: {e}")
        sys.exit(1)

def create_price(
    product_id: str,
    plan_name: str,
    currency: str,
    recurring_interval: str = "month"
) -> Dict:
    """
    Create a Stripe price for a product in a specific currency.

    Args:
        product_id: Stripe product ID
        plan_name: Plan name ("pro" or "elite")
        currency: Currency code (e.g., "USD")
        recurring_interval: "month" or "year"

    Returns:
        Dictionary with price details
    """
    # Determine base price
    if recurring_interval == "year":
        base_usd_price = BASE_PRICES_USD.get(f"{plan_name}_yearly")
    else:
        base_usd_price = BASE_PRICES_USD.get(plan_name)

    # Convert to target currency
    amount = convert_price(base_usd_price, currency)
    amount = ensure_minimum_amount(amount, currency)

    try:
        # Check if price already exists
        existing_prices = stripe.Price.list(
            product=product_id,
            currency=currency.lower(),
            recurring={"interval": recurring_interval},
            limit=10
        )

        for existing_price in existing_prices.data:
            if existing_price.unit_amount == amount:
                print(f"  → Price already exists: {format_price_display(amount, currency)} / {recurring_interval}")
                return {
                    "id": existing_price.id,
                    "currency": currency,
                    "amount": amount,
                    "interval": recurring_interval,
                    "status": "exists"
                }

        # Create new price
        price = stripe.Price.create(
            product=product_id,
            unit_amount=amount,
            currency=currency.lower(),
            recurring={"interval": recurring_interval, "interval_count": 1},
            metadata={
                "plan": plan_name,
                "billing_cycle": recurring_interval
            }
        )

        print(f"  ✓ Created: {format_price_display(amount, currency)} / {recurring_interval} (ID: {price.id})")

        return {
            "id": price.id,
            "currency": currency,
            "amount": amount,
            "interval": recurring_interval,
            "status": "created"
        }

    except stripe.error.StripeError as e:
        print(f"  ✗ Error creating price for {currency}: {e}")
        return {
            "currency": currency,
            "error": str(e),
            "status": "error"
        }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Create multi-currency Stripe prices for Intelia Expert"
    )
    parser.add_argument(
        "--mode",
        choices=["test", "production"],
        default="test",
        help="Stripe mode (test or production)"
    )
    parser.add_argument(
        "--currencies",
        nargs="+",
        default=SUPPORTED_CURRENCIES,
        help="Specific currencies to create (default: all)"
    )
    parser.add_argument(
        "--plans",
        nargs="+",
        choices=["pro", "elite"],
        default=["pro", "elite"],
        help="Plans to create prices for"
    )

    args = parser.parse_args()

    # Configure Stripe API key
    if args.mode == "production":
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        if not stripe.api_key:
            print("✗ Error: STRIPE_API_KEY environment variable not set")
            sys.exit(1)
    else:
        stripe.api_key = os.getenv("STRIPE_TEST_KEY")
        if not stripe.api_key:
            print("✗ Error: STRIPE_TEST_KEY environment variable not set")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"Stripe Multi-Currency Price Creation")
    print(f"Mode: {args.mode.upper()}")
    print(f"{'='*70}\n")

    results = {
        "pro": {"monthly": [], "yearly": []},
        "elite": {"monthly": [], "yearly": []}
    }

    # Process each plan
    for plan_name in args.plans:
        print(f"\n{'─'*70}")
        print(f"Creating prices for: {plan_name.upper()}")
        print(f"{'─'*70}")

        # Get or create product
        product_id = get_or_create_product(plan_name, args.mode)

        # Create prices for each currency
        for currency in args.currencies:
            print(f"\n{currency}:")

            # Monthly price
            monthly_result = create_price(product_id, plan_name, currency, "month")
            results[plan_name]["monthly"].append(monthly_result)

            # Yearly price
            yearly_result = create_price(product_id, plan_name, currency, "year")
            results[plan_name]["yearly"].append(yearly_result)

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")

    for plan_name in args.plans:
        monthly_created = sum(1 for r in results[plan_name]["monthly"] if r.get("status") == "created")
        monthly_exists = sum(1 for r in results[plan_name]["monthly"] if r.get("status") == "exists")
        monthly_errors = sum(1 for r in results[plan_name]["monthly"] if r.get("status") == "error")

        yearly_created = sum(1 for r in results[plan_name]["yearly"] if r.get("status") == "created")
        yearly_exists = sum(1 for r in results[plan_name]["yearly"] if r.get("status") == "exists")
        yearly_errors = sum(1 for r in results[plan_name]["yearly"] if r.get("status") == "error")

        print(f"{plan_name.upper()} Plan:")
        print(f"  Monthly: {monthly_created} created, {monthly_exists} already exist, {monthly_errors} errors")
        print(f"  Yearly:  {yearly_created} created, {yearly_exists} already exist, {yearly_errors} errors")
        print()

    print(f"{'='*70}\n")
    print("✓ Multi-currency price creation complete!")
    print("\nNext steps:")
    print("1. Verify prices in Stripe Dashboard")
    print("2. Update backend checkout flow to use currency-specific prices")
    print("3. Test checkout with different currencies")

if __name__ == "__main__":
    main()
