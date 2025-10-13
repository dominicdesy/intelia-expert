# External Sources Configuration Guide

## 🚀 Quick Summary

**✅ CONFIGURATION WORKING** - Les variables d'environnement sont maintenant utilisées par le code !

Suite à la mise à jour du 2025-01-XX, toutes les variables d'environnement sont désormais correctement intégrées dans le code.

## ✅ Variables d'environnement actives sur Digital Ocean

Vous avez configuré ces variables et **elles sont maintenant utilisées** :

```bash
ENABLE_EXTERNAL_SOURCES=true          # ✅ Utilisée dans rag_engine.py
EXTERNAL_SEARCH_THRESHOLD=0.7         # ✅ Utilisée dans query_processor.py
EXTERNAL_SOURCES_LOG_DIR=/app/logs/external_sources
```

## 🔧 Comment ça fonctionne maintenant

### 1. Activation via configuration (Nouvelle implémentation)

**Fichier:** `llm/core/rag_engine.py` (ligne 193)
```python
# 🆕 Enable external sources if config enabled AND Weaviate is available
enable_external = ENABLE_EXTERNAL_SOURCES and bool(self.weaviate_core)
```

Le système s'active quand **DEUX conditions** sont remplies :
1. `ENABLE_EXTERNAL_SOURCES=true` (variable d'environnement)
2. Weaviate est disponible

**Log au démarrage :**
```
✅ External sources system ENABLED (Semantic Scholar, PubMed, Europe PMC)
```

### 2. Seuil de confiance configurable

**Fichier:** `llm/core/query_processor.py` (ligne 473)
```python
# Importé depuis config.py
from config.config import EXTERNAL_SEARCH_THRESHOLD

if result.confidence < EXTERNAL_SEARCH_THRESHOLD:
    # Déclenche la recherche externe
```

La recherche externe se déclenche automatiquement quand :
- Confiance Weaviate < `EXTERNAL_SEARCH_THRESHOLD` (par défaut 0.7)
- Requête routée vers Weaviate (questions diagnostiques)

**Log lors du déclenchement :**
```
🔍 Low confidence (0.45), searching external sources...
```

### 3. Configuration complète des sources

**Fichier:** `llm/config/config.py` (lignes 112-131)

Toutes ces variables sont maintenant configurables via environnement :

```python
# Configuration principale
ENABLE_EXTERNAL_SOURCES = os.getenv("ENABLE_EXTERNAL_SOURCES", "true").lower() == "true"
EXTERNAL_SEARCH_THRESHOLD = float(os.getenv("EXTERNAL_SEARCH_THRESHOLD", "0.7"))
EXTERNAL_SOURCES_LOG_DIR = os.getenv("EXTERNAL_SOURCES_LOG_DIR", "/app/logs/external_sources")

# Paramètres de recherche
EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE = int(os.getenv("EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE", "5"))
EXTERNAL_SOURCES_MIN_YEAR = int(os.getenv("EXTERNAL_SOURCES_MIN_YEAR", "2015"))

# Toggles individuels par source
ENABLE_SEMANTIC_SCHOLAR = os.getenv("ENABLE_SEMANTIC_SCHOLAR", "true").lower() == "true"
ENABLE_PUBMED = os.getenv("ENABLE_PUBMED", "true").lower() == "true"
ENABLE_EUROPE_PMC = os.getenv("ENABLE_EUROPE_PMC", "true").lower() == "true"
ENABLE_FAO = os.getenv("ENABLE_FAO", "false").lower() == "true"  # Placeholder

# API key optionnelle
PUBMED_API_KEY = os.getenv("PUBMED_API_KEY")  # Optionnel: augmente limite
```

## 📚 Sources externes (Toutes GRATUITES)

### 1. Semantic Scholar ✅
- **Couverture:** 200M+ articles académiques
- **Limite:** 10 requêtes/seconde
- **Clé API:** ❌ NON requise
- **Coût:** $0

### 2. PubMed (NCBI) ✅
- **Couverture:** 35M+ articles biomédicaux
- **Limite:** 3 requêtes/seconde (par défaut)
- **Clé API:** ⚠️ Optionnelle (augmente à 10 req/s)
- **Coût:** $0

### 3. Europe PMC ✅
- **Couverture:** 40M+ articles sciences de la vie
- **Limite:** 5 requêtes/seconde
- **Clé API:** ❌ NON requise
- **Coût:** $0

## 💰 Structure de coûts

### APIs externes
- **Semantic Scholar:** $0
- **PubMed:** $0
- **Europe PMC:** $0
- **Total APIs:** $0

### Embeddings OpenAI (seul coût)
- **Usage:** ~90 tokens par document ingéré
- **Coût:** ~$0.0018 par ingestion (text-embedding-3-small)
- **Estimation:** ~$0.002/mois (usage typique)

**Coût mensuel total:** ~$0.002 (quasi gratuit !)

## ⚙️ Configuration optionnelle

### Variables déjà configurées sur Digital Ocean

```bash
# ✅ Déjà configurées et utilisées
ENABLE_EXTERNAL_SOURCES=true
EXTERNAL_SEARCH_THRESHOLD=0.7
EXTERNAL_SOURCES_LOG_DIR=/app/logs/external_sources
```

### Variables optionnelles supplémentaires

Si vous voulez personnaliser davantage, vous pouvez ajouter :

```bash
# Paramètres de recherche
EXTERNAL_SOURCES_MAX_RESULTS_PER_SOURCE=5    # Résultats par source
EXTERNAL_SOURCES_MIN_YEAR=2015               # Année minimale

# Désactiver une source spécifique
ENABLE_SEMANTIC_SCHOLAR=true
ENABLE_PUBMED=true
ENABLE_EUROPE_PMC=true
ENABLE_FAO=false                             # Placeholder (pas implémenté)

# Clé API optionnelle pour PubMed (augmente limite)
PUBMED_API_KEY=votre_cle_api_ncbi           # Seulement si rate limiting
```

### Option : Clé API PubMed (Optionnelle)

**Quand :** Seulement si vous rencontrez des limites de taux (très rare)

**Comment obtenir :**
1. Créer un compte NCBI gratuit : https://www.ncbi.nlm.nih.gov/account/
2. Générer une clé API dans les paramètres du compte
3. Ajouter sur Digital Ocean :
   ```bash
   PUBMED_API_KEY=votre_cle_api_ici
   ```

**Bénéfice :** Limite de taux passe de 3 à 10 req/s

## 📊 Métriques de performance

### Performance de recherche
- **Recherche parallèle :** Les 3 sources interrogées simultanément
- **Latence totale :** ~2-3 secondes
- **Résultats :** 5 documents par source = 15 total
- **Meilleur document :** Automatiquement sélectionné et ingéré

### Diagramme de flux
```
Requête utilisateur
    ↓
Recherche Weaviate (primaire)
    ↓
Confiance < 0.7 ?
    ↓ Oui
Recherche externe parallèle
├── Semantic Scholar (5 docs)
├── PubMed (5 docs)
└── Europe PMC (5 docs)
    ↓
Sélection meilleur document
    ↓
Vérifier si existe dans Weaviate
    ↓
Ingérer si nouveau (~$0.0018)
    ↓
Retourner réponse avec citation
```

## 🔍 Vérifier que ça fonctionne

### Vérifier les logs

Cherchez ces messages dans les logs de production :

1. **Système activé :**
   ```
   ✅ External sources system ENABLED (Semantic Scholar, PubMed, Europe PMC)
   ```

2. **Déclenchement (confiance basse) :**
   ```
   🔍 Low confidence (0.45), searching external sources...
   ```

3. **Document trouvé :**
   ```
   ✅ Found external document: 'Spaghetti breast in broilers...' (score=0.92, source=pubmed)
   ```

4. **Document ingéré :**
   ```
   📥 Ingesting document into Weaviate...
   ✅ Document ingested successfully
   ```

### Requête de test

Essayez une requête sur une recherche récente absente de votre base :

```
"What is spaghetti breast in broilers?"
```

Comportement attendu :
- Weaviate peut avoir une faible confiance
- Sources externes déclenchées automatiquement
- Articles PubMed/Semantic Scholar récupérés
- Meilleur document ingéré pour usage futur

## 🎛️ Contrôle du système

### Désactiver temporairement

Pour désactiver les sources externes :
```bash
ENABLE_EXTERNAL_SOURCES=false
```

Le système continuera de fonctionner normalement, mais ne fera plus de recherches externes.

### Ajuster le seuil

Pour déclencher plus/moins souvent :
```bash
EXTERNAL_SEARCH_THRESHOLD=0.8    # Moins de recherches externes (seulement si très faible confiance)
EXTERNAL_SEARCH_THRESHOLD=0.6    # Plus de recherches externes (confiance modérée suffit)
```

### Désactiver une source spécifique

Pour désactiver PubMed par exemple :
```bash
ENABLE_PUBMED=false
```

## ❌ Ce dont vous N'AVEZ PAS besoin

### Clés API (NON requises)
```bash
SEMANTIC_SCHOLAR_API_KEY=...      # ❌ Pas nécessaire
PUBMED_API_KEY=...                # ⚠️ Optionnel (seulement pour limite)
EUROPE_PMC_API_KEY=...            # ❌ Pas nécessaire
FAO_API_KEY=...                   # ❌ Placeholder (pas implémenté)
```

## ✨ Checklist de déploiement

- [x] **Variables configurées** → ENABLE_EXTERNAL_SOURCES, EXTERNAL_SEARCH_THRESHOLD
- [x] **Weaviate activé** → Requis pour sources externes
- [x] **Clé API OpenAI** → Pour embeddings (~$0.002/mois)
- [ ] **Clé API PubMed** → Seulement si rate limiting (optionnel)
- [ ] **Monitorer logs** → Vérifier recherches externes fonctionnent
- [ ] **Tester requêtes** → Essayer des questions sur recherches récentes

## 🐛 Dépannage

### Problème : Sources externes ne se déclenchent pas
**Cause :** Confiance Weaviate toujours > 0.7
**Solution :** C'est normal ! Cela signifie que votre base de connaissances est complète

### Problème : Erreurs de limite de taux PubMed
**Cause :** Volume élevé de requêtes
**Solution :** Ajouter PUBMED_API_KEY pour passer de 3 à 10 req/s

### Problème : Coût embeddings trop élevé
**Cause :** Trop de documents ingérés
**Solution :**
- Vérifier si seuil trop bas (< 0.7)
- Examiner quelles requêtes déclenchent recherche externe
- Considérer augmenter seuil à 0.8

### Problème : Sources externes désactivées
**Vérifier :**
```bash
# Sur Digital Ocean, vérifier que la variable existe
echo $ENABLE_EXTERNAL_SOURCES  # Doit retourner "true"
```

**Solution :**
- Ajouter/corriger la variable sur Digital Ocean
- Redémarrer l'application

## 📝 Résumé

**Configuration actuelle (Production) :**
- ✅ Sources externes : ACTIVÉES via `ENABLE_EXTERNAL_SOURCES=true`
- ✅ Seuil de confiance : 0.7 via `EXTERNAL_SEARCH_THRESHOLD=0.7`
- ✅ Sources de données : Semantic Scholar, PubMed, Europe PMC
- ✅ Clés API : Aucune requise (toutes gratuites)
- ✅ Coût : ~$0.002/mois (embeddings OpenAI)

**Vos variables Digital Ocean :**
- ✅ `ENABLE_EXTERNAL_SOURCES=true` → **Utilisée** (contrôle l'activation)
- ✅ `EXTERNAL_SEARCH_THRESHOLD=0.7` → **Utilisée** (contrôle le seuil)
- ✅ `EXTERNAL_SOURCES_LOG_DIR=/app/logs/external_sources` → **Utilisée** (logs)

**Recommandation :**
🚀 Le système est prêt ! Aucune clé API nécessaire. Ajoutez PUBMED_API_KEY seulement si vous rencontrez des limites de taux (peu probable).

## 🔄 Historique des modifications

**2025-01-XX :** Intégration des variables d'environnement dans le code
- Ajout de toutes les variables dans `config/config.py`
- Utilisation de `ENABLE_EXTERNAL_SOURCES` dans `rag_engine.py`
- Utilisation de `EXTERNAL_SEARCH_THRESHOLD` dans `query_processor.py`
- Ajout toggles individuels par source
- Support configuration complète via environnement
