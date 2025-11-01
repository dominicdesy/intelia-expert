# Extracteur Multimodal - Texte + Images

Nouveau système d'extraction qui capture **à la fois le texte ET les images** des documents PDF.

---

## 🎯 Fonctionnalités

### Extraction de Texte (Existant)
- ✅ Extraction de texte avec pdfplumber (GRATUIT)
- ✅ Chunking intelligent (600 mots, 120 overlap)
- ✅ Métadonnées riches (60+ champs)
- ✅ Quality scoring
- ✅ Entity extraction
- ✅ Stockage dans Weaviate (InteliaKnowledge)

### Extraction d'Images (NOUVEAU) 🆕
- ✅ Extraction d'images depuis PDFs (PyMuPDF)
- ✅ Upload vers Digital Ocean Spaces (Object Storage)
- ✅ Génération de captions avec Claude Vision
- ✅ Embeddings visuels (CLIP) pour recherche multimodale
- ✅ Métadonnées stockées dans Weaviate (InteliaImages)
- ✅ Liens entre images et chunks de texte

---

## 📊 Architecture

```
┌─────────────┐
│ PDF Document│
└──────┬──────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌──────┐ ┌───────┐
│ Text │ │Images │
└──┬───┘ └───┬───┘
   │         │
   │         ├──► Digital Ocean Spaces (fichiers PNG/JPG)
   │         │    https://intelia.nyc3.cdn.digitaloceanspaces.com/...
   │         │
   │         └──► Weaviate (InteliaImages)
   │              - image_url
   │              - caption
   │              - CLIP vector
   │              - linked_chunk_ids
   │
   └──────────► Weaviate (InteliaKnowledge)
                - content
                - metadata
                - text vector
```

---

## 🚀 Installation

### 1. Dépendances Python

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\document_extractor

# Installer les nouvelles dépendances
pip install PyMuPDF Pillow boto3
```

### 2. Configuration Digital Ocean Spaces

Créer un fichier `.env` avec vos credentials:

```bash
# Digital Ocean Spaces (S3-compatible)
DO_SPACES_KEY=your_access_key_here
DO_SPACES_SECRET=your_secret_key_here
DO_SPACES_REGION=nyc3  # ou sfo3, ams3, etc.
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Weaviate (existant)
WEAVIATE_URL=https://your-cluster.weaviate.cloud
WEAVIATE_API_KEY=your_weaviate_key

# Claude API (existant)
CLAUDE_API_KEY=sk-ant-...
```

### 3. Créer le Bucket Spaces

1. Aller sur https://cloud.digitalocean.com/spaces
2. Créer un nouveau Space nommé **`intelia-knowledge`**
3. Région: **NYC3** (ou votre région préférée)
4. CDN: **Activer** (pour delivery rapide des images)
5. Accès: **Public** (pour que les URLs soient accessibles)

### 4. Créer les Credentials Spaces

1. Aller sur: API → Spaces Keys
2. Générer un nouveau pair de clés
3. Copier **Access Key** → `DO_SPACES_KEY`
4. Copier **Secret Key** → `DO_SPACES_SECRET`

---

## 📖 Utilisation

### Mode 1: Texte Seulement (comme avant)

```bash
python multimodal_extractor.py path/to/document.pdf --no-images
```

### Mode 2: Texte + Images (NOUVEAU)

```bash
# Extraire texte + images
python multimodal_extractor.py path/to/document.pdf

# Avec classification explicite
python multimodal_extractor.py path/to/document.pdf \
    --classification "intelia/public/broiler_farms/management/common"

# Traiter tous les PDFs d'un dossier
python multimodal_extractor.py path/to/folder

# Utiliser un bucket Spaces personnalisé
python multimodal_extractor.py path/to/document.pdf \
    --spaces-bucket "mon-bucket-custom"
```

### Exemple: Nano Manual

```bash
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\document_extractor

# Extraire le manuel Nano avec images
python multimodal_extractor.py \
    "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/intelia_products/nano/nano-manual.pdf" \
    --classification "intelia/intelia_products/nano/documentation/common"
