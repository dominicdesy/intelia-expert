# app/api/v1/utils/entity_normalizer.py - VERSION AMÉLIORÉE
from __future__ import annotations

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NormalizationRule:
    """Règle de normalisation avec pattern et transformation"""
    field: str
    pattern: str
    replacement: str
    priority: int = 1
    conditions: Dict[str, Any] = None

class EntityNormalizer:
    """
    Normaliseur d'entités avancé pour l'aviculture.
    - Normalisation avec règles contextuelles
    - Correction de fautes de frappe
    - Validation et enrichissement automatique
    - Gestion des synonymes et variantes linguistiques
    """
    
    def __init__(self):
        # Dictionnaires de normalisation étendus
        self.species_mapping = {
            # Français vers anglais normalisé
            "poulet de chair": "broiler",
            "poulets de chair": "broiler", 
            "chair": "broiler",
            "poulet chair": "broiler",
            "broilers": "broiler",
            "broiler chicken": "broiler",
            
            "pondeuse": "layer",
            "pondeuses": "layer",
            "poule pondeuse": "layer",
            "poules pondeuses": "layer",
            "layers": "layer",
            "laying hen": "layer",
            "laying hens": "layer",
            
            "reproducteur": "breeder",
            "reproducteurs": "breeder",
            "parentale": "breeder",
            "parentales": "breeder",
            "breeders": "breeder",
            "breeding stock": "breeder"
        }
        
        self.sex_mapping = {
            # Variations françaises et anglaises
            "mâle": "male",
            "males": "male",
            "mâles": "male",
            "coq": "male",
            "coqs": "male",
            "cockerel": "male",
            "cockerels": "male",
            
            "femelle": "female",
            "femelles": "female",
            "poule": "female",
            "poules": "female",
            "hen": "female",
            "hens": "female",
            "pullet": "female",
            "pullets": "female",
            
            "mixte": "mixed",
            "mixtes": "mixed",
            "mix": "mixed",
            "straight run": "mixed"
        }
        
        # Mapping lignées avec variations orthographiques et linguistiques
        self.breed_mapping = {
            # Ross variants
            "ross trois cent huit": "Ross 308",
            "ross 3 0 8": "Ross 308",
            "ross308": "Ross 308",
            "ros 308": "Ross 308",
            "ross trois cents huit": "Ross 308",
            
            "ross cinq cents": "Ross 500", 
            "ross 5 0 0": "Ross 500",
            "ross500": "Ross 500",
            "ros 500": "Ross 500",
            
            "ross sept cent huit": "Ross 708",
            "ross 7 0 8": "Ross 708",
            "ross708": "Ross 708",
            
            # Cobb variants
            "cobb cinq cents": "Cobb 500",
            "cobb 5 0 0": "Cobb 500", 
            "cobb500": "Cobb 500",
            "cob 500": "Cobb 500",
            
            "cobb sept cents": "Cobb 700",
            "cobb 7 0 0": "Cobb 700",
            "cobb700": "Cobb 700",
            
            # Hubbard variants
            "hubbard ja": "Hubbard JA",
            "hubbard j a": "Hubbard JA",
            "hubbard flex": "Hubbard Flex",
            "hubbard classic": "Hubbard Classic",
            
            # ISA variants
            "isa brown": "ISA Brown",
            "isa brun": "ISA Brown",
            "isabrown": "ISA Brown",
            "isa blanc": "ISA White",
            "isa white": "ISA White",
            
            # Lohmann variants
            "lohmann brown": "Lohmann Brown",
            "lohmann brun": "Lohmann Brown",
            "lohmann white": "Lohmann White",
            "lohmann blanc": "Lohmann White",
            "lohmann lsl": "Lohmann LSL",
            
            # Hy-Line variants
            "hy-line brown": "Hy-Line Brown",
            "hy line brown": "Hy-Line Brown",
            "hyline brown": "Hy-Line Brown",
            "hy-line white": "Hy-Line White",
            "hy line white": "Hy-Line White",
            "hyline white": "Hy-Line White",
            "hy-line w36": "Hy-Line W36",
            "hy line w36": "Hy-Line W36",
            "hy-line w-36": "Hy-Line W36"
        }
        
        self.phase_mapping = {
            # Phases français vers anglais
            "démarrage": "starter",
            "demarrage": "starter",
            "pré-starter": "pre-starter",
            "pre starter": "pre-starter",
            "préstarter": "pre-starter",
            "prestarter": "pre-starter",
            
            "croissance": "grower",
            "élevage": "grower",
            "elevage": "grower",
            
            "finition": "finisher",
            "finisher": "finisher",
            "fin": "finisher",
            
            "ponte": "laying",
            "laying": "laying",
            "lay": "laying",
            "production": "laying"
        }
        
        # Patterns de correction de fautes courantes
        self.typo_corrections = {
            r"\bross\s*30(\d)\b": r"Ross 30\1",  # ross 30X -> Ross 30X
            r"\bcobb\s*50(\d)\b": r"Cobb 50\1",  # cobb 50X -> Cobb 50X
            r"\bisa\s*brow?n?\b": "ISA Brown",   # isa brow -> ISA Brown
            r"\blohman+\b": "Lohmann",           # lohman -> Lohmann
            r"\bhy[-\s]*lin?e?\b": "Hy-Line",    # hy lin -> Hy-Line
        }
        
        # Règles de validation et enrichissement
        self.validation_rules = [
            # Si lignée Ross/Cobb/Hubbard -> espèce broiler
            NormalizationRule(
                field="species",
                pattern=r"ross|cobb|hubbard",
                replacement="broiler",
                conditions={"source_field": "line"}
            ),
            # Si lignée ISA/Lohmann/Hy-Line -> espèce layer
            NormalizationRule(
                field="species", 
                pattern=r"isa|lohmann|hy-line",
                replacement="layer",
                conditions={"source_field": "line"}
            )
        ]

    def normalize(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise complètement un contexte avec toutes les règles
        
        Args:
            context: Contexte brut à normaliser
            
        Returns:
            Contexte normalisé et enrichi
        """
        
        if not context:
            return {}
        
        normalized = dict(context)
        
        # 1. Nettoyage de base
        normalized = self._clean_basic_fields(normalized)
        
        # 2. Correction des fautes de frappe
        normalized = self._correct_typos(normalized)
        
        # 3. Normalisation des entités spécifiques
        normalized = self._normalize_species(normalized)
        normalized = self._normalize_sex(normalized)
        normalized = self._normalize_breeds(normalized)
        normalized = self._normalize_phases(normalized)
        
        # 4. Conversions numériques avec validation
        normalized = self._normalize_numeric_fields(normalized)
        
        # 5. Enrichissement automatique
        normalized = self._apply_enrichment_rules(normalized)
        
        # 6. Validation et cohérence
        normalized = self._apply_validation_rules(normalized)
        
        # 7. Synchronisation des champs liés
        normalized = self._synchronize_related_fields(normalized)
        
        logger.debug("🔧 Normalisation: %d→%d champs, enrichi", len(context), len(normalized))
        
        return normalized

    def _clean_basic_fields(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Nettoyage de base des champs"""
        
        cleaned = {}
        
        for key, value in context.items():
            if value is None:
                continue
                
            # Nettoyer les chaînes
            if isinstance(value, str):
                # Supprimer espaces superflus
                clean_value = re.sub(r'\s+', ' ', str(value).strip())
                
                # Supprimer caractères spéciaux parasites
                clean_value = re.sub(r'[^\w\s\-\.,%°]', '', clean_value)
                
                # Ne garder que si non vide
                if clean_value:
                    cleaned[key] = clean_value
            else:
                cleaned[key] = value
        
        return cleaned

    def _correct_typos(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Correction automatique des fautes de frappe"""
        
        corrected = dict(context)
        
        # Appliquer corrections aux champs textuels
        for field in ["line", "race", "breed", "species"]:
            value = corrected.get(field)
            if not value or not isinstance(value, str):
                continue
                
            original_value = value
            
            # Appliquer patterns de correction
            for pattern, replacement in self.typo_corrections.items():
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
            
            # Log si correction appliquée
            if value != original_value:
                logger.debug("🔧 Correction faute: '%s' → '%s'", original_value, value)
                corrected[field] = value
        
        return corrected

    def _normalize_species(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation des espèces"""
        
        normalized = dict(context)
        
        for field in ["species", "production_type", "espece"]:
            value = normalized.get(field)
            if not value:
                continue
                
            value_lower = str(value).lower().strip()
            
            # Recherche dans mapping
            if value_lower in self.species_mapping:
                normalized_species = self.species_mapping[value_lower]
                normalized["species"] = normalized_species
                
                # Synchroniser champs connexes
                if field != "species":
                    normalized["production_type"] = normalized_species
                
                logger.debug("🔧 Espèce normalisée: '%s' → '%s'", value, normalized_species)
                break
        
        return normalized

    def _normalize_sex(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation du sexe"""
        
        normalized = dict(context)
        
        for field in ["sex", "sexe", "sex_category"]:
            value = normalized.get(field)
            if not value:
                continue
                
            value_lower = str(value).lower().strip()
            
            # Recherche dans mapping
            if value_lower in self.sex_mapping:
                normalized_sex = self.sex_mapping[value_lower]
                normalized["sex"] = normalized_sex
                normalized["sexe"] = normalized_sex  # Synchroniser français
                
                logger.debug("🔧 Sexe normalisé: '%s' → '%s'", value, normalized_sex)
                break
        
        return normalized

    def _normalize_breeds(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation des lignées/races"""
        
        normalized = dict(context)
        
        for field in ["line", "race", "breed"]:
            value = normalized.get(field)
            if not value:
                continue
                
            value_lower = str(value).lower().strip()
            
            # Recherche exacte dans mapping
            if value_lower in self.breed_mapping:
                normalized_breed = self.breed_mapping[value_lower]
                
                # Synchroniser tous les champs lignée
                normalized["line"] = normalized_breed
                normalized["race"] = normalized_breed
                normalized["breed"] = normalized_breed
                
                logger.debug("🔧 Lignée normalisée: '%s' → '%s'", value, normalized_breed)
                break
            
            # Recherche partielle pour variants non listés
            normalized_breed = self._fuzzy_breed_match(value_lower)
            if normalized_breed:
                normalized["line"] = normalized_breed
                normalized["race"] = normalized_breed
                normalized["breed"] = normalized_breed
                
                logger.debug("🔧 Lignée fuzzy match: '%s' → '%s'", value, normalized_breed)
                break
        
        return normalized

    def _fuzzy_breed_match(self, value: str) -> Optional[str]:
        """Correspondance floue pour lignées non listées"""
        
        value_clean = re.sub(r'[^\w]', '', value.lower())
        
        # Patterns de reconnaissance
        patterns = [
            (r'ross.*30.*8', "Ross 308"),
            (r'ross.*50.*0', "Ross 500"), 
            (r'ross.*70.*8', "Ross 708"),
            (r'cobb.*50.*0', "Cobb 500"),
            (r'cobb.*70.*0', "Cobb 700"),
            (r'hubbard.*ja', "Hubbard JA"),
            (r'hubbard.*flex', "Hubbard Flex"),
            (r'isa.*brown', "ISA Brown"),
            (r'isa.*white', "ISA White"),
            (r'lohmann.*brown', "Lohmann Brown"),
            (r'lohmann.*white', "Lohmann White"),
            (r'hyline.*brown', "Hy-Line Brown"),
            (r'hyline.*white', "Hy-Line White")
        ]
        
        for pattern, normalized_name in patterns:
            if re.search(pattern, value_clean):
                return normalized_name
        
        return None

    def _normalize_phases(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation des phases d'élevage"""
        
        normalized = dict(context)
        
        for field in ["phase", "age_phase"]:
            value = normalized.get(field)
            if not value:
                continue
                
            value_lower = str(value).lower().strip()
            
            # Recherche dans mapping
            if value_lower in self.phase_mapping:
                normalized_phase = self.phase_mapping[value_lower]
                normalized["phase"] = normalized_phase
                
                logger.debug("🔧 Phase normalisée: '%s' → '%s'", value, normalized_phase)
                break
        
        return normalized

    def _normalize_numeric_fields(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation et validation des champs numériques"""
        
        normalized = dict(context)
        
        # Champs entiers
        integer_fields = {
            "age_days": (0, 365),
            "age_jours": (0, 365),
            "effectif": (1, 1000000),
            "flock_size": (1, 1000000),
            "poids_moyen_g": (10, 10000),
            "target_weight_g": (10, 10000)
        }
        
        for field, (min_val, max_val) in integer_fields.items():
            value = normalized.get(field)
            if value is None:
                continue
                
            try:
                # Extraire nombre si chaîne
                if isinstance(value, str):
                    # Supprimer unités et caractères non numériques  
                    clean_value = re.sub(r'[^\d]', '', value)
                    if not clean_value:
                        continue
                    numeric_value = int(clean_value)
                else:
                    numeric_value = int(value)
                
                # Valider plage
                if min_val <= numeric_value <= max_val:
                    normalized[field] = numeric_value
                else:
                    logger.warning("⚠️ Valeur %s hors plage [%d-%d]: %d", 
                                 field, min_val, max_val, numeric_value)
                    # Garder quand même mais signaler
                    normalized[field] = numeric_value
                    
            except (ValueError, TypeError):
                logger.warning("⚠️ Impossible de convertir %s en entier: %s", field, value)
        
        # Champs flottants
        float_fields = {
            "fcr": (0.5, 10.0),
            "ambient_c": (-20.0, 50.0),
            "temperature": (-20.0, 50.0),
            "livability_pct": (0.0, 100.0),
            "production_rate_pct": (0.0, 100.0),
            "protein_pct": (5.0, 35.0)
        }
        
        for field, (min_val, max_val) in float_fields.items():
            value = normalized.get(field)
            if value is None:
                continue
                
            try:
                # Nettoyer et convertir
                if isinstance(value, str):
                    clean_value = value.replace(',', '.').strip()
                    # Garder seulement chiffres, point et signe moins
                    clean_value = re.sub(r'[^\d\.\-]', '', clean_value)
                    if not clean_value or clean_value in ['.', '-']:
                        continue
                    numeric_value = float(clean_value)
                else:
                    numeric_value = float(value)
                
                # Valider plage
                if min_val <= numeric_value <= max_val:
                    normalized[field] = numeric_value
                else:
                    logger.warning("⚠️ Valeur %s hors plage [%.1f-%.1f]: %.2f", 
                                 field, min_val, max_val, numeric_value)
                    normalized[field] = numeric_value
                    
            except (ValueError, TypeError):
                logger.warning("⚠️ Impossible de convertir %s en float: %s", field, value)
        
        return normalized

    def _apply_enrichment_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Application des règles d'enrichissement automatique"""
        
        enriched = dict(context)
        
        # Déduction espèce depuis lignée
        line = enriched.get("line") or enriched.get("race") or enriched.get("breed")
        if line and not enriched.get("species"):
            line_lower = line.lower()
            
            if any(breed in line_lower for breed in ["ross", "cobb", "hubbard"]):
                enriched["species"] = "broiler"
                logger.debug("🔧 Espèce déduite: broiler (depuis lignée %s)", line)
            elif any(breed in line_lower for breed in ["isa", "lohmann", "hy-line"]):
                enriched["species"] = "layer"
                logger.debug("🔧 Espèce déduite: layer (depuis lignée %s)", line)
        
        # Déduction phase depuis âge et espèce
        age_days = enriched.get("age_days") or enriched.get("age_jours")
        species = enriched.get("species")
        
        if age_days and species and not enriched.get("phase"):
            try:
                age = int(age_days)
                
                if species == "broiler":
                    if age <= 10:
                        enriched["phase"] = "starter"
                    elif age <= 25:
                        enriched["phase"] = "grower"
                    else:
                        enriched["phase"] = "finisher"
                elif species == "layer":
                    if age <= 42:  # 6 semaines
                        enriched["phase"] = "starter"
                    elif age <= 112:  # 16 semaines
                        enriched["phase"] = "grower"
                    elif age <= 140:  # 20 semaines
                        enriched["phase"] = "pre_lay"
                    else:
                        enriched["phase"] = "laying"
                
                if enriched.get("phase"):
                    logger.debug("🔧 Phase déduite: %s (âge %dj, espèce %s)", 
                               enriched["phase"], age, species)
                    
            except (ValueError, TypeError):
                pass
        
        # Conversion âge semaines vers jours
        age_weeks = enriched.get("age_weeks")
        if age_weeks and not enriched.get("age_days"):
            try:
                weeks = float(age_weeks)
                days = int(weeks * 7)
                enriched["age_days"] = days
                enriched["age_jours"] = days
                logger.debug("🔧 Âge converti: %s sem → %d jours", age_weeks, days)
            except (ValueError, TypeError):
                pass
        
        return enriched

    def _apply_validation_rules(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Application des règles de validation avec correction automatique"""
        
        validated = dict(context)
        
        for rule in self.validation_rules:
            conditions = rule.conditions or {}
            source_field = conditions.get("source_field")
            
            # Vérifier si règle s'applique
            if source_field and source_field in validated:
                source_value = str(validated[source_field]).lower()
                
                if re.search(rule.pattern, source_value, re.IGNORECASE):
                    # Appliquer correction
                    current_value = validated.get(rule.field)
                    
                    # Seulement si pas déjà défini ou si conflit
                    if not current_value or current_value != rule.replacement:
                        validated[rule.field] = rule.replacement
                        logger.debug("🔧 Règle validation: %s=%s (depuis %s=%s)", 
                                   rule.field, rule.replacement, source_field, source_value)
        
        return validated

    def _synchronize_related_fields(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronisation des champs liés pour cohérence"""
        
        synchronized = dict(context)
        
        # Synchroniser age_days et age_jours
        age_days = synchronized.get("age_days")
        age_jours = synchronized.get("age_jours")
        
        if age_days and not age_jours:
            synchronized["age_jours"] = age_days
        elif age_jours and not age_days:
            synchronized["age_days"] = age_jours
        
        # Synchroniser sex et sexe
        sex = synchronized.get("sex")
        sexe = synchronized.get("sexe")
        
        if sex and not sexe:
            synchronized["sexe"] = sex
        elif sexe and not sex:
            synchronized["sex"] = sexe
        
        # Synchroniser line, race, breed
        line_fields = ["line", "race", "breed"]
        line_values = [synchronized.get(f) for f in line_fields if synchronized.get(f)]
        
        if line_values:
            # Prendre la valeur la plus complète (plus longue)
            best_value = max(line_values, key=len)
            for field in line_fields:
                synchronized[field] = best_value
        
        return synchronized

    def get_normalization_report(self, original: Dict[str, Any], normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un rapport des normalisations appliquées"""
        
        report = {
            "fields_added": [],
            "fields_modified": [],
            "fields_removed": [],
            "enrichments": [],
            "validations": []
        }
        
        # Champs ajoutés
        for key in normalized:
            if key not in original:
                report["fields_added"].append(key)
        
        # Champs modifiés
        for key in original:
            if key in normalized and original[key] != normalized[key]:
                report["fields_modified"].append({
                    "field": key,
                    "from": original[key],
                    "to": normalized[key]
                })
        
        # Champs supprimés
        for key in original:
            if key not in normalized:
                report["fields_removed"].append(key)
        
        return report

    def suggest_corrections(self, context: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """Suggère des corrections possibles sans les appliquer"""
        
        suggestions = []
        
        for field, value in context.items():
            if not value or not isinstance(value, str):
                continue
                
            value_lower = value.lower().strip()
            
            # Suggestions pour espèces
            if field in ["species", "production_type"]:
                if value_lower in self.species_mapping:
                    suggestions.append((field, value, self.species_mapping[value_lower]))
            
            # Suggestions pour lignées
            elif field in ["line", "race", "breed"]:
                if value_lower in self.breed_mapping:
                    suggestions.append((field, value, self.breed_mapping[value_lower]))
                else:
                    fuzzy_match = self._fuzzy_breed_match(value_lower)
                    if fuzzy_match:
                        suggestions.append((field, value, fuzzy_match))
            
            # Suggestions pour sexe
            elif field in ["sex", "sexe"]:
                if value_lower in self.sex_mapping:
                    suggestions.append((field, value, self.sex_mapping[value_lower]))
        
        return suggestions