#!/usr/bin/env python3
"""
Extracteur de connaissances intelligent avec analyse LLM et injection Weaviate v4
Version complète corrigée - extrait et enrichit automatiquement les connaissances
des documents avicoles avec métadonnées intelligentes pour Weaviate.

CORRECTIONS APPLIQUÉES:
- Syntaxe Weaviate v4 complètement corrigée
- Collection name en PascalCase
- Gestion d'erreurs robuste
- Validation de conformité améliorée
- Support Unicode complet
"""

import json
import os
import re
import hashlib
import logging
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

# Gestion robuste des encodages
try:
    import chardet

    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    print("pip install chardet recommandé pour la détection automatique d'encodage")

# Chargement des variables d'environnement
try:
    from dotenv import load_dotenv

    # Cherche le .env dans le répertoire parent puis dans le répertoire courant
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Variables d'environnement chargées depuis: {env_path}")
            break
except ImportError:
    print(
        "pip install python-dotenv recommandé pour charger automatiquement les clés API"
    )


@dataclass
class DocumentContext:
    """Contexte d'un document analysé par LLM"""

    genetic_line: str
    document_type: str
    species: str
    measurement_units: str
    target_audience: str
    table_types_expected: List[str]
    confidence_score: float = 0.0
    raw_analysis: str = ""


@dataclass
class ChunkMetadata:
    """Métadonnées enrichies d'un chunk analysé"""

    intent_category: str
    content_type: str
    technical_level: str
    age_applicability: List[str]
    applicable_metrics: List[str]
    actionable_recommendations: List[str]
    followup_themes: List[str]
    detected_phase: Optional[str]
    detected_bird_type: Optional[str]
    detected_site_type: Optional[str]
    confidence_score: float = 0.0
    reasoning: str = ""


@dataclass
class KnowledgeChunk:
    """Chunk de connaissance complet"""

    chunk_id: str
    content: str
    word_count: int
    document_context: DocumentContext
    metadata: ChunkMetadata
    source_file: str
    extraction_timestamp: str


