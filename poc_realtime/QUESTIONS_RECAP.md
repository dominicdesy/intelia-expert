# 📋 Récapitulatif des Questions Critiques

Liste complète des 10 questions à résoudre avant développement.

---

## ✅ Phase 0 : Validation Économique

### Q1. Le budget peut-il supporter les coûts OpenAI Realtime ?

**Status** : ✅ **RÉSOLU**

**Réponse** : OUI - Budget validé, fonction sera proposée avec forfait premium.

**Impact** :
- Coût estimé : ~$600/mois pour 1000 conversations
- 3x plus cher que l'approche hybride actuelle ($200/mois)
- Acceptable car monétisé via forfait premium

**Documents** : Aucun (décision business)

**Date validation** : [Aujourd'hui]

---

## 🧪 Phase 1 : Validation Technique (POC)

### Q2. OpenAI Realtime API fonctionne-t-il avec nos contraintes ?

**Status** : 🔨 **À TESTER**

**Script** : `test_openai_realtime.py`

**Questions spécifiques** :
- [ ] L'API accepte streaming audio PCM16 ?
- [ ] Quelle latence (question → premier chunk audio) ?
- [ ] VAD fonctionne en français ?
- [ ] Interruption possible via `response.cancel` ?

**Critères de succès** :
- Latence P95 <500ms
- VAD détecte fin de phrase en français
- Interruption fonctionnelle

**Comment exécuter** :
```bash
export OPENAI_API_KEY="sk-..."
python test_openai_realtime.py
```

**Documents** : `README.md` section Q2

**Temps estimé** : 30 minutes

---

### Q3. Quelle est la latence réelle de Weaviate ?

**Status** : 🔨 **À TESTER**

**Script** : `test_weaviate_latency.py`

**Questions spécifiques** :
- [ ] Latence P50, P95, P99 ?
- [ ] Impact queries concurrentes ?
- [ ] Compatibilité avec streaming OpenAI ?

**Critères de succès** :
- P50 <200ms
- P95 <300ms
- Pas de blocage streaming

**Comment exécuter** :
```bash
python test_weaviate_latency.py
```

**Impact sur décision** :
- Si P95 <300ms → Option A ou B viables
- Si P95 300-500ms → Option B obligatoire
- Si P95 >500ms → Cache ou optimisation nécessaire

**Documents** : `README.md` section Q3

**Temps estimé** : 20 minutes

---

### Q4. Architecture WebSocket fonctionne-t-elle ?

**Status** : 🔨 **À TESTER**

**Scripts** :
- Backend : `backend_websocket_minimal.py`
- Client : `test_websocket_audio.py`

**Questions spécifiques** :
- [ ] Format audio (Base64 vs Binaire) ?
- [ ] Latence RTT acceptable ?
- [ ] Streaming bidirectionnel sans coupures ?

**Critères de succès** :
- Connexion <150ms
- RTT <50ms
- Pas de coupures audio

**Comment exécuter** :
```bash
# Terminal 1
python backend_websocket_minimal.py

# Terminal 2
python test_websocket_audio.py
```

**Documents** : `README.md` section Q4

**Temps estimé** : 30 minutes

---

## 🎨 Phase 2 : Design Technique

### Q5. Comment injecter le contexte RAG ?

**Status** : 📝 **DÉCISION REQUISE** (après Q3)

**Options** :
- **Option A** : Injection après VAD (simple, +780ms)
- **Option B** : Pré-chargement pendant parole (optimal, ~500ms)
- **Hybride** : Option B avec fallback A

**Critères de choix** :
- Si latence Weaviate P95 <200ms → Option A acceptable
- Si latence Weaviate P95 200-300ms → Option B recommandée
- Si latence Weaviate P95 >300ms → Option B obligatoire + cache

**Comment décider** :
1. Exécuter Q3 (test latence Weaviate)
2. Consulter `DECISIONS_TECHNIQUES.md` section Q5
3. Choisir option basée sur résultats

**Documents** : `DECISIONS_TECHNIQUES.md` - Q5

**Temps estimé** : 15 minutes (lecture + décision)

---

### Q6. Comment gérer l'interruption utilisateur ?

**Status** : 📝 **DÉCISION REQUISE**

**Sous-questions** :
- [ ] Détection : VAD client ou serveur ?
- [ ] Action : `response.cancel` ou fade out ?
- [ ] Contexte : Conserver ou réinitialiser ?
- [ ] Audio queue : Clear immédiat ou drain ?

**Recommandation** :
- Détection : VAD client + serveur (double sécurité)
- Action : `response.cancel` immédiat
- Contexte : Conserver (conversation naturelle)
- Queue : Clear immédiat

**Comment décider** :
1. Lire `DECISIONS_TECHNIQUES.md` section Q6
2. Valider stratégie recommandée ou ajuster
3. Noter décision dans `VALIDATION_CHECKLIST.md`

**Documents** : `DECISIONS_TECHNIQUES.md` - Q6

**Temps estimé** : 10 minutes

---

### Q7. Quel format audio utiliser ?

**Status** : 📝 **DÉCISION REQUISE** (après Q4)

**Options** :
- **PCM16 Base64 JSON** : Simple, overhead +33%
- **WebSocket Binaire** : Optimisé, complexe
- **Opus codec** : Compression 10x, compatibilité variable

**Sous-questions** :
- [ ] Format : PCM16, Opus, AAC ?
- [ ] Sample rate : 16kHz, 44.1kHz, 48kHz ?
- [ ] Encoding : Base64 ou binaire ?
- [ ] iOS Safari compatible ?

**Recommandation MVP** :
- Format : PCM16
- Encoding : Base64 JSON
- Sample rate : 16kHz
- Channels : Mono

**Comment décider** :
1. Exécuter Q4 (test WebSocket)
2. Vérifier overhead Base64 acceptable (<50%)
3. Si overhead >50% → Considérer binaire
4. Consulter `DECISIONS_TECHNIQUES.md` section Q7

**Documents** : `DECISIONS_TECHNIQUES.md` - Q7

**Temps estimé** : 10 minutes

---

## 🔐 Phase 3 : Sécurité & Production

### Q8. Quelle stratégie de sécurité WebSocket ?

**Status** : ⏳ **PHASE 1 DEV**

**Décisions requises** :
- [ ] Authentification : JWT dans header ou message ?
- [ ] Rate limiting : 5 sessions/heure suffisant ?
- [ ] Durée max session : 10 min approprié ?
- [ ] Reconnexion : Combien de retry ?
- [ ] CORS : Quels origins autorisés ?

**Recommandation** :
```python
# Authentification
headers = {"Authorization": f"Bearer {jwt_token}"}

# Rate limiting
MAX_SESSIONS_PER_HOUR = 5
MAX_SESSION_DURATION = 600  # 10 min

# Reconnexion
MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # Exponential backoff
```

**Timing** : À implémenter Phase 1 backend (pas bloquant pour POC)

**Documents** : `REAL_TIME_VOICE_PLAN.md` section Sécurité

---

### Q9. Quelles métriques tracker ?

**Status** : ⏳ **PHASE 5 DEV**

**Métriques système** :
- [ ] Connexions WebSocket actives
- [ ] Latence P50/P95/P99
- [ ] Taux d'erreur par type
- [ ] Coût réel par conversation
- [ ] Durée moyenne session

**Métriques business** :
- [ ] Taux d'adoption (% users)
- [ ] Taux d'abandon (<30s)
- [ ] Satisfaction post-conversation
- [ ] Ratio questions RAG vs externes

**Recommandation outil** :
- Sentry : Erreurs
- Datadog : Latence & infra
- Custom dashboard : Business metrics

**Timing** : À implémenter Phase 5 production

**Documents** : `REAL_TIME_VOICE_PLAN.md` section Métriques

---

### Q10. Quelle stratégie de rollout ?

**Status** : ⏳ **POST-DEV**

**Options** :
- **A** : Lancer pour tous immédiatement
- **B** : Beta progressive (10% → 50% → 100%)
- **C** : Opt-in explicite (toggle settings)

**Recommandation** : **Option B (Beta progressive)**

**Plan** :
1. Semaine 1 : 10% users premium (beta testers)
2. Semaine 2 : 50% users premium (si métriques OK)
3. Semaine 3 : 100% users premium
4. Mois 2 : Tous users (si ROI positif)

**Critères GO next phase** :
- Latence P95 <800ms
- Taux d'erreur <2%
- Satisfaction >4/5
- Coût/conversation <$0.70

**Timing** : À décider juste avant déploiement

**Documents** : `REAL_TIME_VOICE_PLAN.md` section Production

---

## 📊 Tableau Synthétique

| # | Question | Phase | Status | Temps | Bloquant |
|---|----------|-------|--------|-------|----------|
| Q1 | Budget OK ? | 0 | ✅ Résolu | - | Oui |
| Q2 | OpenAI Realtime ? | POC | 🔨 À tester | 30m | Oui |
| Q3 | Latence Weaviate ? | POC | 🔨 À tester | 20m | Oui |
| Q4 | WebSocket audio ? | POC | 🔨 À tester | 30m | Moyen |
| Q5 | Injection RAG ? | Design | 📝 Après Q3 | 15m | Oui |
| Q6 | Interruption ? | Design | 📝 À décider | 10m | Moyen |
| Q7 | Format audio ? | Design | 📝 Après Q4 | 10m | Faible |
| Q8 | Sécurité ? | Dev | ⏳ Phase 1 | - | Faible |
| Q9 | Monitoring ? | Dev | ⏳ Phase 5 | - | Faible |
| Q10 | Rollout ? | Prod | ⏳ Post-dev | - | Faible |

**Légende Status** :
- ✅ Résolu
- 🔨 À tester (POC requis)
- 📝 À décider (lecture doc)
- ⏳ Plus tard (pendant dev)

**Légende Bloquant** :
- **Oui** : Doit être résolu avant démarrage dev
- **Moyen** : Important mais ajustable pendant dev
- **Faible** : Peut être résolu pendant/après dev

---

## 🎯 Chemin Critique

Pour démarrer développement, vous DEVEZ résoudre :

```
Q1 (Budget) ✅
    ↓
Q2 (OpenAI) 🔨 ← CRITIQUE
    ↓
Q3 (Weaviate) 🔨 ← CRITIQUE
    ↓
Q5 (RAG injection) 📝 ← Dépend de Q3
    ↓
Q4 (WebSocket) 🔨 ← Moins critique
    ↓
Q6-Q7 (Design) 📝 ← Nice to have
    ↓
✅ GO pour développement
```

**Temps minimum** : Q1 (✅) + Q2 (30m) + Q3 (20m) + Q5 (15m) = **65 minutes**

**Temps recommandé** : Q1-Q7 complet = **2h05 tests + 35m décisions = 2h40**

---

## ✅ Prochaines Actions

### Action Immédiate (Aujourd'hui)

1. ✅ Lire `START_HERE.md` (vous y êtes !)
2. 🔨 Exécuter Q2 : `python test_openai_realtime.py`
3. 🔨 Exécuter Q3 : `python test_weaviate_latency.py`
4. 📝 Décider Q5 basé sur résultats Q3

### Action J+1 (Demain)

5. 🔨 Exécuter Q4 : Tests WebSocket
6. 📝 Décider Q6 et Q7
7. ✅ Remplir `VALIDATION_CHECKLIST.md`
8. 🎯 Réunion GO/NO-GO (30 min)

### Si GO (J+2)

9. 🚀 Démarrer Phase 1 backend
10. ⏳ Résoudre Q8-Q10 pendant dev

---

## 📞 Support

**Problème avec questions** :
- Q2-Q4 : Consulter `README.md` Troubleshooting
- Q5-Q7 : Relire `DECISIONS_TECHNIQUES.md`
- GO/NO-GO : Utiliser `VALIDATION_CHECKLIST.md`

**Doute architecture** :
- Relire `REAL_TIME_VOICE_PLAN.md`
- Consulter docs OpenAI Realtime API

---

**🎯 PROCHAINE ACTION : Commencer Q2 !**

```bash
export OPENAI_API_KEY="sk-..."
python test_openai_realtime.py
```

Bonne chance ! 🚀
