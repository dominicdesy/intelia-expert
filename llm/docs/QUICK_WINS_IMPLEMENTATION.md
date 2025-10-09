# QUICK WINS - Guide d'Implémentation Détaillé

**Objectif**: Passer de 23.50% à 60-70% de score RAGAS en implémentant 3 quick wins

---

## 🎯 QUICK WIN #1: Intégrer Semantic Re-Ranker

**Impact Attendu**: Context Precision 2.06% → 40-50%

### Fichier: `llm/core/handlers/standard_handler.py`

**Ligne 1: Import du re-ranker (après ligne 18)**

```python
# Ajout APRÈS la ligne:
# from .standard_handler_helpers import (

# AJOUTER CETTE IMPORT:
from retrieval.semantic_reranker import get_reranker
```

**Ligne 2: Initialiser re-ranker dans __init__ (après ligne 27)**

```python
# Ajout APRÈS la ligne:
# self.response_generator = None

# AJOUTER:
self.semantic_reranker = None  # Lazy load
```

**Ligne 3: Propriété lazy-loading (avant méthode configure, ~ligne 29)**

```python
# AJOUTER CETTE PROPRIÉTÉ COMPLÈTE:
@property
def reranker(self):
    """Lazy load semantic re-ranker"""
    if self.semantic_reranker is None:
        try:
            self.semantic_reranker = get_reranker(
                model_name='cross-encoder/ms-marco-MiniLM-L-6-v2',
                score_threshold=0.3  # Liberal pour commencer
            )
            logger.info("✅ Semantic re-ranker initialized")
        except Exception as e:
            logger.warning(f"⚠️ Re-ranker init failed: {e}. Continuing without re-ranking.")
            self.semantic_reranker = False  # Flag pour ne pas réessayer
    return self.semantic_reranker if self.semantic_reranker is not False else None
```

**Ligne 4: Appliquer re-ranking après search Weaviate (lignes 390-401)**

```python
# REMPLACER ce bloc (lignes 390-401):
result = await self.weaviate_core.search(
    query=query,
    top_k=weaviate_top_k,
    language=language,
    filters=filters,
    conversation_context=conversation_context_list,
)

# Handle result based on source
if result and result.source not in (RAGSource.NO_RESULTS, RAGSource.LOW_CONFIDENCE):
    doc_count = len(result.context_docs) if result.context_docs else 0
    logger.info(f"Weaviate ({language}): {doc_count} documents found")

# PAR CE NOUVEAU CODE:
# 🆕 STEP 1: Récupérer PLUS de documents (20 au lieu de 5-12)
# pour avoir un meilleur recall avant re-ranking
weaviate_initial_k = weaviate_top_k * 3  # 15-36 docs au lieu de 5-12

result = await self.weaviate_core.search(
    query=query,
    top_k=weaviate_initial_k,  # Plus de docs
    language=language,
    filters=filters,
    conversation_context=conversation_context_list,
)

# Handle result based on source
if result and result.source not in (RAGSource.NO_RESULTS, RAGSource.LOW_CONFIDENCE):
    doc_count_before = len(result.context_docs) if result.context_docs else 0
    logger.info(f"Weaviate ({language}): {doc_count_before} documents retrieved (before re-ranking)")

    # 🆕 STEP 2: Appliquer re-ranking sémantique
    if result.context_docs and self.reranker:
        try:
            # Extraire textes des documents
            doc_texts = [
                doc.get('content', '') if isinstance(doc, dict)
                else getattr(doc, 'content', '')
                for doc in result.context_docs
            ]

            # Re-ranker avec cross-encoder
            reranked_texts = self.reranker.rerank(
                query=query,
                documents=doc_texts,
                top_k=weaviate_top_k,  # Garder seulement top 5-12
                return_scores=False
            )

            # Reconstruire docs avec seulement les pertinents
            if reranked_texts:
                # Mapper textes → docs originaux
                text_to_doc = {
                    (doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'content', '')): doc
                    for doc in result.context_docs
                }

                result.context_docs = [text_to_doc[text] for text in reranked_texts if text in text_to_doc]

                doc_count_after = len(result.context_docs)
                logger.info(
                    f"✅ Re-ranking: {doc_count_before} docs → {doc_count_after} relevant docs "
                    f"(filtered {doc_count_before - doc_count_after})"
                )
            else:
                logger.warning(f"⚠️ Re-ranking returned 0 docs - keeping original")

        except Exception as e:
            logger.error(f"❌ Re-ranking error: {e}. Using original documents.", exc_info=True)
            # Continue avec documents originaux si erreur

    doc_count = len(result.context_docs) if result.context_docs else 0
```

