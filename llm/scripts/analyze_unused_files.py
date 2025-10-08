#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete LLM Codebase Analysis - Find Unused Files and Optimization Opportunities

This script performs a comprehensive analysis to identify:
1. Unused Python files (imported nowhere)
2. Dead code (functions/classes defined but never called)
3. Unused dependencies
4. Configuration files not referenced
5. Optimization opportunities

Runs autonomously with detailed reporting.
"""

import os
import ast
import sys
import json
import importlib.util
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import re

# Add llm directory to Python path
llm_dir = Path(__file__).parent.parent
sys.path.insert(0, str(llm_dir))

class CodebaseAnalyzer:
    """Comprehensive codebase analyzer for unused files and optimization opportunities"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.python_files: List[Path] = []
        self.imports: Dict[str, Set[str]] = defaultdict(set)  # file -> imported modules
        self.defined_items: Dict[str, Set[str]] = defaultdict(set)  # file -> defined functions/classes
        self.used_items: Dict[str, Set[str]] = defaultdict(set)  # file -> used functions/classes
        self.file_imports: Dict[str, Set[str]] = defaultdict(set)  # module -> files that import it

    def find_python_files(self):
        """Find all Python files in the directory"""
        print(f"Scanning {self.root_dir} for Python files...")

        exclude_dirs = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'env'}

        for root, dirs, files in os.walk(self.root_dir):
            # Remove excluded directories from the search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    self.python_files.append(file_path)

        print(f"OK Found {len(self.python_files)} Python files")
        return self.python_files

    def analyze_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file for imports and definitions"""
        rel_path = str(file_path.relative_to(self.root_dir))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Track imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports[rel_path].add(alias.name)
                        self.file_imports[alias.name].add(rel_path)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        full_import = f"{module}.{alias.name}" if module else alias.name
                        self.imports[rel_path].add(full_import)
                        self.file_imports[module].add(rel_path)

                # Track function definitions
                elif isinstance(node, ast.FunctionDef):
                    self.defined_items[rel_path].add(f"function:{node.name}")

                # Track class definitions
                elif isinstance(node, ast.ClassDef):
                    self.defined_items[rel_path].add(f"class:{node.name}")

                # Track function/class calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        self.used_items[rel_path].add(f"function:{node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name):
                            self.used_items[rel_path].add(f"class:{node.func.value.id}")

            return {
                'imports': list(self.imports[rel_path]),
                'defined': list(self.defined_items[rel_path]),
                'used': list(self.used_items[rel_path])
            }

        except Exception as e:
            print(f"! Error analyzing {rel_path}: {e}")
            return {'imports': [], 'defined': [], 'used': [], 'error': str(e)}

    def find_unused_files(self) -> List[Tuple[Path, str]]:
        """Find Python files that are never imported"""
        print("\n🔍 Analyzing file usage...")

        unused_files = []

        for file_path in self.python_files:
            rel_path = str(file_path.relative_to(self.root_dir))

            # Skip special files that don't need to be imported
            if any(skip in rel_path for skip in ['__init__.py', '__main__.py', 'setup.py', 'test_', 'scripts/']):
                continue

            # Convert file path to module name
            module_name = rel_path.replace('/', '.').replace('\\', '.').replace('.py', '')

            # Check if this module is imported anywhere
            is_imported = False
            for imported_module in self.file_imports.keys():
                if module_name in imported_module or imported_module in module_name:
                    is_imported = True
                    break

            if not is_imported:
                # Check if it's a script (has if __name__ == "__main__")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        is_script = 'if __name__ == "__main__"' in content

                    if not is_script:
                        unused_files.append((file_path, "Never imported, not a script"))
                except:
                    pass

        return unused_files

    def find_dead_code(self) -> List[Tuple[str, str, str]]:
        """Find functions/classes that are defined but never used"""
        print("\n🔍 Analyzing dead code (unused functions/classes)...")

        dead_code = []

        for file_path, defined in self.defined_items.items():
            for item in defined:
                # Check if this item is used in any file
                is_used = False
                item_name = item.split(':')[1]

                for used_file, used_items in self.used_items.items():
                    if item in used_items or any(item_name in u for u in used_items):
                        is_used = True
                        break

                # Also check if it's imported elsewhere
                for imported_file, imports in self.imports.items():
                    if any(item_name in imp for imp in imports):
                        is_used = True
                        break

                # Skip common patterns that are expected to be unused
                skip_patterns = [
                    'main', '__init__', '__str__', '__repr__',
                    'test_', 'get_', 'set_', '__call__',
                    'setUp', 'tearDown'
                ]

                if not is_used and not any(pattern in item_name for pattern in skip_patterns):
                    dead_code.append((file_path, item.split(':')[0], item_name))

        return dead_code

    def analyze_config_files(self) -> List[Tuple[Path, str]]:
        """Find configuration files that might not be used"""
        print("\n🔍 Analyzing configuration files...")

        unused_configs = []
        config_extensions = ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules'}]

            for file in files:
                if any(file.endswith(ext) for ext in config_extensions):
                    file_path = Path(root) / file

                    # Check if this config file is referenced in any Python file
                    is_referenced = False

                    for py_file in self.python_files:
                        try:
                            with open(py_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if file in content:
                                    is_referenced = True
                                    break
                        except:
                            pass

                    if not is_referenced:
                        unused_configs.append((file_path, "Not referenced in any Python file"))

        return unused_configs

    def generate_report(self, output_file: Path):
        """Generate comprehensive analysis report"""
        print("\n📊 Generating comprehensive report...\n")

        # Analyze all files
        for file_path in self.python_files:
            self.analyze_file(file_path)

        # Find issues
        unused_files = self.find_unused_files()
        dead_code = self.find_dead_code()
        unused_configs = self.analyze_config_files()

        # Prepare report
        report = {
            'summary': {
                'total_python_files': len(self.python_files),
                'unused_files': len(unused_files),
                'dead_code_items': len(dead_code),
                'unused_config_files': len(unused_configs),
                'total_imports': sum(len(imports) for imports in self.imports.values()),
                'total_defined_items': sum(len(items) for items in self.defined_items.values()),
            },
            'unused_files': [
                {
                    'file': str(path.relative_to(self.root_dir)),
                    'reason': reason,
                    'size_bytes': path.stat().st_size
                }
                for path, reason in sorted(unused_files, key=lambda x: x[0].stat().st_size, reverse=True)
            ],
            'dead_code': [
                {
                    'file': file,
                    'type': item_type,
                    'name': name
                }
                for file, item_type, name in sorted(dead_code)
            ],
            'unused_config_files': [
                {
                    'file': str(path.relative_to(self.root_dir)),
                    'reason': reason,
                    'size_bytes': path.stat().st_size
                }
                for path, reason in sorted(unused_configs)
            ],
            'recommendations': []
        }

        # Add recommendations
        if unused_files:
            total_size = sum(path.stat().st_size for path, _ in unused_files)
            report['recommendations'].append({
                'category': 'unused_files',
                'priority': 'high',
                'message': f"Remove {len(unused_files)} unused files to save {total_size:,} bytes"
            })

        if dead_code:
            report['recommendations'].append({
                'category': 'dead_code',
                'priority': 'medium',
                'message': f"Remove {len(dead_code)} unused functions/classes to improve maintainability"
            })

        if unused_configs:
            report['recommendations'].append({
                'category': 'unused_configs',
                'priority': 'low',
                'message': f"Review {len(unused_configs)} unreferenced config files"
            })

        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Print summary
        print("=" * 80)
        print("📊 CODEBASE ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"\n📁 Total Python files analyzed: {report['summary']['total_python_files']}")
        print(f"📦 Total imports: {report['summary']['total_imports']}")
        print(f"🔧 Total defined items: {report['summary']['total_defined_items']}")
        print(f"\n! Unused files found: {report['summary']['unused_files']}")
        print(f"💀 Dead code items found: {report['summary']['dead_code_items']}")
        print(f"📋 Unused config files found: {report['summary']['unused_config_files']}")

        if unused_files:
            print(f"\n🗑️ TOP 10 LARGEST UNUSED FILES:")
            for path, reason in unused_files[:10]:
                size_kb = path.stat().st_size / 1024
                print(f"  - {path.relative_to(self.root_dir)} ({size_kb:.1f} KB) - {reason}")

        if dead_code:
            print(f"\n💀 SAMPLE DEAD CODE (first 10):")
            for file, item_type, name in dead_code[:10]:
                print(f"  - {file}: {item_type} '{name}'")

        print(f"\n📄 Full report saved to: {output_file}")
        print("=" * 80)

        return report


def main():
    """Run comprehensive codebase analysis"""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("Starting Complete LLM Codebase Analysis")
    print("=" * 80)

    llm_dir = Path(__file__).parent.parent
    output_file = llm_dir / 'logs' / 'codebase_analysis_report.json'
    output_file.parent.mkdir(exist_ok=True)

    analyzer = CodebaseAnalyzer(llm_dir)
    analyzer.find_python_files()
    report = analyzer.generate_report(output_file)

    print(f"\nOK Analysis complete! Check {output_file} for full details.")

    # Exit with status code based on findings
    if report['summary']['unused_files'] > 0 or report['summary']['dead_code_items'] > 10:
        print("\n! Optimization opportunities found - review the report!")
        sys.exit(1)
    else:
        print("\n Codebase is clean - excellent work!")
        sys.exit(0)


if __name__ == "__main__":
    main()
