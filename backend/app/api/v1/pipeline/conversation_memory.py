# -*- coding: utf-8 -*-
"""
Conversation Memory - VERSION AVEC EXTRACTION GPT MULTILINGUE
Gestion de la mémoire conversationnelle avec support français/anglais
Extraction intelligente via GPT avec fallback regex
Compatible Digital Ocean App Platform
"""

import json
import os
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration App Platform (via variables d'environnement)
ENABLE_GPT_MULTILINGUAL = os.getenv("ENABLE_GPT_MULTILINGUAL", "true").lower() in ("1", "true", "yes")
USE_POSTGRES_MEMORY = os.getenv("USE_POSTGRES_MEMORY", "false").lower() in ("1", "true", "yes")

# Import des utilitaires OpenAI
try:
    from ..utils.openai_utils import safe_chat_completion
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI utils non disponibles, fallback regex seulement")

# Import PostgreSQL conditionnel
if USE_POSTGRES_MEMORY:
    try:
        from .postgres_memory import PostgresMemory
        POSTGRES_AVAILABLE = True
    except ImportError:
        POSTGRES_AVAILABLE = False
        logger.warning("PostgreSQL non disponible, utilisation mémoire locale")
else:
    POSTGRES_AVAILABLE = False

# =============================================================================
# EXTRACTION GPT MULTILINGUE
# =============================================================================

GPT_EXTRACTION_PROMPT = """Tu es un expert en extraction d'entités pour l'aviculture. 
Extrait UNIQUEMENT les informations présentes dans cette question.
Réponds en JSON valide avec les champs suivants (null si absent):

{
  "species": "broiler" ou "layer" ou "breeder",
  "line": "ross308" ou "cobb500" ou "isa_brown" etc.,
  "sex": "male" ou "female" ou "mixed" ou "as_hatched",
  "age_days": nombre en jours,
  "age_weeks": nombre en semaines,
  "phase": "starter" ou "grower" ou "finisher" etc.,
  "weight_g": poids en grammes,
  "flock_size": nombre d'oiseaux,
  "temperature_c": température celsius,
  "mortality_rate": taux mortalité %,
  "production_rate": taux ponte %,
  "problem_type": diagnostic/problème
}

RÈGLES CRITIQUES:
1. "18-day-old" → age_days: 18
2. "3-week-old" → age_weeks: 3, age_days: 21  
3. "poulet de chair" → species: "broiler"
4. "pondeuse" → species: "layer"
5. "Ross 308", "Cobb 500" → line: "ross308", "cobb500"
6. "mâle/male" → sex: "male"
7. "jour 14" → age_days: 14
8. "semaine 3" → age_weeks: 3

Question: """

def extract_entities_via_gpt(question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extraction d'entités via GPT - Support multilingue français/anglais
    """
    if not ENABLE_GPT_MULTILINGUAL or not OPENAI_AVAILABLE:
        return {}
        
    if not question or not question.strip():
        return {}
        
    try:
        full_prompt = GPT_EXTRACTION_PROMPT + f'"{question}"'
        
        response = safe_chat_completion(
            messages=[{"role": "user", "content": full_prompt}],
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=500
        )
        
        if not response or not response.get("choices"):
            logger.warning("[GPT_EXTRACT] Réponse GPT vide")
            return {}
            
        content = response["choices"][0]["message"]["content"].strip()
        logger.debug(f"[GPT_EXTRACT] Réponse brute: {content}")
        
        try:
            extracted = json.loads(content)
            if isinstance(extracted, dict):
                cleaned = _clean_gpt_entities(extracted)
                logger.info(f"[GPT_EXTRACT] Entités extraites: {cleaned}")
                return cleaned
            else:
                logger.warning("[GPT_EXTRACT] Réponse n'est pas un dict")
                return {}
                
        except json.JSONDecodeError as e:
            logger.warning(f"[GPT_EXTRACT] Erreur JSON: {e}")
            return {}
            
    except Exception as e:
        logger.error(f"[GPT_EXTRACT] Erreur: {e}")
        return {}

def _clean_gpt_entities(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Nettoie et valide les entités extraites par GPT"""
    cleaned = {}
    
    # Species validation
    if extracted.get("species") in ["broiler", "layer", "breeder"]:
        cleaned["species"] = extracted["species"]
        
    # Line normalization
    line = extracted.get("line")
    if line:
        line_clean = line.lower().replace(" ", "").replace("-", "")
        line_map = {
            "ross308": "ross308", "cobb500": "cobb500", "cobb700": "cobb700",
            "isabrown": "isa_brown", "lohmannbrown": "lohmann_brown",
            "hylinebrown": "hyline_brown", "hylinew36": "hyline_w36"
        }
        if line_clean in line_map:
            cleaned["line"] = line_map[line_clean]
            
    # Sex validation  
    if extracted.get("sex") in ["male", "female", "mixed", "as_hatched"]:
        cleaned["sex"] = extracted["sex"]
        
    # Age validation
    age_days = extracted.get("age_days")
    if age_days is not None:
        try:
            age_val = int(age_days)
            if 0 <= age_val <= 70:
                cleaned["age_days"] = age_val
        except (ValueError, TypeError):
            pass
            
    age_weeks = extracted.get("age_weeks")  
    if age_weeks is not None:
        try:
            weeks_val = float(age_weeks)
            if 0 <= weeks_val <= 100:
                cleaned["age_weeks"] = weeks_val
                if "age_days" not in cleaned:
                    cleaned["age_days"] = int(weeks_val * 7)
        except (ValueError, TypeError):
            pass
    
    # Autres champs numériques
    numeric_fields = {
        "weight_g": (0, 10000),
        "flock_size": (1, 1000000), 
        "temperature_c": (-20, 50),
        "mortality_rate": (0, 100),
        "production_rate": (0, 100)
    }
    
    for field, (min_val, max_val) in numeric_fields.items():
        value = extracted.get(field)
        if value is not None:
            try:
                num_val = float(value)
                if min_val <= num_val <= max_val:
                    cleaned[field] = num_val
            except (ValueError, TypeError):
                pass
    
    # Champs texte
    text_fields = ["phase", "problem_type"]
    for field in text_fields:
        value = extracted.get(field)
        if value and isinstance(value, str) and value.strip():
            cleaned[field] = value.strip()
    
    return cleaned

# =============================================================================
# EXTRACTION REGEX (FALLBACK)
# =============================================================================

# Patterns d'âge améliorés - priorité par spécificité
_AGE_PATTERNS = [
    # Priorité 1: Formats composés spécifiques (anglais)
    r"\b(\d{1,2})-day-old\b",                                    # 18-day-old
    r"\b(\d{1,2})-week-old\b",                                   # 3-week-old
    r"\b(\d{1,2})\s*day\s*old\b",                               # 18 day old
    r"\b(\d{1,2})\s*week\s*old\b",                              # 3 week old
    
    # Priorité 2: Formats français spécifiques
    r"\bâgés?\s*de\s*(\d{1,2})\s*(?:j|jours)\b",                # âgé de 18 jours
    r"\bâgés?\s*de\s*(\d{1,2})\s*(?:sem|semaines)\b",           # âgé de 3 semaines
    r"\b(?:âge|age)\s*[:=]?\s*(\d{1,2})\s*(?:j|jours|d|days)\b", # âge: 21 jours / age=21d
    
    # Priorité 3: Formats mixtes haute spécificité
    r"\bjour\s+(\d{1,2})\b",                                     # jour 14 (CRITIQUE)
    r"\bsemaine\s+(\d{1,2})\b",                                  # semaine 3
    r"\bweek\s+(\d{1,2})\b",                                     # week 3
    r"\bday\s+(\d{1,2})\b",                                      # day 21
    
    # Priorité 4: Formats techniques
    r"\b(?:J|D)(\d{1,2})\b",                                     # J14, D14 (sans espace)
    r"\b(?:J|D)\s*(\d{1,2})\b",                                  # J 14, D 14 (avec espace)
    r"\bage_days\s*[:=]\s*(\d{1,2})\b",                          # age_days=21
    
    # Priorité 5: Patterns génériques (moins précis)
    r"\b(\d{1,2})\s*(?:j|jours|d|days)\b",                       # 21 j / 21d
]

# Patterns pour les autres entités
_SEX_PATTERNS = [
    r"\b(male|mâle)\b",
    r"\b(female|femelle)\b", 
    r"\b(mixed|mixte|as[-_]hatched)\b"
]

_SPECIES_PATTERNS = [
    r"\b(broiler|poulet\s*de\s*chair)\b",
    r"\b(layer|pondeuse)\b",
    r"\b(breeder|reproducteur)\b"
]

_LINE_PATTERNS = [
    r"\b(ross\s*308|ross308)\b",
    r"\b(ross\s*708|ross708)\b",
    r"\b(cobb\s*500|cobb500)\b",
    r"\b(cobb\s*700|cobb700)\b",
    r"\b(isa\s*brown|isabrown)\b",
    r"\b(lohmann\s*brown|lohmannbrown)\b",
    r"\b(hyline\s*brown|hylinebrown)\b"
]

def extract_age_days_from_text(text: str) -> Optional[int]:
    """Extraction d'âge avec patterns améliorés français/anglais"""
    if not text:
        return None
    
    logger.debug(f"[AGE_EXTRACT] Analyse: '{text}'")
    
    for i, pattern in enumerate(_AGE_PATTERNS):
        match = re.search(pattern, text, flags=re.I)
        if match:
            try:
                age_val = int(match.group(1))
                logger.info(f"[AGE_EXTRACT] Pattern {i} trouvé: '{pattern}' -> âge={age_val}")
                if 0 <= age_val <= 70:
                    return age_val
                else:
                    logger.warning(f"[AGE_EXTRACT] Âge hors limites: {age_val}")
            except (ValueError, IndexError):
                continue
    
    logger.warning(f"[AGE_EXTRACT] Aucun âge détecté dans: '{text}'")
    return None

def normalize_sex_from_text(text: str) -> Optional[str]:
    """Extraction et normalisation du sexe"""
    if not text:
        return None
        
    text_lower = text.lower()
    
    if re.search(r"\b(male|mâle)\b", text_lower):
        return "male"
    elif re.search(r"\b(female|femelle)\b", text_lower):
        return "female"
    elif re.search(r"\b(mixed|mixte|as[-_]hatched)\b", text_lower):
        return "mixed"
    
    return None

def extract_line_from_text(text: str) -> Optional[str]:
    """Extraction de la lignée/souche"""
    if not text:
        return None
        
    text_lower = text.lower().replace(" ", "").replace("-", "")
    
    line_mapping = {
        "ross308": "ross308",
        "ross708": "ross708", 
        "cobb500": "cobb500",
        "cobb700": "cobb700",
        "isabrown": "isa_brown",
        "lohmannbrown": "lohmann_brown",
        "hylinebrown": "hyline_brown"
    }
    
    for pattern, normalized in line_mapping.items():
        if pattern in text_lower:
            return normalized
    
    return None

def extract_species_from_text(text: str) -> Optional[str]:
    """Extraction de l'espèce"""
    if not text:
        return None
        
    text_lower = text.lower()
    
    if re.search(r"\b(broiler|poulet\s*de\s*chair)\b", text_lower):
        return "broiler"
    elif re.search(r"\b(layer|pondeuse)\b", text_lower):
        return "layer"
    elif re.search(r"\b(breeder|reproducteur)\b", text_lower):
        return "breeder"
    
    return None

# =============================================================================
# GESTION DE LA MÉMOIRE CONVERSATIONNELLE
# =============================================================================

# Stockage en mémoire locale (fallback)
_local_memory: Dict[str, Dict[str, Any]] = {}

# Instance PostgreSQL
_postgres_memory: Optional['PostgresMemory'] = None

def get_conversation_memory():
    """Retourne l'instance de mémoire (PostgreSQL ou locale)"""
    global _postgres_memory
    
    if POSTGRES_AVAILABLE and _postgres_memory is None:
        try:
            _postgres_memory = PostgresMemory()
            logger.info("Mémoire PostgreSQL initialisée")
        except Exception as e:
            logger.warning(f"Erreur init PostgreSQL: {e}")
            _postgres_memory = None
    
    return _postgres_memory if _postgres_memory else _local_memory

def merge_conversation_context(current_entities: Dict[str, Any], session_context: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Fusion intelligente du contexte conversationnel avec extraction GPT multilingue
    Point d'entrée principal pour l'extraction d'entités
    """
    logger.info("[MERGE] Début fusion avec extraction multilingue")
    
    # Extraction GPT en priorité
    gpt_entities = {}
    if ENABLE_GPT_MULTILINGUAL and OPENAI_AVAILABLE:
        try:
            gpt_entities = extract_entities_via_gpt(question, session_context.get("entities"))
            logger.info(f"[GPT_SUCCESS] Entités GPT: {gpt_entities}")
        except Exception as e:
            logger.warning(f"[GPT_FALLBACK] Erreur GPT, fallback regex: {e}")
    
    # Si GPT échoue, utiliser extraction regex
    if not gpt_entities:
        logger.info("[REGEX_FALLBACK] Utilisation patterns regex")
        gpt_entities = {
            "age_days": extract_age_days_from_text(question),
            "sex": normalize_sex_from_text(question), 
            "line": extract_line_from_text(question),
            "species": extract_species_from_text(question)
        }
        # Nettoyer les None
        gpt_entities = {k: v for k, v in gpt_entities.items() if v is not None}
    
    # Fusion avec priorité: GPT > session > current
    merged = dict(current_entities or {})
    session_entities = session_context.get("entities", {})
    
    # Appliquer GPT en priorité
    for key, value in gpt_entities.items():
        if value is not None:
            merged[key] = value
            logger.debug(f"[MERGE] {key}: GPT -> {value}")
    
    # Compléter avec session
    for key, value in session_entities.items():
        if key not in merged and value is not None:
            merged[key] = value
            logger.debug(f"[MERGE] {key}: Session -> {value}")
    
    # Assurer cohérence
    merged = _ensure_entity_consistency(merged)
    
    logger.info(f"[MERGE] Résultat final: {merged}")
    return merged

def _ensure_entity_consistency(entities: Dict[str, Any]) -> Dict[str, Any]:
    """Assure la cohérence métier des entités extraites"""
    
    # Auto-déduction species depuis line
    if not entities.get("species") and entities.get("line"):
        line = str(entities["line"]).lower()
        if any(x in line for x in ["ross", "cobb", "hubbard"]):
            entities["species"] = "broiler"
            logger.debug("[CONSISTENCY] Species déduite: broiler")
        elif any(x in line for x in ["isa", "lohmann", "hyline"]):
            entities["species"] = "layer"
            logger.debug("[CONSISTENCY] Species déduite: layer")
    
    # Conversion age_days <-> age_weeks
    if entities.get("age_days") and not entities.get("age_weeks"):
        entities["age_weeks"] = round(entities["age_days"] / 7, 1)
    elif entities.get("age_weeks") and not entities.get("age_days"):
        entities["age_days"] = int(entities["age_weeks"] * 7)
    
    # Phase auto-déduction
    if entities.get("age_days") and entities.get("species") and not entities.get("phase"):
        age_days = entities["age_days"]
        species = entities["species"]
        
        if species == "broiler":
            if age_days <= 10:
                entities["phase"] = "starter"
            elif age_days <= 24:
                entities["phase"] = "grower" 
            else:
                entities["phase"] = "finisher"
        elif species == "layer" and entities.get("age_weeks"):
            age_weeks = entities["age_weeks"]
            if age_weeks < 18:
                entities["phase"] = "pre_lay"
            elif age_weeks < 35:
                entities["phase"] = "peak"
            else:
                entities["phase"] = "post_peak"
    
    return entities

def should_continue_conversation(session_context: Dict[str, Any], current_intent) -> bool:
    """Détermine si on doit continuer une conversation en cours"""
    if not session_context:
        return False
    
    pending_intent = session_context.get("pending_intent")
    missing_fields = session_context.get("missing_fields", [])
    
    # Continue si même intention et champs manquants
    return (pending_intent == str(current_intent) and 
            missing_fields and 
            len(missing_fields) > 0)

def save_conversation_context(session_id: str, intent, entities: Dict[str, Any], question: str, missing_fields: List[str]) -> bool:
    """Sauvegarde le contexte conversationnel"""
    try:
        context = {
            "entities": entities,
            "pending_intent": str(intent),
            "missing_fields": missing_fields,
            "last_question": question,
            "timestamp": datetime.now().isoformat()
        }
        
        memory = get_conversation_memory()
        if isinstance(memory, dict):  # Mémoire locale
            memory[session_id] = context
        else:  # PostgreSQL
            memory.save_context(session_id, context)
        
        logger.info(f"[CONTEXT_SAVE] Session {session_id} sauvegardée")
        return True
        
    except Exception as e:
        logger.error(f"[CONTEXT_SAVE] Erreur: {e}")
        return False

def clear_conversation_context(session_id: str) -> bool:
    """Efface le contexte conversationnel"""
    try:
        memory = get_conversation_memory()
        if isinstance(memory, dict):  # Mémoire locale
            if session_id in memory:
                del memory[session_id]
        else:  # PostgreSQL
            memory.clear_context(session_id)
        
        logger.info(f"[CONTEXT_CLEAR] Session {session_id} effacée")
        return True
        
    except Exception as e:
        logger.error(f"[CONTEXT_CLEAR] Erreur: {e}")
        return False

# =============================================================================
# FONCTIONS DE TEST ET DEBUG
# =============================================================================

def test_multilingual_extraction() -> Dict[str, Any]:
    """Test complet de l'extraction multilingue"""
    test_cases = [
        # Cas problématique original
        ("What is the target weight for an 18-day-old male Cobb 500 chicken?", {
            "expected": {"species": "broiler", "line": "cobb500", "sex": "male", "age_days": 18}
        }),
        ("Quel est le poids cible d'un poulet Cobb 500 mâle de 18 jours ?", {
            "expected": {"species": "broiler", "line": "cobb500", "sex": "male", "age_days": 18}
        }),
        
        # Autres patterns
        ("Ross 308 females at 35 days old", {
            "expected": {"species": "broiler", "line": "ross308", "sex": "female", "age_days": 35}
        }),
        ("Mortalité 3% jour 14 chez Ross 308 femelles", {
            "expected": {"species": "broiler", "line": "ross308", "sex": "female", "age_days": 14, "mortality_rate": 3}
        }),
        ("Pondeuses ISA Brown 40 semaines, production 85%", {
            "expected": {"species": "layer", "line": "isa_brown", "age_weeks": 40, "production_rate": 85}
        })
    ]
    
    results = {}
    for i, (question, meta) in enumerate(test_cases):
        test_key = f"test_{i+1}"
        
        try:
            # Test GPT
            if ENABLE_GPT_MULTILINGUAL and OPENAI_AVAILABLE:
                gpt_result = extract_entities_via_gpt(question)
                gpt_success = bool(gpt_result)
            else:
                gpt_result = {}
                gpt_success = False
            
            # Test regex fallback
            regex_result = {
                "age_days": extract_age_days_from_text(question),
                "sex": normalize_sex_from_text(question),
                "line": extract_line_from_text(question),
                "species": extract_species_from_text(question)
            }
            regex_result = {k: v for k, v in regex_result.items() if v is not None}
            
            # Test fusion complète
            merged = merge_conversation_context({}, {}, question)
            
            results[test_key] = {
                "question": question,
                "expected": meta.get("expected", {}),
                "gpt_result": gpt_result,
                "gpt_success": gpt_success,
                "regex_result": regex_result,
                "merged_result": merged,
                "has_critical_fields": bool(merged.get("age_days") and merged.get("species"))
            }
            
        except Exception as e:
            results[test_key] = {
                "question": question,
                "error": str(e)
            }
    
    # Statistiques globales
    total_tests = len(test_cases)
    successful_tests = len([r for r in results.values() if r.get("has_critical_fields", False)])
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    return {
        "status": "completed",
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": success_rate,
        "gpt_enabled": ENABLE_GPT_MULTILINGUAL and OPENAI_AVAILABLE,
        "postgres_enabled": POSTGRES_AVAILABLE,
        "detailed_results": results
    }

def get_memory_status() -> Dict[str, Any]:
    """Status de la mémoire conversationnelle"""
    return {
        "version": "multilingual_gpt_enhanced",
        "gpt_extraction": {
            "enabled": ENABLE_GPT_MULTILINGUAL,
            "available": OPENAI_AVAILABLE
        },
        "memory_backend": {
            "postgres_enabled": USE_POSTGRES_MEMORY,
            "postgres_available": POSTGRES_AVAILABLE,
            "current_backend": "postgres" if POSTGRES_AVAILABLE else "local"
        },
        "features": [
            "extraction_multilingue",
            "fallback_regex_automatique", 
            "coherence_entites_automatique",
            "contexte_conversationnel",
            "auto_deduction_species_phase"
        ]
    }

def debug_text_extraction(text: str) -> Dict[str, Any]:
    """Debug complet de l'extraction pour une question"""
    logger.info(f"[DEBUG] Test extraction sur: '{text}'")
    
    results = {
        "text": text,
        "gpt_extraction": {},
        "regex_extraction": {},
        "merged_result": {}
    }
    
    try:
        # Test GPT
        if ENABLE_GPT_MULTILINGUAL and OPENAI_AVAILABLE:
            results["gpt_extraction"] = extract_entities_via_gpt(text)
        
        # Test regex
        results["regex_extraction"] = {
            "age_days": extract_age_days_from_text(text),
            "species": extract_species_from_text(text),
            "line": extract_line_from_text(text),
            "sex": normalize_sex_from_text(text)
        }
        
        # Test fusion
        results["merged_result"] = merge_conversation_context({}, {}, text)
        
    except Exception as e:
        results["error"] = str(e)
    
    logger.info(f"[DEBUG] Résultats: {results}")
    return results