class IntentManager:
    """Gestionnaire des intents basé sur intents.json"""

    def __init__(self, intents_file_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.intents_data = self._load_intents_data(intents_file_path)

    def _load_intents_data(self, intents_file_path: str = None) -> Dict:
        """Charge les données d'intents depuis le fichier JSON"""
        if intents_file_path and Path(intents_file_path).exists():
            try:
                with open(intents_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Erreur chargement intents.json: {e}")

        # Fallback - cherche intents.json dans les répertoires parents
        search_paths = [
            Path(__file__).parent.parent / "intents.json",
            Path(__file__).parent / "intents.json",
            Path.cwd() / "intents.json",
        ]

        for path in search_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.logger.info(f"Intents chargé depuis: {path}")
                        return json.load(f)
                except Exception:
                    continue

        self.logger.warning("intents.json non trouvé - métadonnées basiques utilisées")
        return {}

    def normalize_genetic_line(self, raw_text: str) -> str:
        """Normalise une lignée génétique selon les alias d'intents.json"""
        if not self.intents_data or "aliases" not in self.intents_data:
            return raw_text

        line_aliases = self.intents_data["aliases"].get("line", {})
        text_lower = raw_text.lower()

        # Scoring pour trouver la meilleure correspondance
        best_match = None
        best_score = 0

        for canonical_line, aliases in line_aliases.items():
            score = 0

            # Score pour correspondance exacte du nom canonique
            if canonical_line.lower() in text_lower:
                score += 10

            # Score pour correspondances d'alias
            for alias in aliases:
                if alias.lower() in text_lower:
                    score += 5

            if score > best_score:
                best_score = score
                best_match = canonical_line

        return best_match if best_match else raw_text

    def detect_intent_category(self, content: str) -> Dict[str, Any]:
        """Détecte la catégorie d'intent principale d'un contenu"""
        if not self.intents_data or "intents" not in self.intents_data:
            return {"primary_intent": "general", "confidence": 0.3}

        content_lower = content.lower()
        intent_scores = {}

        # Analyse des mots-clés par intent
        for intent_name, intent_config in self.intents_data["intents"].items():
            score = 0

            # Score basé sur les métriques mentionnées
            if "metrics" in intent_config:
                for metric_name in intent_config["metrics"].keys():
                    metric_keywords = self._metric_to_keywords(metric_name)
                    for keyword in metric_keywords:
                        if keyword in content_lower:
                            score += 3

            # Score basé sur les thèmes de suivi
            if "followup_themes" in intent_config:
                for theme in intent_config["followup_themes"]:
                    theme_keywords = theme.replace("_", " ").split()
                    for keyword in theme_keywords:
                        if keyword in content_lower:
                            score += 2

            if score > 0:
                intent_scores[intent_name] = score

        if not intent_scores:
            return {"primary_intent": "general", "confidence": 0.3}

        # Retourne l'intent avec le meilleur score
        primary_intent = max(intent_scores, key=intent_scores.get)
        confidence = min(intent_scores[primary_intent] / 20.0, 1.0)  # Normalisation

        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "all_intents": list(intent_scores.keys()),
        }

    def _metric_to_keywords(self, metric_name: str) -> List[str]:
        """Convertit un nom de métrique en mots-clés recherchables"""
        custom_mapping = {
            "body_weight_target": ["body weight", "weight", "poids", "live weight"],
            "fcr_target": [
                "fcr",
                "feed conversion",
                "conversion",
                "indice consommation",
            ],
            "ambient_temp_target": ["temperature", "température", "temp", "ambient"],
            "humidity_target": ["humidity", "humidité", "rh"],
            "lighting_hours": ["lighting", "light", "éclairage", "lumière"],
            "water_intake_daily": ["water", "eau", "intake", "consommation"],
            "feed_intake_daily": ["feed", "aliment", "intake", "consommation"],
            "mortality_expected_pct": ["mortality", "mortalité", "death", "mort"],
            "stocking_density_kgm2": ["density", "densité", "stocking", "kg/m2"],
        }

        if metric_name in custom_mapping:
            return custom_mapping[metric_name]

        return metric_name.replace("_", " ").split()

    def extract_applicable_metrics(
        self, content: str, intent_category: str
    ) -> List[str]:
        """Extrait les métriques applicables mentionnées dans le contenu"""
        if not self.intents_data or "intents" not in self.intents_data:
            return []

        intent_config = self.intents_data["intents"].get(intent_category, {})
        if "metrics" not in intent_config:
            return []

        content_lower = content.lower()
        detected_metrics = []

        for metric_name in intent_config["metrics"].keys():
            metric_keywords = self._metric_to_keywords(metric_name)
            if any(keyword in content_lower for keyword in metric_keywords):
                detected_metrics.append(metric_name)

        return detected_metrics


class LLMClient:
    """Interface pour différents clients LLM avec chargement automatique des clés"""

    def __init__(self, provider="openai", api_key=None, model="gpt-4"):
        self.provider = provider.lower()
        self.logger = logging.getLogger(__name__)

        # Chargement automatique de la clé API depuis .env
        if api_key is None:
            if self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")

        self.api_key = api_key
        self.model = model
        self._setup_client()

    def _setup_client(self):
        """Configure le client LLM selon le provider"""
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("Clé OPENAI_API_KEY manquante dans .env ou paramètres")
            try:
                import openai

                self.client = openai.OpenAI(api_key=self.api_key)
                self.logger.info(f"Client OpenAI configuré avec modèle {self.model}")
            except ImportError:
                raise ImportError("pip install openai required for OpenAI provider")

        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError(
                    "Clé ANTHROPIC_API_KEY manquante dans .env ou paramètres"
                )
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.logger.info(f"Client Anthropic configuré avec modèle {self.model}")
            except ImportError:
                raise ImportError(
                    "pip install anthropic required for Anthropic provider"
                )

        elif self.provider == "mock":
            self.client = None
        else:
            raise ValueError(f"Provider non supporté: {self.provider}")

    @classmethod
    def create_auto(cls, provider="openai", model="gpt-4"):
        """Factory method pour créer un client avec chargement automatique de clé"""
        return cls(provider=provider, model=model)

    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        """Complète un prompt avec le LLM"""
        if self.provider == "mock":
            return self._mock_response(prompt)

        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

    def _mock_response(self, prompt: str) -> str:
        """Réponse mock pour tests"""
        if "analyze this document" in prompt.lower():
            return json.dumps(
                {
                    "genetic_line": "Ross 308",
                    "document_type": "health_management",
                    "species": "broilers",
                    "measurement_units": "metric",
                    "target_audience": "veterinarians",
                    "table_types_expected": [
                        "prevention_guidelines",
                        "treatment_protocols",
                    ],
                    "confidence_score": 0.9,
                }
            )
        elif "analyze this chunk" in prompt.lower():
            return json.dumps(
                {
                    "intent_category": "environment_setting",
                    "content_type": "prevention_guidelines",
                    "technical_level": "intermediate",
                    "age_applicability": ["0-42_days"],
                    "applicable_metrics": ["ambient_temp_target", "humidity_target"],
                    "actionable_recommendations": [
                        "maintain_consistent_temperature",
                        "optimize_air_quality",
                    ],
                    "followup_themes": ["ventilation_strategy", "heating_profile"],
                    "detected_phase": "all",
                    "detected_bird_type": "broiler",
                    "detected_site_type": "broiler_farm",
                    "confidence_score": 0.85,
                    "reasoning": "Content describes environmental management for broiler health",
                }
            )
        return "{}"


class DocumentAnalyzer:
    """Analyseur de documents avec LLM"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)

    def analyze_document(self, json_file: str, txt_file: str = None) -> DocumentContext:
        """Analyse un document pour extraire le contexte global"""
        try:
            sample = self._extract_document_sample(json_file, txt_file)
            prompt = self._build_document_analysis_prompt(sample, json_file)
            response = self.llm_client.complete(prompt, max_tokens=800)
            context = self._parse_document_response(response)

            self.logger.info(
                f"Document analysé: {context.genetic_line} - {context.document_type}"
            )
            return context

        except Exception as e:
            self.logger.error(f"Erreur analyse document: {e}")
            return self._fallback_document_context(json_file)

    def _extract_document_sample(self, json_file: str, txt_file: str = None) -> str:
        """Extrait un échantillon représentatif du document"""
        sample_parts = []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            if "metadata" in json_data:
                sample_parts.append(
                    f"Metadata: {json.dumps(json_data['metadata'], indent=2)}"
                )

            if "text" in json_data:
                text_sample = json_data["text"][:2000]
                sample_parts.append(f"Text sample: {text_sample}")

            if "chunks" in json_data and isinstance(json_data["chunks"], list):
                for i, chunk in enumerate(json_data["chunks"][:3]):
                    if isinstance(chunk, str):
                        chunk_sample = chunk[:500]
                        sample_parts.append(f"Chunk {i}: {chunk_sample}")

        except Exception as e:
            sample_parts.append(f"JSON error: {e}")

        if txt_file and Path(txt_file).exists():
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    txt_sample = f.read(1500)
                    sample_parts.append(f"TXT sample: {txt_sample}")
            except Exception as e:
                sample_parts.append(f"TXT error: {e}")

        return "\n\n".join(sample_parts)

    def _build_document_analysis_prompt(self, sample: str, filename: str) -> str:
        """Construit le prompt d'analyse du document"""
        return f"""
Analyze this agricultural/poultry document and extract key metadata.

Filename: {Path(filename).name}

Document sample:
{sample}

Return ONLY a valid JSON object with these fields:
{{
    "genetic_line": "exact genetic line (Ross 308, Ross 708, Cobb 500, etc.) or Unknown",
    "document_type": "type (health_management, biosecurity_guide, nutrition_specifications, etc.)",
    "species": "target species (broilers, layers, breeders, etc.)",
    "measurement_units": "primary units (metric, imperial, mixed)",
    "target_audience": "primary audience (veterinarians, farmers, nutritionists, etc.)",
    "table_types_expected": ["list", "of", "expected", "content", "types"],
    "confidence_score": 0.0-1.0
}}

Focus on extracting precise, specific information for poultry knowledge management.
"""

    def _parse_document_response(self, response: str) -> DocumentContext:
        """Parse et valide la réponse LLM"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)

            return DocumentContext(
                genetic_line=data.get("genetic_line", "Unknown"),
                document_type=data.get("document_type", "unknown"),
                species=data.get("species", "unknown"),
                measurement_units=data.get("measurement_units", "unknown"),
                target_audience=data.get("target_audience", "unknown"),
                table_types_expected=data.get("table_types_expected", []),
                confidence_score=float(data.get("confidence_score", 0.0)),
                raw_analysis=response,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Erreur parsing réponse LLM: {e}")
            raise

    def _fallback_document_context(self, json_file: str) -> DocumentContext:
        """Contexte de fallback en cas d'échec LLM"""
        filename = Path(json_file).name.lower()

        genetic_line = "Unknown"
        if "ross308" in filename or "ross_308" in filename:
            genetic_line = "Ross 308"
        elif "cobb500" in filename:
            genetic_line = "Cobb 500"

        document_type = "unknown"
        if "ascites" in filename or "health" in filename:
            document_type = "health_management"
        elif "biosec" in filename or "biosecurity" in filename:
            document_type = "biosecurity_guide"

        return DocumentContext(
            genetic_line=genetic_line,
            document_type=document_type,
            species="broilers",
            measurement_units="unknown",
            target_audience="unknown",
            table_types_expected=[],
            confidence_score=0.3,
        )


class ContentSegmenter:
    """Segmenteur de contenu intelligent pour créer des chunks sémantiques"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_chunk_words = 50
        self.max_chunk_words = 500
        self.overlap_words = 25

    def create_semantic_segments(
        self,
        json_file: str,
        txt_file: str = None,
        document_context: DocumentContext = None,
    ) -> List[Dict[str, Any]]:
        """Crée des segments sémantiques depuis les fichiers JSON/TXT"""
        try:
            # Extraction du contenu depuis JSON et TXT
            content_parts = self._extract_content_from_files(json_file, txt_file)

            # Segmentation sémantique
            segments = []

            for part_name, content in content_parts.items():
                if (
                    not content or len(content.strip()) < self.min_chunk_words * 5
                ):  # ~5 chars per word
                    continue

                part_segments = self._segment_content_intelligently(content, part_name)
                segments.extend(part_segments)

            # Post-traitement et validation
            validated_segments = self._validate_and_filter_segments(segments)

            self.logger.info(
                f"Segmentation terminée: {len(validated_segments)} segments créés"
            )
            return validated_segments

        except Exception as e:
            self.logger.error(f"Erreur segmentation: {e}")
            return []

    def _extract_content_from_files(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, str]:
        """Extrait le contenu depuis les fichiers JSON et TXT avec gestion robuste des encodages"""
        content_parts = {}

        # Extraction depuis JSON avec gestion d'encodage robuste
        try:
            with open(json_file, "r", encoding="utf-8", errors="strict") as f:
                json_data = json.load(f)
        except UnicodeDecodeError as e:
            self.logger.warning(f"Erreur encodage UTF-8 pour {json_file}: {e}")

            # Tentative de détection automatique d'encodage
            if CHARDET_AVAILABLE:
                with open(json_file, "rb") as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding = (
                        detected["encoding"]
                        if detected["confidence"] > 0.8
                        else "utf-8"
                    )
                    self.logger.info(
                        f"Encodage détecté pour {json_file}: {encoding} (confiance: {detected['confidence']:.2f})"
                    )
            else:
                encoding = "latin-1"

            try:
                with open(json_file, "r", encoding=encoding, errors="replace") as f:
                    json_data = json.load(f)
                self.logger.info(f"Fichier {json_file} lu avec encodage {encoding}")
            except Exception as e:
                self.logger.error(
                    f"Échec lecture {json_file} même avec {encoding}: {e}"
                )
                return content_parts

        try:
            # Priorité au texte principal
            if "text" in json_data and json_data["text"]:
                content_parts["main_text"] = self._normalize_unicode_content(
                    json_data["text"]
                )

            # Utilisation des chunks si disponibles
            elif "chunks" in json_data and isinstance(json_data["chunks"], list):
                for i, chunk in enumerate(json_data["chunks"]):
                    if isinstance(chunk, str) and chunk.strip():
                        content_parts[f"chunk_{i}"] = self._normalize_unicode_content(
                            chunk
                        )

        except Exception as e:
            self.logger.error(f"Erreur traitement contenu JSON {json_file}: {e}")

        # Extraction depuis TXT (prioritaire si disponible)
        if txt_file and Path(txt_file).exists():
            try:
                with open(txt_file, "r", encoding="utf-8", errors="strict") as f:
                    txt_content = f.read()
                    if txt_content and len(txt_content.strip()) > 100:
                        content_parts["txt_content"] = self._normalize_unicode_content(
                            txt_content
                        )
                        self.logger.info(
                            f"Contenu TXT lu: {len(txt_content)} caractères"
                        )

            except UnicodeDecodeError as e:
                self.logger.warning(f"Erreur encodage UTF-8 pour {txt_file}: {e}")

                # Auto-détection pour TXT
                if CHARDET_AVAILABLE:
                    with open(txt_file, "rb") as f:
                        raw_data = f.read()
                        detected = chardet.detect(raw_data)
                        encoding = (
                            detected["encoding"]
                            if detected["confidence"] > 0.8
                            else "latin-1"
                        )
                else:
                    encoding = "latin-1"

                try:
                    with open(txt_file, "r", encoding=encoding, errors="replace") as f:
                        txt_content = f.read()
                        if txt_content and len(txt_content.strip()) > 100:
                            content_parts["txt_content"] = (
                                self._normalize_unicode_content(txt_content)
                            )
                            self.logger.info(f"Fichier TXT lu avec encodage {encoding}")
                except Exception as e:
                    self.logger.error(f"Échec lecture TXT {txt_file}: {e}")

        return content_parts

    def _normalize_unicode_content(self, content: str) -> str:
        """Normalise le contenu Unicode pour éviter les problèmes d'accents"""
        if not content:
            return content

        try:
            # Normalisation NFD puis NFC pour gérer les accents composés
            normalized = unicodedata.normalize("NFD", content)
            normalized = unicodedata.normalize("NFC", normalized)

            # Suppression des caractères de contrôle problématiques (sauf \n, \t, \r)
            cleaned = "".join(
                char
                for char in normalized
                if not unicodedata.category(char).startswith("C") or char in "\n\t\r"
            )

            return cleaned

        except Exception as e:
            self.logger.warning(f"Erreur normalisation Unicode: {e}")
            return content

    def _segment_content_intelligently(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente le contenu de manière intelligente"""
        segments = []

        # Nettoyage du contenu
        content = self._clean_content(content)

        # Segmentation par structure markdown/sections
        if self._has_markdown_structure(content):
            segments = self._segment_by_markdown_sections(content, source_name)
        else:
            # Segmentation par paragraphes intelligente
            segments = self._segment_by_paragraphs(content, source_name)

        return segments

    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu en gardant la structure"""
        # Supprime les références d'images markdown
        content = re.sub(r"!\[Image description\]\([^)]*\)", "", content)

        # Normalise les espaces
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = re.sub(r"[ \t]+", " ", content)

        return content.strip()

    def _has_markdown_structure(self, content: str) -> bool:
        """Vérifie si le contenu a une structure markdown"""
        markdown_indicators = [
            r"^#+\s",  # Headers
            r"^\s*[-*]\s",  # Listes
            r"^\s*\d+\.\s",  # Listes numérotées
            r"\*\*.*\*\*",  # Gras
        ]

        for pattern in markdown_indicators:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _segment_by_markdown_sections(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente par sections markdown"""
        segments = []
        current_segment = ""
        current_header = ""

        lines = content.split("\n")

        for line in lines:
            # Détection des headers
            header_match = re.match(r"^(#+)\s+(.+)$", line.strip())

            if header_match:
                # Sauvegarde du segment précédent
                if (
                    current_segment
                    and len(current_segment.split()) >= self.min_chunk_words
                ):
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "section_header": current_header,
                            "source": source_name,
                            "word_count": len(current_segment.split()),
                            "segment_type": "markdown_section",
                        }
                    )

                # Début nouveau segment
                current_header = header_match.group(2).strip()
                current_segment = line + "\n"

            else:
                current_segment += line + "\n"

                # Vérification taille max
                if len(current_segment.split()) > self.max_chunk_words:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "section_header": current_header,
                            "source": source_name,
                            "word_count": len(current_segment.split()),
                            "segment_type": "markdown_section",
                        }
                    )
                    current_segment = ""

        # Segment final
        if current_segment and len(current_segment.split()) >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "section_header": current_header,
                    "source": source_name,
                    "word_count": len(current_segment.split()),
                    "segment_type": "markdown_section",
                }
            )

        return segments

    def _segment_by_paragraphs(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente par paragraphes avec chevauchement"""
        segments = []
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        current_chunk = ""
        current_words = 0

        for paragraph in paragraphs:
            paragraph_words = len(paragraph.split())

            # Si le paragraphe seul dépasse la limite
            if paragraph_words > self.max_chunk_words:
                # Sauvegarde du chunk actuel s'il existe
                if current_chunk:
                    segments.append(
                        {
                            "content": current_chunk.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "paragraph_group",
                        }
                    )
                    current_chunk = ""
                    current_words = 0

                # Divise le long paragraphe
                long_segments = self._split_long_paragraph(paragraph, source_name)
                segments.extend(long_segments)

            elif current_words + paragraph_words > self.max_chunk_words:
                # Sauvegarde du chunk actuel
                if current_chunk:
                    segments.append(
                        {
                            "content": current_chunk.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "paragraph_group",
                        }
                    )

                # Début nouveau chunk avec chevauchement
                current_chunk = paragraph + "\n\n"
                current_words = paragraph_words

            else:
                # Ajout au chunk actuel
                current_chunk += paragraph + "\n\n"
                current_words += paragraph_words

        # Chunk final
        if current_chunk and current_words >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_chunk.strip(),
                    "source": source_name,
                    "word_count": current_words,
                    "segment_type": "paragraph_group",
                }
            )

        return segments

    def _split_long_paragraph(
        self, paragraph: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Divise un long paragraphe en segments plus petits"""
        segments = []
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        current_segment = ""
        current_words = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_words + sentence_words > self.max_chunk_words:
                if current_segment:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "sentence_group",
                        }
                    )

                current_segment = sentence + " "
                current_words = sentence_words
            else:
                current_segment += sentence + " "
                current_words += sentence_words

        if current_segment and current_words >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "source": source_name,
                    "word_count": current_words,
                    "segment_type": "sentence_group",
                }
            )

        return segments

    def _validate_and_filter_segments(
        self, segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Valide et filtre les segments selon les critères de qualité"""
        validated = []

        for segment in segments:
            # Filtres de qualité
            word_count = segment.get("word_count", 0)
            content = segment.get("content", "")

            # Filtre taille
            if word_count < self.min_chunk_words or word_count > self.max_chunk_words:
                continue

            # Filtre contenu vide ou répétitif
            if not content or len(set(content.split())) < 10:
                continue

            # Filtre contenu trop technique (tables HTML, etc.)
            if self._is_low_quality_content(content):
                continue

            validated.append(segment)

        return validated

    def _is_low_quality_content(self, content: str) -> bool:
        """Vérifie si le contenu est de faible qualité"""
        # Contenu principalement constitué de caractères spéciaux
        special_chars_ratio = len(re.findall(r"[^a-zA-Z0-9\s]", content)) / len(content)
        if special_chars_ratio > 0.3:
            return True

        # Contenu répétitif
        words = content.split()
        unique_words = set(words)
        if len(words) > 20 and len(unique_words) / len(words) < 0.3:
            return True

        return False


class KnowledgeEnricher:
    """Enrichisseur de connaissances avec LLM et intents"""

    def __init__(self, llm_client: LLMClient, intent_manager: IntentManager):
        self.llm_client = llm_client
        self.intent_manager = intent_manager
        self.logger = logging.getLogger(__name__)

    def enrich_chunk(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> ChunkMetadata:
        """Enrichit un segment avec métadonnées avancées"""
        try:
            # Analyse des intents
            intent_analysis = self.intent_manager.detect_intent_category(
                segment["content"]
            )

            # Analyse LLM complémentaire si confiance faible
            if intent_analysis["confidence"] < 0.7:
                llm_metadata = self._llm_analyze_chunk(segment, document_context)
                merged_metadata = self._merge_analyses(intent_analysis, llm_metadata)
            else:
                merged_metadata = self._intent_to_metadata(
                    intent_analysis, segment, document_context
                )

            self.logger.debug(
                f"Chunk enrichi: {merged_metadata.intent_category} - {merged_metadata.confidence_score}"
            )
            return merged_metadata

        except Exception as e:
            self.logger.error(f"Erreur enrichissement chunk: {e}")
            return self._fallback_metadata(segment, document_context)

    def _llm_analyze_chunk(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> Dict[str, Any]:
        """Analyse LLM d'un chunk"""
        prompt = self._build_chunk_analysis_prompt(segment, document_context)
        response = self.llm_client.complete(prompt, max_tokens=600)
        return self._parse_chunk_response(response)

    def _build_chunk_analysis_prompt(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> str:
        """Construit le prompt d'analyse du chunk"""
        return f"""
Analyze this poultry knowledge chunk for metadata extraction.

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
    "content_type": "prevention|treatment|pathophysiology|management|nutrition|economics",
    "technical_level": "basic|intermediate|advanced",
    "age_applicability": ["0-14_days", "15-35_days", "36-52_days", "all_ages"],
    "applicable_metrics": ["list of relevant metrics from the content"],
    "actionable_recommendations": ["specific actionable items"],
    "followup_themes": ["related topics"],
    "detected_phase": "starter|grower|finisher|all",
    "detected_bird_type": "broiler|layer|breeder|mixed",
    "detected_site_type": "broiler_farm|layer_farm|hatchery|feed_mill",
    "confidence_score": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Focus on actionable knowledge for poultry professionals.
"""

    def _parse_chunk_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse LLM pour un chunk"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            return json.loads(response)

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Erreur parsing réponse chunk LLM: {e}")
            return {}

    def _intent_to_metadata(
        self,
        intent_analysis: Dict[str, Any],
        segment: Dict[str, Any],
        document_context: DocumentContext,
    ) -> ChunkMetadata:
        """Convertit l'analyse d'intent en métadonnées"""
        intent_category = intent_analysis["primary_intent"]

        # Extraction des métriques applicables
        applicable_metrics = self.intent_manager.extract_applicable_metrics(
            segment["content"], intent_category
        )

        # Détection des recommandations actionnables
        actionable_recommendations = self._extract_actionable_items(segment["content"])

        return ChunkMetadata(
            intent_category=intent_category,
            content_type=self._infer_content_type(segment["content"]),
            technical_level=self._assess_technical_level(segment["content"]),
            age_applicability=self._detect_age_applicability(segment["content"]),
            applicable_metrics=applicable_metrics,
            actionable_recommendations=actionable_recommendations,
            followup_themes=self._get_followup_themes(intent_category),
            detected_phase=self._detect_phase(segment["content"]),
            detected_bird_type=document_context.species,
            detected_site_type=self._infer_site_type(document_context.document_type),
            confidence_score=intent_analysis["confidence"],
            reasoning=f"Intent-based analysis: {intent_category}",
        )

    def _extract_actionable_items(self, content: str) -> List[str]:
        """Extrait les éléments actionnables du contenu"""
        actionable_patterns = [
            r"maintain\s+([^.]+)",
            r"keep\s+([^.]+)",
            r"avoid\s+([^.]+)",
            r"ensure\s+([^.]+)",
            r"provide\s+([^.]+)",
            r"use\s+([^.]+)",
            r"follow\s+([^.]+)",
        ]

        actionable_items = []
        content_lower = content.lower()

        for pattern in actionable_patterns:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                if 10 < len(match) < 100:  # Filtre longueur raisonnable
                    clean_action = re.sub(r"[^a-zA-Z0-9\s-]", "", match).strip()
                    if clean_action:
                        actionable_items.append(clean_action[:50])  # Limite longueur

        return list(set(actionable_items))[:10]  # Max 10 items uniques

    def _infer_content_type(self, content: str) -> str:
        """Infère le type de contenu"""
        content_lower = content.lower()

        if any(word in content_lower for word in ["prevent", "avoid", "control"]):
            return "prevention"
        elif any(word in content_lower for word in ["treat", "therapy", "medication"]):
            return "treatment"
        elif any(
            word in content_lower for word in ["cause", "pathogenesis", "disease"]
        ):
            return "pathophysiology"
        elif any(
            word in content_lower for word in ["manage", "housing", "environment"]
        ):
            return "management"
        elif any(word in content_lower for word in ["feed", "nutrition", "protein"]):
            return "nutrition"
        elif any(word in content_lower for word in ["cost", "economic", "profit"]):
            return "economics"
        else:
            return "general"

    def _assess_technical_level(self, content: str) -> str:
        """Évalue le niveau technique du contenu"""
        technical_indicators = {
            "advanced": [
                "pathogenesis",
                "etiology",
                "histopathology",
                "immunosuppressive",
                "metabolic",
            ],
            "intermediate": [
                "vaccination",
                "biosecurity",
                "management",
                "protocol",
                "diagnosis",
            ],
            "basic": ["feed", "water", "temperature", "housing", "cleaning"],
        }

        content_lower = content.lower()

        for level, indicators in technical_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return level

        # Par défaut basé sur la longueur et complexité
        return "intermediate" if len(content.split()) > 200 else "basic"

    def _detect_age_applicability(self, content: str) -> List[str]:
        """Détecte l'applicabilité par âge"""
        age_patterns = {
            "0-14_days": ["chick", "day-old", "starter", "early", "hatch"],
            "15-35_days": ["grower", "growing", "middle", "develop"],
            "36-52_days": ["finisher", "finishing", "slaughter", "market"],
            "all_ages": ["all", "throughout", "entire", "whole"],
        }

        content_lower = content.lower()
        applicable_ages = []

        for age_range, indicators in age_patterns.items():
            if any(indicator in content_lower for indicator in indicators):
                applicable_ages.append(age_range)

        # Si aucune mention spécifique, assume applicable à tous
        return applicable_ages if applicable_ages else ["all_ages"]

    def _detect_phase(self, content: str) -> Optional[str]:
        """Détecte la phase d'élevage"""
        phase_indicators = {
            "starter": ["starter", "chick", "0-10", "day-old", "early"],
            "grower": ["grower", "growing", "11-28", "15-35", "middle"],
            "finisher": ["finisher", "finishing", "29-42", "36-52", "slaughter"],
        }

        content_lower = content.lower()

        for phase, indicators in phase_indicators.items():
            if any(indicator in content_lower for indicator in indicators):
                return phase

        return "all"

    def _infer_site_type(self, document_type: str) -> Optional[str]:
        """Infère le type de site basé sur le type de document"""
        site_mapping = {
            "health_management": "broiler_farm",
            "biosecurity_guide": "broiler_farm",
            "nutrition_specifications": "feed_mill",
            "hatchery_management": "hatchery",
            "layer_management": "layer_farm",
        }

        return site_mapping.get(document_type, "broiler_farm")

    def _get_followup_themes(self, intent_category: str) -> List[str]:
        """Récupère les thèmes de suivi pour un intent"""
        if not self.intent_manager.intents_data:
            return []

        intent_config = self.intent_manager.intents_data.get("intents", {}).get(
            intent_category, {}
        )
        return intent_config.get("followup_themes", [])

    def _merge_analyses(
        self, intent_analysis: Dict[str, Any], llm_analysis: Dict[str, Any]
    ) -> ChunkMetadata:
        """Fusionne les analyses intent et LLM"""
        # Priorise LLM si confiance intent faible
        confidence_intent = intent_analysis.get("confidence", 0.0)
        confidence_llm = llm_analysis.get("confidence_score", 0.0)

        if confidence_llm > confidence_intent:
            # Utilise principalement LLM
            return ChunkMetadata(
                intent_category=llm_analysis.get("intent_category", "general"),
                content_type=llm_analysis.get("content_type", "general"),
                technical_level=llm_analysis.get("technical_level", "basic"),
                age_applicability=llm_analysis.get("age_applicability", ["all_ages"]),
                applicable_metrics=llm_analysis.get("applicable_metrics", []),
                actionable_recommendations=llm_analysis.get(
                    "actionable_recommendations", []
                ),
                followup_themes=llm_analysis.get("followup_themes", []),
                detected_phase=llm_analysis.get("detected_phase"),
                detected_bird_type=llm_analysis.get("detected_bird_type"),
                detected_site_type=llm_analysis.get("detected_site_type"),
                confidence_score=confidence_llm,
                reasoning=llm_analysis.get("reasoning", "LLM analysis"),
            )
        else:
            # Utilise principalement intent avec compléments LLM
            return ChunkMetadata(
                intent_category=intent_analysis["primary_intent"],
                content_type=llm_analysis.get("content_type", "general"),
                technical_level=llm_analysis.get("technical_level", "basic"),
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
                detected_phase=llm_analysis.get("detected_phase"),
                detected_bird_type=llm_analysis.get("detected_bird_type"),
                detected_site_type=llm_analysis.get("detected_site_type"),
                confidence_score=max(confidence_intent, confidence_llm),
                reasoning=f"Merged: {intent_analysis['primary_intent']} + LLM",
            )

    def _fallback_metadata(
        self, segment: Dict[str, Any], document_context: DocumentContext
    ) -> ChunkMetadata:
        """Métadonnées de fallback en cas d'échec"""
        return ChunkMetadata(
            intent_category="general",
            content_type=self._infer_content_type(segment["content"]),
            technical_level="basic",
            age_applicability=["all_ages"],
            applicable_metrics=[],
            actionable_recommendations=self._extract_actionable_items(
                segment["content"]
            ),
            followup_themes=[],
            detected_phase="all",
            detected_bird_type=document_context.species,
            detected_site_type="broiler_farm",
            confidence_score=0.3,
            reasoning="Fallback analysis",
        )


class ContentValidator:
    """Validateur de conformité pour l'injection Weaviate avec gestion des accents"""

    def __init__(self, weaviate_client, collection_name: str):
        self.client = weaviate_client
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)

    async def comprehensive_validation(
        self, original_chunks: List[KnowledgeChunk], source_file: str
    ) -> Dict[str, Any]:
        """Validation complète avec gestion des accents et retry automatique + logging détaillé"""
        max_retries = 3
        retry_delay = 1  # seconde

        # Statistiques de validation détaillées
        validation_stats = {
            "total_chunks": len(original_chunks),
            "method_1_success": 0,  # Filter
            "method_2_success": 0,  # Dictionary
            "method_3_success": 0,  # Batches
            "method_4_success": 0,  # GraphQL
            "total_failures": 0,
            "retrieval_details": [],
        }

        self.logger.info(
            f"🔍 Validation démarrée: {validation_stats['total_chunks']} chunks à valider"
        )

        for attempt in range(max_retries):
            try:
                # Reset des statistiques par tentative
                if attempt > 0:
                    validation_stats["retrieval_details"].clear()
                    validation_stats["method_1_success"] = 0
                    validation_stats["method_2_success"] = 0
                    validation_stats["method_3_success"] = 0
                    validation_stats["method_4_success"] = 0
                    validation_stats["total_failures"] = 0

                # Récupération depuis Weaviate avec retry
                if attempt > 0:
                    self.logger.info(f"🔄 Tentative de validation #{attempt + 1}")
                    await asyncio.sleep(retry_delay * attempt)  # Délai progressif

                injected_data = await self._fetch_injected_chunks_with_stats(
                    original_chunks, validation_stats
                )

                # Logs statistiques détaillés
                self.logger.info("📊 Statistiques de récupération:")
                self.logger.info(
                    f"   • Méthode Filter: {validation_stats['method_1_success']}"
                )
                self.logger.info(
                    f"   • Méthode Dict: {validation_stats['method_2_success']}"
                )
                self.logger.info(
                    f"   • Méthode Batches: {validation_stats['method_3_success']}"
                )
                self.logger.info(
                    f"   • Méthode GraphQL: {validation_stats['method_4_success']}"
                )
                self.logger.info(
                    f"   • Échecs totaux: {validation_stats['total_failures']}"
                )
                self.logger.info(
                    f"   • Récupérés: {len(injected_data)}/{validation_stats['total_chunks']}"
                )

                if not injected_data:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"⚠️ Tentative {attempt + 1} - Aucune donnée récupérée, retry dans {retry_delay * (attempt + 1)}s..."
                        )
                        continue
                    else:
                        return {
                            "conformity_score": 0.0,
                            "error": f"Aucune donnée récupérée de Weaviate après {max_retries} tentatives",
                            "requires_correction": True,
                            "validation_stats": validation_stats,
                        }

                # Si on a récupéré des données, continuer avec la validation normale
                break

            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"⚠️ Erreur tentative {attempt + 1}: {e}, retry..."
                    )
                    continue
                else:
                    self.logger.error(
                        f"❌ Erreur validation après {max_retries} tentatives: {e}"
                    )
                    return {
                        "conformity_score": 0.0,
                        "error": str(e),
                        "requires_correction": True,
                        "validation_stats": validation_stats,
                    }

        # 2. Validation multi-niveaux
        validations = {
            "content_integrity": self._validate_content_with_unicode(
                original_chunks, injected_data
            ),
            "metadata_consistency": self._validate_metadata_consistency(
                original_chunks, injected_data
            ),
            "encoding_preservation": self._validate_encoding_preservation(
                original_chunks, injected_data
            ),
            "completeness": self._validate_completeness(original_chunks, injected_data),
        }

        # 3. Score de conformité global
        conformity_score = self._calculate_conformity_score(validations)

        return {
            "conformity_score": conformity_score,
            "validations": validations,
            "requires_correction": conformity_score < 0.95,
            "source_file": source_file,
            "validation_attempts": attempt + 1,  # Nombre de tentatives utilisées
            "validation_stats": validation_stats,  # Statistiques détaillées
        }

    async def _fetch_injected_chunks_with_stats(
        self, original_chunks: List[KnowledgeChunk], stats: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Version avec statistiques détaillées de _fetch_injected_chunks"""
        injected_data = []

        try:
            collection = self.client.collections.get(self.collection_name)

            # Compter les chunks récupérés par méthode
            for chunk_idx, chunk in enumerate(original_chunks):
                success_method = None

                try:
                    # Méthode 1: Essai avec Filter (Weaviate v4 moderne)
                    try:
                        from weaviate.classes.query import Filter

                        response = collection.query.fetch_objects(
                            where=Filter.by_property("chunk_id").equal(chunk.chunk_id),
                            limit=1,
                        )
                        if (
                            response
                            and hasattr(response, "objects")
                            and response.objects
                        ):
                            success_method = "Filter"
                            stats["method_1_success"] += 1
                        else:
                            raise Exception("Pas de résultats avec Filter")

                    except Exception as filter_error:
                        self.logger.debug(
                            f"Filter échoué pour chunk {chunk_idx}: {filter_error}"
                        )

                        # Méthode 2: Syntaxe dictionnaire
                        try:
                            response = collection.query.fetch_objects(
                                where={
                                    "path": ["chunk_id"],
                                    "operator": "Equal",
                                    "valueText": chunk.chunk_id,
                                },
                                limit=1,
                            )
                            if (
                                response
                                and hasattr(response, "objects")
                                and response.objects
                            ):
                                success_method = "Dictionary"
                                stats["method_2_success"] += 1
                            else:
                                raise Exception("Pas de résultats avec Dict")

                        except Exception as dict_error:
                            self.logger.debug(
                                f"Dict échoué pour chunk {chunk_idx}: {dict_error}"
                            )

                            # Méthode 3: GraphQL direct (plus fiable pour recherche spécifique)
                            try:
                                query = f"""
                                {{
                                    Get {{
                                        {self.collection_name}(
                                            where: {{
                                                path: ["chunk_id"],
                                                operator: Equal,
                                                valueText: "{chunk.chunk_id}"
                                            }},
                                            limit: 1
                                        ) {{
                                            chunk_id
                                            content
                                            genetic_line
                                            intent_category
                                            confidence_score
                                            applicable_metrics
                                            _additional {{ id }}
                                        }}
                                    }}
                                }}
                                """

                                result = self.client.query.raw(query)

                                if (
                                    result
                                    and "data" in result
                                    and "Get" in result["data"]
                                    and self.collection_name in result["data"]["Get"]
                                    and result["data"]["Get"][self.collection_name]
                                ):

                                    obj = result["data"]["Get"][self.collection_name][0]
                                    injected_data.append(
                                        {
                                            "content": obj.get("content", ""),
                                            "chunk_id": obj.get("chunk_id", ""),
                                            "genetic_line": obj.get("genetic_line", ""),
                                            "intent_category": obj.get(
                                                "intent_category", ""
                                            ),
                                            "confidence_score": obj.get(
                                                "confidence_score", 0.0
                                            ),
                                            "applicable_metrics": obj.get(
                                                "applicable_metrics", []
                                            ),
                                        }
                                    )
                                    success_method = "GraphQL"
                                    stats["method_4_success"] += 1
                                    continue
                                else:
                                    raise Exception("Pas de résultats avec GraphQL")

                            except Exception as graphql_error:
                                self.logger.debug(
                                    f"GraphQL échoué pour chunk {chunk_idx}: {graphql_error}"
                                )
                                self.logger.error(
                                    f"Toutes les méthodes ont échoué pour {chunk.chunk_id}"
                                )
                                stats["total_failures"] += 1
                                continue

                    # Traitement des résultats pour les méthodes 1 et 2
                    if response and hasattr(response, "objects") and response.objects:
                        obj = response.objects[0]
                        injected_data.append(
                            {
                                "content": obj.properties.get("content", ""),
                                "chunk_id": obj.properties.get("chunk_id", ""),
                                "genetic_line": obj.properties.get("genetic_line", ""),
                                "intent_category": obj.properties.get(
                                    "intent_category", ""
                                ),
                                "confidence_score": obj.properties.get(
                                    "confidence_score", 0.0
                                ),
                                "applicable_metrics": obj.properties.get(
                                    "applicable_metrics", []
                                ),
                                **obj.properties,
                            }
                        )

                except Exception as chunk_error:
                    self.logger.error(
                        f"Erreur complète pour chunk {chunk_idx} ({chunk.chunk_id}): {chunk_error}"
                    )
                    stats["total_failures"] += 1
                    continue

        except Exception as e:
            self.logger.error(f"Erreur récupération chunks: {e}")

        return injected_data

    async def _fetch_injected_chunks(
        self, original_chunks: List[KnowledgeChunk]
    ) -> List[Dict[str, Any]]:
        """Récupère les chunks injectés depuis Weaviate - COMPATIBILITÉ UNIVERSELLE"""
        injected_data = []

        try:
            collection = self.client.collections.get(self.collection_name)

            for chunk in original_chunks:
                try:
                    # Méthode 1: Essai avec Filter (Weaviate v4 moderne)
                    try:
                        from weaviate.classes.query import Filter

                        response = collection.query.fetch_objects(
                            where=Filter.by_property("chunk_id").equal(chunk.chunk_id),
                            limit=1,
                        )
                    except (ImportError, TypeError, AttributeError) as filter_error:
                        self.logger.debug(f"Filter non disponible: {filter_error}")

                        # Méthode 2: Syntaxe dictionnaire (Weaviate v4 early)
                        try:
                            response = collection.query.fetch_objects(
                                where={
                                    "path": ["chunk_id"],
                                    "operator": "Equal",
                                    "valueText": chunk.chunk_id,
                                },
                                limit=1,
                            )
                        except (TypeError, AttributeError) as dict_error:
                            self.logger.debug(
                                f"Syntaxe dictionnaire échouée: {dict_error}"
                            )

                            # Méthode 3: fetch_objects sans where (récupération de tous puis filtrage)
                            try:
                                # Récupération limitée d'objets puis filtrage local
                                response_all = collection.query.fetch_objects(limit=100)

                                # Recherche locale du chunk
                                found = False
                                if hasattr(response_all, "objects"):
                                    for obj in response_all.objects:
                                        if (
                                            hasattr(obj, "properties")
                                            and obj.properties.get("chunk_id")
                                            == chunk.chunk_id
                                        ):
                                            injected_data.append(
                                                {
                                                    "content": obj.properties.get(
                                                        "content", ""
                                                    ),
                                                    "chunk_id": obj.properties.get(
                                                        "chunk_id", ""
                                                    ),
                                                    "genetic_line": obj.properties.get(
                                                        "genetic_line", ""
                                                    ),
                                                    "intent_category": obj.properties.get(
                                                        "intent_category", ""
                                                    ),
                                                    "confidence_score": obj.properties.get(
                                                        "confidence_score", 0.0
                                                    ),
                                                    "applicable_metrics": obj.properties.get(
                                                        "applicable_metrics", []
                                                    ),
                                                    **obj.properties,
                                                }
                                            )
                                            found = True
                                            break

                                if not found:
                                    self.logger.warning(
                                        f"Chunk {chunk.chunk_id} non trouvé avec fetch_objects général"
                                    )
                                continue

                            except Exception as fetch_all_error:
                                self.logger.error(
                                    f"Méthode fetch_objects général échouée pour {chunk.chunk_id}: {fetch_all_error}"
                                )

                                # Méthode 4: Utilisation directe du client Weaviate v3 style
                                try:
                                    # Fallback complet vers l'API GraphQL directe
                                    query = f"""
                                    {{
                                        Get {{
                                            {self.collection_name}(
                                                where: {{
                                                    path: ["chunk_id"],
                                                    operator: Equal,
                                                    valueText: "{chunk.chunk_id}"
                                                }},
                                                limit: 1
                                            ) {{
                                                chunk_id
                                                content
                                                genetic_line
                                                intent_category
                                                confidence_score
                                                applicable_metrics
                                            }}
                                        }}
                                    }}
                                    """

                                    # Exécution de la requête GraphQL
                                    result = self.client.query.raw(query)

                                    if (
                                        result
                                        and "data" in result
                                        and "Get" in result["data"]
                                        and self.collection_name
                                        in result["data"]["Get"]
                                        and result["data"]["Get"][self.collection_name]
                                    ):

                                        obj = result["data"]["Get"][
                                            self.collection_name
                                        ][0]
                                        injected_data.append(
                                            {
                                                "content": obj.get("content", ""),
                                                "chunk_id": obj.get("chunk_id", ""),
                                                "genetic_line": obj.get(
                                                    "genetic_line", ""
                                                ),
                                                "intent_category": obj.get(
                                                    "intent_category", ""
                                                ),
                                                "confidence_score": obj.get(
                                                    "confidence_score", 0.0
                                                ),
                                                "applicable_metrics": obj.get(
                                                    "applicable_metrics", []
                                                ),
                                            }
                                        )
                                    else:
                                        self.logger.warning(
                                            f"Chunk {chunk.chunk_id} non trouvé avec GraphQL"
                                        )
                                    continue

                                except Exception as graphql_error:
                                    self.logger.error(
                                        f"Toutes les méthodes ont échoué pour {chunk.chunk_id}: {graphql_error}"
                                    )
                                    continue

                    # Traitement des résultats pour les méthodes 1 et 2
                    if response and hasattr(response, "objects") and response.objects:
                        obj = response.objects[0]
                        injected_data.append(
                            {
                                "content": obj.properties.get("content", ""),
                                "chunk_id": obj.properties.get("chunk_id", ""),
                                "genetic_line": obj.properties.get("genetic_line", ""),
                                "intent_category": obj.properties.get(
                                    "intent_category", ""
                                ),
                                "confidence_score": obj.properties.get(
                                    "confidence_score", 0.0
                                ),
                                "applicable_metrics": obj.properties.get(
                                    "applicable_metrics", []
                                ),
                                **obj.properties,
                            }
                        )
                    else:
                        self.logger.warning(
                            f"Chunk {chunk.chunk_id} non trouvé dans Weaviate"
                        )

                except Exception as chunk_error:
                    self.logger.error(
                        f"Erreur récupération chunk {chunk.chunk_id}: {chunk_error}"
                    )
                    continue

        except Exception as e:
            self.logger.error(f"Erreur récupération chunks: {e}")

        return injected_data

    def _validate_content_with_unicode(
        self, original_chunks: List[KnowledgeChunk], injected_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validation spéciale pour les accents et caractères spéciaux"""
        mismatches = []

        for original, injected in zip(original_chunks, injected_data):
            if not injected:
                mismatches.append(
                    {
                        "chunk_id": original.chunk_id,
                        "error": "Chunk manquant dans Weaviate",
                    }
                )
                continue

            # Normalisation Unicode des deux côtés
            original_normalized = unicodedata.normalize("NFC", original.content)
            injected_normalized = unicodedata.normalize(
                "NFC", injected.get("content", "")
            )

            # Comparaison byte-level pour être sûr
            original_bytes = original_normalized.encode("utf-8")
            injected_bytes = injected_normalized.encode("utf-8")

            if original_bytes != injected_bytes:
                # Analyse détaillée des différences
                accent_issues = self._detect_accent_corruption(
                    original_normalized, injected_normalized
                )

                mismatches.append(
                    {
                        "chunk_id": original.chunk_id,
                        "byte_length_diff": len(original_bytes) - len(injected_bytes),
                        "char_length_diff": len(original_normalized)
                        - len(injected_normalized),
                        "accent_corruption": accent_issues,
                        "char_diff_sample": self._show_char_diff(
                            original_normalized[:200], injected_normalized[:200]
                        ),
                    }
                )

        total_chunks = len(original_chunks)
        perfect_matches = total_chunks - len(mismatches)

        return {
            "total_chunks": total_chunks,
            "perfect_matches": perfect_matches,
            "content_mismatches": len(mismatches),
            "integrity_rate": perfect_matches / total_chunks if total_chunks > 0 else 0,
            "corruption_details": mismatches[:5],  # Limite à 5 exemples
        }

    def _detect_accent_corruption(self, original: str, injected: str) -> Dict[str, Any]:
        """Détecte spécifiquement les problèmes d'accents"""
        accent_chars = (
            "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿšœžÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŠŒŽ"
        )

        original_accents = [c for c in original if c in accent_chars]
        injected_accents = [c for c in injected if c in accent_chars]

        lost_accents = len(original_accents) - len(injected_accents)
        preservation_rate = (
            len(injected_accents) / len(original_accents) if original_accents else 1.0
        )

        return {
            "original_accent_count": len(original_accents),
            "injected_accent_count": len(injected_accents),
            "lost_accents": lost_accents,
            "accent_preservation_rate": preservation_rate,
            "critical_loss": lost_accents > 0,
        }

    def _show_char_diff(self, original: str, injected: str) -> Dict[str, str]:
        """Montre un échantillon des différences de caractères"""
        return {
            "original_sample": repr(original),
            "injected_sample": repr(injected),
            "first_difference": self._find_first_difference(original, injected),
        }

    def _find_first_difference(self, str1: str, str2: str) -> str:
        """Trouve la première différence entre deux chaînes"""
        for i, (c1, c2) in enumerate(zip(str1, str2)):
            if c1 != c2:
                return f"Position {i}: '{c1}' vs '{c2}' (codes: {ord(c1)} vs {ord(c2)})"

        if len(str1) != len(str2):
            return f"Longueurs différentes: {len(str1)} vs {len(str2)}"

        return "Aucune différence détectée"

    def _validate_metadata_consistency(
        self, original_chunks: List[KnowledgeChunk], injected_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Valide la cohérence des métadonnées"""
        inconsistencies = []

        critical_fields = [
            "genetic_line",
            "intent_category",
            "technical_level",
            "confidence_score",
        ]

        for original, injected in zip(original_chunks, injected_data):
            if not injected:
                continue

            chunk_inconsistencies = {}

            # Vérification des champs critiques
            for field in critical_fields:
                if hasattr(original.metadata, field):
                    original_val = getattr(original.metadata, field, None)
                elif hasattr(original.document_context, field):
                    original_val = getattr(original.document_context, field, None)
                else:
                    continue

                injected_val = injected.get(field, None)

                if original_val != injected_val:
                    chunk_inconsistencies[field] = {
                        "original": original_val,
                        "injected": injected_val,
                    }

            if chunk_inconsistencies:
                inconsistencies.append(
                    {
                        "chunk_id": original.chunk_id,
                        "inconsistencies": chunk_inconsistencies,
                    }
                )

        return {
            "total_validated": len(original_chunks),
            "consistent_chunks": len(original_chunks) - len(inconsistencies),
            "inconsistent_chunks": len(inconsistencies),
            "consistency_rate": (
                (len(original_chunks) - len(inconsistencies)) / len(original_chunks)
                if original_chunks
                else 1.0
            ),
            "inconsistency_details": inconsistencies[:3],  # Limite à 3 exemples
        }

    def _validate_encoding_preservation(
        self, original_chunks: List[KnowledgeChunk], injected_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validation spécifique de la préservation des encodages"""
        encoding_issues = []
        total_accents_lost = 0

        for original, injected in zip(original_chunks, injected_data):
            if not injected:
                continue

            accent_analysis = self._detect_accent_corruption(
                original.content, injected.get("content", "")
            )

            if accent_analysis["critical_loss"]:
                encoding_issues.append(
                    {
                        "chunk_id": original.chunk_id,
                        "lost_accents": accent_analysis["lost_accents"],
                        "preservation_rate": accent_analysis[
                            "accent_preservation_rate"
                        ],
                    }
                )
                total_accents_lost += accent_analysis["lost_accents"]

        return {
            "chunks_with_encoding_issues": len(encoding_issues),
            "total_accents_lost": total_accents_lost,
            "encoding_preservation_rate": (
                (len(original_chunks) - len(encoding_issues)) / len(original_chunks)
                if original_chunks
                else 1.0
            ),
            "critical_encoding_loss": total_accents_lost > 0,
            "encoding_issues_details": encoding_issues[:3],
        }

    def _validate_completeness(
        self, original_chunks: List[KnowledgeChunk], injected_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Vérifie la complétude des données injectées"""
        # Reconstruction du texte original
        original_text = " ".join([chunk.content for chunk in original_chunks])
        original_words = set(original_text.lower().split())

        # Reconstruction du texte injecté
        injected_text = " ".join(
            [chunk.get("content", "") for chunk in injected_data if chunk]
        )
        injected_words = set(injected_text.lower().split())

        # Analyse des pertes
        missing_words = original_words - injected_words
        added_words = injected_words - original_words
        preserved_words = original_words & injected_words

        return {
            "original_word_count": len(original_words),
            "injected_word_count": len(injected_words),
            "preserved_word_count": len(preserved_words),
            "missing_words_count": len(missing_words),
            "added_words_count": len(added_words),
            "word_preservation_rate": (
                len(preserved_words) / len(original_words) if original_words else 1.0
            ),
            "critical_missing": [w for w in missing_words if len(w) > 6][
                :10
            ],  # Mots importants perdus
        }

    def _calculate_conformity_score(self, validations: Dict[str, Any]) -> float:
        """Calcule un score global de conformité"""
        scores = []
        weights = []

        # Score d'intégrité du contenu (poids 40%)
        if "content_integrity" in validations:
            scores.append(validations["content_integrity"]["integrity_rate"])
            weights.append(0.4)

        # Score de cohérence métadonnées (poids 25%)
        if "metadata_consistency" in validations:
            scores.append(validations["metadata_consistency"]["consistency_rate"])
            weights.append(0.25)

        # Score préservation encodage (poids 25%)
        if "encoding_preservation" in validations:
            scores.append(
                validations["encoding_preservation"]["encoding_preservation_rate"]
            )
            weights.append(0.25)

        # Score complétude (poids 10%)
        if "completeness" in validations:
            scores.append(validations["completeness"]["word_preservation_rate"])
            weights.append(0.1)

        # Calcul pondéré
        if scores and weights:
            weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
            return min(1.0, max(0.0, weighted_score))

        return 0.0


class WeaviateIngester:
    """Ingesteur Weaviate v4 avec gestion des erreurs et validation robuste"""

    def __init__(self, collection_name: str = "InteliaExpertKnowledge"):
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)
        self.client = None
        self._setup_weaviate_client()

    def _setup_weaviate_client(self):
        """Configure le client Weaviate v4"""
        try:
            import weaviate

            # Configuration du client avec les paramètres du cluster
            weaviate_url = os.getenv(
                "WEAVIATE_URL", "https://intelia-expert-rag-9rhqrfcv.weaviate.network"
            )
            api_key = os.getenv("WEAVIATE_API_KEY")

            if not api_key:
                raise ValueError("WEAVIATE_API_KEY manquante dans .env")

            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(api_key),
                headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")},
            )

            self.logger.info(f"Client Weaviate configuré: {weaviate_url}")

            # Vérification de la collection
            self._ensure_collection_exists()

        except ImportError:
            raise ImportError(
                "pip install weaviate-client required for Weaviate integration"
            )
        except Exception as e:
            self.logger.error(f"Erreur configuration Weaviate: {e}")
            raise

    def _ensure_collection_exists(self):
        """Vérifie et crée la collection si nécessaire"""
        try:
            if not self.client.collections.exists(self.collection_name):
                self.logger.info(f"Création de la collection {self.collection_name}")
                self._create_collection()
            else:
                self.logger.info(f"Collection {self.collection_name} trouvée")

        except Exception as e:
            self.logger.error(f"Erreur vérification collection: {e}")

    def _create_collection(self):
        """Crée la collection Weaviate avec le schéma approprié - SCHÉMA V4 OPTIMISÉ"""
        from weaviate.classes.config import Configure, Property, DataType

        try:
            self.client.collections.create(
                name=self.collection_name,
                properties=[
                    # Contenu principal vectorisé
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        description="Contenu principal du chunk de connaissance",
                    ),
                    # Métadonnées de contexte (non vectorisées)
                    Property(
                        name="genetic_line",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Lignée génétique",
                    ),
                    Property(
                        name="document_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de document source",
                    ),
                    Property(
                        name="species",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Espèce cible",
                    ),
                    Property(
                        name="target_audience",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Audience cible",
                    ),
                    # Métadonnées d'intent
                    Property(
                        name="intent_category",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Catégorie d'intent principal",
                    ),
                    Property(
                        name="content_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de contenu",
                    ),
                    Property(
                        name="technical_level",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Niveau technique",
                    ),
                    Property(
                        name="detected_phase",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Phase d'élevage détectée",
                    ),
                    Property(
                        name="detected_bird_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type d'oiseau détecté",
                    ),
                    Property(
                        name="detected_site_type",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Type de site détecté",
                    ),
                    # Listes (arrays)
                    Property(
                        name="age_applicability",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Tranches d'âge applicables",
                    ),
                    Property(
                        name="applicable_metrics",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Métriques applicables",
                    ),
                    Property(
                        name="actionable_recommendations",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Recommandations actionnables",
                    ),
                    Property(
                        name="followup_themes",
                        data_type=DataType.TEXT_ARRAY,
                        skip_vectorization=True,
                        description="Thèmes de suivi suggérés",
                    ),
                    # Métadonnées techniques
                    Property(
                        name="confidence_score",
                        data_type=DataType.NUMBER,
                        skip_vectorization=True,
                        description="Score de confiance de l'analyse",
                    ),
                    Property(
                        name="word_count",
                        data_type=DataType.INT,
                        skip_vectorization=True,
                        description="Nombre de mots du chunk",
                    ),
                    Property(
                        name="source_file",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Fichier source",
                    ),
                    Property(
                        name="extraction_timestamp",
                        data_type=DataType.DATE,
                        skip_vectorization=True,
                        description="Timestamp d'extraction",
                    ),
                    Property(
                        name="chunk_id",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                        description="Identifiant unique du chunk",
                    ),
                ],
                vectorizer_config=Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small", vectorize_collection_name=False
                ),
            )

            self.logger.info(f"Collection {self.collection_name} créée avec succès")

        except Exception as e:
            self.logger.error(f"Erreur création collection: {e}")
            raise

    async def ingest_batch(
        self, knowledge_chunks: List[KnowledgeChunk]
    ) -> Dict[str, Any]:
        """Ingère un batch de chunks dans Weaviate avec gestion robuste des erreurs"""
        results = {
            "success": [],
            "errors": [],
            "total_processed": len(knowledge_chunks),
            "success_count": 0,
            "error_count": 0,
        }

        if not knowledge_chunks:
            self.logger.warning("Aucun chunk à ingérer")
            return results

        try:
            collection = self.client.collections.get(self.collection_name)

            # Préparation des objets à ingérer
            objects_to_insert = []

            for chunk in knowledge_chunks:
                try:
                    obj = self._prepare_weaviate_object(chunk)
                    objects_to_insert.append(obj)
                except Exception as e:
                    error_msg = f"Erreur préparation chunk {chunk.chunk_id}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(
                        {"chunk_id": chunk.chunk_id, "error": str(e)}
                    )
                    continue

            # Insertion par batch
            if objects_to_insert:
                response = collection.data.insert_many(objects_to_insert)

                # Traitement des résultats
                if hasattr(response, "uuids"):
                    results["success_count"] = len(response.uuids)
                    results["success"] = [
                        {"uuid": str(uuid)} for uuid in response.uuids
                    ]

                if hasattr(response, "errors") and response.errors:
                    for error in response.errors:
                        results["errors"].append(
                            {"error": str(error), "type": "insertion_error"}
                        )
                        results["error_count"] += 1

                self.logger.info(
                    f"Ingestion terminée: {results['success_count']} succès, {results['error_count']} erreurs"
                )

        except Exception as e:
            self.logger.error(f"Erreur ingestion batch: {e}")
            results["errors"].append({"error": str(e), "type": "batch_error"})
            results["error_count"] += 1

        return results

    def _prepare_weaviate_object(self, chunk: KnowledgeChunk) -> Dict[str, Any]:
        """Prépare un objet pour insertion Weaviate avec validation Unicode et format de date RFC3339"""

        # Formatage RFC3339 pour la date (requis par Weaviate)
        try:
            # Convertit ISO format vers RFC3339
            timestamp_dt = datetime.fromisoformat(chunk.extraction_timestamp)
            rfc3339_timestamp = timestamp_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except Exception:
            # Fallback si problème de parsing
            rfc3339_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return {
            "content": chunk.content,
            "genetic_line": chunk.document_context.genetic_line,
            "document_type": chunk.document_context.document_type,
            "species": chunk.document_context.species,
            "target_audience": chunk.document_context.target_audience,
            "intent_category": chunk.metadata.intent_category,
            "content_type": chunk.metadata.content_type,
            "technical_level": chunk.metadata.technical_level,
            "detected_phase": chunk.metadata.detected_phase,
            "detected_bird_type": chunk.metadata.detected_bird_type,
            "detected_site_type": chunk.metadata.detected_site_type,
            "age_applicability": chunk.metadata.age_applicability,
            "applicable_metrics": chunk.metadata.applicable_metrics,
            "actionable_recommendations": chunk.metadata.actionable_recommendations,
            "followup_themes": chunk.metadata.followup_themes,
            "confidence_score": chunk.metadata.confidence_score,
            "word_count": chunk.word_count,
            "source_file": chunk.source_file,
            "extraction_timestamp": rfc3339_timestamp,  # Format RFC3339 requis
            "chunk_id": chunk.chunk_id,
        }

    async def validate_injection(self, chunk_ids: List[str]) -> Dict[str, Any]:
        """Valide que les chunks ont été correctement injectés - SYNTAXE V4 CORRIGÉE"""
        validation_results = {
            "validated_count": 0,
            "missing_count": 0,
            "validation_success_rate": 0.0,
            "missing_chunks": [],
        }

        try:
            # Import Filter une seule fois au début
            try:
                from weaviate.classes.query import Filter
            except ImportError:
                # Fallback pour versions plus anciennes
                self.logger.warning("Filter non disponible, validation basique")
                return validation_results

            collection = self.client.collections.get(self.collection_name)

            for chunk_id in chunk_ids:
                try:
                    # SYNTAXE WEAVIATE V4 CORRIGÉE - AVEC FILTER
                    response = collection.query.fetch_objects(
                        where=Filter.by_property("chunk_id").equal(chunk_id),
                        limit=1,
                    )

                    if response.objects:
                        validation_results["validated_count"] += 1
                    else:
                        validation_results["missing_count"] += 1
                        validation_results["missing_chunks"].append(chunk_id)

                except Exception as chunk_error:
                    self.logger.error(
                        f"Erreur validation chunk {chunk_id}: {chunk_error}"
                    )
                    validation_results["missing_count"] += 1
                    validation_results["missing_chunks"].append(chunk_id)

            total = len(chunk_ids)
            validation_results["validation_success_rate"] = (
                validation_results["validated_count"] / total if total > 0 else 0
            )

            self.logger.info(
                f"Validation: {validation_results['validated_count']}/{total} chunks trouvés"
            )

        except Exception as e:
            self.logger.error(f"Erreur validation injection: {e}")

        return validation_results

    def close(self):
        """Ferme la connexion Weaviate"""
        if self.client:
            self.client.close()


class IntelligentKnowledgeExtractor:
    """Extracteur de connaissances intelligent principal avec validation de conformité complète"""

    def __init__(
        self,
        output_dir: str = "extracted_knowledge",
        llm_client: LLMClient = None,
        intents_file: str = None,
        collection_name: str = "InteliaExpertKnowledge",
        auto_correct: bool = True,
        conformity_threshold: float = 0.95,
    ):
        # Configuration des répertoires
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configuration du logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Paramètres de validation
        self.auto_correct = auto_correct
        self.conformity_threshold = conformity_threshold

        # Client LLM
        if llm_client is None:
            self.llm_client = LLMClient(provider="mock")
        else:
            self.llm_client = llm_client

        # Composants
        self.intent_manager = IntentManager(intents_file)
        self.document_analyzer = DocumentAnalyzer(self.llm_client)
        self.content_segmenter = ContentSegmenter()
        self.knowledge_enricher = KnowledgeEnricher(
            self.llm_client, self.intent_manager
        )
        self.weaviate_ingester = WeaviateIngester(collection_name)

        # Validateur de conformité
        self.content_validator = ContentValidator(
            self.weaviate_ingester.client, collection_name
        )

        # Statistiques
        self.extraction_stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "chunks_injected": 0,
            "validation_failures": 0,
            "corrections_applied": 0,
            "errors": 0,
        }

        self.logger.info(
            f"Extracteur de connaissances initialisé - LLM: {self.llm_client.provider}"
        )
        self.logger.info(
            f"Validation de conformité activée - Seuil: {conformity_threshold:.1%}"
        )

    async def process_document(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, Any]:
        """Traite un document complet avec analyse LLM, injection Weaviate et validation de conformité"""
        try:
            self.logger.info(f"Traitement intelligent: {Path(json_file).name}")

            # 1. Analyse du contexte du document
            document_context = self.document_analyzer.analyze_document(
                json_file, txt_file
            )

            # 2. Normalisation avec intents.json
            document_context.genetic_line = self.intent_manager.normalize_genetic_line(
                f"{document_context.genetic_line} {document_context.raw_analysis}"
            )

            # 3. Segmentation sémantique intelligente avec gestion Unicode
            segments = self.content_segmenter.create_semantic_segments(
                json_file, txt_file, document_context
            )

            if not segments:
                self.logger.warning(f"Aucun segment créé pour {json_file}")
                return self._empty_result()

            self.logger.info(f"Segments créés: {len(segments)}")

            # 4. Enrichissement avec métadonnées avancées
            knowledge_chunks = []
            timestamp = datetime.now().isoformat()

            for i, segment in enumerate(segments):
                try:
                    # Enrichissement métadonnées
                    metadata = self.knowledge_enricher.enrich_chunk(
                        segment, document_context
                    )

                    # Création chunk complet
                    chunk_id = self._generate_chunk_id(json_file, i, segment)

                    chunk = KnowledgeChunk(
                        chunk_id=chunk_id,
                        content=segment["content"],
                        word_count=segment.get(
                            "word_count", len(segment["content"].split())
                        ),
                        document_context=document_context,
                        metadata=metadata,
                        source_file=json_file,
                        extraction_timestamp=timestamp,
                    )

                    knowledge_chunks.append(chunk)

                except Exception as e:
                    self.logger.error(f"Erreur enrichissement segment {i}: {e}")
                    self.extraction_stats["errors"] += 1
                    continue

            # 5. Filtrage qualité
            validated_chunks = self._quality_filter(knowledge_chunks)

            # 6. Injection Weaviate
            injection_results = await self.weaviate_ingester.ingest_batch(
                validated_chunks
            )

            # 6.5. Attente pour l'indexation Weaviate (éviter les problèmes de timing)
            if injection_results["success_count"] > 0:
                self.logger.info(
                    f"⏳ Attente de l'indexation Weaviate ({injection_results['success_count']} objets)..."
                )
                await asyncio.sleep(2)  # Attente de 2 secondes pour l'indexation

            # 7. Validation complète avec gestion accents
            self.logger.info("Validation de conformité en cours...")
            comprehensive_validation = (
                await self.content_validator.comprehensive_validation(
                    validated_chunks, json_file
                )
            )

            # 8. Actions correctives si nécessaire
            correction_results = None
            if comprehensive_validation["requires_correction"]:
                self.logger.warning(
                    f"Conformité insuffisante: {comprehensive_validation['conformity_score']:.1%} "
                    f"(seuil: {self.conformity_threshold:.1%})"
                )
                self.extraction_stats["validation_failures"] += 1

                if self.auto_correct:
                    self.logger.info("Application des corrections automatiques...")
                    correction_results = await self._perform_corrections(
                        validated_chunks, comprehensive_validation
                    )
                    comprehensive_validation["corrections_applied"] = correction_results
                    self.extraction_stats["corrections_applied"] += 1
            else:
                self.logger.info(
                    f"Validation réussie: {comprehensive_validation['conformity_score']:.1%}"
                )

            # 9. Mise à jour statistiques
            self.extraction_stats["documents_processed"] += 1
            self.extraction_stats["chunks_created"] += len(segments)
            self.extraction_stats["chunks_injected"] += injection_results[
                "success_count"
            ]

            # 10. Sauvegarde rapport local enrichi
            report_path = self._save_comprehensive_report(
                json_file,
                document_context,
                segments,
                injection_results,
                comprehensive_validation,
                correction_results,
            )

            result = {
                "document": Path(json_file).name,
                "document_context": asdict(document_context),
                "segments_created": len(segments),
                "chunks_validated": len(validated_chunks),
                "injection_success": injection_results["success_count"],
                "injection_errors": injection_results["error_count"],
                "conformity_validation": comprehensive_validation,
                "encoding_issues_detected": comprehensive_validation.get(
                    "validations", {}
                )
                .get("encoding_preservation", {})
                .get("critical_encoding_loss", False),
                "corrections_applied": correction_results is not None,
                "final_conformity_score": comprehensive_validation.get(
                    "conformity_score", 0.0
                ),
                "report_path": report_path,
            }

            self.logger.info(
                f"Traitement terminé: {result['injection_success']}/{result['segments_created']} chunks injectés "
                f"- Conformité: {result['final_conformity_score']:.1%}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Erreur traitement document: {e}")
            self.extraction_stats["errors"] += 1
            return self._error_result(str(e))

    async def _perform_corrections(
        self, validated_chunks: List[KnowledgeChunk], validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Applique des corrections automatiques basées sur les résultats de validation"""
        corrections = {
            "reinjection_attempted": False,
            "reinjection_success": 0,
            "encoding_fixes": 0,
            "metadata_fixes": 0,
        }

        try:
            validations = validation_results.get("validations", {})

            # Correction des problèmes d'encodage critiques
            encoding_issues = validations.get("encoding_preservation", {})
            if encoding_issues.get("critical_encoding_loss", False):
                self.logger.info("Correction des problèmes d'encodage...")

                # Re-normalisation Unicode plus agressive
                for chunk in validated_chunks:
                    original_content = chunk.content

                    # Double normalisation
                    normalized = unicodedata.normalize("NFD", chunk.content)
                    normalized = unicodedata.normalize("NFC", normalized)

                    if normalized != original_content:
                        chunk.content = normalized
                        corrections["encoding_fixes"] += 1

                # Re-injection des chunks corrigés
                if corrections["encoding_fixes"] > 0:
                    self.logger.info(
                        f"Re-injection de {corrections['encoding_fixes']} chunks corrigés"
                    )
                    reinjection_results = await self.weaviate_ingester.ingest_batch(
                        validated_chunks
                    )
                    corrections["reinjection_attempted"] = True
                    corrections["reinjection_success"] = reinjection_results[
                        "success_count"
                    ]

            self.logger.info(f"Corrections appliquées: {corrections}")

        except Exception as e:
            self.logger.error(f"Erreur lors des corrections: {e}")
            corrections["error"] = str(e)

        return corrections

    def _save_comprehensive_report(
        self,
        json_file: str,
        document_context: DocumentContext,
        segments: List[Dict[str, Any]],
        injection_results: Dict[str, Any],
        validation_results: Dict[str, Any],
        correction_results: Optional[Dict[str, Any]],
    ) -> str:
        """Sauvegarde un rapport d'extraction complet avec validation"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_file": json_file,
            "document_analysis": asdict(document_context),
            "segmentation_results": {
                "total_segments": len(segments),
                "segment_types": list(
                    set(seg.get("segment_type", "unknown") for seg in segments)
                ),
                "avg_word_count": (
                    sum(seg.get("word_count", 0) for seg in segments) / len(segments)
                    if segments
                    else 0
                ),
                "unicode_normalization_applied": True,
            },
            "injection_results": injection_results,
            "conformity_validation": validation_results,
            "correction_results": correction_results,
            "extraction_stats": self.extraction_stats.copy(),
        }

        report_filename = f"comprehensive_report_{Path(json_file).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.output_dir / report_filename

        with open(report_path, "w", encoding="utf-8", errors="strict") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(report_path)

    def _generate_chunk_id(
        self, json_file: str, index: int, segment: Dict[str, Any]
    ) -> str:
        """Génère un ID unique pour un chunk"""
        filename = Path(json_file).stem
        content_hash = hashlib.md5(segment["content"].encode()).hexdigest()[:8]
        return f"{filename}_{index:03d}_{content_hash}"

    def _quality_filter(
        self, knowledge_chunks: List[KnowledgeChunk]
    ) -> List[KnowledgeChunk]:
        """Filtre les chunks selon les critères de qualité"""
        validated = []

        for chunk in knowledge_chunks:
            # Filtres de qualité
            if chunk.word_count < 50 or chunk.word_count > 500:
                continue

            if chunk.metadata.confidence_score < 0.3:
                continue

            if not chunk.content or len(chunk.content.strip()) < 100:
                continue

            # Filtre contenu dupliqué
            if self._is_duplicate_content(chunk, validated):
                continue

            validated.append(chunk)

        self.logger.info(
            f"Filtrage qualité: {len(validated)}/{len(knowledge_chunks)} chunks validés"
        )
        return validated

    def _is_duplicate_content(
        self, chunk: KnowledgeChunk, existing_chunks: List[KnowledgeChunk]
    ) -> bool:
        """Vérifie si le contenu est dupliqué"""
        chunk_words = set(chunk.content.lower().split())

        for existing in existing_chunks:
            existing_words = set(existing.content.lower().split())

            # Calcul similarité Jaccard
            intersection = len(chunk_words & existing_words)
            union = len(chunk_words | existing_words)

            similarity = intersection / union if union > 0 else 0

            if similarity > 0.8:  # Seuil de similarité
                return True

        return False

    def _empty_result(self) -> Dict[str, Any]:
        """Résultat vide"""
        return {
            "document": "",
            "document_context": {},
            "segments_created": 0,
            "chunks_validated": 0,
            "injection_success": 0,
            "injection_errors": 0,
            "validation_rate": 0.0,
            "report_path": "",
        }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Résultat d'erreur"""
        return {
            "document": "",
            "error": error_msg,
            "segments_created": 0,
            "chunks_validated": 0,
            "injection_success": 0,
            "injection_errors": 1,
            "validation_rate": 0.0,
            "report_path": "",
        }

    async def process_directory(
        self, json_dir: str, pattern: str = "*.json", recursive: bool = True
    ) -> Dict[str, Any]:
        """Traite tous les fichiers d'un répertoire"""
        json_dir_path = Path(json_dir)

        if not json_dir_path.exists():
            raise FileNotFoundError(f"Répertoire non trouvé: {json_dir}")

        if recursive:
            json_files = list(json_dir_path.rglob(pattern))
        else:
            json_files = list(json_dir_path.glob(pattern))

        if not json_files:
            self.logger.warning(f"Aucun fichier JSON trouvé dans {json_dir}")
            return {}

        self.logger.info(f"Traitement de {len(json_files)} fichiers")

        results = {}
        for json_file in json_files:
            try:
                txt_file = self._find_corresponding_txt_file(str(json_file))
                result = await self.process_document(str(json_file), txt_file)
                results[str(json_file)] = result

            except Exception as e:
                self.logger.error(f"Erreur avec {json_file.name}: {e}")
                results[str(json_file)] = self._error_result(str(e))

        # Génération du rapport de synthèse
        summary_report = self._generate_summary_report(results, json_dir)

        return {"summary": summary_report, "individual_results": results}

    def _find_corresponding_txt_file(self, json_file_path: str) -> Optional[str]:
        """Trouve le fichier TXT correspondant au fichier JSON"""
        json_path = Path(json_file_path)

        possible_txt_paths = [
            json_path.with_suffix(".txt"),
            json_path.parent
            / (json_path.name.replace("_extracted.json", "_extracted.txt")),
            json_path.parent / (json_path.stem.replace("_extracted", "") + ".txt"),
        ]

        for txt_path in possible_txt_paths:
            if txt_path.exists():
                return str(txt_path)

        return None

    def _generate_summary_report(
        self, results: Dict[str, Any], base_dir: str
    ) -> Dict[str, Any]:
        """Génère un rapport de synthèse"""
        total_files = len(results)
        successful_files = sum(
            1 for r in results.values() if r.get("injection_success", 0) > 0
        )
        total_chunks_injected = sum(
            r.get("injection_success", 0) for r in results.values()
        )
        total_errors = sum(r.get("injection_errors", 0) for r in results.values())

        summary = {
            "timestamp": datetime.now().isoformat(),
            "base_directory": base_dir,
            "total_files_processed": total_files,
            "successful_files": successful_files,
            "failed_files": total_files - successful_files,
            "total_chunks_injected": total_chunks_injected,
            "total_errors": total_errors,
            "success_rate": successful_files / total_files if total_files > 0 else 0,
            "avg_chunks_per_file": (
                total_chunks_injected / successful_files if successful_files > 0 else 0
            ),
            "extraction_stats": self.extraction_stats.copy(),
        }

        # Sauvegarde du rapport
        summary_path = (
            self.output_dir
            / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Rapport de synthèse sauvegardé: {summary_path}")

        return summary

    def get_extraction_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'extraction"""
        stats = self.extraction_stats.copy()

        if stats["chunks_created"] > 0:
            stats["injection_rate"] = stats["chunks_injected"] / stats["chunks_created"]
        else:
            stats["injection_rate"] = 0.0

        if stats["documents_processed"] > 0:
            stats["avg_chunks_per_document"] = (
                stats["chunks_created"] / stats["documents_processed"]
            )
        else:
            stats["avg_chunks_per_document"] = 0.0

        return stats

    def close(self):
        """Ferme les connexions"""
        if hasattr(self.weaviate_ingester, "close"):
            self.weaviate_ingester.close()


# =============================================================================
# FONCTIONS UTILITAIRES ET CLI
# =============================================================================


def main():
    """Interface en ligne de commande complète"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extracteur de connaissances intelligent pour Weaviate v4"
    )
    parser.add_argument("input_path", help="Chemin vers fichier JSON ou répertoire")
    parser.add_argument(
        "--llm-provider",
        choices=["openai", "anthropic", "mock"],
        default="openai",
        help="Provider LLM à utiliser",
    )
    parser.add_argument("--llm-model", default="gpt-4", help="Modèle LLM à utiliser")
    parser.add_argument("--intents-file", help="Chemin vers intents.json")
    parser.add_argument(
        "--collection",
        default="InteliaExpertKnowledge",
        help="Nom de la collection Weaviate",
    )
    parser.add_argument(
        "--output-dir",
        default="extracted_knowledge",
        help="Répertoire de sortie pour les rapports",
    )
    parser.add_argument(
        "--pattern", default="*.json", help="Pattern de fichiers à traiter"
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Traitement récursif des répertoires"
    )
    parser.add_argument(
        "--no-auto-correct",
        action="store_true",
        help="Désactive la correction automatique",
    )
    parser.add_argument(
        "--conformity-threshold",
        type=float,
        default=0.95,
        help="Seuil de conformité (0.0-1.0)",
    )

    args = parser.parse_args()

    async def run_extraction():
        try:
            # Configuration du client LLM
            if args.llm_provider == "mock":
                llm_client = LLMClient(provider="mock")
                print("Mode MOCK activé - Pas d'appels LLM réels")
            else:
                llm_client = LLMClient.create_auto(
                    provider=args.llm_provider, model=args.llm_model
                )
                print(f"Client LLM configuré: {args.llm_provider}/{args.llm_model}")

            # Création de l'extracteur
            extractor = IntelligentKnowledgeExtractor(
                output_dir=args.output_dir,
                llm_client=llm_client,
                intents_file=args.intents_file,
                collection_name=args.collection,
                auto_correct=not args.no_auto_correct,
                conformity_threshold=args.conformity_threshold,
            )

            input_path = Path(args.input_path)

            if input_path.is_file():
                # Traitement d'un seul fichier
                txt_file = extractor._find_corresponding_txt_file(str(input_path))
                result = await extractor.process_document(str(input_path), txt_file)

                print("\nRésultat du traitement:")
                print(f"Document: {result['document']}")
                print(f"Segments créés: {result['segments_created']}")
                print(f"Chunks injectés: {result['injection_success']}")
                print(f"Erreurs: {result['injection_errors']}")
                print(
                    f"Conformité finale: {result.get('final_conformity_score', 0):.1%}"
                )
                print(
                    f"Corrections appliquées: {'Oui' if result.get('corrections_applied', False) else 'Non'}"
                )

            elif input_path.is_dir():
                # Traitement d'un répertoire
                results = await extractor.process_directory(
                    str(input_path), pattern=args.pattern, recursive=args.recursive
                )

                summary = results["summary"]
                print("\nRésultat du traitement par lots:")
                print(f"Fichiers traités: {summary['total_files_processed']}")
                print(f"Fichiers réussis: {summary['successful_files']}")
                print(f"Chunks injectés: {summary['total_chunks_injected']}")
                print(f"Taux de succès: {summary['success_rate']:.1%}")
                print(f"Moyenne chunks/fichier: {summary['avg_chunks_per_file']:.1f}")

            else:
                print(f"Erreur: Chemin invalide {args.input_path}")
                return 1

            # Statistiques finales
            stats = extractor.get_extraction_statistics()
            print("\nStatistiques d'extraction:")
            print(f"Documents traités: {stats['documents_processed']}")
            print(f"Chunks créés: {stats['chunks_created']}")
            print(f"Chunks injectés: {stats['chunks_injected']}")
            print(f"Taux d'injection: {stats['injection_rate']:.1%}")
            print(f"Échecs de validation: {stats['validation_failures']}")
            print(f"Corrections appliquées: {stats['corrections_applied']}")

            # Fermeture
            extractor.close()

            return 0

        except Exception as e:
            print(f"Erreur: {e}")
            return 1

    # Exécution
    exit_code = asyncio.run(run_extraction())
    exit(exit_code)


def quick_extract(
    json_path: str,
    txt_path: str = None,
    llm_provider: str = "openai",
    collection_name: str = "InteliaExpertKnowledge",
) -> Dict[str, Any]:
    """Fonction utilitaire pour extraction rapide"""

    async def extract():
        llm_client = LLMClient.create_auto(provider=llm_provider)
        extractor = IntelligentKnowledgeExtractor(
            llm_client=llm_client, collection_name=collection_name
        )

        try:
            result = await extractor.process_document(json_path, txt_path)
            return result
        finally:
            extractor.close()

    return asyncio.run(extract())


# =============================================================================
# TESTS ET VALIDATION
# =============================================================================


async def test_weaviate_v4_connectivity(
    collection_name: str = "InteliaExpertKnowledge",
) -> Dict[str, Any]:
    """Test de connectivité Weaviate v4 avec syntaxe corrigée"""
    test_results = {
        "connection_success": False,
        "collection_exists": False,
        "query_syntax_works": False,
        "error_details": [],
    }

    try:
        import weaviate

        # Test connexion
        weaviate_url = os.getenv(
            "WEAVIATE_URL", "https://intelia-expert-rag-9rhqrfcv.weaviate.network"
        )
        api_key = os.getenv("WEAVIATE_API_KEY")

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key),
        )

        test_results["connection_success"] = True

        # Test collection
        if client.collections.exists(collection_name):
            test_results["collection_exists"] = True

            # Test syntaxe de requête v4
            collection = client.collections.get(collection_name)

            try:
                # Test syntaxe de requête v4 - pas besoin de stocker le résultat
                collection.query.fetch_objects(
                    where={
                        "path": ["chunk_id"],
                        "operator": "Equal",
                        "valueText": "test_chunk_nonexistent",
                    },
                    limit=1,
                )
                test_results["query_syntax_works"] = True

            except Exception as query_error:
                test_results["error_details"].append(
                    f"Erreur syntaxe requête: {query_error}"
                )

        client.close()

    except Exception as e:
        test_results["error_details"].append(f"Erreur connexion: {e}")

    return test_results


if __name__ == "__main__":
    main()
