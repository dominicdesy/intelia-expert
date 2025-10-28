# Intelia Expert - Documentation

Bienvenue dans la documentation complète du projet Intelia Expert.

> **📌 Instructions Claude Code:** [guidelines/CLAUDE_INSTRUCTIONS.md](./guidelines/CLAUDE_INSTRUCTIONS.md) - Guide pour les interactions avec Claude Code (conventions, architecture, workflow)

## 📚 Structure de la Documentation

### 📊 [Reports](./reports/)
Rapports d'implémentation et d'optimisation du système.

**Implémentation:**
- [External Sources Implementation](./reports/EXTERNAL_SOURCES_IMPLEMENTATION_REPORT.md) - Système de sources externes (Semantic Scholar, PubMed, Europe PMC)
- [Data Ingestion Implementation Plan](./reports/DATA_INGESTION_IMPLEMENTATION_PLAN.md) - Plan d'ingestion de données
- [Unified Chunking Implementation](./reports/UNIFIED_CHUNKING_IMPLEMENTATION_REPORT.md) - Système de chunking unifié
- [LLM Clarification Implementation](./reports/LLM_CLARIFICATION_IMPLEMENTATION_REPORT.md) - Système de clarification LLM

**Optimisation:**
- [Phase 1 Optimization](./reports/PHASE_1_OPTIMIZATION_REPORT.md) - Optimisation Phase 1 (RRF, Cohere)
- [Quick Win Report](./reports/QUICK_WIN_REPORT.md) - Gains rapides d'optimisation
- [Language Bug Fix](./reports/LANGUAGE_BUG_FIX_REPORT.md) - Correction du bug multilingue
- [Language Detection Fixes](./reports/LANGUAGE_DETECTION_FIXES_REPORT.md) - Améliorations détection de langue

**Modules:**
- [Rapport Utilisation Modules](./reports/RAPPORT_UTILISATION_MODULES.md) - Analyse utilisation des modules

### 🔬 [Analysis](./analysis/)
Analyses techniques et audits de qualité.

**Code Quality:**
- [Dead Code Analysis](./analysis/DEAD_CODE_ANALYSIS_REPORT.md) - Analyse du code mort
- [Argument Type Errors](./analysis/ARGUMENT_TYPE_ERRORS_ANALYSIS.md) - Analyse des erreurs de type
- [Unbound Variables](./analysis/UNBOUND_VARIABLES_FINAL_REPORT.md) - Analyse des variables non liées

**System Analysis:**
- [Contextualization System](./analysis/CONTEXTUALIZATION_SYSTEM_ANALYSIS.md) - Analyse du système de contextualisation
- [Faithfulness Root Cause](./analysis/FAITHFULNESS_ROOT_CAUSE.md) - Analyse de la fidélité des réponses
- [Chunking Strategy](./analysis/CHUNKING_STRATEGY_ANALYSIS.md) - Analyse de la stratégie de chunking

### 🔒 [Security](./security/)
Rapports d'audit de sécurité et analyses de vulnérabilités.

**Security Audits:**
- [Security Analysis Report](./security/SECURITY_ANALYSIS_REPORT.md) - Analyse complète de sécurité
- [Security Audit Report](./security/SECURITY_AUDIT_REPORT.md) - Audit de sécurité détaillé
- [Security Final Summary](./security/SECURITY_FINAL_SUMMARY.md) - Résumé final de sécurité
- [Security Tools Analysis](./security/SECURITY_TOOLS_ANALYSIS.md) - Analyse des outils de sécurité

**SQL Security:**
- [SQL Injection Audit Report](./security/SQL_INJECTION_AUDIT_REPORT.md) - Audit SQL injection
- [Medium Issues Analysis](./security/MEDIUM_ISSUES_ANALYSIS.md) - Analyse des problèmes MEDIUM (Bandit)

### 🔧 [Backend](./backend/)
Documentation spécifique au backend.

- [GDPR Compliance Report](./backend/GDPR_COMPLIANCE_REPORT.md) - Conformité RGPD
- [QA Quality Tool README](./backend/QA_QUALITY_TOOL_README.md) - Outil d'analyse qualité QA

### ⚙️ [Configuration](./configuration/)
Guides de configuration du système.

- [External Sources Config](./configuration/EXTERNAL_SOURCES_CONFIG.md) - Configuration des sources externes

