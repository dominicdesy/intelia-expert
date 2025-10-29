#!/usr/bin/env python3
"""
# Trouver le début de l'appel
Version: 1.4.1
Last modified: 2025-10-26
"""
"""Script pour corriger automatiquement tous les appels secureLog.log() avec trop d'arguments"""

import re
import os
from pathlib import Path

def extract_call_with_context(content, match_pos):
    """Extrait l'appel complet de secureLog.log() avec son contexte"""
    # Trouver le début de l'appel
    start_pos = content.find('(', match_pos) + 1

    # Trouver la fin de l'appel en comptant les parenthèses
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

    return content[start_pos:end_pos-1], start_pos, end_pos

def parse_arguments(call_content):
    """Parse les arguments en tenant compte des parenthèses/accolades/strings"""
    args = []
    current_arg = []
    depth_paren = 0
    depth_brace = 0
    depth_bracket = 0
    in_string = False
    in_template = False
    string_char = None

    i = 0
    while i < len(call_content):
        char = call_content[i]

        # Gestion des template literals
        if char == '`' and (i == 0 or call_content[i-1] != '\\'):
            if not in_string:
                in_template = not in_template
            current_arg.append(char)

        # Gestion des strings
        elif char in ('"', "'") and not in_template and (i == 0 or call_content[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None
            current_arg.append(char)

        # Si on n'est pas dans une string ou template
        elif not in_string and not in_template:
            if char == '(':
                depth_paren += 1
                current_arg.append(char)
            elif char == ')':
                depth_paren -= 1
                current_arg.append(char)
            elif char == '{':
                depth_brace += 1
                current_arg.append(char)
            elif char == '}':
                depth_brace -= 1
                current_arg.append(char)
            elif char == '[':
                depth_bracket += 1
                current_arg.append(char)
            elif char == ']':
                depth_bracket -= 1
                current_arg.append(char)
            elif char == ',' and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
                # Nouvelle argument
                args.append(''.join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
        else:
            current_arg.append(char)

        i += 1

    # Ajouter le dernier argument
    if current_arg:
        args.append(''.join(current_arg).strip())

    return args

def fix_securelog_call(args):
    """Convertit les multiples arguments en 2 arguments max"""
    if len(args) <= 2:
        return ', '.join(args)

    # Premier argument (généralement le message)
    first_arg = args[0]

    # Si le premier argument est déjà un template literal, on continue à l'étendre
    if first_arg.startswith('`') and first_arg.endswith('`'):
        # Enlever les backticks
        message = first_arg[1:-1]

        # Ajouter les autres arguments dans le template literal
        for arg in args[1:]:
            # Si l'argument est une variable simple, on l'intègre avec ${}
            arg_clean = arg.strip()
            if arg_clean and not arg_clean.startswith('"') and not arg_clean.startswith("'"):
                message += f' ${{{arg_clean}}}'
            else:
                # Si c'est une string, on enlève les guillemets
                if arg_clean.startswith('"') and arg_clean.endswith('"'):
                    message += ' ' + arg_clean[1:-1]
                elif arg_clean.startswith("'") and arg_clean.endswith("'"):
                    message += ' ' + arg_clean[1:-1]
                else:
                    message += ' ' + arg_clean

        return f'`{message}`'

    # Si le premier argument est une string normale, on la convertit en template literal
    elif first_arg.startswith('"') or first_arg.startswith("'"):
        quote_char = first_arg[0]
        message = first_arg[1:-1] if first_arg.endswith(quote_char) else first_arg[1:]

        # Ajouter les autres arguments
        for arg in args[1:]:
            arg_clean = arg.strip()
            if arg_clean and not arg_clean.startswith('"') and not arg_clean.startswith("'"):
                message += f' ${{{arg_clean}}}'
            else:
                if arg_clean.startswith('"') and arg_clean.endswith('"'):
                    message += ' ' + arg_clean[1:-1]
                elif arg_clean.startswith("'") and arg_clean.endswith("'"):
                    message += ' ' + arg_clean[1:-1]
                else:
                    message += ' ' + arg_clean

        return f'`{message}`'

    # Fallback: créer un template literal avec tous les arguments
    else:
        message_parts = [first_arg]
        for arg in args[1:]:
            arg_clean = arg.strip()
            if arg_clean:
                message_parts.append(f'${{{arg_clean}}}')

        return '`' + ' '.join(message_parts) + '`'

def fix_file(file_path):
    """Corrige tous les appels secureLog.log() dans un fichier"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content
        modifications = 0

        # Trouver tous les appels secureLog.log
        pattern = r'secureLog\.log\s*\('
        matches = list(re.finditer(pattern, content))

        # Traiter les appels en ordre inverse pour ne pas invalider les positions
        for match in reversed(matches):
            call_content, start_pos, end_pos = extract_call_with_context(content, match.start())
            args = parse_arguments(call_content)

            if len(args) > 2:
                # Correction nécessaire
                new_call = fix_securelog_call(args)

                # Remplacer dans le contenu
                content = content[:start_pos] + new_call + content[end_pos-1:]
                modifications += 1

        if modifications > 0:
            # Sauvegarder le fichier
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)

            return modifications
        else:
            return 0

    except Exception as e:
        print(f"ERREUR lors du traitement de {file_path}: {e}")
        return 0

def scan_and_fix_directory(root_dir):
    """Scanne et corrige tous les fichiers .ts et .tsx"""
    total_modifications = 0
    files_modified = 0

    for ext in ['*.ts', '*.tsx']:
        for file_path in Path(root_dir).rglob(ext):
            # Ignorer node_modules et .next
            if 'node_modules' in str(file_path) or '.next' in str(file_path):
                continue

            mods = fix_file(str(file_path))
            if mods > 0:
                rel_path = os.path.relpath(str(file_path), root_dir)
                print(f"  {rel_path}: {mods} correction(s)")
                total_modifications += mods
                files_modified += 1

    return total_modifications, files_modified

if __name__ == '__main__':
    print("=" * 80)
    print("Correction automatique des appels secureLog.log()")
    print("=" * 80)
    print()

    frontend_dir = Path(__file__).parent

    print("Correction en cours...")
    total_mods, files_count = scan_and_fix_directory(frontend_dir)

    print()
    print("=" * 80)
    print(f"TERMINE: {total_mods} correction(s) dans {files_count} fichier(s)")
    print("=" * 80)
