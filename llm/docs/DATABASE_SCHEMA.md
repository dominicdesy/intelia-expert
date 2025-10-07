# Documentation Complète - Structure des Bases de Données

**Version**: 2.0
**Dernière mise à jour**: 2025-01-15
**Statut**: ✅ Synchronisé RAG + LLM

---

## Vue d'ensemble

Le système utilise **deux bases de données complémentaires**:

1. **Weaviate** (Vector DB): Documents textuels avec recherche sémantique + métadonnées structurées
2. **PostgreSQL**: Métriques de performance chiffrées (poids, FCR, consommation, etc.)

---

## 1. Weaviate - Collection `InteliaExpertKnowledge`

### Schéma complet (25 propriétés)

#### Propriétés de contenu
| Propriété | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `content` | TEXT | Contenu textuel du chunk | "At 21 days, the target weight is..." |
| `chunk_id` | TEXT | Identifiant unique du chunk | "abc123-chunk-5" |
| `source_file` | TEXT | Nom du fichier PDF source | "Ross-308-Broiler-Guide.pdf" |
| `page_number` | INT | Numéro de page dans le PDF | 42 |

#### Métadonnées taxonomiques (**NOUVELLES v2.0**)
| Propriété | Type | Description | Valeurs possibles | Utilisation LLM |
|-----------|------|-------------|-------------------|-----------------|
| **`breed`** | TEXT | Race/lignée génétique | `"ross 308"`, `"cobb 500"`, `"hyline brown"` | **✅ FILTRAGE** par breed |
| **`company`** | TEXT | Compagnie productrice | `"Aviagen"`, `"Cobb-Vantress"`, `"Hy-Line"` | **✅ FILTRAGE** par compagnie |
| **`sex`** | TEXT | Sexe des animaux | `"male"`, `"female"`, `"as_hatched"`, `"mixed"` | **✅ FILTRAGE** par sexe |
| `species` | TEXT | Espèce | `"broiler"`, `"layer"`, `"breeder"` | **✅ FILTRAGE** par espèce |

#### Métadonnées temporelles (**NOUVELLES v2.0**)
| Propriété | Type | Description | Exemple | Utilisation LLM |
|-----------|------|-------------|---------|-----------------|
| **`age_min_days`** | INT | Âge minimum (jours) | 0, 14, 21 | **✅ FILTRAGE** par plage d'âge |
| **`age_max_days`** | INT | Âge maximum (jours) | 7, 35, 56 | **✅ FILTRAGE** par plage d'âge |
| `age_band` | TEXT | Bande d'âge (legacy) | `"0-7j"`, `"8-21j"`, `"22-35j"`, `"36j+"` | ⚠️ **DEPRECATED** - utiliser age_min/max |

#### Métadonnées techniques (**NOUVELLES v2.0**)
| Propriété | Type | Description | Valeurs possibles | Utilisation LLM |
|-----------|------|-------------|-------------------|-----------------|
| **`unit_system`** | TEXT | Système d'unités | `"metric"`, `"imperial"`, `"unknown"` | **✅ FILTRAGE** + conversion |
| `data_type` | TEXT | Type de données | `"management_guide"`, `"performance_guide"`, `"nutrition_manual"`, `"health_protocol"` | **✅ FILTRAGE** par type de doc |

#### Propriétés legacy (compatibilité)
| Propriété | Type | Description | Statut |
|-----------|------|-------------|--------|
| `geneticLine` | TEXT | Ligne génétique (ancien format) | ⚠️ Remplacé par `breed` |
| `phase` | TEXT | Phase d'élevage | ⚠️ Remplacé par `age_min_days`/`age_max_days` |
| `housing_system` | TEXT | Système de logement | `"floor"`, `"cage"`, `"free_range"` |
| `feather_color` | TEXT | Couleur des plumes | `"brown"`, `"white"` |

#### Métadonnées techniques
| Propriété | Type | Description |
|-----------|------|-------------|
| `context` | TEXT | Contexte élargi (3 paragraphes avant/après) |
| `metadata` | TEXT | Métadonnées additionnelles JSON |
| `chunk_index` | INT | Index du chunk dans le document |
| `total_chunks` | INT | Nombre total de chunks du document |
| `extraction_date` | DATE | Date d'extraction |

---

### Mapping Entités LLM → Champs Weaviate

| Entité extraite | Champ Weaviate | Type de filtrage | Priorité |
|----------------|----------------|------------------|----------|
| `breed` (ex: "ross 308") | `breed` | Equal (exact match) | 🔴 **HAUTE** |
| `company` (ex: "Aviagen") | `company` | Like (partial match) | 🟡 **MOYENNE** |
| `sex` (ex: "male") | `sex` | Equal | 🔴 **HAUTE** |
| `age_days` (ex: 21) | `age_min_days` + `age_max_days` | Range (BETWEEN) | 🔴 **HAUTE** |
| `species` (ex: "broiler") | `species` | Like | 🟡 **MOYENNE** |
| `unit_system` (ex: "metric") | `unit_system` | Equal | 🟢 **BASSE** |
| `data_type` (ex: "nutrition") | `data_type` | Like | 🟢 **BASSE** |

