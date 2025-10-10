# 🔧 Exemple d'intégration: LLM Ensemble dans ResponseGenerator

**Date:** 2025-10-06

---

## Option recommandée: Ensemble Conditionnel

Voici comment intégrer l'ensemble dans `generation/response_generator.py`:

### 1. Modification de `__init__`

```python
# Dans generation/response_generator.py

from .llm_router import get_llm_router
from .llm_ensemble import get_llm_ensemble, EnsembleMode

class ResponseGenerator:
    def __init__(
        self,
        client,
        cache_manager=None,
        language: str = "fr",
        prompts_path: Optional[str] = None,
        descriptions_path: Optional[str] = None,
    ):
        self.client = client
        self.cache_manager = cache_manager
        self.language = language

        # Initialize modular components
        self.entity_enrichment_builder = EntityEnrichmentBuilder(descriptions_path)
        self.language_handler = LanguageHandler()

        # Initialize Multi-LLM Router (existing)
        self.llm_router = get_llm_router()

        # NOUVEAU: Initialize Multi-LLM Ensemble
        self.llm_ensemble = get_llm_ensemble(mode=EnsembleMode.BEST_OF_N)

        # NOUVEAU: Configuration ensemble
        self.ensemble_enabled = os.getenv("ENABLE_LLM_ENSEMBLE", "false").lower() == "true"

        # Load prompts manager
        ...
```

### 2. Ajout de la logique de décision

```python
class ResponseGenerator:
    # ... existing code ...

    def _should_use_ensemble(
        self,
        query: str,
        domain: Optional[str],
        entities: Dict[str, Any],
        context_docs: List[Dict],
    ) -> bool:
        """
        Détermine si on doit utiliser l'ensemble pour cette requête

        Critères:
        1. Domaine santé = critique
        2. Peu de contexte disponible
        3. Mots-clés critiques (symptôme, diagnostic, traitement)
        4. Entities ambiguës ou manquantes
        """

        # Critère 1: Domaine santé = haute priorité
        if domain and domain.lower() in ["health", "santé"]:
            logger.info(
                f"🔀 Ensemble trigger: health domain ({domain})"
            )
            return True

        # Critère 2: Peu de contexte = besoin de qualité
        if len(context_docs) < 2:
            logger.info(
                f"🔀 Ensemble trigger: low context ({len(context_docs)} docs)"
            )
            return True

        # Critère 3: Mots-clés critiques
        critical_keywords = [
            "symptôme",
            "symptom",
            "maladie",
            "disease",
            "diagnostic",
            "diagnosis",
            "traitement",
            "treatment",
            "protocole",
            "protocol",
            "recommandation",
            "recommendation",
        ]
        query_lower = query.lower()
        for keyword in critical_keywords:
            if keyword in query_lower:
                logger.info(
                    f"🔀 Ensemble trigger: critical keyword '{keyword}'"
                )
                return True

        # Critère 4: Entités manquantes (query complexe)
        if not entities or len(entities) < 2:
            # Query complexe sans entities claires = besoin de multiple perspectives
            if len(query.split()) > 15:  # Query longue
                logger.info(
                    "🔀 Ensemble trigger: complex query with few entities"
                )
                return True

        # Sinon, router single LLM suffit
        return False
```

### 3. Modification de `generate_response`

