# RAGAS Evaluation - Intelia Expert

Ce répertoire contient le système d'évaluation automatique du RAG utilisant RAGAS (Retrieval-Augmented Generation Assessment).

## 🎯 Objectif

Mesurer automatiquement la qualité du système RAG sur 4 dimensions :
- **Context Precision** : Pertinence des documents récupérés
- **Context Recall** : Couverture du contexte vs ground truth
- **Faithfulness** : Fidélité aux sources (pas d'hallucination)
- **Answer Relevancy** : Pertinence de la réponse à la question

## 📁 Structure

```
evaluation/
├── ragas_evaluator.py          # Classe principale RAGAS
├── golden_dataset_intelia.py   # Dataset de test (28 questions)
└── README.md                    # Ce fichier

scripts/
├── run_ragas_evaluation.py     # Script d'exécution principal
└── evaluate.sh                  # Helper bash pour exécution facile
```

## 🚀 Utilisation (Digital Ocean)

### Prérequis

```bash
# 1. Installer dépendances (si pas déjà fait)
pip install ragas datasets langchain-openai

# 2. Vérifier OPENAI_API_KEY
echo $OPENAI_API_KEY  # Doit afficher votre clé
```

### Exécution rapide

```bash
# Se placer dans le bon répertoire
cd /app/llm

# Rendre le script exécutable (première fois seulement)
chmod +x scripts/evaluate.sh

# Test rapide (3 questions, ~30s, ~$0.01)
./scripts/evaluate.sh test

# Évaluation rapide (5 questions, ~1 min, ~$0.05)
./scripts/evaluate.sh quick

# Évaluation complète (28 questions, ~5 min, ~$0.50)
./scripts/evaluate.sh full
```

### Exécution avancée

```bash
# Spécifier nombre de questions
python3 scripts/run_ragas_evaluation.py --test-cases 10

# Utiliser GPT-4 au lieu de GPT-4o-mini (plus précis mais cher)
python3 scripts/run_ragas_evaluation.py --llm gpt-4

# Spécifier fichier de sortie
python3 scripts/run_ragas_evaluation.py --output results/eval_v2.json

# Mode simulation (ne pas appeler le RAG réel, pour tests)
python3 scripts/run_ragas_evaluation.py --simulate
```

## 📊 Dataset de test (28 questions)

Le dataset couvre tous les aspects critiques :

| Catégorie | Questions | Description |
|-----------|-----------|-------------|
| **Calculs** | 5 | Feed calculation, reverse lookup, projection, flock |
| **Diagnostics** | 3 | Sous-performance, FCR élevé, stress thermique |
| **Nutrition** | 2 | Spécifications Cobb 500, concepts starter/grower |
| **Environnement** | 2 | Température, validation paramètres |
| **Comparatifs** | 3 | Multi-âges, subjectif (Ross vs Cobb) |
| **Multi-langue** | 2 | Français, anglais, thaï (non supporté) |
| **Conversationnel** | 4 | Follow-up avec mémoire contextuelle |
| **Validation** | 3 | Âge hors limites, questions incomplètes |
| **Out-of-domain** | 1 | Cryptomonnaie (doit être rejeté) |
| **Métriques simples** | 3 | Poids, FCR, multi-métriques |

**Exemples de questions :**

```python
# Calcul complexe
"Je suis rendu au 18e jour et j'élève du Ross 308 mâle.
 De combien de moulées pour atteindre 2,4 kg ?"

# Diagnostic
"Mon troupeau Ross 308 à 28j pèse 1300g au lieu de 1550g, c'est grave ?"

# Out-of-domain
"Qu'est-ce que la cryptomonnaie ?"  # Doit être rejeté

# Conversationnel (2 tours)
Tour 1: "Quel est le poids Ross 308 mâle à 21 jours ?"
Tour 2: "Et à 28 jours ?"  # Doit garder contexte
```

## 📈 Interprétation des scores

### Scores globaux

| Score | Interprétation | Action |
|-------|----------------|--------|
| **≥ 90%** | 🏆 Excellent | Système très performant |
| **80-90%** | ✅ Très bon | Qualité élevée, améliorations mineures |
| **70-80%** | ⚠️ Bon | Améliorations recommandées |
| **< 70%** | ❌ Insuffisant | Optimisation requise |

### Métriques individuelles

**Context Precision < 80% ?**
- Améliorer reranking (Cohere)
- Optimiser seuils de similarité
- Affiner recherche hybride (RRF)

**Context Recall < 80% ?**
- Augmenter top_k retrieval
- Enrichir base de connaissances
- Améliorer embeddings (fine-tuning)

**Faithfulness < 80% ?**
- Renforcer guardrails (hallucination detection)
- Ajuster prompts système
- Réduire température LLM

**Answer Relevancy < 80% ?**
- Optimiser génération de réponse
- Affiner prompts contextuels
- Améliorer compréhension d'intention

## 📁 Résultats générés

### Fichier JSON (`logs/ragas_evaluation_{timestamp}.json`)

```json
{
  "scores": {
    "context_precision": 0.892,
    "context_recall": 0.854,
    "faithfulness": 0.913,
    "answer_relevancy": 0.841,
    "overall": 0.875
  },
  "detailed_scores": [
    {
      "question": "Je suis rendu au 18e jour...",
      "answer": "Pour atteindre un poids cible de 2400g...",
      "context_precision": 0.95,
      "context_recall": 0.88,
      "faithfulness": 0.92,
      "answer_relevancy": 0.87
    }
  ],
  "timestamp": "2025-10-07T14:45:00",
  "llm_model": "gpt-4o-mini",
  "num_test_cases": 28,
  "duration_seconds": 297.3
}
```

### Voir les résultats

```bash
# Lister les évaluations récentes
ls -lht logs/ragas_evaluation_* | head -5

# Voir le résumé d'une évaluation
cat logs/ragas_evaluation_20251007_144500.json | jq '.scores'

# Voir les questions qui ont échoué (score < 0.7)
cat logs/ragas_evaluation_*.json | jq '.detailed_scores[] | select(.answer_relevancy < 0.7) | .question'
```

## 💰 Coûts estimés

| Mode | Questions | Durée | Coût (GPT-4o-mini) |
|------|-----------|-------|-------------------|
| **test** | 3 | ~30s | ~$0.01 |
| **quick** | 5 | ~1 min | ~$0.05 |
| **full** | 28 | ~5 min | ~$0.40-0.60 |

**Budget mensuel recommandé :**
- Tests après changements : ~$2-3/mois (5-10 évaluations)
- Monitoring hebdomadaire : ~$2-3/mois (4 évaluations × $0.60)
- **Total : ~$5-6/mois**

## 🔧 Ajouter de nouvelles questions

Éditer `evaluation/golden_dataset_intelia.py` :

```python
{
    "question": "Votre nouvelle question ici",
    "ground_truth": "Réponse attendue (validée manuellement)",
    "category": "nutrition",  # ou calculation, diagnostic, etc.
    "expected_behavior": "Description du comportement attendu",
    "contexts": [],  # Rempli automatiquement
    "answer": ""     # Rempli automatiquement
},
```

## 📝 Maintenance

### Quand ré-évaluer ?

✅ **Après changements importants :**
- Modifications du query router
- Nouveaux handlers (calculation, comparative)
- Changements dans les prompts système
- Mise à jour des embeddings
- Ajout de nouvelles données

✅ **Périodiquement :**
- 1x/semaine : Quick evaluation (5 questions)
- 1x/mois : Full evaluation (28 questions)
- Avant déploiement production

### Enrichir le dataset

Le dataset doit évoluer avec le système :
- Ajouter questions basées sur feedback utilisateurs
- Couvrir nouveaux features (pondeuses, vaccination)
- Cas d'edge découverts en production
- Objectif : 50-100 questions à terme

## 🐛 Troubleshooting

**Erreur "OPENAI_API_KEY non configurée" :**
```bash
export OPENAI_API_KEY='sk-...'
# Ou ajouter dans .env
```

**Erreur "ragas not installed" :**
```bash
pip install ragas datasets langchain-openai
```

**Timeout lors de l'évaluation :**
```bash
# Réduire nombre de questions
./scripts/evaluate.sh test  # Au lieu de full
```

**Scores très bas (< 50%) :**
- Vérifier que le RAG Engine est bien initialisé
- Vérifier connexion PostgreSQL/Weaviate
- Tester en mode `--simulate` pour isoler le problème

## 📚 Références

- [RAGAS Documentation](https://docs.ragas.io/en/stable/)
- [RAGAS GitHub](https://github.com/explodinggradients/ragas)
- [Paper: RAGAS Framework](https://arxiv.org/abs/2309.15217)

---

**Questions ?** Voir les logs détaillés dans `logs/ragas_evaluation_*.log`
