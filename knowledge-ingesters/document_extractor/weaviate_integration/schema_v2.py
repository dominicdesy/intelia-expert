"""
Weaviate Schema V2 for Knowledge Extraction
Updated schema with path-based + vision-based metadata
Multi-tenant support via metadata filtering
"""

from weaviate.classes.config import Configure, Property, DataType
from typing import List, Dict, Any


def create_knowledge_chunks_schema() -> Dict[str, Any]:
    """
    Create schema for KnowledgeChunks collection.

    Single collection with rich metadata for filtering:
    - Path-based metadata (70%): org, visibility, site_type, breed, etc.
    - Vision-based metadata (25%): species, topics, genetic_line, etc.
    - Smart defaults (5%): language, unit_system, etc.

    Multi-tenant via metadata filtering, not separate collections.
    """

    properties = [
        # ============================================================
        # CONTENT (Vectorized)
        # ============================================================
        Property(
            name="content",
            data_type=DataType.TEXT,
            description="Main text content of the chunk (vectorized for semantic search)"
        ),

        # ============================================================
        # PATH-BASED METADATA (70% - from directory structure)
        # ============================================================
        Property(
            name="owner_org_id",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Organization ID (intelia, client_abc, etc.) - PRIMARY FILTER"
        ),
        Property(
            name="visibility_level",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Visibility level: public_global, intelia_internal, org_internal, org_customer_facing"
        ),
        Property(
            name="site_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Site type: broiler_farms, layer_farms, breeding_farms, hatcheries, etc."
        ),
        Property(
            name="breed",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Breed/genetic line from path: ross_308, cobb_500, hy_line_brown, etc."
        ),
        Property(
            name="category",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document category: biosecurity, breed, housing, management, etc."
        ),
        Property(
            name="subcategory",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Subcategory: common, by_breed, by_climate, etc."
        ),
        Property(
            name="climate_zone",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Climate zone: tropical, temperate, cold"
        ),

        # ============================================================
        # VISION-BASED METADATA (25% - from document analysis)
        # ============================================================
        Property(
            name="species",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Poultry species: chicken, turkey, duck"
        ),
        Property(
            name="genetic_line",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Genetic line/brand: Ross, Cobb, Hy-Line, Lohmann, Hubbard"
        ),
        Property(
            name="company",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Company/breeder: Aviagen, Cobb-Vantress, Hy-Line, Lohmann"
        ),
        Property(
            name="document_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document type: handbook, guide, technical_note, research, standard, supplement"
        ),
        Property(
            name="target_audience",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Target audience: farmer, veterinarian, manager, technician, all"
        ),
        Property(
            name="technical_level",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Technical complexity: basic, intermediate, advanced"
        ),
        Property(
            name="topics",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Main topics: nutrition, housing, health, biosecurity, management, breeding, etc."
        ),

        # ============================================================
        # DOCUMENT-LEVEL METADATA
        # ============================================================
        Property(
            name="language",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Document language: en, es, fr, etc."
        ),
        Property(
            name="unit_system",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Unit system: metric, imperial, mixed"
        ),

        # ============================================================
        # LEGACY FIELDS (for backward compatibility with old data)
        # ============================================================
        Property(
            name="intent_category",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="LEGACY: Intent category from old system"
        ),
        Property(
            name="content_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="LEGACY: Content type from old system"
        ),
        Property(
            name="detected_phase",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="LEGACY: Phase detected (starter, grower, finisher)"
        ),
        Property(
            name="detected_bird_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="LEGACY: Bird type detected"
        ),
        Property(
            name="detected_site_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="LEGACY: Site type detected (use site_type instead)"
        ),
        Property(
            name="age_applicability",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="LEGACY: Age applicability list"
        ),
        Property(
            name="applicable_metrics",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="LEGACY: Applicable metrics list"
        ),
        Property(
            name="actionable_recommendations",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="LEGACY: Actionable recommendations"
        ),
        Property(
            name="followup_themes",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="LEGACY: Follow-up themes"
        ),

        # ============================================================
        # CONFIDENCE SCORES
        # ============================================================
        Property(
            name="path_confidence",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Confidence score for path-based classification (0.0-1.0)"
        ),
        Property(
            name="vision_confidence",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Confidence score for vision-based classification (0.0-1.0)"
        ),
        Property(
            name="overall_confidence",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Overall confidence score (0.0-1.0)"
        ),

        # ============================================================
        # CHUNK QUALITY SCORES (from chunk_quality_scorer.py)
        # ============================================================
        Property(
            name="quality_score",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Overall chunk quality score (0.0-1.0) - higher = better for retrieval"
        ),
        Property(
            name="info_density",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Information density score (0.0-1.0) - entity and number presence"
        ),
        Property(
            name="completeness",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Completeness score (0.0-1.0) - has intro and conclusion"
        ),
        Property(
            name="semantic_coherence",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Semantic coherence score (0.0-1.0) - sentence variance and transitions"
        ),
        Property(
            name="structure_score",
            data_type=DataType.NUMBER,
            skip_vectorization=True,
            description="Structure score (0.0-1.0) - lists, tables, headers"
        ),

        # ============================================================
        # EXTRACTED ENTITIES (from entity_extractor.py)
        # ============================================================
        Property(
            name="breeds",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted breeds: Ross 308, Cobb 500, Hy-Line Brown, etc."
        ),
        Property(
            name="diseases",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted diseases: Newcastle, Gumboro, Coccidiosis, E. coli, etc."
        ),
        Property(
            name="medications",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="Extracted medications: Amprolium, vaccines, antibiotics, etc."
        ),
        Property(
            name="has_performance_data",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Chunk contains performance metrics (FCR, weight, mortality)"
        ),
        Property(
            name="has_health_info",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Chunk contains health/disease information"
        ),
        Property(
            name="has_nutrition_info",
            data_type=DataType.BOOL,
            skip_vectorization=True,
            description="Chunk contains nutrition/feed information"
        ),
        Property(
            name="metrics",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="JSON string of extracted metrics: [{type: 'fcr', value: 1.65}, ...]"
        ),
        Property(
            name="age_ranges",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="JSON string of age ranges: [{start: 1, end: 21, unit: 'days'}, ...]"
        ),

        # ============================================================
        # SOURCE TRACKING
        # ============================================================
        Property(
            name="source_file",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Source file path"
        ),
        Property(
            name="extraction_method",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Extraction method: pdf_vision, docx_text, web_scrape, json_text"
        ),
        Property(
            name="chunk_id",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Unique chunk identifier"
        ),
        Property(
            name="word_count",
            data_type=DataType.INT,
            skip_vectorization=True,
            description="Word count of chunk"
        ),
        Property(
            name="extraction_timestamp",
            data_type=DataType.DATE,
            skip_vectorization=True,
            description="Timestamp of extraction (RFC3339 format)"
        ),
    ]

    return {
        "name": "KnowledgeChunks",
        "properties": properties,
        "description": "Knowledge chunks from poultry industry documents with rich metadata",
        "vectorizer_config": Configure.Vectorizer.text2vec_openai(
            model="text-embedding-3-large"
        ),
    }


