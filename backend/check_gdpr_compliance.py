#!/usr/bin/env python3
"""
GDPR Compliance Checker for Intelia Expert
Analyse la conformité RGPD du code et génère un rapport détaillé
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Données personnelles à détecter
PERSONAL_DATA_PATTERNS = {
    "email": r'\b(email|e-mail|mail)\b',
    "phone": r'\b(phone|telephone|tel|mobile)\b',
    "name": r'\b(name|first_name|last_name|full_name|prenom|nom)\b',
    "address": r'\b(address|adresse|street|city|postal|zip)\b',
    "password": r'\b(password|passwd|pwd|mot_de_passe)\b',
    "ip_address": r'\b(ip_address|ip|remote_addr)\b',
    "date_of_birth": r'\b(birth|dob|age|birthday)\b',
    "ssn": r'\b(ssn|social_security|securite_sociale)\b',
    "credit_card": r'\b(credit_card|card_number|cvv|carte)\b',
    "user_id": r'\b(user_id|user_email|auth_user_id)\b',
}

# Pratiques GDPR à vérifier
GDPR_CHECKS = {
    "encryption": r'\b(encrypt|decrypt|cipher|hash|bcrypt|scrypt|argon2)\b',
    "consent": r'\b(consent|consentement|agree|accepte)\b',
    "deletion": r'\b(delete|remove|purge|anonymize|supprimer)\b',
    "export": r'\b(export|download|extract|telecharger)\b',
    "audit_log": r'\b(audit|log|track|tracer)\b',
    "anonymization": r'\b(anonymize|pseudonymize|mask|obfuscate)\b',
    "retention": r'\b(retention|expire|ttl|cleanup|conservation)\b',
}

def scan_file(file_path):
    """Scan un fichier pour données personnelles et pratiques GDPR"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None

    result = {
        "file": str(file_path),
        "personal_data": defaultdict(list),
        "gdpr_practices": defaultdict(list),
        "issues": [],
    }

    # Détecter données personnelles
    for data_type, pattern in PERSONAL_DATA_PATTERNS.items():
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            context = content[max(0, match.start()-50):match.end()+50]
            result["personal_data"][data_type].append({
                "line": line_num,
                "context": context.strip()
            })

    # Détecter pratiques GDPR
    for practice, pattern in GDPR_CHECKS.items():
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            result["gdpr_practices"][practice].append(line_num)

    # Vérifier issues spécifiques
    # 1. Logging d'emails en clair
    if re.search(r'logger\.(info|debug|warning).*\bemail\b', content, re.IGNORECASE):
        result["issues"].append({
            "type": "email_logging",
            "severity": "HIGH",
            "message": "Emails potentiellement loggés en clair (violation RGPD Article 32)"
        })

    # 2. Pas de chiffrement explicite pour données sensibles
    if result["personal_data"]["password"] and not result["gdpr_practices"]["encryption"]:
        result["issues"].append({
            "type": "missing_encryption",
            "severity": "CRITICAL",
            "message": "Mots de passe trouvés sans chiffrement apparent"
        })

    # 3. Absence d'audit log pour accès données
    if result["personal_data"]["user_id"] and not result["gdpr_practices"]["audit_log"]:
        result["issues"].append({
            "type": "missing_audit",
            "severity": "MEDIUM",
            "message": "Accès données utilisateur sans audit log"
        })

    return result

def generate_report(scan_results):
    """Génère un rapport de conformité GDPR"""
    report = {
        "scan_date": datetime.now().isoformat(),
        "summary": {
            "files_scanned": len(scan_results),
            "total_personal_data": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
        },
        "files": scan_results,
        "recommendations": []
    }

    # Compter occurrences
    for result in scan_results:
        for data_type, occurrences in result["personal_data"].items():
            report["summary"]["total_personal_data"] += len(occurrences)

        for issue in result["issues"]:
            report["summary"]["total_issues"] += 1
            if issue["severity"] == "CRITICAL":
                report["summary"]["critical_issues"] += 1
            elif issue["severity"] == "HIGH":
                report["summary"]["high_issues"] += 1
            elif issue["severity"] == "MEDIUM":
                report["summary"]["medium_issues"] += 1

    # Générer recommandations
    if report["summary"]["critical_issues"] > 0:
        report["recommendations"].append({
            "priority": "CRITICAL",
            "action": "Implémenter le chiffrement pour tous les mots de passe",
            "article": "RGPD Article 32 (Sécurité du traitement)"
        })

    if report["summary"]["high_issues"] > 0:
        report["recommendations"].append({
            "priority": "HIGH",
            "action": "Masquer ou hasher les emails dans les logs",
            "article": "RGPD Article 32 (Sécurité du traitement)"
        })

    if report["summary"]["medium_issues"] > 0:
        report["recommendations"].append({
            "priority": "MEDIUM",
            "action": "Créer un audit log des accès aux données personnelles",
            "article": "RGPD Article 30 (Registre des activités de traitement)"
        })

    # Vérifier présence de pratiques GDPR essentielles
    has_consent = any(r["gdpr_practices"]["consent"] for r in scan_results)
    has_deletion = any(r["gdpr_practices"]["deletion"] for r in scan_results)
    has_export = any(r["gdpr_practices"]["export"] for r in scan_results)

    if not has_consent:
        report["recommendations"].append({
            "priority": "HIGH",
            "action": "Implémenter mécanisme de consentement explicite",
            "article": "RGPD Article 6 (Licéité du traitement)"
        })

    if not has_deletion:
        report["recommendations"].append({
            "priority": "HIGH",
            "action": "Implémenter droit à l'effacement (right to be forgotten)",
            "article": "RGPD Article 17 (Droit à l'effacement)"
        })

    if not has_export:
        report["recommendations"].append({
            "priority": "MEDIUM",
            "action": "Implémenter droit à la portabilité des données",
            "article": "RGPD Article 20 (Droit à la portabilité)"
        })

    return report

