# Schéma Weaviate Enrichi - Taxonomie 4 Niveaux + Sécurité Multi-tenant

**Date**: 2025-10-29
**Version**: 2.0
**Objectif**: Enrichir le schéma Weaviate avec structure hiérarchique, sécurité multi-tenant et contexte métier

---

## 🏗️ Architecture Proposée

### Structure à 3 Dimensions

```
┌─────────────────────────────────────────────────┐
│  1. SÉCURITÉ / ACCÈS (Multi-tenant)            │
│  2. CONTEXTE MÉTIER (Aviculture)               │
│  3. TAXONOMIE 4 NIVEAUX (Classification)       │
└─────────────────────────────────────────────────┘
```

---

## 1️⃣ Dimension Sécurité / Accès

### Objectif
Permettre partage sélectif de connaissances entre organisations tout en préservant la confidentialité.

### Propriétés

```python
# Niveau de visibilité
visibility_level: "public" | "organization" | "private"

# Organisation propriétaire
owner_org_id: str  # UUID de l'organisation propriétaire

# Organisations avec accès (si partagé)
allowed_org_ids: List[str]  # Liste d'UUIDs organisations autorisées
```

### Cas d'usage

**Exemple 1 : Contenu Public**
```json
{
  "content": "Ross 308 performance objectives...",
  "visibility_level": "public",
  "owner_org_id": "aviagen_official",
  "allowed_org_ids": []
}
```
→ Accessible à tous les utilisateurs

**Exemple 2 : Contenu Privé Organisation**
```json
{
  "content": "Notre protocole vaccination interne...",
  "visibility_level": "organization",
  "owner_org_id": "ferme_beauce_inc",
  "allowed_org_ids": []
}
```
→ Accessible uniquement aux membres de `ferme_beauce_inc`

**Exemple 3 : Partage Sélectif**
```json
{
  "content": "Résultats essai nutrition collaboratif...",
  "visibility_level": "organization",
  "owner_org_id": "cooperative_quebec",
  "allowed_org_ids": ["ferme_a", "ferme_b", "ferme_c"]
}
```
→ Accessible à cooperative_quebec + 3 fermes partenaires

---

## 2️⃣ Dimension Contexte Métier

### Objectif
Enrichir chunks avec contexte avicole pour filtrage précis et pertinence.

### Propriétés Aviculture

```python
# Espèce cible
species: "broilers" | "layers" | "turkeys" | "breeders" | "ducks"

# Stade de production
production_stage: "hatchery" | "brooding" | "growing" | "finishing" | "laying" | "breeder"

# Type de site
site_type: "farm" | "hatchery" | "processing_plant" | "feed_mill" | "laboratory"

# Portée géographique
geo_scope: "global" | "north_america" | "europe" | "asia" | "country_specific" | "region_specific"

# Type de source
source_type: "technical_guide" | "performance_data" | "research_paper" | "field_report" | "regulation"

# Nom de la source
source_name: str  # Ex: "Ross 308 Broiler Performance Objectives 2023"

# Langue du contenu
language: "en" | "fr" | "es" | "pt" | "de" | ...

# Métadonnées temporelles
created_at: datetime
updated_at: datetime
```

### Exemples de Filtrage

**Query 1** : "Ross 308 brooding temperature"
```python
filters = {
    "species": "broilers",
    "production_stage": "brooding",
    "genetic_line": "ross_308"
}
```

**Query 2** : "Layer nutrition in Canada"
```python
filters = {
    "species": "layers",
    "category": "nutrition",
    "geo_scope": "north_america"
}
```

---

## 3️⃣ Taxonomie 4 Niveaux

### Architecture Hiérarchique

```
LEVEL 1: Category (Domaine principal)
    └─ LEVEL 2: Subcategory (Sous-domaine)
        └─ LEVEL 3: Topic (Sujet spécifique)
            └─ LEVEL 4: Attributes (Paramètres détaillés)
```

### Niveau 1 : Category (10-15 catégories)

