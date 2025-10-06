# Multi-LLM Router - Implementation Guide

## Vue d'ensemble

**Réduction des coûts LLM de 70%** via routing intelligent entre 3 modèles.

Le Multi-LLM Router analyse chaque query et route automatiquement vers le modèle optimal en fonction de:
- La complexité de la requête
- Le type de contexte disponible (PostgreSQL vs Weaviate)
- Les capacités requises pour la génération

## Architecture

### Providers LLM

| Provider | Coût/1M tokens | Use Case | % Queries |
|----------|---------------|----------|-----------|
| **DeepSeek** | $0.55 | Queries simples, direct PostgreSQL hits | ~40% |
| **Claude 3.5 Sonnet** | $3.00 | RAG complexe, synthèse multi-documents | ~50% |
| **GPT-4o** | $15.00 | Edge cases, fallback | ~10% |

### Routing Logic

Le router utilise 4 règles séquentielles:

#### Règle 1: PostgreSQL Direct Hit → DeepSeek
```python
if source == "postgresql" and score > 0.9:
    return DEEPSEEK
```

**Critères:**
- Document provenant de PostgreSQL
- Score de similarité > 0.9
- Question quantitative simple

**Exemples:**
- "Poids Ross 308 35 jours ?" → PostgreSQL score 0.95 → **DeepSeek**
- "FCR Cobb 500 40 jours ?" → PostgreSQL score 0.92 → **DeepSeek**

#### Règle 2: Weaviate RAG → Claude 3.5 Sonnet
```python
if "weaviate" in sources and len(context_docs) >= 2:
    return CLAUDE_35_SONNET
```

**Critères:**
- Documents Weaviate (documents non-structurés)
- Minimum 2 documents de contexte
- Synthèse requise

**Exemples:**
- "Comment améliorer FCR ?" → 5 docs Weaviate → **Claude**
- "Différences Ross 308 vs Cobb 500 ?" → Multiple docs → **Claude**

#### Règle 3: Queries Complexes → Claude 3.5 Sonnet
```python
if query_type in ["comparative", "temporal", "calculation"]:
    return CLAUDE_35_SONNET
```

**Critères:**
- Type d'intention: comparative, temporelle, calcul
- Nécessite raisonnement avancé

**Exemples:**
- "Evolution poids jours 20-30 ?" → temporal → **Claude**
- "Quelle lignée a le meilleur ROI ?" → comparative → **Claude**

#### Règle 4: Fallback → GPT-4o
```python
else:
    return GPT_4O
```

**Critères:**
- Edge cases non couverts
- Providers alternatifs indisponibles
- Fallback sécurisé

## Impact Coût

### Avant (100% GPT-4o)
```
1,000,000 tokens × $15/1M = $15.00
```

### Après (Multi-LLM Routing)

Distribution estimée:
```
400,000 tokens × $0.55/1M (DeepSeek)     = $0.22
500,000 tokens × $3.00/1M (Claude)       = $1.50
100,000 tokens × $15.00/1M (GPT-4o)      = $1.50
────────────────────────────────────────────────
Total:                                     $3.22
```

**Économie: $11.78 par 1M tokens (-79%)**

### ROI Mensuel

Pour 100k queries/mois (moyenne 1000 tokens/query):

- **Avant:** 100k × 1000 tokens × $15/1M = **$1,500/mois**
- **Après:** 100k × 1000 tokens × $3.22/1M = **$322/mois**
- **Économie:** **$1,178/mois** = **$14,136/an**

## Configuration

### Variables d'environnement

Ajouter dans `.env`:

