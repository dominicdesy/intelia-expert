# TODOs en suspens - Intelia Expert

**Date**: 2025-10-28
**Status**: Inventaire après cleanup

---

## Vue d'ensemble

Après le nettoyage complet du projet, voici les TODOs identifiés dans la documentation qui nécessitent une action.

**Total**: 13 TODOs répartis dans 9 fichiers

---

## 🔴 TODOs critiques (Action requise)

### 1. Corporate Multi-tenant (PRIORITÉ HAUTE)
**Fichier**: `docs/guides/enterprise/CORPORATE_MULTITENANT_IMPLEMENTATION_PLAN.md:173`

```sql
-- TODO: Setup partitioning strategy
```

**Action requise**:
- Définir stratégie de partitioning pour tables multi-tenant
- Choisir entre partition par organization_id vs schemas séparés
- Implémenter la stratégie choisie

**Impact**: Bloque l'implémentation corporate multi-tenant

---

### 2. Billing Currency - Intégration Frontend (PRIORITÉ HAUTE)
**Fichier**: `docs/guides/billing/BILLING_CURRENCY_SETUP.md`

**TODOs**:
- Ligne 257: `## Frontend Integration (TODO)`
- Ligne 300: `## Stripe Integration (TODO)`

**Action requise**:
- Implémenter sélecteur de devise dans UI
- Intégrer API Stripe pour création de subscriptions multi-devises
- Tester flow complet de payment

**Impact**: Feature billing multi-devises incomplète

---

### 3. Subscription Tiers - Limite images (PRIORITÉ MOYENNE)
**Fichier**: `docs/analysis/SUBSCRIPTION_TIERS_ANALYSIS.md:1422`

```python
# TODO: Implémenter vérification du nombre d'images uploadées ce mois
```

**Action requise**:
- Ajouter compteur d'images par mois dans user_billing_info
- Implémenter vérification avant upload
- Ajouter message d'erreur si limite atteinte

**Impact**: Quota images non enforced, risque abus

---

## 🟡 TODOs importants (Planifier)

### 4. Voice Realtime - Tests WebSocket (PRIORITÉ MOYENNE)
**Fichier**: `docs/reports/VOICE_REALTIME_PHASE1_COMPLETE.md:54`

```
⏳ TODO: Tests WebSocket complets (nécessitent mocks)
```

**Action requise**:
- Créer mocks pour OpenAI Realtime API
- Écrire tests unitaires WebSocket
- Tester gestion erreurs et reconnexion

**Impact**: Coverage tests incomplet pour feature Voice

---

### 5. Voice Realtime - Production Redis (PRIORITÉ MOYENNE)
**Fichier**: `docs/reports/VOICE_REALTIME_PHASE1_COMPLETE.md:96`

```
TODO Production : Migrer vers Redis (actuellement in-memory)
```

**Action requise**:
- Configurer Redis pour session storage
- Migrer code de in-memory vers Redis
- Tester persistence sessions

**Impact**: Sessions perdues au redémarrage en production

---

### 6. Voice Realtime - Monitoring Production (PRIORITÉ MOYENNE)
**Fichiers**:
- `docs/reports/VOICE_REALTIME_PHASE1_COMPLETE.md:137`
- `docs/deployment/VOICE_REALTIME_DEPLOYMENT.md:175,201`

**TODOs**:
```
- TODO : Intégration Sentry/Datadog
- TODO: Ajouter JWT token dans headers
- TODO: Adapter scripts pour tester contre https://expert.intelia.com
```

**Action requise**:
- Intégrer Sentry pour error tracking
- Ajouter métriques Datadog (latence, erreurs)
- Sécuriser endpoints avec JWT
- Créer scripts de test production

**Impact**: Pas de monitoring temps réel de la feature Voice

---

### 7. QA Analysis - Session de travail planifiée
**Fichier**: `docs/backend/QA_ANALYSIS_REPORT.md:296`

```
# TODO pour la prochaine session:
```

**Action requise**:
- Réviser le rapport QA_ANALYSIS_REPORT
- Compléter les analyses en suspens
- Implémenter les recommandations

**Impact**: Analyses QA incomplètes

---

### 8. GDPR Compliance - Améliorations optionnelles
**Fichier**: `docs/security/GDPR_COMPLIANCE_AUDIT.md:72`

```
**TODO Optionnel** (amélioration future):
```

**Action requise**:
- Réviser les améliorations GDPR proposées
- Prioriser selon risque/impact
- Planifier implémentation

**Impact**: Faible - améliorations optionnelles

---

