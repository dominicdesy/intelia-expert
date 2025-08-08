import os
from typing import Dict, List
import numpy as np
from app.api.v1.utils.openai_utils import safe_embedding_create

# Define categories and corresponding prompts for embedding
CATEGORIES: Dict[str, str] = {
    "nutrition": "nutrition context: fields: race, age_jours, poids, objectif",
    "sante": "sante context: fields: race, age_jours, symptomes, duree",
    "reproduction": "reproduction context: fields: race, age_jours, historique_ponte",
    "logement": "logement context: fields: effectif, surface, equipement",
    "incubation": "incubation context: fields: race, parametres, duree",
    "general": "general context: fields: race, age_jours"
}

# Required fields per category
REQUIRED_FIELDS_BY_TYPE: Dict[str, List[str]] = {
    "nutrition": ["race", "age_jours", "poids", "objectif"],
    "sante": ["race", "age_jours", "symptomes", "duree"],
    "reproduction": ["race", "age_jours", "historique_ponte"],
    "logement": ["effectif", "surface", "equipement"],
    "incubation": ["race", "parametres", "duree"],
    "general": ["race", "age_jours"]
}

# Pre-compute category embeddings
_CATEGORY_EMBEDDINGS: Dict[str, List[float]] = {}
_model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
for cat, prompt in CATEGORIES.items():
    resp = safe_embedding_create(model=_model, input=prompt)
    _CATEGORY_EMBEDDINGS[cat] = resp["data"][0]["embedding"]


def classify_question(question: str) -> str:
    """
    Classify question into one of the known categories via embedding similarity.
    """
    # Get embedding for the question
    resp = safe_embedding_create(model=_model, input=question)
    q_emb: List[float] = resp["data"][0]["embedding"]

    # Compute cosine similarity
    best_cat = None
    best_score = -1.0
    q_vec = np.array(q_emb)
    for cat, emb in _CATEGORY_EMBEDDINGS.items():
        v = np.array(emb)
        score = float(np.dot(q_vec, v) / (np.linalg.norm(q_vec) * np.linalg.norm(v)))
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat or "general"
