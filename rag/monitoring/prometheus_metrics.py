"""
Prometheus Metrics for Intelia Expert LLM Service
Version: 1.4.1
Last modified: 2025-10-26
"""

"""
Prometheus Metrics for Intelia Expert LLM Service
==================================================

Centralized metrics tracking for LLM costs, performance, and system health.

Tracks metrics for OpenAI, Anthropic Claude, and DeepSeek providers.
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import time

# ============================================================
# LLM METRICS - Coûts et utilisation
# ============================================================

# Tokens consommés par modèle
llm_tokens_total = Counter(
    "intelia_llm_tokens_total",
    "Total tokens consumed by LLM",
    [
        "model",
        "type",
        "provider",
    ],  # type = prompt | completion, provider = openai | anthropic
)

# Coûts LLM en USD
llm_cost_usd_total = Counter(
    "intelia_llm_cost_usd_total",
    "Total LLM cost in USD",
    ["model", "feature", "provider"],  # feature = chat | embeddings | tts
)

# Requêtes LLM
llm_requests_total = Counter(
    "intelia_llm_requests_total",
    "Total LLM API requests",
    ["model", "status", "provider"],  # status = success | error | rate_limited
)

# Latence LLM
llm_request_duration_seconds = Histogram(
    "intelia_llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model", "feature", "provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ============================================================
# RAG METRICS - Retrieval Augmented Generation
# ============================================================

# Documents retrieved
rag_documents_retrieved = Histogram(
    "intelia_rag_documents_retrieved",
    "Number of documents retrieved per query",
    ["query_type"],
    buckets=[0, 1, 5, 10, 20, 50, 100],
)

# RAG latency
rag_query_duration_seconds = Histogram(
    "intelia_rag_query_duration_seconds",
    "RAG query duration in seconds",
    ["stage"],  # stage = retrieval | rerank | generation
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# Cache hits/misses
rag_cache_operations = Counter(
    "intelia_rag_cache_operations_total",
    "RAG cache operations",
    ["operation"],  # operation = hit | miss | write
)

# ============================================================
# SYSTEM METRICS - Santé du système
# ============================================================

# Uptime
system_uptime_seconds = Gauge(
    "intelia_system_uptime_seconds", "System uptime in seconds"
)

# System info
system_info = Info("intelia_system", "System information")

# Active connections
system_active_connections = Gauge(
    "intelia_system_active_connections",
    "Number of active connections",
    ["type"],  # type = redis | weaviate | postgresql
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

_start_time = time.time()


def track_llm_call(
    model: str,
    provider: str,
    feature: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    duration: float,
    status: str = "success",
):
    """Track a single LLM API call"""
    llm_tokens_total.labels(model=model, type="prompt", provider=provider).inc(
        prompt_tokens
    )
    llm_tokens_total.labels(model=model, type="completion", provider=provider).inc(
        completion_tokens
    )
    llm_cost_usd_total.labels(model=model, feature=feature, provider=provider).inc(
        cost_usd
    )
    llm_requests_total.labels(model=model, status=status, provider=provider).inc()
    llm_request_duration_seconds.labels(
        model=model, feature=feature, provider=provider
    ).observe(duration)


def track_rag_query(
    query_type: str,
    num_docs: int,
    retrieval_time: float,
    rerank_time: float = 0,
    generation_time: float = 0,
):
    """Track a RAG query"""
    rag_documents_retrieved.labels(query_type=query_type).observe(num_docs)
    rag_query_duration_seconds.labels(stage="retrieval").observe(retrieval_time)
    if rerank_time > 0:
        rag_query_duration_seconds.labels(stage="rerank").observe(rerank_time)
    if generation_time > 0:
        rag_query_duration_seconds.labels(stage="generation").observe(generation_time)


def track_cache_operation(operation: str):
    """Track cache hit/miss/write"""
    rag_cache_operations.labels(operation=operation).inc()


def update_uptime():
    """Update system uptime"""
    system_uptime_seconds.set(time.time() - _start_time)


def update_connections(
    redis_count: int = 0, weaviate_count: int = 0, postgres_count: int = 0
):
    """Update active connections"""
    if redis_count >= 0:
        system_active_connections.labels(type="redis").set(redis_count)
    if weaviate_count >= 0:
        system_active_connections.labels(type="weaviate").set(weaviate_count)
    if postgres_count >= 0:
        system_active_connections.labels(type="postgresql").set(postgres_count)


def generate_metrics() -> bytes:
    """Generate Prometheus metrics in text format"""
    update_uptime()
    return generate_latest()


def get_content_type() -> str:
    """Get Prometheus content type"""
    return CONTENT_TYPE_LATEST
