# Fix pour le Déploiement DigitalOcean App Platform

## Problème

L'erreur `404 Image tag or digest not found` survient car l'App Platform sur DigitalOcean est configurée pour utiliser un tag d'image spécifique (probablement un SHA de commit comme `main-abc123`) qui n'existe plus après chaque nouveau build.

## Solution: Configurer l'App Platform pour utiliser le tag `latest`

### Option 1: Via l'interface DigitalOcean (Recommandé)

1. **Aller sur DigitalOcean App Platform**
   - https://cloud.digitalocean.com/apps

2. **Sélectionner votre app Intelia**
   - Cliquer sur l'app dans la liste

3. **Aller dans Settings → Components**

4. **Pour CHAQUE composant (frontend, backend, llm, rag):**

   a. Cliquer sur le composant (ex: "llm")

   b. Dans la section **"Source"**, vérifier:
      - **Source Type**: Container Registry
      - **Registry**: `registry.digitalocean.com/intelia-registry`
      - **Repository**: `intelia-llm` (ou backend/frontend/rag)
      - **Tag**: `latest` ← **IMPORTANT: Changer ici!**

   c. Cliquer sur **"Save"**

5. **Sauvegarder les changements globaux**
   - Cliquer sur **"Save"** en bas de la page

6. **Déclencher un nouveau déploiement**
   - Cliquer sur **"Actions" → "Force Rebuild and Deploy"**

### Option 2: Via la CLI doctl

```bash
# 1. Récupérer la spec actuelle
doctl apps spec get YOUR_APP_ID > app-spec.yaml

# 2. Éditer le fichier app-spec.yaml
# Pour chaque service, modifier la section image:
#
# Avant:
#   image:
#     registry_type: DOCR
#     registry: intelia-registry
#     repository: intelia-llm
#     tag: main-a3b1f76c  ← Ancien tag
#
# Après:
#   image:
#     registry_type: DOCR
#     registry: intelia-registry
#     repository: intelia-llm
#     tag: latest  ← Nouveau tag

# 3. Appliquer la nouvelle spec
doctl apps update YOUR_APP_ID --spec app-spec.yaml

# 4. Déclencher un déploiement
doctl apps create-deployment YOUR_APP_ID
```

### Option 3: Script automatique

Créer un script `update-app-tags.sh`:

```bash
#!/bin/bash

APP_ID="YOUR_APP_ID"

# Récupérer la spec
doctl apps spec get $APP_ID --format yaml > app-spec.yaml

# Mettre à jour tous les tags vers 'latest'
sed -i 's/tag: main-.*/tag: latest/g' app-spec.yaml
sed -i 's/tag: sha-.*/tag: latest/g' app-spec.yaml

# Appliquer
doctl apps update $APP_ID --spec app-spec.yaml

echo "Tags mis à jour vers 'latest'. Déclenchement du déploiement..."
doctl apps create-deployment $APP_ID
```

Exécuter:
```bash
chmod +x update-app-tags.sh
./update-app-tags.sh
```

## Vérification

Après avoir appliqué la solution, vérifier que les tags sont corrects:

```bash
# Voir la spec actuelle
doctl apps spec get YOUR_APP_ID

# Chercher la section 'image' pour chaque service
# Vous devriez voir:
#   tag: latest
```

## Pourquoi cela résout le problème

**Avant:**
```yaml
services:
  - name: llm
    image:
      tag: main-abc123  ← Tag ancien/inexistant
```
→ Déploiement cherche `intelia-llm:main-abc123` → **404 Not Found**

**Après:**
```yaml
services:
  - name: llm
    image:
      tag: latest  ← Tag toujours à jour
```
→ Déploiement cherche `intelia-llm:latest` → **✅ Trouvé!**

Le workflow GitHub pousse toujours une image avec le tag `latest`:
```yaml
tags: |
  registry.digitalocean.com/.../intelia-llm:latest  ← Toujours créé
  registry.digitalocean.com/.../intelia-llm:main
  registry.digitalocean.com/.../intelia-llm:main-${{ github.sha }}
```

## Workflow CI/CD mis à jour

Le workflow `.github/workflows/deploy.yml` a été simplifié:

```yaml
deploy:
  steps:
    - name: Wait for registry propagation
      run: sleep 60  # Attente augmentée à 60s

    - name: Trigger deployment
      run: doctl apps create-deployment ${{ secrets.DO_APP_ID }}
```

Pas besoin de modifier la spec dans le workflow si elle est déjà configurée avec `tag: latest`!

## Configuration recommandée finale

Dans l'App Platform, pour chaque composant:

| Composant | Registry | Repository | Tag |
|-----------|----------|------------|-----|
| Frontend | intelia-registry | intelia-frontend | **latest** |
| Backend | intelia-registry | intelia-backend | **latest** |
| LLM | intelia-registry | intelia-llm | **latest** |
| RAG | intelia-registry | intelia-rag | **latest** |

## Notes importantes

- ✅ Le tag `latest` est automatiquement mis à jour à chaque push
- ✅ L'App Platform pull toujours la dernière version
- ✅ Pas besoin de modifier la spec à chaque déploiement
- ⚠️ L'attente de 60s assure que le registry est à jour
- ⚠️ En production, considérer des tags de version (v1.0.0) au lieu de `latest`

## Prochaines étapes

Une fois le tag configuré à `latest` sur tous les composants:

1. **Tester le workflow:**
   ```bash
   git commit --allow-empty -m "Test: Trigger deployment"
   git push
   ```

2. **Surveiller dans GitHub Actions:**
   - Build devrait réussir
   - Deploy devrait réussir sans erreur 404

3. **Vérifier le déploiement:**
   ```bash
   doctl apps list-deployments YOUR_APP_ID
   ```

## Dépannage

Si l'erreur 404 persiste:

1. **Vérifier que le tag existe dans le registry:**
   ```bash
   doctl registry repository list-tags intelia-llm
   # Devrait afficher 'latest'
   ```

2. **Vérifier la spec de l'app:**
   ```bash
   doctl apps spec get YOUR_APP_ID | grep -A 3 "image:"
   # Tous les tags doivent être 'latest'
   ```

3. **Forcer un rebuild complet:**
   ```bash
   doctl apps create-deployment YOUR_APP_ID --force-rebuild
   ```
