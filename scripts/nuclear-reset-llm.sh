#!/bin/bash
# NUCLEAR RESET: Delete ALL intelia-llm images and rebuild from scratch

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  NUCLEAR RESET - SUPPRESSION TOTALE DES IMAGES LLM       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  ATTENTION: Cette opération va:"
echo "    1. Supprimer TOUS les tags de intelia-llm (29 images)"
echo "    2. Supprimer toutes les images non-taguées (fantômes)"
echo "    3. Lancer le garbage collection complet"
echo "    4. Le repository sera VIDE après cette opération"
echo ""
echo "✅ Avantages:"
echo "    - Registre propre (économie de coûts)"
echo "    - Pas de manifests ou d'images corrompues"
echo "    - Rebuild complet sans cache"
echo ""
read -p "Tapez 'DELETE ALL' pour confirmer: " CONFIRM

if [[ "$CONFIRM" != "DELETE ALL" ]]; then
    echo "❌ Annulé - confirmation incorrecte"
    exit 1
fi

REPO="intelia-llm"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "ÉTAPE 1: Suppression de tous les tags"
echo "════════════════════════════════════════════════════════════"

# Get all tags
ALL_TAGS=$(doctl registry repository list-tags "$REPO" --format Tag --no-header 2>/dev/null || echo "")

if [[ -z "$ALL_TAGS" ]]; then
    echo "ℹ️  Aucun tag trouvé dans $REPO"
else
    TAG_COUNT=$(echo "$ALL_TAGS" | wc -l)
    echo "🗑️  Suppression de $TAG_COUNT tags..."

    for TAG in $ALL_TAGS; do
        echo "  → Suppression: $TAG"
        doctl registry repository delete-tag "$REPO" "$TAG" --force 2>&1 | grep -v "Warning" || true
    done

    echo "✅ Tous les tags supprimés"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "ÉTAPE 2: Garbage Collection"
echo "════════════════════════════════════════════════════════════"
echo "🗑️  Lancement du garbage collection (inclut les manifests non-tagués)..."

doctl registry garbage-collection start --include-untagged-manifests --force

echo "✅ Garbage collection lancé"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "ÉTAPE 3: Vérification"
echo "════════════════════════════════════════════════════════════"

sleep 5

REMAINING_TAGS=$(doctl registry repository list-tags "$REPO" --format Tag --no-header 2>/dev/null || echo "")

if [[ -z "$REMAINING_TAGS" ]]; then
    echo "✅ Repository intelia-llm est maintenant VIDE"
else
    echo "⚠️  Tags restants:"
    echo "$REMAINING_TAGS"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  NETTOYAGE TERMINÉ - PROCHAINES ÉTAPES                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Maintenant, déclenchez un rebuild complet:"
echo ""
echo "  cd C:\\intelia_gpt\\intelia-expert\\llm"
echo "  git commit --allow-empty -m 'Nuclear reset: Rebuild LLM from scratch'"
echo "  git push"
echo ""
echo "Le workflow GitHub va:"
echo "  • Builder une nouvelle image propre (~10 min)"
echo "  • Créer les tags: latest, main, main-SHA"
echo "  • Déployer automatiquement sur App Platform"
echo ""
echo "Surveillance du build:"
echo "  https://github.com/votre-repo/intelia-expert/actions"
echo ""
