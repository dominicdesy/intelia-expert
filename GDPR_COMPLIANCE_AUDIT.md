# 🔒 Audit de Conformité GDPR - Intelia Expert
**Date**: 2025-10-19
**Version**: 1.0
**Auditeur**: Claude Code (Anthropic)

---

## 📋 Résumé Exécutif

| Critère GDPR | Status | Priorité | Risque |
|---|---|---|---|
| **1. Consentement Explicite** | ❌ **NON CONFORME** | 🔴 CRITIQUE | TRÈS ÉLEVÉ |
| **2. Conservation 30 jours** | ❌ **NON CONFORME** | 🔴 CRITIQUE | TRÈS ÉLEVÉ |
| **3. Minimisation des logs** | ⚠️ **PARTIELLEMENT CONFORME** | 🟡 MOYENNE | MOYEN |
| **4. Droit à l'Oubli** | ⚠️ **PARTIELLEMENT CONFORME** | 🟡 MOYENNE | MOYEN |
| **5. Portabilité des Données** | ✅ **CONFORME** | 🟢 FAIBLE | FAIBLE |
| **6. Chiffrement Transit/Repos** | ✅ **CONFORME** | 🟢 FAIBLE | FAIBLE |
| **7. Notification Breach** | ❌ **NON CONFORME** | 🔴 CRITIQUE | ÉLEVÉ |
| **8. DPO / Contact GDPR** | ❌ **NON CONFORME** | 🔴 CRITIQUE | MOYEN |

**Score Global**: 3/8 = **37.5% conforme** ⚠️

---

## 🔴 PROBLÈMES CRITIQUES (Action Immédiate Requise)

### ❌ CRITIQUE #1: Consentement Explicite Absent

**Fichier**: `frontend/app/page_signup_modal.tsx` (lignes 854-873)

**Problème Actuel**:
```tsx
// ❌ PROBLÈME: Simple texte informatif, PAS de checkbox
<p className="text-xs text-gray-500 leading-relaxed">
  {safeT("gdpr.signupNotice")}{" "}
  <a href="/terms">...</a>
  <a href="/privacy">...</a>
</p>
```

**Impact GDPR**:
- ❌ **Article 7 GDPR**: Pas de consentement explicite et démontrable
- ❌ **Article 4(11)**: Le consentement doit être "une action positive claire"
- ❌ **Amende potentielle**: Jusqu'à 20M€ ou 4% CA mondial

**Solution Requise**:
```tsx
// ✅ SOLUTION: Checkbox obligatoire + validation
const [acceptTerms, setAcceptTerms] = useState(false);

<label className="flex items-start space-x-3">
  <input
    type="checkbox"
    checked={acceptTerms}
    onChange={(e) => setAcceptTerms(e.target.checked)}
    required
    className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded"
  />
  <span className="text-xs text-gray-700">
    J'accepte les{" "}
    <a href="/terms" className="text-blue-600 underline">
      Conditions d'utilisation
    </a>
    {" "}et la{" "}
    <a href="/privacy" className="text-blue-600 underline">
      Politique de confidentialité
    </a>
  </span>
</label>

// Désactiver le bouton si non coché
<button
  disabled={!acceptTerms || isLoading}
  onClick={handleSignup}
>
  Créer mon compte
</button>
```

**Backend - Sauvegarder le consentement**:
```sql
-- Ajouter colonne dans users table
ALTER TABLE users ADD COLUMN consent_timestamp TIMESTAMP DEFAULT NOW();
ALTER TABLE users ADD COLUMN consent_version VARCHAR(50); -- "v1.0-2025-10-19"
ALTER TABLE users ADD COLUMN consent_ip_address VARCHAR(45); -- IPv4/IPv6
```

**Estimation**: 2-3 heures de dev + test

---

### ❌ CRITIQUE #2: Aucune Politique de Conservation (30 jours)

**Problème**: Aucun script automatique de suppression des données après 30 jours.

**Tables Concernées**:
- `conversations` (historique complet conservé indéfiniment)
- `messages` (tous les messages conservés)
- `monthly_usage_tracking` (statistiques conservées)
- `sessions` (sessions expirées non nettoyées)
- Logs applicatifs (non purgés)

**Impact GDPR**:
- ❌ **Article 5(1)(e)**: Limitation de la conservation
- ❌ **Amende potentielle**: 10M€ ou 2% CA mondial

