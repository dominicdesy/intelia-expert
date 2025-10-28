# -*- coding: utf-8 -*-
"""
run_all_tests.py - Exécute tous les tests d'intégration et génère un rapport

Usage:
    python tests/run_all_tests.py
    python tests/run_all_tests.py --fast  # Tests rapides seulement
    python tests/run_all_tests.py --critical  # Tests critiques seulement
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime


class TestRunner:
    """Runner pour tous les tests d'intégration"""

    def __init__(self, fast_mode=False, critical_only=False):
        self.fast_mode = fast_mode
        self.critical_only = critical_only
        self.results = {}

    def run_test_file(self, test_file, description):
        """Exécute un fichier de test"""

        print(f"\n{'=' * 80}")
        print(f"Running: {description}")
        print(f"File: {test_file}")
        print(f"{'=' * 80}")

        start = time.time()

        try:
            result = subprocess.run(
                ["pytest", test_file, "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes max
            )

            duration = time.time() - start

            # Parse output
            passed = result.stdout.count(" PASSED")
            failed = result.stdout.count(" FAILED")
            errors = result.stdout.count(" ERROR")

            success = result.returncode == 0

            self.results[description] = {
                "success": success,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "duration": duration,
                "returncode": result.returncode,
            }

            # Print summary
            if success:
                print(f"\n[OK] SUCCESS: {passed} tests passed in {duration:.2f}s")
            else:
                print(
                    f"\n[FAILED] FAILED: {passed} passed, {failed} failed, {errors} errors"
                )
                print("\nError output:")
                print(result.stdout[-500:])  # Last 500 chars

            return success

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            print(f"\n[TIMEOUT] TIMEOUT after {duration:.2f}s")

            self.results[description] = {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "duration": duration,
                "returncode": -1,
            }

            return False

        except Exception as e:
            print(f"\n[ERROR] ERROR: {e}")

            self.results[description] = {
                "success": False,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "duration": 0,
                "returncode": -1,
            }

            return False

    def run_all_tests(self):
        """Exécute tous les tests"""

        # Tests critiques (toujours exécutés)
        critical_tests = [
            ("tests/integration/test_api_chat_endpoint.py", "API /chat Endpoint"),
            ("tests/integration/test_rag_pipeline.py", "RAG Pipeline End-to-End"),
        ]

        # Tests importants
        important_tests = [
            (
                "tests/integration/test_postgresql_retriever.py",
                "PostgreSQL Retriever + Normalizer",
            ),
            (
                "tests/integration/test_security_guardrails.py",
                "Security Guardrails + OOD",
            ),
            ("tests/integration/test_redis_cache.py", "Redis Cache Performance"),
        ]

        # Tests supplémentaires
        additional_tests = [
            ("tests/integration/test_weaviate_retriever.py", "Weaviate Retriever"),
            (
                "tests/integration/test_translation_service.py",
                "Translation Service (12 langues)",
            ),
            (
                "tests/integration/test_rate_limiting_agent.py",
                "Rate Limiting + Agent RAG",
            ),
        ]

        # Déterminer quels tests exécuter
        tests_to_run = critical_tests.copy()

        if not self.critical_only:
            tests_to_run.extend(important_tests)

            if not self.fast_mode:
                tests_to_run.extend(additional_tests)

        # Exécuter les tests
        print(f"\n{'*' * 80}")
        print("INTELIA EXPERT LLM - TEST SUITE")
        print(
            f"Mode: {'FAST' if self.fast_mode else 'CRITICAL ONLY' if self.critical_only else 'FULL'}"
        )
        print(f"Total tests: {len(tests_to_run)}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'*' * 80}")

        for test_file, description in tests_to_run:
            test_path = Path(test_file)

            if not test_path.exists():
                print(f"\n⚠️  SKIP: {description} (file not found)")
                continue

            self.run_test_file(test_file, description)

        # Générer rapport final
        self.print_report()

    def print_report(self):
        """Affiche le rapport final"""

        print(f"\n\n{'*' * 80}")
        print("FINAL REPORT")
        print(f"{'*' * 80}\n")

        total_passed = 0
        total_failed = 0
        total_errors = 0
        total_duration = 0
        success_count = 0

        for description, result in self.results.items():
            status = "[PASS]" if result["success"] else "[FAIL]"

            print(f"{status} | {description}")
            print(
                f"       Tests: {result['passed']} passed, {result['failed']} failed, {result['errors']} errors"
            )
            print(f"       Duration: {result['duration']:.2f}s")
            print()

            total_passed += result["passed"]
            total_failed += result["failed"]
            total_errors += result["errors"]
            total_duration += result["duration"]

            if result["success"]:
                success_count += 1

        # Résumé global
        print(f"{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")
        print(f"Test files: {success_count}/{len(self.results)} passed")
        print(
            f"Total tests: {total_passed} passed, {total_failed} failed, {total_errors} errors"
        )
        print(
            f"Total duration: {total_duration:.2f}s ({total_duration/60:.1f} minutes)"
        )
        print()

        # Verdict
        if success_count == len(self.results):
            print("[SUCCESS] ALL TESTS PASSED!")
            return 0
        else:
            print(f"[FAILED] {len(self.results) - success_count} test file(s) failed")
            return 1


def main():
    parser = argparse.ArgumentParser(description="Run Intelia Expert LLM tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument(
        "--critical", action="store_true", help="Run critical tests only"
    )

    args = parser.parse_args()

    runner = TestRunner(fast_mode=args.fast, critical_only=args.critical)

    exit_code = runner.run_all_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
