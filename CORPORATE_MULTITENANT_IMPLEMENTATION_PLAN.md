# Plan d'Implémentation - Multi-tenant Corporatif B2B

**Version**: 1.0.0
**Date**: 26 octobre 2025
**Statut**: 🔴 Planification

---

## Vue d'ensemble

Ajouter le support de clients corporatifs (B2B) avec:
- Isolation complète des données (DB dédiée + collections Weaviate privées)
- Admin corporatif pour gérer les utilisateurs
- SSO Microsoft configurable
- Sécurité renforcée (IP whitelist, audit logs, etc.)
- Collections publiques/privées par corpo
- Support multi-région (data residency)

---

## Architecture Multi-tenant

### Modèle utilisateurs

```
Utilisateurs individuels (B2C)
├─ Stripe billing
├─ DB principale (public schema)
└─ Collection Weaviate: main_knowledge_base

Utilisateurs corporatifs (B2B)
├─ Factures manuelles
├─ DB dédiée par corpo: intelia_corp_acme
├─ Collections Weaviate:
│  ├─ corp_acme_public_kb (accessible via widget)
│  └─ corp_acme_private_kb (employés seulement)
├─ SSO Microsoft (optionnel, configurable)
└─ IP whitelist (optionnel)
```

### Isolation des données

| Ressource | Utilisateurs individuels | Utilisateurs corporatifs |
|-----------|-------------------------|-------------------------|
| **PostgreSQL** | DB principale (`intelia_db`) | DB dédiée (`intelia_corp_acme`) |
| **Contenu DB** | Conversations, messages, stats | Données de performance (courbes Ross, etc.) |
| **Weaviate** | `main_knowledge_base` | `corp_xxx_public_kb` + `corp_xxx_private_kb` |
| **Backup** | Digital Ocean automated | Digital Ocean automated (région spécifique) |
| **Région** | us-east-1 | Configurable (EU, Canada, etc.) |

---

## Phase 1: Schéma de base de données

### 1.1 Table `corporations`

```sql
CREATE TABLE corporations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- Ex: 'acme'

    -- Database configuration
    postgres_connection_string TEXT NOT NULL, -- Chiffré
    postgres_db_name VARCHAR(100) NOT NULL,   -- Ex: 'intelia_corp_acme'
    postgres_region VARCHAR(50) DEFAULT 'us-east-1', -- Ex: 'eu-central-1', 'ca-central-1'

    -- Weaviate collections
    weaviate_public_collection VARCHAR(100) NOT NULL,  -- Ex: 'corp_acme_public_kb'
    weaviate_private_collection VARCHAR(100) NOT NULL, -- Ex: 'corp_acme_private_kb'
    weaviate_region VARCHAR(50) DEFAULT 'us-east-1',

    -- Security settings
    ip_whitelist JSONB DEFAULT '[]'::jsonb, -- Ex: ["203.0.113.0/24", "198.51.100.42"]
    enforce_sso BOOLEAN DEFAULT false,
    session_timeout_minutes INTEGER DEFAULT 60,

    -- Status
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb -- Plan, contacts, notes, etc.
);

CREATE INDEX idx_corporations_slug ON corporations(slug);
CREATE INDEX idx_corporations_active ON corporations(is_active);
```

### 1.2 Table `users` - Modifications

```sql
-- Ajouter colonnes à la table users existante
ALTER TABLE users ADD COLUMN corporation_id UUID REFERENCES corporations(id) ON DELETE CASCADE;
ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'; -- 'user', 'corp_admin', 'super_admin'
ALTER TABLE users ADD COLUMN is_corporate BOOLEAN DEFAULT false;

CREATE INDEX idx_users_corporation ON users(corporation_id);
CREATE INDEX idx_users_role ON users(role);

-- Row-Level Security (RLS) pour isolation stricte
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Users ne peuvent voir que leur propre data ou users de leur corpo
CREATE POLICY users_isolation_policy ON users
    USING (
        id = current_setting('app.current_user_id')::uuid
        OR corporation_id = current_setting('app.current_corporation_id')::uuid
    );
```

### 1.3 Table `sso_configurations`