**Solution Requise - Script de Nettoyage Automatique**:

Créer `backend/scripts/gdpr_data_retention.py`:
```python
#!/usr/bin/env python3
"""
GDPR Data Retention Policy - Auto-delete after 30 days
Runs daily via cron job
"""
import asyncpg
import os
from datetime import datetime, timedelta

async def cleanup_old_data():
    """Delete user data older than 30 days"""

    retention_days = int(os.getenv("GDPR_RETENTION_DAYS", "30"))
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    try:
        # 1. Supprimer vieilles conversations (> 30 jours)
        deleted_conversations = await conn.execute(
            """
            DELETE FROM conversations
            WHERE created_at < $1
            AND status != 'archived'  -- Garder archives explicites
            """,
            cutoff_date
        )

        # 2. Supprimer vieux messages orphelins
        deleted_messages = await conn.execute(
            """
            DELETE FROM messages
            WHERE conversation_id NOT IN (SELECT id FROM conversations)
            """
        )

        # 3. Supprimer vieilles sessions expirées (> 7 jours)
        session_cutoff = datetime.now() - timedelta(days=7)
        deleted_sessions = await conn.execute(
            """
            DELETE FROM sessions
            WHERE last_activity_at < $1
            AND status = 'expired'
            """,
            session_cutoff
        )

        # 4. Anonymiser logs utilisateurs (> 90 jours)
        log_cutoff = datetime.now() - timedelta(days=90)
        # Note: Si vous avez une table de logs

        print(f"✅ GDPR Cleanup completed:")
        print(f"  - Conversations deleted: {deleted_conversations}")
        print(f"  - Messages deleted: {deleted_messages}")
        print(f"  - Sessions deleted: {deleted_sessions}")

    finally:
        await conn.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(cleanup_old_data())
```

**Cron Job** (à ajouter sur le serveur):
```bash
# Exécuter tous les jours à 3h du matin
0 3 * * * cd /path/to/backend && python3 scripts/gdpr_data_retention.py >> /var/log/gdpr_cleanup.log 2>&1
```

**Endpoint API pour déclencher manuellement**:
```python
# backend/app/api/v1/admin.py
@router.post("/admin/gdpr/cleanup")
async def trigger_gdpr_cleanup(current_user: Dict = Depends(require_admin)):
    """Déclenche le nettoyage GDPR manuellement (admin only)"""
    # Exécuter le script de nettoyage
    subprocess.run(["python3", "scripts/gdpr_data_retention.py"])
    return {"success": True, "message": "GDPR cleanup triggered"}
```

**Estimation**: 4-6 heures de dev + test + déploiement cron

---

### ❌ CRITIQUE #3: Notification de Violation (Breach Notification)

**Problème**: Aucun mécanisme pour détecter et notifier les violations de données.

**Impact GDPR**:
- ❌ **Article 33**: Notification à l'autorité de contrôle dans les 72h
- ❌ **Article 34**: Notification aux personnes concernées si risque élevé
- ❌ **Amende potentielle**: 10M€ ou 2% CA mondial

**Solution Requise**:

Créer `backend/app/services/gdpr_breach_notifier.py`:
```python
"""
GDPR Breach Detection & Notification Service
Monitors suspicious activities and triggers alerts
"""
import logging
from datetime import datetime
from typing import Dict, List
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

class GDPRBreachNotifier:
    """Détecte et notifie les violations GDPR"""

    BREACH_EMAIL = "dpo@intelia.com"  # À configurer
    CNIL_EMAIL = "violations@cnil.fr"  # Autorité française

    def __init__(self):
        self.breach_log = []

    async def detect_suspicious_activity(self, event: Dict):
        """Détecte activités suspectes"""
        suspicious = False
        reason = ""

        # 1. Tentatives multiples de connexion échouées
        if event.get("failed_login_attempts", 0) > 10:
            suspicious = True
            reason = "Multiple failed login attempts"

        # 2. Accès à des données sensibles en masse
        if event.get("records_accessed", 0) > 1000:
            suspicious = True
            reason = "Mass data access detected"

        # 3. Modification inhabituelle de permissions
        if event.get("permission_changes", 0) > 5:
            suspicious = True
            reason = "Unusual permission modifications"

        if suspicious:
            await self.log_potential_breach(event, reason)

    async def log_potential_breach(self, event: Dict, reason: str):
        """Enregistre une violation potentielle"""
        breach_entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "event": event,
            "severity": self._assess_severity(event)
        }

        self.breach_log.append(breach_entry)

        # Si sévérité élevée → notification immédiate
        if breach_entry["severity"] == "HIGH":
            await self.notify_breach(breach_entry)

    def _assess_severity(self, event: Dict) -> str:
        """Évalue la gravité: LOW, MEDIUM, HIGH"""
        if event.get("records_accessed", 0) > 10000:
            return "HIGH"
        elif event.get("records_accessed", 0) > 1000:
            return "MEDIUM"
        return "LOW"

    async def notify_breach(self, breach: Dict):
        """Notifie le DPO et potentiellement la CNIL"""

        # 1. Alerter le DPO immédiatement
        await self._send_email(
            to=self.BREACH_EMAIL,
            subject=f"🚨 ALERTE GDPR: Violation Potentielle Détectée",
            body=f"""
            Une violation potentielle des données a été détectée:

            Timestamp: {breach['timestamp']}
            Sévérité: {breach['severity']}
            Raison: {breach['reason']}

            Détails:
            {breach['event']}

            Action requise: Investiguer dans les 72h (Article 33 GDPR)
            """
        )

        logger.critical(f"🚨 GDPR BREACH DETECTED: {breach['reason']}")

    async def _send_email(self, to: str, subject: str, body: str):
        """Envoie email d'alerte"""
        # Implémenter avec votre service email existant
        pass
```

**Intégration dans le middleware**:
```python
# backend/app/middleware/auth_middleware.py
from app.services.gdpr_breach_notifier import GDPRBreachNotifier

breach_notifier = GDPRBreachNotifier()

async def check_suspicious_activity(user_email: str):
    """Check après chaque requête"""
    event = {
        "user_email": user_email,
        "timestamp": datetime.now(),
        "failed_login_attempts": get_failed_attempts(user_email),
        # ...
    }
    await breach_notifier.detect_suspicious_activity(event)
```

**Estimation**: 6-8 heures de dev + configuration alertes

---

### ❌ CRITIQUE #4: Absence de DPO / Contact GDPR

**Problème**: Aucun contact GDPR visible pour les utilisateurs.

**Impact GDPR**:
- ❌ **Article 37-39**: Obligation de désigner un DPO (selon la taille/activité)
- ❌ **Article 13**: Informer les utilisateurs du contact DPO

**Solution Requise**:

**1. Page Contact GDPR** (`frontend/app/gdpr/page.tsx`):
```tsx
export default function GDPRContactPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-6">
        Protection des Données Personnelles
      </h1>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Délégué à la Protection des Données (DPO)</h2>
        <p className="mb-2">
          Pour toute question concernant vos données personnelles, vous pouvez contacter notre DPO:
        </p>
        <ul className="space-y-2">
          <li>📧 Email: <a href="mailto:dpo@intelia.com" className="text-blue-600">dpo@intelia.com</a></li>
          <li>📞 Téléphone: +33 1 XX XX XX XX</li>
          <li>✉️ Courrier: Intelia Technologies, DPO, [Adresse Complète]</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Vos Droits GDPR</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong>Droit d'accès</strong>: Obtenir une copie de vos données</li>
          <li><strong>Droit de rectification</strong>: Corriger vos données inexactes</li>
          <li><strong>Droit à l'effacement</strong>: Supprimer vos données ("droit à l'oubli")</li>
          <li><strong>Droit à la portabilité</strong>: Recevoir vos données dans un format structuré</li>
          <li><strong>Droit d'opposition</strong>: Vous opposer au traitement de vos données</li>
          <li><strong>Droit de limitation</strong>: Limiter le traitement de vos données</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Exercer vos Droits</h2>
        <p className="mb-4">
          Pour exercer vos droits, envoyez un email à <strong>dpo@intelia.com</strong> avec:
        </p>
        <ul className="list-disc pl-6 space-y-2">
          <li>Votre nom et prénom</li>
          <li>Votre adresse email associée à votre compte</li>
          <li>Le droit que vous souhaitez exercer</li>
          <li>Une pièce d'identité (pour vérification)</li>
        </ul>
        <p className="mt-4 text-sm text-gray-600">
          Nous nous engageons à répondre dans un délai de <strong>1 mois</strong> (Article 12 GDPR).
        </p>
      </section>
    </div>
  );
}
```

