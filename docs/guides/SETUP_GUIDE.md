# Guide de Setup - Intelia LLM

**Version**: 1.0.0
**Date**: 2025-10-27
**Objectif**: Démarrer le développement du service LLM avec budget <$150/mois

---

## Étape 1: Créer Compte HuggingFace (5 min)

### 1.1 Inscription

1. Aller sur https://huggingface.co/join
2. Créer compte avec email professionnel Intelia
3. Vérifier email

### 1.2 Accepter Termes Meta Llama

**IMPORTANT**: Requis pour accéder au modèle Llama 3.1 8B

1. Aller sur https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
2. Cliquer "Agree and access repository"
3. Accepter les conditions d'utilisation Meta
4. **Attendre approbation** (généralement instantané, parfois 1-2h)

### 1.3 Créer API Token

1. Aller sur https://huggingface.co/settings/tokens
2. Cliquer "New token"
3. **Name**: `intelia-llm-dev`
4. **Type**: Write (requis pour fine-tuning)
5. Copier le token (commence par `hf_...`)
6. **Sauvegarder dans 1Password/secrets manager** ⚠️

---

## Étape 2: Configuration Digital Ocean (10 min)

### 2.1 Créer Service `llm`

**Dans Digital Ocean Console**:

1. Apps → Create App
2. Source: GitHub
3. Repository: `intelia-expert` (monorepo)
4. **Branch**: `main`
5. **Source Directory**: `/llm` (sera créé par Claude)
6. **Build Command**: (laisser auto-detect)
7. **Run Command**: (laisser auto-detect)

### 2.2 Configuration Service

**Nom**: `llm`
**Region**: Same as ai-service (US East ou Frankfurt)
**Instance Size**: Basic ($12/mois) ✅ Suffisant pour Phase 1 (proxy API)
**HTTP Port**: 8081

### 2.3 Environment Variables

Ajouter ces variables dans DO Console:

```bash
# Provider (Phase 1: HuggingFace Serverless)
LLM_PROVIDER=huggingface

# HuggingFace Credentials
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxxxxxx  # SECRET - du Step 1.3
HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct

# Server Config
PORT=8081
LOG_LEVEL=INFO
ENABLE_METRICS=true

# Monitoring (optionnel Phase 1)
LANGFUSE_PUBLIC_KEY=  # À configurer plus tard
LANGFUSE_SECRET_KEY=  # À configurer plus tard
```

**⚠️ IMPORTANT**: Marquer `HUGGINGFACE_API_KEY` comme **SECRET**

### 2.4 Internal Networking

Vérifier que `llm` et `ai-service` sont dans le **même App** ou **même VPC**.

**Internal URLs**:
- `ai-service`: http://ai-service:8080
- `llm`: http://llm:8081 ✅ (nouveau)

### 2.5 Health Check

```
Path: /health
Initial Delay: 30s
Period: 10s
Timeout: 5s
```

---

## Étape 3: Validation Accès Llama (2 min)

### Test accès au modèle

```python
# Test local (avant déploiement)
from huggingface_hub import InferenceClient

client = InferenceClient(token="hf_xxxxxxx")

# Test si accès Llama accordé
try:
    response = client.chat_completion(
        model="meta-llama/Llama-3.1-8B-Instruct",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=20
    )
    print("✅ Accès Llama validé!")
    print(response.choices[0].message.content)
except Exception as e:
    print("❌ Erreur accès Llama:", e)
    print("Vérifier: 1) Token valide, 2) Terms acceptés, 3) Approbation reçue")
```

**Si erreur "Gated model"**: Attendre approbation Meta (vérifier email HF)

---

## Étape 4: Budget Phase 1 - Détails

### Stratégie Optimisation Coûts

**Phase Développement (150-250 requêtes test)**:

| Service | Pricing | Coût 250 requêtes |
|---------|---------|-------------------|
| **HuggingFace Serverless API** | $0.20/1M tokens | ~$0.05 |
| Calcul: 250 requêtes × 500 tokens moy × $0.20/1M = $0.025 | | |

**Coût mensuel réel Phase 1**:

