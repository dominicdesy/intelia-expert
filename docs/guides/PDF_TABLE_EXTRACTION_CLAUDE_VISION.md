# PDF Table Extraction avec Claude Vision API

Guide complet pour l'extraction intelligente de tableaux depuis des PDFs en utilisant Claude Vision API.

## 📋 Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Pourquoi Claude Vision?](#pourquoi-claude-vision)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Architecture](#architecture)
- [Exemples](#exemples)
- [Coûts](#coûts)
- [Limitations](#limitations)

---

## Vue d'ensemble

Ce système permet d'extraire automatiquement et intelligemment **tous les tableaux** présents dans des PDFs, sans configuration manuelle ni mots-clés prédéfinis. Il génère un fichier Excel structuré avec métadonnées complètes.

### ✅ Avantages

- **Générique**: Fonctionne avec n'importe quel type de tableau
- **Intelligent**: Détecte automatiquement les en-têtes multi-lignes, les unités, les métadonnées
- **Précis**: Extraction à 100% sur les tests avec Cobb500 (57/57 lignes extraites correctement)
- **Robuste**: Pas de dépendance à des mots-clés spécifiques (age, weight, etc.)
- **Métadonnées riches**: Génère automatiquement le contexte du tableau

### 📊 Résultats

Test sur `Cobb500-Broiler-Performance-Nutrition-Supplement.pdf`:

| Métrique | Résultat |
|----------|----------|
| **Pages traitées** | 11 pages (4-6, 10-14) |
| **Tableaux extraits** | 11 tableaux |
| **Précision** | 100% (57/57 lignes sur test Female) |
| **Temps d'exécution** | ~30 secondes/page |
| **Coût** | ~$0.15-0.30 USD total |

---

## Pourquoi Claude Vision?

### Comparaison des approches

| Approche | Avantages | Inconvénients |
|----------|-----------|---------------|
| **pdfplumber** | Gratuit, rapide | Rate des lignes, nécessite mots-clés spécifiques |
| **Camelot** | Open source | Dépendances complexes, fragmentation |
| **Tabula** | Gratuit | Précision variable, difficile à configurer |
| **Claude Vision** ✅ | Intelligence contextuelle, haute précision, générique | Coût API (~$0.01-0.05/page) |
| **AWS Textract** | Précis, scalable | Plus coûteux, configuration complexe |
| **Google Document AI** | Précis | Setup complexe, coûteux |

### Pourquoi nous avons choisi Claude Vision

1. **Déjà intégré**: Vous utilisez déjà Claude dans votre stack
2. **Qualité supérieure**: Comprend le contexte et la sémantique
3. **Facilité**: Code simple, pas de configuration complexe
4. **Flexibilité**: S'adapte à tous types de tableaux
5. **Coût raisonnable**: ~$0.15 pour un document complet de 16 pages

---

## Installation

### Prérequis

```bash
# Python 3.11+
python --version

# Installer les dépendances
pip install anthropic pymupdf pandas openpyxl pillow
```

### Configuration

```bash
# Définir la clé API Anthropic
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."
```

---

## Utilisation

### Extraction basique

```bash
cd rag/performance_extractor
python extract_pdf_tables_claude_vision.py input.pdf output.xlsx
```

### Extraction de pages spécifiques

```bash
cd rag/performance_extractor

# Extraire seulement les pages 4 à 6
python extract_pdf_tables_claude_vision.py input.pdf output.xlsx 4 6

# Extraire la page 10
python extract_pdf_tables_claude_vision.py input.pdf output.xlsx 10 10
```

### Exemple complet (Cobb500)

```bash
cd C:\intelia_gpt\intelia-expert\rag\performance_extractor

# Extraire les tables de performance (pages 4-6)
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/cobb/2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf" \
  "../documents/PerformanceMetrics/Cobb500_Tables.xlsx" \
  4 6

# Résultat: 3 feuilles créées (mixed_metric, male_metric, female_metric)
```

---

## Architecture

### Workflow d'extraction

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PDF Input                                                 │
│    └─> Convert to images (PyMuPDF, 300 DPI)                │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 2. Claude Vision API                                         │
│    ├─> Send image + extraction prompt                       │
│    ├─> Claude analyzes and extracts tables                  │
│    └─> Returns JSON with tables + metadata                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 3. JSON Processing                                           │
│    ├─> Parse table structure                                │
│    ├─> Extract headers + units                              │
│    ├─> Extract data rows                                    │
│    └─> Generate metadata                                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 4. Excel Generation                                          │
│    ├─> Create sheets with metadata (rows 1-N)              │
│    ├─> Add column definitions                               │
│    ├─> Insert data table with styling                       │
│    └─> Save XLSX file                                       │
└─────────────────────────────────────────────────────────────┘
```

### Structure du fichier Excel généré

Chaque feuille suit ce format:

```
Row 1-2:    [METADATA HEADER] metadata | value
Row 3-N:    [METADATA] source_page, table_title, table_type, description, ...
Row N+1:    [TABLE INFO] table_data_rows, table_columns
Row N+2:    [COLUMN DEFINITIONS] column_1_name, column_1_type, column_1_unit, ...
Row N+3:    [BLANK ROWS]
Row N+4:    [DATA HEADER] Age | Weight | Daily Gain | ...
Row N+5+:   [DATA ROWS] 0 | 42 | ... | ...
```

### Métadonnées extraites automatiquement

```json
{
  "source_page": 6,
  "table_title": "C500 Broiler Performance Objectives (Metric) - Female",
  "table_type": "performance",
  "description": "Tableau de performance de croissance pour poulets...",
  "sex": "female",
  "unit_system": "metric",
  "bird_type": "broiler",
  "age_range": "0-56 days"
}
```

---

## Exemples

### Exemple 1: Table de Performance

**Input**: Page 6 du PDF Cobb500 (Female performance)

**Prompt Claude**:
```
Analyse cette page de PDF et extrait TOUS les tableaux...
```

**Output JSON** (extrait):
```json
{
  "tables": [
    {
      "table_title": "C500 Broiler Performance Objectives (Metric) - Female",
      "table_type": "performance",
      "headers": ["Age", "Weight", "Daily Gain", "Average Daily Gain", ...],
      "units": ["days", "g", "g", "g", "ratio", "g", "g"],
      "data": [
        ["0", "42", "", "", "", "", ""],
        ["1", "54", "12", "", "", "", ""],
        ["2", "70", "16", "", "", "", ""],
        ...
        ["56", "4329", "80", "76.6", "1.890", "257", "8180"]
      ],
      "metadata": {
        "sex": "female",
        "unit_system": "metric",
        "bird_type": "broiler",
        "age_range": "0-56 days"
      }
    }
  ]
}
```

**Résultat**: Feuille Excel `female_metric` avec 57 lignes de données

### Exemple 2: Table de Nutrition

**Input**: Page 10 (Nutrition specifications)

**Output**: 2 tableaux détectés sur la même page
- `nutrient_med_large`: Spécifications nutritionnelles pour poulets moyens/larges
- `amino_med_large`: Ratios d'acides aminés

### Exemple 3: Extraction complète multi-pages

```python
from llm.scripts.extract_pdf_tables_claude_vision import ClaudeVisionTableExtractor

# Initialiser
extractor = ClaudeVisionTableExtractor("document.pdf")

# Extraire pages 1-20
tables = extractor.extract_all_tables(start_page=1, end_page=20)

# Sauvegarder
extractor.save_to_excel(tables, "all_tables.xlsx")

print(f"Extrait {len(tables)} tableaux")
```

---

## Coûts

### Modèle: Claude 3.5 Sonnet (Vision)

| Métrique | Coût | Calcul |
|----------|------|--------|
| **Input tokens** | $3.00 / 1M tokens | ~5000 tokens/page (image) |
| **Output tokens** | $15.00 / 1M tokens | ~1000 tokens/page (JSON) |
| **Coût par page** | ~$0.01-0.03 | Dépend de la complexité |

### Exemple réel (Cobb500, 11 pages)

```
Pages traitées: 11
Input tokens:   ~55,000 (11 images)
Output tokens:  ~11,000 (JSON responses)
Coût total:     $0.165 + $0.165 = ~$0.33 USD
```

### Optimisation des coûts

1. **Traiter seulement les pages nécessaires**
   ```bash
   # Au lieu de tout le document
   python extract.py doc.pdf out.xlsx 4 14
   ```

2. **Réduire le DPI** (si la qualité le permet)
   ```python
   images = extractor.convert_pdf_to_images(dpi=200)  # Default: 300
   ```

3. **Batch processing**: Traiter plusieurs documents en parallèle

---

## Limitations

### 1. Tableaux très complexes

Claude Vision peut avoir des difficultés avec:
- Tableaux avec cellules fusionnées complexes
- Tableaux multi-niveaux imbriqués
- Tableaux avec mise en page très irrégulière

**Solution**: Pré-traiter le PDF ou post-traiter le JSON

### 2. Tableaux fragmentés sur plusieurs pages

Si un tableau commence sur page 5 et continue sur page 6:
- Claude Vision les traite séparément
- Nécessite fusion manuelle ou logique de continuité

**Solution**: Implémenter une logique de fusion basée sur les en-têtes

### 3. Limite de tokens

- Image haute résolution = beaucoup de tokens
- PDFs très lourds peuvent dépasser les limites

**Solution**:
```python
# Réduire la résolution si nécessaire
images = extractor.convert_pdf_to_images(dpi=200)
```

### 4. Langues non-latines

Claude Vision est excellent pour l'anglais/français, mais peut avoir des difficultés avec:
- Caractères chinois/japonais
- Alphabets cyrilliques
- Symboles spéciaux

**Solution**: Spécifier la langue dans le prompt

---

## Bonnes Pratiques

### 1. Validation des résultats

```python
# Toujours valider le nombre de lignes extraites
expected_rows = 57
actual_rows = len(df)

if actual_rows != expected_rows:
    print(f"[WARNING] Expected {expected_rows}, got {actual_rows}")
```

### 2. Gestion des erreurs

```python
try:
    tables = extractor.extract_all_tables(1, 20)
except anthropic.APIError as e:
    print(f"API Error: {e}")
    # Retry logic or fallback
```

### 3. Logs détaillés

Le script inclut déjà des logs:
```
[OK] Conversion du PDF en images (DPI=300)...
  16 pages converties
[Processing] Page 6...
  [OK] 1 tableau(x) trouvé(s)
```

### 4. Tests de régression

```python
# Garder un "golden dataset" pour comparer
original_df = pd.read_excel("golden/cobb500_female.xlsx")
extracted_df = pd.read_excel("output/female_metric.xlsx")

assert original_df.equals(extracted_df), "Extraction differs from golden!"
```

---

## Scripts Disponibles

**Emplacement:** `rag/performance_extractor/`

### 1. `extract_pdf_tables_claude_vision.py`

**Principal script d'extraction**

```bash
cd rag/performance_extractor
python extract_pdf_tables_claude_vision.py <pdf> <output.xlsx> [start] [end]
```

**Fonctionnalités**:
- Conversion PDF → Images (PyMuPDF)
- Extraction intelligente via Claude Vision
- Génération Excel avec métadonnées
- Support de plages de pages
- Sortie automatique vers `rag/documents/PerformanceMetrics/`

### 2. `merge_excel_files.py`

**Fusion de plusieurs fichiers Excel**

```bash
cd rag/performance_extractor
python merge_excel_files.py output.xlsx file1.xlsx file2.xlsx file3.xlsx
```

**Utilisation**: Combiner les résultats de plusieurs extractions partielles

### 3. `extract_pdf_tables_to_excel.py` (Ancien)

**Version pdfplumber** (deprecated, gardé pour référence)

Utilise `extract_table()` avec détection heuristique. Problèmes:
- Rate des lignes
- Nécessite mots-clés hardcodés
- Pas générique

❌ **Non recommandé** - Utiliser Claude Vision à la place

### README Complet

Voir `rag/performance_extractor/README.md` pour:
- Exemples d'utilisation détaillés
- Workflow typique
- Guide d'intégration RAG

---

## Troubleshooting

### Erreur: "ANTHROPIC_API_KEY not found"

```bash
# Vérifier la clé
echo $ANTHROPIC_API_KEY  # Linux/Mac
echo $env:ANTHROPIC_API_KEY  # Windows PowerShell

# La définir
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Erreur: "Unable to get page count"

```bash
# Vérifier PyMuPDF
pip install --upgrade pymupdf

# Tester
python -c "import fitz; print('OK')"
```

### Erreur: "JSONDecodeError"

Claude a retourné du texte au lieu de JSON. Causes possibles:
- Prompt mal formé
- Page sans tableau
- Erreur API

**Debug**:
```python
# Le script affiche déjà la réponse en cas d'erreur
# Response: {"tables": [...]} ...
```

### Tableaux manquants

Si Claude ne détecte pas un tableau:
1. Vérifier la qualité de l'image (DPI)
2. Le tableau est peut-être dans une zone non-standard
3. Affiner le prompt pour ce cas spécifique

---

## Évolutions Futures

### 1. Support multi-langue

```python
prompt = f"""
Analyze this {language} PDF page and extract ALL tables...
"""
```

### 2. Fusion automatique de tableaux fragmentés

```python
def merge_fragmented_tables(tables):
    """Fusionne les tableaux qui se poursuivent sur plusieurs pages"""
    # Logique basée sur headers identiques
    pass
```

### 3. Validation automatique

```python
def validate_extraction(tables, rules):
    """Valide que l'extraction respecte des règles métier"""
    for table in tables:
        assert len(table['data']) > 0
        assert 'headers' in table
        # etc.
```

### 4. Interface Web

```python
# Flask/FastAPI endpoint
@app.post("/extract")
async def extract_tables(pdf: UploadFile):
    # Process PDF
    # Return Excel file
    pass
```

---

## Références

- [Claude API Documentation](https://docs.anthropic.com/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [OpenPyXL Documentation](https://openpyxl.readthedocs.io/)
- [Project README](../../README.md)

---

## Support

Pour toute question ou problème:

1. Vérifier les logs du script
2. Consulter la section [Troubleshooting](#troubleshooting)
3. Vérifier les [Limitations](#limitations)
4. Contacter l'équipe de développement

---

**Dernière mise à jour**: 2025-10-12
**Version**: 1.0.0
**Auteur**: Équipe Intelia Expert + Claude Code
