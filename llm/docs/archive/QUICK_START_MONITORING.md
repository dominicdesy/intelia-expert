# Quick Start - Rate Limiting & Monitoring

## Démarrage Rapide

Ce guide vous permet de tester rapidement le rate limiting et le monitoring.

---

## 1. Démarrer l'API

```bash
cd /c/intelia_gpt/intelia-expert/llm
python main.py
```

**Vérifier les logs** :
```
✅ Rate limiting middleware activé (10 req/min/user)
```

---

## 2. Tester le Rate Limiting

### Test Basique

```bash
# Requête normale
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -d '{"message": "Bonjour, quelle est la température idéale pour un poulet?", "tenant_id": "test"}'
```

### Vérifier les Headers de Rate Limit

```bash
curl -I -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test-user" \
  -d '{"message": "Test", "tenant_id": "test"}'
```

**Résultat attendu** :
```
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1696521660
```

### Tester le Dépassement

```bash
# Faire 11 requêtes rapidement (la 11ème sera bloquée)
for i in {1..11}; do
  echo "Requête $i:"
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -H "X-User-ID: rate-limit-test" \
    -d "{\"message\": \"Test $i\", \"tenant_id\": \"test\"}" \
    -w "\nHTTP Code: %{http_code}\n\n"
  sleep 0.5
done
```

**Résultat attendu pour la 11ème requête** :
```
HTTP Code: 429

{
  "error": "Rate limit exceeded",
  "message": "Maximum 10 requests per minute allowed",
  "retry_after": 60
}
```

---

## 3. Consulter les Métriques

### Métriques Complètes

```bash
curl http://localhost:8000/api/v1/metrics | python -m json.tool
```

### Métriques de Monitoring Uniquement

```bash
curl http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring'
```

**Exemple de réponse** :
```json
{
  "uptime_seconds": 1234.56,
  "endpoints": {
    "/chat": {
      "count": 42,
      "total_time": 19.2,
      "errors": 2,
      "last_reset": "2025-10-05T14:30:00",
      "avg_time": 0.457,
      "error_rate": 0.047
    }
  },
  "cache": {
    "cache_semantic_hits": {"count": 15},
    "cache_semantic_misses": {"count": 27}
  },
  "openai": {
    "openai_gpt-4": {
      "count": 38,
      "total_tokens": 12456,
      "total_time": 15.8
    }
  }
}
```

### Métriques d'un Endpoint Spécifique

```bash
# Métriques de /chat
curl http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.endpoints["/chat"]'
```

### Uptime de l'Application

```bash
curl http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.uptime_seconds'
```

---

## 4. Health Check

### Health Check Basique

```bash
curl http://localhost:8000/api/v1/health | python -m json.tool
```

**Exemple de réponse** :
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

---

## 5. Script de Test Automatique

### Exécuter le Script

```bash
# Rendre le script exécutable
chmod +x test_rate_limiting.sh

# Lancer le test
./test_rate_limiting.sh
```

Le script va :
1. Faire 12 requêtes (dépassement attendu à la 11ème)
2. Attendre 60 secondes
3. Refaire une requête (devrait passer)
4. Consulter les métriques
5. Faire un health check

---

## 6. Cas d'Usage Courants

### Cas 1 : Tester avec Différents Utilisateurs

```bash
# Utilisateur 1 (10 requêtes OK)
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "X-User-ID: user-1" \
    -H "Content-Type: application/json" \
    -d '{"message": "Test", "tenant_id": "test"}'
done

# Utilisateur 2 (10 requêtes OK aussi - compteur séparé)
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "X-User-ID: user-2" \
    -H "Content-Type: application/json" \
    -d '{"message": "Test", "tenant_id": "test"}'
done
```

### Cas 2 : Surveillance Continue

```bash
# Boucle infinie pour surveiller les métriques
while true; do
  clear
  echo "=== Métriques - $(date) ==="
  curl -s http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.endpoints'
  sleep 5
done
```

### Cas 3 : Générer du Trafic de Test

```bash
# Générer 50 requêtes avec différents users
for user_id in {1..5}; do
  for req in {1..10}; do
    curl -X POST http://localhost:8000/api/v1/chat \
      -H "X-User-ID: load-test-user-$user_id" \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"Load test request $req\", \"tenant_id\": \"test\"}" &
  done
done

# Attendre que toutes les requêtes se terminent
wait

# Consulter les métriques
curl http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring'
```

