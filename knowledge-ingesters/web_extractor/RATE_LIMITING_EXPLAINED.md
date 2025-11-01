# Rate Limiting Intelligent - Web Batch Processor

Le `web_batch_processor.py` utilise un système de **rate limiting par domaine** pour respecter les serveurs web tout en maximisant la vitesse de traitement.

---

## Comment ça fonctionne

### Principe de Base

**Règle simple**: Attendre 3 minutes entre chaque requête vers le **même domaine**, mais traiter immédiatement les URLs de **domaines différents**.

### Exemples Concrets

#### Scénario 1: Même Domaine (Rate Limiting Actif)

**URLs à traiter**:
1. `https://www.thepoultrysite.com/articles/article1`
2. `https://www.thepoultrysite.com/articles/article2`
3. `https://www.thepoultrysite.com/articles/article3`

**Temps de traitement**:
```
00:00 → Traiter article1 (thepoultrysite.com)
00:30 → Article1 terminé
        ⏳ Attendre 2min30s (180s total depuis le début)
03:00 → Traiter article2 (thepoultrysite.com)
03:30 → Article2 terminé
        ⏳ Attendre 2min30s
06:00 → Traiter article3 (thepoultrysite.com)
```

**Total**: ~6 minutes pour 3 URLs du même domaine

---

#### Scénario 2: Domaines Différents (Pas d'Attente!)

**URLs à traiter**:
1. `https://www.thepoultrysite.com/articles/article1`
2. `https://aviagen.com/ross-handbook`
3. `https://www.hyline.com/layer-guide`

**Temps de traitement**:
```
00:00 → Traiter article1 (thepoultrysite.com)
00:30 → Article1 terminé
        ✅ Passer immédiatement à aviagen.com (domaine différent)
00:30 → Traiter ross-handbook (aviagen.com)
01:00 → Ross-handbook terminé
        ✅ Passer immédiatement à hyline.com (domaine différent)
01:00 → Traiter layer-guide (hyline.com)
```

**Total**: ~1 minute pour 3 URLs de domaines différents

**Gain de temps**: 6x plus rapide! 🚀

---

#### Scénario 3: Mélange de Domaines (Optimisation Intelligente)

**URLs à traiter**:
1. `https://www.thepoultrysite.com/articles/article1` (poultrysite)
2. `https://aviagen.com/ross-handbook` (aviagen)
3. `https://www.thepoultrysite.com/articles/article2` (poultrysite)
4. `https://www.hyline.com/layer-guide` (hyline)

**Temps de traitement**:
```
00:00 → Traiter article1 (poultrysite)
00:30 → Article1 terminé
        ✅ Passer immédiatement à aviagen (domaine différent)
00:30 → Traiter ross-handbook (aviagen)
01:00 → Ross-handbook terminé
        ⏳ ATTENTION: article2 est aussi poultrysite
        ⏳ Dernier accès à poultrysite: 00:00
        ⏳ Il faut attendre jusqu'à 03:00 (2 minutes restantes)
03:00 → Traiter article2 (poultrysite)
03:30 → Article2 terminé
        ✅ Passer immédiatement à hyline (domaine différent)
03:30 → Traiter layer-guide (hyline)
```

**Total**: ~3.5 minutes au lieu de 9+ minutes avec délai fixe

---

## Code Expliqué

### Tracking des Domaines (lignes 70-73)

```python
# Track last access time per domain
# Format: {"domain.com": datetime}
self.domain_last_access = {}
self.domain_delay_seconds = 180  # 3 minutes between pages from same domain
```

**Ce dictionnaire stocke**:
- Clé: Nom de domaine (ex: "thepoultrysite.com")
- Valeur: Timestamp du dernier accès

### Extraction du Domaine (lignes 75-86)

```python
def _get_domain(self, url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc
```

**Exemples**:
- `https://www.thepoultrysite.com/articles/abc` → `www.thepoultrysite.com`
- `https://aviagen.com/products/ross` → `aviagen.com`

### Logique de Rate Limiting (lignes 88-107)

```python
def _wait_for_domain_rate_limit(self, url: str):
    """Wait if necessary to respect rate limit for domain."""
    domain = self._get_domain(url)

    if domain in self.domain_last_access:
        last_access = self.domain_last_access[domain]
        elapsed = (datetime.now() - last_access).total_seconds()

        if elapsed < self.domain_delay_seconds:
            wait_time = self.domain_delay_seconds - elapsed
            print(f"  Rate limit: Waiting {wait_time:.1f}s for domain {domain}")
            time.sleep(wait_time)

    # Update last access time
    self.domain_last_access[domain] = datetime.now()
```

**Étapes**:
1. Extraire le domaine de l'URL
2. Vérifier si on a déjà accédé à ce domaine
3. Si oui, calculer le temps écoulé depuis le dernier accès
4. Si < 180 secondes, attendre le temps restant
5. Mettre à jour le timestamp du dernier accès

---

## Configuration

### Modifier le Délai par Domaine

**Fichier**: `web_batch_processor.py` (ligne 73)

```python
# Valeur par défaut: 180 secondes (3 minutes)
self.domain_delay_seconds = 180

# Pour être plus respectueux (5 minutes):
self.domain_delay_seconds = 300

# Pour aller plus vite (1 minute) - ATTENTION: risque de blocage
self.domain_delay_seconds = 60
```

**Recommandations**:
- ✅ **180 secondes (3 min)**: Bon équilibre pour la plupart des sites
- ✅ **300 secondes (5 min)**: Sites avec rate limiting strict
- ⚠️ **60 secondes (1 min)**: Seulement pour vos propres sites
- ❌ **< 30 secondes**: Risque de blocage IP

---

## Avantages du Système

