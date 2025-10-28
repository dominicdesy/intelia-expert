# Billing Currency Preference System

## Overview

This system allows users to select their preferred billing currency from **16 supported currencies** for Stripe payments while displaying prices in their local currency.

**16 Supported Currencies** (covering 87-90% of global poultry production):
- USD, EUR, CNY, INR, BRL, IDR, MXN, JPY, TRY, GBP, ZAR, THB, MYR, PHP, PLN, VND

## Architecture

```
User visits /billing/plans
  ↓
Geo-location detects country via IP
  ↓
Display prices in local currency (e.g., ¥2,999 for Japan)
  ↓
User upgrades to paid plan
  ↓
System checks if billing_currency is set
  ↓
If NOT set → Block upgrade, show error
If SET → Process with Stripe using billing_currency (16 supported currencies)
```

## Key Features

### 1. **Display vs. Billing Separation**
- **Display**: Show prices in user's local currency (e.g., JPY, GBP, AUD)
- **Billing**: Charge in one of 16 supported currencies via Stripe

### 2. **Intelligent Currency Suggestion**
Based on top poultry-producing countries:
- Eurozone countries → EUR
- Poland → PLN
- United States → USD
- China → CNY
- India → INR
- Brazil → BRL
- Indonesia → IDR
- Mexico → MXN
- Japan → JPY
- Turkey → TRY
- United Kingdom → GBP
- South Africa → ZAR
- Thailand → THB
- Malaysia → MYR
- Philippines → PHP
- Vietnam → VND
- Regional defaults (e.g., Pakistan → INR, Korea → CNY, Canada → USD)

### 3. **Mandatory Before Upgrade**
- Users MUST select billing_currency before upgrading to paid plans
- Free plan (essential) doesn't require billing_currency

## Database Changes

### New Column: `user_billing_info.billing_currency`

```sql
ALTER TABLE user_billing_info
ADD COLUMN IF NOT EXISTS billing_currency VARCHAR(3) DEFAULT NULL
    CHECK (billing_currency IN (
        'USD', 'EUR', 'CNY', 'INR', 'BRL', 'IDR', 'MXN', 'JPY',
        'TRY', 'GBP', 'ZAR', 'THB', 'MYR', 'PHP', 'PLN', 'VND'
    ));
```

### New Function: `suggest_billing_currency(country_code)`

```sql
CREATE OR REPLACE FUNCTION suggest_billing_currency(p_country_code VARCHAR(2))
RETURNS VARCHAR(3) AS $$
BEGIN
    -- Eurozone countries → EUR
    IF p_country_code IN ('AT', 'BE', 'FR', 'DE', ...) THEN RETURN 'EUR';

    -- Poland → PLN
    ELSIF p_country_code = 'PL' THEN RETURN 'PLN';

    -- China → CNY
    ELSIF p_country_code = 'CN' THEN RETURN 'CNY';

    -- India → INR
    ELSIF p_country_code = 'IN' THEN RETURN 'INR';

    -- Brazil → BRL
    ELSIF p_country_code = 'BR' THEN RETURN 'BRL';

    -- ... (16 total currencies with intelligent regional defaults)

    -- Default fallback → USD
    ELSE RETURN 'USD';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

## API Endpoints

### 1. GET `/api/v1/billing/plans` (Public)
Returns localized pricing + billing_currency info for logged-in users.

**Response (logged-in user with currency set):**
```json
{
  "plans": {
    "pro": {
      "price": 2999.00,
      "currency": "JPY",
      "currency_symbol": "¥"
    }
  },
  "billing_currency": "USD",
  "billing_currency_set": true,
  "country_code": "JP",
  "detection_method": "auto_ip"
}
```

**Response (logged-in user without currency):**
```json
{
  "plans": {...},
  "billing_currency": null,
  "billing_currency_set": false
}
```

### 2. GET `/api/v1/billing/currency-preference` (Authenticated)
Get current billing currency + intelligent suggestion.

**Response:**
```json
{
  "billing_currency": "USD",
  "is_set": true,
  "suggested_currency": "EUR",
  "detected_country": "FR",
  "available_currencies": [
    "USD", "EUR", "CNY", "INR", "BRL", "IDR", "MXN", "JPY",
    "TRY", "GBP", "ZAR", "THB", "MYR", "PHP", "PLN", "VND"
  ],
  "currency_names": {
    "USD": "US Dollar ($)",
    "EUR": "Euro (€)",
    "CNY": "Chinese Yuan (¥)",
    "INR": "Indian Rupee (₹)",
    "BRL": "Brazilian Real (R$)",
    "IDR": "Indonesian Rupiah (Rp)",
    "MXN": "Mexican Peso (MX$)",
    "JPY": "Japanese Yen (¥)",
    "TRY": "Turkish Lira (₺)",
    "GBP": "British Pound (£)",
    "ZAR": "South African Rand (R)",
    "THB": "Thai Baht (฿)",
    "MYR": "Malaysian Ringgit (RM)",
    "PHP": "Philippine Peso (₱)",
    "PLN": "Polish Zloty (zł)",
    "VND": "Vietnamese Dong (₫)"
  }
}
```

### 3. POST `/api/v1/billing/set-currency` (Authenticated)
Set user's billing currency.

**Request:**
```json
{
  "currency": "EUR"
}
```

**Response:**
```json
{
  "success": true,
  "billing_currency": "EUR",
  "message": "Billing currency set to EUR"
}
```

**Error:**
```json
{
  "detail": "Invalid currency. Must be one of: USD, EUR, CNY, INR, BRL, IDR, MXN, JPY, TRY, GBP, ZAR, THB, MYR, PHP, PLN, VND. Got: ABC"
}
```

### 4. POST `/api/v1/billing/change-plan` (Authenticated)
Change user plan with billing_currency validation.

**Error when billing_currency not set:**
```json
{
  "detail": {
    "error": "billing_currency_required",
    "message": "Please select your billing currency before upgrading to a paid plan",
    "action_required": "set_billing_currency",
    "available_currencies": [
      "USD", "EUR", "CNY", "INR", "BRL", "IDR", "MXN", "JPY",
      "TRY", "GBP", "ZAR", "THB", "MYR", "PHP", "PLN", "VND"
    ]
  }
}
```

## Migration Steps

### 1. Execute SQL Migration on Digital Ocean

```bash
# SSH into Digital Ocean server
ssh root@your-server

