# Archive Scripts SQL

Scripts SQL temporaires et obsolètes, conservés pour référence historique.

## Contenu

### Tests utilisateur (Dominic)
Scripts utilisés pour tester les subscriptions:
- `add_essential_subscription_dominic*.sql` - Tests subscription Essential
- `add_free_subscription_dominic*.sql` - Tests subscription Free
- `check_dominic_usage*.sql` - Vérifications usage
- `reset_dominic_quota_to_zero.sql` - Reset quota de test

### Scripts temporaires
- `temp_reduce_essential_limit_for_testing.sql` - Réduction temporaire limite
- `temp_restore_essential_limit.sql` - Restauration limite

### Scripts de vérification ponctuels
- `check_billing_plans.sql` - Vérification plans billing
- `check_user_billing_info_structure.sql` - Vérification structure user billing
- `list_existing_plans.sql` - Liste des plans
- `restore_free_plan_quota.sql` - Restauration quota plan Free

## ⚠️ Avertissement

**NE PAS UTILISER CES SCRIPTS EN PRODUCTION**

Ces scripts sont obsolètes et conservés uniquement pour référence.
Pour les scripts actuels, voir les dossiers:
- `../migrations/` - Migrations de base de données
- `../stripe/` - Configuration Stripe
- `../maintenance/` - Scripts de maintenance

## Scripts actifs

Pour modifier les quotas ou subscriptions, utiliser:
- Admin panel Stripe
- Scripts dans `../stripe/`
- API backend `/admin/subscriptions/`
