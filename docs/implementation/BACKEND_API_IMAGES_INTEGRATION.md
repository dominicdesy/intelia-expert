# Backend API - Intégration Images

## Vue d'Ensemble

L'API backend retourne maintenant des images associées aux chunks de texte dans les réponses RAG.

## Modifications RAG

### Structure de Données

Le `RAGResult` inclut maintenant un champ `images`:

```python
@dataclass
class RAGResult:
    # ... champs existants ...
    images: List[Dict] = field(default_factory=list)
```

### Format d'une Image

Chaque image dans `result.images` contient:

```python
{
    "image_id": "nano_manual_img008",
    "image_url": "https://intelia-expert-images.tor1.cdn.digitaloceanspaces.com/documents/...",
    "caption": "Image 8 from Nano Installation and Operation Manual",
    "image_type": "diagram",
    "source_file": "C:\\...\\Nano EN.docx",
    "width": 941,
    "height": 560,
    "format": "jpeg"
}
```

## API Endpoint Changes

### Endpoint: `POST /api/v1/query`

**Avant**:
```json
{
  "answer": "Installation instructions...",
  "confidence": 0.95,
  "source": "rag_success",
  "context_docs": [...]
}
```

**Après (avec images)**:
```json
{
  "answer": "Installation instructions...",
  "confidence": 0.95,
  "source": "rag_success",
  "context_docs": [...],
  "images": [
    {
      "image_id": "nano_manual_img008",
      "image_url": "https://intelia-expert-images.tor1.cdn.digitaloceanspaces.com/documents/30-008-00096-605%20Installation%20and%20Operation%20Manual%20Nano%20EN_img08.jpeg",
      "caption": "Image 8 from Nano Installation and Operation Manual",
      "image_type": "diagram",
      "width": 941,
      "height": 560,
      "format": "jpeg"
    }
  ],
  "metadata": {
    "has_images": true
  }
}
```

## Backend Integration Steps

### Étape 1: Vérifier le Code Backend

Le backend utilise déjà `result.to_dict()` qui inclut automatiquement les images:

```python
# Dans backend/app/api/v1/query.py ou similaire
result = await rag_engine.generate_response(query, language, user_id)
return result.to_dict()  # Inclut déjà "images"
```

**Aucune modification nécessaire** si le backend utilise déjà `to_dict()`.

### Étape 2: Vérifier les CORS (si nécessaire)

Si les images sont sur un domaine différent (Digital Ocean Spaces), vérifier que CORS est configuré:

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou liste spécifique
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Étape 3: Logging (Optionnel)

Ajouter des logs pour tracer quand des images sont retournées:

```python
if result.images:
    logger.info(f"Returning {len(result.images)} images with response")
```

## Digital Ocean Spaces Configuration

### URLs des Images

Les images sont servies via CDN:
- Bucket: `intelia-expert-images`
- Région: `tor1`
- Format URL: `https://intelia-expert-images.tor1.cdn.digitaloceanspaces.com/documents/{filename}`

### Permissions

Les images doivent être **publiques** (lecture seule) pour être accessibles depuis le frontend.

Configuration Spaces:
```
Files and Folders → Public Access: Read Only
```

## Tests Backend

### Test 1: Query avec Images

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Comment installer le Nano?",
    "language": "fr",
    "user_id": "test"
  }'
```

Vérifier que la réponse contient:
- `"images": [...]` (liste non vide)
- `"metadata": {"has_images": true}`

### Test 2: Query sans Images

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is broiler nutrition?",
    "language": "en",
    "user_id": "test"
  }'
```

Vérifier que la réponse contient:
- `"images": []` (liste vide)
- `"metadata": {"has_images": false}`

## Monitoring

### Métriques à Surveiller

1. **Taille des Réponses**: Les réponses avec images sont plus grandes
2. **Temps de Réponse**: Récupération d'images ajoute ~50-200ms
3. **Taux d'Images**: % de requêtes retournant des images

### Exemple de Log

```
INFO - Query processed: query="Comment installer le Nano?",
       docs=85, images=3, duration=2.5s
```

## Troubleshooting

### Problème: Pas d'images retournées

**Vérifications**:
1. Les images sont-elles dans Weaviate?
   ```python
   collection.aggregate.over_all(total_count=True)
   ```
2. Le `source_file` des chunks correspond-il aux images?
3. Le `weaviate_client` est-il passé au `response_generator`?

### Problème: URLs d'images inaccessibles

**Vérifications**:
1. Les images existent-elles sur Spaces?
2. Les permissions sont-elles publiques?
3. Le CDN est-il activé?

### Problème: Erreurs CORS

**Solution**: Ajouter le domaine Spaces aux CORS autorisés:
```python
allow_origins=["https://intelia-expert-images.tor1.cdn.digitaloceanspaces.com"]
```

## Performance

### Optimisations Possibles

1. **Limite d'Images**: `max_images_per_chunk=3` (configurable)
2. **Lazy Loading**: Frontend charge les images uniquement quand visible
3. **CDN**: Digital Ocean Spaces CDN déjà activé
4. **Compression**: Images déjà optimisées lors de l'extraction

### Impact Performance

- Récupération images: ~50-200ms
- Taille réponse: +2-5KB par image (métadonnées uniquement)
- Images elles-mêmes: Chargées par le frontend depuis CDN

## Prochaines Étapes

1. ✅ Backend RAG intégration complète
2. ⏳ Tests backend avec vraies requêtes
3. ⏳ Frontend: Affichage des images
4. ⏳ UX: Galerie, zoom, lightbox, etc.

## Références

- Code RAG: `rag/core/response_generator.py`
- ImageRetriever: `rag/retrieval/image_retriever.py`
- Data Models: `rag/core/data_models.py`
- Tests: `rag/test_image_retrieval.py`
