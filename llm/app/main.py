"""
Intelia LLM Service - Main Application
FastAPI server providing OpenAI-compatible LLM inference API

Version: 1.0.0
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers import chat, models, health, generation
from app.utils.logger import setup_logging
import logging
import time

# Setup logging
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Intelia LLM Service",
    description="""
    OpenAI-compatible LLM inference API for Intelia.

    Provides chat completions using specialized models fine-tuned for animal production.

    **Features:**
    - OpenAI-compatible API (`/v1/chat/completions`)
    - Support for HuggingFace Inference API (Phase 1) and vLLM (Phase 2)
    - Prometheus metrics for monitoring
    - Health checks

    **Provider Abstraction:**
    - Phase 1: HuggingFace Serverless API (pay-per-use)
    - Phase 2: Self-hosted vLLM (cost optimization)

    **Migration-friendly:** Same API, zero code changes when switching providers.
    """,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()

    logger.info(f"-> {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"<- {request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Duration: {duration:.3f}s"
        )

        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[X] {request.method} {request.url.path} "
            f"- Error: {str(e)} "
            f"- Duration: {duration:.3f}s",
            exc_info=True,
        )
        raise


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error",
                "code": "internal_error",
            }
        },
    )


# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(generation.router)  # Intelligent generation endpoints


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("=" * 60)
    logger.info(f" Intelia LLM Service v{settings.version}")
    logger.info("=" * 60)
    logger.info(f"Provider: {settings.llm_provider}")

    if settings.llm_provider == "huggingface":
        logger.info(f"Model: {settings.huggingface_model}")
        logger.info(
            f"HuggingFace API Key: {'[OK] Configured' if settings.huggingface_api_key else '[X] Missing'}"
        )
    elif settings.llm_provider == "vllm":
        logger.info(f"vLLM URL: {settings.vllm_url}")

    logger.info(f"Port: {settings.port}")
    logger.info(f"Metrics: {'Enabled' if settings.enable_metrics else 'Disabled'}")
    logger.info("=" * 60)

    # Validate configuration
    try:
        from app.dependencies import get_llm_client

        _ = get_llm_client()  # Validate client initialization
        logger.info("[OK] LLM client initialized successfully")
    except Exception as e:
        logger.error(f"[X] Failed to initialize LLM client: {e}")
        logger.error("Service may not work correctly. Check configuration.")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down Intelia LLM Service...")


# Run with: uvicorn app.main:app --host 0.0.0.0 --port 8081
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,  # Set to True for development
    )