```sql
CREATE TABLE sso_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID UNIQUE NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,

    -- Microsoft Azure AD
    provider VARCHAR(50) DEFAULT 'microsoft', -- 'microsoft', 'google', 'okta', etc.
    tenant_id VARCHAR(255), -- Chiffré
    client_id VARCHAR(255), -- Chiffré
    client_secret TEXT,     -- Chiffré avec clé dédiée
    authority_url TEXT,

    -- Configuration
    is_enabled BOOLEAN DEFAULT false,
    auto_provision_users BOOLEAN DEFAULT true, -- Créer compte auto si SSO réussit

    -- Security
    credentials_last_rotated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.4 Table `audit_logs`

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    corporation_id UUID REFERENCES corporations(id) ON DELETE CASCADE,

    -- What
    action VARCHAR(100) NOT NULL, -- 'query_weaviate', 'access_db', 'invite_user', etc.
    resource_type VARCHAR(50),    -- 'collection', 'database', 'user', etc.
    resource_id VARCHAR(255),

    -- Details
    details JSONB DEFAULT '{}'::jsonb, -- Query, filters, result count, etc.

    -- When & Where
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Result
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_corporation ON audit_logs(corporation_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Partition par mois pour performance
-- TODO: Setup partitioning strategy
```

### 1.5 Table `invitations`

```sql
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID NOT NULL REFERENCES corporations(id) ON DELETE CASCADE,

    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'corp_admin'
    token VARCHAR(255) UNIQUE NOT NULL,

    invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    used_at TIMESTAMP WITH TIME ZONE,
    used_by UUID REFERENCES users(id) ON DELETE SET NULL,

    is_active BOOLEAN DEFAULT true
);

CREATE INDEX idx_invitations_token ON invitations(token);
CREATE INDEX idx_invitations_email ON invitations(email);
CREATE INDEX idx_invitations_corporation ON invitations(corporation_id);
```

### 1.6 Table `ip_whitelist_logs`

```sql
CREATE TABLE ip_whitelist_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corporation_id UUID REFERENCES corporations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    ip_address INET NOT NULL,
    is_allowed BOOLEAN NOT NULL,
    attempted_action VARCHAR(100),

    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ip_whitelist_logs_corporation ON ip_whitelist_logs(corporation_id);
CREATE INDEX idx_ip_whitelist_logs_timestamp ON ip_whitelist_logs(timestamp);
```

### 1.7 Vue `corporation_users`

```sql
CREATE VIEW corporation_users AS
SELECT
    u.id,
    u.email,
    u.corporation_id,
    c.name AS corporation_name,
    u.role,
    u.is_corporate,
    u.created_at,
    u.last_sign_in_at
FROM users u
LEFT JOIN corporations c ON u.corporation_id = c.id
WHERE u.is_corporate = true;
```

---

## Phase 2: Backend - Sécurité & Routing

### 2.1 Middleware de sécurité

**Fichier**: `backend/app/middleware/corporate_security.py`

```python
from fastapi import Request, HTTPException
from ipaddress import ip_address, ip_network
import logging

logger = logging.getLogger(__name__)

async def validate_ip_whitelist(request: Request, corporation_id: str):
    """
    Valide que l'IP du client est dans la whitelist de la corpo
    """
    # Récupérer la config de la corpo
    corp = get_corporation(corporation_id)

    if not corp.ip_whitelist or len(corp.ip_whitelist) == 0:
        return True  # Pas de whitelist = pas de restriction

    # Obtenir l'IP du client
    client_ip = request.client.host
    if request.headers.get("X-Forwarded-For"):
        client_ip = request.headers.get("X-Forwarded-For").split(",")[0]

    # Vérifier si l'IP est dans la whitelist
    client_ip_obj = ip_address(client_ip)
    allowed = False

    for cidr in corp.ip_whitelist:
        if client_ip_obj in ip_network(cidr):
            allowed = True
            break

    # Logger l'événement
    log_ip_whitelist_attempt(
        corporation_id=corporation_id,
        user_id=request.state.user_id,
        ip_address=client_ip,
        is_allowed=allowed
    )

    if not allowed:
        logger.warning(f"IP {client_ip} bloquée pour corporation {corporation_id}")
        raise HTTPException(
            status_code=403,
            detail="Access denied: IP address not in whitelist"
        )

    return True


async def get_user_context(user_id: str) -> dict:
    """
    Retourne le contexte de l'utilisateur (corpo vs individuel)
    """
    user = get_user_with_corporation(user_id)

    if user.is_corporate and user.corporation_id:
        corp = get_corporation(user.corporation_id)

        return {
            "is_corporate": True,
            "corporation_id": str(corp.id),
            "corporation_name": corp.name,

            # Database routing
            "postgres_connection": decrypt_connection_string(corp.postgres_connection_string),
            "postgres_db_name": corp.postgres_db_name,

            # Weaviate routing
            "weaviate_public_collection": corp.weaviate_public_collection,
            "weaviate_private_collection": corp.weaviate_private_collection,

            # Security
            "enforce_sso": corp.enforce_sso,
            "ip_whitelist_enabled": len(corp.ip_whitelist) > 0,

            # User role
            "role": user.role,
            "is_admin": user.role == "corp_admin"
        }
    else:
        return {
            "is_corporate": False,
            "corporation_id": None,

            # Default routing
            "postgres_connection": None,  # Use default connection
            "postgres_db_name": "intelia_db",

            # Weaviate routing
            "weaviate_collection": "main_knowledge_base",

            # User role
            "role": "user",
            "is_admin": False
        }


async def audit_log(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict,
    request: Request,
    success: bool = True,
    error_message: str = None
):
    """
    Enregistre une action dans les audit logs
    """
    user_context = await get_user_context(user_id)

    # Masquer les PII dans les logs
    safe_details = mask_pii(details)

    log_entry = {
        "user_id": user_id,
        "corporation_id": user_context.get("corporation_id"),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": safe_details,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("User-Agent"),
        "success": success,
        "error_message": error_message
    }

    # Insérer dans audit_logs table
    insert_audit_log(log_entry)
```

