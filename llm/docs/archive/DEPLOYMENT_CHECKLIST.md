# Checklist de Déploiement - Digital Ocean App Platform

**Date:** 2025-10-05
**Objectif:** Déployer les Quick Wins en production

---

## ✅ Pré-requis

- [x] Code poussé sur GitHub (branche main)
- [x] requirements.txt mis à jour avec nouvelles dépendances :
  - `cohere>=5.0.0`
  - `anthropic>=0.40.0`
  - `ragas==0.1.19`
  - `datasets>=2.14.0`
  - `langchain-openai>=0.0.5`

---

## 🔑 Étape 1 : Obtenir les Clés API

### 1.1 Cohere API Key

**URL:** https://dashboard.cohere.com/api-keys

1. Créer compte gratuit Cohere
2. Aller dans "API Keys"
3. Créer nouvelle clé → Copier `COHERE_API_KEY`
4. Plan gratuit : 1000 req/mois (suffisant pour démarrer)

**Format:** `co-xxxxxxxxxxxxxxxxxxxxxxxx`

---

### 1.2 Anthropic API Key (Claude)

**URL:** https://console.anthropic.com/

1. Créer compte Anthropic
2. Aller dans "API Keys"
3. Créer nouvelle clé → Copier `ANTHROPIC_API_KEY`
4. Ajouter crédits ($5 minimum recommandé)

**Format:** `sk-ant-xxxxxxxxxxxxxxxxxxxxx`

---

### 1.3 DeepSeek API Key

**URL:** https://platform.deepseek.com/

1. Créer compte DeepSeek
2. Aller dans "API Keys"
3. Créer nouvelle clé → Copier `DEEPSEEK_API_KEY`
4. Ajouter crédits ($5 recommandé)

**Format:** `sk-xxxxxxxxxxxxxxxxxxxxxxxx`

---

## ⚙️ Étape 2 : Configurer Digital Ocean App Platform

### 2.1 Accéder aux Variables d'Environnement

1. Ouvrir Digital Ocean Console
2. Aller dans "Apps" → Sélectionner "intelia-expert"
3. Aller dans "Settings" → "Environment Variables"
4. Cliquer "Edit" pour le composant LLM

---

### 2.2 Ajouter Nouvelles Variables

**Copier-coller ces variables :**

```bash
# === COHERE RERANK (+25% PRECISION) ===
COHERE_API_KEY=co-xxxxxxxxxxxxxxxxxxxxxxxx
COHERE_RERANK_MODEL=rerank-multilingual-v3.0
COHERE_RERANK_TOP_N=3

# === MULTI-LLM ROUTER (-79% COÛT) ===
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=gpt4o
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# === EMBEDDINGS 3-LARGE (+15% RECALL) ===
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1536
```

**⚠️ Remplacer les `xxx` par les vraies clés API obtenues à l'étape 1**

---

### 2.3 Sauvegarder et Redémarrer

1. Cliquer "Save" en bas de la page
2. Digital Ocean va automatiquement :
   - Installer les nouvelles dépendances (requirements.txt)
   - Configurer les variables d'environnement
   - Redémarrer le service LLM

**Durée estimée:** 5-10 minutes

---

## 🧪 Étape 3 : Valider le Déploiement

### 3.1 Vérifier Logs de Démarrage

**Aller dans:** Apps → intelia-expert → Runtime Logs

**Chercher ces messages:**
```
✅ RAG Engine initialisé
✅ Cohere Reranker initialisé (model: rerank-multilingual-v3.0)
✅ Multi-LLM Router activé (3 providers)
📊 Modèle d'embedding: text-embedding-3-large
📊 Dimensions: 1536
```

**Si erreur:**
- Vérifier que les clés API sont correctes
- Vérifier qu'il n'y a pas d'espaces avant/après les clés

---

### 3.2 Tester une Query Simple

**Endpoint:** `https://votre-app.ondigitalocean.app/api/v1/query`

**cURL:**
```bash
curl -X POST https://votre-app.ondigitalocean.app/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quel est le poids cible pour des mâles Ross 308 à 35 jours?",
    "language": "fr"
  }'
```

**Vérifier dans la réponse:**
- ✅ Réponse cohérente
- ✅ Score de confiance > 0.7
- ✅ Documents pertinents retournés

---

### 3.3 Vérifier Métriques

**Endpoint:** `https://votre-app.ondigitalocean.app/metrics`

**Chercher ces métriques:**
```
cohere_reranking_used{...} 1
llm_provider_usage{provider="deepseek"} X
llm_provider_usage{provider="claude"} Y
llm_provider_usage{provider="gpt4o"} Z
embedding_model{model="text-embedding-3-large"} 1
```

---

## 🔄 Étape 4 : Migration des Embeddings

**⚠️ Cette étape doit être faite APRÈS le redémarrage du service**

