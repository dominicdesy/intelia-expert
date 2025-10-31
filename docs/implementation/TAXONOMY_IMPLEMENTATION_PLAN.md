# Plan d'Implémentation - Taxonomie Automatique Simple & Efficace

**Date**: 2025-10-29
**Objectif**: Classifier automatiquement 90% des métadonnées avec intervention manuelle minimale

---

## 🎯 Stratégie : 3 Niveaux d'Automatisation

```
┌─────────────────────────────────────────────────────┐
│ Niveau 1: Path-based (70% auto)  ← Arborescence    │
│ Niveau 2: LLM-based (25% auto)   ← Claude/GPT      │
│ Niveau 3: Defaults (5% auto)     ← Règles simples  │
└─────────────────────────────────────────────────────┘
```

---

## 📋 Mapping Détaillé

### 1. SÉCURITÉ / ACCÈS (100% automatique via path)

| Dossier | visibility_level | owner_org_id | allowed_org_ids |
|---------|------------------|--------------|-----------------|
| `public/` | `public_global` | `INTELIA_GLOBAL` | `[]` |
| `tenant_ABC/` | `org_shared` | `ABC` | `[]` |
| `tenant_ABC/site_X/` | `org_internal` | `ABC` | `["ABC_SITE_X"]` |

**Règle simple** :
```python
if "public" in path:
    visibility = "public_global"
elif "tenant_" in path:
    org_id = extract_org_id(path)  # "tenant_ABC" → "ABC"
    if has_subdivision(path):  # ex: /site_X/
        visibility = "org_internal"
        allowed_org_ids = [f"{org_id}_SITE_X"]
    else:
        visibility = "org_shared"
```

---

### 2. CONTEXTE MÉTIER (80% automatique)

#### 2.1 Species (100% auto)

| Path Contains | species | Notes |
|---------------|---------|-------|
| `/broiler/` | `["broiler"]` | |
| `/layer/` | `["layer"]` | |
| `/breeder/` | `["breeder"]` | |
| `/turkey/` | `["turkey"]` | |
| `/common/` | `["broiler", "layer", "breeder"]` | Multi-espèces |

#### 2.2 Source Type (100% auto via path + filename)

| Path/Filename Pattern | source_type |
|----------------------|-------------|
| `/PerformanceMetrics/` | `genetic_guide` |
| `/breeds/ross_308/` | `genetic_guide` |
| `/regulations/` | `regulatory_standard` |
| `/tenant_*/` + "SOP" in filename | `internal_SOP_client` |
| `/tenant_*/` + "report" in filename | `field_report` |
| "scientific" or "journal" in filename | `scientific_article` |

#### 2.3 Geo Scope (80% auto)

**Par défaut** : `["global"]`

**Si détecté dans path/filename** :
- "EU" → `["EU"]`
- "Canada" or "CA" → `["North_America", "Country_CA"]`
- "USA" or "US" → `["North_America", "Country_US"]`

#### 2.4 Production Stage (LLM - 80% auto)

**LLM analyse titre + contenu** pour déduire :
```python
# Patterns simples d'abord
if "brooding" in title or "day 1-7" in content:
    production_stage = "starter"
elif "finisher" in title or "day 35+" in content:
    production_stage = "finisher"
else:
    # LLM classification si ambigu
    production_stage = llm_classify_stage(content)
```

#### 2.5 Site Type (LLM - 70% auto)

**Patterns** :
- "hatchery" in path → `hatchery`
- "processing" in path → `processing_plant`
- "feed" in path → `feed_mill`
- Sinon : LLM déduit du contenu

---

### 3. TAXONOMIE 4 NIVEAUX

#### 3.1 Category (90% auto - Path + LLM)

**Mapping Path → Category** :

