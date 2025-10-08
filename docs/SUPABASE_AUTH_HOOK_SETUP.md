# Configuration Supabase Auth Hook pour Emails Multilingues

## Problème Résolu

Supabase n'expose pas le token de confirmation dans la réponse de `sign_up()`, ce qui empêche d'envoyer des emails custom avec des liens de confirmation fonctionnels. La solution est d'utiliser les **Auth Hooks** de Supabase.

## Architecture

```
User Registration (Frontend)
    ↓
POST /api/v1/auth/register (Backend)
    ↓
supabase.auth.sign_up() - Crée l'utilisateur
    ↓
Supabase génère le token de confirmation
    ↓
Supabase appelle Auth Hook → POST /api/v1/webhooks/supabase/auth
    ↓
Webhook reçoit le token et envoie l'email multilingue
    ↓
User reçoit l'email avec lien fonctionnel
```

## Configuration Requise

### 1. Supabase Dashboard - Désactiver les Emails Automatiques

**Authentication → Email Templates → Confirm signup**
- ✅ **DÉCOCHER** "Enable Confirmations"
- Ceci empêche Supabase d'envoyer son propre email (non-multilingue)

### 2. Supabase Dashboard - Configurer Auth Hook

**Authentication → Hooks**
- Click "Add a new hook"
- **Type**: Send Email Hook
- **Event**: `user.created` (signup)
- **HTTP Endpoint**: `https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth`
- **Secret**: Générer un secret sécurisé (ex: avec `openssl rand -hex 32`)
- **Enabled**: ✅ Cocher

### 3. DigitalOcean App Platform - Variable d'Environnement

Ajouter la variable suivante dans **expert-app → Settings → Environment Variables**:

```
SUPABASE_WEBHOOK_SECRET=<le secret généré à l'étape 2>
```

### 4. Vérifier la Configuration

Test endpoint disponible:
```bash
curl https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth/config
```

Réponse attendue:
```json
{
  "version": "1.0.2",
  "webhook_url": "https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth",
  "smtp_configured": true,
  "webhook_secret_configured": true,
  "supported_events": [
    "user.created (signup)",
    "password.recovery.requested (reset password)",
    ...
  ],
  "email_languages_supported": ["en", "fr", "es", "de", "pt", "th", "zh", "ru", "hi", "id", "it", "nl", "pl"]
}
```

## Flux Complet

### 1. User s'inscrit avec langue préférée (ex: "fr")
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "firstName": "Jean",
  "lastName": "Dupont",
  "preferredLanguage": "fr"
}
```

### 2. Backend crée l'utilisateur Supabase
```python
result = supabase.auth.sign_up({
    "email": user_data.email,
    "password": user_data.password,
    "options": {
        "data": {
            "first_name": "Jean",
            "last_name": "Dupont",
            "preferred_language": "fr"
        }
    }
})
```

### 3. Supabase appelle le webhook avec le token
```json
{
  "type": "user.created",
  "email": "user@example.com",
  "user_metadata": {
    "first_name": "Jean",
    "last_name": "Dupont",
    "preferred_language": "fr"
  },
  "confirmation_token": "pkce_xxxxxxxxxxxxxxx",
  "confirmation_url": "https://expert.intelia.com/auth/verify-email?token=pkce_xxxxxxxxxxxxxxx&type=signup"
}
```

### 4. Webhook envoie l'email en français
Email envoyé via `backend/app/services/email_service.py`:
- Template: `templates/email_signup_confirmation_fr.html`
- Sujet: "Confirmez votre adresse email - Intelia Expert"
- Lien: `https://expert.intelia.com/auth/verify-email?token=pkce_xxxxxxxxxxxxxxx&type=signup`

### 5. User clique sur le lien → Email confirmé ✅

## Fichiers Impliqués

- **Backend Webhook**: `backend/app/api/v1/webhooks.py`
  - Endpoint: `/api/v1/webhooks/supabase/auth`
  - Handler: `handle_signup_event()`

- **Email Service**: `backend/app/services/email_service.py`
  - Méthode: `send_auth_email(EmailType.SIGNUP_CONFIRMATION, ...)`
  - Templates: `backend/app/templates/email_signup_confirmation_{lang}.html`

- **Registration Endpoint**: `backend/app/api/v1/auth.py`
  - Endpoint: `/api/v1/auth/register`
  - Note: N'envoie PLUS d'email directement (ligne 1343)

## Debugging

### Vérifier que le webhook est appelé

Logs DigitalOcean après inscription:
```
INFO:app.api.v1.webhooks:[Webhook] Received Supabase auth event
INFO:app.api.v1.webhooks:[Webhook] Processing event: user.created
INFO:app.api.v1.webhooks:[Webhook/Signup] Processing signup event
INFO:app.api.v1.webhooks:[Webhook/Signup] Sending signup email to user@example.com in language 'fr'
INFO:app.services.email_service:[EmailService] ✅ Email sent successfully to user@example.com
INFO:app.api.v1.webhooks:[Webhook/Signup] Email sent successfully
```

### Problèmes Courants

#### 1. Webhook non appelé
- ✅ Vérifier que "Enable Confirmations" est DÉCOCHÉ dans Email Templates
- ✅ Vérifier que le Auth Hook est activé (enabled)
- ✅ Vérifier que l'URL du webhook est correcte

#### 2. Email non envoyé
- ✅ Vérifier variables SMTP dans DigitalOcean
- ✅ Vérifier logs webhook: `docker logs expert-app | grep Webhook`

#### 3. Lien de confirmation ne fonctionne pas
- ✅ Vérifier que `FRONTEND_URL=https://expert.intelia.com` dans DigitalOcean
- ✅ Vérifier que `/auth/verify-email` page existe dans frontend

## Langues Supportées

Les templates d'email existent pour ces langues:
- `en` - English
- `fr` - Français
- `es` - Español
- `de` - Deutsch
- `pt` - Português
- `th` - ไทย (Thai)
- `zh` - 中文 (Chinese)
- `ru` - Русский (Russian)
- `hi` - हिन्दी (Hindi)
- `id` - Bahasa Indonesia
- `it` - Italiano
- `nl` - Nederlands
- `pl` - Polski

Par défaut: English si langue non supportée ou non spécifiée.

## Sécurité

### Vérification de Signature

Le webhook vérifie la signature HMAC-SHA256 de Supabase:
```python
expected_signature = hmac.new(
    SUPABASE_WEBHOOK_SECRET.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()

if signature != expected_signature:
    # Reject webhook
```

### Mode Permissif (Temporaire)

Actuellement en mode permissif pour debug:
```python
# backend/app/api/v1/webhooks.py ligne 168
if not is_valid:
    logger.warning("Invalid signature - continuing anyway (permissive mode)")
    # raise HTTPException(status_code=401, detail="Invalid webhook signature")
```

**TODO**: Activer la vérification stricte en production.

## Prochaines Étapes

1. ✅ Configurer Auth Hook dans Supabase Dashboard
2. ✅ Ajouter `SUPABASE_WEBHOOK_SECRET` dans DigitalOcean
3. ✅ Tester l'inscription avec différentes langues
4. ⏳ Activer vérification signature stricte
5. ⏳ Configurer hooks pour reset password et email change
