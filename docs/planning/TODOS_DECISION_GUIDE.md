# Guide de Décision - TODOs Intelia Expert

**Date**: 2025-10-28
**But**: Vous aider à décider quelles tâches implémenter

---

## 🔴 CRITIQUES - Recommandation: **FAIRE**

### 1. ✅ Subscription Tiers - Limite images
**Statut**: NÉCESSAIRE
**Effort**: 1 jour
**Impact**: ÉLEVÉ

**Problème actuel**:
- Les utilisateurs Pro peuvent uploader infiniment d'images
- Quota de 50 images/mois pas enforced
- Risque d'abus et de coûts S3 explosifs

**Ce que ça fait**:
- Ajoute compteur d'images uploadées par mois dans DB
- Bloque upload si quota dépassé (Pro = 50/mois)
- Affiche quota restant dans l'UI
- Message d'upgrade vers Elite (images illimitées)

**Pourquoi c'est important**:
- **Coût**: Protège contre abus (S3 storage coûteux)
- **Business**: Incite upgrade vers Elite
- **UX**: Utilisateur voit combien il lui reste

**Recommandation**: ✅ **FAIRE - Priorité #1**

---

### 2. ✅ Billing Currency - Intégration frontend
**Statut**: NÉCESSAIRE
**Effort**: 2 jours
**Impact**: ÉLEVÉ

**Problème actuel**:
- Backend supporte 16 devises
- Mais pas d'interface frontend pour sélectionner
- Utilisateurs bloqués s'ils essaient d'upgrade sans devise

**Ce que ça fait**:
- Page `/billing/currency` pour choisir devise
- Suggestions intelligentes (EUR pour France, USD pour USA, etc.)
- Modal d'avertissement si pas de devise avant upgrade
- Intégration Stripe avec multi-currency

**Pourquoi c'est important**:
- **Business**: Débloque ventes internationales
- **UX**: Évite confusion devise (ex: Indien facturé en USD)
- **Légal**: Transparence des prix

**Recommandation**: ✅ **FAIRE - Priorité #2**

---

## 🟡 IMPORTANTS - Recommandation: **ÉVALUER**

### 3. ⚠️ Voice Realtime - Migration Redis
**Statut**: IMPORTANT pour production
**Effort**: 1 jour
**Impact**: MOYEN

**Problème actuel**:
- Sessions Voice stockées in-memory
- Pertes de sessions si backend redémarre
- Pas de load balancing possible

**Ce que ça fait**:
- Migre sessions vers Redis
- Persistence des sessions
- Permet scaling horizontal

**Pourquoi c'est optionnel pour maintenant**:
- ✅ Si backend stable (pas de restarts fréquents) → Pas urgent
- ❌ Si users se plaignent de déconnexions → Urgent

**Questions pour décider**:
1. Avez-vous des plaintes de déconnexions Voice?
2. Redémarrez-vous souvent le backend?
3. Prévoyez-vous du load balancing bientôt?

**Recommandation**: ⏸️ **PEUT ATTENDRE** si pas de problèmes actuels

---

### 4. ⚠️ Voice Realtime - Monitoring Sentry/Datadog
**Statut**: IMPORTANT pour production
**Effort**: 1.5 jours
**Impact**: MOYEN

**Problème actuel**:
- Pas d'error tracking Voice
- Pas de métriques temps réel
- Debug difficile en production

**Ce que ça fait**:
- Intègre Sentry pour erreurs
- Ajoute métriques Datadog (latence, erreurs)
- Dashboard monitoring Voice

**Pourquoi c'est optionnel pour maintenant**:
- ✅ Si Voice fonctionne bien → Pas urgent
- ❌ Si bugs fréquents → Urgent

**Questions pour décider**:
1. Voice est-il stable en production?
2. Avez-vous déjà Sentry/Datadog configurés?
3. Combien d'utilisateurs utilisent Voice?

**Recommandation**: ⏸️ **PEUT ATTENDRE** sauf si bugs fréquents

---

### 5. 🚨 Voice Realtime - Sécurisation JWT
**Statut**: CRITIQUE pour production
**Effort**: 0.5 jour
**Impact**: TRÈS ÉLEVÉ (Sécurité)

