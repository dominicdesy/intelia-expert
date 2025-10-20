# Configuration des Mises à Jour Automatiques des Taux de Change

Ce document explique comment configurer la mise à jour automatique quotidienne des taux de change depuis l'API Frankfurter (Banque Centrale Européenne).

## Architecture

Le système récupère les taux de change en temps réel depuis l'API Frankfurter et met à jour la table `stripe_currency_rates` dans PostgreSQL.

**Source des données :** https://api.frankfurter.app (basé sur les données de la BCE)
**Fréquence recommandée :** Quotidienne (les taux sont mis à jour une fois par jour ouvrable)

---

## Option 1: Mise à Jour Manuelle via l'API

### Endpoint API

```
POST /api/v1/billing/admin/currency-rates/update
```

### Authentification

Nécessite un token JWT de super admin.

### Exemple avec curl

```bash
curl -X POST "https://expert.intelia.com/api/v1/billing/admin/currency-rates/update" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Réponse

```json
{
  "success": true,
  "message": "Taux de change mis à jour avec succès",
  "rates_date": "2025-10-19",
  "currencies_fetched": 31,
  "updated": 31,
  "new": 0,
  "failed": 0,
  "timestamp": "2025-10-19T14:30:00"
}
```

---

## Option 2: Script Standalone (Recommandé pour CRON)

### Script Python

Le script se trouve à : `backend/scripts/update_currency_rates.py`

### Exécution manuelle

```bash
cd /path/to/intelia-expert/backend
python scripts/update_currency_rates.py
```

### Variables d'environnement requises

Le script nécessite la variable `DATABASE_URL` :

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/intelia"
python scripts/update_currency_rates.py
```

---

## Option 3: CRON Job Quotidien (Production)

### Configuration Linux/Unix

Éditez la crontab :

```bash
crontab -e
```

Ajoutez la ligne suivante pour exécuter le script chaque jour à 2h00 du matin :

```bash
0 2 * * * cd /path/to/intelia-expert/backend && /path/to/python scripts/update_currency_rates.py >> logs/currency_updates.log 2>&1
```

### Exemple complet avec environnement virtuel

```bash
0 2 * * * cd /home/app/intelia-expert/backend && source venv/bin/activate && DATABASE_URL="postgresql://user:password@localhost:5432/intelia" python scripts/update_currency_rates.py >> logs/currency_updates.log 2>&1
```

### Configuration Windows (Task Scheduler)

1. Ouvrir le "Planificateur de tâches" (Task Scheduler)
2. Créer une nouvelle tâche
3. **Déclencheur :** Quotidien à 2h00
4. **Action :** Démarrer un programme
   - Programme : `C:\Python\python.exe`
   - Arguments : `scripts\update_currency_rates.py`
   - Répertoire : `C:\intelia_gpt\intelia-expert\backend`
5. **Conditions :** Décocher "Démarrer uniquement si connecté"

### Configuration Docker

Si vous utilisez Docker, ajoutez le CRON job dans votre conteneur backend :

**Dockerfile** (ajouter) :
```dockerfile
# Install cron
RUN apt-get update && apt-get install -y cron

# Add crontab file
COPY crontab /etc/cron.d/currency-updates
RUN chmod 0644 /etc/cron.d/currency-updates
RUN crontab /etc/cron.d/currency-updates
```

**crontab** (créer ce fichier) :
```
0 2 * * * cd /app && python scripts/update_currency_rates.py >> /var/log/currency_updates.log 2>&1
```

---

## Vérification et Monitoring

### Consulter les logs

Les logs contiennent des informations détaillées sur chaque mise à jour :

```bash
tail -f logs/currency_updates.log
```

### Consulter les taux dans la base de données

```sql
SELECT
    currency_code,
    currency_name,
    rate_to_usd,
    last_updated
FROM stripe_currency_rates
ORDER BY last_updated DESC
LIMIT 10;
```

### API de consultation

Récupérer tous les taux actuels :

```bash
curl -X GET "https://expert.intelia.com/api/v1/billing/admin/currency-rates" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Gestion des Erreurs

### Que se passe-t-il si l'API Frankfurter est indisponible ?

Le script/endpoint retournera une erreur mais ne modifiera pas les taux existants. Les prix continueront de fonctionner avec les derniers taux connus.

### Notification d'échec

Pour recevoir des notifications en cas d'échec du CRON job :

```bash
0 2 * * * cd /path/to/backend && python scripts/update_currency_rates.py || echo "Currency rates update failed on $(date)" | mail -s "Currency Update Failed" admin@intelia.com
```

---

## Tests

### Tester le script

```bash
# Test avec verbose logging
python scripts/update_currency_rates.py
```

### Tester l'endpoint API

```bash
curl -X POST "http://localhost:8000/api/v1/billing/admin/currency-rates/update" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

---

## Notes Importantes

1. **Fréquence :** Les taux de Frankfurter sont mis à jour une fois par jour ouvrable (du lundi au vendredi)
2. **Weekend :** Le script fonctionnera le weekend mais retournera les taux du vendredi
3. **Performance :** La mise à jour prend ~2-3 secondes pour 31 devises
4. **Impact :** Les nouveaux taux sont immédiatement utilisés pour calculer les prix marketing
5. **Sécurité :** Seuls les super admins peuvent déclencher les mises à jour manuelles

---

## Support

En cas de problème :

1. Vérifier les logs : `logs/currency_updates.log`
2. Vérifier la connexion à l'API : `curl https://api.frankfurter.app/latest?from=USD`
3. Vérifier la base de données : `SELECT COUNT(*) FROM stripe_currency_rates;`
4. Vérifier les variables d'environnement : `echo $DATABASE_URL`
