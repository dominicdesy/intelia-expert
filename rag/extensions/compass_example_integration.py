"""
Compass Integration Example - How to integrate into existing RAG pipeline
Version: 1.0.0
Date: 2025-10-30
Description: Complete example showing how to add Compass support to your RAG engine
"""

import logging
from typing import Dict, List, Optional, Any
from extensions.compass_extension import get_compass_extension

logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Simple Integration in Query Processing
# ============================================================================

async def process_query_with_compass(
    query: str,
    user_token: str,
    existing_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Example: Add Compass enrichment to your query processing pipeline

    Args:
        query: User query
        user_token: User's JWT token
        existing_context: Context from RAG retrieval

    Returns:
        Dictionary with enriched context and metadata
    """
    # Get Compass extension
    compass = get_compass_extension()

    # Check if this is a Compass query
    if compass.is_compass_query(query):
        logger.info(f"Compass query detected: {query}")

        # Enrich context with real-time barn data
        enriched = await compass.enrich_context(
            query=query,
            user_token=user_token,
            existing_context=existing_context
        )

        return {
            "query": query,
            "context": enriched["context"],
            "is_compass": True,
            "barn_data": enriched["barn_data"],
            "metadata": {
                "requested_barns": enriched.get("requested_barns"),
                "requested_data_types": enriched.get("requested_data_types")
            }
        }
    else:
        # Not a Compass query, return normal context
        return {
            "query": query,
            "context": existing_context or "",
            "is_compass": False,
            "barn_data": [],
            "metadata": {}
        }


# ============================================================================
# EXAMPLE 2: Integration in Response Generator
# ============================================================================

class CompassAwareResponseGenerator:
    """
    Example: Response generator with Compass support

    This shows how to modify your existing EnhancedResponseGenerator
    or similar class to support Compass queries
    """

    def __init__(self, openai_client):
        self.client = openai_client
        self.compass = get_compass_extension()

    async def generate_response(
        self,
        query: str,
        context: str,
        user_token: Optional[str] = None,
        language: str = "fr"
    ) -> str:
        """
        Generate response with Compass enrichment

        Args:
            query: User query
            context: Retrieved context from RAG
            user_token: User's JWT token (required for Compass)
            language: Response language

        Returns:
            Generated response
        """
        # Step 1: Check if Compass query and enrich context
        if user_token and self.compass.is_compass_query(query):
            logger.info("Enriching context with Compass data")

            enriched = await self.compass.enrich_context(
                query=query,
                user_token=user_token,
                existing_context=context
            )

            # Use enriched context
            context = enriched["context"]

            # Add Compass system prompt
            compass_prompt = self.compass.create_compass_system_prompt()
        else:
            compass_prompt = ""

        # Step 2: Build system prompt
        system_prompt = self._build_system_prompt(language) + compass_prompt

        # Step 3: Build messages for LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]

        # Step 4: Generate response
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )

        return response.choices[0].message.content

    def _build_system_prompt(self, language: str) -> str:
        """Build base system prompt"""
        if language == "fr":
            return """Vous êtes un expert en aviculture.
Répondez de manière précise et professionnelle."""
        else:
            return """You are a poultry farming expert.
Answer precisely and professionally."""


# ============================================================================
# EXAMPLE 3: Integration in Chat Endpoint
# ============================================================================

async def handle_chat_with_compass(
    query: str,
    user_token: str,
    language: str = "fr"
) -> Dict[str, Any]:
    """
    Example: Complete chat endpoint with Compass support

    This shows the full flow from query to response

    Args:
        query: User query
        user_token: User's JWT token
        language: Response language

    Returns:
        Chat response with metadata
    """
    # Step 1: Initialize components
    compass = get_compass_extension()

    # Step 2: Retrieve relevant documents from RAG
    # (Your existing RAG retrieval logic here)
    retrieved_context = await retrieve_documents(query)

    # Step 3: Check for Compass query and enrich
    if compass.is_compass_query(query):
        enriched = await compass.enrich_context(
            query=query,
            user_token=user_token,
            existing_context=retrieved_context
        )

        context = enriched["context"]
        is_compass = True
        barn_data = enriched["barn_data"]
    else:
        context = retrieved_context
        is_compass = False
        barn_data = []

    # Step 4: Generate response
    response_generator = CompassAwareResponseGenerator(openai_client=None)
    response_text = await response_generator.generate_response(
        query=query,
        context=context,
        user_token=user_token,
        language=language
    )

    # Step 5: Return response with metadata
    return {
        "response": response_text,
        "metadata": {
            "is_compass_query": is_compass,
            "barn_data": barn_data,
            "language": language
        }
    }


async def retrieve_documents(query: str) -> str:
    """Placeholder for your RAG retrieval logic"""
    # Your existing document retrieval here
    return "Retrieved context from knowledge base..."


# ============================================================================
# EXAMPLE 4: Conditional System Prompt
# ============================================================================

def build_system_prompt_with_compass(
    base_prompt: str,
    is_compass_query: bool
) -> str:
    """
    Example: Add Compass instructions to system prompt only when needed

    Args:
        base_prompt: Your existing system prompt
        is_compass_query: Whether this is a Compass query

    Returns:
        Enhanced system prompt
    """
    if not is_compass_query:
        return base_prompt

    compass = get_compass_extension()
    compass_instructions = compass.create_compass_system_prompt()

    return f"{base_prompt}\n\n{compass_instructions}"


# ============================================================================
# EXAMPLE 5: Error Handling
# ============================================================================

async def safe_compass_enrichment(
    query: str,
    user_token: str,
    context: str
) -> str:
    """
    Example: Safe Compass enrichment with error handling

    Args:
        query: User query
        user_token: User's JWT token
        context: Existing context

    Returns:
        Enriched context (or original if error)
    """
    compass = get_compass_extension()

    try:
        if compass.is_compass_query(query):
            enriched = await compass.enrich_context(
                query=query,
                user_token=user_token,
                existing_context=context
            )
            return enriched["context"]
    except Exception as e:
        logger.error(f"Compass enrichment failed: {e}")
        # Fallback to original context
        logger.info("Falling back to non-Compass response")

    return context


# ============================================================================
# EXAMPLE 6: Testing Compass Integration
# ============================================================================

async def test_compass_integration():
    """
    Example: Test your Compass integration

    Run this to verify everything works
    """
    import asyncio

    # Test queries
    test_cases = [
        {
            "query": "Quelle est la température dans mon poulailler 2?",
            "expected_compass": True
        },
        {
            "query": "Comment nourrir les poulets?",
            "expected_compass": False
        },
        {
            "query": "Conditions actuelles barn 3",
            "expected_compass": True
        }
    ]

    compass = get_compass_extension()

    print("\n=== Testing Compass Query Detection ===\n")

    for test in test_cases:
        query = test["query"]
        is_compass = compass.is_compass_query(query)
        expected = test["expected_compass"]

        status = "✅ PASS" if is_compass == expected else "❌ FAIL"
        print(f"{status}: {query}")
        print(f"  Detected: {is_compass}, Expected: {expected}")

        if is_compass:
            barn_numbers = compass.extract_barn_numbers(query)
            data_types = compass.detect_data_types(query)
            print(f"  Barns: {barn_numbers}")
            print(f"  Data types: {data_types}")

        print()


# ============================================================================
# EXAMPLE 7: Full RAG Engine Integration
# ============================================================================

class CompassEnabledRAGEngine:
    """
    Example: Complete RAG engine with Compass support

    This is a simplified example showing all the pieces together
    """

    def __init__(self, openai_client):
        self.client = openai_client
        self.compass = get_compass_extension()
        self.response_generator = CompassAwareResponseGenerator(openai_client)

    async def process_query(
        self,
        query: str,
        user_token: str,
        language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Process query with full RAG + Compass pipeline

        Args:
            query: User query
            user_token: User JWT token
            language: Response language

        Returns:
            Response with metadata
        """
        logger.info(f"Processing query: {query}")

        # Step 1: Retrieve from knowledge base
        logger.info("Retrieving from knowledge base...")
        kb_context = await self._retrieve_from_kb(query)

        # Step 2: Check for Compass query
        is_compass = self.compass.is_compass_query(query)
        logger.info(f"Compass query: {is_compass}")

        # Step 3: Enrich with Compass if applicable
        if is_compass:
            logger.info("Enriching with Compass data...")
            enriched = await self.compass.enrich_context(
                query=query,
                user_token=user_token,
                existing_context=kb_context
            )
            final_context = enriched["context"]
            barn_data = enriched["barn_data"]
        else:
            final_context = kb_context
            barn_data = []

        # Step 4: Generate response
        logger.info("Generating response...")
        response = await self.response_generator.generate_response(
            query=query,
            context=final_context,
            user_token=user_token,
            language=language
        )

        # Step 5: Return with metadata
        return {
            "response": response,
            "metadata": {
                "is_compass_query": is_compass,
                "barn_data": barn_data,
                "language": language,
                "sources": ["knowledge_base"] + (["compass"] if is_compass else [])
            }
        }

    async def _retrieve_from_kb(self, query: str) -> str:
        """Retrieve context from knowledge base"""
        # Your RAG retrieval logic here
        return "Context from knowledge base..."


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def main():
        """Run examples"""
        print("=" * 80)
        print("COMPASS INTEGRATION EXAMPLES")
        print("=" * 80)

        # Example 1: Test detection
        await test_compass_integration()

        # Example 2: Test query processing
        print("\n=== Testing Query Processing ===\n")

        query = "Quelle est la température dans mon poulailler 2?"
        user_token = "mock_jwt_token"

        result = await process_query_with_compass(
            query=query,
            user_token=user_token,
            existing_context="Context from KB..."
        )

        print(f"Query: {query}")
        print(f"Is Compass: {result['is_compass']}")
        print(f"Barn data: {result['barn_data']}")
        print()

    # Run examples
    asyncio.run(main())
