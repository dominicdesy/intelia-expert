#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete LLM Analysis - No Emojis - Windows Compatible
Runs autonomously without user interaction
"""

import os
import sys
import ast
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def log(message):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def find_files(root_dir):
    """Find all Python files"""
    files = []
    exclude = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'env'}

    for root, dirs, filenames in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        for filename in filenames:
            if filename.endswith('.py'):
                files.append(Path(root) / filename)

    return files

def analyze_imports(files, root_dir):
    """Analyze imports and find unused files"""
    imports = defaultdict(set)
    file_imports = defaultdict(set)

    for file_path in files:
        rel_path = str(file_path.relative_to(root_dir))
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[rel_path].add(alias.name)
                        file_imports[alias.name].add(rel_path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports[rel_path].add(node.module)
                        file_imports[node.module].add(rel_path)
        except:
            pass

    return imports, file_imports

def find_unused(files, file_imports, root_dir):
    """Find unused Python files"""
    unused = []

    for file_path in files:
        rel_path = str(file_path.relative_to(root_dir))

        # Skip special files
        if any(skip in rel_path for skip in ['__init__.py', '__main__.py', 'setup.py', 'test_', 'scripts/']):
            continue

        # Check if module is imported
        module_name = rel_path.replace('/', '.').replace('\\', '.').replace('.py', '')

        is_imported = False
        for imported in file_imports.keys():
            if module_name in imported or imported in module_name:
                is_imported = True
                break

        if not is_imported:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if 'if __name__ == "__main__"' not in f.read():
                        unused.append({
                            'file': rel_path,
                            'size': file_path.stat().st_size
                        })
            except:
                pass

    return sorted(unused, key=lambda x: x['size'], reverse=True)

def analyze_complexity(files, root_dir):
    """Find high complexity functions"""
    high_complexity = []

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            complexity += 1

                    if complexity > 10:
                        high_complexity.append({
                            'file': str(file_path.relative_to(root_dir)),
                            'function': node.name,
                            'complexity': complexity,
                            'line': node.lineno
                        })
        except:
            pass

    return sorted(high_complexity, key=lambda x: x['complexity'], reverse=True)

def find_duplicates(files, root_dir):
    """Find duplicate code blocks"""
    code_hashes = defaultdict(list)

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i in range(len(lines) - 5):
                block = ''.join(lines[i:i+5]).strip()
                if len(block) > 50:
                    block_hash = hashlib.md5(block.encode()).hexdigest()
                    code_hashes[block_hash].append({
                        'file': str(file_path.relative_to(root_dir)),
                        'line': i + 1
                    })
        except:
            pass

    duplicates = []
    for hash_val, locations in code_hashes.items():
        if len(locations) > 1:
            duplicates.append({
                'occurrences': len(locations),
                'locations': locations
            })

    return sorted(duplicates, key=lambda x: x['occurrences'], reverse=True)[:20]

def analyze_type_hints(files, root_dir):
    """Analyze type hint coverage"""
    total = 0
    typed = 0

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total += 1
                    if node.returns and all(arg.annotation for arg in node.args.args if arg.arg != 'self'):
                        typed += 1
        except:
            pass

    coverage = (typed / total * 100) if total > 0 else 0
    return {'total': total, 'typed': typed, 'coverage': round(coverage, 2)}

def main():
    """Run complete analysis"""
    log("Starting Complete LLM Analysis")
    log("=" * 60)

    root_dir = Path(__file__).parent.parent
    output_file = root_dir / 'logs' / 'final_analysis_report.json'
    output_file.parent.mkdir(exist_ok=True)

    # Find files
    log("Finding Python files...")
    files = find_files(root_dir)
    log(f"Found {len(files)} Python files")

    # Analyze imports
    log("Analyzing imports...")
    imports, file_imports = analyze_imports(files, root_dir)

    # Find unused files
    log("Finding unused files...")
    unused = find_unused(files, file_imports, root_dir)
    log(f"Found {len(unused)} unused files")

    # Analyze complexity
    log("Analyzing cyclomatic complexity...")
    complexity = analyze_complexity(files, root_dir)
    log(f"Found {len(complexity)} high-complexity functions")

    # Find duplicates
    log("Finding code duplicates...")
    duplicates = find_duplicates(files, root_dir)
    log(f"Found {len(duplicates)} duplicate blocks")

    # Type hints
    log("Analyzing type hints...")
    type_hints = analyze_type_hints(files, root_dir)
    log(f"Type hint coverage: {type_hints['coverage']}%")

    # Build report
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_files': len(files),
            'unused_files': len(unused),
            'high_complexity': len(complexity),
            'duplicates': len(duplicates),
            'type_coverage': type_hints['coverage']
        },
        'details': {
            'unused_files': unused[:20],
            'high_complexity_functions': complexity[:20],
            'code_duplicates': duplicates,
            'type_hints': type_hints
        }
    }

    # Save report
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print summary
    log("=" * 60)
    log("ANALYSIS COMPLETE")
    log("=" * 60)
    log(f"Total files: {report['summary']['total_files']}")
    log(f"Unused files: {report['summary']['unused_files']}")
    log(f"High complexity: {report['summary']['high_complexity']}")
    log(f"Duplicates: {report['summary']['duplicates']}")
    log(f"Type coverage: {report['summary']['type_coverage']}%")
    log("")
    log(f"Report saved to: {output_file}")
    log("=" * 60)

if __name__ == "__main__":
    main()
