# Guide: Re-extraction du Manuel Nano avec Images

Guide étape par étape pour nettoyer les données existantes et refaire l'extraction avec les images.

---

## 🎯 Objectif

Remplacer les données texte-seulement du manuel Nano par des données enrichies avec images:
- ❌ **Ancien**: Texte uniquement
- ✅ **Nouveau**: Texte + Images (diagrammes, schémas, figures)

---

## 📋 Étapes

### Option 1: Script Automatique (Recommandé) 🚀

Un seul script qui fait tout automatiquement:

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\document_extractor

python reextract_nano_with_images.py
```

Le script va:
1. ✅ Supprimer les données existantes du Nano dans Weaviate
2. ✅ Extraire texte + images du PDF
3. ✅ Uploader images vers Spaces (`documents/`)
4. ✅ Ingérer tout dans Weaviate

**Temps estimé**: 5-10 minutes (selon taille du PDF)

---

### Option 2: Étape par Étape (Manuel)

Si vous préférez contrôler chaque étape:

#### Étape 1: Nettoyer les données existantes

```bash
python cleanup_nano.py
```

Confirmez avec `yes` quand demandé.

Le script va chercher et supprimer tous les chunks contenant:
- `nano-manual`
- `nano_manual`
- `nano/`
- `/nano/`

#### Étape 2: Extraire avec images

```bash
python multimodal_extractor.py ^
    "Sources\intelia\intelia_products\nano\nano-manual.pdf" ^
    --classification "intelia/intelia_products/nano/documentation/common"
```

---

## 📊 Ce Qui Se Passe

### Pendant le Nettoyage

```
================================================================================
CLEANING INTELIA KNOWLEDGE (Text Chunks)
================================================================================
Counting existing Nano manual chunks...
  Found 125 chunks matching pattern 'nano-manual'
  ✓ Deleted 125 chunks

✓ Total text chunks deleted: 125

================================================================================
CLEANING INTELIA IMAGES (Image Metadata)
================================================================================
  InteliaImages collection does not exist yet (will be created)
```

### Pendant l'Extraction

```
================================================================================
PROCESSING DOCUMENT: nano-manual.pdf
================================================================================

[1/3] Extracting TEXT...
✓ Text extraction complete: 125 chunks
  Ingested to Weaviate: 125 successful

[2/3] Extracting IMAGES...
  Page 1: Found 2 images
    Extracted: nano-manual_page001_img01.png (1200x800)
  Page 5: Found 3 images
    Extracted: nano-manual_page005_img01.png (1024x768)
  ...
✓ Image extraction complete: 47 images

[3/3] Uploading IMAGES to Spaces...
  ✓ Uploaded: nano-manual_page001_img01.png
    URL: https://intelia-knowledge.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page001_img01.png
  ✓ Ingested metadata to Weaviate
  ...

================================================================================
PROCESSING COMPLETE
================================================================================
Text chunks: 125
Images: 47
Errors: 0
```

---

## ✅ Vérification

### 1. Vérifier Weaviate

Connectez-vous à votre dashboard Weaviate et vérifiez:

**Collection InteliaKnowledge:**
- Nombre d'objets: devrait être le même qu'avant (~125 chunks)
- Mais maintenant avec métadonnées d'images

**Collection InteliaImages (nouvelle):**
- Nombre d'objets: ~47 images
- Chaque objet a: `image_url`, `caption`, `page_number`, etc.

### 2. Vérifier Digital Ocean Spaces

1. Aller sur: https://cloud.digitalocean.com/spaces
2. Ouvrir le bucket `intelia-knowledge`
3. Naviguer dans le dossier `documents/`
4. Vous devriez voir les images PNG:
   ```
   documents/
   ├── nano-manual_page001_img01.png
   ├── nano-manual_page001_img02.png
   ├── nano-manual_page005_img01.png
   └── ...
   ```

### 3. Tester les URLs

Copier une URL d'image depuis les logs, par exemple:
```
https://intelia-knowledge.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page001_img01.png
```

Ouvrir dans un navigateur → L'image devrait s'afficher

### 4. Tester la Recherche

```python
from services.image_ingester import ImageIngester

ingester = ImageIngester()

# Rechercher des images
results = ingester.search_images("diagram", limit=5)

print(f"Trouvé {len(results)} images")
for r in results:
    print(f"  - {r['caption']}")
    print(f"    {r['image_url']}")
```

---

## 🔧 Dépannage

### Problème: "Nano manual PDF not found"

**Cause**: Le chemin vers le PDF est incorrect

**Solution**: Vérifier le chemin du fichier

```bash
# Trouver le PDF
dir /s /b C:\Software_Development\intelia-cognito\knowledge-ingesters\Sources\*nano*.pdf
```

Puis ajuster le chemin dans le script.

### Problème: "Weaviate credentials not found"

**Cause**: Variables d'environnement manquantes

**Solution**: Vérifier le `.env`

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters
type .env | findstr WEAVIATE
```

### Problème: "Spaces credentials not found"

**Cause**: Variables Digital Ocean manquantes

**Solution**: Vérifier le `.env`

```bash
type .env | findstr DO_SPACES
```

Doit afficher:
```
DO_SPACES_KEY=...
DO_SPACES_SECRET=...
DO_SPACES_BUCKET=intelia-knowledge
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

### Problème: Cleanup échoue avec "Filter not found"

**Normal** si aucun chunk Nano n'existe

Le script continue quand même vers l'extraction.

---

## 📸 Résultat Final

### Avant (texte seulement)

```json
{
  "content": "Figure 1 shows the ventilation system...",
  "source_file": "nano-manual.pdf",
  "page_number": 5
}
```

### Après (texte + images)

**Chunk de texte (InteliaKnowledge):**
```json
{
  "content": "Figure 1 shows the ventilation system...",
  "source_file": "nano-manual.pdf",
  "page_number": 5,
  "has_images": true
}
```

**Image associée (InteliaImages):**
```json
{
  "image_id": "nano_manual_page005_img01",
  "image_url": "https://intelia-knowledge.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page005_img01.png",
  "caption": "Figure 1: Ventilation system diagram",
  "page_number": 5,
  "source_file": "nano-manual.pdf",
  "linked_chunk_ids": ["chunk_nano_p5_001"],
  "image_type": "diagram"
}
```

---

## 🎉 Prochaines Étapes

Une fois la re-extraction complète:

1. **Intégrer dans l'application**
   - Modifier le RAG pour retourner aussi les images liées
   - Afficher images dans les résultats de recherche

2. **Extraire d'autres documents**
   - Ross 308 Handbook
   - Cobb Management Guide
   - Etc.

3. **Optimiser**
   - Améliorer les captions avec Claude Vision
   - Ajouter OCR pour texte dans images
   - Classification automatique des types d'images

---

**Prêt à lancer?**

```bash
python reextract_nano_with_images.py
```

Confirmez avec `yes` et laissez le script travailler! ✨
