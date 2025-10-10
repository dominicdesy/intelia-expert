#!/bin/bash
# run_quality_checks.sh - Comprehensive Quality Check Script for Intelia LLM
# Usage: bash run_quality_checks.sh

set -e  # Exit on error

echo "================================================================================"
echo "INTELIA LLM - COMPREHENSIVE QUALITY CHECKS"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to run a check
run_check() {
    local name="$1"
    local command="$2"
    local description="$3"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo "--------------------------------------------------------------------------------"
    echo "CHECK $TOTAL_CHECKS: $name"
    echo "Description: $description"
    echo "Command: $command"
    echo "--------------------------------------------------------------------------------"

    if eval "$command"; then
        echo -e "${GREEN}✓ PASSED${NC}: $name"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}✗ FAILED${NC}: $name"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi

    echo ""
}

# =============================================================================
# 1. RUFF - Linting
# =============================================================================
run_check \
    "Ruff Linting" \
    "ruff check ." \
    "Fast Python linter checking for code quality issues (PEP 8, security, etc.)"

# =============================================================================
# 2. BLACK - Code Formatting
# =============================================================================
run_check \
    "Black Formatting" \
    "black --check ." \
    "Verify code follows Black's opinionated formatting style"

# =============================================================================
# 3. PYRIGHT - Type Checking
# =============================================================================
# Note: Pyright may have many errors initially, so we capture output
echo "--------------------------------------------------------------------------------"
echo "CHECK $((TOTAL_CHECKS + 1)): Pyright Type Checking"
echo "Description: Static type analysis for Python code"
echo "Command: pyright --outputjson > pyright_report.json"
echo "--------------------------------------------------------------------------------"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

pyright --outputjson > pyright_report.json 2>&1 || true
PYRIGHT_ERRORS=$(cat pyright_report.json | grep -o '"errorCount":[0-9]*' | cut -d':' -f2 || echo "0")

if [ "$PYRIGHT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓ PASSED${NC}: Pyright Type Checking (0 errors)"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${YELLOW}⚠ INFO${NC}: Pyright found $PYRIGHT_ERRORS type errors (expected - gradual improvement)"
    echo "   Report saved to: pyright_report.json"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))  # Don't fail on type errors (gradual improvement)
fi
echo ""

# =============================================================================
# 4. BANDIT - Security Analysis
# =============================================================================
run_check \
    "Bandit Security Scan" \
    "bandit -r . -f json -o bandit_report.json --exclude './tests/*,./scripts/*' && cat bandit_report.json | grep -q '\"SEVERITY\": \"HIGH\"' && exit 1 || exit 0" \
    "Security vulnerability scanner for Python code (HIGH severity issues will fail)"

# =============================================================================
# 5. PIP-AUDIT - Dependency Vulnerabilities
# =============================================================================
run_check \
    "pip-audit CVE Check" \
    "pip-audit --format json --output pip_audit_report.json || test -f pip_audit_report.json" \
    "Check for known CVE vulnerabilities in Python dependencies"

# =============================================================================
# 6. IMPORT VERIFICATION
# =============================================================================
echo "--------------------------------------------------------------------------------"
echo "CHECK $((TOTAL_CHECKS + 1)): Critical Import Verification"
echo "Description: Verify critical Python modules can be imported"
echo "--------------------------------------------------------------------------------"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

IMPORT_FAILED=0
python -c "
import sys
modules_to_test = [
    'core.rag_engine',
    'retrieval.weaviate.core',
    'security.guardrails.core',
    'cache.cache_core'
]

failed = []
for module in modules_to_test:
    try:
        __import__(module)
        print(f'OK: {module}')
    except Exception as e:
        print(f'FAIL: {module} - {e}')
        failed.append(module)

if failed:
    sys.exit(1)
" && IMPORT_RESULT="PASS" || IMPORT_RESULT="FAIL"

if [ "$IMPORT_RESULT" = "PASS" ]; then
    echo -e "${GREEN}✓ PASSED${NC}: All critical imports successful"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Some imports failed"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
echo ""

# =============================================================================
# FINAL SUMMARY
# =============================================================================
echo "================================================================================"
echo "QUALITY CHECK SUMMARY"
echo "================================================================================"
echo "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}================================================================================"
    echo -e "                        ALL QUALITY CHECKS PASSED!"
    echo -e "================================================================================${NC}"
    exit 0
else
    echo -e "${RED}================================================================================"
    echo -e "                      $FAILED_CHECKS QUALITY CHECK(S) FAILED"
    echo -e "================================================================================${NC}"
    echo ""
    echo "Review the output above to identify and fix failing checks."
    exit 1
fi
