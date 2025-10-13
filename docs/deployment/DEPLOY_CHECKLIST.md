# 🚀 Checklist de Déploiement - Migration Conversations + Messages

## ✅ Ce Qui Est Déjà Fait

- [x] Migration SQL complétée (conversations.id TEXT → UUID)
- [x] Table messages créée avec foreign keys
- [x] Vue user_questions_complete recréée
- [x] Backend stats_fast.py mis à jour
- [x] Format de réponse Q&A corrigé
- [x] Code commité et documenté
- [x] Base de données nettoyée (2 conversations, 4 messages)

**Commits récents:**
- `d49c750f` - docs: Add comprehensive migration documentation
- `d7e81dd5` - fix: Transform conversations to questions format for Q&A page ⭐
- `add603dd` - fix: Update stats_fast.py to use user_questions_complete view

---

## 🔄 Actions Restantes

### 1. Redémarrer le Backend

```bash
# Si Docker Compose
cd /path/to/intelia-expert
docker-compose restart backend

# Si service systemd
sudo systemctl restart intelia-backend

# Si Docker standalone
docker restart intelia-backend

# Si PM2
pm2 restart intelia-backend

# Si en développement local
# Arrêter (Ctrl+C) et relancer:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**⚠️ Important**: Le nouveau code dans `stats_fast.py` doit être chargé pour que le fix Q&A fonctionne.

---

### 2. Tester l'Application

#### A. Tester la Connexion
- [ ] Ouvrir https://expert.intelia.com
- [ ] Se connecter avec un compte utilisateur
- [ ] Vérifier qu'il n'y a pas d'erreur dans la console

#### B. Tester une Nouvelle Conversation
- [ ] Créer une nouvelle conversation
- [ ] Poser une question
- [ ] Vérifier que la réponse s'affiche
- [ ] Vérifier que la conversation apparaît dans le menu Historique

#### C. Tester la Page Dashboard
- [ ] Aller dans **Statistiques > Dashboard**
- [ ] Vérifier **"Questions ce mois"** (devrait afficher 3 après nouvelle conversation)
- [ ] Vérifier **"Utilisateurs plus actifs"** (devrait afficher votre utilisateur)
- [ ] Vérifier les graphiques

#### D. Tester la Page Q&A ⭐ CRITIQUE
- [ ] Aller dans **Statistiques > Q&A**
- [ ] **Vérifier qu'il n'y a PAS d'erreur** dans la console browser (F12)
- [ ] **Vérifier que les questions s'affichent** (devrait afficher 2 questions existantes + 1 nouvelle)
- [ ] Cliquer sur une question pour voir les détails
- [ ] Tester le feedback (👍/👎)

---

### 3. Vérifier les Logs

```bash
# Logs backend
docker logs -f backend
# ou
tail -f /var/log/intelia/backend.log

# Chercher ces lignes de succès:
# ✅ [QUESTIONS] Found X conversations
# ✅ [QUESTIONS] Returning X/X conversations
```

**Logs à surveiller:**
- ❌ Pas d'erreur `Cannot read properties of undefined (reading 'map')`
- ✅ Requêtes SQL qui fonctionnent
- ✅ Connexions PostgreSQL + Supabase réussies

---

### 4. Vérifier la Base de Données

```bash
# Se connecter à PostgreSQL
psql "postgresql://your_connection_string"

# Vérifier le nombre de conversations
SELECT COUNT(*) FROM conversations WHERE status = 'active';
-- Devrait afficher: 3 (2 anciennes + 1 nouvelle)

# Vérifier le nombre de messages
SELECT COUNT(*) FROM messages;
-- Devrait afficher: 6 (4 anciens + 2 nouveaux)

# Vérifier user_questions_complete
SELECT COUNT(*) FROM user_questions_complete;
-- Devrait afficher: 3

