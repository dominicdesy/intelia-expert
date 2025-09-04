# app/utils/taxonomy.py
from __future__ import annotations

def species_from_breed(breed: str | None) -> str | None:
    if not breed:
        return None
    b = breed.lower()
    if any(x in b for x in ["ross", "cobb", "hubbard", "308", "500", "708", "broiler"]):
        return "broiler"
    if any(x in b for x in ["lohmann", "hy-line", "isa", "layer", "pondeuse", "w36", "w80"]):
        return "layer"
    return None
