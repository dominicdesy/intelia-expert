# -*- coding: utf-8 -*-
"""
Detect code duplication in the codebase using AST similarity analysis
"""

import ast
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List


def normalize_ast_node(node: ast.AST) -> str:
    """
    Normalize an AST node by removing variable names and keeping structure
    """
    if isinstance(node, ast.Name):
        return "VAR"
    elif isinstance(node, ast.Constant):
        # Normalize constants by type
        if isinstance(node.value, str):
            return "STR_CONST"
        elif isinstance(node.value, (int, float)):
            return "NUM_CONST"
        elif isinstance(node.value, bool):
            return "BOOL_CONST"
        else:
            return "CONST"
    elif isinstance(node, ast.Attribute):
        return f"ATTR.{node.attr}"
    else:
        return node.__class__.__name__


def get_ast_hash(node: ast.AST, depth: int = 0, max_depth: int = 5) -> str:
    """
    Get a hash representing the structure of an AST node
    """
    if depth > max_depth:
        return ""

    parts = [normalize_ast_node(node)]

    for child in ast.iter_child_nodes(node):
        parts.append(get_ast_hash(child, depth + 1, max_depth))

    return hashlib.md5("|".join(parts).encode()).hexdigest()


def extract_code_blocks(file_path: str) -> List[Dict]:
    """
    Extract significant code blocks from a Python file
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        blocks = []

        for node in ast.walk(tree):
            # Extract functions and class methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only consider functions with at least 5 lines
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    lines = node.end_lineno - node.lineno
                    if lines >= 5:  # Minimum size for duplication
                        ast_hash = get_ast_hash(node)
                        blocks.append(
                            {
                                "file": file_path,
                                "name": node.name,
                                "type": "function",
                                "lineno": node.lineno,
                                "end_lineno": node.end_lineno,
                                "lines": lines,
                                "hash": ast_hash,
                            }
                        )

            # Extract significant if/for/while blocks
            elif isinstance(node, (ast.If, ast.For, ast.While)) and hasattr(
                node, "lineno"
            ):
                if hasattr(node, "end_lineno"):
                    lines = node.end_lineno - node.lineno
                    if lines >= 8:  # Larger minimum for control structures
                        ast_hash = get_ast_hash(node)
                        blocks.append(
                            {
                                "file": file_path,
                                "name": f"{node.__class__.__name__}_block",
                                "type": "control_structure",
                                "lineno": node.lineno,
                                "end_lineno": node.end_lineno,
                                "lines": lines,
                                "hash": ast_hash,
                            }
                        )

        return blocks

    except Exception:
        return []


def find_duplicates(blocks: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Find duplicate blocks by hash
    """
    hash_map = defaultdict(list)

    for block in blocks:
        hash_map[block["hash"]].append(block)

    # Only return hashes with more than one occurrence
    duplicates = {h: blocks for h, blocks in hash_map.items() if len(blocks) > 1}

    return duplicates


def analyze_similarity(
    file_path1: str,
    file_path2: str,
    lineno1: int,
    lineno2: int,
    lines1: int,
    lines2: int,
) -> float:
    """
    Calculate line-by-line similarity between two code blocks
    """
    try:
        with open(file_path1, "r", encoding="utf-8") as f:
            content1 = f.readlines()[lineno1 - 1 : lineno1 - 1 + lines1]

        with open(file_path2, "r", encoding="utf-8") as f:
            content2 = f.readlines()[lineno2 - 1 : lineno2 - 1 + lines2]

        # Simple similarity: count matching lines (normalized)
        content1_norm = [line.strip() for line in content1]
        content2_norm = [line.strip() for line in content2]

        matches = sum(1 for line in content1_norm if line and line in content2_norm)
        total = max(len(content1_norm), len(content2_norm))

        return (matches / total * 100) if total > 0 else 0

    except Exception:
        return 0


def main():
    """Main analysis"""
    base_path = Path(__file__).parent.parent

    # Directories to analyze
    dirs_to_scan = ["api", "core", "retrieval", "generation", "utils"]

    all_blocks = []

    for dir_name in dirs_to_scan:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            blocks = extract_code_blocks(str(py_file))
            all_blocks.extend(blocks)

    print("=" * 80)
    print("CODE DUPLICATION DETECTION")
    print("=" * 80)
    print(f"\nTotal code blocks analyzed: {len(all_blocks)}")
    print()

    # Find duplicates
    duplicates = find_duplicates(all_blocks)

    # Filter out trivial duplicates (e.g., simple getters/setters)
    significant_duplicates = {}
    for hash_val, blocks in duplicates.items():
        # Must be at least 10 lines or appear 3+ times
        if blocks[0]["lines"] >= 10 or len(blocks) >= 3:
            significant_duplicates[hash_val] = blocks

    print(f"Duplicate block groups found: {len(significant_duplicates)}")
    print()

    if len(significant_duplicates) == 0:
        print("✅ NO SIGNIFICANT CODE DUPLICATION DETECTED!")
        print()
        print("The codebase has excellent code reuse patterns.")
        print()
        return

    # Sort by impact (number of duplicates * size)
    sorted_duplicates = sorted(
        significant_duplicates.items(),
        key=lambda x: len(x[1]) * x[1][0]["lines"],
        reverse=True,
    )

    print("=" * 80)
    print(f"TOP {min(10, len(sorted_duplicates))} DUPLICATE BLOCKS (by impact)")
    print("=" * 80)
    print()

    for i, (hash_val, blocks) in enumerate(sorted_duplicates[:10], 1):
        impact = len(blocks) * blocks[0]["lines"]
        print(f"{i}. {blocks[0]['type'].upper()}: '{blocks[0]['name']}'")
        print(
            f"   Lines: {blocks[0]['lines']} | Occurrences: {len(blocks)} | Impact: {impact}"
        )
        print("   Locations:")

        for j, block in enumerate(blocks[:5], 1):  # Show first 5 occurrences
            rel_path = str(Path(block["file"]).relative_to(base_path))
            print(f"     {j}. {rel_path}:{block['lineno']}")

        if len(blocks) > 5:
            print(f"     ... and {len(blocks) - 5} more occurrences")

        # Calculate similarity for first two occurrences
        if len(blocks) >= 2:
            similarity = analyze_similarity(
                blocks[0]["file"],
                blocks[1]["file"],
                blocks[0]["lineno"],
                blocks[1]["lineno"],
                blocks[0]["lines"],
                blocks[1]["lines"],
            )
            print(f"   Similarity: {similarity:.1f}%")

        print()

    # Summary
    total_duplicate_lines = sum(
        len(blocks) * blocks[0]["lines"] for blocks in significant_duplicates.values()
    )
    total_lines = sum(block["lines"] for block in all_blocks)
    duplication_percentage = (
        (total_duplicate_lines / total_lines * 100) if total_lines > 0 else 0
    )

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total duplicate lines: {total_duplicate_lines}")
    print(f"Total code lines: {total_lines}")
    print(f"Duplication percentage: {duplication_percentage:.2f}%")
    print()

    if duplication_percentage < 3:
        print("✅ EXCELLENT: Duplication is very low (<3%)")
    elif duplication_percentage < 5:
        print("✓ GOOD: Duplication is acceptable (<5%)")
    elif duplication_percentage < 10:
        print("⚠ WARNING: Duplication is moderate (5-10%)")
    else:
        print("❌ HIGH: Duplication is significant (>10%)")

    print()


if __name__ == "__main__":
    main()
