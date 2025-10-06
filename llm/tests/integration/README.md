# Complete System Integration Tests

Suite complète de tests d'intégration pour le système RAG Intelia Expert.

## Vue d'ensemble

Cette suite de tests valide le système complet de bout en bout avec:

- **100 requêtes réalistes** couvrant tous les domaines
- **12 langues** : FR, EN, ES, DE, IT, PT, PL, NL, ID, HI, ZH, TH
- **5 domaines** : Production, Santé, Nutrition, Environnement, Management
- **Validations automatiques** : longueur de réponse, extraction d'entités, génération de follow-ups
- **Métriques détaillées** : latence, coût, taux de succès

## Structure des fichiers

```
tests/integration/
├── README.md                           # Ce fichier
├── test_queries.json                   # 100 requêtes de test avec métadonnées
├── generate_full_queries_multilang.py  # Générateur de requêtes
├── test_complete_system.py             # Runner de tests principal
└── test_results_YYYYMMDD_HHMMSS.json  # Résultats détaillés (générés)
```

## Requêtes de test

### Distribution par langue

| Langue | Code | Requêtes | %    |
|--------|------|----------|------|
| Français | fr | 25 | 25% |
| Anglais | en | 20 | 20% |
| Espagnol | es | 10 | 10% |
| Allemand | de | 10 | 10% |
| Italien | it | 8 | 8% |
| Portugais | pt | 7 | 7% |
| Polonais | pl | 5 | 5% |
| Néerlandais | nl | 5 | 5% |
| Indonésien | id | 4 | 4% |
| Hindi | hi | 3 | 3% |
| Chinois | zh | 2 | 2% |
| Thaï | th | 1 | 1% |

### Distribution par domaine

| Domaine | Requêtes | % |
|---------|----------|---|
| Production | 49 | 49% |
| Santé | 19 | 19% |
| Nutrition | 16 | 16% |
| Environnement | 10 | 10% |
| Management | 6 | 6% |

### Types de requêtes

- **Standard** (85%) : Requêtes simples sur des métriques ou données
- **Comparative** (15%) : Comparaisons entre races ou stratégies

### Contextes d'assistance

- **performance_issue** : Problèmes de performance (poids, FCR, etc.)
- **health_concern** : Préoccupations de santé (maladies, mortalité)
- **optimization** : Comment améliorer les performances
- **comparison** : Comparaison de races ou stratégies
- **planning** : Planification de lots
- **general_info** : Informations générales

## Utilisation

### Prérequis

1. Copier les variables d'environnement de Digital Ocean :

```bash
# Créer un fichier .env.test
cp .env.production .env.test

# Variables requises :
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY (optionnel)
# - DEEPSEEK_API_KEY (optionnel)
# - COHERE_API_KEY (pour reranking)
# - DATABASE_URL (PostgreSQL)
# - CHROMADB_PATH
```

2. Charger les variables :

```bash
# Linux/Mac
export $(cat .env.test | xargs)

# Windows PowerShell
Get-Content .env.test | ForEach-Object {
    $name, $value = $_.split('=')
    Set-Item -Path env:$name -Value $value
}
```

### Exécuter tous les tests (100 requêtes)

```bash
cd tests/integration
python test_complete_system.py
```

**Durée estimée** : 15-20 minutes
**Coût estimé** : $0.30 USD

### Exécuter un sous-ensemble de tests

```bash
# Tester seulement les 10 premières requêtes
python test_complete_system.py --queries 10

# Mode verbeux pour déboguer
python test_complete_system.py --queries 10 --verbose
```

### Exemple de sortie

```
======================================================================
COMPLETE SYSTEM INTEGRATION TEST SUITE
======================================================================

Loading test queries from test_queries.json...
Loaded 100 test queries

Initializing system components...
OK - Intent Classifier initialized
OK - Multi-Retriever initialized
OK - Response Generator initialized
OK - All components initialized successfully

Executing 100 test queries...
Progress: 100/100 (100%)

======================================================================
TEST RESULTS SUMMARY
======================================================================

Overall Results:
  Total queries:    100
  Successful:       97
  Failed:           3
  Success rate:     97.0%
  Total time:       842.3s

Performance Metrics:
  Avg latency:      8423ms
  Min latency:      3201ms
  Max latency:      15678ms

Entity Extraction:
  Success rate:     94.8%
  Total entities:   412

Proactive Assistant:
  Follow-up rate:   91.7%

Response Quality:
  Avg length:       487 chars
  Length valid:     96.9%

Estimated Cost:
  Total:            $0.29 USD

Failures (3):
  [45] Masa ciała Ross 308 w 35 dniu...
      Error: Connection timeout

======================================================================
OK - EXCELLENT: All systems operational
======================================================================

Detailed results saved to: test_results_20251006_143022.json
```

