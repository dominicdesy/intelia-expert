#!/bin/bash
# Script to clean old images and keep only essential ones

set -e

echo "=== NETTOYAGE PARTIEL DU CONTAINER REGISTRY ==="
echo ""
echo "Ce script va:"
echo "1. Garder les tags: latest, main, buildcache"
echo "2. Garder les 3 images les plus récentes avec tag 'main-*'"
echo "3. Supprimer toutes les autres images"
echo ""
read -p "Continuer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé"
    exit 1
fi

REGISTRY_NAME="intelia-registry"
REPOS=("intelia-frontend" "intelia-backend" "intelia-llm" "intelia-rag")

for REPO in "${REPOS[@]}"; do
    echo ""
    echo "================================================"
    echo "Nettoyage: $REPO"
    echo "================================================"

    # Get all tags
    echo "Récupération de tous les tags..."
    ALL_TAGS=$(doctl registry repository list-tags "$REPO" --format Tag --no-header)

    # Protected tags
    PROTECTED_TAGS=("latest" "main" "buildcache")

    # Get main-* tags sorted by date (keep only 3 most recent)
    MAIN_TAGS=$(echo "$ALL_TAGS" | grep "^main-" | head -n 3 || true)

    echo "Tags protégés: ${PROTECTED_TAGS[@]}"
    echo "Tags main-* à garder: $(echo $MAIN_TAGS | wc -w)"

    # Delete all other tags
    for TAG in $ALL_TAGS; do
        # Skip if protected
        if [[ " ${PROTECTED_TAGS[@]} " =~ " ${TAG} " ]]; then
            echo "  [KEEP] $TAG (protégé)"
            continue
        fi

        # Skip if in recent main-* list
        if echo "$MAIN_TAGS" | grep -q "^${TAG}$"; then
            echo "  [KEEP] $TAG (récent)"
            continue
        fi

        # Delete the tag
        echo "  [DELETE] $TAG"
        doctl registry repository delete-tag "$REPO" "$TAG" --force || echo "    Erreur"
    done

    echo "✅ Nettoyage terminé pour $REPO"
done

echo ""
echo "================================================"
echo "LANCEMENT DU GARBAGE COLLECTION"
echo "================================================"
doctl registry garbage-collection start --include-untagged-manifests --force

echo ""
echo "✅ Nettoyage complet terminé!"
echo ""
echo "Résumé par repository:"
for REPO in "${REPOS[@]}"; do
    COUNT=$(doctl registry repository list-tags "$REPO" --format Tag --no-header | wc -l)
    echo "  - $REPO: $COUNT tags restants"
done
