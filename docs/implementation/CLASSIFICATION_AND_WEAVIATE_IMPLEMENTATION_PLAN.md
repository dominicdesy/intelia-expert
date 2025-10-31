# Plan d'Implémentation : Classification Automatique et Architecture Weaviate

**Date** : 2025-10-29
**Statut** : Plan détaillé - Prêt pour implémentation
**Objectif** : Classification automatique (90%+) avec architecture Weaviate single-collection optimisée

---

## Table des Matières

1. [Vision Globale](#vision-globale)
2. [Architecture Weaviate](#architecture-weaviate)
3. [Système de Classification Hybride](#système-de-classification-hybride)
4. [Schéma de Métadonnées Complet](#schéma-de-métadonnées-complet)
5. [Plan d'Implémentation Par Phases](#plan-dimplémentation-par-phases)
6. [Exemples Concrets](#exemples-concrets)
7. [Validation et Tests](#validation-et-tests)

---

## Vision Globale

### Problème à Résoudre

L'utilisateur a exprimé un stress significatif concernant la **charge de classification manuelle** des documents. Notre solution doit :

- ✅ **Automatiser 90%+** de la classification
- ✅ Supporter **multi-tenant** (organisations multiples)
- ✅ Gérer **sécurité d'accès** (public, partagé, interne)
- ✅ Classifier selon **4 dimensions** (taxonomie, contexte métier, sécurité, provenance)
- ✅ Rester **simple et maintenable**

### Principes Directeurs

1. **Single Collection** : Une seule collection Weaviate avec filtrage par métadonnées (évite la complexité)
2. **Classification Hybride** : Path-based (70%) + LLM inference (25%) + Defaults (5%)
3. **Évolutivité** : Schema extensible pour futures catégories
4. **Performance** : Filtrage efficace via indexes Weaviate
5. **Coût** : Minimiser les appels LLM (classification path-based gratuite)

---

## Architecture Weaviate

### Option Retenue : Single Collection avec Filtrage Avancé

**Nom de collection** : `KnowledgeChunks` (ou `InteliaKnowledge_v2`)

#### Avantages

✅ **Simplicité** : Un seul schema à maintenir
✅ **Flexibilité** : Queries cross-domain faciles (ex: "broiler + vaccination + hatchery")
✅ **Performance** : Weaviate optimisé pour filtrage massif
✅ **Maintenance** : Pas de synchronisation multi-collections
✅ **Évolutivité** : Ajout de filtres sans créer nouvelles collections

#### Filtrage Multi-Dimension

```python
# Exemple : Requête filtré pour organisation "Acme Corp", documents publics, catégorie "Health"
results = collection.query.near_text(
    query="vaccination schedule broilers",
    limit=10,
    filters=(
        Filter.by_property("visibility_level").equal("public_global") |
        (
            Filter.by_property("visibility_level").equal("org_shared") &
            Filter.by_property("owner_org_id").equal("acme_corp")
        )
    ) &
    Filter.by_property("category_level1").equal("Animal_Health") &
    Filter.by_property("species").contains_any(["broiler", "layer"])
)
```

---

## Système de Classification Hybride

### Architecture en 3 Tiers

```
┌─────────────────────────────────────────────────────────┐
│              HYBRID DOCUMENT CLASSIFIER                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TIER 1: Path-Based Classification (70% coverage)      │
│  ├─ Extraction depuis structure de répertoires         │
│  ├─ Règles déterministes (rapide, gratuit)             │
│  └─ Champs: species, visibility_level, source_type     │
│                                                         │
│  TIER 2: LLM-Based Inference (25% coverage)            │
│  ├─ GPT-4o-mini pour classification complexe           │
│  ├─ Taxonomie 4 niveaux (category → topic)             │
│  └─ Champs: production_stage, site_type, tags          │
│                                                         │
│  TIER 3: Smart Defaults (5% coverage)                  │
│  ├─ Valeurs par défaut intelligentes                   │
│  └─ Gestion des cas non couverts                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Tier 1 : Classification Path-Based (70%)

#### Règles d'Extraction depuis Directory Structure

**Structure actuelle** :
```
C:\Software_Development\documents\
├── public/
│   ├── common/
│   │   ├── health/           → category_level1="Animal_Health"
│   │   ├── regulations/      → category_level1="Regulatory"
│   │   └── standards/        → category_level1="Industry_Standards"
│   └── species/
│       ├── broiler/
│       │   ├── nutrition/    → species="broiler", category_level2="Nutrition"
│       │   ├── health/       → species="broiler", category_level2="Health"
│       │   └── management/   → species="broiler", category_level2="Management"
│       └── layer/
│           └── [similar]
├── PerformanceMetrics/
│   ├── Broiler/
│   │   ├── Ross/            → species="broiler", genetic_line="Ross", source_type="performance_data"
│   │   └── Cobb/            → species="broiler", genetic_line="Cobb"
│   └── Layer/
│       └── [similar]
└── tenant_ABC/              → visibility_level="org_internal", owner_org_id="ABC"
```

#### Mappings Automatiques

```python
PATH_CLASSIFICATION_RULES = {
    # Sécurité / Visibilité
    "public/": {"visibility_level": "public_global"},
    "tenant_*/": {"visibility_level": "org_internal", "owner_org_id": "<tenant_name>"},
    "PerformanceMetrics/": {"visibility_level": "org_shared", "source_type": "performance_data"},

    # Espèces
    "/broiler/": {"species": "broiler"},
    "/layer/": {"species": "layer"},
    "/breeder/": {"species": "breeder"},
    "/turkey/": {"species": "turkey"},

    # Taxonomie Niveau 1
    "/health/": {"category_level1": "Animal_Health"},
    "/nutrition/": {"category_level1": "Nutrition"},
    "/management/": {"category_level1": "Farm_Management"},
    "/regulations/": {"category_level1": "Regulatory"},
    "/biosecurity/": {"category_level1": "Biosecurity"},
    "/performance/": {"category_level1": "Performance_Metrics"},

    # Taxonomie Niveau 2 (contexte)
    "/vaccination/": {"category_level2": "Vaccination_Programs"},
    "/disease/": {"category_level2": "Disease_Management"},
    "/feed/": {"category_level2": "Feed_Formulation"},
    "/water/": {"category_level2": "Water_Management"},
    "/environment/": {"category_level2": "Environmental_Control"},

    # Lignées génétiques
    "/Ross/": {"genetic_line": "Ross"},
    "/Cobb/": {"genetic_line": "Cobb"},
    "/Aviagen/": {"genetic_line": "Aviagen"},
    "/Hubbard/": {"genetic_line": "Hubbard"},

    # Source types
    "/guides/": {"source_type": "technical_guide"},
    "/manuals/": {"source_type": "manual"},
    "/research/": {"source_type": "research_paper"},
}
```

**Avantage** : Gratuit, instantané, déterministe

### Tier 2 : LLM-Based Classification (25%)

Pour les champs nécessitant compréhension du contenu :

#### Prompt Template pour GPT-4o-mini

```python
CLASSIFICATION_PROMPT = """
Analyze the following poultry document and classify it according to these dimensions:

**Document Title**: {title}
**First 500 words**: {content_preview}
**Already classified**: {path_based_classification}

Please provide classification for:

1. **production_stage** (select all that apply):
   - hatchery, brooding, growing, finishing, processing, all_stages

2. **site_type** (select all that apply):
   - hatchery, broiler_farm, layer_farm, breeder_farm, feed_mill, processing_plant, veterinary_clinic, all_sites

3. **category_level3** (specific topic within {category_level2}):
   - For Health/Disease: coccidiosis, necrotic_enteritis, ascites, respiratory_diseases, etc.
   - For Nutrition: feed_formulation, water_quality, supplements, feeding_programs, etc.
   - For Management: lighting_programs, ventilation, temperature_control, etc.

4. **category_level4** (specific attributes - up to 3 keywords):
   - Examples: ["vaccination_schedule", "dose_recommendations", "withdrawal_period"]

5. **technical_tags** (5-10 searchable keywords):
   - Industry-specific terms users might search for

6. **climate_zone** (select all that apply):
   - tropical, subtropical, temperate, cold, hot_arid, multiple_zones

7. **geo_region** (optional, for specific targeting):
   - global, north_america, europe, asia, latin_america, africa, oceania

8. **document_purpose**:
   - reference_guide, troubleshooting, best_practices, regulatory_compliance, training_material

Return as JSON:
{
  "production_stage": ["brooding", "growing"],
  "site_type": ["broiler_farm"],
  "category_level3": "coccidiosis",
  "category_level4": ["vaccination_protocol", "anticoccidial_program", "prophylaxis"],
  "technical_tags": ["coccidiosis", "eimeria", "anticoccidials", "vaccination", "gut_health"],
  "climate_zone": ["tropical", "subtropical"],
  "geo_region": ["global"],
  "document_purpose": "reference_guide"
}
"""
```

**Coût estimé** : ~$0.001 per document (GPT-4o-mini)

### Tier 3 : Smart Defaults (5%)

Pour les cas où Path + LLM ne suffisent pas :

```python
SMART_DEFAULTS = {
    "visibility_level": "public_global",  # Par défaut : public
    "climate_zone": ["multiple_zones"],  # Applicable à plusieurs zones
    "geo_region": ["global"],  # Par défaut : global
    "production_stage": ["all_stages"],
    "site_type": ["all_sites"],
    "source_type": "technical_guide",
    "document_purpose": "reference_guide",
    "genetic_line": None,  # Champ ouvert, pas de défaut
    "confidence_score": 0.5,  # Indique classification par défaut
}
```

---

## Schéma de Métadonnées Complet

### Structure Weaviate v4

```python
from weaviate.classes.config import Property, DataType, Configure

KNOWLEDGE_CHUNKS_SCHEMA = {
    "class": "KnowledgeChunks",
    "description": "Unified knowledge base with multi-tenant support and advanced filtering",

    # Vectorization
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
            "model": "text-embedding-3-large",
            "dimensions": 3072,
            "vectorizeClassName": False
        }
    },

    # Properties (39 champs)
    "properties": [
        # === CORE CONTENT ===
        Property(name="chunk_id", dataType=DataType.TEXT, description="Unique chunk identifier"),
        Property(name="content", dataType=DataType.TEXT, description="Main chunk content (vectorized)",
                 skip_vectorization=False, indexFilterable=False, indexSearchable=False),
        Property(name="source_file", dataType=DataType.TEXT, description="Original document filename",
                 indexFilterable=True, indexSearchable=True),
        Property(name="chunk_index", dataType=DataType.INT, description="Position in document",
                 indexFilterable=True, indexRangeFilters=True),

        # === SECURITY / ACCESS CONTROL ===
        Property(name="visibility_level", dataType=DataType.TEXT,
                 description="Access level: public_global | org_shared | org_internal",
                 indexFilterable=True),
        Property(name="owner_org_id", dataType=DataType.TEXT,
                 description="Organization ID (tenant identifier)",
                 indexFilterable=True, indexSearchable=True),
        Property(name="allowed_org_ids", dataType=DataType.TEXT_ARRAY,
                 description="Organizations with shared access",
                 indexFilterable=True),
        Property(name="classification_confidence", dataType=DataType.NUMBER,
                 description="Confidence score (0.0-1.0) for classification",
                 indexRangeFilters=True),

        # === BUSINESS CONTEXT ===
        Property(name="species", dataType=DataType.TEXT_ARRAY,
                 description="Target species: broiler | layer | breeder | turkey",
                 indexFilterable=True),
        Property(name="genetic_line", dataType=DataType.TEXT,
                 description="Genetic line: Open field (Ross, Cobb, Hubbard, Aviagen, ISA, Hy-Line, or any regional/emerging line)",
                 indexFilterable=True, indexSearchable=True),
        Property(name="production_stage", dataType=DataType.TEXT_ARRAY,
                 description="Production stages: hatchery | brooding | growing | finishing | processing | all_stages",
                 indexFilterable=True),
        Property(name="site_type", dataType=DataType.TEXT_ARRAY,
                 description="Facility types: hatchery | broiler_farm | layer_farm | breeder_farm | feed_mill | processing_plant | veterinary_clinic | all_sites",
                 indexFilterable=True),
        Property(name="climate_zone", dataType=DataType.TEXT_ARRAY,
                 description="Climate zones: tropical | subtropical | temperate | cold | hot_arid | multiple_zones",
                 indexFilterable=True),
        Property(name="geo_region", dataType=DataType.TEXT_ARRAY,
                 description="Geographic regions (optional, for specific targeting): north_america | europe | asia | latin_america | africa | oceania | global",
                 indexFilterable=True),
        Property(name="source_type", dataType=DataType.TEXT,
                 description="Document type: technical_guide | manual | research_paper | regulation | standard | performance_data | case_study | training_material",
                 indexFilterable=True),
        Property(name="document_purpose", dataType=DataType.TEXT,
                 description="Purpose: reference_guide | troubleshooting | best_practices | regulatory_compliance | training_material",
                 indexFilterable=True),
        Property(name="language", dataType=DataType.TEXT,
                 description="Content language (ISO 639-1)",
                 indexFilterable=True),

        # === 4-LEVEL TAXONOMY ===
        Property(name="category_level1", dataType=DataType.TEXT,
                 description="Main category: Animal_Health | Nutrition | Farm_Management | Biosecurity | Performance_Metrics | Regulatory | Equipment | Processing | Welfare",
                 indexFilterable=True),
        Property(name="category_level2", dataType=DataType.TEXT,
                 description="Subcategory: Vaccination_Programs | Disease_Management | Feed_Formulation | Water_Management | Environmental_Control | etc.",
                 indexFilterable=True, indexSearchable=True),
        Property(name="category_level3", dataType=DataType.TEXT,
                 description="Specific topic: coccidiosis | necrotic_enteritis | ascites | lighting_programs | ventilation_systems | etc.",
                 indexFilterable=True, indexSearchable=True),
        Property(name="category_level4", dataType=DataType.TEXT_ARRAY,
                 description="Granular attributes/tags (3-5 keywords): vaccination_schedule | dose_recommendations | withdrawal_period | etc.",
                 indexFilterable=True, indexSearchable=True),

        # === SEARCHABILITY ===
        Property(name="technical_tags", dataType=DataType.TEXT_ARRAY,
                 description="Industry-specific searchable keywords (5-10 tags)",
                 indexFilterable=True, indexSearchable=True),
        Property(name="entities", dataType=DataType.TEXT_ARRAY,
                 description="Named entities: diseases, products, locations, organizations",
                 indexFilterable=True, indexSearchable=True),

        # === METADATA ===
        Property(name="title", dataType=DataType.TEXT, description="Document title",
                 indexSearchable=True),
        Property(name="author", dataType=DataType.TEXT, description="Document author/creator"),
        Property(name="publication_date", dataType=DataType.DATE, description="Original publication date",
                 indexRangeFilters=True),
        Property(name="version", dataType=DataType.TEXT, description="Document version"),
        Property(name="word_count", dataType=DataType.INT, description="Chunk word count",
                 indexRangeFilters=True),
        Property(name="ingestion_timestamp", dataType=DataType.DATE, description="When chunk was indexed",
                 indexRangeFilters=True),
        Property(name="last_updated", dataType=DataType.DATE, description="Last modification date",
                 indexRangeFilters=True),

        # === TECHNICAL FIELDS ===
        Property(name="chunk_type", dataType=DataType.TEXT,
                 description="Content type: text | table | figure | list | code"),
        Property(name="semantic_density", dataType=DataType.NUMBER,
                 description="Information density score",
                 indexRangeFilters=True),
        Property(name="has_tables", dataType=DataType.BOOL, description="Contains structured data"),
        Property(name="has_images", dataType=DataType.BOOL, description="Contains images/figures"),
        Property(name="has_calculations", dataType=DataType.BOOL, description="Contains numerical calculations"),

        # === QUALITY METRICS ===
        Property(name="quality_score", dataType=DataType.NUMBER,
                 description="Content quality score (0.0-1.0)",
                 indexRangeFilters=True),
        Property(name="relevance_score", dataType=DataType.NUMBER,
                 description="Domain relevance score",
                 indexRangeFilters=True),
        Property(name="validation_status", dataType=DataType.TEXT,
                 description="Validation state: validated | pending | flagged",
                 indexFilterable=True),

        # === RELATIONSHIPS ===
        Property(name="related_chunk_ids", dataType=DataType.TEXT_ARRAY,
                 description="IDs of semantically related chunks"),
        Property(name="parent_section", dataType=DataType.TEXT,
                 description="Parent section/chapter in original document"),
    ]
}
```

### Index Strategy

Weaviate indexes optimisés pour performance :

- **Filterable** : visibility_level, owner_org_id, species, category_level1-3
- **Searchable** : source_file, technical_tags, entities, category_level2-4
- **Range Filters** : chunk_index, word_count, quality_score, publication_date

---

## Plan d'Implémentation Par Phases

### Phase 1 : Infrastructure de Base (Semaine 1)

#### Objectifs
- ✅ Créer nouvelle collection Weaviate avec schéma complet
- ✅ Implémenter Path-Based Classifier (Tier 1)
- ✅ Tester classification sur 20 documents

#### Livrables
```
knowledge-ingesters/knowledge_extractor/
├── classifiers/
│   ├── __init__.py
│   ├── base_classifier.py          # Interface abstraite
│   ├── path_classifier.py          # Tier 1 : Path-based
│   ├── llm_classifier.py           # Tier 2 : LLM-based (stub)
│   └── hybrid_classifier.py        # Orchestrateur
├── config/
│   └── classification_rules.yaml   # Règles path-based
└── tests/
    └── test_classifiers.py
```

#### Code : Path Classifier

```python
# classifiers/path_classifier.py
import re
from pathlib import Path
from typing import Dict, List, Any
import yaml

class PathBasedClassifier:
    """
    Tier 1: Extract metadata from file path structure
    Coverage: ~70% of fields
    Cost: $0 (deterministic rules)
    """

    def __init__(self, rules_file: str):
        with open(rules_file, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)

    def classify(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file path"""
        metadata = {
            "classification_method": "path_based",
            "classification_confidence": 1.0,  # Rules are deterministic
        }

        path_lower = file_path.lower().replace('\\', '/')

        # Apply all matching rules
        for pattern, values in self.rules['path_patterns'].items():
            if pattern in path_lower:
                metadata.update(values)

        # Extract tenant ID from path
        tenant_match = re.search(r'/tenant_([^/]+)/', path_lower)
        if tenant_match:
            metadata['owner_org_id'] = tenant_match.group(1)
            metadata['visibility_level'] = 'org_internal'

        # Extract genetic line from filename
        for line in ['ross', 'cobb', 'hubbard', 'aviagen', 'isa', 'hy-line']:
            if line in path_lower:
                metadata['genetic_line'] = line.capitalize()
                break

        return metadata
```

#### Configuration : classification_rules.yaml

```yaml
path_patterns:
  # Visibility / Security
  "/public/":
    visibility_level: "public_global"

  "/performancemetrics/":
    visibility_level: "org_shared"
    source_type: "performance_data"

  # Species
  "/broiler/":
    species: ["broiler"]

  "/layer/":
    species: ["layer"]

  # Category Level 1
  "/health/":
    category_level1: "Animal_Health"

  "/nutrition/":
    category_level1: "Nutrition"

  "/management/":
    category_level1: "Farm_Management"

  "/biosecurity/":
    category_level1: "Biosecurity"

  # Category Level 2
  "/vaccination/":
    category_level2: "Vaccination_Programs"

  "/disease/":
    category_level2: "Disease_Management"

  "/feed/":
    category_level2: "Feed_Formulation"

  "/water/":
    category_level2: "Water_Management"

# Add more rules as directory structure evolves
```

### Phase 2 : LLM Classification (Semaine 2)

#### Objectifs
- ✅ Implémenter LLM Classifier (Tier 2) avec GPT-4o-mini
- ✅ Intégrer avec Path Classifier dans Hybrid Classifier
- ✅ Tester sur 100 documents

#### Code : LLM Classifier

```python
# classifiers/llm_classifier.py
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

class LLMClassifier:
    """
    Tier 2: Use LLM for complex classification
    Coverage: ~25% of fields (requires content understanding)
    Cost: ~$0.001 per document (GPT-4o-mini)
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.prompt_template = self._load_prompt_template()

    async def classify(
        self,
        title: str,
        content_preview: str,
        existing_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to classify complex fields

        Args:
            title: Document title
            content_preview: First 500 words of document
            existing_metadata: Already classified fields (from path)

        Returns:
            Additional metadata fields
        """

        prompt = self.prompt_template.format(
            title=title,
            content_preview=content_preview[:2000],  # Limit tokens
            existing_classification=json.dumps(existing_metadata, indent=2)
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a poultry industry document classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Deterministic
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            result['classification_method'] = 'llm_based'
            result['classification_confidence'] = 0.85  # LLM confidence

            return result

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {"classification_confidence": 0.3}  # Low confidence fallback

    def _load_prompt_template(self) -> str:
        return """
Analyze this poultry document and provide classification:

**Document Title**: {title}
**Content Preview**: {content_preview}
**Already Classified**: {existing_classification}

Provide JSON with these fields:

1. production_stage: ["hatchery", "brooding", "growing", "finishing", "processing", "all_stages"]
2. site_type: ["hatchery", "broiler_farm", "layer_farm", "feed_mill", "processing_plant", "all_sites"]
3. category_level3: Specific topic within the category_level2
4. category_level4: 3-5 granular keywords/attributes
5. technical_tags: 5-10 searchable industry terms
6. geo_scope: "global" | "north_america" | "europe" | etc.
7. document_purpose: "reference_guide" | "troubleshooting" | "best_practices" | etc.

Return valid JSON only.
"""
```

#### Code : Hybrid Orchestrator

```python
# classifiers/hybrid_classifier.py
from typing import Dict, Any, Optional
from .path_classifier import PathBasedClassifier
from .llm_classifier import LLMClassifier

class HybridClassifier:
    """
    Orchestrator combining Tier 1 (Path) + Tier 2 (LLM) + Tier 3 (Defaults)

    Classification Strategy:
    1. Always run Path-Based (fast, free)
    2. Run LLM if path-based confidence < 0.8
    3. Apply smart defaults for missing fields
    """

    def __init__(
        self,
        path_classifier: PathBasedClassifier,
        llm_classifier: Optional[LLMClassifier] = None,
        enable_llm: bool = True
    ):
        self.path_classifier = path_classifier
        self.llm_classifier = llm_classifier
        self.enable_llm = enable_llm
        self.smart_defaults = self._load_smart_defaults()

    async def classify_document(
        self,
        file_path: str,
        title: str,
        content_preview: str
    ) -> Dict[str, Any]:
        """
        Full classification pipeline

        Returns:
            Complete metadata dictionary
        """

        # TIER 1: Path-Based (always run - free and fast)
        metadata = self.path_classifier.classify(file_path)

        # TIER 2: LLM-Based (conditional - costs money)
        needs_llm = (
            self.enable_llm and
            self.llm_classifier and
            metadata.get('classification_confidence', 0) < 0.8
        )

        if needs_llm:
            llm_metadata = await self.llm_classifier.classify(
                title=title,
                content_preview=content_preview,
                existing_metadata=metadata
            )

            # Merge, prioritizing higher confidence
            for key, value in llm_metadata.items():
                if key not in metadata or value:  # LLM fills gaps
                    metadata[key] = value

        # TIER 3: Smart Defaults (fill remaining gaps)
        for key, default_value in self.smart_defaults.items():
            if key not in metadata or not metadata[key]:
                metadata[key] = default_value

        # Calculate final confidence
        metadata['classification_confidence'] = self._calculate_confidence(metadata)

        return metadata

    def _calculate_confidence(self, metadata: Dict[str, Any]) -> float:
        """
        Calculate overall classification confidence

        Logic:
        - Path-based fields: 1.0
        - LLM fields: 0.85
        - Default fields: 0.5
        """
        method = metadata.get('classification_method', 'default')

        if method == 'path_based':
            return 1.0
        elif method == 'llm_based':
            return 0.85
        else:
            return 0.5

    def _load_smart_defaults(self) -> Dict[str, Any]:
        """Default values for unclassified fields"""
        return {
            "visibility_level": "public_global",
            "geo_scope": "global",
            "production_stage": ["all_stages"],
            "site_type": ["all_sites"],
            "source_type": "technical_guide",
            "document_purpose": "reference_guide",
            "language": "en",
        }
```

### Phase 3 : Intégration Pipeline (Semaine 3)

#### Objectifs
- ✅ Intégrer Hybrid Classifier dans knowledge_extractor.py
- ✅ Créer nouvelle collection Weaviate avec schéma complet
- ✅ Migrer 100 documents test vers nouvelle collection
- ✅ Valider filtrage multi-dimension

#### Modifications knowledge_extractor.py

```python
# knowledge_extractor.py (modifications)

class IntelligentKnowledgeExtractor:
    def __init__(self, collection_name: str = "KnowledgeChunks_v2", ...):
        # ... existing code ...

        # NEW: Initialize classifier
        self.classifier = HybridClassifier(
            path_classifier=PathBasedClassifier("config/classification_rules.yaml"),
            llm_classifier=LLMClassifier(api_key=os.getenv("OPENAI_API_KEY")),
            enable_llm=True
        )

    async def process_document(self, json_file: str, txt_file: str) -> Dict[str, Any]:
        """Enhanced with automatic classification"""

        # ... existing extraction logic ...

        # NEW: Classify document
        title = document_context.title or Path(json_file).stem
        content_preview = self._extract_preview(txt_file)

        classification_metadata = await self.classifier.classify_document(
            file_path=json_file,
            title=title,
            content_preview=content_preview
        )

        # Merge classification into document_context
        document_context.metadata.update(classification_metadata)

        # ... continue with chunking and ingestion ...
```

### Phase 4 : Testing & Validation (Semaine 4)

#### Tests Automatisés

```python
# tests/test_hybrid_classification.py
import pytest
from classifiers.hybrid_classifier import HybridClassifier

@pytest.mark.asyncio
async def test_public_broiler_health_document():
    """Test classification of public broiler health guide"""

    classifier = HybridClassifier(...)

    result = await classifier.classify_document(
        file_path="C:/documents/public/species/broiler/health/coccidiosis_guide.pdf",
        title="Coccidiosis Control in Broilers",
        content_preview="Coccidiosis is a parasitic disease caused by Eimeria species..."
    )

    # Assertions
    assert result['visibility_level'] == 'public_global'
    assert 'broiler' in result['species']
    assert result['category_level1'] == 'Animal_Health'
    assert result['category_level2'] == 'Disease_Management'
    assert result['category_level3'] == 'coccidiosis'
    assert 'coccidiosis' in result['technical_tags']
    assert result['classification_confidence'] > 0.8

@pytest.mark.asyncio
async def test_tenant_performance_data():
    """Test classification of tenant-specific performance metrics"""

    result = await classifier.classify_document(
        file_path="C:/documents/tenant_ABC/PerformanceMetrics/Broiler/Ross/2024Q1.json",
        title="Q1 2024 Ross Broiler Performance",
        content_preview="Average daily gain: 58.2g, FCR: 1.68, Mortality: 3.2%..."
    )

    assert result['visibility_level'] == 'org_internal'
    assert result['owner_org_id'] == 'ABC'
    assert result['source_type'] == 'performance_data'
    assert result['genetic_line'] == 'Ross'

@pytest.mark.asyncio
async def test_llm_fallback():
    """Test LLM kicks in for ambiguous documents"""

    result = await classifier.classify_document(
        file_path="C:/documents/unknown_folder/mystery_doc.pdf",
        title="Advanced Feeding Strategies",
        content_preview="Modern feeding programs require precise nutrient timing..."
    )

    # Should use LLM since path gives low confidence
    assert result['classification_method'] == 'llm_based'
    assert 0.7 < result['classification_confidence'] < 0.9
```

#### Validation Manuelle

Créer dashboard de validation :

```python
# scripts/validate_classifications.py
"""
Interactive validation tool for reviewing classifications
"""

def review_classifications(sample_size: int = 50):
    """
    Present random sample of classified documents for human review

    Metrics to track:
    - Accuracy per field
    - Path-based accuracy
    - LLM-based accuracy
    - Fields requiring correction
    """

    # Retrieve random sample
    # Display classification results
    # Allow corrections
    # Calculate accuracy metrics
    # Update rules if needed
```

---

## Exemples Concrets

### Exemple 1 : Document Public - Guide de Vaccination

**File Path** : `C:\documents\public\species\broiler\health\vaccination\ross_vaccination_guide_2024.pdf`

**Classification Automatique** :

```json
{
  "visibility_level": "public_global",
  "owner_org_id": null,
  "allowed_org_ids": [],
  "species": ["broiler"],
  "genetic_line": "Ross",
  "production_stage": ["hatchery", "brooding"],
  "site_type": ["hatchery", "broiler_farm"],
  "climate_zone": ["multiple_zones"],
  "geo_region": ["global"],
  "source_type": "technical_guide",
  "document_purpose": "reference_guide",
  "language": "en",

  "category_level1": "Animal_Health",
  "category_level2": "Vaccination_Programs",
  "category_level3": "broiler_vaccination",
  "category_level4": ["vaccination_schedule", "dose_recommendations", "marek_disease", "newcastle_disease"],

  "technical_tags": ["vaccination", "immunization", "broiler", "ross", "marek", "newcastle", "infectious_bursal_disease", "hatchery_vaccination"],
  "entities": ["Ross", "Marek's Disease", "Newcastle Disease", "IBD"],

  "classification_method": "hybrid",
  "classification_confidence": 0.95
}
```

**Méthode** :
- Path-based : visibility_level, species, genetic_line, category_level1-2
- LLM-based : category_level3-4, technical_tags, production_stage, document_purpose

### Exemple 2 : Document Tenant - Données de Performance

**File Path** : `C:\documents\tenant_FermesDuQuebec\PerformanceMetrics\Broiler\Cobb\2024\Q3_results.json`

**Classification Automatique** :

```json
{
  "visibility_level": "org_internal",
  "owner_org_id": "FermesDuQuebec",
  "allowed_org_ids": [],
  "species": ["broiler"],
  "genetic_line": "Cobb",
  "production_stage": ["growing", "finishing"],
  "site_type": ["broiler_farm"],
  "climate_zone": ["temperate_mild"],
  "geo_region": ["north_america"],
  "source_type": "performance_data",
  "document_purpose": "performance_tracking",
  "language": "fr",

  "category_level1": "Performance_Metrics",
  "category_level2": "Growth_Performance",
  "category_level3": "production_kpis",
  "category_level4": ["daily_gain", "fcr", "mortality", "uniformity"],

  "technical_tags": ["performance", "kpi", "fcr", "adg", "mortality", "cobb500", "quarterly_report"],
  "entities": ["Cobb 500", "Quebec"],

  "classification_method": "path_based",
  "classification_confidence": 1.0
}
```

**Méthode** :
- Path-based : 100% (structure de répertoire très claire)

### Exemple 3 : Document Ambigu - Recherche Académique

**File Path** : `C:\documents\uploads\nutrition_research_2024.pdf`

**Classification Automatique** :

```json
{
  "visibility_level": "public_global",
  "owner_org_id": null,
  "species": ["broiler", "layer"],
  "genetic_line": null,
  "production_stage": ["all_stages"],
  "site_type": ["broiler_farm", "layer_farm"],
  "climate_zone": ["temperate_hot", "temperate_mild"],
  "geo_region": ["global"],
  "source_type": "research_paper",
  "document_purpose": "reference_guide",
  "language": "en",

  "category_level1": "Nutrition",
  "category_level2": "Feed_Formulation",
  "category_level3": "amino_acid_nutrition",
  "category_level4": ["methionine", "lysine", "threonine", "protein_efficiency"],

  "technical_tags": ["nutrition", "amino_acids", "protein", "feed_formulation", "methionine", "lysine", "digestibility"],
  "entities": ["University of Guelph", "Dr. Smith"],

  "classification_method": "llm_based",
  "classification_confidence": 0.85
}
```

**Méthode** :
- Path-based : visibility_level (default)
- LLM-based : Tout le reste (pas d'indices dans le path)

---

## Validation et Tests

### Métriques de Succès

1. **Couverture de Classification** : >90% des champs remplis automatiquement
2. **Précision** : >85% des classifications correctes (validation manuelle)
3. **Performance** : <500ms pour path-based, <2s pour LLM-based
4. **Coût** : <$0.002 par document en moyenne

### Plan de Test

#### Phase 1 : Test Path-Based (20 documents)
- 5 documents public/broiler/health → Valider category_level1-2
- 5 documents tenant → Valider visibility_level, owner_org_id
- 5 documents PerformanceMetrics → Valider source_type
- 5 documents ambigus → Valider fallback vers LLM

#### Phase 2 : Test LLM-Based (50 documents)
- Comparer classifications LLM vs. classification manuelle
- Mesurer précision par champ
- Identifier patterns d'erreurs
- Ajuster prompts si nécessaire

#### Phase 3 : Test End-to-End (100 documents)
- Pipeline complet : extraction → classification → ingestion
- Valider filtrage Weaviate
- Tests de requêtes multi-filtres
- Performance queries

### Queries de Test

```python
# Test 1: Broiler health documents for Tenant A
results = collection.query.near_text(
    query="coccidiosis prevention broilers",
    filters=(
        Filter.by_property("category_level1").equal("Animal_Health") &
        (
            Filter.by_property("visibility_level").equal("public_global") |
            (
                Filter.by_property("visibility_level").equal("org_shared") &
                Filter.by_property("owner_org_id").equal("TenantA")
            )
        )
    )
)

# Test 2: Ross broiler nutrition guides
results = collection.query.near_text(
    query="feed formulation ross broilers",
    filters=(
        Filter.by_property("genetic_line").equal("Ross") &
        Filter.by_property("species").contains_any(["broiler"]) &
        Filter.by_property("category_level1").equal("Nutrition")
    )
)

# Test 3: Hatchery-specific vaccination protocols
results = collection.query.near_text(
    query="hatchery vaccination schedule",
    filters=(
        Filter.by_property("site_type").contains_any(["hatchery"]) &
        Filter.by_property("category_level2").equal("Vaccination_Programs")
    )
)
```

---

## Prochaines Étapes

### Immédiat (Cette Semaine)
1. ✅ Attendre résultats Phase 2 A/B Test chunking
2. ⏳ Créer `classifiers/path_classifier.py`
3. ⏳ Créer `config/classification_rules.yaml`
4. ⏳ Tester sur 5 documents

### Court Terme (2-3 Semaines)
1. Implémenter LLM Classifier
2. Créer Hybrid Classifier orchestrator
3. Intégrer dans knowledge_extractor
4. Tester sur 50 documents

### Moyen Terme (1 Mois)
1. Créer nouvelle collection Weaviate avec schéma complet
2. Migration progressive des documents
3. Dashboard de validation des classifications
4. Ajustement des règles basé sur feedback

### Long Terme (2-3 Mois)
1. Migration complète vers nouvelle architecture
2. Dépréciation ancienne collection
3. Documentation utilisateur
4. Formation équipe

---

## Annexe : Questions & Décisions

### Décisions Confirmées avec l'Utilisateur

1. **✅ Lignées génétiques** : Champ OUVERT et extensible
   - Raison : Nouvelles lignées régionales découvertes en continu (impossible de prévoir)
   - Solution : Champ TEXT libre, pas de liste fermée
   - Exemples connus : Ross, Cobb, Hubbard, Aviagen, ISA, Hy-Line, mais accepte toute valeur
   - Le LLM peut extraire automatiquement les noms de lignées du contenu

2. **✅ Classification géographique** : Par ZONES CLIMATIQUES (pas régions géographiques)
   - Raison : Plus pertinent pour l'aviculture (conditions d'élevage similaires)
   - Zones : **tropical, subtropical, temperate, cold, hot_arid, multiple_zones**
   - Optionnel : geo_region pour ciblage spécifique (north_america, europe, asia, etc.)
   - Avantage : Document "ventilation tropicale" applicable Brésil + Asie du Sud-Est + Afrique centrale

   **Définition des Zones Climatiques (voir Annexe pour détails complets)** :

   - **Tropical** : Chaud et humide toute l'année (>18°C, >1500mm pluie)
     → 🇧🇷 Brésil Nord, 🇮🇩 Indonésie, 🇵🇭 Philippines, 🇹🇭 Thaïlande, 🇲🇾 Malaisie, 🇳🇬 Nigeria, 🇮🇳 Inde Sud

   - **Subtropical** : Étés chauds, hivers doux, alternance saison sèche/humide
     → 🇨🇳 Chine Sud-Est, 🇲🇽 Mexique Centre, 🇦🇺 Australie Nord, 🇺🇸 Floride/Texas, 🇦🇷 Argentine Nord

   - **Temperate** : Quatre saisons, températures modérées
     → 🇫🇷 France, 🇩🇪 Allemagne, 🇨🇦 Canada Sud, 🇺🇸 Nord-Est, 🇯🇵 Japon, 🇦🇺 Australie Sud

   - **Cold** : Longs hivers rigoureux (<10°C majeure partie année)
     → 🇨🇦 Canada Nord, 🇷🇺 Russie, 🇫🇮 Finlande, 🇸🇪 Suède, 🇳🇴 Norvège

   - **Hot/Arid** : Chaleur extrême, faible humidité (<250mm pluie/an)
     → 🇸🇦 Arabie Saoudite, 🇦🇪 Émirats, 🇪🇬 Égypte, 🇶🇦 Qatar, 🇦🇺 Australie Centre, 🇨🇱 Chili Nord

3. **LLM Model** : GPT-4o-mini suffisant ?
   - Avantage : Coût bas (~$0.001/doc)
   - Alternative : GPT-4o pour meilleure précision (+$0.005/doc)
   - Recommandation : Commencer avec 4o-mini, upgrade si besoin

4. **Classification Validation** : Qui valide ?
   - Option 1 : Validation automatique (sample aléatoire)
   - Option 2 : Validation manuelle systématique
   - Recommandation : Hybrid - automatique + spot checks manuels

### Décisions Prises

✅ **Single Collection** : Confirmé - plus simple et flexible
✅ **Hybrid Classification** : Path + LLM + Defaults
✅ **Schema 39 champs** : Approuvé pour couvrir tous les cas
✅ **Multi-tenant Support** : Via visibility_level + owner_org_id
✅ **4-Level Taxonomy** : Confirmé pour granularité

---

## Annexe A : Taxonomie Climatique Détaillée

Cette taxonomie est optimisée pour l'aviculture, où les **conditions climatiques** déterminent les pratiques d'élevage (ventilation, refroidissement, chauffage, densité, alimentation).

### 1. Tropical Climate 🌴

**Caractéristiques** :
- Chaud et humide toute l'année
- Peu de variation saisonnière
- Température moyenne > 18°C
- Précipitations fortes (> 1500 mm/an)

**Challenges avicoles** :
- Stress thermique constant
- Humidité élevée → maladies respiratoires
- Litière humide → problèmes de pattes
- Refroidissement évaporatif nécessaire

**Pays concernés** :
- 🇧🇷 **Brésil** (Nord et Centre) : Amazonie, Mato Grosso
- 🇮🇩 **Indonésie** : Java, Sumatra, Kalimantan
- 🇵🇭 **Philippines** : Luzon, Mindanao
- 🇹🇭 **Thaïlande** : Régions centrales et Sud
- 🇲🇾 **Malaisie** : Péninsule malaise, Sabah, Sarawak
- 🇳🇬 **Nigeria** : Delta du Niger, Sud
- 🇰🇪 **Kenya** : Zones côtières (Mombasa)
- 🇨🇩 **RD Congo** : Bassin du Congo
- 🇮🇳 **Inde** : Sud (Kerala, Tamil Nadu)
- 🇪🇨 **Équateur** : Zones côtières et Amazonie
- 🇨🇷 **Costa Rica** : Zones basses
- 🇨🇴 **Colombie** : Zones basses (Amazonie, Côte Pacifique)

**Exemple de contenu pertinent** :
- "Cooling systems for high humidity broiler houses"
- "Tropical disease management: coccidiosis and necrotic enteritis"
- "Litter management in wet tropical conditions"

---

### 2. Subtropical Climate 🌞

**Caractéristiques** :
- Étés chauds, hivers doux à frais
- Alternance saison sèche/humide OU hiver frais
- Températures modérées avec variations saisonnières
- Précipitations variables

**Challenges avicoles** :
- Gestion saisonnière (chauffage hiver, refroidissement été)
- Transitions climatiques → stress
- Ventilation adaptative nécessaire
- Maladies saisonnières

**Pays concernés** :
- 🇨🇳 **Chine** : Sud-Est (Guangdong, Fujian, Guangxi)
- 🇲🇽 **Mexique** : Centre et Nord-Est (Jalisco, Veracruz)
- 🇦🇺 **Australie** : Nord (Queensland Nord)
- 🇿🇦 **Afrique du Sud** : Nord-Est (KwaZulu-Natal)
- 🇬🇷 **Grèce** : Ensemble du pays
- 🇪🇸 **Espagne** : Sud (Andalousie, Murcie)
- 🇺🇸 **États-Unis** : Sud-Est (Floride, Géorgie, Texas, Louisiane)
- 🇹🇷 **Turquie** : Sud (Méditerranée)
- 🇮🇷 **Iran** : Sud (Golfe Persique)
- 🇨🇱 **Chili** : Centre (Santiago, Valparaíso)
- 🇦🇷 **Argentine** : Nord (Tucumán, Salta)

**Exemple de contenu pertinent** :
- "Seasonal ventilation management for subtropical poultry farms"
- "Heat stress mitigation during summer peaks"
- "Winter heating strategies for mild climates"

---

### 3. Temperate Climate 🍂

**Caractéristiques** :
- Quatre saisons bien marquées
- Températures modérées
- Précipitations réparties sur l'année
- Hiver froid mais pas extrême

**Challenges avicoles** :
- Chauffage significatif en hiver
- Ventilation contrôlée
- Isolation thermique critique
- Gestion transition printemps/automne

**Pays concernés** :
- 🇫🇷 **France** : Ensemble du pays
- 🇩🇪 **Allemagne** : Ensemble du pays
- 🇬🇧 **Royaume-Uni** : Angleterre, Écosse, Pays de Galles
- 🇨🇦 **Canada** : Sud (Ontario, Québec Sud)
- 🇺🇸 **États-Unis** : Nord, Nord-Est (New York, Pennsylvania, Ohio)
- 🇯🇵 **Japon** : Honshū, Kyūshū
- 🇨🇳 **Chine** : Centre (Jiangsu, Zhejiang, Anhui)
- 🇰🇷 **Corée du Sud** : Ensemble du pays
- 🇦🇺 **Australie** : Sud (Victoria, Nouvelle-Galles du Sud Sud)
- 🇳🇿 **Nouvelle-Zélande** : Île du Nord et du Sud
- 🇨🇱 **Chili** : Sud (Région des Lacs)
- 🇦🇷 **Argentine** : Centre-Sud (Buenos Aires, Pampa)

**Exemple de contenu pertinent** :
- "Insulation and heating systems for temperate broiler houses"
- "Seasonal lighting programs for layers"
- "Winter biosecurity protocols"

---

### 4. Cold Climate ❄️

**Caractéristiques** :
- Longs hivers rigoureux
- Été court et doux
- Température moyenne < 10°C majeure partie de l'année
- Neige et gel fréquents

**Challenges avicoles** :
- Chauffage intensif (coût élevé)
- Isolation maximale nécessaire
- Ventilation minimale (conserver chaleur)
- Gestion eau (gel)
- Courte saison de production extérieure

**Pays concernés** :
- 🇨🇦 **Canada** : Nord (Alberta, Saskatchewan, Manitoba Nord, Territoires)
- 🇷🇺 **Russie** : Sibérie, Oural, Nord-Ouest
- 🇫🇮 **Finlande** : Ensemble du pays
- 🇸🇪 **Suède** : Centre et Nord
- 🇳🇴 **Norvège** : Ensemble du pays
- 🇮🇸 **Islande** : Ensemble du pays
- 🇺🇸 **États-Unis** : Alaska, Montana, Dakota du Nord
- 🇨🇭 **Suisse** : Zones montagneuses (Alpes)
- 🇨🇱 **Chili** : Patagonie (Région de Magallanes)

**Exemple de contenu pertinent** :
- "Extreme cold management for broiler production"
- "Energy-efficient heating systems for arctic conditions"
- "Winter water management and freeze prevention"

---

### 5. Hot/Arid Climate 🏜️

**Caractéristiques** :
- Chaleur extrême
- Faible humidité
- Fortes variations jour/nuit
- Pluviométrie < 250 mm/an
- Peu ou pas de végétation

**Challenges avicoles** :
- Stress thermique diurne sévère
- Déshydratation rapide
- Poussière excessive
- Refroidissement évaporatif très efficace (air sec)
- Isolation contre chaleur

**Pays concernés** :
- 🇸🇦 **Arabie Saoudite** : Ensemble du pays (désert arabique)
- 🇦🇪 **Émirats arabes unis** : Ensemble du pays
- 🇴🇲 **Oman** : Intérieur (désert)
- 🇪🇬 **Égypte** : Désert occidental et oriental
- 🇱🇾 **Libye** : Intérieur (Sahara)
- 🇶🇦 **Qatar** : Ensemble du pays
- 🇮🇷 **Iran** : Centre (déserts Dasht-e Kavir, Dasht-e Lut)
- 🇨🇱 **Chili** : Nord (désert d'Atacama)
- 🇦🇺 **Australie** : Centre (outback, Great Victoria Desert)
- 🇲🇱 **Mali** : Nord (Sahara, Sahel)

**Exemple de contenu pertinent** :
- "Evaporative cooling for arid climates"
- "Water consumption management in desert conditions"
- "Dust control in hot arid poultry farms"

---

### 6. Multiple Zones 🌍

**Utilisation** : Documents applicables à plusieurs zones climatiques simultanément.

**Exemples** :
- Guides généraux de biosécurité (applicables partout)
- Standards de qualité internationaux
- Génétique et sélection (indépendant du climat)
- Maladies globales (Newcastle, Influenza aviaire)

**Classification** :
```json
{
  "climate_zone": ["multiple_zones"],
  "geo_region": ["global"]
}
```

---

## Cas d'Usage : Filtrage Intelligent par Climat

### Exemple 1 : Utilisateur au Brésil (tropical/subtropical)

**Query** : "Comment gérer la ventilation dans ma ferme de poulets ?"

**Filtre automatique appliqué** :
```python
climate_filter = (
    Filter.by_property("climate_zone").contains_any(["tropical", "subtropical", "multiple_zones"])
)
```

**Résultats pertinents** :
✅ Guide ventilation tropicale (Thaïlande)
✅ Cooling systems humidité élevée (Philippines)
✅ Standards internationaux ventilation (global)
❌ Systèmes chauffage hiver Canada (cold)
❌ Désert cooling Arabie Saoudite (hot_arid)

### Exemple 2 : Utilisateur en Arabie Saoudite (hot_arid)

**Query** : "Réduire mortalité chaleur"

**Filtre automatique appliqué** :
```python
climate_filter = (
    Filter.by_property("climate_zone").contains_any(["hot_arid", "subtropical", "multiple_zones"])
)
```

**Résultats pertinents** :
✅ Evaporative cooling désert (Arabie, Australie centre)
✅ Gestion eau chaleur extrême
✅ Stress thermique général (multiple_zones)
✅ Subtropical chaleur sèche été (Espagne)
❌ Chauffage hiver (cold, temperate)

### Exemple 3 : Utilisateur en France (temperate)

**Query** : "Programme d'élevage annuel"

**Filtre automatique appliqué** :
```python
climate_filter = (
    Filter.by_property("climate_zone").contains_any(["temperate", "multiple_zones"])
)
```

**Résultats pertinents** :
✅ Gestion 4 saisons (Allemagne, UK)
✅ Transition printemps/automne (Japon)
✅ Standards généraux (multiple_zones)
❌ Tropical constant (Indonésie)
❌ Désert chaleur extrême (Qatar)

---

**Document Version** : 1.1
**Dernière Mise à Jour** : 2025-10-29 (Ajout Annexe Climatique)
**Auteur** : Claude Code (Assistant IA)
**Statut** : Prêt pour Revue & Implémentation
