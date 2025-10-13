#!/usr/bin/env python3
"""
Analyse le rapport Bandit et génère un résumé des problèmes de sécurité
"""

import json
from collections import defaultdict
from pathlib import Path

def analyze_bandit_report(report_path="bandit_report.json"):
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data.get('results', [])
    metrics = data.get('metrics', {})

    # Grouper par sévérité et type
    by_severity = defaultdict(list)
    by_test_id = defaultdict(list)

    for result in results:
        severity = result.get('issue_severity', 'UNDEFINED')
        test_id = result.get('test_id', 'UNKNOWN')

        by_severity[severity].append(result)
        by_test_id[test_id].append(result)

    # Générer le rapport
    print("=" * 80)
    print("RAPPORT D'ANALYSE DE SÉCURITÉ - BANDIT")
    print("=" * 80)
    print()

    # Résumé global
    print("📊 RÉSUMÉ GLOBAL")
    print("-" * 80)
    total_lines = metrics.get('_totals', {}).get('loc', 0)
    total_issues = len(results)
    print(f"Total de lignes de code: {total_lines}")
    print(f"Total de problèmes détectés: {total_issues}")
    print()

    # Par sévérité
    print("🔴 PAR SÉVÉRITÉ")
    print("-" * 80)
    for severity in ['HIGH', 'MEDIUM', 'LOW']:
        count = len(by_severity.get(severity, []))
        if count > 0:
            emoji = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
            print(f"{emoji} {severity}: {count} problème(s)")
    print()

    # Top 10 des problèmes par type
    print("🎯 TOP 10 DES TYPES DE PROBLÈMES")
    print("-" * 80)
    sorted_by_count = sorted(by_test_id.items(), key=lambda x: len(x[1]), reverse=True)[:10]

    for test_id, issues in sorted_by_count:
        first_issue = issues[0]
        test_name = first_issue.get('test_name', 'Unknown')
        severity = first_issue.get('issue_severity', 'UNDEFINED')
        confidence = first_issue.get('issue_confidence', 'UNDEFINED')
        count = len(issues)

        emoji = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
        print(f"{emoji} {test_id}: {test_name}")
        print(f"   Sévérité: {severity} | Confiance: {confidence} | Occurences: {count}")
        print(f"   Description: {first_issue.get('issue_text', 'N/A')}")
        print()

    # Quick Wins (problèmes HIGH ou MEDIUM avec confiance HIGH)
    print("⚡ QUICK WINS (Haute sévérité + Haute confiance)")
    print("-" * 80)
    quick_wins = [
        r for r in results
        if r.get('issue_severity') in ['HIGH', 'MEDIUM']
        and r.get('issue_confidence') == 'HIGH'
    ]

    if quick_wins:
        # Grouper par test_id
        quick_wins_by_type = defaultdict(list)
        for issue in quick_wins:
            quick_wins_by_type[issue.get('test_id')].append(issue)

        for test_id, issues in sorted(quick_wins_by_type.items(), key=lambda x: len(x[1]), reverse=True):
            first = issues[0]
            severity = first.get('issue_severity')
            emoji = "🔴" if severity == "HIGH" else "🟡"

            print(f"{emoji} {test_id}: {first.get('test_name')}")
            print(f"   {len(issues)} occurence(s)")
            print(f"   {first.get('issue_text')}")

            # Montrer jusqu'à 3 exemples
            for i, issue in enumerate(issues[:3]):
                file_path = issue.get('filename', 'Unknown')
                line_number = issue.get('line_number', 0)
                print(f"   - {file_path}:{line_number}")

            if len(issues) > 3:
                print(f"   ... et {len(issues) - 3} autre(s)")
            print()
    else:
        print("✅ Aucun quick win identifié!")

    print("=" * 80)

    # Sauvegarder un résumé JSON
    summary = {
        "total_issues": total_issues,
        "by_severity": {k: len(v) for k, v in by_severity.items()},
        "quick_wins_count": len(quick_wins),
        "top_issues": [
            {
                "test_id": test_id,
                "test_name": issues[0].get('test_name'),
                "severity": issues[0].get('issue_severity'),
                "count": len(issues)
            }
            for test_id, issues in sorted_by_count[:10]
        ]
    }

    with open('security_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n📝 Résumé sauvegardé dans: security_summary.json")

if __name__ == "__main__":
    analyze_bandit_report()
