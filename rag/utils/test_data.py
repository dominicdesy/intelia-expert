# -*- coding: utf-8 -*-
"""
utils/test_data.py - Données de test et exemples
Extrait de utilities.py pour modularisation
"""

import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# DONNÉES DE TEST
# ============================================================================

COMPREHENSIVE_TEST_QUERIES = [
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "What is the optimal FCR for Ross 308 at 35 days?",
    "¿Cuál es el peso objetivo a 21 días para Ross 308?",
    "Ross 308在35天时的最佳FCR是多少?",
    "Ross 308 के लिए 35 दिन में अनुकूल FCR क्या है?",
    "อัตราแปลงอาหารที่เหมาะสมสำหรับ Ross 308 อายุ 35 วันคืออะไร?",
]


def setup_logging(level: str = "INFO") -> None:
    """Configure le logging pour l'application"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            (
                logging.FileHandler("app.log")
                if os.getenv("LOG_TO_FILE")
                else logging.NullHandler()
            ),
        ],
    )

    # Suppression des logs verbeux de bibliothèques externes
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    logging.getLogger("openai").setLevel(logging.INFO)
