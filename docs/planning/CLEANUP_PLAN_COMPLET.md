# Plan de nettoyage COMPLET et réorganisation - Intelia Expert

**Date**: 2025-10-28
**Status**: PROPOSITION FINALE
**Analyse**: Racine + docs + llm + ai-service + backend + frontend

---

## Vue d'ensemble

### Statistiques complètes
- **278 fichiers .md** dispersés dans le projet
- **76 fichiers .sql** dans backend/sql/
- **10 fichiers test Python** à la racine de llm/
- **30+ fichiers test Python** dans ai-service/
- **10 fichiers backup** (.bak, .backup, .old) à supprimer
- **3 scripts .js temporaires** d'analyse setTimeout
- **2 fichiers .json** de résultats de tests temporaires
- **3 fichiers .txt** de résultats QA temporaires
- **50+ fichiers .md** à la racine à déplacer

---

## 🔴 SECTION 1: Fichiers à SUPPRIMER IMMÉDIATEMENT

### 1.1 Fichiers backup (.backup, .bak, .old)
```bash
# À SUPPRIMER
./.github/workflows/deploy.yml.bak
./ai-service/config/poultry_terminology.json.OLD
./frontend/app/chat/components/modals/AccountModal.bak
./frontend/app/chat/components/modals/InviteFriendModal.tsx.bak
./frontend/app/chat/components/modals/UserInfoModal.tsx.backup
./frontend/app/chat/components/modals/UserInfoModal.tsx.bak
```

### 1.2 Fichiers cache webpack (.old)
```bash
# À SUPPRIMER
./frontend/.next/cache/webpack/**/*.old
```

### 1.3 Scripts temporaires d'analyse (obsolètes)
```bash
# ai-service/ - Scripts d'analyse setTimeout (déjà fixé)
./ai-service/analyze_all_settimeout.js              → SUPPRIMER
./ai-service/deep-settimeout-analysis.js            → SUPPRIMER
./ai-service/eslint-check-settimeout.js             → SUPPRIMER
./ai-service/find_unsafe_settimeout.sh              → SUPPRIMER
./ai-service/setTimeout_analysis.md                 → ARCHIVER dans docs/archive/
```

### 1.4 Fichiers de résultats de tests temporaires
```bash
# llm/
./llm/load_test_results.json                        → SUPPRIMER (résultats temporaires)

# backend/
./backend/qa_analysis_20251028_081623.json         → SUPPRIMER (résultats temporaires)
./backend/qa_analysis_20251028_081623.txt          → SUPPRIMER
./backend/qa_analysis_20251028_081659.json         → SUPPRIMER
./backend/qa_analysis_20251028_081659.txt          → SUPPRIMER
```

### 1.5 Fichiers de notes temporaires
```bash
./test_fresh_query.md                               → SUPPRIMER (notes de test)
./ai-service/run-dev-mode.md                        → SUPPRIMER (notes de debug)
./backend/trigger.txt                               → SUPPRIMER (fichier de test)
```

### 1.6 Fichiers .deploytest (marqueurs de build)
```bash
./ai-service/.deploytest                            → SUPPRIMER
./backend/.deploytest                               → SUPPRIMER
```

**Total à supprimer: 24 fichiers**

---

## 🟡 SECTION 2: Tests Python à ORGANISER

### 2.1 llm/ - Tests à la racine (À DÉPLACER vers llm/tests/)
```bash
# CRÉER llm/tests/ et déplacer:
./llm/test_complete_system.py                      → llm/tests/
./llm/test_compliance.py                           → llm/tests/
./llm/test_full_generation.py                      → llm/tests/
./llm/test_generation_api.py                       → llm/tests/
./llm/test_load.py                                 → llm/tests/
./llm/test_performance_optimizations.py            → llm/tests/
./llm/test_streaming.py                            → llm/tests/
./llm/test_terminology_injection.py                → llm/tests/
./llm/test_value_chain_coverage.py                 → llm/tests/
```

### 2.2 ai-service/ - Tests bien organisés (GARDER)
```
ai-service/tests/
├── integration/          # ✅ Bien organisé
│   ├── test_api_chat_endpoint.py
│   ├── test_complete_system.py
│   ├── test_llm_router.py
│   └── ... (11 tests d'intégration)
├── test_*.py             # ✅ Tests unitaires
└── run_all_tests.py      # ✅ Runner de tests
```

### 2.3 ai-service/scripts/testing/ - Tests spécialisés (GARDER)
```
ai-service/scripts/testing/
├── test_agrovoc_coverage.py
├── test_clarification_generation.py
├── test_external_sources.py
└── ... (9 tests spécialisés)
```

### 2.4 backend/ - Scripts de test temporaires (À DÉPLACER)
```bash
# CRÉER backend/tests/ et déplacer:
./backend/check_twilio_message_status.py           → backend/tests/manual/
./backend/test_monitoring.py                       → backend/tests/
./backend/test_whatsapp_update.py                  → backend/tests/manual/
```

