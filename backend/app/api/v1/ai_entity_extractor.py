"""
ai_entity_extractor.py - EXTRACTION D'ENTITÉS AVEC IA - CORRIGÉ

🎯 REMPLACE: 300+ lignes de patterns regex par compréhension IA
🔧 CORRECTIONS v1.1:
   - Gestion robuste des erreurs async
   - Fallback vers extraction basique si IA échoue
   - Métadonnées de traçabilité améliorées
   - Validation supplémentaire des résultats

🚀 CAPACITÉS:
- ✅ Extraction intelligente des races, âges, sexes, symptômes
- ✅ Normalisation automatique (Ross 308, 21 jours, male/female)  
- ✅ Compréhension du langage naturel ("trois semaines", "poulets mâles")
- ✅ Détection contextuelle avancée
- ✅ Support multilingue natif
- ✅ Gestion des variations et abréviations

Architecture:
- Prompts spécialisés par type d'extraction
- Normalisation systématique des résultats
- Validation et correction automatique
- Cache intelligent pour optimisation
- Fallback robuste vers extraction basique
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

# Import conditionnel pour éviter les erreurs si AI service non disponible
try:
    from .ai_service_manager import AIServiceType, call_ai, AIResponse
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False
    logging.warning("AI Service Manager non disponible - fallback vers extraction basique")

logger = logging.getLogger(__name__)

@dataclass
class ExtractedEntities:
    """Structure pour les entités extraites par IA"""
    age_days: Optional[int] = None
    age_weeks: Optional[int] = None
    breed_specific: Optional[str] = None
    breed_generic: Optional[str] = None
    sex: Optional[str] = None
    weight_mentioned: bool = False
    weight_grams: Optional[float] = None
    weight_unit: Optional[str] = None
    symptoms: List[str] = None
    context_type: Optional[str] = None
    housing_conditions: Optional[str] = None
    feeding_context: Optional[str] = None
    
    # Métadonnées IA
    extraction_confidence: float = 0.0
    ai_reasoning: Optional[str] = None
    normalized_by_ai: bool = True
    
    def __post_init__(self):
        if self.symptoms is None:
            self.symptoms = []

class AIEntityExtractor:
    """Extracteur d'entités avec IA - Remplace les patterns regex"""
    
    def __init__(self):
        # Vérifier disponibilité du service IA
        self.ai_available = AI_SERVICE_AVAILABLE
        
        if not self.ai_available:
            logger.warning("🔧 [AI Entity Extractor] Service IA non disponible - mode fallback")
            
        # Configuration des modèles par complexité
        self.models = {
            "simple": "gpt-3.5-turbo",    # Questions simples
            "complex": "gpt-4",           # Questions complexes/ambiguës  
            "multilingual": "gpt-4"       # Support multilingue
        }
        
        # Templates de prompts optimisés
        self.prompts = self._initialize_prompts()
        
        # Mapping de normalisation (backup pour validation)
        self.normalization_maps = {
            "breeds": {
                "ross 308": "Ross 308", "ross308": "Ross 308", "ross trois cent huit": "Ross 308",
                "cobb 500": "Cobb 500", "cobb500": "Cobb 500", "cobb cinq cents": "Cobb 500",
                "hubbard": "Hubbard", "arbor acres": "Arbor Acres",
                "isa brown": "ISA Brown", "lohmann brown": "Lohmann Brown"
            },
            "sexes": {
                "mâle": "male", "male": "male", "coq": "male", "masculin": "male",
                "femelle": "female", "female": "female", "poule": "female", "féminin": "female", 
                "mixte": "mixed", "mixed": "mixed", "mélangé": "mixed", "both": "mixed"
            },
            "contexts": {
                "poids": "performance", "weight": "performance", "croissance": "performance",
                "malade": "santé", "sick": "santé", "symptôme": "santé", "problem": "santé",
                "alimentation": "alimentation", "feed": "alimentation", "nutrition": "alimentation"
            }
        }
        
        # Statistiques pour monitoring
        self.stats = {
            "total_extractions": 0,
            "ai_extractions": 0,
            "fallback_extractions": 0,
            "validation_calls": 0,
            "errors": 0
        }
        
        logger.info(f"🤖 [AI Entity Extractor] Initialisé - IA disponible: {self.ai_available}")
    
    def _initialize_prompts(self) -> Dict[str, str]:
        """Initialise les templates de prompts spécialisés"""
        return {
            "extraction_complete": """Analyse cette question d'élevage avicole et extrait toutes les entités pertinentes.

QUESTION: "{question}"

Extrait précisément:

1. **RACE/SOUCHE**: Toute mention de race spécifique (Ross 308, Cobb 500, Hubbard, ISA Brown, etc.) ou générique (poulet, poule, broiler)

2. **ÂGE**: Âge mentionné sous toute forme (21 jours, 3 semaines, trois semaines, 21j, etc.)
   - Convertis TOUJOURS en jours
   - 1 semaine = 7 jours

3. **SEXE**: Mâle, femelle, mixte, coq, poule, etc.
   - Normalise: mâle/coq/masculin → "male"
   - Normalise: femelle/poule/féminin → "female"  
   - Normalise: mixte/mélangé/both → "mixed"

4. **POIDS**: Toute mention de poids, grammes, kg
   - Convertis en grammes
   - Note si c'est mentionné même sans valeur

5. **SYMPTÔMES**: Problèmes de santé, maladies, comportements anormaux

6. **CONTEXTE**: Type de question (performance/poids, santé, alimentation, général)

7. **CONDITIONS**: Logement, environnement, température mentionnés

Réponds UNIQUEMENT en JSON valide:
```json
{{
  "age_days": null|number,
  "age_weeks": null|number,
  "breed_specific": null|"Ross 308"|"Cobb 500"|etc,
  "breed_generic": null|"poulet"|"poule"|"broiler"|etc,
  "sex": null|"male"|"female"|"mixed",
  "weight_mentioned": true|false,
  "weight_grams": null|number,
  "weight_unit": null|"g"|"kg",
  "symptoms": [],
  "context_type": "performance"|"santé"|"alimentation"|"général",
  "housing_conditions": null|"description",
  "feeding_context": null|"description",
  "extraction_confidence": 0.0-1.0,
  "ai_reasoning": "explication courte du raisonnement"
}}
```

IMPORTANT: 
- Sois précis et conservateur
- Si incertain, mets null plutôt que deviner
- Normalise SYSTÉMATIQUEMENT les races (Ross 308, Cobb 500, etc.)
- Convertis TOUJOURS les âges en jours
- Utilise uniquement "male", "female", "mixed" pour le sexe""",

            "validation_normalization": """Valide et corrige ces entités extraites selon les standards avicoles.

ENTITÉS BRUTES: {entities}

CORRECTIONS NÉCESSAIRES:

1. **RACES**: Normalise selon standards:
   - ross 308/ross308/Ross trois cent huit → "Ross 308"
   - cobb 500/cobb500/Cobb cinq cents → "Cobb 500"  
   - hubbard/Hubbard → "Hubbard"
   - isa brown/ISA Brown → "ISA Brown"

2. **ÂGES**: Vérifie conversions:
   - Semaines × 7 = jours
   - Cohérence age_days et age_weeks

3. **SEXE**: Standardise:
   - mâle/coq/masculin → "male"
   - femelle/poule/féminin → "female"
   - mixte/mélangé → "mixed"

4. **COHÉRENCE**: Vérifie logique des combinaisons

Réponds avec les entités CORRIGÉES en JSON:
```json
{{
  "age_days": number|null,
  "age_weeks": number|null, 
  "breed_specific": "forme_normalisée"|null,
  "breed_generic": "forme_standard"|null,
  "sex": "male"|"female"|"mixed"|null,
  "weight_mentioned": true|false,
  "weight_grams": number|null,
  "weight_unit": "g"|"kg"|null,
  "symptoms": ["symptôme1", "symptôme2"],
  "context_type": "performance"|"santé"|"alimentation"|"général",
  "housing_conditions": "description"|null,
  "feeding_context": "description"|null,
  "extraction_confidence": 0.0-1.0,
  "validation_notes": "corrections appliquées"
}}
```""",

            "multilingual_extraction": """Extract poultry farming entities from this question in any language.

QUESTION: "{question}"
DETECTED LANGUAGE: {language}

Extract and normalize to standard English format:

1. **BREED**: Any breed mention (Ross 308, Cobb 500, Hubbard, etc.)
2. **AGE**: Convert to days (semanas/weeks × 7)
3. **SEX**: Normalize to "male", "female", "mixed"
4. **WEIGHT**: Convert to grams  
5. **SYMPTOMS**: Health issues
6. **CONTEXT**: Question type

Respond in JSON:
```json
{{
  "age_days": null|number,
  "breed_specific": null|"Ross 308"|"Cobb 500"|etc,
  "sex": null|"male"|"female"|"mixed",
  "weight_mentioned": true|false,
  "weight_grams": null|number,
  "symptoms": [],
  "context_type": "performance"|"health"|"feeding"|"general",
  "extraction_confidence": 0.0-1.0,
  "source_language": "{language}"
}}
```"""
        }
    
    async def extract_entities(self, question: str, language: str = "fr") -> ExtractedEntities:
        """
        🔧 CORRIGÉ: Point d'entrée principal - Extraction complète avec gestion d'erreurs robuste
        
        Args:
            question: Question de l'utilisateur
            language: Langue détectée (fr, en, es)
            
        Returns:
            ExtractedEntities avec toutes les informations extraites et normalisées
        """
        self.stats["total_extractions"] += 1
        
        try:
            logger.info(f"🤖 [AI Entity Extractor] Extraction: '{question[:50]}...'")
            
            # 🔧 NOUVEAU: Vérification disponibilité IA
            if not self.ai_available:
                logger.warning("⚠️ [AI Entity Extractor] Service IA non disponible - fallback")
                return self._basic_extraction_fallback(question)
            
            # Déterminer le modèle selon la complexité
            model = self._select_model(question, language)
            
            # Choisir le prompt approprié
            if language != "fr":
                prompt = self.prompts["multilingual_extraction"].format(
                    question=question, 
                    language=language
                )
            else:
                prompt = self.prompts["extraction_complete"].format(question=question)
            
            # 🔧 CORRIGÉ: Appel IA avec gestion d'erreurs améliorée
            try:
                ai_response = await call_ai(
                    service_type=AIServiceType.ENTITY_EXTRACTION,
                    prompt=prompt,
                    model=model,
                    max_tokens=800,
                    temperature=0.1,
                    cache_key=f"extract_{hash(question)}_{language}"
                )
                
                self.stats["ai_extractions"] += 1
                
            except Exception as ai_error:
                logger.warning(f"⚠️ [AI Entity Extractor] Erreur appel IA: {ai_error}")
                self.stats["errors"] += 1
                return self._basic_extraction_fallback(question)
            
            # Parser la réponse JSON
            raw_entities = self._parse_ai_response(ai_response.content)
            if not raw_entities:
                logger.warning("⚠️ [AI Entity Extractor] Parsing échoué - fallback")
                return self._basic_extraction_fallback(question)
            
            # Validation et normalisation supplémentaire
            validated_entities = await self._validate_and_normalize(raw_entities, question)
            
            # Convertir en objet ExtractedEntities
            entities = self._build_extracted_entities(validated_entities, ai_response)
            
            logger.info(f"✅ [AI Entity Extractor] Extraction réussie: {entities.breed_specific or 'race inconnue'}, {entities.age_days or 'âge inconnu'}j, {entities.sex or 'sexe inconnu'}")
            
            return entities
            
        except Exception as e:
            logger.error(f"❌ [AI Entity Extractor] Erreur extraction: {e}")
            self.stats["errors"] += 1
            # Retourner fallback plutôt que faire échouer
            return self._basic_extraction_fallback(question)
    
    def _basic_extraction_fallback(self, question: str) -> ExtractedEntities:
        """
        🔧 NOUVEAU: Extraction basique en cas d'échec IA
        
        Returns:
            ExtractedEntities avec extraction de base par mots-clés
        """
        self.stats["fallback_extractions"] += 1
        logger.debug("🔧 [AI Entity Extractor] Mode fallback - extraction basique")
        
        entities = ExtractedEntities()
        question_lower = question.lower()
        
        # Extraction basique par mots-clés
        
        # Âge - patterns simples
        import re
        age_match = re.search(r'(\d+)\s*(?:jour|day)s?', question_lower)
        if age_match:
            entities.age_days = int(age_match.group(1))
            entities.age_weeks = entities.age_days // 7
        else:
            week_match = re.search(r'(\d+)\s*(?:semaine|week)s?', question_lower)
            if week_match:
                entities.age_weeks = int(week_match.group(1))
                entities.age_days = entities.age_weeks * 7
        
        # Race - recherche dans les mappings
        for breed_raw, breed_normalized in self.normalization_maps["breeds"].items():
            if breed_raw in question_lower:
                entities.breed_specific = breed_normalized
                break
        
        # Si pas de race spécifique, chercher générique
        if not entities.breed_specific:
            for generic in ['poulet', 'poule', 'coq', 'chicken', 'broiler']:
                if generic in question_lower:
                    entities.breed_generic = generic
                    break
        
        # Sexe
        for sex_raw, sex_normalized in self.normalization_maps["sexes"].items():
            if sex_raw in question_lower:
                entities.sex = sex_normalized
                break
        
        # Poids
        entities.weight_mentioned = any(word in question_lower 
                                       for word in ['poids', 'weight', 'gramme', 'kg', 'kilo'])
        
        # Contexte basique
        if any(word in question_lower for word in ['malade', 'symptôme', 'problème']):
            entities.context_type = 'santé'
        elif any(word in question_lower for word in ['poids', 'weight', 'croissance']):
            entities.context_type = 'performance'
        elif any(word in question_lower for word in ['alimentation', 'nourrir', 'aliment']):
            entities.context_type = 'alimentation'
        else:
            entities.context_type = 'général'
        
        # Métadonnées fallback
        entities.extraction_confidence = 0.5  # Confiance moyenne pour fallback
        entities.ai_reasoning = "Extraction basique par mots-clés (fallback)"
        entities.normalized_by_ai = False
        
        return entities
    
    def _select_model(self, question: str, language: str) -> str:
        """Sélectionne le modèle optimal selon la complexité"""
        
        # Multilingue → GPT-4
        if language != "fr":
            return self.models["multilingual"]
        
        # Question complexe → GPT-4  
        complexity_indicators = [
            len(question.split()) > 15,  # Question longue
            any(word in question.lower() for word in ["comment", "pourquoi", "expliquer", "différence"]),  # Questions conceptuelles
            question.count(',') > 2,  # Multiples éléments
            any(word in question.lower() for word in ["symptôme", "problème", "malade"])  # Santé complexe
        ]
        
        if sum(complexity_indicators) >= 2:
            return self.models["complex"]
        
        return self.models["simple"]
    
    def _parse_ai_response(self, content: str) -> Optional[Dict[str, Any]]:
        """🔧 AMÉLIORÉ: Parse la réponse JSON de l'IA avec gestion d'erreurs robuste"""
        
        if not content or not content.strip():
            logger.warning("⚠️ [AI Entity Extractor] Contenu vide")
            return None
        
        try:
            # Nettoyer le contenu (supprimer markdown, etc.)
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parser JSON
            entities = json.loads(content)
            
            # Validation basique de structure
            if not isinstance(entities, dict):
                logger.warning("⚠️ [AI Entity Extractor] Réponse non-dict")
                return None
            
            # Garantir les champs essentiels
            required_fields = ["age_days", "breed_specific", "sex", "weight_mentioned", "context_type"]
            for field in required_fields:
                if field not in entities:
                    entities[field] = None
            
            return entities
            
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [AI Entity Extractor] Erreur parsing JSON: {e}")
            return self._parse_fallback(content)
        except Exception as e:
            logger.error(f"❌ [AI Entity Extractor] Erreur parsing: {e}")
            return None
    
    def _parse_fallback(self, content: str) -> Optional[Dict[str, Any]]:
        """🔧 AMÉLIORÉ: Parsing de fallback si JSON invalide"""
        
        logger.debug("🔧 [AI Entity Extractor] Tentative parsing fallback")
        
        entities = {
            "age_days": None, "breed_specific": None, "sex": None,
            "weight_mentioned": False, "context_type": "général",
            "extraction_confidence": 0.3,
            "ai_reasoning": "Parsing fallback - JSON invalide"
        }
        
        # Extraction basique par mots-clés du contenu
        content_lower = content.lower()
        
        # Recherche âge
        import re
        age_match = re.search(r'"?age_days"?\s*:\s*(\d+)', content_lower)
        if age_match:
            entities["age_days"] = int(age_match.group(1))
        
        # Recherche race
        for normalized, standard in self.normalization_maps["breeds"].items():
            if normalized in content_lower or standard.lower() in content_lower:
                entities["breed_specific"] = standard
                break
        
        # Recherche sexe  
        for raw, normalized in self.normalization_maps["sexes"].items():
            if raw in content_lower or normalized in content_lower:
                entities["sex"] = normalized
                break
        
        return entities
    
    async def _validate_and_normalize(self, entities: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """🔧 CORRIGÉ: Validation et normalisation supplémentaire avec IA"""
        
        self.stats["validation_calls"] += 1
        
        try:
            # Si confiance élevée, validation légère
            if entities.get("extraction_confidence", 0) > 0.8:
                return self._normalize_locally(entities)
            
            # Sinon, validation IA complète si disponible
            if not self.ai_available:
                logger.debug("🔧 [AI Entity Extractor] Validation locale - IA non disponible")
                return self._normalize_locally(entities)
            
            prompt = self.prompts["validation_normalization"].format(
                entities=json.dumps(entities, ensure_ascii=False)
            )
            
            try:
                ai_response = await call_ai(
                    service_type=AIServiceType.VALIDATION,
                    prompt=prompt,
                    model="gpt-4",
                    max_tokens=600,
                    temperature=0.05,
                    cache_key=f"validate_{hash(str(entities))}"
                )
                
                validated = self._parse_ai_response(ai_response.content)
                return validated if validated else self._normalize_locally(entities)
                
            except Exception as ai_error:
                logger.warning(f"⚠️ [AI Entity Extractor] Erreur validation IA: {ai_error}")
                return self._normalize_locally(entities)
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Entity Extractor] Erreur validation: {e}")
            return self._normalize_locally(entities)
    
    def _normalize_locally(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation locale avec les mappings de backup"""
        
        logger.debug("🔧 [AI Entity Extractor] Normalisation locale")
        
        # Normaliser race
        breed = entities.get("breed_specific", "").lower()
        for raw, normalized in self.normalization_maps["breeds"].items():
            if raw in breed:
                entities["breed_specific"] = normalized
                break
        
        # Normaliser sexe
        sex = entities.get("sex", "").lower()
        for raw, normalized in self.normalization_maps["sexes"].items():
            if raw in sex:
                entities["sex"] = normalized
                break
        
        # Calculer age_weeks si age_days disponible
        age_days = entities.get("age_days")
        if age_days and isinstance(age_days, int):
            entities["age_weeks"] = age_days // 7
        
        # Normaliser contexte
        context = entities.get("context_type", "").lower()
        for raw, normalized in self.normalization_maps["contexts"].items():
            if raw in context:
                entities["context_type"] = normalized
                break
        
        return entities
    
    def _build_extracted_entities(self, validated_entities: Dict[str, Any], ai_response) -> ExtractedEntities:
        """Construit l'objet ExtractedEntities final"""
        
        return ExtractedEntities(
            age_days=validated_entities.get("age_days"),
            age_weeks=validated_entities.get("age_weeks"),
            breed_specific=validated_entities.get("breed_specific"),
            breed_generic=validated_entities.get("breed_generic"),
            sex=validated_entities.get("sex"),
            weight_mentioned=validated_entities.get("weight_mentioned", False),
            weight_grams=validated_entities.get("weight_grams"),
            weight_unit=validated_entities.get("weight_unit"),
            symptoms=validated_entities.get("symptoms", []),
            context_type=validated_entities.get("context_type"),
            housing_conditions=validated_entities.get("housing_conditions"),
            feeding_context=validated_entities.get("feeding_context"),
            extraction_confidence=validated_entities.get("extraction_confidence", 0.7),
            ai_reasoning=validated_entities.get("ai_reasoning") or validated_entities.get("validation_notes"),
            normalized_by_ai=self.ai_available
        )
    
    async def extract_entities_batch(self, questions: List[str], language: str = "fr") -> List[ExtractedEntities]:
        """Extraction par lot pour optimisation"""
        
        logger.info(f"🤖 [AI Entity Extractor] Extraction par lot: {len(questions)} questions")
        
        # Traitement parallèle avec asyncio
        import asyncio
        tasks = [self.extract_entities(q, language) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrer les erreurs
        entities_list = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"⚠️ [AI Entity Extractor] Erreur dans lot: {result}")
                entities_list.append(self._basic_extraction_fallback(""))
            else:
                entities_list.append(result)
        
        logger.info(f"✅ [AI Entity Extractor] Extraction par lot terminée: {len(entities_list)} résultats")
        return entities_list
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Statistiques d'extraction pour monitoring"""
        
        total = max(self.stats["total_extractions"], 1)
        
        return {
            "service_name": "AI Entity Extractor",
            "ai_available": self.ai_available,
            "total_extractions": self.stats["total_extractions"],
            "ai_extractions": self.stats["ai_extractions"],
            "fallback_extractions": self.stats["fallback_extractions"],
            "validation_calls": self.stats["validation_calls"],
            "errors": self.stats["errors"],
            "ai_success_rate": f"{(self.stats['ai_extractions']/total)*100:.1f}%" if self.ai_available else "0%",
            "fallback_rate": f"{(self.stats['fallback_extractions']/total)*100:.1f}%",
            "error_rate": f"{(self.stats['errors']/total)*100:.1f}%",
            "models_available": list(self.models.keys()) if self.ai_available else [],
            "normalization_maps": {k: len(v) for k, v in self.normalization_maps.items()},
            "supported_languages": ["fr", "en", "es"]
        }

    def get_stats(self) -> Dict[str, Any]:
        """🔧 NOUVEAU: Alias pour get_extraction_stats() pour compatibilité"""
        return self.get_extraction_stats()

# Instance globale pour utilisation facile
_ai_entity_extractor = None

def get_ai_entity_extractor() -> AIEntityExtractor:
    """Récupère l'instance singleton de l'extracteur IA"""
    global _ai_entity_extractor
    if _ai_entity_extractor is None:
        _ai_entity_extractor = AIEntityExtractor()
    return _ai_entity_extractor

# 🔧 NOUVEAU: Fonction de test pour validation
async def test_ai_extractor():
    """Test de l'extracteur IA avec gestion d'erreurs"""
    
    extractor = AIEntityExtractor()
    
    test_questions = [
        "Quel est le poids d'un poulet Ross 308 mâle de 21 jours ?",
        "Mes poules Cobb 500 de 3 semaines ont de la diarrhée",
        "Comment nourrir des poussins ?",
        "Question invalide pour tester le fallback"
    ]
    
    print("🧪 Test de l'extracteur IA avec fallback:")
    print("=" * 60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Test {i}: {question}")
        
        try:
            entities = await extractor.extract_entities(question)
            print(f"   ✅ Race: {entities.breed_specific}")
            print(f"   ✅ Âge: {entities.age_days} jours")
            print(f"   ✅ Sexe: {entities.sex}")
            print(f"   ✅ Contexte: {entities.context_type}")
            print(f"   ✅ Confiance: {entities.extraction_confidence:.2f}")
            print(f"   ✅ IA utilisée: {entities.normalized_by_ai}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
    
    print(f"\n📊 Statistiques:")
    stats = extractor.get_extraction_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Tests terminés!")

def test_ai_extractor_sync():
    """Version synchrone pour compatibilité"""
    try:
        import asyncio
        asyncio.run(test_ai_extractor())
    except Exception as e:
        print(f"⚠️ Tests async échoués: {e}")

if __name__ == "__main__":
    test_ai_extractor_sync()