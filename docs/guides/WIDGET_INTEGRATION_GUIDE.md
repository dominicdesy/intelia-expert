# Widget Intelia Cognito - Guide d'Intégration

**Version**: 1.0.0
**Date**: 26 octobre 2025
**Statut**: Implémentation initiale complétée ✅

---

## 1. Vue d'Ensemble

Le Widget Intelia Cognito permet d'intégrer un assistant IA conversationnel sur n'importe quel site web. Les utilisateurs peuvent poser des questions et obtenir des réponses instantanées basées sur votre base de connaissances Intelia.

### Caractéristiques Principales

- 🔒 **Sécurisé**: Authentification JWT côté serveur
- ⚡ **Rapide**: Réponses en streaming pour une expérience fluide
- 🎨 **Personnalisable**: Couleurs, position, langue adaptables
- 📊 **Analytics**: Suivi de l'utilisation et des conversations
- 💬 **Multilingue**: Support français et anglais
- 📱 **Responsive**: Optimisé mobile et desktop

---

## 2. Architecture Technique

```
┌─────────────────────────────────────────────────────────────┐
│                    Site Web du Client                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Widget JavaScript (intelia-widget.js)                │  │
│  │  - Interface utilisateur (bulle de chat)             │  │
│  │  - Gestion des messages                               │  │
│  │  - Streaming des réponses                             │  │
│  └───────────┬──────────────────────────────────────────┘  │
│              │ 1. Demande token JWT                         │
│              ▼                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Backend du Client (Node.js, PHP, Python, etc.)      │  │
│  │  - Génère JWT token avec client_id + user_id         │  │
│  │  - Secret partagé avec Intelia                        │  │
│  └───────────┬──────────────────────────────────────────┘  │
└──────────────┼──────────────────────────────────────────────┘
               │ 2. Retourne token
               │
               │ 3. Envoie message + token
               ▼
┌─────────────────────────────────────────────────────────────┐
│                 API Intelia Cognito                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Widget API (/api/v1/widget)                          │  │
│  │  - Vérifie JWT token                                  │  │
│  │  - Vérifie quota client                               │  │
│  │  - Appelle LLM API                                    │  │
│  └───────────┬──────────────────────────────────────────┘  │
│              │ 4. Appelle LLM                               │
│              ▼                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  LLM Service                                           │  │
│  │  - RAG Engine (récupération contexte)                │  │
│  │  - OpenAI / Anthropic                                 │  │
│  │  - Streaming de la réponse                            │  │
│  └───────────┬──────────────────────────────────────────┘  │
└──────────────┼──────────────────────────────────────────────┘
               │ 5. Streaming réponse
               ▼
        Utilisateur voit la réponse
```

---

## 3. Fichiers Créés

### 3.1 Backend - API Widget

**Fichier**: `backend/app/api/v1/widget.py`

Endpoints disponibles:

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/v1/widget/chat` | POST | Envoyer un message au chat (JWT requis) |
| `/api/v1/widget/generate-token` | POST | Générer un JWT token (admin) |
| `/api/v1/widget/health` | GET | Health check du widget API |

**Fonctionnalités**:
- Vérification JWT token
- Vérification quota client (requêtes/mois)
- Streaming des réponses LLM
- Enregistrement usage dans PostgreSQL

### 3.2 Base de Données

**Fichier**: `backend/sql/migrations/create_widget_tables.sql`

Tables créées:

1. **widget_clients**
   - Stocke les clients (entreprises) qui utilisent le widget
   - Champs: `client_id`, `client_name`, `domain`, `is_active`, `monthly_limit`, etc.

2. **widget_usage**
   - Enregistre chaque utilisation du widget
   - Champs: `client_id`, `user_id`, `timestamp`, `request_type`, `success`, etc.

3. **widget_conversations**
   - Stocke les conversations pour historique
   - Champs: `conversation_id`, `client_id`, `user_id`, `message_count`, etc.

4. **widget_messages**
   - Stocke les messages individuels
   - Champs: `conversation_id`, `role`, `content`, `timestamp`, etc.

5. **widget_monthly_usage** (Vue)
   - Agrégation mensuelle de l'utilisation par client
   - Statistiques: requests, users, conversations, avg response time

### 3.3 Frontend - Widget JavaScript

**Fichier**: `backend/static/widget/intelia-widget.js`

**Taille**: ~15 KB (minifié)
**Dépendances**: Aucune (vanilla JS)

**API publique**:
```javascript
// Initialiser
InteliaWidget.init({
  apiUrl: 'https://expert.intelia.com/api/v1/widget',
  getToken: async () => { /* ... */ },
  userId: 'user-123',
  userEmail: 'user@example.com',
  position: 'bottom-right',
  primaryColor: '#2563eb',
  locale: 'fr'
});

