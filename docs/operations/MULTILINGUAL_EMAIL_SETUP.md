# Configuration des Emails Multilingues via Webhooks Supabase

## Vue d'ensemble

Ce système permet d'envoyer des emails d'authentification (signup, reset password, etc.) dans la langue préférée de l'utilisateur, avec un fallback automatique en anglais.

**Architecture** :
1. Supabase gère l'authentification et les mots de passe (sécurité 100%)
2. Supabase désactive l'envoi automatique d'emails
3. Supabase appelle notre webhook lors des événements auth
4. Notre backend envoie les emails personnalisés via SMTP

## Fichiers créés/modifiés

### Nouveaux fichiers

1. **`app/services/email_service.py`** - Service d'envoi d'emails multilingues
   - Templates HTML bilingues (langue préférée + anglais)
   - Support SMTP (Gmail, SendGrid, AWS SES, etc.)
   - 8 langues incluses : EN, FR, ES, DE, PT, TH, ZH, RU
   - Fallback automatique vers EN pour les langues non traduites

2. **`app/api/v1/webhooks.py`** - Endpoint webhook pour recevoir les événements Supabase
   - Vérifie la signature HMAC pour sécurité
   - Traite les événements : signup, password reset, email change, invite
   - Endpoints de debug et test

3. **`backend/docs/MULTILINGUAL_EMAIL_SETUP.md`** - Cette documentation

### Fichiers modifiés

1. **`app/api/v1/auth.py`**
   - Ajout du champ `preferred_language` au modèle `UserRegister`
   - Stockage de la langue dans `user_metadata` lors du signup

2. **`app/main.py`**
   - Ajout du router webhooks dans la liste des routers chargés

## Variables d'environnement à ajouter

Ajoutez ces variables dans votre fichier `.env` (ou dans votre configuration DigitalOcean App Platform) :

```bash
# === SMTP CONFIGURATION (pour l'envoi d'emails) ===

# Resend.com (Production - Configuration Intelia)
SMTP_HOST=smtp.resend.com
SMTP_PORT=465
SMTP_USER=resend
SMTP_PASSWORD=votre_api_key_resend  # Clé API Resend (re_...)
SMTP_FROM_EMAIL=assistant@intelia.com
SMTP_FROM_NAME=Intelia Expert

# Alternatives SMTP populaires:
# Gmail: smtp.gmail.com:587 (dev/test uniquement)
# SendGrid: smtp.sendgrid.net:587
# AWS SES: email-smtp.us-east-1.amazonaws.com:587
# Mailgun: smtp.mailgun.org:587
# Postmark: smtp.postmarkapp.com:587

# === WEBHOOK SECURITY ===
SUPABASE_WEBHOOK_SECRET=votre-secret-securise-genere-par-supabase
# Ce secret est généré par Supabase et utilisé pour vérifier l'authenticité des webhooks

# === URLS (déjà configurées normalement) ===
BACKEND_URL=https://expert-app-cngws.ondigitalocean.app
FRONTEND_URL=https://expert.intelia.com
```

## Configuration Supabase Dashboard

### Étape 1 : Désactiver les emails automatiques de Supabase

1. Allez dans **Authentication > Email Templates**
2. Pour chaque template (Confirm signup, Reset password, etc.) :
   - **Désactivez "Enable email confirmations"** ou
   - **Remplacez le contenu du template par un message vide** (pour garder la fonctionnalité active)

### Étape 2 : Configurer les Webhooks (Auth Hooks)

1. Allez dans **Database > Webhooks** ou **Authentication > Hooks**
2. Créez un nouveau webhook avec ces paramètres :

**Pour l'événement "user.created" (signup)** :
```
Nom: Signup Email Hook
Table: auth.users
Events: INSERT
Webhook URL: https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth
HTTP Method: POST
HTTP Headers:
  X-Supabase-Signature: [votre_secret]
```

**Pour l'événement "password.recovery.requested" (reset password)** :
```
Nom: Password Reset Email Hook
Table: auth.users
Events: UPDATE (avec condition: recovery_token IS NOT NULL)
Webhook URL: https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth
HTTP Method: POST
HTTP Headers:
  X-Supabase-Signature: [votre_secret]
```

### Étape 3 : Tester le webhook

Utilisez l'endpoint de test :

```bash
curl https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth/test
```

Réponse attendue :
```json
{
  "success": true,
  "message": "Webhook endpoint is working",
  "timestamp": "2025-10-08T...",
  "email_service_configured": true,
  "webhook_secret_configured": true
}
```

## Configuration Gmail pour SMTP

Si vous utilisez Gmail :

1. Activez la vérification en 2 étapes sur votre compte Google
2. Allez dans **Compte Google > Sécurité > Mots de passe d'application**
3. Générez un mot de passe d'application pour "Autre (nom personnalisé)"
4. Utilisez ce mot de passe dans `SMTP_PASSWORD`

## Flux d'utilisation

### 1. Inscription d'un nouvel utilisateur

```
Frontend envoie POST /api/v1/auth/register
  {
    "email": "user@example.com",
    "password": "...",
    "first_name": "John",
    "preferred_language": "th"  ← langue préférée
  }
    ↓
Backend stocke user_metadata.preferred_language = "th"
    ↓
Supabase crée le compte et génère le token de confirmation
    ↓
Supabase appelle notre webhook /api/v1/webhooks/supabase/auth
    ↓
Notre backend envoie l'email en Thai + English fallback
    ↓
Utilisateur reçoit l'email bilingue
```

### 2. Reset password

