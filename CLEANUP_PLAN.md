# Plan de nettoyage et réorganisation - Intelia Expert

**Date**: 2025-10-28
**Status**: PROPOSITION

---

## Vue d'ensemble

Actuellement, le projet contient **278 fichiers .md** et **76 fichiers .sql** dispersés dans différents dossiers. De nombreux fichiers sont obsolètes, en double, ou mal classés.

### Objectifs
1. Centraliser toute la documentation dans `docs/`
2. Supprimer les fichiers obsolètes et de backup
3. Organiser les fichiers SQL par type et état
4. Identifier et compléter les TODOs en suspend
5. Créer une structure claire et maintenable

---

## 1. Fichiers de backup à supprimer

### Fichiers .backup, .bak, .old, .OLD (SUPPRIMER IMMÉDIATEMENT)
```bash
# À supprimer
./.github/workflows/deploy.yml.bak
./ai-service/config/poultry_terminology.json.OLD
./frontend/app/chat/components/modals/AccountModal.bak
./frontend/app/chat/components/modals/InviteFriendModal.tsx.bak
./frontend/app/chat/components/modals/UserInfoModal.tsx.backup
./frontend/app/chat/components/modals/UserInfoModal.tsx.bak
```

### Fichiers cache webpack (SUPPRIMER)
```bash
./frontend/.next/cache/webpack/**/*.old
```

**Action**: Supprimer tous ces fichiers sans préserver

---

## 2. Fichiers .md à la racine (À DÉPLACER ou SUPPRIMER)

