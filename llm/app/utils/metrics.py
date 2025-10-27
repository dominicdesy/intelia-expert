"""
Prometheus Metrics for LLM Service
Tracks requests, latency, tokens, and errors
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# ============================================
# METRICS DEFINITIONS
# ============================================

# Request counter
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM inference requests',
    ['model', 'status']
)

# Latency histogram
llm_inference_duration_seconds = Histogram(
    'llm_inference_duration_seconds',
    'LLM inference latency in seconds',
    ['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]
)

# Token counters
llm_tokens_generated_total = Counter(
    'llm_tokens_generated_total',
    'Total tokens generated',
    ['model']
)

llm_tokens_prompt_total = Counter(
    'llm_tokens_prompt_total',
    'Total prompt tokens processed',
    ['model']
)

# Model availability
llm_model_loaded = Gauge(
    'llm_model_loaded',
    'Is the model loaded and available (1=yes, 0=no)',
    ['model', 'provider']
)

# Error counter
llm_errors_total = Counter(
    'llm_errors_total',
    'Total number of errors',
    ['model', 'error_type']
)


# ============================================
# TRACKING FUNCTIONS
# ============================================

def track_request(model: str, status: str):
    """Track a request"""
    llm_requests_total.labels(model=model, status=status).inc()


def track_latency(model: str, duration: float):
    """Track request latency"""
    llm_inference_duration_seconds.labels(model=model).observe(duration)


def track_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    """Track token usage"""
    llm_tokens_prompt_total.labels(model=model).inc(prompt_tokens)
    llm_tokens_generated_total.labels(model=model).inc(completion_tokens)


def track_error(model: str, error_type: str):
    """Track an error"""
    llm_errors_total.labels(model=model, error_type=error_type).inc()


def set_model_status(model: str, provider: str, available: bool):
    """Set model availability status"""
    llm_model_loaded.labels(model=model, provider=provider).set(1 if available else 0)


# ============================================
# DECORATOR
# ============================================

def track_inference(model_name: str):
    """
    Decorator to automatically track inference metrics

    Usage:
        @track_inference("llama-3.1-8b")
        async def my_inference_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_type = type(e).__name__
                track_error(model_name, error_type)
                raise
            finally:
                duration = time.time() - start_time
                track_request(model_name, status)
                track_latency(model_name, duration)

        return wrapper
    return decorator


# ============================================
# METRICS ENDPOINT RESPONSE
# ============================================

def get_metrics():
    """Get Prometheus metrics in text format"""
    return generate_latest()


def get_metrics_content_type():
    """Get content type for metrics response"""
    return CONTENT_TYPE_LATEST
