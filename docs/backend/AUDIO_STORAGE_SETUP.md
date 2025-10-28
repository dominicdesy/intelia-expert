# Configuration du stockage audio sur DigitalOcean Spaces

## Variables d'environnement requises

Pour activer le stockage permanent des fichiers audio (WhatsApp, voix temps réel), configurez ces variables dans votre fichier `.env`:

```bash
# DigitalOcean Spaces Configuration
DO_SPACES_KEY=your_access_key_here
DO_SPACES_SECRET=your_secret_key_here
DO_SPACES_BUCKET=intelia-expert-media
DO_SPACES_REGION=nyc3
DO_SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
```

## Obtenir les credentials DigitalOcean Spaces

1. **Se connecter à DigitalOcean**
   - Aller sur https://cloud.digitalocean.com/
   - Naviguer vers "Spaces" dans le menu latéral

2. **Créer un Space** (si pas déjà fait)
   - Cliquer sur "Create Space"
   - Choisir une région (ex: `nyc3`, `sfo3`, `ams3`, `fra1`)
   - Nommer le Space: `intelia-expert-media`
   - Sélectionner "Restrict File Listing" (recommandé)

3. **Générer les API Keys**
   - Aller dans "API" → "Spaces Keys"
   - Cliquer sur "Generate New Key"
   - Nommer la clé: `intelia-backend-audio`
   - **Important**: Copier immédiatement la Secret Key (elle ne sera plus visible)

4. **Configurer les variables**
   - `DO_SPACES_KEY`: Access Key (exemple: `DO00ABCDEFGHIJ1234567`)
   - `DO_SPACES_SECRET`: Secret Key (exemple: `abcd1234...`)
   - `DO_SPACES_BUCKET`: Nom de votre Space
   - `DO_SPACES_REGION`: Région choisie
   - `DO_SPACES_ENDPOINT`: `https://{region}.digitaloceanspaces.com`

## Structure de stockage

Les fichiers audio sont organisés comme suit:

```
audio/
├── whatsapp/
│   └── {user_id}/
│       └── {year}/
│           └── {month}/
│               └── {uuid}.ogg
└── voice_realtime/
    └── {user_id}/
        └── {year}/
            └── {month}/
                └── {uuid}.pcm16
```

## Exemple d'URL générée

```
https://nyc3.digitaloceanspaces.com/intelia-expert-media/audio/whatsapp/abc-123/2025/10/def-456.ogg
```

## Permissions requises

Le bucket doit avoir:
- **ACL public-read** pour les fichiers audio (accès lecture publique)
- **CORS configuré** si accès depuis frontend

Configuration CORS recommandée:
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://expert.intelia.com"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

## Taille et limites

- **Taille max par fichier**: 25 MB
- **Formats supportés**: OGG, MP3, M4A, WAV
- **Durée de rétention**: Permanente (pas d'expiration comme Twilio)

## Coûts estimés

DigitalOcean Spaces:
- **Stockage**: $5/mois pour 250 GB
- **Transfer sortant**: $0.01/GB après 1 TB gratuit/mois

Estimation pour 1000 messages audio/mois (moyenne 50 KB/audio):
- Stockage: ~50 MB/mois = négligeable
- Transfer: Dépend de l'écoute des audios

## Vérifier la configuration

Pour tester que la configuration fonctionne:

```python
from app.services.audio_storage_service import audio_storage_service

# Test de connexion
try:
    client = audio_storage_service._get_client()
    print("✅ DigitalOcean Spaces configuré correctement")
except Exception as e:
    print(f"❌ Erreur configuration: {e}")
```

## Troubleshooting

### Erreur "Configuration DigitalOcean Spaces manquante"
- Vérifier que `DO_SPACES_KEY` et `DO_SPACES_SECRET` sont définis
- Redémarrer le backend après modification du `.env`

### Erreur "Access Denied"
- Vérifier les permissions de la clé API
- Vérifier que le bucket existe et est accessible

### Erreur "Upload échoué"
- Vérifier la taille du fichier (< 25 MB)
- Vérifier l'espace disponible dans le Space
- Vérifier les logs backend pour détails

## Migration SQL requise

Pour activer le stockage des URLs audio en base de données:

```bash
psql -U postgres -d intelia_expert -f backend/sql/migrations/add_media_url_to_messages.sql
```

Ou via Docker:
```bash
docker exec -i intelia-postgres psql -U postgres -d intelia_expert < backend/sql/migrations/add_media_url_to_messages.sql
```
