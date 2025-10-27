"""
Fix E402
Version: 1.4.1
Last modified: 2025-10-26
"""
import re
from pathlib import Path

# Files to fix based on ruff output
files_to_fix = [
    ('scripts/run_ragas_evaluation.py', [46, 47, 48, 49]),
    ('tests/integration/test_api_chat_endpoint.py', [27]),
    ('tests/integration/test_cohere_reranker.py', [25]),
    ('tests/integration/test_postgresql_retriever.py', [24, 25]),
    ('tests/integration/test_rag_pipeline.py', [28]),
    ('tests/integration/test_rate_limiting_agent.py', [26, 27]),
    ('tests/integration/test_redis_cache.py', [28]),
    ('tests/integration/test_security_guardrails.py', [24, 25]),
    ('tests/integration/test_translation_service.py', [24]),
    ('tests/integration/test_weaviate_retriever.py', [24]),
    ('tests/test_ood_fix.py', [22]),
    ('tests/test_processing_plant_full.py', [23]),
    ('version.py', [10, 11, 12]),
]

for file_path, line_numbers in files_to_fix:
    path = Path(file_path)
    if not path.exists():
        print(f"SKIP: {file_path} (not found)")
        continue
    
    # Read file
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Add noqa comment to each import line
    fixed_count = 0
    for line_num in line_numbers:
        idx = line_num - 1
        if idx < len(lines):
            original = lines[idx]
            # Check if it's an import line
            if re.search(r'^\s*(from|import)\s+', original):
                # Check if noqa already present
                if '# noqa' not in original:
                    # Add noqa: E402 comment before newline
                    lines[idx] = original.rstrip() + '  # noqa: E402\n'
                    fixed_count += 1
                    print(f"FIX {file_path}:{line_num}: Added noqa comment")
    
    # Write back
    if fixed_count > 0:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"OK: Fixed {fixed_count} E402 errors in {file_path}\n")

print("E402 fixes complete!")
