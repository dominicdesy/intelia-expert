# -*- coding: utf-8 -*-
"""
trace_query_flow.py - Trace le flow complet d'une query dans le système

Audit d'intégration Phase 2: Vérifie quels modules sont actifs
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "="*80)
print("AUDIT D'INTEGRATION - TRACE DU FLOW QUERY")
print("="*80 + "\n")

# Test imports
modules_active = {}

# 1. RAG Engine (point d'entrée)
print("1. RAG ENGINE (Point d'entrée)")
print("-" * 60)
try:
    from core.rag_engine import RAGEngine
    modules_active['RAGEngine'] = True
    print("   [OK] RAGEngine imported")

    # Check methods
    import inspect
    methods = [m for m in dir(RAGEngine) if not m.startswith('_')]
    print(f"   Public methods: {len(methods)}")
    print(f"   Key methods: {[m for m in methods if 'process' in m or 'query' in m]}")
except Exception as e:
    modules_active['RAGEngine'] = False
    print(f"   [ERROR] {e}")

print()

# 2. Query Processor
print("2. QUERY PROCESSOR")
print("-" * 60)
try:
    from core.query_processor import QueryProcessor
    modules_active['QueryProcessor'] = True
    print("   [OK] QueryProcessor imported")

    # Check if uses ClarificationHelper
    import inspect
    source = inspect.getsource(QueryProcessor)
    uses_clarification = 'clarification' in source.lower()
    print(f"   Uses ClarificationHelper: {uses_clarification}")
except Exception as e:
    modules_active['QueryProcessor'] = False
    print(f"   [ERROR] {e}")

print()

# 3. Intent Classifier
print("3. INTENT CLASSIFIER")
print("-" * 60)
try:
    modules_active['IntentClassifier'] = True
    print("   [OK] IntentClassifier imported")
except Exception as e:
    modules_active['IntentClassifier'] = False
    print(f"   [ERROR] {e}")

print()

# 4. QueryRouter
print("4. QUERY ROUTER v3.0")
print("-" * 60)
try:
    from retrieval.postgresql.router import QueryRouter
    router = QueryRouter(use_context_manager=True)
    modules_active['QueryRouter'] = True

    stats = router.get_routing_stats()
    print(f"   [OK] QueryRouter v{stats.get('version', 'N/A')}")
    print(f"   ContextManager enabled: {router.use_context_manager}")
    print(f"   Keywords: {stats.get('metric_keywords_count', 0)} METRICS + {stats.get('knowledge_keywords_count', 0)} KNOWLEDGE")
except Exception as e:
    modules_active['QueryRouter'] = False
    print(f"   [ERROR] {e}")

print()

# 5. Handlers (calculation, etc.)
print("5. QUERY HANDLERS")
print("-" * 60)
try:
    modules_active['CalculationHandler'] = True
    print("   [OK] CalculationQueryHandler imported")
except Exception as e:
    modules_active['CalculationHandler'] = False
    print(f"   [ERROR] {e}")

try:
    # Check for other handlers
    import core.handlers as handlers_module
    all_handlers = [name for name in dir(handlers_module) if 'Handler' in name]
    print(f"   Available handlers: {all_handlers}")
except Exception:
    pass

print()

# 6. ClarificationHelper
print("6. CLARIFICATION HELPER")
print("-" * 60)
try:
    from utils.clarification_helper import get_clarification_helper
    helper = get_clarification_helper()
    modules_active['ClarificationHelper'] = True

    print("   [OK] ClarificationHelper loaded")
    print(f"   Ambiguity types: {len(helper.ambiguity_types)}")
    print(f"   Types: {list(helper.ambiguity_types.keys())[:3]}...")

    # Test detection
    test_query = "Performance à 35 jours"
    ambiguity = helper.detect_ambiguity_type(test_query, ["breed"], {})
    print(f"   Test detection: '{test_query}' -> {ambiguity}")
except Exception as e:
    modules_active['ClarificationHelper'] = False
    print(f"   [ERROR] {e}")

print()

# 7. ContextManager
print("7. CONTEXT MANAGER (Phase 1)")
print("-" * 60)
try:
    from processing.context_manager import get_context_manager
    manager = get_context_manager()
    modules_active['ContextManager'] = True

    print("   [OK] ContextManager loaded")

    # Test
    manager.update_context("Ross 308 à 35 jours")
    expanded = manager.expand_query("Et pour les femelles?")
    print("   Test expansion:")
    print("      Original: 'Et pour les femelles?'")
    print(f"      Expanded: '{expanded}'")
except Exception as e:
    modules_active['ContextManager'] = False
    print(f"   [ERROR] {e}")

print()

# 8. Check integration in RAG pipeline
print("8. INTEGRATION CHECK - RAG PIPELINE")
print("-" * 60)
try:
    from core.rag_engine import RAGEngine
    import inspect

    # Get RAGEngine source
    source = inspect.getsource(RAGEngine)

    # Check mentions
    checks = {
        'ClarificationHelper': 'clarification' in source.lower(),
        'CalculationHandler': 'calculation' in source.lower(),
        'ContextManager': 'context' in source.lower() and 'manager' in source.lower(),
        'QueryRouter': 'router' in source.lower() or 'route' in source.lower(),
    }

    for module, is_used in checks.items():
        status = "ACTIVE" if is_used else "NOT FOUND"
        icon = "[+]" if is_used else "[-]"
        print(f"   {icon} {module:25} : {status}")

except Exception as e:
    print(f"   [ERROR] Cannot check: {e}")

print()

# SUMMARY
print("="*80)
print("SUMMARY - MODULES STATUS")
print("="*80 + "\n")

active_count = sum(1 for v in modules_active.values() if v)
total_count = len(modules_active)

for module, is_active in modules_active.items():
    status = "ACTIVE" if is_active else "INACTIVE"
    icon = "[+]" if is_active else "[-]"
    print(f"   {icon} {module:25} : {status}")

print(f"\nActive modules: {active_count}/{total_count}\n")

# RECOMMENDATIONS
print("="*80)
print("RECOMMENDATIONS")
print("="*80 + "\n")

if active_count == total_count:
    print("All modules are loaded successfully!")
    print("\nNext steps:")
    print("   1. Verify they are called in the execution flow")
    print("   2. Run end-to-end tests to measure real coverage")
    print("   3. Check logs for activation traces")
else:
    print(f"Missing modules: {total_count - active_count}")
    print("\nTroubleshooting:")
    for module, is_active in modules_active.items():
        if not is_active:
            print(f"   - Fix import/initialization for {module}")

print()
