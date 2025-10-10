from pathlib import Path

fixes = [
    ('core/handlers/standard_handler.py', 483, 'doc_count', 'delete'),
    ('evaluation/auto_add_metadata.py', 79, 'category_line', 'delete'),
    ('evaluation/enrich_metadata.py', 117, 'content', 'prefix_underscore'),
    ('retrieval/semantic_reranker.py', 133, 'cached_pairs', 'delete'),
    ('scripts/deep_optimization_analysis.py', 331, 'lines', 'delete'),
    ('tests/test_enhanced_clarification.py', 421, 'ambiguity', 'prefix_underscore'),
    ('tests/test_query_decomposer.py', 261, 'query_lower', 'delete'),
]

for file_path, line_num, var_name, action in fixes:
    path = Path(file_path)
    if not path.exists():
        print(f"SKIP: {file_path} (not found)")
        continue
    
    # Read file
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    idx = line_num - 1
    if idx < len(lines):
        original = lines[idx]
        
        if action == 'delete':
            # Delete the entire line
            del lines[idx]
            print(f"DELETE {file_path}:{line_num}: {original.strip()}")
        elif action == 'prefix_underscore':
            # Replace variable name with _variable_name
            lines[idx] = original.replace(var_name, f'_{var_name}', 1)
            print(f"RENAME {file_path}:{line_num}: {var_name} -> _{var_name}")
        
        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

print("\nF841 fixes complete!")