**Action**: Créer llm/tests/ et backend/tests/, déplacer les tests

---

## 🟢 SECTION 3: Documentation à RÉORGANISER

### 3.1 llm/ - Documentation (BIEN ORGANISÉ ✅)
```
llm/
├── README.md                                      # ✅ GARDER
└── TERMINOLOGY_ENRICHMENT.md                      # ✅ GARDER
```

### 3.2 ai-service/ - Documentation (À DÉPLACER)
```bash
./ai-service/README.md                             # ✅ GARDER (doc service)
./ai-service/config/README_TERMINOLOGY.md          # ✅ GARDER (config spécifique)
./ai-service/core/INTEGRATION_GUIDE.md             # → docs/guides/
./ai-service/scripts/README.md                     # ✅ GARDER (doc scripts)
./ai-service/tests/README.md                       # ✅ GARDER (doc tests)
./ai-service/tests/README_TESTS.md                 # ✅ GARDER (doc tests)
./ai-service/tests/integration/README.md           # ✅ GARDER (doc tests)
```

### 3.3 backend/ - Documentation (À DÉPLACER)
```bash
# À déplacer vers docs/backend/
./backend/AUDIO_STORAGE_SETUP.md                   → docs/backend/
./backend/CURRENCY_RATES_SETUP.md                  → docs/backend/
./backend/ENV_VARIABLES_COMPLETE.md                → docs/backend/
./backend/QA_ANALYSIS_REPORT.md                    → docs/backend/
./backend/QUOTA_SYSTEM_README.md                   → docs/backend/
./backend/VOICE_REALTIME_DEPLOYMENT.md             → docs/deployment/

# SQL documentation (À GARDER dans backend/sql/)
./backend/sql/README.md                            # ✅ GARDER
./backend/sql/fixes/README_PROFILE_FIX.md          # ✅ GARDER
./backend/sql/fixes/RECREATE_ADMIN_USER_GUIDE.md   # ✅ GARDER
./backend/sql/fixes/SECURITY_FIXES_GUIDE.md        # ✅ GARDER
./backend/sql/migrations/CHECKLIST_*.md            # ✅ GARDER
./backend/sql/migrations/IMPLEMENTATION_*.md       # ✅ GARDER
./backend/sql/migrations/README_*.md               # ✅ GARDER
./backend/sql/stripe/INTELIA_PLAN_README.md        # ✅ GARDER
./backend/sql/stripe/PRICING_MANAGEMENT_GUIDE.md   # ✅ GARDER
./backend/migrations/run_migration.md              # ✅ GARDER
```

### 3.4 frontend/ - Documentation (À DÉPLACER)
```bash
./frontend/REFACTORING_PLAN.md                     → docs/frontend/
./frontend/public/THIRD_PARTY_NOTICES.md           # ✅ GARDER (license public)
```

---

## 📁 SECTION 4: Fichiers .md à la racine (À DÉPLACER)

### 4.1 Guides → docs/guides/
```
AI_SERVICE_INTEGRATION.md                          → docs/guides/
LLM_SERVICE_INTEGRATION.md                         → docs/guides/
LLM_SERVICE_SPECS.md                               → docs/guides/
REAL_TIME_VOICE_PLAN.md                            → docs/guides/
WEBAUTHN_IMPLEMENTATION.md                         → docs/guides/
WIDGET_INTEGRATION_GUIDE.md                        → docs/guides/
SATISFACTION_SURVEY_MOCKUP.md                      → docs/guides/
POULTRY_PRODUCTION_COUNTRIES.md                    → docs/guides/
```

### 4.2 Billing → docs/guides/billing/
```
BILLING_CURRENCY_SETUP.md                          → docs/guides/billing/
STRIPE_FRAUD_DETECTION_INTEGRATION.md              → docs/guides/billing/
STRIPE_IMPLEMENTATION_COMPLETE.md                  → docs/guides/billing/
STRIPE_IMPLEMENTATION_STATUS.md                    → docs/guides/billing/
STRIPE_WEBHOOK_POST_CONFIG.md                      → docs/guides/billing/
STRIPE_WEBHOOK_SETUP_STATUS.md                     → docs/guides/billing/
PRICING_FRAUD_PREVENTION_STRATEGY.md               → docs/guides/billing/
```

### 4.3 Enterprise → docs/guides/enterprise/
```
CORPORATE_MIGRATION_STRATEGY.md                    → docs/guides/enterprise/
CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md       → docs/guides/enterprise/
```

### 4.4 Frontend → docs/frontend/
```
FRONTEND_UI_IMPLEMENTATION.md                      → docs/frontend/
MOBILE_REDESIGN_PROJECT.md                         → docs/frontend/
PWA_IMPLEMENTATION.md                              → docs/frontend/
```

