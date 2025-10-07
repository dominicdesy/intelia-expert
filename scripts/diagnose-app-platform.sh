#!/bin/bash
# Diagnose App Platform configuration issue

set -e

echo "=== DIAGNOSTIC APP PLATFORM ==="
echo ""

# Get the app spec
echo "Récupération de la spec App Platform..."
doctl apps spec get $DO_APP_ID --format yaml > app-spec-current.yaml

echo ""
echo "=== CONFIGURATION DES IMAGES ==="
echo ""

# Extract image configuration for each service
echo "Services configurés:"
grep -A 10 "image:" app-spec-current.yaml | grep -E "(name:|registry_type:|registry:|repository:|tag:|digest:)" || true

echo ""
echo "=== VÉRIFICATION REGISTRE ==="
echo ""

# List available tags in registry
echo "Tags disponibles dans le registre:"
echo ""
echo "Frontend:"
doctl registry repository list-tags intelia-frontend --format Tag,UpdatedAt | head -5

echo ""
echo "Backend:"
doctl registry repository list-tags intelia-backend --format Tag,UpdatedAt | head -5

echo ""
echo "LLM:"
doctl registry repository list-tags intelia-llm --format Tag,UpdatedAt | head -5

echo ""
echo "RAG:"
doctl registry repository list-tags intelia-rag --format Tag,UpdatedAt | head -5

echo ""
echo "=== ANALYSE ==="
echo ""

# Check if digest is hardcoded
if grep -q "digest:" app-spec-current.yaml; then
    echo "⚠️ PROBLÈME DÉTECTÉ: Des digests sont hardcodés dans la spec!"
    echo ""
    echo "Digests trouvés:"
    grep "digest:" app-spec-current.yaml
    echo ""
    echo "SOLUTION: Supprimer les digests et utiliser uniquement les tags"
else
    echo "✅ Pas de digest hardcodé"
fi

# Check registry configuration
REGISTRY_NAME=$(grep "registry:" app-spec-current.yaml | head -1 | awk '{print $2}')
echo ""
echo "Registre configuré: $REGISTRY_NAME"
echo "Registre attendu: intelia-registry (ou votre DOCR_NAME)"

echo ""
echo "Spec complète sauvegardée dans: app-spec-current.yaml"
