import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any
from app.api.v1.utils.entity_normalizer import EntityNormalizer
from app.api.v1.utils.validation_pipeline import validate_and_score
from app.api.v1.utils.openai_utils import safe_chat_completion

# Configuration du logging
logger = logging.getLogger(__name__)

class ContextExtractor:
    """
    Extracts structured context from a raw question.
    Uses GPT via safe_chat_completion to parse key fields into JSON,
    then falls back to regex extraction on failure.
    Returns: (context_dict, completeness_score, missing_fields)
    
    AMÉLIORATIONS APPLIQUÉES:
    - Patterns regex externalisés et configurables
    - Gestion d'erreurs robuste pour l'appel OpenAI
    - Validation JSON stricte avec fallback
    - Logging détaillé pour debug
    - Configuration flexible via fichiers externes
    """
    
    def __init__(self, use_gpt: bool = True, patterns_config_path: str = None):
        self.normalizer = EntityNormalizer()
        self.use_gpt = use_gpt
        self.patterns = self._load_extraction_patterns(patterns_config_path)
        
        # Configuration GPT fields (externalisable aussi)
        self.gpt_fields = self._get_gpt_fields()
        
        logger.debug(f"ContextExtractor initialisé avec {len(self.patterns)} patterns")

    def _get_gpt_fields(self) -> List[str]:
        """
        ✅ AMÉLIORATION: Champs GPT configurables
        Peut être étendu pour charger depuis la configuration
        """
        return [
            "age_jours", "production_type", "age_phase", "sex_category",
            "site_type", "housing_type", "activity", "parameter", 
            "numeric_value", "issue", "user_role", "objective", "breed"
        ]

    def _load_extraction_patterns(self, config_path: str = None) -> Dict[str, str]:
        """
        ✅ AMÉLIORATION MAJEURE: Charge les patterns depuis un fichier de configuration
        
        Ordre de priorité:
        1. Fichier spécifié en paramètre
        2. Variable d'environnement EXTRACTION_PATTERNS_PATH
        3. Fichier par défaut extraction_patterns.json
        4. Patterns hardcodés en fallback
        """
        
        # Déterminer le chemin du fichier de configuration
        if config_path:
            patterns_file = config_path
        else:
            patterns_file = os.getenv(
                'EXTRACTION_PATTERNS_PATH', 
                os.path.join(os.path.dirname(__file__), 'extraction_patterns.json')
            )
        
        # Tentative de chargement depuis fichier
        if os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    patterns_config = json.load(f)
                    
                if 'patterns' in patterns_config:
                    logger.info(f"✅ Patterns chargés depuis: {patterns_file}")
                    return patterns_config['patterns']
                else:
                    logger.warning(f"⚠️ Format invalide dans {patterns_file}, clé 'patterns' manquante")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erreur chargement patterns depuis {patterns_file}: {e}")
        else:
            logger.debug(f"📁 Fichier patterns non trouvé: {patterns_file}")
        
        # Fallback vers patterns hardcodés
        logger.info("🔄 Utilisation des patterns par défaut (hardcodés)")
        return self._get_default_patterns()

    def _get_default_patterns(self) -> Dict[str, str]:
        """
        ✅ AMÉLIORATION: Patterns par défaut séparés en méthode
        Facilite la maintenance et les tests
        """
        return {
            "production_type": r"\b(?:broiler|layer|breeder|pullet)s?\b",
            "age_phase": r"\b(?:day|d|week|wk|wks|month|mo)s?[-\s]*old\b|\b(?:at|from|on)?\s?\b(?:day\s?\d{1,2}|week\s?\d{1,2})\b",
            "sex_category": r"\b(?:male|female|mixed flock|pullets?|cockerels?)\b",
            "site_type": r"\b(?:hatchery|barn|house|processing plant|feed mill)\b",
            "housing_type": r"\b(?:tunnel-ventilated|open-sided|enriched cage|aviary|floor|slatted floor)\b",
            "activity": r"\b(?:feeding|vaccination|beak trimming|culling|catching|lighting|ventilation|weighing|sampling)\b",
            "parameter": r"\b(?:weight|body weight|FCR|feed conversion|mortality|water intake|egg production|temperature|humidity|NH3|CO2|uniformity)\b",
            "numeric_value": r"""
                \b
                (\d+(?:[\.,]\d+)?\s*
                (?:
                    kg|g|mg|\u00b5g|mcg|lb|lbs|oz|
                    l|L|ml|mL|gal|gallon[s]?|qt[s]?|
                    \u00b0C|\u00b0F|C|F|
                    cm|mm|m|in(?:ch)?(?:es)?|ft|feet|
                    ppm|%|bpm|IU|
                    g/bird|lb/bird|oz/bird|
                    g/day|g/bird/day|lb/day|
                    birds|eggs|head[s]?|
                    cal|kcal|kcal/kg|kcal/lb
                ))
                \b
            """,
            "issue": r"\b(" + "|".join([
                "heat stress", "thermal stress", "feather pecking", "pecking", "cannibalism",
                "aggression", "fighting", "lethargy", "inactivity", "reduced mobility",
                "lameness", "leg problems", "limping", "breast blister", "keel bone damage",
                "footpad dermatitis", "footpad lesions", "slipping", "loss of balance", "paralysis", "paresis",
                "high mortality", "sudden death syndrome", "sudden death", "flip[- ]?over", "low viability",
                "low livability", "deformities", "skeletal defects",
                "wet litter", "ammonia smell", "high NH3", "high temperature", "overheating",
                "cold drafts", "low barn temperature", "poor air quality", "low airflow", "CO2 buildup",
                "underfeeding", "feed restriction", "poor FCR", "high feed conversion ratio",
                "waterline blockage", "no access to water", "nutrient deficiency", "excess salt",
                "poor formulation",
                "respiratory issues", "sneezing", "rales", "enteritis", "diarrhea", "wet droppings",
                "bacterial infection", "colibacillosis", "viral outbreak", "IBV", "NDV", "AI", "coccidiosis",
                "vaccination failure", "poor immune response",
                "low egg production", "drop in lay rate", "thin shells", "shell defects", "poor shell quality",
                "dirty eggs", "soiled eggs", "floor eggs", "eggs outside nesting area", "egg binding"
            ]) + r")\b",
            "user_role": r"\b(?:farmer|grower|veterinarian|nutritionist|technician|supervisor|consultant)\b",
            "objective": r"\b(?:optimize|improve|detect|prevent|reduce|increase|adjust|monitor)\b",
            "breed": r"\b(ross\s?\d{3}|ross|cobb\s?\d{3}|cobb|hubbard|dekalb|hy-?line|lohmann|isa\s?brown|isa)\b",
        }

    def reload_patterns(self, config_path: str = None) -> bool:
        """
        ✅ NOUVELLE FONCTIONNALITÉ: Rechargement des patterns à chaud
        Utile pour les mises à jour sans redémarrage
        """
        try:
            old_count = len(self.patterns)
            self.patterns = self._load_extraction_patterns(config_path)
            new_count = len(self.patterns)
            
            logger.info(f"🔄 Patterns rechargés: {old_count} → {new_count}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur rechargement patterns: {e}")
            return False

    def extract(self, question: str) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        Extrait le contexte d'une question avec gestion d'erreurs robuste
        """
        if not question or not question.strip():
            logger.warning("Question vide reçue")
            return {}, 0.0, []
        
        question = question.strip()
        context: Dict[str, Any] = {}
        
        if self.use_gpt:
            logger.debug(f"🤖 Tentative d'extraction GPT pour: {question[:50]}...")
            context = self._extract_with_gpt(question)
            
            # Si GPT échoue ou retourne peu de résultats, essayer regex aussi
            if len(context) < 2:
                logger.debug("🔄 Résultats GPT limités, enrichissement avec regex...")
                regex_context = self._regex_extract(question)
                # Merger les résultats (GPT prioritaire)
                for key, value in regex_context.items():
                    if key not in context:
                        context[key] = value
        else:
            logger.debug("📝 Extraction directe par regex (GPT désactivé)")
            context = self._regex_extract(question)

        # Normalisation et validation (conservé)
        context = self.normalizer.normalize(context)
        score, missing = validate_and_score(context, question)
        
        logger.debug(f"📊 Contexte final: {len(context)} champs, score: {score:.2f}")
        
        return context, score, missing

    def _extract_with_gpt(self, question: str) -> Dict[str, Any]:
        """
        ✅ AMÉLIORATION: Extraction GPT séparée avec gestion d'erreurs robuste
        """
        
        fields_str = ", ".join(self.gpt_fields)
        prompt = (
            "Vous êtes un assistant avicole expert. À partir de la question utilisateur, "
            f"extrayez les champs suivants si présents: {fields_str}. "
            "Répondez UNIQUEMENT au format JSON valide avec ces clés si trouvées. "
            "Ne pas ajouter de texte avant ou après le JSON. "
            "Si un champ n'est pas présent, ne pas l'inclure dans la réponse."
            f"\n\nQuestion: {question}"
        )
        
        try:
            # Tentative d'appel OpenAI avec timeout et retry
            resp = safe_chat_completion(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256
            )
            
            if not resp or not resp.choices:
                logger.warning("⚠️ Réponse OpenAI vide ou malformée")
                return {}
            
            content = resp.choices[0].message.content.strip()
            logger.debug(f"🤖 Réponse GPT brute: {content[:200]}...")
            
            return self._parse_json_response(content)
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur extraction GPT: {type(e).__name__}: {str(e)}")
            return {}

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """
        ✅ AMÉLIORATION: Parse robuste de la réponse JSON avec nettoyage
        """
        try:
            # Nettoyage du contenu
            cleaned_content = content.strip()
            
            # Supprimer les blocs de code markdown si présents
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content[3:]
            
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]
            
            cleaned_content = cleaned_content.strip()
            
            # Tentative de parsing JSON
            extracted = json.loads(cleaned_content)
            
            if not isinstance(extracted, dict):
                logger.warning(f"⚠️ Réponse JSON n'est pas un dict: {type(extracted)}")
                return {}
            
            # Filtrer uniquement les champs valides et non vides
            valid_keys = set(self.gpt_fields)
            filtered_context = {
                k: v for k, v in extracted.items() 
                if k in valid_keys and v and str(v).strip()
            }
            
            if filtered_context:
                logger.debug(f"✅ Extraction GPT réussie: {len(filtered_context)} champs")
            else:
                logger.debug("ℹ️ Aucun champ valide dans la réponse GPT")
            
            return filtered_context
                
        except json.JSONDecodeError as e:
            logger.debug(f"⚠️ Erreur parsing JSON: {e}")
            logger.debug(f"Contenu problématique: {content[:100]}...")
            return {}
        except Exception as e:
            logger.warning(f"⚠️ Erreur inattendue parsing JSON: {e}")
            return {}

    def _regex_extract(self, question: str) -> Dict[str, Any]:
        """
        ✅ AMÉLIORATION: Extraction regex avec patterns configurables
        """
        ctx: Dict[str, Any] = {}
        
        for field, pattern in self.patterns.items():
            try:
                matches = re.findall(pattern, question, re.IGNORECASE | re.VERBOSE)
                if matches:
                    # Nettoyer les matches (supprimer les chaînes vides)
                    clean_matches = [m for m in matches if m and str(m).strip()]
                    if clean_matches:
                        ctx[field] = clean_matches[0] if len(clean_matches) == 1 else clean_matches
                        
            except re.error as e:
                logger.error(f"❌ Erreur regex pour le champ '{field}': {e}")
                continue
        
        logger.debug(f"📝 Extraction regex: {len(ctx)} champs trouvés")
        return ctx

    def get_available_fields(self) -> Dict[str, List[str]]:
        """
        ✅ NOUVELLE FONCTIONNALITÉ: Liste des champs disponibles
        Utile pour la documentation et les tests
        """
        return {
            "gpt_fields": self.gpt_fields.copy(),
            "regex_fields": list(self.patterns.keys()),
            "all_fields": list(set(self.gpt_fields) | set(self.patterns.keys()))
        }

    def validate_patterns(self) -> Dict[str, Any]:
        """
        ✅ NOUVELLE FONCTIONNALITÉ: Validation des patterns regex
        Détecte les patterns malformés
        """
        results = {
            "valid": [],
            "invalid": [],
            "warnings": []
        }
        
        for field, pattern in self.patterns.items():
            try:
                # Test de compilation
                re.compile(pattern, re.IGNORECASE | re.VERBOSE)
                results["valid"].append(field)
                
                # Vérification de patterns trop larges
                if len(pattern) < 10:
                    results["warnings"].append(f"{field}: pattern très court")
                    
            except re.error as e:
                results["invalid"].append(f"{field}: {str(e)}")
        
        return results

# ✅ NOUVELLE FONCTIONNALITÉ: Fonction utilitaire pour créer le fichier de configuration
def create_default_patterns_file(output_path: str = "extraction_patterns.json") -> bool:
    """
    Crée un fichier de configuration par défaut pour les patterns
    """
    try:
        extractor = ContextExtractor()
        config = {
            "version": "1.0",
            "description": "Patterns d'extraction pour ContextExtractor",
            "patterns": extractor._get_default_patterns(),
            "gpt_fields": extractor._get_gpt_fields()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Fichier patterns créé: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur création fichier patterns: {e}")
        return False

if __name__ == "__main__":
    # Script utilitaire pour créer le fichier de configuration
    create_default_patterns_file()