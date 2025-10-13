# Configuration du Cron Job pour l'Analyse Automatique Q&A

## ✅ Statut: CONFIGURÉ ET OPÉRATIONNEL

Le système d'analyse de qualité Q&A s'exécute automatiquement **2 fois par jour**:
- **2h AM** - Analyse nocturne
- **2h PM** - Analyse diurne

Chaque exécution analyse **100 Q&A** en priorisant:
1. Q&A avec feedback négatif (👎)
2. Q&A avec faible confiance (<30%)
3. Q&A récentes non analysées

**Configuration actuelle:**
- ✅ Secret CRON_SECRET configuré sur Digital Ocean
- ✅ Endpoint `/api/v1/qa-quality/cron` opérationnel
- ✅ Cron jobs configurés sur cron-job.org
- ✅ Tests réussis: 4 Q&A analysées, 0 anomalies détectées

---

## Étape 1: Générer un secret pour le cron ✅ COMPLÉTÉ

Le secret a été généré et configuré:

```bash
# Commande utilisée:
openssl rand -hex 32

# Secret généré (déjà configuré):
64197543346761b96674437b1b4c19542fa13da76ec9a07ce19a53bfb30353d8
```

**⚠️ IMPORTANT**: Ce secret est configuré dans les variables d'environnement Digital Ocean. Ne pas le partager publiquement.

---

## Étape 2: Configurer la variable d'environnement sur Digital Ocean ✅ COMPLÉTÉ

Variable d'environnement configurée:

- **Name**: `CRON_SECRET`
- **Value**: `64197543346761b96674437b1b4c19542fa13da76ec9a07ce19a53bfb30353d8`
- **Type**: Secret (encrypted)
- **Scope**: All components
- **Statut**: ✅ Configuré et déployé

### Pour modifier à l'avenir (si nécessaire):

1. Allez sur https://cloud.digitalocean.com/apps
2. Sélectionnez votre application backend
3. Allez dans **Settings** → **App-Level Environment Variables**
4. Modifiez `CRON_SECRET`
5. **Redéployez l'application**

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

## Étape 3: Tester l'endpoint manuellement ✅ COMPLÉTÉ

Test effectué avec succès le 11 octobre 2025:

```bash
curl -X POST "https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=64197543346761b96674437b1b4c19542fa13da76ec9a07ce19a53bfb30353d8" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Résultat:
{
  "status": "completed",
  "trigger": "cron_automatic",
  "analyzed_count": 4,
  "problematic_found": 0,
  "errors": 0,
  "timestamp": "2025-10-11T19:46:38.819298"
}
```

**✅ Test réussi**: 4 Q&A analysées, 0 anomalies détectées, 0 erreurs

**Note importante**: L'User-Agent est requis pour bypasser Cloudflare qui bloque les requêtes sans User-Agent valide.

---

## Étape 4: Configurer le Cron Job sur Digital Ocean ✅ COMPLÉTÉ

**Service utilisé**: cron-job.org (Gratuit, illimité)

### Configuration actuelle:

**Job 1 - Analyse 2h AM:**
- **Title**: QA Analysis 2AM
- **URL**: `https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=64197543346761b96674437b1b4c19542fa13da76ec9a07ce19a53bfb30353d8`
- **Schedule**: Tous les jours à 02:00
- **Request method**: POST
- **Headers**: User-Agent: Mozilla/5.0
- **Statut**: ✅ Activé

**Job 2 - Analyse 2h PM:**
- **Title**: QA Analysis 2PM
- **URL**: `https://expert.intelia.com/api/v1/qa-quality/cron?cron_secret=64197543346761b96674437b1b4c19542fa13da76ec9a07ce19a53bfb30353d8`
- **Schedule**: Tous les jours à 14:00
- **Request method**: POST
- **Headers**: User-Agent: Mozilla/5.0
- **Statut**: ✅ Activé

### Pour modifier ou consulter les jobs:

1. Connectez-vous à https://cron-job.org
2. Dashboard → Voir les cronjobs configurés
3. Execution log → Vérifier l'historique des exécutions

### Alternatives non utilisées (pour référence):

#### Option B: EasyCron
- Gratuit jusqu'à 100 tâches/jour
- https://www.easycron.com

#### Option C: GitHub Actions
- Gratuit pour repos publics/privés
- Nécessite création de workflow `.github/workflows/qa-quality-cron.yml`

#### Option D: Droplet Digital Ocean dédié
- $6/mois
- Nécessite maintenance serveur

---

## Étape 5: Vérification et monitoring ✅ EN COURS

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

**Exemple de log réussi:**
```
[QA_QUALITY_CRON] Démarrage analyse automatique (cron trigger)
[QA_QUALITY_CRON] 4 Q&A sélectionnées pour analyse
[QA_QUALITY_CRON] Analyse automatique terminée: 4 analysées, 0 anomalies détectées, 0 erreurs
```

### Via l'interface frontend

1. Connectez-vous en tant qu'admin sur https://expert.intelia.com
2. Allez dans **Statistics** → **Anomalies potentielles**
3. Vérifiez que de nouvelles analyses apparaissent chaque jour après 2h AM et 2h PM
4. Les statistiques se mettent à jour automatiquement

### Via cron-job.org

1. Connectez-vous à https://cron-job.org
2. Dashboard → Execution log
3. Vérifiez les codes de réponse: **200 = Succès**
4. Consultez les détails de chaque exécution

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

## ✅ Résumé de la configuration complète

**Date de configuration**: 11 octobre 2025
**Statut**: ✅ OPÉRATIONNEL

### Checklist complète:

- ✅ **Secret généré**: 64 caractères hexadécimal (32 bytes)
- ✅ **Variable CRON_SECRET**: Configurée sur Digital Ocean (encrypted)
- ✅ **Backend déployé**: Tous les endpoints fonctionnels
- ✅ **Middleware auth**: Endpoint cron autorisé en public
- ✅ **Tests réussis**: 4 Q&A analysées, 0 anomalies, 0 erreurs
- ✅ **Cron jobs créés**: 2 jobs sur cron-job.org (2h AM et 2h PM)
- ✅ **Documentation**: Mise à jour et complète

### Configuration active:

- **Fréquence**: 2x/jour (02:00 et 14:00)
- **Analyses par exécution**: 100 Q&A maximum
- **Coût estimé**: ~$0.20/jour (~$6/mois) en OpenAI API
- **Service utilisé**: cron-job.org (gratuit, illimité)
- **Endpoint**: `https://expert.intelia.com/api/v1/qa-quality/cron`
- **Sécurité**: Protected par CRON_SECRET + Cloudflare

### Prochaines actions:

1. **Attendre la première exécution automatique** (demain à 2h AM)
2. **Vérifier les logs** sur cron-job.org et Digital Ocean
3. **Consulter l'interface** "Anomalies potentielles" pour voir les résultats
4. **Marquer les anomalies** comme revues ou faux positifs

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