def get_filterable_fields() -> List[str]:
    """
    Get list of fields that should be used for filtering.

    Primary filters for multi-tenant queries:
    - owner_org_id (REQUIRED for all queries)
    - visibility_level
    - site_type
    - breed
    - species
    - category
    - target_audience
    """
    return [
        "owner_org_id",  # PRIMARY: Organization-level filtering
        "visibility_level",  # Security filtering
        "site_type",  # Farm/facility type filtering
        "breed",  # Breed-specific filtering
        "species",  # Species filtering
        "category",  # Category filtering (biosecurity, housing, etc.)
        "subcategory",  # Subcategory filtering
        "climate_zone",  # Climate-specific filtering
        "genetic_line",  # Genetic line filtering
        "company",  # Company/breeder filtering
        "document_type",  # Document type filtering
        "target_audience",  # Audience filtering
        "technical_level",  # Technical level filtering
        "language",  # Language filtering
    ]


def get_example_filters() -> Dict[str, Any]:
    """
    Example filter combinations for common queries.
    """
    return {
        "client_broiler_ross": {
            "owner_org_id": "client_abc",
            "visibility_level": ["org_internal", "org_customer_facing"],
            "site_type": "broiler_farms",
            "breed": "ross_308"
        },
        "intelia_veterinary": {
            "owner_org_id": "intelia",
            "visibility_level": "public_global",
            "site_type": "veterinary_services",
            "target_audience": "veterinarian"
        },
        "layer_farm_manager": {
            "owner_org_id": "client_xyz",
            "site_type": "layer_farms",
            "target_audience": ["farmer", "manager"],
            "technical_level": ["basic", "intermediate"]
        }
    }


# Schema migration helper
def get_new_fields_v2() -> List[str]:
    """
    List of new fields added in V2 schema.
    Used for migration from old schema.
    """
    return [
        "owner_org_id",
        "visibility_level",
        "site_type",
        "breed",
        "category",
        "subcategory",
        "climate_zone",
        "genetic_line",
        "company",
        "topics",
        "path_confidence",
        "vision_confidence",
        "overall_confidence",
        "extraction_method",
    ]
