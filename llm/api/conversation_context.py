# -*- coding: utf-8 -*-
"""
api/conversation_context.py - Gestionnaire de contexte conversationnel
Version 4.2.3 - DÉTECTION AMÉLIORÉE + GESTION AMBIGUÏTÉ + ABANDON
"""

import time
import re
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """
    Gestionnaire de contexte conversationnel pour clarifications
    VERSION 4.2.3 - DÉTECTION AMÉLIORÉE + AMBIGUÏTÉ + ABANDON
    """

    # NOUVEAUX PATTERNS D'AMBIGUÏTÉ
    AMBIGUOUS_PATTERNS = [
        r"je ne sais pas",
        r"pas sûr",
        r"peut-être",
        r"probablement",
        r"je pense",
        r"environ",
        r"à peu près",
        r"not sure",
        r"maybe",
        r"probably",
        r"i think",
        r"approximately",
    ]

    # NOUVEAUX PATTERNS D'ABANDON
    ABANDON_PATTERNS = [
        r"peu importe",
        r"laisse tomber",
        r"oublie",
        r"moyenne générale",
        r"sans précision",
        r"approximativement",
        r"never mind",
        r"forget it",
        r"skip",
        r"general average",
        r"no importa",
    ]

    def __init__(self, intents_config_path: str = None):
        self.pending_clarifications = {}
        self.clarification_patterns = self._load_clarification_patterns(
            intents_config_path
        )

    def _load_clarification_patterns(self, config_path: str = None) -> Dict:
        """Charge les patterns de clarification depuis intents.json"""

        if config_path is None:
            # Chemins par défaut
            possible_paths = [
                Path(__file__).parent.parent / "config" / "intents.json",
                Path(__file__).parent / "config" / "intents.json",
                Path.cwd() / "config" / "intents.json",
                Path.cwd() / "llm" / "config" / "intents.json",
            ]

            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break

        if not config_path or not Path(config_path).exists():
            logger.warning("intents.json non trouvé - utilisation patterns par défaut")
            return self._get_default_patterns()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Extraire les patterns pertinents
            patterns = {
                "age": self._extract_age_patterns(config),
                "breed": self._extract_breed_patterns(config),
                "sex": self._extract_sex_patterns(config),
                "metric": self._extract_metric_patterns(config),
            }

            logger.info(f"Patterns de clarification chargés depuis {config_path}")
            return patterns

        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return self._get_default_patterns()

    def _extract_age_patterns(self, config: Dict) -> Dict:
        """Extrait les patterns d'âge depuis intents.json"""
        return {"regex": r"\d+\s*(jour|day|j\b|d\b|semaine|week|sem)", "keywords": []}

    def _extract_breed_patterns(self, config: Dict) -> Dict:
        """
        Extrait les patterns de races depuis intents.json

        ✅ Version 2.0: Utilise UNIQUEMENT intents.json (pas de hardcodés)
        """
        breeds = []
        aliases = config.get("aliases", {}).get("line", {})

        # Extraire TOUS les aliases depuis intents.json
        for line, line_breeds in aliases.items():
            if isinstance(line_breeds, list):
                breeds.extend([b.lower() for b in line_breeds])

        # ✅ PAS de hardcodés - intents.json contient déjà tout !
        logger.info(
            f"✅ {len(set(breeds))} aliases de races chargés depuis intents.json"
        )

        return {"regex": None, "keywords": list(set(breeds))}

    def _extract_sex_patterns(self, config: Dict) -> Dict:
        """Extrait les patterns de sexe depuis intents.json"""
        sex_aliases = config.get("aliases", {}).get("sex", {})

        keywords = []
        for sex_type, variants in sex_aliases.items():
            if isinstance(variants, list):
                keywords.extend([v.lower() for v in variants])

        return {"regex": None, "keywords": keywords}

    def _extract_metric_patterns(self, config: Dict) -> Dict:
        """Extrait les patterns de métriques depuis intents.json"""
        metric_aliases = config.get("aliases", {}).get("metric", {})

        keywords = []
        for metric_type, variants in metric_aliases.items():
            if isinstance(variants, list):
                keywords.extend([v.lower() for v in variants])

        return {"regex": None, "keywords": keywords}

    def _get_default_patterns(self) -> Dict:
        """Patterns par défaut en cas d'échec de chargement"""
        return {
            "age": {"regex": r"\d+\s*(jour|day|j\b|d\b|semaine|week)", "keywords": []},
            "breed": {
                "regex": None,
                "keywords": ["ross", "cobb", "hubbard", "aviagen", "308", "500", "700"],
            },
            "sex": {
                "regex": None,
                "keywords": ["mâle", "femelle", "male", "female", "mixte", "mixed"],
            },
            "metric": {
                "regex": None,
                "keywords": [
                    "poids",
                    "weight",
                    "fcr",
                    "conversion",
                    "mortalité",
                    "gain",
                ],
            },
        }

    def mark_pending(
        self,
        tenant_id: str,
        original_query: str,
        missing_fields: List[str],
        suggestions: Dict,
        language: str,
    ):
        """Marque une conversation en attente de clarification"""
        self.pending_clarifications[tenant_id] = {
            "original_query": original_query,
            "missing_fields": missing_fields,
            "suggestions": suggestions,
            "language": language,
            "original_language": language,
            "timestamp": time.time(),
            "clarification_count": 0,
            "clarification_attempts": 0,
        }
        logger.info(
            f"Clarification en attente pour {tenant_id}: {missing_fields} (langue: {language})"
        )

    def get_pending(self, tenant_id: str) -> Optional[Dict]:
        """Récupère le contexte en attente"""
        return self.pending_clarifications.get(tenant_id)

    def clear_pending(self, tenant_id: str):
        """Efface le contexte en attente"""
        if tenant_id in self.pending_clarifications:
            del self.pending_clarifications[tenant_id]
            logger.info(f"Clarification résolue pour {tenant_id}")

    def update_accumulated_query(self, tenant_id: str, new_info: str):
        """
        Accumule les informations de clarification de manière intelligente

        ✅ Version 2.0:
        - Fusion sémantique au lieu de séparateur |
        - Extraction des entités pour construction cohérente
        - Maintien de la lisibilité de la requête
        """
        if tenant_id not in self.pending_clarifications:
            return

        context = self.pending_clarifications[tenant_id]
        original = context["original_query"]

        # Extraire entités de la réponse
        try:
            from llm.core.entity_extractor import EntityExtractor

            extractor = EntityExtractor()
            response_entities = extractor.extract(new_info)

            # Construire requête enrichie intelligemment
            merged = original

            if response_entities.breed and response_entities.has_explicit_breed:
                # "quel est le poids" + "Cobb 500" → "quel est le poids pour Cobb 500"
                merged = f"{original} pour {response_entities.breed}"
                logger.info(f"✅ Requête enrichie avec race: {merged}")

            elif response_entities.age_days and response_entities.has_explicit_age:
                # "quel est le poids" + "35 jours" → "quel est le poids à 35 jours"
                merged = f"{original} à {response_entities.age_days} jours"
                logger.info(f"✅ Requête enrichie avec âge: {merged}")

            elif response_entities.sex and response_entities.has_explicit_sex:
                # "quel est le poids" + "mâles" → "quel est le poids pour les mâles"
                sex_label = {"male": "les mâles", "female": "les femelles"}.get(
                    response_entities.sex, response_entities.sex
                )
                merged = f"{original} pour {sex_label}"
                logger.info(f"✅ Requête enrichie avec sexe: {merged}")

            else:
                # Fallback: ajout simple
                merged = f"{original} {new_info}"
                logger.debug(f"Fusion simple: {merged}")

            context["original_query"] = merged

        except Exception as e:
            # Fallback en cas d'erreur
            logger.warning(
                f"Erreur fusion intelligente: {e}, fallback séparateur simple"
            )
            context["original_query"] = f"{original} | {new_info}"

        context["clarification_count"] = context.get("clarification_count", 0) + 1
        context["timestamp"] = time.time()

        logger.info(
            f"Requête accumulée (tour {context['clarification_count']}): {context['original_query'][:100]}..."
        )

    def increment_clarification_attempt(self, tenant_id: str):
        """Incrémente le compteur de tentatives de clarification"""
        if tenant_id in self.pending_clarifications:
            context = self.pending_clarifications[tenant_id]
            context["clarification_attempts"] = (
                context.get("clarification_attempts", 0) + 1
            )
            logger.info(
                f"Tentative de clarification #{context['clarification_attempts']} pour {tenant_id}"
            )

    def is_clarification_response(self, message: str, pending_context: Dict) -> bool:
        """
        Détecte si le message est une réponse à une demande de clarification

        ✅ Version 2.0:
        - Utilise entity_extractor pour robustesse (Test 11)
        - Supporte TOUTES les races via breeds_registry (51 races)
        - Gère phrases complètes, pas seulement mots courts
        - Fallback sur patterns intents.json si extraction échoue
        """
        if not pending_context:
            return False

        missing = pending_context.get("missing_fields", [])
        msg = message.lower().strip()

        # ========================================
        # APPROCHE 1: Utiliser entity_extractor (PRIORITAIRE)
        # ========================================
        try:
            from llm.core.entity_extractor import EntityExtractor

            # Extraire les entités depuis le message
            extractor = EntityExtractor()
            extracted = extractor.extract(message)

            # Vérifier si une entité manquante a été fournie
            if any("breed" in f.lower() or "race" in f.lower() for f in missing):
                if extracted.breed and extracted.has_explicit_breed:
                    logger.info(
                        f"✅ Race détectée via entity_extractor: {extracted.breed}"
                    )
                    return True

            if any("age" in f.lower() for f in missing):
                if extracted.age_days and extracted.has_explicit_age:
                    logger.info(
                        f"✅ Âge détecté via entity_extractor: {extracted.age_days} jours"
                    )
                    return True

            if any("sex" in f.lower() or "sexe" in f.lower() for f in missing):
                if extracted.sex and extracted.has_explicit_sex:
                    logger.info(
                        f"✅ Sexe détecté via entity_extractor: {extracted.sex}"
                    )
                    return True

        except Exception as e:
            logger.warning(
                f"entity_extractor non disponible, fallback sur patterns: {e}"
            )

        # ========================================
        # APPROCHE 2: Patterns simples pour âge (FALLBACK)
        # ========================================
        if any("age" in field.lower() for field in missing):
            age_patterns = [
                r"^\s*(\d+)\s*$",  # "35"
                r"^\s*(\d+)\s*(?:jours?|days?|j|d)\s*$",  # "35 jours"
                r"^\s*à\s*(\d+)\s*(?:jours?|j)?\s*$",  # "à 35 jours"
                r"^\s*(\d+)\s*semaines?\s*$",  # "3 semaines"
                r"^\s*(\d+)\s*weeks?\s*$",  # "3 weeks"
            ]

            for pattern in age_patterns:
                if re.search(pattern, msg):
                    logger.info(f"✅ Âge détecté via patterns: {message}")
                    return True

        # ========================================
        # APPROCHE 3: Patterns depuis intents.json (FALLBACK)
        # ========================================
        for field in missing:
            normalized = field.replace("_days", "").replace("_type", "")

            if normalized not in self.clarification_patterns:
                continue

            pattern_config = self.clarification_patterns[normalized]

            # Vérifier regex
            if pattern_config.get("regex"):
                if re.search(pattern_config["regex"], msg):
                    logger.info(
                        f"✅ Champ détecté via regex intents.json: {normalized}"
                    )
                    return True

            # Vérifier keywords
            if pattern_config.get("keywords"):
                if any(kw in msg for kw in pattern_config["keywords"]):
                    logger.info(
                        f"✅ Champ détecté via keywords intents.json: {normalized}"
                    )
                    return True

        logger.debug(f"❌ Pas de réponse de clarification détectée: {message}")
        return False

    def detect_ambiguous_response(self, message: str) -> bool:
        """
        Détecte si la réponse est ambiguë/incertaine
        """
        msg_lower = message.lower()

        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, msg_lower):
                logger.info(f"Réponse ambiguë détectée: {message}")
                return True

        return False

    def detect_clarification_abandon(self, message: str) -> bool:
        """
        Détecte si l'utilisateur abandonne la clarification
        """
        msg_lower = message.lower()

        for pattern in self.ABANDON_PATTERNS:
            if re.search(pattern, msg_lower):
                logger.info(f"Abandon de clarification détecté: {message}")
                return True

        return False

    def generate_clarification_retry(
        self, original_message: str, missing_field: str, language: str = "fr"
    ) -> str:
        """
        Génère une demande de clarification plus précise
        après détection d'ambiguïté
        """
        retry_templates = {
            "fr": {
                "breed": "Pourriez-vous confirmer la race exacte parmi ces options ?\n• Ross 308\n• Cobb 500\n• Hubbard Classic\n• Autre (précisez)",
                "age": "Pourriez-vous confirmer l'âge exact en jours ? (exemple: 21, 35, 42)",
                "sex": "Pourriez-vous préciser le sexe ?\n• Mâle\n• Femelle\n• Mixte",
            },
            "en": {
                "breed": "Could you confirm the exact breed from these options?\n• Ross 308\n• Cobb 500\n• Hubbard Classic\n• Other (specify)",
                "age": "Could you confirm the exact age in days? (example: 21, 35, 42)",
                "sex": "Could you specify the sex?\n• Male\n• Female\n• Mixed",
            },
        }

        field_normalized = missing_field.replace("_days", "").replace("_type", "")
        templates = retry_templates.get(language, retry_templates["fr"])

        return templates.get(field_normalized, "Pourriez-vous être plus précis ?")


