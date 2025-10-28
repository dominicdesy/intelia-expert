# -*- coding: utf-8 -*-
"""
validate_golden_dataset.py - Comprehensive validator for RAGAS golden dataset
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
validate_golden_dataset.py - Comprehensive validator for RAGAS golden dataset

Validates structure, types, and content quality for optimal RAGAS evaluation.
Based on pragmatic recommendations for production-ready datasets.
"""

import re
import json
from typing import Dict, List, Any
from collections import Counter
from golden_dataset_intelia import get_intelia_test_dataset

# RAGAS required fields
REQUIRED_FIELDS = {"question", "ground_truth", "contexts", "answer"}

# Recommended optional fields for enhanced evaluation
RECOMMENDED_FIELDS = {
    "id",
    "lang",
    "category",
    "expected_behavior",
    "metric",
    "unit",
    "target_value",
    "tolerance_abs",
    "tolerance_rel",
    "source_ref",
    "difficulty",
    "exclude_from_main",
}


class DatasetValidator:
    """Comprehensive validator for golden dataset"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = {
            "total_tests": 0,
            "by_category": Counter(),
            "by_lang": Counter(),
            "by_difficulty": Counter(),
            "missing_ids": 0,
            "missing_source_refs": 0,
            "long_ground_truths": 0,
            "comma_decimals": 0,
            "empty_contexts": 0,
            "duplicate_questions": 0,
        }

    def validate_required_fields(self, idx: int, item: Dict[str, Any]) -> None:
        """Validate presence of required RAGAS fields"""
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            self.errors.append(
                (idx, f"CRITICAL: Missing required fields: {sorted(missing)}")
            )

    def validate_field_types(self, idx: int, item: Dict[str, Any]) -> None:
        """Validate field types match RAGAS expectations"""
        q = item.get("question")
        if not isinstance(q, str):
            self.errors.append(
                (idx, f"CRITICAL: 'question' must be str, got {type(q).__name__}")
            )

        gt = item.get("ground_truth")
        if not isinstance(gt, str):
            self.errors.append(
                (idx, f"CRITICAL: 'ground_truth' must be str, got {type(gt).__name__}")
            )

        ctx = item.get("contexts")
        if not isinstance(ctx, list):
            self.errors.append(
                (idx, f"CRITICAL: 'contexts' must be list, got {type(ctx).__name__}")
            )
        elif ctx and not all(isinstance(c, str) for c in ctx):
            self.errors.append((idx, "CRITICAL: All 'contexts' items must be str"))

        ans = item.get("answer")
        if not isinstance(ans, str):
            self.errors.append(
                (idx, f"CRITICAL: 'answer' must be str, got {type(ans).__name__}")
            )

    def validate_decimal_format(self, idx: int, item: Dict[str, Any]) -> None:
        """Check for comma decimals (should use dot)"""
        gt = item.get("ground_truth", "")
        comma_nums = re.findall(r"\d+,\d+", gt)
        if comma_nums:
            self.errors.append(
                (
                    idx,
                    f"FORMAT: Comma decimals found in ground_truth: {comma_nums[:3]}... (use dot instead)",
                )
            )
            self.stats["comma_decimals"] += 1

    def validate_ground_truth_length(self, idx: int, item: Dict[str, Any]) -> None:
        """Warn if ground truth is too long (reduces RAGAS accuracy)"""
        gt = item.get("ground_truth", "")
        words = len(gt.split())

        if words > 200:
            self.warnings.append(
                (
                    idx,
                    f"VERBOSE: Ground truth has {words} words (>200). Consider shortening to atomic facts.",
                )
            )
            self.stats["long_ground_truths"] += 1
        elif words > 100:
            self.info.append(
                (
                    idx,
                    f"Ground truth has {words} words. Consider moving explanations to 'rationale' field.",
                )
            )

    def validate_metadata_presence(self, idx: int, item: Dict[str, Any]) -> None:
        """Check presence of recommended metadata fields"""
        if "id" not in item:
            self.warnings.append(
                (idx, "METADATA: Missing 'id' field for stable tracking")
            )
            self.stats["missing_ids"] += 1

        if "source_ref" not in item:
            self.warnings.append(
                (idx, "METADATA: Missing 'source_ref' for traceability")
            )
            self.stats["missing_source_refs"] += 1

        if "lang" not in item:
            self.info.append(
                (idx, "Missing 'lang' field (fr/en/th) for language-specific analysis")
            )

        if "difficulty" not in item:
            self.info.append(
                (
                    idx,
                    "Missing 'difficulty' field (easy/medium/hard/subjective) for segmented analysis",
                )
            )

    def validate_numeric_metadata(self, idx: int, item: Dict[str, Any]) -> None:
        """Validate numeric tolerance metadata"""
        has_metric = "metric" in item
        has_target = "target_value" in item
        has_tolerance = "tolerance_abs" in item or "tolerance_rel" in item

        if has_metric and not has_target:
            self.warnings.append(
                (
                    idx,
                    f"NUMERIC: Has 'metric' ({item['metric']}) but missing 'target_value'",
                )
            )

        if has_target and not has_tolerance:
            self.info.append(
                (
                    idx,
                    "Has 'target_value' but no tolerance. Consider adding 'tolerance_abs' or 'tolerance_rel'",
                )
            )

    def validate_empty_contexts(self, idx: int, item: Dict[str, Any]) -> None:
        """Check if contexts are empty (expected if filled dynamically)"""
        if not item.get("contexts"):
            self.stats["empty_contexts"] += 1

    def validate_special_cases(self, idx: int, item: Dict[str, Any]) -> None:
        """Validate special test cases"""
        q = item.get("question", "")

        # Empty query test
        if q == "":
            if not item.get("exclude_from_main"):
                self.warnings.append(
                    (
                        idx,
                        "SPECIAL: Empty query test should have 'exclude_from_main': True",
                    )
                )

        # OOD tests
        if "out_of_domain" in item.get("category", ""):
            if not item.get("exclude_from_main"):
                self.info.append(
                    (
                        idx,
                        "Consider 'exclude_from_main': True for OOD tests to evaluate separately",
                    )
                )

        # Subjective questions
        if "subjective" in item.get("category", "").lower():
            if item.get("difficulty") != "subjective":
                self.info.append(
                    (idx, "Subjective question should have difficulty='subjective'")
                )

    def detect_duplicate_questions(self, dataset: List[Dict[str, Any]]) -> None:
        """Detect duplicate questions"""
        questions = [item.get("question", "") for item in dataset]
        counts = Counter(questions)
        duplicates = {q: c for q, c in counts.items() if c > 1 and q}

        if duplicates:
            for q, count in duplicates.items():
                indices = [
                    i for i, item in enumerate(dataset) if item.get("question") == q
                ]
                self.errors.append(
                    (
                        indices[0],
                        f"DUPLICATE: Question appears {count} times at indices {indices}",
                    )
                )
                self.stats["duplicate_questions"] += 1

    def collect_statistics(self, dataset: List[Dict[str, Any]]) -> None:
        """Collect dataset statistics"""
        self.stats["total_tests"] = len(dataset)

        for item in dataset:
            cat = item.get("category", "unknown")
            self.stats["by_category"][cat] += 1

            lang = item.get("lang", "unknown")
            self.stats["by_lang"][lang] += 1

            diff = item.get("difficulty", "unknown")
            self.stats["by_difficulty"][diff] += 1

    def validate(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run all validations and return report"""
        print("=" * 80)
        print("RAGAS GOLDEN DATASET VALIDATOR")
        print("=" * 80)
        print(f"\nValidating {len(dataset)} test cases...\n")

        # Collect stats
        self.collect_statistics(dataset)

        # Detect duplicates (dataset-level)
        self.detect_duplicate_questions(dataset)

        # Per-item validations
        for idx, item in enumerate(dataset):
            self.validate_required_fields(idx, item)
            self.validate_field_types(idx, item)
            self.validate_decimal_format(idx, item)
            self.validate_ground_truth_length(idx, item)
            self.validate_metadata_presence(idx, item)
            self.validate_numeric_metadata(idx, item)
            self.validate_empty_contexts(idx, item)
            self.validate_special_cases(idx, item)

        # Generate report
        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        print("\n" + "=" * 80)
        print("VALIDATION REPORT")
        print("=" * 80)

        # Critical errors (blocking)
        if self.errors:
            print(f"\n🔴 CRITICAL ERRORS ({len(self.errors)}):")
            print("-" * 80)
            for idx, msg in self.errors[:20]:  # Show first 20
                print(f"  [{idx:2d}] {msg}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more errors")
        else:
            print("\n✅ No critical errors found!")

        # Warnings (should fix)
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            print("-" * 80)
            for idx, msg in self.warnings[:15]:
                print(f"  [{idx:2d}] {msg}")
            if len(self.warnings) > 15:
                print(f"  ... and {len(self.warnings) - 15} more warnings")

        # Info (nice to have)
        if self.info:
            print(f"\nℹ️  RECOMMENDATIONS ({len(self.info)}):")
            print("-" * 80)
            for idx, msg in self.info[:10]:
                print(f"  [{idx:2d}] {msg}")
            if len(self.info) > 10:
                print(f"  ... and {len(self.info) - 10} more recommendations")

        # Statistics
        print("\n" + "=" * 80)
        print("DATASET STATISTICS")
        print("=" * 80)
        print(f"\n📊 Total Tests: {self.stats['total_tests']}")

        print(f"\n📁 By Category ({len(self.stats['by_category'])} categories):")
        for cat, count in self.stats["by_category"].most_common():
            print(f"  - {cat}: {count}")

        print("\n🌍 By Language:")
        for lang, count in self.stats["by_lang"].most_common():
            print(f"  - {lang}: {count}")

        print("\n📈 By Difficulty:")
        for diff, count in self.stats["by_difficulty"].most_common():
            print(f"  - {diff}: {count}")

        print("\n🔍 Quality Metrics:")
        print(
            f"  - Missing IDs: {self.stats['missing_ids']}/{self.stats['total_tests']}"
        )
        print(
            f"  - Missing source_refs: {self.stats['missing_source_refs']}/{self.stats['total_tests']}"
        )
        print(
            f"  - Long ground truths (>200 words): {self.stats['long_ground_truths']}"
        )
        print(f"  - Comma decimals: {self.stats['comma_decimals']}")
        print(
            f"  - Empty contexts: {self.stats['empty_contexts']}/{self.stats['total_tests']}"
        )
        print(f"  - Duplicate questions: {self.stats['duplicate_questions']}")

        # Priority recommendations
        print("\n" + "=" * 80)
        print("PRIORITY ACTIONS")
        print("=" * 80)

        priorities = []

        if self.errors:
            priorities.append(
                f"🔴 FIX {len(self.errors)} CRITICAL ERRORS (blocking for RAGAS)"
            )

        if self.stats["comma_decimals"] > 0:
            priorities.append(
                f"🔴 Replace {self.stats['comma_decimals']} comma decimals with dots"
            )

        if self.stats["long_ground_truths"] > 0:
            priorities.append(
                f"⚠️  Shorten {self.stats['long_ground_truths']} long ground truths (move details to 'rationale')"
            )

        if self.stats["missing_ids"] > self.stats["total_tests"] * 0.5:
            priorities.append(f"⚠️  Add stable IDs to {self.stats['missing_ids']} tests")

        if self.stats["missing_source_refs"] > self.stats["total_tests"] * 0.7:
            priorities.append(
                f"ℹ️  Add source_ref to {self.stats['missing_source_refs']} tests for traceability"
            )

        if not priorities:
            priorities.append(
                "✅ Dataset structure looks good! Consider adding optional metadata for richer analysis."
            )

        for i, action in enumerate(priorities, 1):
            print(f"\n{i}. {action}")

        print("\n" + "=" * 80)

        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "info": len(self.info),
            "stats": dict(self.stats),
            "error_details": self.errors,
            "warning_details": self.warnings,
            "info_details": self.info,
        }


def main():
    """Main validation entry point"""
    dataset = get_intelia_test_dataset()
    validator = DatasetValidator()
    report = validator.validate(dataset)

    # Save report to JSON
    report_path = "logs/golden_dataset_validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Full report saved to: {report_path}")

    # Exit code
    if report["errors"] > 0:
        print("\n❌ Validation FAILED (critical errors found)")
        return 1
    elif report["warnings"] > 5:
        print("\n⚠️  Validation PASSED with warnings")
        return 0
    else:
        print("\n✅ Validation PASSED")
        return 0


if __name__ == "__main__":
    exit(main())