### 4.5 Implementation → docs/implementation/
```
IMPLEMENTATION_BROILER_LAYER_COT.md                → docs/implementation/
IMPLEMENTATION_PLAN_USER_PROFILING.md              → docs/implementation/
COT_PHASES_2_3_IMPLEMENTATION.md                   → docs/implementation/
```

### 4.6 Analysis → docs/analysis/
```
CHAIN_OF_THOUGHT_ANALYSIS.md                       → docs/analysis/
COST_ANALYSIS.md                                   → docs/analysis/
LLM_BOTTLENECK_ANALYSIS.md                         → docs/analysis/
SUBSCRIPTION_TIERS_ANALYSIS.md                     → docs/analysis/
WEAVIATE_EMBEDDING_ANALYSIS.md                     → docs/analysis/
```

### 4.7 Reports → docs/reports/
```
CACHING_AND_PROMPT_OPTIMIZATION_REPORT.md          → docs/reports/
COMPLETION_REPORT.md                               → docs/reports/
DATA_FLOW_OPTIMIZATION_REPORT.md                   → docs/reports/
DATA_FLOW_OPTIMIZATION_STATUS.md                   → docs/reports/
LLM_INTEGRATION_TEST_RESULTS.md                    → docs/reports/
LLM_OPTIMIZATION_COMPLETE_SUMMARY.md               → docs/reports/
METRIQUES_PHASE2_ETAT_ACTUEL.md                    → docs/reports/
MODEL_ROUTING_IMPLEMENTATION_REPORT.md             → docs/reports/
MULTILINGUAL_STRATEGY_REPORT.md                    → docs/reports/
OPTIMIZATION_SUMMARY.md                            → docs/reports/
STREAMING_IMPLEMENTATION_REPORT.md                 → docs/reports/
VOICE_REALTIME_PHASE1_COMPLETE.md                  → docs/reports/
VOICE_SETTINGS_IMPLEMENTATION_SUMMARY.md           → docs/reports/
PHASE_1A_OPTIMIZATION_REPORT.md                    → docs/reports/
PHASE_1B_BEFORE_AFTER.md                           → docs/reports/
PHASE_1B_COMPLETE.md                               → docs/reports/
PHASE_1B_IMPLEMENTATION_REPORT.md                  → docs/reports/
PHASE_1B_INDEX.md                                  → docs/reports/
PHASE_1B_README.md                                 → docs/reports/
PHASE_1B_SUMMARY.md                                → docs/reports/
```

### 4.8 Deployment → docs/deployment/
```
DEPLOYMENT_GUIDE_COUNTRY_TRACKING.md               → docs/deployment/
VERIFY_COT_DEPLOYMENT.md                           → docs/deployment/
```

### 4.9 Security → docs/security/
```
CSP_MONITORING_GUIDE.md                            → docs/security/
DATA_RETENTION_POLICY.md                           → docs/security/
GDPR_ACCOUNT_DELETION_POLICY.md                    → docs/security/
GDPR_COMPLIANCE_AUDIT.md                           → docs/security/
HSTS_PRELOAD_GUIDE.md                              → docs/security/
SECURITY_HEADERS_IMPLEMENTATION.md                 → docs/security/
SECURITY_VALIDATION_REPORT.md                      → docs/security/
SRI_IMPLEMENTATION_GUIDE.md                        → docs/security/
```

### 4.10 Operations → docs/operations/
```
GRAFANA_SETUP.md                                   → docs/operations/
VERSION_MANAGEMENT.md                              → docs/operations/
```

### 4.11 Migration → docs/migration/
```
MIGRATION_STATUS.md                                → docs/migration/
```

### 4.12 Archive → docs/archive/
```
CHANGELOG_PHASE_1B.md                              → docs/archive/ (fusionner avec PHASE_1B_SUMMARY)
```

### 4.13 À GARDER à la racine
```
README.md                                          # ✅ GARDER (index principal)
SETUP_GUIDE.md                                     # ✅ GARDER (setup rapide)
THIRD_PARTY_NOTICES.md                             # ✅ GARDER (licenses)
```

**Total à déplacer: 55 fichiers .md**

---

## 🗄️ SECTION 5: Scripts SQL à RÉORGANISER

### 5.1 Structure actuelle de backend/sql/
```
backend/sql/
├── schema/               # ✅ Définitions tables - GARDER
├── migrations/           # ✅ Migrations appliquées - GARDER
├── stripe/               # ✅ Scripts Stripe - GARDER
├── whatsapp/             # ✅ Scripts WhatsApp - GARDER
├── fixes/                # ✅ Correctifs - GARDER
├── maintenance/          # ✅ Maintenance - GARDER
├── queries/              # ✅ Requêtes utiles - GARDER
├── *.sql (racine)        # ⚠️ Scripts temporaires - À ARCHIVER
└── README.md             # ✅ GARDER
```