### ✅ À déplacer vers `docs/guides/`
```
AI_SERVICE_INTEGRATION.md                    → docs/guides/
BILLING_CURRENCY_SETUP.md                    → docs/guides/billing/
CACHING_AND_PROMPT_OPTIMIZATION_REPORT.md    → docs/reports/
CHAIN_OF_THOUGHT_ANALYSIS.md                 → docs/analysis/
COMPLETION_REPORT.md                         → docs/reports/
CORPORATE_MIGRATION_STRATEGY.md              → docs/guides/enterprise/
CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md → docs/guides/enterprise/
COST_ANALYSIS.md                             → docs/analysis/
COT_PHASES_2_3_IMPLEMENTATION.md            → docs/implementation/
CSP_MONITORING_GUIDE.md                      → docs/security/
DATA_FLOW_OPTIMIZATION_REPORT.md             → docs/reports/
DATA_FLOW_OPTIMIZATION_STATUS.md             → docs/reports/
DATA_RETENTION_POLICY.md                     → docs/security/
DEPLOYMENT_GUIDE_COUNTRY_TRACKING.md         → docs/deployment/
FRONTEND_UI_IMPLEMENTATION.md                → docs/frontend/
GDPR_ACCOUNT_DELETION_POLICY.md              → docs/security/
GDPR_COMPLIANCE_AUDIT.md                     → docs/security/
GRAFANA_SETUP.md                             → docs/operations/
HSTS_PRELOAD_GUIDE.md                        → docs/security/
IMPLEMENTATION_BROILER_LAYER_COT.md          → docs/implementation/
IMPLEMENTATION_PLAN_USER_PROFILING.md        → docs/implementation/
LLM_BOTTLENECK_ANALYSIS.md                   → docs/analysis/
LLM_INTEGRATION_TEST_RESULTS.md              → docs/reports/
LLM_OPTIMIZATION_COMPLETE_SUMMARY.md         → docs/reports/
LLM_SERVICE_INTEGRATION.md                   → docs/guides/
LLM_SERVICE_SPECS.md                         → docs/guides/
METRIQUES_PHASE2_ETAT_ACTUEL.md              → docs/reports/
MIGRATION_STATUS.md                          → docs/migration/
MOBILE_REDESIGN_PROJECT.md                   → docs/frontend/
MODEL_ROUTING_IMPLEMENTATION_REPORT.md       → docs/reports/
MULTILINGUAL_STRATEGY_REPORT.md              → docs/reports/
OPTIMIZATION_SUMMARY.md                      → docs/reports/
PHASE_1A_OPTIMIZATION_REPORT.md              → docs/reports/
PHASE_1B_BEFORE_AFTER.md                     → docs/reports/
PHASE_1B_COMPLETE.md                         → docs/reports/
PHASE_1B_IMPLEMENTATION_REPORT.md            → docs/reports/
PHASE_1B_INDEX.md                            → docs/reports/
PHASE_1B_README.md                           → docs/reports/
PHASE_1B_SUMMARY.md                          → docs/reports/
POULTRY_PRODUCTION_COUNTRIES.md              → docs/guides/
PRICING_FRAUD_PREVENTION_STRATEGY.md         → docs/security/
PWA_IMPLEMENTATION.md                        → docs/frontend/
REAL_TIME_VOICE_PLAN.md                      → docs/guides/
SATISFACTION_SURVEY_MOCKUP.md                → docs/guides/
SECURITY_HEADERS_IMPLEMENTATION.md           → docs/security/
SECURITY_VALIDATION_REPORT.md                → docs/security/
SETUP_GUIDE.md                               → docs/ (GARDER À LA RACINE)
SRI_IMPLEMENTATION_GUIDE.md                  → docs/security/
STREAMING_IMPLEMENTATION_REPORT.md           → docs/reports/
STRIPE_FRAUD_DETECTION_INTEGRATION.md        → docs/guides/billing/
STRIPE_IMPLEMENTATION_COMPLETE.md            → docs/guides/billing/
STRIPE_IMPLEMENTATION_STATUS.md              → docs/guides/billing/
STRIPE_WEBHOOK_POST_CONFIG.md                → docs/guides/billing/
STRIPE_WEBHOOK_SETUP_STATUS.md               → docs/guides/billing/
SUBSCRIPTION_TIERS_ANALYSIS.md               → docs/analysis/
THIRD_PARTY_NOTICES.md                       → docs/ (GARDER)
VERIFY_COT_DEPLOYMENT.md                     → docs/deployment/
VERSION_MANAGEMENT.md                        → docs/operations/
VOICE_REALTIME_PHASE1_COMPLETE.md            → docs/reports/
VOICE_SETTINGS_IMPLEMENTATION_SUMMARY.md     → docs/reports/
WEAVIATE_EMBEDDING_ANALYSIS.md               → docs/analysis/
WEBAUTHN_IMPLEMENTATION.md                   → docs/guides/
WIDGET_INTEGRATION_GUIDE.md                  → docs/guides/
```

### ❌ À SUPPRIMER (obsolètes/temporaires)
```
test_fresh_query.md                          → SUPPRIMER (notes de test temporaires)
CHANGELOG_PHASE_1B.md                        → FUSIONNER avec PHASE_1B_SUMMARY.md puis SUPPRIMER
```

---

## 3. Fichiers .md dans `backend/` (À DÉPLACER)

```
backend/AUDIO_STORAGE_SETUP.md               → docs/backend/
backend/CURRENCY_RATES_SETUP.md              → docs/backend/
backend/ENV_VARIABLES_COMPLETE.md            → docs/backend/
backend/QA_ANALYSIS_REPORT.md                → docs/backend/
backend/QUOTA_SYSTEM_README.md               → docs/backend/
backend/VOICE_REALTIME_DEPLOYMENT.md         → docs/deployment/
```

---

## 4. Fichiers SQL à réorganiser

