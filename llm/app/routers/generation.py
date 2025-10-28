"""
Generation Router - Intelligent LLM Generation Endpoints
Provides domain-aware LLM generation with automatic configuration
"""

import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Dict, List

from app.models.generation_schemas import (
    GenerateRequest, GenerateResponse,
    RouteRequest, RouteResponse,
    CalculateTokensRequest, CalculateTokensResponse,
    PostProcessRequest, PostProcessResponse
)
from app.config import settings
from app.dependencies import get_llm_client
from app.models.llm_client import LLMClient
from app.utils.adaptive_length import get_adaptive_length
from app.utils.post_processor import create_post_processor
from app.utils.semantic_cache import get_semantic_cache
from app.utils.model_router import get_model_router, ModelSize

# Import domain configuration (now properly within app package)
from app.domain_config.domains.aviculture.config import get_aviculture_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["generation"])


# ============================================
# POST /v1/generate - Intelligent Generation
# ============================================

@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    llm_client: LLMClient = Depends(get_llm_client)
) -> GenerateResponse:
    """
    Generate LLM completion with domain-aware configuration

    This endpoint:
    - Automatically calculates optimal max_tokens based on query complexity
    - Selects appropriate system prompts based on domain and query type
    - Applies post-processing and formatting rules
    - Adds veterinary disclaimers when appropriate

    **Example:**
    ```json
    {
        "query": "What is the weight of a Ross 308 at 21 days?",
        "domain": "aviculture",
        "language": "en",
        "query_type": "genetics_performance"
    }
    ```
    """
    try:
        logger.info(f"[GEN] Generate request: domain={request.domain}, query_len={len(request.query)}")

        # [FAST] OPTIMIZATION Phase 1: Check semantic cache first
        semantic_cache = get_semantic_cache(
            redis_host=settings.redis_host if hasattr(settings, 'redis_host') else "localhost",
            redis_port=settings.redis_port if hasattr(settings, 'redis_port') else 6379,
            redis_db=settings.redis_db if hasattr(settings, 'redis_db') else 0,
            redis_password=settings.redis_password if hasattr(settings, 'redis_password') and settings.redis_password else None,
            ttl=settings.cache_ttl if hasattr(settings, 'cache_ttl') else 3600,
            enabled=settings.cache_enabled if hasattr(settings, 'cache_enabled') else True
        )

        cache_entry = await semantic_cache.get(
            query=request.query,
            entities=request.entities,
            language=request.language,
            domain=request.domain,
            query_type=request.query_type
        )

        if cache_entry:
            # Cache hit - return cached response immediately (5ms vs 5000ms!)
            logger.info(f"[FAST] CACHE HIT: Returning cached response (~5ms vs ~5000ms LLM call)")
            return GenerateResponse(
                generated_text=cache_entry.response,
                provider=settings.llm_provider,
                model=settings.huggingface_model if settings.llm_provider == "huggingface" else "vllm",
                prompt_tokens=cache_entry.prompt_tokens,
                completion_tokens=cache_entry.completion_tokens,
                total_tokens=cache_entry.prompt_tokens + cache_entry.completion_tokens,
                complexity=cache_entry.complexity,
                calculated_max_tokens=0,  # Not recalculated for cache hits
                post_processed=True,  # Cached responses are already post-processed
                disclaimer_added=False,  # Already included in cached response
                cached=True  # Indicate this is a cached response
            )

        # Get domain configuration
        if request.domain == "aviculture":
            domain_config = get_aviculture_config()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")

        # Calculate max_tokens if not provided
        adaptive_calc = get_adaptive_length()
        calculated_max_tokens = adaptive_calc.calculate_max_tokens(
            query=request.query,
            entities=request.entities,
            query_type=request.query_type,
            context_docs=request.context_docs,
            domain=request.domain
        )
        max_tokens = request.max_tokens or calculated_max_tokens

        # Get complexity info for metadata
        complexity_info = adaptive_calc.get_complexity_info(
            query=request.query,
            entities=request.entities,
            query_type=request.query_type,
            context_docs=request.context_docs,
            domain=request.domain
        )

        # Build messages
        if request.messages:
            messages = request.messages
        else:
            # Get system prompt from domain config with terminology injection
            system_prompt = domain_config.get_system_prompt(
                query_type=request.query_type or "general_poultry",
                language=request.language,
                query=request.query,  # Pass query for terminology matching
                inject_terminology=True,  # Enable terminology injection
                max_terminology_tokens=1000  # Limit terminology to 1000 tokens
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ]

        # Get generation parameters from domain config if not provided
        domain_reqs = domain_config.get_requirements()
        temperature = request.temperature or domain_reqs.get("temperature", 0.7)
        top_p = request.top_p or 1.0

        # [FAST] OPTIMIZATION Option 3: Intelligent Model Routing (3B vs 8B)
        model_used = settings.huggingface_model  # Default
        routing_decision = None

        if settings.enable_model_routing and settings.llm_provider == "huggingface":
            # Determine query complexity and select optimal model
            import time
            routing_start = time.time()

            model_router = get_model_router(
                ab_test_ratio=settings.ab_test_ratio,
                enable_routing=True
            )

            # Determine complexity
            from app.utils.model_router import QueryComplexity
            complexity = model_router.determine_complexity(
                query=request.query,
                query_type=request.query_type,
                entities=request.entities,
                context_docs=request.context_docs
            )

            # Select model
            model_size = model_router.select_model(
                complexity=complexity,
                query=request.query
            )

            # Get model name
            if model_size == ModelSize.SMALL:
                model_used = settings.model_3b_name
                routing_decision = "3b"
            else:
                model_used = settings.model_8b_name
                routing_decision = "8b"

            routing_time = int((time.time() - routing_start) * 1000)
            logger.info(f" Model routing: {complexity.value} → {routing_decision} ({routing_time}ms)")

            # Create new LLM client with selected model (if different from default)
            if model_used != llm_client.model:
                from app.models.llm_client import HuggingFaceProvider
                llm_client = HuggingFaceProvider(
                    api_key=settings.huggingface_api_key,
                    model=model_used
                )

        # Generate completion
        logger.info(f" Generating with model={model_used}, max_tokens={max_tokens}, temperature={temperature}")
        import time
        gen_start = time.time()

        generated_text, prompt_tokens, completion_tokens = await llm_client.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=None
        )

        gen_time = int((time.time() - gen_start) * 1000)

        # Record routing stats
        if settings.enable_model_routing and routing_decision:
            model_router = get_model_router()
            model_size = ModelSize.SMALL if routing_decision == "3b" else ModelSize.LARGE
            model_router.record_usage(model_size, gen_time)

        # Post-process if requested
        disclaimer_added = False
        if request.post_process:
            # [FAST] Use cached PostProcessor from domain config (saves ~2ms per request)
            original_length = len(generated_text)
            generated_text = domain_config.post_processor.post_process_response(
                response=generated_text,
                query=request.query,
                language=request.language,
                context_docs=request.context_docs
            )

            # Check if disclaimer was added
            if len(generated_text) > original_length:
                disclaimer_added = True

            logger.info(f"[CLEAN] Post-processing applied (disclaimer_added={disclaimer_added})")

        # [FAST] OPTIMIZATION Phase 1: Store in cache for future requests
        await semantic_cache.set(
            query=request.query,
            response=generated_text,
            entities=request.entities,
            language=request.language,
            domain=request.domain,
            query_type=request.query_type or "general",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            complexity=complexity_info["complexity"]
        )

        return GenerateResponse(
            generated_text=generated_text,
            provider=settings.llm_provider,
            model=model_used if settings.llm_provider == "huggingface" else "vllm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            complexity=complexity_info["complexity"],
            calculated_max_tokens=calculated_max_tokens,
            post_processed=request.post_process,
            disclaimer_added=disclaimer_added
        )

    except Exception as e:
        logger.error(f"[ERROR] Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST /v1/generate-stream - Streaming Generation
# ============================================

@router.post("/generate-stream")
async def generate_stream(
    request: GenerateRequest,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    Generate LLM completion with streaming (Server-Sent Events)

    [FAST] OPTIMIZATION: Streaming reduces perceived latency by 90%+
    - First token: 300-500ms (vs 5000ms for complete response)
    - User sees progress in real-time
    - Better UX for long responses

    This endpoint:
    - Streams response chunks as they are generated
    - Automatically calculates optimal max_tokens based on query complexity
    - Selects appropriate system prompts based on domain and query type
    - Can optionally post-process the final response

    **Example:**
    ```json
    {
        "query": "What is the weight of a Ross 308 at 21 days?",
        "domain": "aviculture",
        "language": "en",
        "query_type": "genetics_performance"
    }
    ```

    **SSE Event Format:**
    ```
    event: start
    data: {"status": "generating", "complexity": "simple", "max_tokens": 400}

    event: chunk
    data: {"content": "The Ross 308 broiler..."}

    event: chunk
    data: {"content": " typically weighs..."}

    event: end
    data: {"prompt_tokens": 2100, "completion_tokens": 350, "total_tokens": 2450}
    ```
    """

    async def event_generator():
        try:
            logger.info(f"[GEN] Generate-stream request: domain={request.domain}, query_len={len(request.query)}")

            # Get domain configuration
            if request.domain == "aviculture":
                domain_config = get_aviculture_config()
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")

            # Calculate max_tokens if not provided
            adaptive_calc = get_adaptive_length()
            calculated_max_tokens = adaptive_calc.calculate_max_tokens(
                query=request.query,
                entities=request.entities,
                query_type=request.query_type,
                context_docs=request.context_docs,
                domain=request.domain
            )
            max_tokens = request.max_tokens or calculated_max_tokens

            # Get complexity info for metadata
            complexity_info = adaptive_calc.get_complexity_info(
                query=request.query,
                entities=request.entities,
                query_type=request.query_type,
                context_docs=request.context_docs,
                domain=request.domain
            )

            # Build messages
            if request.messages:
                messages = request.messages
            else:
                # Get system prompt from domain config with terminology injection
                system_prompt = domain_config.get_system_prompt(
                    query_type=request.query_type or "general_poultry",
                    language=request.language,
                    query=request.query,
                    inject_terminology=True,
                    max_terminology_tokens=1000
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.query}
                ]

            # Get generation parameters
            domain_reqs = domain_config.get_requirements()
            temperature = request.temperature or domain_reqs.get("temperature", 0.7)
            top_p = request.top_p or 1.0

            # Send START event with metadata
            start_data = {
                "status": "generating",
                "complexity": complexity_info["complexity"],
                "max_tokens": max_tokens,
                "provider": settings.llm_provider,
                "model": settings.huggingface_model if settings.llm_provider == "huggingface" else "vllm"
            }
            yield f"event: start\ndata: {json.dumps(start_data)}\n\n"

            logger.info(f" Streaming generation with max_tokens={max_tokens}, temperature={temperature}")

            # Stream generation
            full_text = ""
            prompt_tokens = 0
            completion_tokens = 0

            async for chunk_text, is_final, metadata in llm_client.generate_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=None
            ):
                if is_final:
                    # Final chunk - extract metadata
                    prompt_tokens = metadata.get("prompt_tokens", 0)
                    completion_tokens = metadata.get("completion_tokens", 0)
                    full_text = metadata.get("full_text", full_text)
                    break
                else:
                    # Regular chunk - stream to client
                    if chunk_text:
                        full_text += chunk_text
                        chunk_data = {"content": chunk_text}
                        yield f"event: chunk\ndata: {json.dumps(chunk_data)}\n\n"

            # Post-process if requested
            final_text = full_text
            disclaimer_added = False
            if request.post_process:
                original_length = len(full_text)
                final_text = domain_config.post_processor.post_process_response(
                    response=full_text,
                    query=request.query,
                    language=request.language,
                    context_docs=request.context_docs
                )

                # If post-processing added content (disclaimer), send it as additional chunk
                if len(final_text) > original_length:
                    disclaimer_added = True
                    added_content = final_text[original_length:]
                    chunk_data = {"content": added_content}
                    yield f"event: chunk\ndata: {json.dumps(chunk_data)}\n\n"

                logger.info(f"[CLEAN] Post-processing applied (disclaimer_added={disclaimer_added})")

            # Send END event with final metadata
            end_data = {
                "status": "complete",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "complexity": complexity_info["complexity"],
                "calculated_max_tokens": calculated_max_tokens,
                "post_processed": request.post_process,
                "disclaimer_added": disclaimer_added
            }
            yield f"event: end\ndata: {json.dumps(end_data)}\n\n"

            logger.info(f"[OK] Streaming complete: {completion_tokens} tokens generated")

        except Exception as e:
            logger.error(f"[ERROR] Streaming generation failed: {e}", exc_info=True)
            error_data = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ============================================
# POST /v1/route - Provider Routing
# ============================================

@router.post("/route", response_model=RouteResponse)
async def route(request: RouteRequest) -> RouteResponse:
    """
    Determine optimal LLM provider for query

    This endpoint analyzes the query and returns the recommended provider
    based on domain detection, query complexity, and cost optimization.

    **Example:**
    ```json
    {
        "query": "Ross 308 weight at 33 days",
        "domain": "aviculture"
    }
    ```

    Returns provider recommendation (e.g., "intelia_llama" for aviculture queries)
    """
    try:
        logger.info(f" Route request: domain={request.domain}, query={request.query[:50]}...")

        # Get domain configuration
        if request.domain == "aviculture":
            domain_config = get_aviculture_config()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")

        # Check if query is domain-specific
        is_domain_query = domain_config.is_domain_query(
            query=request.query,
            intent_result=request.intent_result
        )

        # Get provider preferences
        provider_prefs = domain_config.get_provider_preferences()

        # Route based on domain detection
        if is_domain_query:
            # Use domain-preferred provider
            if "intelia_llama" in provider_prefs and provider_prefs["intelia_llama"] > 0.8:
                provider = "intelia_llama"
                model = settings.huggingface_model
                reason = f"Domain-specific query detected ({request.domain})"
                confidence = provider_prefs["intelia_llama"]
            else:
                provider = "gpt4o"
                model = "gpt-4o"
                reason = "Domain query but preferred provider not available"
                confidence = 0.7
        else:
            # Use general provider
            provider = "gpt4o"
            model = "gpt-4o"
            reason = "General query outside domain expertise"
            confidence = 0.9

        logger.info(f"[OK] Routed to {provider}: {reason}")

        return RouteResponse(
            provider=provider,
            model=model,
            reason=reason,
            is_aviculture=is_domain_query,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"[ERROR] Routing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST /v1/calculate-tokens - Token Calculation
# ============================================

@router.post("/calculate-tokens", response_model=CalculateTokensResponse)
async def calculate_tokens(request: CalculateTokensRequest) -> CalculateTokensResponse:
    """
    Calculate optimal max_tokens for query

    Analyzes query complexity and returns recommended max_tokens with
    detailed complexity breakdown.

    **Example:**
    ```json
    {
        "query": "Compare Ross 308 and Cobb 500 at 21 days",
        "query_type": "comparative",
        "entities": {"breed": "Ross 308, Cobb 500", "age_days": 21}
    }
    ```

    Returns calculated max_tokens and complexity analysis.
    """
    try:
        logger.info(f" Calculate tokens: query_len={len(request.query)}")

        adaptive_calc = get_adaptive_length()
        complexity_info = adaptive_calc.get_complexity_info(
            query=request.query,
            entities=request.entities,
            query_type=request.query_type,
            context_docs=request.context_docs,
            domain=request.domain
        )

        logger.info(f"[OK] Calculated: {complexity_info['max_tokens']} tokens (complexity={complexity_info['complexity']})")

        return CalculateTokensResponse(
            max_tokens=complexity_info["max_tokens"],
            complexity=complexity_info["complexity"],
            token_range=complexity_info["token_range"],
            factors=complexity_info["factors"]
        )

    except Exception as e:
        logger.error(f"[ERROR] Token calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST /v1/post-process - Response Post-Processing
# ============================================

@router.post("/post-process", response_model=PostProcessResponse)
async def post_process(request: PostProcessRequest) -> PostProcessResponse:
    """
    Post-process LLM response

    Applies formatting cleanup and adds disclaimers when appropriate.

    **Example:**
    ```json
    {
        "response": "**Header:** Raw LLM output\\n\\n1. Item one\\n2. Item two",
        "query": "What are symptoms of coccidiosis?",
        "language": "en",
        "domain": "aviculture"
    }
    ```

    Returns cleaned response with disclaimer if health-related.
    """
    try:
        logger.info(f" Post-process request: response_len={len(request.response)}")

        # Get domain configuration
        if request.domain == "aviculture":
            domain_config = get_aviculture_config()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")

        # [FAST] OPTIMIZATION: Use cached PostProcessor from domain config (saves ~2ms per request)
        # The PostProcessor is cached with @cached_property and includes pre-compiled regex patterns
        post_processor = domain_config.post_processor

        # Check if veterinary before processing
        is_veterinary = post_processor.is_veterinary_query(
            query=request.query,
            context_docs=request.context_docs
        )

        # Process response
        original_length = len(request.response)
        processed_text = post_processor.post_process_response(
            response=request.response,
            query=request.query,
            language=request.language,
            context_docs=request.context_docs
        )

        # Check if disclaimer was added
        disclaimer_added = request.add_disclaimer and len(processed_text) > original_length

        logger.info(f"[OK] Post-processed (veterinary={is_veterinary}, disclaimer={disclaimer_added})")

        return PostProcessResponse(
            processed_text=processed_text,
            disclaimer_added=disclaimer_added,
            is_veterinary=is_veterinary
        )

    except Exception as e:
        logger.error(f"[ERROR] Post-processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# GET /v1/model-routing/stats - A/B Test Metrics
# ============================================

@router.get("/model-routing/stats")
async def get_model_routing_stats():
    """
    Get model routing statistics and A/B test metrics

    Returns detailed metrics about model selection distribution,
    performance improvements, and cost savings.

    **Example Response:**
    ```json
    {
        "total_requests": 1543,
        "model_distribution": {
            "3b": {
                "count": 924,
                "percentage": 59.9,
                "avg_latency_ms": 2650
            },
            "8b": {
                "count": 619,
                "percentage": 40.1,
                "avg_latency_ms": 4380
            }
        },
        "average_latency_ms": 3300,
        "baseline_latency_ms": 4500,
        "latency_improvement_pct": 26.7,
        "estimated_cost_savings_pct": 29.9,
        "ab_test_ratio": 0.5,
        "routing_enabled": true
    }
    ```
    """
    try:
        if not settings.enable_model_routing:
            return {
                "routing_enabled": False,
                "message": "Model routing is disabled. Set ENABLE_MODEL_ROUTING=true to enable."
            }

        model_router = get_model_router()
        stats = model_router.get_stats()

        logger.info(f" Model routing stats requested: {stats['total_requests']} requests")

        return stats

    except Exception as e:
        logger.error(f"[ERROR] Failed to get routing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# POST /v1/model-routing/reset - Reset Stats
# ============================================

@router.post("/model-routing/reset")
async def reset_model_routing_stats():
    """
    Reset model routing statistics

    Clears all accumulated routing stats. Useful for starting
    a fresh A/B test period.

    **Returns:**
    ```json
    {
        "status": "success",
        "message": "Model routing stats reset"
    }
    ```
    """
    try:
        if not settings.enable_model_routing:
            return {
                "status": "disabled",
                "message": "Model routing is disabled"
            }

        model_router = get_model_router()
        model_router.reset_stats()

        logger.info(" Model routing stats reset")

        return {
            "status": "success",
            "message": "Model routing stats reset"
        }

    except Exception as e:
        logger.error(f"[ERROR] Failed to reset routing stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
