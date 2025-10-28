# -*- coding: utf-8 -*-
"""
relevance_checker.py - Relevance verification for LLM responses
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
relevance_checker.py - Relevance verification for LLM responses

Verifies that retrieved documents and generated responses are actually relevant
to the user's query, preventing off-topic content (e.g., dairy cattle when asking about poultry).
"""

import logging
from utils.types import Dict, Tuple

logger = logging.getLogger(__name__)


class RelevanceChecker:
    """
    Checks relevance of documents and responses to the original query

    Uses LLM-based verification to detect off-topic content that may have
    been retrieved incorrectly (e.g., "dairy cattle" when query is about "chickens").
    """

    def __init__(self, client=None):
        """
        Initialize relevance checker

        Args:
            client: Optional LLM client for advanced relevance checking
        """
        self.client = client

        # Topic keywords for quick filtering (poultry domain)
        self.domain_keywords = {
            "poultry": [
                "chicken",
                "poulet",
                "broiler",
                "layer",
                "hen",
                "rooster",
                "cobb",
                "ross",
                "hubbard",
                "avian",
                "poultry",
                "volaille",
            ],
            "off_topic": [
                "cattle",
                "bovine",
                "cow",
                "dairy",
                "beef",
                "pig",
                "swine",
                "sheep",
                "goat",
                "horse",
                "fish",
                "aquaculture",
            ],
        }

    async def check_document_relevance(
        self, query: str, document: Dict, language: str = "en"
    ) -> Tuple[bool, float, Dict]:
        """
        Check if a document is relevant to the query

        Args:
            query: User's original question
            document: Document to check (must have 'content' or 'abstract' field)
            language: Query language

        Returns:
            (is_relevant, relevance_score, details)
            - is_relevant: True if document matches query topic
            - relevance_score: 0.0 to 1.0 (1.0 = highly relevant)
            - details: Dict with explanation
        """
        try:
            # Extract document text
            doc_text = document.get("content", document.get("abstract", ""))
            doc_title = document.get("title", "")

            if not doc_text:
                return False, 0.0, {"reason": "empty_document"}

            # Quick keyword-based check first (fast filter)
            quick_result = self._quick_relevance_check(query, doc_text, doc_title)
            if quick_result[0] == False:  # Definitely off-topic
                logger.warning(
                    f"[RelevanceChecker] Document rejected (quick check): {doc_title[:80]}"
                )
                return quick_result

            # If LLM client available, do deep semantic check
            if self.client:
                return await self._llm_relevance_check(
                    query, doc_text, doc_title, language
                )

            # Otherwise, return quick check result
            return quick_result

        except Exception as e:
            logger.error(f"[RelevanceChecker] Error checking document relevance: {e}")
            # Fail-open: assume relevant if check fails
            return True, 0.7, {"error": str(e), "fallback": True}

    def _quick_relevance_check(
        self, query: str, doc_text: str, doc_title: str
    ) -> Tuple[bool, float, Dict]:
        """
        Fast keyword-based relevance check

        Returns:
            (is_relevant, score, details)
        """
        query_lower = query.lower()
        doc_text_lower = doc_text[:1000].lower()  # Check first 1000 chars
        doc_title_lower = doc_title.lower()

        # Check for off-topic keywords
        off_topic_count = sum(
            1
            for keyword in self.domain_keywords["off_topic"]
            if keyword in doc_title_lower or keyword in doc_text_lower[:500]
        )

        # Check for on-topic keywords
        on_topic_count = sum(
            1
            for keyword in self.domain_keywords["poultry"]
            if keyword in doc_title_lower or keyword in doc_text_lower[:500]
        )

        # Strong signal: off-topic keywords in title or early in text
        if off_topic_count > 0 and on_topic_count == 0:
            logger.info(
                f"[RelevanceChecker] Off-topic document detected (quick): "
                f"off_topic={off_topic_count}, on_topic={on_topic_count}"
            )
            return (
                False,
                0.1,
                {
                    "reason": "off_topic_keywords_detected",
                    "off_topic_count": off_topic_count,
                    "on_topic_count": on_topic_count,
                    "method": "quick_keyword",
                },
            )

        # Likely relevant if poultry keywords present
        if on_topic_count > 0:
            score = min(0.9, 0.6 + (on_topic_count * 0.1))
            return (
                True,
                score,
                {
                    "reason": "on_topic_keywords_found",
                    "on_topic_count": on_topic_count,
                    "method": "quick_keyword",
                },
            )

        # Neutral: no strong signals, pass to LLM if available
        return (
            True,
            0.5,
            {"reason": "neutral_needs_deep_check", "method": "quick_keyword"},
        )

    async def _llm_relevance_check(
        self, query: str, doc_text: str, doc_title: str, language: str
    ) -> Tuple[bool, float, Dict]:
        """
        Deep LLM-based relevance verification

        Uses Claude/GPT to semantically verify if document is relevant to query
        """
        try:
            # Build relevance verification prompt
            prompt = self._build_relevance_prompt(query, doc_text, doc_title, language)

            # Call LLM
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cheap for verification
                messages=[
                    {
                        "role": "system",
                        "content": "You are a relevance verification expert. Your job is to determine if a scientific document is relevant to a user's query.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=150,
            )

            result_text = response.choices[0].message.content.strip().lower()

            # Parse LLM response
            is_relevant = (
                "relevant: yes" in result_text or "relevant:yes" in result_text
            )

            # Extract relevance score if provided
            score = 0.5
            if "score:" in result_text:
                try:
                    score_str = result_text.split("score:")[1].split()[0].strip()
                    score = float(score_str)
                except:
                    score = 0.8 if is_relevant else 0.2
            else:
                score = 0.8 if is_relevant else 0.2

            logger.info(
                f"[RelevanceChecker] LLM verification: relevant={is_relevant}, "
                f"score={score:.2f}, doc_title={doc_title[:60]}"
            )

            return (
                is_relevant,
                score,
                {
                    "reason": "llm_verification",
                    "llm_response": result_text[:200],
                    "method": "llm_semantic",
                },
            )

        except Exception as e:
            logger.error(f"[RelevanceChecker] LLM check failed: {e}")
            # Fallback to quick check result
            return True, 0.6, {"error": str(e), "fallback": "llm_failed"}

    def _build_relevance_prompt(
        self, query: str, doc_text: str, doc_title: str, language: str
    ) -> str:
        """Build LLM prompt for relevance verification"""

        # Truncate document to first 800 characters for efficiency
        doc_snippet = doc_text[:800] + "..." if len(doc_text) > 800 else doc_text

        prompt = f"""Verify if this scientific document is relevant to the user's query.

USER QUERY: "{query}"

DOCUMENT TITLE: "{doc_title}"

DOCUMENT EXCERPT: "{doc_snippet}"

INSTRUCTIONS:
1. Check if the document's topic matches the query's topic
2. Example: If query is about "chickens" or "poultry", documents about "dairy cattle" or "cows" are NOT relevant
3. Documents can mention other topics in passing, but the MAIN topic must match
4. Consider synonyms and related terms (e.g., "broiler" = "chicken", "bovine" = "cattle")

OUTPUT FORMAT (strictly follow):
Relevant: YES or NO
Score: <0.0 to 1.0>
Reason: <brief explanation in one line>

Answer:"""

        return prompt

    async def check_response_relevance(
        self, query: str, response: str, language: str = "en"
    ) -> Tuple[bool, float, Dict]:
        """
        Check if generated response is relevant to the query

        Args:
            query: User's original question
            response: LLM-generated response to verify
            language: Query language

        Returns:
            (is_relevant, relevance_score, details)
        """
        try:
            # Quick keyword check first
            query_lower = query.lower()
            response_lower = response[:1000].lower()

            # Check for blatant off-topic content in response
            off_topic_in_response = sum(
                1
                for keyword in self.domain_keywords["off_topic"]
                if keyword in response_lower
            )

            on_topic_in_response = sum(
                1
                for keyword in self.domain_keywords["poultry"]
                if keyword in response_lower
            )

            # Strong signal: response talks about wrong animals
            if off_topic_in_response > 2 and on_topic_in_response == 0:
                logger.warning(
                    f"[RelevanceChecker] OFF-TOPIC RESPONSE DETECTED: "
                    f"Query about poultry but response mentions {off_topic_in_response} off-topic terms"
                )
                return (
                    False,
                    0.1,
                    {
                        "reason": "response_off_topic",
                        "off_topic_terms": off_topic_in_response,
                        "on_topic_terms": on_topic_in_response,
                        "method": "keyword_analysis",
                    },
                )

            # If LLM available, do semantic check
            if self.client and off_topic_in_response > 0:
                return await self._llm_response_relevance_check(
                    query, response, language
                )

            # Otherwise, assume relevant
            return True, 0.8, {"method": "keyword_analysis", "passed": True}

        except Exception as e:
            logger.error(f"[RelevanceChecker] Error checking response relevance: {e}")
            return True, 0.7, {"error": str(e), "fallback": True}

    async def _llm_response_relevance_check(
        self, query: str, response: str, language: str
    ) -> Tuple[bool, float, Dict]:
        """LLM-based response relevance verification"""
        try:
            # Truncate response for efficiency
            response_snippet = (
                response[:1000] + "..." if len(response) > 1000 else response
            )

            prompt = f"""Verify if this response properly answers the user's query.

USER QUERY: "{query}"

GENERATED RESPONSE: "{response_snippet}"

INSTRUCTIONS:
1. Check if the response addresses the query's topic
2. Example: If query is about "chickens/poultry", response should NOT primarily discuss "cattle/cows"
3. The response must be relevant to the animals/topic mentioned in the query

OUTPUT FORMAT:
Relevant: YES or NO
Score: <0.0 to 1.0>
Reason: <brief explanation>

Answer:"""

            result = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a relevance verification expert.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=150,
            )

            result_text = result.choices[0].message.content.strip().lower()
            is_relevant = "relevant: yes" in result_text

            score = 0.8 if is_relevant else 0.2

            logger.info(
                f"[RelevanceChecker] Response relevance: {is_relevant}, score: {score}"
            )

            return (
                is_relevant,
                score,
                {
                    "reason": "llm_response_verification",
                    "llm_response": result_text[:200],
                },
            )

        except Exception as e:
            logger.error(f"[RelevanceChecker] LLM response check failed: {e}")
            return True, 0.7, {"error": str(e), "fallback": True}


__all__ = ["RelevanceChecker"]
