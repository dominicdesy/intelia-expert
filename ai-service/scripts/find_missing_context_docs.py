#!/usr/bin/env python3
"""
Script pour trouver tous les RAGResults manquant context_docs
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Script pour trouver tous les RAGResults manquant context_docs
"""
import os
from pathlib import Path


def find_ragresult_without_context_docs(file_path):
    """Trouve les RAGResults sans context_docs dans un fichier"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.split("\n")

    issues = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Chercher "return RAGResult("
        if "return RAGResult(" in line:
            # Lire les 15 lignes suivantes pour voir si context_docs est présent
            block_lines = [line]
            j = i + 1
            paren_count = line.count("(") - line.count(")")

            while j < len(lines) and (paren_count > 0 or ")" not in lines[j]):
                block_lines.append(lines[j])
                paren_count += lines[j].count("(") - lines[j].count(")")
                j += 1
                if j - i > 20:  # Safety limit
                    break

            # Joindre le bloc
            block = "\n".join(block_lines)

            # Vérifier si context_docs est présent
            if "context_docs" not in block:
                issues.append(
                    {"file": file_path, "line": i + 1, "snippet": block[:200]}
                )

        i += 1

    return issues


def main():
    llm_dir = Path(__file__).parent.parent

    # Fichiers Python à scanner
    python_files = []
    for root, dirs, files in os.walk(llm_dir):
        # Skip venv, __pycache__, etc.
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ["venv", "__pycache__", "logs", "scripts"]
        ]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    all_issues = []
    for file_path in python_files:
        issues = find_ragresult_without_context_docs(file_path)
        all_issues.extend(issues)

    print(f"\nTrouve {len(all_issues)} RAGResults sans context_docs:\n")

    for issue in all_issues:
        print(f"Fichier: {issue['file']}:{issue['line']}")
        print(f"   {issue['snippet'][:150]}...")
        print()

    if not all_issues:
        print("Tous les RAGResults ont context_docs defini!")


if __name__ == "__main__":
    main()