---

## 🎯 QUICK WIN #2: Prompts Stricts + Température Basse

**Impact Attendu**: Faithfulness 31.27% → 65-70%

### Fichier: `llm/config/system_prompts.json`

**Modification: Prompt "answer_generation"**

```json
{
  "answer_generation": {
    "description": "Génération de réponse RAG stricte - PRIORITÉ FIDÉLITÉ AU CONTEXTE",
    "prompt": "Tu es un expert en production avicole. Ta mission est de répondre aux questions en te basant UNIQUEMENT sur le contexte fourni.\n\nRÈGLES CRITIQUES (À SUIVRE ABSOLUMENT):\n\n1. ✅ OBLIGATOIRE: Réponds SEULEMENT en utilisant les informations du contexte ci-dessous\n2. ❌ INTERDIT: N'invente JAMAIS de chiffres, dates, noms, ou faits\n3. ❌ INTERDIT: N'utilise PAS tes connaissances générales si le contexte ne contient pas la réponse\n4. ✅ Si le contexte est insuffisant: Dis clairement \"Je n'ai pas assez d'informations dans ma base de données pour répondre précisément\"\n5. ✅ Cite des extraits du contexte pour justifier ta réponse\n6. ✅ Si le contexte est incomplet: Indique quelles informations manquent\n\nCONTEXTE FOURNI:\n{context}\n\nQUESTION:\n{question}\n\nRÉPONSE (basée UNIQUEMENT sur le contexte ci-dessus):"
  }
}
```

### Fichier: `llm/generation/generators.py`

**Modification: Baisser température (chercher ligne avec `temperature=`)**

Trouver la ligne qui ressemble à:
```python
response = await self.client.chat.completions.create(
    model=self.model,
    temperature=0.7,  # ou autre valeur
    ...
)
```

**REMPLACER** `temperature=0.7` **PAR** `temperature=0.2`

Explication:
- 0.7 = Créatif mais hallucine
- 0.2 = Factuel, fidèle au contexte
- 0.0 = Déterministe (trop rigide)

**Recherche rapide:**
```bash
grep -n "temperature=" llm/generation/generators.py
```

---

## 🎯 QUICK WIN #3: Recherche Partielle pour Queries Incomplètes

**Impact Attendu**: Context Recall 1.11% → 40%

### Contexte du Problème

Actuellement: "Quel poids Ross 308?" (manque âge) → 0 documents récupérés
Correction: "Quel poids Ross 308?" → Cherche quand même "Ross 308 poids performance"

### Fichier: `llm/core/query_router.py`

**Chercher la section où needs_clarification est détecté** (~ligne 600-700)

Code actuel ressemble à:
```python
if needs_clarification:
    # Build clarification message
    return QueryRoute(
        destination="needs_clarification",
        entities=entities,
        missing_fields=missing_fields,
        ...
    )
```

**REMPLACER PAR:**

```python
if needs_clarification:
    # 🆕 NOUVELLE STRATÉGIE: Faire une recherche partielle AVANT de demander clarification
    # pour fournir du contexte même avec query incomplète

    # Construire query de recherche partielle avec ce qu'on a
    partial_search_terms = []

    if entities.get('breed'):
        partial_search_terms.append(entities['breed'])
    if entities.get('metric'):
        partial_search_terms.append(entities['metric'])
    if entities.get('sex'):
        partial_search_terms.append(entities['sex'])

    # Ajouter mots-clés de la query originale (sans les questions)
    query_words = [
        word for word in query.lower().split()
        if len(word) > 3 and word not in ['quel', 'quelle', 'what', 'cual', 'comment', 'how']
    ]
    partial_search_terms.extend(query_words[:3])  # Max 3 mots

    partial_query = ' '.join(partial_search_terms)

    logger.info(
        f"🔍 Incomplete query detected. Partial search: '{partial_query}' "
        f"(entities: {list(entities.keys())}, missing: {missing_fields})"
    )

    # Build clarification message (comme avant)
    return QueryRoute(
        destination="needs_clarification",
        entities=entities,
        missing_fields=missing_fields,
        partial_search_query=partial_query,  # 🆕 NOUVEAU: Passer query partielle
        ...
    )
```

### Fichier: `llm/core/query_processor.py`

**Chercher où "needs_clarification" est traité** (~ligne 150-200)

