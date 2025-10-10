# Configuration des Logs des Sources Externes sur Digital Ocean

## 📍 Emplacement des Logs

### Par Défaut
```
/app/logs/external_sources/
├── activity.jsonl              # Toutes les activités (1 JSON par ligne)
├── daily_stats.json           # Statistiques quotidiennes
└── monthly_stats.json         # Statistiques mensuelles
```

### ⚠️ Problème: Logs Éphémères
Sur Digital Ocean App Platform, le filesystem du container est **éphémère**. Les logs sont perdus à chaque redémarrage du container!

## 🔧 Solution 1: Volume Persistant Digital Ocean (Recommandé)

### Étape 1: Créer le Volume
Dans Digital Ocean App Platform:
1. Aller dans votre App → Settings → Storage
2. Cliquer "Add Volume"
3. Configuration:
   - Name: `llm-logs`
   - Mount Path: `/app/logs`
   - Size: 1GB (ajustez selon besoin)

### Étape 2: Vérifier la Configuration
Le volume sera automatiquement attaché au redémarrage. Vérifiez dans les logs:
```
✅ ExternalSourcesActivityLogger initialized: /app/logs/external_sources
```

### Coût
- ~$0.10/GB/mois
- 1GB devrait suffire pour des mois de logs

## 🔧 Solution 2: Variable d'Environnement Personnalisée

### Configuration
Dans Digital Ocean App Platform → Settings → Environment Variables:

```bash
EXTERNAL_SOURCES_LOG_DIR=/app/logs/external_sources
```

### Avantages
- Flexibilité: change l'emplacement sans rebuild
- Possibilité d'utiliser un volume custom

### Utilisation
Le logger détecte automatiquement la variable:
```python
log_dir = os.getenv("EXTERNAL_SOURCES_LOG_DIR", "/app/logs/external_sources")
```

## 🔧 Solution 3: Logging vers Service Cloud (Avancé)

Pour une solution enterprise, considérez:

### Option A: Digital Ocean Spaces (S3-compatible)
Modifier le logger pour écrire dans DO Spaces:

```python
import boto3

s3 = boto3.client(
    's3',
    region_name='nyc3',
    endpoint_url='https://nyc3.digitaloceanspaces.com',
    aws_access_key_id=os.getenv('DO_SPACES_KEY'),
    aws_secret_access_key=os.getenv('DO_SPACES_SECRET')
)

s3.put_object(
    Bucket='intelia-logs',
    Key=f'external_sources/{date}/activity.jsonl',
    Body=json.dumps(activity)
)
```

### Option B: Logging Centralisé (Papertrail, Datadog, etc.)
Configurer structlog pour envoyer vers un service tiers:

```python
import structlog
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
```

## 📊 Accéder aux Logs

### Via Digital Ocean Console
1. App → Runtime Logs
2. Filtrer par "external_search_activity"

### Via SSH (si volume persistant)
```bash
# Connexion au container
doctl apps logs <app-id> --follow

# Ou via console web
# App → Console → Attach Console

# Analyser les logs
cd /app/logs/external_sources
cat activity.jsonl | jq '.'
```

### Via Script d'Analyse
```bash
# SSH dans le container
docker exec -it <container> bash

# Analyser les 30 derniers jours
cd /app/llm
python scripts/analyze_external_sources.py 30

# Exporter en CSV
python scripts/analyze_external_sources.py --export csv /tmp/activity.csv

# Copier localement
docker cp <container>:/tmp/activity.csv ./
```

## 📈 Monitoring

### Logs Structurés (JSON)
Tous les événements sont loggés en JSON structuré:

```json
{
  "event": "external_search_activity",
  "request_id": "abc-123",
  "query": "What is spaghetti breast?",
  "language": "en",
  "weaviate_confidence": 0.45,
  "documents_found": 12,
  "document_ingested": true,
  "estimated_cost_usd": 0.0018,
  "timestamp": "2025-01-15T10:30:45Z"
}
```

