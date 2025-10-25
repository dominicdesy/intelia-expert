# Configuration Grafana Cloud pour Intelia Expert

## Vue d'ensemble

Le backend expose des métriques Prometheus à l'endpoint `/metrics` qui peuvent être scrapées par Grafana Cloud pour monitoring en temps réel.

## Métriques disponibles

### 1. LLM Metrics (Coûts et Performance)

- `intelia_llm_tokens_total{model, type}` - Total tokens (prompt/completion)
- `intelia_llm_cost_usd_total{model, feature}` - Coût total en USD
- `intelia_llm_requests_total{model, status}` - Nombre de requêtes LLM
- `intelia_llm_request_duration_seconds{model, feature}` - Latence des appels LLM

**Features:** `chat`, `embeddings`, `tts`, `voice_realtime`
**Models:** `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`, etc.

### 2. API Performance Metrics

- `intelia_http_requests_total{method, endpoint, status}` - Total requêtes HTTP
- `intelia_http_request_duration_seconds{method, endpoint}` - Latence des endpoints

### 3. Database Metrics

- `intelia_db_connections_active{pool}` - Connexions DB actives
- `intelia_db_query_duration_seconds{operation, table}` - Performance requêtes
- `intelia_db_queries_total{operation, table, status}` - Total requêtes DB

### 4. Business Metrics

- `intelia_active_users` - Utilisateurs actifs
- `intelia_questions_total{source, language}` - Questions posées
- `intelia_revenue_usd_total{plan}` - Revenus par plan

### 5. System Health Metrics

- `intelia_errors_total{type, severity}` - Erreurs système
- `intelia_uptime_seconds` - Temps de fonctionnement
- `intelia_system_info` - Informations système

## Configuration Grafana Cloud

### Étape 1: Créer compte Grafana Cloud

1. Aller sur https://grafana.com/products/cloud
2. Sign up (gratuit jusqu'à 10k séries métriques)
3. Choisir une région (US/EU)
4. Noter votre **tenant URL**: `https://VOTRE-TENANT.grafana.net`

### Étape 2: Configurer le scraping

1. Dans Grafana Cloud, aller dans **Connections** > **Add new connection**
2. Sélectionner **Prometheus**
3. Configuration:
   ```yaml
   URL: https://expert.intelia.com/api/metrics
   Scrape interval: 60s
   ```
4. Authentification (optionnel):
   - Type: Bearer Token
   - Token: Votre token JWT super_admin

### Étape 3: Créer dashboards

#### Dashboard 1: Coûts LLM

Requêtes Prometheus utiles:

```promql
# Coût total par jour
sum(increase(intelia_llm_cost_usd_total[1d])) by (model)

# Top 5 modèles les plus coûteux
topk(5, sum(intelia_llm_cost_usd_total) by (model))

# Tokens consommés par heure
sum(rate(intelia_llm_tokens_total[1h])) by (model, type)

# Coût moyen par requête
sum(intelia_llm_cost_usd_total) / sum(intelia_llm_requests_total)
```

#### Dashboard 2: Performance API

```promql
# Latence p95 par endpoint
histogram_quantile(0.95,
  sum(rate(intelia_http_request_duration_seconds_bucket[5m])) by (endpoint, le)
)

# Taux d'erreur
sum(rate(intelia_http_requests_total{status=~"5.."}[5m]))
/
sum(rate(intelia_http_requests_total[5m]))

# Requêtes par minute
sum(rate(intelia_http_requests_total[1m])) by (endpoint)
```

#### Dashboard 3: Business KPIs

```promql
# Questions par jour
sum(increase(intelia_questions_total[1d])) by (source)

# Revenus cumulés
sum(intelia_revenue_usd_total) by (plan)

# Utilisateurs actifs
intelia_active_users
```

### Étape 4: Configurer alertes

Exemples d'alertes critiques:

```yaml
# Coût LLM quotidien > $100
sum(increase(intelia_llm_cost_usd_total[1d])) > 100

# Taux d'erreur > 5%
sum(rate(intelia_errors_total[5m])) / sum(rate(intelia_http_requests_total[5m])) > 0.05

# Latence p95 > 5 secondes
histogram_quantile(0.95, sum(rate(intelia_llm_request_duration_seconds_bucket[5m])) by (le)) > 5
```

### Étape 5: Intégrer dans le frontend

1. Créer un dashboard dans Grafana Cloud
2. Cliquer sur **Share** > **Copy link**
3. Ajouter les paramètres:
   - `?kiosk=tv` - Mode plein écran
   - `&theme=light` - Thème clair
   - `&from=now-24h&to=now` - Dernières 24h

4. Exemple d'URL finale:
   ```
   https://VOTRE-TENANT.grafana.net/d/abc123/llm-costs?orgId=1&kiosk=tv&theme=light
   ```

5. Ajouter dans `frontend/.env.local`:
   ```bash
   NEXT_PUBLIC_GRAFANA_URL=https://VOTRE-TENANT.grafana.net/d/abc123/llm-costs?orgId=1&kiosk=tv&theme=light
   ```

6. Le dashboard s'affichera automatiquement dans **Admin > Statistiques > Métriques**

## Dashboards recommandés

### Dashboard "Executive Summary"
- Coût total mensuel
- Nombre d'utilisateurs actifs
- Questions traitées
- Taux de satisfaction
- Uptime

### Dashboard "LLM Operations"
- Coût par modèle (graphique temps réel)
- Distribution des tokens
- Latence moyenne
- Taux d'erreur
- Alertes coûts

### Dashboard "Technical Health"
- CPU/RAM utilization
- Database performance
- API response times
- Error rates
- Active connections

## Ajouter tracking pour nouvelles fonctionnalités

Pour tracker une nouvelle feature LLM:

```python
from app.metrics import track_llm_call

# Après votre appel LLM
track_llm_call(
    model="gpt-4o",
    feature="nouvelle_feature",  # e.g., "summary", "translation"
    prompt_tokens=1000,
    completion_tokens=500,
    cost_usd=0.015,
    duration=2.5,
    status="success"
)
```

Pour tracker un endpoint HTTP:

```python
from app.metrics import track_http_request

track_http_request(
    method="POST",
    endpoint="/api/v1/nouvelle-route",
    status=200,
    duration=0.5
)
```

## Troubleshooting

### Métriques ne s'affichent pas

1. Vérifier que `/metrics` est accessible:
   ```bash
   curl https://expert.intelia.com/api/metrics
   ```

2. Vérifier la configuration du scraper dans Grafana Cloud

3. Vérifier les logs backend pour erreurs de tracking

### Coûts semblent incorrects

- Vérifier les prix dans `openai_utils.py` fonction `_calculate_llm_cost()`
- OpenAI change parfois les prix, mettre à jour si nécessaire

### Dashboard vide

- Attendre 1-2 minutes après déploiement (temps de scrape initial)
- Vérifier que des requêtes LLM ont été effectuées
- Vérifier la période de temps sélectionnée dans Grafana

## Support

- Documentation Grafana Cloud: https://grafana.com/docs/grafana-cloud/
- Prometheus query language: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Issues: Créer une issue sur GitHub avec tag `monitoring`