```env
# Multi-LLM Configuration
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=gpt4o

# Provider API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

### Options de configuration

#### ENABLE_LLM_ROUTING
- `true`: Active le routing intelligent (défaut, recommandé)
- `false`: Utilise uniquement DEFAULT_LLM_PROVIDER

#### DEFAULT_LLM_PROVIDER
- `gpt4o`: GPT-4o (défaut)
- `claude`: Claude 3.5 Sonnet
- `deepseek`: DeepSeek Chat

**Note:** Si ENABLE_LLM_ROUTING=false, seul DEFAULT_LLM_PROVIDER sera utilisé.

### Désactiver routing

Pour désactiver temporairement le routing et utiliser 100% GPT-4o:

```env
ENABLE_LLM_ROUTING=false
DEFAULT_LLM_PROVIDER=gpt4o
```

### Providers partiels

Le router fonctionne même si certains providers ne sont pas configurés:

- **Sans DeepSeek:** Queries simples → fallback GPT-4o
- **Sans Claude:** Queries complexes → fallback GPT-4o
- **Sans Anthropic key:** 100% GPT-4o (aucune erreur)

## Métriques

### Endpoint `/api/v1/metrics`

Le router expose des métriques détaillées:

```json
{
  "llm_router": {
    "providers": {
      "deepseek": {
        "calls": 400,
        "tokens": 400000,
        "cost": 0.22
      },
      "claude": {
        "calls": 500,
        "tokens": 500000,
        "cost": 1.50
      },
      "gpt4o": {
        "calls": 100,
        "tokens": 100000,
        "cost": 1.50
      }
    },
    "total": {
      "calls": 1000,
      "tokens": 1000000,
      "cost": 3.22,
      "avg_cost_per_1m": 3.22,
      "cost_if_gpt4o_only": 15.00,
      "savings": 11.78,
      "savings_pct": 78.5
    },
    "routing_enabled": true,
    "providers_available": {
      "deepseek": true,
      "claude": true,
      "gpt4o": true
    }
  }
}
```

### Métriques clés

- **cost**: Coût total réel
- **cost_if_gpt4o_only**: Coût si 100% GPT-4o
- **savings**: Économies réalisées ($)
- **savings_pct**: Pourcentage d'économies (%)
- **avg_cost_per_1m**: Coût moyen par 1M tokens

## Tests de Validation

### Test 1: Routing PostgreSQL → DeepSeek

```python
from generation.llm_router import get_llm_router, LLMProvider

router = get_llm_router()

# Simuler PostgreSQL direct hit
context_docs = [{
    "score": 0.95,
    "metadata": {"source": "postgresql"},
    "content": "Ross 308: 2441g at 35 days"
}]

provider = router.route_query(
    query="Poids Ross 308 35 jours ?",
    context_docs=context_docs,
    intent_result=None
)

assert provider == LLMProvider.DEEPSEEK
print("✅ Test 1 passed: PostgreSQL → DeepSeek")
```

### Test 2: Routing Weaviate → Claude

```python
# Simuler Weaviate RAG
context_docs = [
    {"metadata": {"source": "weaviate"}, "content": "Doc 1..."},
    {"metadata": {"source": "weaviate"}, "content": "Doc 2..."}
]

provider = router.route_query(
    query="Comment améliorer FCR ?",
    context_docs=context_docs,
    intent_result=None
)

assert provider == LLMProvider.CLAUDE_35_SONNET
print("✅ Test 2 passed: Weaviate RAG → Claude")
```

### Test 3: Routing Comparative → Claude

```python
# Simuler query comparative
intent_result = {"intent_type": "comparative"}

provider = router.route_query(
    query="Ross 308 vs Cobb 500 ?",
    context_docs=[],
    intent_result=intent_result
)

assert provider == LLMProvider.CLAUDE_35_SONNET
print("✅ Test 3 passed: Comparative query → Claude")
```

### Test 4: Fallback → GPT-4o

```python
# Simuler edge case
provider = router.route_query(
    query="Question complexe atypique",
    context_docs=[],
    intent_result=None
)

assert provider == LLMProvider.GPT_4O
print("✅ Test 4 passed: Edge case → GPT-4o")
```

### Test 5: Génération end-to-end

```python
import asyncio

async def test_generation():
    router = get_llm_router()

    messages = [
        {"role": "system", "content": "You are a poultry expert."},
        {"role": "user", "content": "What is the target weight for Ross 308 at 35 days?"}
    ]

    # Test avec DeepSeek
    response = await router.generate(
        provider=LLMProvider.DEEPSEEK,
        messages=messages,
        temperature=0.1,
        max_tokens=200
    )

    assert len(response) > 0
    print(f"✅ Test 5 passed: DeepSeek generation: {response[:50]}...")

    # Vérifier les stats
    stats = router.get_stats()
    assert stats["total"]["calls"] > 0
    assert stats["providers"]["deepseek"]["calls"] > 0
    print(f"✅ Stats updated: {stats['total']}")

