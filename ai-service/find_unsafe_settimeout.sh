#!/bin/bash
# Script pour trouver TOUS les setTimeout dangereux dans le frontend

echo "======================================"
echo "🔍 Recherche de setTimeout dangereux"
echo "======================================"
echo ""

cd ../frontend

# Trouver tous les fichiers avec setTimeout
echo "📁 Fichiers contenant setTimeout:"
find app components lib -name "*.tsx" -o -name "*.ts" | xargs grep -l "setTimeout" | sort

echo ""
echo "======================================"
echo "🎯 Analyse détaillée:"
echo "======================================"
echo ""

# Pour chaque fichier, montrer les setTimeout avec contexte
for file in $(find app components lib -name "*.tsx" -o -name "*.ts" | xargs grep -l "setTimeout"); do
    echo ""
    echo "📄 $file"
    echo "----------------------------------------"

    # Afficher chaque setTimeout avec 10 lignes de contexte
    grep -n -B10 -A5 "setTimeout" "$file" | head -50

    echo ""
done
