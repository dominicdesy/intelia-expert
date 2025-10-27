"""
Generation Router - Intelligent LLM Generation Endpoints
Provides domain-aware LLM generation with automatic configuration
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
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

# Import domain configuration
# Using relative import from project root
import os
import sys

# Add parent directory to path to find config module
llm_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if llm_root not in sys.path:
    sys.path.insert(0, llm_root)

from config.aviculture.config import get_aviculture_config

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
        logger.info(f"📝 Generate request: domain={request.domain}, query_len={len(request.query)}")

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
            # Get system prompt from domain config
            system_prompt = domain_config.get_system_prompt(
                query_type=request.query_type or "general_poultry",
                language=request.language
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ]

        # Get generation parameters from domain config if not provided
        domain_reqs = domain_config.get_requirements()
        temperature = request.temperature or domain_reqs.get("temperature", 0.7)
        top_p = request.top_p or 1.0

        # Generate completion
        logger.info(f"🤖 Generating with max_tokens={max_tokens}, temperature={temperature}")
        generated_text, prompt_tokens, completion_tokens = await llm_client.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=None
        )

        # Post-process if requested
        disclaimer_added = False
        if request.post_process:
            post_processor = create_post_processor(
                veterinary_terms=domain_config.veterinary_terms,
                language_messages=domain_config.languages
            )

            original_length = len(generated_text)
            generated_text = post_processor.post_process_response(
                response=generated_text,
                query=request.query,
                language=request.language,
                context_docs=request.context_docs
            )

            # Check if disclaimer was added
            if len(generated_text) > original_length:
                disclaimer_added = True

            logger.info(f"✨ Post-processing applied (disclaimer_added={disclaimer_added})")

        return GenerateResponse(
            generated_text=generated_text,
            provider=settings.llm_provider,
            model=settings.huggingface_model if settings.llm_provider == "huggingface" else "vllm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            complexity=complexity_info["complexity"],
            calculated_max_tokens=calculated_max_tokens,
            post_processed=request.post_process,
            disclaimer_added=disclaimer_added
        )

    except Exception as e:
        logger.error(f"❌ Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.info(f"🧭 Route request: domain={request.domain}, query={request.query[:50]}...")

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

        logger.info(f"✅ Routed to {provider}: {reason}")

        return RouteResponse(
            provider=provider,
            model=model,
            reason=reason,
            is_aviculture=is_domain_query,
            confidence=confidence
        )

    except Exception as e:
        logger.error(f"❌ Routing failed: {e}", exc_info=True)
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
        logger.info(f"🔢 Calculate tokens: query_len={len(request.query)}")

        adaptive_calc = get_adaptive_length()
        complexity_info = adaptive_calc.get_complexity_info(
            query=request.query,
            entities=request.entities,
            query_type=request.query_type,
            context_docs=request.context_docs,
            domain=request.domain
        )

        logger.info(f"✅ Calculated: {complexity_info['max_tokens']} tokens (complexity={complexity_info['complexity']})")

        return CalculateTokensResponse(
            max_tokens=complexity_info["max_tokens"],
            complexity=complexity_info["complexity"],
            token_range=complexity_info["token_range"],
            factors=complexity_info["factors"]
        )

    except Exception as e:
        logger.error(f"❌ Token calculation failed: {e}", exc_info=True)
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
        logger.info(f"🧹 Post-process request: response_len={len(request.response)}")

        # Get domain configuration
        if request.domain == "aviculture":
            domain_config = get_aviculture_config()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported domain: {request.domain}")

        # Create post-processor
        post_processor = create_post_processor(
            veterinary_terms=domain_config.veterinary_terms,
            language_messages=domain_config.languages
        )

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

        logger.info(f"✅ Post-processed (veterinary={is_veterinary}, disclaimer={disclaimer_added})")

        return PostProcessResponse(
            processed_text=processed_text,
            disclaimer_added=disclaimer_added,
            is_veterinary=is_veterinary
        )

    except Exception as e:
        logger.error(f"❌ Post-processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