### 5.2 Scripts SQL temporaires/tests (À ARCHIVER)
```bash
# CRÉER backend/sql/archive/ et déplacer:

# Tests utilisateur Dominic (obsolètes)
./backend/sql/add_essential_subscription_dominic.sql          → archive/
./backend/sql/add_essential_subscription_dominic_COMPLETE.sql → archive/
./backend/sql/add_essential_subscription_dominic_v2.sql       → archive/
./backend/sql/add_essential_subscription_dominic_v3.sql       → archive/
./backend/sql/add_free_subscription_dominic_SAFE.sql          → archive/
./backend/sql/add_free_subscription_dominic_test.sql          → archive/
./backend/sql/check_dominic_usage.sql                         → archive/
./backend/sql/check_dominic_usage_simple.sql                  → archive/
./backend/sql/reset_dominic_quota_to_zero.sql                 → archive/

# Scripts de vérification ponctuels (obsolètes)
./backend/sql/check_billing_plans.sql                         → archive/
./backend/sql/check_user_billing_info_structure.sql           → archive/
./backend/sql/list_existing_plans.sql                         → archive/
./backend/sql/restore_free_plan_quota.sql                     → archive/

# Scripts temporaires de test
./backend/sql/temp_reduce_essential_limit_for_testing.sql     → archive/
./backend/sql/temp_restore_essential_limit.sql                → archive/
```

**Total à archiver: 15 scripts SQL**

### 5.3 README.md à créer
```bash
# CRÉER ces fichiers de documentation:
backend/sql/archive/README.md                      # Expliquer l'historique
backend/sql/migrations/README.md                   # Guide des migrations
backend/sql/maintenance/README.md                  # Quand utiliser ces scripts
```

---

## 📂 SECTION 6: Structure finale des dossiers

### 6.1 Racine du projet (MINIMALISTE)
```
C:\intelia_gpt\intelia-expert\
├── README.md                      # Index principal
├── SETUP_GUIDE.md                 # Guide installation
├── THIRD_PARTY_NOTICES.md         # Licences
├── .gitignore
├── docker-compose.yml
├── llm/                           # Service LLM
├── ai-service/                    # Service AI/RAG
├── backend/                       # API Backend
├── frontend/                      # Application Next.js
├── poc_realtime/                  # POC Voice (bien organisé)
├── rag/                           # Modules RAG
└── docs/                          # TOUTE LA DOCUMENTATION
```

### 6.2 llm/ (SERVICE LLM)
```
llm/
├── README.md                      # ✅ Doc service
├── TERMINOLOGY_ENRICHMENT.md      # ✅ Doc fonctionnalité
├── .env
├── Dockerfile
├── requirements.txt
├── app/                           # Code application
├── config/                        # Configuration
├── scripts/                       # Scripts utilitaires
├── tests/                         # ⭐ CRÉER - Tous les tests
│   ├── test_complete_system.py
│   ├── test_compliance.py
│   ├── test_full_generation.py
│   ├── test_generation_api.py
│   ├── test_load.py
│   ├── test_performance_optimizations.py
│   ├── test_streaming.py
│   ├── test_terminology_injection.py
│   └── test_value_chain_coverage.py
└── vllm/                          # VLLM integration
```

### 6.3 ai-service/ (SERVICE AI/RAG)
```
ai-service/
├── README.md                      # ✅ Doc service
├── .env
├── Dockerfile
├── main.py
├── requirements.txt
├── api/                           # Routes API
├── config/                        # Configuration
│   └── README_TERMINOLOGY.md      # ✅ Doc config
├── core/                          # Core logic
├── generation/                    # LLM generation
├── retrieval/                     # RAG retrieval
├── scripts/                       # Scripts utilitaires
│   ├── README.md                  # ✅ Doc scripts
│   └── testing/                   # ✅ Tests spécialisés (GARDER)
├── tests/                         # ✅ Tests (bien organisé)
│   ├── integration/
│   │   └── README.md
│   ├── README.md
│   └── README_TESTS.md
└── utils/                         # Utilitaires
```