**Exemple de requête filtrée**:
```python
# User query: "What is the target weight for Ross 308 males at 21 days?"
where_filter = {
    "operator": "And",
    "operands": [
        {"path": ["breed"], "operator": "Equal", "valueText": "ross 308"},
        {"path": ["sex"], "operator": "Equal", "valueText": "male"},
        {"path": ["age_min_days"], "operator": "LessThanEqual", "valueInt": 21},
        {"path": ["age_max_days"], "operator": "GreaterThanEqual", "valueInt": 21},
    ]
}
```

---

## 2. PostgreSQL - Base de Données Structurée

### Architecture des tables

```
companies
    ↓ (1:N)
breeds
    ↓ (1:N)
strains
    ↓ (1:N)
documents ←→ data_categories
    ↓ (1:N)
metrics
```

### Table `companies`
| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `id` | SERIAL | Identifiant unique | 1 |
| `company_name` | VARCHAR(100) | Nom de la compagnie | "Aviagen" |
| `description` | TEXT | Description | "Leading genetics company" |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 |

### Table `breeds`
| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `id` | SERIAL | Identifiant unique | 1 |
| `company_id` | INT | Référence compagnie | 1 |
| `breed_name` | VARCHAR(100) | Nom de la race | "Ross" |
| `description` | TEXT | Description | "Fast-growing broiler" |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 |

### Table `strains`
| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `id` | SERIAL | Identifiant unique | 1 |
| `breed_id` | INT | Référence breed | 1 |
| `strain_name` | VARCHAR(100) | Nom de la lignée | "308/308 FF" |
| `species` | VARCHAR(50) | Espèce | "broiler" |
| `description` | TEXT | Description | "Ross 308 Fast Feather" |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 |

### Table `documents` (**MISE À JOUR v2.0**)
| Colonne | Type | Description | Exemple | **Nouveau v2.0** |
|---------|------|-------------|---------|------------------|
| `id` | SERIAL | Identifiant unique | 1 | |
| `filename` | VARCHAR(255) | Nom du fichier | "Cobb500-2022.xlsx#male_metric" | |
| `strain_id` | INT | Référence strain | 1 | |
| `housing_system` | VARCHAR(200) | Système de logement | "floor" | |
| `feather_color` | VARCHAR(50) | Couleur plumes | "white" | |
| **`sex`** | **VARCHAR(10)** | **Sexe** | **"male"** | **✅ OUI** |
| **`data_type`** | **VARCHAR(50)** | **Type de données** | **"performance"** | **✅ OUI** |
| **`unit_system`** | **VARCHAR(10)** | **Système d'unités** | **"metric"** | **✅ OUI** |
| `file_hash` | VARCHAR(64) | Hash MD5 du fichier | "abc123..." | |
| `metadata` | JSONB | Métadonnées JSON | `{"year": 2022}` | |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 | |

### Table `data_categories`
| Colonne | Type | Description | Valeurs |
|---------|------|-------------|---------|
| `id` | SERIAL | Identifiant unique | 1 |
| `category_name` | VARCHAR(100) | Nom de la catégorie | "performance", "nutrition", "health", etc. |
| `description` | TEXT | Description | "Performance and production metrics" |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 |

**Catégories prédéfinies**:
1. `performance` - Métriques de performance
2. `nutrition` - Données nutritionnelles
3. `pharmaceutical` - Données vétérinaires
4. `carcass` - Rendement carcasse
5. `environment` - Conditions environnementales
6. `health` - Santé et mortalité
7. `economics` - Données économiques
8. `other` - Autres données

### Table `metrics` (**MISE À JOUR v2.0**)
| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `id` | SERIAL | Identifiant unique | 1 |
| `document_id` | INT | Référence document | 1 |
| `category_id` | INT | Référence catégorie | 1 (performance) |
| `sheet_name` | VARCHAR(100) | Nom de la feuille Excel | "male_metric" |
| `metric_key` | VARCHAR(200) | Clé de la métrique | "weight_g" |
| `metric_name` | VARCHAR(200) | Nom de la métrique | "Body Weight (g)" |
| `value_text` | TEXT | Valeur textuelle | "2500" |
| `value_numeric` | DECIMAL(15,6) | Valeur numérique | 2500.0 |
| `unit` | VARCHAR(50) | Unité de mesure | "grams" |
| **`age_min`** | **INT** | **Âge minimum (jours)** | **21** |
| **`age_max`** | **INT** | **Âge maximum (jours)** | **21** |
| `metadata` | JSONB | Métadonnées additionnelles | `{}` |
| `created_at` | TIMESTAMP | Date de création | 2025-01-15 10:00:00 |

