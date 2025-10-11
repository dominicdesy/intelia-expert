# 🔒 Analyse de Sécurité Complète avec Outils Automatisés

**Date**: 2025-10-11
**Outils utilisés**: Bandit, pip-audit, analyse manuelle

---

## 📊 Résumé Exécutif

### Score Global de Sécurité: **6.5/10** (RISQUE MODÉRÉ)

**Problèmes critiques identifiés**:
- ✅ **0 vulnérabilités HIGH** dans le code (Bandit)
- ⚠️ **6 vulnérabilités MEDIUM** (potentielles injections SQL)
- ⚠️ **7 vulnérabilités LOW** (bonnes pratiques)
- 🔴 **17 endpoints non protégés** exposant données sensibles
- 🔴 **Secret JWT de fallback hardcodé**
- 🔴 **Pas de Row-Level Security (RLS)** dans la base de données

---

## 🛠️ Résultats Bandit (Analyseur de Sécurité Python)

### Statistiques Globales
- **Lignes de code analysées**: 13,038
- **Fichiers scannés**: 33
- **Issues trouvées**: 13
  - HIGH Confidence: 4
  - MEDIUM Confidence: 5
  - LOW Confidence: 4

### Issues Critiques à Corriger

#### 1. **Injections SQL Potentielles** (MEDIUM - 4 occurrences)

**Fichiers concernés**:
- `app/api/v1/logging.py:607` - Construction dynamique de requête
- `app/api/v1/logging.py:613` - f-string dans requête SQL
- `app/api/v1/logging_endpoints.py:489` - Table name non sanitisé
- `app/api/v1/stats_fast_OLD_backup.py:665,678` - Backup file (à supprimer)

**Exemple du problème**:
```python
# ❌ RISQUE D'INJECTION SQL
count_query = f"SELECT COUNT(*) FROM user_questions_complete {where_clause}"

# ✅ CORRECTION
count_query = "SELECT COUNT(*) FROM user_questions_complete WHERE created_at >= %s"
params = [start_date]
```

**Action requise**: Remplacer f-strings par paramètres dans toutes les requêtes SQL.

---

#### 2. **Try/Except Vides** (LOW - 4 occurrences)

**Fichiers**:
- `app/api/v1/auth.py:377,1607` - Exceptions silencieuses lors du décodage JWT
- `app/api/v1/invitations.py:161` - Erreur de décodage non loggée
- `app/api/v1/utils/openai_utils.py:598` - Try/except/pass

**Problème**: Les erreurs sont ignorées sans logging, rendant le debug impossible.

**Correction**:
```python
# ❌ MAUVAIS
except Exception:
    continue

# ✅ BON
except Exception as e:
    logger.warning(f"Erreur décodage: {e}")
    continue
```

---

#### 3. **Binding sur Toutes les Interfaces** (MEDIUM)

**Fichier**: `app/main.py:857`

```python
# ❌ RISQUE - Accessible depuis internet
uvicorn.run(app, host="0.0.0.0", port=8080)

# ✅ CORRECTION - Utiliser un reverse proxy
uvicorn.run(app, host="127.0.0.1", port=8080)
```

**Recommandation**: Utiliser Nginx/Caddy comme reverse proxy et binder uniquement sur localhost.

---

#### 4. **Faux Positifs Bandit** (Peut être ignoré)

