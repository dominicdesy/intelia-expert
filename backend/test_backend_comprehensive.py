#!/usr/bin/env python3
"""
Script de Test Complet Backend Intelia Expert
VERSION 3.5.0 - Post-corrections expert.py et auth.py

Ce script teste TOUS les endpoints pour s'assurer que le backend est solide
après les modifications critiques dans expert.py et auth.py.

Usage:
    python test_backend_comprehensive.py [--base-url http://localhost:8080] [--verbose]
"""

import requests
import json
import time
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid
import base64

class BackendTester:
    def __init__(self, base_url: str = "http://localhost:8080", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8',
            'User-Agent': 'Intelia-Backend-Tester/3.5.0'
        })
        
        # Résultats des tests
        self.test_results = []
        self.auth_token = None
        self.test_user_email = "test@intelia.com"
        self.test_conversation_id = None
        
        # Données de test UTF-8
        self.utf8_test_cases = {
            "french_accents": "Température élevée à 32°C pour poulets - humidité 65%",
            "spanish_special": "¿Cuál es la nutrición óptima para pollos de engorde?",
            "symbols_mixed": "Coût: 15€/kg, efficacité: 95%, température: 32°C",
            "complex_question": "Mes poulets Ross 308 de 25 jours pèsent 800g à 32°C - est-ce normal?",
            "emoji_question": "🐔 Problème croissance poulets 📊 Besoin aide urgente! 🔥"
        }
        
        print(f"🚀 Initialisation du testeur backend")
        print(f"📡 URL de base: {self.base_url}")
        print(f"🔤 Mode verbose: {verbose}")
        print(f"🧪 Cas de test UTF-8: {len(self.utf8_test_cases)}")

    def log(self, message: str, level: str = "INFO"):
        """Log avec timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self.verbose or level in ["ERROR", "SUCCESS", "FAIL"]:
            print(f"[{timestamp}] {level}: {message}")

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Effectue une requête HTTP avec gestion d'erreurs complète"""
        url = f"{self.base_url}{endpoint}"
        
        # Headers par défaut + headers spécifiques
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        self.log(f"🔄 {method} {endpoint}", "DEBUG")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data if data else None,
                headers=request_headers,
                timeout=timeout
            )
            
            # Tentative de parsing JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            result = {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response_data,
                "headers": dict(response.headers),
                "url": url,
                "method": method,
                "request_data": data
            }
            
            # Log du résultat
            if response.status_code < 400:
                self.log(f"✅ {method} {endpoint} -> {response.status_code}", "SUCCESS")
            else:
                self.log(f"❌ {method} {endpoint} -> {response.status_code}: {response_data}", "ERROR")
            
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "success": False,
                "status_code": 0,
                "response": {"error": "Request timeout"},
                "url": url,
                "method": method,
                "request_data": data
            }
            self.log(f"⏰ {method} {endpoint} -> Timeout", "ERROR")
            return error_result
            
        except requests.exceptions.ConnectionError:
            error_result = {
                "success": False,
                "status_code": 0,
                "response": {"error": "Connection error - Backend may be down"},
                "url": url,
                "method": method,
                "request_data": data
            }
            self.log(f"🔌 {method} {endpoint} -> Connection Error", "ERROR")
            return error_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "status_code": 0,
                "response": {"error": f"Unexpected error: {str(e)}"},
                "url": url,
                "method": method,
                "request_data": data
            }
            self.log(f"💥 {method} {endpoint} -> Unexpected Error: {e}", "ERROR")
            return error_result

    def test_endpoint(self, name: str, method: str, endpoint: str, 
                     data: Optional[Dict] = None, headers: Optional[Dict] = None,
                     expected_status: int = 200, description: str = "") -> Dict[str, Any]:
        """Test un endpoint spécifique"""
        self.log(f"🧪 Test: {name}", "INFO")
        
        start_time = time.time()
        result = self.make_request(method, endpoint, data, headers)
        duration = round((time.time() - start_time) * 1000, 2)
        
        # Évaluation du test
        test_passed = (
            result["success"] and 
            result["status_code"] == expected_status
        )
        
        test_result = {
            "name": name,
            "description": description,
            "endpoint": endpoint,
            "method": method,
            "expected_status": expected_status,
            "actual_status": result["status_code"],
            "passed": test_passed,
            "duration_ms": duration,
            "response": result["response"],
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results.append(test_result)
        
        if test_passed:
            self.log(f"✅ {name} -> PASSED ({duration}ms)", "SUCCESS")
        else:
            self.log(f"❌ {name} -> FAILED ({duration}ms) - Status: {result['status_code']}", "FAIL")
            if self.verbose:
                self.log(f"   Response: {result['response']}", "DEBUG")
        
        return test_result

    def run_health_tests(self):
        """Tests des endpoints de santé système"""
        print("\n" + "="*60)
        print("🩺 TESTS DE SANTÉ SYSTÈME")
        print("="*60)
        
        # Test root endpoint
        self.test_endpoint(
            "Root API Info",
            "GET", "/",
            description="Endpoint racine avec informations API"
        )
        
        # Test health principal
        self.test_endpoint(
            "Health Check Principal",
            "GET", "/health",
            description="Health check global de l'API"
        )
        
        # Test health system
        self.test_endpoint(
            "System Health",
            "GET", "/v1/system/health",
            description="Health check système détaillé"
        )
        
        # Test health logging
        self.test_endpoint(
            "Logging Health",
            "GET", "/v1/logging/health",
            description="Health check système de logging (CORRIGÉ 404)"
        )
        
        # Test health admin
        self.test_endpoint(
            "Health Detailed", 
            "GET", "/v1/health/health",
            description="Health check détaillé (CORRIGÉ 404)"
        )

    def run_auth_tests(self):
        """Tests du système d'authentification"""
        print("\n" + "="*60)
        print("🔐 TESTS D'AUTHENTIFICATION")
        print("="*60)
        
        # Test auth debug
        self.test_endpoint(
            "Auth Debug Info",
            "GET", "/v1/auth/debug",
            description="Diagnostics configuration authentification"
        )
        
        # Test login (sans credentials valides - expect 401)
        self.test_endpoint(
            "Login Test",
            "POST", "/v1/auth/login",
            data={
                "email": self.test_user_email,
                "password": "test_password_123"
            },
            expected_status=401,
            description="Test login (échec attendu sans compte valide)"
        )
        
        # Note: Pour les tests authentifiés, nous aurions besoin d'un vrai compte
        # ou d'un système de mock auth pour les tests

    def run_expert_public_tests(self):
        """Tests des endpoints expert publics (sans auth)"""
        print("\n" + "="*60)
        print("🤖 TESTS EXPERT SYSTÈME (PUBLIC)")
        print("="*60)
        
        # Test topics (doit fonctionner sans auth)
        self.test_endpoint(
            "Expert Topics FR",
            "GET", "/v1/expert/topics?language=fr",
            description="Sujets suggérés en français"
        )
        
        self.test_endpoint(
            "Expert Topics EN",
            "GET", "/v1/expert/topics?language=en", 
            description="Sujets suggérés en anglais"
        )
        
        self.test_endpoint(
            "Expert Topics ES",
            "GET", "/v1/expert/topics?language=es",
            description="Sujets suggérés en espagnol"
        )
        
        # Test questions publiques avec cas UTF-8
        for test_name, question_text in self.utf8_test_cases.items():
            self.test_endpoint(
                f"Question Publique UTF-8: {test_name}",
                "POST", "/v1/expert/ask-public",
                data={
                    "text": question_text,
                    "language": "fr",
                    "speed_mode": "fast"
                },
                description=f"Test UTF-8 CORRIGÉ: {question_text[:50]}..."
            )
        
        # Test feedback
        self.test_endpoint(
            "Feedback Submission",
            "POST", "/v1/expert/feedback",
            data={
                "rating": "positive",
                "comment": "Test feedback avec accents éàçù",
                "conversation_id": str(uuid.uuid4())
            },
            description="Soumission feedback avec caractères UTF-8"
        )

    def run_expert_debug_tests(self):
        """Tests des endpoints de debug expert"""
        print("\n" + "="*60)
        print("🔧 TESTS DEBUG EXPERT SYSTÈME")
        print("="*60)
        
        # Test debug système
        self.test_endpoint(
            "Expert Debug System",
            "GET", "/v1/expert/debug-system",
            description="Diagnostics détaillés du système expert"
        )
        
        # Test debug auth
        self.test_endpoint(
            "Expert Debug Auth",
            "GET", "/v1/expert/debug-auth",
            description="Diagnostics rapides authentification"
        )
        
        # Test UTF-8 direct
        self.test_endpoint(
            "Expert Test UTF-8 Direct",
            "POST", "/v1/expert/test-utf8",
            data={
                "text": "Test direct UTF-8: éàçù ñ¿¡ 32°C 95% €",
                "language": "fr"
            },
            description="Test validation UTF-8 réécrite"
        )

    def run_logging_tests(self):
        """Tests du système de logging"""
        print("\n" + "="*60)
        print("📊 TESTS SYSTÈME DE LOGGING")
        print("="*60)
        
        # Test analytics (CORRIGÉ 404)
        self.test_endpoint(
            "Logging Analytics",
            "GET", "/v1/logging/analytics?days=7",
            description="Analytics logging (ENDPOINT CORRIGÉ 404)"
        )
        
        # Test admin stats (CORRIGÉ 404)
        self.test_endpoint(
            "Logging Admin Stats",
            "GET", "/v1/logging/admin/stats",
            description="Statistiques admin (ENDPOINT CORRIGÉ 404)"
        )
        
        # Test database info (CORRIGÉ 404)
        self.test_endpoint(
            "Logging Database Info",
            "GET", "/v1/logging/database/info",
            description="Informations base de données (ENDPOINT CORRIGÉ 404)"
        )
        
        # Test conversations utilisateur (CORRIGÉ 404)
        test_user_id = "test_user_123"
        self.test_endpoint(
            "User Conversations",
            "GET", f"/v1/logging/conversations/{test_user_id}",
            description="Conversations utilisateur (ENDPOINT CORRIGÉ 404)"
        )
        
        # Test création conversation
        conversation_data = {
            "user_id": test_user_id,
            "question": "Test question avec accents éàçù",
            "response": "Test réponse avec caractères spéciaux ñ¿¡",
            "conversation_id": str(uuid.uuid4()),
            "confidence_score": 0.85,
            "response_time_ms": 1500,
            "language": "fr",
            "rag_used": True
        }
        
        result = self.test_endpoint(
            "Create Conversation",
            "POST", "/v1/logging/conversations",
            data=conversation_data,
            expected_status=201,
            description="Création conversation avec données UTF-8"
        )
        
        # Garder l'ID pour les tests suivants
        if result["passed"] and "conversation_id" in result["response"]:
            self.test_conversation_id = result["response"]["conversation_id"]

    def run_admin_tests(self):
        """Tests des endpoints d'administration"""
        print("\n" + "="*60)
        print("⚙️ TESTS ADMINISTRATION")
        print("="*60)
        
        # Test dashboard admin
        self.test_endpoint(
            "Admin Dashboard",
            "GET", "/v1/admin/dashboard",
            description="Dashboard administrateur principal"
        )
        
        # Test users admin (CORRIGÉ 404)
        self.test_endpoint(
            "Admin Users",
            "GET", "/v1/admin/users",
            description="Gestion utilisateurs (ENDPOINT CORRIGÉ 404)"
        )
        
        # Test RAG diagnostics
        self.test_endpoint(
            "RAG Diagnostics",
            "GET", "/v1/admin/rag/diagnostics",
            description="Diagnostics système RAG"
        )
        
        # Test RAG status
        self.test_endpoint(
            "RAG Status",
            "GET", "/v1/admin/rag/status",
            description="Status détaillé système RAG"
        )

    def run_comprehensive_utf8_validation(self):
        """Tests spécialisés pour la validation UTF-8 corrigée"""
        print("\n" + "="*60)
        print("🔤 TESTS VALIDATION UTF-8 RENFORCÉE")
        print("="*60)
        
        # Test corrections debug
        self.test_endpoint(
            "Debug Corrections v3.5",
            "GET", "/debug/corrections",
            description="Informations sur les corrections appliquées"
        )
        
        # Test UTF-8 debug
        self.test_endpoint(
            "Debug UTF-8 Test",
            "GET", "/debug/utf8-test",
            description="Test des corrections UTF-8 appliquées"
        )
        
        # Cas de test UTF-8 extrêmes
        extreme_utf8_cases = {
            "accents_multiples": "Contrôle qualité effectué à 32°C avec humidité relative de 65%",
            "spanish_complex": "Diagnóstico: nutrición deficiente en proteínas (18% vs 22% requerido)",
            "symbols_heavy": "Coût €15/kg • Température 32°C • Efficacité ≥95% • pH≈6.5",
            "mixed_languages": "Temperature 32°C pour élevage - ¿es normal? Efficacité 95%",
            "unicode_symbols": "🌡️32°C ➡️ 🐔Poulets ✅Normal ❌Problème 📊Stats: 95%"
        }
        
        for test_name, question_text in extreme_utf8_cases.items():
            self.test_endpoint(
                f"UTF-8 Extrême: {test_name}",
                "POST", "/v1/expert/ask-public",
                data={
                    "text": question_text,
                    "language": "fr",
                    "speed_mode": "fast"
                },
                description=f"Test UTF-8 extrême: {question_text[:40]}..."
            )

    def run_genetic_line_neutrality_tests(self):
        """Tests pour vérifier la neutralité des lignées génétiques"""
        print("\n" + "="*60)
        print("🧬 TESTS NEUTRALITÉ LIGNÉES GÉNÉTIQUES")
        print("="*60)
        
        # Questions sans mention de lignée (doit être générique)
        generic_questions = [
            "Quelle est la température optimale pour poulets de chair ?",
            "Problème de croissance chez mes poulets",
            "Mortalité élevée dans mon élevage"
        ]
        
        for question in generic_questions:
            result = self.test_endpoint(
                f"Question Générique: {question[:30]}...",
                "POST", "/v1/expert/ask-public",
                data={
                    "text": question,
                    "language": "fr",
                    "speed_mode": "fast"
                },
                description="Question générique - réponse doit être neutre"
            )
            
            # Vérifier que la réponse ne mentionne pas Ross/Cobb
            if result["passed"] and "response" in result["response"]:
                response_text = result["response"].get("response", "").lower()
                has_ross = "ross" in response_text
                has_cobb = "cobb" in response_text
                if has_ross or has_cobb:
                    self.log(f"⚠️ Réponse générique mentionne lignée spécifique: Ross={has_ross}, Cobb={has_cobb}", "WARNING")
        
        # Questions avec mention explicite (doit garder la mention)
        specific_questions = [
            "Mes poulets Ross 308 ont un problème de croissance",
            "Température optimale pour Cobb 500 ?",
            "Protocole vaccination pour Ross 308"
        ]
        
        for question in specific_questions:
            result = self.test_endpoint(
                f"Question Spécifique: {question[:30]}...",
                "POST", "/v1/expert/ask-public", 
                data={
                    "text": question,
                    "language": "fr",
                    "speed_mode": "fast"
                },
                description="Question spécifique - lignée peut être mentionnée"
            )

    def run_all_tests(self):
        """Exécute tous les tests"""
        print("🚀 DÉMARRAGE DES TESTS COMPLETS BACKEND INTELIA EXPERT")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Backend URL: {self.base_url}")
        
        start_time = time.time()
        
        # Séquence complète de tests
        try:
            self.run_health_tests()
            self.run_auth_tests() 
            self.run_expert_public_tests()
            self.run_expert_debug_tests()
            self.run_logging_tests()
            self.run_admin_tests()
            self.run_comprehensive_utf8_validation()
            self.run_genetic_line_neutrality_tests()
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrompus par l'utilisateur")
            
        except Exception as e:
            print(f"\n💥 Erreur critique pendant les tests: {e}")
        
        total_time = time.time() - start_time
        self.print_final_report(total_time)

    def print_final_report(self, total_time: float):
        """Affiche le rapport final des tests"""
        print("\n" + "="*80)
        print("📊 RAPPORT FINAL DES TESTS")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📈 STATISTIQUES GÉNÉRALES:")
        print(f"   ✅ Tests réussis: {passed_tests}")
        print(f"   ❌ Tests échoués: {failed_tests}")
        print(f"   📊 Total tests: {total_tests}")
        print(f"   🎯 Taux de succès: {success_rate:.1f}%")
        print(f"   ⏱️ Temps total: {total_time:.2f}s")
        
        # Analyse des performances
        response_times = [test["duration_ms"] for test in self.test_results if test["passed"]]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            print(f"   📊 Temps réponse moyen: {avg_response:.1f}ms")
            print(f"   📊 Temps réponse max: {max_response:.1f}ms")
        
        # Tests échoués détaillés
        if failed_tests > 0:
            print(f"\n❌ TESTS ÉCHOUÉS ({failed_tests}):")
            for test in self.test_results:
                if not test["passed"]:
                    print(f"   • {test['name']} ({test['method']} {test['endpoint']}) -> {test['actual_status']}")
                    if "error" in test["response"]:
                        print(f"     Erreur: {test['response']['error']}")
        
        # Analyse spéciale des corrections
        print(f"\n🔧 ANALYSE DES CORRECTIONS v3.5:")
        
        # Tests UTF-8
        utf8_tests = [test for test in self.test_results if "UTF-8" in test["name"] or "utf8" in test["name"].lower()]
        utf8_success = sum(1 for test in utf8_tests if test["passed"])
        print(f"   🔤 Tests UTF-8: {utf8_success}/{len(utf8_tests)} réussis")
        
        # Tests logging (endpoints 404 corrigés)
        logging_tests = [test for test in self.test_results if "logging" in test["endpoint"].lower()]
        logging_success = sum(1 for test in logging_tests if test["passed"])
        print(f"   📊 Tests Logging: {logging_success}/{len(logging_tests)} réussis")
        
        # Tests authentification
        auth_tests = [test for test in self.test_results if "auth" in test["endpoint"].lower() or "Auth" in test["name"]]
        auth_success = sum(1 for test in auth_tests if test["passed"])
        print(f"   🔐 Tests Auth: {auth_success}/{len(auth_tests)} réussis")
        
        # Recommandations
        print(f"\n💡 RECOMMANDATIONS:")
        if success_rate >= 90:
            print("   🎉 Excellent! Le backend est très stable après les corrections.")
        elif success_rate >= 75:
            print("   ✅ Bon! Le backend fonctionne bien avec quelques améliorations mineures.")
        elif success_rate >= 50:
            print("   ⚠️ Attention! Plusieurs problèmes détectés, investigation nécessaire.")
        else:
            print("   🚨 Critique! Le backend nécessite des corrections majeures.")
        
        if failed_tests > 0:
            print("   🔍 Consultez les tests échoués ci-dessus pour les corrections.")
            print("   📋 Vérifiez que le backend est démarré et accessible.")
            print("   🔧 Vérifiez la configuration des variables d'environnement.")
        
        print("\n✅ Tests terminés!")

    def save_report_json(self, filename: str = None):
        """Sauvegarde le rapport en JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backend_test_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "base_url": self.base_url,
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for test in self.test_results if test["passed"]),
            "failed_tests": sum(1 for test in self.test_results if not test["passed"]),
            "success_rate": (sum(1 for test in self.test_results if test["passed"]) / len(self.test_results) * 100) if self.test_results else 0,
            "test_results": self.test_results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"📄 Rapport sauvegardé: {filename}")
        except Exception as e:
            print(f"❌ Erreur sauvegarde rapport: {e}")

def main():
    parser = argparse.ArgumentParser(description="Test complet du backend Intelia Expert")
    parser.add_argument("--base-url", default="http://localhost:8080", 
                       help="URL de base du backend (défaut: http://localhost:8080)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Mode verbose pour plus de détails")
    parser.add_argument("--save-report", action="store_true",
                       help="Sauvegarder le rapport en JSON")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Timeout des requêtes en secondes (défaut: 30)")
    
    args = parser.parse_args()
    
    # Créer et exécuter le testeur
    tester = BackendTester(
        base_url=args.base_url,
        verbose=args.verbose
    )
    
    try:
        tester.run_all_tests()
        
        if args.save_report:
            tester.save_report_json()
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur critique: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()