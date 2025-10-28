# -*- coding: utf-8 -*-
"""
llm/generation/claude_vision_analyzer.py - Medical Image Analysis with Claude Vision
Version: 1.4.1
Last modified: 2025-10-26
"""
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
        model: Optional[str] = None,
        language: str = "fr",
    ):
        """
        Initialize Claude Vision analyzer

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use (defaults to ANTHROPIC_VISION_MODEL env var or claude-3-5-sonnet-20240620)
            language: Response language (fr, en, es, etc.)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY non trouvé. Définir la variable d'environnement ou passer api_key"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        # Use dedicated vision model env var, fallback to general model, then default
        # Default: claude-sonnet-4-5-20250929 (Claude 3.x retired Oct 22, 2025)
        self.model = (
            model
            or os.getenv("ANTHROPIC_VISION_MODEL")
            or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        )
        self.language = (
            language if language in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE
        )

        logger.info(
            f"✅ ClaudeVisionAnalyzer initialized - Model: {self.model}, Language: {language}"
        )

    def _image_to_base64(
        self, image_data: bytes, content_type: str = "image/jpeg"
    ) -> tuple[str, str]:
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
            base64_data = base64.b64encode(image_data).decode("utf-8")

            logger.debug(
                f"Image converted to base64 - Size: {len(image_data)} bytes, Format: {image.format}"
            )

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
            context_text = "\n\n".join(
                [
                    f"Document {i+1}: {doc.get('content', '')[:500]}"
                    for i, doc in enumerate(context_docs[:3])
                ]
            )

            prompt += f"""

CONTEXTE DOCUMENTAIRE ADDITIONNEL:
Les informations suivantes proviennent de notre base de connaissances avicoles et peuvent être pertinentes:

{context_text}

Utilise ces informations comme référence pour enrichir ton analyse si elles sont pertinentes.
"""

        # Messages de suivi multilingues pour demander d'autres images
        followup_question = {
            "fr": "Avez-vous d'autres photos du même problème ou d'autres animaux affectés à analyser ? Des images supplémentaires (différents angles, autres organes, autres animaux) peuvent aider à affiner le diagnostic.",
            "en": "Do you have other photos of the same problem or other affected animals to analyze? Additional images (different angles, other organs, other animals) can help refine the diagnosis.",
            "es": "¿Tiene otras fotos del mismo problema u otros animales afectados para analizar? Imágenes adicionales (diferentes ángulos, otros órganos, otros animales) pueden ayudar a refinar el diagnóstico.",
            "de": "Haben Sie weitere Fotos desselben Problems oder anderer betroffener Tiere zu analysieren? Zusätzliche Bilder (verschiedene Winkel, andere Organe, andere Tiere) können helfen, die Diagnose zu verfeinern.",
            "it": "Hai altre foto dello stesso problema o di altri animali colpiti da analizzare? Immagini aggiuntive (angoli diversi, altri organi, altri animali) possono aiutare a perfezionare la diagnosi.",
            "pt": "Você tem outras fotos do mesmo problema ou de outros animais afetados para analisar? Imagens adicionais (diferentes ângulos, outros órgãos, outros animais) podem ajudar a refinar o diagnóstico.",
            "nl": "Heeft u andere foto's van hetzelfde probleem of andere getroffen dieren om te analyseren? Extra afbeeldingen (verschillende hoeken, andere organen, andere dieren) kunnen helpen de diagnose te verfijnen.",
            "pl": "Czy masz inne zdjęcia tego samego problemu lub innych dotkniętych zwierząt do analizy? Dodatkowe obrazy (różne kąty, inne narządy, inne zwierzęta) mogą pomóc w doprecyzowaniu diagnozy.",
            "ar": "هل لديك صور أخرى لنفس المشكلة أو حيوانات أخرى مصابة لتحليلها؟ يمكن أن تساعد الصور الإضافية (زوايا مختلفة، أعضاء أخرى، حيوانات أخرى) في تحسين التشخيص.",
            "zh": "您是否有同一问题的其他照片或其他受影响动物的照片需要分析？额外的图像（不同角度、其他器官、其他动物）可以帮助完善诊断。",
            "ja": "同じ問題または他の影響を受けた動物の他の写真を分析する必要がありますか？追加の画像（異なる角度、他の臓器、他の動物）は診断を洗練するのに役立ちます。",
            "hi": "क्या आपके पास इसी समस्या की या अन्य प्रभावित जानवरों की अन्य तस्वीरें हैं जिनका विश्लेषण करना है? अतिरिक्त छवियां (विभिन्न कोण, अन्य अंग, अन्य जानवर) निदान को परिष्कृत करने में मदद कर सकती हैं।",
            "id": "Apakah Anda memiliki foto lain dari masalah yang sama atau hewan lain yang terkena untuk dianalisis? Gambar tambahan (sudut berbeda, organ lain, hewan lain) dapat membantu menyempurnakan diagnosis.",
            "th": "คุณมีรูปภาพอื่นของปัญหาเดียวกันหรือสัตว์อื่นที่ได้รับผลกระทบเพื่อวิเคราะห์หรือไม่? ภาพเพิ่มเติม (มุมต่างๆ อวัยวะอื่นๆ สัตว์อื่นๆ) สามารถช่วยปรับปรุงการวินิจฉัยได้",
            "tr": "Analiz edilecek aynı sorunun veya etkilenen diğer hayvanların başka fotoğrafları var mı? Ek görüntüler (farklı açılar, diğer organlar, diğer hayvanlar) teşhisin iyileştirilmesine yardımcı olabilir.",
            "vi": "Bạn có ảnh khác về cùng một vấn đề hoặc các động vật khác bị ảnh hưởng để phân tích không? Hình ảnh bổ sung (góc độ khác nhau, các cơ quan khác, động vật khác) có thể giúp cải thiện chẩn đoán.",
        }.get(
            language,
            "Do you have other photos of the same problem or other affected animals to analyze? Additional images (different angles, other organs, other animals) can help refine the diagnosis.",
        )

        # Ajouter question de suivi et disclaimer
        prompt += f"""

