# Analyse de la Stack de Monitoring - Intelia Expert

**Date**: 2025-10-28
**Status**: Analyse complète
**Contexte**: Évaluation avant ajout de Sentry

---

## 📊 Vue d'ensemble de la stack actuelle

Vous avez actuellement **3 systèmes de monitoring**:

### 1. ✅ **Endpoints de Monitoring Custom** (`/monitoring/*`)
### 2. ✅ **Prometheus Metrics** (via `prometheus-client`)
### 3. ⏸️ **Sentry** (code ajouté, pas encore activé)

**Note importante**: Grafana a été expérimenté mais abandonné en raison de problèmes.

---

## 🔍 Analyse détaillée de chaque système

### 1. Endpoints de Monitoring Custom (`backend/app/api/v1/monitoring.py`)

**Ce que ça fait**:
- ✅ Endpoints REST pour récupérer des metrics système
- ✅ Health checks des services (PostgreSQL, Supabase, LLM Service, AI Service)
- ✅ Logs d'application (actuellement mock, à implémenter)
- ✅ Métriques système (CPU, RAM, Disk via `psutil`)

**Endpoints disponibles**:
```python
GET /api/v1/monitoring/summary      # Vue d'ensemble
GET /api/v1/monitoring/services     # État des services
GET /api/v1/monitoring/logs         # Logs applicatifs
GET /api/v1/monitoring/system       # Métriques système
```

**Frontend associé**: `MonitoringTab.tsx`
- ✅ Interface custom dans StatisticsPage
- ✅ Affichage en temps réel des services
- ✅ Logs avec filtres (service, level, limit)
- ✅ Auto-refresh configuré (30s par défaut)
- ✅ Affichage du response time par service

**Forces**:
- ✅ Totalement sous votre contrôle
- ✅ Pas de coût externe
- ✅ Interface custom adaptée à vos besoins
- ✅ Pas de dépendance à un service tiers

**Faiblesses**:
- ❌ Logs actuellement **mock** (TODO ligne 309)
- ❌ Pas d'alerting automatique
- ❌ Pas de rétention long terme des logs
- ❌ Pas de stack traces détaillées pour erreurs
- ❌ Nécessite que vous soyez connecté pour voir les metrics

---

### 2. Prometheus Metrics (`backend/app/metrics/__init__.py`)

**Ce que ça fait**:
- ✅ Export de métriques au format Prometheus
- ✅ Tracking LLM (tokens, coûts, latence)
- ✅ Tracking HTTP (requêtes, latence, status codes)
- ✅ Tracking DB (queries, latence, connexions)
- ✅ Tracking Business (revenue, questions, users)
- ✅ Tracking Erreurs (types, severity)

**Métriques exposées**:
```python
# LLM Metrics
intelia_llm_tokens_total{model, type}
intelia_llm_cost_usd_total{model, feature}
intelia_llm_requests_total{model, status}
intelia_llm_request_duration_seconds{model, feature}

# API Metrics
intelia_http_requests_total{method, endpoint, status}
intelia_http_request_duration_seconds{method, endpoint}

# DB Metrics
intelia_db_connections_active{pool}
intelia_db_query_duration_seconds{operation, table}
intelia_db_queries_total{operation, table, status}

# Business Metrics
intelia_active_users
intelia_questions_total{source, language}
intelia_revenue_usd_total{plan}

# System Health
intelia_errors_total{type, severity}
intelia_uptime_seconds
```

**Endpoint**: `/api/metrics` (requis JWT admin)

**Configuration Prometheus**: `prometheus-service/prometheus.yml`
- Scrape AI Service uniquement (backend désactivé car auth requise)

**Frontend associé**: `PrometheusMetrics.tsx`
- ✅ Composant custom pour afficher metrics Prometheus
- ✅ Affiché dans l'onglet "Métriques" de StatisticsPage

**Forces**:
- ✅ Standard de l'industrie
- ✅ Format universellement accepté
- ✅ Facile à intégrer avec autres outils (Grafana Cloud, etc.)
- ✅ Performance élevée (format binaire)
- ✅ Rétention historique possible

**Faiblesses**:
- ❌ **Backend metrics non scrapables** (auth JWT requise)
- ❌ Pas d'alerting sans outil externe (Alertmanager, Grafana Cloud)
- ❌ Pas de stack traces ou context des erreurs
- ❌ Nécessite infrastructure Prometheus pour être utile

