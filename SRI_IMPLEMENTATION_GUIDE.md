# 🔐 Subresource Integrity (SRI) - Guide d'implémentation

**Statut actuel** : ✅ **Non nécessaire** - Aucun script CDN externe utilisé

**Date** : 2025-10-19

---

## 📋 Résultat de l'audit

Scan effectué sur le projet Intelia Expert :
- ✅ Aucun script `<script src="https://cdn...">` détecté
- ✅ Aucun CDN externe (Google Fonts, CDNJS, unpkg, jsdelivr, etc.)
- ✅ Tous les scripts sont bundlés et servis localement par Next.js

**Conclusion** : SRI n'est **pas requis** actuellement.

---

## 🎯 Quand implémenter SRI ?

Implémenter SRI **si vous ajoutez** :
- Scripts provenant de CDN externes (Google, Cloudflare, etc.)
- Feuilles de styles CSS externes
- Fonts hébergées sur CDN (Google Fonts, Adobe Fonts)
- Bibliothèques JavaScript tierces non bundlées

---

## 📝 Comment implémenter SRI

### **Étape 1 : Générer le hash SRI**

```bash
# Pour un fichier local
openssl dgst -sha384 -binary FILENAME | openssl base64 -A

# Pour un fichier distant
curl https://cdn.example.com/library.js | openssl dgst -sha384 -binary | openssl base64 -A
```

### **Étape 2 : Ajouter l'attribut `integrity`**

**Avant (vulnérable)** :
```html
<script src="https://cdn.example.com/library.js"></script>
```

**Après (protégé avec SRI)** :
```html
<script
  src="https://cdn.example.com/library.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/ux..."
  crossorigin="anonymous">
</script>
```

### **Étape 3 : CSP doit autoriser le script**

Mettre à jour le Content-Security-Policy :

```javascript
// next.config.js
{
  key: "Content-Security-Policy",
  value: "... script-src 'self' https://cdn.example.com; ..."
}
```

---

## 🔍 Outils pour générer SRI

### **Outil en ligne** :
https://www.srihash.org/

### **Commande automatique** :
```bash
# Script bash pour générer SRI
#!/bin/bash
URL=$1
HASH=$(curl -s $URL | openssl dgst -sha384 -binary | openssl base64 -A)
echo "<script src=\"$URL\" integrity=\"sha384-$HASH\" crossorigin=\"anonymous\"></script>"
```

### **Node.js (pour build automation)** :
```javascript
const crypto = require('crypto');
const fs = require('fs');

function generateSRI(filePath) {
  const content = fs.readFileSync(filePath);
  const hash = crypto.createHash('sha384').update(content).digest('base64');
  return `sha384-${hash}`;
}

// Usage
const integrity = generateSRI('./public/script.js');
console.log(`integrity="${integrity}"`);
```

---

## 📊 Exemple complet

### **Scénario** : Ajout de Google Analytics

```html
<!-- ❌ Avant (vulnerable) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>

<!-- ✅ Après (protégé avec SRI) -->
<script
  async
  src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"
  integrity="sha384-ABC123..."
  crossorigin="anonymous">
</script>
```

**CSP mis à jour** :
```javascript
// next.config.js
{
  key: "Content-Security-Policy",
  value: "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com; ..."
}
```

---

## ⚠️ Limitations de SRI

### **1. Scripts dynamiques**
SRI ne fonctionne **PAS** pour :
- Scripts modifiés fréquemment par le CDN
- Scripts qui changent selon la géolocalisation
- Scripts A/B testés

**Solution** : Héberger localement ou accepter le risque.

### **2. Mise à jour du hash**
Si le script CDN change, le hash SRI doit être mis à jour :

```bash
# Automatiser avec un check CI/CD
npm run verify-sri  # Script personnalisé pour vérifier les hashes
```

### **3. Crossorigin**
SRI requiert `crossorigin="anonymous"` :
- Sinon, le navigateur refuse de charger le script
- Tous les CDN ne supportent pas CORS

---

## 🧪 Tester SRI

### **Test 1 : Hash invalide**
```html
<script
  src="https://cdn.example.com/script.js"
  integrity="sha384-INVALID_HASH"
  crossorigin="anonymous">
</script>
```

**Résultat attendu** : Console affiche erreur SRI, script non exécuté.

### **Test 2 : Pas de crossorigin**
```html
<script
  src="https://cdn.example.com/script.js"
  integrity="sha384-VALID_HASH">
  <!-- crossorigin manquant -->
</script>
```

**Résultat attendu** : Console affiche erreur, script non exécuté.

---

## 📋 Checklist de déploiement SRI

Avant de pousser en production :

- [ ] Générer le hash SRI pour chaque script externe
- [ ] Ajouter `integrity="sha384-..."` à chaque `<script>`
- [ ] Ajouter `crossorigin="anonymous"` à chaque `<script>`
- [ ] Mettre à jour CSP pour whitelist le domaine du CDN
- [ ] Tester en local (DevTools → Console → Aucune erreur SRI)
- [ ] Tester en staging
- [ ] Documenter les hashes dans un fichier `SRI_HASHES.md`
- [ ] Ajouter un check CI/CD pour vérifier les hashes

---

## 🔄 Monitoring continu

### **Script de vérification automatique** :

```bash
#!/bin/bash
# verify-sri.sh

EXPECTED_HASH="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/ux..."
ACTUAL_HASH=$(curl -s https://cdn.example.com/library.js | openssl dgst -sha384 -binary | openssl base64 -A)

if [ "sha384-$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
  echo "⚠️ ALERTE : Le hash SRI a changé !"
  echo "Attendu : $EXPECTED_HASH"
  echo "Actuel  : sha384-$ACTUAL_HASH"
  exit 1
else
  echo "✅ Hash SRI valide"
fi
```

**Ajouter à CI/CD** :
```yaml
# .github/workflows/sri-check.yml
name: SRI Verification
on: [push, pull_request, schedule]
jobs:
  verify-sri:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Verify SRI hashes
        run: ./verify-sri.sh
```

---

## 📚 Ressources

- [MDN - Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity)
- [SRI Hash Generator](https://www.srihash.org/)
- [W3C SRI Specification](https://www.w3.org/TR/SRI/)
- [Can I Use SRI](https://caniuse.com/subresource-integrity)

---

## ✅ Recommandation Intelia Expert

**Statut actuel** : Aucune action requise

**Si vous ajoutez des scripts CDN à l'avenir** :
1. Consulter ce guide
2. Générer les hashes SRI
3. Tester en local
4. Déployer en staging
5. Monitorer en production

**Alternative recommandée** : Héberger tous les scripts localement via Next.js bundling (approche actuelle) pour éviter la complexité de SRI.

---

*Guide créé le 2025-10-19 dans le cadre de l'audit de sécurité OWASP Top 10.*