---

### Mapping Entités LLM → Requêtes PostgreSQL

| Entité extraite | Tables concernées | Champs filtrés | Type de requête |
|----------------|-------------------|----------------|-----------------|
| `breed` (ex: "ross 308") | `companies` + `breeds` + `strains` | `strain_name LIKE '%308%'` | JOIN avec mapping intents.json |
| `company` (ex: "Aviagen") | `companies` | `company_name LIKE '%Aviagen%'` | JOIN direct |
| `sex` (ex: "male") | `documents` | `sex = 'male'` | WHERE direct |
| `age_days` (ex: 21) | `metrics` | `age_min <= 21 AND age_max >= 21` | WHERE avec range |
| `metric` (ex: "weight") | `metrics` | `metric_name LIKE '%weight%'` | WHERE avec LIKE |
| `unit_system` (ex: "metric") | `documents` | `unit_system = 'metric'` | WHERE direct |

**Exemple de requête SQL**:
```sql
-- User query: "What is the target weight for Ross 308 males at 21 days?"
SELECT
    m.metric_name,
    m.value_numeric,
    m.unit,
    m.age_min,
    m.age_max,
    d.sex,
    s.strain_name
FROM metrics m
JOIN documents d ON m.document_id = d.id
JOIN strains s ON d.strain_id = s.id
JOIN breeds b ON s.breed_id = b.id
JOIN companies c ON b.company_id = c.id
WHERE
    s.strain_name LIKE '%308%'  -- breed mapping
    AND d.sex = 'male'
    AND m.age_min <= 21
    AND m.age_max >= 21
    AND m.metric_name LIKE '%weight%'
ORDER BY m.value_numeric DESC
LIMIT 10;
```

---

## 3. Index et Optimisations

### Weaviate - Index vectoriel
- **Dimension**: 1536 (text-embedding-3-small)
- **Méthode**: HNSW (Hierarchical Navigable Small World)
- **Distance**: Cosine similarity
- **Index propriétés**: sex, breed, company, age_min_days, age_max_days, unit_system

### PostgreSQL - Index B-tree
```sql
-- Index existants
CREATE INDEX idx_metrics_document_sheet ON metrics(document_id, sheet_name);
CREATE INDEX idx_metrics_category ON metrics(category_id);
CREATE INDEX idx_metrics_age ON metrics(age_min, age_max);
CREATE INDEX idx_metrics_key ON metrics(metric_key);
CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_unit ON metrics(unit);
CREATE INDEX idx_documents_data_type ON documents(data_type);
CREATE INDEX idx_documents_unit_system ON documents(unit_system);
CREATE INDEX idx_documents_metadata_gin ON documents USING GIN (metadata);
```

---

## 4. État Actuel des Données

### Weaviate
- **Total objets**: 1932 chunks
- **PDFs traités**: 50
- **En attente**: 6 PDFs (quota Vectorize Iris)

### PostgreSQL
- **Documents**: 15
- **Métriques**: 3090
- **Companies**: 2 (Cobb-Vantress, Aviagen)
- **Breeds**: 2 (Cobb, Ross)
- **Strains**: 2 (500, 308/308 FF)

---

## 5. Guide d'utilisation pour le LLM

### Stratégie de recherche recommandée

1. **Requête textuelle/sémantique** → **Weaviate**
   - Questions ouvertes
   - Recherche de contexte
   - Comparaisons qualitatives

2. **Requête numérique/métrique** → **PostgreSQL**
   - Valeurs précises (poids, FCR, etc.)
   - Calculs sur plages d'âges
   - Agrégations statistiques

3. **Requête hybride** → **Weaviate + PostgreSQL**
   - Contexte textuel + métriques
   - Enrichissement mutuel

### Champs prioritaires pour le filtrage

**HAUTE PRIORITÉ** (toujours filtrer si disponible):
- `breed` / `strain_name`
- `sex`
- `age_min_days` / `age_max_days` (ou `age_min` / `age_max`)

**MOYENNE PRIORITÉ** (filtrer si pertinent):
- `company`
- `species`
- `data_type`

**BASSE PRIORITÉ** (optionnel):
- `unit_system` (mais critique pour conversion)
- `housing_system`
- `feather_color`

---

## 6. Changelog

### Version 2.0 (2025-01-15)
- ✅ Ajout propriétés Weaviate: sex, age_min_days, age_max_days, breed, company, unit_system
- ✅ Ajout colonnes PostgreSQL: sex, data_type, unit_system, age_min, age_max
- ✅ Suppression dépendance aux bandes d'âge (age_band deprecated)
- ✅ Support multi-breed comparisons
- ✅ Intégration intents.json v1.5

### Version 1.0 (2025-01-10)
- Version initiale avec schéma de base
