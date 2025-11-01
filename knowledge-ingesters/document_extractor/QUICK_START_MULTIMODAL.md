# Quick Start - Extracteur Multimodal

Guide rapide pour tester l'extraction d'images.

---

## ✅ Pré-requis

### 1. Variables d'environnement (`.env`)

Vous avez déjà ajouté:
```bash
DO_SPACES_KEY=your_key
DO_SPACES_SECRET=your_secret
DO_SPACES_BUCKET=intelia-knowledge
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...

CLAUDE_API_KEY=sk-ant-...
```

### 2. Installer les dépendances

```bash
pip install PyMuPDF Pillow boto3
```

---

## 🚀 Test Rapide (1 fichier)

### Option 1: Avec le manuel Nano

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\document_extractor

python multimodal_extractor.py ^
    "C:\Software_Development\intelia-cognito\knowledge-ingesters\Sources\intelia\intelia_products\nano\nano-manual.pdf" ^
    --classification "intelia/intelia_products/nano/documentation/common"
```

### Option 2: Avec n'importe quel PDF

```bash
python multimodal_extractor.py "chemin/vers/votre/fichier.pdf"
```

---

## 📊 Ce qui va se passer

1. **Extraction du texte** (comme avant)
   - Chunks de texte créés
   - Ingérés dans Weaviate (InteliaKnowledge)

2. **Extraction des images** (NOUVEAU)
   - Images détectées dans le PDF
   - Filtrées (> 100x100 pixels)
   - Converties en PNG

3. **Upload vers Spaces** (NOUVEAU)
   - Chaque image uploadée vers: `intelia-knowledge/documents/`
   - URL générée: `https://intelia-knowledge.nyc3.cdn.digitaloceanspaces.com/documents/...`

4. **Ingestion des métadonnées** (NOUVEAU)
   - Métadonnées des images stockées dans Weaviate (InteliaImages)
   - Lien avec les chunks de texte

---

## 🎯 Résultat Attendu

### Dans la Console

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
    Extracted: nano-manual_page001_img02.png (800x600)
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

================================================================================
EXTRACTION STATISTICS
================================================================================
Text chunks created: 125
Images extracted: 47
Images uploaded to Spaces: 47
Image metadata ingested to Weaviate: 47
Errors: 0
================================================================================
```

### Dans Digital Ocean Spaces

Vous verrez un nouveau dossier:

```
intelia-knowledge/
└── documents/
    └── nano-manual_page001_img01.png
    └── nano-manual_page001_img02.png
    └── nano-manual_page005_img01.png
    └── ...
```

Accessible via URL:
```
https://intelia-knowledge.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page001_img01.png
```

### Dans Weaviate

**Collection InteliaKnowledge (texte - existante):**
- 125 nouveaux chunks de texte

**Collection InteliaImages (images - NOUVELLE):**
- 47 nouveaux objets avec métadonnées d'images

---

## 🔍 Vérifier le Résultat

### 1. Vérifier Spaces (Digital Ocean)

1. Aller sur https://cloud.digitalocean.com/spaces
2. Ouvrir votre bucket `intelia-knowledge`
3. Naviguer dans le dossier `documents/`
4. Vous devriez voir les images PNG uploadées

### 2. Vérifier Weaviate

```python
from services.image_ingester import ImageIngester

ingester = ImageIngester()

# Rechercher des images
results = ingester.search_images("diagram", limit=5)

for result in results:
    print(f"Caption: {result['caption']}")
    print(f"URL: {result['image_url']}")
    print(f"Page: {result['page_number']}")
    print()
```

### 3. Tester une URL d'image

Copier une URL depuis la console (ex: `https://intelia-knowledge.nyc3.cdn.../...png`)

Ouvrir dans un navigateur → Vous devriez voir l'image

---

## ⚠️ Dépannage

### Erreur: "Spaces credentials not found"

**Solution**: Vérifier le fichier `.env`

```bash
# Dans le terminal
cd C:\Software_Development\intelia-cognito\knowledge-ingesters
type .env | findstr DO_SPACES
```

Doit afficher vos credentials.

### Erreur: "Access Denied" lors de l'upload

**Cause**: Les credentials Spaces ne sont pas valides

**Solution**:
1. Vérifier les clés dans Digital Ocean → API → Spaces Keys
2. Regénérer si nécessaire
3. Mettre à jour le `.env`

### Erreur: "Collection InteliaImages does not exist"

**Normal** - La collection est créée automatiquement au premier lancement.

Si l'erreur persiste:
```bash
python -c "from services.image_ingester import ImageIngester; ImageIngester()"
```

### Aucune image extraite

**Cause**: Le PDF n'a pas d'images, ou seulement des petites images (< 100x100px)

**Solution**: Vérifier avec un PDF qui contient des diagrammes/figures

---

## 🎨 Test avec un PDF Simple

Si vous n'avez pas le manuel Nano, testez avec n'importe quel PDF:

```bash
# Télécharger un PDF de test (guide Ross par exemple)
python multimodal_extractor.py "path/to/any-pdf-with-images.pdf"
```

Le script détectera et extraira automatiquement toutes les images > 100x100 pixels.

---

## 📝 Options Avancées

### Désactiver l'extraction d'images

```bash
python multimodal_extractor.py document.pdf --no-images
```

### Traiter tout un dossier

```bash
python multimodal_extractor.py "Sources/intelia/intelia_products/nano/"
```

### Utiliser un bucket custom

```bash
python multimodal_extractor.py document.pdf --spaces-bucket "mon-bucket"
```

---

## ✅ Prochaines Étapes

Une fois que l'extraction fonctionne:

1. **Tester la recherche multimodale**
   - Rechercher du texte → obtenir images liées
   - Rechercher des images par description

2. **Extraire tous vos documents**
   - Batch processing de tous les PDFs
   - Organisation par catégorie

3. **Intégrer dans l'application**
   - Afficher images dans les résultats de recherche
   - Galerie d'images par document

---

**Prêt à tester?**

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\document_extractor
python test_multimodal.py
```

Ou directement:

```bash
python multimodal_extractor.py "chemin/vers/un/pdf.pdf"
```
