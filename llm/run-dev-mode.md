# Instructions pour tester en mode développement

## Option 1: Tester localement (RECOMMANDÉ)

1. Aller dans le dossier frontend:
   ```bash
   cd C:\intelia_gpt\intelia-expert\frontend
   ```

2. Lancer le serveur de développement:
   ```bash
   npm run dev
   ```

3. Ouvrir le navigateur à: http://localhost:3000

4. Ouvrir la console du navigateur (F12)

5. L'erreur React #310 apparaîtra avec le **message complet non-minifié** incluant:
   - Le nom EXACT du composant qui cause l'erreur
   - La ligne exacte du code
   - Le message d'erreur complet

## Option 2: Build de développement

Si vous voulez tester le build mais avec les erreurs non-minifiées:

1. Créer un fichier `.env.local` dans le dossier frontend:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://expert.intelia.com/api
   NODE_ENV=development
   ```

2. Builder:
   ```bash
   npm run build
   npm start
   ```

## Ce que nous cherchons

L'erreur React #310 signifie l'une de ces 3 choses:

1. **setState appelé sur un composant démonté**
   - Message: "Can't perform a React state update on an unmounted component"

2. **setState appelé pendant le render d'un autre composant**
   - Message: "Cannot update a component while rendering a different component"

3. **setState appelé dans le render (synchrone)**
   - Message: "Cannot update during an existing state transition"

Le message complet nous dira EXACTEMENT quel composant et quelle ligne.

## Partager le résultat

Une fois que vous avez l'erreur non-minifiée dans la console, copiez-collez:
1. Le message d'erreur COMPLET
2. La stack trace complète
3. Les noms des composants visibles

Cela nous permettra d'identifier le VRAI coupable en quelques secondes.
