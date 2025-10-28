# Vérification Déploiement CoT - Checklist

## Sur le serveur backend:

### 1. Vérifier que le code a été mis à jour
```bash
cd /path/to/intelia-expert/backend
git log --oneline -5
```

**Vous DEVEZ voir:**
```
3dc78711 fix: Move cot_parser to backend/app/utils for proper import
b2249700 feat: Backend CoT integration - parse and save to database
```

Si vous ne voyez PAS ces commits:
```bash
git pull origin main
```

### 2. Vérifier que le fichier cot_parser.py existe
```bash
ls -la app/utils/cot_parser.py
```

**Résultat attendu:**
```
-rw-r--r-- 1 user user 4567 Oct 19 01:XX app/utils/cot_parser.py
```

Si le fichier n'existe PAS → `git pull origin main`

### 3. Vérifier le contenu de conversation_service.py
```bash
grep -n "from app.utils.cot_parser import parse_cot_response" app/services/conversation_service.py
```

**Résultat attendu:**
```
17:from app.utils.cot_parser import parse_cot_response
```

Si vous voyez `from utils.cot_parser` (sans app.) → code pas à jour → `git pull`

### 4. Redémarrer le backend APRÈS git pull
```bash
# Docker
docker-compose down
docker-compose up -d backend

# OU PM2
pm2 restart backend

# OU Systemd
sudo systemctl restart intelia-backend
```

### 5. Vérifier les logs de démarrage
```bash
# Docker
docker-compose logs -f backend | head -100

# OU PM2
pm2 logs backend --lines 100

# Chercher les erreurs d'import
docker-compose logs backend | grep -i "error\|traceback\|import"
```

**Ce que vous devez voir:**
- Aucune erreur d'import
- Serveur démarre normalement
- "Application startup complete"

### 6. Tester l'import manuellement dans le conteneur
```bash
# Entrer dans le conteneur backend
docker-compose exec backend bash

# OU si PM2
cd /path/to/backend

# Tester l'import
python3 -c "from app.utils.cot_parser import parse_cot_response; print('Import OK')"
```

**Résultat attendu:**
```
Import OK
```

Si erreur → le fichier n'est pas là → `git pull` et redémarrer

---

## Test après déploiement:

### Question test:
```
Quel est le poids d'un Ross 308 mâle de 22 jours ?
```

### Logs backend DOIVENT montrer:
```
🧠 CoT detected in assistant message - thinking: X chars, analysis: Y chars
Message ajouté: [UUID] (conversation: [UUID], sequence: N, CoT: True)
```

### Base de données DOIT montrer:
```sql
SELECT
    LEFT(content, 100) as content,
    LEFT(cot_thinking, 50) as thinking,
    has_cot_structure
FROM messages
WHERE role = 'assistant'
ORDER BY created_at DESC
LIMIT 1;
```

**Résultat attendu:**
```
content: "Le poids d'un Ross 308 mâle de 22 jours est de 1131 grammes."
thinking: "L'utilisateur souhaite connaître le poids d'un poulet..."
has_cot_structure: true
```

**PAS:**
```
content: "<thinking>L'utilisateur souhaite...</thinking><analysis>..."
thinking: NULL
has_cot_structure: false
```

---

## Debugging si ça ne marche toujours pas:

### Vérifier la version Python du backend
```bash
docker-compose exec backend python3 --version
```

### Vérifier les permissions du fichier
```bash
ls -la app/utils/cot_parser.py
chmod 644 app/utils/cot_parser.py
```

### Vérifier le __init__.py existe
```bash
ls -la app/utils/__init__.py
```

### Forcer reconstruction du conteneur Docker
```bash
docker-compose down
docker-compose build backend --no-cache
docker-compose up -d backend
```

---

## Si RIEN ne fonctionne:

Envoyez-moi:
1. `git log --oneline -5` (depuis backend/)
2. `ls -la app/utils/`
3. `docker-compose logs backend | tail -100`
4. `grep "parse_cot_response" app/services/conversation_service.py`