```
Digital Ocean llm (Basic):     $12/mois
HuggingFace Hub (private):      $9/mois (optionnel si modèle public OK)
Fine-tuning (2-3 runs):        $15 total (pas mensuel)
Dev API calls (250 tests):     ~$0.05

TOTAL PHASE 1: ~$21-36/mois ✅ Bien sous $150
```

**Notes**:
- HF Serverless API = pay-per-use (pas de minimum)
- Pas besoin d'Inference Endpoint dedicated en Phase 1
- Digital Ocean Basic tier suffit (juste un proxy FastAPI)

### Quand Upgrade?

**Phase 2 (Production)** - Quand >10,000 requêtes/mois:
- Upgrade DO: Basic → Professional ($50/mois)
- Ajouter: HF Inference Endpoint ($200-300/mois)
- **Total**: ~$250-350/mois

---

## Étape 5: Développement (Claude Code)

### 5.1 Structure à Créer

```
llm/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Config env vars
│   ├── models/
│   │   ├── llm_client.py    # Provider abstraction
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   ├── chat.py          # /v1/chat/completions
│   │   ├── models.py        # /v1/models
│   │   └── health.py        # /health
│   └── utils/
│       ├── logger.py
│       └── metrics.py       # Prometheus
├── tests/
│   ├── test_api.py
│   └── test_providers.py
├── Dockerfile
├── requirements.txt
├── .dockerignore
└── README.md
```

### 5.2 API à Implémenter

**POST /v1/chat/completions** (OpenAI-compatible)
```json
{
  "model": "intelia-llama-3.1-8b",
  "messages": [...],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**GET /v1/models** (list models)
**GET /health** (health check)
**GET /metrics** (Prometheus)

### 5.3 Provider Abstraction

Phase 1: HuggingFaceProvider (Serverless API)
Phase 2: vLLMProvider (Self-hosted)

**Même code ai-service, zero changes lors migration** ✅

---

## Étape 6: Tests Développement

### 6.1 Tests Locaux (150-250 requêtes)

**Questions test recommandées** (couvrir use cases):

**Catégorie 1: Questions simples** (50 questions)
- "C'est quoi la coccidiose ?"
- "Comment vacciner des poulets ?"
- "Quelle température pour poussins ?"

**Catégorie 2: Diagnostics** (75 questions)
- "Mes poulets ont diarrhée, que faire ?"
- "Mortalité 5% à J+10, causes possibles ?"
- "Détresse respiratoire + léthargie, diagnostic ?"

**Catégorie 3: Optimisation** (50 questions)
- "Comment réduire indice de conversion ?"
- "Améliorer taux de ponte ?"
- "Optimiser croissance poulets de chair ?"

**Catégorie 4: Multilingual** (50 questions)
- English, Español, Português (test multilingual)

**Catégorie 5: Edge cases** (25 questions)
- Questions hors-scope
- Questions ambiguës
- Questions multi-tours

**Total: 250 requêtes × 500 tokens = ~$0.05** ✅

### 6.2 Validation Qualité

**Métriques à mesurer**:
- Latency (target: <3s Phase 1)
- Quality (human eval 1-5)
- Relevance (répond à la question ?)
- Factuality (pas d'hallucinations ?)

**Comparaison**:
- Llama 3.1 8B base vs GPT-4o (baseline)
- Objectif: Qualité comparable ou meilleure sur domaine aviculture

---

## Étape 7: Fine-tuning (Après validation Phase 1)

### Prérequis

✅ Service llm déployé et fonctionnel
✅ API validée avec 250 requêtes test
✅ Dataset préparé (10K+ conversations PostgreSQL)

### Process

1. **Upload dataset HuggingFace**
```bash
huggingface-cli upload intelia/aviculture-dataset ./data/train.jsonl
```

2. **Fine-tune avec AutoTrain**
```bash
autotrain llm \
  --train \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --data-path intelia/aviculture-dataset \
  --project-name intelia-llama-aviculture