### Console Logs (Human-Readable)
```
📥 EXTERNAL DOC INGESTED | Query: 'What is spaghetti breast?...' |
   Source: pubmed | Title: 'Spaghetti breast myopathy in broilers...' |
   Cost: $0.001800
```

### Alertes Recommandées
Configurer des alertes Digital Ocean pour:
- Coût quotidien > $0.10 (beaucoup d'ingestions)
- Temps de recherche > 5s (performance dégradée)
- Taux d'erreur > 5% (problèmes API)

## 🔍 Analyse des Logs

### Commandes Utiles

**Résumé 30 jours:**
```bash
python scripts/analyze_external_sources.py 30
```

**Top 10 queries:**
```bash
python scripts/analyze_external_sources.py --top-queries 10
```

**Analyse des coûts:**
```bash
python scripts/analyze_external_sources.py --cost 90
```

**Performance par source:**
```bash
python scripts/analyze_external_sources.py --sources
```

**Timeline des ingestions:**
```bash
python scripts/analyze_external_sources.py --timeline 14
```

**Export CSV:**
```bash
python scripts/analyze_external_sources.py --export csv activity.csv
```

## 💰 Estimation des Coûts

### Logs sur Volume Persistant
- **Volume 1GB:** ~$0.10/mois
- **Croissance:** ~10MB/mois pour usage moyen
- **Durée:** ~100 mois avant saturation (8+ ans)

### Logs sur Digital Ocean Spaces
- **Storage:** $0.02/GB/mois
- **Bandwidth:** $0.01/GB transfert
- **Total:** ~$0.03/mois pour usage moyen

### Recommandation
**Volume Persistant** pour simplicité et coût fixe bas.

## 🔒 Sécurité

### Logs Contiennent
- ✅ Queries utilisateur (peut contenir infos sensibles)
- ✅ Request IDs (traçabilité)
- ✅ Tenant IDs (identification utilisateur)
- ❌ Pas de tokens API
- ❌ Pas de credentials

### Bonnes Pratiques
1. **Limiter l'accès** au volume persistant
2. **Rotation des logs** après 90 jours (optionnel)
3. **Backup** mensuel si données critiques
4. **GDPR:** Anonymiser les queries si requis

## 🛠️ Troubleshooting

### Logs non créés
**Symptôme:** Pas de fichier activity.jsonl

**Solutions:**
1. Vérifier permissions volume: `/app/logs/` doit être writable
2. Vérifier logs container: chercher "ExternalSourcesActivityLogger initialized"
3. Vérifier espace disque: `df -h /app/logs`

### Volume plein
**Symptôme:** Erreur "No space left on device"

**Solutions:**
1. Augmenter taille volume dans DO Settings
2. Nettoyer vieux logs: `find /app/logs -mtime +90 -delete`
3. Compresser: `gzip /app/logs/external_sources/activity.jsonl`

### Performances dégradées
**Symptôme:** Écritures lentes

**Solutions:**
1. Vérifier taille fichier: `ls -lh activity.jsonl`
2. Rotation si > 100MB: `mv activity.jsonl activity_backup.jsonl`
3. Utiliser compression gzip pour archivage

## 📝 Configuration Recommandée

### Digital Ocean App Platform

**Variables d'Environnement:**
```bash
# Optionnel - change l'emplacement
EXTERNAL_SOURCES_LOG_DIR=/app/logs/external_sources
```

**Volume Persistant:**
```yaml
volumes:
  - name: llm-logs
    mount_path: /app/logs
    storage: 1GB
```

**Résultat:**
- ✅ Logs persistés entre redémarrages
- ✅ Coût fixe: $0.10/mois
- ✅ Analyse facile avec scripts
- ✅ Pas de config code nécessaire

---

**Dernière mise à jour:** Octobre 2025
