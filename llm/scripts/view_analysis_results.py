#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
View Analysis Results - Display comprehensive analysis reports

Quick script to view the results of overnight analysis runs.
"""

import json
from pathlib import Path
from datetime import datetime

def print_section(title, char="="):
    """Print section header"""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")

def view_codebase_analysis():
    """View unused files analysis results"""
    print_section("CODEBASE ANALYSIS - UNUSED FILES & DEAD CODE")

    report_file = Path(__file__).parent.parent / 'logs' / 'codebase_analysis_report.json'

    if not report_file.exists():
        print(f"Report not found: {report_file}")
        return

    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)

    summary = report.get('summary', {})

    print(f"Total Python files: {summary.get('total_python_files', 0)}")
    print(f"Total imports: {summary.get('total_imports', 0)}")
    print(f"Total defined items: {summary.get('total_defined_items', 0)}")
    print(f"\nUnused files: {summary.get('unused_files', 0)}")
    print(f"Dead code items: {summary.get('dead_code_items', 0)}")
    print(f"Unused config files: {summary.get('unused_config_files', 0)}")

    # Show top unused files
    unused_files = report.get('unused_files', [])
    if unused_files:
        print("\nTOP 10 LARGEST UNUSED FILES:")
        for item in unused_files[:10]:
            size_kb = item['size_bytes'] / 1024
            print(f"  - {item['file']} ({size_kb:.1f} KB)")
            print(f"    Reason: {item['reason']}")

    # Show sample dead code
    dead_code = report.get('dead_code', [])
    if dead_code:
        print(f"\nSAMPLE DEAD CODE (first 10 of {len(dead_code)}):")
        for item in dead_code[:10]:
            print(f"  - {item['file']}: {item['type']} '{item['name']}'")

    # Show recommendations
    recommendations = report.get('recommendations', [])
    if recommendations:
        print("\nRECOMMENDATIONS:")
        for rec in recommendations:
            priority = rec.get('priority', 'unknown').upper()
            print(f"  [{priority}] {rec.get('message', '')}")

def view_deep_optimization():
    """View deep optimization analysis results"""
    print_section("DEEP OPTIMIZATION ANALYSIS")

    report_file = Path(__file__).parent.parent / 'logs' / 'deep_optimization_report.json'

    if not report_file.exists():
        print(f"Report not found: {report_file}")
        return

    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)

    summary = report.get('summary', {})

    print(f"Total files analyzed: {summary.get('total_files_analyzed', 0)}")
    print(f"Analysis duration: {summary.get('analysis_duration_seconds', 0):.1f} seconds")
    print(f"Health score: {summary.get('health_score', 0):.1f}/100")
    print(f"Total issues found: {summary.get('total_issues_found', 0)}")

    # Top priorities
    priorities = summary.get('top_priorities', [])
    if priorities:
        print("\nTOP PRIORITIES:")
        for p in priorities:
            print(f"  [{p['priority']}] {p['category']}: {p['action']}")
            print(f"       Impact: {p['impact']}")

    # Detailed analyses
    analyses = report.get('analyses', {})

    # Cyclomatic complexity
    complexity = analyses.get('cyclomatic_complexity', {})
    if complexity.get('total_high_complexity', 0) > 0:
        print(f"\nHIGH COMPLEXITY FUNCTIONS ({complexity['total_high_complexity']}):")
        for func in complexity.get('high_complexity_functions', [])[:5]:
            print(f"  - {func['file']}:{func['line']} - {func['function']} (complexity: {func['complexity']})")

    # Code duplication
    duplication = analyses.get('code_duplication', {})
    if duplication.get('total_duplicates', 0) > 0:
        print(f"\nCODE DUPLICATION ({duplication['total_duplicates']} blocks):")
        for dup in duplication.get('duplicate_blocks', [])[:3]:
            print(f"  - {dup['occurrences']} occurrences of similar code block")
            print(f"    Locations: {', '.join([loc['file'] for loc in dup['locations'][:3]])}")

    # Type hints coverage
    type_hints = analyses.get('type_hints', {})
    if type_hints:
        coverage = type_hints.get('coverage_percentage', 0)
        print(f"\nTYPE HINTS COVERAGE: {coverage:.1f}%")
        print(f"  Typed functions: {type_hints.get('typed_functions', 0)}/{type_hints.get('total_functions', 0)}")

    # Documentation coverage
    docs = analyses.get('documentation', {})
    if docs:
        coverage = docs.get('coverage_percentage', 0)
        print(f"\nDOCUMENTATION COVERAGE: {coverage:.1f}%")
        print(f"  Documented items: {docs.get('documented_items', 0)}/{docs.get('total_items', 0)}")

    # Error handling
    error_handling = analyses.get('error_handling', {})
    if error_handling.get('bare_except_count', 0) > 0:
        print("\nERROR HANDLING ISSUES:")
        print(f"  Bare except clauses: {error_handling['bare_except_count']}")
        for exc in error_handling.get('bare_excepts', [])[:5]:
            print(f"    - {exc['file']}:{exc['line']}")

    # Long functions
    long_funcs = analyses.get('long_functions', {})
    if long_funcs.get('total_long_functions', 0) > 0:
        print(f"\nLONG FUNCTIONS (>50 lines): {long_funcs['total_long_functions']}")
        for func in long_funcs.get('functions_over_50_lines', [])[:5]:
            print(f"  - {func['file']}:{func['line']} - {func['function']} ({func['length']} lines)")

    # Performance patterns
    perf = analyses.get('performance_patterns', {})
    if perf.get('total_issues', 0) > 0:
        print(f"\nPERFORMANCE ANTI-PATTERNS: {perf['total_issues']}")
        issue_types = {}
        for issue in perf.get('performance_issues', []):
            issue_type = issue['issue']
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {issue_type}: {count} occurrences")

def view_analysis_logs():
    """View analysis output logs"""
    print_section("ANALYSIS EXECUTION LOGS", "-")

    log_files = [
        'logs/codebase_analysis_output.log',
        'logs/deep_optimization_output.log'
    ]

    for log_file in log_files:
        log_path = Path(__file__).parent.parent / log_file

        if log_path.exists():
            print(f"\n{log_file}:")
            print("-" * 40)
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Show last 20 lines
                for line in lines[-20:]:
                    print(f"  {line.rstrip()}")
        else:
            print(f"\n{log_file}: Not found")

def main():
    """Main function to display all analysis results"""
    print("=" * 80)
    print(f"LLM OPTIMIZATION ANALYSIS RESULTS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    view_codebase_analysis()
    view_deep_optimization()
    view_analysis_logs()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nFull JSON reports available at:")
    print("  - llm/logs/codebase_analysis_report.json")
    print("  - llm/logs/deep_optimization_report.json")

if __name__ == "__main__":
    main()
