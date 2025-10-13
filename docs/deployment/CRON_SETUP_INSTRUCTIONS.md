# Configuration du Cron Job pour l'Analyse Automatique Q&A

## Vue d'ensemble

Le système d'analyse de qualité Q&A s'exécute automatiquement **2 fois par jour**:
- **2h AM** - Analyse nocturne
- **2h PM** - Analyse diurne

Chaque exécution analyse **100 Q&A** en priorisant:
1. Q&A avec feedback négatif (👎)
2. Q&A avec faible confiance (<30%)
3. Q&A récentes non analysées

---

## Étape 1: Générer un secret pour le cron

Sur votre machine locale, générez un secret aléatoire sécurisé:

```bash
# Option 1: Avec OpenSSL
openssl rand -hex 32

# Option 2: Avec Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Exemple de résultat:
# 7f3d9a2b8c4e1f6a5d9c3b7e2a8f1c6d4b9e3a7f2c5d8b1e6a4f9c3d7b2e5a8f1c
```

**IMPORTANT**: Copiez ce secret, vous en aurez besoin pour les étapes suivantes.

---

## Étape 2: Configurer la variable d'environnement sur Digital Ocean

### Via l'interface Digital Ocean (App Platform)

1. Allez sur https://cloud.digitalocean.com/apps
2. Sélectionnez votre application backend (`intelia-expert-backend`)
3. Allez dans **Settings** → **App-Level Environment Variables**
4. Ajoutez une nouvelle variable:
   - **Name**: `CRON_SECRET`
   - **Value**: Le secret généré à l'étape 1
   - **Type**: Secret (encrypted)
   - **Scope**: All components
5. Cliquez sur **Save**
6. **Redéployez l'application** pour que la variable soit prise en compte

### Via doctl (CLI Digital Ocean)

```bash
# Installer doctl si pas déjà fait
brew install doctl  # macOS
# ou
snap install doctl  # Linux

# S'authentifier
doctl auth init

# Ajouter la variable d'environnement
doctl apps update <YOUR_APP_ID> --env "CRON_SECRET=<VOTRE_SECRET>"
```

---

## Étape 3: Tester l'endpoint manuellement

Avant de configurer le cron, testez que l'endpoint fonctionne:

```bash
# Remplacez <VOTRE_SECRET> par le secret généré
curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=<VOTRE_SECRET>" \
  -H "Content-Type: application/json"

# Réponse attendue:
{
  "status": "completed",
  "trigger": "cron_automatic",
  "analyzed_count": 100,
  "problematic_found": 15,
  "errors": 0,
  "timestamp": "2025-10-11T14:30:00.000000"
}
```

**Si vous obtenez une erreur 403**: Le secret est incorrect
**Si vous obtenez une erreur 500**: Vérifiez que `CRON_SECRET` est bien configuré dans DO
**Si vous obtenez 200 OK**: Tout fonctionne! Passez à l'étape suivante

---

## Étape 4: Configurer le Cron Job sur Digital Ocean

Digital Ocean App Platform **ne supporte pas directement les cron jobs intégrés**.

### Option A: Utiliser un service externe (RECOMMANDÉ)

#### 1. EasyCron (Gratuit jusqu'à 100 tâches/jour)

1. Créez un compte sur https://www.easycron.com
2. Ajoutez un nouveau cron job:
   - **URL**: `https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=<VOTRE_SECRET>`
   - **Method**: POST
   - **Schedule**:
     - Première tâche: `0 2 * * *` (2h AM tous les jours)
     - Deuxième tâche: `0 14 * * *` (2h PM tous les jours)
   - **Timezone**: America/Montreal (ou votre timezone)

#### 2. cron-job.org (Gratuit, illimité)

1. Créez un compte sur https://cron-job.org
2. Ajoutez un nouveau job:
   - **Title**: "QA Quality Analysis - 2h AM"
   - **URL**: `https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=<VOTRE_SECRET>`
   - **Schedule**: `0 2 * * *`
   - **Request method**: POST
   - **Enabled**: Yes
3. Répétez pour le job de 2h PM avec schedule `0 14 * * *`

#### 3. GitHub Actions (Gratuit pour repos publics/privés)