```python
category: str  # Domaine principal

# Valeurs possibles :
[
    "health",              # Santé & maladies
    "nutrition",           # Nutrition & aliments
    "genetics",            # Génétique & sélection
    "environment",         # Environnement & logement
    "biosecurity",         # Biosécurité
    "welfare",             # Bien-être animal
    "performance",         # Performance & métriques
    "reproduction",        # Reproduction
    "processing",          # Transformation
    "regulation",          # Réglementations
    "economics",           # Économie & coûts
    "technology",          # Technologies & équipements
    "sustainability"       # Développement durable
]
```

### Niveau 2 : Subcategory (3-5 par category)

```python
subcategory: str  # Sous-domaine spécifique

# Exemples pour category="health" :
health_subcategories = [
    "infectious_diseases",      # Maladies infectieuses
    "metabolic_disorders",      # Troubles métaboliques
    "vaccination",              # Vaccination
    "diagnostics",              # Diagnostics
    "treatment"                 # Traitements
]

# Exemples pour category="nutrition" :
nutrition_subcategories = [
    "feed_formulation",         # Formulation aliment
    "ingredients",              # Ingrédients
    "supplements",              # Suppléments
    "water_quality",            # Qualité eau
    "feeding_program"           # Programme alimentation
]

# Exemples pour category="environment" :
environment_subcategories = [
    "ventilation",              # Ventilation
    "temperature_control",      # Contrôle température
    "lighting",                 # Éclairage
    "litter_management",        # Gestion litière
    "air_quality"               # Qualité air
]
```

### Niveau 3 : Topic (Sujet précis)

```python
topic: str  # Sujet spécifique dans subcategory

# Exemples pour subcategory="infectious_diseases" :
infectious_disease_topics = [
    "newcastle_disease",
    "avian_influenza",
    "infectious_bronchitis",
    "gumboro_disease",
    "coccidiosis",
    "salmonella",
    "e_coli",
    "mycoplasma"
]

# Exemples pour subcategory="metabolic_disorders" :
metabolic_disorder_topics = [
    "ascites",
    "sudden_death_syndrome",
    "leg_problems",
    "fatty_liver_syndrome",
    "heat_stress"
]
```

### Niveau 4 : Attributes (Objet JSON - Paramètres)

```python
attributes: Dict[str, Any]  # Paramètres spécifiques au topic

# Exemple pour topic="ascites" :
{
    "severity": "high",                    # Impact severity
    "age_range": "21-35 days",            # Affected age
    "mortality_rate": "1-3%",             # Mortality impact
    "prevention_methods": [                # Prevention strategies
        "temperature_control",
        "ventilation",
        "feed_management"
    ],
    "risk_factors": [                      # Contributing factors
        "fast_growth",
        "poor_ventilation",
        "high_altitude"
    ],
    "seasonal": "winter"                   # Seasonal occurrence
}

# Exemple pour topic="newcastle_disease" :
{
    "pathogen": "Newcastle disease virus (NDV)",
    "transmission": "airborne",
    "vaccination_required": true,
    "vaccination_schedule": ["day 1", "day 14", "day 28"],
    "mortality_rate": "up to 100%",
    "reportable": true,                    # Notifiable disease
    "quarantine_required": true
}

# Exemple pour topic="feed_formulation" :
{
    "life_stage": "starter",               # 0-10 days
    "protein_percent": "23-24%",
    "energy_kcal_kg": "3000-3100",
    "calcium_percent": "1.0-1.1%",
    "phosphorus_percent": "0.45-0.50%",
    "form": "crumble"
}
```

---

## 📊 Schéma Weaviate Complet

### Collection: `InteliaExpertKnowledge_v2`

