# RAPPORT D'ANALYSE RAGAS - Post Follow-up Fixes

**Date**: 2025-10-08
**Tests**: 15 cas
**Score Global**: 23.50% (vs 21.17% précédent, +11%)

---

## 📊 RÉSULTATS GLOBAUX

| Métrique | Avant | Après | Évolution | Cible |
|----------|-------|-------|-----------|-------|
| **Context Precision** | 1.59% | 2.06% | +30% 📈 | 70%+ |
| **Context Recall** | 5.56% | 1.11% | -80% 📉 | 70%+ |
| **Faithfulness** | 26.39% | 31.27% | +18.5% 📈 | 70%+ |
| **Answer Relevancy** | 51.15% | 59.57% | +16.5% 📈 | 70%+ |
| **Score Global** | 21.17% | 23.50% | +11% 📈 | 70%+ |

### Statut: ⚠️ INSUFFISANT (< 30%)

---

## 🔍 ANALYSE DÉTAILLÉE PAR PROBLÈME

### 1. 🚨 CONTEXT RECALL CRITIQUE (-80%)

**Problème identifié**: **12 tests sur 15 (80%) retournent 0 documents de contexte**

#### Causes par Catégorie:

**A) Queries Out-of-Domain (1 test - CORRECT):**
```json
{
  "query": "Qu'est-ce que la cryptomonnaie ?",
  "contexts": [],
  "raison": "OOD detector rejette correctement"
}
```
✅ **Comportement attendu** - Pas de problème

**B) Queries Incomplètes nécessitant Clarification (6+ tests - PROBLÈME):**
```json
{
  "query": "Quel est le poids d'un Ross 308 mâle ?",
  "entites_extraites": {"breed": "Ross 308", "sex": "male"},
  "entites_manquantes": ["age_days"],
  "contexts": [],
  "raison": "Retourne clarification SANS chercher contexte"
}
```
❌ **Problème**: Le système demande l'âge sans faire de recherche partielle

**C) Recherche Vectorielle Défaillante (5+ tests - PROBLÈME MAJEUR):**
```json
{
  "query": "Quels sont les symptômes de Newcastle ?",
  "contexts": [
    "Litter disposal...",
    "Feed Clean-up Trends...",
    "Minimum Ventilation Calculation...",
    "Drinkers configuration..."
  ],
  "raison": "12 documents récupérés mais AUCUN ne parle de Newcastle!"
}
```
❌ **Problème**: Embeddings/chunking de mauvaise qualité

---

### 2. 🔴 CONTEXT PRECISION CATASTROPHIQUE (2.06%)

**Définition**: % de documents récupérés qui sont réellement pertinents

**Exemple concret** - Test "Symptômes Newcastle":
- **Récupéré**: 12 documents
- **Pertinents**: ~0 (tous parlent de litière, ventilation, alimentation)
- **Precision**: 0/12 = 0%

#### Causes Racines:

1. **Embeddings inadaptés au domaine médical avicole**
   - Mots techniques (Newcastle, coccidiose, Gumboro) mal vectorisés
   - Similarité cosinus trouve documents avec mots génériques similaires

2. **Chunking inapproprié**
   - Chunks trop longs → dilution du sens
   - Chunks sans contexte médical clair

3. **Absence de filtrage sémantique post-récupération**
   - Aucun re-ranking
   - Aucune validation de pertinence

---

### 3. 🟡 FAITHFULNESS INSUFFISANT (31.27%)

**Définition**: % de la réponse qui est fidèle au contexte fourni

**Exemple concret** - Test calcul moulée:
```
Contexte: "0.0 kg d'aliment par poulet"
Réponse: "vous aurez besoin de 0.0 kg d'aliment"
Référence attendue: "2.16 kg"
```

❌ **Problème**: Le système suit fidèlement un contexte ERRONÉ (bug calculation)

#### Causes:

1. **Prompt permissif** - Ne force pas assez "use ONLY context"
2. **Contexte de mauvaise qualité** (voir Context Precision)
3. **Température LLM trop élevée** → Hallucinations