Créez `.github/workflows/qa-quality-cron.yml`:

```yaml
name: QA Quality Analysis Cron

on:
  schedule:
    - cron: '0 2 * * *'  # 2h AM UTC (ajuster selon timezone)
    - cron: '0 14 * * *' # 2h PM UTC

  # Permet aussi l'exécution manuelle
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger QA Analysis
        run: |
          curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=${{ secrets.CRON_SECRET }}" \
            -H "Content-Type: application/json"
```

Puis ajoutez le secret dans GitHub:
1. Settings → Secrets and variables → Actions
2. New repository secret:
   - Name: `CRON_SECRET`
   - Value: Votre secret généré

### Option B: Créer un service cron séparé sur Digital Ocean

Si vous préférez héberger le cron sur DO:

1. Créez un nouveau Droplet (machine virtuelle)
   - Image: Ubuntu 22.04
   - Plan: Basic $6/month (amplement suffisant)

2. SSH dans le Droplet:
```bash
ssh root@<DROPLET_IP>
```

3. Installez curl si nécessaire:
```bash
apt update && apt install -y curl
```

4. Configurez le cron:
```bash
# Ouvrir l'éditeur cron
crontab -e

# Ajouter ces 2 lignes (remplacez <VOTRE_SECRET>):
0 2 * * * curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=<VOTRE_SECRET>"
0 14 * * * curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=<VOTRE_SECRET>"
```

5. Vérifiez que le cron est actif:
```bash
crontab -l
```

---

## Étape 5: Vérifier que le cron fonctionne

### Via les logs Digital Ocean

1. Allez sur https://cloud.digitalocean.com/apps
2. Sélectionnez votre backend
3. Onglet **Runtime Logs**
4. Cherchez les messages:
```
[QA_QUALITY_CRON] Démarrage analyse automatique (cron trigger)
[QA_QUALITY_CRON] X Q&A sélectionnées pour analyse
[QA_QUALITY_CRON] Analyse automatique terminée: X analysées, Y anomalies détectées
```

### Via l'interface frontend

1. Connectez-vous en tant qu'admin
2. Allez dans **Statistics** → **Anomalies potentielles**
3. Vérifiez que de nouvelles analyses apparaissent chaque jour après 2h AM et 2h PM

---

## Dépannage

### Le cron ne se déclenche pas

1. **Vérifiez que le secret est correct**:
```bash
# Test manuel
curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=VOTRE_SECRET"
```

2. **Vérifiez les logs du service de cron** (EasyCron, cron-job.org, etc.)

3. **Vérifiez que CRON_SECRET est bien configuré sur DO**:
```bash
# Via doctl
doctl apps list
doctl apps spec get <APP_ID>
```

### Les analyses échouent

Vérifiez les logs backend pour:
- Erreurs de connexion OpenAI
- Erreurs de base de données
- Limites de rate OpenAI

### Coût OpenAI trop élevé

**Réduire le nombre d'analyses**:
- Modifiez `LIMIT 100` → `LIMIT 50` dans `qa_quality.py` ligne 609
- Ou désactivez un des 2 crons (garder seulement 2h AM)

---

## Résumé de la configuration

✅ **Secret généré** (32 caractères hex)
✅ **Variable CRON_SECRET** configurée sur Digital Ocean
✅ **Backend redéployé** avec la nouvelle variable
✅ **Endpoint testé** manuellement (réponse 200 OK)
✅ **Service de cron** configuré (EasyCron, GitHub Actions, ou Droplet)
✅ **Vérification** dans les logs et l'interface

**Fréquence**: 2x/jour (2h AM et 2h PM)
**Analyses par exécution**: 100 Q&A
**Coût estimé**: ~$0.20/jour (~$6/mois) en OpenAI API

---

## Commandes utiles

```bash
# Tester l'endpoint
curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=SECRET"

# Voir les logs en temps réel (Digital Ocean)
doctl apps logs <APP_ID> --type run --follow

# Désactiver temporairement le cron (EasyCron/cron-job.org)
# → Désactiver le job dans l'interface web

# Lancer une analyse manuelle depuis l'interface
# → Bouton "🔍 Analyser 50 Q&A" dans l'onglet Anomalies potentielles
```
