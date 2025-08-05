"""
app/api/v1/expert_services_utils.py - FONCTIONS UTILITAIRES EXPERT SYSTEM

🚀 FONCTIONS UTILITAIRES EXTRAITES v4.0.0:
1. ✅ Fonctions d'accès sécurisé weight
2. ✅ Fonctions d'accès sécurisé missing_entities  
3. ✅ Fonctions de gestion robuste erreurs mémoire
4. ✅ Fonctions de vérification champs avant ajout
"""

import logging
import re
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# =============================================================================
# 🚀 FONCTIONS UTILITAIRES POUR ACCÈS SÉCURISÉ WEIGHT
# =============================================================================

def safe_get_weight(entities, default=None):
    """⚖️ ACCÈS SÉCURISÉ AU POIDS"""
    try:
        if entities is None:
            return default
        
        # Si entities est un dictionnaire
        if isinstance(entities, dict):
            weight_value = entities.get('weight', default)
        # Si entities est un objet avec attributs
        elif hasattr(entities, '__dict__'):
            weight_value = getattr(entities, 'weight', default)
        else:
            weight_value = default
        
        logger.debug(f"⚖️ [Safe Weight v4.0.0] Récupéré: {weight_value} (type: {type(weight_value)})")
        return weight_value
        
    except Exception as e:
        logger.error(f"❌ [Safe Weight v4.0.0] Erreur accès weight: {e}")
        return default

def safe_get_weight_unit(entities, default="g"):
    """⚖️ ACCÈS SÉCURISÉ À L'UNITÉ DE POIDS"""
    try:
        if entities is None:
            return default
        
        if isinstance(entities, dict):
            unit_value = entities.get('weight_unit', default)
        elif hasattr(entities, '__dict__'):
            unit_value = getattr(entities, 'weight_unit', default)
        else:
            unit_value = default
        
        return unit_value
        
    except Exception as e:
        logger.error(f"❌ [Safe Weight Unit v4.0.0] Erreur: {e}")
        return default

def validate_and_normalize_weight(weight_value, unit="g"):
    """⚖️ VALIDATION ET NORMALISATION DU POIDS"""
    try:
        if weight_value is None:
            return {"value": None, "unit": unit, "is_valid": False, "error": "Valeur None"}
        
        # Conversion en float si possible
        if isinstance(weight_value, str):
            try:
                # Remplacer virgule par point pour les locales françaises
                normalized_str = str(weight_value).replace(',', '.').strip()
                weight_float = float(normalized_str)
            except (ValueError, TypeError) as e:
                return {"value": None, "unit": unit, "is_valid": False, "error": f"Conversion impossible: {e}"}
        elif isinstance(weight_value, (int, float)):
            weight_float = float(weight_value)
        else:
            return {"value": None, "unit": unit, "is_valid": False, "error": f"Type non supporté: {type(weight_value)}"}
        
        # Validation des valeurs sensées
        if weight_float < 0:
            return {"value": weight_float, "unit": unit, "is_valid": False, "error": "Poids négatif"}
        elif weight_float > 100000:  # 100kg max pour éviter les erreurs
            return {"value": weight_float, "unit": unit, "is_valid": False, "error": "Poids trop élevé"}
        
        return {"value": weight_float, "unit": unit, "is_valid": True, "error": None}
        
    except Exception as e:
        logger.error(f"❌ [Validate Weight v4.0.0] Erreur: {e}")
        return {"value": None, "unit": unit, "is_valid": False, "error": str(e)}

def extract_weight_from_text_safe(text, language="fr"):
    """⚖️ EXTRACTION SÉCURISÉE DU POIDS DEPUIS TEXTE"""
    try:
        if not text or not isinstance(text, str):
            return {"weight": None, "unit": None, "confidence": 0.0}
        
        text_lower = text.lower()
        
        # Patterns pour détecter poids + unité
        weight_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(g|grammes?|kg|kilogrammes?|pounds?|lbs?)',
            r'(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'poids.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'weight.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)',
            r'peso.*?(\d+(?:[.,]\d+)?)\s*(g|kg|lb)'
        ]
        
        for pattern in weight_patterns:
            try:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    # Prendre la première occurrence
                    weight_str, unit = matches[0]
                    
                    # Validation du poids
                    weight_result = validate_and_normalize_weight(weight_str, unit)
                    
                    if weight_result["is_valid"]:
                        return {
                            "weight": weight_result["value"],
                            "unit": weight_result["unit"],
                            "confidence": 0.8
                        }
            except Exception as e:
                logger.warning(f"⚠️ [Extract Weight v4.0.0] Erreur pattern: {e}")
                continue
        
        return {"weight": None, "unit": None, "confidence": 0.0}
        
    except Exception as e:
        logger.error(f"❌ [Extract Weight Text v4.0.0] Erreur: {e}")
        return {"weight": None, "unit": None, "confidence": 0.0}

