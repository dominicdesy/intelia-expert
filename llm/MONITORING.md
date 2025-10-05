# Documentation Monitoring & Rate Limiting

## Vue d'ensemble

Ce document décrit les fonctionnalités de **rate limiting** et de **monitoring** implémentées dans l'API Intelia Expert.

## Table des matières

1. [Rate Limiting](#rate-limiting)
2. [Monitoring](#monitoring)
3. [Configuration](#configuration)
4. [Endpoints](#endpoints)
5. [Exemples d'utilisation](#exemples-dutilisation)
6. [Intégration Prometheus](#intégration-prometheus)

---

## Rate Limiting

### Description

Le rate limiting protège l'API contre les abus en limitant le nombre de requêtes par utilisateur.

**Limite par défaut : 10 requêtes par minute par utilisateur**

### Fonctionnement

1. **Identification de l'utilisateur** :
   - Header `X-User-ID` (prioritaire)
   - Champ `user_id` ou `tenant_id` dans le body
   - Adresse IP du client (fallback)

2. **Stockage** :
   - **Redis** (recommandé en production) si disponible
   - **Mémoire** (fallback automatique) si Redis indisponible

3. **Headers de réponse** :
   ```
   X-RateLimit-Limit: 10
   X-RateLimit-Remaining: 7
   X-RateLimit-Reset: 1696521600
   ```

### Réponse en cas de dépassement

**Code HTTP : 429 Too Many Requests**

```json
{
  "error": "Rate limit exceeded",
  "message": "Maximum 10 requests per minute allowed",
  "retry_after": 60
}
```

### Activation

Le rate limiting est automatiquement activé au démarrage de l'application dans `main.py`.

Logs de démarrage :
```
✅ Rate limiting avec Redis activé
✅ Rate limiting middleware activé (10 req/min/user)
```

Ou en mode dégradé :
```
⚠️ Rate limiting en mémoire (Redis indisponible)
✅ Rate limiting middleware activé (10 req/min/user)
```

---

## Monitoring

### Description

Le système de monitoring collecte des métriques de performance en temps réel pour tous les endpoints de l'API.

### Métriques collectées

#### 1. Métriques par endpoint
- **Nombre de requêtes** (`count`)
- **Temps total** (`total_time`)
- **Temps moyen** (`avg_time`)
- **Nombre d'erreurs** (`errors`)
- **Taux d'erreur** (`error_rate`)

#### 2. Métriques de cache
- **Cache hits** (`cache_*_hits`)
- **Cache misses** (`cache_*_misses`)

#### 3. Métriques OpenAI
- **Nombre d'appels** (`count`)
- **Total de tokens** (`total_tokens`)
- **Temps total** (`total_time`)

#### 4. Métriques système
- **Uptime** (en secondes)

### Instrumentation des endpoints

Les endpoints `/chat` et `/chat/expert` sont automatiquement instrumentés :

```python
from monitoring.metrics import get_metrics_collector

# Enregistrer une requête réussie
monitoring_collector = get_metrics_collector()
monitoring_collector.record_request("/chat", duration, error=False)

# Enregistrer une erreur
monitoring_collector.record_request("/chat", duration, error=True)
```

---

## Configuration

### Variables d'environnement

Aucune variable d'environnement spécifique n'est requise. Le système utilise les configurations par défaut :

- **Rate limit** : 10 requêtes/minute
- **Fenêtre de temps** : 60 secondes
- **Redis** : Automatique si disponible, sinon fallback mémoire

### Personnalisation

Pour modifier les limites, éditez `C:\intelia_gpt\intelia-expert\llm\api\middleware\rate_limiter.py` :

```python
# Configuration
self.max_requests = 10  # Modifier ici
self.window_seconds = 60  # Modifier ici
```

---

## Endpoints

### GET /api/v1/health

**Health check** de l'application.

**Réponse** :
```json
{
  "overall_status": "healthy",
  "timestamp": 1696521234.567,
  "weaviate": {"connected": true},
  "redis": {"connected": true},
  "openai": {"connected": true},
  "rag_engine": {"connected": true},
  "cache_enabled": true,
  "degraded_mode": false
}
```

### GET /api/v1/metrics

**Métriques détaillées** de performance et monitoring.

**Réponse** :
```json
{
  "cache_stats": {
    "hits": 150,
    "misses": 45,
    "hit_rate": 0.77
  },
  "application_metrics": { ... },
  "performance_metrics": {
    "throughput_qps": 12.5,
    "latency_percentiles": {...},
    "memory_usage": {...}
  },
  "monitoring": {
    "uptime_seconds": 3600,
    "endpoints": {
      "/chat": {
        "count": 1234,
        "total_time": 567.8,
        "avg_time": 0.46,
        "errors": 12,
        "error_rate": 0.01
      }
    },
    "cache": {
      "cache_semantic_hits": {"count": 89},
      "cache_semantic_misses": {"count": 23}
    },
    "openai": {
      "openai_gpt-4": {
        "count": 156,
        "total_tokens": 45678,
        "total_time": 234.5
      }
    }
  },
  "architecture": "modular-endpoints"
}
```

---

## Exemples d'utilisation

### 1. Tester le rate limiting

**Requête normale** :
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user123" \
  -d '{"message": "Bonjour", "tenant_id": "test"}'
```

**Headers de réponse** :
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1696521660
```

**Dépasser la limite** (11ème requête en 1 minute) :
```bash
# 11ème requête
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user123" \
  -d '{"message": "Bonjour", "tenant_id": "test"}'
```

**Réponse** :
```json
{
  "error": "Rate limit exceeded",
  "message": "Maximum 10 requests per minute allowed",
  "retry_after": 60
}
```
**Code HTTP : 429**

### 2. Consulter les métriques

```bash
curl http://localhost:8000/api/v1/metrics
```

### 3. Vérifier le health check

```bash
curl http://localhost:8000/api/v1/health
```

### 4. Script de test automatique

```bash
#!/bin/bash

# Tester le rate limiting
echo "Test rate limiting..."
for i in {1..12}; do
  echo "Requête $i"
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-User-ID: test-user" \
    -d '{"message": "Test", "tenant_id": "test"}' \
    -w "\nHTTP Code: %{http_code}\n\n"
  sleep 1
done

# Consulter les métriques
echo -e "\n\nMétriques:"
curl http://localhost:8000/api/v1/metrics | jq '.monitoring.endpoints'
```

---

## Intégration Prometheus

### Configuration Prometheus

Le endpoint `/metrics` peut être intégré avec Prometheus pour un monitoring avancé.

**prometheus.yml** :
```yaml
scrape_configs:
  - job_name: 'intelia-expert-api'
    scrape_interval: 15s
    metrics_path: '/api/v1/metrics'
    static_configs:
      - targets: ['localhost:8000']
```

### Format des métriques

Actuellement, les métriques sont retournées au format JSON. Pour une intégration complète avec Prometheus, vous pouvez :

1. **Utiliser un exporter JSON** : `prometheus-json-exporter`
2. **Convertir les métriques** avec un script Python
3. **Utiliser Grafana** avec la datasource JSON

### Dashboards recommandés

**Métriques clés à surveiller** :

- **Taux de requêtes** : `monitoring.endpoints["/chat"].count`
- **Temps de réponse moyen** : `monitoring.endpoints["/chat"].avg_time`
- **Taux d'erreur** : `monitoring.endpoints["/chat"].error_rate`
- **Cache hit rate** : `cache_stats.hit_rate`
- **Uptime** : `monitoring.uptime_seconds`

---

## Architecture

### Composants

1. **RateLimiter** (`api/middleware/rate_limiter.py`)
   - Middleware FastAPI
   - Supporte Redis et mémoire
   - Gestion automatique du fallback

2. **MetricsCollector** (`monitoring/metrics.py`)
   - Collecteur singleton global
   - Métriques par endpoint
   - Métriques cache et OpenAI

3. **Intégration dans main.py**
   - Activation automatique au démarrage
   - Détection Redis automatique

### Flux de données

```
Requête → RateLimiter → Endpoint → MetricsCollector → Réponse
                ↓                           ↓
            Headers                    Stockage
        (rate limit info)              (métriques)
```

---

## Dépannage

### Rate limiting ne fonctionne pas

**Vérifier les logs** :
```
✅ Rate limiting middleware activé (10 req/min/user)
```

**Vérifier Redis** :
```python
# Dans Python
from cache.cache_core import RedisCacheCore
cache = RedisCacheCore()
print(cache.client)  # Doit être un client Redis, pas None
```

### Métriques vides

**Vérifier l'instrumentation** :
```bash
# Faire quelques requêtes
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "tenant_id": "test"}'

# Consulter les métriques
curl http://localhost:8000/api/v1/metrics | jq '.monitoring'
```

### Redis indisponible

Le système bascule automatiquement en mode mémoire :
```
⚠️ Redis non disponible pour rate limiting
⚠️ Rate limiting en mémoire activé (fallback)
```

**Limitation** : En mode mémoire, le rate limiting ne persiste pas entre les redémarrages.

---

## Prochaines étapes

### Améliorations futures

1. **Format Prometheus natif** : Exposer les métriques au format Prometheus
2. **Alertes** : Configurer des alertes sur le taux d'erreur
3. **Distributed tracing** : Ajouter OpenTelemetry
4. **Rate limiting configurable** : Permettre différentes limites par endpoint
5. **Circuit breaker** : Protection contre les services défaillants

---

## Support

Pour toute question ou problème :

1. Consulter les logs de l'application
2. Vérifier le endpoint `/health`
3. Consulter le endpoint `/metrics`
4. Contacter l'équipe de développement

---

**Version** : 1.0
**Date** : 2025-10-05
**Auteur** : Équipe Intelia Expert
