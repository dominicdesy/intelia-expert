# Intelia LLM - Spécifications Techniques

**Version**: 1.0.0
**Date**: 2025-10-27
**Status**: Architecture & Development Plan
**Service Name**: `llm` (not llm-service)

---

## Table des Matières

1. [Vision & Objectifs](#vision--objectifs)
2. [Architecture Globale](#architecture-globale)
3. [Spécifications LLM Service](#spécifications-llm-service)
4. [Migration ai-service](#migration-ai-service)
5. [Plan de Développement](#plan-de-développement)
6. [Infrastructure & Déploiement](#infrastructure--déploiement)
7. [Fine-tuning Strategy](#fine-tuning-strategy)
8. [Monitoring & Observability](#monitoring--observability)
9. [Budget & ROI](#budget--roi)
10. [Roadmap](#roadmap)

---

## Vision & Objectifs

### Positionnement Marché

**Tagline**: *"The AI Expert Trusted by Animal Producers Worldwide"*

**Proposition de valeur**:
> Intelia transforms decades of industry knowledge into specialized AI—delivering expert-level guidance on health, nutrition, and management in seconds.

### Différenciation Compétitive

| Aspect | Intelia | Compétiteurs |
|--------|---------|--------------|
| **LLM** | Llama 3.1 8B fine-tuné aviculture | GPT-4o générique |
| **Knowledge Base** | 50,000+ conversations + 10,000+ docs propriétaires | Documentation publique |
| **Coût** | $0.20/1M tokens | $5/1M tokens (GPT-4o) |
| **Souveraineté** | Self-hosted capable | Dépendance totale OpenAI |
| **IP** | Modèle propriétaire | Zero IP |

### Objectifs Techniques

1. ✅ **Indépendance** - Propriété complète du modèle et des données
2. ✅ **Performance** - Meilleur que GPT-4o sur domaine aviculture
3. ✅ **Coût** - Réduction 25x du coût par requête
4. ✅ **Scalabilité** - Architecture microservices découplée
5. ✅ **Migration** - Path clair API → Self-hosted

---

## Architecture Globale

### Schéma d'Architecture - 3 Services

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                       │
│                    https://expert.intelia.com                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                     AI-SERVICE (Orchestrator)                    │
│  • RAG (Weaviate search)                                        │
│  • Multi-model routing (Llama / GPT-4o / Claude)               │
│  • Conversation management                                      │
│  • Proactive follow-ups                                         │
│  • Business logic (quotas, permissions)                         │
│  • WhatsApp/Widget webhooks                                     │
└────┬────────────────────┬─────────────────────┬────────────────┘
     │                    │                     │
     ↓                    ↓                     ↓
┌────────────┐   ┌──────────────────┐   ┌─────────────────┐
│  Weaviate  │   │  LLM-SERVICE     │   │  External APIs  │
│  (Vector   │   │  (NEW)           │   │  • OpenAI       │
│   Store)   │   │                  │   │  • Anthropic    │
└────────────┘   │  • Llama 3.1 8B  │   └─────────────────┘
                 │  • Fine-tuned    │
                 │  • vLLM server   │
                 │  • OpenAI API    │
                 └──────────────────┘
```

### Services & Responsabilités

#### **1. ai-service** (Existant - Orchestrateur)
- **Port**: 8080
- **Rôle**: Chef d'orchestre RAG + Multi-LLM
- **Technologies**: Python, FastAPI, httpx
- **Responsabilités**:
  - Recevoir requêtes chat (frontend, WhatsApp, Widget)
  - Rechercher contexte dans Weaviate (RAG)
  - Router vers le bon LLM (Llama vs GPT-4o vs Claude)
  - Gérer historique conversations (PostgreSQL)
  - Appliquer business rules (quotas, permissions)
  - Déclencher proactive follow-ups
  - Logging & analytics
- **Reste inchangé**: ✅ (sauf ajout appel llm-service)

#### **2. llm** (NOUVEAU - Inference LLM)
- **Port**: 8081
- **Rôle**: Serveur inference Llama 3.1 8B fine-tuné
- **Technologies**: Python, FastAPI, vLLM (plus tard), HuggingFace
- **Responsabilités**:
  - Servir le modèle Llama 3.1 8B fine-tuné
  - API OpenAI-compatible (`/v1/chat/completions`)
  - Health check & metrics Prometheus
  - **AUCUNE logique métier** (pure inference)
- **Phase 1**: HuggingFace Inference API (proxy)
- **Phase 2**: Self-hosted avec vLLM

#### **3. prediction-service** (Futur - ML Prédictif)
- **Port**: 8082
- **Rôle**: Machine Learning prédictif (non-génératif)
- **Technologies**: Python, FastAPI, scikit-learn, XGBoost
- **Responsabilités**:
  - Prédictions mortalité, ponte, maladies
  - Time-series forecasting
  - Anomaly detection IoT
  - Analytics avancés
- **Data source**: PostgreSQL (pas Weaviate)
- **Status**: Futur (pas Phase 1)

---

## Spécifications LLM Service

### Architecture Technique

```
llm-service/
├── app/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Configuration (env vars)
│   ├── models/
│   │   ├── llm_client.py          # Abstraction provider (HF, vLLM)
│   │   └── schemas.py             # Pydantic models (OpenAI-compatible)
│   ├── routers/
│   │   ├── chat.py                # /v1/chat/completions
│   │   ├── models.py              # /v1/models (list available models)
│   │   └── health.py              # /health, /metrics
│   └── utils/
│       ├── logger.py              # Logging structuré
│       └── metrics.py             # Prometheus metrics
├── fine_tuning/
│   ├── dataset_builder.py         # Extraction conversations PostgreSQL
│   ├── train.py                   # Script fine-tuning (HF AutoTrain)
│   └── evaluate.py                # Évaluation modèle vs baseline
├── tests/
│   ├── test_api.py                # Tests API
│   └── test_inference.py          # Tests qualité réponses
├── Dockerfile
├── requirements.txt
└── README.md
```

### API Endpoints (OpenAI-Compatible)

#### **POST /v1/chat/completions**
```json
// Request
{
  "model": "intelia-llama-3.1-8b-aviculture",
  "messages": [
    {"role": "system", "content": "Context from Weaviate..."},
    {"role": "user", "content": "Comment réduire mortalité poulets ?"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000,
  "stream": false
}

// Response
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "intelia-llama-3.1-8b-aviculture",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Pour réduire la mortalité..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 320,
    "total_tokens": 470
  }
}
```

#### **GET /v1/models**
```json
{
  "object": "list",
  "data": [
    {
      "id": "intelia-llama-3.1-8b-aviculture",
      "object": "model",
      "created": 1234567890,
      "owned_by": "intelia"
    }
  ]
}
```

#### **GET /health**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "provider": "huggingface",
  "version": "1.0.0"
}
```

#### **GET /metrics** (Prometheus)
```
# HELP llm_requests_total Total inference requests
# TYPE llm_requests_total counter
llm_requests_total{model="intelia-llama-3.1-8b",status="success"} 1523

# HELP llm_inference_duration_seconds Inference latency
# TYPE llm_inference_duration_seconds histogram
llm_inference_duration_seconds_bucket{le="0.5"} 892
llm_inference_duration_seconds_bucket{le="1.0"} 1450
```

### Configuration (Environment Variables)

```bash
# llm-service/.env

# Phase 1: HuggingFace API
LLM_PROVIDER=huggingface
HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxx
HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct

# Phase 2: Self-hosted vLLM
# LLM_PROVIDER=vllm
# VLLM_URL=http://localhost:8000
# MODEL_PATH=/models/intelia-llama-3.1-8b-aviculture

# Server
PORT=8081
LOG_LEVEL=INFO

# Prometheus
ENABLE_METRICS=true
```

### Provider Abstraction Layer

```python
# app/models/llm_client.py

from typing import Protocol, List, Dict
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        pass

class HuggingFaceProvider(LLMClient):
    def __init__(self, api_key: str, model: str):
        from huggingface_hub import InferenceClient
        self.client = InferenceClient(token=api_key)
        self.model = model

    async def generate(self, messages, temperature=0.7, max_tokens=2000):
        response = await self.client.chat_completion(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

class vLLMProvider(LLMClient):
    def __init__(self, base_url: str):
        import openai
        self.client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key="dummy"  # vLLM doesn't require key
        )

    async def generate(self, messages, temperature=0.7, max_tokens=2000):
        response = await self.client.chat.completions.create(
            model="intelia-llama-3.1-8b-aviculture",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

# Factory
def get_llm_client(provider: str, **kwargs) -> LLMClient:
    if provider == "huggingface":
        return HuggingFaceProvider(
            api_key=kwargs["api_key"],
            model=kwargs["model"]
        )
    elif provider == "vllm":
        return vLLMProvider(base_url=kwargs["base_url"])
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

---

## Migration ai-service

### Modifications Minimales

#### 1. **Ajouter llm-service comme provider**

```python
# ai-service/app/core/llm_router.py

class LLMRouter:
    def __init__(self):
        self.llm_service_url = os.getenv(
            "LLM_SERVICE_URL",
            "http://llm-service:8081"
        )
        self.openai_client = openai.AsyncOpenAI()
        self.anthropic_client = anthropic.AsyncAnthropic()

    async def route_and_generate(
        self,
        message: str,
        context: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Décide quel LLM utiliser et génère la réponse
        """
        # Déterminer le meilleur modèle
        if self._requires_complex_reasoning(message):
            # Questions complexes → GPT-4o
            model = "gpt-4o"
            return await self._call_openai(message, context, conversation_history)

        elif self._is_domain_specific(message):
            # Aviculture domain → Llama fine-tuné
            model = "intelia-llama"
            return await self._call_llm_service(message, context, conversation_history)

        else:
            # Default → Claude 3.5 Sonnet
            model = "claude-3.5-sonnet"
            return await self._call_anthropic(message, context, conversation_history)

    async def _call_llm_service(
        self,
        message: str,
        context: str,
        history: List[Dict]
    ) -> str:
        """
        Appel au nouveau llm-service (Llama fine-tuné)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.llm_service_url}/v1/chat/completions",
                json={
                    "model": "intelia-llama-3.1-8b-aviculture",
                    "messages": [
                        {"role": "system", "content": f"Context: {context}"},
                        *history,
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=30.0
            )
            result = response.json()
            return result["choices"][0]["message"]["content"]

    def _is_domain_specific(self, message: str) -> bool:
        """
        Détecte si la question est spécifique aviculture
        """
        domain_keywords = [
            "poulet", "poule", "aviculture", "ponte", "mortalité",
            "aliment", "biosécurité", "vaccination", "coccidiose",
            "Newcastle", "broiler", "layer", "poultry"
        ]
        return any(kw in message.lower() for kw in domain_keywords)
```

#### 2. **Retirer system prompts longs (après fine-tuning)**

**Avant** (avec GPT-4o):
```python
SYSTEM_PROMPT = """
Tu es un expert vétérinaire spécialisé en aviculture avec 20 ans d'expérience.
Tu maîtrises parfaitement les poulets de chair, les pondeuses, la biosécurité...
Toujours répondre avec des protocoles vétérinaires validés...
[500+ tokens de instructions]
"""
```

**Après** (avec Llama fine-tuné):
```python
# Le modèle "sait déjà" qu'il est expert aviculture
# Pas besoin de system prompt
# Juste passer le contexte RAG
context = f"Relevant documents: {weaviate_results}"
```

#### 3. **Environment Variables**

```bash
# ai-service/.env (ajout)

# LLM Service (nouveau)
LLM_SERVICE_URL=http://llm-service:8081

# Routing preferences
USE_INTELIA_LLM_FOR_DOMAIN=true
FALLBACK_TO_GPT4=true
```

---

## Plan de Développement

### Phase 1: Setup Infrastructure (Semaine 1-2)

**Objectif**: llm-service fonctionnel avec HuggingFace API

#### Tâches:
- [ ] Créer repository `llm-service/` avec structure FastAPI
- [ ] Implémenter API OpenAI-compatible (`/v1/chat/completions`)
- [ ] Provider abstraction layer (HuggingFace + vLLM)
- [ ] Configuration HuggingFace Inference API
- [ ] Health check & Prometheus metrics
- [ ] Docker image & Dockerfile
- [ ] Tests unitaires API
- [ ] Documentation API (OpenAPI/Swagger)

#### Déploiement:
- Digital Ocean App Platform - nouveau service `llm-service`
- Variables d'environnement: `HUGGINGFACE_API_KEY`
- Internal URL: `http://llm-service:8081`

#### Validation:
```bash
# Test local
curl -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Comment réduire mortalité poulets ?"}]
  }'

# Should return valid OpenAI-format response
```

---

### Phase 2: Dataset Preparation (Semaine 2-3)

**Objectif**: Créer dataset fine-tuning de qualité

#### Sources de Données:

1. **Conversations PostgreSQL** (Priorité 1)
   - Extraire `conversations` table
   - Filtrer conversations de qualité (thumbs up, >3 échanges)
   - Format: JSONL avec messages user/assistant
   - **Target**: 10,000+ conversations

2. **Documents Weaviate** (Priorité 2)
   - Synthétiser Q&A depuis documents techniques
   - Utiliser GPT-4o pour générer paires question/réponse
   - **Target**: 5,000+ synthetic examples

3. **Expert Annotations** (Priorité 3)
   - Demander aux experts d'annoter cas difficiles
   - Corrections réponses incorrectes
   - **Target**: 500+ high-quality examples

#### Dataset Structure:

```jsonl
{"messages": [{"role": "system", "content": "Tu es un expert en aviculture."}, {"role": "user", "content": "Mes poulets ont une mortalité de 3% à J+10, que faire ?"}, {"role": "assistant", "content": "Une mortalité de 3% à J+10 est légèrement élevée. Voici les actions prioritaires:\n\n1. **Vérifier l'ambiance**: Température, humidité, ventilation\n2. **Observer les symptômes**: Détresse respiratoire, diarrhée, comportement léthargique ?\n3. **Contrôler la qualité de l'eau**: Analyse bactériologique\n4. **Examiner l'aliment**: Qualité, distribution, accès\n5. **Autopsie**: Faire autopsier 3-5 sujets pour diagnostic précis\n\nLes causes fréquentes à cet âge: infections respiratoires (bronchite infectieuse), problèmes de ventilation, qualité de l'eau. Un diagnostic vétérinaire est recommandé si la mortalité persiste."}]}
{"messages": [{"role": "user", "content": "C'est quoi la coccidiose ?"}, {"role": "assistant", "content": "La coccidiose est une maladie parasitaire intestinale très fréquente en aviculture, causée par des protozoaires du genre *Eimeria*.\n\n**Symptômes**:\n- Diarrhée (parfois sanguinolente)\n- Plumage ébouriffé\n- Perte d'appétit\n- Baisse de croissance\n- Mortalité (si non traité)\n\n**Transmission**: Les oocystes (œufs du parasite) sont présents dans les fientes et contaminent la litière. Les poulets s'infectent en picorant.\n\n**Prévention**:\n- Anticoccidiens dans l'aliment\n- Bonne gestion de la litière (éviter humidité)\n- Hygiène stricte entre bandes\n- Vaccination (selon programme)\n\n**Traitement**: Anticoccidiens curatifs (sulfamides, amprolium) + réhydratation.\n\nC'est une maladie très coûteuse si mal contrôlée, d'où l'importance de la prévention."}]}
```

#### Script d'Extraction:

```python
# llm-service/fine_tuning/dataset_builder.py

import psycopg2
import json
from typing import List, Dict

def extract_conversations_from_db(min_quality: float = 4.0) -> List[Dict]:
    """
    Extrait conversations de qualité depuis PostgreSQL
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()

    query = """
    SELECT
        c.conversation_id,
        c.messages,
        c.rating,
        c.created_at
    FROM conversations c
    WHERE
        c.rating >= %s
        AND jsonb_array_length(c.messages) >= 3
        AND c.language IN ('fr', 'en', 'es', 'pt')
    ORDER BY c.created_at DESC
    LIMIT 50000
    """

    cursor.execute(query, (min_quality,))
    results = cursor.fetchall()

    dataset = []
    for conv_id, messages, rating, created_at in results:
        # Convertir format Intelia → OpenAI format
        formatted_messages = []
        for msg in messages:
            if msg["role"] in ["user", "assistant"]:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        if len(formatted_messages) >= 2:
            dataset.append({
                "messages": formatted_messages,
                "metadata": {
                    "conversation_id": conv_id,
                    "rating": rating,
                    "source": "intelia_production"
                }
            })

    cursor.close()
    conn.close()

    return dataset

def save_dataset(dataset: List[Dict], output_path: str):
    """
    Sauvegarde au format JSONL pour fine-tuning
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    print("Extracting conversations...")
    dataset = extract_conversations_from_db(min_quality=4.0)
    print(f"Extracted {len(dataset)} conversations")

    # Split train/validation
    train_size = int(len(dataset) * 0.9)
    train_data = dataset[:train_size]
    val_data = dataset[train_size:]

    save_dataset(train_data, "data/train.jsonl")
    save_dataset(val_data, "data/validation.jsonl")

    print(f"Train: {len(train_data)}, Validation: {len(val_data)}")
```

---

### Phase 3: Fine-tuning (Semaine 3-4)

**Objectif**: Llama 3.1 8B fine-tuné sur aviculture

#### Option A: HuggingFace AutoTrain (Recommandé Phase 1)

```bash
# Install AutoTrain
pip install autotrain-advanced

# Upload dataset to HuggingFace
huggingface-cli login
huggingface-cli upload intelia/aviculture-dataset ./data/train.jsonl

# Launch fine-tuning
autotrain llm \
  --train \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --data-path intelia/aviculture-dataset \
  --text-column messages \
  --lr 2e-5 \
  --batch-size 4 \
  --epochs 3 \
  --trainer sft \
  --peft \
  --quantization int4 \
  --project-name intelia-llama-3.1-8b-aviculture
```

**Coût**: ~$5-10 pour training complet

#### Option B: Custom Training Script

```python
# llm-service/fine_tuning/train.py

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import torch

def train_llama_aviculture():
    # Load model
    model_name = "meta-llama/Llama-3.1-8B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True  # QLoRA
    )

    # LoRA config
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)

    # Load dataset
    dataset = load_dataset("json", data_files={
        "train": "data/train.jsonl",
        "validation": "data/validation.jsonl"
    })

    # Training arguments
    training_args = TrainingArguments(
        output_dir="./models/intelia-llama-3.1-8b-aviculture",
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-5,
        fp16=True,
        logging_steps=10,
        evaluation_strategy="steps",
        eval_steps=100,
        save_steps=500,
        save_total_limit=3,
        load_best_model_at_end=True,
        report_to="wandb",  # Weights & Biases tracking
        run_name="intelia-llama-aviculture-v1"
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer
    )

    # Train
    trainer.train()

    # Save
    trainer.save_model("./models/intelia-llama-3.1-8b-aviculture-final")
    tokenizer.save_pretrained("./models/intelia-llama-3.1-8b-aviculture-final")

if __name__ == "__main__":
    train_llama_aviculture()
```

#### Evaluation

```python
# llm-service/fine_tuning/evaluate.py

import json
from transformers import pipeline

def evaluate_model(model_path: str, test_questions: List[str]):
    """
    Compare fine-tuned vs base model
    """
    # Load models
    base_model = pipeline("text-generation", model="meta-llama/Llama-3.1-8B-Instruct")
    finetuned_model = pipeline("text-generation", model=model_path)

    results = []

    for question in test_questions:
        base_answer = base_model(question, max_new_tokens=200)[0]["generated_text"]
        finetuned_answer = finetuned_model(question, max_new_tokens=200)[0]["generated_text"]

        results.append({
            "question": question,
            "base_model": base_answer,
            "finetuned_model": finetuned_answer
        })

    return results

# Test questions
test_questions = [
    "Comment réduire la mortalité chez les poulets de chair ?",
    "Quels sont les symptômes de la coccidiose ?",
    "Quel programme de vaccination recommandez-vous pour les pondeuses ?",
    "Comment améliorer l'indice de conversion alimentaire ?"
]

results = evaluate_model("./models/intelia-llama-3.1-8b-aviculture-final", test_questions)

# Human evaluation needed
for r in results:
    print(f"\nQuestion: {r['question']}")
    print(f"Base: {r['base_model'][:200]}...")
    print(f"Fine-tuned: {r['finetuned_model'][:200]}...")
    print("---")
```

---

### Phase 4: Integration ai-service (Semaine 4-5)

**Objectif**: ai-service utilise llm-service en production

#### Modifications:

1. **Ajouter LLM Router** (voir section Migration)
2. **Configurer routing logic**
3. **A/B Testing**: 10% trafic → llm-service, 90% → GPT-4o
4. **Monitoring**: Comparer qualité/latence/coût

#### Validation:

```python
# Test A/B
import random

async def handle_chat_with_ab_test(message: str, user_id: str):
    # 10% vers llm-service
    if random.random() < 0.1:
        model = "intelia-llama"
        response = await llm_router.call_llm_service(message)
        log_experiment(user_id, model="intelia-llama", response=response)
    else:
        model = "gpt-4o"
        response = await llm_router.call_openai(message)
        log_experiment(user_id, model="gpt-4o", response=response)

    return response
```

#### Metrics à Surveiller:

| Metric | Target | Alert if |
|--------|--------|----------|
| **Latency** | <2s p95 | >3s |
| **Error rate** | <1% | >5% |
| **User satisfaction** | >4.5/5 | <4.0 |
| **Cost per request** | <$0.001 | >$0.01 |

---

### Phase 5: Self-hosted Migration (Semaine 6-8)

**Objectif**: Migrer de HuggingFace API → vLLM self-hosted

#### Infrastructure:

**Option A: RunPod GPU** (Recommandé)
- GPU: 1x RTX 4090 (24GB VRAM)
- Coût: $0.34/heure = $245/mois
- vLLM pre-installed

**Option B: Digital Ocean GPU Droplet**
- GPU Droplet (plus cher, mais integrated)
- Coût: $800-1200/mois

#### Setup vLLM:

```bash
# On GPU server (RunPod)

# Install vLLM
pip install vllm

# Download fine-tuned model from HuggingFace
huggingface-cli download intelia/llama-3.1-8b-aviculture \
  --local-dir /models/intelia-llama

# Start vLLM server (OpenAI-compatible API)
python -m vllm.entrypoints.openai.api_server \
  --model /models/intelia-llama \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype float16 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9
```

#### Update llm-service Config:

```bash
# Change provider
LLM_PROVIDER=vllm
VLLM_URL=http://<runpod-ip>:8000
```

**Zero code change needed** - provider abstraction handles it! ✅

---

## Infrastructure & Déploiement

### Digital Ocean App Platform

#### Service: `llm-service`

```yaml
# .do/app.yaml (ajout)

- name: llm-service
  type: service

  github:
    repo: intelia-expert/llm-service
    branch: main
    deploy_on_push: true

  source_dir: /

  dockerfile_path: Dockerfile

  instance_count: 1
  instance_size_slug: professional-m  # 4GB RAM, 2 vCPU

  http_port: 8081

  internal_ports:
    - 8081

  routes:
    - path: /

  envs:
    - key: LLM_PROVIDER
      value: "huggingface"

    - key: HUGGINGFACE_API_KEY
      value: ${HUGGINGFACE_API_KEY}  # Secret
      type: SECRET

    - key: HUGGINGFACE_MODEL
      value: "meta-llama/Llama-3.1-8B-Instruct"

    - key: PORT
      value: "8081"

    - key: LOG_LEVEL
      value: "INFO"

    - key: ENABLE_METRICS
      value: "true"

  health_check:
    http_path: /health
    initial_delay_seconds: 30
    period_seconds: 10
    timeout_seconds: 5
    success_threshold: 1
    failure_threshold: 3
```

#### Service Internal URLs:

```
ai-service:       http://ai-service:8080
llm-service:      http://llm-service:8081  (NEW)
frontend:         https://expert.intelia.com
```

#### Networking:

- **ai-service** peut appeler **llm-service** via réseau interne DO (pas d'exposition publique)
- **llm-service** ne reçoit que des appels depuis ai-service (pas depuis internet)

---

### Dockerfile llm-service

```dockerfile
# llm-service/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8081/health')"

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
```

### requirements.txt

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
huggingface-hub==0.20.1
prometheus-client==0.19.0
python-dotenv==1.0.0

# Fine-tuning (dev only)
transformers==4.36.2
datasets==2.16.1
peft==0.7.1
bitsandbytes==0.41.3
accelerate==0.25.0
```

---

## Fine-tuning Strategy

### Data Collection Pipeline

```
PostgreSQL conversations
         ↓
    Filter quality
    (rating ≥ 4.0)
         ↓
    Extract & format
      (JSONL)
         ↓
   Upload HuggingFace
         ↓
    Fine-tune Llama
         ↓
   Evaluate vs baseline
         ↓
   Deploy to production
         ↓
    Collect feedback
         ↓
  (Loop back to top)
```

### Continuous Improvement

**Tous les 3 mois**:
1. Extraire nouvelles conversations (N+10,000)
2. Re-fine-tuner avec dataset augmenté
3. A/B test nouvelle version vs actuelle
4. Déployer si supérieur

**Data Flywheel**: Plus d'utilisateurs → Plus de données → Meilleur modèle → Meilleur produit → Plus d'utilisateurs ✅

### Quality Metrics

| Metric | Measurement | Target |
|--------|-------------|--------|
| **Accuracy** | Human eval (1-5 scale) | >4.5/5 |
| **Relevance** | RAG context usage | >90% |
| **Factuality** | No hallucinations | >95% |
| **Language** | Multilingual quality | FR/EN/ES >4.5 |
| **Speed** | p95 latency | <2s |

---

## Monitoring & Observability

### Stack Technique

1. **Prometheus** (Metrics) - Déjà en place ✅
2. **Grafana** (Dashboards) - Déjà en place ✅
3. **Langfuse** (LLM Tracing) - NOUVEAU
4. **Sentry** (Error tracking) - Existant ✅

### Métriques LLM-Specific

```python
# llm-service/app/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Requests
llm_requests_total = Counter(
    'llm_requests_total',
    'Total inference requests',
    ['model', 'status']
)

# Latency
llm_inference_duration = Histogram(
    'llm_inference_duration_seconds',
    'Inference latency',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Tokens
llm_tokens_generated = Counter(
    'llm_tokens_generated_total',
    'Total tokens generated',
    ['model']
)

# Model health
llm_model_loaded = Gauge(
    'llm_model_loaded',
    'Is model loaded in memory',
    ['model']
)

# Usage
def track_inference(model: str, duration: float, tokens: int, status: str):
    llm_requests_total.labels(model=model, status=status).inc()
    llm_inference_duration.labels(model=model).observe(duration)
    llm_tokens_generated.labels(model=model).inc(tokens)
```

### Grafana Dashboard

**Panel 1: Requests/sec**
```promql
rate(llm_requests_total[5m])
```

**Panel 2: Latency p95**
```promql
histogram_quantile(0.95, rate(llm_inference_duration_seconds_bucket[5m]))
```

**Panel 3: Error Rate**
```promql
rate(llm_requests_total{status="error"}[5m]) / rate(llm_requests_total[5m])
```

**Panel 4: Cost Estimation**
```promql
rate(llm_tokens_generated_total[1h]) * 0.0000002  # $0.20/1M tokens
```

### Langfuse Integration

```python
# LLM observability
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY")
)

async def generate_with_tracing(messages: List[Dict]):
    trace = langfuse.trace(name="llm_generation")

    generation = trace.generation(
        name="intelia-llama",
        model="intelia-llama-3.1-8b-aviculture",
        input=messages
    )

    response = await llm_client.generate(messages)

    generation.end(output=response)

    return response
```

**Langfuse dashboard** montre:
- Latence par requête
- Coût par conversation
- Quality scores (si feedback user)
- Traces complètes RAG + LLM

---

## Budget & ROI

### Coûts Phase 1 - Développement (Budget: <$150/mois)

**Approche optimisée budget**:

| Item | Coût Mensuel | Notes |
|------|--------------|-------|
| **HuggingFace Inference API** (Serverless) | $0-50 | Pay-per-use, 150-250 requêtes dev = ~$0.05 |
| **Fine-tuning runs** | $5-10 | 2-3 runs avec AutoTrain |
| **Digital Ocean llm** (Basic) | $12 | Basic tier suffisant (proxy API seulement) |
| **HuggingFace Hub Storage** (private) | $9 | Modèle fine-tuné privé |
| **Langfuse** (monitoring) | $0 | Free tier |
| **Total Phase 1** | **~$26-81/mois** | ✅ Sous budget $150 |

**Phase développement (150-250 requêtes test)**: ~$0.05 (négligeable)

### Coûts Phase 2 - Production (Après validation)

| Item | Coût Mensuel | Notes |
|------|--------------|-------|
| **HuggingFace Inference Endpoint** | $200-300 | Dedicated, quand trafic augmente |
| **Digital Ocean llm** | $50 | Professional tier |
| **Total Phase 2** | **$250-350/mois** | Quand >10K requêtes/mois |

### Coûts Phase 3+ (Mois 7-12 - Self-hosted)

| Item | Coût Mensuel | Coût 6 Mois |
|------|--------------|-------------|
| **RunPod GPU** (RTX 4090) | $245 | $1,470 |
| **Digital Ocean llm-service** (proxy) | $50 | $300 |
| **Fine-tuning** | $10 | $60 |
| **Total** | **$305/mois** | **$1,830** |

### ROI vs GPT-4o Only

**Scénario**: 1M conversations/an

| Approach | Coût Annuel | Économie |
|----------|-------------|----------|
| **GPT-4o uniquement** | $60,000 | - |
| **Llama 3.1 8B (HF API)** | $4,000 | $56,000 (93%) |
| **Llama 3.1 8B (self-hosted)** | $3,000 | $57,000 (95%) |

**Break-even**: Après 100,000 conversations (~Mois 3-4)

---

## Roadmap

### Q1 2025 - Foundation

**Mois 1-2**: Infrastructure
- ✅ llm-service setup (FastAPI + HuggingFace)
- ✅ OpenAI-compatible API
- ✅ Déploiement Digital Ocean
- ✅ Monitoring Prometheus

**Mois 3**: Fine-tuning v1
- ✅ Dataset extraction (10K+ conversations)
- ✅ Fine-tune Llama 3.1 8B
- ✅ Evaluation vs baseline

### Q2 2025 - Production

**Mois 4-5**: Integration
- ✅ ai-service → llm-service integration
- ✅ A/B testing (10% trafic)
- ✅ Quality validation

**Mois 6**: Scale
- ✅ 100% trafic domain-specific → Llama
- ✅ GPT-4o fallback pour edge cases
- ✅ Cost reduction validation

### Q3 2025 - Optimization

**Mois 7-8**: Self-hosted
- ✅ Migration RunPod GPU
- ✅ vLLM optimization
- ✅ Latency <1s p95

**Mois 9**: Multi-species
- ✅ Fine-tune datasets porc, aquaculture
- ✅ Model routing par espèce

### Q4 2025 - Advanced

**Mois 10-11**: Multimodal
- ✅ Llama 3.2 Vision fine-tuning
- ✅ Image analysis (lésions, comportement)

**Mois 12**: API Externe
- ✅ Public API pour B2B partners
- ✅ API documentation & SDK
- ✅ Pricing tiers

---

## Success Criteria

### Phase 1 (HuggingFace API)
✅ llm-service répond <2s p95
✅ API OpenAI-compatible validée
✅ Coût <$0.001 par requête

### Phase 2 (Fine-tuning)
✅ Modèle fine-tuné meilleur que base Llama (human eval >4.5)
✅ Dataset 10,000+ conversations
✅ Fine-tuning reproductible (CI/CD)

### Phase 3 (Production)
✅ 80%+ trafic domain-specific via Llama
✅ User satisfaction ≥ GPT-4o baseline
✅ Cost reduction >90% vs GPT-4o only

### Phase 4 (Self-hosted)
✅ Migration zéro downtime
✅ Latency <1s p95
✅ Cost <$300/mois

---

## Next Steps - Immediate Actions

### Action 1: Créer Service Digital Ocean

**Tu dois faire** (dans DO Console):
1. Apps → Create App → From GitHub
2. Repository: `intelia-expert` (ou créer nouveau repo `llm-service`)
3. Source Directory: `/llm-service`
4. Service Name: `llm-service`
5. Instance Size: Professional-M (4GB RAM)
6. Environment Variables:
   - `LLM_PROVIDER=huggingface`
   - `HUGGINGFACE_API_KEY=<secret>`
   - `HUGGINGFACE_MODEL=meta-llama/Llama-3.1-8B-Instruct`
   - `PORT=8081`

### Action 2: Je Développe llm-service

**Je vais créer**:
- Structure FastAPI complète
- API OpenAI-compatible
- Provider abstraction (HuggingFace)
- Dockerfile
- Tests

### Action 3: Dataset Extraction

**Je vais créer**:
- Script extraction PostgreSQL
- Format JSONL pour fine-tuning
- Validation dataset quality

---

## Questions à Résoudre

1. **HuggingFace API Key**: Tu as déjà un compte HuggingFace ?
2. **Meta Llama Access**: Tu as accepté les terms Meta Llama sur HF ? (requis)
3. **Budget approval**: $365/mois Phase 1 OK ?
4. **Timeline**: On vise mise en prod quand ? (suggestion: 6 semaines)

---

## Annexes

### A. Glossary

- **LLM**: Large Language Model
- **RAG**: Retrieval-Augmented Generation
- **Fine-tuning**: Entraînement spécialisé d'un modèle pré-entraîné
- **LoRA**: Low-Rank Adaptation (technique fine-tuning efficace)
- **vLLM**: Serveur inference LLM optimisé
- **Inference**: Génération de réponses par le modèle

### B. References

- [Llama 3.1 Model Card](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
- [HuggingFace Inference API Docs](https://huggingface.co/docs/api-inference/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)

### C. Support

**Questions techniques**: Contact dev team
**Infrastructure**: Digital Ocean support
**HuggingFace**: Community forum ou Pro support

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-27
**Status**: Ready for Development ✅