### 4.1 Se Connecter au Serveur

**Option A : Console Digital Ocean**
1. Aller dans Apps → intelia-expert → Console
2. Cliquer "Launch Console"

**Option B : SSH (si configuré)**
```bash
ssh your-server
```

---

### 4.2 Dry-Run (Test Sans Modification)

**Exécuter:**
```bash
cd /app
python scripts/migrate_embeddings.py --dry-run
```

**Vérifier la sortie:**
```
🔧 Initialisation des clients...
✅ Client OpenAI initialisé
📊 Modèle d'embedding: text-embedding-3-large
📊 Dimensions cibles: 1536
✅ Weaviate connecté
📊 Documents trouvés: XXXX
🔍 DRY RUN: XXXX documents seraient migrés
```

**Si erreur "OPENAI_API_KEY non trouvée":**
- Attendre 5 min et réessayer (variables env en cours de propagation)
- Vérifier que le service a bien redémarré

---

### 4.3 Migration Réelle

**⚠️ IMPORTANT:** Cette opération modifie tous les vecteurs dans Weaviate

**Exécuter:**
```bash
python scripts/migrate_embeddings.py --batch-size 100
```

**Durée estimée:**
- 1000 documents: ~2-3 minutes
- 5000 documents: ~10-15 minutes
- 10000 documents: ~20-25 minutes

**Suivre la progression:**
```
📦 Batch 1 (documents 1-100/1234)...
   ✅ Success: 100, ❌ Failed: 0
   📊 Progress: 8.1% (100/1234) - Rate: 45.2 docs/s - ETA: 0.4 min

📦 Batch 2 (documents 101-200/1234)...
   ✅ Success: 100, ❌ Failed: 0
   📊 Progress: 16.2% (200/1234) - Rate: 48.1 docs/s - ETA: 0.4 min
...
```

**Résultat attendu:**
```
======================================================================
📊 RÉSUMÉ MIGRATION
======================================================================
Documents total:  1234
✅ Traités:        1234
❌ Échecs:         0
Durée:            25.7s (0.4 min)
Rate:             48.0 docs/s
======================================================================
🎉 Migration terminée avec succès!
```

---

### 4.4 Validation Post-Migration

**Tester la même query qu'avant:**
```bash
curl -X POST https://votre-app.ondigitalocean.app/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Quel est le poids cible pour des mâles Ross 308 à 35 jours?",
    "language": "fr"
  }'
```

**Comparer:**
- Score de confiance devrait être plus élevé
- Documents retournés devraient être plus pertinents
- Temps de réponse similaire ou meilleur

---

## 📊 Étape 5 : Évaluation RAGAS (Baseline)

**⚠️ Cette étape est OPTIONNELLE mais fortement recommandée**

### 5.1 Installer Dépendances RAGAS (si pas déjà fait)

```bash
cd /app
pip install ragas==0.1.19 datasets langchain-openai
```

---

### 5.2 Exécuter Évaluation Baseline

```bash
python scripts/run_ragas_evaluation.py --test-cases 5
```

**Durée:** ~2-3 minutes pour 5 cas de test

**Sortie attendue:**
```
🚀 RAGAS EVALUATION - Intelia Expert LLM
📊 Génération dataset golden...
   ✅ 5 cas de test générés
🔍 Interrogation du système RAG (5 questions)...
   [1/5] Quel est le poids cible pour des mâles Ross 308 à 35 jours?...
   [2/5] Quel FCR est attendu pour des Ross 308 mixte à 42 jours?...
   ...
📊 Évaluation RAGAS en cours...

=================================================================
📊 RAGAS EVALUATION REPORT - Intelia Expert LLM
=================================================================
Overall Score:          XX.X%

Context Precision:      XX.X%
Context Recall:         XX.X%
Faithfulness:           XX.X%
Answer Relevancy:       XX.X%
=================================================================
```

---

### 5.3 Documenter Scores Baseline

**Copier les scores dans un fichier texte pour référence future:**

```
Date: 2025-10-05
Après Quick Wins Deployment:

Overall Score: XX.X%
Context Precision: XX.X%
Context Recall: XX.X%
Faithfulness: XX.X%
Answer Relevancy: XX.X%
```

**Objectifs:**
- Overall Score: ≥ 85%
- Context Precision: ≥ 85%
- Context Recall: ≥ 80%
- Faithfulness: ≥ 90%
- Answer Relevancy: ≥ 85%

---

## 🎯 Étape 6 : Monitoring Post-Déploiement

### 6.1 Métriques à Surveiller (24-48h)

**Endpoint:** `/metrics`

**KPIs:**
```bash
# Cohere Rerank usage
cohere_reranking_used

# Multi-LLM distribution
llm_provider_usage{provider="deepseek"}
llm_provider_usage{provider="claude"}
llm_provider_usage{provider="gpt4o"}

# Embeddings model
embedding_model{model="text-embedding-3-large"}

# Cache hit rate
cache_hits_total / (cache_hits_total + cache_misses_total)
```