| Directory | Category |
|-----------|----------|
| `/health/` | `Health & Biosecurity` |
| `/nutrition/` | `Feed & Nutrition` |
| `/breeds/` ou `/genetics/` | `Animal Performance & Biology` |
| `/housing/` ou `/environment/` | `Environment & Housing` |
| `/welfare/` | `Welfare & Compliance` |
| `/biosecurity/` | `Health & Biosecurity` |
| `/sustainability/` | `Economics & Benchmarking` |
| `/value_chain/` | `Processing & Product Quality` |
| `/regulations/` | `Regulations & Certification` |
| `/PerformanceMetrics/` | `Animal Performance & Biology` |

**Fallback LLM** : Si path ambigu, LLM lit contenu et choisit parmi les 12 catégories fixes.

#### 3.2 Subcategory (70% LLM)

**LLM Prompt Simple** :
```
Analyze this poultry document chunk.
Category: {category}
Content: {content[:500]}

Choose ONE subcategory from this list:
[liste des subcategories pour cette category]

Return only the subcategory name.
```

**Exemples de Patterns détectables automatiquement** :
- Category="Health" + "vaccination" in content → `Vaccination Programs`
- Category="Health" + "Salmonella" in content → `Infectious Diseases`
- Category="Environment" + "ventilation" in content → `Ventilation & Air Quality`

#### 3.3 Topic (90% LLM avec validation)

**Approche** :
1. **Filename d'abord** : `ascites.pdf` → topic = `ascites`
2. **LLM génère topic** : Court, snake_case, réutilisable
3. **Validation** : Normalise selon liste existante

**LLM Prompt** :
```
Extract the specific topic of this poultry content.
Category: {category}
Subcategory: {subcategory}
Content: {content[:500]}

Generate a short, reusable topic name (snake_case).
Examples: "target_weight_day_35", "tunnel_ventilation_parameters", "vaccination_schedule"

Topic:
```

#### 3.4 Attributes (100% LLM)

**LLM Extraction Structurée** :
```
Extract technical parameters from this poultry content as JSON.

Category: {category}
Subcategory: {subcategory}
Topic: {topic}
Content: {content}

Return a JSON object with relevant parameters.
Examples:
- For weight targets: {age_days, body_weight_kg, genetic_line, sex}
- For temperature: {age_days_start, age_days_end, setpoint_temp_C, tolerance_C}
- For vaccination: {vaccine_name, age_days, route, dosage}

Return ONLY valid JSON:
```

---

## 🛠️ Architecture du Classifier

### Fichier : `hybrid_classifier.py`

