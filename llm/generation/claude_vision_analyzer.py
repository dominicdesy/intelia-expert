# -*- coding: utf-8 -*-
"""
llm/generation/claude_vision_analyzer.py - Medical Image Analysis with Claude Vision
Version 1.0.0 - Veterinary diagnostic support for poultry diseases

Utilise Claude 3.5 Sonnet Vision pour analyser des images médicales d'élevage avicole
et fournir des diagnostics préliminaires basés sur les symptômes visuels.

IMPORTANT: Les diagnostics sont éducatifs uniquement - consultation vétérinaire requise.
"""

import os
import logging
import base64
from typing import Optional, Dict, List, Any
from io import BytesIO
from PIL import Image
import anthropic

from config.config import SUPPORTED_LANGUAGES, FALLBACK_LANGUAGE

# Import message handler for veterinary disclaimers
try:
    from config.messages import get_message
    MESSAGES_AVAILABLE = True
except ImportError:
    MESSAGES_AVAILABLE = False
    logging.warning("config.messages not available - disclaimers will be minimal")

logger = logging.getLogger(__name__)


class ClaudeVisionAnalyzer:
    """
    Medical image analyzer using Claude 3.5 Sonnet Vision API

    Specialized for poultry disease diagnosis with visual symptoms analysis.
    Integrates with the existing RAG system to provide context-aware diagnostics.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        language: str = "fr",
    ):
        """
        Initialize Claude Vision analyzer

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use (must support vision)
            language: Response language (fr, en, es, etc.)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY non trouvé. Définir la variable d'environnement ou passer api_key"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.language = language if language in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE

        logger.info(f"✅ ClaudeVisionAnalyzer initialized - Model: {model}, Language: {language}")

    def _image_to_base64(self, image_data: bytes, content_type: str = "image/jpeg") -> tuple[str, str]:
        """
        Convert image bytes to base64 for API transmission

        Args:
            image_data: Raw image bytes
            content_type: MIME type (image/jpeg, image/png, image/webp)

        Returns:
            Tuple of (base64_string, media_type)
        """
        try:
            # Valider que l'image est bien lisible
            image = Image.open(BytesIO(image_data))

            # Convertir en base64
            base64_data = base64.b64encode(image_data).decode('utf-8')

            logger.debug(f"Image converted to base64 - Size: {len(image_data)} bytes, Format: {image.format}")

            return base64_data, content_type

        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            raise ValueError(f"Image invalide ou corrompue: {e}")

    def _build_veterinary_prompt(
        self,
        user_query: str,
        context_docs: Optional[List[Dict]] = None,
        language: str = "fr",
    ) -> str:
        """
        Build specialized veterinary diagnostic prompt

        Args:
            user_query: User's question about the image
            context_docs: Optional RAG context documents
            language: Response language

        Returns:
            Formatted prompt for Claude Vision
        """

        # Prompt de base multilingue
        language_instruction = {
            "fr": "Réponds EN FRANÇAIS UNIQUEMENT.",
            "en": "Respond IN ENGLISH ONLY.",
            "es": "Responde EN ESPAÑOL ÚNICAMENTE.",
            "de": "Antworte NUR AUF DEUTSCH.",
            "it": "Rispondi SOLO IN ITALIANO.",
            "pt": "Responda APENAS EM PORTUGUÊS.",
            "nl": "Antwoord ALLEEN IN HET NEDERLANDS.",
            "pl": "Odpowiadaj TYLKO PO POLSKU.",
            "ar": "أجب بالعربية فقط.",
            "zh": "仅用中文回答。",
            "ja": "日本語のみで回答してください。",
            "hi": "केवल हिंदी में उत्तर दें।",
            "id": "Jawab HANYA DALAM BAHASA INDONESIA.",
            "th": "ตอบเป็นภาษาไทยเท่านั้น",
            "tr": "YALNIZCA TÜRKÇE cevap verin.",
            "vi": "Chỉ trả lời bằng TIẾNG VIỆT.",
        }.get(language, "Respond IN ENGLISH ONLY.")

        prompt = f"""Tu es un expert vétérinaire spécialisé en aviculture avec 20+ ans d'expérience en diagnostic de maladies aviaires.

{language_instruction}

CONTEXTE DE L'ANALYSE:
Tu analyses une image médicale fournie par un éleveur de volaille qui a posé la question suivante:
"{user_query}"

OBJECTIF:
Fournis une analyse médicale structurée basée sur les symptômes visuels observés dans l'image.

INSTRUCTIONS D'ANALYSE:
1. **Observation visuelle détaillée**:
   - Décris les symptômes visibles (couleur, texture, forme, taille, anomalies)
   - Note les caractéristiques physiques inhabituelles
   - Identifie les organes ou zones affectés

2. **Hypothèses diagnostiques**:
   - Liste 2-3 maladies probables par ordre de probabilité
   - Pour chaque hypothèse, explique les symptômes qui correspondent
   - Mentionne les causes possibles (virale, bactérienne, parasitaire, nutritionnelle)

3. **Facteurs de risque**:
   - Conditions d'élevage qui peuvent favoriser cette maladie
   - Âge typique des animaux affectés
   - Transmission et contagiosité

4. **Actions recommandées**:
   - Tests diagnostiques complémentaires nécessaires
   - Mesures d'urgence (isolement, biosécurité)
   - Traitements possibles (À CONFIRMER PAR VÉTÉRINAIRE)

5. **Prévention**:
   - Mesures de biosécurité
   - Protocoles de vaccination pertinents
   - Gestion de l'environnement

LIMITATIONS:
- Tu fournis une analyse éducative, PAS un diagnostic définitif
- Les photos peuvent ne pas montrer tous les symptômes
- Certaines maladies ont des symptômes similaires nécessitant des tests laboratoire

FORMAT DE RÉPONSE:
Structure ta réponse avec des sections claires et des bullet points.
Utilise un ton professionnel mais accessible.
"""

        # Ajouter contexte RAG si disponible
        if context_docs and len(context_docs) > 0:
            context_text = "\n\n".join([
                f"Document {i+1}: {doc.get('content', '')[:500]}"
                for i, doc in enumerate(context_docs[:3])
            ])

            prompt += f"""

CONTEXTE DOCUMENTAIRE ADDITIONNEL:
Les informations suivantes proviennent de notre base de connaissances avicoles et peuvent être pertinentes:

{context_text}

Utilise ces informations comme référence pour enrichir ton analyse si elles sont pertinentes.
"""

        # Ajouter disclaimer en fin de prompt
        prompt += f"""

DISCLAIMER OBLIGATOIRE:
À la fin de ta réponse, ajoute TOUJOURS cet avertissement:
"⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement. Pour toute préoccupation de santé animale, consultez immédiatement un vétérinaire qualifié. Un diagnostic définitif nécessite un examen clinique complet et potentiellement des tests de laboratoire."
"""

        return prompt

    async def analyze_medical_image(
        self,
        image_data: bytes,
        user_query: str,
        content_type: str = "image/jpeg",
        context_docs: Optional[List[Dict]] = None,
        language: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Analyze medical image with Claude Vision

        Args:
            image_data: Raw image bytes (from upload or URL fetch)
            user_query: User's question about the image
            content_type: Image MIME type (image/jpeg, image/png, image/webp)
            context_docs: Optional RAG context documents
            language: Response language (defaults to instance language)
            max_tokens: Maximum response length

        Returns:
            Dict with:
                - analysis: Full text analysis
                - success: Boolean success flag
                - error: Error message if failed
                - usage: Token usage information
        """
        lang = language or self.language

        try:
            logger.info(f"[VISION] Analyzing medical image - Query: '{user_query[:50]}...'")

            # Convert image to base64
            image_base64, media_type = self._image_to_base64(image_data, content_type)

            # Build veterinary prompt
            prompt = self._build_veterinary_prompt(user_query, context_docs, lang)

            # Call Claude Vision API
            logger.debug(f"[VISION] Calling Claude API - Model: {self.model}, Max tokens: {max_tokens}")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            }
                        ],
                    }
                ],
            )

            # Extract response
            analysis_text = message.content[0].text

            # Get usage stats
            usage_info = {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            }

            logger.info(f"[VISION] Analysis completed - Tokens: {usage_info['total_tokens']}")

            # Add veterinary disclaimer if not present (safety check)
            if "⚠️" not in analysis_text and MESSAGES_AVAILABLE:
                disclaimer = self._get_veterinary_disclaimer(lang)
                analysis_text = f"{analysis_text}\n\n{disclaimer}"

            return {
                "success": True,
                "analysis": analysis_text,
                "usage": usage_info,
                "model": self.model,
                "language": lang,
            }

        except anthropic.APIError as e:
            logger.error(f"[VISION] Anthropic API error: {e}")
            return {
                "success": False,
                "error": f"Erreur API Claude: {str(e)}",
                "analysis": None,
            }

        except Exception as e:
            logger.exception(f"[VISION] Unexpected error during analysis: {e}")
            return {
                "success": False,
                "error": f"Erreur inattendue: {str(e)}",
                "analysis": None,
            }

    def _get_veterinary_disclaimer(self, language: str = "fr") -> str:
        """
        Get veterinary disclaimer message in requested language

        Args:
            language: Target language code

        Returns:
            Disclaimer text with warning emoji
        """
        if MESSAGES_AVAILABLE:
            try:
                disclaimer = get_message("veterinary_disclaimer", language)
                return f"⚠️ {disclaimer}"
            except Exception as e:
                logger.warning(f"Failed to get veterinary_disclaimer for {language}: {e}")

        # Fallback disclaimers multilingues
        fallback_disclaimers = {
            "fr": "⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement. Pour toute préoccupation de santé animale, consultez immédiatement un vétérinaire qualifié.",
            "en": "⚠️ IMPORTANT: This analysis is provided for educational purposes only. For any animal health concerns, consult a qualified veterinarian immediately.",
            "es": "⚠️ IMPORTANTE: Este análisis se proporciona únicamente con fines educativos. Para cualquier problema de salud animal, consulte inmediatamente a un veterinario calificado.",
            "de": "⚠️ WICHTIG: Diese Analyse wird nur zu Bildungszwecken bereitgestellt. Bei gesundheitlichen Problemen bei Tieren konsultieren Sie sofort einen qualifizierten Tierarzt.",
        }

        return fallback_disclaimers.get(language, fallback_disclaimers["en"])

    async def analyze_batch_images(
        self,
        images: List[tuple[bytes, str, str]],
        context_docs: Optional[List[Dict]] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple medical images in batch

        Args:
            images: List of (image_data, query, content_type) tuples
            context_docs: Shared RAG context documents
            language: Response language

        Returns:
            List of analysis results for each image
        """
        results = []

        for i, (image_data, query, content_type) in enumerate(images):
            logger.info(f"[VISION BATCH] Processing image {i+1}/{len(images)}")

            result = await self.analyze_medical_image(
                image_data=image_data,
                user_query=query,
                content_type=content_type,
                context_docs=context_docs,
                language=language,
            )

            results.append(result)

        logger.info(f"[VISION BATCH] Completed {len(results)} analyses")
        return results


# Factory function
def create_vision_analyzer(
    api_key: Optional[str] = None,
    language: str = "fr",
) -> ClaudeVisionAnalyzer:
    """
    Factory function to create a ClaudeVisionAnalyzer instance

    Args:
        api_key: Anthropic API key (optional, defaults to env var)
        language: Default response language

    Returns:
        Configured ClaudeVisionAnalyzer instance
    """
    return ClaudeVisionAnalyzer(api_key=api_key, language=language)
