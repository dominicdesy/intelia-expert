# app/api/v1/pipeline/context_extractor.py - VERSION AMÉLIORÉE
from __future__ import annotations

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any, Optional

from ..utils.entity_normalizer import EntityNormalizer
from ..utils.validation_pipeline import validate_and_score
from ..utils.openai_utils import safe_chat_completion

logger = logging.getLogger(__name__)

class ContextExtractor:
    """
    Extraction universelle des 'slots' depuis la question - VERSION AMÉLIORÉE.
    - GPT avec prompt spécialisé aviculture + regex patterns étendus
    - Normalisation forte avec synonymes et validation croisée
    - Scoring de confiance et détection d'incohérences
    """

    def __init__(self, use_gpt: bool = True, patterns_config_path: str | None = None) -> None:
        self.normalizer = EntityNormalizer()
        self.use_gpt = use_gpt
        self.patterns = self._load_patterns(patterns_config_path)
        self.gpt_fields = self._gpt_fields()
        
        # NOUVEAU : Dictionnaire de synonymes étendus
        self.synonyms = {
            "species": {
                "poulet de chair": "broiler",
                "chair": "broiler",
                "broilers": "broiler",
                "pondeuse": "layer",
                "pondeuses": "layer",
                "poule pondeuse": "layer",
                "poules pondeuses": "layer",
                "reproducteur": "breeder",
                "reproducteurs": "breeder"
            },
            "sex": {
                "mâles": "male",
                "males": "male",
                "mâle": "male",
                "femelles": "female",
                "femelle": "female",
                "coqs": "male",
                "coq": "male",
                "poules": "female",
                "poule": "female",
                "mixte": "mixed",
                "mixtes": "mixed"
            },
            "phase": {
                "démarrage": "starter",
                "demarrage": "starter",
                "croissance": "grower",
                "finition": "finisher",
                "ponte": "laying",
                "pré-starter": "pre-starter",
                "pre starter": "pre-starter"
            },
            "line_aliases": {
                "ross trois cent huit": "Ross 308",
                "ross 3 0 8": "Ross 308",
                "cobb cinq cents": "Cobb 500",
                "cobb 5 0 0": "Cobb 500",
                "isa brown": "ISA Brown",
                "hy line": "Hy-Line",
                "hy-line": "Hy-Line"
            }
        }

    # ---------------- Configuration ---------------- #
    def _gpt_fields(self) -> List[str]:
        return [
            # UNIVERSELS - étendus
            "species", "production_type", "line", "breed", "race", "sex", "sexe",
            "age_days", "age_jours", "age_weeks", "age_phase", "phase",
            "equipment", "type_mangeoire", "type_abreuvoir",
            "objective", "user_role", "problem_type", "symptoms",
            "jurisdiction", "label",

            # ENVIRONNEMENT - étendus
            "temperature", "ambient_c", "humidity", "deltaT_C", "temp_outside",
            "lighting_hours", "light_intensity",

            # DIMENSIONNEMENT / COMPTAGES - étendus
            "effectif", "flock_size", "density_kg_m2", "floor_space_m2",

            # NUTRITION - étendus
            "type_aliment", "feed_type", "np", "dp", "lysine", "kcal_kg", "protein_pct",
            "calcium_pct", "phosphorus_pct",

            # KPI/COÛTS - étendus
            "fcr", "avg_weight_kg", "poids_moyen_g", "target_weight_g",
            "livability_pct", "mortality_pct", "production_rate_pct",
            "prix_aliment_tonne_eur", "feed_cost",

            # DIAGNOSTIC - nouveaux
            "issue", "symptomes", "problem_description", "duration",
            "affected_count", "timeline"
        ]

    def _patterns_default(self) -> Dict[str, str]:
        return {
            # ESPÈCES & LIGNÉES - patterns étendus
            "species": r"\b(broiler|poulet\s+de\s+chair|chair|layer|pondeuse|poule\s+pondeuse|breeder|reproducteur)\b",
            
            # LIGNÉES - patterns plus robustes avec variations
            "line": r"\b(ross\s*(?:308|500|708|trois\s*cent\s*huit)|cobb\s*(?:500|700|cinq\s*cents)|hubbard\s*(?:ja|flex|classic)?|isa\s*brown|lohmann\s*(?:brown|white)?|hy-?line\s*(?:brown|white)?|arbor\s*acres)\b",
            "breed": r"\b(ross\s*(?:308|500|708)|cobb\s*(?:500|700)|hubbard|isa\s*brown|lohmann|hy-?line)\b",
            "race": r"\b(ross\s*(?:308|500|708)|cobb\s*(?:500|700)|hubbard|isa\s*brown|lohmann|hy-?line)\b",

            # SEXE - patterns étendus
            "sex": r"\b(male|mâle|males|mâles|femelle|femelles|female|mixed|mixte|pullets?|cockerels?|coqs?|poules?)\b",
            "sexe": r"\b(male|mâle|males|mâles|femelle|femelles|female|mixed|mixte|pullets?|cockerels?|coqs?|poules?)\b",

            # ÂGE - patterns améliorés avec plus de variations
            "age_days": r"(?:(?:âge|age)\s+)?(?:de\s+)?(\d{1,3})\s*(?:j|jours?|d|days?)\b|(?:à\s+)?(\d{1,3})\s*(?:j|jours?)\b",
            "age_weeks": r"(?:(?:âge|age)\s+)?(?:de\s+)?(\d{1,2})\s*(?:sem|semaines?|week|weeks?)\b",
            "age_phase": r"\b(day-?old|jour|starter|pre-?starter|grower|finisher|ponte|démarrage|élevage|croissance|finition)\b",
            "phase": r"\b(starter|pre-?starter|grower|finisher|ponte|démarrage|élevage|croissance|finition)\b",

            # POIDS - patterns étendus
            "target_weight_g": r"(?:poids\s+(?:cible|target|optimal|visé))\s*[:=]?\s*(\d+)\s*g\b",
            "poids_moyen_g": r"(?:poids\s+(?:moyen|actuel|vif))?\s*[:=]?\s*(\d{2,4})\s*g\b",
            "avg_weight_kg": r"(?:poids\s+(?:moyen|vif))?\s*[:=]?\s*(\d(?:\.\d{1,3})?)\s*kg\b",

            # ÉQUIPEMENTS - patterns étendus
            "equipment": r"\b(nipple|abreuvoir|cloche|mangeoire|assiette|pan|cha[iî]ne|extracteur|tunnel|ventilateur|feeding|drinking)\b",
            "type_mangeoire": r"\b(assiette|pan|cha[iî]ne|feeding\s+system)\b",
            "type_abreuvoir": r"\b(nipple|cloche|bell|drinking\s+system)\b",

            # ENVIRONNEMENT - patterns étendus
            "ambient_c": r"(?:température|temp|t°)\s*[:=]?\s*(-?\d{1,2})\s*°?\s*c\b",
            "deltaT_C": r"(?:delta|Δt|delta\s*t|écart)\s*[:=]?\s*(-?\d{1,2})\s*°?\s*c\b",
            "temp_outside": r"(?:ext[ée]rieur|outside|dehors)\s*[:=]?\s*(-?\d{1,2})\s*°?\s*c\b",
            "humidity": r"(?:humidité|humidity)\s*[:=]?\s*(\d{1,3})\s*%",

            # PRODUCTION - patterns étendus
            "production_rate_pct": r"(?:ponte|production|laying)\s*[:=]?\s*(\d{1,3})\s*%",
            "mortality_pct": r"(?:mortalité|mortality)\s*[:=]?\s*(\d{1,3})\s*%",

            # DIMENSIONNEMENT - patterns étendus
            "effectif": r"(?:(?:lot|troupeau|flock|effectif)\s*[:=]?\s*)?(\d{3,7})\s*(?:oiseaux|birds|poulets|poules)?\b",
            "density_kg_m2": r"(?:densité|density)\s*[:=]?\s*(\d{1,3})\s*kg\s*/\s*m[²2]",

            # NUTRITION - patterns étendus
            "type_aliment": r"\b(starter|pre-?starter|grower|finisher|aliment\s+de\s+(?:démarrage|croissance|finition))\b",
            "protein_pct": r"(?:protéine|protein)\s*[:=]?\s*(\d{1,2}(?:\.\d)?)\s*%",
            "kcal_kg": r"(\d{4})\s*kcal\s*/\s*kg\b",

            # KPI - patterns étendus
            "fcr": r"\b(?:fcr|indice\s+de\s+consommation)\s*[:=]?\s*(\d\.\d{2})\b",
            "livability_pct": r"(?:survie|viabilité|livability)\s*[:=]?\s*(\d{2,3})\s*%\b",
            "prix_aliment_tonne_eur": r"(\d{2,4})\s*€\s*/\s*t(?:onne)?\b",

            # CONFORMITÉ - patterns étendus
            "jurisdiction": r"\b(france|français|ue|eu|europe|espagne|italie|maroc|tunisie|québec|canada)\b",
            "label": r"\b(label\s+rouge|bio|biologique|plein\s+air|free[-\s]?range|fermier)\b",

            # DIAGNOSTIC - nouveaux patterns
            "problem_type": r"\b(diarrhée|hémorragique|respiratory|respiratoire|digestive|nerveux|boiterie|picage)\b",
            "symptoms": r"\b(symptômes?|signes?|observe|constate|problème|maladie|infection)\b",
            "duration": r"(?:depuis|from|for)\s*(\d+)\s*(?:jours?|days?|semaines?|weeks?)",
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

        # ÉTAPE 1: Extraction brute (GPT + regex)
        raw: Dict[str, Any] = {}

        if self.use_gpt:
            raw = self._extract_gpt(question)
            if len(raw) < 2:  # Si GPT n'a pas bien fonctionné
                raw.update(self._extract_regex(question))
        else:
            raw = self._extract_regex(question)

        # ÉTAPE 2: Normalisation et enrichissement
        norm = self._normalize_and_enrich(raw, question)
        
        # ÉTAPE 3: Validation croisée et cohérence
        validated = self._validate_consistency(norm)
        
        # ÉTAPE 4: Scoring et identification champs manquants
        score, missing = validate_and_score(validated, question)
        
        logger.debug("🔍 Extraction: raw=%d, norm=%d, score=%.2f, missing=%s", 
                    len(raw), len(validated), score, missing)
        
        return validated, float(score), list(missing)

    # ---------------- Extraction GPT améliorée ---------------- #
    def _extract_gpt(self, question: str) -> Dict[str, Any]:
        """Extraction GPT avec prompt spécialisé aviculture"""
        prompt = f"""Tu es un expert en extraction d'entités pour l'aviculture. 
Extrait UNIQUEMENT les informations explicitement mentionnées dans cette question.

ENTITÉS PRIORITAIRES À RECHERCHER:
- species: "broiler" (poulet de chair) / "layer" (pondeuse) / "breeder" (reproducteur)
- line: lignée génétique exacte ("Ross 308", "Cobb 500", "ISA Brown", "Lohmann", "Hy-Line")
- sex: "male" (mâle) / "female" (femelle) / "mixed" (mixte)
- age_days: âge en jours (convertir semaines: 5 sem = 35 jours)
- phase: "starter" (0-10j) / "grower" (11-25j) / "finisher" (26j+) / "laying" (ponte)
- target_weight_g: poids cible en grammes
- production_rate_pct: taux de ponte en pourcentage

ENTITÉS SECONDAIRES:
- effectif: nombre d'oiseaux
- fcr: indice de consommation alimentaire
- problem_type: type de problème observé
- temperature: température ambiante

RÈGLES STRICTES:
1. Convertir semaines en jours (×7)
2. Normaliser lignées: "Ross trois cent huit" → "Ross 308"
3. Déduire espèce si lignée connue: Ross/Cobb → "broiler", ISA/Lohmann → "layer"
4. Extraire valeurs numériques avec unités
5. Retourner UNIQUEMENT du JSON valide, pas de texte explicatif

EXEMPLES:
Question: "Poids cible mâles Ross 308 à 35 jours ?"
→ {{"species": "broiler", "line": "Ross 308", "sex": "male", "age_days": 35, "target_weight_g": null}}

Question: "FCR normal Cobb 500 femelles 42 jours ?"
→ {{"species": "broiler", "line": "Cobb 500", "sex": "female", "age_days": 42}}

Question actuelle: "{question}"

JSON:"""

        try:
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=300,
            )
            content = (resp.choices[0].message.content or "").strip()
            extracted = self._parse_json(content)
            
            logger.debug("🤖 GPT extraction: %d champs extraits", len(extracted))
            return extracted
        except Exception as e:
            logger.debug("⚠️ GPT extraction error: %s", e)
            return {}

    def _parse_json(self, s: str) -> Dict[str, Any]:
        """Parse JSON avec nettoyage robuste"""
        try:
            t = s.strip()
            # Nettoyer les marqueurs markdown
            if t.startswith("```json"):
                t = t[7:]
            if t.startswith("```"):
                t = t[3:]
            if t.endswith("```"):
                t = t[:-3]
            
            # Nettoyer les caractères parasites courants
            t = t.strip().replace('\n', ' ').replace('\t', ' ')
            
            data = json.loads(t)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            logger.debug("⚠️ JSON parse error: %s", e)
            # Tentative de récupération avec regex simple
            try:
                # Chercher des paires clé-valeur simples
                pairs = re.findall(r'"([^"]+)":\s*"?([^",}]+)"?', s)
                return {k: v.strip('"') for k, v in pairs}
            except Exception:
                return {}
        except Exception:
            return {}

    def _extract_regex(self, question: str) -> Dict[str, Any]:
        """Extraction regex avec gestion d'erreurs robuste"""
        out: Dict[str, Any] = {}
        text = question or ""
        
        for k, rx in self.patterns.items():
            try:
                matches = re.findall(rx, text, re.IGNORECASE)
                if not matches:
                    continue
                    
                # Choisir premier match non vide
                val = matches[0]
                if isinstance(val, tuple):
                    val = next((x for x in val if x), "")
                if val and val.strip():
                    out[k] = val.strip()
                    
            except re.error as e:
                logger.warning("⚠️ Regex error for %s: %s", k, e)
        
        logger.debug("🔍 Regex extraction: %d champs extraits", len(out))
        return out

    # ---------------- Normalisation améliorée ---------------- #
    def _normalize_and_enrich(self, ctx: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Normalisation complète avec enrichissement et validation"""
        c = dict(ctx or {})

        # 1. NORMALISATION DES LIGNÉES avec synonymes
        line = self._normalize_line(c.get("line") or c.get("breed") or c.get("race") or "")
        if line:
            c["line"] = line
            c.setdefault("breed", line)
            c.setdefault("race", line)

        # 2. DÉDUCTION D'ESPÈCE depuis lignée ou texte
        species = self._deduce_species(line, question)
        if species:
            c["species"] = species

        # 3. NORMALISATION DU SEXE
        sex = self._normalize_sex(c.get("sex") or c.get("sexe") or "")
        if sex:
            c["sex"] = sex
            c["sexe"] = sex

        # 4. NORMALISATION DE L'ÂGE
        age_days = self._normalize_age(c)
        if age_days:
            c["age_days"] = age_days
            c["age_jours"] = age_days

        # 5. NORMALISATION DE LA PHASE
        phase = self._normalize_phase(c.get("phase") or c.get("age_phase") or "", age_days)
        if phase:
            c["phase"] = phase

        # 6. CONVERSIONS NUMÉRIQUES avec validation
        c = self._convert_numeric_fields(c)

        # 7. ENRICHISSEMENT CONTEXTUEL
        c = self._enrich_context(c, question)

        # 8. NORMALISATION FINALE via EntityNormalizer
        c = self.normalizer.normalize(c)
        
        return c

    def _normalize_line(self, line_raw: str) -> str:
        """Normalise les lignées avec gestion des variantes"""
        if not line_raw:
            return ""
            
        line = line_raw.lower().strip()
        
        # Substitutions directes depuis dictionnaire
        for alias, canonical in self.synonyms["line_aliases"].items():
            if alias in line:
                return canonical
        
        # Patterns de normalisation
        if re.search(r"ross.*30.*8", line):
            return "Ross 308"
        elif re.search(r"ross.*50.*0", line):
            return "Ross 500"
        elif re.search(r"ross.*70.*8", line):
            return "Ross 708"
        elif re.search(r"cobb.*50.*0", line):
            return "Cobb 500"
        elif re.search(r"cobb.*70.*0", line):
            return "Cobb 700"
        elif "hubbard" in line:
            if "ja" in line:
                return "Hubbard JA"
            elif "flex" in line:
                return "Hubbard Flex"
            else:
                return "Hubbard"
        elif "isa" in line and "brown" in line:
            return "ISA Brown"
        elif "lohmann" in line:
            if "brown" in line:
                return "Lohmann Brown"
            elif "white" in line:
                return "Lohmann White"
            else:
                return "Lohmann"
        elif "hy" in line and "line" in line:
            if "brown" in line:
                return "Hy-Line Brown"
            elif "white" in line:
                return "Hy-Line White"
            else:
                return "Hy-Line"
        
        # Retourner original capitalisé si pas de correspondance
        return line_raw.title()

    def _deduce_species(self, line: str, question: str) -> Optional[str]:
        """Déduit l'espèce depuis la lignée ou le texte"""
        # Depuis lignée
        if line:
            line_lower = line.lower()
            if any(x in line_lower for x in ["ross", "cobb", "hubbard"]):
                return "broiler"
            elif any(x in line_lower for x in ["isa", "lohmann", "hy-line"]):
                return "layer"
        
        # Depuis question avec synonymes
        q_lower = question.lower()
        for variant, canonical in self.synonyms["species"].items():
            if variant in q_lower:
                return canonical
        
        # Patterns contextuels
        if any(x in q_lower for x in ["poulet", "poussins", "poussin", "chick", "chicken"]):
            # Exclure si termes de ponte présents
            if not any(x in q_lower for x in ["pondeuse", "layer", "œuf", "oeuf", "ponte", "egg"]):
                return "broiler"
        
        return None

    def _normalize_sex(self, sex_raw: str) -> Optional[str]:
        """Normalise le sexe avec gestion synonymes"""
        if not sex_raw:
            return None
            
        sex_lower = sex_raw.lower().strip()
        
        # Substitutions directes
        for variant, canonical in self.synonyms["sex"].items():
            if variant in sex_lower:
                return canonical
        
        # Patterns additionnels
        if any(w in sex_lower for w in ["male", "mâle", "coq", "cockerel"]):
            return "male"
        elif any(w in sex_lower for w in ["female", "femelle", "poule", "hen", "pullet"]):
            return "female"
        elif any(w in sex_lower for w in ["mix", "mixed", "mixte"]):
            return "mixed"
        
        return None

    def _normalize_age(self, ctx: Dict[str, Any]) -> Optional[int]:
        """Normalise l'âge en jours avec conversion semaines"""
        # Priorité: age_days direct
        age_days = ctx.get("age_days") or ctx.get("age_jours")
        if age_days:
            if isinstance(age_days, str):
                # Extraction numérique
                match = re.search(r"(\d{1,3})", age_days)
                if match:
                    age_days = int(match.group(1))
                else:
                    age_days = None
            if isinstance(age_days, (int, float)) and 0 < age_days <= 365:
                return int(age_days)
        
        # Conversion depuis semaines
        age_weeks = ctx.get("age_weeks")
        if age_weeks:
            if isinstance(age_weeks, str):
                match = re.search(r"(\d{1,2})", age_weeks)
                if match:
                    weeks = int(match.group(1))
                    if 0 < weeks <= 80:
                        return weeks * 7
        
        return None

    def _normalize_phase(self, phase_raw: str, age_days: Optional[int]) -> Optional[str]:
        """Normalise la phase avec déduction depuis âge"""
        if phase_raw:
            phase_lower = phase_raw.lower().strip()
            
            # Substitutions directes
            for variant, canonical in self.synonyms["phase"].items():
                if variant in phase_lower:
                    return canonical
            
            # Patterns directs
            if "starter" in phase_lower or "start" in phase_lower:
                return "starter"
            elif "grower" in phase_lower or "grow" in phase_lower:
                return "grower"
            elif "finisher" in phase_lower or "finish" in phase_lower:
                return "finisher"
            elif "ponte" in phase_lower or "lay" in phase_lower:
                return "laying"
        
        # Déduction depuis âge (si broiler implicite)
        if age_days:
            if age_days <= 10:
                return "starter"
            elif age_days <= 25:
                return "grower"
            elif age_days <= 50:
                return "finisher"
            else:
                return "laying"  # Pourrait être pondeuse
        
        return None

    def _convert_numeric_fields(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Conversion des champs numériques avec validation"""
        # Champs flottants
        float_fields = ["ambient_c", "deltaT_C", "temp_outside", "fcr", "avg_weight_kg", 
                       "livability_pct", "production_rate_pct", "protein_pct", "density_kg_m2"]
        
        for field in float_fields:
            val = ctx.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    # Nettoyer et convertir
                    cleaned = val.replace(",", ".").strip()
                    num_val = float(re.sub(r"[^\d\.-]", "", cleaned))
                    
                    # Validation basique des plages
                    if field in ["livability_pct", "production_rate_pct"] and not (0 <= num_val <= 100):
                        continue
                    if field == "fcr" and not (0.5 <= num_val <= 10):
                        continue
                    if field in ["ambient_c", "temp_outside"] and not (-20 <= num_val <= 50):
                        continue
                    
                    ctx[field] = num_val
                except (ValueError, TypeError):
                    pass
        
        # Champs entiers
        int_fields = ["effectif", "flock_size", "poids_moyen_g", "target_weight_g", 
                     "age_days", "age_jours", "lighting_hours"]
        
        for field in int_fields:
            val = ctx.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    # Extraire premier nombre
                    match = re.search(r"(\d+)", val)
                    if match:
                        num_val = int(match.group(1))
                        
                        # Validation basique des plages
                        if field in ["effectif", "flock_size"] and not (10 <= num_val <= 1000000):
                            continue
                        if field in ["poids_moyen_g", "target_weight_g"] and not (10 <= num_val <= 10000):
                            continue
                        if field in ["age_days", "age_jours"] and not (0 <= num_val <= 365):
                            continue
                        
                        ctx[field] = num_val
                except (ValueError, TypeError):
                    pass
        
        return ctx

    def _enrich_context(self, ctx: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Enrichissement contextuel basé sur la question"""
        q_lower = question.lower()
        
        # Détection type de problème
        if any(x in q_lower for x in ["problème", "baisse", "dégradé", "anormal", "inquiétant"]):
            ctx["problem_detected"] = True
            
            if any(x in q_lower for x in ["ponte", "production", "œuf", "laying"]):
                ctx["problem_type"] = "production"
            elif any(x in q_lower for x in ["croissance", "poids", "growth", "weight"]):
                ctx["problem_type"] = "growth"
            elif any(x in q_lower for x in ["mortalité", "mortality", "mort"]):
                ctx["problem_type"] = "mortality"
            elif any(x in q_lower for x in ["fcr", "consommation", "conversion"]):
                ctx["problem_type"] = "feed_efficiency"
        
        # Détection objectif performance
        if any(x in q_lower for x in ["cible", "target", "optimal", "recommandé", "idéal"]):
            ctx["seeking_target"] = True
        
        # Détection urgence
        if any(x in q_lower for x in ["urgent", "rapide", "immédiat", "que faire"]):
            ctx["urgency"] = "high"
        
        return ctx

    # ---------------- Validation de cohérence ---------------- #
    def _validate_consistency(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Validation de cohérence métier avicole"""
        validated = dict(ctx)
        
        # Cohérence lignée-espèce
        line = validated.get("line", "")
        species = validated.get("species", "")
        
        if line and not species:
            # Déduire espèce manquante
            if any(x in line.lower() for x in ["ross", "cobb", "hubbard"]):
                validated["species"] = "broiler"
            elif any(x in line.lower() for x in ["isa", "lohmann", "hy-line"]):
                validated["species"] = "layer"
        
        elif line and species:
            # Vérifier cohérence
            broiler_lines = ["ross", "cobb", "hubbard"]
            layer_lines = ["isa", "lohmann", "hy-line"]
            
            line_lower = line.lower()
            is_broiler_line = any(x in line_lower for x in broiler_lines)
            is_layer_line = any(x in line_lower for x in layer_lines)
            
            if species == "broiler" and is_layer_line:
                logger.warning("⚠️ Incohérence: lignée pondeuse avec espèce broiler")
                validated["species"] = "layer"  # Corriger
            elif species == "layer" and is_broiler_line:
                logger.warning("⚠️ Incohérence: lignée broiler avec espèce layer")
                validated["species"] = "broiler"  # Corriger
        
        # Cohérence âge-phase
        age_days = validated.get("age_days")
        phase = validated.get("phase")
        
        if age_days and phase:
            # Vérifications logiques
            if phase == "starter" and age_days > 15:
                logger.warning("⚠️ Incohérence: phase starter à %d jours", age_days)
            elif phase == "finisher" and age_days < 20:
                logger.warning("⚠️ Incohérence: phase finisher à %d jours", age_days)
        
        # Cohérence poids-âge (validation grossière)
        weight_g = validated.get("target_weight_g") or validated.get("poids_moyen_g")
        if weight_g and age_days and species == "broiler":
            expected_range = self._expected_weight_range(age_days)
            if expected_range and not (expected_range[0] <= weight_g <= expected_range[1]):
                logger.warning("⚠️ Poids %dg à %dj semble atypique (attendu %d-%dg)", 
                             weight_g, age_days, expected_range[0], expected_range[1])
        
        return validated

    def _expected_weight_range(self, age_days: int) -> Optional[Tuple[int, int]]:
        """Plages de poids attendues pour broilers (approximatives)"""
        if age_days <= 0:
            return None
        elif age_days <= 7:
            return (40, 200)
        elif age_days <= 14:
            return (200, 500)
        elif age_days <= 21:
            return (500, 1000)
        elif age_days <= 28:
            return (1000, 1800)
        elif age_days <= 35:
            return (1800, 2500)
        elif age_days <= 42:
            return (2500, 3500)
        elif age_days <= 49:
            return (3000, 4500)
        else:
            return (3500, 5000)

    # ---------------- Méthodes utilitaires ---------------- #
    def get_confidence_score(self, ctx: Dict[str, Any], question: str) -> float:
        """Calcule un score de confiance pour l'extraction"""
        if not ctx:
            return 0.0
        
        # Facteurs de confiance
        score = 0.0
        factors = 0
        
        # Présence champs critiques
        critical_fields = ["species", "line", "age_days"]
        for field in critical_fields:
            if field in ctx and ctx[field]:
                score += 1.0
                factors += 1
        
        # Cohérence détectée
        if self._check_consistency_simple(ctx):
            score += 0.5
            factors += 1
        
        # Précision numérique
        numeric_fields = ["age_days", "target_weight_g", "fcr", "effectif"]
        numeric_count = sum(1 for f in numeric_fields if f in ctx and isinstance(ctx[f], (int, float)))
        if numeric_count > 0:
            score += numeric_count * 0.3
            factors += 1
        
        return min(score / max(factors, 1), 1.0)

    def _check_consistency_simple(self, ctx: Dict[str, Any]) -> bool:
        """Vérification simple de cohérence"""
        line = ctx.get("line", "").lower()
        species = ctx.get("species", "")
        
        if not line or not species:
            return True  # Pas assez d'info pour vérifier
        
        broiler_lines = ["ross", "cobb", "hubbard"]
        layer_lines = ["isa", "lohmann", "hy-line"]
        
        is_broiler_line = any(x in line for x in broiler_lines)
        is_layer_line = any(x in line for x in layer_lines)
        
        if species == "broiler" and is_broiler_line:
            return True
        elif species == "layer" and is_layer_line:
            return True
        elif not is_broiler_line and not is_layer_line:
            return True  # Lignée inconnue
        
        return False  # Incohérence détectée