```python
"""
Hybrid Classifier: Path-based (70%) + LLM-based (30%)
Minimizes manual classification while maintaining accuracy
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


class HybridClassifier:
    """
    3-tier classification:
    1. Path-based (instant, free)
    2. LLM-based (smart, minimal cost)
    3. Defaults (fallback)
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.path_mappings = self._load_path_mappings()
        self.category_list = self._load_category_taxonomy()

    def classify(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Full classification pipeline
        Returns complete metadata for Weaviate
        """
        logger.info(f"🔍 Classifying: {file_path}")

        metadata = {}

        # ═══════════════════════════════════════════
        # TIER 1: PATH-BASED (instant, 70% coverage)
        # ═══════════════════════════════════════════
        path_metadata = self._classify_from_path(file_path)
        metadata.update(path_metadata)
        logger.debug(f"   Path-based: {path_metadata}")

        # ═══════════════════════════════════════════
        # TIER 2: LLM-BASED (smart, 25% coverage)
        # ═══════════════════════════════════════════
        # Only call LLM for missing critical fields
        llm_metadata = self._classify_with_llm(
            content=content,
            existing_metadata=metadata,
            file_path=file_path
        )
        metadata.update(llm_metadata)
        logger.debug(f"   LLM-based: {llm_metadata}")

        # ═══════════════════════════════════════════
        # TIER 3: DEFAULTS (fallback, 5% coverage)
        # ═══════════════════════════════════════════
        metadata = self._apply_defaults(metadata)

        logger.info(f"✅ Classification complete: category={metadata.get('category')}, topic={metadata.get('topic')}")
        return metadata

    def _classify_from_path(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from directory structure"""
        path = Path(file_path)
        parts = [p.lower() for p in path.parts]
        metadata = {}

        # 1. SECURITY
        if "public" in parts:
            metadata["visibility_level"] = "public_global"
            metadata["owner_org_id"] = "INTELIA_GLOBAL"
            metadata["allowed_org_ids"] = []

        for part in path.parts:
            if part.startswith("tenant_"):
                org_id = part.replace("tenant_", "")
                metadata["owner_org_id"] = org_id

                # Check for subdivision
                if len([p for p in parts if "site" in p or "division" in p]) > 0:
                    metadata["visibility_level"] = "org_internal"
                    metadata["allowed_org_ids"] = [f"{org_id}_SUBDIVISION"]
                else:
                    metadata["visibility_level"] = "org_shared"
                    metadata["allowed_org_ids"] = []

        # 2. SPECIES
        if "broiler" in parts:
            metadata["species"] = ["broiler"]
        elif "layer" in parts:
            metadata["species"] = ["layer"]
        elif "breeder" in parts:
            metadata["species"] = ["breeder"]
        elif "turkey" in parts:
            metadata["species"] = ["turkey"]
        elif "common" in parts:
            metadata["species"] = ["broiler", "layer", "breeder"]

        # 3. SOURCE TYPE
        if "performancemetrics" in parts or "performance" in parts:
            metadata["source_type"] = "genetic_guide"
        elif "regulations" in parts or "regulatory" in parts:
            metadata["source_type"] = "regulatory_standard"
        elif any(t in parts for t in ["tenant_", "internal"]):
            if "sop" in path.name.lower():
                metadata["source_type"] = "internal_SOP_client"
            elif "report" in path.name.lower():
                metadata["source_type"] = "field_report"

        # 4. CATEGORY (from path)
        category_mapping = {
            "health": "Health & Biosecurity",
            "nutrition": "Feed & Nutrition",
            "breeds": "Animal Performance & Biology",
            "genetics": "Animal Performance & Biology",
            "housing": "Environment & Housing",
            "environment": "Environment & Housing",
            "welfare": "Welfare & Compliance",
            "biosecurity": "Health & Biosecurity",
            "sustainability": "Economics & Benchmarking",
            "value_chain": "Processing & Product Quality",
            "processing": "Processing & Product Quality",
            "regulations": "Regulations & Certification",
            "performancemetrics": "Animal Performance & Biology",
        }

        for part in parts:
            if part in category_mapping:
                metadata["category"] = category_mapping[part]
                break

        # 5. TOPIC (from filename)
        filename_no_ext = path.stem.replace("_extracted", "")
        metadata["topic"] = filename_no_ext.replace("-", "_").replace(" ", "_").lower()

        # 6. SOURCE NAME
        metadata["source_name"] = path.name

        return metadata

    def _classify_with_llm(
        self,
        content: str,
        existing_metadata: Dict[str, Any],
        file_path: str
    ) -> Dict[str, Any]:
        """
        Use LLM only for missing/complex fields
        Minimizes API calls and cost
        """
        llm_metadata = {}

        # Only call LLM if category is missing
        if "category" not in existing_metadata:
            llm_metadata["category"] = self._llm_classify_category(content)

        # Get subcategory (depends on category)
        category = existing_metadata.get("category") or llm_metadata.get("category")
        if category:
            llm_metadata["subcategory"] = self._llm_classify_subcategory(
                content, category
            )

        # Refine topic with LLM (make it more standard)
        if "topic" in existing_metadata:
            llm_metadata["topic"] = self._llm_normalize_topic(
                content,
                existing_metadata["topic"],
                category,
                llm_metadata.get("subcategory")
            )

        # Extract attributes (always use LLM for this)
        llm_metadata["attributes"] = self._llm_extract_attributes(
            content,
            category,
            llm_metadata.get("subcategory"),
            llm_metadata.get("topic")
        )

        # Production stage if not obvious from path
        if "production_stage" not in existing_metadata:
            llm_metadata["production_stage"] = self._llm_classify_production_stage(
                content
            )

        return llm_metadata

    def _llm_classify_category(self, content: str) -> str:
        """LLM chooses from 12 fixed categories"""
        prompt = f"""Classify this poultry document into ONE category.

Content (first 500 chars):
{content[:500]}

Categories (choose exactly one):
1. Animal Performance & Biology
2. Environment & Housing
3. Feed & Nutrition
4. Health & Biosecurity
5. Welfare & Compliance
6. Hatchery & Reproduction
7. Planning & Logistics
8. Processing & Product Quality
9. Economics & Benchmarking
10. Regulations & Certification
11. Technology & Sensing
12. Internal Programs & SOP

Return ONLY the category name:"""

        response = self.llm_client.classify(prompt)
        return response.strip()

    def _llm_classify_subcategory(self, content: str, category: str) -> str:
        """LLM chooses subcategory based on category"""

        # Get valid subcategories for this category
        valid_subcategories = self.category_list[category]["subcategories"]

        prompt = f"""Choose the most specific subcategory for this content.

Category: {category}
Content (first 500 chars):
{content[:500]}

Valid subcategories for "{category}":
{chr(10).join(f"- {sc}" for sc in valid_subcategories)}

Return ONLY the subcategory name:"""

        response = self.llm_client.classify(prompt)
        return response.strip()

    def _llm_normalize_topic(
        self, content: str, raw_topic: str, category: str, subcategory: str
    ) -> str:
        """LLM creates standard, reusable topic name"""

        prompt = f"""Generate a standardized topic name for this content.

Category: {category}
Subcategory: {subcategory}
Current topic: {raw_topic}
Content (first 300 chars):
{content[:300]}

Requirements:
- Short, specific, reusable
- snake_case format
- Examples: "target_weight_day_35", "tunnel_ventilation_parameters", "vaccination_schedule"

Standardized topic:"""

        response = self.llm_client.classify(prompt)
        return response.strip().replace(" ", "_").replace("-", "_").lower()

    def _llm_extract_attributes(
        self, content: str, category: str, subcategory: str, topic: str
    ) -> Dict[str, Any]:
        """LLM extracts structured parameters"""

        prompt = f"""Extract technical parameters from this poultry content as JSON.

Category: {category}
Subcategory: {subcategory}
Topic: {topic}
Content:
{content[:1000]}

Extract relevant parameters. Examples:
- Weight targets: {{"age_days": 35, "body_weight_kg": 2.45, "genetic_line": "Ross 308", "sex": "male"}}
- Temperature: {{"age_days_start": 0, "age_days_end": 3, "setpoint_temp_C": 32, "tolerance_C": 1.0}}
- Vaccination: {{"vaccine_name": "IBV spray", "age_days": 1, "route": "spray cabinet"}}

Return ONLY valid JSON (no explanation):"""

        try:
            response = self.llm_client.classify(prompt)
            # Parse JSON response
            attributes = json.loads(response)
            return attributes
        except Exception as e:
            logger.warning(f"Failed to parse LLM attributes: {e}")
            return {}

    def _llm_classify_production_stage(self, content: str) -> str:
        """LLM determines production stage"""

        # Try pattern matching first
        content_lower = content.lower()

        if any(word in content_lower for word in ["hatchery", "incubation", "hatching"]):
            return "hatchery"
        elif any(word in content_lower for word in ["brooding", "day 1-7", "starter phase"]):
            return "starter"
        elif any(word in content_lower for word in ["grower", "day 11-28"]):
            return "grower"
        elif any(word in content_lower for word in ["finisher", "day 29+", "pre-slaughter"]):
            return "finisher"
        elif any(word in content_lower for word in ["laying", "egg production"]):
            return "laying_start"

        # If ambiguous, ask LLM
        prompt = f"""Determine the production stage for this poultry content.

Content (first 300 chars):
{content[:300]}

Stages:
- hatchery
- starter (0-10 days)
- grower (11-28 days)
- finisher (29+ days)
- laying_start
- peak_lay
- late_lay
- transport
- processing_plant
- multi-stage

Return ONLY the stage name:"""

        response = self.llm_client.classify(prompt)
        return response.strip()

    def _apply_defaults(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for missing fields"""

        # Defaults
        metadata.setdefault("geo_scope", ["global"])
        metadata.setdefault("language", "en")
        metadata.setdefault("createdAt", datetime.now().isoformat())
        metadata.setdefault("updatedAt", datetime.now().isoformat())

        # If still missing visibility, default to public
        metadata.setdefault("visibility_level", "public_global")
        metadata.setdefault("owner_org_id", "INTELIA_GLOBAL")
        metadata.setdefault("allowed_org_ids", [])

        return metadata

    def _load_category_taxonomy(self) -> Dict[str, Any]:
        """Load full category/subcategory taxonomy"""
        # This would load from a config file
        # Simplified version here
        return {
            "Health & Biosecurity": {
                "subcategories": [
                    "Vaccination Programs",
                    "Infectious Diseases",
                    "Gut Health / Enteric Disorders",
                    "Antimicrobial Use",
                    "Farm Biosecurity",
                    "Cleaning & Disinfection",
                    "Mortality Handling",
                    "Diagnostics & Sampling"
                ]
            },
            # ... autres catégories
        }
```

