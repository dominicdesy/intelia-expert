#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyze to_dict() methods to identify which can be replaced with SerializableMixin
"""

import re
from pathlib import Path
from dataclasses import dataclass
from utils.types import List


@dataclass
class ToDictAnalysis:
    file_path: str
    class_name: str
    is_dataclass: bool
    field_count: int
    dict_keys: List[str]
    has_enum_values: bool
    has_property_usage: bool
    has_conditionals: bool
    has_field_renames: bool
    can_use_mixin: bool
    complexity: str  # 'simple', 'medium', 'complex'


def analyze_file(file_path: Path) -> List[ToDictAnalysis]:
    """Analyze all to_dict methods in a file"""
    results = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return results

    # Find all to_dict methods with context
    pattern = (
        r"(@dataclass\n)?(class \w+.*?):\n.*?def to_dict\(self\).*?return \{(.*?)\}"
    )
    matches = re.finditer(pattern, content, re.DOTALL | re.MULTILINE)

    for match in matches:
        is_dataclass = match.group(1) is not None
        class_def = match.group(2)
        class_name = re.search(r"class (\w+)", class_def).group(1)
        dict_content = match.group(3)

        # Parse dictionary keys
        dict_keys = re.findall(r'"(\w+)":|\'(\w+)\':', dict_content)
        dict_keys = [k[0] or k[1] for k in dict_keys]

        # Analyze complexity
        has_enum_values = ".value" in dict_content
        has_conditionals = " if " in dict_content
        has_property_usage = "@property" in content[: match.start()]

        # Check for field renames (key != field)
        has_renames = False
        for key in dict_keys:
            if f"self.{key}" not in dict_content:
                has_renames = True
                break

        # Determine if mixin can be used
        can_use_mixin = (
            is_dataclass
            and not has_conditionals
            and not has_renames
            and not has_property_usage
        )

        # Complexity assessment
        if can_use_mixin:
            complexity = "simple"
        elif has_conditionals or has_renames:
            complexity = "complex"
        else:
            complexity = "medium"

        results.append(
            ToDictAnalysis(
                file_path=str(file_path),
                class_name=class_name,
                is_dataclass=is_dataclass,
                field_count=len(dict_keys),
                dict_keys=dict_keys,
                has_enum_values=has_enum_values,
                has_property_usage=has_property_usage,
                has_conditionals=has_conditionals,
                has_field_renames=has_renames,
                can_use_mixin=can_use_mixin,
                complexity=complexity,
            )
        )

    return results


def main():
    """Main analysis"""
    all_results = []

    # Analyze all Python files
    for file_path in Path(".").rglob("*.py"):
        if "analyze_to_dict" in str(file_path):
            continue
        results = analyze_file(file_path)
        all_results.extend(results)

    # Print report
    print("=" * 80)
    print("TO_DICT() ANALYSIS REPORT")
    print("=" * 80)

    # Group by complexity
    simple = [r for r in all_results if r.complexity == "simple"]
    medium = [r for r in all_results if r.complexity == "medium"]
    complex_ones = [r for r in all_results if r.complexity == "complex"]

    print(f"\nSIMPLE (can use mixin directly): {len(simple)}")
    for r in simple:
        print(f"  - {r.class_name:30} in {r.file_path}")

    print(f"\nMEDIUM (mixin with enum handling): {len(medium)}")
    for r in medium:
        flags = []
        if r.has_enum_values:
            flags.append("enums")
        print(f"  - {r.class_name:30} in {r.file_path:50} [{', '.join(flags)}]")

    print(f"\nCOMPLEX (keep custom to_dict): {len(complex_ones)}")
    for r in complex_ones:
        reasons = []
        if r.has_conditionals:
            reasons.append("conditionals")
        if r.has_field_renames:
            reasons.append("renames")
        if r.has_property_usage:
            reasons.append("properties")
        print(f"  - {r.class_name:30} in {r.file_path:50} [{', '.join(reasons)}]")

    print("\n" + "=" * 80)
    print(
        f"SUMMARY: {len(simple)} simple, {len(medium)} medium, {len(complex_ones)} complex"
    )
    print(f"Potential lines saved: ~{len(simple) * 10 + len(medium) * 5}")
    print("=" * 80)


if __name__ == "__main__":
    main()
