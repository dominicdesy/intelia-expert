#!/bin/bash
# verify-hsts-preload.sh
# Script pour vérifier le header HSTS preload en production (contourne CloudFlare WAF)

DOMAIN="expert.intelia.com"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

echo "🔍 Vérification HSTS Preload pour $DOMAIN"
echo "================================================"
echo ""

# 1. Vérifier le header HSTS
echo "1️⃣  Header HSTS en production :"
echo "   (avec User-Agent pour contourner CloudFlare WAF)"
echo ""
HSTS_HEADER=$(curl -I -A "$USER_AGENT" https://$DOMAIN 2>/dev/null | grep -i strict-transport-security)

if [ -z "$HSTS_HEADER" ]; then
    echo "   ❌ Header HSTS non trouvé !"
    echo "   Vérifiez que le déploiement est terminé."
    exit 1
else
    echo "   ✅ $HSTS_HEADER"
fi

# Vérifier les directives spécifiques
echo ""
echo "2️⃣  Validation des directives :"
if echo "$HSTS_HEADER" | grep -q "max-age=31536000"; then
    echo "   ✅ max-age=31536000 (1 an)"
else
    echo "   ❌ max-age incorrect ou manquant"
fi

if echo "$HSTS_HEADER" | grep -q "includeSubDomains"; then
    echo "   ✅ includeSubDomains présent"
else
    echo "   ❌ includeSubDomains manquant"
fi

if echo "$HSTS_HEADER" | grep -q "preload"; then
    echo "   ✅ preload présent ← NOUVEAU"
else
    echo "   ⚠️  preload manquant (objectif de cette mise à jour)"
fi

# 3. Vérifier la redirection HTTP → HTTPS
echo ""
echo "3️⃣  Redirection HTTP → HTTPS :"
HTTP_REDIRECT=$(curl -I -A "$USER_AGENT" http://$DOMAIN 2>/dev/null | grep -i location)

if echo "$HTTP_REDIRECT" | grep -q "https://"; then
    echo "   ✅ $HTTP_REDIRECT"
else
    echo "   ❌ Pas de redirection HTTPS détectée"
fi

# 4. Vérifier le certificat SSL
echo ""
echo "4️⃣  Certificat SSL :"
CERT_INFO=$(echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)

if [ -z "$CERT_INFO" ]; then
    echo "   ❌ Impossible de récupérer le certificat"
else
    echo "   ✅ Certificat valide :"
    echo "$CERT_INFO" | sed 's/^/      /'
fi

# 5. Vérifier l'éligibilité pour preload
echo ""
echo "5️⃣  Éligibilité hstspreload.org :"
echo ""

ELIGIBLE=true

if ! echo "$HSTS_HEADER" | grep -q "max-age=31536000"; then
    echo "   ❌ max-age doit être >= 31536000"
    ELIGIBLE=false
fi

if ! echo "$HSTS_HEADER" | grep -q "includeSubDomains"; then
    echo "   ❌ includeSubDomains requis"
    ELIGIBLE=false
fi

if ! echo "$HSTS_HEADER" | grep -q "preload"; then
    echo "   ❌ preload requis"
    ELIGIBLE=false
fi

if [ "$ELIGIBLE" = true ]; then
    echo "   ✅ ÉLIGIBLE pour soumission à hstspreload.org"
    echo ""
    echo "================================================"
    echo "🎯 PROCHAINES ÉTAPES :"
    echo "================================================"
    echo ""
    echo "1. Aller sur https://hstspreload.org/"
    echo "2. Entrer : $DOMAIN"
    echo "3. Cliquer sur 'Check HSTS preload status and eligibility'"
    echo "4. Si tout est vert, cliquer sur 'Submit'"
    echo ""
    echo "⏱️  Délai de propagation : 6-12 semaines"
    echo "📊 Vérifier le statut : https://hstspreload.org/api/v2/status?domain=$DOMAIN"
    echo ""
else
    echo "   ⚠️  NON ÉLIGIBLE - Corriger les erreurs ci-dessus"
fi

echo ""
echo "================================================"
echo "✅ Vérification terminée"
echo "================================================"
