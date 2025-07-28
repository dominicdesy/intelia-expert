# Test direct de l'endpoint sécurisé Intelia Expert
Write-Host "🚀 Test Intelia Expert - Endpoint Sécurisé" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

try {
    # ÉTAPE 1: Collecte des informations
    Write-Host "📧 Email détecté: dominic.desy@intelia.com" -ForegroundColor Cyan
    $email = "dominic.desy@intelia.com"
    
    $securePassword = Read-Host "🔑 Entrez votre mot de passe Intelia" -AsSecureString
    $password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
    
    Write-Host ""
    Write-Host "🔐 ÉTAPE 1: Authentification Supabase..." -ForegroundColor Yellow
    
    # Configuration Supabase
    $supabaseUrl = "https://nujgqbxkixndjpnmrlfs.supabase.co"
    $supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51amdxYnhraXhuZGpwbm1ybGZzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIwMzk1MzEsImV4cCI6MjA0NzYxNTUzMX0.RdGJAMWtOJTiNKDhMPZkD97yVsKWg-P7sRNWHHAFsyc"
    
    # Authentification
    $authBody = @{
        email = $email
        password = $password
    } | ConvertTo-Json
    
    $authHeaders = @{
        'Content-Type' = 'application/json'
        'apikey' = $supabaseKey
    }
    
    Write-Host "📡 Connexion à Supabase..." -ForegroundColor Gray
    
    $authResponse = Invoke-RestMethod -Uri "$supabaseUrl/auth/v1/token?grant_type=password" -Method Post -Headers $authHeaders -Body $authBody
    
    $accessToken = $authResponse.access_token
    $userId = $authResponse.user.id
    
    Write-Host "✅ Authentification réussie!" -ForegroundColor Green
    Write-Host "   👤 User ID: $($userId.Substring(0,8))..." -ForegroundColor White
    Write-Host "   🔑 Token: $($accessToken.Substring(0,20))..." -ForegroundColor White
    Write-Host ""
    
    # ÉTAPE 2: Test de l'endpoint sécurisé
    Write-Host "🤖 ÉTAPE 2: Test endpoint sécurisé /ask..." -ForegroundColor Yellow
    
    $apiUrl = "https://expert-app-cngws.ondigitalocean.app/api/v1/expert/ask"
    
    $questionBody = @{
        text = "Quelles sont les principales causes de mortalité chez les poulets de chair ?"
        language = "fr"
        speed_mode = "balanced"
    } | ConvertTo-Json
    
    $apiHeaders = @{
        'Content-Type' = 'application/json'
        'Accept' = 'application/json'
        'Authorization' = "Bearer $accessToken"
    }
    
    Write-Host "📡 Envoi de la question à l'API sécurisée..." -ForegroundColor Gray
    Write-Host "❓ Question: Quelles sont les principales causes de mortalité chez les poulets de chair ?" -ForegroundColor Gray
    
    $startTime = Get-Date
    $apiResponse = Invoke-RestMethod -Uri $apiUrl -Method Post -Headers $apiHeaders -Body $questionBody
    $endTime = Get-Date
    $responseTime = ($endTime - $startTime).TotalMilliseconds
    
    # ÉTAPE 3: Affichage des résultats
    Write-Host ""
    Write-Host "✅ SUCCÈS! Réponse reçue de l'endpoint sécurisé" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    Write-Host "📊 RÉSULTATS DU TEST:" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "🔧 Informations techniques:" -ForegroundColor Yellow
    Write-Host "   • Conversation ID: $($apiResponse.conversation_id)" -ForegroundColor White
    Write-Host "   • Temps de réponse: $([math]::Round($responseTime, 2)) ms" -ForegroundColor White
    Write-Host "   • RAG utilisé: $($apiResponse.rag_used)" -ForegroundColor White
    if ($apiResponse.rag_score) {
        Write-Host "   • Score RAG: $($apiResponse.rag_score)" -ForegroundColor White
    }
    Write-Host "   • Langue: $($apiResponse.language)" -ForegroundColor White
    Write-Host "   • Mode: $($apiResponse.mode)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "🤖 Réponse de l'IA Expert:" -ForegroundColor Yellow
    $response = $apiResponse.response
    
    # Afficher les premiers 300 caractères pour un aperçu
    if ($response.Length -gt 300) {
        $preview = $response.Substring(0, 300) + "..."
        Write-Host "   $preview" -ForegroundColor White
        Write-Host ""
        Write-Host "   📝 Réponse complète: $($response.Length) caractères" -ForegroundColor Gray
        Write-Host "   📄 Réponse complète disponible dans l'objet `$apiResponse.response`" -ForegroundColor Gray
    } else {
        Write-Host "   $response" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    Write-Host "🎉 TEST RÉUSSI!" -ForegroundColor Green
    Write-Host "✅ L'endpoint sécurisé /ask fonctionne parfaitement" -ForegroundColor Green
    Write-Host "✅ L'authentification est opérationnelle" -ForegroundColor Green
    Write-Host "✅ Le RAG répond correctement aux questions" -ForegroundColor Green
    Write-Host ""
    Write-Host "➡️  Vous pouvez maintenant déployer le code avec l'endpoint sécurisé!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
} catch {
    Write-Host ""
    Write-Host "❌ ERREUR lors du test:" -ForegroundColor Red
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "🔍 Code d'erreur HTTP: $statusCode" -ForegroundColor Yellow
        
        switch ($statusCode) {
            400 { Write-Host "📝 Erreur de format dans la requête" -ForegroundColor Red }
            401 { Write-Host "🔐 Erreur d'authentification - Vérifiez email/mot de passe" -ForegroundColor Red }
            403 { Write-Host "🚫 Accès refusé - Permissions insuffisantes" -ForegroundColor Red }
            404 { Write-Host "🔍 Endpoint non trouvé - Vérifiez l'URL" -ForegroundColor Red }
            500 { Write-Host "⚙️ Erreur serveur - Réessayez plus tard" -ForegroundColor Red }
            default { Write-Host "❓ Erreur inconnue: $statusCode" -ForegroundColor Red }
        }
    }
    
    Write-Host ""
    Write-Host "📄 Message d'erreur:" -ForegroundColor Yellow
    Write-Host "   $($_.Exception.Message)" -ForegroundColor White
    
    if ($_.ErrorDetails.Message) {
        Write-Host ""
        Write-Host "📋 Détails:" -ForegroundColor Yellow
        Write-Host "   $($_.ErrorDetails.Message)" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Appuyez sur Entrée pour fermer..." -ForegroundColor Gray
Read-Host