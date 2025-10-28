# Instructions Claude Code - Intelia Expert

**Date de création:** 2025-10-12
**Projet:** Intelia Expert - Plateforme RAG pour l'aviculture
**Environnement:** Production - https://expert.intelia.com

---

## 📋 Vue d'ensemble du projet

Intelia Expert est une plateforme RAG (Retrieval-Augmented Generation) spécialisée dans l'aviculture, offrant des réponses expertes basées sur des données techniques et scientifiques.

### Stack technique
- **Frontend:** Next.js 14 (TypeScript, React, Tailwind CSS)
- **Backend:** FastAPI (Python)
- **LLM:** Module Python avec génération de réponses enrichies
- **Base de données:** PostgreSQL + Supabase (auth uniquement)
- **Déploiement:** Digital Ocean, Cloudflare WAF

---

## 📁 Emplacement des fichiers d'instructions

**RÈGLE IMPORTANTE:** Tous les fichiers d'instructions, de documentation et de planification doivent être placés dans :

```
C:\intelia_gpt\intelia-expert\docs\
```

### Structure de documentation

```
docs/
├── README.md                          # Index principal de la documentation
│
├── guidelines/                       # Directives et conventions
│   └── CLAUDE_INSTRUCTIONS.md        # Ce fichier - Instructions pour Claude
│
├── planning/                         # Gestion de projet et TODOs
│   ├── TODOS_EN_SUSPENS.md          # Inventaire des tâches en attente
│   └── TODOS_DECISION_GUIDE.md      # Guide de décision pour prioriser
│
├── security/                         # Audits et rapports de sécurité
│   ├── SECURITY_FINAL_SUMMARY.md
│   ├── SQL_INJECTION_AUDIT_REPORT.md
│   └── MEDIUM_ISSUES_ANALYSIS.md
│
├── backend/                          # Documentation backend
│   ├── GDPR_COMPLIANCE_REPORT.md
│   └── QA_QUALITY_TOOL_README.md
│
├── deployment/                       # Guides de déploiement
│   ├── DEPLOYMENT_PRODUCTION_GUIDE.md
│   ├── DEPLOY_CHECKLIST.md
│   └── CRON_SETUP_INSTRUCTIONS.md
│
├── operations/                       # Documentation opérationnelle
│   ├── DIAGNOSTIC_STATISTIQUES_BETA.md
│   └── MULTILINGUAL_EMAIL_SETUP.md
│
├── migration/                        # Archives de migration
│   ├── MIGRATION_GUIDE.md
│   └── MIGRATION_COMPLETED.md
│
├── implementation/                   # Documentation d'implémentation
├── analysis/                         # Analyses techniques
├── configuration/                    # Guides de configuration
├── guides/                           # Guides développeur
├── reports/                          # Rapports d'implémentation
├── frontend/                         # Documentation frontend
└── archive/                          # Documentation obsolète
```

---

## 🏗️ Architecture du projet

### Frontend ↔ Backend

```
Frontend (Next.js)
    │
    ├─► Supabase Auth (direct)        ✅ Authentification uniquement
    │   - OAuth (LinkedIn, Facebook)
    │   - Login/Register
    │   - Token management
    │
    └─► Backend API (FastAPI)          ✅ Toute la logique métier
        │
        ├─► Supabase (indirect)
        │   - Conversations
        │   - Profils utilisateurs
        │   - Métadonnées
        │
        └─► LLM Module (Python)
            - Génération de réponses
            - RAG pipeline
            - PostgreSQL direct
```

### Points d'entrée importants

**Frontend:**
- `frontend/lib/stores/auth.ts` - Store d'authentification Zustand
- `frontend/app/chat/services/apiService.ts` - Service API principal
- `frontend/lib/api/client.ts` - Client API avec gestion des tokens

**Backend:**
- `backend/main.py` - Point d'entrée FastAPI
- `backend/routers/` - Routes API
- `backend/services/` - Logique métier

**LLM:**
- `llm/main.py` - Endpoint de génération
- `llm/retrieval/` - Système RAG
- `llm/generation/` - Générateurs de réponses

---

## 🔒 Sécurité et bonnes pratiques

### Sécurité implémentée

✅ **Audit de sécurité terminé (Score: 10/10)**
- Aucune vulnérabilité SQL injection (queries paramétrées)
- Migration pickle → msgpack (désérialisation sécurisée)
- XML parsing sécurisé (defusedxml)
- MD5 avec usedforsecurity=False
- Binding 0.0.0.0 validé pour Docker/Cloud

**Référence:** `docs/security/SECURITY_FINAL_SUMMARY.md`

### Sécurité à implémenter (futur)

⏳ **Non prioritaire actuellement:**
- Rotation automatique des secrets
- Alertes de sécurité automatisées
- Monitoring avancé

### Standards de code

**Python (Backend/LLM):**
- Utiliser des **parameterized queries** pour SQL (`$1, $2, ...`)
- Ne JAMAIS utiliser `pickle` - utiliser `msgpack`
- Type hints obligatoires
- Logging structuré avec contexte

**TypeScript (Frontend):**
- Types stricts (pas de `any` sauf justifié)
- Hooks React appropriés
- Gestion d'erreurs explicite
- Commentaires pour la logique complexe

---

## 📝 Conventions de documentation

### Création de nouveaux documents

