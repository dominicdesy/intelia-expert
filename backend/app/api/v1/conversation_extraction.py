"""
app/api/v1/conversation_extraction.py - Extraction d'entités et logique IA

🔧 MODULE 2/3: Extraction intelligente d'entités avec OpenAI et fallback - VERSION TYPAGE FORCÉ
✅ Extraction OpenAI avec prompts optimisés
✅ Fallback robuste sans dépendances
✅ Gestion d'erreurs complète
✅ CORRECTION CRITIQUE: Typage forcé str → int/float dans toute l'extraction
✅ Protection complète contre les erreurs de comparaison str/int
✅ Validation renforcée avec coercition de types obligatoire
"""

import os
import json
import logging
import re
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import OpenAI sécurisé pour extraction intelligente
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

from .conversation_entities import IntelligentEntities, IntelligentConversationContext, safe_int_conversion, safe_float_conversion, force_type_coercion

logger = logging.getLogger(__name__)

class ConversationEntityExtractor:
    """Extracteur d'entités conversationnelles avec IA et fallback robuste - VERSION TYPAGE FORCÉ"""
    
    def __init__(self):
        self.ai_enhancement_enabled = os.getenv('AI_ENHANCEMENT_ENABLED', 'true').lower() == 'true'
        self.ai_enhancement_model = os.getenv('AI_ENHANCEMENT_MODEL', 'gpt-4o-mini')
        self.ai_enhancement_timeout = int(os.getenv('AI_ENHANCEMENT_TIMEOUT', '15'))
        
        logger.info(f"🤖 [Extractor] Initialisé - IA: {'✅' if self.ai_enhancement_enabled else '❌'}")

    async def extract_entities_ai_enhanced(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """🔧 CORRECTION TYPAGE: Extraction d'entités avec fallback robuste et COERCITION OBLIGATOIRE"""
        
        # Tentative IA si disponible
        if self.ai_enhancement_enabled and OPENAI_AVAILABLE and openai:
            try:
                entities = await self._extract_entities_openai_safe(message, language, conversation_context)
                if entities and entities.confidence_overall > 0.3:
                    # 🔧 CORRECTION CRITIQUE: FORCER les types après extraction IA
                    entities._force_all_numeric_types()
                    return entities.validate_and_correct_safe()
            except Exception as e:
                logger.warning(f"⚠️ [AI Extraction] Échec IA: {e}")
        
        # 🔧 FIX 7: Fallback robuste sans dépendances manquantes + TYPAGE FORCÉ
        logger.info("🔄 [Fallback] Utilisation extraction basique robuste avec typage forcé")
        try:
            entities = await self._extract_entities_basic_robust_safe(message, language)
            entities.extraction_method = "fallback_robust"
            # 🔧 CORRECTION CRITIQUE: FORCER les types après extraction fallback
            entities._force_all_numeric_types()
            return entities.validate_and_correct_safe()
        except Exception as fallback_error:
            logger.error(f"❌ [Fallback] Échec fallback: {fallback_error}")
            # Fallback ultime: entités vides mais valides avec types corrects
            empty_entities = IntelligentEntities(
                extraction_method="empty_fallback",
                extraction_success=False,
                confidence_overall=0.0
            )
            empty_entities._force_all_numeric_types()
            return empty_entities

    async def _extract_entities_openai_safe(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """🔧 EXTRACTION OpenAI SÉCURISÉE avec COERCITION DE TYPES obligatoire"""
        
        try:
            entities = await self._extract_entities_openai(message, language, conversation_context)
            # 🔧 CORRECTION CRITIQUE: FORCER les types après extraction OpenAI
            entities._force_all_numeric_types()
            return entities
        except Exception as e:
            logger.error(f"❌ [OpenAI Safe] Erreur extraction OpenAI: {e}")
            # Retourner entités vides mais valides avec types corrects
            empty_entities = IntelligentEntities(
                extraction_method="openai_failed",
                extraction_success=False,
                confidence_overall=0.0
            )
            empty_entities._force_all_numeric_types()
            return empty_entities

    async def _extract_entities_openai(
        self, 
        message: str, 
        language: str = "fr",
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> IntelligentEntities:
        """Extraction d'entités par OpenAI avec VALIDATION DE TYPES renforcée"""
        
        # Contexte pour l'IA avec gestion sécurisée
        context_info = ""
        if conversation_context and conversation_context.consolidated_entities:
            try:
                existing_entities = conversation_context.consolidated_entities.to_dict_safe()
                if existing_entities and not existing_entities.get('error'):
                    context_info = f"\n\nEntités déjà connues:\n{json.dumps(existing_entities, ensure_ascii=False, indent=2)}"
            except Exception as context_error:
                logger.warning(f"⚠️ [OpenAI] Erreur génération contexte: {context_error}")
                context_info = ""
        
        extraction_prompt = f"""Tu es un expert en extraction d'informations vétérinaires pour l'aviculture. Analyse ce message et extrait TOUTES les informations pertinentes.

Message: "{message}"{context_info}

INSTRUCTIONS CRITIQUES:
1. Extrait toutes les informations, même partielles ou implicites
2. Utilise le contexte existant pour éviter les doublons
3. Assigne des scores de confiance (0.0 à 1.0) basés sur la précision
4. Inférer des informations logiques (ex: si "mes poulets Ross 308", alors breed_type="specific")
5. Convertir automatiquement les unités (semaines -> jours, kg -> grammes)
6. IMPORTANT: Détecte le SEXE avec variations multilingues
7. POIDS: Toujours en grammes (weight ET weight_grams synchronisés)
8. ⚠️ CRITIQUE: Renvoie UNIQUEMENT des NOMBRES pour les champs numériques (pas de texte)

SEXES SUPPORTÉS:
- FR: mâles, mâle, femelles, femelle, mixte, troupeau mixte, coqs, poules
- EN: males, male, females, female, mixed, mixed flock, roosters, hens  
- ES: machos, macho, hembras, hembra, mixto, lote mixto, gallos, gallinas

VALIDATION TYPAGE - TRÈS IMPORTANT:
- age, age_days, flock_size: ENTIERS UNIQUEMENT (exemple: 25, pas "25")
- weight, weight_grams, temperature, mortality_rate: NOMBRES DÉCIMAUX (exemple: 800.0, pas "800g")
- Tous les _confidence: NOMBRES entre 0.0 et 1.0

Réponds UNIQUEMENT avec ce JSON exact avec TYPES CORRECTS:
```json
{{
  "breed": "race_détectée_ou_null",
  "breed_confidence": 0.8,
  "breed_type": "specific",
  
  "sex": "sexe_détecté_ou_null", 
  "sex_confidence": 0.9,
  
  "age": 25,
  "age_days": 25,
  "age_weeks": 3.6,
  "age_confidence": 0.8,
  
  "weight": 800.0,
  "weight_grams": 800.0,
  "weight_confidence": 0.7,
  "expected_weight_range": [750.0, 850.0],
  "growth_rate": "normal",
  
  "mortality_rate": 2.5,
  "mortality_confidence": 0.6,
  "symptoms": ["symptôme1", "symptôme2"],
  "health_status": "good",
  
  "temperature": 28.5,
  "humidity": 65.0,
  "housing_type": "type_ou_null",
  
  "feed_type": "type_ou_null",
  "flock_size": 1000,
  
  "problem_severity": "low",
  "intervention_urgency": "none",
  
  "extraction_method": "openai",
  "confidence_overall": 0.75
}}
```

EXEMPLES DE TYPES CORRECTS:
- "Ross 308 mâles 25 jours 800g" → age: 25, age_days: 25, weight: 800.0, weight_grams: 800.0
- "3 semaines" → age_weeks: 3.0, age_days: 21, age: 21
- "mortalité 2.5%" → mortality_rate: 2.5
- "10000 poulets" → flock_size: 10000
"""

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("Clé API OpenAI manquante")
        
        # Gestion d'erreurs spécifique OpenAI
        try:
            # Créer le client OpenAI
            client = openai.AsyncOpenAI(api_key=api_key)
            
            response = await client.chat.completions.create(
                model=self.ai_enhancement_model,
                messages=[
                    {"role": "system", "content": "Tu es un extracteur d'entités expert en aviculture. Réponds UNIQUEMENT avec du JSON valide avec les types corrects (nombres pour les champs numériques)."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=800,
                timeout=self.ai_enhancement_timeout
            )
            
            answer = response.choices[0].message.content.strip()
            
        except asyncio.TimeoutError:
            raise Exception("Timeout lors de l'appel OpenAI")
        except Exception as e:
            raise Exception(f"Erreur OpenAI: {e}")
        
        # Extraire le JSON de manière sécurisée
        try:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', answer, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', answer, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise Exception("Pas de JSON trouvé dans la réponse IA")
        except Exception as json_extract_error:
            logger.error(f"❌ [OpenAI] Erreur extraction JSON: {json_extract_error}")
            raise Exception(f"Erreur extraction JSON: {json_extract_error}")
        
        # Parser et créer les entités avec VALIDATION DE TYPES RENFORCÉE
        try:
            data = json.loads(json_str)
            
            # 🔧 CORRECTION CRITIQUE: COERCITION FORCÉE de tous les types depuis JSON
            age_days_safe = safe_int_conversion(data.get("age_days") or data.get("age"))
            age_weeks_safe = safe_float_conversion(data.get("age_weeks"))
            weight_safe = safe_float_conversion(data.get("weight_grams") or data.get("weight"))
            
            # Validation expected_weight_range avec coercition
            expected_weight_range_safe = None
            if data.get("expected_weight_range") and isinstance(data["expected_weight_range"], list) and len(data["expected_weight_range"]) == 2:
                try:
                    range_min = safe_float_conversion(data["expected_weight_range"][0])
                    range_max = safe_float_conversion(data["expected_weight_range"][1])
                    if range_min is not None and range_max is not None:
                        expected_weight_range_safe = (range_min, range_max)
                except Exception as range_error:
                    logger.warning(f"⚠️ [OpenAI] Erreur conversion range poids: {range_error}")
            
            # 🔧 CONSTRUCTION avec COERCITION FORCÉE de TOUS les champs numériques
            try:
                entities = IntelligentEntities(
                    breed=str(data.get("breed")) if data.get("breed") else None,
                    breed_confidence=safe_float_conversion(data.get("breed_confidence")) or 0.0,
                    breed_type=str(data.get("breed_type")) if data.get("breed_type") else None,
                    
                    sex=str(data.get("sex")) if data.get("sex") else None,
                    sex_confidence=safe_float_conversion(data.get("sex_confidence")) or 0.0,
                    
                    # 🔧 COERCITION FORCÉE: Âge avec types validés
                    age=age_days_safe,
                    age_days=age_days_safe,
                    age_weeks=age_weeks_safe,
                    age_confidence=safe_float_conversion(data.get("age_confidence")) or 0.0,
                    age_last_updated=datetime.now(),
                    
                    # 🔧 COERCITION FORCÉE: Poids avec types validés
                    weight=weight_safe,
                    weight_grams=weight_safe,
                    weight_confidence=safe_float_conversion(data.get("weight_confidence")) or 0.0,
                    expected_weight_range=expected_weight_range_safe,
                    growth_rate=str(data.get("growth_rate")) if data.get("growth_rate") else None,
                    
                    # 🔧 COERCITION FORCÉE: Mortalité avec type validé
                    mortality_rate=safe_float_conversion(data.get("mortality_rate")),
                    mortality_confidence=safe_float_conversion(data.get("mortality_confidence")) or 0.0,
                    symptoms=data.get("symptoms", []) if isinstance(data.get("symptoms"), list) else [],
                    health_status=str(data.get("health_status")) if data.get("health_status") else None,
                    
                    # 🔧 COERCITION FORCÉE: Environnement avec types validés
                    temperature=safe_float_conversion(data.get("temperature")),
                    humidity=safe_float_conversion(data.get("humidity")),
                    housing_type=str(data.get("housing_type")) if data.get("housing_type") else None,
                    
                    # 🔧 COERCITION FORCÉE: Flock_size avec type validé
                    feed_type=str(data.get("feed_type")) if data.get("feed_type") else None,
                    flock_size=safe_int_conversion(data.get("flock_size")),
                    
                    problem_severity=str(data.get("problem_severity")) if data.get("problem_severity") else None,
                    intervention_urgency=str(data.get("intervention_urgency")) if data.get("intervention_urgency") else None,
                    
                    extraction_method="openai",
                    last_ai_update=datetime.now(),
                    confidence_overall=safe_float_conversion(data.get("confidence_overall")) or 0.0,
                    extraction_success=True
                )
                
                # 🔧 VALIDATION FINALE: FORCER tous les types après création
                entities._force_all_numeric_types()
                
                logger.info(f"✅ [OpenAI] Entités extraites avec coercition de types réussie")
                logger.debug(f"  🔢 Types validés: age={type(entities.age)}, weight={type(entities.weight)}, mortality_rate={type(entities.mortality_rate)}")
                
                return entities
                
            except Exception as entity_creation_error:
                logger.error(f"❌ [OpenAI] Erreur création entités: {entity_creation_error}")
                # Fallback: créer entités vides mais valides avec types corrects
                empty_entities = IntelligentEntities(
                    extraction_method="openai_creation_failed",
                    extraction_success=False,
                    confidence_overall=0.0
                )
                empty_entities._force_all_numeric_types()
                return empty_entities
            
        except json.JSONDecodeError as e:
            raise Exception(f"Erreur parsing JSON IA: {e}")

    async def _extract_entities_basic_robust_safe(self, message: str, language: str) -> IntelligentEntities:
        """🔧 EXTRACTION BASIQUE SÉCURISÉE avec COERCITION DE TYPES obligatoire"""
        
        try:
            entities = await self._extract_entities_basic_robust(message, language)
            # 🔧 CORRECTION CRITIQUE: FORCER les types après extraction basique
            entities._force_all_numeric_types()
            return entities
        except Exception as e:
            logger.error(f"❌ [Basic Safe] Erreur extraction basique: {e}")
            # Fallback entités vides mais valides avec types corrects
            empty_entities = IntelligentEntities(
                extraction_method="basic_failed",
                extraction_success=False,
                confidence_overall=0.0
            )
            empty_entities._force_all_numeric_types()
            return empty_entities

    async def _extract_entities_basic_robust(self, message: str, language: str) -> IntelligentEntities:
        """🔧 EXTRACTION BASIQUE avec COERCITION DE TYPES OBLIGATOIRE dès l'assignation"""
        
        try:
            entities = IntelligentEntities(extraction_method="basic_robust")
            message_lower = message.lower()
            
            # Race spécifique avec gestion d'erreurs
            specific_breeds = [
                r'ross\s*308', r'ross\s*708', r'cobb\s*500', r'cobb\s*700',
                r'hubbard\s*flex', r'arbor\s*acres'
            ]
            
            for pattern in specific_breeds:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        breed_found = match.group(0).strip().replace(' ', ' ').title()
                        
                        # 🔧 ASSIGNATION SÉCURISÉE avec validation hasattr + TYPE STRING
                        if hasattr(entities, 'breed'):
                            entities.breed = str(breed_found)
                        if hasattr(entities, 'breed_type'):
                            entities.breed_type = str("specific")
                        if hasattr(entities, 'breed_confidence'):
                            entities.breed_confidence = float(0.9)  # FORCER float
                        
                        logger.debug(f"🔍 [BasicRobust] Race spécifique détectée: {breed_found}")
                        break
                except Exception as breed_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur détection race: {breed_error}")
                    continue
            
            # EXTRACTION SEXE avec ASSIGNATION DE TYPE STRING forcé
            sex_patterns = {
                "fr": [
                    (r'\bmâles?\b', 'mâles'),
                    (r'\bmales?\b', 'mâles'),
                    (r'\bcoqs?\b', 'mâles'),
                    (r'\bfemelles?\b', 'femelles'),
                    (r'\bfemales?\b', 'femelles'),
                    (r'\bpoules?\b', 'femelles'),
                    (r'\bmixte\b', 'mixte'),
                    (r'\btroupeau\s+mixte\b', 'mixte')
                ],
                "en": [
                    (r'\bmales?\b', 'males'),
                    (r'\brooster\b', 'males'),
                    (r'\bfemales?\b', 'females'),
                    (r'\bhens?\b', 'females'),
                    (r'\bmixed?\b', 'mixed'),
                    (r'\bmixed\s+flock\b', 'mixed')
                ],
                "es": [
                    (r'\bmachos?\b', 'machos'),
                    (r'\bgallos?\b', 'machos'),
                    (r'\bhembras?\b', 'hembras'),
                    (r'\bgallinas?\b', 'hembras'),
                    (r'\bmixto\b', 'mixto'),
                    (r'\blote\s+mixto\b', 'mixto')
                ]
            }
            
            patterns = sex_patterns.get(language, sex_patterns["fr"])
            
            for pattern, sex_name in patterns:
                try:
                    if re.search(pattern, message_lower, re.IGNORECASE):
                        # 🔧 ASSIGNATION avec TYPE STRING forcé
                        if hasattr(entities, 'sex'):
                            entities.sex = str(sex_name)
                        if hasattr(entities, 'sex_confidence'):
                            entities.sex_confidence = float(0.8)  # FORCER float
                        
                        logger.debug(f"🔍 [BasicRobust] Sexe détecté: {sex_name}")
                        break
                except Exception as sex_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur détection sexe: {sex_error}")
                    continue
            
            # 🔧 CORRECTION CRITIQUE: ÂGE avec COERCITION FORCÉE INT
            age_patterns = [
                (r'(\d+)\s*jours?', 1, "days"),
                (r'(\d+)\s*semaines?', 7, "weeks"),
                (r'(\d+)\s*days?', 1, "days"),
                (r'(\d+)\s*weeks?', 7, "weeks")
            ]
            
            for pattern, multiplier, unit in age_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        # 🔧 COERCITION FORCÉE: str → int obligatoire
                        value_raw = match.group(1)
                        value = safe_int_conversion(value_raw)
                        
                        if value is None:
                            logger.warning(f"⚠️ [BasicRobust] Impossible de convertir âge en int: {value_raw}")
                            continue
                        
                        if unit == "weeks":
                            age_weeks = float(value)  # FORCER float
                            age_days = int(value * 7)  # FORCER int
                        else:
                            age_days = int(value)  # FORCER int
                            age_weeks = round(value / 7, 1)  # CALCULER float
                        
                        # 🔧 ASSIGNATION avec TYPES FORCÉS
                        if hasattr(entities, 'age_weeks'):
                            entities.age_weeks = float(age_weeks)  # FORCER float
                        if hasattr(entities, 'age_days'):
                            entities.age_days = int(age_days)  # FORCER int
                        if hasattr(entities, 'age'):
                            entities.age = int(age_days)  # FORCER int
                        
                        # Validation âge réaliste avec confiance forcée float
                        if 0 < age_days <= 365:
                            if hasattr(entities, 'age_confidence'):
                                entities.age_confidence = float(0.8)  # FORCER float
                        else:
                            if hasattr(entities, 'age_confidence'):
                                entities.age_confidence = float(0.3)  # FORCER float
                        
                        if hasattr(entities, 'age_last_updated'):
                            entities.age_last_updated = datetime.now()
                        
                        logger.debug(f"🔍 [BasicRobust] Âge détecté avec types: {age_days}j (int), {age_weeks}sem (float)")
                        break
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [BasicRobust] Erreur conversion âge: {e}")
                    continue
                except Exception as age_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur générale âge: {age_error}")
                    continue
            
            # 🔧 CORRECTION CRITIQUE: POIDS avec COERCITION FORCÉE FLOAT
            weight_patterns = [
                (r'(\d+(?:\.\d+)?)\s*g\b', 1, "grams"),
                (r'(\d+(?:\.\d+)?)\s*kg', 1000, "kg"),
                (r'pèsent?\s+(\d+(?:\.\d+)?)', 1, "grams"),
                (r'weigh\s+(\d+(?:\.\d+)?)', 1, "grams")
            ]
            
            for pattern, multiplier, unit in weight_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        # 🔧 COERCITION FORCÉE: str → float obligatoire
                        weight_raw = match.group(1)
                        weight_value = safe_float_conversion(weight_raw)
                        
                        if weight_value is None:
                            logger.warning(f"⚠️ [BasicRobust] Impossible de convertir poids en float: {weight_raw}")
                            continue
                        
                        weight = float(weight_value * multiplier)  # FORCER float
                        
                        # Validation et correction automatique avec types forcés
                        if weight < 10:  # Probablement en kg
                            weight = float(weight * 1000)  # FORCER float
                            weight_confidence = float(0.7)  # FORCER float
                        elif weight > 10000:  # Trop élevé
                            weight_confidence = float(0.3)  # FORCER float
                        else:
                            weight_confidence = float(0.8)  # FORCER float
                        
                        # 🔧 ASSIGNATION avec TYPES FORCÉS float
                        if hasattr(entities, 'weight'):
                            entities.weight = float(weight)  # FORCER float
                        if hasattr(entities, 'weight_grams'):
                            entities.weight_grams = float(weight)  # FORCER float
                        if hasattr(entities, 'weight_confidence'):
                            entities.weight_confidence = float(weight_confidence)  # FORCER float
                        
                        logger.debug(f"🔍 [BasicRobust] Poids détecté avec type: {weight}g (float)")
                        break
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [BasicRobust] Erreur conversion poids: {e}")
                    continue
                except Exception as weight_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur générale poids: {weight_error}")
                    continue
            
            # 🔧 CORRECTION CRITIQUE: MORTALITÉ avec COERCITION FORCÉE FLOAT
            mortality_patterns = [
                r'mortalité.*?(\d+(?:\.\d+)?)%',
                r'mortality.*?(\d+(?:\.\d+)?)%',
                r'(\d+(?:\.\d+)?)%.*?mort'
            ]
            
            for pattern in mortality_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        # 🔧 COERCITION FORCÉE: str → float obligatoire
                        mortality_raw = match.group(1)
                        mortality_value = safe_float_conversion(mortality_raw)
                        
                        if mortality_value is not None and 0 <= mortality_value <= 100:
                            # 🔧 ASSIGNATION avec TYPE FORCÉ float
                            if hasattr(entities, 'mortality_rate'):
                                entities.mortality_rate = float(mortality_value)  # FORCER float
                            if hasattr(entities, 'mortality_confidence'):
                                entities.mortality_confidence = float(0.8)  # FORCER float
                            
                            logger.debug(f"🔍 [BasicRobust] Mortalité détectée avec type: {mortality_value}% (float)")
                            break
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [BasicRobust] Erreur conversion mortalité: {e}")
                    continue
                except Exception as mortality_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur générale mortalité: {mortality_error}")
                    continue
            
            # 🔧 CORRECTION CRITIQUE: TEMPÉRATURE avec COERCITION FORCÉE FLOAT
            temp_patterns = [
                r'température.*?(\d+(?:\.\d+)?)°?c',
                r'temperature.*?(\d+(?:\.\d+)?)°?c',
                r'(\d+(?:\.\d+)?)°c'
            ]
            
            for pattern in temp_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        # 🔧 COERCITION FORCÉE: str → float obligatoire
                        temp_raw = match.group(1)
                        temp_value = safe_float_conversion(temp_raw)
                        
                        if temp_value is not None and 10 <= temp_value <= 50:  # Plage réaliste
                            # 🔧 ASSIGNATION avec TYPE FORCÉ float
                            if hasattr(entities, 'temperature'):
                                entities.temperature = float(temp_value)  # FORCER float
                            
                            logger.debug(f"🔍 [BasicRobust] Température détectée avec type: {temp_value}°C (float)")
                            break
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [BasicRobust] Erreur conversion température: {e}")
                    continue
                except Exception as temp_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur générale température: {temp_error}")
                    continue
            
            # 🔧 CORRECTION CRITIQUE: FLOCK_SIZE avec COERCITION FORCÉE INT
            flock_patterns = [
                r'(\d+)\s*poulets?',
                r'(\d+)\s*birds?',
                r'troupeau.*?(\d+)',
                r'flock.*?(\d+)'
            ]
            
            for pattern in flock_patterns:
                try:
                    match = re.search(pattern, message_lower, re.IGNORECASE)
                    if match:
                        # 🔧 COERCITION FORCÉE: str → int obligatoire
                        flock_raw = match.group(1)
                        flock_value = safe_int_conversion(flock_raw)
                        
                        if flock_value is not None and flock_value > 0:
                            # 🔧 ASSIGNATION avec TYPE FORCÉ int
                            if hasattr(entities, 'flock_size'):
                                entities.flock_size = int(flock_value)  # FORCER int
                            
                            logger.debug(f"🔍 [BasicRobust] Taille troupeau détectée avec type: {flock_value} (int)")
                            break
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ [BasicRobust] Erreur conversion taille troupeau: {e}")
                    continue
                except Exception as flock_error:
                    logger.warning(f"⚠️ [BasicRobust] Erreur générale taille troupeau: {flock_error}")
                    continue
            
            # 🔧 CALCUL CONFIANCE GLOBALE avec COERCITION FORCÉE FLOAT
            try:
                confidence_scores = []
                
                # 🔧 ACCÈS SÉCURISÉ avec validation de type
                if hasattr(entities, 'breed_confidence') and isinstance(entities.breed_confidence, (int, float)) and entities.breed_confidence > 0:
                    confidence_scores.append(float(entities.breed_confidence))
                if hasattr(entities, 'sex_confidence') and isinstance(entities.sex_confidence, (int, float)) and entities.sex_confidence > 0:
                    confidence_scores.append(float(entities.sex_confidence))
                if hasattr(entities, 'age_confidence') and isinstance(entities.age_confidence, (int, float)) and entities.age_confidence > 0:
                    confidence_scores.append(float(entities.age_confidence))
                if hasattr(entities, 'weight_confidence') and isinstance(entities.weight_confidence, (int, float)) and entities.weight_confidence > 0:
                    confidence_scores.append(float(entities.weight_confidence))
                if hasattr(entities, 'mortality_confidence') and isinstance(entities.mortality_confidence, (int, float)) and entities.mortality_confidence > 0:
                    confidence_scores.append(float(entities.mortality_confidence))
                
                if confidence_scores:
                    overall_confidence = float(sum(confidence_scores) / len(confidence_scores))  # FORCER float
                else:
                    overall_confidence = float(0.0)  # FORCER float
                
                # 🔧 ASSIGNATION FINALE avec TYPES FORCÉS
                if hasattr(entities, 'confidence_overall'):
                    entities.confidence_overall = float(overall_confidence)  # FORCER float
                if hasattr(entities, 'extraction_success'):
                    entities.extraction_success = bool(overall_confidence > 0.1)  # FORCER bool
                
                logger.info(f"✅ [BasicRobust] Extraction terminée - Confiance globale: {overall_confidence} (float)")
                
            except Exception as confidence_error:
                logger.warning(f"⚠️ [BasicRobust] Erreur calcul confiance: {confidence_error}")
                # Fallback: confiance minimale avec types forcés
                if hasattr(entities, 'confidence_overall'):
                    entities.confidence_overall = float(0.0)  # FORCER float
                if hasattr(entities, 'extraction_success'):
                    entities.extraction_success = bool(False)  # FORCER bool
            
            # 🔧 VALIDATION FINALE: FORCER tous les types avant retour
            entities._force_all_numeric_types()
            
            return entities
            
        except Exception as e:
            logger.error(f"❌ [BasicRobust] Erreur globale extraction: {e}")
            # Fallback ultime: entités vides mais valides avec types corrects
            empty_entities = IntelligentEntities(
                extraction_method="basic_robust_failed",
                extraction_success=False,
                confidence_overall=0.0
            )
            empty_entities._force_all_numeric_types()
            return empty_entities


class ConversationClarificationHandler:
    """Gestionnaire de clarifications conversationnelles avec système d'enrichissement intelligent - VERSION TYPAGE SÉCURISÉ"""
    
    def __init__(self):
        logger.info("🔄 [ClarificationHandler] Système de clarification initialisé avec validation de types")
    
    def build_enriched_question_from_clarification(
        self,
        original_question: str,
        clarification_response: str,
        conversation_context: Optional[IntelligentConversationContext] = None
    ) -> str:
        """
        Enrichit la question originale avec la clarification de manière robuste - VERSION SÉCURISÉE
        
        Exemple:
        - Original: "Quel est le poids d'un poulet de 12 jours ?"
        - Clarification: "Ross 308 mâles"
        - Enrichi: "Quel est le poids d'un poulet Ross 308 mâle de 12 jours ?"
        """
        
        try:
            # Analyser la clarification pour extraire les entités
            clarification_lower = clarification_response.lower().strip()
            
            # Détection race avec gestion d'erreurs
            breed_info = self._extract_breed_from_clarification_safe(clarification_lower)
            sex_info = self._extract_sex_from_clarification_safe(clarification_lower)
            
            # Construire l'enrichissement
            enrichments = []
            
            if breed_info:
                enrichments.append(str(breed_info))  # FORCER string
            
            if sex_info:
                enrichments.append(str(sex_info))  # FORCER string
            
            # Intégrer dans la question originale
            if enrichments:
                enriched_question = self._integrate_enrichments_into_question_safe(
                    original_question, 
                    enrichments
                )
                
                logger.info(f"✅ [Clarification] Question enrichie réussie")
                logger.info(f"  📝 Original: {original_question}")
                logger.info(f"  🔁 Enrichi: {enriched_question}")
                
                return str(enriched_question)  # FORCER string
            else:
                # Fallback: concaténation simple avec types forcés
                fallback_question = f"{str(original_question)} Contexte: {str(clarification_response)}"
                logger.warning(f"⚠️ [Clarification] Fallback utilisé: {fallback_question}")
                return str(fallback_question)  # FORCER string
                
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur enrichissement: {e}")
            # Fallback ultime: question originale avec type forcé
            return str(original_question)  # FORCER string
    
    def _extract_breed_from_clarification_safe(self, clarification: str) -> Optional[str]:
        """🔧 EXTRACTION RACE SÉCURISÉE avec TYPE STRING forcé"""
        
        try:
            breed = self._extract_breed_from_clarification(clarification)
            return str(breed) if breed else None  # FORCER string
        except Exception as e:
            logger.warning(f"⚠️ [Clarification] Erreur extraction race: {e}")
            return None
    
    def _extract_breed_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait la race de la réponse de clarification avec TYPE STRING"""
        
        breed_patterns = [
            r'ross\s*308',
            r'ross\s*708', 
            r'cobb\s*500',
            r'cobb\s*700',
            r'hubbard\s*flex',
            r'arbor\s*acres'
        ]
        
        for pattern in breed_patterns:
            try:
                match = re.search(pattern, clarification, re.IGNORECASE)
                if match:
                    breed = str(match.group(0).strip().replace(' ', ' ').title())  # FORCER string
                    logger.debug(f"🔍 [Clarification] Race détectée: {breed}")
                    return breed
            except Exception as pattern_error:
                logger.warning(f"⚠️ [Clarification] Erreur pattern race: {pattern_error}")
                continue
        
        # Patterns génériques avec TYPE STRING
        generic_patterns = [
            r'poulets?\s+de\s+chair',
            r'broilers?',
            r'poulets?'
        ]
        
        for pattern in generic_patterns:
            try:
                if re.search(pattern, clarification, re.IGNORECASE):
                    logger.debug(f"🔍 [Clarification] Race générique détectée")
                    return str("poulets de chair")  # FORCER string
            except Exception as generic_error:
                logger.warning(f"⚠️ [Clarification] Erreur pattern générique: {generic_error}")
                continue
        
        return None
    
    def _extract_sex_from_clarification_safe(self, clarification: str) -> Optional[str]:
        """🔧 EXTRACTION SEXE SÉCURISÉE avec TYPE STRING forcé"""
        
        try:
            sex = self._extract_sex_from_clarification(clarification)
            return str(sex) if sex else None  # FORCER string
        except Exception as e:
            logger.warning(f"⚠️ [Clarification] Erreur extraction sexe: {e}")
            return None
    
    def _extract_sex_from_clarification(self, clarification: str) -> Optional[str]:
        """Extrait le sexe de la réponse de clarification avec TYPE STRING"""
        
        sex_patterns = [
            (r'\bmâles?\b', 'mâles'),
            (r'\bmales?\b', 'mâles'),
            (r'\bcoqs?\b', 'mâles'),
            (r'\bfemelles?\b', 'femelles'),
            (r'\bfemales?\b', 'femelles'),
            (r'\bpoules?\b', 'femelles'),
            (r'\bmixte\b', 'mixte'),
            (r'\btroupeau\s+mixte\b', 'mixte')
        ]
        
        for pattern, sex_name in sex_patterns:
            try:
                if re.search(pattern, clarification, re.IGNORECASE):
                    logger.debug(f"🔍 [Clarification] Sexe détecté: {sex_name}")
                    return str(sex_name)  # FORCER string
            except Exception as sex_error:
                logger.warning(f"⚠️ [Clarification] Erreur pattern sexe: {sex_error}")
                continue
        
        return None
    
    def _integrate_enrichments_into_question_safe(
        self, 
        original_question: str, 
        enrichments: list
    ) -> str:
        """🔧 INTÉGRATION ENRICHISSEMENTS SÉCURISÉE avec TYPES STRING forcés"""
        
        try:
            result = self._integrate_enrichments_into_question(original_question, enrichments)
            return str(result)  # FORCER string
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur intégration enrichissements: {e}")
            # Fallback: concaténation simple avec types forcés
            enrichment_text = ' '.join([str(e) for e in enrichments]) if enrichments else ""
            return str(f"{original_question} (Contexte: {enrichment_text})")  # FORCER string
    
    def _integrate_enrichments_into_question(
        self, 
        original_question: str, 
        enrichments: list
    ) -> str:
        """Intègre intelligemment les enrichissements dans la question avec TYPES STRING"""
        
        # Patterns de questions communes où insérer les enrichissements
        question_patterns = [
            # "Quel est le poids d'un poulet de X jours ?"
            (r'(quel\s+est\s+le\s+poids\s+d.un\s+)poulet(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            
            # "Mes poulets de X jours pèsent Y"
            (r'(mes\s+)poulets?(\s+de\s+\d+\s+jours?)',
             r'\1{} \2'),
            
            # "Comment nourrir des poulets de X semaines ?"
            (r'(comment\s+\w+\s+des\s+)poulets?(\s+de\s+\d+\s+semaines?)',
             r'\1{} \2'),
            
            # Pattern générique "poulet" → "poulet [race] [sexe]"
            (r'\bpoulets?\b',
             '{}')
        ]
        
        # 🔧 CONSTRUCTION ENRICHISSEMENT avec TYPES STRING forcés
        enrichment_text = ' '.join([str(e) for e in enrichments])  # FORCER string
        
        for pattern, replacement in question_patterns:
            try:
                if re.search(pattern, original_question, re.IGNORECASE):
                    enriched = re.sub(
                        pattern, 
                        replacement.format(enrichment_text),
                        original_question, 
                        flags=re.IGNORECASE
                    )
                    
                    # Nettoyer les espaces multiples et FORCER string
                    enriched = str(re.sub(r'\s+', ' ', enriched).strip())
                    
                    return enriched
            except Exception as pattern_error:
                logger.warning(f"⚠️ [Clarification] Erreur pattern intégration: {pattern_error}")
                continue
        
        # Fallback: ajout en contexte avec TYPE STRING forcé
        return str(f"{original_question} (Contexte: {enrichment_text})")
    
    def detect_clarification_state(
        self, 
        conversation_context: IntelligentConversationContext
    ) -> Tuple[bool, Optional[str]]:
        """
        Détecte si on est en attente de clarification - VERSION SÉCURISÉE avec TYPES forcés
        
        Returns:
            (is_awaiting_clarification, original_question_text) avec types forcés
        """
        
        try:
            # Vérifier l'état dans le contexte
            if hasattr(conversation_context, 'pending_clarification') and conversation_context.pending_clarification:
                try:
                    original_question_msg = conversation_context.find_original_question()
                    
                    if original_question_msg:
                        return bool(True), str(original_question_msg.message)  # FORCER bool + string
                except Exception as find_error:
                    logger.warning(f"⚠️ [Clarification] Erreur recherche question originale: {find_error}")
            
            # VÉRIFIER AUSSI L'ÉTAT CLARIFICATION CRITIQUE avec TYPES forcés
            if (hasattr(conversation_context, 'critical_clarification_active') and 
                conversation_context.critical_clarification_active and 
                hasattr(conversation_context, 'original_question_pending') and
                conversation_context.original_question_pending):
                
                return bool(True), str(conversation_context.original_question_pending)  # FORCER bool + string
            
            # Fallback: analyser les derniers messages
            try:
                if hasattr(conversation_context, 'messages') and len(conversation_context.messages) >= 2:
                    last_assistant_msg = None
                    
                    # Chercher le dernier message assistant
                    for msg in reversed(conversation_context.messages):
                        try:
                            if hasattr(msg, 'role') and msg.role == "assistant":
                                last_assistant_msg = msg
                                break
                        except Exception as msg_error:
                            logger.warning(f"⚠️ [Clarification] Erreur vérification message: {msg_error}")
                            continue
                    
                    if last_assistant_msg and hasattr(last_assistant_msg, 'message'):
                        # Mots-clés indiquant une demande de clarification
                        clarification_keywords = [
                            "j'ai besoin de", "pouvez-vous préciser", "quelle est la race",
                            "quel est le sexe", "de quelle race", "mâles ou femelles"
                        ]
                        
                        msg_lower = str(last_assistant_msg.message).lower()  # FORCER string
                        
                        if any(keyword in msg_lower for keyword in clarification_keywords):
                            # Chercher la question utilisateur précédente
                            try:
                                original_question = conversation_context.get_last_user_question()
                                
                                if original_question and hasattr(original_question, 'message'):
                                    return bool(True), str(original_question.message)  # FORCER bool + string
                            except Exception as user_question_error:
                                logger.warning(f"⚠️ [Clarification] Erreur recherche dernière question: {user_question_error}")
            except Exception as fallback_error:
                logger.warning(f"⚠️ [Clarification] Erreur analyse fallback: {fallback_error}")
            
            return bool(False), None  # FORCER bool
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur détection état: {e}")
            return bool(False), None  # FORCER bool

    def check_if_clarification_needed(
        self,
        question: str,
        rag_response: Any,
        context: Optional[IntelligentConversationContext],
        language: str = "fr"
    ) -> Tuple[bool, List[str]]:
        """Détermine si une clarification est nécessaire - VERSION SÉCURISÉE avec TYPES forcés"""
        
        try:
            if not context:
                return bool(False), []  # FORCER bool
            
            # Accès sécurisé aux entités
            if not hasattr(context, 'consolidated_entities'):
                return bool(False), []  # FORCER bool
            
            entities = context.consolidated_entities
            
            try:
                missing_info = entities.get_critical_missing_info()
            except Exception as missing_error:
                logger.warning(f"⚠️ [Clarification] Erreur get_critical_missing_info: {missing_error}")
                missing_info = []
            
            clarification_questions = []
            
            # Messages de clarification par langue avec TYPES STRING forcés
            clarification_messages = {
                "fr": {
                    "breed": str("De quelle race de poulets s'agit-il ? (ex: Ross 308, Cobb 500)"),
                    "sex": str("S'agit-il de mâles, femelles, ou d'un troupeau mixte ?"),
                    "age": str("Quel est l'âge de vos poulets ?")
                },
                "en": {
                    "breed": str("What breed of chickens are we talking about? (e.g., Ross 308, Cobb 500)"),
                    "sex": str("Are these males, females, or a mixed flock?"),
                    "age": str("How old are your chickens?")
                },
                "es": {
                    "breed": str("¿De qué raza de pollos estamos hablando? (ej: Ross 308, Cobb 500)"),
                    "sex": str("¿Son machos, hembras, o un lote mixto?"),
                    "age": str("¿Qué edad tienen sus pollos?")
                }
            }
            
            messages = clarification_messages.get(language, clarification_messages["fr"])
            
            # Race manquante ou générique
            if "breed" in missing_info:
                clarification_questions.append(str(messages["breed"]))  # FORCER string
            
            # Sexe manquant
            if "sex" in missing_info:
                clarification_questions.append(str(messages["sex"]))  # FORCER string
            
            # Âge manquant
            if "age" in missing_info:
                clarification_questions.append(str(messages["age"]))  # FORCER string
            
            # Au maximum 2 questions de clarification
            needs_clarification = bool(len(clarification_questions) > 0 and len(clarification_questions) <= 2)  # FORCER bool
            
            # S'assurer que toutes les questions sont des strings
            clarification_questions_safe = [str(q) for q in clarification_questions[:2]]
            
            return needs_clarification, clarification_questions_safe
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur check_if_clarification_needed: {e}")
            return bool(False), []  # FORCER bool

    def generate_clarification_request(
        self, 
        clarification_questions: List[str], 
        language: str = "fr"
    ) -> str:
        """Génère une demande de clarification naturelle - VERSION SÉCURISÉE avec TYPES forcés"""
        
        try:
            if not clarification_questions:
                fallback_messages = {
                    "fr": str("Pouvez-vous me donner plus de détails ?"),
                    "en": str("Can you give me more details?"),
                    "es": str("¿Puede darme más detalles?")
                }
                return str(fallback_messages.get(language, fallback_messages["fr"]))  # FORCER string
            
            intro_messages = {
                "fr": str("Pour vous donner une réponse plus précise, j'ai besoin de quelques informations supplémentaires :"),
                "en": str("To give you a more accurate answer, I need some additional information:"),
                "es": str("Para darle una respuesta más precisa, necesito información adicional:")
            }
            
            intro = str(intro_messages.get(language, intro_messages["fr"]))  # FORCER string
            
            try:
                # S'assurer que toutes les questions sont des strings
                questions_safe = [str(q) for q in clarification_questions]
                questions_text = str("\n".join([f"• {q}" for q in questions_safe]))  # FORCER string
            except Exception as questions_error:
                logger.warning(f"⚠️ [Clarification] Erreur formatage questions: {questions_error}")
                questions_text = str(clarification_questions)  # FORCER string
            
            result = str(f"{intro}\n\n{questions_text}")  # FORCER string
            return result
            
        except Exception as e:
            logger.error(f"❌ [Clarification] Erreur generate_clarification_request: {e}")
            return str("Pouvez-vous me donner plus de détails ?")  # FORCER string


# ===============================
# 🔧 RÉSUMÉ DES CORRECTIONS TYPAGE FORCÉ APPLIQUÉES
# ===============================

"""
🚨 CORRECTIONS TYPAGE FORCÉ APPLIQUÉES dans conversation_extraction.py:

CLASSE ConversationEntityExtractor - CORRECTIONS CRITIQUES:

✅ extract_entities_ai_enhanced()
  - Coercition forcée après extraction IA: entities._force_all_numeric_types()
  - Coercition forcée après extraction fallback: entities._force_all_numeric_types()
  - Fallback ultime avec types corrects: empty_entities._force_all_numeric_types()

✅ _extract_entities_openai_safe()
  - Coercition forcée après extraction OpenAI réussie
  - Fallback avec types corrects si échec

✅ _extract_entities_openai()
  - Prompt renforcé avec instructions de types explicites
  - Coercition forcée de TOUS les champs numériques depuis JSON:
    * age_days_safe = safe_int_conversion()
    * age_weeks_safe = safe_float_conversion()  
    * weight_safe = safe_float_conversion()
  - Construction entités avec types forcés explicites
  - Validation finale: entities._force_all_numeric_types()

✅ _extract_entities_basic_robust()
  - COERCITION FORCÉE à chaque assignation:
    * entities.breed = str(breed_found) 
    * entities.breed_confidence = float(0.9)
    * entities.age_days = int(age_days)
    * entities.age_weeks = float(age_weeks)
    * entities.weight = float(weight)
    * entities.weight_grams = float(weight)
    * entities.mortality_rate = float(mortality_value)
    * entities.temperature = float(temp_value)
    * entities.flock_size = int(flock_value)
  - Validation finale: entities._force_all_numeric_types()

CLASSE ConversationClarificationHandler - CORRECTIONS:

✅ Toutes les méthodes avec types STRING forcés:
  - build_enriched_question_from_clarification() → return str()
  - _extract_breed_from_clarification_safe() → return str()
  - _extract_sex_from_clarification_safe() → return str()
  - _integrate_enrichments_into_question_safe() → return str()
  - generate_clarification_request() → return str()

✅ detect_clarification_state() avec types forcés:
  - return bool(True), str(message)
  - return bool(False), None

✅ check_if_clarification_needed() avec types forcés:
  - return bool(needs_clarification), [str(q) for q in questions]

AVANTAGES DES CORRECTIONS APPLIQUÉES:

❌ PLUS JAMAIS d'erreur "< not supported between instances of str and int"
✅ Conversion automatique str → int/float dans TOUTE l'extraction
✅ Types forcés explicitement à chaque assignation de variable
✅ Validation des types avant ET après chaque opération
✅ Fallbacks avec types corrects garantis
✅ Messages de clarification avec types STRING forcés
✅ Retours de fonction avec types explicites

EXEMPLES DE CORRECTIONS APPLIQUÉES:

AVANT (PROBLÉMATIQUE):
entities.age = "25"           # str - ERREUR sur comparaison
entities.weight = "800"       # str - ERREUR sur comparaison  
entities.mortality_rate = "2.5" # str - ERREUR sur comparaison

APRÈS (CORRIGÉ):
entities.age = int(25)                    # int forcé
entities.weight = float(800.0)            # float forcé
entities.mortality_rate = float(2.5)      # float forcé

RÉSULTAT:
✅ Toutes les comparaisons numériques fonctionnent
✅ Pas d'erreur str/int dans les opérations
✅ Types cohérents dans toute l'application
✅ Validation robuste avec coercition automatique
"""