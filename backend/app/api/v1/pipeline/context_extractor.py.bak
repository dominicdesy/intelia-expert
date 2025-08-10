# app/api/v1/pipeline/context_extractor.py
from __future__ import annotations

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any

from ..utils.entity_normalizer import EntityNormalizer
from ..utils.validation_pipeline import validate_and_score
from ..utils.openai_utils import safe_chat_completion

logger = logging.getLogger(__name__)

class ContextExtractor:
    """
    Extraction universelle des 'slots' depuis la question.
    - GPT (optionnel) + regex patterns configurables
    - Normalisation forte (species/line/sex/age_days/phase/equipment/climate/label/jurisdiction…)
    - Résilience (fallback regex) et scoring via validate_and_score
    """

    def __init__(self, use_gpt: bool = True, patterns_config_path: str | None = None) -> None:
        self.normalizer = EntityNormalizer()
        self.use_gpt = use_gpt
        self.patterns = self._load_patterns(patterns_config_path)
        self.gpt_fields = self._gpt_fields()

    # ---------------- Configuration ---------------- #
    def _gpt_fields(self) -> List[str]:
        return [
            # universels
            "species", "production_type", "line", "breed", "race", "sex", "sexe",
            "age_days", "age_jours", "age_phase", "phase",
            "equipment", "type_mangeoire", "type_abreuvoir",
            "objective", "user_role",
            "jurisdiction", "label",

            # environnement
            "temperature", "ambient_c", "humidity", "deltaT_C", "temp_outside",

            # dimensionnement / comptages
            "effectif", "flock_size",

            # nutrition
            "type_aliment", "np", "dp", "lysine", "kcal_kg",

            # KPI/coûts
            "fcr", "avg_weight_kg", "poids_moyen_g", "livability_pct", "prix_aliment_tonne_eur",

            # diagnostic
            "issue", "symptomes",
        ]

    def _patterns_default(self) -> Dict[str, str]:
        return {
            # espèces & lignées
            "species": r"\b(broiler|poulet\s+de\s+chair|layer|pondeuse|breeder|reproducteur)\b",
            "line": r"\b(ross\s*30[8|5|7]|cobb\s*500|cobb\s*700|hubbard\s*(?:ja|flex|classic)?|isa\s*brown|lohmann|hy-?line|arbor\s*acres)\b",
            "breed": r"\b(ross\s*30[8|5|7]|cobb\s*500|cobb\s*700|hubbard\s*(?:ja|flex|classic)?|isa\s*brown|lohmann|hy-?line|arbor\s*acres)\b",
            "race": r"\b(ross\s*30[8|5|7]|cobb\s*500|cobb\s*700|hubbard\s*(?:ja|flex|classic)?|isa\s*brown|lohmann|hy-?line|arbor\s*acres)\b",

            # sexe
            "sex": r"\b(male|mâle|males|mâles|female|femelle|femelles|mixed|mixte|pullets?|cockerels?)\b",
            "sexe": r"\b(male|mâle|males|mâles|female|femelle|femelles|mixed|mixte|pullets?|cockerels?)\b",

            # âge (jours)
            "age_days": r"\b(?:(?:j|jour|jours|day|d)\s*:?|)\s*(\d{1,3})\s*(?:j|jours|d|day)?\b|\b(\d{1,2})\s*semaines?\b",
            "age_phase": r"\b(day-?old|starter|pre-?starter|grower|finisher|ponte|démarrage|élevage)\b",
            "phase": r"\b(starter|pre-?starter|grower|finisher|ponte|démarrage|élevage)\b",

            # équipements
            "equipment": r"\b(nipple|abreuvoir|cloche|mangeoire|assiette|pan|cha[iî]ne|extracteur|tunnel|ventilateur)\b",
            "type_mangeoire": r"\b(assiette|pan|cha[iî]ne)\b",
            "type_abreuvoir": r"\b(nipple|cloche)\b",

            # environnement
            "ambient_c": r"(-?\d{1,2})\s*°?\s*c",
            "deltaT_C": r"(?:delta|Δt|delta\s*t|écart)\s*[:=]?\s*(-?\d{1,2})\s*°?\s*c",
            "temp_outside": r"(?:ext[ée]rieur|outside|dehors)\s*[:=]?\s*(-?\d{1,2})\s*°?\s*c",
            "humidity": r"(\d{1,3})\s*%",

            # dimensionnement
            "effectif": r"\b(?:(?:lot|troupeau|flock|effectif)\s*[:=]?\s*)?(\d{3,7})\b",

            # nutrition
            "type_aliment": r"\b(starter|pre-?starter|grower|finisher|aliment\s+de\s+démarrage|croissance|finition)\b",

            # KPI
            "fcr": r"\bfcr\s*[:=]?\s*(\d\.\d{2})\b",
            "poids_moyen_g": r"(\d{2,4})\s*g\b",
            "avg_weight_kg": r"(\d(?:\.\d{1,3})?)\s*kg\b",
            "livability_pct": r"(\d{2,3})\s*%\b",
            "prix_aliment_tonne_eur": r"(\d{2,4})\s*€\s*/\s*t",

            # conformité
            "jurisdiction": r"\b(france|ue|eu|es|it|ma|tn|qc|ca)\b",
            "label": r"\b(label\s+rouge|bio|plein\s+air|free[-\s]?range)\b",
        }

    def _load_patterns(self, path: str | None) -> Dict[str, str]:
        file_path = path or os.getenv("EXTRACTION_PATTERNS_PATH") or os.path.join(os.path.dirname(__file__), "extraction_patterns.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                pats = cfg.get("patterns") or {}
                if pats:
                    logger.info("✅ Patterns chargés depuis: %s", file_path)
                    return pats
            except Exception as e:
                logger.warning("⚠️ Erreur chargement patterns (%s): %s", file_path, e)
        logger.info("🔄 Utilisation des patterns par défaut")
        return self._patterns_default()

    # ---------------- Public API ---------------- #
    def extract(self, question: str) -> Tuple[Dict[str, Any], float, List[str]]:
        if not question or not question.strip():
            return {}, 0.0, []

        raw: Dict[str, Any] = {}

        if self.use_gpt:
            raw = self._extract_gpt(question)
            if len(raw) < 2:
                raw |= self._extract_regex(question)
        else:
            raw = self._extract_regex(question)

        norm = self._normalize(raw)
        score, missing = validate_and_score(norm, question)
        return norm, float(score), list(missing)

    # ---------------- Internals ---------------- #
    def _extract_gpt(self, question: str) -> Dict[str, Any]:
        fields = ", ".join(self.gpt_fields)
        prompt = (
            "Assistant avicole expert. Extrait en JSON les champs suivants si présents: "
            f"{fields}. Règles: "
            "1) 'age_days' en jours (convertir semaines), 2) 'sex' ∈ {male,female,mixed}, "
            "3) 'species' ∈ {broiler,layer,breeder} si possible, 4) pas de texte hors JSON.\n\n"
            f"Question: {question}"
        )
        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
            )
            content = (resp.choices[0].message.content or "").strip()
            return self._parse_json(content)
        except Exception as e:
            logger.debug("GPT extraction error: %s", e)
            return {}

    def _parse_json(self, s: str) -> Dict[str, Any]:
        try:
            t = s.strip()
            if t.startswith("```json"):
                t = t[7:]
            if t.startswith("```"):
                t = t[3:]
            if t.endswith("```"):
                t = t[:-3]
            data = json.loads(t.strip())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _extract_regex(self, question: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        text = question or ""
        for k, rx in self.patterns.items():
            try:
                m = re.findall(rx, text, re.IGNORECASE)
                if not m:
                    continue
                # choisir premier match non vide
                val = m[0]
                if isinstance(val, tuple):
                    val = next((x for x in val if x), "")
                if val:
                    out[k] = val
            except re.error as e:
                logger.warning("Regex error for %s: %s", k, e)
        return out

    def _normalize(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        c = dict(ctx or {})

        # map race/breed/line
        line = (c.get("line") or c.get("breed") or c.get("race") or "").lower().strip()
        if line:
            c["line"] = line
            c.setdefault("breed", line)
            c.setdefault("race", line)

        # species
        sp = (c.get("species") or c.get("production_type") or "").lower()
        if not sp:
            if any(x in line for x in ["ross", "cobb", "hubbard"]):
                sp = "broiler"
            elif any(x in line for x in ["lohmann", "hy-line", "isa"]):
                sp = "layer"
        if sp in ["poulet de chair", "broilers", "broiler"]:
            sp = "broiler"
        elif sp in ["layer", "pondeuse", "poule pondeuse"]:
            sp = "layer"
        elif sp in ["breeder", "reproducteur"]:
            sp = "breeder"
        if sp:
            c["species"] = sp

        # sex
        sex = (c.get("sex") or c.get("sexe") or "").lower()
        if sex:
            if any(w in sex for w in ["male", "mâle", "coq", "cockerel"]):
                sex = "male"
            elif any(w in sex for w in ["female", "femelle", "poule", "hen"]):
                sex = "female"
            elif any(w in sex for w in ["mix", "mixed", "mixte"]):
                sex = "mixed"
            c["sex"] = sex
            c["sexe"] = sex

        # age_days from patterns (can be weeks)
        age = c.get("age_days") or c.get("age_jours") or ""
        if isinstance(age, str) and age:
            wk = re.match(r"(\d{1,2})\s*semaines?", age, re.I)
            if wk:
                age = int(wk.group(1)) * 7
            else:
                try:
                    age = int(re.findall(r"\d{1,3}", age)[0])
                except Exception:
                    age = None
        if isinstance(age, (int, float)) and age > 0:
            c["age_days"] = int(age)
            c["age_jours"] = int(age)

        # phase
        phase = (c.get("phase") or c.get("age_phase") or "").lower()
        if phase:
            for k, canon in [("pre", "pre-starter"), ("starter", "starter"), ("grower", "grower"), ("finisher", "finisher"),
                             ("ponte", "lay"), ("démarrage", "starter"), ("élevage", "rearing")]:
                if k in phase:
                    phase = canon
                    break
            c["phase"] = phase

        # numeric coercions
        for k in ["ambient_c", "deltaT_C", "temp_outside", "fcr", "avg_weight_kg", "livability_pct",
                  "prix_aliment_tonne_eur"]:
            v = c.get(k)
            if isinstance(v, str):
                try:
                    c[k] = float(v.replace(",", "."))
                except Exception:
                    pass
        for k in ["effectif", "flock_size", "poids_moyen_g"]:
            v = c.get(k)
            if isinstance(v, str):
                try:
                    c[k] = int(re.findall(r"\d+", v)[0])
                except Exception:
                    pass

        # final normalization hook
        c = self.normalizer.normalize(c)
        return c