```python
from weaviate.classes.config import Configure, Property, DataType

schema = {
    "class": "InteliaExpertKnowledge_v2",
    "description": "Enhanced knowledge base with security, business context, and 4-level taxonomy",

    "properties": [
        # ═══════════════════════════════════════════════
        # CORE CONTENT (Vectorized)
        # ═══════════════════════════════════════════════
        Property(
            name="content",
            data_type=DataType.TEXT,
            description="Main chunk content (vectorized)"
        ),

        # ═══════════════════════════════════════════════
        # 1. SECURITY / ACCESS
        # ═══════════════════════════════════════════════
        Property(
            name="visibility_level",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="public | organization | private"
        ),
        Property(
            name="owner_org_id",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Owner organization UUID"
        ),
        Property(
            name="allowed_org_ids",
            data_type=DataType.TEXT_ARRAY,
            skip_vectorization=True,
            description="List of allowed organization UUIDs"
        ),

        # ═══════════════════════════════════════════════
        # 2. BUSINESS CONTEXT
        # ═══════════════════════════════════════════════
        Property(
            name="species",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="broilers | layers | turkeys | breeders | ducks"
        ),
        Property(
            name="production_stage",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="hatchery | brooding | growing | finishing | laying | breeder"
        ),
        Property(
            name="site_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="farm | hatchery | processing_plant | feed_mill | laboratory"
        ),
        Property(
            name="geo_scope",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="global | north_america | europe | asia | country_specific"
        ),
        Property(
            name="source_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="technical_guide | performance_data | research_paper | field_report | regulation"
        ),
        Property(
            name="source_name",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Name of source document"
        ),
        Property(
            name="language",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Content language code (en, fr, es, etc.)"
        ),
        Property(
            name="created_at",
            data_type=DataType.DATE,
            skip_vectorization=True,
            description="Creation timestamp"
        ),
        Property(
            name="updated_at",
            data_type=DataType.DATE,
            skip_vectorization=True,
            description="Last update timestamp"
        ),

        # ═══════════════════════════════════════════════
        # 3. TAXONOMY - 4 LEVELS
        # ═══════════════════════════════════════════════

        # LEVEL 1: Category
        Property(
            name="category",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Main domain: health | nutrition | genetics | environment | ..."
        ),

        # LEVEL 2: Subcategory
        Property(
            name="subcategory",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Sub-domain within category"
        ),

        # LEVEL 3: Topic
        Property(
            name="topic",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Specific topic within subcategory"
        ),

        # LEVEL 4: Attributes (JSON object)
        Property(
            name="attributes",
            data_type=DataType.OBJECT,
            skip_vectorization=True,
            description="Topic-specific parameters as JSON object"
        ),

        # ═══════════════════════════════════════════════
        # LEGACY METADATA (Backward compatibility)
        # ═══════════════════════════════════════════════
        Property(
            name="genetic_line",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="ross_308 | cobb_500 | hubbard | etc."
        ),
        Property(
            name="document_type",
            data_type=DataType.TEXT,
            skip_vectorization=True,
            description="Legacy: management_guide | performance_table | etc."
        ),
    ],

    # Vectorizer configuration
    "vectorizer_config": Configure.Vectorizer.text2vec_openai(
        model="text-embedding-3-large",
        dimensions=1536
    )
}
```

---

## 🔍 Exemples de Requêtes avec Taxonomie

### Exemple 1 : Recherche Santé - Ascites

```python
# Query: "How to prevent ascites in broilers?"

# Filtres taxonomie
filters = {
    "category": "health",
    "subcategory": "metabolic_disorders",
    "topic": "ascites",
    "species": "broilers"
}

# Recherche Weaviate
response = client.query.get("InteliaExpertKnowledge_v2", ["content", "attributes"]) \
    .with_where({
        "operator": "And",
        "operands": [
            {"path": ["category"], "operator": "Equal", "valueText": "health"},
            {"path": ["subcategory"], "operator": "Equal", "valueText": "metabolic_disorders"},
            {"path": ["topic"], "operator": "Equal", "valueText": "ascites"},
            {"path": ["species"], "operator": "Equal", "valueText": "broilers"}
        ]
    }) \
    .with_near_text({"concepts": ["prevent ascites broilers"]}) \
    .with_limit(10) \
    .do()

# Résultat enrichi avec attributes
for item in response["data"]["Get"]["InteliaExpertKnowledge_v2"]:
    print(f"Content: {item['content']}")
    print(f"Prevention methods: {item['attributes']['prevention_methods']}")
    print(f"Risk factors: {item['attributes']['risk_factors']}")
```

### Exemple 2 : Nutrition - Feed Formulation