---

### 4. ✅ ANSWER RELEVANCY EN PROGRÈS (59.57%)

**Définition**: % de pertinence de la réponse vs question

**Résultat**: Seule métrique au-dessus de 50%

#### Points positifs:
- Les réponses sont bien formulées
- Le ton est approprié
- La structure est cohérente

#### Point d'amélioration:
- Encore 40% de marge pour atteindre 70%+

---

## 🎯 PLAN D'ACTION CORRECTIF

### PRIORITÉ 1 (Impact Immédiat - Critical Path)

#### 1.1. Activer recherche "best effort" pour queries incomplètes

**Problème**: "Quel poids Ross 308?" → 0 contextes au lieu de chercher infos générales

**Solution**:
```python
# Dans query_router.py, méthode route()
if route.destination == "needs_clarification":
    # 🆕 NOUVEAU: Faire quand même une recherche partielle
    partial_query = self._build_partial_query(
        original_query=query,
        known_entities=route.entities,
        missing_entities=route.missing_fields
    )

    # Chercher avec ce qu'on a (ex: "Ross 308 poids performance")
    fallback_docs = await weaviate_search(partial_query, limit=5)

    # Retourner clarification AVEC contexte partiel
    return clarification_with_context(
        message=clarification_message,
        partial_context=fallback_docs,
        missing=route.missing_fields
    )
```

**Impact attendu**: Context Recall +40-50% (tests B ne seront plus à 0)

---

#### 1.2. Implémenter Re-Ranking Sémantique

**Problème**: "Newcastle?" → Documents sur litière/ventilation

**Solution - Cross-Encoder Re-Ranking**:
```python
# Nouveau fichier: llm/retrieval/semantic_reranker.py
from sentence_transformers import CrossEncoder

class SemanticReRanker:
    def __init__(self, model_name='cross-encoder/ms-marco-MiniLM-L-6-v2'):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Re-rank documents using cross-encoder

        Returns: List of (doc, score) tuples, filtered by score > 0.3
        """
        # Créer paires (query, doc)
        pairs = [(query, doc) for doc in documents]

        # Scorer avec cross-encoder (plus précis que cosine similarity)
        scores = self.model.predict(pairs)

        # Filtrer scores faibles + trier
        results = [
            (doc, score)
            for doc, score in zip(documents, scores)
            if score > 0.3  # Seuil de pertinence
        ]
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]
```

**Intégration dans standard_handler.py**:
```python
# Après récupération Weaviate
raw_docs = await weaviate_client.search(query, limit=20)  # Récupérer plus

# Re-rank pour garder les meilleurs
reranker = SemanticReRanker()
filtered_docs = reranker.rerank(
    query=query,
    documents=[d.content for d in raw_docs],
    top_k=5
)

# Utiliser seulement les documents pertinents
context_docs = [doc for doc, score in filtered_docs]
```

**Impact attendu**: Context Precision: 2% → 40-50%

---

#### 1.3. Renforcer Prompts de Génération

**Problème**: Faithfulness 31% → LLM ne suit pas assez le contexte

**Solution - Prompt Strict**:
```python
# Dans system_prompts.json, modifier "answer_generation"
STRICT_PROMPT = """Tu es un expert en production avicole.

RÈGLES CRITIQUES - À SUIVRE ABSOLUMENT:

1. ✅ Réponds UNIQUEMENT en te basant sur le contexte fourni ci-dessous
2. ❌ NE JAMAIS inventer de chiffres, dates, ou faits
3. ❌ Si le contexte ne contient pas la réponse, dis: "Je n'ai pas assez d'informations dans ma base de données"
4. ✅ Cite des extraits du contexte pour justifier ta réponse
5. ✅ Si le contexte est incomplet, indique ce qui manque

CONTEXTE FOURNI:
{context}

QUESTION:
{question}

RÉPONSE (basée UNIQUEMENT sur le contexte):"""
```