---

## 7. Troubleshooting

### Problème : Pas de headers de rate limit

**Solution** :
```bash
# Vérifier les logs de démarrage
grep "Rate limiting" /path/to/logs/app.log

# Tester avec curl verbose
curl -v -X POST http://localhost:8000/api/v1/chat \
  -H "X-User-ID: debug" \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "tenant_id": "test"}' 2>&1 | grep -i ratelimit
```

### Problème : Métriques vides

**Solution** :
```bash
# 1. Générer du trafic
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Test", "tenant_id": "test"}'
done

# 2. Vérifier les métriques
curl http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.endpoints'
```

### Problème : Redis indisponible

**Vérification** :
```bash
# Tester Redis
redis-cli ping

# Vérifier le health check
curl http://localhost:8000/api/v1/health | python -m json.tool | jq '.redis'
```

**Comportement attendu** :
- L'API fonctionne quand même (fallback mémoire)
- Les logs indiquent : `⚠️ Rate limiting en mémoire activé (fallback)`

---

## 8. Intégration dans vos Tests

### Test Unitaire (Python)

```python
import requests
import time

def test_rate_limiting():
    url = "http://localhost:8000/api/v1/chat"
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": "test-user-unittest"
    }
    data = {"message": "Test", "tenant_id": "test"}

    # Faire 10 requêtes (devrait passer)
    for i in range(10):
        response = requests.post(url, json=data, headers=headers)
        assert response.status_code == 200
        assert "X-RateLimit-Remaining" in response.headers

    # 11ème requête (devrait être bloquée)
    response = requests.post(url, json=data, headers=headers)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["error"]

def test_metrics():
    response = requests.get("http://localhost:8000/api/v1/metrics")
    assert response.status_code == 200

    metrics = response.json()
    assert "monitoring" in metrics
    assert "uptime_seconds" in metrics["monitoring"]
```

### Test d'Intégration (Bash)

```bash
#!/bin/bash

# Test complet
set -e

echo "Test 1: Requête normale"
response=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-ID: integration-test" \
  -d '{"message": "Test", "tenant_id": "test"}')

http_code="${response: -3}"
if [ "$http_code" != "200" ]; then
  echo "❌ Test 1 échoué: $http_code"
  exit 1
fi
echo "✅ Test 1 passé"

echo "Test 2: Métriques"
metrics=$(curl -s http://localhost:8000/api/v1/metrics)
if ! echo "$metrics" | grep -q "monitoring"; then
  echo "❌ Test 2 échoué: pas de métriques"
  exit 1
fi
echo "✅ Test 2 passé"

echo "Test 3: Health check"
health=$(curl -s http://localhost:8000/api/v1/health)
if ! echo "$health" | grep -q "overall_status"; then
  echo "❌ Test 3 échoué: pas de status"
  exit 1
fi
echo "✅ Test 3 passé"

echo "✅ Tous les tests passés!"
```

---

## 9. Dashboards et Visualisation

### Option 1 : Terminal Watch

```bash
# Surveiller les métriques en temps réel
watch -n 2 'curl -s http://localhost:8000/api/v1/metrics | python -m json.tool | jq ".monitoring.endpoints[\"/chat\"]"'
```

### Option 2 : Grafana (Avancé)

Voir la section **Intégration Prometheus** dans `MONITORING.md`

---

## 10. Commandes Rapides

### Résumé des Commandes Essentielles

```bash
# Health check
curl http://localhost:8000/api/v1/health | python -m json.tool

# Métriques complètes
curl http://localhost:8000/api/v1/metrics | python -m json.tool

# Test rate limiting
for i in {1..11}; do curl -X POST http://localhost:8000/api/v1/chat \
  -H "X-User-ID: quick-test" -H "Content-Type: application/json" \
  -d '{"message": "Test", "tenant_id": "test"}' -w "\n%{http_code}\n"; done

# Métriques /chat seulement
curl -s http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.endpoints["/chat"]'

# Uptime
curl -s http://localhost:8000/api/v1/metrics | python -m json.tool | jq '.monitoring.uptime_seconds'

# Test automatique
./test_rate_limiting.sh
```

---

## Support

Pour plus de détails, consulter :
- `MONITORING.md` : Documentation complète
- `RATE_LIMITING_MONITORING_REPORT.md` : Rapport d'implémentation détaillé

**Questions** : Consulter les logs ou créer une issue sur GitHub
