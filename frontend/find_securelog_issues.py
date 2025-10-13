#!/usr/bin/env python3
"""Script pour trouver tous les appels secureLog.log() avec plus de 2 arguments"""

import re
import os
from pathlib import Path

def count_arguments(call_content):
    """Compte le nombre d'arguments dans un appel de fonction en tenant compte des parenthèses/accolades"""
    depth_paren = 0
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    in_template = False
    string_char = None
    arg_count = 1 if call_content.strip() else 0

    i = 0
    while i < len(call_content):
        char = call_content[i]

        # Gestion des template literals
        if char == '`' and (i == 0 or call_content[i-1] != '\\'):
            if not in_string:
                in_template = not in_template

        # Gestion des strings normales
        elif char in ('"', "'") and not in_template and (i == 0 or call_content[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None

        # Si on n'est pas dans une string ou template
        elif not in_string and not in_template:
            if char == '(':
                depth_paren += 1
            elif char == ')':
                depth_paren -= 1
            elif char == '{':
                depth_brace += 1
            elif char == '}':
                depth_brace -= 1
            elif char == '[':
                depth_bracket += 1
            elif char == ']':
                depth_bracket -= 1
            elif char == ',' and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
                arg_count += 1

        i += 1

    return arg_count

def find_securelog_calls(file_path):
    """Trouve tous les appels secureLog.log() dans un fichier"""
    issues = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern pour trouver les appels secureLog.log(...)
        pattern = r'secureLog\.log\s*\('

        for match in re.finditer(pattern, content):
            start_pos = match.end()

            # Trouver la fin de l'appel
            depth = 1
            end_pos = start_pos
            in_string = False
            in_template = False
            string_char = None

            while end_pos < len(content) and depth > 0:
                char = content[end_pos]

                # Gestion des template literals
                if char == '`' and (end_pos == 0 or content[end_pos-1] != '\\'):
                    if not in_string:
                        in_template = not in_template

                # Gestion des strings
                elif char in ('"', "'") and not in_template and (end_pos == 0 or content[end_pos-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
                        string_char = None

                # Compter les parenthèses seulement hors des strings
                elif not in_string and not in_template:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1

                end_pos += 1

            # Extraire le contenu entre parenthèses
            call_content = content[start_pos:end_pos-1]

            # Compter les arguments
            arg_count = count_arguments(call_content)

            if arg_count > 2:
                # Trouver le numéro de ligne
                line_num = content[:match.start()].count('\n') + 1

                # Extraire un contexte
                lines = content.split('\n')
                context_line = lines[line_num - 1].strip()

                issues.append({
                    'file': file_path,
                    'line': line_num,
                    'args': arg_count,
                    'context': context_line[:100]
                })

    except Exception as e:
        print(f"Erreur lors de la lecture de {file_path}: {e}")

    return issues

def scan_directory(root_dir):
    """Scanne tous les fichiers .ts et .tsx"""
    all_issues = []

    for ext in ['*.ts', '*.tsx']:
        for file_path in Path(root_dir).rglob(ext):
            # Ignorer node_modules et .next
            if 'node_modules' in str(file_path) or '.next' in str(file_path):
                continue

            issues = find_securelog_calls(str(file_path))
            all_issues.extend(issues)

    return all_issues

if __name__ == '__main__':
    print("=" * 80)
    print("Recherche des appels secureLog.log() avec plus de 2 arguments")
    print("=" * 80)
    print()

    frontend_dir = Path(__file__).parent
    issues = scan_directory(frontend_dir)

    if not issues:
        print("[OK] AUCUN PROBLEME TROUVE!")
        print("Tous les appels secureLog.log() ont 2 arguments ou moins.")
    else:
        print(f"[ERREUR] {len(issues)} PROBLEME(S) TROUVE(S):\n")

        for issue in issues:
            rel_path = os.path.relpath(issue['file'], frontend_dir)
            print(f"Fichier: {rel_path}:{issue['line']}")
            print(f"Arguments: {issue['args']}")
            print(f"Code: {issue['context']}")
            print()

    print("=" * 80)
    print(f"Scan terminé - {len(issues)} problème(s) trouvé(s)")
    print("=" * 80)