### 2.2 Connection Pool PostgreSQL Multi-DB

**Fichier**: `backend/app/core/database_pool.py`

```python
import asyncpg
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class CorporateDatabasePool:
    """
    Gère les connection pools pour chaque DB corporative
    """

    def __init__(self):
        self.pools: Dict[str, asyncpg.Pool] = {}
        self.main_pool = None  # Pool pour DB principale

    async def initialize_main_pool(self, connection_string: str):
        """Initialise le pool pour la DB principale"""
        self.main_pool = await asyncpg.create_pool(connection_string)
        logger.info("Main database pool initialized")

    async def get_pool(self, corporation_id: str = None, connection_string: str = None) -> asyncpg.Pool:
        """
        Retourne le pool approprié selon le contexte
        """
        if corporation_id is None:
            return self.main_pool

        # Check si le pool existe déjà
        if corporation_id in self.pools:
            return self.pools[corporation_id]

        # Créer un nouveau pool pour cette corpo
        if connection_string is None:
            raise ValueError(f"Connection string required for corporation {corporation_id}")

        pool = await asyncpg.create_pool(connection_string)
        self.pools[corporation_id] = pool

        logger.info(f"Created database pool for corporation {corporation_id}")
        return pool

    async def close_all(self):
        """Ferme tous les pools"""
        if self.main_pool:
            await self.main_pool.close()

        for corp_id, pool in self.pools.items():
            await pool.close()
            logger.info(f"Closed pool for corporation {corp_id}")

# Instance globale
db_pool = CorporateDatabasePool()
```

### 2.3 Router Weaviate avec sélection de collection

**Fichier**: `backend/app/core/weaviate_router.py`

```python
import weaviate
from typing import Optional

async def query_weaviate(
    query: str,
    collection_name: str,
    corporation_id: Optional[str] = None,
    user_id: str = None
) -> dict:
    """
    Query Weaviate avec la collection appropriée

    IMPORTANT: Validation stricte pour éviter accès cross-tenant
    """

    # Validation: Vérifier que le user a accès à cette collection
    if corporation_id:
        user = get_user(user_id)
        if user.corporation_id != corporation_id:
            logger.error(f"SECURITY: User {user_id} attempted to access corporation {corporation_id}")
            raise PermissionError("Access denied: Invalid corporation")

        corp = get_corporation(corporation_id)
        allowed_collections = [
            corp.weaviate_public_collection,
            corp.weaviate_private_collection
        ]

        if collection_name not in allowed_collections:
            logger.error(f"SECURITY: User {user_id} attempted to access collection {collection_name}")
            raise PermissionError(f"Access denied: Collection {collection_name} not allowed")

    # Audit log
    await audit_log(
        user_id=user_id,
        action="query_weaviate",
        resource_type="collection",
        resource_id=collection_name,
        details={"query": query[:100]},  # Premier 100 chars seulement
        request=request
    )

    # Query Weaviate
    client = weaviate.Client(url=WEAVIATE_URL)
    result = client.query.get(collection_name, ["content"]).with_near_text({"concepts": [query]}).do()

    return result
```