```python
# Query: "Ross 308 starter feed composition"

filters = {
    "category": "nutrition",
    "subcategory": "feed_formulation",
    "genetic_line": "ross_308",
    "attributes.life_stage": "starter"
}

# Chunks retournés incluront:
# - Protein percent: 23-24%
# - Energy: 3000-3100 kcal/kg
# - Form: crumble
```

### Exemple 3 : Multi-tenant avec Partage

```python
# Organisation "ferme_a" veut accéder au contenu

user_org_id = "ferme_a"

# Filtres sécurité
security_filter = {
    "operator": "Or",
    "operands": [
        # Contenu public
        {"path": ["visibility_level"], "operator": "Equal", "valueText": "public"},
        # Contenu possédé par l'organisation
        {"path": ["owner_org_id"], "operator": "Equal", "valueText": user_org_id},
        # Contenu partagé avec l'organisation
        {"path": ["allowed_org_ids"], "operator": "ContainsAny", "valueText": [user_org_id]}
    ]
}

response = client.query.get("InteliaExpertKnowledge_v2", ["content"]) \
    .with_where(security_filter) \
    .with_near_text({"concepts": ["vaccination protocol"]}) \
    .do()
```

---

## 📋 Plan de Migration

### Phase 1 : Enrichir Knowledge Extractor

**Fichier** : `knowledge-ingesters/knowledge_extractor/core/document_analyzer.py`

Ajouter classification automatique:
```python
def classify_document(self, content: str, metadata: dict) -> dict:
    """Classify document using LLM into taxonomy"""

    prompt = f"""
    Analyze this poultry document and classify it:

    Content: {content[:1000]}...

    Return JSON:
    {{
        "category": "health|nutrition|environment|...",
        "subcategory": "...",
        "topic": "...",
        "attributes": {{...}},
        "species": "broilers|layers|...",
        "production_stage": "...",
        "geo_scope": "...",
        "source_type": "..."
    }}
    """

    # Call LLM (Claude/GPT)
    classification = llm_client.classify(prompt)
    return classification
```

### Phase 2 : Mise à jour Schéma Weaviate

1. Créer nouvelle collection `InteliaExpertKnowledge_v2`
2. Migrer données existantes avec classification
3. Basculer RAG vers v2
4. Supprimer v1 après validation

### Phase 3 : Adapter RAG

**Fichier** : `rag/retrieval/weaviate/core.py`

Ajouter filtrage taxonomie:
```python
def build_taxonomy_filter(self, intent_result, user_org_id):
    """Build Weaviate filter from intent + taxonomy"""

    filters = {
        "operator": "And",
        "operands": []
    }

    # Security filter (multi-tenant)
    filters["operands"].append(self._build_security_filter(user_org_id))

    # Taxonomy filter
    if intent_result.category:
        filters["operands"].append({
            "path": ["category"],
            "operator": "Equal",
            "valueText": intent_result.category
        })

    # Business context
    if intent_result.species:
        filters["operands"].append({
            "path": ["species"],
            "operator": "Equal",
            "valueText": intent_result.species
        })

    return filters
```

---

## 🎯 Bénéfices Attendus

### Performance RAG
- **Context Precision** : +20-30% (filtrage taxonomie élimine bruit)
- **Context Recall** : +10-15% (classification précise trouve meilleur contenu)
- **Latence** : -30-40% (moins de chunks à scanner grâce aux filtres)

### Multi-tenant
- Isolation sécurisée des données clients
- Partage sélectif entre organisations
- Conformité GDPR/réglementaire

### Expérience Utilisateur
- Résultats plus pertinents (filtrage fin)
- Support de recherche avancée (browse by taxonomy)
- Recommandations intelligentes (related topics)

---

## 📚 Références

- [Weaviate Multi-Tenancy](https://weaviate.io/developers/weaviate/manage-data/multi-tenancy)
- [Weaviate Filtering](https://weaviate.io/developers/weaviate/search/filters)
- [Taxonomy Best Practices](https://schema.org/docs/about.html)

---

**Status** : ⏳ Proposition - En attente validation
**Next Steps** :
1. Valider structure taxonomie avec équipe métier
2. Créer script classification LLM
3. Migrer collection test
4. A/B test taxonomie vs baseline
