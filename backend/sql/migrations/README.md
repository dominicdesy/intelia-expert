# Migrations SQL

Scripts de migration de base de données appliqués au fur et à mesure de l'évolution du projet.

## Guide d'utilisation

### Appliquer une migration

1. Vérifier l'ordre des migrations (fichiers numérotés ou datés)
2. Tester en local d'abord
3. Backup de la base de données de production
4. Appliquer via Supabase SQL Editor
5. Vérifier avec les scripts de `../maintenance/verify_*.sql`

### Créer une nouvelle migration

1. Nommer selon la convention: `YYYY-MM-DD_description.sql` ou `add_feature_name.sql`
2. Inclure des checks `IF NOT EXISTS` pour idempotence
3. Ajouter un commentaire expliquant le but
4. Tester en local
5. Documenter dans ce README

## Migrations importantes

### Architecture
- **migration_to_conversations_messages.sql** - Migration vers nouvelle architecture conversations/messages
- **create_conversation_shares.sql** - Système de partage de conversations
- **create_qa_quality_checks.sql** - Système de quality checks Q&A

### Features utilisateur
- **add_user_profile_fields.sql** - Ajout champs profil utilisateur
- **add_voice_preferences.sql** - Préférences vocales
- **add_whatsapp_number_to_users.sql** - Support WhatsApp
- **add_facebook_profile_to_users.sql** - Extraction profil Facebook
- **add_ad_history_to_users.sql** - Historique publicités

### Médias et contenu
- **add_media_url_to_messages.sql** - Support médias dans messages
- **create_widget_tables.sql** - Tables pour widget intégré
- **create_satisfaction_surveys.sql** - Système d'enquêtes satisfaction

### Métriques
- **create_llm_metrics_history.sql** - Historique métriques LLM
- **add_user_analytics_to_metrics.sql** - Analytics utilisateur
- **create_infrastructure_metrics.sql** - Métriques infrastructure

### Cleanup
- **remove_unused_cot_analysis_column.sql** - Suppression colonnes inutilisées
- **drop_whatsapp_postgres_tables.sql** - Migration WhatsApp vers MongoDB

## Vérification

Après migration, utiliser:
```sql
-- Vérifier structure
\d+ table_name

-- Vérifier données
SELECT COUNT(*) FROM table_name;
```

Ou scripts de `../maintenance/verify_*.sql`

## Rollback

En cas de problème:
1. Restaurer le backup
2. Identifier la migration problématique
3. Créer un script de rollback
4. Documenter le problème
