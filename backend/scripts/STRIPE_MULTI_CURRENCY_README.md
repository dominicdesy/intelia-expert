# Stripe Multi-Currency Price Setup

**Date**: 2025-10-28
**Version**: 1.0.0

## Overview

This script creates Stripe prices for all supported billing currencies (16 currencies) for both Pro and Elite plans, with monthly and yearly billing cycles.

## Supported Currencies

16 currencies covering 87-90% of global market:

| Currency | Code | Countries/Regions |
|----------|------|-------------------|
| US Dollar | USD | United States, international default |
| Euro | EUR | Eurozone (France, Germany, Spain, Italy, etc.) |
| Chinese Yuan | CNY | China (Top #1 producer) |
| Indian Rupee | INR | India (Top #2 eggs, #5 chicken) |
| Brazilian Real | BRL | Brazil (Top #3 chicken) |
| Indonesian Rupiah | IDR | Indonesia (Top #3 eggs, #6 chicken) |
| Mexican Peso | MXN | Mexico |
| Japanese Yen | JPY | Japan (Top #8 eggs) |
| Turkish Lira | TRY | Turkey |
| British Pound | GBP | United Kingdom |
| South African Rand | ZAR | South Africa |
| Thai Baht | THB | Thailand |
| Malaysian Ringgit | MYR | Malaysia |
| Philippine Peso | PHP | Philippines |
| Polish Zloty | PLN | Poland |
| Vietnamese Dong | VND | Vietnam |

## Prerequisites

### 1. Stripe Account Setup

1. Create Stripe account at https://stripe.com
2. Complete account verification
3. Enable multi-currency support:
   - Go to Settings → Payment methods
   - Enable "Multiple currencies"
   - Add desired currencies

### 2. API Keys

Get your Stripe API keys:

**Test Mode** (for development):
```bash
export STRIPE_TEST_KEY="sk_test_..."
```

**Production Mode**:
```bash
export STRIPE_API_KEY="sk_live_..."
```

### 3. Python Dependencies

```bash
pip install stripe
```

## Usage

### Test Mode (Recommended First)

```bash
# Create all prices in test mode
python backend/scripts/stripe_multi_currency_prices.py --mode test

# Create prices for specific currencies
python backend/scripts/stripe_multi_currency_prices.py --mode test --currencies USD EUR CNY

# Create prices for specific plans
python backend/scripts/stripe_multi_currency_prices.py --mode test --plans pro
```

### Production Mode

**⚠️ WARNING**: Only run in production after testing!

```bash
# Create all production prices
python backend/scripts/stripe_multi_currency_prices.py --mode production
```

## Pricing Structure

### Monthly Prices (USD base)

- **Pro Plan**: $18.00/month
- **Elite Plan**: $28.00/month

### Yearly Prices (15% discount)

- **Pro Plan**: $183.60/year (equivalent to $15.30/month)
- **Elite Plan**: $285.60/year (equivalent to $23.80/month)

### Exchange Rates

The script uses approximate exchange rates. Update `EXCHANGE_RATES` in the script periodically:

```python
EXCHANGE_RATES = {
    "USD": 1.00,
    "EUR": 0.92,
    "CNY": 7.25,
    # ... update as needed
}
```

## Script Output

Example output:

```
======================================================================
Stripe Multi-Currency Price Creation
Mode: TEST
======================================================================

──────────────────────────────────────────────────────────────────────
Creating prices for: PRO
──────────────────────────────────────────────────────────────────────
✓ Found existing product: Pro Plan (prod_abc123)

USD:
  ✓ Created: 18.00 USD / month (ID: price_xyz789)
  ✓ Created: 183.60 USD / year (ID: price_abc456)

EUR:
  ✓ Created: 16.56 EUR / month (ID: price_def789)
  ✓ Created: 168.91 EUR / year (ID: price_ghi012)

...

======================================================================
SUMMARY
======================================================================

PRO Plan:
  Monthly: 16 created, 0 already exist, 0 errors
  Yearly:  16 created, 0 already exist, 0 errors

ELITE Plan:
  Monthly: 16 created, 0 already exist, 0 errors
  Yearly:  16 created, 0 already exist, 0 errors

======================================================================

✓ Multi-currency price creation complete!

Next steps:
1. Verify prices in Stripe Dashboard
2. Update backend checkout flow to use currency-specific prices
3. Test checkout with different currencies
```

## Verification

### 1. Check Stripe Dashboard

Go to: **Products** → Select product → **Pricing**

Verify:
- All currencies are present
- Amounts are correct
- Both monthly and yearly cycles exist

### 2. Test API Access

```bash
# List all prices for a product
stripe prices list --product prod_abc123
```

### 3. SQL Verification

Query database to check user currency preferences:

```sql
SELECT
    billing_currency,
    COUNT(*) as user_count
FROM user_billing_info
WHERE billing_currency IS NOT NULL
GROUP BY billing_currency
ORDER BY user_count DESC;
```

## Integration with Backend

The backend (`backend/app/api/v1/stripe_routes.py`) needs to:

1. **Fetch user's billing currency**:
```python
user_currency = user_billing_info.get("billing_currency", "USD")
```

2. **Find appropriate Stripe price**:
```python
# Get all prices for product
prices = stripe.Price.list(product=product_id, active=True)

# Filter by currency and billing cycle
matching_price = [
    p for p in prices.data
    if p.currency.upper() == user_currency
    and p.recurring.interval == billing_cycle
][0]
```

3. **Create checkout session with currency-specific price**:
```python
checkout_session = stripe.checkout.Session.create(
    line_items=[{
        'price': matching_price.id,  # Currency-specific price ID
        'quantity': 1,
    }],
    mode='subscription',
    # ... other params
)
```

## Troubleshooting

### Error: "Currency not supported"

**Solution**: Enable the currency in Stripe Dashboard:
- Settings → Payment methods → Multiple currencies
- Add the desired currency

### Error: "Amount below minimum"

**Solution**: Update `MINIMUM_AMOUNTS` in script to match Stripe requirements:
- https://stripe.com/docs/currencies#minimum-and-maximum-charge-amounts

### Prices Don't Match Expected Amount

**Solution**: Update exchange rates in `EXCHANGE_RATES` dictionary.

### Product Not Found

**Solution**: Create products manually in Stripe Dashboard first, or let script auto-create them.

## Maintenance

### Update Exchange Rates (Monthly)

```bash
# Edit script
nano backend/scripts/stripe_multi_currency_prices.py

# Find EXCHANGE_RATES dictionary
# Update rates from https://www.xe.com or similar

# Re-run script (will update existing prices)
python backend/scripts/stripe_multi_currency_prices.py --mode production
```

### Add New Currency

1. Add currency to `SUPPORTED_CURRENCIES`
2. Add exchange rate to `EXCHANGE_RATES`
3. Add minimum amount to `MINIMUM_AMOUNTS`
4. Update database constraint in `24_add_billing_currency_preference.sql`
5. Update backend `SUPPORTED_BILLING_CURRENCIES` constant
6. Run script to create prices

## Security Notes

- ⚠️ **Never commit API keys to git**
- Use environment variables for keys
- Use test mode for development
- Test thoroughly before production run
- Keep exchange rates updated

## Support

For issues:
1. Check Stripe API logs in Dashboard
2. Review script output for error messages
3. Verify API key has correct permissions
4. Check Stripe account settings

## References

- Stripe Multi-Currency: https://stripe.com/docs/currencies
- Stripe Prices API: https://stripe.com/docs/api/prices
- Stripe Products: https://stripe.com/docs/api/products
- Supported Currencies: https://stripe.com/docs/currencies
