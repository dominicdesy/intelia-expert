# Web Auto-Classifier - Guide d'utilisation

Script intelligent qui analyse automatiquement les pages web et les classifie selon la taxonomie Intelia.

---

## Fonctionnement

Le script effectue ces étapes pour chaque URL:

1. **Extraction des métadonnées de la page**:
   - 📍 **Breadcrumbs** (fil d'Ariane) - Excellent indicateur de classification
   - 🏷️ **Catégories** de la page (meta tags, classes CSS)
   - 🔖 **Tags** et mots-clés
   - 📄 **Titre** et contenu principal

2. **Classification intelligente avec Claude**:
   - Analyse le titre, breadcrumbs, catégories et contenu
   - Compare avec la taxonomie Intelia
   - Détermine: site_type, category, subcategory
   - Calcule un score de confiance (0-100%)

3. **Mise à jour automatique du fichier Excel**:
   - Remplace "To be analyzed" par la classification détectée
   - Ajoute une note avec le niveau de confiance et le raisonnement

---

## Prérequis

### 1. Fichier Excel (`websites.xlsx`)

Dans la feuille "URL", ajouter les URLs à classifier avec:
- **Website Address**: L'URL complète
- **Classification**: Écrire `To be analyzed`
- **Notes**: (Optionnel) Description

**Exemple:**

| Website Address | Classification | Notes |
|----------------|----------------|-------|
| https://www.thepoultrysite.com/articles/broiler-management-best-practices | To be analyzed | Article sur gestion poulets |
| https://aviagen.com/ross-308-handbook | To be analyzed | Guide Ross 308 |

### 2. Variables d'environnement

Fichier `.env` dans `knowledge-ingesters/`:

```bash
# Claude API (pour classification)
CLAUDE_API_KEY=sk-ant-...

# Optionnel (si vous voulez lancer l'extraction après)
OPENAI_API_KEY=sk-...
WEAVIATE_URL=https://...
WEAVIATE_API_KEY=...
```

---

## Utilisation

### Mode Standard (toutes les URLs "To be analyzed")

```bash
cd C:/Software_Development/intelia-cognito/knowledge-ingesters/web_extractor
python web_auto_classifier.py
```

**Ce qui se passe:**
- Lit toutes les URLs avec "To be analyzed"
- Les classifie une par une avec Claude
- Met à jour Excel avec les classifications

### Mode Test (limité)

Tester avec seulement 3 URLs:

```bash
python web_auto_classifier.py --limit 3
```

### Mode Dry-Run (afficher sans modifier)

Voir ce qui serait fait sans sauvegarder:

```bash
python web_auto_classifier.py --dry-run
```

### Fichier Excel personnalisé

```bash
python web_auto_classifier.py --excel mon_fichier.xlsx
```

---

## Exemple de Sortie

```
================================================================================
WEB AUTO-CLASSIFIER
================================================================================
📊 5 URLs à classifier

[1] https://www.thepoultrysite.com/articles/broiler-care-practices
  📥 Extraction de la page...
  📍 Breadcrumbs: Home > Articles > Broilers > Management
  🏷️  Catégories: Broiler Production, Farm Management
  🔖 Tags: broilers, management, welfare, production
  🤖 Classification avec Claude...
  ✅ Classification: intelia/public/broiler_farms/management/common
     Confiance: 92%
     Raison: Breadcrumb indique "Broilers > Management", contenu général sur pratiques d'élevage

[2] https://aviagen.com/ross-308-parent-stock-handbook
  📥 Extraction de la page...
  📍 Breadcrumbs: Products > Ross > Ross 308 > Parent Stock
  🏷️  Catégories: Breed Guides, Parent Stock
  🔖 Tags: ross, 308, parent stock, breeding
  🤖 Classification avec Claude...
  ✅ Classification: intelia/public/breeding_farms/breed/ross_308_parent_stock
     Confiance: 95%
     Raison: URL et breadcrumb mentionnent explicitement Ross 308 Parent Stock

[3] https://www.poultryworld.net/biosecurity-measures
  📥 Extraction de la page...
  📍 Breadcrumbs: Articles > Health > Biosecurity
  🏷️  Catégories: Biosecurity, Disease Prevention
  🔖 Tags: biosecurity, sanitation, protocols
  🤖 Classification avec Claude...
  ✅ Classification: intelia/public/broiler_farms/biosecurity/common
     Confiance: 88%
     Raison: Focus sur biosécurité, applicable à l'élevage de poulets de chair

💾 Sauvegarde dans Excel...
✅ Fichier sauvegardé: websites.xlsx

================================================================================
RÉSUMÉ DE LA CLASSIFICATION
================================================================================
Total traité: 5
✅ Succès: 5
❌ Échecs: 0
📊 Confiance moyenne: 91.2%

📋 Classifications attribuées:
  - intelia/public/broiler_farms/biosecurity/common: 1 URL(s)
  - intelia/public/broiler_farms/management/common: 2 URL(s)
  - intelia/public/breeding_farms/breed/ross_308_parent_stock: 1 URL(s)
  - intelia/public/layer_farms/breed/hy_line_brown: 1 URL(s)
================================================================================
```

---

## Résultat dans Excel

Après exécution, Excel est mis à jour:

**AVANT:**
| Website Address | Classification | Notes |
|----------------|----------------|-------|
| https://thepoultrysite.com/article1 | To be analyzed | |

**APRÈS:**
| Website Address | Classification | Notes |
|----------------|----------------|-------|
| https://thepoultrysite.com/article1 | intelia/public/broiler_farms/management/common | Auto-classified (confidence: 92%) - Breadcrumb indique "Broilers > Management", contenu général |

---

## Taxonomie Intelia

Le script classifie selon cette structure:

```
intelia/{visibility}/{site_type}/{category}/{subcategory}
```

### Visibility
- `public` - Contenu public
- `internal` - Contenu interne Intelia

### Site Types
- `broiler_farms` - Élevage de poulets de chair
- `layer_farms` - Élevage de pondeuses
- `breeding_farms` - Élevage de reproducteurs
- `hatcheries` - Couvoirs
- `feed_mills` - Usines d'aliments
- `processing_plants` - Usines de transformation
- `veterinary_services` - Services vétérinaires

### Categories
- `biosecurity` - Biosécurité
- `breed` - Spécifique à une race
- `housing` - Bâtiments et équipements
- `management` - Gestion quotidienne

### Subcategories
- `common` - Général (pas spécifique à une race)
- `{breed_name}` - Spécifique: ross_308, cobb_500, hy_line_brown, etc.

---

## Indices Utilisés pour la Classification

Le script analyse ces éléments dans l'ordre de priorité:

### 1. Breadcrumbs (Priorité Haute) 🏆
Les fils d'Ariane sont l'indicateur le plus fiable:
```
Home > Products > Broilers > Ross 308 → breed: ross_308
Home > Articles > Layers > Management → layer_farms/management
```

### 2. Catégories de la Page (Priorité Moyenne)
Balises meta et classes CSS:
```html
<meta name="category" content="Broiler Production">
<div class="category-tag">Biosecurity</div>
```

### 3. Tags et Mots-clés (Priorité Faible)
```html
<meta name="keywords" content="broilers, biosecurity, protocols">
```

### 4. Titre et Contenu (Contexte)
Analysé pour confirmer la classification

---

## Workflow Complet

### Étape 1: Préparer Excel

1. Ouvrir `websites.xlsx`
2. Aller dans la feuille "URL"
3. Ajouter vos URLs avec `Classification = "To be analyzed"`
4. Sauvegarder et **fermer Excel** (important!)

### Étape 2: Classifier Automatiquement

```bash
# Test avec 3 URLs
python web_auto_classifier.py --limit 3 --dry-run

# Si les résultats sont bons, lancer sans dry-run
python web_auto_classifier.py --limit 3

# Puis toutes les URLs
python web_auto_classifier.py
```

### Étape 3: Vérifier les Résultats

1. Ouvrir `websites.xlsx`
2. Vérifier la colonne "Classification"
3. Lire les notes pour le niveau de confiance
4. Ajuster manuellement si nécessaire (confiance < 80%)

### Étape 4: Extraire et Ingérer

Une fois les classifications validées:

```bash
# Lancer l'extracteur web normal
python web_batch_processor.py
```

---

## Cas Spéciaux

### Pages Multi-Thèmes

Si une page couvre plusieurs sujets, Claude privilégie:
1. Le thème principal (basé sur breadcrumbs)
2. Le thème le plus spécifique

### Pages Génériques

Pour les pages très générales (ex: "Poultry Management Tips"):
- Classé dans `broiler_farms/management/common` par défaut
- Note indique la nature générale

### Échecs de Classification

Si Claude n'arrive pas à classifier (confiance < 50%):
- La classification reste "To be analyzed"
- Une note explique pourquoi
- Classifier manuellement

---

## Dépannage

### Problème: Excel n'est pas mis à jour

**Cause**: Fichier Excel ouvert

**Solution**: Fermer Excel avant de lancer le script

### Problème: "CLAUDE_API_KEY not found"

**Cause**: Variable d'environnement manquante

**Solution**:
```bash
# Vérifier le fichier .env
cd C:/Software_Development/intelia-cognito/knowledge-ingesters
cat .env | grep CLAUDE
```

### Problème: Toutes les classifications échouent

**Cause**: Pages inaccessibles ou bloquées

**Solution**:
1. Vérifier les URLs dans un navigateur
2. Certains sites bloquent le scraping
3. Classifier manuellement ces URLs

### Problème: Classifications incorrectes

**Cause**: Métadonnées de page trompeuses

**Solution**:
1. Vérifier le niveau de confiance (< 70% = suspect)
2. Corriger manuellement dans Excel
3. Signaler les patterns problématiques

---

## Performance

- **Vitesse**: ~5-10 secondes par URL (extraction + classification)
- **Pause**: 2 secondes entre chaque URL (respect des serveurs)
- **Limite**: Aucune limite technique, mais recommandé de traiter par batch de 20-50

**Estimation**:
- 10 URLs = ~2 minutes
- 50 URLs = ~10 minutes
- 100 URLs = ~20 minutes

---

## Conseils

✅ **Faire un dry-run d'abord** pour vérifier les résultats

✅ **Commencer par 5-10 URLs** pour calibrer

✅ **Vérifier les confidences** - Ajuster manuellement si < 75%

✅ **Utiliser les breadcrumbs** - Ajouter des URLs avec de bons breadcrumbs = meilleures classifications

✅ **Grouper par domaine** - Les pages du même site ont souvent une structure similaire

❌ **Ne pas lancer sur 1000 URLs** d'un coup - Traiter par batch

❌ **Ne pas négliger la vérification** - Toujours valider les résultats

---

## Support

Pour toute question:
1. Vérifier cette documentation
2. Lancer en mode `--dry-run` pour voir ce qui serait fait
3. Vérifier les logs dans la console
4. Contacter l'équipe technique Intelia
