# Stratégie de Migration - Backward Compatibility

**Version**: 1.0.0
**Date**: 26 octobre 2025
**Objectif**: Ajouter le support corporatif SANS casser les fonctionnalités existantes

---

## Principe Fondamental

**Tous les utilisateurs actuels continuent de fonctionner normalement.**
- Aucun changement de comportement pour les users existants
- Nouvelles colonnes avec valeurs par défaut
- Routing conditionnel (corpo vs individuel)
- Feature flags pour tester en isolation

---

## Analyse de l'Existant

### Ce qui fonctionne actuellement (B2C)

```
User individuel
├─ Inscription via Supabase Auth (email/password ou OAuth)
├─ Billing via Stripe (subscriptions)
├─ Chat → LLM API → Weaviate (main_knowledge_base)
├─ Conversations stockées dans PostgreSQL (DB principale)
├─ Widget pour intégration externe
└─ Frontend React (chat, settings, billing)
```

### Tables existantes (à ne PAS modifier destructivement)

```sql
-- Tables critiques à préserver
users (Supabase Auth)
conversations
messages
user_stats
stripe_subscriptions
widget_clients
widget_usage
...
```

---

## Stratégie de Migration par Phase

### Phase 0: Préparation (AVANT tout changement)

#### 0.1 Backup complet
```bash
# Backup PostgreSQL
pg_dump $DATABASE_URL > backup_pre_corporate_$(date +%Y%m%d).sql

# Backup Supabase Auth
# Export via Supabase Dashboard

# Backup Weaviate
# Export collections existantes
```

#### 0.2 Tests de régression
```bash
# Créer suite de tests pour valider comportement actuel
pytest backend/tests/test_existing_features.py

# Tests à couvrir:
# - Signup/login utilisateur individuel
# - Chat avec LLM
# - Billing Stripe
# - Widget externe
# - Conversations persistence
```

#### 0.3 Feature flags
```python
# backend/app/core/config.py
CORPORATE_FEATURES_ENABLED = os.getenv("CORPORATE_FEATURES_ENABLED", "false").lower() == "true"
```

---

## Phase 1: Ajout des Tables (NON-DESTRUCTIF)

### ✅ Approche: Nouvelles tables séparées

```sql
-- ============================================
-- MIGRATION 001: Ajouter tables corporatives
-- Date: 2025-10-26
-- Backward compatible: OUI ✅
-- ============================================

-- Nouvelle table: corporations
CREATE TABLE IF NOT EXISTS corporations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,

    postgres_connection_string TEXT NOT NULL,
    postgres_db_name VARCHAR(100) NOT NULL,
    postgres_region VARCHAR(50) DEFAULT 'us-east-1',

    weaviate_public_collection VARCHAR(100) NOT NULL,
    weaviate_private_collection VARCHAR(100) NOT NULL,
    weaviate_region VARCHAR(50) DEFAULT 'us-east-1',

    ip_whitelist JSONB DEFAULT '[]'::jsonb,
    enforce_sso BOOLEAN DEFAULT false,
    session_timeout_minutes INTEGER DEFAULT 60,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    metadata JSONB DEFAULT '{}'::jsonb
);

-- Nouvelle table: sso_configurations
CREATE TABLE IF NOT EXISTS sso_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID UNIQUE NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,

    provider VARCHAR(50) DEFAULT 'microsoft',
    tenant_id VARCHAR(255),
    client_id VARCHAR(255),
    client_secret TEXT,
    authority_url TEXT,

    is_enabled BOOLEAN DEFAULT false,
    auto_provision_users BOOLEAN DEFAULT true,

    credentials_last_rotated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Nouvelle table: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID,
    corporation_id UUID REFERENCES corporations(id) ON DELETE CASCADE,

    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),

    details JSONB DEFAULT '{}'::jsonb,

    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    success BOOLEAN DEFAULT true,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_corporation ON audit_logs(corporation_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Nouvelle table: ip_whitelist_logs
CREATE TABLE IF NOT EXISTS ip_whitelist_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID REFERENCES corporations(id) ON DELETE CASCADE,
    user_id UUID,

    ip_address INET NOT NULL,
    is_allowed BOOLEAN NOT NULL,
    attempted_action VARCHAR(100),

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ip_whitelist_logs_corporation ON ip_whitelist_logs(corporation_id);

-- ✅ AUCUNE modification destructive
-- ✅ Tables existantes intactes
```