---

## Phase 3: Endpoints Admin Corporatif

### 3.1 API Routes

**Fichier**: `backend/app/api/v1/corporate.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.corporate_security import get_user_context, validate_ip_whitelist
import secrets

router = APIRouter(prefix="/corporate", tags=["corporate"])


@router.get("/users")
async def list_corporate_users(
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Liste les utilisateurs de la corporation
    Accessible uniquement par corp_admin
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Valider IP whitelist
    await validate_ip_whitelist(request, context["corporation_id"])

    # Récupérer les users de cette corpo
    users = get_users_by_corporation(context["corporation_id"])

    return {"users": users}


@router.post("/users/invite")
async def invite_user(
    email: str,
    role: str,
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Générer un lien d'invitation pour un nouvel utilisateur
    L'admin corpo copie ce lien et l'envoie dans son propre email
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    await validate_ip_whitelist(request, context["corporation_id"])

    # Vérifier que l'email n'existe pas déjà
    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    # Générer token d'invitation sécurisé (expire dans 7 jours)
    invitation_token = secrets.token_urlsafe(32)

    invitation = create_invitation(
        corporation_id=context["corporation_id"],
        email=email,
        role=role,
        token=invitation_token,
        invited_by=current_user_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )

    # Générer le lien d'invitation
    invitation_link = f"https://expert.intelia.com/signup?invite={invitation_token}"

    # Audit log
    await audit_log(
        user_id=current_user_id,
        action="generate_invite_link",
        resource_type="invitation",
        resource_id=email,
        details={"role": role},
        request=request
    )

    # Retourner le lien à copier
    return {
        "invitation_link": invitation_link,
        "expires_at": invitation.expires_at.isoformat(),
        "message": "Copy this link and send it to the user via your own email"
    }


@router.get("/collections")
async def list_collections(
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Liste les collections Weaviate de la corporation
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"]:
        raise HTTPException(status_code=403, detail="Corporate access only")

    return {
        "collections": [
            {
                "name": context["weaviate_public_collection"],
                "type": "public",
                "description": "Accessible via widget (clients externes)"
            },
            {
                "name": context["weaviate_private_collection"],
                "type": "private",
                "description": "Accessible uniquement par employés"
            }
        ]
    }


@router.get("/sso/config")
async def get_sso_config(
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Récupérer la configuration SSO (masquer secrets)
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    sso_config = get_sso_configuration(context["corporation_id"])

    # Masquer les secrets
    return {
        "provider": sso_config.provider,
        "tenant_id": sso_config.tenant_id,
        "client_id": sso_config.client_id,
        "client_secret": "***MASKED***",
        "is_enabled": sso_config.is_enabled
    }


@router.put("/sso/config")
async def update_sso_config(
    config: SSOConfigUpdate,
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Mettre à jour la configuration SSO
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Chiffrer les secrets
    encrypted_secret = encrypt_secret(config.client_secret)

    # Update config
    update_sso_configuration(
        corporation_id=context["corporation_id"],
        tenant_id=config.tenant_id,
        client_id=config.client_id,
        client_secret=encrypted_secret
    )

    # Audit log
    await audit_log(
        user_id=current_user_id,
        action="update_sso_config",
        resource_type="sso_config",
        resource_id=context["corporation_id"],
        details={"provider": "microsoft"},
        request=request
    )

    return {"message": "SSO configuration updated"}


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user)
):
    """
    Récupérer les audit logs de la corporation
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    logs = get_audit_logs_by_corporation(
        corporation_id=context["corporation_id"],
        limit=limit
    )

    return {"logs": logs}


@router.get("/export-gdpr")
async def export_gdpr_data(
    request: Request,
    user_id: Optional[str] = None,
    current_user_id: str = Depends(get_current_user)
):
    """
    Export GDPR - Toutes les données d'un utilisateur en JSON
    Si user_id fourni: export de cet utilisateur (admin corpo seulement)
    Sinon: export de l'utilisateur courant
    """
    context = await get_user_context(current_user_id)

    # Si user_id spécifié, vérifier que c'est un admin corpo
    if user_id and user_id != current_user_id:
        if not context["is_corporate"] or context["role"] != "corp_admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        # Vérifier que le user appartient à la même corpo
        target_user = get_user(user_id)
        if target_user.corporation_id != context["corporation_id"]:
            raise HTTPException(status_code=403, detail="User not in your corporation")
    else:
        user_id = current_user_id

    # Collecter toutes les données
    user_data = get_user(user_id)
    conversations = get_user_conversations(user_id)
    messages = get_user_messages(user_id)
    audit_logs = get_user_audit_logs(user_id)

    gdpr_export = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": str(user_data.id),
            "email": user_data.email,
            "created_at": user_data.created_at.isoformat(),
            "is_corporate": user_data.is_corporate,
            "role": user_data.role
        },
        "conversations": [
            {
                "id": str(conv.id),
                "created_at": conv.created_at.isoformat(),
                "message_count": conv.message_count
            }
            for conv in conversations
        ],
        "messages": [
            {
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ],
        "audit_logs": [
            {
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "resource_type": log.resource_type
            }
            for log in audit_logs
        ]
    }

    # Audit log
    await audit_log(
        user_id=current_user_id,
        action="gdpr_export",
        resource_type="user",
        resource_id=user_id,
        details={},
        request=request
    )

    return JSONResponse(
        content=gdpr_export,
        headers={
            "Content-Disposition": f"attachment; filename=gdpr_export_{user_id}.json"
        }
    )


@router.put("/settings/session-timeout")
async def update_session_timeout(
    timeout_minutes: int,
    request: Request,
    current_user_id: str = Depends(get_current_user)
):
    """
    Configurer le session timeout pour la corporation
    """
    context = await get_user_context(current_user_id)

    if not context["is_corporate"] or context["role"] != "corp_admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Valider la valeur
    if timeout_minutes < 5 or timeout_minutes > 1440:  # 5 min à 24h
        raise HTTPException(status_code=400, detail="Timeout must be between 5 and 1440 minutes")

    # Mettre à jour
    update_corporation_setting(
        corporation_id=context["corporation_id"],
        setting="session_timeout_minutes",
        value=timeout_minutes
    )

    # Audit log
    await audit_log(
        user_id=current_user_id,
        action="update_session_timeout",
        resource_type="corporation",
        resource_id=context["corporation_id"],
        details={"timeout_minutes": timeout_minutes},
        request=request
    )

    return {"message": "Session timeout updated", "timeout_minutes": timeout_minutes}
```