asyncio.run(test_generation())
```

## Fallback Strategy

Le router implémente une stratégie de fallback robuste:

### Fallback automatique

1. Si DeepSeek échoue → GPT-4o
2. Si Claude échoue → GPT-4o
3. Si provider non configuré → GPT-4o

### Logging des fallbacks

```
⚠️ deepseek generation failed: API timeout, fallback to GPT-4o
✅ GPT-4o: 1500 tokens, $0.0225
```

### Pas d'interruption de service

- Aucune requête utilisateur échoue
- Fallback transparent vers GPT-4o
- Métriques trackent les fallbacks

## Qualité vs Coût

### Benchmark qualité (estimation)

| Provider | Qualité | Use Case | Coût |
|----------|---------|----------|------|
| DeepSeek | ~95% GPT-4o | Queries simples | $0.55/1M |
| Claude 3.5 Sonnet | ~98% GPT-4o | RAG complexe | $3/1M |
| GPT-4o | 100% (baseline) | Edge cases | $15/1M |

**Qualité moyenne pondérée: 96-97%**

### Trade-off acceptable

- **Perte qualité:** -3% vs 100% GPT-4o
- **Gain coût:** -79% vs 100% GPT-4o

**ROI: Excellent** pour la majorité des use cases avicoles.

## Checklist d'Activation

### Prérequis

- [ ] Backend `llm/` version avec `llm_router.py`
- [ ] `anthropic>=0.40.0` dans `requirements.txt`
- [ ] `.env` configuré avec variables Multi-LLM

### Configuration minimale (GPT-4o + Claude)

```env
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=gpt4o
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Économies: ~50%** (Claude pour RAG, GPT-4o pour simple queries)

### Configuration optimale (3 providers)

```env
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=gpt4o
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPSEEK_API_KEY=sk-...
```

**Économies: ~79%** (routing optimal)

### Vérification post-déploiement

1. **Test endpoint `/api/v1/metrics`**
   - Vérifier `llm_router.providers_available`
   - Vérifier `llm_router.routing_enabled: true`

2. **Test query simple**
   - Query: "Poids Ross 308 35j ?"
   - Logs: Chercher `🔀 Route → DeepSeek`

3. **Test query complexe**
   - Query: "Différence Ross vs Cobb ?"
   - Logs: Chercher `🔀 Route → Claude`

4. **Vérifier métriques après 1h**
   - Endpoint `/api/v1/metrics`
   - Vérifier `llm_router.total.savings_pct > 0`

### Rollback si problème

En cas de problème, désactiver immédiatement:

```env
ENABLE_LLM_ROUTING=false
DEFAULT_LLM_PROVIDER=gpt4o
```

Redémarrer service → Retour 100% GPT-4o.

## Troubleshooting

### Provider unavailable

**Symptôme:** Logs `⚠️ DeepSeek client initialization failed`

**Solution:**
- Vérifier `DEEPSEEK_API_KEY` dans `.env`
- Router utilisera GPT-4o en fallback automatique
- Pas d'impact sur le service

### Coût ne diminue pas

**Symptôme:** `savings_pct` reste à 0%

**Vérifications:**
1. `ENABLE_LLM_ROUTING=true` ?
2. API keys configurées ?
3. Queries variées (pas que fallback) ?
4. Logs montrent routing actif ?

### Qualité dégradée

**Symptôme:** Réponses moins précises

**Actions:**
1. Identifier le provider responsable (via logs)
2. Désactiver ce provider spécifiquement
3. Ouvrir issue avec exemples

**Rollback temporaire:**
```env
ENABLE_LLM_ROUTING=false
DEFAULT_LLM_PROVIDER=gpt4o
```

## Monitoring Continu

### Métriques à surveiller

1. **savings_pct**: Objectif >60%
2. **avg_cost_per_1m**: Objectif <$5/1M
3. **providers distribution**: Équilibré selon use cases
4. **fallback rate**: Objectif <5%

### Alertes recommandées

- savings_pct < 40% pendant 24h → Investiguer routing
- DeepSeek calls = 0 pendant 1h → Vérifier API key
- Claude calls = 0 pendant 1h → Vérifier API key
- GPT-4o calls > 50% → Vérifier règles routing

## Future Optimizations

### Phase 2 (Q2 2025)
- [ ] Ajout modèles spécialisés (Mistral, LLaMA)
- [ ] Routing basé sur score de confiance
- [ ] A/B testing qualité par provider

### Phase 3 (Q3 2025)
- [ ] Routing ML-based (apprentissage optimal)
- [ ] Cache cross-provider (déduplication)
- [ ] Cost prediction en temps réel

## Support

**Questions:** Voir `C:\intelia_gpt\intelia-expert\llm\generation\llm_router.py`

**Issues:** Créer ticket avec:
- Logs de routing
- Métriques `/api/v1/metrics`
- Exemples de queries problématiques

---

**Date de création:** 2025-10-05
**Version:** 1.0.0
**Auteur:** Multi-LLM Router Implementation Team
