# Performance Extractor

Système d'extraction automatique de tableaux de performance depuis des PDFs.

Scripts pour extraire automatiquement les tableaux des PDFs et générer des fichiers Excel structurés pour le système RAG.

## 📁 Scripts

### 1. `extract_pdf_tables_claude_vision.py` ⭐ RECOMMANDÉ

**Extraction intelligente utilisant Claude Vision API**

```bash
# Usage basique
python extract_pdf_tables_claude_vision.py <pdf_file> <output.xlsx>

# Extraire des pages spécifiques
python extract_pdf_tables_claude_vision.py <pdf_file> <output.xlsx> <start_page> <end_page>
```

**Exemples:**

```bash
cd C:\intelia_gpt\intelia-expert\rag\performance_extractor

# Extraire tout le PDF
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/cobb/2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf" \
  "../documents/PerformanceMetrics/Cobb500_Output.xlsx"

# Extraire seulement les pages 4-6 (performance tables)
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/cobb/2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf" \
  "../documents/PerformanceMetrics/Cobb500_Performance.xlsx" \
  4 6
```

**Prérequis:**
```bash
pip install anthropic pymupdf pandas openpyxl pillow
export ANTHROPIC_API_KEY="sk-ant-api03-..."  # Votre clé API
```

**Avantages:**
- ✅ **Générique**: Fonctionne avec n'importe quel type de tableau
- ✅ **Précis**: 100% de précision sur les tests
- ✅ **Intelligent**: Détecte automatiquement les en-têtes, unités, métadonnées
- ✅ **Robuste**: Pas de mots-clés hardcodés

**Coût:** ~$0.01-0.03 USD par page

---

### 2. `extract_pdf_tables_to_excel.py` (Legacy)

**Extraction basée sur pdfplumber avec heuristiques**

⚠️ **Non recommandé** - Utiliser Claude Vision à la place

Gardé pour référence et cas où l'API Claude n'est pas disponible.

**Problèmes connus:**
- Rate des lignes de données
- Nécessite adaptation pour chaque type de tableau
- Moins précis

---

### 3. `merge_excel_files.py`

**Utilitaire pour fusionner plusieurs fichiers Excel**

```bash
python merge_excel_files.py <output.xlsx> <file1.xlsx> <file2.xlsx> ...
```

**Exemple:**
```bash
python merge_excel_files.py \
  "../documents/PerformanceMetrics/Combined.xlsx" \
  performance.xlsx \
  nutrition.xlsx \
  yield.xlsx
```

**Utilisation:** Combiner les résultats de plusieurs extractions partielles.

---

## 📊 Workflow Typique

### 1. Extraire les tableaux d'un nouveau PDF

```bash
cd C:\intelia_gpt\intelia-expert\rag\performance_extractor

# Extraire tous les tableaux
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/ross/Ross308-2022.pdf" \
  "../documents/PerformanceMetrics/Ross308-2022-Extracted.xlsx"
```

### 2. Vérifier le résultat

```bash
# Ouvrir le fichier Excel généré
explorer "..\documents\PerformanceMetrics\Ross308-2022-Extracted.xlsx"
```

### 3. Si extraction partielle nécessaire

```bash
# Extraire par sections
python extract_pdf_tables_claude_vision.py input.pdf performance.xlsx 4 6
python extract_pdf_tables_claude_vision.py input.pdf nutrition.xlsx 10 12
python extract_pdf_tables_claude_vision.py input.pdf yield.xlsx 13 14

# Fusionner
python merge_excel_files.py output.xlsx performance.xlsx nutrition.xlsx yield.xlsx
```

---

## 🗂️ Structure des Sorties

### Répertoire cible: `../../documents/PerformanceMetrics/`

Les fichiers Excel générés doivent être sauvegardés dans:
```
C:\intelia_gpt\intelia-expert\rag\documents\PerformanceMetrics\
```

### Format des fichiers Excel

Chaque feuille contient:

```
Rows 1-N:     Métadonnées (source_page, table_title, table_type, sex, unit_system, etc.)
Row N+1-N+3:  Informations de table (data_rows, columns, column definitions)
Row N+4:      Lignes vides
Row N+5:      En-tête de données (Age | Weight | Daily Gain | ...)
Row N+6+:     Données
```

**Exemple:**
```
Row 1:  metadata | value
Row 2:  source_page | 6
Row 3:  table_title | C500 Broiler Performance Objectives (Metric) - Female
Row 4:  table_type | performance
Row 5:  sex | female
...
Row 35: Age | Weight | Daily Gain | Average Daily Gain | ...
Row 36: 0 | 42 | | | ...
Row 37: 1 | 54 | 12 | | ...
...
```

---

## 🔍 Exemples Réels

### Exemple 1: Cobb500 (2022)

**Source:** `2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf`

**Commande:**
```bash
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/cobb/2022-Cobb500-Broiler-Performance-Nutrition-Supplement.pdf" \
  "../documents/PerformanceMetrics/Cobb500_Complete_Claude_Vision.xlsx" \
  4 14
```

**Résultat:**
- 11 feuilles créées
- 11 tableaux extraits
- Feuilles: mixed_metric, male_metric, female_metric, nutrient_med_large, amino_med_large, nutrient_small, yield_mixed_metric, yield_female_metric, yield_male_metric, etc.

### Exemple 2: Ross 308

```bash
python extract_pdf_tables_claude_vision.py \
  "../documents/Sources/public/species/broiler/breeds/ross/Ross308-2022.pdf" \
  "../documents/PerformanceMetrics/Ross308-2022.xlsx"
```

---

## 🛠️ Dépannage

### Erreur: "ANTHROPIC_API_KEY not found"

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows CMD
set ANTHROPIC_API_KEY=sk-ant-...

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

### Erreur: Module not found

```bash
pip install --upgrade anthropic pymupdf pandas openpyxl pillow
```

### Les tableaux ne sont pas détectés

1. Vérifier la qualité du PDF (pas d'images scannées)
2. Essayer avec un DPI plus élevé (modifier dans le script si nécessaire)
3. Vérifier que la page contient bien un tableau structuré

---

## 📚 Documentation Complète

Voir: `../../docs/guides/PDF_TABLE_EXTRACTION_CLAUDE_VISION.md`

Contient:
- Guide d'installation détaillé
- Architecture du système
- Analyse des coûts
- Bonnes pratiques
- Troubleshooting complet
- Exemples avancés

---

## 🚀 Intégration RAG

Les fichiers Excel générés sont directement utilisables par le système RAG:

1. **Emplacement:** `rag/documents/PerformanceMetrics/`
2. **Format structuré:** Métadonnées + données tabulaires
3. **Indexation:** Les métadonnées facilitent la recherche et le contexte

---

**Dernière mise à jour:** 2025-10-12
**Mainteneur:** Équipe Intelia Expert
