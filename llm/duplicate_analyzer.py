#!/usr/bin/env python3
"""
Advanced duplicate code analyzer for LLM module
Detects duplicate code blocks, similar functions, and refactoring opportunities
"""

import ast
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


class DuplicateAnalyzer:
    """Analyzes Python code for duplication and similarity"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.py_files = list(self.root_dir.rglob("*.py"))
        self.function_signatures: Dict[str, List[str]] = defaultdict(list)
        self.code_blocks: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.similar_functions: List[Tuple[str, str, float]] = []

    def analyze_all(self):
        """Run all analysis methods"""
        print("=" * 70)
        print("DUPLICATE CODE ANALYSIS - Advanced Python Analysis")
        print("=" * 70)
        print(f"\nAnalyzing {len(self.py_files)} Python files...\n")

        self.find_duplicate_functions()
        self.find_duplicate_code_blocks()
        self.find_similar_imports()
        self.find_long_functions()
        self.find_duplicate_docstrings()
        self.generate_summary()

    def find_duplicate_functions(self):
        """Find functions with identical signatures"""
        print("1. DUPLICATE FUNCTION SIGNATURES")
        print("-" * 70)

        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(file_path))

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) or isinstance(
                        node, ast.AsyncFunctionDef
                    ):
                        signature = self._get_function_signature(node)
                        self.function_signatures[signature].append(
                            str(file_path.relative_to(self.root_dir))
                        )
            except Exception:
                continue

        duplicates = {
            sig: files
            for sig, files in self.function_signatures.items()
            if len(files) > 1
        }

        if duplicates:
            for signature, files in sorted(
                duplicates.items(), key=lambda x: len(x[1]), reverse=True
            ):
                print(f"\n  {len(files)} occurrences: {signature}")
                for file in files[:5]:  # Show first 5
                    print(f"    - {file}")
                if len(files) > 5:
                    print(f"    ... and {len(files) - 5} more")
        else:
            print("  No duplicate function signatures found.")

        print()

    def find_duplicate_code_blocks(self):
        """Find duplicate code blocks (5+ lines)"""
        print("2. DUPLICATE CODE BLOCKS (5+ lines)")
        print("-" * 70)

        min_lines = 5

        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Analyze sliding windows of code
                for i in range(len(lines) - min_lines + 1):
                    block = "".join(lines[i : i + min_lines])
                    # Normalize whitespace for comparison
                    normalized = self._normalize_code(block)
                    if normalized:
                        block_hash = hashlib.md5(normalized.encode()).hexdigest()
                        self.code_blocks[block_hash].append(
                            (str(file_path.relative_to(self.root_dir)), i + 1)
                        )
            except Exception:
                continue

        duplicates = {h: locs for h, locs in self.code_blocks.items() if len(locs) > 1}

        if duplicates:
            print(f"\n  Found {len(duplicates)} duplicate code blocks")
            for i, (block_hash, locations) in enumerate(
                sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]
            ):
                print(f"\n  Block {i+1}: {len(locations)} occurrences")
                for file, line in locations[:3]:
                    print(f"    - {file}:{line}")
                if len(locations) > 3:
                    print(f"    ... and {len(locations) - 3} more")
        else:
            print("  No significant duplicate code blocks found.")

        print()

    def find_similar_imports(self):
        """Find common import patterns"""
        print("3. IMPORT ANALYSIS")
        print("-" * 70)

        imports: Dict[str, int] = defaultdict(int)

        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports[f"import {alias.name}"] += 1
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            imports[f"from {module} import {alias.name}"] += 1
            except Exception:
                continue

        print("\n  Most common imports:")
        for imp, count in sorted(imports.items(), key=lambda x: x[1], reverse=True)[
            :15
        ]:
            if count > 3:
                print(f"    {count:3d}x  {imp}")

        print()

    def find_long_functions(self):
        """Find functions that might benefit from refactoring"""
        print("4. LONG FUNCTIONS (>50 lines)")
        print("-" * 70)

        long_functions = []

        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content)

                content.splitlines()

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                            length = node.end_lineno - node.lineno + 1
                            if length > 50:
                                long_functions.append(
                                    (
                                        str(file_path.relative_to(self.root_dir)),
                                        node.name,
                                        node.lineno,
                                        length,
                                    )
                                )
            except Exception:
                continue

        if long_functions:
            print("\n  Functions that may need refactoring:")
            for file, name, line, length in sorted(
                long_functions, key=lambda x: x[3], reverse=True
            )[:15]:
                print(f"    {length:3d} lines: {file}:{line} - {name}()")
        else:
            print("  All functions are reasonably sized.")

        print()

    def find_duplicate_docstrings(self):
        """Find duplicate docstrings (possible copy-paste)"""
        print("5. DUPLICATE DOCSTRINGS")
        print("-" * 70)

        docstrings: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        for file_path in self.py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    ):
                        docstring = ast.get_docstring(node)
                        if docstring and len(docstring) > 20:
                            # Normalize docstring
                            normalized = " ".join(docstring.split())
                            if len(normalized) > 30:
                                docstrings[normalized].append(
                                    (
                                        str(file_path.relative_to(self.root_dir)),
                                        node.name,
                                    )
                                )
            except Exception:
                continue

        duplicates = {doc: locs for doc, locs in docstrings.items() if len(locs) > 1}

        if duplicates:
            print(f"\n  Found {len(duplicates)} duplicate docstrings")
            for doc, locations in sorted(
                duplicates.items(), key=lambda x: len(x[1]), reverse=True
            )[:5]:
                print(f"\n  '{doc[:60]}...' ({len(locations)} occurrences)")
                for file, name in locations[:3]:
                    print(f"    - {file} - {name}")
        else:
            print("  No duplicate docstrings found.")

        print()

    def generate_summary(self):
        """Generate summary and recommendations"""
        print("6. SUMMARY & RECOMMENDATIONS")
        print("-" * 70)

        total_lines = 0
        for file_path in self.py_files:
            try:
                with open(file_path, "r") as f:
                    total_lines += len(f.readlines())
            except Exception:
                continue

        print(f"\n  Total files analyzed: {len(self.py_files)}")
        print(f"  Total lines of code: {total_lines:,}")
        print(
            f"  Average file size: {total_lines // len(self.py_files) if self.py_files else 0} lines"
        )

        duplicate_funcs = sum(
            1 for files in self.function_signatures.values() if len(files) > 1
        )
        duplicate_blocks = sum(1 for locs in self.code_blocks.values() if len(locs) > 1)

        print(f"\n  Duplicate function signatures: {duplicate_funcs}")
        print(f"  Duplicate code blocks: {duplicate_blocks}")

        print("\n  RECOMMENDATIONS:")
        if duplicate_funcs > 0:
            print("    - Consider creating utility modules for common functions")
        if duplicate_blocks > 10:
            print("    - Refactor duplicate code into shared helper functions")
        print("    - Use inheritance or composition for repeated patterns")
        print("    - Consider creating base classes for common functionality")

        print("\n" + "=" * 70)

    def _get_function_signature(self, node) -> str:
        """Extract normalized function signature"""
        args = []
        if hasattr(node.args, "args"):
            args = [arg.arg for arg in node.args.args]

        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{async_prefix}def {node.name}({', '.join(args)})"

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison (remove comments, normalize whitespace)"""
        lines = []
        for line in code.splitlines():
            # Remove comments
            if "#" in line:
                line = line[: line.index("#")]
            # Strip whitespace
            line = line.strip()
            # Skip empty lines
            if line:
                lines.append(line)
        return "\n".join(lines)


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."

    analyzer = DuplicateAnalyzer(root)
    analyzer.analyze_all()