**Baisser température**:
```python
# Dans generators.py
response = await openai_client.chat.completions.create(
    model="gpt-4o",
    temperature=0.3,  # ⬇️ Baissé de 0.7 → Plus factuel, moins créatif
    messages=[...]
)
```

**Impact attendu**: Faithfulness: 31% → 60-70%

---

### PRIORITÉ 2 (Moyen Terme - Optimisations)

#### 2.1. Améliorer Embeddings

**Options**:
1. **Fine-tuning** sur corpus avicole
   - Collecter 5000+ paires (question, document_pertinent)
   - Fine-tune `intfloat/multilingual-e5-large`

2. **Utiliser modèle spécialisé sciences**:
   ```python
   # Remplacer embedding actuel
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('allenai/specter')  # Spécialisé sciences
   ```

**Impact**: Context Precision +10-20%

---

#### 2.2. Hybrid Search (BM25 + Vector)

**Problème**: Recherche purement vectorielle rate des mots-clés exacts

**Solution**:
```python
# Combiner recherche lexicale (mots-clés) + sémantique
from rank_bm25 import BM25Okapi

class HybridSearcher:
    def search(self, query, documents):
        # 1. BM25 (lexical)
        bm25_scores = bm25.get_scores(query.split())

        # 2. Vector (semantic)
        vector_scores = cosine_similarity(query_embed, doc_embeds)

        # 3. Combiner (0.3 BM25 + 0.7 Vector)
        hybrid_scores = 0.3 * bm25_scores + 0.7 * vector_scores

        return top_k_docs(hybrid_scores)
```

**Impact**: Context Recall +15-20%

---

## 📋 SYNTHÈSE EXÉCUTIVE

### Problèmes Critiques:

1. **80% des tests sans contexte** → Queries incomplètes + OOD + mauvaise recherche
2. **98% des documents non pertinents** → Embeddings/chunking inadaptés
3. **69% de non-fidélité au contexte** → Prompts permissifs + température élevée

### Actions Immédiates (1-2 jours):

✅ **Quick Wins** (Impact: +30-40% score global):
1. Recherche partielle pour queries incomplètes
2. Re-ranking sémantique post-récupération
3. Prompts stricts + température ↓

### Actions Moyen Terme (1-2 semaines):

🔧 **Optimisations** (Impact: +20-30% score global):
4. Fine-tune embeddings domaine avicole
5. Hybrid search BM25+Vector
6. Améliorer chunking (contexte médical)

### Objectif Final:

🎯 **Score Global: 70%+**
- Context Precision: 70%
- Context Recall: 70%
- Faithfulness: 75%
- Answer Relevancy: 80%

---

## 📁 FICHIERS À MODIFIER

### Priorité 1:
1. `llm/core/query_router.py` → Recherche partielle
2. `llm/retrieval/semantic_reranker.py` → **NOUVEAU FICHIER** re-ranker
3. `llm/core/handlers/standard_handler.py` → Intégrer re-ranker
4. `llm/config/system_prompts.json` → Prompts stricts
5. `llm/generation/generators.py` → Température ↓

### Priorité 2:
6. `llm/config/embedding_config.json` → **NOUVEAU** config embeddings
7. `llm/retrieval/hybrid_search.py` → **NOUVEAU** BM25+Vector

---

## 🧪 VALIDATION

Après chaque correction:
```bash
cd /c/intelia_gpt/intelia-expert/llm
python scripts/run_ragas_evaluation.py \
  --test-cases 15 \
  --output logs/ragas_post_corrections_v2.json
```

**Cible par itération**:
- Itération 1 (P1.1): Context Recall 1% → 40%
- Itération 2 (P1.2): Context Precision 2% → 50%
- Itération 3 (P1.3): Faithfulness 31% → 65%
- Final: Score global 23% → 70%+

---

**Rapport généré le**: 2025-10-08 21:35 UTC
**Prochaine étape**: Implémenter P1.1 (recherche partielle)