// Ouvrir programmatiquement
InteliaWidget.open();

// Fermer programmatiquement
InteliaWidget.close();

// Version
InteliaWidget.version; // "1.0.0"
```

### 3.4 Pages de Demo

**Fichier**: `backend/static/widget/demo-client.html`

Page de démonstration professionnelle pour clients (exemple: Animal Production company) avec:
- Site web complet avec widget intégré
- Design professionnel et responsive
- Exemple de configuration du widget
- Génération automatique de token JWT

**Fichier**: `backend/static/widget/test.html`

Page de test technique avec:
- Console de logs en temps réel
- Test de génération de token
- Initialisation manuelle du widget
- Monitoring des appels API

---

## 4. Guide d'Utilisation pour les Clients

### Étape 1: Obtenir les Identifiants

1. Contacter l'équipe Intelia
2. Recevoir:
   - `client_id` (ID unique de votre entreprise)
   - `WIDGET_JWT_SECRET` (secret partagé pour signer les tokens)
   - `monthly_limit` (nombre de requêtes/mois)

### Étape 2: Configuration Backend

Créer un endpoint sur votre serveur pour générer des JWT tokens.

#### Exemple Node.js / Express

```javascript
const jwt = require('jsonwebtoken');
const express = require('express');
const app = express();

// IMPORTANT: Ne JAMAIS exposer ce secret côté client !
const WIDGET_JWT_SECRET = process.env.WIDGET_JWT_SECRET;
const CLIENT_ID = 'votre-client-id';

app.get('/api/widget-token', (req, res) => {
  // Vérifier que l'utilisateur est authentifié
  if (!req.user) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Créer le token JWT
  const token = jwt.sign({
    client_id: CLIENT_ID,
    user_id: req.user.id,           // ID utilisateur dans votre système
    user_email: req.user.email,      // Email utilisateur (optionnel)
    exp: Math.floor(Date.now() / 1000) + (60 * 60)  // Expire dans 1h
  }, WIDGET_JWT_SECRET);

  res.json({ token });
});
```

#### Exemple Python / Flask

```python
import jwt
import time
from flask import Flask, jsonify, request

app = Flask(__name__)

WIDGET_JWT_SECRET = os.getenv('WIDGET_JWT_SECRET')
CLIENT_ID = 'votre-client-id'

@app.route('/api/widget-token')
def widget_token():
    # Vérifier que l'utilisateur est authentifié
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401

    # Créer le token JWT
    payload = {
        'client_id': CLIENT_ID,
        'user_id': str(current_user.id),
        'user_email': current_user.email,
        'exp': int(time.time()) + 3600  # Expire dans 1h
    }
    token = jwt.encode(payload, WIDGET_JWT_SECRET, algorithm='HS256')

    return jsonify({'token': token})
```

#### Exemple PHP

```php
<?php
use Firebase\JWT\JWT;

$widgetSecret = getenv('WIDGET_JWT_SECRET');
$clientId = 'votre-client-id';

