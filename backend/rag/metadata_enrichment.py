# rag/metadata_enrichment.py
import re
import os
from typing import Dict, Optional
from rag.metadata_schema import ChunkMeta

SPECIES_KEYWORDS = {
    "broiler": ["ross", "cobb", "broiler"],
    "layer": ["hy-line", "lohmann", "isa", "layer"],
}

DOMAIN_KEYWORDS = {
    "performance": ["weight", "fcr", "mortality", "performance"],
    "nutrition": ["protein", "energy", "lysine", "calcium", "phosphorus", "feed"],
    "health": ["vaccine", "treatment", "dose", "protocol", "disease"],
    "environment": ["temperature", "humidity", "ventilation", "lux", "density"],
    "biosecurity": ["biosecurity", "hygiene", "disinfection", "ppe", "visitor"],
}

def detect_species(text: str, filename: str) -> Optional[str]:
    combined = (filename + " " + text).lower()
    for sp, kws in SPECIES_KEYWORDS.items():
        if any(k in combined for k in kws):
            return sp
    return None

def detect_domain(text: str, filename: str) -> Optional[str]:
    combined = (filename + " " + text).lower()
    for dom, kws in DOMAIN_KEYWORDS.items():
        if any(k in combined for k in kws):
            return dom
    return None

def enrich_metadata(file_path: str, text: str, chunk_type: str = "text", domain: Optional[str] = None) -> ChunkMeta:
    filename = os.path.basename(file_path)
    species = detect_species(text, filename)
    if not domain:
        domain = detect_domain(text, filename)
    return {
        "source": filename,
        "species": species or "unknown",
        "strain": None,  # Optional: add strain detection logic
        "domain": domain or "general",
        "chunk_type": chunk_type,
        "language": "fr" if re.search(r"[éèàù]", text) else "en",
    }