### 📖 [Guides](./guides/)
Guides utilisateur et documentation technique complète.

**System Guides:**
- [Complete System Documentation](./guides/COMPLETE_SYSTEM_DOCUMENTATION.md) - Documentation système complète
- [Database Schema](./guides/DATABASE_SCHEMA.md) - Schéma de base de données
- [Complete Entity Taxonomy](./guides/COMPLETE_ENTITY_TAXONOMY.md) - Taxonomie des entités

**Integration Guides:**
- [External Sources README](./guides/EXTERNAL_SOURCES_README.md) - Guide sources externes
- [Evaluation Quickstart](./guides/EVALUATION_QUICKSTART.md) - Guide rapide d'évaluation
- [RAG LLM Integration](./guides/RAG_LLM_INTEGRATION.md) - Intégration RAG-LLM
- [Hybrid Extraction Deployment](./guides/HYBRID_EXTRACTION_DEPLOYMENT.md) - Déploiement extraction hybride
- [LLM Ensemble Guide](./guides/LLM_ENSEMBLE_GUIDE.md) - Guide LLM Ensemble

**Strategy & Analysis:**
- [Domain Detection Strategy](./guides/DOMAIN_DETECTION_STRATEGY.md) - Stratégie de détection de domaine
- [Query Routing 100% Coverage](./guides/QUERY_ROUTING_100_PERCENT_COVERAGE.md) - Routage de requêtes
- [Query Understanding Analysis](./guides/QUERY_UNDERSTANDING_ANALYSIS.md) - Analyse de compréhension
- [Reranker Comparison](./guides/RERANKER_COMPARISON.md) - Comparaison des rerankers

**Quality & Testing:**
- [Quality Audit Current System](./guides/QUALITY_AUDIT_CURRENT_SYSTEM.md) - Audit qualité
- [Test Coverage Analysis](./guides/TEST_COVERAGE_ANALYSIS.md) - Analyse couverture de tests
- [RAGAS Analysis Report](./guides/RAGAS_ANALYSIS_REPORT.md) - Rapport RAGAS
- [README Admin RAGAS](./guides/README_ADMIN_RAGAS.md) - Guide admin RAGAS
- [README Analyse](./guides/README_ANALYSE.md) - Guide d'analyse
- [README Evaluation](./guides/README_EVALUATION.md) - Guide d'évaluation
- [Resultats Analyse](./guides/RESULTATS_ANALYSE.md) - Résultats d'analyse

**CI/CD & Deployment:**
- [CI/CD Setup](./guides/CI_CD_SETUP.md) - Configuration CI/CD
- [Deployment Fix](./guides/DEPLOYMENT_FIX.md) - Corrections déploiement

**Phase Reports:**
- [Phase 2 Completion](./guides/PHASE2_COMPLETION_REPORT.md) - Rapport Phase 2
- [Phase 2 Test Results](./guides/PHASE2_TEST_RESULTS.md) - Résultats tests Phase 2
- [Phase 3 Completion](./guides/PHASE3_COMPLETION_REPORT.md) - Rapport Phase 3
- [Phase 3 Roadmap](./guides/PHASE3_ROADMAP.md) - Roadmap Phase 3
- [Audit Integration Phase 2 Final](./guides/AUDIT_INTEGRATION_PHASE2_FINAL.md) - Audit Phase 2

**Optimization:**
- [Sessions Optimisation Roadmap](./guides/SESSIONS_OPTIMISATION_ROADMAP.md) - Roadmap optimisation
- [Rapport Optimisation Final](./guides/RAPPORT_OPTIMISATION_FINAL.md) - Rapport final
- [Quick Wins Implementation](./guides/QUICK_WINS_IMPLEMENTATION.md) - Implémentation gains rapides
- [Pyright Safe Fixes](./guides/PYRIGHT_SAFE_FIXES.md) - Corrections sûres Pyright
- [Critical Errors Analysis](./guides/CRITICAL_ERRORS_ANALYSIS.md) - Analyse erreurs critiques
- [Obsolete Files LLM OOD](./guides/OBSOLETE_FILES_LLM_OOD.md) - Fichiers obsolètes

**Tools & Integrations:**
- [External Tools Recommendations](./guides/EXTERNAL_TOOLS_RECOMMENDATIONS.md) - Recommandations outils
- [Ensemble Integration Example](./guides/ENSEMBLE_INTEGRATION_EXAMPLE.md) - Exemple intégration ensemble
- [ZEP Impact Analysis](./guides/ZEP_IMPACT_ANALYSIS.md) - Analyse impact ZEP