---

## Phase 4: Frontend - Interface Utilisateur

### 4.1 Sélecteur de collection dans le chat

**Fichier**: `frontend/src/components/chat/CollectionSelector.tsx`

```tsx
import React from 'react';

interface CollectionSelectorProps {
  isCorporate: boolean;
  selectedCollection: 'public' | 'private';
  onCollectionChange: (collection: 'public' | 'private') => void;
}

export const CollectionSelector: React.FC<CollectionSelectorProps> = ({
  isCorporate,
  selectedCollection,
  onCollectionChange
}) => {
  if (!isCorporate) return null;

  return (
    <div className="collection-selector">
      <select
        value={selectedCollection}
        onChange={(e) => onCollectionChange(e.target.value as 'public' | 'private')}
      >
        <option value="private">🔒 Private KB (Internal)</option>
        <option value="public">🌐 Public KB (Widget)</option>
      </select>
    </div>
  );
};
```

### 4.2 Page Admin Corporatif

**Fichier**: `frontend/src/pages/CorporateAdmin.tsx`

- Gérer les utilisateurs (inviter, désactiver, voir la liste)
- Configurer SSO Microsoft
- Configurer IP whitelist
- Voir les audit logs
- Export GDPR des données

---

## Phase 5: SSO Microsoft (OAuth)

### 5.1 Configuration Supabase Auth

- Configurer Azure AD comme provider
- Tenant-specific: Chaque corpo a son propre tenant
- Auto-provision users si SSO réussit

### 5.2 Forcer SSO si activé

- Redirection automatique vers Microsoft login
- Empêcher login email/password si `enforce_sso = true`

---

## Phase 6: Widget avec Collection Publique

### 6.1 Modifier Widget API

**Fichier**: `backend/app/api/v1/widget.py`

