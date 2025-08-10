# rag/parsers/metadata_enrichment.py
from __future__ import annotations

import re
from typing import Dict, Any

def enrich_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise/enrichit les métadonnées essentielles pour le filtrage universel.
    Ajoute (si possible): species, life_stage, document_type, chunk_type, section
    """
    m = dict(meta or {})
    path = " ".join([str(m.get(k, "")) for k in ["file_path", "path", "source", "filename"]]).lower()

    # species
    if "species" not in m or not m["species"]:
        if any(x in path for x in ["broiler", "ross", "cobb", "hubbard"]):
            m["species"] = "broiler"
        elif any(x in path for x in ["layer", "lohmann", "hy-line", "isa"]):
            m["species"] = "layer"

    # life_stage
    if "life_stage" not in m or not m["life_stage"]:
        if "parent stock" in path or "breeder" in path:
            m["life_stage"] = "parent_stock"
        elif any(x in path for x in ["broiler", "growout", "fattening"]):
            m["life_stage"] = "broiler"

    # document_type
    if "document_type" not in m or not m["document_type"]:
        if any(x in path for x in ["performance objectives", "performance_objectives", "objectifs de performance"]):
            m["document_type"] = "performance_objectives"
        elif any(x in path for x in ["handbook", "guide", "manual"]):
            # heuristique selon espèce
            m["document_type"] = "broiler_handbook" if m.get("species") == "broiler" else "layer_handbook"
        elif "regulation" in path or "reglement" in path or "cahier des charges" in path:
            m["document_type"] = "regulations"

    # chunk_type: conserver si déjà défini par parser table; sinon text
    if not m.get("chunk_type"):
        m["chunk_type"] = "table" if "table" in path else "paragraph"

    # section heuristique
    if not m.get("section"):
        sec = re.findall(r"(section\s+\d+(\.\d+)?)", path)
        if sec:
            m["section"] = sec[0][0]

    return m
