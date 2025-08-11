# rag/metadata_schema.py
from __future__ import annotations
from typing import TypedDict, Literal, NotRequired, Dict, Any, List

ChunkType = Literal["text", "table", "image", "figure", "code", "other"]

# 🆕 Types étendus pour les nouvelles métadonnées
SpeciesType = Literal["broiler", "layer", "breeder", "duck", "turkey", "global"]
ProductionPhase = Literal["starter", "grower", "finisher", "layer_phase1", "layer_phase2", "pre_lay"]
DomainType = Literal["performance", "nutrition", "health", "environment", "biosecurity", "genetics", "welfare"]

# 🆕 Nouveaux types pour les champs ajoutés
DocumentType = Literal["guide", "specification", "research", "technical_sheet", "presentation"]
TableType = Literal["perf_targets", "nutrition_specs", "vaccination_schedule", "feeding_program"]
SexType = Literal["male", "female", "mixed"]

class ChunkMeta(TypedDict, total=False):
    # ===============================
    # CHAMPS EXISTANTS (conservés)
    # ===============================
    doc_id: str
    source: str                 # chemin/URL du document source
    section: NotRequired[str]
    page: NotRequired[int]      # 🆕 Conservé pour compatibilité
    species: NotRequired[SpeciesType]  # ← Étendu de Literal["broiler", "layer", "global"]
    role_hint: NotRequired[str] # ex: vet, grower, nutritionist
    chunk_type: NotRequired[ChunkType]
    tags: NotRequired[List[str]]
    extra: NotRequired[Dict[str, Any]]
    
    # ===============================
    # 🆕 NOUVELLES MÉTADONNÉES CRITIQUES POUR LE FILTRAGE RAG
    # ===============================
    line: NotRequired[str]                      # "Ross 308", "Lohmann Brown", "Cobb 500" (ex: strain)
    sex: NotRequired[SexType]                   # "male", "female", "mixed"
    document_type: NotRequired[DocumentType]    # Type de document source
    table_type: NotRequired[TableType]          # Type spécialisé de tableau
    page_number: NotRequired[int]               # Numéro de page (nouveau nom standard)
    
    # ===============================
    # MÉTADONNÉES CONTEXTUELLES EXISTANTES ÉTENDUES
    # ===============================
    strain: NotRequired[str]                    # 🆕 Alias pour "line" (rétrocompatibilité)
    production_phase: NotRequired[ProductionPhase]  # Phase de production
    age_range: NotRequired[str]                 # "0-21 days", "22-42 days", "16-20 weeks"
    domain: NotRequired[DomainType]             # Classification par domaine
    domain_confidence: NotRequired[float]       # Score de confiance 0-1
    technical_level: NotRequired[Literal["basic", "intermediate", "advanced"]]
    data_quality: NotRequired[Literal["low", "medium", "high"]]
    language: NotRequired[Literal["fr", "en", "es", "de"]]
    
    # ===============================
    # MÉTADONNÉES CONTEXTUELLES SUPPLÉMENTAIRES
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
# 🆕 NOUVELLES FONCTIONS D'AIDE ÉTENDUES
# ===============================

