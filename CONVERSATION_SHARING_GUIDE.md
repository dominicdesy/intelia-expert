# Guide de partage de conversations - Intelia Expert

**Date**: 2025-10-12
**Fonctionnalité**: Partage public de conversations via lien

---

## 📋 Vue d'ensemble

Cette fonctionnalité permet aux utilisateurs authentifiés de partager leurs conversations via un lien public. Les destinataires peuvent consulter la conversation **sans créer de compte**, maximisant ainsi l'effet viral et l'acquisition d'utilisateurs.

---

## 🏗️ Architecture implémentée

### Backend (Python/FastAPI)

#### 1. Base de données

**Fichier**: `backend/migrations/create_conversation_shares.sql`

```sql
CREATE TABLE conversation_shares (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    share_token VARCHAR(64) UNIQUE NOT NULL,
    created_by UUID NOT NULL,
    share_type VARCHAR(20) DEFAULT 'public',
    anonymize BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Exécution**:
```bash
psql $DATABASE_URL -f backend/migrations/create_conversation_shares.sql
```

#### 2. Endpoints API

**Fichier**: `backend/app/api/v1/conversations.py`

**Endpoints authentifiés** (requiert token JWT):
- `POST /api/v1/conversations/{id}/share` - Créer un partage
- `GET /api/v1/conversations/{id}/shares` - Lister les partages actifs
- `DELETE /api/v1/shares/{share_id}` - Révoquer un partage

**Fichier**: `backend/app/api/v1/shared.py`

**Endpoints publics** (pas d'auth requise):
- `GET /api/v1/shared/{token}` - Consulter conversation partagée
- `GET /api/v1/shared/{token}/health` - Vérifier validité du lien

#### 3. Fonctionnalités de sécurité

**Anonymisation automatique** (si activée):
- Emails → `[email protégé]`
- Téléphones → `[téléphone]`
- Nom du créateur masqué

**Token cryptographique**:
- Génération avec `secrets.token_urlsafe(48)` (64 caractères)
- Impossible à deviner ou bruteforcer

### Frontend (Next.js/React)

#### 1. Composant de partage

**Fichier**: `frontend/app/chat/components/ShareConversationButton.tsx`

**Fonctionnalités**:
- Modal de configuration du partage
- Options : anonymisation, expiration (7/30/90 jours ou jamais)
- Copie automatique du lien dans le clipboard
- Affichage des informations du partage créé

**Utilisation**:
```tsx
import ShareConversationButton from "@/app/chat/components/ShareConversationButton";

<ShareConversationButton
  conversationId={conversationId}
  onShareCreated={(url) => console.log("Partage créé:", url)}
/>
```

#### 2. Page publique

**Fichier**: `frontend/app/shared/[token]/page.tsx`

**Fonctionnalités**:
- Affichage élégant de la conversation complète
- Messages alternés user/assistant avec design différencié
- Informations sur le partage (créateur, vues, expiration)
- CTA pour créer un compte ("Créer un compte gratuit")
- Responsive et accessible sans authentification

**URL**: `https://expert.intelia.com/shared/{token}`

---

## 🎯 Flow utilisateur complet

### Utilisateur authentifié (celui qui partage)

```
1. Dans /chat, sélectionne une conversation
2. Clique sur le bouton "Partager"
3. Configure les options:
   ✓ Anonymiser mes données (recommandé)
   ✓ Expiration: 7 jours / 30 jours / 90 jours / Jamais
4. Clique "Générer le lien de partage"
5. Le lien est généré: https://expert.intelia.com/shared/abc123xyz...
6. Copie le lien automatiquement dans le clipboard
7. Partage le lien via email/WhatsApp/Slack/etc.
```

### Destinataire (peut être non-authentifié)

```
1. Reçoit le lien: https://expert.intelia.com/shared/abc123xyz...
2. Clique sur le lien
3. Voit la conversation complète (anonymisée si option activée)
4. Informations affichées:
   - Toute la conversation (Q&A)
   - "Partagé par [Prénom]" (ou "Un utilisateur")
   - Nombre de vues
   - Date d'expiration
5. Banner CTA: "Créer un compte gratuit pour poser vos questions"
6. Peut créer un compte en un clic
```