QUESTION DE SUIVI:
Après ton analyse complète, ajoute cette question pour encourager l'envoi d'images supplémentaires si nécessaire:
"📸 {followup_question}"

DISCLAIMER OBLIGATOIRE:
À la fin de ta réponse (après la question de suivi), ajoute TOUJOURS cet avertissement:
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
            logger.info(
                f"[VISION] Analyzing medical image - Query: '{user_query[:50]}...'"
            )

            # Convert image to base64
            image_base64, media_type = self._image_to_base64(image_data, content_type)

            # Build veterinary prompt
            prompt = self._build_veterinary_prompt(user_query, context_docs, lang)

            # Call Claude Vision API
            logger.debug(
                f"[VISION] Calling Claude API - Model: {self.model}, Max tokens: {max_tokens}"
            )

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
                            },
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
                "total_tokens": message.usage.input_tokens
                + message.usage.output_tokens,
            }

            logger.info(
                f"[VISION] Analysis completed - Tokens: {usage_info['total_tokens']}"
            )

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
                logger.warning(
                    f"Failed to get veterinary_disclaimer for {language}: {e}"
                )

        # Fallback disclaimers multilingues
        fallback_disclaimers = {
            "fr": "⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement. Pour toute préoccupation de santé animale, consultez immédiatement un vétérinaire qualifié.",
            "en": "⚠️ IMPORTANT: This analysis is provided for educational purposes only. For any animal health concerns, consult a qualified veterinarian immediately.",
            "es": "⚠️ IMPORTANTE: Este análisis se proporciona únicamente con fines educativos. Para cualquier problema de salud animal, consulte inmediatamente a un veterinario calificado.",
            "de": "⚠️ WICHTIG: Diese Analyse wird nur zu Bildungszwecken bereitgestellt. Bei gesundheitlichen Problemen bei Tieren konsultieren Sie sofort einen qualifizierten Tierarzt.",
        }

        return fallback_disclaimers.get(language, fallback_disclaimers["en"])

    async def analyze_multiple_medical_images(
        self,
        images_data: List[Dict[str, Any]],
        user_query: str,
        context_docs: Optional[List[Dict]] = None,
        language: Optional[str] = None,
        max_tokens: int = 3072,
    ) -> Dict[str, Any]:
        """
        Analyze multiple medical images in a SINGLE API call for comprehensive diagnosis

        This method sends ALL images to Claude Vision in one request, allowing it to
        perform a comparative analysis across multiple images (different angles, organs, animals).

        Args:
            images_data: List of dicts with keys:
                - data: bytes (raw image data)
                - content_type: str (MIME type)
                - filename: str (original filename)
            user_query: User's question about the images
            context_docs: Optional RAG context documents
            language: Response language (defaults to instance language)
            max_tokens: Maximum response length (higher for multi-image analysis)

        Returns:
            Dict with:
                - analysis: Full comparative analysis text
                - success: Boolean success flag
                - error: Error message if failed
                - usage: Token usage information
                - images_count: Number of images analyzed
        """
        lang = language or self.language

        try:
            images_count = len(images_data)
            logger.info(
                f"[VISION MULTI] Analyzing {images_count} medical images - Query: '{user_query[:50]}...'"
            )

            # Build multi-image prompt
            prompt = self._build_multi_image_veterinary_prompt(
                user_query, images_count, context_docs, lang
            )

            # Build message content with all images
            message_content = []

            # Add all images first
            for idx, img_info in enumerate(images_data):
                image_base64, media_type = self._image_to_base64(
                    img_info["data"], img_info["content_type"]
                )

                message_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    }
                )

                logger.debug(
                    f"[VISION MULTI] Image {idx+1}/{images_count} added - {img_info['filename']}"
                )

            # Add prompt text after all images
            message_content.append(
                {
                    "type": "text",
                    "text": prompt,
                }
            )

            # Call Claude Vision API with all images
            logger.debug(
                f"[VISION MULTI] Calling Claude API - Model: {self.model}, Images: {images_count}, Max tokens: {max_tokens}"
            )

            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": message_content,
                    }
                ],
            )

            # Extract response
            analysis_text = message.content[0].text

            # Get usage stats
            usage_info = {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
                "total_tokens": message.usage.input_tokens
                + message.usage.output_tokens,
            }

            logger.info(
                f"[VISION MULTI] Analysis completed - Images: {images_count}, "
                f"Tokens: {usage_info['total_tokens']}"
            )

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
                "images_count": images_count,
            }

        except anthropic.APIError as e:
            logger.error(f"[VISION MULTI] Anthropic API error: {e}")
            return {
                "success": False,
                "error": f"Erreur API Claude: {str(e)}",
                "analysis": None,
            }

        except Exception as e:
            logger.exception(
                f"[VISION MULTI] Unexpected error during multi-image analysis: {e}"
            )
            return {
                "success": False,
                "error": f"Erreur inattendue: {str(e)}",
                "analysis": None,
            }

    def _build_multi_image_veterinary_prompt(
        self,
        user_query: str,
        images_count: int,
        context_docs: Optional[List[Dict]] = None,
        language: str = "fr",
    ) -> str:
        """
        Build specialized veterinary diagnostic prompt for MULTIPLE images

        Args:
            user_query: User's question about the images
            images_count: Number of images being analyzed
            context_docs: Optional RAG context documents
            language: Response language

        Returns:
            Formatted prompt for Claude Vision multi-image analysis
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

CONTEXTE DE L'ANALYSE MULTI-IMAGES:
Tu analyses {images_count} images médicales fournies par un éleveur de volaille qui a posé la question suivante:
"{user_query}"

Ces {images_count} images peuvent montrer:
- Différents angles du même problème
- Différents organes ou zones affectés
- Différents animaux présentant les mêmes symptômes
- L'évolution temporelle d'une maladie

OBJECTIF:
Fournis une analyse médicale structurée et COMPARATIVE basée sur les symptômes visuels observés dans TOUTES les images.

INSTRUCTIONS D'ANALYSE MULTI-IMAGES:

1. **Vue d'ensemble comparative**:
   - Analyse chaque image individuellement d'abord (Image 1, Image 2, etc.)
   - Identifie les similarités et différences entre les images
   - Détermine si elles montrent le même problème ou des problèmes différents

2. **Observation visuelle détaillée**:
   - Pour chaque image, décris les symptômes visibles (couleur, texture, forme, taille, anomalies)
   - Compare les symptômes entre les images
   - Note les caractéristiques physiques inhabituelles
   - Identifie les organes ou zones affectés dans chaque image

3. **Hypothèses diagnostiques consolidées**:
   - En considérant TOUTES les images ensemble, liste 2-3 maladies probables par ordre de probabilité
   - Pour chaque hypothèse, explique quelles images supportent ce diagnostic et pourquoi
   - Mentionne si certaines images montrent des stades différents de la même maladie
   - Précise les causes possibles (virale, bactérienne, parasitaire, nutritionnelle)

4. **Sévérité et étendue**:
   - Évalue la sévérité du problème basée sur l'ensemble des images
   - Détermine si le problème semble localisé ou systémique
   - Indique si plusieurs animaux semblent affectés (si visible)

5. **Facteurs de risque**:
   - Conditions d'élevage qui peuvent favoriser cette maladie
   - Âge typique des animaux affectés
   - Transmission et contagiosité

6. **Actions recommandées** (basées sur l'analyse complète):
   - Tests diagnostiques complémentaires nécessaires
   - Mesures d'urgence (isolement, biosécurité)
   - Traitements possibles (À CONFIRMER PAR VÉTÉRINAIRE)

7. **Prévention**:
   - Mesures de biosécurité
   - Protocoles de vaccination pertinents
   - Gestion de l'environnement

LIMITATIONS:
- Tu fournis une analyse éducative, PAS un diagnostic définitif
- Les photos peuvent ne pas montrer tous les symptômes
- Certaines maladies ont des symptômes similaires nécessitant des tests laboratoire
- L'angle ou la qualité des images peuvent limiter l'analyse

FORMAT DE RÉPONSE:
Structure ta réponse avec des sections claires et des bullet points.
Commence par une analyse image par image, puis consolide vers un diagnostic global.
Utilise un ton professionnel mais accessible.
"""

        # Ajouter contexte RAG si disponible
        if context_docs and len(context_docs) > 0:
            context_text = "\n\n".join(
                [
                    f"Document {i+1}: {doc.get('content', '')[:500]}"
                    for i, doc in enumerate(context_docs[:3])
                ]
            )

            prompt += f"""

CONTEXTE DOCUMENTAIRE ADDITIONNEL:
Les informations suivantes proviennent de notre base de connaissances avicoles et peuvent être pertinentes:

{context_text}

Utilise ces informations comme référence pour enrichir ton analyse comparative si elles sont pertinentes.
"""

        # Messages de suivi pour encourager plus d'images si nécessaire
        followup_question = {
            "fr": "Ces images fournissent une bonne vue d'ensemble. Si vous avez d'autres photos complémentaires (autres angles, autres organes, autres animaux affectés), n'hésitez pas à les partager pour affiner davantage le diagnostic.",
            "en": "These images provide a good overview. If you have other complementary photos (other angles, other organs, other affected animals), feel free to share them to further refine the diagnosis.",
            "es": "Estas imágenes proporcionan una buena visión general. Si tiene otras fotos complementarias (otros ángulos, otros órganos, otros animales afectados), no dude en compartirlas para refinar aún más el diagnóstico.",
            "de": "Diese Bilder bieten einen guten Überblick. Wenn Sie weitere ergänzende Fotos haben (andere Winkel, andere Organe, andere betroffene Tiere), teilen Sie diese gerne mit, um die Diagnose weiter zu verfeinern.",
            "it": "Queste immagini forniscono una buona panoramica. Se hai altre foto complementari (altri angoli, altri organi, altri animali colpiti), sentiti libero di condividerle per affinare ulteriormente la diagnosi.",
            "pt": "Essas imagens fornecem uma boa visão geral. Se você tiver outras fotos complementares (outros ângulos, outros órgãos, outros animais afetados), sinta-se à vontade para compartilhá-las para refinar ainda mais o diagnóstico.",
            "nl": "Deze afbeeldingen bieden een goed overzicht. Als u andere aanvullende foto's heeft (andere hoeken, andere organen, andere getroffen dieren), deel deze dan gerust om de diagnose verder te verfijnen.",
            "pl": "Te obrazy zapewniają dobry przegląd. Jeśli masz inne uzupełniające zdjęcia (inne kąty, inne narządy, inne dotknięte zwierzęta), podziel się nimi, aby jeszcze bardziej doprecyzować diagnozę.",
            "ar": "توفر هذه الصور نظرة عامة جيدة. إذا كان لديك صور تكميلية أخرى (زوايا أخرى، أعضاء أخرى، حيوانات أخرى مصابة)، فلا تتردد في مشاركتها لتحسين التشخيص بشكل أكبر.",
            "zh": "这些图像提供了良好的概览。如果您有其他补充照片（其他角度、其他器官、其他受影响的动物），请随时分享以进一步完善诊断。",
            "ja": "これらの画像は良い概要を提供します。他の補完的な写真（他の角度、他の臓器、他の影響を受けた動物）がある場合は、診断をさらに洗練するために共有してください。",
            "hi": "ये छवियां एक अच्छा अवलोकन प्रदान करती हैं। यदि आपके पास अन्य पूरक तस्वीरें हैं (अन्य कोण, अन्य अंग, अन्य प्रभावित जानवर), तो निदान को और परिष्कृत करने के लिए उन्हें साझा करने में संकोच न करें।",
            "id": "Gambar-gambar ini memberikan gambaran yang baik. Jika Anda memiliki foto pelengkap lainnya (sudut lain, organ lain, hewan lain yang terkena), jangan ragu untuk membagikannya untuk lebih menyempurnakan diagnosis.",
            "th": "ภาพเหล่านี้ให้ภาพรวมที่ดี หากคุณมีรูปภาพเสริมอื่นๆ (มุมอื่นๆ อวัยวะอื่นๆ สัตว์อื่นๆ ที่ได้รับผลกระทบ) อย่าลังเลที่จะแบ่งปันเพื่อปรับปรุงการวินิจฉัยเพิ่มเติม",
            "tr": "Bu görüntüler iyi bir genel bakış sağlıyor. Diğer tamamlayıcı fotoğraflarınız varsa (diğer açılar, diğer organlar, etkilenen diğer hayvanlar), teşhisi daha da iyileştirmek için bunları paylaşmaktan çekinmeyin.",
            "vi": "Những hình ảnh này cung cấp cái nhìn tổng quan tốt. Nếu bạn có các bức ảnh bổ sung khác (góc độ khác, các cơ quan khác, động vật khác bị ảnh hưởng), hãy thoải mái chia sẻ để cải thiện chẩn đoán hơn nữa.",
        }.get(
            language,
            "These images provide a good overview. If you have other complementary photos, feel free to share them to further refine the diagnosis.",
        )

        # Ajouter question de suivi et disclaimer
        prompt += f"""

QUESTION DE SUIVI:
Après ton analyse complète, ajoute cette remarque:
"📸 {followup_question}"

DISCLAIMER OBLIGATOIRE:
À la fin de ta réponse (après la question de suivi), ajoute TOUJOURS cet avertissement:
"⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement. Pour toute préoccupation de santé animale, consultez immédiatement un vétérinaire qualifié. Un diagnostic définitif nécessite un examen clinique complet et potentiellement des tests de laboratoire."
"""

        return prompt

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