---

## Phase 2: Modification de la Table Users (PRUDENT)

### ⚠️ Approche: Colonnes optionnelles avec valeurs par défaut

```sql
-- ============================================
-- MIGRATION 002: Ajouter colonnes corporatives à users
-- Date: 2025-10-26
-- Backward compatible: OUI ✅
-- ============================================

-- Ajouter colonnes NULLABLE (ne casse rien)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS corporation_id UUID REFERENCES corporations(id) ON DELETE SET NULL;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';

ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_corporate BOOLEAN DEFAULT false;

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_users_corporation ON users(corporation_id)
WHERE corporation_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)
WHERE is_corporate = true;

-- ✅ Valeurs par défaut pour users existants:
--    corporation_id = NULL (user individuel)
--    role = 'user'
--    is_corporate = false

-- ✅ Comportement existant préservé
-- ✅ Aucune migration de données requise
```

### Validation post-migration

```sql
-- Vérifier que tous les users existants ont les bonnes valeurs par défaut
SELECT
    COUNT(*) AS total_users,
    COUNT(*) FILTER (WHERE corporation_id IS NULL) AS individual_users,
    COUNT(*) FILTER (WHERE is_corporate = false) AS non_corporate_users
FROM users;

-- Doit retourner:
-- total_users = X
-- individual_users = X (même nombre)
-- non_corporate_users = X (même nombre)
```

---

## Phase 3: Backend Routing (CONDITIONNEL)

### ✅ Approche: Détection du type d'utilisateur

**Fichier**: `backend/app/middleware/user_context.py`

```python
async def get_user_context(user_id: str) -> dict:
    """
    Retourne le contexte utilisateur

    BACKWARD COMPATIBLE:
    - Si user.is_corporate = false → Comportement actuel (inchangé)
    - Si user.is_corporate = true → Nouveau comportement (corpo)
    """
    user = await get_user(user_id)

    # ✅ Users existants (is_corporate = false)
    if not user.is_corporate or user.corporation_id is None:
        return {
            "is_corporate": False,
            "corporation_id": None,

            # ✅ COMPORTEMENT ACTUEL PRÉSERVÉ
            "weaviate_collection": "main_knowledge_base",
            "postgres_db": None,  # Use default connection

            "role": "user",
            "features": {
                "billing": "stripe",
                "quota_enabled": True,
                "sso_enabled": False
            }
        }

    # 🆕 Nouveaux users corporatifs (is_corporate = true)
    corp = await get_corporation(user.corporation_id)

    return {
        "is_corporate": True,
        "corporation_id": str(corp.id),
        "corporation_name": corp.name,

        # 🆕 NOUVEAU COMPORTEMENT
        "weaviate_public_collection": corp.weaviate_public_collection,
        "weaviate_private_collection": corp.weaviate_private_collection,
        "postgres_connection": corp.postgres_connection_string,

        "role": user.role,
        "features": {
            "billing": "manual",
            "quota_enabled": False,
            "sso_enabled": corp.enforce_sso,
            "ip_whitelist_enabled": len(corp.ip_whitelist) > 0
        }
    }
```

### LLM API - Modification minimale

**Fichier**: `backend/app/api/v1/chat.py`