### Structure proposée pour `backend/sql/`
```
backend/sql/
├── schema/                    # Définitions de tables (GARDER)
│   ├── create_conversation_shares_table.sql
│   ├── create_medical_images_table.sql
│   ├── create_messages_table_only.sql
│   └── db_schema_conversations_messages.sql
│
├── migrations/                # Migrations appliquées (GARDER)
│   ├── add_ad_history_to_users.sql
│   ├── create_widget_tables.sql
│   └── ... (tous les .sql avec dates dans migrations/)
│
├── stripe/                    # Scripts Stripe (GARDER)
│   ├── 01_create_stripe_tables.sql
│   └── ...
│
├── whatsapp/                  # Scripts WhatsApp (GARDER)
│   └── 01_create_whatsapp_tables.sql
│
├── archive/                   # Scripts historiques/obsolètes (CRÉER ET DÉPLACER)
│   ├── temp_*.sql            # Scripts temporaires
│   ├── add_essential_subscription_dominic*.sql  # Tests utilisateurs
│   ├── check_*.sql           # Scripts de vérification ponctuels
│   └── ...
│
└── maintenance/               # Scripts de maintenance (GARDER)
    ├── cleanup_*.sql
    └── verify_*.sql
```

### Scripts SQL à ARCHIVER (déplacer vers `backend/sql/archive/`)
```
# Scripts de test utilisateur Dominic (obsolètes)
add_essential_subscription_dominic.sql
add_essential_subscription_dominic_COMPLETE.sql
add_essential_subscription_dominic_v2.sql
add_essential_subscription_dominic_v3.sql
add_free_subscription_dominic_SAFE.sql
add_free_subscription_dominic_test.sql
check_dominic_usage.sql
check_dominic_usage_simple.sql
reset_dominic_quota_to_zero.sql

# Scripts temporaires
temp_reduce_essential_limit_for_testing.sql
temp_restore_essential_limit.sql

# Scripts de vérification ponctuels
check_billing_plans.sql
check_user_billing_info_structure.sql
list_existing_plans.sql
restore_free_plan_quota.sql
```

### Scripts SQL à DOCUMENTER (ajouter des README.md)
```
backend/sql/stripe/README.md           # Expliquer l'ordre d'exécution
backend/sql/migrations/README.md        # Guide des migrations
backend/sql/maintenance/README.md       # Quand utiliser ces scripts
```

---

## 5. Fichiers dans `docs/` à réorganiser

### Créer de nouveaux sous-dossiers
```
docs/
├── analysis/          # ✅ Existe déjà
├── backend/           # ✅ Existe déjà
├── configuration/     # ✅ Existe déjà
├── deployment/        # ✅ Existe déjà
├── guides/            # ✅ Existe déjà
├── migration/         # ✅ Existe déjà
├── operations/        # ✅ Existe déjà
├── reports/           # ✅ Existe déjà
├── security/          # ✅ Existe déjà
│
├── frontend/          # ⭐ À CRÉER
├── implementation/    # ⭐ À CRÉER
└── archive/           # ⭐ À CRÉER (fichiers obsolètes mais historiques)
```

### Fichiers dans `docs/` racine à classer
```
CLAUDE_COT_IMPLEMENTATION_PLAN.md        → docs/implementation/
CLAUDE_INSTRUCTIONS.md                   → docs/ (GARDER - instructions générales)
COT_ANOMALY_INTEGRATION.md              → docs/implementation/
DIGITALOCEAN_ENV_SETUP.md                → docs/deployment/
DOCS_REORGANIZATION_PLAN.md              → docs/archive/ (obsolète après ce cleanup)
MEDICAL_IMAGE_ANALYSIS_GUIDE.md          → docs/guides/
README.md                                → docs/ (GARDER - index principal)
VOICE_REALTIME.md                        → docs/guides/
```

---

## 6. Fichiers POC à conserver (GARDER)

```
poc_realtime/
├── DECISIONS_TECHNIQUES.md
├── INDEX.md
├── QUESTIONS_RECAP.md
├── README.md
├── RESULTATS_POC.md
├── RESUME_EXECUTIF.md
├── RUN_ON_DIGITAL_OCEAN.md
├── START_HERE.md
└── VALIDATION_CHECKLIST.md
```
**Commentaire**: Bien organisé, ne pas toucher

---

