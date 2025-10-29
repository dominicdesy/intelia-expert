# POC - Validation Technique Voice Realtime

Scripts de test pour valider les hypothèses critiques avant développement complet.

## 📋 Vue d'Ensemble

Ces scripts répondent aux questions **Q2, Q3, Q4** du plan de validation :
- **Q2** : OpenAI Realtime API (latence, VAD français, interruption)
- **Q3** : Latence Weaviate pendant streaming
- **Q4** : Architecture WebSocket bidirectionnel

---

## 🚀 Installation

```bash
# Installer dépendances
cd poc_realtime
pip install -r requirements.txt
```

### Prérequis
- Python 3.11+
- OpenAI API Key (pour Q2)
- Weaviate accessible (pour Q3)
- Port 8000 disponible (pour Q4)

---

## 🧪 Exécution des Tests

### Q2 : Test OpenAI Realtime API

```bash
# Définir API key
export OPENAI_API_KEY="sk-..."

# Exécuter test
python test_openai_realtime.py
```

**Ce qui est testé** :
- ✅ Connexion WebSocket à OpenAI Realtime API
- ✅ Latence premier chunk audio (objectif <500ms)
- ✅ VAD (Voice Activity Detection) en français
- ✅ Capacité d'interruption (response.cancel)
- ✅ Format audio PCM16

**Métriques attendues** :
```
⏱️  LATENCE:
  - Connexion WebSocket: ~200-400ms
  - Premier chunk audio: ~300-600ms

🎯 ÉVALUATION:
  ✅ Latence EXCELLENTE (<500ms)
  ✅ Streaming audio fonctionnel
```

**Questions à répondre après test** :
1. La latence P95 est-elle <500ms ?
2. Le VAD détecte-t-il correctement les fins de phrase en français ?
3. L'interruption fonctionne-t-elle (`response.cancel`) ?

---

### Q3 : Test Latence Weaviate

```bash
# S'assurer que Weaviate est accessible
# Config dans llm/config/config.py

python test_weaviate_latency.py
```

**Ce qui est testé** :
- ✅ Latence query Weaviate (baseline)
- ✅ Queries concurrentes (charge réaliste)
- ✅ Statistiques P50/P95/P99
- ✅ Impact sur streaming concurrent

**Métriques attendues** :
```
📈 STATISTIQUES LATENCE:
  - P50:    ~150-250ms
  - P95:    ~250-400ms

🎯 ÉVALUATION:
  ✅ BON: P95=280ms - Acceptable pour voice realtime

💡 RECOMMANDATIONS:
  ✅ Option B recommandée: Pré-chargement pendant parole

⏱️  ESTIMATION LATENCE TOTALE:
  Option A (injection après VAD): ~780ms
  Option B (pré-chargement): ~500ms ✅
```

**Questions à répondre après test** :
1. La latence P95 Weaviate est-elle <300ms ?
2. L'Option A (injection après VAD) est-elle viable ou doit-on faire Option B ?
3. La latence totale estimée (VAD + Weaviate + OpenAI) respecte-t-elle l'objectif <500ms ?

---

### Q4 : Test WebSocket Audio Bidirectionnel

#### Étape 1 : Démarrer le backend POC

```bash
# Terminal 1
python backend_websocket_minimal.py

# Ou avec uvicorn
uvicorn backend_websocket_minimal:app --reload --port 8000
```

Vérifier : http://localhost:8000 doit retourner `{"status": "running"}`

#### Étape 2 : Exécuter le client de test

```bash
# Terminal 2
python test_websocket_audio.py
```

**Ce qui est testé** :
- ✅ Connexion WebSocket (latence)
- ✅ Streaming audio bidirectionnel (client → backend → client)
- ✅ Format audio (Base64 vs Binaire)
- ✅ Latence réseau (ping-pong RTT)
- ✅ Buffering audio sans coupures

**Métriques attendues** :
```
📡 CONNEXION:
  - Temps connexion: ~50-150ms
  - RTT moyen: ~10-50ms

📦 STREAMING:
  - Chunks envoyés: 30
  - Chunks reçus: 30

⚖️  COMPARAISON FORMATS:
  Base64 JSON: 2133 bytes (overhead +33%)
  Binaire: 1600 bytes
  💡 Recommandation: Base64 acceptable
```

**Questions à répondre après test** :
1. Le streaming bidirectionnel fonctionne-t-il sans coupures ?
2. La latence WebSocket est-elle acceptable (<100ms connexion, <50ms RTT) ?
3. Quel format utiliser (Base64 JSON vs Binaire) ?

---

## 📊 Résultats Attendus

Après exécution des 3 tests, vous devriez pouvoir répondre :