```

**Coût**: ~$5-10 par run

3. **Evaluate**
- Tester modèle fine-tuné vs base
- Human evaluation
- A/B test si qualité supérieure

4. **Deploy**
- Changer `HUGGINGFACE_MODEL` → `intelia/llama-3.1-8b-aviculture`
- Redeploy service
- Monitor qualité

---

## Checklist Setup Complet

### Phase 1 - Infrastructure (Cette semaine)

- [ ] Compte HuggingFace créé
- [ ] Terms Meta Llama acceptés et approuvés
- [ ] API Token HuggingFace généré et sécurisé
- [ ] Service DO `llm` créé (Basic tier $12/mois)
- [ ] Environment variables configurées
- [ ] Health check configuré
- [ ] Test accès Llama validé (script Python)

### Phase 2 - Développement (Semaine 2)

- [ ] Structure FastAPI créée par Claude
- [ ] API OpenAI-compatible implémentée
- [ ] Provider HuggingFace intégré
- [ ] Tests unitaires passent
- [ ] Dockerfile validé
- [ ] Déploiement DO réussi
- [ ] `/health` retourne 200 OK

### Phase 3 - Validation (Semaine 3)

- [ ] 250 requêtes test exécutées (~$0.05)
- [ ] Latency <3s mesurée
- [ ] Qualité comparable GPT-4o validée
- [ ] Pas d'hallucinations majeures
- [ ] Multilingual (FR/EN/ES) validé

### Phase 4 - Integration ai-service (Semaine 4)

- [ ] ai-service appelle llm pour requêtes domain-specific
- [ ] Fallback GPT-4o configuré
- [ ] Monitoring Prometheus actif
- [ ] A/B test 10% trafic → llm
- [ ] User satisfaction ≥ baseline

### Phase 5 - Fine-tuning (Semaine 5-6)

- [ ] Dataset 10K+ conversations extrait PostgreSQL
- [ ] Fine-tuning Llama réussi ($5-10)
- [ ] Modèle fine-tuné déployé
- [ ] Quality improvement mesuré
- [ ] 100% trafic domain → llm fine-tuné

---

## Troubleshooting

### Erreur: "Gated model - Access denied"

**Cause**: Terms Meta Llama pas acceptés ou approbation en attente

**Solution**:
1. Aller sur https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
2. Vérifier statut approbation
3. Attendre email confirmation (1-2h max)
4. Vérifier token a scope "Read" minimum

### Erreur: "Rate limit exceeded"

**Cause**: Trop de requêtes sur HF Serverless (rare en dev)

**Solution**:
1. Attendre quelques minutes
2. Ou upgrade HF Pro ($9/mois) pour rate limit plus haut
3. Ou passer à Inference Endpoint dedicated

### Service DO ne démarre pas

**Cause**: Dockerfile ou requirements.txt invalide

**Solution**:
1. Vérifier logs DO Console
2. Tester build local: `docker build -t llm .`
3. Vérifier PORT=8081 dans env vars
4. Vérifier health check path `/health`

### Latency >10s

**Cause**: Cold start HF Serverless API

**Solution**:
- Première requête toujours lente (cold start)
- Requêtes suivantes <2s
- Si problème persiste: upgrade Inference Endpoint

---

## Support & Resources

**HuggingFace**:
- Docs: https://huggingface.co/docs
- Community: https://discuss.huggingface.co
- Support: support@huggingface.co (si Pro)

**Meta Llama**:
- Model Card: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
- License: https://llama.meta.com/llama3_1/license/

**Digital Ocean**:
- Docs: https://docs.digitalocean.com/products/app-platform/
- Support: Console → Support → New Ticket

---

## Prochaines Étapes Immédiatement

### TOI (Maintenant - 15 min):

1. **Créer compte HuggingFace** → Copier API token
2. **Accepter terms Llama** → Attendre approbation
3. **Créer service DO `llm`** → Basic tier, env vars
4. **Me donner feu vert** → Je développe le code

### MOI (Après ton feu vert - 2h):

1. Créer structure complète `llm/`
2. Implémenter API FastAPI OpenAI-compatible
3. Provider HuggingFace
4. Dockerfile + tests
5. Push + déploiement DO

### NOUS (Après déploiement - 1h):

1. Tests validation 50 requêtes
2. Mesurer latency/qualité
3. Ajustements si besoin

**Timeline totale Phase 1: 1 semaine** ✅

---

**Dis-moi quand tu es prêt à démarrer !** 🚀