## 7. TODOs identifiés (31 fichiers avec TODOs)

### TODOs critiques à traiter
1. **CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md** - Plan non terminé
2. **WIDGET_INTEGRATION_GUIDE.md** - Implémentation widget
3. **METRIQUES_PHASE2_ETAT_ACTUEL.md** - Métriques manquantes
4. **DATA_RETENTION_POLICY.md** - Politique à finaliser
5. **VOICE_REALTIME_PHASE1_COMPLETE.md** - Phase 2 à planifier
6. **SUBSCRIPTION_TIERS_ANALYSIS.md** - Analyse à compléter
7. **BILLING_CURRENCY_SETUP.md** - Configuration multi-devises
8. **SECURITY_VALIDATION_REPORT.md** - Tests de sécurité
9. **GDPR_COMPLIANCE_AUDIT.md** - Audit GDPR
10. **STRIPE_WEBHOOK_SETUP_STATUS.md** - Configuration webhooks

### TODOs de documentation (à mettre à jour)
- **docs/security/SECURITY_FINAL_SUMMARY.md** - Résumé à jour
- **docs/migration/READY_TO_MIGRATE.md** - Checklist migration
- **ai-service/tests/README_TESTS.md** - Documentation tests

---

## 8. Plan d'action prioritaire

### Phase 1: Nettoyage immédiat (URGENT)
- [ ] Supprimer tous les fichiers .backup, .bak, .old, .OLD
- [ ] Supprimer les fichiers cache webpack .old
- [ ] Supprimer `test_fresh_query.md`

### Phase 2: Créer la nouvelle structure
- [ ] Créer `docs/frontend/`
- [ ] Créer `docs/implementation/`
- [ ] Créer `docs/archive/`
- [ ] Créer `docs/guides/billing/`
- [ ] Créer `docs/guides/enterprise/`
- [ ] Créer `backend/sql/archive/`

### Phase 3: Déplacer les fichiers de la racine
- [ ] Déplacer les 50+ fichiers .md de la racine vers docs/
- [ ] Garder seulement: README.md, SETUP_GUIDE.md, THIRD_PARTY_NOTICES.md

### Phase 4: Réorganiser backend/
- [ ] Déplacer les .md de backend/ vers docs/backend/
- [ ] Archiver les scripts SQL temporaires

### Phase 5: Créer les README.md manquants
- [ ] backend/sql/stripe/README.md
- [ ] backend/sql/migrations/README.md
- [ ] backend/sql/maintenance/README.md
- [ ] backend/sql/archive/README.md
- [ ] docs/frontend/README.md
- [ ] docs/implementation/README.md

### Phase 6: Traiter les TODOs critiques
- [ ] Réviser les 10 fichiers avec TODOs critiques
- [ ] Créer des tickets pour les TODOs non terminés
- [ ] Mettre à jour la documentation

---

## 9. Structure finale attendue

### Racine du projet (MINIMALISTE)
```
C:\intelia_gpt\intelia-expert\
├── README.md                      # Index principal
├── SETUP_GUIDE.md                 # Guide installation
├── THIRD_PARTY_NOTICES.md         # Licences
├── .gitignore
├── docker-compose.yml
└── docs/                          # TOUTE LA DOCUMENTATION
```