```python
@router.post("/chat")
async def widget_chat(
    request_body: WidgetChatRequest,
    auth: dict = Depends(get_widget_auth)
):
    client_id = auth.get("client_id")

    # Vérifier si c'est un client corpo
    client = get_widget_client(client_id)

    if client.corporation_id:
        # Client corpo → Utiliser collection publique
        corp = get_corporation(client.corporation_id)
        collection_name = corp.weaviate_public_collection
    else:
        # Client individuel → Collection principale
        collection_name = "main_knowledge_base"

    # Appeler LLM avec la bonne collection
    llm_payload = {
        "message": request_body.message,
        "tenant_id": f"widget_{client_id}",
        "conversation_id": conversation_id,
        "collection_name": collection_name  # 👈 Nouveau paramètre
    }

    # ... rest of the code
```

---

## Phase 7: Backups & Data Residency

### 7.1 Backup Strategy

- **Automatisé via Digital Ocean**: Daily snapshots
- **Région-specific**: Backups dans la même région que les données
- **Retention**: 30 jours minimum
- **Restore**: Process documenté pour super_admin

### 7.2 Multi-région

**Table `regions`**:
```sql
CREATE TABLE regions (
    id UUID PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL, -- 'us-east-1', 'eu-central-1', 'ca-central-1'
    name VARCHAR(100) NOT NULL,
    postgres_host VARCHAR(255) NOT NULL,
    weaviate_host VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true
);
```

---

## Checklist de Sécurité

### Pré-déploiement

- [ ] Tous les secrets chiffrés (SSO credentials, connection strings)
- [ ] Row-Level Security (RLS) activé sur tables partagées
- [ ] IP whitelist testée avec différents scénarios
- [ ] Audit logging actif sur toutes les actions sensibles
- [ ] Rate limiting configuré par corporation
- [ ] Session timeout configuré
- [ ] 2FA optionnel disponible pour admins corpo
- [ ] PII masking dans les logs
- [ ] Tests de pénétration: Essayer d'accéder à data d'une autre corpo

### Post-déploiement

- [ ] Monitoring actif des audit logs
- [ ] Alerts sur tentatives d'accès bloquées (IP whitelist)
- [ ] Alerts sur failed logins répétés
- [ ] Dashboard de sécurité pour super_admin
- [ ] Documentation backup/restore
- [ ] Plan de rotation des credentials SSO

---

## Migration & Déploiement

### Étape 1: Base de données
1. Exécuter migrations SQL (Phase 1)
2. Tester RLS policies
3. Créer première corpo de test

### Étape 2: Backend
1. Déployer middleware de sécurité
2. Déployer connection pool multi-DB
3. Tester routing Weaviate

### Étape 3: Frontend
1. Déployer sélecteur de collection
2. Déployer page admin corpo
3. Tests end-to-end

### Étape 4: SSO
1. Configurer Azure AD
2. Tester SSO avec corpo test
3. Valider enforce_sso

### Étape 5: Widget
1. Modifier widget API
2. Tester avec collection publique
3. Tests de sécurité (isolation)

---

## Questions résolues ✅

1. ✅ **Onboarding processo**: Admin corpo génère un lien d'invitation et l'envoie dans son propre email
2. ✅ **Pricing B2B**: Pas de pricing automatisé - Ententes individuelles par client, facturé via logiciel comptable interne
3. ✅ **Support**: Pas de SLA différencié pour l'instant
4. ✅ **Monitoring**: Pas de dashboard temps réel pour admin corpo (Phase future)
5. ✅ **GDPR**: Export en format JSON
6. ✅ **Nom DB corporative**: Choisi manuellement par super_admin lors de la création
7. ✅ **Collection Weaviate naming**: Choisi manuellement par super_admin lors de la création
8. ✅ **Admin corpo - Limites**: Aucune limite sur nombre d'utilisateurs ou invitations
9. ✅ **Session timeout**: Configurable par admin corpo (pas de min/max)

---

## Prochaines Étapes

**Recommandé**: Commencer par Phase 1 (Schéma SQL)

1. ✅ Créer ce document de plan
2. ⏳ Review du plan avec l'équipe
3. ⏳ Valider approche de sécurité
4. ⏳ Créer migrations SQL (Phase 1)
5. ⏳ Implémenter middleware de sécurité (Phase 2)

---

**Document créé le**: 26 octobre 2025
**Dernière mise à jour**: 26 octobre 2025
**Auteur**: Claude Code (Anthropic)