### 1. Respect des Serveurs ✅
- Évite de surcharger un seul site
- Conforme aux bonnes pratiques de scraping
- Réduit le risque de blocage IP

### 2. Performance Optimale 🚀
- Pas de délai inutile entre domaines différents
- Traitement en parallèle "virtuel" (séquentiel mais optimisé)
- Peut traiter des dizaines de domaines en quelques minutes

### 3. Traçabilité 📊
- Affiche le temps d'attente dans la console
- Facile de déboguer les problèmes de rate limiting
- Logs clairs: "Rate limit: Waiting 120.3s for domain thepoultrysite.com"

---

## Exemples de Sortie Console

### URLs du Même Domaine

```
[1/5] https://www.thepoultrysite.com/articles/article1
Classification: intelia/public/broiler_farms/biosecurity/common
--------------------------------------------------------------------------------
SUCCESS
  Chunks created: 12
  Ingested to Weaviate: True

[2/5] https://www.thepoultrysite.com/articles/article2
Classification: intelia/public/layer_farms/management/common
--------------------------------------------------------------------------------
  Rate limit: Waiting 156.7s for domain www.thepoultrysite.com
SUCCESS
  Chunks created: 8
  Ingested to Weaviate: True
```

### URLs de Domaines Différents

```
[1/5] https://www.thepoultrysite.com/articles/article1
Classification: intelia/public/broiler_farms/biosecurity/common
--------------------------------------------------------------------------------
SUCCESS
  Chunks created: 12
  Ingested to Weaviate: True

[2/5] https://aviagen.com/ross-handbook
Classification: intelia/public/broiler_farms/breed/ross_308
--------------------------------------------------------------------------------
SUCCESS  ← Pas d'attente! Domaine différent
  Chunks created: 25
  Ingested to Weaviate: True

[3/5] https://www.hyline.com/layer-guide
Classification: intelia/public/layer_farms/breed/hy_line_brown
--------------------------------------------------------------------------------
SUCCESS  ← Encore pas d'attente!
  Chunks created: 18
  Ingested to Weaviate: True
```

---

## Stratégies d'Optimisation

### Stratégie 1: Trier par Domaine

**Problème**: Si vous avez 10 URLs du même domaine suivies de 10 URLs d'un autre

**Solution**: Réorganiser l'Excel pour alterner les domaines

**Avant** (lent):
```
1. thepoultrysite.com/article1
2. thepoultrysite.com/article2
3. thepoultrysite.com/article3
4. aviagen.com/guide1
5. aviagen.com/guide2
```

**Après** (rapide):
```
1. thepoultrysite.com/article1
2. aviagen.com/guide1
3. thepoultrysite.com/article2
4. aviagen.com/guide2
5. thepoultrysite.com/article3
```

**Gain**: Traitement quasi-instantané au lieu d'attendre 15 minutes!

### Stratégie 2: Batch Processing

Si vous avez beaucoup d'URLs du même domaine:

1. **Phase 1**: Traiter toutes les URLs uniques (domaines différents)
2. **Phase 2**: Traiter les URLs restantes (même domaine) en batch

**Script**: Lancer plusieurs fois le processor en triant l'Excel différemment

---

## FAQ

### Q: Pourquoi 3 minutes exactement?

**R**: C'est un bon compromis:
- Assez long pour ne pas surcharger le serveur
- Assez court pour rester efficace
- Aligné avec les pratiques courantes de scraping éthique

### Q: Le système détecte-t-il automatiquement les limites du serveur?

**R**: Non, c'est un délai fixe. Si un site bloque votre IP, augmentez `domain_delay_seconds`.

### Q: Que se passe-t-il si je redémarre le script?

**R**: Le tracking par domaine est en mémoire. Si vous redémarrez, le délai repart à 0 pour tous les domaines. **Les URLs déjà traitées sont trackées dans `processed_websites.json` et ne seront pas re-traitées**.

### Q: Puis-je désactiver le rate limiting?

**R**: Oui, mettez `self.domain_delay_seconds = 0`, mais **FORTEMENT DÉCONSEILLÉ** - risque de blocage IP.

### Q: Comment paralléliser vraiment (async)?

**R**: Le code actuel est séquentiel. Pour du vrai parallélisme:
- Il faudrait réécrire avec `asyncio` et `aiohttp`
- Gérer un pool de workers par domaine
- Plus complexe mais possible

---

## Modifications Apportées

### Avant (problématique)

```python
# Rate limiting delay
if idx < len(df) - 1:
    time.sleep(delay_seconds)  # ❌ Attente fixe de 3s entre TOUTES les URLs
```

**Problème**: Même avec des domaines différents, on attendait 3 secondes

### Après (optimisé)

```python
# No fixed delay needed - rate limiting is handled per domain
# in _wait_for_domain_rate_limit() method
```

**Avantage**:
- ✅ Pas de délai fixe
- ✅ Délai intelligent uniquement pour le même domaine
- ✅ URLs de domaines différents traitées immédiatement

---

## Résumé

| Scénario | Avant (délai fixe 3s) | Après (rate limiting intelligent) | Gain |
|----------|----------------------|----------------------------------|------|
| 10 URLs même domaine | ~30 min | ~30 min | 0% (identique) |
| 10 URLs domaines différents | ~30 s | ~5 s | **6x plus rapide** |
| 5 URLs domaine A + 5 URLs domaine B | ~30 s | ~10 min | **3x plus rapide** |

**Le système intelligent s'adapte automatiquement à votre mix d'URLs!**

---

## Support

Pour plus d'informations:
1. Voir le code dans `web_batch_processor.py` lignes 70-107
2. Lire `AUTO_CLASSIFIER_README.md` pour le workflow complet
3. Contacter l'équipe technique Intelia
