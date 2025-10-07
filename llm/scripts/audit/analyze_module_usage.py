#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse complète de l'utilisation des modules avancés du système
"""

import re
from pathlib import Path

# Modules avancés à vérifier
ADVANCED_MODULES = {
    "LLM Ensemble": {
        "file": "generation/llm_ensemble.py",
        "class": "LLMEnsemble",
        "description": "Multi-LLM consensus system (Claude, OpenAI, DeepSeek)"
    },
    "ProactiveAssistant": {
        "file": "generation/proactive_assistant.py",
        "class": "ProactiveAssistant",
        "description": "Follow-up questions generator"
    },
    "ConversationMemory": {
        "file": "conversation/conversation_memory.py",
        "class": "ConversationMemory",
        "description": "Conversation context management"
    },
    "PostgreSQLValidator": {
        "file": "preprocessing/postgresql_validator.py",
        "class": "PostgreSQLValidator",
        "description": "Entity validation for PostgreSQL queries"
    },
    "BreedContextEnricher": {
        "file": "preprocessing/breed_context_enricher.py",
        "class": "BreedContextEnricher",
        "description": "Breed context enrichment"
    },
    "GuardrailsOrchestrator": {
        "file": "security/guardrails/core.py",
        "class": "GuardrailsOrchestrator",
        "description": "Security guardrails orchestrator"
    },
    "QueryRouter": {
        "file": "routing/query_router.py",
        "class": "QueryRouter",
        "description": "Intelligent query routing"
    },
    "RAGQueryProcessor": {
        "file": "core/processors/query_processor.py",
        "class": "RAGQueryProcessor",
        "description": "Query processing orchestrator"
    },
    "WeaviateCore": {
        "file": "databases/weaviate_core.py",
        "class": "WeaviateCore",
        "description": "Weaviate vector database with RRF fusion"
    },
    "IntelligentRRFFusion": {
        "file": "retrieval/intelligent_rrf_fusion.py",
        "class": "IntelligentRRFFusion",
        "description": "Intelligent RRF fusion for multi-query search"
    },
}

def find_imports(module_name, class_name):
    """Find all imports of a module/class in the codebase"""
    llm_dir = Path(__file__).parent
    imports = []

    for py_file in llm_dir.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue

        try:
            content = py_file.read_text(encoding='utf-8')

            # Check for imports
            patterns = [
                f"from.*{module_name.replace('/', '.')}.*import.*{class_name}",
                f"import.*{module_name.replace('/', '.')}",
                f"from.*import.*{class_name}",
            ]

            for pattern in patterns:
                if re.search(pattern, content):
                    imports.append(str(py_file.relative_to(llm_dir)))
                    break
        except Exception:
            pass

    return imports

def find_instantiations(class_name):
    """Find all instantiations of a class in the codebase"""
    llm_dir = Path(__file__).parent
    instantiations = []

    for py_file in llm_dir.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue

        try:
            content = py_file.read_text(encoding='utf-8')

            # Check for class instantiation
            patterns = [
                f"{class_name}\s*\(",
                f"=\s*{class_name}\s*\(",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Get line numbers
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            instantiations.append({
                                "file": str(py_file.relative_to(llm_dir)),
                                "line": i,
                                "code": line.strip()
                            })
        except Exception:
            pass

    return instantiations

def find_method_calls(class_name):
    """Find method calls on a class instance"""
    llm_dir = Path(__file__).parent
    calls = []

    for py_file in llm_dir.rglob("*.py"):
        if py_file.name == "__pycache__":
            continue

        try:
            content = py_file.read_text(encoding='utf-8')

            # Look for self.xxx or instance.xxx where xxx is the class instance
            # This is approximate but gives us an idea
            instance_names = [
                class_name.lower().replace("orchestrator", "").replace("assistant", "").replace("enricher", ""),
                class_name.lower(),
                f"{class_name.lower()}_instance",
            ]

            for instance in instance_names:
                pattern = f"{instance}\\.\\w+\("
                if re.search(pattern, content, re.IGNORECASE):
                    calls.append(str(py_file.relative_to(llm_dir)))
                    break
        except Exception:
            pass

    return calls

def main():
    print("=" * 100)
    print("ANALYSE DE L'UTILISATION DES MODULES AVANCÉS")
    print("=" * 100)
    print()

    results = {}

    for module_name, module_info in ADVANCED_MODULES.items():
        print(f"\n{'='*100}")
        print(f"MODULE: {module_name}")
        print(f"Description: {module_info['description']}")
        print(f"Fichier: {module_info['file']}")
        print(f"Classe: {module_info['class']}")
        print(f"{'='*100}")

        # Find imports
        imports = find_imports(module_info['file'].replace('.py', ''), module_info['class'])
        print(f"\n[IMPORTS] trouves: {len(imports)}")
        for imp in imports:
            print(f"   - {imp}")

        # Find instantiations
        instantiations = find_instantiations(module_info['class'])
        print(f"\n[INSTANTIATIONS] trouvees: {len(instantiations)}")
        for inst in instantiations:
            print(f"   - {inst['file']}:{inst['line']} -> {inst['code'][:80]}")

        # Find method calls
        calls = find_method_calls(module_info['class'])
        print(f"\n[APPELS] FICHIERS avec appels de methodes: {len(calls)}")
        for call in calls:
            print(f"   - {call}")

        # Verdict
        is_used = len(imports) > 0 or len(instantiations) > 0 or len(calls) > 0
        status = "[OK] UTILISE" if is_used else "[NON] NON UTILISE"

        if not is_used:
            status = "[WARN] POTENTIELLEMENT NON UTILISE"
        elif len(instantiations) == 0:
            status = "[WARN] IMPORTE MAIS PEUT-ETRE PAS INSTANCIE"

        print(f"\n{status}")

        results[module_name] = {
            "imports": len(imports),
            "instantiations": len(instantiations),
            "calls": len(calls),
            "status": status
        }

    # Summary
    print("\n" + "=" * 100)
    print("RÉSUMÉ")
    print("=" * 100)

    for module_name, stats in results.items():
        print(f"\n{stats['status']} {module_name}")
        print(f"   Imports: {stats['imports']} | Instantiations: {stats['instantiations']} | Appels: {stats['calls']}")

    # Count by status
    print("\n" + "=" * 100)
    print("STATISTIQUES")
    print("=" * 100)

    used = sum(1 for s in results.values() if "[OK]" in s['status'])
    maybe = sum(1 for s in results.values() if "[WARN]" in s['status'])
    unused = sum(1 for s in results.values() if "[NON]" in s['status'])

    print(f"\n[OK] Modules utilises: {used}/{len(ADVANCED_MODULES)}")
    print(f"[WARN] Modules a verifier: {maybe}/{len(ADVANCED_MODULES)}")
    print(f"[NON] Modules non utilises: {unused}/{len(ADVANCED_MODULES)}")

    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