**2. Ajouter lien dans footer/privacy**:
```tsx
<Link href="/gdpr">Contact GDPR / DPO</Link>
```

**Estimation**: 1-2 heures

---

## 🟡 PROBLÈMES MOYENS (Action Recommandée)

### ⚠️ MOYEN #1: Logs Contenant des Emails en Clair

**Fichiers Problématiques**:
- `backend/app/services/email_service.py:578` - Email loggé en clair
- `backend/app/services/usage_limiter.py:92` - Email loggé
- `backend/app/api/v1/auth.py:329` - Email loggé

**Problème**:
```python
# ❌ ACTUEL: Email en clair dans les logs
logger.info(f"✅ Email sent successfully to {to_email}")
logger.warning(f"Aucun plan trouvé pour {user_email}")
```

**Solution**:
```python
# ✅ SOLUTION: Hasher ou masquer l'email
def mask_email(email: str) -> str:
    """Masque l'email: john.doe@example.com -> j***e@e***e.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@")
    return f"{local[0]}***{local[-1] if len(local) > 1 else ''}@{domain[0]}***{domain.split('.')[-1]}"

# Usage
logger.info(f"✅ Email sent to {mask_email(to_email)}")
```

**Estimation**: 2-3 heures (rechercher tous les logs + remplacer)

---

### ⚠️ MOYEN #2: Droit à l'Oubli Incomplet

**Problème Actuel** (`backend/app/api/v1/users.py:381-421`):
```python
# ❌ Supprime SEULEMENT la table users, pas les autres données
supabase.table("users").delete().eq("auth_user_id", current_user["user_id"]).execute()
```

**Tables Non Supprimées**:
- ❌ `conversations` (historique complet)
- ❌ `messages` (tous les messages)
- ❌ `monthly_usage_tracking` (stats usage)
- ❌ `stripe_subscriptions` (données billing)
- ❌ `sessions` (sessions actives)
- ❌ `passkeys` (clés biométriques)

**Solution - Suppression en Cascade**:
```python
@router.delete("/profile/complete")
async def delete_user_complete_gdpr(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Suppression COMPLÈTE des données utilisateur (GDPR Article 17)
    Supprime TOUTES les données liées à l'utilisateur
    """
    user_id = current_user["user_id"]
    email = current_user["email"]

    logger.warning(f"🗑️ GDPR DELETE REQUEST: User {email} requesting complete data deletion")

    try:
        supabase = get_supabase_admin_client()

        # 1. Supprimer conversations + messages (cascade)
        conversations = supabase.table("conversations").select("id").eq("user_id", user_id).execute()
        for conv in conversations.data:
            # Supprimer messages de cette conversation
            supabase.table("messages").delete().eq("conversation_id", conv["id"]).execute()

        # Supprimer les conversations
        supabase.table("conversations").delete().eq("user_id", user_id).execute()

        # 2. Supprimer usage tracking
        supabase.table("monthly_usage_tracking").delete().eq("user_email", email).execute()

        # 3. Supprimer stripe subscriptions (garder pour compliance fiscal si nécessaire)
        # NOTE: Consulter un avocat - les données de facturation peuvent être conservées 10 ans
        supabase.table("stripe_subscriptions").update({"status": "deleted"}).eq("user_email", email).execute()

        # 4. Supprimer sessions
        supabase.table("sessions").delete().eq("user_id", user_id).execute()

        # 5. Supprimer passkeys
        supabase.table("passkeys").delete().eq("user_id", user_id).execute()

        # 6. Supprimer profil utilisateur
        supabase.table("users").delete().eq("auth_user_id", user_id).execute()

        # 7. Supprimer compte auth
        try:
            supabase.auth.admin.delete_user(user_id)
        except Exception as e:
            logger.error(f"Auth deletion failed: {e}")

        # 8. Logger la suppression (pour audit)
        logger.warning(f"✅ GDPR DELETE COMPLETED: All data for {mask_email(email)} deleted")

        return {
            "success": True,
            "message": "Toutes vos données ont été supprimées conformément au GDPR",
            "deleted_items": {
                "conversations": len(conversations.data),
                "profile": 1,
                "sessions": "all",
                "usage_tracking": "all"
            }
        }

    except Exception as e:
        logger.error(f"GDPR deletion failed for {email}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression")
```