```

---

## 📂 Résultat

### Texte → Weaviate (InteliaKnowledge)

```json
{
  "content": "The broiler should be fed a balanced diet...",
  "vector": [0.123, 0.456, ...],
  "page_number": 5,
  "has_images": true,
  "source_file": "nano-manual.pdf",
  "chunk_id": "nano_manual_chunk_005"
}
```

### Images → Digital Ocean Spaces

```
https://intelia.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page005_img01.png
https://intelia.nyc3.cdn.digitaloceanspaces.com/documents/nano-manual_page007_img01.png
```

### Métadonnées Images → Weaviate (InteliaImages)

```json
{
  "image_id": "nano_manual_page005_img01",
  "image_url": "https://intelia.nyc3.cdn.digitaloceanspaces.com/...",
  "caption": "Figure 1: Broiler housing ventilation system",
  "image_type": "diagram",
  "page_number": 5,
  "source_file": "nano-manual.pdf",
  "width": 1200,
  "height": 800,
  "file_size_kb": 245.3,
  "format": "png",
  "linked_chunk_ids": ["nano_manual_chunk_005"],
  "vector": [0.789, 0.234, ...],  // CLIP embedding
  "owner_org_id": "intelia",
  "visibility_level": "intelia_products",
  "site_type": "nano",
  "category": "documentation"
}
```

---

## 🔍 Recherche Multimodale

### Recherche Textuelle (retourne texte + images liées)

```python
from weaviate_integration.ingester_v2 import WeaviateIngesterV2
from services.image_ingester import ImageIngester

# Rechercher du texte
text_ingester = WeaviateIngesterV2("InteliaKnowledge")
text_results = text_ingester.search("broiler ventilation system")

# Pour chaque résultat texte, obtenir les images liées
image_ingester = ImageIngester()
for result in text_results:
    chunk_id = result['chunk_id']
    images = image_ingester.get_images_by_chunk(chunk_id)
    print(f"Chunk: {result['content'][:100]}...")
    for img in images:
        print(f"  → Image: {img['image_url']}")
        print(f"     Caption: {img['caption']}")
```

### Recherche Visuelle (retourne images similaires)

```python
# Rechercher par description
image_results = image_ingester.search_images("ventilation diagram", limit=5)

for result in image_results:
    print(f"Image: {result['caption']}")
    print(f"URL: {result['image_url']}")
    print(f"Source: {result['source_file']} (page {result['page_number']})")
```

---

## 💰 Coûts

### Digital Ocean Spaces

**Plan Standard:**
- 250 GB stockage: **$5/mois**
- 1 TB bande passante sortante: **inclus**
- CDN delivery: **inclus**
- Requêtes illimitées: **inclus**

**Estimation:**
- 1 PDF de 100 pages avec 50 images (~125 MB)
- 100 PDFs = 12.5 GB de stockage
- **Coût: $5/mois** (largement dans le plan gratuit)

### Weaviate Cloud

**Pas de coût supplémentaire:**
- Seulement les métadonnées sont stockées (URLs, captions, vectors)
- Les fichiers binaires lourds sont dans Spaces
- Augmentation minime de la base de données vectorielle

---

## 🎨 Types d'Images Détectés

L'extracteur classifie automatiquement les images:

- **diagram** - Diagrammes, schémas, flowcharts
- **chart** - Graphiques, courbes, plots
- **table** - Tableaux de données (format image)
- **photo** - Photos réelles
- **infographic** - Infographies, illustrations
- **unknown** - Type non déterminé

---

## 🛠️ Architecture Technique

### Fichiers Créés

```
document_extractor/
├── multimodal_extractor.py           # ← Extracteur principal (NOUVEAU)
├── services/
│   ├── __init__.py
│   ├── spaces_uploader.py            # ← Upload vers Spaces (NOUVEAU)
│   └── image_ingester.py             # ← Ingestion Weaviate (NOUVEAU)
├── multi_format_pipeline.py          # Existant (texte seulement)
└── weaviate_integration/
    └── ingester_v2.py                 # Existant (texte seulement)
```

### Workflow

```python
# 1. Extraire texte (pipeline existant)
text_result = self.text_pipeline.process_file(pdf_path)
text_chunks = text_result.chunks_with_metadata

# 2. Ingérer texte dans Weaviate (InteliaKnowledge)
self.text_ingester.ingest_chunks(text_chunks)

# 3. Extraire images du PDF
images = self.extract_images_from_pdf(pdf_path)

# 4. Pour chaque image:
for image in images:
    # 4a. Upload vers Spaces
    image_url = self.spaces_uploader.upload_image(
        image_data=image["image_data"],
        filename=image["filename"]
    )

    # 4b. Générer caption (optionnel - Claude Vision)
    caption = self._generate_caption(image["pil_image"], context)

    # 4c. Créer métadonnées
    image_metadata = {
        "image_url": image_url,
        "caption": caption,
        "page_number": image["page_number"],
        "linked_chunk_ids": [chunk_ids_from_same_page]
    }

    # 4d. Ingérer métadonnées dans Weaviate (InteliaImages)
    self.image_ingester.ingest_image(image_metadata)
