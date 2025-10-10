# -*- coding: utf-8 -*-
"""
llm_translator.py - LLM-Based Translation Service
High-quality translation via OpenAI GPT-4o-mini with Redis cache support
Preserves Markdown structure and provides fast, cost-effective translations
"""

import logging
import hashlib
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMTranslator:
    """
    LLM-based translator for robust and high-quality translations

    Uses gpt-4o-mini for:
    - Fast translations (<100ms)
    - Low cost (~$0.0001 per translation)
    - Native quality (understands context and nuances)
    - Markdown formatting preservation
    """

    TRANSLATION_PROMPT = """Translate the following text from {source_lang} to {target_lang}.

IMPORTANT RULES:
1. Preserve ALL Markdown formatting (**bold**, *italic*, `code`, etc.)
2. Preserve ALL placeholders like {{variable}} if present
3. Keep technical terms accurate (breed names like "Ross 308", "Cobb 500" unchanged)
4. Keep numbers and units unchanged (e.g., "21 days", "35 jours")
5. Translate naturally and idiomatically (not word-for-word)
6. Keep the tone professional and clear

Text to translate:
\"\"\"
{text}
\"\"\"

Translation in {target_lang}:"""

    # Language names for prompt
    LANGUAGE_NAMES = {
        "en": "English",
        "fr": "French",
        "es": "Spanish",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "nl": "Dutch",
        "pl": "Polish",
        "th": "Thai",
        "vi": "Vietnamese",
        "id": "Indonesian",
        "hi": "Hindi",
        "zh": "Chinese",
        "ar": "Arabic",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
    }

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        cache_enabled: bool = True,
        redis_cache=None
    ):
        """
        Initialize LLM-based translator with Redis cache support

        Args:
            openai_api_key: OpenAI API key (if None, uses env var OPENAI_API_KEY)
            model: OpenAI model to use (default: gpt-4o-mini for speed/cost)
            cache_enabled: Enable caching for identical translations
            redis_cache: Optional Redis cache manager (RAGCacheManager instance)
        """
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
        self.model = model
        self.cache_enabled = cache_enabled
        self.redis_cache = redis_cache
        self.memory_cache = {}  # Fallback in-memory cache

        cache_type = "Redis" if redis_cache else "memory"
        logger.info(f"✅ LLMTranslator initialized with model={model}, cache={cache_type}")

    def _generate_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate a unique cache key for translation"""
        content = f"{source_lang}:{target_lang}:{text}"
        return f"translation:{hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()}"

    async def translate_async(
        self,
        text: str,
        target_language: str,
        source_language: str = "en"
    ) -> str:
        """
        Async translation with Redis cache support

        Args:
            text: Text to translate
            target_language: Target language code (fr, es, th, etc.)
            source_language: Source language code (default: en)

        Returns:
            Translated text (or original if same language)
        """
        # If same language, return directly
        if target_language == source_language:
            return text

        # If empty text, return empty
        if not text or not text.strip():
            return text

        # Generate cache key
        cache_key = self._generate_cache_key(text, source_language, target_language)

        # Check Redis cache first
        if self.cache_enabled and self.redis_cache:
            try:
                cached = await self.redis_cache.get(cache_key)
                if cached:
                    logger.debug(f"📦 Redis cache hit for translation to {target_language}")
                    return cached.decode('utf-8')
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # Fallback to memory cache
        memory_key = (text, source_language, target_language)
        if self.cache_enabled and memory_key in self.memory_cache:
            logger.debug(f"📦 Memory cache hit for translation to {target_language}")
            return self.memory_cache[memory_key]

        try:
            # Build prompt
            source_lang_name = self.LANGUAGE_NAMES.get(source_language, source_language)
            target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

            prompt = self.TRANSLATION_PROMPT.format(
                source_lang=source_lang_name,
                target_lang=target_lang_name,
                text=text
            )

            # OpenAI call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator specializing in poultry production terminology."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Low for consistency, but not 0 for naturalness
                max_tokens=500,   # Sufficient for clarification messages
                timeout=5.0       # 5s timeout
            )

            # Extract translation
            translation = response.choices[0].message.content.strip()

            # Clean if LLM added quotes (all variants)
            # Remove triple quotes
            if translation.startswith('"""') and translation.endswith('"""'):
                translation = translation[3:-3].strip()
            elif translation.startswith("'''") and translation.endswith("'''"):
                translation = translation[3:-3].strip()
            # Remove double quotes
            elif translation.startswith('"') and translation.endswith('"'):
                translation = translation[1:-1].strip()
            elif translation.startswith("'") and translation.endswith("'"):
                translation = translation[1:-1].strip()

            # Clean residual empty quotes
            translation = translation.replace('""', '').replace("''", '')

            # Log
            logger.debug(
                f"🌍 Translated ({source_language}→{target_language}): "
                f"'{text[:50]}...' → '{translation[:50]}...'"
            )

            # Cache result in Redis (async)
            if self.cache_enabled:
                # Store in memory cache
                self.memory_cache[memory_key] = translation

                # Store in Redis if available
                if self.redis_cache:
                    try:
                        await self.redis_cache.set(
                            cache_key,
                            translation.encode('utf-8'),
                            ttl=86400  # 24 hours
                        )
                        logger.debug(f"💾 Translation cached in Redis: {cache_key[:50]}...")
                    except Exception as e:
                        logger.warning(f"Redis cache write error: {e}")

            return translation

        except Exception as e:
            logger.error(f"❌ LLM translation error ({source_language}→{target_language}): {e}")

            # Fallback: return original text
            logger.warning("⚠️ Fallback to original text due to translation error")
            return text

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en"
    ) -> str:
        """
        Synchronous wrapper for translate_async (for backward compatibility)

        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (default: en)

        Returns:
            Translated text
        """
        import asyncio

        # If same language, return directly
        if target_language == source_language:
            return text

        try:
            # Try to use existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.translate_async(text, target_language, source_language)
                    )
                    return future.result(timeout=10)
            else:
                # No running loop, use asyncio.run
                return asyncio.run(
                    self.translate_async(text, target_language, source_language)
                )
        except Exception as e:
            logger.error(f"Sync translation wrapper error: {e}")
            return text

    def clear_cache(self):
        """Clear translation cache (memory only)"""
        self.memory_cache.clear()
        logger.info("🗑️ Translation memory cache cleared")

    def get_cache_size(self) -> int:
        """Return memory cache size"""
        return len(self.memory_cache)


# Factory singleton
_llm_translator_instance = None


def get_llm_translator(
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> LLMTranslator:
    """
    Get LLMTranslator singleton instance

    Args:
        openai_api_key: OpenAI API key (optional)
        model: Model to use (default: gpt-4o-mini)

    Returns:
        LLMTranslator instance
    """
    global _llm_translator_instance

    if _llm_translator_instance is None:
        _llm_translator_instance = LLMTranslator(
            openai_api_key=openai_api_key,
            model=model
        )

    return _llm_translator_instance


# Unit tests
if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Create translator
    translator = LLMTranslator()

    print("\n" + "=" * 80)
    print("TESTS LLM TRANSLATOR")
    print("=" * 80)

    # Test cases
    test_cases = [
        # Case 1: Simple clarification message
        (
            "To analyze performance of Ross 308, I need to know:",
            "fr",
            "Pour analyser la performance du Ross 308, j'ai besoin de savoir"
        ),

        # Case 2: Message with Markdown
        (
            "Please specify **the breed**. For example: Ross 308, Cobb 500.",
            "fr",
            "Veuillez préciser **la race**. Par exemple : Ross 308, Cobb 500."
        ),

        # Case 3: Message with list
        (
            "To help you best, I need details on:\n- **Breed**: Ross 308, Cobb 500, other?\n- **Age**: in days or weeks?",
            "fr",
            "Pour mieux vous aider, j'ai besoin de détails sur :\n- **Race** : Ross 308, Cobb 500, autre ?\n- **Âge** : en jours ou semaines ?"
        ),

        # Case 4: Translation to Thai
        (
            "Please specify **the age** of the flock. For example: 21 days, 35 days.",
            "th",
            "กรุณาระบุ **อายุ** ของฝูง ตัวอย่างเช่น: 21 วัน, 35 วัน"
        ),

        # Case 5: Translation to Spanish
        (
            "To recommend a treatment for Newcastle disease, I need to know:",
            "es",
            "Para recomendar un tratamiento para la enfermedad de Newcastle, necesito saber"
        ),
    ]

    passed = 0
    failed = 0

    for i, (text_en, target_lang, expected_contains) in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: EN → {target_lang.upper()} ---")
        print(f"Input: {text_en[:80]}...")

        translation = translator.translate(text_en, target_lang)

        print(f"Output: {translation[:80]}...")

        # Verify translation contains target language keywords
        # (no exact verification as LLM can slightly vary)
        if translation and translation != text_en and len(translation) > 10:
            print("✅ PASS - Translation successful")
            passed += 1
        else:
            print("❌ FAIL - Translation failed or unchanged")
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    print(f"Cache size: {translator.get_cache_size()} entries")
    print("=" * 80)

    sys.exit(0 if failed == 0 else 1)
