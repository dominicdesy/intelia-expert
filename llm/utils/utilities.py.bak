# -*- coding: utf-8 -*-
"""
utilities.py - Fonctions utilitaires unifiées COMPLÈTES
Version modulaire avec toutes les fonctions nécessaires - CORRIGÉE
"""

import os
import re
import time
import json
import logging
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Imports modulaires
from config.config import (
    LANG_DETECTION_MIN_LENGTH,
    FRENCH_HINTS,
    ENGLISH_HINTS,
    FRENCH_CHARS,
)

# CORRECTION: Éviter l'import circulaire - importer seulement si nécessaire
try:
    from utils.imports_and_dependencies import UNIDECODE_AVAILABLE

    if UNIDECODE_AVAILABLE:
        from unidecode import unidecode
except ImportError:
    # Fallback si imports_and_dependencies n'est pas encore disponible
    UNIDECODE_AVAILABLE = False
    try:
        from unidecode import unidecode

        UNIDECODE_AVAILABLE = True
    except ImportError:
        pass

logger = logging.getLogger(__name__)

# ============================================================================
# CLASSES DE DONNÉES
# ============================================================================


@dataclass
class ValidationReport:
    """Rapport de validation détaillé"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, Any]
    recommendations: List[str]


@dataclass
class ProcessingResult:
    """Résultat de traitement d'une requête"""

    success: bool
    result: Optional[Any] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None


# ============================================================================
# COLLECTEUR DE MÉTRIQUES (Version complète)
# ============================================================================


class MetricsCollector:
    """Collecteur de métriques enrichi avec statistiques intent et cache sémantique"""

    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)
        self.intent_stats = defaultdict(int)
        self.semantic_cache_stats = defaultdict(int)
        self.ood_stats = defaultdict(int)
        self.api_corrections = defaultdict(int)

    def inc(self, key: str, n: int = 1):
        self.counters[key] += n

    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100:
            self.last_100_lat = self.last_100_lat[-100:]

    def cache_hit(self, cache_type: str):
        self.cache_stats[f"{cache_type}_hits"] += 1

    def cache_miss(self, cache_type: str):
        self.cache_stats[f"{cache_type}_misses"] += 1

    def intent_detected(self, intent_type: str, confidence: float):
        self.intent_stats[f"intent_{intent_type}"] += 1
        self.intent_stats["total_intents"] += 1
        self.intent_stats["avg_confidence"] = (
            self.intent_stats.get("avg_confidence", 0.0)
            * (self.intent_stats["total_intents"] - 1)
            + confidence
        ) / self.intent_stats["total_intents"]

    def semantic_cache_hit(self, cache_type: str):
        self.semantic_cache_stats[f"semantic_{cache_type}_hits"] += 1

    def semantic_fallback_used(self):
        self.semantic_cache_stats["fallback_hits"] += 1

    def ood_filtered(self, score: float, reason: str):
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_total"] += 1
        self.ood_stats["avg_ood_score"] = (
            self.ood_stats.get("avg_ood_score", 0.0) * (self.ood_stats["ood_total"] - 1)
            + score
        ) / self.ood_stats["ood_total"]

    def api_correction_applied(self, correction_type: str):
        self.api_corrections[correction_type] += 1

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (
            sorted(self.last_100_lat)[int(0.95 * len(self.last_100_lat)) - 1]
            if len(self.last_100_lat) >= 20
            else p50
        )
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "intent_stats": dict(self.intent_stats),
            "semantic_cache_stats": dict(self.semantic_cache_stats),
            "ood_stats": dict(self.ood_stats),
            "api_corrections": dict(self.api_corrections),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat),
        }

    def as_json(self) -> dict:
        """Export JSON des métriques pour l'app"""
        return {
            "cache": self.cache_stats,
            "ood": self.ood_stats,
            "guardrails": self.api_corrections,
        }


# Instance globale - DÉFINIE AVANT TOUTE AUTRE UTILISATION
METRICS = MetricsCollector()