---

### 3. Sentry (ajouté mais pas activé)

**Ce que ça ferait** (si activé):
- ✅ Capture automatique des exceptions Python
- ✅ Stack traces complètes avec contexte
- ✅ Groupement intelligent des erreurs similaires
- ✅ Alerting email/Slack automatique
- ✅ Performance monitoring (10% sampling)
- ✅ Release tracking (via `APP_VERSION`)
- ✅ Breadcrumbs (logs menant à l'erreur)
- ✅ User context (qui était affecté)

**Code ajouté** (`backend/app/main.py`):
```python
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=0.1,
        integrations=[FastApiIntegration(), LoggingIntegration()],
        ignore_errors=["HTTPException"],
        before_send=lambda event: None if "healthz" in event.get("request", {}).get("url", "") else event
    )
```

**Forces**:
- ✅ Leader du marché pour error tracking
- ✅ Interface web professionnelle
- ✅ Alerting intelligent (pas de spam)
- ✅ Context riche (user, request, breadcrumbs)
- ✅ Plan gratuit généreux (10k events/mois)
- ✅ Intégration FastAPI native
- ✅ Zéro maintenance infrastructure

**Faiblesses**:
- ❌ Service externe (dépendance)
- ❌ Coût si volume élevé (>10k events/mois)
- ❌ Nécessite compte/configuration externe
- ❌ Données envoyées hors de votre infrastructure

---

## 🔄 Comparaison: Que fait chaque outil

| Fonctionnalité | Monitoring Endpoints | Prometheus | Sentry |
|---|---|---|---|
| **Health checks services** | ✅ Oui (temps réel) | ⏸️ Possible via exporter | ❌ Non |
| **Métriques système (CPU/RAM)** | ✅ Oui (`psutil`) | ✅ Oui (node exporter) | ❌ Non |
| **Logs applicatifs** | ⏸️ TODO (mock actuellement) | ❌ Non (pas fait pour ça) | ✅ Oui (breadcrumbs) |
| **Stack traces erreurs** | ❌ Non | ❌ Non | ✅ Oui (détaillées) |
| **Métriques LLM (coûts, tokens)** | ❌ Non | ✅ Oui (complet) | ❌ Non |
| **Métriques HTTP (latence, taux)** | ❌ Non | ✅ Oui | ✅ Oui (performance monitoring) |
| **Métriques DB** | ❌ Non | ✅ Oui | ❌ Non |
| **Alerting** | ❌ Non | ⏸️ Via Alertmanager | ✅ Oui (email, Slack) |
| **Interface web** | ✅ Oui (custom) | ⏸️ Via Grafana | ✅ Oui (sentry.io) |
| **Rétention historique** | ❌ Non (temps réel) | ✅ Oui (configurable) | ✅ Oui (30 jours gratuit) |
| **User context (qui affecté)** | ❌ Non | ❌ Non | ✅ Oui |
| **Release tracking** | ❌ Non | ⏸️ Via labels | ✅ Oui |
| **Coût** | 💚 $0 | 💚 $0 (self-hosted) | 💚 $0 (<10k events) |
| **Maintenance** | 🟡 Vous devez coder | 🟡 Infra à gérer | 💚 Zéro |

---

## 🎯 Zones de couverture et gaps

### Ce qui est **bien couvert** actuellement:

✅ **Health checks services** (Monitoring Endpoints)
- PostgreSQL, Supabase, LLM Service, AI Service
- Response time par service
- Interface MonitoringTab

✅ **Métriques LLM/Business** (Prometheus)
- Coûts OpenAI par modèle
- Tokens consommés
- Revenue par plan
- Questions posées

✅ **Statistiques business** (Custom endpoints)
- Dashboard utilisateurs actifs
- Questions ce mois
- Top utilisateurs
- Interface StatisticsPage complète

### Ce qui **manque** actuellement:

❌ **Logs centralisés persistants**
- Actuellement mock dans `/monitoring/logs`
- Pas de rétention long terme
- Difficile de debugger erreurs passées

❌ **Stack traces détaillées**
- Quand erreur arrive, pas de context complet
- Pas de breadcrumbs (actions menant à l'erreur)
- Pas de user context (quel utilisateur affecté)

❌ **Alerting automatique**
- Vous devez manuellement vérifier MonitoringTab
- Pas de notification si service down
- Pas d'email si taux d'erreur élevé

❌ **Performance monitoring applicatif**
- Prometheus track latence, mais pas assez granulaire
- Pas de "slow requests" automatiques
- Pas de profiling CPU/memory par requête

---

## 💡 Recommandations: Que garder, que consolider

### Option 1: Stack Minimale (Recommandée pour MVP)

**Garder**:
- ✅ **Monitoring Endpoints** → Health checks temps réel
- ✅ **Prometheus** → Métriques LLM/Business
- ✅ **Ajouter Sentry** → Error tracking uniquement

**Pourquoi**:
- Chaque outil a un rôle distinct (pas de redondance)
- Monitoring Endpoints = health checks instantanés
- Prometheus = business metrics long terme
- Sentry = debugging erreurs critiques

**Coût**: $0 si <10k erreurs/mois

**Effort**: Configuration Sentry uniquement (5 min)

---

### Option 2: Stack Consolidée (Si budget limité)

**Garder**:
- ✅ **Monitoring Endpoints** → Tout faire avec ça
- ❌ Supprimer Prometheus (peu utilisé actuellement)
- ❌ Skip Sentry

**Implémenter dans Monitoring Endpoints**:
1. Remplacer mock logs par vrais logs (lire fichiers logs backend)
2. Ajouter stack trace capture dans `/monitoring/logs`
3. Ajouter métriques LLM dans `/monitoring/summary`
4. Ajouter alerting webhook (email/Slack) si service down

**Avantages**:
- Un seul système à maintenir
- Totalement sous votre contrôle
- Zéro dépendance externe
- Zéro coût

**Inconvénients**:
- Beaucoup de code à écrire vous-même
- Pas d'outils professionnels (Sentry > votre code)
- Nécessite être connecté pour voir metrics

---

### Option 3: Stack Professionnelle (Recommandée pour Production)

**Garder**:
- ✅ **Monitoring Endpoints** → Health checks + interface admin
- ✅ **Prometheus** → Métriques détaillées
- ✅ **Sentry** → Error tracking + alerting

**Ajouter**:
- ➕ **Grafana Cloud Free Tier** (si besoin de dashboards)
  - Connect to Prometheus metrics
  - Pre-built dashboards
  - Free tier: 10k series, 50GB logs

**OU**:
- ➕ **Better Stack (Logtail)** pour logs centralisés
  - Free tier: 1GB logs/mois
  - Alternative à implémenter logs custom

**Avantages**:
- Stack production-grade
- Chaque outil fait ce qu'il fait le mieux
- Alerting professionnel (Sentry + Grafana Cloud)
- Debugging rapide (Sentry stack traces)

**Inconvénients**:
- Plus de dépendances externes
- Coût potentiel si dépassement free tier

---

## 🚀 Ma recommandation finale

### Pour votre cas spécifique:

**Activer Sentry** (Option 1) car:

1. ✅ **Vous avez déjà le code** → 5 min de setup (juste SENTRY_DSN)

2. ✅ **Comble le plus gros gap** → Error tracking avec context
   - Actuellement, si erreur Voice Realtime, vous devez chercher manuellement dans logs DO
   - Avec Sentry: email automatique + stack trace + user affecté

3. ✅ **Complémentaire, pas redondant**:
   - Monitoring Endpoints → "Services sont-ils UP?" (health checks)
   - Prometheus → "Combien ça coûte?" (LLM costs, business metrics)
   - Sentry → "Pourquoi ça a crashé?" (error debugging)

4. ✅ **Plan gratuit suffisant**:
   - Voice Realtime limité à Elite/Intelia
   - Rate limiting 5 sessions/heure/user
   - Peu d'utilisateurs → <10k events/mois garanti

5. ✅ **Pas besoin de toucher au reste**:
   - Monitoring Endpoints → Reste tel quel (utile pour admin)
   - Prometheus → Reste tel quel (metrics business)

---

## ✂️ Ce qu'on peut simplifier plus tard

### Prometheus: À garder ou supprimer?

**Garder si**:
- Vous utilisez les metrics LLM pour optimiser coûts
- Vous voulez exporter vers Grafana Cloud later
- Vous aimez le format standardisé

**Supprimer si**:
- Vous ne regardez jamais ces metrics
- Vous préférez tout dans MonitoringTab custom
- Vous voulez minimiser dépendances

**Mon avis**: **Garder Prometheus** car:
- Déjà configuré
- Métriques LLM coûts très utiles (ligne 150-156 de `metrics/__init__.py`)
- Format standard = facile d'exporter si besoin

---

### Monitoring Endpoints: À améliorer

**TODO prioritaire**:

1. **Implémenter vrais logs** (actuellement mock ligne 309):
```python
# backend/app/api/v1/monitoring.py ligne 386-398
# TODO: Implement actual log retrieval from log files or logging system
```

**Comment**:
```python
import logging
from logging.handlers import RotatingFileHandler

# Configurer handler fichier
file_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)

# Dans /monitoring/logs, lire fichier logs/app.log
def get_application_logs(limit, level):
    logs = []
    with open("logs/app.log", "r") as f:
        for line in f.readlines()[-limit:]:
            # Parser et filtrer
            ...
    return logs
```

2. **Ajouter alerting webhook** (optionnel):
```python
@router.get("/monitoring/alerts")
async def check_alerts():
    """Envoyer email/Slack si service unhealthy"""
    services = await get_services_status()
    unhealthy = [s for s in services if s.status == "unhealthy"]

    if unhealthy:
        # Envoyer notification
        await send_slack_alert(unhealthy)
```

---

## 📋 Plan d'action recommandé

### Phase 1: Activer Sentry (5 minutes)

1. Créer compte sentry.io (gratuit)
2. Créer projet FastAPI
3. Copier DSN
4. Ajouter variables DO:
   ```bash
   SENTRY_DSN=https://...@o0.ingest.sentry.io/...
   SENTRY_ENVIRONMENT=production
   ```
5. Redéployer
6. Vérifier logs: `✅ Sentry initialized: production`

### Phase 2: Améliorer Monitoring Endpoints (optionnel, 1-2h)

1. Implémenter vrais logs (remplacer mock)
2. Ajouter file handler pour logs persistants
3. Tester interface MonitoringTab avec vrais logs

### Phase 3: Cleanup (optionnel)

1. Supprimer documentation Grafana (déjà fait mentalement)
2. Décider si garder Prometheus (je recommande OUI)
3. Documenter stack finale

---

## 🎬 Conclusion

**Stack finale recommandée**:

```
┌─────────────────────────────────────────────────┐
│           FRONTEND (StatisticsPage)             │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │Dashboard │ │Questions │ │ Monitoring Tab │  │
│  │   Tab    │ │   Tab    │ │                │  │
│  └──────────┘ └──────────┘ └────────────────┘  │
└───────┬──────────┬────────────────┬─────────────┘
        │          │                │
        ↓          ↓                ↓
┌───────────────────────────────────────────────┐
│              BACKEND (FastAPI)                │
│                                               │
│  /stats-fast/*     /monitoring/*    /metrics  │
│  (Business)        (Health)         (Prom)    │
└───────┬──────────────┬─────────────┬──────────┘
        │              │             │
        ↓              ↓             ↓
┌──────────┐  ┌────────────┐  ┌──────────────┐
│PostgreSQL│  │  Services  │  │  Prometheus  │
│  Stats   │  │  Health    │  │   Metrics    │
└──────────┘  └────────────┘  └──────────────┘
                                      │
                                      ↓
                              ┌───────────────┐
                              │ Grafana Cloud │
                              │  (Optional)   │
                              └───────────────┘

        + Sentry (error tracking, alerts)
```

**Rôles**:
- **Monitoring Endpoints** → Admin health checks temps réel
- **Prometheus** → Business metrics long terme (LLM costs, revenue)
- **Sentry** → Error tracking + alerting + debugging

**Pourquoi cette stack**:
1. ✅ Pas de redondance (chacun a rôle unique)
2. ✅ Gratuit (<10k events/mois Sentry)
3. ✅ Déjà 80% implémenté
4. ✅ Production-ready
5. ✅ Facile à maintenir

---

**Prochaine étape suggérée**: Activer Sentry (5 min) ou décider de skip?
