# API Admin - RAGAS Evaluation

Endpoint API pour déclencher des évaluations RAGAS du système RAG sur Digital Ocean App Platform.

## 🚀 Utilisation

### Déclencher une évaluation

```bash
curl -X POST https://expert.intelia.com/llm/admin/evaluate-rag \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -d '{
    "test_cases": 2,
    "llm_model": "gpt-4o-mini",
    "use_simulation": false
  }'
```

**Paramètres:**
- `test_cases`: Nombre de questions (⚠️ **MAX 2** pour éviter timeout)
- `llm_model`: Modèle d'évaluation (`gpt-4o-mini` ou `gpt-4o`)
- `use_simulation`: `false` pour RAG réel, `true` pour simulation

**Réponse (après ~50s):**
```json
{
  "scores": {
    "context_precision": 0.85,
    "context_recall": 0.78,
    "faithfulness": 0.92,
    "answer_relevancy": 0.88,
    "overall": 0.86
  },
  "detailed_scores": [...],
  "summary": "📊 RAGAS EVALUATION REPORT...",
  "timestamp": "2025-10-07T15:32:53",
  "llm_model": "gpt-4o-mini",
  "num_test_cases": 2,
  "duration_seconds": 51.88
}
```

### Vérifier les dépendances

```bash
curl -s https://expert.intelia.com/llm/admin/debug-imports | python3 -m json.tool
```

**Réponse:**
```json
{
  "imports": {
    "ragas": {"available": true},
    "datasets": {"available": true},
    "langchain_openai": {"available": true}
  },
  "ready_for_evaluation": true
}
```

### Info système

```bash
curl -s https://expert.intelia.com/llm/admin/info | python3 -m json.tool
```

## ⚠️ Limitations

### Timeout 2 minutes
Digital Ocean App Platform a un timeout de **2 minutes** pour les requêtes HTTP.

**Durée par question:**
- 1 question: ~25 secondes ✅
- 2 questions: ~50 secondes ✅
- 3 questions: ~75 secondes ✅ (mais risqué)
- 5 questions: ~2+ minutes ❌ **TIMEOUT**

**Recommandation:** Maximum **2 questions** pour production

### Coûts estimés

| Questions | Durée | Coût (gpt-4o-mini) |
|-----------|-------|-------------------|
| 2         | ~50s  | ~$0.02           |
| 3         | ~75s  | ~$0.03           |
| 5         | ~2min | ~$0.05           |
| 10        | ~4min | ~$0.10 (timeout) |

**Budget recommandé:** ~$1-2/mois pour évaluations régulières

## 📊 Interprétation des scores

### Scores individuels

**Context Precision (0-100%)**
- Pertinence des documents récupérés
- **< 70%:** Documents non pertinents → Améliorer reranking/similarité
- **70-85%:** Bon
- **> 85%:** Excellent

**Context Recall (0-100%)**
- Couverture du contexte vs ground truth
- **< 70%:** Contexte incomplet → Augmenter top_k, enrichir base
- **70-85%:** Bon
- **> 85%:** Excellent

**Faithfulness (0-100%)**
- Fidélité de la réponse au contexte (pas d'hallucination)
- **< 70%:** Hallucinations → Renforcer guardrails, réduire température
- **70-85%:** Bon
- **> 85%:** Excellent

**Answer Relevancy (0-100%)**
- Pertinence de la réponse à la question
- **< 70%:** Réponse hors-sujet → Améliorer prompts
- **70-85%:** Bon
- **> 85%:** Excellent ✅

### Score global (Overall)

```
≥ 90%  🏆 Excellent
80-90% ✅ Très bon
70-80% ⚠️  Acceptable
< 70%  ❌ Problème
```

## 🧪 Dataset de test

**28 questions couvrant:**
- Calculs (feed, projections, reverse lookup)
- Diagnostics (sous-performance, FCR, stress)
- Nutrition (spécifications, concepts)
- Environnement (température, validation)
- Comparatifs (multi-âges, Ross vs Cobb)
- Multi-langue (FR, EN, TH)
- Conversationnel (follow-up avec mémoire)
- Validation (âge hors limites, questions incomplètes)
- Out-of-domain (doit être rejeté)

**Fichier:** `llm/evaluation/golden_dataset_intelia.py`

## 🔧 Troubleshooting

### Erreur 524 (Timeout)
```
error code: 524
```
**Solution:** Réduire `test_cases` à 2 maximum

### Scores NaN
```json
{
  "context_precision": 0.0,
  "context_recall": "nan"
}
```
**Cause:** Contexts vides → Questions de calcul ne retournent pas de contexts

**Solution:** En cours (correction CalculationHandler)

### Dépendances manquantes
```json
{
  "ragas": {"available": false}
}
```
**Solution:** Vérifier `requirements.txt` contient:
```
ragas==0.1.1
datasets>=2.14.0
langchain-core==0.1.52
langsmith>=0.1.0,<0.2.0
langchain-openai>=0.0.5
```

## 📝 Workflow recommandé

### Après modification du RAG
```bash
# 1. Test rapide (2 questions)
curl -X POST https://expert.intelia.com/llm/admin/evaluate-rag \
  -H "Content-Type: application/json" \
  -d '{"test_cases": 2, "llm_model": "gpt-4o-mini", "use_simulation": false}'

# 2. Vérifier Answer Relevancy > 80%
# Si OK → Déployer
```

### Monitoring hebdomadaire
```bash
# Lancer évaluation tous les lundis
curl -X POST https://expert.intelia.com/llm/admin/evaluate-rag \
  -H "Content-Type: application/json" \
  -d '{"test_cases": 2, "llm_model": "gpt-4o-mini", "use_simulation": false}' \
  > weekly_evaluation_$(date +%Y%m%d).json

# Vérifier score global
cat weekly_evaluation_*.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Overall: {data['scores']['overall']:.2%}\")"
```

## 🚧 Problèmes connus

### 1. Context Precision = 0% pour certaines questions
**Symptôme:** Documents retournés non pertinents (ex: question sur maladies → contextes sur feed intake)

**Cause:** Problème dans le RAG Engine (embeddings, reranking, ou base vectorielle)

**Statut:** Investigation requise (Option 3)

### 2. Contexts vides pour calculs
**Symptôme:** Questions de calcul retournent `contexts: []`

**Cause:** CalculationHandler ne renseigne pas `context_docs`

**Statut:** ✅ **En cours de correction (Option 2)**

### 3. Timeout pour 3+ questions
**Symptôme:** Erreur 524 après 2 minutes

**Cause:** Limite Digital Ocean App Platform

**Solution:** Utiliser 2 questions maximum

## 📚 Documentation complète

- **Guide détaillé:** `llm/evaluation/README.md`
- **Quick start:** `llm/scripts/EVALUATION_QUICKSTART.md`
- **Dataset:** `llm/evaluation/golden_dataset_intelia.py`
- **Script CLI:** `llm/scripts/run_ragas_evaluation.py`

## 🔗 Endpoints disponibles

```
GET  /llm/admin/info              # Info système
GET  /llm/admin/debug-imports     # Vérifier dépendances
POST /llm/admin/evaluate-rag      # Déclencher évaluation
GET  /llm/admin/evaluation-results    # Résultats (fichiers, non fonctionnel sur App Platform)
GET  /llm/admin/evaluation-history    # Historique (fichiers, non fonctionnel sur App Platform)
```

---

**Version:** 1.0
**Date:** 2025-10-07
**Statut:** ✅ Opérationnel (avec limitations)
