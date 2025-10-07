#!/bin/bash
# Fix App Platform: Remove hardcoded digest and use tag only

set -e

echo "=== FIX APP PLATFORM DIGEST ==="
echo ""

if [ -z "$DO_APP_ID" ]; then
    echo "❌ Erreur: Variable DO_APP_ID non définie"
    echo "Usage: export DO_APP_ID='votre-app-id' && bash fix-app-platform-digest.sh"
    exit 1
fi

# Get current spec
echo "1. Récupération de la spec actuelle..."
doctl apps spec get $DO_APP_ID --format yaml > app-spec-before.yaml

# Remove digest fields using sed
echo "2. Suppression des digests hardcodés..."
sed '/digest:/d' app-spec-before.yaml > app-spec-fixed.yaml

echo ""
echo "=== CHANGEMENTS ==="
diff app-spec-before.yaml app-spec-fixed.yaml || true

echo ""
echo "3. Application de la nouvelle spec..."
doctl apps update $DO_APP_ID --spec app-spec-fixed.yaml

echo ""
echo "✅ Spec mise à jour!"
echo ""
echo "Les services utiliseront maintenant les tags dynamiques sans digest hardcodé"
echo ""
echo "Prochaine étape: Déclenchez un déploiement depuis App Platform"
