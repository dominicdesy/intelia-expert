"""
DocumentAnalyzer amélioré avec gestion robuste des réponses vides, fichiers volumineux et système d'intentions
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List
from core.models import DocumentContext
from core.llm_client import LLMClient


class DocumentAnalyzer:
    """Analyseur de documents pour extraire le contexte - VERSION RENFORCÉE avec système d'intentions"""

    def __init__(self, llm_client: LLMClient, intents_file: str = "intents.json"):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        self.intents_data = self._load_intents(intents_file)

        # Cache des patterns de détection pour performance
        self._genetic_line_patterns = self._build_genetic_line_patterns()
        self._document_type_patterns = self._build_document_type_patterns()

    def _load_intents(self, intents_file: str) -> Dict:
        """Charge le système d'intentions pour améliorer la détection"""
        try:
            if Path(intents_file).exists():
                with open(intents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.logger.info(
                        f"Système d'intentions chargé: {len(data.get('aliases', {}).get('line', {}))} lignées génétiques"
                    )
                    return data
            else:
                self.logger.warning(
                    f"Fichier intents {intents_file} non trouvé, utilisation patterns par défaut"
                )
                return {}
        except Exception as e:
            self.logger.error(f"Erreur chargement intents: {e}")
            return {}

    def _build_genetic_line_patterns(self) -> Dict[str, List[str]]:
        """Construit les patterns de détection des lignées depuis le système d'intentions"""
        patterns = {}

        if (
            self.intents_data
            and "aliases" in self.intents_data
            and "line" in self.intents_data["aliases"]
        ):
            # Utiliser les aliases du système d'intentions
            for canonical_line, aliases in self.intents_data["aliases"]["line"].items():
                # Créer des patterns regex depuis les aliases
                regex_patterns = []
                for alias in aliases:
                    # Échapper les caractères spéciaux et créer un pattern flexible
                    escaped = re.escape(alias).replace(r"\ ", r"\s*")
                    regex_patterns.append(escaped)

                # Ajouter des patterns basés sur le nom canonique
                canonical_escaped = re.escape(canonical_line).replace(r"\ ", r"\s*")
                regex_patterns.append(canonical_escaped)

                patterns[canonical_line] = regex_patterns
        else:
            # Fallback vers patterns par défaut si pas d'intents
            patterns = {
                "ross 308": [
                    r"ross\s*308",
                    r"ross.*308",
                    r"aviagen.*ross.*308",
                    r"r-?308",
                ],
                "ross 708": [r"ross\s*708", r"ross.*708", r"r-?708"],
                "cobb 500": [r"cobb\s*500", r"cobb.*500", r"c-?500"],
                "cobb 700": [r"cobb\s*700", r"cobb.*700", r"c-?700"],
                "hubbard classic": [
                    r"hubbard.*classic",
                    r"classic",
                    r"hubbard\s+classic",
                ],
                "isa brown": [r"isa.*brown", r"isa\s+brown", r"isabrown"],
                "lohmann brown": [r"lohmann.*brown", r"lohmann\s+brown", r"lb(?:\s|$)"],
            }

        self.logger.debug(f"Patterns génétiques construits: {len(patterns)} lignées")
        return patterns

    def _build_document_type_patterns(self) -> Dict[str, List[str]]:
        """Construit les patterns de détection du type de document depuis les intentions"""
        patterns = {
            "health_protocol": [
                "health",
                "disease",
                "pathology",
                "illness",
                "ascites",
                "mortality",
                "diagnostic",
                "signs",
                "symptoms",
                "treatment",
                "medication",
                "therapy",
                "vaccination",
                "vaccine",
                "immunization",
                "biosecurity",
            ],
            "performance_guide": [
                "performance",
                "target",
                "objective",
                "standard",
                "growth",
                "weight",
                "fcr",
                "feed conversion",
                "gain",
                "production index",
                "epef",
                "uniformity",
            ],
            "nutrition_manual": [
                "nutrition",
                "feed",
                "feeding",
                "diet",
                "nutrient",
                "vitamin",
                "mineral",
                "protein",
                "energy",
                "amino acid",
                "calcium",
                "phosphorus",
                "starter",
                "grower",
                "finisher",
                "phase",
                "me_kcalkg",
                "cp_pct",
            ],
            "management_guide": [
                "management",
                "guide",
                "handbook",
                "manual",
                "practice",
                "housing",
                "environment",
                "lighting",
                "ventilation",
                "temperature",
                "humidity",
                "stocking",
                "density",
                "welfare",
                "handling",
            ],
            "breeding_handbook": [
                "breed",
                "breeder",
                "reproduction",
                "parent",
                "hatch",
                "incubation",
                "fertility",
                "hatchability",
                "egg",
                "production",
                "parent stock",
                "ps",
            ],
            "biosecurity_guide": [
                "biosecurity",
                "disinfection",
                "cleaning",
                "quarantine",
                "hygiene",
                "sanitation",
                "protocol",
                "contamination",
                "prevention",
            ],
        }

        return patterns

    def analyze_document(self, json_file: str, txt_file: str = None) -> DocumentContext:
        """Analyse un document pour extraire le contexte global avec stratégie adaptative"""

        # Stratégie adaptative selon la taille du fichier
        try:
            file_size = Path(json_file).stat().st_size
            self.logger.info(
                f"Analyse document {Path(json_file).name} - Taille: {file_size} bytes"
            )

            # Adaptation des paramètres selon la taille
            if file_size > 50000:  # > 50KB
                max_tokens = 1200
                sample_size = 4000
                retries = 3
            elif file_size > 20000:  # > 20KB
                max_tokens = 1000
                sample_size = 3000
                retries = 2
            else:
                max_tokens = 800
                sample_size = 2000
                retries = 2

        except Exception:
            # Valeurs par défaut si impossible de déterminer la taille
            max_tokens = 800
            sample_size = 2000
            retries = 2

        # Tentatives d'analyse avec stratégie progressive
        for attempt in range(retries + 1):
            try:
                sample = self._extract_document_sample(
                    json_file, txt_file, max_size=sample_size
                )

                # Stratégie de prompt adaptatif
                if attempt == 0:
                    # Première tentative: prompt complet
                    prompt = self._build_analysis_prompt(sample, json_file)
                elif attempt == 1:
                    # Deuxième tentative: prompt simplifié
                    prompt = self._build_simplified_prompt(sample, json_file)
                else:
                    # Dernière tentative: prompt minimal
                    prompt = self._build_minimal_prompt(sample, json_file)

                self.logger.debug(
                    f"Tentative {attempt + 1}: prompt_length={len(prompt)}, max_tokens={max_tokens}"
                )

                # Appel LLM avec paramètres adaptatifs
                response = self.llm_client.complete(prompt, max_tokens=max_tokens)

                # Validation critique de la réponse
                if not response or not response.strip():
                    raise ValueError(
                        f"Réponse LLM vide (tentative {attempt + 1}/{retries + 1})"
                    )

                context = self._parse_response(response)

                self.logger.info(
                    f"Document analysé avec succès (tentative {attempt + 1}): {context.genetic_line} - {context.document_type}"
                )
                return context

            except Exception as e:
                self.logger.warning(
                    f"Tentative {attempt + 1}/{retries + 1} échouée: {e}"
                )

                if attempt < retries:
                    # Attendre avant retry avec backoff progressif
                    wait_time = (attempt + 1) * 2
                    self.logger.info(f"Attente {wait_time}s avant retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Toutes les tentatives échouées
                    self.logger.error(
                        "Toutes les tentatives d'analyse LLM échouées, utilisation fallback enrichi"
                    )
                    return self._fallback_context(json_file, error_details=str(e))

    def _extract_document_sample(
        self, json_file: str, txt_file: str = None, max_size: int = 2000
    ) -> str:
        """Extrait un échantillon représentatif du document avec gestion de taille adaptative"""
        sample_parts = []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Métadonnées existantes (priorité haute)
            if "metadata" in json_data:
                sample_parts.append(
                    f"Metadata: {json.dumps(json_data['metadata'], indent=2)}"
                )

            # Titre si disponible (priorité haute)
            if "title" in json_data:
                sample_parts.append(f"Title: {json_data['title']}")

            # Texte principal (adaptatif selon taille max)
            if "text" in json_data:
                text_content = json_data["text"]
                # Pour le contenu médical, privilégier le début + sections importantes
                if len(text_content) > max_size:
                    # Extraire le début et chercher des sections importantes
                    beginning = text_content[: max_size // 2]

                    # Chercher des sections importantes (causes, traitement, prévention)
                    important_sections = []
                    for keyword in [
                        "cause",
                        "treatment",
                        "prevention",
                        "minimize",
                        "management",
                    ]:
                        pattern = rf"#{1,3}.*{keyword}.*?\n(.*?)(?=\n#{1,3}|\Z)"
                        matches = re.findall(
                            pattern, text_content.lower(), re.DOTALL | re.IGNORECASE
                        )
                        if matches:
                            important_sections.extend(
                                matches[:1]
                            )  # Une section par keyword

                    combined_important = " ".join(important_sections)[: max_size // 2]
                    sample_parts.append(
                        f"Text sample: {beginning}\n\nImportant sections: {combined_important}"
                    )
                else:
                    sample_parts.append(f"Text sample: {text_content}")

            # Chunks pré-extraits (échantillon représentatif)
            if "chunks" in json_data and isinstance(json_data["chunks"], list):
                chunks = json_data["chunks"]
                # Prendre le premier, un du milieu, et le dernier chunk
                sample_chunks = []
                if len(chunks) > 0:
                    sample_chunks.append(chunks[0])  # Premier
                if len(chunks) > 2:
                    sample_chunks.append(chunks[len(chunks) // 2])  # Milieu
                if len(chunks) > 1:
                    sample_chunks.append(chunks[-1])  # Dernier

                for i, chunk in enumerate(sample_chunks):
                    chunk_content = ""
                    if isinstance(chunk, str):
                        chunk_content = chunk[:300]  # Limiter la taille
                    elif isinstance(chunk, dict) and "content" in chunk:
                        chunk_content = chunk["content"][:300]

                    if chunk_content:
                        sample_parts.append(f"Chunk {i}: {chunk_content}")

        except Exception as e:
            sample_parts.append(f"JSON processing error: {e}")
            self.logger.warning(f"Erreur extraction JSON: {e}")

        # Fichier texte complémentaire (si espace disponible)
        if txt_file and Path(txt_file).exists():
            try:
                current_size = sum(len(part) for part in sample_parts)
                remaining_space = max_size - current_size

                if remaining_space > 500:  # Seulement si assez d'espace
                    with open(txt_file, "r", encoding="utf-8") as f:
                        txt_content = f.read(remaining_space)
                        sample_parts.append(f"TXT supplement: {txt_content}")
            except Exception as e:
                sample_parts.append(f"TXT error: {e}")

        combined_sample = "\n\n".join(sample_parts)

        # Troncature finale si nécessaire
        if len(combined_sample) > max_size:
            combined_sample = (
                combined_sample[:max_size] + "\n... [content truncated for analysis]"
            )

        return combined_sample

    def _build_analysis_prompt(self, sample: str, filename: str) -> str:
        """Construit le prompt d'analyse enrichi avec le système d'intentions"""

        # Adaptation dynamique de la taille selon le contenu
        sample_size = min(3000, len(sample))
        sample_truncated = sample[:sample_size]

        # Construire la liste des lignées génétiques depuis les intentions
        genetic_lines = (
            list(self._genetic_line_patterns.keys())
            if self._genetic_line_patterns
            else [
                "ross 308",
                "ross 708",
                "cobb 500",
                "cobb 700",
                "hubbard classic",
                "isa brown",
                "lohmann brown",
            ]
        )

        genetic_lines_str = ", ".join(
            genetic_lines[:15]
        )  # Limiter pour éviter prompt trop long

        return f"""
Analyze this poultry/veterinary document and extract precise metadata.

Filename: {Path(filename).name}
Document content:
{sample_truncated}

GENETIC LINES TO DETECT:
{genetic_lines_str}

Instructions:
1. Look for specific genetic lines in the content
2. If no specific genetic line is mentioned, use "unknown"
3. Classify document types based on content focus:
   - health_protocol: diseases, treatments, vaccination, biosecurity
   - performance_guide: targets, standards, FCR, growth curves
   - nutrition_manual: feed formulation, nutrients, amino acids
   - management_guide: housing, environment, handling practices
   - breeding_handbook: reproduction, parent stock, hatchery
   - biosecurity_guide: hygiene, disinfection, quarantine

4. Detect species from context and terminology
5. Large medical/technical documents are normal in poultry industry

Return this JSON structure:
{{
    "genetic_line": "specific_line_found_or_unknown",
    "document_type": "health_protocol|management_guide|performance_guide|nutrition_manual|breeding_handbook|biosecurity_guide",
    "species": "broilers|layers|breeders|pullets|mixed|unknown", 
    "measurement_units": "metric|imperial|mixed|unknown",
    "target_audience": "veterinarians|farmers|nutritionists|technical_advisors|breeders|mixed",
    "table_types_expected": ["performance_tables", "nutrition_tables", "health_protocols", "management_guidelines", "vaccination_schedules"],
    "confidence_score": 0.7
}}

Respond with valid JSON only.
"""

    def _build_simplified_prompt(self, sample: str, filename: str) -> str:
        """Prompt simplifié pour la deuxième tentative"""
        return f"""
Analyze this poultry document: {Path(filename).name}

Content: {sample[:2000]}

Return JSON with:
- genetic_line: specific breed or "unknown"  
- document_type: health_protocol, management_guide, performance_guide, nutrition_manual
- species: broilers, layers, breeders, unknown
- confidence_score: 0.5-1.0

Format:
{{"genetic_line":"unknown","document_type":"health_protocol","species":"broilers","measurement_units":"metric","target_audience":"veterinarians","table_types_expected":["health_protocols"],"confidence_score":0.7}}
"""

    def _build_minimal_prompt(self, sample: str, filename: str) -> str:
        """Prompt minimal pour la dernière tentative"""
        # Détection basique depuis le filename et un échantillon très court
        filename_lower = Path(filename).name.lower()
        sample_short = sample[:800]

        return f"""
Document: {filename_lower}
Content: {sample_short}

Return only this JSON:
{{"genetic_line":"unknown","document_type":"management_guide","species":"broilers","measurement_units":"unknown","target_audience":"mixed","table_types_expected":[],"confidence_score":0.5}}

Replace values based on content if detected.
"""

    def _parse_response(self, response: str) -> DocumentContext:
        """Parse et valide la réponse LLM avec validation renforcée"""
        try:
            # Nettoyage préventif de la réponse
            response = response.strip()

            # Validation critique - réponse vide
            if not response:
                raise ValueError("Réponse complètement vide")

            # Nettoyage des marqueurs markdown
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            # Nouvelle validation après nettoyage
            response = response.strip()
            if not response:
                raise ValueError("Réponse vide après nettoyage markdown")

            # Tentative de parsing JSON
            try:
                data = json.loads(response)
            except json.JSONDecodeError as json_err:
                # Log détaillé pour debug
                self.logger.error(
                    f"JSON invalide. Réponse reçue: '{response[:200]}...'"
                )
                self.logger.error(f"Erreur JSON: {json_err}")
                raise ValueError(f"JSON invalide: {json_err}")

            # Validation des champs requis
            if not isinstance(data, dict):
                raise ValueError(f"Réponse JSON n'est pas un objet: {type(data)}")

            # Normalisation de la lignée génétique
            raw_genetic_line = data.get("genetic_line", "Unknown")
            normalized_genetic_line = self._normalize_genetic_line_response(
                raw_genetic_line
            )

            return DocumentContext(
                genetic_line=normalized_genetic_line,
                document_type=data.get("document_type", "unknown"),
                species=data.get("species", "unknown"),
                measurement_units=data.get("measurement_units", "unknown"),
                target_audience=data.get("target_audience", "unknown"),
                table_types_expected=data.get("table_types_expected", []),
                confidence_score=float(data.get("confidence_score", 0.0)),
                raw_analysis=response,
            )

        except Exception as e:
            self.logger.error(f"Erreur parsing réponse LLM: {e}")
            raise

    def _normalize_genetic_line_response(self, raw_genetic_line: str) -> str:
        """Normalise la réponse de lignée génétique avec le système d'intentions"""
        if not raw_genetic_line or raw_genetic_line.lower() in [
            "unknown",
            "unclear",
            "",
        ]:
            return "unknown"

        text_lower = raw_genetic_line.lower().strip()

        # Utiliser les patterns construits depuis le système d'intentions
        for canonical_line, patterns in self._genetic_line_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    self.logger.debug(
                        f"Normalisation intents: '{raw_genetic_line}' -> '{canonical_line}'"
                    )
                    return canonical_line

        # Nettoyage si aucune correspondance
        cleaned = re.sub(r"[^\w\s]", " ", raw_genetic_line).strip()
        return cleaned if cleaned else "unknown"

    def _fallback_context(
        self, json_file: str, error_details: str = None
    ) -> DocumentContext:
        """Contexte de fallback enrichi avec analyse intelligente du contenu"""
        filename = Path(json_file).name.lower()

        # Détection améliorée depuis le nom de fichier
        genetic_line = self._detect_genetic_line_from_filename(filename)
        document_type = self._detect_document_type_from_filename(filename)
        species = self._detect_species_from_filename(filename)

        # Analyse du contenu pour améliorer la détection
        content_context = {"measurement_units": "unknown", "target_audience": "unknown"}
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                content = f.read(3000).lower()  # Premier 3KB pour analyse enrichie

            # Améliorer la détection de lignée depuis le contenu
            content_genetic_line = self._detect_genetic_line_from_content(content)
            if content_genetic_line != "unknown":
                genetic_line = content_genetic_line

            # Analyser le contenu pour métriques et contexte
            detected_context = self._detect_content_metrics_and_context(content)
            content_context["measurement_units"] = detected_context["measurement_units"]

            # Détecter l'audience cible depuis le contenu
            if any(
                term in content
                for term in ["veterinary", "pathology", "disease", "diagnosis"]
            ):
                content_context["target_audience"] = "veterinarians"
            elif any(
                term in content
                for term in ["nutrition", "feed", "amino acid", "nutrient"]
            ):
                content_context["target_audience"] = "nutritionists"
            elif any(
                term in content
                for term in ["management", "housing", "production", "farm"]
            ):
                content_context["target_audience"] = "farmers"
            elif any(
                term in content for term in ["technical", "specification", "standard"]
            ):
                content_context["target_audience"] = "technical_advisors"
            else:
                content_context["target_audience"] = "mixed"

            # Ajuster le type de document basé sur le contenu détaillé
            if detected_context["intent_categories"]:
                primary_intent = detected_context["intent_categories"][0]
                if primary_intent == "protocol_query":
                    document_type = "health_protocol"
                elif (
                    primary_intent == "metric_query"
                    and "performance" in detected_context["metrics_detected"]
                ):
                    document_type = "performance_guide"
                elif primary_intent == "metric_query" and any(
                    "nutrition" in m or "feed" in m
                    for m in detected_context["metrics_detected"]
                ):
                    document_type = "nutrition_manual"

        except Exception as content_error:
            self.logger.warning(
                f"Impossible de lire le contenu pour fallback enrichi: {content_error}"
            )

        # Construire les types de tables attendus basés sur le type de document et métriques détectées
        table_types = []
        if document_type == "health_protocol":
            table_types = [
                "health_protocols",
                "vaccination_schedules",
                "diagnostic_procedures",
            ]
        elif document_type == "performance_guide":
            table_types = ["performance_tables", "growth_curves", "target_weights"]
        elif document_type == "nutrition_manual":
            table_types = [
                "nutrition_tables",
                "feed_formulations",
                "nutrient_requirements",
            ]
        elif document_type == "management_guide":
            table_types = [
                "management_guidelines",
                "environmental_settings",
                "housing_specifications",
            ]
        elif document_type == "breeding_handbook":
            table_types = [
                "breeding_schedules",
                "production_targets",
                "hatchery_protocols",
            ]
        else:
            table_types = ["performance_tables", "management_guidelines"]

        return DocumentContext(
            genetic_line=genetic_line,
            document_type=document_type,
            species=species,
            measurement_units=content_context["measurement_units"],
            target_audience=content_context["target_audience"],
            table_types_expected=table_types,
            confidence_score=0.75,  # Score plus élevé pour fallback enrichi avec intentions
            raw_analysis=f"Enhanced fallback with intents system. Error: {error_details or 'LLM response failed'}. Detected context: {str(content_context)[:200]}",
        )

    def _detect_genetic_line_from_content(self, content: str) -> str:
        """Détecte la lignée génétique directement dans le contenu avec le système d'intentions"""

        # Utiliser les patterns construits depuis le système d'intentions
        for canonical_line, patterns in self._genetic_line_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    self.logger.debug(
                        f"Détection contenu intents: '{canonical_line}' trouvé"
                    )
                    return canonical_line

        return "unknown"

    def _detect_genetic_line_from_filename(self, filename: str) -> str:
        """Détecte la lignée génétique depuis le nom de fichier avec le système d'intentions"""

        # Utiliser les aliases du système d'intentions
        if (
            self.intents_data
            and "aliases" in self.intents_data
            and "line" in self.intents_data["aliases"]
        ):
            for canonical_line, aliases in self.intents_data["aliases"]["line"].items():
                # Vérifier les aliases dans le nom de fichier
                for alias in aliases:
                    if alias.lower() in filename.lower():
                        self.logger.debug(
                            f"Détection filename intents: '{canonical_line}' via alias '{alias}'"
                        )
                        return canonical_line

        # Fallback vers patterns par défaut
        filename_patterns = {
            "ross 308": ["ross308", "ross_308", "ross-308", "aviagen", "r308"],
            "ross 708": ["ross708", "ross_708", "ross-708", "r708"],
            "cobb 500": ["cobb500", "cobb_500", "cobb-500", "c500"],
            "cobb 700": ["cobb700", "cobb_700", "cobb-700", "c700"],
            "hubbard classic": [
                "hubbard_classic",
                "hubbard-classic",
                "classic",
                "hclassic",
            ],
            "hubbard flex": ["hubbard_flex", "hubbard-flex", "flex", "hflex"],
            "isa brown": ["isa_brown", "isa-brown", "isabrown", "isa"],
            "lohmann brown": ["lohmann_brown", "lohmann-brown", "lohmann", "lb"],
        }

        for canonical_line, patterns in filename_patterns.items():
            if any(pattern in filename for pattern in patterns):
                return canonical_line

        return "unknown"

    def _detect_document_type_from_filename(self, filename: str) -> str:
        """Détecte le type de document depuis le nom de fichier avec patterns enrichis"""

        # Utiliser les patterns enrichis construits depuis les intentions
        for doc_type, patterns in self._document_type_patterns.items():
            if any(pattern in filename for pattern in patterns):
                self.logger.debug(
                    f"Type document détecté: '{doc_type}' via pattern dans filename"
                )
                return doc_type

        return "management_guide"

    def _detect_species_from_filename(self, filename: str) -> str:
        """Détecte l'espèce depuis le nom de fichier avec système d'intentions"""

        # Utiliser les aliases du système d'intentions pour bird_type
        if (
            self.intents_data
            and "aliases" in self.intents_data
            and "bird_type" in self.intents_data["aliases"]
        ):
            bird_type_aliases = self.intents_data["aliases"]["bird_type"]
            for species, aliases in bird_type_aliases.items():
                if any(alias in filename for alias in aliases):
                    # Mapper vers les espèces attendues
                    if species in ["broiler", "chair"]:
                        return "broilers"
                    elif species in ["layer", "pondeuse"]:
                        return "layers"
                    elif species in ["breeder", "reproducteur"]:
                        return "breeders"
                    elif species in ["pullet", "poulette"]:
                        return "pullets"

        # Fallback vers détection par mots-clés
        if any(word in filename for word in ["broiler", "chair", "meat", "poulet"]):
            return "broilers"
        elif any(
            word in filename for word in ["layer", "pondeuse", "egg", "laying", "ponte"]
        ):
            return "layers"
        elif any(
            word in filename
            for word in ["breed", "parent", "stock", "ps", "reproducteur"]
        ):
            return "breeders"
        elif any(word in filename for word in ["pullet", "poulette", "rearing"]):
            return "pullets"
        else:
            return "broilers"  # Par défaut

    def _detect_content_metrics_and_context(self, content: str) -> Dict[str, any]:
        """Détecte les métriques et contexte spécialisés depuis le contenu"""
        detected_context = {
            "metrics_detected": [],
            "intent_categories": [],
            "specialized_terms": [],
            "age_indicators": [],
            "measurement_units": "unknown",
        }

        # Détecter les métriques spécialisées depuis les intentions
        if self.intents_data and "intents" in self.intents_data:
            for intent_name, intent_data in self.intents_data["intents"].items():
                if "metrics" in intent_data:
                    for metric_name, metric_info in intent_data["metrics"].items():
                        # Chercher des variantes du nom de métrique dans le contenu
                        metric_variations = [
                            metric_name.replace("_", " "),
                            metric_name.replace("_", "-"),
                            metric_name,
                        ]

                        for variation in metric_variations:
                            if variation.lower() in content.lower():
                                detected_context["metrics_detected"].append(metric_name)
                                if (
                                    intent_name
                                    not in detected_context["intent_categories"]
                                ):
                                    detected_context["intent_categories"].append(
                                        intent_name
                                    )

        # Détecter les unités de mesure
        if re.search(
            r"\b(kg|g|cm|mm|m2|°c|celsius|fahrenheit|°f)\b", content, re.IGNORECASE
        ):
            detected_context["measurement_units"] = "metric"
        elif re.search(
            r"\b(lb|lbs|inch|inches|ft|feet|°f|fahrenheit)\b", content, re.IGNORECASE
        ):
            detected_context["measurement_units"] = "imperial"
        elif re.search(r"\b(kg|lb|°c|°f)\b", content, re.IGNORECASE):
            detected_context["measurement_units"] = "mixed"

        # Détecter les indicateurs d'âge
        age_patterns = [
            r"(\d+)\s*(?:days?|jours?|d)\b",
            r"(\d+)\s*(?:weeks?|semaines?|w)\b",
            r"(\d+)-(\d+)\s*(?:days?|jours?)",
            r"day\s*(\d+)",
            r"week\s*(\d+)",
        ]

        for pattern in age_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            detected_context["age_indicators"].extend(matches)

        return detected_context
