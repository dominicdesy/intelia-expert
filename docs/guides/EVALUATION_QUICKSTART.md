# RAGAS Evaluation - Guide de démarrage rapide

## 🚀 Premiers pas sur Digital Ocean

### 1. Connexion SSH
```bash
ssh root@your-droplet-ip
cd /app/llm
```

### 2. Vérifier prérequis
```bash
# Vérifier que RAGAS est installé
python3 -c "import ragas; print('✅ RAGAS OK')"

# Si erreur, installer
pip install ragas datasets langchain-openai

# Vérifier OPENAI_API_KEY
echo $OPENAI_API_KEY
# Si vide, configurer:
export OPENAI_API_KEY='sk-...'
```

### 3. Premier test (30 secondes)
```bash
# Rendre le script exécutable
chmod +x scripts/evaluate.sh

# Lancer test rapide
./scripts/evaluate.sh test
```

**Résultat attendu :**
```
🧪 Test rapide (3 questions)
   Durée: ~30 secondes
   Coût estimé: ~$0.01

🚀 RAGAS EVALUATION - Intelia Expert LLM
📊 Chargement dataset golden Intelia...
   ✅ 28 cas de test générés
   Limité à 3 cas de test
🔧 Initialisation InteliaRAGEngine...
   ✅ RAG Engine initialisé
🔍 Interrogation du système RAG (3 questions)...
   [1/3] Je suis rendu au 18e jour de production...
   [2/3] Quelle maladie frappe le plus souvent...
   [3/3] Qu'est-ce que la cryptomonnaie ?
   ✅ Toutes les questions traitées

📊 Évaluation RAGAS en cours...

=================================================================
📊 RAGAS EVALUATION REPORT - Intelia Expert LLM
=================================================================

Test Cases:        3
LLM Model:         gpt-4o-mini
Duration:          28.5s
Timestamp:         2025-10-07 14:30:00

-----------------------------------------------------------------
SCORES
-----------------------------------------------------------------
Overall Score:          85.30%

Context Precision:      88.40%
Context Recall:         82.10%
Faithfulness:           89.20%
Answer Relevancy:       81.50%

-----------------------------------------------------------------
INTERPRETATION
-----------------------------------------------------------------
✅ Très Bon: Qualité élevée (80-90%)

=================================================================

✅ Évaluation terminée
📁 Résultats: logs/ragas_evaluation_20251007_143000.json
```

## 📋 Commandes courantes

### Test rapide après changements
```bash
./scripts/evaluate.sh quick    # 5 questions, ~1 min
```

### Évaluation complète avant déploiement
```bash
./scripts/evaluate.sh full     # 28 questions, ~5 min
```

### Voir les résultats récents
```bash
# Lister les 5 dernières évaluations
ls -lht logs/ragas_evaluation_* | head -5

# Voir les scores de la dernière évaluation
cat $(ls -t logs/ragas_evaluation_*.json | head -1) | jq '.scores'
```

### Exemples de résultats
```bash
# Scores globaux
cat logs/ragas_evaluation_*.json | jq '{
  overall: .scores.overall,
  precision: .scores.context_precision,
  recall: .scores.context_recall,
  faithfulness: .scores.faithfulness,
  relevancy: .scores.answer_relevancy
}'

# Questions qui ont échoué (< 70%)
cat logs/ragas_evaluation_*.json | jq '
  .detailed_scores[] |
  select(.answer_relevancy < 0.7) |
  {question: .question, score: .answer_relevancy}
'
```

## ⚠️ Problèmes fréquents

### "OPENAI_API_KEY non définie"
```bash
export OPENAI_API_KEY='sk-proj-...'

# Pour rendre permanent, ajouter dans ~/.bashrc
echo "export OPENAI_API_KEY='sk-proj-...'" >> ~/.bashrc
source ~/.bashrc
```

### "Module ragas not found"
```bash
pip install ragas datasets langchain-openai
```

### "Permission denied: ./scripts/evaluate.sh"
```bash
chmod +x scripts/evaluate.sh
```

### Évaluation trop lente
```bash
# Utiliser mode test (3 questions)
./scripts/evaluate.sh test

# Ou spécifier nombre réduit
python3 scripts/run_ragas_evaluation.py --test-cases 5
```

## 📊 Interprétation rapide

| Score Overall | Signification | Action |
|---------------|---------------|--------|
| **≥ 90%** | 🏆 Excellent | Continue comme ça ! |
| **80-90%** | ✅ Très bon | RAS, petites optimisations possibles |
| **70-80%** | ⚠️ Acceptable | Identifier questions problématiques |
| **< 70%** | ❌ Problème | Investigation requise |

### Si score baisse soudainement

1. **Vérifier les logs :**
   ```bash
   tail -50 logs/ragas_evaluation_*.log
   ```

2. **Comparer avec évaluation précédente :**
   ```bash
   # Score actuel
   cat $(ls -t logs/ragas_evaluation_*.json | head -1) | jq '.scores.overall'

   # Score précédent
   cat $(ls -t logs/ragas_evaluation_*.json | head -2 | tail -1) | jq '.scores.overall'
   ```

3. **Identifier questions problématiques :**
   ```bash
   cat logs/ragas_evaluation_*.json | jq '.detailed_scores[] | select(.answer_relevancy < 0.7)'
   ```

## 🔄 Workflow recommandé

### Après un changement de code
```bash
# 1. Test rapide
./scripts/evaluate.sh test

# 2. Si OK, évaluation plus large
./scripts/evaluate.sh quick

# 3. Si tout OK, deployer
git push origin main
```

### Monitoring hebdomadaire
```bash
# Tous les lundis
./scripts/evaluate.sh quick > weekly_evaluation.txt
# Vérifier que score > 80%
```

## 💡 Conseils

✅ **Bonnes pratiques :**
- Faire `test` après chaque changement majeur
- Faire `quick` avant chaque déploiement
- Faire `full` 1x/mois pour monitoring complet
- Garder historique des résultats (déjà dans logs/)

❌ **À éviter :**
- Ne pas lancer `full` trop souvent (coût)
- Ne pas ignorer score < 80%
- Ne pas déployer sans tester

## 📞 Support

**Documentation complète :** `evaluation/README.md`

**Ajouter des questions :** Éditer `evaluation/golden_dataset_intelia.py`

**Problème technique :** Vérifier `logs/ragas_evaluation_*.log`
