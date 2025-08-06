"""
ai_entity_extractor.py - EXTRACTION D'ENTITÉS AVEC IA

🎯 REMPLACE: 300+ lignes de patterns regex par compréhension IA
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
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime

from .ai_service_manager import AIServiceType, call_ai, AIResponse

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
        
        logger.info("🤖 [AI Entity Extractor] Initialisé avec prompts optimisés")
    
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
        Point d'entrée principal - Extraction complète des entités avec IA
        
        Args:
            question: Question de l'utilisateur
            language: Langue détectée (fr, en, es)
            
        Returns:
            ExtractedEntities avec toutes les informations extraites et normalisées
        """
        try:
            logger.info(f"🤖 [AI Entity Extractor] Extraction: '{question[:50]}...'")
            
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
            
            # Appel IA pour extraction
            ai_response = await call_ai(
                service_type=AIServiceType.ENTITY_EXTRACTION,
                prompt=prompt,
                model=model,
                max_tokens=800,
                temperature=0.1,
                cache_key=f"extract_{hash(question)}_{language}"
            )
            
            # Parser la réponse JSON
            raw_entities = self._parse_ai_response(ai_response.content)
            
            # Validation et normalisation supplémentaire
            validated_entities = await self._validate_and_normalize(raw_entities, question)
            
            # Convertir en objet ExtractedEntities
            entities = self._build_extracted_entities(validated_entities, ai_response)
            
            logger.info(f"✅ [AI Entity Extractor] Extraction réussie: {entities.breed_specific or 'race inconnue'}, {entities.age_days or 'âge inconnu'}j, {entities.sex or 'sexe inconnu'}")
            
            return entities
            
        except Exception as e:
            logger.error(f"❌ [AI Entity Extractor] Erreur extraction: {e}")
            # Retourner entités vides plutôt que faire échouer
            return self._create_empty_entities(question, str(e))
    
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
    
    def _parse_ai_response(self, content: str) -> Dict[str, Any]:
        """Parse la réponse JSON de l'IA avec gestion d'erreurs"""
        
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
            return {}
    
    def _parse_fallback(self, content: str) -> Dict[str, Any]:
        """Parsing de fallback si JSON invalide"""
        
        entities = {
            "age_days": None, "breed_specific": None, "sex": None,
            "weight_mentioned": False, "context_type": "général",
            "extraction_confidence": 0.3,
            "ai_reasoning": "Parsing fallback - JSON invalide"
        }
        
        # Extraction basique par mots-clés
        content_lower = content.lower()
        
        # Recherche âge
        import re
        age_match = re.search(r'(\d+)\s*(?:jour|day)s?', content_lower)
        if age_match:
            entities["age_days"] = int(age_match.group(1))
        
        # Recherche race
        for normalized, standard in self.normalization_maps["breeds"].items():
            if normalized in content_lower:
                entities["breed_specific"] = standard
                break
        
        # Recherche sexe  
        for raw, normalized in self.normalization_maps["sexes"].items():
            if raw in content_lower:
                entities["sex"] = normalized
                break
        
        return entities
    
    async def _validate_and_normalize(self, entities: Dict[str, Any], original_question: str) -> Dict[str, Any]:
        """Validation et normalisation supplémentaire avec IA"""
        
        try:
            # Si confiance élevée, validation légère
            if entities.get("extraction_confidence", 0) > 0.8:
                return self._normalize_locally(entities)
            
            # Sinon, validation IA complète
            prompt = self.prompts["validation_normalization"].format(
                entities=json.dumps(entities, ensure_ascii=False)
            )
            
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
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Entity Extractor] Erreur validation IA: {e}")
            return self._normalize_locally(entities)
    
    def _normalize_locally(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisation locale avec les mappings de backup"""
        
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
    
    def _build_extracted_entities(self, validated_entities: Dict[str, Any], ai_response: AIResponse) -> ExtractedEntities:
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
            normalized_by_ai=True
        )
    
    def _create_empty_entities(self, question: str, error: str) -> ExtractedEntities:
        """Crée un objet entités vide en cas d'erreur"""
        
        return ExtractedEntities(
            context_type="général",
            extraction_confidence=0.0,
            ai_reasoning=f"Erreur extraction: {error}",
            normalized_by_ai=False
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
                entities_list.append(self._create_empty_entities("", str(result)))
            else:
                entities_list.append(result)
        
        logger.info(f"✅ [AI Entity Extractor] Extraction par lot terminée: {len(entities_list)} résultats")
        return entities_list
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Statistiques d'extraction pour monitoring"""
        # Ces stats seraient collectées via AIServiceManager
        from .ai_service_manager import get_ai_service_manager
        
        manager = get_ai_service_manager()
        health = manager.get_service_health()
        
        return {
            "service_name": "AI Entity Extractor",
            "extraction_requests": health.get("requests_by_service", {}).get("entity_extraction", 0),
            "models_available": list(self.models.keys()),
            "normalization_maps": {k: len(v) for k, v in self.normalization_maps.items()},
            "supported_languages": ["fr", "en", "es"],
            "ai_service_health": health
        }

# Instance globale pour utilisation facile
_ai_entity_extractor = None

def get_ai_entity_extractor() -> AIEntityExtractor:
    """Récupère l'instance singleton de l'extracteur IA"""
    global _ai_entity_extractor
    if _ai_entity_extractor is None:
        _ai_entity_extractor = AIEntityExtractor()
    return _ai_entity_extractor