### 6.4 backend/ (API BACKEND)
```
backend/
├── .env
├── Dockerfile
├── requirements.txt
├── app/                           # Code application
├── email_templates/               # Templates email
├── migrations/                    # Migrations DB
│   └── run_migration.md           # ✅ Guide
├── scripts/                       # Scripts utilitaires
├── sql/                           # Scripts SQL
│   ├── README.md                  # ✅ Guide général
│   ├── schema/                    # Schémas de tables
│   ├── migrations/                # Migrations appliquées
│   │   └── README.md              # ⭐ CRÉER
│   ├── stripe/                    # Scripts Stripe
│   │   ├── README.md              # ✅ Guide Stripe
│   │   ├── INTELIA_PLAN_README.md
│   │   └── PRICING_MANAGEMENT_GUIDE.md
│   ├── whatsapp/                  # Scripts WhatsApp
│   ├── fixes/                     # Correctifs
│   │   ├── README_PROFILE_FIX.md
│   │   ├── RECREATE_ADMIN_USER_GUIDE.md
│   │   └── SECURITY_FIXES_GUIDE.md
│   ├── maintenance/               # Scripts maintenance
│   │   └── README.md              # ⭐ CRÉER
│   ├── queries/                   # Requêtes utiles
│   └── archive/                   # ⭐ CRÉER - Scripts obsolètes
│       └── README.md              # ⭐ CRÉER
├── static/                        # Fichiers statiques
└── tests/                         # ⭐ CRÉER
    ├── test_monitoring.py
    └── manual/                    # ⭐ CRÉER
        ├── check_twilio_message_status.py
        └── test_whatsapp_update.py
```

### 6.5 frontend/ (APPLICATION NEXT.JS)
```
frontend/
├── REFACTORING_PLAN.md            # → DÉPLACER vers docs/frontend/
├── .env
├── next.config.js
├── package.json
├── app/                           # Pages Next.js
├── components/                    # Composants React
└── public/
    └── THIRD_PARTY_NOTICES.md     # ✅ Licenses publiques
```

### 6.6 docs/ (DOCUMENTATION CENTRALISÉE)
```
docs/
├── README.md                      # Index de la documentation
├── CLAUDE_INSTRUCTIONS.md         # Instructions générales Claude
│
├── analysis/                      # Analyses techniques
│   ├── CHAIN_OF_THOUGHT_ANALYSIS.md
│   ├── COST_ANALYSIS.md
│   ├── LLM_BOTTLENECK_ANALYSIS.md
│   └── ...
│
├── backend/                       # Documentation backend
│   ├── AUDIO_STORAGE_SETUP.md
│   ├── CURRENCY_RATES_SETUP.md
│   ├── ENV_VARIABLES_COMPLETE.md
│   ├── QA_ANALYSIS_REPORT.md
│   └── QUOTA_SYSTEM_README.md
│
├── configuration/                 # Configuration
│   ├── DIGITAL_OCEAN_EXTERNAL_SOURCES_LOGS.md
│   └── EXTERNAL_SOURCES_CONFIG.md
│
├── deployment/                    # Guides déploiement
│   ├── CRON_SETUP_INSTRUCTIONS.md
│   ├── DEPLOY_CHECKLIST.md
│   ├── DEPLOYMENT_PRODUCTION_GUIDE.md
│   ├── DEPLOYMENT_GUIDE_COUNTRY_TRACKING.md
│   ├── VERIFY_COT_DEPLOYMENT.md
│   └── VOICE_REALTIME_DEPLOYMENT.md
│
├── frontend/                      # ⭐ CRÉER
│   ├── README.md
│   ├── REFACTORING_PLAN.md
│   ├── MOBILE_REDESIGN_PROJECT.md
│   ├── PWA_IMPLEMENTATION.md
│   └── FRONTEND_UI_IMPLEMENTATION.md
│
├── guides/                        # Guides pratiques
│   ├── billing/                   # ⭐ CRÉER
│   │   ├── README.md
│   │   ├── BILLING_CURRENCY_SETUP.md
│   │   ├── STRIPE_IMPLEMENTATION_COMPLETE.md
│   │   ├── STRIPE_WEBHOOK_POST_CONFIG.md
│   │   └── ...
│   ├── enterprise/                # ⭐ CRÉER
│   │   ├── README.md
│   │   ├── CORPORATE_MIGRATION_STRATEGY.md
│   │   └── CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md
│   ├── AI_SERVICE_INTEGRATION.md
│   ├── LLM_SERVICE_INTEGRATION.md
│   ├── WEBAUTHN_IMPLEMENTATION.md
│   ├── WIDGET_INTEGRATION_GUIDE.md
│   └── ... (40+ guides)
│
├── implementation/                # ⭐ CRÉER
│   ├── README.md
│   ├── CLAUDE_COT_IMPLEMENTATION_PLAN.md
│   ├── COT_PHASES_2_3_IMPLEMENTATION.md
│   ├── COT_ANOMALY_INTEGRATION.md
│   ├── IMPLEMENTATION_BROILER_LAYER_COT.md
│   └── IMPLEMENTATION_PLAN_USER_PROFILING.md
│
├── migration/                     # Guides migration
│   ├── EXECUTE_NOW.md
│   ├── MIGRATION_COMPLETED.md
│   ├── MIGRATION_GUIDE.md
│   ├── MIGRATION_STATUS.md
│   └── ...
│
├── operations/                    # Opérations
│   ├── GRAFANA_SETUP.md
│   ├── VERSION_MANAGEMENT.md
│   ├── MULTILINGUAL_EMAIL_SETUP.md
│   └── ...
│
├── reports/                       # Rapports d'implémentation
│   ├── COMPLETION_REPORT.md
│   ├── LLM_OPTIMIZATION_COMPLETE_SUMMARY.md
│   ├── STREAMING_IMPLEMENTATION_REPORT.md
│   ├── PHASE_1A_OPTIMIZATION_REPORT.md
│   ├── PHASE_1B_SUMMARY.md
│   └── ... (20+ rapports)
│
├── security/                      # Sécurité et GDPR
│   ├── README.md
│   ├── GDPR_COMPLIANCE_AUDIT.md
│   ├── SECURITY_VALIDATION_REPORT.md
│   ├── DATA_RETENTION_POLICY.md
│   └── ...
│
└── archive/                       # ⭐ CRÉER - Obsolètes mais historiques
    ├── README.md
    ├── DOCS_REORGANIZATION_PLAN.md
    └── setTimeout_analysis.md
```

