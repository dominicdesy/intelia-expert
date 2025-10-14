# Guide d'Analyse d'Images Médicales - Intelia Expert

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Endpoints API](#endpoints-api)
5. [Tests et validation](#tests-et-validation)
6. [Exemples d'utilisation](#exemples-dutilisation)
7. [Limitations et considérations](#limitations-et-considérations)

---

## Vue d'ensemble

Le système d'analyse d'images médicales d'Intelia Expert permet aux éleveurs de soumettre des photos de volailles malades et de recevoir une analyse vétérinaire préliminaire automatisée.

### Fonctionnalités principales

- ✅ **Upload d'images** vers DigitalOcean Spaces (stockage sécurisé)
- ✅ **Analyse IA** avec Claude 3.5 Sonnet Vision
- ✅ **Contexte RAG** intégré (maladies avicoles depuis la base de connaissances)
- ✅ **Multilingue** (fr, en, es, de, it, pt, nl, pl)
- ✅ **Disclaimers vétérinaires** automatiques
- ✅ **Diagnostic structuré** (symptômes, hypothèses, recommandations)

### ⚠️ Avertissement

**Cette fonctionnalité est à usage ÉDUCATIF uniquement.**
- Les diagnostics fournis ne remplacent PAS une consultation vétérinaire
- Un diagnostic définitif nécessite un examen clinique et des tests de laboratoire
- En cas de doute, consultez TOUJOURS un vétérinaire qualifié

---

## Architecture

### Séparation Backend / LLM

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
│              - Upload UI (caché par défaut)                 │
│              - Affichage résultats analyse                  │
└────────────────────┬───────────────────┬────────────────────┘
                     │                   │
         ┌───────────▼──────────┐   ┌───▼─────────────────┐
         │   BACKEND (FastAPI)  │   │   LLM (FastAPI)     │
         │   Port: 8001         │   │   Port: 8000        │
         ├──────────────────────┤   ├─────────────────────┤
         │ • Upload images      │   │ • Claude Vision API │
         │ • DO Spaces storage  │   │ • RAG integration   │
         │ • Métadonnées DB     │   │ • Diagnostic        │
         │ • Gestion fichiers   │   │ • Multilingue       │
         └──────────────────────┘   └─────────────────────┘
                     │                           │
         ┌───────────▼──────────┐   ┌───────────▼─────────┐
         │  DigitalOcean Spaces │   │  Anthropic Claude   │
         │  • Stockage images   │   │  • Vision analysis  │
         │  • URLs signées      │   │  • Medical prompts  │
         │  • $5/mois           │   │  • Token counting   │
         └──────────────────────┘   └─────────────────────┘
```

### Flux de données

1. **Upload** : Frontend → Backend → DigitalOcean Spaces
2. **Analyse** : Frontend → LLM → Claude Vision API
3. **RAG Context** : LLM récupère contexte maladies depuis Weaviate/PostgreSQL
4. **Réponse** : Diagnostic structuré avec disclaimer vétérinaire

---

## Configuration

### 1. Variables d'environnement

#### Backend (`.env`)

```bash
# DigitalOcean Spaces Configuration
DO_SPACES_KEY=your_digitalocean_spaces_access_key
DO_SPACES_SECRET=your_digitalocean_spaces_secret_key
DO_SPACES_BUCKET=intelia-expert-images
DO_SPACES_REGION=nyc3  # nyc3, sfo3, sgp1, ams3, fra1
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

#### LLM (`.env`)

```bash
# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...your_key_here...
```

### 2. Dépendances Python

#### Backend

```bash
cd backend
pip install boto3>=1.28.0  # AWS SDK compatible DO Spaces
```

#### LLM

```bash
cd llm
pip install anthropic>=0.40.0  # Claude Vision API
pip install httpx[http2]>=0.27.0  # Pour fetch images depuis URLs
```

### 3. Base de données PostgreSQL

Créer la table `medical_images` :

```bash
cd backend/sql/schema
psql -U your_user -d your_db -f create_medical_images_table.sql
```

---

## Endpoints API

### Backend - Upload Images

#### `POST /api/v1/images/upload`

Upload une image médicale vers DigitalOcean Spaces.

**Request (multipart/form-data)**:

```bash
curl -X POST http://localhost:8001/api/v1/images/upload \
  -F "file=@chicken_sick.jpg" \
  -F "user_id=farmer-123" \
  -F "description=Poule avec diarrhée sanglante"
```

**Response**:

```json
{
  "success": true,
  "image_id": "a1b2c3d4-...",
  "url": "https://intelia-expert-images.nyc3.digitaloceanspaces.com/...",
  "spaces_key": "medical-images/farmer-123/2025/10/a1b2c3d4_chicken_sick.jpg",
  "size_bytes": 245678,
  "content_type": "image/jpeg",
  "expires_in_hours": 24,
  "message": "Image uploadée avec succès"
}
```

**Limites**:

- Taille max: 10 MB
- Formats acceptés: JPG, PNG, WEBP
- URL valide: 24 heures

---

### LLM - Analyse Vision

#### `POST /llm/chat-with-image`

Analyse une image médicale avec Claude Vision + contexte RAG.

**Option 1: Avec URL d'image** (depuis upload backend)

```bash
curl -X POST http://localhost:8000/llm/chat-with-image \
  -F "image_url=https://intelia-expert-images.nyc3.digitaloceanspaces.com/..." \
  -F "message=Cette poule a des diarrhées sanglantes, qu'est-ce qu'elle a ?" \
  -F "tenant_id=farmer-123" \
  -F "language=fr" \
  -F "use_rag_context=true"
```

**Option 2: Avec upload direct**

```bash
curl -X POST http://localhost:8000/llm/chat-with-image \
  -F "file=@chicken_sick.jpg" \
  -F "message=What disease does this chicken have?" \
  -F "language=en" \
  -F "use_rag_context=true"
```

**Response**:

```json
{
  "success": true,
  "analysis": "Basé sur les symptômes visuels observés...\n\n**Hypothèses diagnostiques:**\n\n- Coccidiose (probabilité élevée)\n  - Diarrhées sanglantes caractéristiques\n  - ...\n\n⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement...",
  "metadata": {
    "model": "claude-3-5-sonnet-20241022",
    "language": "fr",
    "tenant_id": "farmer-123",
    "processing_time": 3.45,
    "usage": {
      "input_tokens": 2456,
      "output_tokens": 892,
      "total_tokens": 3348
    },
    "rag_context_used": true,
    "rag_documents_count": 3
  }
}
```

**Paramètres**:

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `file` | File | Oui* | Image uploadée (JPG, PNG, WEBP) |
| `image_url` | String | Oui* | URL de l'image (si pas de file) |
| `message` | String | Oui | Question de l'utilisateur |
| `tenant_id` | String | Non | ID du tenant (auto-généré si absent) |
| `language` | String | Non | Langue (auto-détectée si absente) |
| `use_rag_context` | Boolean | Non | Utiliser contexte RAG (default: true) |

*Fournir soit `file`, soit `image_url` (pas les deux)

---

#### `GET /llm/vision/health`

Health check du service Claude Vision.

```bash
curl http://localhost:8000/llm/vision/health
```

**Response**:

```json
{
  "status": "healthy",
  "message": "Claude Vision service disponible",
  "configured": true,
  "model": "claude-3-5-sonnet-20241022"
}
```

---

## Tests et validation

### Tests unitaires

```bash
cd llm
python -m pytest tests/test_vision_integration.py -v
```

**Tests inclus**:

- ✅ Initialisation du ClaudeVisionAnalyzer
- ✅ Conversion image → base64
- ✅ Construction du prompt vétérinaire
- ✅ Gestion d'erreurs (images invalides)
- ✅ Disclaimers multilingues
- ✅ (Optionnel) Test API live si `ANTHROPIC_API_KEY` définie

### Tests manuels

#### 1. Test Backend Upload

```bash
curl -X POST http://localhost:8001/api/v1/images/upload \
  -F "file=@test_chicken.jpg" \
  -F "user_id=test-user" \
  -F "description=Test upload"
```

**Attendu**: `{"success": true, "image_id": "...", "url": "..."}`

#### 2. Test LLM Vision (avec URL)

```bash
curl -X POST http://localhost:8000/llm/chat-with-image \
  -F "image_url=<URL_FROM_STEP_1>" \
  -F "message=What do you see in this image?" \
  -F "language=en"
```

**Attendu**: Analyse détaillée avec disclaimer

#### 3. Test LLM Vision (upload direct)

```bash
curl -X POST http://localhost:8000/llm/chat-with-image \
  -F "file=@test_chicken.jpg" \
  -F "message=Cette poule a l'air malade, qu'est-ce qu'elle a ?" \
  -F "language=fr"
```

---

## Exemples d'utilisation

### Exemple 1: Diagnostic de coccidiose

**Image**: Poule avec diarrhées sanglantes

**Question**: "Ma poule a des diarrhées rouges, qu'est-ce que c'est ?"

**Réponse attendue**:

```
Basé sur les symptômes visuels observés, voici mon analyse :

Observation visuelle :
- Diarrhées de couleur rouge/sanglante
- Plumes souillées au niveau du cloaque
- L'animal semble léthargique

Hypothèses diagnostiques (par ordre de probabilité) :

1. Coccidiose (Eimeria spp.) - Probabilité élevée
   - Les diarrhées sanglantes sont un symptôme caractéristique
   - Maladie parasitaire très fréquente chez les volailles
   - Affecte principalement les jeunes oiseaux (2-6 semaines)

2. Entérite nécrotique (Clostridium perfringens) - Probabilité modérée
   - Peut causer des diarrhées hémorragiques
   - Souvent secondaire à la coccidiose

Facteurs de risque :
- Surpopulation et stress
- Humidité élevée dans le poulailler
- Manque d'hygiène (litière humide)
- Jeune âge des oiseaux

Actions recommandées :
- Isoler immédiatement l'oiseau malade
- Tests diagnostiques : examen microscopique des fèces
- Traitement potentiel : anticoccidiens (à confirmer par vétérinaire)
- Améliorer les conditions d'hygiène

Prévention :
- Programme de vaccination contre la coccidiose
- Maintenir une litière sèche
- Éviter la surpopulation
- Rotation des parcours

⚠️ IMPORTANT: Cette analyse est fournie à titre éducatif uniquement.
Pour toute préoccupation de santé animale, consultez immédiatement un
vétérinaire qualifié. Un diagnostic définitif nécessite un examen
clinique complet et potentiellement des tests de laboratoire.
```

### Exemple 2: Diagnostic multilingue (anglais)

**Question**: "My hen has swollen eyes, what disease could this be?"

**Réponse**: Analyse complète en anglais avec recommandations (Infectious coryza, Mycoplasma, etc.)

---

## Limitations et considérations

### Limitations techniques

1. **Taille des images**: Maximum 10 MB par fichier
2. **Formats supportés**: JPG, PNG, WEBP uniquement
3. **Coûts API**: Claude Vision consomme ~2000-4000 tokens par analyse
4. **Temps de réponse**: 3-5 secondes typiquement
5. **Stockage**: DigitalOcean Spaces ($5/mois pour 250GB)

### Limitations médicales

1. **Pas de diagnostic définitif**: L'IA ne remplace pas un vétérinaire
2. **Symptômes visibles uniquement**: Certaines maladies sont invisibles
3. **Qualité des photos**: Résultats dépendent de la qualité de l'image
4. **Contexte limité**: L'IA ne connaît pas l'historique de l'élevage

### Considérations légales

1. **Responsabilité**: Disclaimers obligatoires sur toutes les réponses
2. **GDPR**: Stocker les images avec consentement utilisateur
3. **Pratique vétérinaire**: Ne pas remplacer l'examen clinique

### Sécurité

1. **Validation des uploads**: Types MIME vérifiés
2. **URLs signées**: Expiration après 24h
3. **Isolation tenant**: Chaque utilisateur a son propre dossier
4. **ACL privé**: Images non publiques par défaut

---

## Roadmap

### Version 1.1 (Future)

- [ ] Support vidéos courtes (symptômes comportementaux)
- [ ] Analyse batch (plusieurs images d'une même poule)
- [ ] Historique médical intégré
- [ ] Export PDF des analyses
- [ ] Dashboard vétérinaire (statistiques élevage)

### Version 2.0 (Future)

- [ ] Fine-tuning spécialisé maladies avicoles
- [ ] Reconnaissance automatique des races
- [ ] Détection de parasites externes
- [ ] Analyse de l'environnement (poulailler)

---

## Support et contact

Pour toute question technique :

- **Issues GitHub**: [lien vers votre repo]
- **Documentation**: `/docs`
- **Tests**: `llm/tests/test_vision_integration.py`

---

**Dernière mise à jour**: 2025-10-14
**Version**: 1.0.0
**Auteur**: Intelia Expert Team