---

## 🔒 Sécurité et confidentialité

### Protection des données

**Anonymisation (si activée)**:
- ✅ Emails masqués
- ✅ Téléphones masqués
- ✅ Nom du créateur anonymisé
- ✅ Informations d'entreprise dans les questions/réponses masquées

**Données toujours visibles**:
- Question et réponse complètes (contenu technique)
- Date et heure de la conversation
- Langue

### Contrôles d'accès

**Création d'un partage**:
- ✅ Authentification requise (JWT token)
- ✅ Vérification propriétaire (user_id)
- ✅ Conversation non supprimée

**Consultation d'un partage**:
- ⚪ Pas d'authentification requise (accès public)
- ✅ Token valide
- ✅ Pas expiré
- ✅ Conversation non supprimée

**Révocation d'un partage**:
- ✅ Authentification requise
- ✅ Seul le créateur peut révoquer

### Expiration automatique

```sql
-- Nettoyage automatique (cron job recommandé)
DELETE FROM conversation_shares
WHERE expires_at IS NOT NULL
AND expires_at < NOW();
```

---

## 📊 Métriques et analytics

### Tracking automatique

Chaque vue de partage incrémente automatiquement:
```sql
UPDATE conversation_shares
SET view_count = view_count + 1,
    last_viewed_at = NOW()
WHERE share_token = 'abc123';
```

### Queries analytics utiles

**Partages les plus consultés**:
```sql
SELECT
  cs.conversation_id,
  cs.view_count,
  cs.created_at,
  u.email as creator_email
FROM conversation_shares cs
JOIN users u ON cs.created_by = u.user_id
ORDER BY cs.view_count DESC
LIMIT 10;
```

**Taux de conversion (vues → inscriptions)**:
```sql
-- À implémenter: tracker les users créés depuis un partage
-- via UTM params ou referrer
```

**Partages actifs par utilisateur**:
```sql
SELECT
  u.email,
  COUNT(*) as active_shares,
  SUM(cs.view_count) as total_views
FROM conversation_shares cs
JOIN users u ON cs.created_by = u.user_id
WHERE (cs.expires_at IS NULL OR cs.expires_at > NOW())
GROUP BY u.email
ORDER BY active_shares DESC;
```

---

## 🚀 Déploiement

### 1. Backend

```bash
# 1. Appliquer la migration SQL
cd backend
psql $DATABASE_URL -f migrations/create_conversation_shares.sql

# 2. Redémarrer le backend
# Les routers sont auto-chargés via backend/app/api/v1/__init__.py
```

### 2. Frontend

```bash
# 1. Build
cd frontend
npm run build

# 2. Deploy (Digital Ocean / Vercel / etc.)
npm run deploy
```

### 3. Tests

**Test endpoint de création**:
```bash
curl -X POST https://expert.intelia.com/api/v1/conversations/{conv_id}/share \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "share_type": "public",
    "anonymize": true,
    "expires_in_days": 30
  }'
```

**Test endpoint public**:
```bash
curl https://expert.intelia.com/api/v1/shared/{token}
```

**Test page frontend**:
```
https://expert.intelia.com/shared/{token}
```

---

## 🎨 Intégration dans l'interface existante

### Ajouter le bouton de partage

**Dans ConversationSidebar.tsx** (ou équivalent):

```tsx
import ShareConversationButton from "@/app/chat/components/ShareConversationButton";

// Dans le menu d'actions de chaque conversation
<div className="flex items-center gap-2">
  <ShareConversationButton conversationId={conversation.id} />
  <DeleteButton conversationId={conversation.id} />
  <FeedbackButton conversationId={conversation.id} />
</div>
```

**Dans la page de conversation elle-même**:

```tsx
// Header de la conversation
<div className="flex items-center justify-between">
  <h2>Conversation {conversationId}</h2>
  <div className="flex gap-2">
    <ShareConversationButton conversationId={conversationId} />
  </div>
</div>
```

