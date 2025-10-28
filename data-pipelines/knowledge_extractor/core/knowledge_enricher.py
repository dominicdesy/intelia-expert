"""
Enrichisseur de connaissances avec LLM et intents - VERSION CORRIGÉE
Support complet des lignées génétiques multiples - SANS TRONCATURE
"""

import re
import json
import logging
from typing import Dict, List, Any
from core.models import ChunkMetadata, DocumentContext
from core.llm_client import LLMClient
from core.intent_manager import IntentManager


class KnowledgeEnricher:
    """Enrichisseur de connaissances avec métadonnées avancées - VERSION PRESERVEE"""

    def __init__(self, llm_client: LLMClient, intent_manager: IntentManager):
        self.llm_client = llm_client
        self.intent_manager = intent_manager
        self.logger = logging.getLogger(__name__)

    def enrich_chunk(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> ChunkMetadata:
        """Enrichit un segment avec métadonnées avancées - SANS PERTE DE CONTENU"""
        try:
            # DIAGNOSTIC: Log taille avant enrichissement
            original_size = len(segment["content"])
            self.logger.debug(
                f"DIAGNOSTIC: Chunk avant enrichissement: {original_size} caractères"
            )

            # Analyse des intents avec contexte génétique
            intent_analysis = self.intent_manager.detect_intent_category(
                segment["content"]
            )

            # Analyse LLM seulement si vraiment nécessaire
            needs_llm_analysis = intent_analysis["confidence"] < 0.4 or (
                intent_analysis["confidence"] < 0.7 and len(segment["content"]) > 800
            )

            if needs_llm_analysis:
                llm_metadata = self._llm_analyze_chunk(segment, document_context)
                merged_metadata = self._merge_analyses(
                    intent_analysis, llm_metadata, document_context
                )
            else:
                merged_metadata = self._intent_to_metadata(
                    intent_analysis, segment, document_context
                )

            self.logger.debug(
                f"Chunk enrichi ({document_context.genetic_line}): "
                f"{merged_metadata.intent_category} - {merged_metadata.confidence_score:.2f}"
            )
            return merged_metadata

        except Exception as e:
            self.logger.error(f"Erreur enrichissement chunk: {e}")
            return self._fallback_metadata(segment, document_context)

    def _is_well_supported_genetic_line(self, genetic_line: str) -> bool:
        """Vérifie si une lignée génétique est bien supportée par le système intent"""
        if not genetic_line or genetic_line.lower() in ["unknown", "unclear"]:
            return False

        # Les lignées bien supportées par les intents
        well_supported = ["ross 308", "ross308"]
        return genetic_line.lower() in [line.lower() for line in well_supported]

    def _llm_analyze_chunk(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> Dict[str, Any]:
        """Analyse LLM d'un chunk avec contexte génétique"""
        prompt = self._build_chunk_analysis_prompt(segment, document_context)
        response = self.llm_client.complete(prompt, max_tokens=700)
        return self._parse_chunk_response(response)

    def _build_chunk_analysis_prompt(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> str:
        """Construit le prompt d'analyse du chunk - VERSION MULTI-LIGNÉES"""

        # Information sur les lignées génétiques supportées
        genetic_line_context = f"""
GENETIC LINE CONTEXT:
- Document genetic line: {document_context.genetic_line}
- This content is specifically for {document_context.genetic_line} poultry
- Consider breed-specific characteristics and requirements
"""

        return f"""
Analyze this poultry knowledge chunk for comprehensive metadata extraction.

{genetic_line_context}

Document context:
- Genetic line: {document_context.genetic_line}
- Document type: {document_context.document_type}
- Species: {document_context.species}
- Target audience: {document_context.target_audience}

Chunk content:
{segment['content'][:1500]}

Return ONLY a valid JSON object:
{{
    "intent_category": "metric_query|environment_setting|protocol_query|diagnosis_triage|economics_cost|general",
    "content_type": "prevention|treatment|pathophysiology|management|nutrition|economics|performance",
    "technical_level": "basic|intermediate|advanced",
    "age_applicability": ["0-14_days", "15-35_days", "36-52_days", "all_ages"],
    "applicable_metrics": ["specific metrics mentioned or relevant to the content"],
    "actionable_recommendations": ["concrete actionable items"],
    "followup_themes": ["related topics for follow-up"],
    "detected_phase": "starter|grower|finisher|breeder|all",
    "detected_bird_type": "broiler|layer|breeder|mixed",
    "detected_site_type": "broiler_farm|layer_farm|breeding_farm|hatchery|feed_mill",
    "confidence_score": 0.0-1.0,
    "reasoning": "brief explanation focusing on genetic line relevance"
}}

IMPORTANT: Consider the specific genetic line ({document_context.genetic_line}) when analyzing:
- Performance targets may vary between breeds
- Management practices may be breed-specific  
- Nutritional requirements may differ
- Focus on actionable knowledge for {document_context.genetic_line} professionals
"""

    def _parse_chunk_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse LLM pour un chunk avec validation étendue"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            parsed_data = json.loads(response)

            # Validation et nettoyage des données SANS TRONCATURE
            cleaned_data = self._validate_and_clean_llm_response(parsed_data)
            return cleaned_data

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Erreur parsing réponse chunk LLM: {e}")
            return {}

    def _validate_and_clean_llm_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie la réponse LLM - CORRECTION: SANS TRONCATURE"""

        # Valeurs par défaut et validation
        valid_intent_categories = [
            "metric_query",
            "environment_setting",
            "protocol_query",
            "diagnosis_triage",
            "economics_cost",
            "general",
        ]
        valid_content_types = [
            "prevention",
            "treatment",
            "pathophysiology",
            "management",
            "nutrition",
            "economics",
            "performance",
        ]
        valid_technical_levels = ["basic", "intermediate", "advanced"]
        valid_phases = ["starter", "grower", "finisher", "breeder", "all"]
        valid_bird_types = ["broiler", "layer", "breeder", "mixed"]
        valid_site_types = [
            "broiler_farm",
            "layer_farm",
            "breeding_farm",
            "hatchery",
            "feed_mill",
        ]

        cleaned = {
            "intent_category": self._validate_enum_field(
                data.get("intent_category"), valid_intent_categories, "general"
            ),
            "content_type": self._validate_enum_field(
                data.get("content_type"), valid_content_types, "management"
            ),
            "technical_level": self._validate_enum_field(
                data.get("technical_level"), valid_technical_levels, "intermediate"
            ),
            "detected_phase": self._validate_enum_field(
                data.get("detected_phase"), valid_phases, "all"
            ),
            "detected_bird_type": self._validate_enum_field(
                data.get("detected_bird_type"), valid_bird_types, "broiler"
            ),
            "detected_site_type": self._validate_enum_field(
                data.get("detected_site_type"), valid_site_types, "broiler_farm"
            ),
            "age_applicability": self._validate_list_field(
                data.get("age_applicability"), ["all_ages"]
            ),
            "applicable_metrics": self._validate_list_field(
                data.get("applicable_metrics"), []
            ),
            "actionable_recommendations": self._validate_list_field(
                data.get("actionable_recommendations"), []
            ),
            "followup_themes": self._validate_list_field(
                data.get("followup_themes"), []
            ),
            "confidence_score": self._validate_numeric_field(
                data.get("confidence_score"), 0.0, 1.0, 0.5
            ),
            # CORRECTION CRITIQUE: SUPPRESSION DE LA TRONCATURE
            "reasoning": str(data.get("reasoning", "LLM analysis")),  # PLUS DE [:200]
        }

        return cleaned

    def _validate_enum_field(
        self, value: Any, valid_values: List[str], default: str
    ) -> str:
        """Valide un champ énuméré"""
        if isinstance(value, str) and value.lower() in [
            v.lower() for v in valid_values
        ]:
            return value.lower()
        return default

    def _validate_list_field(self, value: Any, default: List[str]) -> List[str]:
        """Valide un champ liste - CORRECTION: SUPPRESSION DES TRONCATURES"""
        if isinstance(value, list):
            # Filtre et nettoie les éléments de la liste SANS TRONCATURE
            cleaned_list = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    # CORRECTION: Suppression de la troncature [:100]
                    cleaned_item = item.strip()
                    if cleaned_item not in cleaned_list:  # Évite doublons
                        cleaned_list.append(cleaned_item)
            # CORRECTION: Augmentation de la limite de 10 à 20 éléments
            return cleaned_list[:20]
        return default

    def _validate_numeric_field(
        self, value: Any, min_val: float, max_val: float, default: float
    ) -> float:
        """Valide un champ numérique"""
        try:
            numeric_value = float(value)
            return max(min_val, min(max_val, numeric_value))
        except (TypeError, ValueError):
            return default

    def _intent_to_metadata(
        self,
        intent_analysis: Dict[str, Any],
        segment: Dict[str, Any],
        document_context: DocumentContext,
    ) -> ChunkMetadata:
        """Convertit l'analyse d'intent en métadonnées avec support multi-lignées"""
        intent_category = intent_analysis["primary_intent"]

        # Extraction des métriques applicables avec contexte génétique
        applicable_metrics = self.intent_manager.extract_applicable_metrics(
            segment["content"], intent_category
        )

        # Détection des recommandations actionnables améliorée
        actionable_recommendations = self._extract_actionable_items(
            segment["content"], document_context.genetic_line
        )

        # Détection du type de site basée sur lignée génétique
        detected_site_type = self._infer_site_type_genetic_aware(
            document_context.document_type, document_context.genetic_line
        )

        return ChunkMetadata(
            intent_category=intent_category,
            content_type=self._infer_content_type(segment["content"]),
            technical_level=self._assess_technical_level(segment["content"]),
            age_applicability=self._detect_age_applicability(segment["content"]),
            applicable_metrics=applicable_metrics,
            actionable_recommendations=actionable_recommendations,
            followup_themes=self._get_followup_themes(intent_category),
            detected_phase=self._detect_phase(segment["content"]),
            detected_bird_type=self._infer_bird_type_from_genetic_line(
                document_context.genetic_line
            ),
            detected_site_type=detected_site_type,
            confidence_score=intent_analysis["confidence"],
            reasoning=f"Intent-based analysis for {document_context.genetic_line}: {intent_category}",
        )

    def _extract_actionable_items(self, content: str, genetic_line: str) -> List[str]:
        """Extrait les éléments actionnables du contenu avec contexte génétique - SANS TRONCATURE"""
        actionable_patterns = [
            r"maintain\s+([^.]{10,80})",
            r"keep\s+([^.]{10,80})",
            r"avoid\s+([^.]{10,80})",
            r"ensure\s+([^.]{10,80})",
            r"provide\s+([^.]{10,80})",
            r"use\s+([^.]{10,80})",
            r"follow\s+([^.]{10,80})",
            r"implement\s+([^.]{10,80})",
            r"monitor\s+([^.]{10,80})",
            r"adjust\s+([^.]{10,80})",
            r"apply\s+([^.]{10,80})",
            r"set\s+([^.]{10,80})",
        ]

        actionable_items = []
        content_lower = content.lower()

        for pattern in actionable_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                clean_action = re.sub(r"[^a-zA-Z0-9\s\-\.]", "", match).strip()
                if clean_action and len(clean_action) > 5:
                    # CORRECTION: SUPPRESSION de la troncature [:45] et [:50]
                    if genetic_line and genetic_line.lower() != "unknown":
                        contextualized_action = clean_action
                    else:
                        contextualized_action = clean_action

                    if contextualized_action not in actionable_items:
                        actionable_items.append(contextualized_action)

        # CORRECTION: Augmentation de la limite de 8 à 15 items
        return actionable_items[:15]

    def _infer_content_type(self, content: str) -> str:
        """Infère le type de contenu avec détection améliorée"""
        content_lower = content.lower()

        content_type_patterns = {
            "performance": [
                "performance",
                "target",
                "objective",
                "standard",
                "fcr",
                "weight",
                "gain",
            ],
            "prevention": ["prevent", "avoid", "control", "prophylaxis", "biosecurity"],
            "treatment": [
                "treat",
                "therapy",
                "medication",
                "antibiotic",
                "vaccine",
                "cure",
            ],
            "pathophysiology": [
                "cause",
                "pathogenesis",
                "disease",
                "etiology",
                "pathology",
            ],
            "management": [
                "manage",
                "housing",
                "environment",
                "ventilation",
                "lighting",
            ],
            "nutrition": [
                "feed",
                "nutrition",
                "protein",
                "energy",
                "vitamin",
                "mineral",
            ],
            "economics": [
                "cost",
                "economic",
                "profit",
                "price",
                "budget",
                "roi",
                "financial",
            ],
        }

        scores = {}
        for content_type, patterns in content_type_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content_lower)
            if score > 0:
                scores[content_type] = score

        return max(scores, key=scores.get) if scores else "management"

    def _assess_technical_level(self, content: str) -> str:
        """Évalue le niveau technique du contenu avec critères étendus"""
        content_lower = content.lower()

        # Indicateurs de niveau technique
        technical_indicators = {
            "advanced": [
                "pathogenesis",
                "etiology",
                "histopathology",
                "immunosuppressive",
                "metabolic",
                "genomic",
                "molecular",
                "biochemical",
                "pharmacokinetics",
            ],
            "intermediate": [
                "vaccination",
                "biosecurity",
                "management",
                "protocol",
                "diagnosis",
                "treatment",
                "prevention",
                "monitoring",
                "analysis",
            ],
            "basic": [
                "feed",
                "water",
                "temperature",
                "housing",
                "cleaning",
                "basic",
                "simple",
                "daily",
                "routine",
            ],
        }

        scores = {}
        for level, indicators in technical_indicators.items():
            score = sum(1 for indicator in indicators if indicator in content_lower)
            if score > 0:
                scores[level] = score

        if scores:
            return max(scores, key=scores.get)

        # Évaluation basée sur la complexité du vocabulaire
        words = content.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0

        if avg_word_length > 7:
            return "advanced"
        elif avg_word_length > 5:
            return "intermediate"
        else:
            return "basic"

    def _detect_age_applicability(self, content: str) -> List[str]:
        """Détecte l'applicabilité par âge avec patterns étendus"""
        age_patterns = {
            "0-14_days": [
                "chick",
                "day-old",
                "starter",
                "early",
                "hatch",
                "d0",
                "0-10",
                "first week",
                "hatching",
                "placement",
            ],
            "15-35_days": [
                "grower",
                "growing",
                "middle",
                "develop",
                "15-28",
                "2-4 weeks",
                "growing phase",
                "intermediate",
            ],
            "36-52_days": [
                "finisher",
                "finishing",
                "slaughter",
                "market",
                "final",
                "42",
                "processing",
                "harvest",
                "end",
            ],
            "all_ages": [
                "all",
                "throughout",
                "entire",
                "whole",
                "any age",
                "all ages",
                "continuously",
                "always",
            ],
        }

        content_lower = content.lower()
        applicable_ages = []

        for age_range, indicators in age_patterns.items():
            score = sum(1 for indicator in indicators if indicator in content_lower)
            if score > 0:
                applicable_ages.append(age_range)

        # Si aucune mention spécifique, assume applicable à tous
        return applicable_ages if applicable_ages else ["all_ages"]

    def _detect_phase(self, content: str) -> str:
        """Détecte la phase d'élevage avec détection améliorée"""
        phase_indicators = {
            "starter": [
                "starter",
                "chick",
                "0-10",
                "day-old",
                "early",
                "first",
                "hatch",
            ],
            "grower": ["grower", "growing", "11-28", "15-35", "middle", "develop"],
            "finisher": [
                "finisher",
                "finishing",
                "29-42",
                "36-52",
                "slaughter",
                "final",
            ],
            "breeder": [
                "breeder",
                "breeding",
                "parent",
                "reproduction",
                "egg",
                "fertile",
            ],
        }

        content_lower = content.lower()
        phase_scores = {}

        for phase, indicators in phase_indicators.items():
            score = sum(1 for indicator in indicators if indicator in content_lower)
            if score > 0:
                phase_scores[phase] = score

        return max(phase_scores, key=phase_scores.get) if phase_scores else "all"

    def _infer_bird_type_from_genetic_line(self, genetic_line: str) -> str:
        """Infère le type d'oiseau basé sur la lignée génétique"""
        if not genetic_line or genetic_line.lower() == "unknown":
            return "broiler"  # Par défaut

        genetic_line_lower = genetic_line.lower()

        # Mapping lignée -> type d'oiseau
        if any(line in genetic_line_lower for line in ["ross", "cobb", "hubbard"]):
            if "parent" in genetic_line_lower or "ps" in genetic_line_lower:
                return "breeder"
            else:
                return "broiler"
        elif any(
            line in genetic_line_lower
            for line in ["isa", "lohmann", "hy-line", "dekalb"]
        ):
            return "layer"
        else:
            return "broiler"

    def _infer_site_type_genetic_aware(
        self, document_type: str, genetic_line: str
    ) -> str:
        """Infère le type de site avec conscience de la lignée génétique"""

        # Mapping basé sur le type de document
        doc_type_mapping = {
            "health_protocol": "broiler_farm",
            "biosecurity_guide": "broiler_farm",
            "nutrition_manual": "feed_mill",
            "breeding_handbook": "breeding_farm",
            "management_guide": "broiler_farm",
        }

        base_site_type = doc_type_mapping.get(document_type, "broiler_farm")

        # Ajustement basé sur la lignée génétique
        if genetic_line and genetic_line.lower() != "unknown":
            genetic_line_lower = genetic_line.lower()

            if any(
                layer_line in genetic_line_lower
                for layer_line in ["isa", "lohmann", "hy-line"]
            ):
                return "layer_farm"
            elif "parent" in genetic_line_lower or "ps" in genetic_line_lower:
                return "breeding_farm"

        return base_site_type

    def _get_followup_themes(self, intent_category: str) -> List[str]:
        """Récupère les thèmes de suivi pour un intent"""
        if not self.intent_manager.intents_data:
            return []

        intent_config = self.intent_manager.intents_data.get("intents", {}).get(
            intent_category, {}
        )
        return intent_config.get("followup_themes", [])

    def _merge_analyses(
        self,
        intent_analysis: Dict[str, Any],
        llm_analysis: Dict[str, Any],
        document_context: DocumentContext,
    ) -> ChunkMetadata:
        """Fusionne les analyses intent et LLM avec contexte génétique"""
        # Priorise LLM si confiance intent faible
        confidence_intent = intent_analysis.get("confidence", 0.0)
        confidence_llm = llm_analysis.get("confidence_score", 0.0)

        if confidence_llm > confidence_intent + 0.1:  # Seuil ajusté
            # Utilise principalement LLM avec compléments intent
            return ChunkMetadata(
                intent_category=llm_analysis.get(
                    "intent_category", intent_analysis["primary_intent"]
                ),
                content_type=llm_analysis.get("content_type", "management"),
                technical_level=llm_analysis.get("technical_level", "intermediate"),
                age_applicability=llm_analysis.get("age_applicability", ["all_ages"]),
                applicable_metrics=llm_analysis.get("applicable_metrics", []),
                actionable_recommendations=llm_analysis.get(
                    "actionable_recommendations", []
                ),
                followup_themes=llm_analysis.get("followup_themes", []),
                detected_phase=llm_analysis.get("detected_phase", "all"),
                detected_bird_type=llm_analysis.get(
                    "detected_bird_type",
                    self._infer_bird_type_from_genetic_line(
                        document_context.genetic_line
                    ),
                ),
                detected_site_type=llm_analysis.get(
                    "detected_site_type", "broiler_farm"
                ),
                confidence_score=confidence_llm,
                reasoning=f"LLM analysis for {document_context.genetic_line}: {llm_analysis.get('reasoning', 'Merged analysis')}",
            )
        else:
            # Utilise intent avec compléments LLM
            return ChunkMetadata(
                intent_category=intent_analysis["primary_intent"],
                content_type=llm_analysis.get("content_type", "management"),
                technical_level=llm_analysis.get("technical_level", "intermediate"),
                age_applicability=llm_analysis.get("age_applicability", ["all_ages"]),
                applicable_metrics=self.intent_manager.extract_applicable_metrics(
                    "", intent_analysis["primary_intent"]
                ),
                actionable_recommendations=llm_analysis.get(
                    "actionable_recommendations", []
                ),
                followup_themes=self._get_followup_themes(
                    intent_analysis["primary_intent"]
                ),
                detected_phase=llm_analysis.get("detected_phase", "all"),
                detected_bird_type=llm_analysis.get(
                    "detected_bird_type",
                    self._infer_bird_type_from_genetic_line(
                        document_context.genetic_line
                    ),
                ),
                detected_site_type=llm_analysis.get(
                    "detected_site_type", "broiler_farm"
                ),
                confidence_score=max(confidence_intent, confidence_llm * 0.9),
                reasoning=f"Intent+LLM for {document_context.genetic_line}: {intent_analysis['primary_intent']}",
            )

    def _fallback_metadata(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> ChunkMetadata:
        """Métadonnées de fallback en cas d'échec avec contexte génétique"""
        return ChunkMetadata(
            intent_category="general",
            content_type=self._infer_content_type(segment["content"]),
            technical_level="intermediate",
            age_applicability=["all_ages"],
            applicable_metrics=[],
            actionable_recommendations=self._extract_actionable_items(
                segment["content"], document_context.genetic_line
            ),
            followup_themes=[],
            detected_phase="all",
            detected_bird_type=self._infer_bird_type_from_genetic_line(
                document_context.genetic_line
            ),
            detected_site_type=self._infer_site_type_genetic_aware(
                document_context.document_type, document_context.genetic_line
            ),
            confidence_score=0.4,
            reasoning=f"Fallback analysis for {document_context.genetic_line}",
        )