```python
class ResponseGenerator:
    # ... existing code ...

    async def generate_response(
        self,
        query: str,
        context_docs: List[Document],
        language: str = None,
        enrichment: Optional[ContextEnrichment] = None,
        query_type: Optional[str] = None,
        domain: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Generate response using either ensemble or router

        Args:
            query: User query
            context_docs: Retrieved documents
            language: Response language
            enrichment: Optional context enrichment
            query_type: Type of query (standard, comparative, temporal)
            domain: Detected domain (health, nutrition, etc.)
            entities: Extracted entities

        Returns:
            Generated response text
        """
        language = language or self.language

        # Convert documents to dict format for ensemble
        context_docs_dict = DocumentUtils.documents_to_dict(context_docs)

        # NOUVEAU: Décision Ensemble vs Router
        use_ensemble = (
            self.ensemble_enabled
            and self._should_use_ensemble(
                query, domain, entities or {}, context_docs_dict
            )
        )

        # Build system prompt
        system_prompt = self._build_system_prompt(enrichment, query_type)

        if use_ensemble:
            # === ENSEMBLE PATH (haute qualité) ===
            logger.info(
                f"🔀 Using LLM Ensemble for high-priority query (domain={domain})"
            )

            try:
                result = await self.llm_ensemble.generate_ensemble_response(
                    query=query,
                    context_docs=context_docs_dict,
                    language=language,
                    system_prompt=system_prompt,
                )

                # Log quality metrics
                logger.info(
                    f"✅ Ensemble response: provider={result['provider']}, "
                    f"confidence={result['confidence']:.2f}, "
                    f"time={result['execution_time_ms']:.0f}ms"
                )

                # Track in metrics
                METRICS["ensemble_queries"].inc()
                METRICS["ensemble_confidence"].observe(result["confidence"])
                METRICS["response_latency"].labels(provider=result["provider"]).observe(
                    result["execution_time_ms"] / 1000
                )

                return result["final_answer"]

            except Exception as e:
                logger.error(f"❌ Ensemble generation failed: {e}")
                logger.info("⚠️ Falling back to router")
                # Fallback to router on error
                use_ensemble = False

        if not use_ensemble:
            # === ROUTER PATH (standard - existing logic) ===
            logger.info(f"🔀 Using LLM Router for standard query")

            # Existing router logic...
            provider = self.llm_router.route_query(
                query, context_docs_dict, {"intent_type": query_type}
            )

            # Build messages
            messages = self._build_messages(
                query, context_docs, language, enrichment, system_prompt
            )

            # Generate with router
            response = await self.llm_router.generate(provider, messages)

            # Track in metrics
            METRICS["router_queries"].inc()
            METRICS["response_latency"].labels(provider=provider.value).observe(...)

            return response

    def _build_system_prompt(
        self, enrichment: Optional[ContextEnrichment], query_type: Optional[str]
    ) -> str:
        """Build system prompt for LLM"""

        base_prompt = (
            "Tu es un expert en production avicole. "
            "Réponds de manière factuelle, précise et complète."
        )

        # Add enrichment if available
        if enrichment and enrichment.enrichment_text:
            base_prompt += f"\n\n{enrichment.enrichment_text}"

        # Add query-type specific instructions
        if query_type == "comparative":
            base_prompt += (
                "\n\nCette question demande une comparaison. "
                "Compare les différentes options de manière structurée."
            )
        elif query_type == "temporal":
            base_prompt += (
                "\n\nCette question concerne l'évolution temporelle. "
                "Décris les changements dans le temps."
            )

        return base_prompt

    def _build_messages(
        self,
        query: str,
        context_docs: List[Document],
        language: str,
        enrichment: Optional[ContextEnrichment],
        system_prompt: str,
    ) -> List[Dict[str, str]]:
        """Build messages for LLM (existing logic)"""

        # Format context
        context_text = self._format_context(context_docs)

        # Build user message
        user_message = f"""Contexte:
{context_text}

Question: {query}

Réponds en {language}."""

        if enrichment and enrichment.enrichment_text:
            user_message = f"{enrichment.enrichment_text}\n\n{user_message}"

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

    def _format_context(self, context_docs: List[Document]) -> str:
        """Format context documents"""
        if not context_docs:
            return "Aucun contexte disponible."

        formatted = []
        for i, doc in enumerate(context_docs[:5], 1):
            content = doc.page_content
            source = doc.metadata.get("source", "unknown")
            formatted.append(f"[Document {i} - {source}]\n{content}")

        return "\n\n".join(formatted)
```

### 4. Ajout de métriques Prometheus

```python
# Au début du fichier, avec les autres imports
from prometheus_client import Counter, Histogram, Gauge

# Métriques pour l'ensemble
METRICS["ensemble_queries"] = Counter(
    "ensemble_queries_total",
    "Total queries handled by LLM ensemble",
)

METRICS["ensemble_confidence"] = Histogram(
    "ensemble_confidence_score",
    "Confidence scores from ensemble responses",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)

METRICS["router_queries"] = Counter(
    "router_queries_total",
    "Total queries handled by LLM router",
)

METRICS["response_latency"] = Histogram(
    "response_generation_latency_seconds",
    "Response generation latency by provider",
    labelnames=["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)
```

---

## Exemple d'utilisation complète

```python
# Dans core/handlers/standard_handler.py

async def handle(self, preprocessed_data, start_time, **kwargs):
    """Handle standard query with ensemble support"""

    query = preprocessed_data.get("normalized_query")
    entities = preprocessed_data.get("entities", {})
    domain = preprocessed_data.get("domain")
    context_docs = ...  # Retrieved from PostgreSQL/Weaviate

    # Generate response (automatically chooses ensemble or router)
    response = await self.response_generator.generate_response(
        query=query,
        context_docs=context_docs,
        language="fr",
        domain=domain,  # IMPORTANT: Pass domain for ensemble decision
        entities=entities,  # IMPORTANT: Pass entities for ensemble decision
        query_type="standard",
    )

    return RAGResult(
        answer=response,
        context_docs=context_docs,
        source=RAGSource.HYBRID,
        processing_time=time.time() - start_time,
    )
```

