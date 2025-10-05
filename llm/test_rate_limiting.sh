#!/bin/bash

# Script de test pour le rate limiting de l'API Intelia Expert
# Teste la limite de 10 requêtes par minute

echo "=========================================="
echo "Test Rate Limiting - API Intelia Expert"
echo "=========================================="
echo ""

# Configuration
API_URL="http://localhost:8000/api/v1/chat"
USER_ID="test-user-$(date +%s)"

echo "Configuration:"
echo "  - API URL: $API_URL"
echo "  - User ID: $USER_ID"
echo "  - Limite: 10 requêtes/minute"
echo ""

# Fonction pour faire une requête
make_request() {
    local request_num=$1
    echo "Requête #$request_num"

    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "X-User-ID: $USER_ID" \
        -d "{\"message\": \"Test message $request_num\", \"tenant_id\": \"test\"}")

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')

    # Extraire les headers de rate limit (si disponibles)
    rate_limit=$(curl -s -I -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "X-User-ID: $USER_ID" \
        -d "{\"message\": \"Test\", \"tenant_id\": \"test\"}" 2>/dev/null | grep -i "x-ratelimit")

    echo "  Code HTTP: $http_code"

    if [ ! -z "$rate_limit" ]; then
        echo "  Rate Limit Info:"
        echo "$rate_limit" | sed 's/^/    /'
    fi

    if [ "$http_code" = "429" ]; then
        echo "  ⚠️  RATE LIMIT EXCEEDED"
        echo "  Réponse: $body" | head -c 200
    elif [ "$http_code" = "200" ]; then
        echo "  ✅ Succès"
    else
        echo "  ❌ Erreur: $http_code"
    fi

    echo ""
}

# Test: Faire 12 requêtes rapidement
echo "Test 1: Requêtes rapides (dépassement attendu à la 11ème)"
echo "------------------------------------------------------"

for i in {1..12}; do
    make_request $i
    sleep 0.5
done

echo ""
echo "=========================================="
echo "Test 2: Attendre et réessayer"
echo "=========================================="
echo ""
echo "Attente de 60 secondes pour reset du rate limit..."

# Countdown
for i in {60..1}; do
    echo -ne "  Temps restant: $i secondes\r"
    sleep 1
done
echo ""

echo ""
echo "Nouvelle requête après reset:"
make_request 13

echo ""
echo "=========================================="
echo "Test 3: Consulter les métriques"
echo "=========================================="
echo ""

echo "GET /api/v1/metrics (monitoring):"
curl -s "http://localhost:8000/api/v1/metrics" | python3 -m json.tool | grep -A 10 "\"monitoring\""

echo ""
echo "=========================================="
echo "Test 4: Health check"
echo "=========================================="
echo ""

echo "GET /api/v1/health:"
curl -s "http://localhost:8000/api/v1/health" | python3 -m json.tool

echo ""
echo "=========================================="
echo "Tests terminés!"
echo "=========================================="
