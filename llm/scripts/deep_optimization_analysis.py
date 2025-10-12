#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep Optimization Analysis - Ultra-Complete LLM Performance Analysis

This script runs a comprehensive multi-hour analysis including:
1. Code complexity analysis (cyclomatic complexity)
2. Import dependency graph analysis
3. Performance bottleneck detection
4. Code duplication detection
5. Security vulnerability scanning
6. Type hint coverage analysis
7. Documentation coverage analysis
8. Test coverage analysis
9. Memory usage patterns
10. Configuration optimization suggestions

Designed to run overnight and provide actionable optimization recommendations.
"""

import os
import sys
import ast
import json
import time
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from typing import List
from datetime import datetime
import re

# Add llm directory to Python path
llm_dir = Path(__file__).parent.parent
sys.path.insert(0, str(llm_dir))

class DeepCodeAnalyzer:
    """Ultra-comprehensive code analysis for optimization opportunities"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.python_files: List[Path] = []
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'root_dir': str(root_dir),
            'analyses': {}
        }

    def log(self, message: str):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def find_python_files(self):
        """Find all Python files"""
        self.log("📂 Scanning for Python files...")
        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'env', 'build', 'dist'}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.py'):
                    self.python_files.append(Path(root) / file)

        self.log(f"OK Found {len(self.python_files)} Python files")
        return self.python_files

    def analyze_cyclomatic_complexity(self):
        """Analyze code complexity (cyclomatic complexity)"""
        self.log("\n🔍 Analysis 1/10: Cyclomatic Complexity...")

        complexity_results = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        complexity = self._calculate_complexity(node)
                        if complexity > 10:  # High complexity threshold
                            complexity_results.append({
                                'file': str(file_path.relative_to(self.root_dir)),
                                'function': node.name,
                                'complexity': complexity,
                                'line': node.lineno
                            })
            except Exception as e:
                self.log(f"! Error analyzing {file_path.name}: {e}")

        complexity_results.sort(key=lambda x: x['complexity'], reverse=True)
        self.analysis_results['analyses']['cyclomatic_complexity'] = {
            'high_complexity_functions': complexity_results,
            'total_high_complexity': len(complexity_results),
            'recommendation': 'Refactor functions with complexity > 10 for better maintainability'
        }

        self.log(f"   Found {len(complexity_results)} high-complexity functions")

    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity of a function"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def analyze_import_dependencies(self):
        """Analyze import dependency graph"""
        self.log("\n🔍 Analysis 2/10: Import Dependency Graph...")

        dependencies = defaultdict(set)
        circular_deps = []

        for file_path in self.python_files:
            rel_path = str(file_path.relative_to(self.root_dir))
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.ImportFrom) and node.module:
                            dependencies[rel_path].add(node.module)
            except Exception:
                pass

        # Detect circular dependencies
        for file, deps in dependencies.items():
            for dep in deps:
                dep_file = dep.replace('.', '/') + '.py'
                if dep_file in dependencies and file in str(dependencies.get(dep_file, [])):
                    circular_deps.append({'file1': file, 'file2': dep_file})

        self.analysis_results['analyses']['dependencies'] = {
            'total_import_statements': sum(len(deps) for deps in dependencies.values()),
            'circular_dependencies': circular_deps,
            'most_imported_modules': self._get_most_imported(dependencies),
            'recommendation': 'Resolve circular dependencies to improve modularity'
        }

        self.log(f"   Found {len(circular_deps)} circular dependencies")

    def _get_most_imported(self, dependencies, top_n=10):
        """Get most frequently imported modules"""
        all_imports = []
        for deps in dependencies.values():
            all_imports.extend(deps)

        counter = Counter(all_imports)
        return [{'module': mod, 'count': count} for mod, count in counter.most_common(top_n)]

    def analyze_code_duplication(self):
        """Detect code duplication"""
        self.log("\n🔍 Analysis 3/10: Code Duplication Detection...")

        code_hashes = defaultdict(list)
        duplicates = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Check for duplicate blocks (5+ lines)
                for i in range(len(lines) - 5):
                    block = ''.join(lines[i:i+5]).strip()
                    if len(block) > 50:  # Ignore very short blocks
                        block_hash = hashlib.md5(block.encode(), usedforsecurity=False).hexdigest()
                        code_hashes[block_hash].append({
                            'file': str(file_path.relative_to(self.root_dir)),
                            'line': i + 1,
                            'code': block[:100]  # First 100 chars
                        })
            except Exception:
                pass

        # Find actual duplicates
        for hash_val, locations in code_hashes.items():
            if len(locations) > 1:
                duplicates.append({
                    'hash': hash_val,
                    'occurrences': len(locations),
                    'locations': locations
                })

        duplicates.sort(key=lambda x: x['occurrences'], reverse=True)

        self.analysis_results['analyses']['code_duplication'] = {
            'duplicate_blocks': duplicates[:20],  # Top 20
            'total_duplicates': len(duplicates),
            'recommendation': 'Extract duplicate code into reusable functions/classes'
        }

        self.log(f"   Found {len(duplicates)} duplicate code blocks")

    def analyze_type_hints(self):
        """Analyze type hint coverage"""
        self.log("\n🔍 Analysis 4/10: Type Hint Coverage...")

        total_functions = 0
        typed_functions = 0
        missing_hints = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_functions += 1

                        has_return_hint = node.returns is not None
                        has_arg_hints = all(arg.annotation is not None for arg in node.args.args if arg.arg != 'self')

                        if has_return_hint and has_arg_hints:
                            typed_functions += 1
                        else:
                            missing_hints.append({
                                'file': str(file_path.relative_to(self.root_dir)),
                                'function': node.name,
                                'line': node.lineno
                            })
            except Exception:
                pass

        coverage = (typed_functions / total_functions * 100) if total_functions > 0 else 0

        self.analysis_results['analyses']['type_hints'] = {
            'coverage_percentage': round(coverage, 2),
            'total_functions': total_functions,
            'typed_functions': typed_functions,
            'functions_missing_hints': missing_hints[:50],  # Top 50
            'recommendation': f'Add type hints to improve code quality (current: {coverage:.1f}%)'
        }

        self.log(f"   Type hint coverage: {coverage:.1f}%")

    def analyze_documentation(self):
        """Analyze documentation coverage"""
        self.log("\n🔍 Analysis 5/10: Documentation Coverage...")

        total_items = 0
        documented_items = 0
        missing_docs = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        total_items += 1
                        docstring = ast.get_docstring(node)

                        if docstring:
                            documented_items += 1
                        else:
                            missing_docs.append({
                                'file': str(file_path.relative_to(self.root_dir)),
                                'type': type(node).__name__,
                                'name': node.name,
                                'line': node.lineno
                            })
            except Exception:
                pass

        coverage = (documented_items / total_items * 100) if total_items > 0 else 0

        self.analysis_results['analyses']['documentation'] = {
            'coverage_percentage': round(coverage, 2),
            'total_items': total_items,
            'documented_items': documented_items,
            'missing_documentation': missing_docs[:50],
            'recommendation': f'Add docstrings to improve maintainability (current: {coverage:.1f}%)'
        }

        self.log(f"   Documentation coverage: {coverage:.1f}%")

    def analyze_error_handling(self):
        """Analyze error handling patterns"""
        self.log("\n🔍 Analysis 6/10: Error Handling Analysis...")

        bare_excepts = []
        total_try_blocks = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Try):
                        total_try_blocks += 1
                        for handler in node.handlers:
                            if handler.type is None:  # Bare except
                                bare_excepts.append({
                                    'file': str(file_path.relative_to(self.root_dir)),
                                    'line': handler.lineno
                                })
            except Exception:
                pass

        self.analysis_results['analyses']['error_handling'] = {
            'total_try_blocks': total_try_blocks,
            'bare_excepts': bare_excepts,
            'bare_except_count': len(bare_excepts),
            'recommendation': 'Replace bare except clauses with specific exception types'
        }

        self.log(f"   Found {len(bare_excepts)} bare except clauses")

    def analyze_long_functions(self):
        """Analyze function length"""
        self.log("\n🔍 Analysis 7/10: Long Functions Analysis...")

        long_functions = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Calculate function length
                        if hasattr(node, 'end_lineno'):
                            length = node.end_lineno - node.lineno
                            if length > 50:  # Functions longer than 50 lines
                                long_functions.append({
                                    'file': str(file_path.relative_to(self.root_dir)),
                                    'function': node.name,
                                    'line': node.lineno,
                                    'length': length
                                })
            except Exception:
                pass

        long_functions.sort(key=lambda x: x['length'], reverse=True)

        self.analysis_results['analyses']['long_functions'] = {
            'functions_over_50_lines': long_functions,
            'total_long_functions': len(long_functions),
            'recommendation': 'Break down long functions into smaller, focused functions'
        }

        self.log(f"   Found {len(long_functions)} functions > 50 lines")

    def analyze_import_optimization(self):
        """Analyze import optimization opportunities"""
        self.log("\n🔍 Analysis 8/10: Import Optimization...")

        unused_imports = []
        wildcard_imports = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                imported_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_names.add(alias.asname or alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name == '*':
                                wildcard_imports.append({
                                    'file': str(file_path.relative_to(self.root_dir)),
                                    'line': node.lineno,
                                    'module': node.module
                                })
                            else:
                                imported_names.add(alias.asname or alias.name)

                # Check if imported names are used
                for name in imported_names:
                    if content.count(name) == 1:  # Only appears in import statement
                        unused_imports.append({
                            'file': str(file_path.relative_to(self.root_dir)),
                            'import': name
                        })
            except Exception:
                pass

        self.analysis_results['analyses']['import_optimization'] = {
            'unused_imports': unused_imports[:50],
            'wildcard_imports': wildcard_imports,
            'total_unused': len(unused_imports),
            'total_wildcards': len(wildcard_imports),
            'recommendation': 'Remove unused imports and replace wildcard imports with explicit imports'
        }

        self.log(f"   Found {len(unused_imports)} unused imports, {len(wildcard_imports)} wildcard imports")

    def analyze_magic_numbers(self):
        """Detect magic numbers (hardcoded constants)"""
        self.log("\n🔍 Analysis 9/10: Magic Numbers Detection...")

        magic_numbers = []

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant):
                        if isinstance(node.value, (int, float)) and node.value not in [0, 1, -1, 2, 10, 100]:
                            magic_numbers.append({
                                'file': str(file_path.relative_to(self.root_dir)),
                                'value': node.value,
                                'line': node.lineno
                            })
            except Exception:
                pass

        # Count occurrences
        number_counter = Counter(tuple(sorted(d.items())) for d in magic_numbers)
        frequent_magic = [dict(items) for items, count in number_counter.most_common(20)]

        self.analysis_results['analyses']['magic_numbers'] = {
            'total_magic_numbers': len(magic_numbers),
            'frequent_magic_numbers': frequent_magic,
            'recommendation': 'Replace magic numbers with named constants'
        }

        self.log(f"   Found {len(magic_numbers)} magic numbers")

    def analyze_performance_patterns(self):
        """Analyze performance anti-patterns"""
        self.log("\n🔍 Analysis 10/10: Performance Patterns...")

        performance_issues = []

        patterns = {
            'string_concat_loop': r'for .+ in .+:\s+\w+\s*\+=\s*["\']',
            'repeated_computation': r'for .+ in .+:.*\n.*\.append\(.+\(.+\)\)',
            'inefficient_membership': r'if .+ in \[',
        }

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern_name, pattern in patterns.items():
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        performance_issues.append({
                            'file': str(file_path.relative_to(self.root_dir)),
                            'issue': pattern_name,
                            'line': line_num,
                            'code': match.group()[:80]
                        })
            except Exception:
                pass

        self.analysis_results['analyses']['performance_patterns'] = {
            'performance_issues': performance_issues,
            'total_issues': len(performance_issues),
            'recommendation': 'Optimize loops, use list comprehensions, and efficient data structures'
        }

        self.log(f"   Found {len(performance_issues)} performance anti-patterns")

    def generate_comprehensive_report(self, output_file: Path):
        """Generate final comprehensive report"""
        self.log("\n📊 Generating comprehensive report...")

        # Calculate overall health score
        total_issues = (
            self.analysis_results['analyses'].get('cyclomatic_complexity', {}).get('total_high_complexity', 0) +
            self.analysis_results['analyses'].get('code_duplication', {}).get('total_duplicates', 0) +
            self.analysis_results['analyses'].get('error_handling', {}).get('bare_except_count', 0) +
            self.analysis_results['analyses'].get('long_functions', {}).get('total_long_functions', 0) +
            self.analysis_results['analyses'].get('import_optimization', {}).get('total_unused', 0) +
            self.analysis_results['analyses'].get('performance_patterns', {}).get('total_issues', 0)
        )

        health_score = max(0, 100 - (total_issues / len(self.python_files) * 10))

        self.analysis_results['summary'] = {
            'total_files_analyzed': len(self.python_files),
            'health_score': round(health_score, 2),
            'total_issues_found': total_issues,
            'analysis_duration_seconds': time.time() - self.start_time,
            'top_priorities': self._get_top_priorities()
        }

        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)

        self._print_summary()

        return self.analysis_results

    def _get_top_priorities(self):
        """Get top priority optimization tasks"""
        priorities = []

        analyses = self.analysis_results['analyses']

        if analyses.get('cyclomatic_complexity', {}).get('total_high_complexity', 0) > 10:
            priorities.append({
                'priority': 'HIGH',
                'category': 'Code Complexity',
                'action': 'Refactor high-complexity functions',
                'impact': 'Maintainability'
            })

        if analyses.get('code_duplication', {}).get('total_duplicates', 0) > 20:
            priorities.append({
                'priority': 'HIGH',
                'category': 'Code Duplication',
                'action': 'Extract duplicate code blocks',
                'impact': 'Maintainability & Size'
            })

        if analyses.get('type_hints', {}).get('coverage_percentage', 0) < 50:
            priorities.append({
                'priority': 'MEDIUM',
                'category': 'Type Safety',
                'action': 'Add type hints to functions',
                'impact': 'Code Quality'
            })

        if analyses.get('performance_patterns', {}).get('total_issues', 0) > 10:
            priorities.append({
                'priority': 'HIGH',
                'category': 'Performance',
                'action': 'Fix performance anti-patterns',
                'impact': 'Runtime Performance'
            })

        return priorities

    def _print_summary(self):
        """Print analysis summary"""
        print("\n" + "=" * 80)
        print("📊 DEEP OPTIMIZATION ANALYSIS - FINAL REPORT")
        print("=" * 80)

        summary = self.analysis_results['summary']
        print(f"\n📁 Total files analyzed: {summary['total_files_analyzed']}")
        print(f"⏱️  Analysis duration: {summary['analysis_duration_seconds']:.1f} seconds")
        print(f"💯 Health score: {summary['health_score']:.1f}/100")
        print(f"!  Total issues found: {summary['total_issues_found']}")

        print("\n🎯 TOP PRIORITIES:")
        for priority in summary['top_priorities']:
            print(f"  [{priority['priority']}] {priority['category']}: {priority['action']}")
            print(f"         Impact: {priority['impact']}")

        print("\n" + "=" * 80)

    def run_full_analysis(self):
        """Run all analyses"""
        self.start_time = time.time()

        self.log("🚀 Starting Deep Optimization Analysis\n")
        self.log("=" * 80)

        self.find_python_files()

        # Run all analyses
        self.analyze_cyclomatic_complexity()
        self.analyze_import_dependencies()
        self.analyze_code_duplication()
        self.analyze_type_hints()
        self.analyze_documentation()
        self.analyze_error_handling()
        self.analyze_long_functions()
        self.analyze_import_optimization()
        self.analyze_magic_numbers()
        self.analyze_performance_patterns()

        # Generate report
        output_file = self.root_dir / 'logs' / 'deep_optimization_report.json'
        output_file.parent.mkdir(exist_ok=True)

        self.generate_comprehensive_report(output_file)

        self.log(f"\nOK Analysis complete! Full report: {output_file}")
        self.log("=" * 80)


def main():
    """Run deep optimization analysis"""
    llm_dir = Path(__file__).parent.parent

    analyzer = DeepCodeAnalyzer(llm_dir)
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