# =============================================================================
# 🚀 FONCTIONS UTILITAIRES POUR ACCÈS SÉCURISÉ missing_entities
# =============================================================================

def safe_get_missing_entities(source_object, default_value=None):
    """🔒 ACCÈS SÉCURISÉ AUX missing_entities"""
    if default_value is None:
        default_value = []
    
    try:
        if source_object is None:
            return default_value
        
        # Si c'est un dictionnaire
        if isinstance(source_object, dict):
            missing = source_object.get('missing_entities', default_value)
        # Si c'est un objet avec attributs
        elif hasattr(source_object, 'missing_entities'):
            missing = getattr(source_object, 'missing_entities', default_value)
        # Si c'est un objet avec méthode get_missing_entities
        elif hasattr(source_object, 'get_missing_entities'):
            try:
                missing = source_object.get_missing_entities()
            except Exception as e:
                logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Erreur get_missing_entities(): {e}")
                missing = default_value
        else:
            missing = default_value
        
        # Validation du type
        if not isinstance(missing, list):
            logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Type invalide: {type(missing)}, conversion en liste")
            if missing is None:
                return default_value
            elif isinstance(missing, (str, int, float)):
                return [str(missing)]
            else:
                return default_value
        
        # Nettoyage de la liste
        cleaned_missing = []
        for item in missing:
            try:
                if item and isinstance(item, str):
                    cleaned_missing.append(item.strip())
                elif item:
                    cleaned_missing.append(str(item))
            except Exception as e:
                logger.warning(f"⚠️ [Safe Missing Entities v4.0.0] Item invalide ignoré: {item}, erreur: {e}")
                continue
        
        return cleaned_missing
        
    except Exception as e:
        logger.error(f"❌ [Safe Missing Entities v4.0.0] Erreur critique: {e}")
        return default_value

def safe_update_missing_entities(target_dict, missing_entities, key="missing_entities"):
    """🔒 MISE À JOUR SÉCURISÉE missing_entities dans un dictionnaire"""
    try:
        if not isinstance(target_dict, dict):
            logger.warning("⚠️ [Safe Update v4.0.0] Target n'est pas un dict")
            return False
        
        safe_missing = safe_get_missing_entities({"missing_entities": missing_entities})
        target_dict[key] = safe_missing
        return True
        
    except Exception as e:
        logger.error(f"❌ [Safe Update Missing v4.0.0] Erreur: {e}")
        return False

def validate_missing_entities_list(missing_entities):
    """🔒 VALIDATION D'UNE LISTE missing_entities"""
    try:
        if not isinstance(missing_entities, list):
            return []
        
        validated = []
        for item in missing_entities:
            if item and isinstance(item, str) and item.strip():
                validated.append(item.strip())
            elif item and not isinstance(item, str):
                try:
                    validated.append(str(item).strip())
                except Exception:
                    continue
        
        return validated
        
    except Exception as e:
        logger.error(f"❌ [Validate Missing Entities v4.0.0] Erreur: {e}")
        return []

# =============================================================================
# 🚀 NOUVELLES FONCTIONS POUR GESTION ROBUSTE ERREURS MÉMOIRE v4.0.0
# =============================================================================

def safe_get_conversation_context(conversation_memory, conversation_id):
    """
    🧠 RÉCUPÉRATION SÉCURISÉE DU CONTEXTE CONVERSATIONNEL - NOUVEAU v4.0.0
    
    Récupère le contexte conversationnel en gérant toutes les erreurs possibles
    pour éviter que les erreurs de mémoire bloquent le pipeline
    """
    try:
        if not conversation_memory:
            logger.debug("🧠 [Safe Context v4.0.0] Mémoire conversationnelle non disponible")
            return None
        
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Context v4.0.0] Conversation ID invalide: {conversation_id}")
            return None
        
        # Tentative récupération contexte avec gestion d'erreurs
        context = conversation_memory.get_conversation_context(conversation_id)
        
        if context is None:
            logger.debug(f"🧠 [Safe Context v4.0.0] Pas de contexte pour: {conversation_id}")
            return None
        
        logger.info(f"✅ [Safe Context v4.0.0] Contexte récupéré: {conversation_id}")
        return context
        
    except AttributeError as e:
        logger.warning(f"⚠️ [Safe Context v4.0.0] Méthode manquante: {e}")
        return None
    except TypeError as e:
        logger.warning(f"⚠️ [Safe Context v4.0.0] Type invalide: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ [Safe Context v4.0.0] Erreur récupération contexte: {e}")
        return None