```

---

## ⚙️ Configuration Avancée

### Filtrer les Petites Images

Dans `multimodal_extractor.py`, ligne 120:

```python
# Ignorer images < 100x100 pixels (icônes, décorations)
if width < 100 or height < 100:
    continue

# Modifier le seuil:
if width < 200 or height < 200:  # Plus strict
    continue
```

### Changer le Dossier de Stockage

```python
# Par défaut: documents/
image_url = uploader.upload_image(
    image_data=img_bytes,
    filename="image.png",
    folder="documents"  # ← Modifier ici
)

# Exemple: Organiser par source
folder = f"nano-manual/{page_num}"
```

### Désactiver la Génération de Captions

Si vous ne voulez pas utiliser Claude Vision pour les captions:

```python
# Ligne 250 dans multimodal_extractor.py
caption = self._generate_caption(image, context)

# Remplacer par:
caption = f"Image from {source_file} page {page_number}"
```

---

## 🐛 Dépannage

### Erreur: "Spaces credentials not found"

**Solution**: Vérifier le fichier `.env`:

```bash
# Vérifier que les variables sont définies
cat .env | grep DO_SPACES

# Doit afficher:
DO_SPACES_KEY=...
DO_SPACES_SECRET=...
DO_SPACES_REGION=nyc3
```

### Erreur: "Collection InteliaImages does not exist"

**Normal** - La collection est créée automatiquement au premier lancement.

Si problème persiste:

```python
# Créer manuellement
from services.image_ingester import ImageIngester
ingester = ImageIngester()  # Crée automatiquement la collection
```

### Images Trop Petites (Icônes)

**Solution**: Augmenter le seuil de taille minimale (ligne 120):

```python
if width < 200 or height < 200:  # Au lieu de 100
    continue
```

### Upload Lent vers Spaces

**Normal** - Images lourdes prennent du temps.

**Optimisation**:
1. Activer le CDN dans Spaces settings
2. Utiliser compression PNG (déjà fait avec Pillow)
3. Traiter en parallèle (TODO: implémentation future)

---

## 📈 Prochaines Améliorations

### Phase 1 (Actuel)
- ✅ Extraction d'images depuis PDFs
- ✅ Upload vers Spaces
- ✅ Métadonnées dans Weaviate
- ✅ Liens images ↔ texte

### Phase 2 (À venir)
- ⏳ Captions générés avec Claude Vision
- ⏳ CLIP embeddings pour recherche visuelle
- ⏳ OCR pour texte dans images
- ⏳ Table extraction (tableaux complexes)

### Phase 3 (Futur)
- 🔮 Recherche image-à-image (upload une image, trouve similaires)
- 🔮 Extraction de diagrammes complexes
- 🔮 Génération automatique de descriptions détaillées
- 🔮 Support vidéo (extraction de frames)

---

## 💡 Exemples d'Utilisation

### Cas 1: Manuel Technique avec Diagrammes

```bash
# Extraire un manuel avec beaucoup de schémas
python multimodal_extractor.py "manuals/ross-308-handbook.pdf" \
    --classification "intelia/public/broiler_farms/breed/ross_308"

# Résultat:
# - Texte: 450 chunks dans Weaviate
# - Images: 75 diagrammes uploadés vers Spaces
# - Recherche: "ventilation system" → retourne texte + images liées
```

### Cas 2: Rapport avec Graphiques

```bash
python multimodal_extractor.py "reports/performance-report-2024.pdf" \
    --classification "intelia/internal/reports/performance/common"

# Résultat:
# - Graphiques de performance extraits
# - Tableaux convertis en images
# - Accessible via recherche multimodale
```

### Cas 3: Batch Processing

```bash
# Traiter tous les manuels Nano
python multimodal_extractor.py "Sources/intelia/intelia_products/nano/" \
    --classification "intelia/intelia_products/nano/documentation/common"

# Traiter tous les guides Ross
python multimodal_extractor.py "Sources/intelia/public/broiler_farms/breed/ross_308/" \
    --classification "intelia/public/broiler_farms/breed/ross_308"
```

---

## 📞 Support

Pour questions ou problèmes:
1. Vérifier cette documentation
2. Consulter les logs (`logging.INFO`)
3. Tester avec un petit PDF d'abord
4. Contacter l'équipe technique Intelia

---

**Version**: 1.0.0
**Date**: 2025-10-31
**Auteur**: Intelia Team