```
Frontend envoie POST /api/v1/auth/reset-password
  {
    "email": "user@example.com"
  }
    ↓
Supabase récupère user_metadata.preferred_language
    ↓
Supabase génère le recovery token
    ↓
Supabase appelle notre webhook
    ↓
Email envoyé dans la langue de l'utilisateur
```

## Structure des emails

Chaque email contient **2 sections** :

1. **Section principale** : Contenu dans la langue préférée de l'utilisateur
2. **Section fallback** : Même contenu en anglais

Exemple d'email en Thai :

```
┌────────────────────────────────┐
│ Intelia Technologies           │
│ Intelia Expert                 │
├────────────────────────────────┤
│ ยืนยันการสมัครของคุณ          │ ← Thai
│ สวัสดี John,                   │
│ ขอบคุณที่สร้างบัญชี...        │
│ [ยืนยันอีเมลของฉัน] ← Button  │
│ หรือป้อนรหัส: 123456          │
├────────────────────────────────┤
│ English version                │ ← Fallback
│ Hello John,                    │
│ Thank you for creating...      │
│ [Confirm my email]             │
│ Or use code: 123456            │
└────────────────────────────────┘
```

## Langues supportées

### Traduites (8 langues)
- 🇬🇧 English (en) - DEFAULT
- 🇫🇷 Français (fr)
- 🇪🇸 Español (es)
- 🇩🇪 Deutsch (de)
- 🇵🇹 Português (pt)
- 🇹🇭 ไทย (th)
- 🇨🇳 中文 (zh)
- 🇷🇺 Русский (ru)

### Avec fallback automatique vers EN
- 🇮🇳 Hindi (hi)
- 🇮🇩 Indonesian (id)
- 🇮🇹 Italian (it)
- 🇳🇱 Dutch (nl)
- 🇵🇱 Polish (pl)

## Ajouter une nouvelle langue

Pour ajouter une nouvelle traduction (ex: Italian) :

1. Ouvrir `backend/app/services/email_service.py`
2. Ajouter dans l'enum `EmailLanguage` (ligne ~25) :
   ```python
   IT = "it"
   ```
3. Ajouter dans `LANGUAGE_NAMES` (ligne ~35) :
   ```python
   EmailLanguage.IT: "Italiano",
   ```
4. Ajouter dans `get_translations()` (ligne ~57) :
   ```python
   EmailLanguage.IT: {
       "signup_title": "Conferma la tua iscrizione",
       "signup_greeting": "Ciao",
       "signup_body": "Grazie per aver creato un account...",
       # ... toutes les autres clés
   },
   ```

## Monitoring et Debug

### Vérifier la configuration

```bash
curl https://expert-app-cngws.ondigitalocean.app/api/v1/webhooks/supabase/auth/config
```

### Logs importants

Dans les logs backend, recherchez :

```
[Webhook] Received Supabase auth event
[Webhook] Processing event: user.created
[Webhook/Signup] Processing signup event
[Webhook/Signup] Sending signup email to user@example.com in language 'th'
[Webhook/Signup] Email sent successfully to user@example.com
```

### Erreurs courantes

**1. "SMTP credentials not configured"**
- Solution : Vérifier que `SMTP_USER` et `SMTP_PASSWORD` sont définis

**2. "Invalid webhook signature"**
- Solution : Vérifier que `SUPABASE_WEBHOOK_SECRET` correspond au secret configuré dans Supabase

**3. "Failed to send email"**
- Solution : Vérifier les credentials SMTP et la connexion réseau

**4. Email reçu en anglais au lieu de la langue préférée**
- Vérifier que `user_metadata.preferred_language` est bien stocké lors du register
- Vérifier les logs backend pour voir quelle langue est détectée

## Sécurité

✅ **Les mots de passe ne transitent JAMAIS par votre backend**
- Supabase gère 100% de l'authentification
- Votre backend reçoit uniquement les métadonnées (email, langue, tokens)
- Les tokens sont générés et validés par Supabase

✅ **Signature HMAC pour les webhooks**
- Chaque requête webhook est signée avec HMAC-SHA256
- Empêche les appels non autorisés à votre endpoint

✅ **Tokens OTP sécurisés**
- Générés par Supabase
- Expiration automatique
- Usage unique

## Dépannage

### L'utilisateur ne reçoit pas l'email

1. Vérifier que le webhook est bien appelé (logs Supabase)
2. Vérifier les logs backend pour les erreurs SMTP
3. Vérifier les spams/courrier indésirable
4. Tester l'envoi d'email directement :

```python
# Test manuel depuis le backend
from app.services.email_service import get_email_service, EmailType

service = get_email_service()
success = service.send_auth_email(
    email_type=EmailType.SIGNUP_CONFIRMATION,
    to_email="test@example.com",
    language="fr",
    confirmation_url="https://example.com/confirm?token=test123",
    otp_token="123456",
    first_name="Test"
)
print(f"Email sent: {success}")
```

### L'email est envoyé mais toujours en anglais

Vérifier que :
1. Le frontend envoie bien `preferred_language` lors du register
2. Le backend stocke bien la langue dans `user_metadata`
3. Les logs montrent la bonne langue détectée

## Support

Pour toute question ou problème :
- **Logs backend** : `docker logs <container-id> | grep -i webhook`
- **Logs Supabase** : Dashboard > Database > Webhooks > Logs
- **Test webhook** : `/api/v1/webhooks/supabase/auth/test`
- **Config webhook** : `/api/v1/webhooks/supabase/auth/config`

---

**Version** : 1.0
**Dernière mise à jour** : 2025-10-08
**Auteur** : Claude Code + Dominic Desy