def generate_clarification_question(
    missing_fields: List[str], suggestions: Dict, language: str
) -> str:
    """Génère une question de clarification naturelle selon la langue"""

    clarification_templates = {
        "fr": {
            "breed": "Pour vous donner une réponse précise, pourriez-vous me dire quelle race/souche vous élevez ? (par exemple : Ross 308, Cobb 500, Hubbard)",
            "age_days": "À quel âge (en jours) souhaitez-vous connaître cette information ?",
            "sex": "Cette information concerne-t-elle des mâles, des femelles, ou un élevage mixte ?",
            "metric_type": "Quelle métrique spécifique vous intéresse ? (poids, FCR, mortalité, etc.)",
            "multiple": "Pour vous aider au mieux, j'ai besoin de quelques précisions :\n{details}",
        },
        "en": {
            "breed": "To give you an accurate answer, could you tell me which breed/strain you're raising? (e.g., Ross 308, Cobb 500, Hubbard)",
            "age_days": "At what age (in days) would you like this information?",
            "sex": "Is this information for males, females, or mixed flock?",
            "metric_type": "Which specific metric are you interested in? (weight, FCR, mortality, etc.)",
            "multiple": "To help you best, I need a few clarifications:\n{details}",
        },
    }

    templates = clarification_templates.get(language, clarification_templates["fr"])

    if len(missing_fields) == 1:
        field = missing_fields[0]
        question = templates.get(field, templates.get("breed"))

        if suggestions and field in suggestions:
            field_suggestions = suggestions[field]
            if field_suggestions:
                if language == "fr":
                    question += f"\n\nSuggestions : {', '.join(field_suggestions[:5])}"
                else:
                    question += f"\n\nSuggestions: {', '.join(field_suggestions[:5])}"

        return question

    else:
        details = []
        for field in missing_fields:
            field_template = templates.get(field, "")
            if field_template and field != "multiple":
                question_part = field_template.split("?")[0] + "?"
                details.append(f"- {question_part}")

        if details:
            return templates["multiple"].format(details="\n".join(details))
        else:
            return templates.get("breed", "Pouvez-vous préciser votre question ?")