// Vérifier que l'utilisateur est authentifié
if (!isset($_SESSION['user_id'])) {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

// Créer le token JWT
$payload = [
    'client_id' => $clientId,
    'user_id' => $_SESSION['user_id'],
    'user_email' => $_SESSION['user_email'],
    'exp' => time() + 3600  // Expire dans 1h
];

$token = JWT::encode($payload, $widgetSecret, 'HS256');

header('Content-Type: application/json');
echo json_encode(['token' => $token]);
```

### Étape 3: Intégration Frontend

Ajouter 2 lignes de code dans votre HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Mon Site</title>
</head>
<body>
    <!-- Votre contenu -->

    <!-- Charger le widget Intelia -->
    <script src="https://expert.intelia.com/api/widget/intelia-widget.js"></script>
    <script>
        InteliaWidget.init({
            apiUrl: 'https://expert.intelia.com/api/v1/widget',
            getToken: async () => {
                // Appeler votre serveur pour obtenir le token
                const response = await fetch('/api/widget-token');
                const data = await response.json();
                return data.token;
            },
            // Options optionnelles
            userId: 'user-123',              // ID utilisateur dans votre système
            userEmail: 'user@example.com',   // Email utilisateur
            position: 'bottom-right',        // 'bottom-right' ou 'bottom-left'
            primaryColor: '#2563eb',         // Couleur de votre marque
            locale: 'fr'                     // 'fr' ou 'en'
        });
    </script>
</body>
</html>
```

### Étape 4: Personnalisation

Options de configuration disponibles:

| Option | Type | Requis | Description |
|--------|------|--------|-------------|
| `apiUrl` | string | ✅ | URL de l'API widget |
| `getToken` | function | ✅ | Fonction async qui retourne le JWT token |
| `userId` | string | ❌ | ID utilisateur dans votre système |
| `userEmail` | string | ❌ | Email de l'utilisateur |
| `position` | string | ❌ | Position: `'bottom-right'` ou `'bottom-left'` |
| `primaryColor` | string | ❌ | Couleur principale (hex) |
| `locale` | string | ❌ | Langue: `'fr'` ou `'en'` |

---

## 5. Sécurité

### 5.1 Authentification JWT

Le widget utilise JWT (JSON Web Tokens) pour l'authentification:

1. **Génération côté serveur**: Le token DOIT être généré sur votre serveur (jamais côté client)
2. **Secret partagé**: Utiliser le `WIDGET_JWT_SECRET` fourni par Intelia
3. **Expiration**: Tokens expirent après 1 heure (configurable)
4. **Validation**: Chaque requête vérifie la signature et l'expiration du token

### 5.2 Quotas et Rate Limiting

- Chaque client a une limite mensuelle de requêtes (ex: 1000/mois)
- Compteur réinitialisé le 1er de chaque mois
- Si quota dépassé: erreur 429 avec message explicite
- Possibilité d'upgrade le plan via Intelia

### 5.3 CORS et Domaines

- Le widget fonctionne sur n'importe quel domaine
- Domaine enregistré dans `widget_clients.domain` pour analytics
- Pas de restriction CORS (le widget appelle l'API Intelia Cognito directement)

---

## 6. Analytics et Monitoring

### 6.1 Données Collectées

Pour chaque interaction:
- `client_id`: ID du client (entreprise)
- `user_id`: ID utilisateur dans le système du client
- `conversation_id`: ID unique de la conversation
- `timestamp`: Date/heure de la requête
- `message_length`: Longueur du message
- `response_time_ms`: Temps de réponse en ms
- `success`: Succès ou échec de la requête

### 6.2 Rapports Disponibles

Via la table `widget_monthly_usage`:
- Nombre total de requêtes par mois
- Nombre de requêtes réussies vs échouées
- Temps de réponse moyen
- Nombre d'utilisateurs uniques
- Nombre de conversations uniques

### 6.3 Dashboard Admin (À venir)

Fonctionnalités prévues:
- Vue en temps réel de l'utilisation
- Graphiques de l'activité mensuelle
- Top conversations les plus longues
- Taux de satisfaction
- Export des données (CSV, JSON)

---

## 7. Dépannage

### Erreur: "Token invalide"

**Cause**: JWT token malformé ou expiré
**Solution**:
1. Vérifier que le `WIDGET_JWT_SECRET` est correct
2. Vérifier l'expiration du token (max 1 heure)
3. Vérifier que le `client_id` est correct

### Erreur: "Quota dépassé"

**Cause**: Limite mensuelle de requêtes atteinte
**Solution**:
1. Attendre le 1er du mois suivant
2. Contacter Intelia pour augmenter le quota

### Widget ne s'affiche pas

**Cause**: Erreur de chargement du script
**Solution**:
1. Vérifier que l'URL du script est correcte
2. Vérifier la console JavaScript pour erreurs
3. Vérifier que `getToken` retourne bien un token

### Réponses lentes

**Cause**: LLM en surcharge ou connexion lente
**Solution**:
1. Vérifier la connexion internet
2. Contacter Intelia si problème persiste

---

## 8. Roadmap et Améliorations Futures

### Version 1.1 (Q1 2026)

- [ ] Support de fichiers (upload d'images/documents)
- [ ] Historique des conversations persistant
- [ ] Mode "suggestions" (questions pré-définies)
- [ ] Customisation avancée du CSS
- [ ] Support de webhooks pour notifications

### Version 1.2 (Q2 2026)

- [ ] Dashboard analytics complet
- [ ] Support multi-agents (différents assistants)
- [ ] Mode vocal (speech-to-text)
- [ ] Intégration Zendesk / Intercom
- [ ] Widget React / Vue / Angular components

### Version 2.0 (Q3 2026)

- [ ] Mode "embedded" (intégré dans la page)
- [ ] Support de formulaires conversationnels
- [ ] A/B testing intégré
- [ ] Machine learning sur satisfaction
- [ ] API REST complète pour gestion programmatique

---

## 9. Support et Contact

### Documentation

- **Guide d'intégration**: [https://expert.intelia.com/api/widget/demo-client.html](https://expert.intelia.com/api/widget/demo-client.html)
- **Page de test**: [https://expert.intelia.com/api/widget/test.html](https://expert.intelia.com/api/widget/test.html)
- **API Documentation**: [https://expert.intelia.com/api/docs](https://expert.intelia.com/api/docs)

### Démonstration Multilingue

Le widget supporte 16 langues. Testez-les directement sur la page de démo en ajoutant le paramètre `?lang=` à l'URL:

- **Anglais**: [?lang=en](https://expert.intelia.com/api/widget/demo-client.html?lang=en)
- **Français**: [?lang=fr](https://expert.intelia.com/api/widget/demo-client.html?lang=fr)
- **Espagnol**: [?lang=es](https://expert.intelia.com/api/widget/demo-client.html?lang=es)
- **Allemand**: [?lang=de](https://expert.intelia.com/api/widget/demo-client.html?lang=de)
- **Italien**: [?lang=it](https://expert.intelia.com/api/widget/demo-client.html?lang=it)
- **Portugais**: [?lang=pt](https://expert.intelia.com/api/widget/demo-client.html?lang=pt)
- **Néerlandais**: [?lang=nl](https://expert.intelia.com/api/widget/demo-client.html?lang=nl)
- **Polonais**: [?lang=pl](https://expert.intelia.com/api/widget/demo-client.html?lang=pl)
- **Japonais**: [?lang=ja](https://expert.intelia.com/api/widget/demo-client.html?lang=ja)
- **Chinois**: [?lang=zh](https://expert.intelia.com/api/widget/demo-client.html?lang=zh)
- **Arabe**: [?lang=ar](https://expert.intelia.com/api/widget/demo-client.html?lang=ar)
- **Hindi**: [?lang=hi](https://expert.intelia.com/api/widget/demo-client.html?lang=hi)
- **Indonésien**: [?lang=id](https://expert.intelia.com/api/widget/demo-client.html?lang=id)
- **Thaï**: [?lang=th](https://expert.intelia.com/api/widget/demo-client.html?lang=th)
- **Turc**: [?lang=tr](https://expert.intelia.com/api/widget/demo-client.html?lang=tr)
- **Vietnamien**: [?lang=vi](https://expert.intelia.com/api/widget/demo-client.html?lang=vi)

### Contact

- **Email**: support@intelia.com
- **Téléphone**: +1 (XXX) XXX-XXXX
- **Chat**: [https://expert.intelia.com](https://expert.intelia.com)

### SLA

- **Disponibilité**: 99.9% uptime garanti
- **Temps de réponse**: < 500ms (95th percentile)
- **Support**: Réponse sous 24h (jours ouvrables)

---

## 10. Migration SQL

Pour activer le widget sur votre instance Intelia, exécuter la migration:

```bash
# Via psql
psql $DATABASE_URL -f backend/sql/migrations/create_widget_tables.sql

# Via interface PostgreSQL
# Copier/coller le contenu de create_widget_tables.sql
```

Créer un client de test:

```sql
INSERT INTO widget_clients (
    client_id,
    client_name,
    domain,
    monthly_limit,
    is_active
) VALUES (
    'test-client-001',
    'Test Client',
    'localhost',
    10000,
    true
);
```

---

## 11. Variables d'Environnement

Ajouter dans `.env` du backend:

```bash
# Widget JWT Secret (généré avec: openssl rand -hex 32)
WIDGET_JWT_SECRET=votre_secret_jwt_de_64_caracteres_minimum

# URL du LLM API (réseau interne Docker)
LLM_INTERNAL_URL=http://intelia-llm:8080
```

---

## 12. Tests

### Test Manuel

1. Ouvrir `https://expert.intelia.com/api/widget/test.html`
2. Cliquer sur "Initialiser le Widget"
3. Vérifier que la bulle de chat apparaît avec le logo Intelia
4. Envoyer un message de test
5. Vérifier que la réponse s'affiche en streaming (texte propre, pas de JSON brut)

### Test Automatisé (À venir)

```bash
# Tests unitaires
pytest backend/tests/test_widget.py

# Tests d'intégration
pytest backend/tests/integration/test_widget_integration.py

# Tests E2E
playwright test widget.spec.ts
```

---

**Document créé le**: 26 octobre 2025
**Dernière mise à jour**: 26 octobre 2025
**Auteur**: Claude Code (Anthropic)
**Version**: 1.0.0