def safe_extract_entities_from_context(conversation_context):
    """
    🔍 EXTRACTION SÉCURISÉE DES ENTITÉS DEPUIS LE CONTEXTE - NOUVEAU v4.0.0
    
    Extrait les entités du contexte conversationnel en gérant tous les cas d'erreur
    """
    try:
        if not conversation_context:
            logger.debug("🔍 [Safe Extract v4.0.0] Pas de contexte fourni")
            return {}, []
        
        # Accès sécurisé aux entités consolidées
        entities = {}
        missing_entities = []
        
        # Extraction des entités consolidées
        if hasattr(conversation_context, 'consolidated_entities'):
            try:
                entities_raw = conversation_context.consolidated_entities
                
                # Vérification hasattr avant conversion
                if hasattr(entities_raw, 'to_dict') and callable(getattr(entities_raw, 'to_dict')):
                    entities = entities_raw.to_dict()
                elif isinstance(entities_raw, dict):
                    entities = entities_raw.copy()
                elif hasattr(entities_raw, '__dict__'):
                    entities = entities_raw.__dict__.copy()
                else:
                    logger.warning(f"⚠️ [Safe Extract v4.0.0] Type entities inconnu: {type(entities_raw)}")
                    entities = {}
                
                logger.debug(f"🔍 [Safe Extract v4.0.0] Entités extraites: {len(entities)} éléments")
                
            except Exception as e:
                logger.warning(f"⚠️ [Safe Extract v4.0.0] Erreur extraction entités: {e}")
                entities = {}
        
        # Extraction sécurisée missing_entities
        if hasattr(conversation_context, 'get_missing_entities'):
            try:
                raw_missing = conversation_context.get_missing_entities()
                missing_entities = safe_get_missing_entities({"missing_entities": raw_missing})
                logger.debug(f"🔍 [Safe Extract v4.0.0] Missing entities: {len(missing_entities)} éléments")
            except Exception as e:
                logger.warning(f"⚠️ [Safe Extract v4.0.0] Erreur extraction missing_entities: {e}")
                missing_entities = []
        
        return entities, missing_entities
        
    except Exception as e:
        logger.error(f"❌ [Safe Extract v4.0.0] Erreur critique extraction: {e}")
        return {}, []

async def safe_add_message_to_memory(conversation_memory, conversation_id, user_id, message, role, language):
    """
    💾 AJOUT SÉCURISÉ DE MESSAGE À LA MÉMOIRE - NOUVEAU v4.0.0
    
    Ajoute un message à la mémoire conversationnelle sans bloquer le pipeline
    en cas d'erreur
    """
    try:
        if not conversation_memory:
            logger.debug("💾 [Safe Memory Add v4.0.0] Mémoire non disponible")
            return False
        
        # Validation des paramètres
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Conversation ID invalide: {conversation_id}")
            return False
        
        if not message or not isinstance(message, str):
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Message invalide: {message}")
            return False
        
        if role not in ['user', 'assistant']:
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Role invalide: {role}")
            return False
        
        # Vérification méthode existe avant appel
        if not hasattr(conversation_memory, 'add_message_to_conversation'):
            logger.warning("⚠️ [Safe Memory Add v4.0.0] Méthode add_message_to_conversation manquante")
            return False
        
        # Tentative ajout avec gestion d'erreurs spécifique
        result = await conversation_memory.add_message_to_conversation(
            conversation_id=conversation_id,
            user_id=user_id or "unknown",
            message=message,
            role=role,
            language=language or "fr"
        )
        
        if result:
            logger.debug(f"✅ [Safe Memory Add v4.0.0] Message ajouté: {role} - {conversation_id}")
        else:
            logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Échec ajout (retour False): {conversation_id}")
        
        return bool(result)
        
    except AttributeError as e:
        logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Méthode manquante: {e}")
        return False
    except TypeError as e:
        logger.warning(f"⚠️ [Safe Memory Add v4.0.0] Paramètre invalide: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ [Safe Memory Add v4.0.0] Erreur ajout mémoire: {e}")
        return False