```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    # 🆕 Obtenir le contexte utilisateur
    context = await get_user_context(current_user.id)

    # ✅ Pour users individuels: comportement IDENTIQUE
    if not context["is_corporate"]:
        collection_name = "main_knowledge_base"
        db_connection = None  # Use default

    # 🆕 Pour users corporatifs: nouveau routing
    else:
        # Déterminer quelle collection utiliser
        # (selon choix de l'utilisateur dans le frontend)
        if request.use_private_kb:
            collection_name = context["weaviate_private_collection"]
        else:
            collection_name = context["weaviate_public_collection"]

        db_connection = context["postgres_connection"]

    # Appeler LLM avec la collection appropriée
    llm_payload = {
        "message": request.message,
        "conversation_id": request.conversation_id,
        "collection_name": collection_name,  # 🆕 Paramètre ajouté
        "db_connection": db_connection        # 🆕 Paramètre ajouté
    }

    # ✅ Reste du code INCHANGÉ
    response = await call_llm_api(llm_payload)
    return response
```

---

## Phase 4: Frontend (CONDITIONNEL)

### ✅ Approche: Feature flags + composants conditionnels

**Fichier**: `frontend/src/hooks/useUserContext.ts`

```typescript
export function useUserContext() {
  const { user } = useAuth();

  // ✅ Users existants: pas de changement
  const isCorporate = user?.is_corporate ?? false;

  return {
    isCorporate,
    corporationId: user?.corporation_id,
    role: user?.role ?? 'user',

    // ✅ Features accessibles selon le type
    features: {
      showCollectionSelector: isCorporate,
      showCorporateAdmin: isCorporate && user?.role === 'corp_admin',
      showStripeBilling: !isCorporate,
      showSSOSettings: isCorporate
    }
  };
}
```

**Fichier**: `frontend/src/components/chat/ChatInterface.tsx`

```tsx
export function ChatInterface() {
  const { isCorporate, features } = useUserContext();
  const [selectedCollection, setSelectedCollection] = useState<'public' | 'private'>('private');

  return (
    <div className="chat-interface">
      {/* ✅ Users existants: ne voient RIEN de nouveau */}
      {/* 🆕 Users corporatifs: voient le sélecteur */}
      {features.showCollectionSelector && (
        <CollectionSelector
          selected={selectedCollection}
          onChange={setSelectedCollection}
        />
      )}

      {/* ✅ Reste du chat IDENTIQUE pour tous */}
      <MessageList />
      <MessageInput />
    </div>
  );
}
```

---

## Phase 5: Tests de Non-Régression

### Scénarios à valider (CRITIQUES)

```typescript
// Test 1: User individuel existant
describe('Individual User - Backward Compatibility', () => {
  it('should login successfully', async () => {
    const user = await login('existing@user.com', 'password');
    expect(user.is_corporate).toBe(false);
  });

  it('should send chat message to main_knowledge_base', async () => {
    const response = await sendChatMessage('Hello');
    expect(response.collection_used).toBe('main_knowledge_base');
  });

  it('should see Stripe billing page', async () => {
    const billingPage = await navigateTo('/billing');
    expect(billingPage).toContain('Stripe');
  });

  it('should NOT see corporate features', async () => {
    const chatPage = await navigateTo('/chat');
    expect(chatPage).not.toContain('Collection Selector');
  });
});

// Test 2: Nouveau user corporatif
describe('Corporate User - New Features', () => {
  it('should access private collection', async () => {
    const user = await loginCorporate('corp@user.com');
    const response = await sendChatMessage('Hello', { collection: 'private' });
    expect(response.collection_used).toContain('private_kb');
  });

  it('should see collection selector', async () => {
    const chatPage = await navigateTo('/chat');
    expect(chatPage).toContain('Collection Selector');
  });
});
```

---

## Phase 6: Déploiement Progressif

### Stratégie: Blue-Green avec Feature Flags

