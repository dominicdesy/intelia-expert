# app/api/v1/pipeline/clarification_manager.py
from __future__ import annotations

import logging
from typing import Iterable, List, Dict, Optional

logger = logging.getLogger(__name__)

# Champs dont la clarification impacte fortement la précision
CRITICAL_FIELDS = {"race", "sexe"}

class ClarificationManager:
    """
    Génère des questions de clarification courtes et actionnables.
    ✅ Compatible avec l'API existante (méthode generate()).
    """

    def __init__(self, max_questions_per_round: int = 3) -> None:
        # -- ORIGINAL: garde le comportement par défaut (3 questions)
        self.max_questions_per_round = max_questions_per_round

        # -- ORIGINAL: dictionnaire de questions génériques (peut déjà exister chez toi)
        # On l’enrichit/normalise doucement, sans casser les clés existantes.
        self._default_questions: Dict[str, str] = {
            # 💡 NOUVEAU: wording robuste pour race/sexe
            "race": "Quelle est la race/génétique (Ross, Cobb, Hubbard, etc.) ?",
            "sexe": "Quel est le sexe du lot (mâles, femelles ou mixte) ?",

            # -- EXEMPLES génériques (laisse ce bloc tel quel si tu avais déjà d’autres clés)
            "age_jours": "Quel est l’âge exact en jours ?",
            "poids_actuel": "Quel est le poids moyen actuel (g) ?",
            "objectif": "Quel est l’objectif (diagnostic, référence, action immédiate) ?",
            "effectif": "Quel est l’effectif du lot (nombre d’animaux) ?",
            "genetique": "Quelle génétique utilisez-vous (Ross, Cobb, etc.) ?",
            "batiment": "S’agit‑il d’un bâtiment standard, tunnel ou aviary ?",
        }

    # ------------------------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------------------------
    def generate(
        self,
        missing_fields: Iterable[str],
        round_number: int = 1,
        language: Optional[str] = None,
    ) -> List[str]:
        """
        Retourne une liste de questions concises.
        - Priorise 'race' et 'sexe'
        - Déduplique
        - Limite à max_questions_per_round
        - Reste compatible avec l’implémentation antérieure
        """
        fields = self._normalize_fields(missing_fields)
        if not fields:
            return []

        # 1) Prioriser les champs critiques (race/sexe en tête)
        prioritized = self._prioritize(fields, CRITICAL_FIELDS)

        questions: List[str] = []
        for f in prioritized:
            q = self._question_for_field(f, language=language)
            if q and q not in questions:
                questions.append(q)
            if len(questions) >= self.max_questions_per_round:
                break

        # -- ORIGINAL: fallback si rien n’a été généré (très rare)
        if not questions:
            questions = ["Pouvez-vous préciser quelques détails supplémentaires ?"]

        logger.debug("Clarification Qs (round=%s): %s", round_number, questions)
        return questions

    # ------------------------------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------------------------------
    def _normalize_fields(self, missing_fields: Iterable[str]) -> List[str]:
        # -- ORIGINAL: nettoyage doux + déduplication
        seen = set()
        out: List[str] = []
        for f in (missing_fields or []):
            if not f:
                continue
            key = str(f).strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(key)
        return out

    def _prioritize(self, fields: List[str], critical: set) -> List[str]:
        # -- ORIGINAL: on garde l’ordre d’entrée, mais on remonte les critiques
        crit = [f for f in fields if f in critical]
        others = [f for f in fields if f not in critical]
        return crit + others

    def _question_for_field(self, field: str, language: Optional[str] = None) -> Optional[str]:
        """
        Renvoie le libellé de question pour un champ donné.
        - Utilise d'abord la table par défaut
        - Sinon, fabrique une question simple et sûre
        """
        # ✅ Wording robuste pour race/sexe (déjà posé dans _default_questions)
        if field in self._default_questions:
            return self._default_questions[field]

        # -- ORIGINAL: règles simples pour quelques alias fréquents
        if field in {"species", "production_type", "type_production"}:
            return "S’agit‑il de poulets de chair, pondeuses, reproducteurs, etc. ?"
        if field in {"poids", "poids_cible"}:
            return "Quel est le poids cible souhaité (g) ?"
        if field in {"alimentation", "feed"}:
            return "Quel aliment est donné actuellement (type/protéine/énergie) ?"

        # -- ORIGINAL: fallback générique
        return f"Pouvez‑vous préciser « {field} » ?"
