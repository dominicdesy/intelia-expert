# Scripts d'Upgrade Embeddings

Ce dossier contient les scripts pour upgrader le système d'embeddings vers **text-embedding-3-large**.

## Scripts disponibles

### 1. migrate_embeddings.py

**Objectif:** Migrer tous les documents vers le nouveau modèle d'embedding

**Usage:**
```bash
# Migration production
python scripts/migrate_embeddings.py

# Simulation (dry-run) pour estimer temps
python scripts/migrate_embeddings.py --dry-run

# Custom batch size
python scripts/migrate_embeddings.py --batch-size 200

# Dimensions complètes (3072 au lieu de 1536)
python scripts/migrate_embeddings.py --dimensions 3072

# Skip cache Redis
python scripts/migrate_embeddings.py --skip-cache
```

**Options:**
- `--dry-run`: Simulation sans modification (compte uniquement)
- `--batch-size N`: Nombre de documents par batch (défaut: 100)
- `--collection C`: Nom collection Weaviate (défaut: Documents)
- `--dimensions D`: Dimensions vecteurs (1536 ou 3072, défaut: 1536)
- `--skip-cache`: Ne pas utiliser le cache Redis

**Prérequis:**
- `OPENAI_API_KEY` configurée
- `WEAVIATE_URL` et `WEAVIATE_API_KEY` configurées
- `OPENAI_EMBEDDING_MODEL` défini dans .env

**Output attendu:**
```
🔧 Initialisation des clients...
✅ Client OpenAI initialisé
📊 Modèle d'embedding: text-embedding-3-large
📊 Dimensions cibles: 1536

📊 Documents trouvés: 10000
🚀 Début migration de 10000 documents...

📦 Batch 1 (documents 1-100/10000)...
   ✅ Success: 100, ❌ Failed: 0
   📊 Progress: 1.0% (100/10000) - Rate: 20.5 docs/s - ETA: 8.1 min

[...]

🎉 Migration terminée avec succès!
```

**Logs:**
- Fichier: `logs/migration_embeddings.log`
- Monitoring: `tail -f logs/migration_embeddings.log`

---

### 2. test_embedding_quality.py

**Objectif:** Tester et comparer la qualité des modèles d'embedding

**Usage:**
```bash
# Test complet (français + anglais, ada-002 vs 3-large)
python scripts/test_embedding_quality.py

# Test français uniquement
python scripts/test_embedding_quality.py --lang fr

# Comparer 3 modèles
python scripts/test_embedding_quality.py \
  --models "text-embedding-ada-002,text-embedding-3-small,text-embedding-3-large"

# Dimensions complètes
python scripts/test_embedding_quality.py --dimensions 3072
```

**Options:**
- `--models`: Liste de modèles à comparer (séparés par virgule)
- `--dimensions`: Dimensions pour text-embedding-3-* (1536 ou 3072)
- `--lang`: Langue de test (fr, en, both - défaut: both)

**Test cases:**
- **Français:** Poids Ross 308, température poulailler, vaccins
- **Anglais:** Ross 308 weight, temperature chicken house

**Output attendu:**
```
🧪 Testing embedding quality

======================================================================
📊 RÉSULTATS TEST QUALITÉ EMBEDDINGS
======================================================================

🌍 Langue: FR
------------------------------------------------------------------------------

Modèle                               Dimensions   Avg Sim      Min        Max
------------------------------------------------------------------------------
text-embedding-ada-002               default      0.8234       0.7654     0.8756
text-embedding-3-large               1536         0.8756       (+6.3%)    0.8312     0.9123

💡 RECOMMANDATION:
  ⭐ Meilleur modèle: text-embedding-3-large
     Amélioration vs text-embedding-ada-002: +6.3%
  ✅ Migration RECOMMANDÉE: amélioration significative
```

---

## Procédure d'Upgrade Complète

### Étape 1: Test baseline (optionnel)

```bash
# Tester le modèle actuel pour avoir une baseline
python scripts/test_embedding_quality.py --models text-embedding-ada-002
```

### Étape 2: Simulation migration

```bash
# Dry-run pour estimer temps et vérifier config
python scripts/migrate_embeddings.py --dry-run
```

### Étape 3: Backup configuration

```bash
# Backup .env actuel
cp .env .env.backup.$(date +%Y%m%d)
```

### Étape 4: Modifier configuration

```bash
# Éditer .env
nano .env

# Ajouter/Modifier:
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1536
```

### Étape 5: Migration production

```bash
# Lancer migration
python scripts/migrate_embeddings.py

# Monitoring temps réel (autre terminal)
tail -f logs/migration_embeddings.log
```

### Étape 6: Validation qualité

```bash
# Tester nouveau modèle
python scripts/test_embedding_quality.py

# Comparer avant/après
python scripts/test_embedding_quality.py \
  --models "text-embedding-ada-002,text-embedding-3-large"
```

### Étape 7: Rollback (si nécessaire)

```bash
# Restaurer configuration
cp .env.backup.YYYYMMDD .env

# Re-migrer vers ada-002 (optionnel)
export OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
python scripts/migrate_embeddings.py
```

---

## Troubleshooting

### Problème: Migration très lente

**Solution:**
```bash
# Augmenter batch size
python scripts/migrate_embeddings.py --batch-size 200

# Vérifier logs
tail -f logs/migration_embeddings.log
```

### Problème: Dimension mismatch error

**Solution:**
```bash
# Vérifier modèle configuré
grep OPENAI_EMBEDDING_MODEL .env

# Forcer détection
export FORCE_DIMENSION_DETECTION=true
python scripts/migrate_embeddings.py
```

### Problème: Qualité pas améliorée

**Solution:**
```bash
# Vérifier modèle réellement utilisé
python -c "
import os
print('Model:', os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'))
print('Dimensions:', os.getenv('EMBEDDING_DIMENSIONS', 'none'))
"

# Doit afficher: text-embedding-3-large
```

---

## Estimation Temps et Coûts

### Temps migration

| Nombre docs | Batch size | Temps estimé |
|-------------|-----------|--------------|
| 1,000 | 100 | ~1 minute |
| 10,000 | 100 | ~8 minutes |
| 100,000 | 100 | ~80 minutes |
| 100,000 | 200 | ~40 minutes |

**Note:** Rate moyen: ~20 docs/seconde

### Coût migration

| Nombre docs | Tokens (avg) | Coût |
|-------------|--------------|------|
| 1,000 | 50k | $0.0065 |
| 10,000 | 500k | $0.065 |
| 100,000 | 5M | $0.65 |

**Note:** Coût = tokens × $0.13 / 1M (text-embedding-3-large)

---

## Support

**Documentation:**
- Plan détaillé: `../EMBEDDINGS_UPGRADE_PLAN.md`
- Rapport final: `../EMBEDDINGS_UPGRADE_RAPPORT_FINAL.md`

**Logs:**
- Migration: `../logs/migration_embeddings.log`

**Contact:** Claude Code

---

**Dernière mise à jour:** 2025-10-05
**Version:** 1.0