# Vérifier les foreign keys
SELECT COUNT(*) FROM messages m
JOIN conversations c ON m.conversation_id = c.id;
-- Devrait afficher: 6 (toutes les FK sont valides)
```

---

## 🔍 Troubleshooting

### Problème 1: Q&A Page Toujours Vide

**Symptômes:**
- La page Q&A ne montre aucune question
- Erreur console: `Cannot read properties of undefined (reading 'map')`

**Solution:**
1. Vérifier que le backend a bien redémarré
2. Vérifier dans les logs backend:
   ```
   ✅ stats_fast.py chargé - Architecture PostgreSQL + Supabase
   ```
3. Tester manuellement l'endpoint:
   ```bash
   # Avec authentification
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://expert.intelia.com/api/v1/stats-fast/questions
   ```
4. Vérifier que la réponse contient `"questions": [...]` et non `"conversations": [...]`

---

### Problème 2: Dashboard Affiche 0

**Symptômes:**
- Questions ce mois: 0
- Utilisateurs plus actifs: vide

**Solution:**
1. Vérifier dans PostgreSQL:
   ```sql
   SELECT * FROM user_questions_complete LIMIT 1;
   ```
2. Si la vue est vide, vérifier:
   ```sql
   SELECT COUNT(*) FROM conversations WHERE message_count > 0;
   SELECT COUNT(*) FROM messages;
   ```
3. Si les données existent mais la vue est vide, recréer la vue:
   ```bash
   \i backend/create_user_questions_view.sql
   ```

---

### Problème 3: Erreur Foreign Key

**Symptômes:**
- Erreur lors de création de conversation
- `foreign key constraint "messages_conversation_id_fkey" fails`

**Solution:**
1. Vérifier le type de conversations.id:
   ```sql
   SELECT data_type FROM information_schema.columns
   WHERE table_name = 'conversations' AND column_name = 'id';
   -- Devrait retourner: uuid
   ```
2. Si TEXT, relancer la migration:
   ```bash
   \i backend/fix_conversations_id_type.sql
   ```

---

## 📊 Critères de Succès

### Critères Obligatoires ✅

- [ ] Backend redémarre sans erreur
- [ ] Page Q&A affiche les questions (pas d'erreur JavaScript)
- [ ] Dashboard affiche statistiques correctes
- [ ] Création de nouvelle conversation fonctionne
- [ ] HistoryMenu affiche toutes les conversations
- [ ] Logs backend ne montrent pas d'erreurs

### Critères Optionnels ⭐

- [ ] Feedback sur questions fonctionne
- [ ] Temps de réponse < 500ms
- [ ] Cache fonctionne (vérifier les logs)
- [ ] Pagination Q&A fonctionne (si > 20 questions)

---

## 🎉 Validation Finale

Quand tous les critères obligatoires sont verts:

```bash
# Créer un tag de release
git tag -a v2.0.0-migration-complete -m "Migration conversations+messages completed"
git push origin v2.0.0-migration-complete

# Ou simplement noter dans un fichier
echo "Migration validée: $(date)" >> DEPLOYMENT_LOG.txt
```

---

## 📞 En Cas de Problème Critique

Si l'application est cassée et que vous devez revenir en arrière:

### Rollback Backend

```bash
# Revenir au commit avant migration
cd /path/to/intelia-expert/backend
git checkout b1eaff59  # Commit avant fix Q&A
docker-compose restart backend
```

### Rollback Database (⚠️ PERTE DE DONNÉES)

```sql
-- Supprimer messages (gardez les conversations)
DROP TABLE messages CASCADE;

-- Les conversations restent intactes
-- Mais l'ancienne architecture ne fonctionnera plus!
```

**Note**: Le rollback complet de la base n'est **pas recommandé** car:
1. La structure `conversations` a changé (UUID au lieu de TEXT)
2. Les anciennes colonnes `question`/`response` n'existent plus
3. Il faudrait restaurer un backup complet

**Mieux vaut:** Debugger et fixer le problème plutôt que faire un rollback.

---

## 🚀 C'est Parti!

1. ✅ Lire cette checklist
2. ✅ Redémarrer le backend
3. ✅ Tester l'application
4. ✅ Valider que tout fonctionne
5. 🎉 Célébrer!

**Bonne chance!** 🍀
