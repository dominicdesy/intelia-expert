# Exécuter POC sur Digital Ocean (Optionnel)

Si tu veux mesurer la **vraie latence production** au lieu d'ajuster mentalement.

---

## Option 1 : SSH Direct (Si Accès SSH)

```bash
# SSH dans ton app
ssh root@your-digital-ocean-droplet

# Cloner repo (ou git pull si déjà présent)
cd /app
git pull origin main

# Aller dans POC
cd poc_realtime

# Copier variables d'environnement
cp ../llm/.env .env

# Installer dépendances
pip install -r requirements.txt

# Exécuter tests
python test_openai_realtime.py > results_q2.txt 2>&1
python test_weaviate_latency.py > results_q3.txt 2>&1

# Télécharger résultats
# Lire les fichiers results_*.txt
cat results_q2.txt
cat results_q3.txt
```

---

## Option 2 : Digital Ocean App Platform Job

Créer un job one-time :

```yaml
# .do/app.yaml (ajouter au fichier existant)

jobs:
  - name: poc-voice-realtime
    kind: POST_DEPLOY
    source_dir: /poc_realtime
    environment_slug: python
    github:
      repo: your-repo/intelia-expert
      branch: main
    envs:
      - key: WEAVIATE_URL
        scope: RUN_TIME
        value: ${WEAVIATE_URL}
      - key: WEAVIATE_API_KEY
        scope: RUN_TIME
        value: ${WEAVIATE_API_KEY}
      - key: OPENAI_API_KEY
        scope: RUN_TIME
        value: ${OPENAI_API_KEY}

    run_command: |
      pip install -r requirements.txt
      python test_openai_realtime.py | tee results_q2.txt
      python test_weaviate_latency.py | tee results_q3.txt

      # Upload results somewhere or log them
      cat results_q2.txt
      cat results_q3.txt
```

Déployer :
```bash
doctl apps create --spec .do/app.yaml
```

---

## Option 3 : Console Digital Ocean (Le Plus Simple)

1. Va sur Digital Ocean Console
2. Ouvre ton app → Console tab
3. Exécute :

```bash
cd /app/poc_realtime
pip install -r requirements.txt
python test_weaviate_latency.py
```

Copie/colle les résultats.

---

## Quand Utiliser ?

**Teste sur Digital Ocean si** :
- Test local Q3 montre P95 >250ms (vérifier si c'est ta connexion)
- Résultats locaux sont limites (750-850ms total)
- Tu veux être 100% sûr avant GO final

**Reste en local si** :
- Résultats locaux clairs (<700ms ou >900ms total)
- Tu acceptes ajustement mental -80ms Weaviate
- Tu veux itérer rapidement

---

## Comparaison Attendue

| Métrique | Local (ton PC) | Digital Ocean Toronto |
|----------|----------------|----------------------|
| OpenAI P95 | ~450ms | ~450ms (identique) |
| Weaviate P95 | ~250ms | **~170ms** (-80ms) |
| Total estimé | ~700ms | **~620ms** |

Différence : ~80ms (négligeable pour GO/NO-GO)