def safe_mark_pending_clarification(conversation_memory, conversation_id, question, critical_entities):
    """
    🛑 MARQUAGE SÉCURISÉ CLARIFICATION PENDANTE - NOUVEAU v4.0.0
    
    Marque une clarification pendante sans bloquer le pipeline
    """
    try:
        if not conversation_memory:
            logger.debug("🛑 [Safe Mark v4.0.0] Mémoire non disponible")
            return False
        
        # Validation paramètres
        if not conversation_id or not isinstance(conversation_id, str):
            logger.warning(f"⚠️ [Safe Mark v4.0.0] Conversation ID invalide: {conversation_id}")
            return False
        
        # Validation missing_entities avec safe_get_missing_entities
        safe_critical_entities = safe_get_missing_entities({"missing_entities": critical_entities})
        
        if not safe_critical_entities:
            logger.warning("⚠️ [Safe Mark v4.0.0] Pas d'entités critiques à marquer")
            return False
        
        # Vérification méthode existe
        if not hasattr(conversation_memory, 'mark_pending_clarification'):
            logger.warning("⚠️ [Safe Mark v4.0.0] Méthode mark_pending_clarification manquante")
            return False
        
        # Tentative marquage
        result = conversation_memory.mark_pending_clarification(
            conversation_id, question, safe_critical_entities
        )
        
        if result:
            logger.info(f"🛑 [Safe Mark v4.0.0] Clarification marquée: {safe_critical_entities}")
        else:
            logger.warning(f"⚠️ [Safe Mark v4.0.0] Échec marquage: {conversation_id}")
        
        return bool(result)
        
    except Exception as e:
        logger.error(f"❌ [Safe Mark v4.0.0] Erreur marquage clarification: {e}")
        return False

# =============================================================================
# 🔧 NOUVELLES FONCTIONS POUR VÉRIFICATION CHAMPS AVANT AJOUT v4.0.0
# =============================================================================

def safe_set_field_if_exists(obj, field_name, value, log_prefix="Safe Set"):
    """
    🔧 ASSIGNATION SÉCURISÉE DE CHAMP - NOUVEAU v4.0.0
    
    Assigne une valeur à un champ seulement s'il existe dans l'objet
    
    Args:
        obj: Objet cible
        field_name: Nom du champ
        value: Valeur à assigner
        log_prefix: Préfixe pour logs
    
    Returns:
        bool: True si assignation réussie, False sinon
    """
    try:
        if obj is None:
            logger.debug(f"🔧 [{log_prefix} v4.0.0] Objet None pour champ {field_name}")
            return False
        
        # Vérification hasattr avant assignation
        if hasattr(obj, field_name):
            setattr(obj, field_name, value)
            logger.debug(f"✅ [{log_prefix} v4.0.0] Champ {field_name} assigné")
            return True
        else:
            logger.debug(f"⚠️ [{log_prefix} v4.0.0] Champ {field_name} n'existe pas dans {type(obj)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ [{log_prefix} v4.0.0] Erreur assignation {field_name}: {e}")
        return False

def safe_get_field_if_exists(obj, field_name, default=None, log_prefix="Safe Get"):
    """
    🔍 RÉCUPÉRATION SÉCURISÉE DE CHAMP - NOUVEAU v4.0.0
    
    Récupère la valeur d'un champ seulement s'il existe dans l'objet
    """
    try:
        if obj is None:
            return default
        
        # hasattr avant getattr
        if hasattr(obj, field_name):
            value = getattr(obj, field_name, default)
            logger.debug(f"✅ [{log_prefix} v4.0.0] Champ {field_name} récupéré: {type(value)}")
            return value
        else:
            logger.debug(f"⚠️ [{log_prefix} v4.0.0] Champ {field_name} n'existe pas")
            return default
        
    except Exception as e:
        logger.error(f"❌ [{log_prefix} v4.0.0] Erreur récupération {field_name}: {e}")
        return default

def validate_response_object_compatibility(response_obj, required_fields=None):
    """
    🔍 VALIDATION COMPATIBILITÉ OBJET RÉPONSE - NOUVEAU v4.0.0
    
    Valide qu'un objet réponse est compatible avec les champs attendus
    """
    try:
        if response_obj is None:
            logger.warning("⚠️ [Validate Response v4.0.0] Objet réponse None")
            return False
        
        if required_fields is None:
            # Champs selon expert_models.py
            required_fields = [
                'question', 'response', 'conversation_id', 'rag_used', 
                'timestamp', 'language', 'response_time_ms', 'mode'
            ]
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(response_obj, field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"⚠️ [Validate Response v4.0.0] Champs manquants: {missing_fields}")
            return False
        
        logger.debug(f"✅ [Validate Response v4.0.0] Objet compatible: {type(response_obj)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ [Validate Response v4.0.0] Erreur validation: {e}")
        return False