## Validations automatiques

Pour chaque requête, le système valide :

### 1. Longueur de réponse

```python
min_response_length <= len(response) <= max_response_length
```

- **Standard** : 200-600 caractères
- **Comparative** : 600-1200 caractères
- **Health/Nutrition** : 400-900 caractères

### 2. Extraction d'entités

Au moins 50% des entités attendues doivent être extraites :

```python
match_rate = len(extracted ∩ expected) / len(expected) >= 0.5
```

Entités attendues selon le type de requête :
- **Production** : `breed`, `age_days`, `metric_type`
- **Nutrition** : `production_phase`, `nutrient_type`
- **Comparative** : `breed` (multiple)

### 3. Génération de follow-up

Vérification qu'une question de suivi proactive a été générée :

```python
follow_up_generated = "?" in response[-200:]
```

### 4. Qualité de réponse

```python
response_valid = (
    response is not None and
    len(response) > 50 and
    response != error_message
)
```

## Métriques collectées

### Par requête

- **Latency** : Temps de réponse total (ms)
- **Retrieval docs** : Nombre de documents récupérés
- **Entities extracted** : Entités extraites avec confiance
- **LLM provider** : Provider utilisé (OpenAI/Anthropic/DeepSeek)
- **Follow-up generated** : Boolean

### Globales

- **Success rate** : % de requêtes réussies
- **Avg latency** : Latence moyenne
- **Entity extraction rate** : % avec extraction réussie
- **Follow-up generation rate** : % avec follow-up généré
- **Cost estimate** : Coût total estimé en USD

## Rapport de test détaillé

Le fichier `test_results_YYYYMMDD_HHMMSS.json` contient :

```json
{
  "summary": {
    "total_queries": 100,
    "successful": 97,
    "failed": 3,
    "success_rate": 97.0,
    "avg_latency_ms": 8423,
    "total_time_seconds": 842.3,
    "entity_extraction_success_rate": 94.8,
    "follow_up_generation_rate": 91.7,
    "avg_response_length": 487,
    "estimated_total_cost_usd": 0.29
  },
  "failures": [
    {
      "id": 45,
      "query": "...",
      "error": "...",
      "language": "pl",
      "domain": "production"
    }
  ],
  "detailed_results": [
    {
      "query_id": 1,
      "query": "Quel poids pour Ross 308 à 35 jours ?",
      "language": "fr",
      "domain": "production",
      "success": true,
      "latency_ms": 7234,
      "response_length": 412,
      "entities_extracted": {
        "breed": "ross 308",
        "age_days": 35,
        "metric_type": "body_weight"
      },
      "follow_up_generated": true,
      "length_valid": true,
      "entities_valid": true
    }
  ]
}
```

## Régénérer les requêtes

Si vous souhaitez modifier les requêtes de test :

```bash
# Éditer generate_full_queries_multilang.py
# Puis régénérer :
python generate_full_queries_multilang.py
```

## Critères de succès

| Critère | Cible | Excellent | Bon | Acceptable |
|---------|-------|-----------|-----|------------|
| Success rate | ≥95% | ≥95% | ≥80% | ≥60% |
| Avg latency | <10s | <8s | <12s | <15s |
| Entity extraction | ≥90% | ≥90% | ≥75% | ≥60% |
| Follow-up rate | ≥85% | ≥90% | ≥80% | ≥70% |
| Length validation | ≥95% | ≥98% | ≥90% | ≥85% |

## Dépannage

### Erreur : "OPENAI_API_KEY non trouvée"

```bash
# Vérifier que les variables sont bien chargées
echo $OPENAI_API_KEY  # Linux/Mac
echo $env:OPENAI_API_KEY  # Windows PowerShell
```

### Erreur : "Connection timeout"

Augmenter le timeout dans `test_complete_system.py` :

```python
# Ligne ~186
response = await self.generator.generate_response(
    query=query,
    context_docs=context_docs,
    language=language,
    intent_result=intent_result,
    timeout=30  # Augmenter à 30s
)
```

### Rate limiting

Ajouter un délai entre les requêtes :

```python
# Ligne ~xxx
await asyncio.sleep(0.5)  # Augmenter à 0.5s
```

## CI/CD Integration

Pour intégrer dans GitHub Actions :

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run integration tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          cd tests/integration
          python test_complete_system.py --queries 20
```

## Support

Pour des questions ou problèmes :

1. Vérifier les logs dans `test_results_*.json`
2. Exécuter en mode verbeux : `--verbose`
3. Tester avec un petit nombre de requêtes : `--queries 5`

## Licence

© 2025 Intelia Expert - Usage interne uniquement