# ============================================================================
# NOUVELLES FONCTIONS UTILITAIRES (depuis main.py)
# ============================================================================


def safe_serialize_for_json(obj: Any) -> Any:
    """Convertit récursivement les objets en types JSON-safe"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {k: safe_serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return safe_serialize_for_json(obj.__dict__)
    else:
        return str(obj)


def safe_get_attribute(obj: Any, attr: str, default: Any = None) -> Any:
    """Récupération sécurisée d'attributs avec validation de type"""
    try:
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(attr, default)
        elif hasattr(obj, attr):
            return getattr(obj, attr, default)
        else:
            return default
    except Exception as e:
        logger.debug(f"Erreur récupération attribut {attr}: {e}")
        return default


def safe_dict_get(obj: Any, key: str, default: Any = None) -> Any:
    """Version sécurisée de dict.get() qui évite les erreurs sur les strings"""
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        else:
            logger.debug(
                f"Tentative d'appel .get() sur type {type(obj)}: {str(obj)[:100]}"
            )
            return default
    except Exception as e:
        logger.debug(f"Erreur safe_dict_get pour {key}: {e}")
        return default


def sse_event(obj: Dict[str, Any]) -> bytes:
    """Formatage SSE avec gestion d'erreurs robuste"""
    try:
        safe_obj = safe_serialize_for_json(obj)
        data = json.dumps(safe_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")
    except Exception as e:
        logger.error(f"Erreur formatage SSE: {e}")
        error_obj = {"type": "error", "message": "Erreur formatage données"}
        data = json.dumps(error_obj, ensure_ascii=False)
        return f"data: {data}\n\n".encode("utf-8")


def smart_chunk_text(text: str, max_chunk_size: int = None) -> list:
    """Découpe intelligente du texte avec validation"""
    if not isinstance(text, str):
        return []

    max_chunk_size = max_chunk_size or int(os.getenv("STREAM_CHUNK_LEN", "400"))
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []

    try:
        chunks = []
        remaining_text = text

        while remaining_text:
            if len(remaining_text) <= max_chunk_size:
                chunks.append(remaining_text)
                break

            # Recherche de points de coupure optimaux
            cut_point = max_chunk_size

            # Préférer les points après ponctuation
            for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
                if i < len(remaining_text) and remaining_text[i] in ".!?:":
                    cut_point = i + 1
                    break

            # Sinon, couper sur un espace
            if cut_point == max_chunk_size:
                for i in range(max_chunk_size, max(max_chunk_size // 2, 0), -1):
                    if i < len(remaining_text) and remaining_text[i] == " ":
                        cut_point = i
                        break

            chunks.append(remaining_text[:cut_point])
            remaining_text = remaining_text[cut_point:].lstrip()

        return chunks

    except Exception as e:
        logger.error(f"Erreur découpe texte: {e}")
        return [text[:max_chunk_size]] if text else []


def get_out_of_domain_message(lang: Optional[str] = None) -> str:
    """Messages out of domain multilingue"""
    OUT_OF_DOMAIN_MESSAGES = {
        "fr": "Désolé, cette question sort du domaine avicole. Pose-moi une question sur l'aviculture, l'élevage de volailles, la nutrition, la santé des oiseaux, ou les performances.",
        "en": "Sorry, this question is outside the poultry domain. Ask me about poultry farming, bird nutrition, health, or performance.",
        "es": "Lo siento, esta pregunta está fuera del dominio avícola. Pregúntame sobre avicultura, nutrición, salud o rendimiento de aves.",
        "default": "Questions outside poultry domain not supported. Ask about poultry farming, nutrition, health, or performance.",
    }

    code = (lang or "").lower()
    msg = OUT_OF_DOMAIN_MESSAGES.get(code)
    if msg:
        return msg

    short = code.split("-")[0]
    return OUT_OF_DOMAIN_MESSAGES.get(
        short,
        OUT_OF_DOMAIN_MESSAGES.get(
            "default", "Questions outside domain not supported."
        ),
    )


def get_aviculture_response(message: str, language: str = "fr") -> str:
    """Génère une réponse aviculture basique si le RAG échoue"""

    message_lower = message.lower()

    # Réponses par sujet aviculture
    if any(term in message_lower for term in ["fcr", "conversion", "indice"]):
        if language == "fr":
            return """L'indice de conversion alimentaire (FCR) optimal varie selon l'âge et la souche :

- **Poulets de chair Ross 308** :
  - 0-21 jours : FCR cible 1.2-1.3
  - 22-35 jours : FCR cible 1.4-1.6  
  - 36-42 jours : FCR cible 1.7-1.9

- **Facteurs influençant le FCR** :
  - Qualité de l'aliment et formulation
  - Température et ventilation du bâtiment
  - Densité d'élevage
  - Santé du troupeau
  - Gestion de l'abreuvement

Pour optimiser le FCR, surveillez la consommation quotidienne et ajustez la distribution selon les courbes de croissance standards."""
        else:
            return "Feed Conversion Ratio (FCR) varies by age and strain. For Ross 308 broilers: 0-21 days FCR 1.2-1.3, 22-35 days FCR 1.4-1.6, 36-42 days FCR 1.7-1.9."

    elif any(
        term in message_lower for term in ["poids", "weight", "croissance", "growth"]
    ):
        if language == "fr":
            return """**Courbes de poids standard poulets de chair :**

- **Ross 308 (mélange)** :
  - 7 jours : 180-200g
  - 14 jours : 420-450g
  - 21 jours : 750-800g
  - 28 jours : 1.200-1.300g
  - 35 jours : 1.800-1.950g
  - 42 jours : 2.400-2.600g

- **Facteurs de croissance** :
  - Nutrition adaptée par phase
  - Température optimale (32°C démarrage, baisse progressive)
  - Densité max 30-33 kg/m²
  - Éclairage progressif
  - Prophylaxie sanitaire

Surveillez l'uniformité du lot (CV < 10%) et ajustez l'alimentation si écart aux standards."""
        else:
            return "Standard broiler weight curves: Ross 308 - 7d: 180-200g, 14d: 420-450g, 21d: 750-800g, 28d: 1200-1300g, 35d: 1800-1950g, 42d: 2400-2600g."

    elif any(
        term in message_lower
        for term in ["température", "temperature", "ventilation", "climat"]
    ):
        if language == "fr":
            return """**Programme température poulets de chair :**

- **Démarrage (0-7 jours)** : 32-34°C
- **Croissance (8-21 jours)** : Réduction 2-3°C/semaine
- **Finition (22-42 jours)** : 18-22°C

- **Ventilation** :
  - Minimum : 0.5 m³/h/kg vif
  - Maximum : 3-4 m³/h/kg vif  
  - Vitesse air max : 2.5 m/s

- **Hygrométrie** : 60-70%

**Points clés** :
- Éviter les chocs thermiques
- Ventilation progressive selon âge
- Surveillance des zones froides/chaudes
- Ajustement selon saison"""
        else:
            return "Broiler temperature program: Start 32-34°C (0-7 days), reduce 2-3°C/week, finish 18-22°C (22-42 days). Ventilation: 0.5-4 m³/h/kg, max air speed 2.5 m/s."

    elif any(
        term in message_lower for term in ["mortalité", "mortality", "santé", "health"]
    ):
        if language == "fr":
            return """**Objectifs mortalité poulets de chair :**

- **0-7 jours** : < 1%
- **8-21 jours** : < 0.5%
- **22-42 jours** : < 0.5%
- **Total cycle** : < 2-3%

**Principales causes mortalité :**
- Ascite, syndrome de mort subite
- Troubles locomoteurs
- Maladies infectieuses (colibacillose, etc.)
- Stress thermique ou nutritionnel

**Prévention :**
- Programme de démarrage rigoureux
- Vaccination adaptée
- Biosécurité stricte
- Surveillance quotidienne
- Nécropsies systématiques"""
        else:
            return "Broiler mortality targets: 0-7 days <1%, 8-21 days <0.5%, 22-42 days <0.5%, total <2-3%. Main causes: ascites, sudden death, locomotor issues, infections."

    elif any(
        term in message_lower
        for term in ["alimentation", "nutrition", "aliment", "feed"]
    ):
        if language == "fr":
            return """**Programme alimentaire 3 phases :**

**STARTER (0-10 jours) :**
- Protéines : 22-23%
- Énergie : 3000-3050 kcal/kg
- Présentation : miettes 2-3mm

**CROISSANCE (11-25 jours) :**
- Protéines : 20-21%
- Énergie : 3100-3150 kcal/kg  
- Présentation : granulés 3-4mm

**FINITION (26-42 jours) :**
- Protéines : 18-19%
- Énergie : 3150-3200 kcal/kg
- Présentation : granulés 4-5mm

**Distribution :** 
- Ad libitum avec restriction nocturne possible
- Transition progressive entre phases (2-3 jours)"""
        else:
            return "3-phase feeding program: Starter (0-10d) 22-23% protein, 3000-3050 kcal/kg; Grower (11-25d) 20-21% protein, 3100-3150 kcal/kg; Finisher (26-42d) 18-19% protein, 3150-3200 kcal/kg."

    else:
        # Réponse générale aviculture
        if language == "fr":
            return """Je suis spécialisé dans l'aviculture et l'élevage de poulets de chair. Je peux vous aider sur :

- **Performances** : FCR, poids, croissance, mortalité
- **Nutrition** : Programmes alimentaires, formulation
- **Environnement** : Température, ventilation, densité
- **Santé** : Prévention, vaccination, biosécurité
- **Technique** : Équipements, bâtiments, gestion

Posez-moi une question précise sur l'un de ces domaines !"""
        else:
            return "I specialize in poultry farming and broiler production. I can help with: Performance (FCR, weight, growth), Nutrition (feeding programs), Environment (temperature, ventilation), Health (prevention, vaccination), and Technical management. Ask me a specific question!"


# ============================================================================
# FONCTIONS UTILITAIRES CORE (existantes)
# ============================================================================


def get_all_metrics_json(
    metrics_instance: MetricsCollector, extra: dict = None
) -> dict:
    """Fonction d'export JSON consolidée des métriques avec données supplémentaires"""
    data = metrics_instance.as_json()
    if extra:
        data.update(extra)
    return data


def detect_language_enhanced(text: str, default: str = "fr") -> str:
    """Détection de langue optimisée pour requêtes courtes et techniques"""
    if len(text) < LANG_DETECTION_MIN_LENGTH:
        s = f" {text.lower()} "

        if any(ch in text.lower() for ch in FRENCH_CHARS):
            return "fr"

        fr = sum(1 for w in FRENCH_HINTS if w in s)
        en = sum(1 for w in ENGLISH_HINTS if w in s)

        # CORRECTION: Éviter multiples statements sur une ligne
        if fr > en + 1:
            return "fr"
        if en > fr + 1:
            return "en"

        if re.search(r"\d+\s*[gj]", text.lower()):
            return "fr"

        return default
    else:
        try:
            import langdetect

            detected = langdetect.detect(text)
            return detected if detected in ["fr", "en"] else default
        # CORRECTION: Remplacer bare except par Exception
        except Exception:
            s = f" {text.lower()} "
            fr = sum(1 for w in FRENCH_HINTS if w in s)
            en = sum(1 for w in ENGLISH_HINTS if w in s)
            if fr > en + 1:
                return "fr"
            if en > fr + 1:
                return "en"
            if any(ch in s for ch in FRENCH_CHARS):
                return "fr"
            return default


def build_where_filter(intent_result) -> Dict:
    """Construire where filter par entités"""
    if not intent_result or not hasattr(intent_result, "detected_entities"):
        return None

    entities = intent_result.detected_entities
    where_conditions = []

    if "line" in entities:
        where_conditions.append(
            {
                "path": ["geneticLine"],
                "operator": "Like",
                "valueText": f"*{entities['line']}*",
            }
        )

    if "species" in entities:
        where_conditions.append(
            {
                "path": ["species"],
                "operator": "Like",
                "valueText": f"*{entities['species']}*",
            }
        )

    if "phase" in entities:
        where_conditions.append(
            {
                "path": ["phase"],
                "operator": "Like",
                "valueText": f"*{entities['phase']}*",
            }
        )

    if "age_days" in entities:
        age_days = entities["age_days"]
        if isinstance(age_days, (int, float)):
            if age_days <= 7:
                age_band = "0-7j"
            elif age_days <= 21:
                age_band = "8-21j"
            elif age_days <= 35:
                age_band = "22-35j"
            else:
                age_band = "36j+"

            where_conditions.append(
                {"path": ["age_band"], "operator": "Equal", "valueText": age_band}
            )

    if not where_conditions:
        return None

    if len(where_conditions) == 1:
        return where_conditions[0]
    else:
        return {"operator": "And", "operands": where_conditions}


# ============================================================================
# DONNÉES DE TEST ET VALIDATION
# ============================================================================

COMPREHENSIVE_TEST_QUERIES = [
    "Quel est le poids cible à 21 jours pour du Ross 308?",
    "FCR optimal pour poulet de chair Cobb 500 à 35 jours",
    "Consommation d'eau à 28 jours pour élevage tunnel",
    "Température de démarrage pour poussins en tunnel",
    "Ventilation minimale à 14 jours Ross 308",
    "Humidité optimale phase starter",
    "Programme de vaccination pour reproducteur",
    "Protocole biosécurité couvoir",
    "Densité optimale en élevage au sol",
    "Mes poulets ont des signes respiratoires",
    "Mortalité élevée à 10 jours que faire",
    "Symptômes Newcastle chez reproducteurs",
    "Coût alimentaire par kg de poids vif produit",
    "Performance EPEF Ross 308 standard",
    "Marge bénéficiaire par sujet abattu",
    "Ross-308 35j FCR",
    "C-500 poids 42 jours",
    "Hubbard Flex vaccination",
    "ISA Brown ponte pic",
    "R308 démarrage température",
    "Météo demain",  # Hors domaine
    "Comment élever des chats",  # Hors domaine
    "Performance globale exploitation complète multi-bâtiments",  # Complexe
]

# ============================================================================
# FACTORY ET FONCTIONS DE VALIDATION
# ============================================================================


class IntentProcessorFactory:
    """Factory robuste pour créer des processeurs d'intentions"""

    @staticmethod
    def create_processor(
        intents_file_path: Optional[str] = None, validate_on_creation: bool = True
    ):
        # CORRECTION: Utiliser string pour le type hint au lieu de forward reference
        try:
            from processing.intent_processor import IntentProcessor
        except ImportError as e:
            raise RuntimeError(f"Module intent_processor non disponible: {e}")

        if intents_file_path is None:
            base_dir = Path(__file__).parent.resolve()
            intents_file_path = base_dir.parent / "config" / "intents.json"
            logger.info(f"Utilisation du chemin par défaut: {intents_file_path}")

        try:
            processor = IntentProcessor(str(intents_file_path))

            if validate_on_creation:
                validation_result = processor.validate_current_config()
                if not validation_result.is_valid:
                    raise ValueError(
                        f"Configuration invalide: {validation_result.errors}"
                    )

            stats = processor.get_processing_stats()
            health = stats.get("health_status", {})

            if health.get("status") == "critical":
                logger.error(
                    f"Processeur créé mais en état critique: {health.get('reason')}"
                )
                raise RuntimeError(
                    f"Processeur en état critique: {health.get('reason')}"
                )

            logger.info(
                f"IntentProcessor créé avec succès - Statut: {health.get('status', 'unknown')}"
            )
            return processor

        except Exception as e:
            logger.error(f"Erreur création IntentProcessor: {e}")
            raise RuntimeError(f"Impossible de créer IntentProcessor: {e}")


def process_query_with_intents(
    processor, query: str, explain_score: Optional[float] = None, timeout: float = 5.0
) -> ProcessingResult:
    start_time = time.time()

    if not processor:
        return ProcessingResult(
            success=False, error_message="Processeur non fourni", processing_time=0.0
        )

    if not query or not query.strip():
        return ProcessingResult(
            success=False,
            error_message="Requête vide ou invalide",
            processing_time=0.0,
        )

    try:
        result = processor.process_query(query.strip(), explain_score)
        processing_time = time.time() - start_time

        if not result:
            return ProcessingResult(
                success=False,
                error_message="Aucun résultat retourné par le processeur",
                processing_time=processing_time,
            )

        return ProcessingResult(
            success=True,
            result=result,
            processing_time=processing_time,
            metadata={
                "query_length": len(query),
                "entities_detected": len(result.detected_entities),
                "intent_type": (
                    result.intent_type.value
                    if hasattr(result.intent_type, "value")
                    else str(result.intent_type)
                ),
                "confidence_level": (
                    "high"
                    if result.confidence > 0.8
                    else "medium" if result.confidence > 0.5 else "low"
                ),
            },
        )

    except Exception as e:
        logger.error(f"Erreur traitement requête '{query[:50]}...': {e}")
        return ProcessingResult(
            success=False,
            error_message=f"Erreur de traitement: {str(e)}",
            processing_time=time.time() - start_time,
            metadata={"exception_type": type(e).__name__},
        )


def validate_intents_config(
    config_path: str, strict_mode: bool = True
) -> ValidationReport:
    """Valide rigoureusement un fichier de configuration intents.json"""
    errors = []
    warnings = []
    recommendations = []
    stats = {}

    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return ValidationReport(
                is_valid=False,
                errors=[f"Fichier non trouvé: {config_path}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez le chemin du fichier de configuration"],
            )

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return ValidationReport(
                is_valid=False,
                errors=[f"Erreur JSON: {e}"],
                warnings=[],
                stats={},
                recommendations=["Vérifiez la syntaxe JSON avec un validateur"],
            )

        # Validation basique
        required_sections = ["aliases", "intents", "universal_slots"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Section manquante: {section}")
            elif not isinstance(config[section], dict):
                errors.append(f"Section {section} doit être un dictionnaire")

        stats.update(
            {
                "file_size_bytes": config_file.stat().st_size,
                "validation_timestamp": time.time(),
                "strict_mode": strict_mode,
            }
        )

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            stats=stats,
            recommendations=recommendations,
        )

    except Exception as e:
        return ValidationReport(
            is_valid=False,
            errors=[f"Erreur validation inattendue: {e}"],
            warnings=[],
            stats={},
            recommendations=["Contactez le support technique"],
        )


# CORRECTION: Retirer le type hint problématique pour compatibilité
def create_intent_processor(intents_file_path: Optional[str] = None):
    """Factory principale pour créer un processeur d'intentions"""
    return IntentProcessorFactory.create_processor(
        intents_file_path, validate_on_creation=True
    )


# ============================================================================
# SETUP ET CONFIGURATION
# ============================================================================


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


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Métriques
    "METRICS",
    "MetricsCollector",
    "get_all_metrics_json",
    # Détection langue
    "detect_language_enhanced",
    # Weaviate
    "build_where_filter",
    # Intent processing
    "create_intent_processor",
    "process_query_with_intents",
    "validate_intents_config",
    "IntentProcessorFactory",
    # Classes de données
    "ValidationReport",
    "ProcessingResult",
    # Données de test
    "COMPREHENSIVE_TEST_QUERIES",
    # Nouvelles fonctions utilitaires
    "safe_serialize_for_json",
    "safe_get_attribute",
    "safe_dict_get",
    "sse_event",
    "smart_chunk_text",
    "get_out_of_domain_message",
    "get_aviculture_response",
    "setup_logging",
]