**Frontend - Bouton de Suppression**:
```tsx
// frontend/app/profile/page.tsx
const handleDeleteAccount = async () => {
  const confirmed = window.confirm(
    "⚠️ ATTENTION: Cette action est IRRÉVERSIBLE.\n\n" +
    "Toutes vos données seront définitivement supprimées:\n" +
    "- Profil utilisateur\n" +
    "- Historique de conversations\n" +
    "- Messages\n" +
    "- Statistiques d'utilisation\n\n" +
    "Confirmez-vous la suppression complète de votre compte?"
  );

  if (!confirmed) return;

  // Double confirmation
  const finalConfirm = window.confirm(
    "Dernière confirmation:\n" +
    "Êtes-vous ABSOLUMENT SÛR de vouloir supprimer votre compte?"
  );

  if (!finalConfirm) return;

  try {
    await fetch("/v1/users/profile/complete", {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${token}` }
    });

    alert("Votre compte a été supprimé. Vous allez être déconnecté.");
    // Déconnecter et rediriger
    logout();
    router.push("/");
  } catch (error) {
    alert("Erreur lors de la suppression. Contactez dpo@intelia.com");
  }
};

<button
  onClick={handleDeleteAccount}
  className="bg-red-600 text-white px-4 py-2 rounded"
>
  🗑️ Supprimer mon compte (GDPR)
</button>
```

**Estimation**: 4-5 heures

---

## ✅ POINTS CONFORMES

### ✅ BON #1: Portabilité des Données (Article 20)

**Fichier**: `backend/app/api/v1/users.py:424-468`

✅ Endpoint `/users/export` permet d'exporter toutes les données utilisateur
✅ Format JSON structuré
✅ Inclut profil + invitations

**Amélioration Suggérée** - Ajouter conversations:
```python
# Ajouter dans export_user_data()
conversations_response = (
    supabase.table("conversations")
    .select("*, messages(*)")
    .eq("user_id", current_user["user_id"])
    .execute()
)