### 🚀 [Deployment](./deployment/)
Guides de déploiement et checklists de mise en production.

- [Deployment Production Guide](./deployment/DEPLOYMENT_PRODUCTION_GUIDE.md) - Guide de déploiement en production
- [Deploy Checklist](./deployment/DEPLOY_CHECKLIST.md) - Checklist de déploiement
- [Cron Setup Instructions](./deployment/CRON_SETUP_INSTRUCTIONS.md) - Instructions configuration CRON

### ⚡ [Operations](./operations/)
Documentation opérationnelle, diagnostics et configuration.

- [Diagnostic Statistiques Beta](./operations/DIAGNOSTIC_STATISTIQUES_BETA.md) - Diagnostic stats beta
- [Solution Stats Beta Resume](./operations/SOLUTION_STATS_BETA_RESUME.md) - Résumé solution stats
- [Multilingual Email Setup](./operations/MULTILINGUAL_EMAIL_SETUP.md) - Configuration emails multilingues

### 📜 [Migration](./migration/)
Archives de migration et historique de changements importants.

- [Migration Guide](./migration/MIGRATION_GUIDE.md) - Guide de migration
- [Migration Completed](./migration/MIGRATION_COMPLETED.md) - Migration complétée
- [Migration Summary Final](./migration/MIGRATION_SUMMARY_FINAL.md) - Résumé final de migration
- [Ready to Migrate](./migration/READY_TO_MIGRATE.md) - Prêt à migrer
- [Execute Now](./migration/EXECUTE_NOW.md) - Exécution migration
- [Q&A Page Fix](./migration/Q&A_PAGE_FIX.md) - Correction page Q&A

### 📋 [Planning](./planning/)
Gestion de projet, TODOs et guides de décision.

