# -*- coding: utf-8 -*-
"""
llm_router.py - Intelligent Multi-LLM Router
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
llm_router.py - Intelligent Multi-LLM Router
Routes queries to optimal LLM based on complexity and type

COST OPTIMIZATION: -70% via intelligent routing
- DeepSeek ($0.55/1M): Simple queries, direct PostgreSQL hits
- Claude 3.5 Sonnet ($3/1M): Complex RAG, synthesis required
- GPT-4o ($15/1M): Edge cases, fallback
"""

import os
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from enum import Enum
from openai import AsyncOpenAI

from generation.adaptive_length import get_adaptive_length

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers with cost per 1M tokens"""

    INTELIA_LLAMA = "intelia-llama"  # $0.20/1M - Domain-specific aviculture
    DEEPSEEK = "deepseek"  # $0.55/1M - Simple queries
    CLAUDE_35_SONNET = "claude"  # $3/1M - Complex RAG
    GPT_4O = "gpt4o"  # $15/1M - Edge cases


class LLMRouter:
    """
    Routes queries to optimal LLM based on:
    - Query complexity
    - Available context (PostgreSQL vs Weaviate)
    - Required capabilities

    Cost optimization: -70% by using cheaper models when appropriate

    Example:
        router = LLMRouter()
        provider = router.route_query(query, context_docs, intent_result)
        response = await router.generate(provider, messages)
    """

    def __init__(self) -> None:
        """Initialize LLM clients and routing configuration"""

        # Initialize OpenAI client for GPT-4o
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize DeepSeek client (OpenAI-compatible)
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_client = None
        if deepseek_api_key:
            try:
                self.deepseek_client = AsyncOpenAI(
                    api_key=deepseek_api_key, base_url="https://api.deepseek.com/v1"
                )
                logger.info("✅ DeepSeek client initialized")
            except Exception as e:
                logger.warning(f"⚠️ DeepSeek client initialization failed: {e}")
        else:
            logger.info("ℹ️ DeepSeek API key not configured, will use GPT-4o fallback")

        # Initialize Claude client
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.claude_client = None
        if anthropic_api_key:
            try:
                from anthropic import AsyncAnthropic

                self.claude_client = AsyncAnthropic(api_key=anthropic_api_key)
                logger.info("✅ Claude 3.5 Sonnet client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Claude client initialization failed: {e}")
        else:
            logger.info("ℹ️ Anthropic API key not configured, will use GPT-4o fallback")

        # Initialize Intelia Llama service (internal)
        self.llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm:8081")
        self.llm_service_enabled = os.getenv("ENABLE_INTELIA_LLAMA", "true").lower() == "true"
        if self.llm_service_enabled:
            logger.info(f"✅ Intelia Llama service configured: {self.llm_service_url}")
        else:
            logger.info("ℹ️ Intelia Llama service disabled")

        # Routing configuration
        self.routing_enabled = os.getenv("ENABLE_LLM_ROUTING", "true").lower() == "true"
        self.default_provider = os.getenv(
            "DEFAULT_LLM_PROVIDER", LLMProvider.GPT_4O.value
        )

        # Cost tracking per provider
        self.usage_stats = {
            LLMProvider.INTELIA_LLAMA.value: {"calls": 0, "tokens": 0, "cost": 0.0},
            LLMProvider.DEEPSEEK.value: {"calls": 0, "tokens": 0, "cost": 0.0},
            LLMProvider.CLAUDE_35_SONNET.value: {"calls": 0, "tokens": 0, "cost": 0.0},
            LLMProvider.GPT_4O.value: {"calls": 0, "tokens": 0, "cost": 0.0},
        }

        # Initialize adaptive length calculator
        self.adaptive_length = get_adaptive_length()

        logger.info(
            f"✅ Multi-LLM Router initialized (routing_enabled={self.routing_enabled}, "
            f"default={self.default_provider})"
        )

    def route_query(
        self, query: str, context_docs: List[Dict], intent_result: Optional[Dict] = None
    ) -> LLMProvider:
        """
        Determine optimal LLM for this query

        Routing logic:
        0. Domain-specific aviculture (if available) → Intelia Llama
        1. PostgreSQL direct hit (score >0.9, simple) → DeepSeek
        2. Weaviate RAG (multiple docs, synthesis) → Claude 3.5 Sonnet
        3. Complex queries (comparative, temporal) → Claude 3.5 Sonnet
        4. Edge cases / fallback → GPT-4o

        Args:
            query: User query
            context_docs: Retrieved context documents
            intent_result: Intent analysis result

        Returns:
            LLMProvider to use for generation
        """

        # If routing disabled, use default provider
        if not self.routing_enabled:
            logger.debug(f"🔀 Routing disabled, using default: {self.default_provider}")
            return LLMProvider(self.default_provider)

        # Rule 0: Domain-specific aviculture → Intelia Llama (highest priority)
        if self.llm_service_enabled and self._is_aviculture_query(query, intent_result):
            logger.info("🔀 Route → Intelia Llama (domain-specific aviculture)")
            return LLMProvider.INTELIA_LLAMA

        # Rule 1: PostgreSQL direct hit → DeepSeek
        if context_docs and len(context_docs) > 0:
            top_doc = context_docs[0]
            top_score = top_doc.get("score", 0)
            source = top_doc.get("metadata", {}).get("source", "")

            if source == "postgresql" and top_score > 0.9 and self.deepseek_client:
                logger.info(
                    f"🔀 Route → DeepSeek (PostgreSQL direct hit, score={top_score:.2f})"
                )
                return LLMProvider.DEEPSEEK

        # Rule 2: Weaviate RAG (multiple documents) → Claude 3.5 Sonnet
        if context_docs and len(context_docs) >= 2:
            sources = [doc.get("metadata", {}).get("source") for doc in context_docs]
            if "weaviate" in sources and self.claude_client:
                logger.info(
                    f"🔀 Route → Claude 3.5 Sonnet (Weaviate RAG, {len(context_docs)} docs)"
                )
                return LLMProvider.CLAUDE_35_SONNET

        # Rule 3: Complex queries (comparative, temporal, calculation) → Claude
        if intent_result and self.claude_client:
            query_type = intent_result.get("intent_type", "")
            if query_type in ["comparative", "temporal", "calculation"]:
                logger.info(f"🔀 Route → Claude 3.5 Sonnet ({query_type} query)")
                return LLMProvider.CLAUDE_35_SONNET

        # Rule 4: Default fallback → GPT-4o
        logger.info("🔀 Route → GPT-4o (default/fallback)")
        return LLMProvider.GPT_4O

    def _is_aviculture_query(self, query: str, intent_result: Optional[Dict] = None) -> bool:
        """
        Detect if query is domain-specific aviculture

        Args:
            query: User query
            intent_result: Intent analysis result

        Returns:
            True if query is aviculture-related
        """
        query_lower = query.lower()

        # Domain keywords (aviculture, poultry, livestock)
        aviculture_keywords = [
            # French
            "poulet", "poule", "pondeuse", "broiler", "poussin", "volaille",
            "aviculture", "élevage", "mortalité", "ponte", "aliment", "eau",
            "biosécurité", "vaccination", "maladie", "coccidiose", "newcastle",
            "gumboro", "bronchite", "marek", "ventilation", "température",
            "litière", "densité", "indice de conversion", "icv", "poids vif",
            # English
            "chicken", "hen", "layer", "broiler", "chick", "poultry",
            "bird", "flock", "mortality", "egg production", "feed", "water",
            "biosecurity", "vaccine", "disease", "coccidiosis",
            # Spanish/Portuguese
            "pollo", "gallina", "ave", "avicultura", "mortalidad",
        ]

        # Breed names (strong indicators of aviculture queries)
        breed_keywords = [
            "ross", "cobb", "hubbard", "isa", "lohmann", "hy-line",
            "aviagen", "novogen", "dekalb", "shaver", "bovans",
        ]

        # Performance metrics (when combined with age/sex, indicate aviculture)
        metric_keywords = [
            "weight", "poids", "fcr", "feed conversion", "indice de conversion",
            "egg production", "ponte", "mortality", "mortalité",
            "body weight", "poids vif", "gain de poids",
        ]

        # Check if query contains aviculture keywords
        if any(keyword in query_lower for keyword in aviculture_keywords):
            return True

        # Check for breed names (strong indicator)
        if any(breed in query_lower for breed in breed_keywords):
            logger.debug(f"🐔 Breed name detected in query → aviculture")
            return True

        # Check for performance metrics with age indicators
        has_metric = any(metric in query_lower for metric in metric_keywords)
        has_age = any(age_term in query_lower for age_term in ["day", "days", "week", "weeks", "jours", "jour", "semaine"])
        if has_metric and has_age:
            logger.debug(f"🐔 Metric + age detected in query → aviculture")
            return True

        # Check domain from intent result
        if intent_result:
            domain = intent_result.get("domain", "")
            intent_type = intent_result.get("intent", "")

            # Check for aviculture-related domains
            if domain in ["aviculture", "poultry", "livestock", "genetics_performance", "nutrition", "health", "housing"]:
                logger.debug(f"🐔 Domain '{domain}' detected → aviculture")
                return True

            # Check for performance-related intents
            if intent_type in ["performance_query", "genetics_query", "nutrition_query", "health_query"]:
                logger.debug(f"🐔 Intent '{intent_type}' detected → aviculture")
                return True

        return False

    async def generate(
        self,
        provider: LLMProvider,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None,
        entities: Optional[Dict] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        domain: Optional[str] = None,
    ) -> str:
        """
        Generate response using specified LLM provider

        Args:
            provider: LLM provider to use
            messages: Chat messages (OpenAI format)
            temperature: Generation temperature
            max_tokens: Max tokens to generate (if None, will use adaptive calculation)
            query: User query (for adaptive length calculation)
            entities: Extracted entities (for adaptive length)
            query_type: Type of query (for adaptive length)
            context_docs: Retrieved context documents (for adaptive length)
            domain: Query domain (for adaptive length)

        Returns:
            Generated response text

        Raises:
            Exception: If generation fails and fallback also fails
        """

        # Calculate adaptive max_tokens if not explicitly provided
        if max_tokens is None:
            if query is not None:
                max_tokens = self.adaptive_length.calculate_max_tokens(
                    query=query,
                    entities=entities or {},
                    query_type=query_type or "standard",
                    context_docs=context_docs or [],
                    domain=domain,
                )
                logger.info(f"📏 Adaptive max_tokens: {max_tokens}")
            else:
                max_tokens = 900  # Default fallback
                logger.warning("⚠️ No query provided for adaptive length, using default 900")

        try:
            if provider == LLMProvider.INTELIA_LLAMA and self.llm_service_enabled:
                return await self._generate_intelia_llama(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    query=query,
                    entities=entities,
                    query_type=query_type,
                    context_docs=context_docs,
                    domain=domain or "aviculture"
                )
            elif provider == LLMProvider.DEEPSEEK and self.deepseek_client:
                return await self._generate_deepseek(messages, temperature, max_tokens)
            elif provider == LLMProvider.CLAUDE_35_SONNET and self.claude_client:
                return await self._generate_claude(messages, temperature, max_tokens)
            else:  # GPT_4O or fallback if provider not available
                if provider != LLMProvider.GPT_4O:
                    logger.warning(
                        f"⚠️ {provider.value} not available, falling back to GPT-4o"
                    )
                return await self._generate_gpt4o(messages, temperature, max_tokens)

        except Exception as e:
            logger.error(
                f"❌ {provider.value} generation failed: {e}, fallback to GPT-4o"
            )
            # Fallback to GPT-4o if not already using it
            if provider != LLMProvider.GPT_4O:
                return await self._generate_gpt4o(messages, temperature, max_tokens)
            raise

    async def generate_stream(
        self,
        provider: LLMProvider,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None,
        entities: Optional[Dict] = None,
        query_type: Optional[str] = None,
        context_docs: Optional[List[Dict]] = None,
        domain: Optional[str] = None,
        language: str = "en",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate response using specified LLM provider with streaming (Server-Sent Events)

        Args:
            provider: LLM provider to use
            messages: Chat messages (OpenAI format)
            temperature: Generation temperature
            max_tokens: Max tokens to generate (if None, will use adaptive calculation)
            query: User query (for adaptive length calculation)
            entities: Extracted entities (for adaptive length)
            query_type: Type of query (for adaptive length)
            context_docs: Retrieved context documents (for adaptive length)
            domain: Query domain (for adaptive length)
            language: Response language

        Yields:
            Dict events from streaming endpoint (start, chunk, end, error)
        """

        # Calculate adaptive max_tokens if not explicitly provided
        if max_tokens is None:
            if query is not None:
                max_tokens = self.adaptive_length.calculate_max_tokens(
                    query=query,
                    entities=entities or {},
                    query_type=query_type or "standard",
                    context_docs=context_docs or [],
                    domain=domain,
                )
                logger.info(f"[RULE] Adaptive max_tokens: {max_tokens}")
            else:
                max_tokens = 900  # Default fallback
                logger.warning("[WARNING] No query provided for adaptive length, using default 900")

        try:
            # Route to appropriate streaming provider
            if provider == LLMProvider.INTELIA_LLAMA and self.llm_service_enabled:
                async for event in self._generate_intelia_llama_stream(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    query=query,
                    entities=entities,
                    query_type=query_type,
                    context_docs=context_docs,
                    domain=domain or "aviculture",
                    language=language
                ):
                    yield event

            elif provider == LLMProvider.DEEPSEEK:
                logger.info("[STREAM] Using DeepSeek streaming")
                yield {"event": "start", "provider": "deepseek"}
                async for chunk in self._generate_deepseek_stream(messages, temperature, max_tokens):
                    yield {"event": "chunk", "content": chunk}
                yield {"event": "end", "total_tokens": 0}

            elif provider == LLMProvider.CLAUDE_35_SONNET:
                logger.info("[STREAM] Using Claude 3.5 Sonnet streaming")
                yield {"event": "start", "provider": "claude"}
                async for chunk in self._generate_claude_stream(messages, temperature, max_tokens):
                    yield {"event": "chunk", "content": chunk}
                yield {"event": "end", "total_tokens": 0}

            elif provider == LLMProvider.GPT_4O:
                logger.info("[STREAM] Using GPT-4o streaming")
                yield {"event": "start", "provider": "gpt4o"}
                async for chunk in self._generate_gpt4o_stream(messages, temperature, max_tokens):
                    yield {"event": "chunk", "content": chunk}
                yield {"event": "end", "total_tokens": 0}

            else:
                # Fallback: use non-streaming generation and yield as single chunk
                logger.warning(f"[WARNING] {provider.value} does not support streaming, falling back to non-streaming")
                text = await self.generate(
                    provider=provider,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    query=query,
                    entities=entities,
                    query_type=query_type,
                    context_docs=context_docs,
                    domain=domain
                )
                # Yield single event with full text
                yield {"event": "chunk", "content": text}
                yield {"event": "end", "total_tokens": 0}

        except Exception as e:
            logger.error(f"[ERROR] {provider.value} streaming failed: {e}")
            yield {"event": "error", "error": str(e)}

    async def _generate_intelia_llama_stream(
        self, messages: List[Dict], temperature: float, max_tokens: int,
        query: Optional[str] = None, entities: Optional[Dict] = None,
        query_type: Optional[str] = None, context_docs: Optional[List[Dict]] = None,
        domain: str = "aviculture", language: str = "en"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate using Intelia Llama with streaming (Server-Sent Events)

        Yields event dictionaries with:
        - event="start": Generation started with metadata
        - event="chunk": Token chunk with content
        - event="end": Generation complete with final metadata
        - event="error": Error occurred
        """
        import time
        from generation.llm_service_client import get_llm_service_client

        start_time = time.time()

        try:
            # Get LLM service client
            llm_client = get_llm_service_client(base_url=self.llm_service_url)

            # Extract query from messages if not provided
            if query is None and messages:
                # Get last user message as query
                user_messages = [m for m in messages if m["role"] == "user"]
                if user_messages:
                    query = user_messages[-1]["content"]

            # Stream from /v1/generate-stream with terminology injection
            total_chunks = 0
            prompt_tokens = 0
            completion_tokens = 0

            async for event in llm_client.generate_stream(
                query=query or "",
                domain=domain,
                language=language,
                entities=entities,
                query_type=query_type,
                context_docs=context_docs,
                temperature=temperature,
                max_tokens=max_tokens,
                post_process=True,
                add_disclaimer=True
            ):
                total_chunks += 1

                # Track token counts from events
                if event.get("event") == "start":
                    prompt_tokens = event.get("prompt_tokens", 0)
                elif event.get("event") == "end":
                    completion_tokens = event.get("completion_tokens", 0)

                yield event

            duration = time.time() - start_time

            # Calculate cost and track usage
            tokens = prompt_tokens + completion_tokens
            cost = tokens / 1_000_000 * 0.20  # $0.20 per 1M tokens

            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["calls"] += 1
            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["tokens"] += tokens
            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["cost"] += cost

            # Track Prometheus metrics
            try:
                from monitoring.prometheus_metrics import track_llm_call
                track_llm_call(
                    model="llama-3.1-8b-instruct",
                    provider="intelia-llama",
                    feature="chat-stream",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    duration=duration,
                    status="success"
                )
            except Exception as e:
                logger.debug(f"Failed to track Prometheus metrics: {e}")

            logger.info(
                f"[OK] Intelia Llama Stream: {tokens} tokens, ${cost:.4f}, {duration:.2f}s, {total_chunks} chunks"
            )

        except Exception as e:
            logger.error(f"[ERROR] Intelia Llama streaming error: {e}")
            yield {"event": "error", "error": str(e)}

    async def _generate_intelia_llama(
        self, messages: List[Dict], temperature: float, max_tokens: int,
        query: Optional[str] = None, entities: Optional[Dict] = None,
        query_type: Optional[str] = None, context_docs: Optional[List[Dict]] = None,
        domain: str = "aviculture", language: str = "en"
    ) -> str:
        """
        Generate using Intelia Llama (internal service with terminology injection, $0.20/1M)

        This method now uses the LLMServiceClient to call /v1/generate endpoint
        which includes intelligent terminology injection (1,580 terms).
        """

        import time
        from generation.llm_service_client import get_llm_service_client

        start_time = time.time()

        try:
            # Get LLM service client
            llm_client = get_llm_service_client(base_url=self.llm_service_url)

            # Extract query from messages if not provided
            if query is None and messages:
                # Get last user message as query
                user_messages = [m for m in messages if m["role"] == "user"]
                if user_messages:
                    query = user_messages[-1]["content"]

            # Call /v1/generate with terminology injection
            generated_text, prompt_tokens, completion_tokens, metadata = await llm_client.generate(
                query=query or "",
                domain=domain,
                language=language,
                entities=entities,
                query_type=query_type,
                context_docs=context_docs,
                temperature=temperature,
                max_tokens=max_tokens,
                post_process=True,
                add_disclaimer=True
            )

            duration = time.time() - start_time

            # Calculate cost and track usage
            tokens = prompt_tokens + completion_tokens
            cost = tokens / 1_000_000 * 0.20  # $0.20 per 1M tokens

            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["calls"] += 1
            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["tokens"] += tokens
            self.usage_stats[LLMProvider.INTELIA_LLAMA.value]["cost"] += cost

            # Track Prometheus metrics
            try:
                from monitoring.prometheus_metrics import track_llm_call
                track_llm_call(
                    model=metadata.get("model", "llama-3.1-8b-instruct"),
                    provider="intelia-llama",
                    feature="chat",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    duration=duration,
                    status="success"
                )
            except Exception as e:
                logger.debug(f"Failed to track Prometheus metrics: {e}")

            logger.info(
                f"✅ Intelia Llama: {tokens} tokens, ${cost:.4f}, {duration:.2f}s "
                f"(terminology: {metadata.get('terminology_injected', False)})"
            )

            return generated_text

        except Exception as e:
            logger.error(f"❌ Intelia Llama service error: {e}")
            raise

    async def _generate_deepseek(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate using DeepSeek ($0.55/1M)"""

        import time
        start_time = time.time()

        response = await self.deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        duration = time.time() - start_time

        # Track usage
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        tokens = response.usage.total_tokens
        cost = tokens / 1_000_000 * 0.55  # $0.55 per 1M tokens

        self.usage_stats[LLMProvider.DEEPSEEK.value]["calls"] += 1
        self.usage_stats[LLMProvider.DEEPSEEK.value]["tokens"] += tokens
        self.usage_stats[LLMProvider.DEEPSEEK.value]["cost"] += cost

        # Track Prometheus metrics
        try:
            from monitoring.prometheus_metrics import track_llm_call
            track_llm_call(
                model="deepseek-chat",
                provider="deepseek",
                feature="chat",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                duration=duration,
                status="success"
            )
        except Exception as e:
            logger.debug(f"Failed to track Prometheus metrics: {e}")

        logger.info(f"✅ DeepSeek: {tokens} tokens, ${cost:.4f}")

        return response.choices[0].message.content

    async def _generate_claude(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate using Claude 3.5 Sonnet ($3/1M)"""

        import time
        start_time = time.time()

        # Convert OpenAI format to Anthropic format
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] != "system"
        ]

        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        response = await self.claude_client.messages.create(
            model=model,
            system=system_msg,
            messages=user_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        duration = time.time() - start_time

        # Track usage
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        tokens = prompt_tokens + completion_tokens
        cost = tokens / 1_000_000 * 3.0  # $3 per 1M tokens

        self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["calls"] += 1
        self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["tokens"] += tokens
        self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["cost"] += cost

        # Track Prometheus metrics
        try:
            from monitoring.prometheus_metrics import track_llm_call
            track_llm_call(
                model=model,
                provider="anthropic",
                feature="chat",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                duration=duration,
                status="success"
            )
        except Exception as e:
            logger.debug(f"Failed to track Prometheus metrics: {e}")

        logger.info(f"✅ Claude 3.5 Sonnet: {tokens} tokens, ${cost:.4f}")

        return response.content[0].text

    async def _generate_gpt4o(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> str:
        """Generate using GPT-4o ($15/1M)"""

        import time
        start_time = time.time()

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        duration = time.time() - start_time

        # Track usage
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        tokens = response.usage.total_tokens
        cost = tokens / 1_000_000 * 15.0  # $15 per 1M tokens

        self.usage_stats[LLMProvider.GPT_4O.value]["calls"] += 1
        self.usage_stats[LLMProvider.GPT_4O.value]["tokens"] += tokens
        self.usage_stats[LLMProvider.GPT_4O.value]["cost"] += cost

        # Track Prometheus metrics
        try:
            from monitoring.prometheus_metrics import track_llm_call
            track_llm_call(
                model="gpt-4o",
                provider="openai",
                feature="chat",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost,
                duration=duration,
                status="success"
            )
        except Exception as e:
            logger.debug(f"Failed to track Prometheus metrics: {e}")

        logger.info(f"✅ GPT-4o: {tokens} tokens, ${cost:.4f}")

        return response.choices[0].message.content

    async def _generate_deepseek_stream(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Generate using DeepSeek with streaming"""
        import time
        start_time = time.time()

        try:
            stream = await self.deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            full_text = ""
            prompt_tokens = 0
            completion_tokens = 0

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_text += content
                        completion_tokens += 1
                        yield content

            duration = time.time() - start_time

            # Estimate tokens (no usage info in streaming)
            tokens = len(full_text.split()) * 1.3  # Rough estimate
            cost = tokens / 1_000_000 * 0.55

            self.usage_stats[LLMProvider.DEEPSEEK.value]["calls"] += 1
            self.usage_stats[LLMProvider.DEEPSEEK.value]["tokens"] += int(tokens)
            self.usage_stats[LLMProvider.DEEPSEEK.value]["cost"] += cost

            logger.info(f"✅ DeepSeek (streaming): ~{int(tokens)} tokens, ${cost:.4f}")

        except Exception as e:
            logger.error(f"DeepSeek streaming error: {e}")
            raise

    async def _generate_claude_stream(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Generate using Claude 3.5 Sonnet with streaming"""
        import time
        start_time = time.time()

        try:
            # Convert OpenAI format to Anthropic format
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] != "system"
            ]

            model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

            async with self.claude_client.messages.stream(
                model=model,
                system=system_msg,
                messages=user_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                full_text = ""
                async for text in stream.text_stream:
                    full_text += text
                    yield text

                # Get final message for usage stats
                final_message = await stream.get_final_message()
                prompt_tokens = final_message.usage.input_tokens
                completion_tokens = final_message.usage.output_tokens
                tokens = prompt_tokens + completion_tokens
                cost = tokens / 1_000_000 * 3.0

                duration = time.time() - start_time

                self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["calls"] += 1
                self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["tokens"] += tokens
                self.usage_stats[LLMProvider.CLAUDE_35_SONNET.value]["cost"] += cost

                logger.info(f"✅ Claude 3.5 Sonnet (streaming): {tokens} tokens, ${cost:.4f}")

        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            raise

    async def _generate_gpt4o_stream(
        self, messages: List[Dict], temperature: float, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Generate using GPT-4o with streaming"""
        import time
        start_time = time.time()

        try:
            stream = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            full_text = ""
            prompt_tokens = 0
            completion_tokens = 0

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_text += content
                        completion_tokens += 1
                        yield content

            duration = time.time() - start_time

            # Estimate tokens (no usage info in streaming)
            tokens = len(full_text.split()) * 1.3  # Rough estimate
            cost = tokens / 1_000_000 * 15.0

            self.usage_stats[LLMProvider.GPT_4O.value]["calls"] += 1
            self.usage_stats[LLMProvider.GPT_4O.value]["tokens"] += int(tokens)
            self.usage_stats[LLMProvider.GPT_4O.value]["cost"] += cost

            logger.info(f"✅ GPT-4o (streaming): ~{int(tokens)} tokens, ${cost:.4f}")

        except Exception as e:
            logger.error(f"GPT-4o streaming error: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics and cost savings

        Returns:
            Dict with provider stats, totals, and savings calculations
        """

        total_calls = sum(s["calls"] for s in self.usage_stats.values())
        total_tokens = sum(s["tokens"] for s in self.usage_stats.values())
        total_cost = sum(s["cost"] for s in self.usage_stats.values())

        # Calculate what it would cost with 100% GPT-4o
        cost_if_gpt4o_only = total_tokens / 1_000_000 * 15.0
        savings = cost_if_gpt4o_only - total_cost
        savings_pct = (
            (savings / cost_if_gpt4o_only * 100) if cost_if_gpt4o_only > 0 else 0
        )

        # Calculate average cost per 1M tokens
        avg_cost_per_1m = (
            (total_cost / total_tokens * 1_000_000) if total_tokens > 0 else 0
        )

        return {
            "providers": self.usage_stats,
            "total": {
                "calls": total_calls,
                "tokens": total_tokens,
                "cost": round(total_cost, 4),
                "avg_cost_per_1m": round(avg_cost_per_1m, 2),
                "cost_if_gpt4o_only": round(cost_if_gpt4o_only, 4),
                "savings": round(savings, 4),
                "savings_pct": round(savings_pct, 1),
            },
            "routing_enabled": self.routing_enabled,
            "providers_available": {
                "intelia_llama": self.llm_service_enabled,
                "deepseek": self.deepseek_client is not None,
                "claude": self.claude_client is not None,
                "gpt4o": True,
            },
        }


# Singleton instance for global access
_router_instance = None


def get_llm_router() -> LLMRouter:
    """
    Get or create singleton LLM Router instance

    Returns:
        LLMRouter singleton instance
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


__all__ = ["LLMRouter", "LLMProvider", "get_llm_router"]