export_data["conversations"] = conversations_response.data
```

---

### ✅ BON #2: Chiffrement en Transit (HTTPS/TLS)

**Fichier**: `backend/app/middleware/auth_middleware.py`

✅ Utilisation de HTTPS pour toutes les connexions
✅ Tokens JWT sécurisés
✅ Passwords non loggés

---

## 📊 AUTRES RISQUES IDENTIFIÉS

### 🔍 RISQUE #1: Transferts Internationaux de Données

**Problème Potentiel**: Si vous utilisez des services hors UE (AWS US, etc.)

**Vérifications Nécessaires**:
- ☐ Où sont hébergées les bases de données? (DigitalOcean? AWS? Région?)
- ☐ Utilisez-vous des services tiers hors UE? (OpenAI, Stripe, etc.)
- ☐ Clauses contractuelles types (SCC) en place?

**Si hors UE**:
- Mettre en place des **Standard Contractual Clauses (SCC)**
- Informer les utilisateurs dans la politique de confidentialité
- Évaluer le **Transfer Impact Assessment (TIA)**

---

### 🔍 RISQUE #2: Cookies et Trackers

**Vérification à Faire**:
```bash
# Chercher les cookies/trackers
grep -r "cookie\|localStorage\|sessionStorage\|analytics\|gtag\|facebook.*pixel" frontend/
```

**Si présents**:
- ❌ Implémenter un **cookie banner** avec consentement granulaire
- ❌ Ne PAS charger Google Analytics / Facebook Pixel avant consentement
- ❌ Permettre retrait du consentement à tout moment

---

### 🔍 RISQUE #3: Sous-Traitants GDPR

**Article 28**: Contrats avec sous-traitants (DPA - Data Processing Agreement)

**Vérifier si vous avez des DPA signés avec**:
- ☐ Hébergeur (DigitalOcean, AWS, etc.)
- ☐ Service Email (SendGrid, Mailgun, etc.)
- ☐ OpenAI (pour le LLM)
- ☐ Stripe (paiements)
- ☐ Tout autre service traitant des données utilisateurs

**Action**: Signer des DPA avec tous les sous-traitants

---

## 🎯 PLAN D'ACTION PRIORITAIRE

### Phase 1: URGENT (1-2 semaines)

1. **Consentement Explicite** (2-3h)
   - Ajouter checkbox Terms + Privacy
   - Sauvegarder consent_timestamp en DB

2. **Masquer Emails dans Logs** (2-3h)
   - Créer fonction `mask_email()`
   - Remplacer tous les logs d'emails

3. **Contact DPO** (1-2h)
   - Créer page `/gdpr`
   - Ajouter email DPO: `dpo@intelia.com`

### Phase 2: IMPORTANT (2-4 semaines)

4. **Auto-Delete 30 jours** (4-6h)
   - Script `gdpr_data_retention.py`
   - Cron job quotidien
   - Endpoint admin manuel

5. **Droit à l'Oubli Complet** (4-5h)
   - Endpoint `/profile/complete` DELETE
   - Suppression en cascade de toutes les tables
   - UI de confirmation

6. **Breach Notification** (6-8h)
   - Service `GDPRBreachNotifier`
   - Monitoring activités suspectes
   - Alertes automatiques

### Phase 3: COMPLIANCE (1-2 mois)

7. **Portabilité Complète** (2h)
   - Ajouter conversations + messages à l'export

8. **Cookie Banner** (si applicable)
   - Implémenter si vous utilisez des trackers

9. **DPA Sous-Traitants**
   - Signer contrats avec tous les services tiers

10. **Documentation**
    - Registre des traitements (Article 30)
    - Privacy Impact Assessment (PIA) si nécessaire

---

## 📝 CHECKLIST FINALE GDPR

### Conformité Minimale

- [ ] ✅ Checkbox consentement explicite à l'inscription
- [ ] ✅ Politique de confidentialité complète et accessible
- [ ] ✅ Conditions d'utilisation complètes
- [ ] ✅ Contact DPO visible (email: dpo@intelia.com)
- [ ] ✅ Droit d'accès (export données)
- [ ] ✅ Droit de rectification (modifier profil)
- [ ] ✅ Droit à l'effacement (supprimer compte + toutes données)
- [ ] ✅ Droit à la portabilité (export JSON)
- [ ] ✅ Auto-delete après 30 jours (conversations/messages)
- [ ] ✅ Logs minimisés (pas d'emails en clair)
- [ ] ✅ Chiffrement transit (HTTPS/TLS)
- [ ] ✅ Chiffrement au repos (si applicable)
- [ ] ✅ Notification breach (mécanisme en place)
- [ ] ✅ DPA signés avec sous-traitants
- [ ] ✅ Registre des traitements (Article 30)
- [ ] ✅ Base légale documentée pour chaque traitement

### Bonus (Recommandé)

- [ ] Cookie banner avec consentement granulaire
- [ ] Privacy Impact Assessment (PIA)
- [ ] Formation GDPR pour l'équipe
- [ ] Audit externe de conformité
- [ ] Certification (ISO 27001, etc.)

---

## 💰 ESTIMATION BUDGÉTAIRE

| Phase | Tâches | Temps Dev | Coût Estimé* |
|---|---|---|---|
| **Phase 1 (Urgent)** | Consentement + Logs + DPO | 6-8h | 1000-1500€ |
| **Phase 2 (Important)** | Auto-delete + Oubli + Breach | 14-19h | 2500-3500€ |
| **Phase 3 (Compliance)** | Export + Docs + DPA | 10-15h | 1500-2500€ |
| **Audit Externe** | Consultant GDPR | - | 3000-8000€ |
| **TOTAL** | - | **30-42h** | **8000-15500€** |

*Basé sur taux horaire dev 150€/h + consultant GDPR

---

## 📞 CONTACTS UTILES

**Autorité de Contrôle France**:
- CNIL: https://www.cnil.fr
- Email: violations@cnil.fr (notifications breach)
- Téléphone: +33 1 53 73 22 22

**Ressources**:
- Guide CNIL: https://www.cnil.fr/fr/rgpd-par-ou-commencer
- Texte GDPR: https://gdpr-info.eu
- Modèles DPA: https://ec.europa.eu/info/law/law-topic/data-protection/international-dimension-data-protection/standard-contractual-clauses-scc_en

---

**Généré par**: Claude Code (Anthropic)
**Date**: 2025-10-19
**Version**: 1.0

⚠️ **AVERTISSEMENT**: Ceci est un audit technique, pas un avis juridique. Consultez un avocat spécialisé GDPR pour validation finale.
