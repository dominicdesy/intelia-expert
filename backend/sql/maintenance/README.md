# Scripts de maintenance SQL

Scripts utilitaires pour la maintenance et vérification de la base de données.

## Scripts disponibles

### Vérification
- **verify_complete_structure.sql** - Vérifier structure complète de la DB
- **verify_migration_complete.sql** - Vérifier migration conversations/messages
- **verify_new_architecture.sql** - Vérifier nouvelle architecture
- **verify_digitalocean_tables.sql** - Vérifier tables DigitalOcean
- **check_conversations_structure.sql** - Vérifier structure conversations

### Cleanup
- **cleanup_old_tables.sql** - Supprimer anciennes tables obsolètes
- **cleanup_digitalocean_tables.sql** - Cleanup tables DigitalOcean
- **cleanup_digitalocean_final.sql** - Cleanup final DigitalOcean
- **cleanup_all_questions.sql** - Cleanup questions (attention: destructif!)

## Usage

### Vérification régulière
```bash
# Vérifier structure complète
psql -f verify_complete_structure.sql

# Vérifier migration spécifique
psql -f verify_migration_complete.sql
```

### Cleanup (⚠️ ATTENTION)
```bash
# TOUJOURS faire un backup avant cleanup
pg_dump dbname > backup_$(date +%Y%m%d).sql

# Puis exécuter le cleanup
psql -f cleanup_old_tables.sql
```

## Fréquence recommandée

### Hebdomadaire
- verify_complete_structure.sql

### Mensuel
- Cleanup des logs anciens (si applicable)
- Vérification des indexes

### Avant migration majeure
- Tous les scripts de vérification
- Backup complet

## Monitoring

Ces scripts peuvent être intégrés dans:
- Grafana alerts
- Cron jobs de monitoring
- CI/CD checks

## ⚠️ Avertissements

- **cleanup_all_questions.sql** est DESTRUCTIF - utiliser avec précaution
- Toujours tester en local d'abord
- Toujours faire un backup avant cleanup
- Vérifier l'impact sur les relations (foreign keys)
