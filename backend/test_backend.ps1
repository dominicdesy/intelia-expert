# ============================================================================
# Lanceur PowerShell pour Tests Backend Intelia Expert
# VERSION 3.5.0 - Compatible Windows + PowerShell
# ============================================================================

param(
    [string]$BaseUrl = "http://localhost:8080",
    [switch]$Verbose,
    [switch]$SaveReport,
    [int]$Timeout = 30,
    [switch]$Help
)

# Fonction d'aide
function Show-Help {
    Write-Host "🚀 LANCEUR POWERSHELL - TESTS BACKEND INTELIA EXPERT" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\test_backend.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -BaseUrl <url>     URL du backend (défaut: http://localhost:8080)"
    Write-Host "  -Verbose           Mode verbose pour plus de détails"
    Write-Host "  -SaveReport        Sauvegarder le rapport en JSON"
    Write-Host "  -Timeout <sec>     Timeout des requêtes en secondes (défaut: 30)"
    Write-Host "  -Help              Afficher cette aide"
    Write-Host ""
    Write-Host "EXEMPLES:" -ForegroundColor Green
    Write-Host "  .\test_backend.ps1"
    Write-Host "  .\test_backend.ps1 -BaseUrl 'https://expert-api.intelia.com' -Verbose"
    Write-Host "  .\test_backend.ps1 -SaveReport -Timeout 60"
    Write-Host ""
    exit 0
}

if ($Help) {
    Show-Help
}

# Configuration initiale
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Couleurs PowerShell
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }

# Header
Clear-Host
Write-Host "🚀 TESTS BACKEND INTELIA EXPERT - POWERSHELL LAUNCHER" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "📅 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "🌐 URL Backend: $BaseUrl" -ForegroundColor Gray
Write-Host "🔧 Verbose: $(if($Verbose){'Activé'}else{'Désactivé'})" -ForegroundColor Gray
Write-Host "💾 Rapport JSON: $(if($SaveReport){'Oui'}else{'Non'})" -ForegroundColor Gray
Write-Host "⏱️ Timeout: $Timeout secondes" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# VÉRIFICATIONS PRÉALABLES
# ============================================================================

Write-Info "🔍 VÉRIFICATIONS PRÉALABLES..."

# Vérifier Python
Write-Host "   • Python..." -NoNewline
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success " ✅ $pythonVersion"
    } else {
        Write-Error " ❌ Python non trouvé"
        Write-Error "💡 Installez Python depuis https://python.org"
        exit 1
    }
} catch {
    Write-Error " ❌ Python non trouvé"
    Write-Error "💡 Installez Python depuis https://python.org"
    exit 1
}

# Vérifier les modules Python requis
Write-Host "   • Modules Python..." -NoNewline
$requiredModules = @("requests", "json", "datetime", "uuid")
$missingModules = @()

try {
    # Test rapide des imports
    $testScript = @"
import sys
try:
    import requests
    import json
    import datetime
    import uuid
    print("OK")
except ImportError as e:
    print(f"MISSING: {e}")
    sys.exit(1)
"@
    
    $result = python -c $testScript 2>&1
    if ($LASTEXITCODE -eq 0 -and $result -eq "OK") {
        Write-Success " ✅ Tous les modules disponibles"
    } else {
        Write-Error " ❌ Modules manquants"
        Write-Warning "💡 Installation automatique des dépendances..."
        
        # Installer requests si manquant
        python -m pip install requests > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "   ✅ Module 'requests' installé"
        } else {
            Write-Error "   ❌ Échec installation 'requests'"
        }
    }
} catch {
    Write-Warning " ⚠️ Vérification modules échouée, tentative d'installation..."
    python -m pip install requests > $null 2>&1
}

# Vérifier la connectivité au backend
Write-Host "   • Connectivité backend..." -NoNewline
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Success " ✅ Backend accessible"
} catch {
    Write-Warning " ⚠️ Backend non accessible"
    Write-Warning "💡 Assurez-vous que le backend est démarré sur $BaseUrl"
    
    $continue = Read-Host "Continuer quand même ? (o/N)"
    if ($continue -ne "o" -and $continue -ne "O") {
        Write-Info "❌ Tests annulés par l'utilisateur"
        exit 1
    }
}

Write-Host ""

# ============================================================================
# CRÉATION DU SCRIPT PYTHON DYNAMIQUE
# ============================================================================

Write-Info "📝 GÉNÉRATION DU SCRIPT DE TEST..."

# Le script Python complet (intégré dans le PowerShell)
$pythonScript = @'
#!/usr/bin/env python3
"""
Script de Test Backend - Généré par PowerShell
Version intégrée pour compatibilité Windows
"""

import requests
import json
import time
import sys
from datetime import datetime
import uuid

