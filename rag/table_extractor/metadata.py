#!/usr/bin/env python3
"""
Module de normalisation des métadonnées avec intents.json
"""

import json
from pathlib import Path
from typing import Dict
from datetime import datetime
from dataclasses import dataclass
import logging


@dataclass
class TableMetadata:
    """Métadonnées simples et normalisées"""

    genetic_line: str
    sex: str = "unknown"
    bird_type: str = "unknown"
    site_type: str = "unknown"
    document_type: str = "unknown"
    table_type: str = "unknown"
    source_file: str = ""
    extraction_date: str = ""


class MetadataNormalizer:
    """Normalise les métadonnées avec intents.json"""

    def __init__(self, intents_file: str = "intents.json"):
        self.intents_data = self._load_intents(intents_file)
        self.logger = logging.getLogger(__name__)

    def _load_intents(self, intents_file: str) -> Dict:
        """Charge le fichier intents.json"""
        try:
            with open(intents_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Cannot load {intents_file}: {e}")
            return {}

    def normalize_genetic_line(self, raw_text: str) -> str:
        """Normalise la lignée génétique selon intents.json"""
        if not self.intents_data:
            return "unknown"

        line_aliases = self.intents_data.get("aliases", {}).get("line", {})
        text_lower = raw_text.lower()

        # Recherche exacte d'abord
        for canonical, aliases in line_aliases.items():
            if canonical.lower() in text_lower:
                return canonical
            for alias in aliases:
                if alias.lower() in text_lower:
                    return canonical

        return "unknown"

    def normalize_sex(self, raw_text: str) -> str:
        """Normalise le sexe selon intents.json"""
        if not self.intents_data:
            return "unknown"

        sex_aliases = self.intents_data.get("aliases", {}).get("sex", {})
        text_lower = raw_text.lower()

        for canonical, aliases in sex_aliases.items():
            if canonical.lower() in text_lower:
                return canonical
            for alias in aliases:
                if alias.lower() in text_lower:
                    return canonical

        return "unknown"

    def detect_bird_type_from_line(self, genetic_line: str) -> str:
        """Détecte le type d'oiseau depuis la lignée"""
        line_lower = genetic_line.lower()

        broiler_lines = ["ross", "cobb", "hubbard", "ranger", "freedom", "sasso"]
        layer_lines = [
            "isa",
            "lohmann",
            "hy-line",
            "dekalb",
            "bovans",
            "shaver",
            "novogen",
            "hisex",
        ]

        for keyword in broiler_lines:
            if keyword in line_lower:
                return "broiler"

        for keyword in layer_lines:
            if keyword in line_lower:
                return "layer"

        return "broiler"  # Default

    def detect_document_type(self, title: str, content: str) -> str:
        """Détecte le type de document"""
        combined = f"{title} {content}".lower()

        if any(
            word in combined for word in ["nutrition", "feed", "amino acid", "protein"]
        ):
            return "nutrition_specifications"
        elif any(
            word in combined
            for word in ["performance", "objectives", "targets", "growth"]
        ):
            return "performance_objectives"
        elif any(word in combined for word in ["management", "handbook", "guide"]):
            return "management_guide"

        return "unknown"

    def detect_table_type(self, title: str, headers: list) -> str:
        """Détecte le type de tableau basé sur le titre et headers"""
        title_lower = title.lower()
        headers_text = " ".join(headers).lower()
        combined = f"{title_lower} {headers_text}"

        if any(word in combined for word in ["amino", "protein", "nutrition", "feed"]):
            return "nutrition_data"
        elif any(word in combined for word in ["weight", "gain", "fcr", "performance"]):
            return "performance_data"
        elif any(
            word in combined for word in ["temperature", "humidity", "environment"]
        ):
            return "environment_data"

        return "data"

    def create_metadata(
        self, title: str, content: str, source_file: str, headers: list = None
    ) -> TableMetadata:
        """Crée les métadonnées normalisées"""
        combined_text = f"{title} {content} {source_file}"

        genetic_line = self.normalize_genetic_line(combined_text)
        sex = self.normalize_sex(combined_text)
        bird_type = self.detect_bird_type_from_line(genetic_line)
        document_type = self.detect_document_type(title, content)
        table_type = self.detect_table_type(title, headers or [])

        # Site type basé sur bird type
        site_type = "broiler_farm" if bird_type == "broiler" else "layer_farm"
        if "parent" in combined_text.lower() or "breeder" in combined_text.lower():
            site_type = "breeding_farm"

        return TableMetadata(
            genetic_line=genetic_line,
            sex=sex,
            bird_type=bird_type,
            site_type=site_type,
            document_type=document_type,
            table_type=table_type,
            source_file=Path(source_file).name,
            extraction_date=datetime.now().isoformat()[:10],
        )
