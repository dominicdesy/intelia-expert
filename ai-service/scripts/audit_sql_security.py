#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQL Security Audit Script
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
SQL Security Audit Script
Analyzes Python files for SQL injection vulnerabilities
"""

import re
import json
from pathlib import Path
from collections import defaultdict

def load_bandit_results():
    """Load B608 findings from Bandit report"""
    with open('bandit_report.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    b608_findings = [r for r in data['results'] if r['test_id'] == 'B608']
    return b608_findings

def analyze_sql_query(code: str, line_number: int, file_path: str) -> dict:
    """Analyze a SQL query for security issues"""

    analysis = {
        'file': file_path,
        'line': line_number,
        'code_snippet': code.strip(),
        'risk_level': 'SAFE',
        'issues': [],
        'uses_parameters': False,
        'uses_fstring': False,
        'uses_format': False,
        'uses_concat': False
    }

    # Check for f-strings
    if 'f"""' in code or "f'''" in code or 'f"' in code or "f'" in code:
        analysis['uses_fstring'] = True

    # Check for .format()
    if '.format(' in code:
        analysis['uses_format'] = True

    # Check for string concatenation
    if ' + ' in code and ('SELECT' in code.upper() or 'WHERE' in code.upper()):
        analysis['uses_concat'] = True

    # Check for parameterized queries ($1, $2, %s, etc.)
    if re.search(r'\$\d+', code):  # PostgreSQL $1, $2
        analysis['uses_parameters'] = True
    if re.search(r'%s|%\(', code):  # Python DB-API %s, %(name)s
        analysis['uses_parameters'] = True

    # Risk assessment
    if analysis['uses_parameters']:
        analysis['risk_level'] = 'SAFE'
    elif analysis['uses_fstring'] or analysis['uses_format'] or analysis['uses_concat']:
        # Check if variables are user-controlled
        if 'user' in code.lower() or 'input' in code.lower() or 'request' in code.lower():
            analysis['risk_level'] = 'HIGH'
            analysis['issues'].append('User input may be interpolated into SQL query')
        else:
            # Check if variables are validated/sanitized
            if 'where_clause' in code.lower() or 'condition' in code.lower():
                analysis['risk_level'] = 'MEDIUM'
                analysis['issues'].append('Dynamic WHERE clause - verify input validation')
            else:
                analysis['risk_level'] = 'LOW'
                analysis['issues'].append('Non-parameterized query with controlled variables')

    return analysis

def audit_file(file_path: str, findings: list) -> list:
    """Audit a specific file for SQL injection issues"""

    # Normalize path separators for Windows/Unix compatibility
    normalized_path = file_path.replace('/', '\\')
    file_findings = [f for f in findings if normalized_path in f['filename']]

    if not file_findings:
        print(f"[INFO] No findings for {file_path}")
        return []

    print(f"[INFO] Found {len(file_findings)} findings for {file_path}")

    results = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for finding in file_findings:
            line_num = finding['line_number']

            # Get context (5 lines before and after)
            start = max(0, line_num - 6)
            end = min(len(lines), line_num + 5)
            context = ''.join(lines[start:end])

            analysis = analyze_sql_query(context, line_num, file_path)
            analysis['bandit_finding'] = {
                'issue_text': finding['issue_text'],
                'severity': finding['issue_severity'],
                'confidence': finding['issue_confidence']
            }
            results.append(analysis)

    except Exception as e:
        print(f"[ERROR] Could not read {file_path}: {e}")

    return results

