# -*- coding: utf-8 -*-
"""
Analyze type hints coverage across the codebase
"""

import ast
from pathlib import Path
from typing import Dict, Tuple


def analyze_function_hints(node: ast.FunctionDef) -> Tuple[int, int]:
    """
    Analyze type hints in a function
    Returns: (total_params, hinted_params)
    """
    total = 0
    hinted = 0

    # Check parameters
    for arg in node.args.args:
        if arg.arg != "self" and arg.arg != "cls":
            total += 1
            if arg.annotation is not None:
                hinted += 1

    # Check return annotation
    if node.returns is not None:
        hinted += 0.5  # Bonus for return type

    return total, hinted


def analyze_file(file_path: str) -> Dict:
    """Analyze type hints in a Python file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)

        total_params = 0
        hinted_params = 0
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                t, h = analyze_function_hints(node)
                total_params += t
                hinted_params += h

                if t > 0:  # Only count functions with parameters
                    coverage = (h / t * 100) if t > 0 else 0
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "total_params": t,
                            "hinted_params": h,
                            "coverage": coverage,
                        }
                    )

        file_coverage = (
            (hinted_params / total_params * 100) if total_params > 0 else 100
        )

        return {
            "file": file_path,
            "total_params": total_params,
            "hinted_params": hinted_params,
            "coverage": file_coverage,
            "functions": sorted(functions, key=lambda x: x["coverage"]),
        }

    except Exception as e:
        return {"file": file_path, "error": str(e), "coverage": 0}


def main():
    """Main analysis"""
    base_path = Path(__file__).parent.parent

    # Directories to analyze
    dirs_to_scan = ["api", "core", "retrieval", "generation", "utils"]

    all_results = []

    for dir_name in dirs_to_scan:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            result = analyze_file(str(py_file))
            all_results.append(result)

    # Sort by coverage (lowest first)
    all_results.sort(key=lambda x: x.get("coverage", 0))

    # Calculate overall stats
    total_all = sum(r.get("total_params", 0) for r in all_results)
    hinted_all = sum(r.get("hinted_params", 0) for r in all_results)
    overall_coverage = (hinted_all / total_all * 100) if total_all > 0 else 0

    # Print results
    print("=" * 80)
    print("TYPE HINTS ANALYSIS")
    print("=" * 80)
    print(f"\nOVERALL COVERAGE: {overall_coverage:.1f}%")
    print(f"Total parameters: {total_all}")
    print(f"Hinted parameters: {hinted_all:.0f}")
    print()

    # Files with LOW coverage (<50%)
    low_coverage = [
        r
        for r in all_results
        if r.get("coverage", 0) < 50 and r.get("total_params", 0) > 0
    ]
    print(f"\n{len(low_coverage)} FILES WITH LOW TYPE HINTS (<50%):")
    print("-" * 80)
    for i, result in enumerate(low_coverage[:20], 1):
        rel_path = str(Path(result["file"]).relative_to(base_path))
        print(
            f"{i:2}. {rel_path:60} {result['coverage']:5.1f}% ({int(result['hinted_params'])}/{result['total_params']})"
        )

    # Files with MEDIUM coverage (50-80%)
    medium_coverage = [r for r in all_results if 50 <= r.get("coverage", 0) < 80]
    print(f"\n\n{len(medium_coverage)} FILES WITH MEDIUM TYPE HINTS (50-80%):")
    print("-" * 80)
    for i, result in enumerate(medium_coverage[:15], 1):
        rel_path = str(Path(result["file"]).relative_to(base_path))
        print(
            f"{i:2}. {rel_path:60} {result['coverage']:5.1f}% ({int(result['hinted_params'])}/{result['total_params']})"
        )

    # Priority files to improve
    print("\n\n" + "=" * 80)
    print("PRIORITY FILES TO IMPROVE (most impact)")
    print("=" * 80)

    # Sort by total_params * (100 - coverage) to find high-impact files
    priority = sorted(
        [
            r
            for r in all_results
            if r.get("total_params", 0) > 5 and r.get("coverage", 0) < 80
        ],
        key=lambda x: x.get("total_params", 0) * (100 - x.get("coverage", 0)),
        reverse=True,
    )

    for i, result in enumerate(priority[:10], 1):
        rel_path = str(Path(result["file"]).relative_to(base_path))
        impact = result["total_params"] * (100 - result["coverage"]) / 100
        print(f"{i:2}. {rel_path:60} {result['coverage']:5.1f}% | Impact: {impact:.1f}")

        # Show worst functions in this file
        if "functions" in result and len(result["functions"]) > 0:
            worst_funcs = [f for f in result["functions"] if f["coverage"] < 50][:3]
            for func in worst_funcs:
                print(
                    f"    - {func['name']:40} Line {func['line']:4} | {func['coverage']:5.1f}%"
                )

    print("\n" + "=" * 80)
    print(
        f"TARGET: 70% coverage | CURRENT: {overall_coverage:.1f}% | NEED: +{70 - overall_coverage:.1f}%"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