# Execute migration
psql $DATABASE_URL -f backend/sql/stripe/24_add_billing_currency_preference.sql
```

### 2. Verify Migration

```sql
-- Check column exists
\d user_billing_info;

-- Test suggest_billing_currency function
SELECT suggest_billing_currency('FR'); -- Should return 'EUR'
SELECT suggest_billing_currency('CA'); -- Should return 'CAD'
SELECT suggest_billing_currency('US'); -- Should return 'USD'
SELECT suggest_billing_currency('GB'); -- Should return 'USD'
SELECT suggest_billing_currency('JP'); -- Should return 'USD'

-- Check users without billing_currency
SELECT
    COUNT(*) as users_without_currency,
    COUNT(*) FILTER (WHERE plan_name != 'essential') as paid_users_without_currency
FROM user_billing_info
WHERE billing_currency IS NULL;
```

### 3. Monitor After Deployment

```sql
-- Currency distribution
SELECT
    billing_currency,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM user_billing_info
WHERE billing_currency IS NOT NULL
GROUP BY billing_currency
ORDER BY user_count DESC;
```

## Frontend Integration (TODO)

### 1. Show Warning Before Upgrade

```typescript
// In upgrade flow
const response = await fetch('/api/v1/billing/plans', {
  headers: { Authorization: `Bearer ${token}` }
});
const data = await response.json();

if (!data.billing_currency_set) {
  // Show modal: "Please select your billing currency first"
  // Redirect to /settings/billing-currency
}
```

### 2. Currency Selection UI

```typescript
// GET current preference
const preference = await fetch('/api/v1/billing/currency-preference', {
  headers: { Authorization: `Bearer ${token}` }
});
const { suggested_currency, available_currencies } = await preference.json();

// Display radio buttons or dropdown
// Highlight suggested_currency

// POST selected currency
await fetch('/api/v1/billing/set-currency', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  body: JSON.stringify({ currency: 'EUR' })
});
```

### 3. Display Logic

- Show local currency in pricing page (¥, £, A$)
- Show billing_currency in checkout (EUR, CAD, USD)
- Display note: "You will be billed in EUR"

## Stripe Integration (TODO)

### 1. Create Price IDs for Each Currency

```bash
# Example: Create pro plan prices
stripe prices create --product prod_XXX --unit-amount 2999 --currency usd
stripe prices create --product prod_XXX --unit-amount 2499 --currency eur
stripe prices create --product prod_XXX --unit-amount 3499 --currency cad
```

### 2. Update Checkout Flow

```python
# In /change-plan or Stripe checkout endpoint
billing_currency = user_billing_info["billing_currency"]  # EUR, CAD, or USD

# Map plan + currency to Stripe price_id
price_mapping = {
    ("pro", "USD"): "price_XXX_usd",
    ("pro", "EUR"): "price_XXX_eur",
    ("pro", "CAD"): "price_XXX_cad",
    ("elite", "USD"): "price_YYY_usd",
    # ...
}

price_id = price_mapping[(new_plan, billing_currency)]

# Create Stripe checkout session with this price_id
stripe.checkout.Session.create(
    line_items=[{"price": price_id, "quantity": 1}],
    # ...
)
```

## Testing Checklist

- [ ] Migration executed successfully
- [ ] `suggest_billing_currency()` returns correct values
- [ ] GET `/billing/plans` returns `billing_currency_set: false` for new users
- [ ] POST `/set-currency` validates only USD/EUR/CAD
- [ ] POST `/change-plan` blocks upgrade if currency not set
- [ ] POST `/change-plan` allows upgrade after currency is set
- [ ] Frontend shows warning before upgrade
- [ ] Currency selection UI works properly
- [ ] Stripe checkout uses correct price_id based on billing_currency

## Expected User Flow

1. **New User Signs Up**
   - No billing_currency set
   - Can use free plan immediately

2. **User Wants to Upgrade**
   - Clicks "Upgrade to Pro"
   - System checks: billing_currency is NULL
   - Shows error: "Please select your billing currency"
   - User redirected to currency selection

3. **User Selects Currency**
   - System suggests EUR (user in France)
   - User confirms EUR
   - billing_currency saved to database

4. **User Completes Upgrade**
   - System validates: billing_currency = EUR ✓
   - Redirects to Stripe checkout with EUR price_id
   - User pays in EUR via Stripe

5. **User Sees Pricing Page**
   - Display: €24.99 (local currency)
   - Note: "You will be billed in EUR"

## Support

### Common Issues

**Q: User in UK sees GBP but can't select GBP for billing?**
A: Correct. Display is GBP, but billing must be USD/EUR/CAD. They can choose EUR or USD.

**Q: Can users change their billing_currency after selecting?**
A: Yes, via POST `/set-currency`. However, active subscriptions keep their original currency.

**Q: What if user's country suggests EUR but they want USD?**
A: They can override. suggestion is just a default, not mandatory.

---

**Status**: Backend implementation complete. Requires:
1. SQL migration execution
2. Frontend UI implementation
3. Stripe price IDs creation
4. Checkout flow update