### ✅ Critères de Succès (GO pour développement)
- [ ] **Q2** : Latence OpenAI P95 < 500ms
- [ ] **Q2** : VAD français fonctionnel
- [ ] **Q2** : Interruption possible
- [ ] **Q3** : Latence Weaviate P95 < 300ms
- [ ] **Q3** : Latence totale estimée < 800ms avec Option B
- [ ] **Q4** : WebSocket bidirectionnel sans coupures
- [ ] **Q4** : RTT < 50ms

### ⚠️ Critères d'Alerte (Ajustements nécessaires)
- [ ] Latence OpenAI > 1s → Problème API ou réseau
- [ ] Latence Weaviate P95 > 500ms → Nécessite optimisation ou cache
- [ ] WebSocket RTT > 100ms → Problème réseau ou backend

### ❌ Critères Bloquants (Reconsidérer approche)
- [ ] OpenAI Realtime API non accessible
- [ ] VAD ne fonctionne pas en français
- [ ] Latence totale > 1.5s même avec Option B
- [ ] WebSocket instable (disconnections fréquentes)

---

## 🔍 Analyse des Résultats

### Si tous les tests passent (✅)

**Conclusion** : L'architecture proposée est viable.

**Prochaines étapes** :
1. Répondre à Q5 (stratégie injection RAG) → Option B recommandée
2. Répondre à Q6 (mécanisme interruption)
3. Répondre à Q7 (format audio mobile)
4. Démarrer Phase 1 du développement (backend)

### Si latence Weaviate trop élevée (⚠️)

**Options** :
1. Implémenter cache pour questions fréquentes
2. Optimiser index Weaviate (sharding, tuning)
3. Pré-charger contexte pendant parole (Option B obligatoire)
4. Fallback : Si query Weaviate >500ms, utiliser LLM sans contexte

### Si OpenAI Realtime problématique (❌)

**Options** :
1. Vérifier quota API et limites
2. Tester avec autre modèle (gpt-4o-mini-realtime)
3. Fallback : Approche hybride (STT → LLM → TTS)

---

## 📝 Notes Importantes

### Différences POC vs Production

**Backend POC** (`backend_websocket_minimal.py`) :
- ❌ Pas d'authentification JWT
- ❌ Pas de connexion OpenAI Realtime
- ❌ Pas d'injection Weaviate
- ✅ Juste echo audio pour valider architecture

**Backend Production** (à développer) :
- ✅ Authentification JWT
- ✅ Connexion OpenAI Realtime API
- ✅ Injection contexte Weaviate
- ✅ Gestion erreurs complète
- ✅ Rate limiting
- ✅ Monitoring

### Format Audio

**Recommandation actuelle** : Base64 JSON
- ✅ Compatible tous browsers
- ✅ Debugging facile
- ⚠️ Overhead +33% bande passante

Si problème bande passante :
- Migrer vers WebSocket binaire
- Utiliser Opus codec (compression)

---

## 🐛 Troubleshooting

### Test Q2 échoue (OpenAI)

```bash
# Vérifier API key
echo $OPENAI_API_KEY

# Vérifier quota
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Tester avec curl
curl https://api.openai.com/v1/realtime \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: realtime=v1"
```

### Test Q3 échoue (Weaviate)

```bash
# Vérifier Weaviate accessible
curl http://localhost:8080/v1/meta

# Vérifier collection existe
python -c "
from llm.retrieval.retriever_core import HybridWeaviateRetriever
from llm.utils.imports_and_dependencies import wvc
from llm.config.config import WEAVIATE_URL
client = wvc.Client(url=WEAVIATE_URL)
print(client.collections.list_all())
"
```

### Test Q4 échoue (WebSocket)

```bash
# Vérifier backend running
curl http://localhost:8000

# Vérifier port libre
netstat -an | grep 8000

# Tester WebSocket manuel
wscat -c ws://localhost:8000/ws/voice
```

---

## 📞 Support

Si problèmes pendant POC :
1. Vérifier logs détaillés des scripts
2. Relire section Troubleshooting
3. Consulter documentation OpenAI Realtime API

---

## ✅ Checklist Validation

Après exécution complète :

- [ ] Q2 exécuté avec succès
- [ ] Q3 exécuté avec succès
- [ ] Q4 exécuté avec succès
- [ ] Métriques documentées dans rapport
- [ ] Décision GO/NO-GO pour développement
- [ ] Choix architecture RAG (Option A ou B)
- [ ] Format audio validé

**Date validation POC** : __________

**Décision** : ☐ GO   ☐ NO-GO   ☐ Ajustements nécessaires

**Notes** : ___________________________________________
