"""
Analyseur de documents avec LLM - VERSION CORRIGÉE
Support complet des lignées génétiques multiples
"""

import json
import logging
import re
from pathlib import Path
from core.models import DocumentContext
from core.llm_client import LLMClient


class DocumentAnalyzer:
    """Analyseur de documents pour extraire le contexte - VERSION MULTI-LIGNÉES"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)

    def analyze_document(self, json_file: str, txt_file: str = None) -> DocumentContext:
        """Analyse un document pour extraire le contexte global"""
        try:
            sample = self._extract_document_sample(json_file, txt_file)
            prompt = self._build_analysis_prompt(sample, json_file)
            response = self.llm_client.complete(prompt, max_tokens=800)
            context = self._parse_response(response)

            self.logger.info(
                f"Document analysé: {context.genetic_line} - {context.document_type}"
            )
            return context

        except Exception as e:
            self.logger.error(f"Erreur analyse document: {e}")
            return self._fallback_context(json_file)

    def _extract_document_sample(self, json_file: str, txt_file: str = None) -> str:
        """Extrait un échantillon représentatif du document"""
        sample_parts = []

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Métadonnées existantes
            if "metadata" in json_data:
                sample_parts.append(
                    f"Metadata: {json.dumps(json_data['metadata'], indent=2)}"
                )

            # Texte principal
            if "text" in json_data:
                sample_parts.append(f"Text sample: {json_data['text'][:2000]}")

            # Titre si disponible
            if "title" in json_data:
                sample_parts.append(f"Title: {json_data['title']}")

            # Chunks pré-extraits
            if "chunks" in json_data and isinstance(json_data["chunks"], list):
                for i, chunk in enumerate(json_data["chunks"][:3]):
                    if isinstance(chunk, str):
                        sample_parts.append(f"Chunk {i}: {chunk[:500]}")
                    elif isinstance(chunk, dict) and "content" in chunk:
                        sample_parts.append(f"Chunk {i}: {chunk['content'][:500]}")

        except Exception as e:
            sample_parts.append(f"JSON error: {e}")

        # Fichier texte complémentaire
        if txt_file and Path(txt_file).exists():
            try:
                with open(txt_file, "r", encoding="utf-8") as f:
                    sample_parts.append(f"TXT sample: {f.read(1500)}")
            except Exception as e:
                sample_parts.append(f"TXT error: {e}")

        return "\n\n".join(sample_parts)

    def _build_analysis_prompt(self, sample: str, filename: str) -> str:
        """Construit le prompt d'analyse du document - VERSION MULTI-LIGNÉES"""
        return f"""
Analyze this poultry/agricultural document and extract precise metadata.

Filename: {Path(filename).name}

Document sample:
{sample}

IMPORTANT: Identify the specific genetic line mentioned in the document. Look for:
- Ross breeds: Ross 308, Ross 708, etc.
- Cobb breeds: Cobb 500, Cobb 700, Cobb 400, etc.  
- Hubbard breeds: Hubbard Classic, Hubbard Flex, etc.
- Layer breeds: ISA Brown, Lohmann Brown, Hy-Line, etc.

Return ONLY a valid JSON object with these fields:
{{
    "genetic_line": "EXACT genetic line found (e.g., 'Ross 308', 'Cobb 500', 'Hubbard Classic') or 'Unknown' if unclear",
    "document_type": "management_guide|performance_guide|nutrition_manual|health_protocol|biosecurity_guide|breeding_handbook",
    "species": "broilers|layers|breeders|mixed|unknown",
    "measurement_units": "metric|imperial|mixed|unknown",
    "target_audience": "farmers|veterinarians|nutritionists|technical_advisors|mixed",
    "table_types_expected": ["performance_tables", "nutrition_tables", "management_guidelines", "health_protocols"],
    "confidence_score": 0.0-1.0
}}

Focus on extracting the EXACT genetic line name as mentioned in the document.
"""

    def _parse_response(self, response: str) -> DocumentContext:
        """Parse et valide la réponse LLM avec normalisation génétique"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)

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

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Erreur parsing réponse LLM: {e}")
            raise

    def _normalize_genetic_line_response(self, raw_genetic_line: str) -> str:
        """Normalise la réponse de lignée génétique du LLM"""
        if not raw_genetic_line or raw_genetic_line.lower() in ["unknown", "unclear"]:
            return "unknown"

        text_lower = raw_genetic_line.lower().strip()

        # Patterns de normalisation pour les réponses LLM
        normalization_patterns = {
            "ross 308": [
                r"ross\s*308",
                r"ross.*308",
                r"aviagen.*ross.*308",
                r"r-?308",
                r"ross\s+308",
                r"ross308",
            ],
            "ross 708": [r"ross\s*708", r"ross.*708", r"r-?708"],
            "cobb 500": [
                r"cobb\s*500",
                r"cobb.*500",
                r"c-?500",
                r"cobb\s+500",
                r"cobb500",
            ],
            "cobb 700": [r"cobb\s*700", r"cobb.*700", r"c-?700"],
            "cobb 400": [r"cobb\s*400", r"cobb.*400", r"c-?400"],
            "hubbard classic": [r"hubbard.*classic", r"classic", r"hubbard\s+classic"],
            "hubbard flex": [r"hubbard.*flex", r"flex", r"hubbard\s+flex"],
            "hubbard color": [r"hubbard.*color", r"color.*broiler", r"hubbard\s+color"],
            "isa brown": [r"isa.*brown", r"isa\s+brown", r"isabrown"],
            "isa white": [r"isa.*white", r"isa\s+white"],
            "lohmann brown": [r"lohmann.*brown", r"lohmann\s+brown", r"lb(?:\s|$)"],
            "lohmann white": [r"lohmann.*white", r"lohmann\s+white", r"lsl"],
            "hy-line brown": [
                r"hy-?line.*brown",
                r"hyline.*brown",
                r"hy\s*line\s+brown",
            ],
        }

        # Recherche de correspondance avec les patterns
        for canonical_line, patterns in normalization_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    self.logger.debug(
                        f"Normalisation LLM: '{raw_genetic_line}' -> '{canonical_line}'"
                    )
                    return canonical_line

        # Si aucune correspondance, nettoyer et retourner
        cleaned = re.sub(r"[^\w\s]", " ", raw_genetic_line).strip()
        return cleaned if cleaned else "unknown"

    def _fallback_context(self, json_file: str) -> DocumentContext:
        """Contexte de fallback en cas d'échec LLM - VERSION MULTI-LIGNÉES"""
        filename = Path(json_file).name.lower()

        # Détection de lignée génétique depuis le nom de fichier
        genetic_line = self._detect_genetic_line_from_filename(filename)

        # Détection type de document
        document_type = self._detect_document_type_from_filename(filename)

        # Détection espèce
        species = self._detect_species_from_filename(filename)

        return DocumentContext(
            genetic_line=genetic_line,
            document_type=document_type,
            species=species,
            measurement_units="unknown",
            target_audience="unknown",
            table_types_expected=[],
            confidence_score=0.4,  # Confiance plus élevée pour fallback amélioré
            raw_analysis=f"Fallback analysis from filename: {filename}",
        )

    def _detect_genetic_line_from_filename(self, filename: str) -> str:
        """Détecte la lignée génétique depuis le nom de fichier"""

        # Patterns étendus pour détection depuis nom de fichier
        filename_patterns = {
            "ross 308": [
                "ross308",
                "ross_308",
                "ross-308",
                "aviagen_ross",
                "ross_broiler",
                "rossbroiler",
            ],
            "ross 708": ["ross708", "ross_708", "ross-708"],
            "cobb 500": [
                "cobb500",
                "cobb_500",
                "cobb-500",
                "cobb_broiler",
                "cobbbroiler",
            ],
            "cobb 700": ["cobb700", "cobb_700", "cobb-700"],
            "hubbard classic": [
                "hubbard_classic",
                "hubbard-classic",
                "classic",
                "hubbardclassic",
            ],
            "hubbard flex": ["hubbard_flex", "hubbard-flex", "flex", "hubbardflex"],
            "isa brown": ["isa_brown", "isa-brown", "isabrown", "isa"],
            "lohmann brown": [
                "lohmann_brown",
                "lohmann-brown",
                "lohmannbrown",
                "lohmann",
                "lb",
            ],
        }

        for canonical_line, patterns in filename_patterns.items():
            for pattern in patterns:
                if pattern in filename:
                    return canonical_line

        # Patterns regex pour cas plus complexes
        regex_patterns = {
            "ross 308": r"ross.*308|r[_-]?308",
            "cobb 500": r"cobb.*500|c[_-]?500",
            "hubbard classic": r"hubbard.*classic|hclassic",
        }

        for canonical_line, pattern in regex_patterns.items():
            if re.search(pattern, filename):
                return canonical_line

        return "unknown"

    def _detect_document_type_from_filename(self, filename: str) -> str:
        """Détecte le type de document depuis le nom de fichier"""

        type_patterns = {
            "health_protocol": ["health", "disease", "pathology", "illness", "ascites"],
            "biosecurity_guide": ["biosec", "biosecurity", "security", "hygiene"],
            "management_guide": ["management", "guide", "handbook", "manual"],
            "performance_guide": ["performance", "target", "objective", "standard"],
            "nutrition_manual": ["nutrition", "feed", "feeding", "diet", "nutrient"],
            "breeding_handbook": ["breed", "breeder", "reproduction", "parent"],
        }

        for doc_type, patterns in type_patterns.items():
            if any(pattern in filename for pattern in patterns):
                return doc_type

        return "management_guide"  # Type par défaut plus spécifique

    def _detect_species_from_filename(self, filename: str) -> str:
        """Détecte l'espèce depuis le nom de fichier"""

        if any(word in filename for word in ["broiler", "chair", "meat"]):
            return "broilers"
        elif any(word in filename for word in ["layer", "pondeuse", "egg", "laying"]):
            return "layers"
        elif any(word in filename for word in ["breed", "parent", "stock", "ps"]):
            return "breeders"
        else:
            return "broilers"  # Par défaut broilers car plus fréquent
