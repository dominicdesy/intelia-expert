# Analyse des Coûts - Intelia Expert

## 📊 Services Externes Utilisés (Payants)

### 1. OpenAI API
- **Embeddings**: `text-embedding-ada-002` (défaut) ou `text-embedding-3-small/large`
- **Génération de texte**: `gpt-4o` (réponses principales)
- **OOD Detection**: `gpt-4o-mini` (détection hors domaine)

### 2. Anthropic Claude API
- **Vision Analysis**: `claude-3-5-sonnet-20241022` (analyse d'images médicales)

### 3. Cohere API
- **Reranking**: `rerank-multilingual-v3.0` (réorganisation des résultats)

### 4. Weaviate Cloud
- **Vector Database**: Stockage et recherche vectorielle (Cloud WCS)

### 5. Redis (Optionnel)
- **Cache**: DigitalOcean Managed Redis ou autre

---

## 💰 Tarifs des Services (Janvier 2025)

### OpenAI Pricing

**Embeddings** (`text-embedding-ada-002`):
- $0.0001 / 1K tokens
- Dimensions: 1536

**Embeddings** (`text-embedding-3-small`):
- $0.00002 / 1K tokens (5x moins cher)
- Dimensions: 512/1536 (configurable)

**GPT-4o** (génération):
- Input: $2.50 / 1M tokens
- Output: $10.00 / 1M tokens

**GPT-4o-mini** (OOD detection):
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens

### Anthropic Claude Pricing

**Claude 3.5 Sonnet** (Vision):
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens
- Images: Coût basé sur taille (voir tableau ci-dessous)

| Image Resolution | Tokens | Cost per Image |
|-----------------|--------|----------------|
| 200x200 | 100 | $0.0003 |
| 400x400 | 400 | $0.0012 |
| 800x800 | 1,600 | $0.0048 |
| 1024x1024 | 2,624 | $0.0079 |
| 2048x2048 | 10,496 | $0.0315 |

**Note**: Pour images vétérinaires (photos smartphone ~1024x1024), estimation: **2,624 tokens/image**

### Cohere Pricing

**Rerank Multilingual v3.0**:
- $1.00 / 1,000 searches
- Limite: 3,000 documents maximum par search
- **Note**: 1 search = 1 appel API (peu importe le nombre de documents reranked)

### Weaviate Cloud Pricing

**Sandbox** (Free Tier):
- Gratuit
- Limite: 10M vecteurs
- 1 cluster

**Standard Plan**:
- ~$25-50/mois selon l'usage
- Scaling automatique

---

## 🔍 Scénario 1: Question Simple

**Exemple**: "Quel est le poids cible Ross 308 à 35 jours?"

### Flux de traitement:

1. **OOD Detection** (gpt-4o-mini)
   - Input: ~150 tokens (query + prompt)
   - Output: ~50 tokens (réponse JSON)
   - **Coût**: ($0.15 × 150 + $0.60 × 50) / 1,000,000 = **$0.00005**

2. **Embedding de la query** (text-embedding-ada-002)
   - Tokens: ~20 tokens
   - **Coût**: $0.0001 / 1,000 × 0.02 = **$0.000002**

3. **Recherche Weaviate**
   - Recherche vectorielle + BM25 hybride
   - **Coût**: $0 (inclus dans abonnement Weaviate)

4. **Cohere Reranking**
   - 1 search avec ~50 documents
   - **Coût**: $1.00 / 1,000 = **$0.001**

5. **Génération de réponse** (gpt-4o)
   - Input: ~1,500 tokens (system prompt + contexte + 5 documents)
   - Output: ~50 tokens (réponse courte)
   - **Coût**: ($2.50 × 1,500 + $10.00 × 50) / 1,000,000 = **$0.00425**

### Coût Total Scénario 1: **$0.00530** (~€0.0048)

---

## 🔍 Scénario 2: Question Complexe

**Exemple**: "Comment optimiser le FCR pour Ross 308 en climat tropical avec problèmes de ventilation?"

### Flux de traitement:

1. **OOD Detection** (gpt-4o-mini)
   - Input: ~200 tokens (query plus longue)
   - Output: ~80 tokens
   - **Coût**: ($0.15 × 200 + $0.60 × 80) / 1,000,000 = **$0.00008**

2. **Embedding de la query** (text-embedding-ada-002)
   - Tokens: ~40 tokens
   - **Coût**: $0.0001 / 1,000 × 0.04 = **$0.000004**

3. **Recherche Weaviate**
   - Recherche vectorielle + BM25 hybride
   - Peut nécessiter 2 rounds de recherche (intent detection + retrieval)
   - **Coût**: $0 (inclus)

4. **Cohere Reranking**
   - 1 search avec ~135 documents (RAG_SIMILARITY_TOP_K=135)
   - **Coût**: $1.00 / 1,000 = **$0.001**

5. **Génération de réponse** (gpt-4o)
   - Input: ~3,500 tokens (system prompt + contexte RAG + 10 documents + conversation context)
   - Output: ~400 tokens (réponse détaillée avec recommandations)
   - **Coût**: ($2.50 × 3,500 + $10.00 × 400) / 1,000,000 = **$0.01275**

6. **Possible traduction** (si langue non-anglaise, désactivé actuellement)
   - N/A (réponse générée directement dans la langue cible)

### Coût Total Scénario 2: **$0.01383** (~€0.0126)

---

## 📸 Scénario 3: Analyse de 2 Images Médicales

**Exemple**: "Analysez ces 2 photos d'organes de poulet et donnez un diagnostic"

### Flux de traitement:

1. **OOD Detection** (gpt-4o-mini)
   - Input: ~150 tokens
   - Output: ~50 tokens
   - **Coût**: **$0.00005**

2. **Retrieval RAG optionnel** (si use_rag_context=True)
   - Embedding: 20 tokens
   - Cohere reranking: 1 search
   - **Coût Embedding**: **$0.000002**
   - **Coût Reranking**: **$0.001**

3. **Claude Vision Analysis** (claude-3-5-sonnet-20241022)
   - **2 images** (1024x1024 chacune): 2 × 2,624 = **5,248 tokens**
   - **Input text**: ~800 tokens (user query + system prompt + RAG context optionnel)
   - **Output**: ~600 tokens (analyse comparative détaillée)

   **Coût Images**: $3.00 × 5,248 / 1,000,000 = **$0.01574**
   **Coût Input text**: $3.00 × 800 / 1,000,000 = **$0.0024**
   **Coût Output**: $15.00 × 600 / 1,000,000 = **$0.009**

   **Sous-total Claude Vision**: **$0.02714**

### Coût Total Scénario 3 (avec RAG): **$0.02819** (~€0.0257)
### Coût Total Scénario 3 (sans RAG): **$0.02714** (~€0.0247)

---

## 📊 Résumé des Coûts par Requête

| Scénario | Coût USD | Coût EUR | Services Principaux |
|----------|----------|----------|---------------------|
| **Question Simple** | $0.00530 | €0.0048 | GPT-4o + Cohere + Embeddings |
| **Question Complexe** | $0.01383 | €0.0126 | GPT-4o + Cohere + Embeddings |
| **2 Images (avec RAG)** | $0.02819 | €0.0257 | Claude Vision + RAG + Cohere |
| **2 Images (sans RAG)** | $0.02714 | €0.0247 | Claude Vision uniquement |

---

## 📈 Coûts Mensuels Estimés

### Hypothèse: 1,000 requêtes/mois

**Mix typique**:
- 60% questions simples = 600 × $0.00530 = **$3.18**
- 30% questions complexes = 300 × $0.01383 = **$4.15**
- 10% analyses d'images = 100 × $0.02819 = **$2.82**

**Total**: **$10.15/mois** pour 1,000 requêtes

### Coûts additionnels fixes:

- **Weaviate Cloud Standard**: ~$25-50/mois
- **Redis Cache** (DigitalOcean): ~$15/mois (optionnel)
- **LangSmith** (monitoring): Gratuit jusqu'à 5K traces/mois

**Total mensuel** (1,000 requêtes): **$50-75/mois**

---

## 💡 Optimisations Possibles

### 1. Embeddings moins chers
**Changement**: `text-embedding-ada-002` → `text-embedding-3-small`
- **Économies**: 80% sur embeddings
- **Impact actuel**: Négligeable (~$0.02/mois sur 1,000 requêtes)

### 2. Cache Redis plus agressif
**Actuel**: Cache activé avec similarité 0.92
- **Taux de hit estimé**: 20-30%
- **Économies**: ~$2-3/mois

### 3. Désactiver Cohere Reranking pour questions simples
- **Économies potentielles**: $0.60/mois (600 questions simples)
- **Impact**: Baisse de Context Precision de ~15%
- **Recommandation**: Garder activé

### 4. Utiliser GPT-4o-mini pour questions simples
**Changement**: gpt-4o → gpt-4o-mini pour Q&A basiques
- **Économies**: ~80% sur génération ($2.54/mois)
- **Risque**: Baisse de qualité pour questions complexes
- **Recommandation**: Tester avec A/B testing

---

## 🎯 Répartition des Coûts (Question Complexe)

```
Total: $0.01383
├─ GPT-4o (génération): $0.01275 (92.2%)
├─ Cohere (reranking): $0.001 (7.2%)
├─ GPT-4o-mini (OOD): $0.00008 (0.6%)
└─ Embeddings: $0.000004 (0.03%)
```

**Conclusion**: GPT-4o représente 92% du coût. C'est le levier principal d'optimisation.

---

## 🔍 Analyse Détaillée: Pourquoi Cohere?

**Coût**: $1/1,000 searches = $0.001/requête

**Bénéfices mesurés** (d'après les commentaires du code):
- Context Precision: +20-30%
- Fidélité des réponses améliorée
- Meilleure compréhension multilingue

**ROI**: Pour $0.60/mois (600 requêtes simples), on obtient une amélioration significative de la qualité. **Recommandé de garder**.

---

## 📝 Recommandations Finales

### Optimisations Prioritaires:

1. **Cache Redis agressif**
   - Augmenter le seuil de similarité sémantique
   - **Économies**: ~20-30% des coûts API

2. **GPT-4o-mini pour Q&A simples**
   - Détecter automatiquement les questions simples (poids, FCR, etc.)
   - Router vers gpt-4o-mini
   - **Économies**: ~$2.50/mois (1,000 requêtes)

3. **Batching des embeddings**
   - Actuel: 1 embedding/requête
   - Proposé: Batch embeddings pour conversation context
   - **Économies**: Négligeables mais améliore latence

### À NE PAS Faire:

1. ❌ **Désactiver Cohere Reranking**
   - Coût minime ($0.60/mois)
   - Impact qualité important

2. ❌ **Utiliser embeddings gratuits**
   - text-embedding-ada-002 déjà très bon marché
   - Qualité critique pour RAG

3. ❌ **Réduire max_tokens GPT-4o**
   - Actuel: 900 tokens (optimal)
   - Risque de réponses tronquées

---

## 🚀 Conclusion

**Coût actuel**: Très raisonnable pour un système RAG de production
- **Question simple**: $0.0053 (0.5 centime)
- **Question complexe**: $0.0138 (1.4 centimes)
- **2 images**: $0.0282 (2.8 centimes)

**Point fort**: Architecture bien optimisée avec cache et reranking intelligent

**Potentiel d'optimisation**: 20-30% avec cache plus agressif + routing GPT-4o-mini

**Verdict**: ✅ Coûts maîtrisés, architecture scalable
