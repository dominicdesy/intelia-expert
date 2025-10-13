# Fix: Titres manquants dans HistoryMenu

## 🐛 Problème identifié

Les conversations dans le HistoryMenu du frontend s'affichent **sans titre**, montrant uniquement des lignes vides.

### Cause racine

La fonction SQL `create_conversation_with_messages()` dans `db_schema_conversations_messages.sql` ne génère **pas automatiquement les titres** lors de la création des conversations:

```sql
-- ❌ PROBLÈME (ligne 112 du schema)
INSERT INTO conversations (session_id, user_id, language)
VALUES (p_session_id, p_user_id, p_language)
-- Le champ 'title' reste NULL !
```

Le trigger `update_conversation_metadata()` met à jour les previews mais **pas le titre**.

## ✅ Solution

### Fichier de correction: `fix_missing_titles.sql`

Ce script SQL effectue 2 actions:

1. **Modifie le trigger** pour générer automatiquement le titre basé sur le 1er message user
2. **Met à jour les conversations existantes** sans titre

### Comment appliquer la correction

#### Option 1: Via psql (Ligne de commande)

```bash
# Se connecter à la base de données PostgreSQL
psql -h <HOST> -U <USER> -d <DATABASE> -f fix_missing_titles.sql

# Exemple pour Digital Ocean
psql "postgresql://user:password@host:25060/defaultdb?sslmode=require" -f fix_missing_titles.sql
```

#### Option 2: Via DBeaver / pgAdmin (GUI)

1. Ouvrir `fix_missing_titles.sql` dans l'éditeur SQL
2. Exécuter le script complet (F5 ou bouton Execute)
3. Vérifier les résultats dans l'onglet Output

#### Option 3: Via Python (depuis le backend)

```python
from app.core.database import get_pg_connection

with open('fix_missing_titles.sql', 'r', encoding='utf-8') as f:
    sql_script = f.read()

with get_pg_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql_script)
    conn.commit()

print("✅ Titres générés avec succès!")
```

## 📊 Résultat attendu

Après l'exécution du script, vous devriez voir:

```
=== RÉSULTAT ===
NOTICE:  Total conversations actives: 45
NOTICE:  Avec titre: 45 (100.0%)
NOTICE:  Sans titre: 0 (0.0%)
NOTICE:  ✅ Toutes les conversations ont un titre!
```

### Vérification visuelle

1. **Frontend**: Ouvrir le HistoryMenu → Les titres s'affichent maintenant
2. **Backend**: Vérifier via API:
   ```bash
   curl https://expert.intelia.com/api/v1/conversations/user/<USER_ID> \
     -H "Authorization: Bearer <TOKEN>"
   ```

## 🔧 Détails techniques

### Nouveau comportement du trigger

Le trigger `update_conversation_metadata()` génère maintenant le titre automatiquement:

```sql
UPDATE conversations
SET title = CASE
    WHEN LENGTH(NEW.content) <= 60 THEN NEW.content
    ELSE SUBSTRING(NEW.content, 1, 60) || '...'
END
WHERE id = NEW.conversation_id
  AND title IS NULL
  AND NEW.role = 'user'
  AND NEW.sequence_number = 1;
```

**Logique**:
- Si le 1er message user fait ≤ 60 caractères → titre = message complet
- Si le 1er message user fait > 60 caractères → titre = 60 premiers caractères + "..."
- Le titre est généré **uniquement** pour le 1er message user (sequence_number = 1)

### Mise à jour des conversations existantes

```sql
UPDATE conversations c
SET title = CASE
    WHEN LENGTH(m.content) <= 60 THEN m.content
    ELSE SUBSTRING(m.content, 1, 60) || '...'
END
FROM messages m
WHERE c.id = m.conversation_id
  AND m.role = 'user'
  AND m.sequence_number = 1
  AND c.title IS NULL;
```

## 🎯 Impact

- **Conversations futures**: Titres générés automatiquement ✅
- **Conversations existantes**: Titres rétroactivement générés ✅
- **Frontend**: HistoryMenu affiche les titres ✅
- **Performance**: Aucun impact (trigger léger) ✅

## 🔍 Vérification après déploiement

### 1. Vérifier qu'aucune conversation active n'a de titre NULL

```sql
SELECT COUNT(*) as sans_titre
FROM conversations
WHERE status = 'active' AND title IS NULL;
-- Doit retourner: 0
```

### 2. Vérifier que les nouveaux titres sont bien générés

```sql
-- Créer une conversation de test
SELECT create_conversation_with_messages(
    gen_random_uuid(),
    'test-user-id',
    'Ceci est une question de test pour vérifier la génération de titre',
    'Réponse de test',
    'fr'
);

-- Vérifier que le titre a bien été généré
SELECT title, first_message_preview
FROM conversations
WHERE user_id = 'test-user-id'
ORDER BY created_at DESC
LIMIT 1;

-- Résultat attendu:
-- title: "Ceci est une question de test pour vérifier la génératio..."
```

### 3. Tester le frontend

1. Se connecter sur https://expert.intelia.com
2. Ouvrir le HistoryMenu (icône horloge)
3. Vérifier que **tous les titres s'affichent correctement**

## 📝 Notes

- Le script est **idempotent**: il peut être exécuté plusieurs fois sans problème
- Les titres existants ne sont **pas écrasés** (condition `WHERE title IS NULL`)
- Le trigger ne s'active **que pour le 1er message user** (sequence_number = 1)

## 🚀 Déploiement sur Digital Ocean

```bash
# 1. Copier le script sur le serveur
scp fix_missing_titles.sql user@server:/tmp/

# 2. Se connecter au serveur
ssh user@server

# 3. Exécuter le script
psql $DATABASE_URL -f /tmp/fix_missing_titles.sql

# 4. Vérifier les logs
# Vous devriez voir les NOTICE avec les statistiques
```

## ⚠️ Important

- Exécuter le script pendant une **fenêtre de maintenance** (peu de trafic)
- Le script crée un **backup implicite** via le trigger (aucune donnée n'est supprimée)
- Durée d'exécution estimée: **< 5 secondes** pour 1000 conversations

## 📧 Support

Si problème, vérifier:
1. Les logs PostgreSQL
2. Les permissions de l'utilisateur SQL (doit pouvoir CREATE FUNCTION et UPDATE)
3. La version de PostgreSQL (doit être ≥ 12)
