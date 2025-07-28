# ==================== SCRIPT DIAGNOSTIC INTELIA EXPERT ====================
# Diagnostic complet sans dépendance sur les tokens récupérés manuellement
# Version: 2.0 - Autonome et complet

param(
    [string]$TestToken = $null,
    [switch]$SkipAuth = $false,
    [switch]$Verbose = $false
)

$baseUrl = "https://expert-app-cngws.ondigitalocean.app"
$ErrorActionPreference = "Continue"

# Fonction d'affichage avec couleurs
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White",
        [string]$Prefix = ""
    )
    
    $colorMap = @{
        "Red" = [ConsoleColor]::Red
        "Green" = [ConsoleColor]::Green
        "Yellow" = [ConsoleColor]::Yellow
        "Cyan" = [ConsoleColor]::Cyan
        "Magenta" = [ConsoleColor]::Magenta
        "Blue" = [ConsoleColor]::Blue
        "White" = [ConsoleColor]::White
        "Gray" = [ConsoleColor]::Gray
    }
    
    if ($Prefix) {
        Write-Host "$Prefix " -NoNewline -ForegroundColor $colorMap[$Color]
    }
    Write-Host $Message -ForegroundColor $colorMap[$Color]
}

# Fonction de test d'endpoint
function Test-ApiEndpoint {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = $null,
        [string]$Description,
        [int]$TimeoutSec = 30
    )
    
    Write-ColorOutput "`n🔍 TEST: $Description" "Yellow"
    Write-ColorOutput "URL: $Method $Url" "Gray"
    
    if ($Verbose -and $Headers.Count -gt 0) {
        Write-ColorOutput "Headers:" "Gray"
        $Headers.GetEnumerator() | ForEach-Object {
            $value = if ($_.Key -eq "Authorization") { 
                $_.Value.Substring(0, [Math]::Min(30, $_.Value.Length)) + "..." 
            } else { 
                $_.Value 
            }
            Write-ColorOutput "  $($_.Key): $value" "Gray"
        }
    }
    
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    
    try {
        if ($Body) {
            if ($Verbose) { Write-ColorOutput "Body: $Body" "Gray" }
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $Headers -Body $Body -TimeoutSec $TimeoutSec
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Headers $Headers -TimeoutSec $TimeoutSec
        }
        
        $stopwatch.Stop()
        
        Write-ColorOutput "✅ SUCCÈS ($($stopwatch.ElapsedMilliseconds)ms)" "Green"
        
        if ($Verbose) {
            Write-ColorOutput "Réponse complète:" "Cyan"
            Write-ColorOutput ($response | ConvertTo-Json -Depth 3) "White"
        } else {
            # Affichage résumé
            if ($response.status) {
                Write-ColorOutput "Status: $($response.status)" "Cyan"
            }
            if ($response.message) {
                Write-ColorOutput "Message: $($response.message)" "Cyan"
            }
            if ($response.response) {
                $preview = if ($response.response.Length -gt 100) { 
                    $response.response.Substring(0, 100) + "..." 
                } else { 
                    $response.response 
                }
                Write-ColorOutput "Réponse: $preview" "Cyan"
            }
        }
        
        return @{ Success = $true; Response = $response; StatusCode = 200 }
        
    } catch {
        $stopwatch.Stop()
        
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "Network Error" }
        $statusDescription = if ($_.Exception.Response) { $_.Exception.Response.StatusDescription } else { $_.Exception.Message }
        
        Write-ColorOutput "❌ ÉCHEC ($($stopwatch.ElapsedMilliseconds)ms)" "Red"
        Write-ColorOutput "Status: $statusCode - $statusDescription" "Red"
        
        # Essayer de récupérer les détails de l'erreur
        if ($_.Exception.Response) {
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $reader = New-Object System.IO.StreamReader($stream)
                $errorDetails = $reader.ReadToEnd()
                if ($errorDetails) {
                    Write-ColorOutput "Détails: $errorDetails" "Red"
                }
            } catch {
                Write-ColorOutput "Impossible de lire les détails de l'erreur" "Red"
            }
        }
        
        return @{ Success = $false; StatusCode = $statusCode; Error = $statusDescription }
    }
}