- [TODOs en Suspens](./planning/TODOS_EN_SUSPENS.md) - Inventaire des tâches en attente
- [Guide de Décision TODOs](./planning/TODOS_DECISION_GUIDE.md) - Guide pour prioriser les tâches
- [Plan de Complétion Multilingue](./planning/MULTILINGUAL_COMPLETION_PLAN.md) - Plan pour aligner les 4 services sur 16 langues
- [Stratégie d'Implémentation Multilingue](./planning/MULTILINGUAL_IMPLEMENTATION_STRATEGY.md) - Guide détaillé pour étendre les structures i18n existantes

### 📘 [Guidelines](./guidelines/)
Directives et conventions pour le développement.

- [Claude Code Instructions](./guidelines/CLAUDE_INSTRUCTIONS.md) - Instructions pour Claude Code (architecture, conventions, workflow)

### 📦 [Archive](./archive/)
Documentation historique et fichiers obsolètes.

---

## 🚀 Quick Links

### Pour démarrer
1. [Complete System Documentation](./guides/COMPLETE_SYSTEM_DOCUMENTATION.md) - Vue d'ensemble du système
2. [Database Schema](./guides/DATABASE_SCHEMA.md) - Comprendre la structure de données
3. [External Sources Config](./configuration/EXTERNAL_SOURCES_CONFIG.md) - Configurer les sources externes

### Pour développer
1. [RAG LLM Integration](./guides/RAG_LLM_INTEGRATION.md) - Intégrer le RAG
2. [Hybrid Extraction Deployment](./guides/HYBRID_EXTRACTION_DEPLOYMENT.md) - Déployer l'extraction
3. [CI/CD Setup](./guides/CI_CD_SETUP.md) - Configurer CI/CD

### Pour déployer
1. [Deployment Production Guide](./deployment/DEPLOYMENT_PRODUCTION_GUIDE.md) - Déployer en production
2. [Deploy Checklist](./deployment/DEPLOY_CHECKLIST.md) - Checklist pré-déploiement
3. [Cron Setup Instructions](./deployment/CRON_SETUP_INSTRUCTIONS.md) - Configurer les tâches CRON

### Pour la sécurité
1. [Security Final Summary](./security/SECURITY_FINAL_SUMMARY.md) - Vue d'ensemble sécurité
2. [SQL Injection Audit Report](./security/SQL_INJECTION_AUDIT_REPORT.md) - Audit SQL
3. [GDPR Compliance Report](./backend/GDPR_COMPLIANCE_REPORT.md) - Conformité RGPD

### Pour optimiser
1. [Phase 1 Optimization](./reports/PHASE_1_OPTIMIZATION_REPORT.md) - Voir les optimisations
2. [RAGAS Analysis Report](./guides/RAGAS_ANALYSIS_REPORT.md) - Analyser la qualité
3. [Reranker Comparison](./guides/RERANKER_COMPARISON.md) - Choisir un reranker

### Pour tester
1. [Evaluation Quickstart](./guides/EVALUATION_QUICKSTART.md) - Démarrer l'évaluation
2. [Test Coverage Analysis](./guides/TEST_COVERAGE_ANALYSIS.md) - Analyser la couverture
3. [Phase 2 Test Results](./guides/PHASE2_TEST_RESULTS.md) - Voir les résultats

---

## 📁 Autres READMEs du Projet

- [Root README](../README.md) - README principal du projet
- [LLM README](../llm/README.md) - README du module LLM
- [Backend README](../backend/README.md) - README du backend
- [Frontend README](../frontend/README.md) - README du frontend
- [Scripts README](../llm/scripts/README.md) - README des scripts
- [Tests README](../llm/tests/README_TESTS.md) - README des tests
- [Integration Tests README](../llm/tests/integration/README.md) - README tests d'intégration

---

## 🔧 Structure du Projet

```
intelia-expert/
├── docs/                    # 📚 Toute la documentation (vous êtes ici)
│   ├── reports/            # Rapports d'implémentation et optimisation
│   ├── analysis/           # Analyses techniques et audits
│   ├── security/           # 🔒 Rapports de sécurité et audits
│   ├── backend/            # Documentation backend (GDPR, QA)
│   ├── configuration/      # Guides de configuration
│   ├── guides/             # Guides utilisateur et documentation
│   ├── deployment/         # 🚀 Guides de déploiement
│   ├── operations/         # ⚡ Documentation opérationnelle
│   ├── migration/          # 📜 Archives de migration
│   ├── planning/           # 📋 Gestion de projet et TODOs
│   ├── guidelines/         # 📘 Directives et conventions
│   └── archive/            # Documentation historique
├── llm/                    # 🧠 Module LLM principal
│   ├── scripts/           # Scripts utilitaires
│   │   ├── analysis/      # Scripts d'analyse de code
│   │   ├── testing/       # Scripts de tests
│   │   ├── fixes/         # Scripts de corrections
│   │   └── audit/         # Scripts d'audit
│   └── tools/             # Outils de développement
│       └── analysis_outputs/  # Sorties d'analyse
├── backend/                # 🔙 Backend API
├── frontend/              # 🎨 Frontend Next.js
└── rag/                   # 📄 Système RAG
```

---

## 📝 Conventions de Documentation

### Nommage des Fichiers
- **Reports:** `*_REPORT.md` - Rapports d'implémentation/optimisation
- **Analysis:** `*_ANALYSIS.md` - Analyses techniques
- **Guides:** `README_*.md` ou guides descriptifs
- **Config:** `*_CONFIG.md` - Guides de configuration

### Structure des Documents
1. **Titre principal** - Nom clair du document
2. **Résumé** - Vue d'ensemble (2-3 phrases)
3. **Table des matières** - Pour documents > 500 lignes
4. **Contenu principal** - Sections logiques
5. **Exemples** - Code et cas d'usage
6. **Références** - Liens vers autres docs

---

## 🤝 Contribution

Pour ajouter de la documentation:

1. **Choisir le bon dossier:**
   - `reports/` → Rapports d'implémentation/optimisation
   - `analysis/` → Analyses techniques/audits
   - `security/` → Rapports d'audit de sécurité
   - `backend/` → Documentation backend (GDPR, QA)
   - `configuration/` → Guides de configuration
   - `guides/` → Documentation utilisateur
   - `deployment/` → Guides de déploiement
   - `operations/` → Documentation opérationnelle
   - `migration/` → Archives de migration
   - `planning/` → Gestion de projet et TODOs
   - `guidelines/` → Directives et conventions
   - `archive/` → Documentation obsolète

2. **Suivre les conventions** de nommage ci-dessus

3. **Mettre à jour ce README** avec le nouveau document

4. **Ajouter des liens croisés** vers docs connexes

---

**Dernière mise à jour:** Octobre 2025