---

## 🐛 Troubleshooting

### "Conversation non trouvée"

**Causes possibles**:
- Token invalide ou expiré
- Conversation supprimée
- Partage révoqué par le créateur

**Solution**:
```sql
-- Vérifier l'existence du partage
SELECT * FROM conversation_shares WHERE share_token = 'TOKEN_ICI';

-- Vérifier l'expiration
SELECT expires_at, expires_at < NOW() as is_expired
FROM conversation_shares
WHERE share_token = 'TOKEN_ICI';
```

### Anonymisation ne fonctionne pas

**Vérifier**:
```python
# Dans backend/app/api/v1/shared.py
# La fonction anonymize_text() utilise des regex
# Tester avec des exemples
from app.api.v1.shared import anonymize_text

text = "Mon email est john@example.com et mon tél est 06 12 34 56 78"
print(anonymize_text(text))
# Output attendu: "Mon email est [email protégé] et mon tél est [téléphone]"
```

### Token ne se copie pas

**Navigateurs supportés**:
- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅ (avec HTTPS obligatoire)

**Fallback** si `navigator.clipboard` non disponible:
```tsx
// Utiliser un input temporaire
const fallbackCopy = (text: string) => {
  const input = document.createElement('input');
  input.value = text;
  document.body.appendChild(input);
  input.select();
  document.execCommand('copy');
  document.body.removeChild(input);
};
```

---

## 🔮 Améliorations futures possibles

### Court terme

1. **Partage par email direct**
   ```tsx
   <button onClick={() => shareViaEmail(shareUrl)}>
     Envoyer par email
   </button>
   ```

2. **Boutons de partage social**
   - LinkedIn
   - Twitter
   - WhatsApp
   - Facebook

3. **QR Code pour partage mobile**
   ```tsx
   import QRCode from 'qrcode.react';
   <QRCode value={shareUrl} />
   ```

### Moyen terme

4. **Analytics détaillées**
   - Temps moyen de lecture
   - Taux de conversion (vue → inscription)
   - Origine géographique des vues

5. **Partage privé avec mot de passe**
   ```sql
   ALTER TABLE conversation_shares
   ADD COLUMN password_hash VARCHAR(255);
   ```

6. **Export PDF de la conversation**
   - Génération côté serveur
   - Logo et branding Intelia
   - Partage hors ligne

### Long terme

7. **Collections de conversations**
   - Partager plusieurs conversations en un lien
   - Créer des "knowledge bases" publiques

8. **Commentaires sur les partages**
   - Permettre aux viewers de poser des questions
   - Fil de discussion public

9. **Embedding de conversations**
   - iframe pour intégrer dans d'autres sites
   - Widget JavaScript

---

## ✅ Checklist de validation

Avant de déployer en production:

**Backend**:
- [ ] Migration SQL exécutée sur la DB de production
- [ ] Endpoints testés avec Postman/curl
- [ ] Logs backend configurés pour tracking
- [ ] Rate limiting configuré sur les endpoints publics

**Frontend**:
- [ ] Composant ShareConversationButton intégré dans l'UI
- [ ] Page /shared/[token] accessible et testée
- [ ] Design responsive testé (mobile/tablet/desktop)
- [ ] Analytics configurés (Google Analytics/Plausible)

**Sécurité**:
- [ ] Anonymisation testée avec données réelles
- [ ] Tokens cryptographiques vérifiés (longueur 64 chars)
- [ ] HTTPS obligatoire en production
- [ ] CORS configuré correctement

**UX**:
- [ ] Messages d'erreur clairs et en français
- [ ] Loading states pour toutes les actions
- [ ] Toast notifications pour succès/échec
- [ ] CTA "Créer un compte" bien visible

---

## 📞 Support

**Documentation technique**:
- Backend API: `/api/docs` (Swagger UI)
- Frontend: Ce fichier

**Contact**:
- Questions techniques: [Votre email]
- Bugs: [GitHub Issues ou Jira]

---

**Implémenté par**: Claude Code
**Date**: 2025-10-12
**Version**: 1.0.0
