# Crawl.ps1 - Guide d'utilisation rapide

Script PowerShell pour explorer un site web et extraire toutes ses URLs internes.

---

## Usage Basique

### 1. Avec le site par défaut (poultryhub.org)
```powershell
cd C:\Software_Development\intelia-cognito\knowledge-ingesters\web_extractor
.\crawl.ps1
```

### 2. Avec votre propre site
```powershell
.\crawl.ps1 -StartUrl "https://www.votresite.com/"
```

### 3. Contrôler la profondeur de crawl
```powershell
# Profondeur 2 (plus rapide, moins d'URLs)
.\crawl.ps1 -StartUrl "https://www.votresite.com/" -MaxDepth 2

# Profondeur 5 (plus lent, plus d'URLs)
.\crawl.ps1 -StartUrl "https://www.votresite.com/" -MaxDepth 5
```

---

## Paramètres

| Paramètre | Description | Défaut | Exemple |
|-----------|-------------|--------|---------|
| **-StartUrl** | URL de départ du site à crawler | `https://www.poultryhub.org/` | `"https://aviagen.com/"` |
| **-MaxDepth** | Profondeur maximale de navigation | `3` | `2`, `5`, `10` |

---

## Résultat

Le script génère **2 fichiers** dans le répertoire courant:

### 1. crawl.txt (fichier texte simple)
Une URL par ligne, facile à lire et copier:
```
https://www.poultryhub.org/
https://www.poultryhub.org/production/
https://www.poultryhub.org/production/layer-housing/
https://www.poultryhub.org/production/broiler-housing/
```

### 2. site-urls.csv (pour Excel)
Format CSV avec métadonnées:
```csv
"Url","Depth"
"https://www.poultryhub.org/","0"
"https://www.poultryhub.org/production/","1"
"https://www.poultryhub.org/production/layer-housing/","2"
"https://www.poultryhub.org/production/broiler-housing/","2"
```

---

## Workflow Complet

### Étape 1: Crawler le site
```powershell
.\crawl.ps1 -StartUrl "https://aviagen.com/" -MaxDepth 3
```

### Étape 2: Consulter les URLs trouvées
```powershell
# Ouvrir le fichier texte (rapide)
notepad crawl.txt

# OU ouvrir le CSV dans Excel
.\site-urls.csv
```

### Étape 3: Copier les URLs dans websites.xlsx
**Méthode 1 (depuis crawl.txt)**:
1. Ouvrir `crawl.txt`
2. Sélectionner et copier les URLs intéressantes
3. Coller dans `websites.xlsx`, colonne "Website Address"
4. Écrire "To be analyzed" dans la colonne "Classification"

**Méthode 2 (depuis site-urls.csv)**:
1. Ouvrir `site-urls.csv` dans Excel
2. Copier les URLs intéressantes
3. Coller dans `websites.xlsx`, colonne "Website Address"
4. Écrire "To be analyzed" dans la colonne "Classification"

### Étape 4: Classifier automatiquement
```powershell
python web_auto_classifier.py
```

### Étape 5: Extraire et ingérer
```powershell
python web_batch_processor.py
```

---

## Exemples Pratiques

### Crawler Aviagen (documentation Ross)
```powershell
.\crawl.ps1 -StartUrl "https://aviagen.com/brands/ross/" -MaxDepth 4
```

### Crawler The Poultry Site
```powershell
.\crawl.ps1 -StartUrl "https://www.thepoultrysite.com/articles/" -MaxDepth 2
```

### Crawler Hy-Line International
```powershell
.\crawl.ps1 -StartUrl "https://www.hyline.com/" -MaxDepth 3
```

### Crawler Cobb
```powershell
.\crawl.ps1 -StartUrl "https://www.cobb-vantress.com/" -MaxDepth 3
```

---

## Fonctionnement

Le crawler:
1. **Démarre** à l'URL spécifiée (`-StartUrl`)
2. **Extrait** tous les liens de la page
3. **Filtre** pour ne garder que les URLs du même domaine
4. **Visite** chaque lien (jusqu'à la profondeur `-MaxDepth`)
5. **Exporte** toutes les URLs trouvées dans `site-urls.csv`

**Sécurité**: Le crawler reste sur le même domaine (ne suit pas les liens externes)

---

## Conseils

✅ **Commencer avec MaxDepth = 2** pour tester rapidement

✅ **Augmenter progressivement** si vous voulez plus d'URLs

✅ **Vérifier le CSV** avant de tout ajouter dans Excel

✅ **Filtrer les URLs** - Toutes les pages ne sont pas pertinentes (ex: contact, mentions légales)

❌ **Ne pas mettre MaxDepth trop élevé** - Peut générer des milliers d'URLs

❌ **Attention aux sites très larges** - Commencer petit et voir

---

## Dépannage

### Problème: "Impossible d'exécuter le script"
**Cause**: Politique d'exécution PowerShell

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problème: Timeout sur certaines pages
**Normal** - Le script continue avec les autres pages

**Solution**: Augmenter le timeout dans le script (ligne 35: `-TimeoutSec 30`)

### Problème: Trop d'URLs générées
**Cause**: MaxDepth trop élevé

**Solution**: Réduire `-MaxDepth` ou filtrer le CSV manuellement

---

## Performance

**Estimation de temps** (dépend du site):
- MaxDepth 1: ~30 secondes, 10-50 URLs
- MaxDepth 2: ~2 minutes, 50-200 URLs
- MaxDepth 3: ~5-10 minutes, 200-1000 URLs
- MaxDepth 4+: 15+ minutes, 1000+ URLs

---

## Support

Pour plus d'informations:
1. Lire `AUTO_CLASSIFIER_README.md` pour la suite du workflow
2. Voir les exemples dans ce document
3. Contacter l'équipe technique Intelia
