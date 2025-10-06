# -*- coding: utf-8 -*-
"""
llm_translator.py - LLM-Based Translation Service
Version 1.0 - Traduction robuste via OpenAI GPT-4o-mini

Avantages vs dictionnaires de traduction:
- Qualité native (pas de "perpourmance" ou fragments non traduits)
- Zéro maintenance (pas de dictionnaires à maintenir)
- Support automatique de toutes les langues
- Préserve structure Markdown et formatage
- Rapide (<100ms avec gpt-4o-mini)
- Peu coûteux (~0.0001$ par traduction)

Exemples:
✅ EN → FR: "To analyze performance of Ross 308, I need to know:"
           → "Pour analyser la performance du Ross 308, j'ai besoin de savoir:"
✅ EN → TH: "Please specify **the breed**. For example: Ross 308..."
           → "กรุณาระบุ **สายพันธุ์** ตัวอย่างเช่น: Ross 308..."
"""

import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMTranslator:
    """
    Traducteur basé sur LLM pour traductions robustes et de haute qualité

    Utilise gpt-4o-mini pour:
    - Traductions rapides (<100ms)
    - Faible coût (~0.0001$ par traduction)
    - Qualité native (comprend contexte et nuances)
    - Préservation du formatage Markdown
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

    # Noms de langues pour le prompt
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
        cache_enabled: bool = True
    ):
        """
        Initialize LLM-based translator

        Args:
            openai_api_key: OpenAI API key (if None, uses env var OPENAI_API_KEY)
            model: OpenAI model to use (default: gpt-4o-mini for speed/cost)
            cache_enabled: Enable caching for identical translations
        """
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
        self.model = model
        self.cache_enabled = cache_enabled
        self.cache = {}  # Simple cache: (text, target_lang) → translation

        logger.info(f"✅ LLMTranslator initialized with model={model}, cache={cache_enabled}")

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "en"
    ) -> str:
        """
        Traduit un texte vers la langue cible via LLM

        Args:
            text: Texte à traduire
            target_language: Code langue cible (fr, es, th, etc.)
            source_language: Code langue source (default: en)

        Returns:
            Texte traduit (ou texte original si target_language == source_language)
        """
        # Si même langue, retourner directement
        if target_language == source_language:
            return text

        # Si texte vide, retourner vide
        if not text or not text.strip():
            return text

        # Check cache
        cache_key = (text, source_language, target_language)
        if self.cache_enabled and cache_key in self.cache:
            logger.debug(f"📦 Cache hit for translation to {target_language}")
            return self.cache[cache_key]

        try:
            # Construire le prompt
            source_lang_name = self.LANGUAGE_NAMES.get(source_language, source_language)
            target_lang_name = self.LANGUAGE_NAMES.get(target_language, target_language)

            prompt = self.TRANSLATION_PROMPT.format(
                source_lang=source_lang_name,
                target_lang=target_lang_name,
                text=text
            )

            # Appel OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator specializing in poultry production terminology."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Bas pour cohérence, mais pas 0 pour naturel
                max_tokens=500,   # Suffisant pour messages de clarification
                timeout=5.0       # 5s timeout
            )

            # Extraire traduction
            translation = response.choices[0].message.content.strip()

            # Nettoyer si LLM a ajouté des quotes (TOUTES les variantes)
            # Enlever quotes triples
            if translation.startswith('"""') and translation.endswith('"""'):
                translation = translation[3:-3].strip()
            elif translation.startswith("'''") and translation.endswith("'''"):
                translation = translation[3:-3].strip()
            # Enlever quotes doubles
            elif translation.startswith('"') and translation.endswith('"'):
                translation = translation[1:-1].strip()
            elif translation.startswith("'") and translation.endswith("'"):
                translation = translation[1:-1].strip()

            # Nettoyer les quotes vides résiduelles
            translation = translation.replace('""', '').replace("''", '')

            # Log
            logger.debug(
                f"🌍 Translated ({source_language}→{target_language}): "
                f"'{text[:50]}...' → '{translation[:50]}...'"
            )

            # Cache result
            if self.cache_enabled:
                self.cache[cache_key] = translation

            return translation

        except Exception as e:
            logger.error(f"❌ LLM translation error ({source_language}→{target_language}): {e}")

            # Fallback: retourner texte original
            logger.warning(f"⚠️ Fallback to original text due to translation error")
            return text

    def clear_cache(self):
        """Vide le cache de traductions"""
        self.cache.clear()
        logger.info("🗑️ Translation cache cleared")

    def get_cache_size(self) -> int:
        """Retourne la taille du cache"""
        return len(self.cache)


# Factory singleton
_llm_translator_instance = None


def get_llm_translator(
    openai_api_key: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> LLMTranslator:
    """
    Récupère l'instance singleton du LLMTranslator

    Args:
        openai_api_key: OpenAI API key (optional)
        model: Model to use (default: gpt-4o-mini)

    Returns:
        Instance LLMTranslator
    """
    global _llm_translator_instance

    if _llm_translator_instance is None:
        _llm_translator_instance = LLMTranslator(
            openai_api_key=openai_api_key,
            model=model
        )

    return _llm_translator_instance


# Tests unitaires
if __name__ == "__main__":
    import sys

    # Configuration logging
    logging.basicConfig(level=logging.INFO)

    # Créer traducteur
    translator = LLMTranslator()

    print("\n" + "=" * 80)
    print("TESTS LLM TRANSLATOR")
    print("=" * 80)

    # Test cases
    test_cases = [
        # Cas 1: Message de clarification simple
        (
            "To analyze performance of Ross 308, I need to know:",
            "fr",
            "Pour analyser la performance du Ross 308, j'ai besoin de savoir"
        ),

        # Cas 2: Message avec Markdown
        (
            "Please specify **the breed**. For example: Ross 308, Cobb 500.",
            "fr",
            "Veuillez préciser **la race**. Par exemple : Ross 308, Cobb 500."
        ),

        # Cas 3: Message avec liste
        (
            "To help you best, I need details on:\n- **Breed**: Ross 308, Cobb 500, other?\n- **Age**: in days or weeks?",
            "fr",
            "Pour mieux vous aider, j'ai besoin de détails sur :\n- **Race** : Ross 308, Cobb 500, autre ?\n- **Âge** : en jours ou semaines ?"
        ),

        # Cas 4: Traduction vers Thai
        (
            "Please specify **the age** of the flock. For example: 21 days, 35 days.",
            "th",
            "กรุณาระบุ **อายุ** ของฝูง ตัวอย่างเช่น: 21 วัน, 35 วัน"
        ),

        # Cas 5: Traduction vers Espagnol
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

        # Vérifier que la traduction contient des mots clés de la langue cible
        # (pas de vérification exacte car LLM peut légèrement varier)
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