# Fonction de génération de tokens JWT de test
function New-TestJWT {
    param(
        [string]$Type = "fake"
    )
    
    switch ($Type) {
        "fake" {
            # Token JWT complètement fake mais bien formaté
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        }
        "expired" {
            # Token expiré (exp dans le passé)
            $header = @{ alg = "HS256"; typ = "JWT" } | ConvertTo-Json -Compress
            $payload = @{ sub = "test"; exp = 1000000000; iat = 999999999 } | ConvertTo-Json -Compress
            $headerB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($header))
            $payloadB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
            return "$headerB64.$payloadB64.fake_signature"
        }
        "malformed" {
            return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload"
        }
        default {
            return $null
        }
    }
}

# ==================== DÉBUT DES TESTS ====================

Write-ColorOutput "🚀 DIAGNOSTIC COMPLET INTELIA EXPERT" "Magenta"
Write-ColorOutput "====================================" "Magenta"
Write-ColorOutput "Timestamp: $(Get-Date)" "Gray"
Write-ColorOutput "Base URL: $baseUrl" "Gray"

# ==================== PHASE 1: TESTS DE BASE ====================
Write-ColorOutput "`n📍 PHASE 1: CONNECTIVITÉ ET SANTÉ DU BACKEND" "Magenta"

# Test 1: Santé du système
$healthResult = Test-ApiEndpoint -Url "$baseUrl/api/v1/" -Description "Health Check Général"

# Test 2: Health endpoint spécifique
Test-ApiEndpoint -Url "$baseUrl/api/v1/system/health" -Description "Health Check Système"

# ==================== PHASE 2: TESTS D'AUTHENTIFICATION ====================
Write-ColorOutput "`n📍 PHASE 2: TESTS D'AUTHENTIFICATION" "Magenta"

$testBody = @{
    text = "Test PowerShell diagnostic"
    language = "fr"
    speed_mode = "balanced"
} | ConvertTo-Json

$baseHeaders = @{
    "Content-Type" = "application/json"
    "Accept" = "application/json"
    "User-Agent" = "PowerShell-Diagnostic/2.0"
}

# Test 3: Requête sans authentification (devrait être 401 ou 403)
$noAuthResult = Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $baseHeaders -Body $testBody -Description "Sans Authentification (attendu: 401/403)"

# Test 4: Token JWT fake
$fakeToken = New-TestJWT -Type "fake"
$fakeAuthHeaders = $baseHeaders.Clone()
$fakeAuthHeaders["Authorization"] = "Bearer $fakeToken"

Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $fakeAuthHeaders -Body $testBody -Description "Token JWT Fake (attendu: 401)"

# Test 5: Token malformé
$malformedToken = New-TestJWT -Type "malformed"
$malformedAuthHeaders = $baseHeaders.Clone()
$malformedAuthHeaders["Authorization"] = "Bearer $malformedToken"

Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $malformedAuthHeaders -Body $testBody -Description "Token JWT Malformé (attendu: 401)"

# Test 6: Token expiré
$expiredToken = New-TestJWT -Type "expired"
$expiredAuthHeaders = $baseHeaders.Clone()
$expiredAuthHeaders["Authorization"] = "Bearer $expiredToken"

Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $expiredAuthHeaders -Body $testBody -Description "Token JWT Expiré (attendu: 401)"

