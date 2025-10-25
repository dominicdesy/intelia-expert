"""
Prometheus Metrics for Intelia Expert
======================================

Centralized metrics tracking for monitoring costs, performance, and system health.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time

# ============================================================
# LLM METRICS - Coûts et utilisation
# ============================================================

# Tokens consommés par modèle
llm_tokens_total = Counter(
    'intelia_llm_tokens_total',
    'Total tokens consumed by LLM',
    ['model', 'type']  # type = prompt | completion
)

# Coûts LLM en USD
llm_cost_usd_total = Counter(
    'intelia_llm_cost_usd_total',
    'Total LLM cost in USD',
    ['model', 'feature']  # feature = chat | embeddings | tts | voice_realtime
)

# Requêtes LLM
llm_requests_total = Counter(
    'intelia_llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']  # status = success | error | rate_limited
)

# Latence LLM
llm_request_duration_seconds = Histogram(
    'intelia_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model', 'feature'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# ============================================================
# API METRICS - Performance endpoints
# ============================================================

# Requêtes HTTP
http_requests_total = Counter(
    'intelia_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Latence HTTP
http_request_duration_seconds = Histogram(
    'intelia_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# ============================================================
# DATABASE METRICS - Performance requêtes
# ============================================================

# Connexions actives
db_connections_active = Gauge(
    'intelia_db_connections_active',
    'Active database connections',
    ['pool']
)

# Requêtes DB
db_query_duration_seconds = Histogram(
    'intelia_db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

db_queries_total = Counter(
    'intelia_db_queries_total',
    'Total database queries',
    ['operation', 'table', 'status']
)

# ============================================================
# BUSINESS METRICS - Utilisateurs et revenus
# ============================================================

# Utilisateurs actifs
active_users = Gauge(
    'intelia_active_users',
    'Currently active users'
)

# Questions posées
questions_total = Counter(
    'intelia_questions_total',
    'Total questions asked',
    ['source', 'language']  # source = rag | openai_fallback
)

# Revenus
revenue_usd_total = Counter(
    'intelia_revenue_usd_total',
    'Total revenue in USD',
    ['plan']  # plan = essential | pro | elite | intelia
)

# ============================================================
# SYSTEM HEALTH METRICS
# ============================================================

# Erreurs
errors_total = Counter(
    'intelia_errors_total',
    'Total errors',
    ['type', 'severity']  # severity = warning | error | critical
)

# Uptime
uptime_seconds = Gauge(
    'intelia_uptime_seconds',
    'Service uptime in seconds'
)

# Info système
system_info = Info(
    'intelia_system',
    'System information'
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

_start_time = time.time()

def update_uptime():
    """Update uptime metric"""
    uptime_seconds.set(time.time() - _start_time)

def track_llm_call(model: str, feature: str, prompt_tokens: int, completion_tokens: int, cost_usd: float, duration: float, status: str = "success"):
    """Track a single LLM API call"""
    llm_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=model, type="completion").inc(completion_tokens)
    llm_cost_usd_total.labels(model=model, feature=feature).inc(cost_usd)
    llm_requests_total.labels(model=model, status=status).inc()
    llm_request_duration_seconds.labels(model=model, feature=feature).observe(duration)

def track_http_request(method: str, endpoint: str, status: int, duration: float):
    """Track a single HTTP request"""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

def track_db_query(operation: str, table: str, duration: float, status: str = "success"):
    """Track a single database query"""
    db_queries_total.labels(operation=operation, table=table, status=status).inc()
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

def track_question(source: str, language: str):
    """Track a user question"""
    questions_total.labels(source=source, language=language).inc()

def track_error(error_type: str, severity: str = "error"):
    """Track an error occurrence"""
    errors_total.labels(type=error_type, severity=severity).inc()