def create_enhanced_metadata(
    source: str,
    species: str = None,
    line: str = None,          # 🆕 Nouveau paramètre
    sex: str = None,           # 🆕 Nouveau paramètre
    document_type: str = None, # 🆕 Nouveau paramètre
    table_type: str = None,    # 🆕 Nouveau paramètre
    domain: str = None,
    production_phase: str = None,
    **kwargs
) -> ChunkMeta:
    """
    🆕 Helper étendu pour créer des métadonnées enrichies avec nouveaux champs
    """
    metadata: ChunkMeta = {
        "source": source,
    }
    
    # Ajouter les champs optionnels s'ils sont fournis
    if species:
        metadata["species"] = species
    if line:
        metadata["line"] = line                    # 🆕 Nouveau
    if sex:
        metadata["sex"] = sex                      # 🆕 Nouveau
    if document_type:
        metadata["document_type"] = document_type  # 🆕 Nouveau
    if table_type:
        metadata["table_type"] = table_type        # 🆕 Nouveau
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
    🆕 Validation étendue des métadonnées selon le schéma
    """
    try:
        # Vérification des types requis
        if "source" not in meta:
            return False
        
        # Vérification des énumérations étendues
        if "species" in meta and meta["species"] not in SpeciesType.__args__:
            return False
        
        if "production_phase" in meta and meta["production_phase"] not in ProductionPhase.__args__:
            return False
        
        if "domain" in meta and meta["domain"] not in DomainType.__args__:
            return False
        
        # 🆕 Nouvelles validations
        if "sex" in meta and meta["sex"] not in SexType.__args__:
            return False
            
        if "document_type" in meta and meta["document_type"] not in DocumentType.__args__:
            return False
            
        if "table_type" in meta and meta["table_type"] not in TableType.__args__:
            return False
        
        # Vérification du score de confiance
        if "domain_confidence" in meta:
            confidence = meta["domain_confidence"]
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                return False
        
        # 🆕 Validation cohérence page/page_number
        if "page" in meta and "page_number" in meta:
            if meta["page"] != meta["page_number"]:
                return False
        
        return True
    except Exception:
        return False


def merge_metadata(base_meta: ChunkMeta, additional_meta: Dict[str, Any]) -> ChunkMeta:
    """
    Fusionne les métadonnées en préservant les types et gérant les alias
    """
    merged = base_meta.copy()
    
    for key, value in additional_meta.items():
        if value is None:
            continue
            
        # 🆕 Gestion des alias et mappings
        if key == "strain" and "line" not in merged:
            # strain → line (nouveau nom standard)
            merged["line"] = value
        elif key == "page" and "page_number" not in merged:
            # page → page_number (nouveau nom standard)  
            merged["page_number"] = value
        elif key in ChunkMeta.__annotations__:
            merged[key] = value
    
    return merged


def normalize_metadata_fields(meta: ChunkMeta) -> ChunkMeta:
    """
    🆕 Normalise les champs de métadonnées (gère les alias et rétrocompatibilité)
    """
    normalized = meta.copy()
    
    # strain → line (migration vers nouveau nom standard)
    if "strain" in normalized and "line" not in normalized:
        normalized["line"] = normalized["strain"]
        # Conserver strain pour rétrocompatibilité
    
    # page → page_number (migration vers nouveau nom standard)
    if "page" in normalized and "page_number" not in normalized:
        normalized["page_number"] = normalized["page"]
        # Conserver page pour rétrocompatibilité
    
    return normalized


def get_filterable_fields() -> List[str]:
    """
    🆕 Retourne la liste des champs utilisables pour le filtrage RAG
    """
    return [
        "species",      # Filtrage par espèce
        "line",         # Filtrage par lignée (ex: Ross 308)
        "sex",          # Filtrage par sexe
        "document_type", # Filtrage par type de document
        "chunk_type",   # Filtrage par type de chunk
        "table_type",   # Filtrage par type de table
        "domain",       # Filtrage par domaine
        "production_phase", # Filtrage par phase
        "language"      # Filtrage par langue
    ]


def get_critical_fields() -> List[str]:
    """
    🆕 Retourne les champs critiques qui doivent être présents pour un filtrage efficace
    """
    return [
        "species",      # Quasi-obligatoire
        "chunk_type",   # Obligatoire
        "source"        # Obligatoire
    ]


def analyze_metadata_completeness(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    🆕 Analyse la complétude des métadonnées sur un ensemble de chunks
    """
    if not chunks:
        return {"total": 0, "completeness": {}}
    
    filterable = get_filterable_fields()
    critical = get_critical_fields()
    
    stats = {
        "total_chunks": len(chunks),
        "completeness": {},
        "critical_coverage": 0,
        "overall_score": 0
    }
    
    for field in filterable + critical:
        with_field = sum(1 for chunk in chunks 
                        if chunk.get("metadata", {}).get(field) is not None)
        stats["completeness"][field] = {
            "count": with_field,
            "percentage": (with_field / len(chunks)) * 100,
            "is_critical": field in critical
        }
    
    # Score critique (species + chunk_type + source)
    critical_complete = sum(1 for chunk in chunks 
                           if all(chunk.get("metadata", {}).get(field) 
                                 for field in critical))
    stats["critical_coverage"] = (critical_complete / len(chunks)) * 100
    
    # Score global pondéré
    total_score = 0
    total_weight = 0
    for field, data in stats["completeness"].items():
        weight = 3 if data["is_critical"] else 1
        total_score += data["percentage"] * weight
        total_weight += weight
    
    stats["overall_score"] = total_score / total_weight if total_weight > 0 else 0
    
    return stats