```bash
# Étape 1: Déployer avec feature flag OFF
CORPORATE_FEATURES_ENABLED=false
# ✅ Aucun changement visible pour les users

# Étape 2: Créer première corpo de test
# Via super_admin interface ou SQL direct

# Étape 3: Activer pour la corpo de test uniquement
CORPORATE_FEATURES_ENABLED=true
CORPORATE_ENABLED_CORPS=["test-corp-001"]

# Étape 4: Valider pendant 1 semaine
# - Tests manuels
# - Monitoring erreurs
# - Feedback admin corpo test

# Étape 5: Rollout progressif
CORPORATE_ENABLED_CORPS=["test-corp-001", "corp-002", "corp-003"]

# Étape 6: Activation complète
CORPORATE_FEATURES_ENABLED=true
CORPORATE_ENABLED_CORPS=["*"]  # Toutes les corpos
```

---

## Rollback Plan

### Si problème détecté

```sql
-- Option 1: Désactiver toutes les corpos
UPDATE corporations SET is_active = false;

-- Option 2: Révoquer accès corpo d'un user
UPDATE users
SET is_corporate = false, corporation_id = NULL
WHERE id = 'problematic-user-id';

-- Option 3: Rollback complet (SI NÉCESSAIRE)
-- Restaurer backup pré-migration
psql $DATABASE_URL < backup_pre_corporate_20251026.sql
```

### Feature flag = Kill switch

```python
# backend/app/middleware/corporate_security.py
if not CORPORATE_FEATURES_ENABLED:
    # Forcer le comportement "individuel" pour TOUS les users
    return {
        "is_corporate": False,
        "weaviate_collection": "main_knowledge_base",
        # ... comportement par défaut
    }
```

---

## Checklist de Validation (AVANT production)

### Base de données
- [ ] Migrations SQL exécutées sans erreur
- [ ] Colonnes ajoutées avec valeurs par défaut correctes
- [ ] Index créés
- [ ] Backup récent disponible (< 24h)

### Backend
- [ ] Tests unitaires: 100% pass
- [ ] Tests d'intégration: users individuels fonctionnent
- [ ] Feature flag OFF: aucun changement visible
- [ ] Feature flag ON (test corpo): nouvelles features accessibles

### Frontend
- [ ] Build successful
- [ ] User individuel: interface identique
- [ ] User corporatif: nouvelles options visibles
- [ ] Pas de console errors

### Performance
- [ ] Temps de réponse chat: < 2s (inchangé)
- [ ] Connection pool: pas de leak
- [ ] Memory usage: stable

### Sécurité
- [ ] User individuel ne peut PAS accéder aux collections corpo
- [ ] User corpo A ne peut PAS accéder aux données corpo B
- [ ] IP whitelist testée
- [ ] SSO testé (si activé)

---

## Timeline Suggéré

| Phase | Durée | Risque |
|-------|-------|--------|
| Phase 0: Préparation & Backup | 1 jour | 🟢 Faible |
| Phase 1: Tables SQL | 1 jour | 🟢 Faible |
| Phase 2: Colonnes users | 1 jour | 🟡 Moyen |
| Phase 3: Backend routing | 3 jours | 🟡 Moyen |
| Phase 4: Frontend | 3 jours | 🟢 Faible |
| Phase 5: Tests non-régression | 2 jours | 🟢 Faible |
| Phase 6: Déploiement progressif | 1 semaine | 🟡 Moyen |
| **TOTAL** | **~3 semaines** | |

---

## Métriques de Succès

### Critères de validation

1. **Zéro régression**: Aucun user individuel affecté
2. **Performance stable**: Temps de réponse < 2s maintenu
3. **Uptime 99.9%**: Pas d'interruption de service
4. **Première corpo test**: Opérationnelle sous 1 semaine
5. **Admin corpo satisfait**: Peut gérer ses users facilement

---

## Conclusion

**Approche recommandée**:
- ✅ Changements ADDITIFS (pas destructifs)
- ✅ Feature flags pour isolation
- ✅ Déploiement progressif
- ✅ Rollback plan clair
- ✅ Tests exhaustifs avant prod

**Prochaine étape**: Commencer Phase 0 (Backup + Tests actuels)

---

**Document créé le**: 26 octobre 2025
**Auteur**: Claude Code (Anthropic)