class BackendTester:
    def __init__(self, base_url, verbose=False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'User-Agent': 'Intelia-PowerShell-Tester/3.5.0'
        })
        self.test_results = []
        
        # Données de test UTF-8
        self.utf8_cases = {
            "french": "Température élevée à 32°C pour poulets - humidité 65%",
            "spanish": "¿Cuál es la nutrición óptima para pollos de engorde?", 
            "symbols": "Coût: 15€/kg, efficacité: 95%, température: 32°C",
            "complex": "Mes poulets de 25 jours pèsent 800g à 32°C - normal?",
            "emoji": "🐔 Problème croissance poulets 📊 Aide urgente! 🔥"
        }

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level in ["ERROR", "SUCCESS", "FAIL"]:
            print(f"[{timestamp}] {level}: {message}")

    def make_request(self, method, endpoint, data=None, timeout=30):
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method, url=url, json=data, timeout=timeout
            )
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response_data,
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response": {"error": str(e)},
                "url": url
            }

    def test_endpoint(self, name, method, endpoint, data=None, expected=200):
        print(f"🧪 Test: {name}")
        start_time = time.time()
        result = self.make_request(method, endpoint, data)
        duration = round((time.time() - start_time) * 1000, 2)
        
        passed = result["success"] and result["status_code"] == expected
        
        test_result = {
            "name": name,
            "endpoint": endpoint,
            "method": method,
            "expected": expected,
            "actual": result["status_code"],
            "passed": passed,
            "duration_ms": duration,
            "response": result["response"]
        }
        
        self.test_results.append(test_result)
        
        if passed:
            print(f"✅ {name} -> PASSED ({duration}ms)")
        else:
            print(f"❌ {name} -> FAILED ({duration}ms) - Status: {result['status_code']}")
        
        return test_result

    def run_critical_tests(self):
        """Tests critiques essentiels"""
        print("\n" + "="*60)
        print("🎯 TESTS CRITIQUES ESSENTIELS")
        print("="*60)
        
        # 1. Health checks
        self.test_endpoint("API Root", "GET", "/")
        self.test_endpoint("Health Check", "GET", "/health")
        self.test_endpoint("System Health", "GET", "/v1/system/health")
        
        # 2. Tests UTF-8 corrigés
        for name, question in self.utf8_cases.items():
            self.test_endpoint(
                f"UTF-8 Question ({name})",
                "POST", "/v1/expert/ask-public",
                data={"text": question, "language": "fr", "speed_mode": "fast"}
            )
        
        # 3. Tests endpoints logging corrigés (404 fixes)
        self.test_endpoint("Logging Health", "GET", "/v1/logging/health")
        self.test_endpoint("Logging Analytics", "GET", "/v1/logging/analytics")
        self.test_endpoint("Admin Stats", "GET", "/v1/logging/admin/stats")
        
        # 4. Tests debug corrections
        self.test_endpoint("Debug Corrections", "GET", "/debug/corrections")
        self.test_endpoint("UTF-8 Debug", "GET", "/debug/utf8-test")
        
        # 5. Expert topics
        self.test_endpoint("Topics FR", "GET", "/v1/expert/topics?language=fr")
        self.test_endpoint("Topics EN", "GET", "/v1/expert/topics?language=en")

    def run_extended_tests(self):
        """Tests étendus si demandés"""
        print("\n" + "="*60)
        print("🔧 TESTS ÉTENDUS")
        print("="*60)
        
        # Tests auth debug
        self.test_endpoint("Auth Debug", "GET", "/v1/auth/debug")
        
        # Tests admin
        self.test_endpoint("Admin Dashboard", "GET", "/v1/admin/dashboard")
        self.test_endpoint("Admin Users", "GET", "/v1/admin/users")
        
        # Tests expert debug
        self.test_endpoint("Expert Debug System", "GET", "/v1/expert/debug-system")
        self.test_endpoint("Expert Debug Auth", "GET", "/v1/expert/debug-auth")

    def print_report(self):
        """Affiche le rapport final"""
        total = len(self.test_results)
        passed = sum(1 for t in self.test_results if t["passed"])
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("📊 RAPPORT FINAL")
        print("="*70)
        print(f"✅ Tests réussis: {passed}")
        print(f"❌ Tests échoués: {failed}")
        print(f"📊 Total: {total}")
        print(f"🎯 Taux de succès: {success_rate:.1f}%")
        
        if failed > 0:
            print(f"\n❌ ÉCHECS DÉTAILLÉS:")
            for test in self.test_results:
                if not test["passed"]:
                    print(f"   • {test['name']} -> {test['actual']} (attendu: {test['expected']})")
        
        # Analyse des corrections
        utf8_tests = [t for t in self.test_results if "UTF-8" in t["name"]]
        utf8_success = sum(1 for t in utf8_tests if t["passed"])
        print(f"\n🔤 Corrections UTF-8: {utf8_success}/{len(utf8_tests)} OK")
        
        logging_tests = [t for t in self.test_results if "logging" in t["endpoint"].lower()]
        logging_success = sum(1 for t in logging_tests if t["passed"])
        print(f"📊 Corrections Logging: {logging_success}/{len(logging_tests)} OK")
        
        if success_rate >= 90:
            print("\n🎉 EXCELLENT! Backend très stable après corrections.")
        elif success_rate >= 75:
            print("\n✅ BON! Backend fonctionnel avec améliorations mineures.")
        elif success_rate >= 50:
            print("\n⚠️ ATTENTION! Plusieurs problèmes détectés.")
        else:
            print("\n🚨 CRITIQUE! Backend nécessite corrections majeures.")

    def save_json_report(self, filename):
        """Sauvegarde en JSON"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for t in self.test_results if t["passed"]),
            "success_rate": (sum(1 for t in self.test_results if t["passed"]) / len(self.test_results) * 100) if self.test_results else 0,
            "tests": self.test_results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"📄 Rapport sauvegardé: {filename}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")

def main():
    if len(sys.argv) < 2:
        print("❌ URL manquante")
        return
    
    base_url = sys.argv[1]
    verbose = len(sys.argv) > 2 and sys.argv[2] == "verbose"
    save_report = len(sys.argv) > 3 and sys.argv[3] == "save"
    
    print(f"🚀 TESTS BACKEND INTELIA EXPERT")
    print(f"🌐 URL: {base_url}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = BackendTester(base_url, verbose)
    
    try:
        # Tests critiques toujours exécutés
        tester.run_critical_tests()
        
        # Tests étendus si verbose
        if verbose:
            tester.run_extended_tests()
        
        tester.print_report()
        
        if save_report:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backend_test_report_{timestamp}.json"
            tester.save_json_report(filename)
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrompus")
    except Exception as e:
        print(f"\n💥 Erreur: {e}")

if __name__ == "__main__":
    main()
'@

# Sauvegarder le script Python temporaire
$tempScript = "$env:TEMP\intelia_backend_test.py"
$pythonScript | Out-File -FilePath $tempScript -Encoding UTF8

Write-Success "   ✅ Script de test généré: $tempScript"
Write-Host ""

# ============================================================================
# EXÉCUTION DES TESTS
# ============================================================================

Write-Info "🚀 LANCEMENT DES TESTS..."
Write-Host ""

# Préparer les arguments
$args = @($BaseUrl)
if ($Verbose) { $args += "verbose" }
if ($SaveReport) { $args += "save" }

try {
    # Exécuter le script Python
    $startTime = Get-Date
    
    if ($Verbose) {
        Write-Info "🔧 Mode verbose activé - Tous les détails affichés"
    }
    
    python $tempScript @args
    $exitCode = $LASTEXITCODE
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    Write-Host ""
    Write-Info "⏱️ Durée totale: $([math]::Round($duration, 2)) secondes"
    
    if ($exitCode -eq 0) {
        Write-Success "✅ Tests terminés avec succès!"
    } else {
        Write-Warning "⚠️ Tests terminés avec des problèmes (code: $exitCode)"
    }
    
} catch {
    Write-Error "💥 Erreur lors de l'exécution des tests: $($_.Exception.Message)"
    exit 1
} finally {
    # Nettoyer le fichier temporaire
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
    }
}

# ============================================================================
# ACTIONS POST-TESTS
# ============================================================================

Write-Host ""
Write-Info "📋 ACTIONS RECOMMANDÉES:"

if ($SaveReport) {
    Write-Host "   • Consultez le rapport JSON généré pour les détails"
}

Write-Host "   • Si des tests échouent, vérifiez que le backend est démarré"
Write-Host "   • Pour plus de détails, relancez avec -Verbose"
Write-Host "   • Les corrections UTF-8 et logging 404 sont automatiquement testées"

Write-Host ""
Write-Info "🔧 COMMANDES UTILES:"
Write-Host "   • Relancer en verbose:" -ForegroundColor Gray
Write-Host "     .\test_backend.ps1 -Verbose" -ForegroundColor White
Write-Host "   • Tester un autre serveur:" -ForegroundColor Gray  
Write-Host "     .\test_backend.ps1 -BaseUrl 'https://api.example.com'" -ForegroundColor White
Write-Host "   • Sauvegarder le rapport:" -ForegroundColor Gray
Write-Host "     .\test_backend.ps1 -SaveReport" -ForegroundColor White

Write-Host ""
Write-Success "✅ Script PowerShell terminé!"