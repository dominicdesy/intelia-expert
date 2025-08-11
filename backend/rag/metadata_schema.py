# rag/metadata_schema.py
from __future__ import annotations
from typing import TypedDict, Literal, NotRequired, Dict, Any, List

ChunkType = Literal["text", "table", "image", "figure", "code", "other"]

# Nouveaux types étendus pour les améliorations
SpeciesType = Literal["broiler", "layer", "breeder", "duck", "turkey", "global"]
ProductionPhase = Literal["starter", "grower", "finisher", "layer_phase1", "layer_phase2", "pre_lay"]
DomainType = Literal["performance", "nutrition", "health", "environment", "biosecurity", "genetics", "welfare"]

class ChunkMeta(TypedDict, total=False):
    # ===============================
    # CHAMPS EXISTANTS (conservés)
    # ===============================
    doc_id: str
    source: str                 # chemin/URL du document source
    section: NotRequired[str]
    page: NotRequired[int]
    species: NotRequired[SpeciesType]  # ← Étendu de Literal["broiler", "layer", "global"]
    role_hint: NotRequired[str] # ex: vet, grower, nutritionist
    chunk_type: NotRequired[ChunkType]
    tags: NotRequired[List[str]]
    extra: NotRequired[Dict[str, Any]]
    
    # ===============================
    # NOUVELLES MÉTADONNÉES CRITIQUES
    # ===============================
    strain: NotRequired[str]                    # "Ross 308", "Lohmann Brown", "Cobb 500"
    production_phase: NotRequired[ProductionPhase]  # Phase de production
    age_range: NotRequired[str]                 # "0-21 days", "22-42 days", "16-20 weeks"
    domain: NotRequired[DomainType]             # Classification par domaine
    domain_confidence: NotRequired[float]       # Score de confiance 0-1
    technical_level: NotRequired[Literal["basic", "intermediate", "advanced"]]
    data_quality: NotRequired[Literal["low", "medium", "high"]]
    language: NotRequired[Literal["fr", "en", "es", "de"]]
    
    # ===============================
    # MÉTADONNÉES CONTEXTUELLES
    # ===============================
    geographic_region: NotRequired[str]         # "EU", "US", "Global", "Canada"
    standard_reference: NotRequired[str]        # "NRC", "INRA", "Aviagen", "Lohmann"
    measurement_units: NotRequired[str]         # "metric", "imperial"


def ensure_chunk_type(meta: Dict[str, Any], default: ChunkType = "text") -> Dict[str, Any]:
    """
    Fonction existante conservée pour compatibilité
    """
    if "chunk_type" not in meta:
        meta["chunk_type"] = default
    return meta


# ===============================
# NOUVELLES FONCTIONS D'AIDE
# ===============================

def create_enhanced_metadata(
    source: str,
    species: str = None,
    strain: str = None,
    domain: str = None,
    production_phase: str = None,
    **kwargs
) -> ChunkMeta:
    """
    Helper pour créer des métadonnées enrichies avec validation
    """
    metadata: ChunkMeta = {
        "source": source,
    }
    
    # Ajouter les champs optionnels s'ils sont fournis
    if species:
        metadata["species"] = species
    if strain:
        metadata["strain"] = strain
    if domain:
        metadata["domain"] = domain
    if production_phase:
        metadata["production_phase"] = production_phase
    
    # Ajouter les kwargs additionnels
    for key, value in kwargs.items():
        if value is not None and key in ChunkMeta.__annotations__:
            metadata[key] = value
    
    return metadata


def validate_metadata(meta: ChunkMeta) -> bool:
    """
    Validation des métadonnées selon le schéma
    """
    try:
        # Vérification des types requis
        if "source" not in meta:
            return False
        
        # Vérification des énumérations
        if "species" in meta and meta["species"] not in SpeciesType.__args__:
            return False
        
        if "production_phase" in meta and meta["production_phase"] not in ProductionPhase.__args__:
            return False
        
        if "domain" in meta and meta["domain"] not in DomainType.__args__:
            return False
        
        # Vérification du score de confiance
        if "domain_confidence" in meta:
            confidence = meta["domain_confidence"]
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                return False
        
        return True
    except Exception:
        return False


def merge_metadata(base_meta: ChunkMeta, additional_meta: Dict[str, Any]) -> ChunkMeta:
    """
    Fusionne les métadonnées en préservant les types
    """
    merged = base_meta.copy()
    
    for key, value in additional_meta.items():
        if key in ChunkMeta.__annotations__ and value is not None:
            merged[key] = value
    
    return merged