def generate_report(all_results: list):
    """Generate a human-readable security audit report"""

    print("=" * 80)
    print("SQL INJECTION SECURITY AUDIT")
    print("=" * 80)
    print()

    # Group by risk level
    by_risk = defaultdict(list)
    for result in all_results:
        by_risk[result['risk_level']].append(result)

    # Summary
    print("SUMMARY")
    print("-" * 80)
    print(f"Total findings: {len(all_results)}")
    print(f"  HIGH risk:   {len(by_risk['HIGH'])}")
    print(f"  MEDIUM risk: {len(by_risk['MEDIUM'])}")
    print(f"  LOW risk:    {len(by_risk['LOW'])}")
    print(f"  SAFE:        {len(by_risk['SAFE'])}")
    print()

    # Detailed findings by risk level
    for risk_level in ['HIGH', 'MEDIUM', 'LOW', 'SAFE']:
        findings = by_risk[risk_level]
        if not findings:
            continue

        print()
        print("=" * 80)
        print(f"{risk_level} RISK FINDINGS ({len(findings)})")
        print("=" * 80)
        print()

        for i, finding in enumerate(findings, 1):
            print(f"{i}. {finding['file']}:{finding['line']}")
            print(f"   Risk: {finding['risk_level']}")

            if finding['issues']:
                print(f"   Issues:")
                for issue in finding['issues']:
                    print(f"     - {issue}")

            print(f"   Analysis:")
            print(f"     - Uses parameters: {finding['uses_parameters']}")
            print(f"     - Uses f-string: {finding['uses_fstring']}")
            print(f"     - Uses .format(): {finding['uses_format']}")
            print(f"     - Uses concatenation: {finding['uses_concat']}")

            print(f"   Code snippet:")
            for line in finding['code_snippet'].split('\n')[:3]:
                if line.strip():
                    # Remove non-ASCII characters to avoid encoding issues
                    clean_line = line.encode('ascii', 'ignore').decode('ascii')
                    print(f"     {clean_line}")

            print()

    # Recommendations
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    if by_risk['HIGH']:
        print("CRITICAL - HIGH RISK findings require immediate attention:")
        print("  - Review user input validation")
        print("  - Convert to parameterized queries using $1, $2, etc.")
        print("  - Never interpolate user input directly into SQL")
        print()

    if by_risk['MEDIUM']:
        print("WARNING - MEDIUM RISK findings should be reviewed:")
        print("  - Verify that dynamic WHERE clauses use validated inputs")
        print("  - Consider using query builders with parameter binding")
        print("  - Add input validation and sanitization")
        print()

    if by_risk['LOW']:
        print("INFO - LOW RISK findings are likely false positives:")
        print("  - Verify variables are from trusted sources (not user input)")
        print("  - Consider refactoring to parameterized queries for best practice")
        print()

    if by_risk['SAFE']:
        print("OK - SAFE findings use proper parameterized queries")
        print("  - These queries are protected against SQL injection")
        print("  - No action needed")
        print()

    # Overall security score
    total = len(all_results)
    if total == 0:
        score = 10.0
    else:
        high_penalty = len(by_risk['HIGH']) * 3
        medium_penalty = len(by_risk['MEDIUM']) * 1.5
        low_penalty = len(by_risk['LOW']) * 0.5

        score = max(0, 10 - (high_penalty + medium_penalty + low_penalty) / total)

    print()
    print("=" * 80)
    print(f"SQL SECURITY SCORE: {score:.1f}/10")
    print("=" * 80)

    if score >= 9:
        print("EXCELLENT - Very few SQL security issues")
    elif score >= 7:
        print("GOOD - Minor SQL security issues to address")
    elif score >= 5:
        print("FAIR - Several SQL security issues need attention")
    else:
        print("POOR - Critical SQL security issues must be fixed")

    print()

def main():
    """Run SQL security audit"""

    files_to_audit = [
        'retrieval/postgresql/retriever.py',
        'retrieval/postgresql/query_builder.py',
        'retrieval/postgresql/temporal.py',
        'generation/generators.py'
    ]

    # Load Bandit findings
    findings = load_bandit_results()

    # Audit each file
    all_results = []
    for file_path in files_to_audit:
        results = audit_file(file_path, findings)
        all_results.extend(results)

    # Generate report
    generate_report(all_results)

    # Save results to JSON
    output_file = 'sql_security_audit.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)

    print(f"Detailed results saved to: {output_file}")
    print()

if __name__ == "__main__":
    main()