def main():
    """Point d'entrée principal"""
    backend_dir = Path("app")
    scan_results = []

    print("[*] Scan GDPR en cours...")
    print(f"[*] Repertoire: {backend_dir.absolute()}\n")

    # Scanner tous les fichiers Python
    for py_file in backend_dir.rglob("*.py"):
        result = scan_file(py_file)
        if result:
            scan_results.append(result)

    # Générer rapport
    report = generate_report(scan_results)

    # Afficher résumé
    print("=" * 60)
    print("RESUME DE CONFORMITE RGPD")
    print("=" * 60)
    print(f"Fichiers scannes: {report['summary']['files_scanned']}")
    print(f"Donnees personnelles trouvees: {report['summary']['total_personal_data']}")
    print(f"\n[CRITICAL] Issues CRITIQUES: {report['summary']['critical_issues']}")
    print(f"[HIGH] Issues HAUTE priorite: {report['summary']['high_issues']}")
    print(f"[MEDIUM] Issues MOYENNE priorite: {report['summary']['medium_issues']}")

    print("\n" + "=" * 60)
    print("RECOMMANDATIONS PRIORITAIRES")
    print("=" * 60)
    for i, rec in enumerate(report["recommendations"][:5], 1):
        print(f"\n{i}. [{rec['priority']}] {rec['action']}")
        print(f"   Article: {rec['article']}")

    # Sauvegarder rapport JSON
    report_file = "gdpr_compliance_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Rapport complet sauvegarde: {report_file}")

    # Générer rapport Markdown
    md_report = generate_markdown_report(report)
    md_file = "GDPR_COMPLIANCE_REPORT.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_report)

    print(f"[OK] Rapport Markdown sauvegarde: {md_file}")

    # Code de sortie basé sur sévérité
    if report['summary']['critical_issues'] > 0:
        print("\n[FAIL] ECHEC: Issues critiques trouvees")
        return 1
    elif report['summary']['high_issues'] > 0:
        print("\n[WARNING] AVERTISSEMENT: Issues haute priorite trouvees")
        return 0
    else:
        print("\n[SUCCESS] Conformite RGPD acceptable")
        return 0

def generate_markdown_report(report):
    """Génère un rapport Markdown lisible"""
    md = f"""# Rapport de Conformité RGPD

**Date**: {report['scan_date']}

## Résumé Exécutif

- **Fichiers scannés**: {report['summary']['files_scanned']}
- **Données personnelles détectées**: {report['summary']['total_personal_data']} occurrences
- **Issues trouvées**: {report['summary']['total_issues']}
  - 🔴 Critiques: {report['summary']['critical_issues']}
  - 🟠 Haute priorité: {report['summary']['high_issues']}
  - 🟡 Moyenne priorité: {report['summary']['medium_issues']}

## Score de Conformité

"""

    # Calculer score
    max_score = 100
    penalty = report['summary']['critical_issues'] * 20
    penalty += report['summary']['high_issues'] * 10
    penalty += report['summary']['medium_issues'] * 5
    score = max(0, max_score - penalty)

    md += f"**Score global: {score}/100**\n\n"

    if score >= 80:
        md += "✅ **Statut**: Conforme\n\n"
    elif score >= 60:
        md += "⚠️ **Statut**: Partiellement conforme - Actions requises\n\n"
    else:
        md += "❌ **Statut**: Non conforme - Actions urgentes requises\n\n"

    # Recommandations
    md += "## Recommandations Prioritaires\n\n"
    for i, rec in enumerate(report['recommendations'], 1):
        md += f"### {i}. [{rec['priority']}] {rec['action']}\n\n"
        md += f"**Base légale**: {rec['article']}\n\n"

    # Détails des fichiers à problèmes
    md += "## Fichiers Nécessitant Attention\n\n"
    for file_result in report['files']:
        if file_result['issues']:
            md += f"### {file_result['file']}\n\n"
            for issue in file_result['issues']:
                md += f"- **[{issue['severity']}]** {issue['message']}\n"
            md += "\n"

    # Articles RGPD concernés
    md += """## Articles RGPD Concernés

### Article 6 - Licéité du traitement
- Obtenir le consentement explicite des utilisateurs
- Documenter la base légale de chaque traitement

### Article 17 - Droit à l'effacement
- Implémenter mécanisme de suppression des données
- Supprimer données dans délai raisonnable (30 jours)

### Article 20 - Droit à la portabilité
- Permettre export des données dans format structuré
- Format machine-readable (JSON, CSV)

### Article 30 - Registre des activités
- Documenter tous les traitements de données
- Tenir à jour registre des activités

### Article 32 - Sécurité du traitement
- Chiffrement des données au repos et en transit
- Pseudonymisation/anonymisation
- Tests réguliers des mesures de sécurité

### Article 33 - Notification des violations
- Procédure de notification sous 72h
- Documentation des violations

## Prochaines Étapes

1. Corriger issues critiques immédiatement
2. Planifier corrections haute priorité (7 jours)
3. Mettre en place audit log GDPR
4. Former l'équipe sur bonnes pratiques RGPD
5. Audit externe annuel recommandé
"""

    return md

if __name__ == "__main__":
    import sys
    sys.exit(main())