---

## 🎯 SECTION 7: Plan d'exécution par phases

### Phase 1: Nettoyage immédiat (URGENT - 5 min)
```bash
# Supprimer fichiers backup
rm ./.github/workflows/deploy.yml.bak
rm ./ai-service/config/poultry_terminology.json.OLD
rm ./frontend/app/chat/components/modals/*.bak
rm ./frontend/app/chat/components/modals/*.backup

# Supprimer cache webpack
find ./frontend/.next/cache/webpack -name "*.old" -delete

# Supprimer scripts temporaires
rm ./ai-service/analyze_all_settimeout.js
rm ./ai-service/deep-settimeout-analysis.js
rm ./ai-service/eslint-check-settimeout.js
rm ./ai-service/find_unsafe_settimeout.sh

# Supprimer résultats de tests
rm ./llm/load_test_results.json
rm ./backend/qa_analysis_*.json
rm ./backend/qa_analysis_*.txt

# Supprimer notes temporaires
rm ./test_fresh_query.md
rm ./ai-service/run-dev-mode.md
rm ./backend/trigger.txt
rm ./ai-service/.deploytest
rm ./backend/.deploytest
```

### Phase 2: Créer la nouvelle structure (10 min)
```bash
# Créer dossiers docs
mkdir -p docs/frontend
mkdir -p docs/implementation
mkdir -p docs/archive
mkdir -p docs/guides/billing
mkdir -p docs/guides/enterprise

# Créer dossiers SQL
mkdir -p backend/sql/archive

# Créer dossiers tests
mkdir -p llm/tests
mkdir -p backend/tests/manual

# Créer README.md
touch docs/frontend/README.md
touch docs/implementation/README.md
touch docs/archive/README.md
touch docs/guides/billing/README.md
touch docs/guides/enterprise/README.md
touch backend/sql/archive/README.md
touch backend/sql/migrations/README.md
touch backend/sql/maintenance/README.md
```

### Phase 3: Déplacer tests Python (10 min)
```bash
# llm/ tests
git mv ./llm/test_*.py ./llm/tests/

# backend/ tests
git mv ./backend/check_twilio_message_status.py ./backend/tests/manual/
git mv ./backend/test_whatsapp_update.py ./backend/tests/manual/
git mv ./backend/test_monitoring.py ./backend/tests/
```

### Phase 4: Archiver scripts SQL (5 min)
```bash
cd backend/sql
git mv add_essential_subscription_dominic*.sql archive/
git mv add_free_subscription_dominic*.sql archive/
git mv check_dominic_usage*.sql archive/
git mv reset_dominic_quota_to_zero.sql archive/
git mv check_billing_plans.sql archive/
git mv check_user_billing_info_structure.sql archive/
git mv list_existing_plans.sql archive/
git mv restore_free_plan_quota.sql archive/
git mv temp_*.sql archive/
cd ../..
```

### Phase 5: Déplacer documentation backend (10 min)
```bash
# Documentation backend
git mv ./backend/AUDIO_STORAGE_SETUP.md ./docs/backend/
git mv ./backend/CURRENCY_RATES_SETUP.md ./docs/backend/
git mv ./backend/ENV_VARIABLES_COMPLETE.md ./docs/backend/
git mv ./backend/QA_ANALYSIS_REPORT.md ./docs/backend/
git mv ./backend/QUOTA_SYSTEM_README.md ./docs/backend/
git mv ./backend/VOICE_REALTIME_DEPLOYMENT.md ./docs/deployment/

# Documentation ai-service
git mv ./ai-service/core/INTEGRATION_GUIDE.md ./docs/guides/

# Documentation frontend
git mv ./frontend/REFACTORING_PLAN.md ./docs/frontend/

# Archives
git mv ./ai-service/setTimeout_analysis.md ./docs/archive/
```

