# app/api/v1/pipeline/clarification_manager.py
from __future__ import annotations

import logging
from typing import Iterable, List, Dict, Optional

logger = logging.getLogger(__name__)

CRITICAL_FIELDS = {"race", "sexe"}

class ClarificationManager:
    """Génère des questions de clarification courtes et actionnables."""

    def __init__(self, max_questions_per_round: int = 3) -> None:
        self.max_questions_per_round = max_questions_per_round
        self._default_questions: Dict[str, str] = {
            "race": "Quelle est la race/génétique (Ross, Cobb, Hubbard, etc.) ?",
            "sexe": "Quel est le sexe du lot (mâles, femelles ou mixte) ?",
            "age_jours": "Quel est l’âge exact en jours ?",
            "type_aliment": "Starter, grower ou finisher ?",
            "pays": "Dans quel pays (ou label) s’applique la question ?",
        }
        # Nouvelles formulations par intention (facultatif)
        self._by_intent: Dict[str, Dict[str, str]] = {
            "weight": {"age": "À quel âge (en jours) souhaites-tu la cible ?"},
            "fcr": {"age": "À quel âge (en jours) évalues-tu le FCR ?"},
            "water_intake": {"age": "Âge exact du lot (jours) ?"},
            "nutrition_targets": {"type_aliment": "Starter, grower ou finisher ?"},
            "compliance": {"pays": "Quel pays/label (ex. Label Rouge France) ?"},
        }

    def generate(
        self,
        missing_fields: Iterable[str],
        round_number: int = 1,
        language: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> List[str]:
        fields = self._normalize_fields(missing_fields)
        if not fields:
            return []
        prioritized = self._prioritize(fields, CRITICAL_FIELDS)
        questions: List[str] = []
        for f in prioritized:
            q = self._question_for_field(f, language=language, intent=intent)
            if q and q not in questions:
                questions.append(q)
            if len(questions) >= self.max_questions_per_round:
                break
        if not questions:
            questions = ["Pouvez-vous préciser quelques détails supplémentaires ?"]
        logger.debug("Clarification Qs (round=%s): %s", round_number, questions)
        return questions

    # ---------------- INTERNALS ---------------- #
    def _normalize_fields(self, missing_fields: Iterable[str]) -> List[str]:
        seen = set(); out: List[str] = []
        for f in (missing_fields or []):
            if not f: continue
            key = str(f).strip().lower()
            if key and key not in seen:
                seen.add(key); out.append(key)
        return out

    def _prioritize(self, fields: List[str], critical: set) -> List[str]:
        crit = [f for f in fields if f in critical]
        others = [f for f in fields if f not in critical]
        return crit + others

    def _question_for_field(self, field: str, language: Optional[str] = None, intent: Optional[str] = None) -> Optional[str]:
        # intent-specific first
        if intent and intent in self._by_intent and field in self._by_intent[intent]:
            return self._by_intent[intent][field]
        # default catalogue
        if field in self._default_questions:
            return self._default_questions[field]
        if field in {"species", "production_type", "type_production"}:
            return "S’agit‑il de poulets de chair, pondeuses, reproducteurs, etc.?"
        if field in {"poids", "poids_cible"}:
            return "Quel est le poids cible souhaité (g) ?"
        if field in {"alimentation", "feed"}:
            return "Quel aliment est donné actuellement (type/protéine/énergie) ?"
        return f"Pouvez‑vous préciser « {field} » ?"