1. **Choisir le bon répertoire** dans `docs/` :
   - `security/` → Audits et rapports de sécurité
   - `backend/` → Documentation backend
   - `deployment/` → Guides de déploiement
   - `operations/` → Documentation opérationnelle
   - `migration/` → Archives de migration
   - `implementation/` → Documentation d'implémentation
   - `analysis/` → Analyses techniques
   - `guides/` → Guides développeur
   - `reports/` → Rapports d'implémentation
   - `planning/` → Gestion de projet et TODOs
   - `guidelines/` → Directives et conventions
   - `frontend/` → Documentation frontend

2. **Nommage des fichiers:**
   - `*_REPORT.md` → Rapports
   - `*_ANALYSIS.md` → Analyses
   - `*_GUIDE.md` → Guides
   - `README_*.md` → Documentation de module

3. **Structure d'un document:**
   ```markdown
   # Titre principal

   **Date:** YYYY-MM-DD
   **Auteur:** [Nom/Système]
   **Statut:** [Draft/Review/Final]

   ## Résumé
   [2-3 phrases]

   ## Table des matières
   [Si > 500 lignes]

   ## Contenu principal
   [Sections logiques]

   ## Références
   [Liens vers autres docs]
   ```

4. **Mettre à jour `docs/README.md`** avec le nouveau document

---

## 🔄 Workflow de développement

### Avant toute modification

1. **Lire la documentation pertinente** dans `docs/`
2. **Vérifier l'architecture** (ce fichier)
3. **Comprendre le contexte** (git log, fichiers connexes)

### Pendant le développement

1. **Utiliser TodoWrite** pour les tâches complexes
2. **Créer des commits atomiques** avec messages descriptifs
3. **Documenter les décisions** dans `docs/` si nécessaire
4. **Tester localement** avant de commit

### Format des commits

```
type: Description courte (50 chars max)

- Détails de l'implémentation
- Contexte/motivation
- Tests effectués

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:** `feat`, `fix`, `refactor`, `docs`, `security`, `perf`, `test`

---

## 🚫 Ce qu'il NE faut PAS faire

### Code

❌ **Ne jamais:**
- Écrire du code malveillant ou de hacking offensif
- Exposer des secrets/credentials dans le code
- Utiliser `pickle` pour la sérialisation
- Construire des queries SQL par concaténation
- Commiter directement sur `main` sans tests
- Modifier le code en production sans backup

### Documentation

❌ **Ne jamais:**
- Créer des fichiers .md en dehors de `docs/`
- Laisser des TODOs non documentés
- Supprimer de la documentation sans archiver
- Créer des doublons de documentation

### Git

❌ **Ne jamais:**
- Force push sur `main`
- Commit des fichiers sensibles (.env, credentials)
- Créer des commits sans message descriptif
- Skip les hooks (--no-verify) sans raison valable

---

## 🎯 Directives spéciales

### RGPD et confidentialité

Le projet est **conforme RGPD** :
- Consentement utilisateur trackgé
- Export de données implémenté (`/users/export-data`)
- Suppression de compte implémenté (`/users/delete-account`)
- Anonymisation des partages possible

**Référence:** `docs/backend/GDPR_COMPLIANCE_REPORT.md`

### Données sensibles

**Toujours anonymiser dans les logs/partages:**
- Noms d'entreprises
- Numéros de téléphone
- Emails
- Données de fermes/exploitations

### Performance

**Considérations:**
- Les queries RAG peuvent être lentes (2-5s)
- Utiliser le streaming SSE pour l'UX
- Cache Redis pour les queries fréquentes
- Pagination pour les listes (100 items max)

---

## 🔗 Références importantes

### Documentation clé

1. **Sécurité:** `docs/security/SECURITY_FINAL_SUMMARY.md`
2. **Architecture:** `docs/guides/COMPLETE_SYSTEM_DOCUMENTATION.md`
3. **Déploiement:** `docs/deployment/DEPLOYMENT_PRODUCTION_GUIDE.md`
4. **RGPD:** `docs/backend/GDPR_COMPLIANCE_REPORT.md`
5. **Base de données:** `docs/guides/DATABASE_SCHEMA.md`

### Endpoints API principaux

**Backend API (https://expert.intelia.com/api/v1):**
- `/auth/login` - Authentification
- `/auth/me` - Session utilisateur
- `/conversations/save` - Sauvegarder conversation
- `/conversations/user/{userId}` - Historique
- `/users/profile` - Profil utilisateur

**LLM (proxy via Next.js /llm):**
- `/llm/chat` - Génération de réponses (SSE streaming)
- `/llm/health/complete` - Health check

---

## 📞 Support et ressources

### En cas de doute

1. **Consulter** `docs/README.md` pour l'index complet
2. **Lire** la documentation du module concerné
3. **Vérifier** les commits récents (`git log --oneline -20`)
4. **Demander** confirmation à l'utilisateur si incertain

### Logs et debugging

**Frontend:** Browser DevTools Console
**Backend:** Logs CloudWatch Digital Ocean
**LLM:** Logs Python structurés

---

## 📊 Métriques et monitoring

**Actuellement implémenté:**
- Session tracking avec heartbeat (30s)
- Stats dashboard (`/api/v1/stats-fast/dashboard`)
- Health checks multiples
- QA quality analysis (cron job)

**Référence:** `docs/operations/DIAGNOSTIC_STATISTIQUES_BETA.md`

---

## 🔄 Mise à jour de ce document

Ce fichier doit être mis à jour lorsque :
- L'architecture change significativement
- De nouvelles conventions sont adoptées
- Des directives importantes sont ajoutées
- La structure de documentation évolue

**Dernière révision:** 2025-10-28

---

**Note:** Ce document est la source de vérité pour les interactions Claude Code sur ce projet. En cas de conflit avec d'autres documents, ce fichier prévaut pour les aspects procéduraux et organisationnels.