**Problème actuel**:
- Endpoint Voice WebSocket **PAS AUTHENTIFIÉ**
- `user_id = 1` hardcodé
- **Risque sécurité majeur**

**Ce que ça fait**:
- Décommente l'auth JWT déjà écrite
- Vérifie token avant WebSocket
- Empêche accès non-autorisé

**Pourquoi c'est critique**:
- 🔴 **FAILLE SÉCURITÉ**: N'importe qui peut se connecter
- 🔴 **ABUS POSSIBLE**: Appels OpenAI gratuits pour tous
- 🔴 **COÛT**: Risque de facture OpenAI explosive

**Questions pour décider**:
1. Voice est-il exposé publiquement? → Si OUI, **URGENT**
2. Est-il derrière un VPN/whitelist? → Si NON, **URGENT**

**Recommandation**: 🚨 **FAIRE IMMÉDIATEMENT** (30 min)

---

### 6. 📊 QA Analysis - Compléter session
**Statut**: OPTIONNEL (Nice-to-have)
**Effort**: 1 jour
**Impact**: FAIBLE

**Problème actuel**:
- Rapport QA incomplet
- Pas de feedback utilisateur capturé

**Ce que ça fait**:
- Ajoute boutons 👍 👎 dans le chat
- Enregistre feedback en DB
- Améliore qualité réponses au fil du temps

**Pourquoi c'est optionnel**:
- ✅ Système fonctionne sans feedback
- ✅ Amélioration incrémentale
- ⏳ Peut attendre Sprint 2-3

**Questions pour décider**:
1. Voulez-vous améliorer la qualité des réponses?
2. Avez-vous du temps disponible?

**Recommandation**: ⏸️ **BACKLOG** (pas urgent)

---

## 🟢 DOCUMENTATION - Recommandation: **OPTIONNELS**

### 7. 📝 GDPR - Améliorations optionnelles
**Statut**: OPTIONNEL (Déjà conforme)
**Effort**: 1 jour
**Impact**: TRÈS FAIBLE

**Problème actuel**:
- **AUCUN** - Vous êtes déjà conforme GDPR ✅

**Ce que propose le TODO**:
```
TODO Optionnel (amélioration future):
- Sauvegarder consent_timestamp, consent_version, consent_ip_address
- Permettrait de prouver le consentement en cas d'audit
```

**Analyse**:
- ✅ Vous avez déjà checkbox consentement GDPR
- ✅ Vous avez déjà suppression compte
- ✅ Vous avez déjà politique confidentialité

**Améliorations optionnelles**:
1. Sauvegarder horodatage consentement
2. Sauvegarder version politique acceptée
3. Sauvegarder IP lors consentement

**Pourquoi c'est VRAIMENT optionnel**:
- 🟢 Pas obligatoire GDPR (checkbox suffit)
- 🟢 Utile seulement si audit approfondi
- 🟢 La plupart des startups ne le font pas

**Questions pour décider**:
1. Êtes-vous dans un secteur régulé (santé, finance)? → Si OUI, utile
2. Avez-vous des clients corporate exigeants? → Si OUI, utile
3. Sinon? → **PAS NÉCESSAIRE**

**Recommandation**: ⏸️ **PAS NÉCESSAIRE** pour maintenant

---

### 8. 🔍 Quality Audit - Validation sémantique avancée
**Statut**: OPTIONNEL (Amélioration)
**Effort**: 1 jour
**Impact**: FAIBLE

**Problème actuel**:
- **AUCUN** - Score qualité actuel = 0.87/1.0 (BON) ✅

**Ce que propose le TODO**:
```python
# Currently basic check
# TODO: Advanced semantic validation
```

**Analyse**:
- ✅ Vous avez déjà 6 checks qualité
- ✅ Score moyen = 87% (très bon)
- ⏳ Validation sémantique = amélioration marginale

**Améliorations proposées**:
1. Vérifier cohérence sémantique réponse/question
2. Détecter contradictions internes
3. Valider citations/références

**Pourquoi c'est optionnel**:
- 🟢 Système actuel fonctionne bien (87%)
- 🟢 Amélioration = +2-3% max
- 🟢 Complexité élevée pour gain marginal

**Questions pour décider**:
1. Avez-vous des plaintes qualité? → Si NON, **pas urgent**
2. Score 87% vous satisfait? → Si OUI, **pas nécessaire**

