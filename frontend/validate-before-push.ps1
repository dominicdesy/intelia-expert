# ===============================================
# VALIDATION INTELIA EXPERT - VERSION SIMPLE
# ===============================================

Clear-Host
Write-Host "🚀 Intelia Expert - Validation" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

$ErrorCount = 0
$WarningCount = 0

# ===============================================
# 1. VÉRIFICATIONS DE BASE
# ===============================================
Write-Host ""
Write-Host "1. Vérifications de base..." -ForegroundColor Blue

# Node.js
try {
    $nodeVer = node --version
    Write-Host "✅ Node.js $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js manquant" -ForegroundColor Red
    $ErrorCount++
}

# npm
try {
    $npmVer = npm --version
    Write-Host "✅ npm $npmVer" -ForegroundColor Green
} catch {
    Write-Host "❌ npm manquant" -ForegroundColor Red
    $ErrorCount++
}

# package.json
if (Test-Path "package.json") {
    Write-Host "✅ package.json trouvé" -ForegroundColor Green
    
    $pkg = Get-Content "package.json" -Raw
    if ($pkg -match '"next"') {
        Write-Host "✅ Projet Next.js détecté" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Next.js non détecté" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "❌ package.json manquant" -ForegroundColor Red
    $ErrorCount++
}

# ===============================================
# 2. DÉPENDANCES
# ===============================================
Write-Host ""
Write-Host "2. Vérification dépendances..." -ForegroundColor Blue

if (Test-Path "node_modules") {
    Write-Host "✅ node_modules existe" -ForegroundColor Green
} else {
    Write-Host "⚠️  Installation des dépendances..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dépendances installées" -ForegroundColor Green
    } else {
        Write-Host "❌ Échec installation dépendances" -ForegroundColor Red
        $ErrorCount++
    }
}

# ===============================================
# 3. TYPESCRIPT
# ===============================================
Write-Host ""
Write-Host "3. Vérification TypeScript..." -ForegroundColor Blue

if (Test-Path "tsconfig.json") {
    Write-Host "✅ tsconfig.json trouvé" -ForegroundColor Green
    
    Write-Host "   Compilation TypeScript..." -ForegroundColor Gray
    $tscOutput = npx tsc --noEmit 2>&1
    
    $tsErrors = ($tscOutput | Select-String "error TS").Count
    
    if ($tsErrors -eq 0) {
        Write-Host "✅ TypeScript OK" -ForegroundColor Green
    } else {
        Write-Host "❌ $tsErrors erreurs TypeScript" -ForegroundColor Red
        $ErrorCount++
        
        # Montrer quelques erreurs
        $tscOutput | Select-String "error TS" | Select-Object -First 3 | ForEach-Object {
            Write-Host "   $_" -ForegroundColor Red
        }
        
        # Sauvegarder toutes les erreurs
        $tscOutput | Out-File "typescript-errors.txt"
        Write-Host "   Toutes les erreurs dans: typescript-errors.txt" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  tsconfig.json manquant" -ForegroundColor Yellow
    $WarningCount++
}

# ===============================================
# 4. BUILD TEST
# ===============================================
Write-Host ""
Write-Host "4. Test de build..." -ForegroundColor Blue

Write-Host "   Build Next.js en cours..." -ForegroundColor Gray
$buildOutput = npm run build 2>&1

$buildErrors = $buildOutput | Select-String "Failed to compile|Error:|Build failed"

if ($buildErrors.Count -eq 0) {
    Write-Host "✅ Build réussi" -ForegroundColor Green
} else {
    Write-Host "❌ Build échoué" -ForegroundColor Red
    $ErrorCount++
    
    # Montrer quelques erreurs
    $buildErrors | Select-Object -First 3 | ForEach-Object {
        Write-Host "   $_" -ForegroundColor Red
    }
    
    # Sauvegarder toutes les erreurs
    $buildOutput | Out-File "build-errors.txt"
    Write-Host "   Toutes les erreurs dans: build-errors.txt" -ForegroundColor Gray
}

# ===============================================
# 5. FICHIERS CRITIQUES
# ===============================================
Write-Host ""
Write-Host "5. Fichiers critiques..." -ForegroundColor Blue

$files = @("next.config.js", "tailwind.config.js", ".env.example")
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "✅ $file" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $file manquant" -ForegroundColor Yellow
        $WarningCount++
    }
}

$dirs = @("app", "components", "lib", "types")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "✅ $dir/" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $dir/ manquant" -ForegroundColor Yellow
        $WarningCount++
    }
}

# ===============================================
# 6. ENVIRONNEMENT
# ===============================================
Write-Host ""
Write-Host "6. Variables d'environnement..." -ForegroundColor Blue

if (Test-Path ".env.local") {
    Write-Host "✅ .env.local trouvé" -ForegroundColor Green
    
    $env = Get-Content ".env.local" -Raw
    if ($env -match "NEXT_PUBLIC_SUPABASE_URL") {
        Write-Host "✅ SUPABASE_URL configuré" -ForegroundColor Green
    } else {
        Write-Host "⚠️  SUPABASE_URL manquant" -ForegroundColor Yellow
        $WarningCount++
    }
    
    if ($env -match "NEXT_PUBLIC_SUPABASE_ANON_KEY") {
        Write-Host "✅ SUPABASE_ANON_KEY configuré" -ForegroundColor Green
    } else {
        Write-Host "⚠️  SUPABASE_ANON_KEY manquant" -ForegroundColor Yellow
        $WarningCount++
    }
} else {
    Write-Host "⚠️  .env.local manquant" -ForegroundColor Yellow
    $WarningCount++
}

# ===============================================
# 7. NETTOYAGE
# ===============================================
Write-Host ""
Write-Host "7. Nettoyage..." -ForegroundColor Blue

if (Test-Path ".next") {
    Remove-Item ".next" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Cache .next nettoyé" -ForegroundColor Green
}

# ===============================================
# RÉSUMÉ FINAL
# ===============================================
Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "         RÉSULTATS" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

Write-Host ""
if ($ErrorCount -eq 0) {
    Write-Host "🎉 SUCCÈS !" -ForegroundColor Green -BackgroundColor Black
    Write-Host ""
    Write-Host "Erreurs: $ErrorCount" -ForegroundColor Green
    Write-Host "Avertissements: $WarningCount" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Vous pouvez pusher:" -ForegroundColor Green
    Write-Host ""
    Write-Host "git add ." -BackgroundColor DarkGray
    Write-Host "git commit -m `"fix: resolve build issues`"" -BackgroundColor DarkGray  
    Write-Host "git push origin main" -BackgroundColor DarkGray
} else {
    Write-Host "❌ ÉCHEC" -ForegroundColor Red -BackgroundColor Black
    Write-Host ""
    Write-Host "Erreurs: $ErrorCount" -ForegroundColor Red
    Write-Host "Avertissements: $WarningCount" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "À corriger:" -ForegroundColor Red
    Write-Host "- Voir typescript-errors.txt" -ForegroundColor White
    Write-Host "- Voir build-errors.txt" -ForegroundColor White
    Write-Host "- Relancer ce script" -ForegroundColor White
}

Write-Host ""
Write-Host "===============================" -ForegroundColor Cyan

# Pause
Write-Host ""
Read-Host "Appuyez sur Entrée pour continuer"