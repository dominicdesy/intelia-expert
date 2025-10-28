# Documentation Billing & Stripe

Documentation complète sur l'intégration Stripe et la gestion de la facturation.

## Fichiers

### Configuration
- **BILLING_CURRENCY_SETUP.md** - Configuration multi-devises
- **STRIPE_IMPLEMENTATION_COMPLETE.md** - Implémentation complète Stripe
- **STRIPE_IMPLEMENTATION_STATUS.md** - Status actuel de l'implémentation

### Webhooks
- **STRIPE_WEBHOOK_POST_CONFIG.md** - Configuration des webhooks Stripe
- **STRIPE_WEBHOOK_SETUP_STATUS.md** - Status setup webhooks

### Sécurité
- **STRIPE_FRAUD_DETECTION_INTEGRATION.md** - Intégration détection de fraude
- **PRICING_FRAUD_PREVENTION_STRATEGY.md** - Stratégie prévention fraude tarifaire

## Tiers de subscription

- **Free**: 10 questions/mois
- **Essential**: 100 questions/mois ($9.99 CAD)
- **Professional**: 500 questions/mois ($29.99 CAD)
- **Enterprise**: Illimité (prix personnalisé)

## Scripts SQL

Voir `../../../backend/sql/stripe/` pour les scripts de configuration:
- Création des tables
- Pricing par tier
- Pricing par pays
- Admin tools

## Variables d'environnement

Voir `backend/.env.stripe.example` pour la configuration complète.