---

## Configuration Production

### Variables d'environnement Digital Ocean

```bash
# Activer l'ensemble (false par défaut)
ENABLE_LLM_ENSEMBLE=true

# Mode (best_of_n | fusion | voting)
LLM_ENSEMBLE_MODE=best_of_n

# Modèle juge (pour évaluation)
LLM_JUDGE_MODEL=gpt-4o-mini

# Clés API (3 providers)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# Router (existing - keep for fallback)
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=gpt4o
```

### Rollout progressif recommandé

**Semaine 1: Test (5% des requêtes santé)**
```python
def _should_use_ensemble(self, query, domain, entities, context_docs):
    # Test sur 5% des requêtes santé uniquement
    if domain == "health":
        import random
        return random.random() < 0.05
    return False
```

**Semaine 2-3: Rollout (10% → 20%)**
```python
def _should_use_ensemble(self, query, domain, entities, context_docs):
    if domain == "health":
        import random
        return random.random() < 0.20  # 20%
    return False
```

**Semaine 4+: Production (20-30% selon budget)**
```python
def _should_use_ensemble(self, query, domain, entities, context_docs):
    # Critères finaux (voir section 2 ci-dessus)
    return self._final_criteria(query, domain, entities, context_docs)
```

---

## Monitoring en production

### Dashboard Grafana

```promql
# Taux d'utilisation ensemble vs router
rate(ensemble_queries_total[5m]) / (rate(ensemble_queries_total[5m]) + rate(router_queries_total[5m]))

# Confidence score moyen
histogram_quantile(0.5, ensemble_confidence_score)

# Latence p95 par provider
histogram_quantile(0.95, response_generation_latency_seconds)

# Coût estimé par heure
(rate(ensemble_queries_total[1h]) * 0.01) + (rate(router_queries_total[1h]) * 0.003)
```

### Alertes

```yaml
# Ensemble usage trop élevé (coût)
- alert: HighEnsembleUsage
  expr: rate(ensemble_queries_total[5m]) / (rate(ensemble_queries_total[5m]) + rate(router_queries_total[5m])) > 0.30
  for: 10m
  annotations:
    summary: "Ensemble usage > 30% (cost risk)"

# Confidence faible (qualité)
- alert: LowEnsembleConfidence
  expr: histogram_quantile(0.5, ensemble_confidence_score) < 0.7
  for: 15m
  annotations:
    summary: "Ensemble median confidence < 0.7"

# Latence élevée
- alert: HighResponseLatency
  expr: histogram_quantile(0.95, response_generation_latency_seconds{provider="fusion"}) > 10
  for: 5m
  annotations:
    summary: "p95 latency > 10s for fusion"
```

---

## Tests A/B recommandés

### Scenario 1: Ensemble ON vs OFF

```python
# Groupe A: Ensemble activé (20% users)
# Groupe B: Router uniquement (80% users)

# Métriques à comparer:
# - User satisfaction score (thumbs up/down)
# - Query resolution rate (clarification needed ?)
# - Response accuracy (manual evaluation on sample)
# - Cost per query
# - Latency p95
```

### Scenario 2: Best-of-N vs Fusion

```python
# Groupe A: Best-of-N (50% ensemble queries)
# Groupe B: Fusion (50% ensemble queries)

# Métriques:
# - Response completeness
# - Factual accuracy
# - Cost difference
# - Latency difference
```

---

## Checklist d'intégration

- [ ] Modifier `generation/response_generator.py` (__init__)
- [ ] Ajouter méthode `_should_use_ensemble()`
- [ ] Modifier `generate_response()` pour décision ensemble
- [ ] Ajouter `_build_system_prompt()` helper
- [ ] Ajouter métriques Prometheus
- [ ] Configurer variables d'environnement Digital Ocean
- [ ] Tester en local (avec API keys)
- [ ] Déployer en mode test (5% traffic)
- [ ] Monitorer coûts et qualité
- [ ] Rollout progressif (5% → 10% → 20%)
- [ ] Setup alertes Grafana
- [ ] A/B testing (ensemble vs router)

---

**Prêt pour déploiement** ✅