**Recommandation**: ⏸️ **PAS PRIORITAIRE**

---

### 9. 📝 Voice Realtime - Code review
**Statut**: TECHNIQUE (Déjà fait?)
**Effort**: 1 jour
**Impact**: FAIBLE

**Problème actuel**:
- Code commenté à ligne 115 du rapport

**Ce que ça dit**:
```python
# TODO: Décommenter quand ready
# user = Depends(get_current_user_from_websocket)
```

**Analyse**:
- ⚠️ C'est le même TODO que #5 (JWT Auth)
- Si vous faites #5, celui-ci est automatiquement fait

**Recommandation**: ✅ **INCLUS DANS #5** (pas de travail séparé)

---

## 📊 RÉSUMÉ & RECOMMANDATIONS FINALES

### ✅ À FAIRE MAINTENANT (Critiques)

| # | Tâche | Effort | Priorité | Raison |
|---|-------|--------|----------|--------|
| 2 | **Billing Currency Frontend** | 2j | 🔴 P1 | Débloque ventes internationales |
| 1 | **Limite Images Quota** | 1j | 🔴 P2 | Protège coûts S3 + business |
| 5 | **Voice JWT Auth** | 0.5j | 🚨 P0 | **FAILLE SÉCURITÉ** |

**TOTAL: 3.5 jours**

---

### ⏸️ PEUT ATTENDRE (Importants mais pas urgents)

| # | Tâche | Effort | Quand? |
|---|-------|--------|--------|
| 3 | Voice Redis | 1j | Si problèmes déconnexions |
| 4 | Voice Monitoring | 1.5j | Si bugs fréquents Voice |
| 6 | QA Feedback | 1j | Sprint 2-3 (amélioration) |

---

### ❌ PAS NÉCESSAIRE (Optionnels)

| # | Tâche | Raison |
|---|-------|--------|
| 7 | GDPR Améliorations | Déjà conforme, pas obligatoire |
| 8 | Validation Sémantique | Score 87% déjà bon |
| 9 | Voice Code Review | Inclus dans #5 |

---

## 🎯 PLAN RECOMMANDÉ

### Sprint Immédiat (Cette semaine - 4 jours)
```bash
Jour 1-2: Billing Currency Frontend  (2j)
Jour 3:   Limite Images Quota        (1j)
Jour 4:   Voice JWT Auth             (0.5j)
          + Tests & Deploy            (0.5j)
```

### Sprint 2 (Si nécessaire - 2-4 semaines)
```bash
- Voice Redis (si problèmes)
- Voice Monitoring (si bugs)
- QA Feedback (si temps disponible)
```

### Backlog (Jamais?)
```bash
- GDPR Améliorations → Pas nécessaire
- Validation Sémantique → Pas nécessaire
```

---

## ❓ QUESTIONS POUR FINALISER LA DÉCISION

Répondez à ces questions pour que je vous donne une recommandation personnalisée:

### 1. Voice Realtime
- [ ] Voice est-il exposé publiquement? (OUI/NON)
- [ ] Avez-vous des déconnexions fréquentes? (OUI/NON)
- [ ] Avez-vous des bugs Voice en production? (OUI/NON)

### 2. Monitoring
- [ ] Avez-vous déjà Sentry configuré? (OUI/NON)
- [ ] Avez-vous déjà Datadog configuré? (OUI/NON)

### 3. Priorités Business
- [ ] Les ventes internationales sont-elles importantes? (OUI/NON)
- [ ] Combien d'uploads images par jour actuellement? (_____)
- [ ] Budget développement cette semaine? (_____ jours)

---

## 🎬 DÉCISION FINALE

**Attendez votre réponse pour:**
1. Confirmer les 3 tâches critiques (Billing, Images, JWT)
2. Décider Voice Redis & Monitoring
3. Ignorer les optionnelles (GDPR, Sémantique)

**Dites-moi simplement:**
- "OK pour les 3 critiques" → Je commence immédiatement
- "Besoin de Voice Redis aussi" → J'ajoute au plan
- "Seulement JWT + Images" → Je fais juste ceux-là

---

**Prêt à démarrer dès votre confirmation!** 🚀
