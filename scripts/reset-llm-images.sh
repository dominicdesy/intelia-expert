#!/bin/bash
# Reset LLM images only - keep other services intact

set -e

echo "=== RESET IMAGES LLM UNIQUEMENT ==="
echo ""
echo "Ce script va:"
echo "1. Supprimer TOUS les tags de intelia-llm"
echo "2. Forcer un rebuild complet"
echo "3. Les autres services (frontend, backend, rag) restent intacts"
echo ""
read -p "Êtes-vous SÛR de vouloir continuer? (yes/no) " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo "Annulé"
    exit 1
fi

REPO="intelia-llm"

echo ""
echo "Suppression de tous les tags de $REPO..."
ALL_TAGS=$(doctl registry repository list-tags "$REPO" --format Tag --no-header)

for TAG in $ALL_TAGS; do
    echo "  Suppression: $TAG"
    doctl registry repository delete-tag "$REPO" "$TAG" --force || echo "    Erreur"
done

echo ""
echo "Lancement du garbage collection..."
doctl registry garbage-collection start --include-untagged-manifests --force

echo ""
echo "✅ Toutes les images LLM ont été supprimées"
echo ""
echo "PROCHAINES ÉTAPES:"
echo "1. Faites un commit vide pour déclencher un rebuild:"
echo "   git commit --allow-empty -m 'Rebuild: Clean LLM images'"
echo "   git push"
echo ""
echo "2. Le workflow va créer de nouvelles images propres"
echo "3. Les tags latest, main, main-SHA seront recréés"
echo ""
echo "Note: Cela prendra ~10 minutes (build complet sans cache)"