---

## 📊 Estimation de Performance

| Champ | Méthode | Taux Auto | Intervention Manuelle |
|-------|---------|-----------|---------------------|
| **visibility_level** | Path | 100% | 0% |
| **owner_org_id** | Path | 100% | 0% |
| **allowed_org_ids** | Path | 100% | 0% |
| **species** | Path | 95% | 5% (cas ambigus) |
| **production_stage** | Pattern + LLM | 80% | 20% |
| **site_type** | Path + LLM | 70% | 30% |
| **geo_scope** | Default + Pattern | 95% | 5% |
| **source_type** | Path + Pattern | 90% | 10% |
| **source_name** | Auto | 100% | 0% |
| **language** | Auto-detect | 100% | 0% |
| **category** | Path + LLM | 95% | 5% |
| **subcategory** | LLM | 85% | 15% |
| **topic** | Filename + LLM | 90% | 10% |
| **attributes** | LLM | 75% | 25% |
| **createdAt/updatedAt** | Auto | 100% | 0% |

**→ TOTAL : ~90% automatique** 🎉

**Intervention manuelle** : Seulement pour validation/correction, pas pour classification initiale !

---

## 🚀 Plan d'Implémentation

### Phase 1 : Core Classifier (1-2 jours)
1. Créer `hybrid_classifier.py`
2. Tester sur 20 documents variés
3. Ajuster prompts LLM

### Phase 2 : Intégration Knowledge Extractor (1 jour)
1. Modifier `document_analyzer.py`
2. Ajouter classification au pipeline
3. Tests end-to-end

### Phase 3 : Validation & Tuning (1 jour)
1. Classifier 100 documents
2. Mesurer précision
3. Créer interface validation manuelle (optionnelle)

**Total : 3-4 jours** pour système complet ! 🎯

---

## ✅ Avantages de cette Approche

1. **90% automatique** - Minimal effort manuel
2. **Scalable** - Nouveau document = classification instantanée
3. **Flexible** - Path rules + LLM intelligence
4. **Cost-effective** - LLM appelé seulement si nécessaire
5. **Maintenable** - Règles centralisées
6. **Multi-tenant ready** - Sécurité automatique
7. **Audit trail** - Traçabilité complète

Voulez-vous que je crée le fichier `hybrid_classifier.py` complet maintenant ?
