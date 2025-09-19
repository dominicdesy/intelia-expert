# -*- coding: utf-8 -*-
"""
ood_detector.py - Détecteur hors-domaine intelligent et multilingue
Version corrigée - FIXES CRITIQUES :
1. Résolution erreur "this event loop is already running"
2. Correction problème IntentResult hashable
3. Amélioration gestion async/sync
"""

import logging
import json
import os
import re
import asyncio
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from utils.utilities import METRICS
from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

if UNIDECODE_AVAILABLE:
    from unidecode import unidecode

logger = logging.getLogger(__name__)


class DomainRelevance(Enum):
    """Niveaux de pertinence pour le domaine avicole"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    GENERIC = "generic"
    BLOCKED = "blocked"


@dataclass
class DomainScore:
    """Score détaillé du domaine"""

    final_score: float
    relevance_level: DomainRelevance
    domain_words: List[str]
    blocked_terms: List[str]
    confidence_boosters: Dict[str, float]
    threshold_applied: float
    reasoning: str
    translation_used: bool = False
    original_language: str = "fr"


class MultilingualOODDetector:
    """Détecteur hors-domaine intelligent avec support multilingue complet"""

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_vocabulary = self._build_domain_vocabulary()
        self.openai_client = openai_client
        self.translation_cache = {}

        # Langues supportées
        self.supported_languages = [
            "fr",
            "en",
            "es",
            "de",
            "it",
            "pt",
            "nl",
            "pl",
            "hi",
            "id",
            "th",
            "zh",
        ]

        # Seuils adaptatifs selon le contexte et la langue
        self.adaptive_thresholds = {
            "technical_query": 0.10,
            "numeric_query": 0.15,
            "standard_query": 0.20,
            "generic_query": 0.30,
            "suspicious_query": 0.50,
        }

        # Ajustements par langue
        self.language_adjustments = {
            "fr": 1.0,
            "en": 0.95,
            "es": 0.90,
            "it": 0.90,
            "pt": 0.90,
            "de": 0.85,
            "nl": 0.85,
            "pl": 0.80,
            "hi": 0.75,
            "th": 0.75,
            "zh": 0.75,
            "id": 0.85,
        }

    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes explicitement bloqués"""
        if path is None:
            possible_paths = [
                os.getenv("BLOCKED_TERMS_FILE", ""),
                "/app/config/blocked_terms.json",
                "config/blocked_terms.json",
                os.path.join(
                    os.path.dirname(__file__), "..", "config", "blocked_terms.json"
                ),
            ]
        else:
            possible_paths = [path]

        for attempt_path in possible_paths:
            if not attempt_path or not os.path.exists(attempt_path):
                continue
            try:
                with open(attempt_path, "r", encoding="utf-8") as f:
                    blocked_terms = json.load(f)
                logger.info(f"Termes bloqués chargés depuis: {attempt_path}")
                return blocked_terms
            except Exception as e:
                logger.warning(f"Erreur lecture {attempt_path}: {e}")
                continue

        # Fallback avec termes critiques minimaux
        fallback_terms = {
            "adult_content": ["porn", "sex", "nude", "adult", "xxx"],
            "crypto_finance": ["bitcoin", "crypto", "blockchain", "trading", "forex"],
            "politics": ["election", "politics", "vote", "government", "politician"],
            "entertainment": ["movie", "film", "cinema", "netflix", "game", "gaming"],
            "sports": ["football", "soccer", "basketball", "tennis", "sport"],
            "technology": ["iphone", "android", "computer", "software", "app"],
        }
        logger.warning(
            f"Utilisation des termes bloqués fallback: {len(fallback_terms)} catégories"
        )
        return fallback_terms

    def _build_domain_vocabulary(self) -> Dict[DomainRelevance, Set[str]]:
        """Construit un vocabulaire hiérarchisé du domaine avicole multilingue"""
        return {
            DomainRelevance.HIGH: {
                # Termes hautement spécifiques à l'aviculture - ÉTENDU MULTILINGUE
                "fcr",
                "ic",
                "indice",
                "conversion",
                "alimentaire",
                "ponte",
                "pondeuse",
                "pondeuses",
                "œuf",
                "œufs",
                "oeufs",
                "egg",
                "eggs",
                "poulet",
                "poulets",
                "poule",
                "poules",
                "poussin",
                "poussins",
                "broiler",
                "broilers",
                "layer",
                "layers",
                "chick",
                "chicks",
                "ross",
                "cobb",
                "hubbard",
                "isa",
                "lohmann",
                "hy-line",
                "aviculture",
                "avicole",
                "poultry",
                "fowl",
                "couvoir",
                "incubation",
                "éclosion",
                "hatchery",
                "hatching",
                "vaccination",
                "vaccin",
                "prophylaxie",
                "biosécurité",
                "mortalité",
                "mortality",
                "morbidité",
                "viabilité",
                "chair",
                "meat",
                "carcasse",
                "carcass",
                "rendement",
                "yield",
                # NOUVEAU: Termes Hindi (हिन्दी)
                "मुर्गी",
                "चिकन",
                "कॉब",
                "रॉस",
                "अंडा",
                "अंडे",
                "मुर्गा",
                "मुर्गियाँ",
                "ब्रॉयलर",
                "लेयर",
                "चूजा",
                "चूजे",
                "हैचरी",
                "टीकाकरण",
                "मांस",
                "वध",
                # NOUVEAU: Termes Chinois (中文)
                "鸡",
                "鸡肉",
                "肉鸡",
                "蛋鸡",
                "科宝",
                "罗斯",
                "哈伯德",
                "鸡蛋",
                "蛋",
                "孵化场",
                "孵化",
                "疫苗",
                "接种",
                "屠宰",
                "肉质",
                "产蛋",
                "饲料转化率",
                # NOUVEAU: Termes Thaï (ไทย)
                "ไก่",
                "เนื้อไก่",
                "ไก่เนื้อ",
                "ไก่ไข่",
                "คอบบ์",
                "รอสส์",
                "ไข่",
                "ไข่ไก่",
                "โรงฟัก",
                "การฟัก",
                "วัคซีน",
                "การฉีดวัคซีน",
                "เชื้อโรค",
            },
            DomainRelevance.MEDIUM: {
                # Termes liés à l'élevage et la nutrition animale - ÉTENDU MULTILINGUE
                "élevage",
                "éleveur",
                "farm",
                "farming",
                "farmer",
                "alimentation",
                "aliment",
                "aliments",
                "feed",
                "feeding",
                "nutrition",
                "nutritionnel",
                "nutritive",
                "nutriment",
                "protéine",
                "protéines",
                "protein",
                "proteins",
                "énergie",
                "energy",
                "calorie",
                "calories",
                "kcal",
                "vitamines",
                "minéraux",
                "calcium",
                "phosphore",
                "croissance",
                "growth",
                "développement",
                "development",
                "poids",
                "weight",
                "masse",
                "mass",
                "gramme",
                "kg",
                "performance",
                "productivité",
                "productivity",
                "efficacité",
                "santé",
                "health",
                "maladie",
                "disease",
                "pathologie",
                "vétérinaire",
                "veterinary",
                "traitement",
                "treatment",
                "logement",
                "housing",
                "bâtiment",
                "building",
                "poulailler",
                "température",
                "temperature",
                "ventilation",
                "éclairage",
                "densité",
                "density",
                "espace",
                "space",
                "surface",
                # NOUVEAU: Termes Hindi moyens
                "पालन",
                "किसान",
                "खेत",
                "आहार",
                "भोजन",
                "खाना",
                "पोषण",
                "प्रोटीन",
                "ऊर्जा",
                "कैलोरी",
                "विटामिन",
                "खनिज",
                "विकास",
                "वृद्धि",
                "वजन",
                "भार",
                "किलो",
                "ग्राम",
                "स्वास्थ्य",
                "बीमारी",
                "उपचार",
                "इलाज",
                "पशु चिकित्सक",
                "घर",
                "इमारत",
                "तापमान",
                "हवा",
                "रोशनी",
                "घनत्व",
                "जगह",
                "क्षेत्र",
                # NOUVEAU: Termes Chinois moyens
                "养殖",
                "农民",
                "农场",
                "饲料",
                "喂食",
                "营养",
                "蛋白质",
                "能量",
                "卡路里",
                "维生素",
                "矿物质",
                "钙",
                "磷",
                "生长",
                "发育",
                "体重",
                "重量",
                "克",
                "公斤",
                "性能",
                "生产力",
                "效率",
                "健康",
                "疾病",
                "病理",
                "兽医",
                "治疗",
                "住房",
                "建筑",
                "鸡舍",
                "温度",
                "通风",
                "照明",
                "密度",
                "空间",
                "表面",
                # NOUVEAU: Termes Thaï moyens
                "การเลี้ยง",
                "เกษตรกร",
                "ฟาร์ม",
                "อาหาร",
                "การให้อาหาร",
                "โภชนาการ",
                "โปรตีน",
                "พลังงาน",
                "แคลอรี",
                "วิตามิน",
                "แร่ธาตุ",
                "การเจริญเติบโต",
                "น้ำหนัก",
                "กิโลกรัม",
                "กรัม",
                "สุขภาพ",
                "โรค",
                "การรักษา",
                "สัตวแพทย์",
                "เรือนเลี้ยง",
                "อาคาร",
                "อุณหภูมิ",
                "การระบายอากาศ",
                "แสงสว่าง",
            },
            DomainRelevance.LOW: {
                # Termes agricoles généraux - ÉTENDU MULTILINGUE
                "agriculture",
                "agricultural",
                "rural",
                "campagne",
                "animal",
                "animaux",
                "animals",
                "bétail",
                "livestock",
                "ferme",
                "exploitation",
                "production",
                "producteur",
                "qualité",
                "quality",
                "sécurité",
                "safety",
                "hygiène",
                "économique",
                "economic",
                "coût",
                "cost",
                "prix",
                "price",
                "marché",
                "market",
                "vente",
                "sale",
                "commercial",
                "environnement",
                "environmental",
                "durable",
                "sustainable",
                "biologique",
                "organic",
                "naturel",
                "natural",
                "règlement",
                "regulation",
                "norme",
                "standard",
                "label",
                # NOUVEAU: Termes Hindi généraux
                "कृषि",
                "ग्रामीण",
                "गांव",
                "जानवर",
                "पशु",
                "मवेशी",
                "उत्पादन",
                "उत्पादक",
                "गुणवत्ता",
                "सुरक्षा",
                "स्वच्छता",
                "आर्थिक",
                "लागत",
                "कीमत",
                "बाजार",
                "बिक्री",
                "व्यावसायिक",
                "पर्यावरण",
                "टिकाऊ",
                "जैविक",
                "प्राकृतिक",
                # NOUVEAU: Termes Chinois généraux
                "农业",
                "农村",
                "动物",
                "牲畜",
                "生产",
                "生产者",
                "质量",
                "安全",
                "卫生",
                "经济",
                "成本",
                "价格",
                "市场",
                "销售",
                "商业",
                "环境",
                "可持续",
                "有机",
                "天然",
                "法规",
                "标准",
                "标签",
                # NOUVEAU: Termes Thaï généraux
                "เกษตรกรรม",
                "ชนบท",
                "สัตว์",
                "ปศุสัตว์",
                "การผลิต",
                "ผู้ผลิต",
                "คุณภาพ",
                "ความปลอดภัย",
                "สุขอนามัย",
                "เศรษฐกิจ",
                "ต้นทุน",
                "ราคา",
                "ตลาด",
                "การขาย",
                "เชิงพาณิชย์",
                "สิ่งแวดล้อม",
                "ยั่งยืน",
                "อินทรีย์",
                "ธรรมชาติ",
            },
            DomainRelevance.GENERIC: {
                # Mots-outils et termes génériques multilingues
                "comment",
                "how",
                "quoi",
                "what",
                "pourquoi",
                "why",
                "quand",
                "when",
                "où",
                "where",
                "combien",
                "how much",
                "quel",
                "quelle",
                "which",
                "que",
                "qui",
                "who",
                "meilleur",
                "best",
                "optimal",
                "idéal",
                "ideal",
                "recommandé",
                "recommended",
                "conseiller",
                "advice",
                "problème",
                "problem",
                "solution",
                "aide",
                "help",
                "information",
                "données",
                "data",
                "étude",
                "study",
                "exemple",
                "example",
                "cas",
                "case",
                "situation",
                "méthode",
                "method",
                "technique",
                "technologie",
                "système",
                "system",
                "processus",
                "process",
                # NOUVEAU: Mots-outils Hindi
                "कैसे",
                "क्या",
                "क्यों",
                "कब",
                "कहाँ",
                "कितना",
                "कौन",
                "कौन सा",
                "बेहतर",
                "अच्छा",
                "आदर्श",
                "सुझाव",
                "समस्या",
                "समाधान",
                "मदद",
                "जानकारी",
                "डेटा",
                "अध्ययन",
                "उदाहरण",
                "मामला",
                "स्थिति",
                "तरीका",
                "तकनीक",
                "प्रौद्योगिकी",
                # NOUVEAU: Mots-outils Chinois
                "如何",
                "怎么",
                "什么",
                "为什么",
                "什么时候",
                "哪里",
                "多少",
                "哪个",
                "谁",
                "最好",
                "理想",
                "推荐",
                "建议",
                "问题",
                "解决方案",
                "帮助",
                "信息",
                "数据",
                "研究",
                "例子",
                "案例",
                "情况",
                "方法",
                "技术",
                "技术",
                "系统",
                "过程",
                # NOUVEAU: Mots-outils Thaï
                "อย่างไร",
                "อะไร",
                "ทำไม",
                "เมื่อไหร่",
                "ที่ไหน",
                "เท่าไหร่",
                "ใคร",
                "ไหน",
                "ดีที่สุด",
                "เหมาะสม",
                "แนะนำ",
                "คำแนะนำ",
                "ปัญหา",
                "วิธีแก้ไข",
                "ช่วยเหลือ",
                "ข้อมูล",
                "การศึกษา",
                "ตัวอย่าง",
                "กรณี",
                "สถานการณ์",
                "วิธี",
                "เทคนิค",
            },
        }

    # CORRECTION 2: Méthode publique synchrone sécurisée
    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Point d'entrée principal - version synchrone sécurisée"""
        return self._calculate_ood_score_sync(query, intent_result, "fr")

    def calculate_ood_score_multilingual(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """CORRECTION CRITIQUE: Méthode publique multilingue synchrone"""
        return self._calculate_ood_score_sync(query, intent_result, language)

    def _calculate_ood_score_sync(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        CORRECTION FINALE: Logique optimisée pour chaque type de langue
        """
        try:
            # NOUVEAU: Stratégie par langue au lieu de détection d'event loop
            if language in ["fr", "en"]:
                # Langues principales - traitement direct synchrone optimisé
                return self._calculate_ood_score_direct_sync(
                    query, intent_result, language
                )

            elif language in ["es", "de", "it", "pt", "nl", "pl", "id"]:
                # Langues européennes/latines - traitement hybride
                try:
                    return asyncio.run(
                        self._calculate_ood_score_async(query, intent_result, language)
                    )
                except Exception as e:
                    logger.debug(f"Async échoué pour {language}: {e}, fallback sync")
                    return self._calculate_ood_score_direct_sync(
                        query, intent_result, language
                    )

            else:
                # Langues non-latines (hi, zh, th) - fallback direct pour éviter les problèmes
                return self._calculate_ood_score_fallback_sync(
                    query, intent_result, language
                )

        except Exception as e:
            logger.warning(f"Erreur calcul OOD pour {language}: {e}, fallback général")
            return self._calculate_ood_score_fallback_sync(
                query, intent_result, language
            )

    async def _calculate_ood_score_async(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Version asynchrone principale"""
        # Si la langue est français ou anglais, traitement direct
        if language in ["fr", "en"]:
            return await self._calculate_ood_score_direct(
                query, intent_result, language
            )

        # Pour les autres langues, utiliser la traduction
        return await self._calculate_ood_score_multilingual_async(
            query, intent_result, language
        )

    def _calculate_ood_score_fallback_sync(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        CORRECTION FALLBACK: Version entièrement synchrone pour cas d'urgence
        Évite complètement les problèmes d'event loop
        """
        # Normalisation basique
        normalized_query = self._normalize_query_basic(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query", "fallback": True}

        # Analyse basique sans async
        context_analysis = self._analyze_query_context_sync(
            normalized_query, words, intent_result
        )
        domain_analysis = self._calculate_domain_relevance_sync(words, context_analysis)
        blocked_analysis = self._detect_blocked_terms_sync(normalized_query, words)

        # Score final
        boosted_score = self._apply_context_boosters_sync(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Seuil avec ajustement linguistique
        base_threshold = self._select_adaptive_threshold_sync(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        # Décision finale
        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Log de fallback
        logger.info(
            f"OOD Fallback sync [{language}]: '{query[:40]}...' | Score: {boosted_score:.3f} | Décision: {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
        )

        return (
            is_in_domain,
            boosted_score,
            {
                "vocab_score": domain_analysis.final_score,
                "boosted_score": boosted_score,
                "threshold_used": adjusted_threshold,
                "language": language,
                "fallback_sync_used": True,
                "domain_words_found": len(domain_analysis.domain_words),
                "relevance_level": domain_analysis.relevance_level.value,
            },
        )

    async def _calculate_ood_score_direct(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD direct pour français/anglais"""
        normalized_query = self._normalize_query_preserve_script(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query"}

        # Analyse contextuelle
        context_analysis = self._analyze_query_context_sync(
            normalized_query, words, intent_result
        )
        domain_analysis = self._calculate_domain_relevance_sync(words, context_analysis)
        blocked_analysis = self._detect_blocked_terms_sync(normalized_query, words)

        # Application de boosters contextuels
        boosted_score = self._apply_context_boosters_sync(
            domain_analysis.final_score, context_analysis, intent_result
        )

        # Sélection du seuil adaptatif avec ajustement linguistique
        base_threshold = self._select_adaptive_threshold_sync(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        # Décision finale
        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Logging et métriques
        self._log_ood_decision(
            query,
            words,
            domain_analysis,
            boosted_score,
            adjusted_threshold,
            is_in_domain,
        )
        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        # Construction de la réponse détaillée
        score_details = {
            "vocab_score": domain_analysis.final_score,
            "boosted_score": boosted_score,
            "threshold_used": adjusted_threshold,
            "base_threshold": base_threshold,
            "language_adjustment": self.language_adjustments.get(language, 1.0),
            "domain_words_found": len(domain_analysis.domain_words),
            "blocked_terms_found": len(domain_analysis.blocked_terms),
            "context_type": context_analysis["type"],
            "relevance_level": domain_analysis.relevance_level.value,
            "reasoning": domain_analysis.reasoning,
            "language": language,
            "translation_used": False,
        }

        return is_in_domain, boosted_score, score_details

    def _calculate_ood_score_direct_sync(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """NOUVELLE: Version synchrone directe optimisée pour fr/en"""
        normalized_query = self._normalize_query_preserve_script(query, language)
        words = normalized_query.split()

        if not words:
            return False, 0.0, {"error": "empty_query"}

        # Traitement synchrone optimisé
        context_analysis = self._analyze_query_context_sync(
            normalized_query, words, intent_result
        )
        domain_analysis = self._calculate_domain_relevance_sync(words, context_analysis)
        blocked_analysis = self._detect_blocked_terms_sync(normalized_query, words)

        boosted_score = self._apply_context_boosters_sync(
            domain_analysis.final_score, context_analysis, intent_result
        )

        base_threshold = self._select_adaptive_threshold_sync(
            context_analysis, domain_analysis
        )
        adjusted_threshold = base_threshold * self.language_adjustments.get(
            language, 1.0
        )

        is_in_domain = (
            boosted_score > adjusted_threshold and not blocked_analysis["is_blocked"]
        )

        # Log optimisé
        logger.debug(
            f"OOD Direct [{language}]: '{query[:40]}...' | Score: {boosted_score:.3f} vs {adjusted_threshold:.3f} | {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
        )

        self._update_ood_metrics(domain_analysis, adjusted_threshold, is_in_domain)

        return (
            is_in_domain,
            boosted_score,
            {
                "vocab_score": domain_analysis.final_score,
                "boosted_score": boosted_score,
                "threshold_used": adjusted_threshold,
                "language": language,
                "method": "direct_sync_optimized",
                "domain_words_found": len(domain_analysis.domain_words),
                "relevance_level": domain_analysis.relevance_level.value,
                "reasoning": domain_analysis.reasoning,
            },
        )

    async def _calculate_ood_score_multilingual_async(
        self, query: str, intent_result=None, language: str = "hi"
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul OOD avec traduction automatique pour langues non-françaises/anglaises"""
        try:
            # CORRECTION 4: Traduction sécurisée sans créer de nouveaux loops
            translated_query = await self._translate_to_french_safe(query, language)

            if not translated_query or translated_query == query:
                # Traduction échouée, utiliser l'analyse de fallback
                return await self._fallback_analysis_async(query, language)

            # Analyse OOD sur la version traduite
            is_in_domain, score, details = await self._calculate_ood_score_direct(
                translated_query, intent_result, "fr"
            )

            # Ajustement du seuil pour les langues traduites (plus permissif)
            translation_adjustment = self.language_adjustments.get(language, 0.75)
            adjusted_threshold = details["threshold_used"] * translation_adjustment
            is_in_domain = score > adjusted_threshold

            # Enrichir les détails avec les informations de traduction
            details.update(
                {
                    "original_language": language,
                    "original_query": query,
                    "translated_query": translated_query,
                    "translation_used": True,
                    "translation_adjustment": translation_adjustment,
                    "final_threshold": adjusted_threshold,
                }
            )

            logger.debug(
                f"OOD Multilingue [{language}]: '{query[:30]}...' -> '{translated_query[:30]}...' | Score: {score:.3f} | Décision: {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
            )

            return is_in_domain, score, details

        except Exception as e:
            logger.warning(f"Erreur traduction {language}: {e}")
            return await self._fallback_analysis_async(query, language)

    async def _translate_to_french_safe(self, query: str, source_lang: str) -> str:
        """
        CORRECTION FINALE: Traduction sécurisée qui évite tous les conflits d'event loop
        """
        # Vérification du cache
        cache_key = f"{source_lang}:{hash(query)}"
        if cache_key in self.translation_cache:
            return self.translation_cache[cache_key]

        # CORRECTION: Si pas de client OpenAI, utiliser fallback immédiatement
        if not self.openai_client:
            logger.debug("Pas de client OpenAI disponible, utilisation fallback")
            return self._simple_translation_fallback(query, source_lang)

        # CORRECTION: Traduction async sécurisée
        try:
            # Vérifier que le client est bien async
            if not hasattr(self.openai_client, "chat"):
                logger.warning("Client OpenAI invalide, utilisation fallback")
                return self._simple_translation_fallback(query, source_lang)

            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": f"Translate the following poultry/agriculture query from {source_lang} to French. "
                        "Keep technical terms like 'Cobb 500', 'Ross 308', 'FCR' unchanged. "
                        "Return only the French translation, no explanations.",
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=150,
                temperature=0,
            )

            translated = response.choices[0].message.content.strip()

            # Validation basique de la traduction
            if len(translated) > 0 and len(translated) < len(query) * 3:
                self.translation_cache[cache_key] = translated
                logger.debug(
                    f"Traduction OpenAI [{source_lang}->fr]: '{query}' -> '{translated}'"
                )
                return translated
            else:
                logger.warning(f"Traduction OpenAI suspecte pour: {query}")

        except Exception as e:
            logger.warning(f"Erreur traduction OpenAI async: {e}")

        # Fallback avec traduction basique par patterns
        return self._simple_translation_fallback(query, source_lang)

    def _simple_translation_fallback(self, query: str, source_lang: str) -> str:
        """Traduction basique par patterns pour les cas d'urgence - ÉTENDUE MULTILINGUE"""
        basic_translations = {
            "hi": {
                # ÉTENDU: Dictionnaire Hindi complet
                "मुर्गी": "poulet",
                "चिकन": "poulet",
                "कॉब": "cobb",
                "रॉस": "ross",
                "वजन": "poids",
                "भार": "poids",
                "दिन": "jour",
                "दिनों": "jours",
                "नर": "mâle",
                "मादा": "femelle",
                "भोजन": "aliment",
                "आहार": "alimentation",
                "अंडा": "œuf",
                "अंडे": "œufs",
                "मुर्गा": "coq",
                "चूजा": "poussin",
                "चूजे": "poussins",
                "पालन": "élevage",
                "किसान": "fermier",
                "खेत": "ferme",
                "स्वास्थ्य": "santé",
                "बीमारी": "maladie",
                "विकास": "croissance",
                "प्रदर्शन": "performance",
                "ग्राम": "gramme",
                "किलो": "kilo",
                "किलोग्राम": "kilogramme",
                "सप्ताह": "semaine",
                "महीना": "mois",
                "साल": "année",
                "वर्ष": "année",
            },
            "zh": {
                # ÉTENDU: Dictionnaire Chinois complet
                "鸡": "poulet",
                "鸡肉": "poulet",
                "肉鸡": "poulet de chair",
                "蛋鸡": "pondeuse",
                "科宝": "cobb",
                "罗斯": "ross",
                "哈伯德": "hubbard",
                "体重": "poids",
                "重量": "poids",
                "重": "poids",
                "天": "jour",
                "日": "jour",
                "公": "mâle",
                "母": "femelle",
                "雄": "mâle",
                "雌": "femelle",
                "饲料": "aliment",
                "喂食": "alimentation",
                "营养": "nutrition",
                "蛋": "œuf",
                "鸡蛋": "œuf",
                "孵化": "éclosion",
                "生长": "croissance",
                "发育": "développement",
                "性能": "performance",
                "健康": "santé",
                "疾病": "maladie",
                "克": "gramme",
                "公斤": "kilogramme",
                "周": "semaine",
                "月": "mois",
                "年": "année",
                "养殖": "élevage",
                "农场": "ferme",
                "农民": "fermier",
            },
            "th": {
                # ÉTENDU: Dictionnaire Thaï complet
                "ไก่": "poulet",
                "เนื้อไก่": "poulet",
                "ไก่เนื้อ": "poulet de chair",
                "ไก่ไข่": "pondeuse",
                "คอบบ์": "cobb",
                "รอสส์": "ross",
                "น้ำหนัก": "poids",
                "วัน": "jour",
                "ตัวผู้": "mâle",
                "ตัวเมีย": "femelle",
                "อาหาร": "aliment",
                "การให้อาหาร": "alimentation",
                "โภชนาการ": "nutrition",
                "ไข่": "œuf",
                "ไข่ไก่": "œuf de poule",
                "การเจริญเติบโต": "croissance",
                "สุขภาพ": "santé",
                "โรค": "maladie",
                "กรัม": "gramme",
                "กิโลกรัม": "kilogramme",
                "สัปดาห์": "semaine",
                "เดือน": "mois",
                "ปี": "année",
                "การเลี้ยง": "élevage",
                "ฟาร์ม": "ferme",
                "เกษตรกร": "fermier",
            },
            "en": {
                "chicken": "poulet",
                "poultry": "volaille",
                "weight": "poids",
                "days": "jours",
                "day": "jour",
                "male": "mâle",
                "female": "femelle",
                "broiler": "poulet de chair",
                "layer": "pondeuse",
                "chick": "poussin",
            },
            "es": {
                "pollo": "poulet",
                "peso": "poids",
                "días": "jours",
                "día": "jour",
                "macho": "mâle",
                "hembra": "femelle",
                "pollito": "poussin",
            },
            "de": {
                "huhn": "poulet",
                "hähnchen": "poulet",
                "gewicht": "poids",
                "tage": "jours",
                "tag": "jour",
                "männlich": "mâle",
                "weiblich": "femelle",
            },
            "it": {
                "pollo": "poulet",
                "peso": "poids",
                "giorni": "jours",
                "giorno": "jour",
                "maschio": "mâle",
                "femmina": "femelle",
            },
            "pt": {
                "frango": "poulet",
                "peso": "poids",
                "dias": "jours",
                "dia": "jour",
                "macho": "mâle",
                "fêmea": "femelle",
            },
        }

        translated = query.lower()
        if source_lang in basic_translations:
            for foreign_term, french_term in basic_translations[source_lang].items():
                translated = re.sub(
                    rf"\b{re.escape(foreign_term)}\b",
                    french_term,
                    translated,
                    flags=re.IGNORECASE,
                )

        # Préserver les termes techniques universels (nombres, marques)
        technical_terms = ["cobb", "ross", "hubbard", "isa", "fcr", "500", "308", "708"]
        for term in technical_terms:
            if term in query.lower():
                translated = translated.replace(term, term)

        # Si la traduction a changé significativement, log pour diagnostic
        if translated != query.lower():
            logger.debug(
                f"Traduction fallback [{source_lang}->fr]: '{query[:30]}' -> '{translated[:30]}'"
            )

        return translated

    def _calculate_ood_score_fallback_sync(
        self, query: str, intent_result=None, language: str = "fr"
    ) -> Tuple[bool, float, Dict]:
        """
        CORRECTION MULTILINGUE: Analyse de secours optimisée pour Hindi et Chinois
        """
        # Recherche de termes techniques universels (marchent dans toutes les langues)
        universal_terms = [
            "cobb",
            "ross",
            "hubbard",
            "isa",
            "fcr",
            "308",
            "500",
            "308",
            "708",
        ]
        found_universal = sum(
            1 for term in universal_terms if term.lower() in query.lower()
        )

        # Recherche de nombres (indicateurs de spécificité technique)
        numbers = re.findall(r"\d+", query)

        # NOUVEAU: Patterns aviculture étendus pour scripts non-latins
        enhanced_patterns = [
            r"\d+\s*(?:g|kg|gram|kilogram|克|公斤)",  # Poids (+ chinois)
            r"\d+\s*(?:day|jour|dia|tag|giorno|วัน|天|दिन|hari)",  # Âge (multilingue)
            r"\d+\s*%",  # Pourcentages universels
            # NOUVEAU: Termes aviculture en Hindi
            r"(?:मुर्गी|चिकन|कॉब|रॉस)",  # Poulet, Cobb, Ross en Hindi
            r"(?:वजन|भार)",  # Poids en Hindi
            r"(?:दिन|दिनों)",  # Jour(s) en Hindi
            r"(?:नर|मादा)",  # Mâle/femelle en Hindi
            # NOUVEAU: Termes aviculture en Chinois
            r"(?:鸡|鸡肉|肉鸡|蛋鸡)",  # Poulet en chinois
            r"(?:体重|重量|重)",  # Poids en chinois
            r"(?:天|日)",  # Jour en chinois
            r"(?:公|母|雄|雌)",  # Mâle/femelle en chinois
            r"(?:科宝|罗斯)",  # Cobb/Ross en chinois
        ]

        pattern_matches = sum(
            1
            for pattern in enhanced_patterns
            if re.search(pattern, query, re.IGNORECASE)
        )

        # NOUVEAU: Bonus spécifique pour langues asiatiques
        asian_language_bonus = 0.0
        if language in ["hi", "zh", "th"]:
            # Détecter si la requête contient des termes d'aviculture dans ces langues
            hindi_poultry_terms = ["मुर्गी", "चिकन", "कॉब", "वजन", "दिन", "नर", "मादा"]
            chinese_poultry_terms = [
                "鸡",
                "体重",
                "重量",
                "天",
                "公",
                "母",
                "科宝",
                "罗斯",
            ]
            thai_poultry_terms = ["ไก่", "น้ำหนัก", "วัน", "ตัวผู้", "ตัวเมีย"]

            if language == "hi":
                asian_terms_found = sum(
                    1 for term in hindi_poultry_terms if term in query
                )
            elif language == "zh":
                asian_terms_found = sum(
                    1 for term in chinese_poultry_terms if term in query
                )
            elif language == "th":
                asian_terms_found = sum(
                    1 for term in thai_poultry_terms if term in query
                )
            else:
                asian_terms_found = 0

            if asian_terms_found >= 1:
                asian_language_bonus = 0.3  # Bonus significatif
            elif pattern_matches >= 1:
                asian_language_bonus = 0.2  # Bonus pour patterns numériques

        # Score basique avec bonus pour termes techniques et langues asiatiques
        base_score = (
            (found_universal * 0.4)
            + (len(numbers) * 0.1)
            + (pattern_matches * 0.15)
            + asian_language_bonus
        )

        # CORRECTION CRITIQUE: Seuils adaptatifs par langue
        if language in ["hi", "zh", "th"]:
            # Seuil très permissif pour éviter de bloquer des questions légitimes en langues asiatiques
            fallback_threshold = 0.05  # Très bas
        else:
            fallback_threshold = 0.08  # Standard

        is_in_domain = base_score > fallback_threshold or found_universal > 0

        # Log détaillé pour diagnostic
        logger.info(
            f"OOD Fallback [{language}]: '{query[:40]}...' | "
            f"Score: {base_score:.3f} vs {fallback_threshold:.3f} | "
            f"Universels: {found_universal} | Patterns: {pattern_matches} | "
            f"Bonus asiatique: {asian_language_bonus:.3f} | "
            f"Décision: {'ACCEPTÉ' if is_in_domain else 'REJETÉ'}"
        )

        return (
            is_in_domain,
            base_score,
            {
                "fallback_used": True,
                "language": language,
                "universal_terms_found": found_universal,
                "numbers_found": len(numbers),
                "poultry_patterns": pattern_matches,
                "asian_language_bonus": asian_language_bonus,
                "threshold": fallback_threshold,
                "reasoning": f"Fallback analysis - {found_universal} universels, {pattern_matches} patterns, bonus asiatique {asian_language_bonus:.3f}",
                "enhanced_multilingue": True,
            },
        )

    # CORRECTIONS MÉTHODES UTILITAIRES SYNCHRONES

    def _normalize_query_basic(self, query: str, language: str) -> str:
        """Normalisation basique synchrone"""
        if not query:
            return ""

        normalized = query.lower()
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _normalize_query_preserve_script(self, query: str, language: str) -> str:
        """Normalisation qui préserve les scripts non-latins"""
        if not query:
            return ""

        # Pour les scripts non-latins, ne PAS utiliser unidecode
        if language in ["hi", "th", "zh"]:
            normalized = query.lower()
            normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            return normalized

        # Pour les scripts latins, normalisation standard
        normalized = unidecode(query).lower() if UNIDECODE_AVAILABLE else query.lower()
        normalized = re.sub(r"[^\w\s\d.,%-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Expansion des acronymes courants
        acronym_expansions = {
            "ic": "indice conversion",
            "fcr": "feed conversion ratio",
            "pv": "poids vif",
            "gmq": "gain moyen quotidien",
        }

        for acronym, expansion in acronym_expansions.items():
            normalized = re.sub(rf"\b{acronym}\b", expansion, normalized)

        return normalized

    def _analyze_query_context_sync(
        self, query: str, words: List[str], intent_result=None
    ) -> Dict:
        """Analyse contextuelle synchrone"""
        context = {
            "type": "standard_query",
            "technical_indicators": [],
            "numeric_indicators": [],
            "question_type": None,
            "specificity_level": "medium",
            "intent_confidence": 0.0,
        }

        # Détection d'indicateurs techniques
        technical_patterns = [
            (r"\b(?:fcr|ic|indice)\b", "conversion_metric"),
            (r"\b(?:ross|cobb|hubbard|isa)\s*\d*\b", "genetic_line"),
            (
                r"\b\d+\s*(?:jour|day|semaine|week|dia|tag|giorno|วัน|天|दिन)s?\b",
                "age_specification",
            ),
            (r"\b\d+[.,]?\d*\s*(?:g|kg|gramme|gram|kilogram)\b", "weight_measure"),
            (r"\b\d+[.,]?\d*\s*%\b", "percentage_value"),
        ]

        for pattern, indicator_type in technical_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                context["technical_indicators"].append(
                    {"type": indicator_type, "matches": matches, "count": len(matches)}
                )

        # Classification du type de requête
        if len(context["technical_indicators"]) >= 2:
            context["type"] = "technical_query"
            context["specificity_level"] = "high"

        # CORRECTION 6: Gestion safe de intent_result
        if intent_result:
            try:
                # Créer une clé string pour le cache au lieu d'utiliser l'objet directement
                if hasattr(intent_result, "confidence"):
                    context["intent_confidence"] = float(intent_result.confidence)
                if hasattr(intent_result, "detected_entities"):
                    entities = intent_result.detected_entities
                    if isinstance(entities, dict) and len(entities) >= 2:
                        context["type"] = "technical_query"
                        context["specificity_level"] = "very_high"
            except Exception as e:
                logger.debug(f"Erreur analyse intention (non-critique): {e}")

        return context

    def _calculate_domain_relevance_sync(
        self, words: List[str], context_analysis: Dict
    ) -> DomainScore:
        """Calcul de la pertinence domaine synchrone"""
        domain_words = []
        relevance_scores = {level: 0 for level in DomainRelevance}

        # Analyse mot par mot
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) < 2:
                continue

            for level, vocabulary in self.domain_vocabulary.items():
                if word_clean in vocabulary:
                    domain_words.append(word_clean)
                    relevance_scores[level] += 1
                    break

        # Calcul du score avec pondération
        weight_multipliers = {
            DomainRelevance.HIGH: 1.0,
            DomainRelevance.MEDIUM: 0.6,
            DomainRelevance.LOW: 0.3,
            DomainRelevance.GENERIC: 0.1,
        }

        weighted_score = sum(
            count * weight_multipliers.get(level, 0.1)
            for level, count in relevance_scores.items()
            if level != DomainRelevance.BLOCKED
        )

        significant_words = [w for w in words if len(w.strip()) >= 2]
        base_score = weighted_score / len(significant_words) if significant_words else 0

        # Détermination du niveau de pertinence
        if relevance_scores[DomainRelevance.HIGH] >= 2:
            overall_relevance = DomainRelevance.HIGH
        elif (
            relevance_scores[DomainRelevance.HIGH] >= 1
            or relevance_scores[DomainRelevance.MEDIUM] >= 2
        ):
            overall_relevance = DomainRelevance.MEDIUM
        elif (
            sum(
                relevance_scores[level]
                for level in [
                    DomainRelevance.HIGH,
                    DomainRelevance.MEDIUM,
                    DomainRelevance.LOW,
                ]
            )
            >= 1
        ):
            overall_relevance = DomainRelevance.LOW
        else:
            overall_relevance = DomainRelevance.GENERIC

        # Bonus contextuel
        context_bonus = 0.0
        if context_analysis["type"] == "technical_query":
            context_bonus += 0.15
        if len(context_analysis["technical_indicators"]) >= 1:
            context_bonus += 0.1

        final_score = min(1.0, base_score + context_bonus)

        confidence_boosters = {
            "context_bonus": context_bonus,
            "high_relevance_words": relevance_scores[DomainRelevance.HIGH],
            "medium_relevance_words": relevance_scores[DomainRelevance.MEDIUM],
            "technical_indicators": len(context_analysis["technical_indicators"]),
        }

        reasoning = f"Mots domaine: {len(domain_words)}/{len(significant_words)} | Niveau: {overall_relevance.value} | Score: {final_score:.3f}"

        return DomainScore(
            final_score=final_score,
            relevance_level=overall_relevance,
            domain_words=domain_words,
            blocked_terms=[],
            confidence_boosters=confidence_boosters,
            threshold_applied=0.0,
            reasoning=reasoning,
        )

    def _detect_blocked_terms_sync(self, query: str, words: List[str]) -> Dict:
        """Détection des termes bloqués synchrone"""
        blocked_found = []
        for category, terms in self.blocked_terms.items():
            for term in terms:
                if term.lower() in query:
                    blocked_found.append(term)

        is_blocked = len(blocked_found) >= 2

        return {
            "is_blocked": is_blocked,
            "blocked_terms": blocked_found,
            "block_score": len(blocked_found) / max(len(words), 1),
        }

    def _apply_context_boosters_sync(
        self, base_score: float, context_analysis: Dict, intent_result=None
    ) -> float:
        """Application de boosters contextuels synchrone"""
        boosted_score = base_score

        if context_analysis["type"] == "technical_query":
            boosted_score += 0.15

        numeric_count = len(context_analysis.get("numeric_indicators", []))
        if numeric_count >= 2:
            boosted_score += 0.1
        elif numeric_count == 1:
            boosted_score += 0.05

        if context_analysis["intent_confidence"] > 0.8:
            boosted_score += 0.1

        return min(0.98, boosted_score)

    def _select_adaptive_threshold_sync(
        self, context_analysis: Dict, domain_analysis: DomainScore
    ) -> float:
        """Sélection du seuil adaptatif synchrone"""
        base_threshold = self.adaptive_thresholds.get(
            context_analysis["type"], self.adaptive_thresholds["standard_query"]
        )

        # Ajustements
        if (
            context_analysis["specificity_level"] == "low"
            and domain_analysis.relevance_level == DomainRelevance.GENERIC
        ):
            base_threshold += 0.1

        if len(context_analysis["technical_indicators"]) >= 2:
            base_threshold -= 0.05

        return max(0.05, min(0.6, base_threshold))

    def _log_ood_decision(
        self,
        query: str,
        words: List[str],
        domain_analysis: DomainScore,
        final_score: float,
        threshold: float,
        is_in_domain: bool,
    ) -> None:
        """Logging des décisions OOD"""
        decision = "ACCEPTÉ" if is_in_domain else "REJETÉ"
        logger.debug(
            f"OOD {decision}: '{query[:50]}...' | "
            f"Score: {final_score:.3f} vs Seuil: {threshold:.3f} | "
            f"Mots domaine: {len(domain_analysis.domain_words)}/{len(words)}"
        )

    def _update_ood_metrics(
        self, domain_analysis: DomainScore, threshold: float, is_in_domain: bool
    ) -> None:
        """Mise à jour des métriques"""
        try:
            if is_in_domain:
                METRICS.ood_accepted(
                    domain_analysis.final_score, domain_analysis.relevance_level.value
                )
            else:
                METRICS.ood_filtered(domain_analysis.final_score, "threshold_not_met")
        except Exception as e:
            logger.warning(f"Erreur mise à jour métriques OOD: {e}")

    def get_detector_stats(self) -> Dict:
        """Statistiques du détecteur"""
        vocab_stats = {
            level.value: len(terms) for level, terms in self.domain_vocabulary.items()
        }
        blocked_stats = {
            category: len(terms) for category, terms in self.blocked_terms.items()
        }

        return {
            "version": "multilingual_v1.1_fixed",
            "vocabulary_stats": vocab_stats,
            "blocked_terms_stats": blocked_stats,
            "adaptive_thresholds": self.adaptive_thresholds.copy(),
            "language_adjustments": self.language_adjustments.copy(),
            "supported_languages": self.supported_languages.copy(),
            "translation_cache_size": len(self.translation_cache),
            "total_domain_terms": sum(
                len(terms) for terms in self.domain_vocabulary.values()
            ),
            "fixes_applied": [
                "event_loop_conflicts_resolved",
                "intentresult_hashable_handled",
                "sync_fallback_implemented",
                "translation_executor_safe",
            ],
        }

    async def test_query_analysis(self, query: str, language: str = "fr") -> Dict:
        """Méthode de test pour analyser une requête en détail"""
        is_in_domain, score, details = await self._calculate_ood_score_async(
            query, None, language
        )

        return {
            "original_query": query,
            "language": language,
            "final_score": score,
            "is_in_domain": is_in_domain,
            "decision": "ACCEPTED" if is_in_domain else "REJECTED",
            "details": details,
        }

    def __del__(self):
        """Nettoyage des ressources - VERSION SIMPLIFIEE"""
        try:
            # Nettoyage basique du cache
            if hasattr(self, "translation_cache"):
                self.translation_cache.clear()
        except Exception:
            pass


# CORRECTION 7: Classe pour compatibilité descendante avec fixes
class EnhancedOODDetector(MultilingualOODDetector):
    """Alias pour compatibilité avec le code existant - VERSION CORRIGÉE"""

    def __init__(self, blocked_terms_path: str = None, openai_client=None):
        super().__init__(blocked_terms_path, openai_client)

    def calculate_ood_score(
        self, query: str, intent_result=None
    ) -> Tuple[bool, float, Dict[str, float]]:
        """Méthode synchrone pour compatibilité - CORRIGÉE"""
        # CORRECTION: Éviter complètement les problèmes d'event loop
        return self._calculate_ood_score_sync(query, intent_result, "fr")


# Factory functions - CORRECTION DES PARAMÈTRES
def create_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> EnhancedOODDetector:
    """Crée une instance du détecteur OOD avec compatibilité - PARAMÈTRES CORRIGÉS"""
    return EnhancedOODDetector(blocked_terms_path, openai_client)


def create_multilingual_ood_detector(
    blocked_terms_path: str = None, openai_client=None
) -> MultilingualOODDetector:
    """Crée une instance du détecteur OOD multilingue complet"""
    return MultilingualOODDetector(blocked_terms_path, openai_client)