Ces warnings sont des **faux positifs** de Bandit:
- `token_type="bearer"` détecté comme mot de passe (c'est un type OAuth standard)
- `PASSWORD_RESET = "recovery"` détecté comme mot de passe (c'est un enum)

**Action**: Aucune - faux positifs.

---

## 🔐 Protection des Données Personnelles (RGPD/GDPR)

### Données Personnelles Identifiées dans le Code

**1,180 occurrences** de champs sensibles trouvés dans 25 fichiers:

| Type de Donnée | Occurrences | Fichiers Principaux |
|----------------|-------------|---------------------|
| Email | ~350 | auth.py, users.py, invitations.py |
| Name (first/last) | ~200 | auth.py, users.py, email_service.py |
| Phone | ~80 | users.py, auth.py |
| Password | ~150 | auth.py (hashage requis) |
| Address/Country | ~50 | users.py |
| Credit Card | 0 | ✅ Aucune - bon signe |

---

### ✅ Bonnes Pratiques RGPD Déjà Implémentées

1. **Hashage des mots de passe**:
   - ✅ Supabase gère le hashage (bcrypt)
   - ✅ Pas de stockage en clair

2. **Consentement explicite**:
   - ✅ Champ `consent_given` dans table `users`
   - ✅ Champ `consent_date` pour tracking

3. **Droit à l'oubli**:
   - ✅ Endpoint `/auth/delete-data` implémenté
   - ⚠️ Mais ne supprime pas réellement les données (seulement un log)

4. **Export des données**:
   - ✅ Endpoint `/users/export` pour récupérer toutes les données

5. **Anonymisation**:
   - ✅ Logs utilisent `user_email` au lieu de noms complets
   - ⚠️ Pas d'anonymisation après suppression

---

### 🔴 Violations RGPD Critiques

#### 1. **Fuite d'Emails dans Logs** (Article 32 - Sécurité)

**Problème**: Les emails sont loggés en clair dans tous les endpoints.

```python
# ❌ RISQUE GDPR
logger.info(f"Login réussi pour: {request.email}")
logger.info(f"Utilisateur: {email} (ID: {user_id})")
```

**Impact**: Si les logs sont compromis, tous les emails sont exposés.

**Correction**:
```python
# ✅ HASHAGE OU TRUNCATION
email_hash = hashlib.sha256(email.encode()).hexdigest()[:8]
logger.info(f"Login réussi pour: {email_hash}")

# ✅ OU MASQUAGE
masked_email = email[:3] + "***" + email.split("@")[1]
logger.info(f"Login réussi pour: {masked_email}")
```

---

#### 2. **Pas de Chiffrement au Repos** (Article 32)

**Problème**: Les données personnelles en base ne sont PAS chiffrées.

**Base de données**:
- PostgreSQL: ❌ Pas de chiffrement TDE (Transparent Data Encryption)
- Supabase: ✅ Chiffrement par défaut (mais vérifie la config)

**Correction**:
```sql
-- PostgreSQL: Activer pgcrypto pour colonnes sensibles
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE users
ADD COLUMN phone_encrypted BYTEA;

-- Chiffrer lors de l'insertion
INSERT INTO users (phone_encrypted)
VALUES (pgp_sym_encrypt('555-1234', 'encryption_key'));
```

---

#### 3. **Durée de Conservation Non Définie** (Article 5.1.e)

**Problème**: Aucune politique de suppression automatique des données.

**Action requise**:
```python
# Créer un job de nettoyage automatique
# backend/app/jobs/gdpr_cleanup.py

from datetime import datetime, timedelta

def cleanup_old_data():
    """Supprime les données > 2 ans (exemple)"""
    cutoff_date = datetime.now() - timedelta(days=730)

    # Anonymiser anciennes conversations
    db.execute("""
        UPDATE conversations
        SET user_id = NULL,
            title = 'Anonymized'
        WHERE created_at < %s
    """, (cutoff_date,))
```

---

#### 4. **Transfert International de Données** (Article 44-50)

**Problème**: Pas de mention de l'hébergement des données.

**À vérifier**:
- DigitalOcean: Quelle région? (EU/US/Autre)
- Supabase: Quelle région? (EU/US/Autre)

**Action requise**:
- Si hors UE → Implémenter Standard Contractual Clauses (SCC)
- Ajouter mention dans Privacy Policy
- Obtenir consentement explicite pour transfert

---

#### 5. **Pas de Traçabilité des Accès** (Article 30)

**Problème**: Aucun audit log des accès aux données personnelles.

**Correction**:
```python
# Créer table d'audit
CREATE TABLE data_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    accessed_by UUID,
    action TEXT,  -- 'read', 'update', 'delete'
    data_type TEXT,  -- 'email', 'phone', 'profile'
    ip_address INET,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

# Middleware pour tracker accès
@app.middleware("http")
async def audit_personal_data(request, call_next):
    if "users" in request.url.path or "profile" in request.url.path:
        log_data_access(request)
    return await call_next(request)
```

---

## 🛡️ Outils de Sécurité Recommandés

### 1. **Bandit** (✅ Déjà utilisé)
```bash
# Installation
pip install bandit

# Scan complet avec rapport JSON
bandit -r app/ -f json -o bandit_report.json

# Scan avec sévérité >= MEDIUM
bandit -r app/ -ll -f csv -o security_report.csv
```

**Avantages**:
- Détecte injections SQL, secrets hardcodés, crypto faible
- Intégration CI/CD facile
- Faux positifs gérables

---

### 2. **Safety** (Vulnérabilités des dépendances)
```bash
# Installation
pip install safety

# Scan des vulnérabilités
safety check --json > safety_report.json

# Scan avec détails complets
safety check --full-report
```

**Détecte**: CVE dans packages (Django, FastAPI, etc.)

---

### 3. **pip-audit** (✅ Déjà utilisé)
```bash
# Installation
pip install pip-audit

# Audit complet
pip-audit --format json > pip_audit_report.json

# Fix automatique (si possible)
pip-audit --fix
```

---

### 4. **Semgrep** (Analyse de code avancée)
```bash
# Installation
pip install semgrep

# Scan avec règles Python/FastAPI
semgrep --config=auto app/

# Règles OWASP Top 10
semgrep --config "p/owasp-top-ten" app/
```

**Avantages**:
- Détecte patterns complexes (race conditions, auth bypass)
- Règles custom possibles
- Moins de faux positifs que Bandit

---

### 5. **Trivy** (Scan containers Docker)
```bash
# Installation
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh

# Scan image Docker
trivy image intelia-expert-backend:latest

# Scan Dockerfile
trivy config Dockerfile
```

---

### 6. **SQLMap** (Test d'injection SQL)
```bash
# Installation
pip install sqlmap

# Test endpoint
sqlmap -u "https://expert.intelia.com/api/v1/questions?search=test" \
       --cookie "token=..." --batch
```

**⚠️ À utiliser UNIQUEMENT en environnement de test!**

---

### 7. **Gitleaks** (Secrets dans Git)
```bash
# Installation
brew install gitleaks  # macOS
# ou télécharger depuis GitHub

# Scan repo complet
gitleaks detect --source . --verbose

# Scan avant commit (pre-commit hook)
gitleaks protect --staged
```

**Détecte**:
- Clés API, tokens, mots de passe dans commits
- Secrets dans .env committé par erreur

---

### 8. **OWASP ZAP** (Scan dynamique)

Outil GUI pour tester l'application en cours d'exécution.

```bash
# Lancer ZAP
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable \
    zap-baseline.py -t https://expert.intelia.com -r zap_report.html
```

**Détecte**:
- XSS, CSRF, injections SQL
- Configurations HTTP incorrectes
- Failles d'authentification

---

## 🔧 Plan d'Action Priorisé

### 🔴 PRIORITÉ 1 (Immédiat - Cette semaine)

1. **Supprimer secret JWT de fallback hardcodé**
   ```python
   # app/api/v1/auth.py ligne 57
   if not JWT_SECRETS:
       raise RuntimeError("❌ FATAL: Aucun JWT secret configuré")
   ```

2. **Protéger endpoints exposés**
   ```python
   # Ajouter Depends(get_current_user) à:
   # - /billing/openai-usage/*
   # - /invitations/stats/summary-all
   # - /system/metrics
   ```

3. **Supprimer fichiers de backup**
   ```bash
   rm app/api/v1/stats_fast_OLD_backup.py
   ```

4. **Activer webhook signature validation**
   ```python
   # app/api/v1/webhooks.py
   PERMISSIVE_MODE = False  # Changer à False
   ```

---

### 🟠 PRIORITÉ 2 (Cette semaine)

1. **Corriger injections SQL potentielles**
   - Remplacer f-strings par paramètres
   - Fichiers: `logging.py`, `logging_endpoints.py`

2. **Ajouter logging des exceptions**
   ```python
   except Exception as e:
       logger.error(f"Erreur: {e}", exc_info=True)
   ```

3. **Implémenter audit log GDPR**
   - Créer table `data_access_log`
   - Logger tous accès à données personnelles

4. **Masquer emails dans logs**
   ```python
   def mask_email(email):
       return email[:3] + "***@" + email.split("@")[1]
   ```

---

### 🟡 PRIORITÉ 3 (Ce mois)

1. **Activer Row-Level Security (RLS)**
   ```sql
   ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

   CREATE POLICY conversations_isolation ON conversations
       USING (user_id = current_user_id());
   ```

2. **Chiffrer données sensibles au repos**
   - Phone numbers
   - Adresses (si collectées)

3. **Implémenter politique de rétention**
   - Anonymiser données > 2 ans
   - Supprimer logs > 90 jours

4. **Ajouter rate limiting**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @app.get("/auth/login")
   @limiter.limit("5/minute")
   async def login(...):
   ```

---

### 🟢 PRIORITÉ 4 (Trimestre)

1. **Penetration testing externe**
   - Engager une société de sécurité
   - Test OWASP Top 10

2. **Certification ISO 27001 / SOC 2**
   - Si croissance importante

3. **Bug Bounty Program**
   - HackerOne / Bugcrowd

---

## 📋 Checklist de Sécurité Continue

### CI/CD Pipeline (À intégrer)

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Bandit Scan
        run: |
          pip install bandit
          bandit -r app/ -f json -o bandit.json

      - name: Dependency Check
        run: |
          pip install pip-audit safety
          pip-audit --format json > audit.json
          safety check --json > safety.json

      - name: Secrets Scan
        run: |
          docker run -v $(pwd):/src trufflesecurity/trufflehog \
            filesystem /src --json > secrets.json

      - name: Fail on Critical
        run: |
          # Parser les rapports et fail si HIGH severity
          python check_security_reports.py
```

---

## 📊 Métriques de Sécurité à Suivre

| Métrique | Cible | Actuel |
|----------|-------|--------|
| Vulnérabilités HIGH | 0 | 0 ✅ |
| Vulnérabilités MEDIUM | < 5 | 6 ⚠️ |
| Coverage sécurité endpoints | 100% | 72% 🔴 |
| Temps de réponse incidents | < 24h | N/A |
| Pentest annuel | Oui | Non 🔴 |
| Formation sécurité équipe | 100% | N/A |

---

## 🔗 Ressources Utiles

1. **OWASP Top 10**: https://owasp.org/www-project-top-ten/
2. **RGPD Guide**: https://www.cnil.fr/fr/rgpd-passer-a-laction
3. **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
4. **Bandit Docs**: https://bandit.readthedocs.io/
5. **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework

---

## ✅ Conclusion

### Points Forts
- ✅ Aucune vulnérabilité critique (HIGH) dans le code
- ✅ Utilisation de JWT pour authentification
- ✅ Requêtes SQL paramétrées (majoritairement)
- ✅ Hashage des mots de passe via Supabase
- ✅ Endpoints GDPR (export, suppression) présents

### Points Faibles
- 🔴 17 endpoints non protégés exposant données sensibles
- 🔴 Secrets hardcodés (fallback JWT)
- 🔴 Pas de RLS sur la base de données
- 🔴 Emails loggés en clair (violation RGPD)
- 🔴 Pas d'audit log des accès

### Recommandation Finale

**Score actuel: 6.5/10**

Avec les corrections de Priorité 1 et 2:
- **Score estimé: 8.5/10** (Production-ready)

Le système est **utilisable en production** mais nécessite les corrections de **Priorité 1 immédiatement** et **Priorité 2 dans les 7 jours**.

---

**Prochaine étape**: Implémenter les fixes de Priorité 1 et relancer Bandit pour validation.