### Phase 6: Déplacer fichiers de la racine (30 min)
```bash
# Guides généraux
git mv AI_SERVICE_INTEGRATION.md docs/guides/
git mv LLM_SERVICE_INTEGRATION.md docs/guides/
git mv LLM_SERVICE_SPECS.md docs/guides/
git mv REAL_TIME_VOICE_PLAN.md docs/guides/
git mv WEBAUTHN_IMPLEMENTATION.md docs/guides/
git mv WIDGET_INTEGRATION_GUIDE.md docs/guides/
git mv SATISFACTION_SURVEY_MOCKUP.md docs/guides/
git mv POULTRY_PRODUCTION_COUNTRIES.md docs/guides/

# Billing
git mv BILLING_CURRENCY_SETUP.md docs/guides/billing/
git mv STRIPE_*.md docs/guides/billing/
git mv PRICING_FRAUD_PREVENTION_STRATEGY.md docs/guides/billing/

# Enterprise
git mv CORPORATE_*.md docs/guides/enterprise/

# Frontend
git mv FRONTEND_UI_IMPLEMENTATION.md docs/frontend/
git mv MOBILE_REDESIGN_PROJECT.md docs/frontend/
git mv PWA_IMPLEMENTATION.md docs/frontend/

# Implementation
git mv IMPLEMENTATION_*.md docs/implementation/
git mv COT_PHASES_2_3_IMPLEMENTATION.md docs/implementation/

# Analysis
git mv CHAIN_OF_THOUGHT_ANALYSIS.md docs/analysis/
git mv COST_ANALYSIS.md docs/analysis/
git mv LLM_BOTTLENECK_ANALYSIS.md docs/analysis/
git mv SUBSCRIPTION_TIERS_ANALYSIS.md docs/analysis/
git mv WEAVIATE_EMBEDDING_ANALYSIS.md docs/analysis/

# Reports
git mv CACHING_AND_PROMPT_OPTIMIZATION_REPORT.md docs/reports/
git mv COMPLETION_REPORT.md docs/reports/
git mv DATA_FLOW_OPTIMIZATION_*.md docs/reports/
git mv LLM_INTEGRATION_TEST_RESULTS.md docs/reports/
git mv LLM_OPTIMIZATION_COMPLETE_SUMMARY.md docs/reports/
git mv METRIQUES_PHASE2_ETAT_ACTUEL.md docs/reports/
git mv MODEL_ROUTING_IMPLEMENTATION_REPORT.md docs/reports/
git mv MULTILINGUAL_STRATEGY_REPORT.md docs/reports/
git mv OPTIMIZATION_SUMMARY.md docs/reports/
git mv STREAMING_IMPLEMENTATION_REPORT.md docs/reports/
git mv VOICE_REALTIME_PHASE1_COMPLETE.md docs/reports/
git mv VOICE_SETTINGS_IMPLEMENTATION_SUMMARY.md docs/reports/
git mv PHASE_1*.md docs/reports/

# Deployment
git mv DEPLOYMENT_GUIDE_COUNTRY_TRACKING.md docs/deployment/
git mv VERIFY_COT_DEPLOYMENT.md docs/deployment/

# Security
git mv CSP_MONITORING_GUIDE.md docs/security/
git mv DATA_RETENTION_POLICY.md docs/security/
git mv GDPR_*.md docs/security/
git mv HSTS_PRELOAD_GUIDE.md docs/security/
git mv SECURITY_*.md docs/security/
git mv SRI_IMPLEMENTATION_GUIDE.md docs/security/

# Operations
git mv GRAFANA_SETUP.md docs/operations/
git mv VERSION_MANAGEMENT.md docs/operations/

# Migration
git mv MIGRATION_STATUS.md docs/migration/

# Archive
git mv CHANGELOG_PHASE_1B.md docs/archive/
```

### Phase 7: Déplacer fichiers dans docs/ (10 min)
```bash
# Déplacer fichiers mal placés dans docs/ vers sous-dossiers
cd docs
git mv CLAUDE_COT_IMPLEMENTATION_PLAN.md implementation/
git mv COT_ANOMALY_INTEGRATION.md implementation/
git mv DIGITALOCEAN_ENV_SETUP.md deployment/
git mv MEDICAL_IMAGE_ANALYSIS_GUIDE.md guides/
git mv VOICE_REALTIME.md guides/
git mv DOCS_REORGANIZATION_PLAN.md archive/
cd ..
```

### Phase 8: Créer les README.md de documentation (15 min)
```bash
# Créer les README.md avec descriptions
# (À faire manuellement avec contenu approprié)
```

### Phase 9: Validation finale (10 min)
```bash
# Vérifier que la racine est propre
ls -la | grep .md
# Devrait montrer seulement: README.md, SETUP_GUIDE.md, THIRD_PARTY_NOTICES.md

# Vérifier docs/
find docs -type f -name "*.md" | wc -l
# Devrait montrer tous les .md

# Vérifier tests
ls -la llm/tests/
ls -la backend/tests/

# Vérifier SQL archive
ls -la backend/sql/archive/
```