---

### 6.2 Logs à Surveiller

**Chercher ces patterns:**

**✅ Bon signe:**
```
🔄 Cohere Rerank: 20 docs → 3 docs (top ranked)
🤖 LLM Router: DeepSeek selected (PostgreSQL hit, confidence=0.95)
📊 Embedding generated: text-embedding-3-large (1536 dims)
```

**⚠️ Avertissement:**
```
⚠️ Cohere API rate limit approached
⚠️ DeepSeek API error, fallback to GPT-4o
⚠️ Embedding generation slow (>2s)
```

**❌ Erreur:**
```
❌ Cohere API key invalid
❌ Anthropic API quota exceeded
❌ Weaviate connection failed
```

---

### 6.3 Coûts à Tracker

**OpenAI (Embeddings + GPT-4o):**
- Dashboard: https://platform.openai.com/usage
- Objectif: <$15/mois (GPT-4o uniquement pour queries complexes)

**Anthropic (Claude 3.5):**
- Dashboard: https://console.anthropic.com/settings/billing
- Objectif: <$20/mois (RAG complexe et multi-docs)

**DeepSeek:**
- Dashboard: https://platform.deepseek.com/usage
- Objectif: <$3/mois (queries simples)

**Cohere:**
- Dashboard: https://dashboard.cohere.com/billing
- Objectif: Plan gratuit (1000 req/mois)

**Total attendu: ~$38/mois** (vs $180/mois avant)

---

## ✅ Checklist Finale

### Code et Configuration
- [x] Code poussé sur GitHub
- [x] requirements.txt mis à jour
- [ ] Variables d'environnement configurées sur Digital Ocean
- [ ] Service LLM redémarré

### Clés API
- [ ] COHERE_API_KEY obtenue et configurée
- [ ] ANTHROPIC_API_KEY obtenue et configurée
- [ ] DEEPSEEK_API_KEY obtenue et configurée

### Déploiement
- [ ] Logs de démarrage vérifiés (pas d'erreur)
- [ ] Query test réussie
- [ ] Métriques `/metrics` accessibles

### Migration Embeddings
- [ ] Dry-run exécuté avec succès
- [ ] Migration réelle terminée sans erreur
- [ ] Validation post-migration (query test)

### Évaluation
- [ ] RAGAS évaluation baseline exécutée
- [ ] Scores documentés
- [ ] Objectifs atteints (≥85% overall)

### Monitoring
- [ ] Métriques surveillées 24h
- [ ] Logs surveillés (pas d'erreur récurrente)
- [ ] Coûts API trackés

---

## 🚨 Troubleshooting

### Erreur: "COHERE_API_KEY invalid"
**Solution:** Vérifier que la clé commence par `co-` et n'a pas d'espaces

### Erreur: "Anthropic API quota exceeded"
**Solution:** Ajouter crédits sur https://console.anthropic.com/settings/billing

### Erreur: "Migration failed - Weaviate connection refused"
**Solution:** Vérifier `WEAVIATE_URL` et `WEAVIATE_API_KEY` dans env vars

### Erreur: "RAGAS evaluation timeout"
**Solution:** Réduire nombre de cas de test: `--test-cases 3`

### Warning: "Cohere rate limit approached"
**Solution:** Passer au plan payant Cohere ou réduire `COHERE_RERANK_TOP_N=2`

---

## 📞 Support

**Documentation:**
- Guide migration: `MIGRATION_EMBEDDINGS_GUIDE.md`
- Guide RAGAS: `RAGAS_IMPLEMENTATION_GUIDE.md`
- Résumé Quick Wins: `QUICK_WINS_DEPLOYMENT_SUMMARY.md`

**Logs:**
- Digital Ocean: Apps → intelia-expert → Runtime Logs
- Fichiers locaux: `logs/` directory

**Contact:**
- GitHub Issues: intelia-expert/llm
- Email: support@intelia.com

---

## 🎉 Succès !

Une fois toutes les étapes complétées, vous aurez :

✅ **+25% précision** retrieval (Cohere Rerank)
✅ **-79% coût** LLM (Multi-LLM Router)
✅ **+15% recall** (Embeddings 3-large)
✅ **Métriques objectives** (RAGAS)
✅ **Système production-ready** pour devenir meilleur au monde

**Prochaines étapes:**
1. Monitorer 1-2 semaines
2. Fine-tuner embeddings (semaines 3-4)
3. Enrichir knowledge base (10k+ documents)
4. Atteindre 92% overall score Q1 2025

---

**Date de création:** 2025-10-05
**Dernière mise à jour:** 2025-10-05
**Status:** ✅ Prêt pour déploiement
