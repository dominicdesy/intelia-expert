# Web Extractor - Documentation Complète

Système d'extraction et d'ingestion de contenu web vers Weaviate avec classification automatique et rate limiting intelligent.

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Fichier Excel - Structure](#fichier-excel---structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Utilisation](#utilisation)
7. [Rate Limiting](#rate-limiting)
8. [Déduplication](#déduplication)
9. [Classification](#classification)
10. [Dépannage](#dépannage)

---

## Vue d'ensemble

Le **Web Extractor** extrait le contenu de pages web, le classifie selon une taxonomie prédéfinie, le découpe en chunks sémantiques et l'ingère dans Weaviate pour utilisation dans le système RAG d'Intelia.

### Fonctionnalités Principales

✅ **Extraction Web Automatique**
- Scraping HTML avec BeautifulSoup
- Conversion en Markdown propre
- Support multi-pages

✅ **Classification Intelligente**
- Classification basée sur la structure de répertoires
- Métadonnées enrichies (owner, visibility, site_type, category, breed)
- Confidence scoring

✅ **Rate Limiting par Domaine**
- 3 minutes minimum entre pages du même domaine
- Traitement parallèle de domaines différents
- Respect des bonnes pratiques web

✅ **Gestion Excel Complète**
- Lecture des URLs depuis `websites.xlsx`
- Mise à jour automatique du Status
- Tracking des erreurs et statistiques

✅ **Ingestion Weaviate**
- Push automatique vers `InteliaKnowledgeBase`
- Chunking sémantique (600 mots, 120 overlap)
- Déduplication automatique

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    EXCEL FILE (websites.xlsx)                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ URL | Classification | Notes | Status | Processed Date │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               WEB BATCH PROCESSOR                            │
├─────────────────────────────────────────────────────────────┤
│  1. Read Excel (Sheet: URL)                                 │
│  2. Filter (Status != "processed")                          │
│  3. Rate Limiting Check (3 min per domain)                  │
│  4. Extract Content (BeautifulSoup)                         │
│  5. Classify (Path-based from Excel column)                 │
│  6. Enrich Metadata (Claude API)                            │
│  7. Chunk Text (600 words, 120 overlap)                     │
│  8. Ingest to Weaviate                                      │
│  9. Update Excel Status                                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  WEAVIATE CLOUD                              │
│  Collection: InteliaKnowledgeBase                           │
│  - Chunks with full metadata                                │
│  - Vectorized (text-embedding-3-large)                      │
│  - Ready for RAG queries                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Fichier Excel - Structure

### Feuille: `URL`

Le fichier `websites.xlsx` contient une feuille nommée **URL** avec les colonnes suivantes:

| Colonne | Type | Requis | Description | Exemple |
|---------|------|---------|-------------|---------|
| **Website Address** | URL | ✅ Oui | URL complète de la page à extraire | `https://www.thepoultrysite.com/articles/broiler-care-practices` |
| **Classification** | Texte | ✅ Oui | Chemin de classification (format: org/visibility/site/category/sub) | `intelia/public/broiler_farms/management/common` |
| **Notes** | Texte | ❌ Non | Notes ou description du contenu | `Article sur les pratiques d'élevage` |
| **Status** | Texte | ❌ Auto | Status de traitement (auto-géré) | `processed`, `failed`, `pending`, ou vide |
| **Processed Date** | Date | ❌ Auto | Date/heure de traitement (auto-ajouté) | `2025-10-29T20:05:44.182298` |
| **Chunks Created** | Nombre | ❌ Auto | Nombre de chunks créés (auto-ajouté) | `10` |
| **Error Message** | Texte | ❌ Auto | Message d'erreur si échec (auto-ajouté) | `Connection timeout` |

### Format de Classification

Le format de la colonne **Classification** suit la structure des répertoires de documents:

```
{owner_org_id}/{visibility}/{site_type}/{category}/{subcategory}
```

**Exemples valides:**
```
intelia/public/broiler_farms/management/common
intelia/public/layer_farms/biosecurity/common
intelia/public/breeding_farms/breed/ross_308
intelia/public/veterinary_services/common
intelia/internal/broiler_farms/management/common
```

### Feuille: `Classification` (Référence)

La deuxième feuille **Classification** contient la liste complète des chemins de classification valides pour faciliter la saisie avec validation de données.

---

## Installation

### Prérequis

- Python 3.11+
- Accès à Weaviate Cloud (DigitalOcean)
- Clés API: Claude (Anthropic), OpenAI
- Excel avec Microsoft Office ou LibreOffice

### Installation des dépendances

```bash
cd C:/Software_Development/intelia-cognito/data-pipelines/web_extractor

# Installer les dépendances (elles sont déjà dans document_extractor)
pip install -r ../document_extractor/requirements_multi_format.txt
```

### Configuration .env

Créer/vérifier le fichier `.env` dans `data-pipelines/`:

```bash
# Claude API (pour enrichissement métadonnées)
CLAUDE_API_KEY=sk-ant-...

# OpenAI API (pour embeddings Weaviate)
OPENAI_API_KEY=sk-...

# Weaviate Cloud
WEAVIATE_URL=https://intelia-expert-rag-9rhqrfcv.weaviate.network
WEAVIATE_API_KEY=...
```

---

## Configuration

### Paramètres par défaut

Le processeur utilise ces paramètres par défaut (modifiables dans le code):

```python
# Rate Limiting
domain_delay_seconds = 180  # 3 minutes entre pages du même domaine

# Weaviate
collection_name = "InteliaKnowledgeBase"

# Fichier Excel
excel_file = "websites.xlsx"
sheet_name = "URL"

# Delay général entre URLs
delay_seconds = 3  # 3 secondes (+ rate limiting si même domaine)
```

### Personnalisation

Pour modifier les paramètres, éditer `web_batch_processor.py`:

```python
processor = WebBatchProcessor(
    excel_file="websites.xlsx",
    sheet_name="URL",
    collection_name="InteliaKnowledgeBase"
)

# Modifier le délai par domaine
processor.domain_delay_seconds = 300  # 5 minutes au lieu de 3
```

---

## Utilisation

### Méthode 1: Traitement Automatique (Recommandé)

Traite toutes les URLs avec Status vide ou "pending":

```bash
cd C:/Software_Development/intelia-cognito/data-pipelines/web_extractor
python web_batch_processor.py
```

**Comportement:**
- Lit toutes les lignes de la feuille "URL"
- Ignore les lignes avec Status = "processed"
- Traite les lignes avec Status vide ou "pending"
- Applique rate limiting automatique (3 min/domaine)
- Met à jour Excel après chaque URL

### Méthode 2: Force Reprocess

Retraite TOUTES les URLs, même celles déjà processed:

```bash
python web_batch_processor.py force
```

⚠️ **Attention:** Cela ignore la déduplication et retraite tout.

### Méthode 3: Fichier Excel Personnalisé

```bash
python web_batch_processor.py path/to/custom_websites.xlsx
```

---

## Rate Limiting

### Fonctionnement

Le système applique un **rate limiting intelligent par domaine**:

```python
# Exemple de séquence de traitement
URL 1: https://thepoultrysite.com/article1  → Traité immédiatement
URL 2: https://example.com/page1            → Traité immédiatement (domaine différent)
URL 3: https://thepoultrysite.com/article2  → ATTENTE 3 minutes (même domaine que URL 1)
URL 4: https://example.com/page2            → ATTENTE 3 minutes (même domaine que URL 2)
```

### Règles

1. **Par Domaine**: Minimum 3 minutes entre deux pages du **même domaine**
2. **Cross-Domain**: Aucune attente entre domaines différents
3. **Tracking**: Garde en mémoire le dernier accès par domaine
4. **Message**: Affiche le temps d'attente restant

### Exemple de Log

```
[1/10] https://thepoultrysite.com/article1
  Processing...
  SUCCESS (15.2s)

[2/10] https://example.com/page1
  Processing...
  SUCCESS (12.8s)

[3/10] https://thepoultrysite.com/article2
  Rate limit: Waiting 164.5s for domain thepoultrysite.com
  Processing...
  SUCCESS (14.1s)
```

---

## Déduplication

### Système de Tracking

Le web extractor utilise un système de déduplication via:

1. **Tracker JSON**: `processed_websites.json`
   - Enregistre les URLs traitées avec hash
   - Stocke métadonnées (date, chunks, confidence)

2. **Excel Status**: Colonne "Status"
   - `processed`: Traité avec succès
   - `failed`: Erreur lors du traitement
   - `pending` ou vide: À traiter

### Comportement

```python
# Première exécution
URL déjà dans tracker? NON → Traitement → Marquer "processed"

# Deuxième exécution (même URL)
URL déjà dans tracker? OUI → Skip
Status Excel = "processed"? OUI → Skip

# Force reprocess
python web_batch_processor.py force
→ Ignore tracker ET status → Retraite tout
```

---

## Classification

### Métadonnées Extraites

Chaque chunk contient ces métadonnées (extraites de la colonne Classification):

```json
{
  "content": "Texte du chunk...",
  "owner_org_id": "intelia",
  "visibility_level": "public_global",
  "site_type": "broiler_farms",
  "category": "management",
  "subcategory": "common",
  "species": "chicken",          // Enrichi par Claude
  "document_type": "article",    // Enrichi par Claude
  "source_file": "https://...",
  "extraction_method": "web_scrape",
  "word_count": 580,
  "extraction_timestamp": "2025-10-29T20:05:44Z"
}
```

### Mapping Visibility

| Excel | Weaviate |
|-------|----------|
| `public` | `public_global` |
| `internal` | `intelia_internal` |

---

## Dépannage

### Problème 1: Excel n'est pas mis à jour

**Cause**: Fichier Excel ouvert dans Excel/LibreOffice

**Solution**: Fermer le fichier Excel avant d'exécuter le script

---

### Problème 2: Erreur "WEAVIATE_URL not found"

**Cause**: Fichier `.env` non chargé

**Solution**:
```bash
# Vérifier que .env existe
ls -la C:/Software_Development/intelia-cognito/data-pipelines/.env

# Vérifier le contenu
cat C:/Software_Development/intelia-cognito/data-pipelines/.env | grep WEAVIATE
```

---

### Problème 3: "Connection timeout" pour certaines URLs

**Cause**: Site web bloque le scraping ou est lent

**Solutions**:
1. Vérifier que l'URL est accessible dans un navigateur
2. Augmenter le timeout dans `core/web_scraper.py`
3. Marquer manuellement Status = "failed" dans Excel

---

### Problème 4: "Rate limit: Waiting XXX seconds"

**Cause**: Comportement normal - protection du domaine cible

**Solution**: C'est normal! Le système attend 3 minutes entre pages du même domaine.

Pour modifier ce délai:
```python
# Dans web_batch_processor.py, ligne 72
self.domain_delay_seconds = 300  # Changer à 5 minutes
```

---

### Problème 5: Contenu extrait est vide ou incomplet

**Cause**: Structure HTML non standard ou JavaScript dynamique

**Solutions**:
1. Vérifier l'URL dans un navigateur
2. Certains sites nécessitent JavaScript → Utiliser Selenium (future amélioration)
3. Marquer manuellement Status = "failed" et traiter différemment

---

## Exemples d'Utilisation

### Exemple 1: Ajouter de nouvelles URLs

1. Ouvrir `websites.xlsx`
2. Aller dans la feuille "URL"
3. Ajouter une nouvelle ligne:
   - **Website Address**: `https://www.example.com/article`
   - **Classification**: `intelia/public/broiler_farms/biosecurity/common`
   - **Notes**: (optionnel) `Article sur biosécurité`
   - **Status**: Laisser vide
4. Sauvegarder et fermer Excel
5. Lancer le processeur:
   ```bash
   python web_batch_processor.py
   ```

### Exemple 2: Retraiter une URL failed

1. Ouvrir `websites.xlsx`
2. Trouver la ligne avec Status = "failed"
3. Changer Status à vide ou "pending"
4. Sauvegarder et fermer Excel
5. Lancer le processeur:
   ```bash
   python web_batch_processor.py
   ```

### Exemple 3: Traiter uniquement les URLs d'un domaine

Cette fonctionnalité n'est pas implémentée mais peut être ajoutée.

**Workaround actuel**:
1. Créer un fichier Excel séparé avec uniquement ces URLs
2. Lancer: `python web_batch_processor.py custom_file.xlsx`

---

## Maintenance

### Nettoyage Périodique

```bash
# Supprimer les caches Python
cd C:/Software_Development/intelia-cognito/data-pipelines/web_extractor
rm -rf __pycache__

# Backup du tracker
cp processed_websites.json processed_websites_backup_$(date +%Y%m%d).json
```

### Monitoring

Vérifier régulièrement:
- Nombre d'URLs en attente (Status vide)
- Taux d'échec (Status = "failed")
- Taille du fichier `processed_websites.json`

---

## Statistiques

À la fin de chaque exécution, le processeur affiche:

```
================================================================================
WEB BATCH PROCESSING COMPLETE
================================================================================
Total URLs: 25
Already Processed (skipped): 15
Skipped (status): 3
Newly Processed: 6
Failed: 1
Total Chunks Created: 58
Elapsed Time: 1230.5s (20.5 minutes)
Average Time per URL: 205.1s
```

---

## Support

Pour toute question ou problème:
1. Vérifier cette documentation
2. Consulter les logs dans la console
3. Vérifier la colonne "Error Message" dans Excel
4. Contacter l'équipe technique Intelia

---

## Historique des Versions

- **v1.0** (2025-10-29): Version initiale avec rate limiting et déduplication