### Phase 10: Commit Git (5 min)
```bash
git add .
git commit -m "chore: Massive cleanup and reorganization

- Remove 24 backup and temporary files
- Organize 10 test files in llm/tests/
- Archive 15 obsolete SQL scripts
- Move 55 .md files from root to docs/
- Move 6 backend .md files to docs/backend/
- Create new structure: docs/{frontend,implementation,archive}
- Create new structure: docs/guides/{billing,enterprise}
- Add README.md in all new directories

Project is now clean with only 3 .md at root:
- README.md (main index)
- SETUP_GUIDE.md (quick start)
- THIRD_PARTY_NOTICES.md (licenses)

All documentation is centralized in docs/ with clear categories."
```

---

## 📊 SECTION 8: Métriques de nettoyage

### Avant
- **278 fichiers .md** dispersés dans le projet
- **76 fichiers .sql** dans backend/sql/
- **24 fichiers backup/temporaires** inutiles
- **55 fichiers .md à la racine**
- **10 tests Python** à la racine de llm/
- **3 tests Python** à la racine de backend/
- **31 fichiers** avec TODOs
- **15 scripts SQL** temporaires dans backend/sql/

### Après
- **3 fichiers .md à la racine** (README, SETUP_GUIDE, THIRD_PARTY_NOTICES)
- **0 fichiers backup** restants
- **0 tests Python** à la racine
- **Structure claire en 9 catégories** dans docs/
- **Tests organisés** dans llm/tests/ et backend/tests/
- **SQL archivé** dans backend/sql/archive/
- **15+ README.md** de navigation créés

### Gain de clarté
- ✅ Racine épurée (55 → 3 fichiers .md)
- ✅ Documentation centralisée
- ✅ Tests organisés par service
- ✅ SQL archivé proprement
- ✅ Structure navigable
- ✅ Historique Git préservé

---

## ✅ SECTION 9: Checklist de validation

### Validation structure
- [ ] Racine contient seulement 3 .md
- [ ] Tous les fichiers backup supprimés
- [ ] Tous les tests dans des dossiers tests/
- [ ] Tous les SQL temporaires archivés
- [ ] docs/ organisé en 9 catégories
- [ ] README.md créés dans chaque sous-dossier

### Validation services
- [ ] llm/ : tests dans llm/tests/
- [ ] ai-service/ : structure préservée
- [ ] backend/ : doc déplacée, tests organisés, SQL archivé
- [ ] frontend/ : doc déplacée vers docs/frontend/

### Validation documentation
- [ ] Aucun fichier .md orphelin
- [ ] Tous les guides dans docs/guides/
- [ ] Tous les rapports dans docs/reports/
- [ ] Toute l'analyse dans docs/analysis/
- [ ] Toute la sécurité dans docs/security/

### Validation Git
- [ ] Historique Git préservé (git mv utilisé)
- [ ] Commit descriptif créé
- [ ] Aucun fichier perdu

---

## 🚀 SECTION 10: Prochaines étapes après cleanup

### Documentation à créer
1. docs/README.md - Index principal de la documentation
2. docs/frontend/README.md - Guide frontend
3. docs/implementation/README.md - Guide implémentation
4. docs/guides/billing/README.md - Guide billing/Stripe
5. docs/guides/enterprise/README.md - Guide entreprise
6. docs/archive/README.md - Expliquer l'historique
7. backend/sql/archive/README.md - Scripts obsolètes
8. backend/sql/migrations/README.md - Guide migrations
9. backend/sql/maintenance/README.md - Scripts maintenance

### TODOs critiques à traiter (identifiés dans analyse)
1. CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md - Plan incomplet
2. WIDGET_INTEGRATION_GUIDE.md - Implémentation widget
3. DATA_RETENTION_POLICY.md - Politique GDPR
4. SUBSCRIPTION_TIERS_ANALYSIS.md - Analyse tiers
5. BILLING_CURRENCY_SETUP.md - Multi-devises
6. SECURITY_VALIDATION_REPORT.md - Tests sécurité
7. GDPR_COMPLIANCE_AUDIT.md - Audit GDPR

### Améliorations futures
- Créer index de navigation dans docs/README.md
- Ajouter badges de statut aux documents
- Créer script de validation de structure
- Automatiser la génération de table des matières

---

**Prêt pour exécution**: OUI ✅
**Durée estimée**: 2 heures
**Risque**: FAIBLE (utilise git mv, historique préservé)

---

**Décision requise**: Voulez-vous que j'exécute ce plan :
1. ✅ Automatiquement en entier (2h)
2. 📝 Phase par phase avec validation
3. 🔧 Modifier certains aspects du plan