Code actuel:
```python
if route.destination == "needs_clarification":
    # Demander clarification
    return RAGResult(
        source=RAGSource.NEEDS_CLARIFICATION,
        answer=clarification_message,
        context_docs=[],  # ← VIDE!
        ...
    )
```

**REMPLACER PAR:**

```python
if route.destination == "needs_clarification":
    # 🆕 Faire recherche partielle avec ce qu'on a
    partial_context_docs = []

    if hasattr(route, 'partial_search_query') and route.partial_search_query:
        try:
            logger.info(f"📚 Fetching partial context with: {route.partial_search_query}")

            # Chercher dans Weaviate avec query partielle
            if self.weaviate_core:
                partial_result = await self.weaviate_core.search(
                    query=route.partial_search_query,
                    top_k=3,  # Juste quelques docs
                    language=language
                )

                if partial_result and partial_result.context_docs:
                    partial_context_docs = partial_result.context_docs
                    logger.info(f"✅ Found {len(partial_context_docs)} partial context docs")

        except Exception as e:
            logger.warning(f"⚠️ Partial search failed: {e}")

    # Demander clarification AVEC contexte partiel
    return RAGResult(
        source=RAGSource.NEEDS_CLARIFICATION,
        answer=clarification_message,
        context_docs=partial_context_docs,  # 🆕 AVEC CONTEXTE!
        ...
    )
```

---

## 📋 CHECKLIST D'IMPLÉMENTATION

### Quick Win #1: Re-Ranker
- [ ] Import `get_reranker` dans `standard_handler.py`
- [ ] Ajouter propriété `reranker` avec lazy loading
- [ ] Modifier appel Weaviate: `top_k` × 3
- [ ] Ajouter logique re-ranking après `weaviate_core.search()`
- [ ] Tester: Query "Newcastle" devrait filtrer docs non pertinents

### Quick Win #2: Prompts Stricts
- [ ] Modifier prompt `answer_generation` dans `system_prompts.json`
- [ ] Baisser température 0.7 → 0.2 dans `generators.py`
- [ ] Tester: Réponse devrait coller au contexte (pas d'hallucinations)

### Quick Win #3: Recherche Partielle
- [ ] Modifier `query_router.py`: construire `partial_search_query`
- [ ] Modifier `query_processor.py`: chercher avec query partielle
- [ ] Retourner `context_docs` non vide même pour clarifications
- [ ] Tester: "Poids Ross 308?" devrait retourner ~3 docs sur Ross 308

---

## 🧪 TESTS DE VALIDATION

Après chaque quick win, tester avec queries problématiques:

**Query 1**: "Quels sont les symptômes de Newcastle?"
- Avant: 12 docs non pertinents (litière, ventilation)
- Après QW1: 3-5 docs sur Newcastle

**Query 2**: "Quel est le poids d'un Ross 308 mâle?"
- Avant: 0 docs (needs_clarification)
- Après QW3: 3 docs sur Ross 308 performance

**Query 3**: Calcul moulée
- Avant: Répond "0.0 kg" (suit contexte erroné)
- Après QW2: Dit "Je n'ai pas assez d'informations" si contexte invalide

---

## 🚀 DÉPLOIEMENT

```bash
# 1. Installer dépendance re-ranker
pip install sentence-transformers

# 2. Tester localement
cd /c/intelia_gpt/intelia-expert/llm
python -c "from retrieval.semantic_reranker import get_reranker; r = get_reranker(); print('✅ Re-ranker OK')"

# 3. Lancer tests RAGAS (5 queries pour rapidité)
python scripts/run_ragas_evaluation.py \
  --test-cases 5 \
  --output logs/ragas_post_quick_wins.json

# 4. Comparer résultats
python scripts/analyze_ragas_results.py

# 5. Si bon: Commit + Push
git add -A
git commit -m "Quick Wins: Re-ranker + Strict Prompts + Partial Search"
git push
```

---

## 📊 RÉSULTATS ATTENDUS

| Métrique | Avant | Après QW | Amélioration |
|----------|-------|----------|--------------|
| Context Precision | 2.06% | **40-50%** | +1940% 📈 |
| Context Recall | 1.11% | **40%** | +3500% 📈 |
| Faithfulness | 31.27% | **65-70%** | +120% 📈 |
| Answer Relevancy | 59.57% | **70%+** | +18% 📈 |
| **GLOBAL** | **23.50%** | **60-70%** | **+185%** 📈 |

---

**Prochaine étape**: Implémenter QW#1 (Re-Ranker) car c'est le plus simple et a le plus gros impact.