### docs/ (ORGANISÉ)
```
docs/
├── README.md                      # Index de la documentation
├── CLAUDE_INSTRUCTIONS.md         # Instructions générales
│
├── analysis/                      # Analyses techniques
│   ├── CHAIN_OF_THOUGHT_ANALYSIS.md
│   ├── COST_ANALYSIS.md
│   └── ...
│
├── backend/                       # Documentation backend
│   ├── AUDIO_STORAGE_SETUP.md
│   ├── QUOTA_SYSTEM_README.md
│   └── ...
│
├── deployment/                    # Guides déploiement
│   ├── DEPLOYMENT_PRODUCTION_GUIDE.md
│   ├── VERIFY_COT_DEPLOYMENT.md
│   └── ...
│
├── frontend/                      # ⭐ NOUVEAU
│   ├── README.md
│   ├── MOBILE_REDESIGN_PROJECT.md
│   ├── PWA_IMPLEMENTATION.md
│   └── ...
│
├── guides/                        # Guides pratiques
│   ├── billing/                   # ⭐ NOUVEAU
│   │   ├── BILLING_CURRENCY_SETUP.md
│   │   ├── STRIPE_IMPLEMENTATION_COMPLETE.md
│   │   └── ...
│   ├── enterprise/                # ⭐ NOUVEAU
│   │   ├── CORPORATE_MIGRATION_STRATEGY.md
│   │   └── ...
│   └── ...
│
├── implementation/                # ⭐ NOUVEAU
│   ├── CLAUDE_COT_IMPLEMENTATION_PLAN.md
│   ├── COT_PHASES_2_3_IMPLEMENTATION.md
│   └── ...
│
├── migration/                     # Guides migration
│   ├── MIGRATION_GUIDE.md
│   ├── MIGRATION_STATUS.md
│   └── ...
│
├── operations/                    # Opérations
│   ├── GRAFANA_SETUP.md
│   ├── VERSION_MANAGEMENT.md
│   └── ...
│
├── reports/                       # Rapports d'implémentation
│   ├── COMPLETION_REPORT.md
│   ├── LLM_OPTIMIZATION_COMPLETE_SUMMARY.md
│   ├── PHASE_1B_SUMMARY.md
│   └── ...
│
├── security/                      # Sécurité et GDPR
│   ├── GDPR_COMPLIANCE_AUDIT.md
│   ├── SECURITY_VALIDATION_REPORT.md
│   └── ...
│
└── archive/                       # ⭐ NOUVEAU (obsolètes mais historiques)
    └── DOCS_REORGANIZATION_PLAN.md
```

### backend/sql/ (PROPRE)
```
backend/sql/
├── README.md                      # Guide général
├── schema/                        # Schémas de tables
├── migrations/                    # Migrations appliquées
│   └── README.md
├── stripe/                        # Scripts Stripe
│   └── README.md
├── whatsapp/                      # Scripts WhatsApp
├── maintenance/                   # Scripts maintenance
│   └── README.md
├── fixes/                         # Correctifs
└── archive/                       # ⭐ Scripts obsolètes
    ├── README.md
    └── temp_*.sql
```

---

## 10. Métriques de nettoyage

### Avant
- **278 fichiers .md** dispersés
- **76 fichiers .sql** dispersés
- **10 fichiers backup** inutiles
- **50+ fichiers à la racine**
- **31 fichiers avec TODOs**

### Après (attendu)
- **3 fichiers .md à la racine** (README, SETUP_GUIDE, THIRD_PARTY_NOTICES)
- **0 fichiers backup**
- **Structure claire en 9 catégories**
- **TODOs identifiés et priorisés**
- **SQL organisé par type et état**

---

## 11. Commandes Git recommandées

### Pour déplacer les fichiers (conserver l'historique)
```bash
# Déplacer un fichier (Git conserve l'historique)
git mv AI_SERVICE_INTEGRATION.md docs/guides/

# Déplacer plusieurs fichiers vers un dossier
git mv BILLING_*.md docs/guides/billing/

# Supprimer des fichiers
git rm frontend/app/chat/components/modals/*.bak
```

---

## Validation finale

### Checklist
- [ ] Tous les fichiers backup supprimés
- [ ] Racine du projet propre (3 fichiers .md max)
- [ ] docs/ organisé en catégories claires
- [ ] backend/sql/ avec structure schema/migrations/archive
- [ ] README.md créés dans chaque sous-dossier
- [ ] TODOs critiques identifiés et trackés
- [ ] Aucun fichier .sql ou .md dispersé

---

**Prochaine étape**: Valider ce plan avec vous avant d'exécuter les déplacements et suppressions.