# ==================== PHASE 3: TEST AVEC TOKEN FOURNI ====================
if ($TestToken) {
    Write-ColorOutput "`n📍 PHASE 3: TEST AVEC TOKEN FOURNI" "Magenta"
    
    # Analyser le token fourni
    Write-ColorOutput "`n🔍 Analyse du token fourni..." "Yellow"
    try {
        $parts = $TestToken.Split('.')
        if ($parts.Length -eq 3) {
            # Décoder le payload
            $payloadPadded = $parts[1] + "=" * (4 - ($parts[1].Length % 4))
            $payloadBytes = [Convert]::FromBase64String($payloadPadded)
            $payload = [Text.Encoding]::UTF8.GetString($payloadBytes)
            $payloadObj = $payload | ConvertFrom-Json
            
            Write-ColorOutput "✅ Token JWT valide structurellement" "Green"
            Write-ColorOutput "Payload: $payload" "Cyan"
            
            if ($payloadObj.exp) {
                $expDate = [DateTimeOffset]::FromUnixTimeSeconds($payloadObj.exp).DateTime
                $now = Get-Date
                if ($expDate -gt $now) {
                    Write-ColorOutput "✅ Token non expiré (expire: $expDate)" "Green"
                } else {
                    Write-ColorOutput "❌ Token expiré depuis: $expDate" "Red"
                }
            }
        } else {
            Write-ColorOutput "❌ Token malformé (pas 3 parties)" "Red"
        }
    } catch {
        Write-ColorOutput "❌ Erreur analyse token: $($_.Exception.Message)" "Red"
    }
    
    # Test avec le token fourni
    $userAuthHeaders = $baseHeaders.Clone()
    $userAuthHeaders["Authorization"] = "Bearer $TestToken"
    
    Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $userAuthHeaders -Body $testBody -Description "Token Utilisateur Fourni"
}

# ==================== PHASE 4: TESTS AVANCÉS ====================
Write-ColorOutput "`n📍 PHASE 4: TESTS AVANCÉS" "Magenta"

# Test CORS
$corsHeaders = @{
    "Origin" = "http://localhost:3000"
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "authorization,content-type"
}

Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "OPTIONS" -Headers $corsHeaders -Description "CORS Preflight"

# Test avec différents User-Agents
$browserHeaders = $baseHeaders.Clone()
$browserHeaders["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

Test-ApiEndpoint -Url "$baseUrl/api/v1/expert/ask" -Method "POST" -Headers $browserHeaders -Body $testBody -Description "User-Agent Navigateur (sans auth)"

# ==================== RÉSULTATS ET RECOMMANDATIONS ====================
Write-ColorOutput "`n📊 ANALYSE DES RÉSULTATS" "Magenta"
Write-ColorOutput "========================" "Magenta"

if ($healthResult.Success) {
    Write-ColorOutput "✅ Backend accessible et fonctionnel" "Green"
} else {
    Write-ColorOutput "❌ Backend inaccessible - problème majeur" "Red"
    exit 1
}

Write-ColorOutput "`n🎯 PROCHAINES ÉTAPES RECOMMANDÉES:" "Yellow"

if ($TestToken) {
    Write-ColorOutput "1. Si votre token a fonctionné → Le problème est dans le frontend React" "White"
    Write-ColorOutput "2. Si votre token a échoué → Problème d'authentification Supabase" "White"
} else {
    Write-ColorOutput "1. Récupérez votre token utilisateur réel depuis le navigateur" "White"
    Write-ColorOutput "2. Relancez avec: .\diagnostic.ps1 -TestToken 'VOTRE_TOKEN'" "White"
}

Write-ColorOutput "3. Si tous les tests d'auth échouent → Problème configuration backend" "White"
Write-ColorOutput "4. Si les tests de base échouent → Problème réseau/infrastructure" "White"

Write-ColorOutput "`n💡 COMMANDES UTILES:" "Cyan"
Write-ColorOutput "Mode verbose: .\diagnostic.ps1 -Verbose" "Gray"
Write-ColorOutput "Avec token: .\diagnostic.ps1 -TestToken 'eyJ...' -Verbose" "Gray"
Write-ColorOutput "Skip auth: .\diagnostic.ps1 -SkipAuth" "Gray"

Write-ColorOutput "`n🏁 DIAGNOSTIC TERMINÉ" "Magenta"
Write-ColorOutput "Timestamp: $(Get-Date)" "Gray"