## 🟢 TODOs documentation (Faible priorité)

### 9. Voice Realtime - Code commenté
**Fichier**: `docs/reports/VOICE_REALTIME_PHASE1_COMPLETE.md:115`

```python
# TODO: Décommenter quand ready
```

**Action requise**:
- Réviser code commenté
- Décommenter si prêt pour production
- Documenter raison si pas prêt

**Impact**: Code potentiellement incomplet

---

### 10. Quality Audit - Validation sémantique avancée
**Fichier**: `docs/guides/QUALITY_AUDIT_CURRENT_SYSTEM.md:303`

```python
# TODO: Advanced semantic validation
```

**Action requise**:
- Définir critères validation sémantique
- Implémenter algorithmes validation
- Tester sur dataset

**Impact**: Amélioration qualité (nice-to-have)

---

### 11. Claude Instructions - Rappel bonnes pratiques
**Fichier**: `docs/CLAUDE_INSTRUCTIONS.md:242`

```
- Laisser des TODOs non documentés
```

**Action**: Documentation seulement, pas d'action technique requise

---

## 📊 Statistiques TODOs

### Par priorité
- 🔴 **Critique**: 3 TODOs
- 🟡 **Important**: 5 TODOs
- 🟢 **Documentation**: 3 TODOs
- 📋 **Checklists**: 2 TODOs (dans poc_realtime/)

### Par catégorie
- **Enterprise/Multi-tenant**: 1 TODO
- **Billing/Subscriptions**: 3 TODOs
- **Voice Realtime**: 5 TODOs
- **Security/GDPR**: 1 TODO
- **Quality/Testing**: 2 TODOs
- **Documentation**: 1 TODO

### Par fichier
```
docs/reports/VOICE_REALTIME_PHASE1_COMPLETE.md          3 TODOs
docs/guides/billing/BILLING_CURRENCY_SETUP.md           2 TODOs
docs/deployment/VOICE_REALTIME_DEPLOYMENT.md            2 TODOs
docs/guides/enterprise/CORPORATE_MULTITENANT_...        1 TODO
docs/analysis/SUBSCRIPTION_TIERS_ANALYSIS.md            1 TODO
docs/backend/QA_ANALYSIS_REPORT.md                      1 TODO
docs/security/GDPR_COMPLIANCE_AUDIT.md                  1 TODO
docs/CLAUDE_INSTRUCTIONS.md                             1 TODO
docs/guides/QUALITY_AUDIT_CURRENT_SYSTEM.md             1 TODO
```

---

## 🎯 Plan d'action recommandé

### Sprint 1 (Semaine prochaine)
1. ✅ **Subscription Tiers - Limite images** (1 jour)
2. ✅ **Voice Realtime - JWT Auth** (0.5 jour)
3. ✅ **Voice Realtime - Scripts test production** (0.5 jour)

### Sprint 2 (Dans 2 semaines)
4. ✅ **Billing Currency - Frontend Integration** (2 jours)
5. ✅ **Voice Realtime - Redis migration** (1 jour)
6. ✅ **Voice Realtime - Monitoring Sentry/Datadog** (1 jour)

### Sprint 3 (Dans 1 mois)
7. ✅ **Corporate Multi-tenant - Partitioning strategy** (3 jours)
8. ✅ **Voice Realtime - Tests WebSocket** (1 jour)
9. ✅ **QA Analysis - Compléter rapport** (1 jour)

### Backlog (À prioriser plus tard)
- GDPR améliorations optionnelles
- Quality audit - validation sémantique avancée
- Code review Voice Realtime commenté

---

## 📝 Notes

### Fichiers POC (poc_realtime/)
Les fichiers dans `poc_realtime/` contiennent de nombreuses checklists ([ ]) qui sont normales pour un POC. Ce ne sont pas des TODOs techniques mais des validations de POC.

### CLEANUP_PLAN*.md
Les TODOs dans CLEANUP_PLAN.md et CLEANUP_PLAN_COMPLET.md sont des checklists du cleanup (maintenant terminé), pas des TODOs projet.

### SETUP_GUIDE.md
Les checklists dans SETUP_GUIDE.md sont des instructions de setup pour nouveaux utilisateurs, pas des TODOs techniques.

---

## ✅ Validation

- ✅ Tous les TODOs critiques identifiés
- ✅ TODOs priorisés par impact
- ✅ Plan d'action créé
- ✅ POC checklists distinguées des TODOs techniques

---

**Prochaine étape**: Créer des tickets GitHub/Jira pour les TODOs critiques (1-3) et planifier Sprint 1.
