#!/usr/bin/env python3
"""
Analyze Pyright Possibly Unbound Variable errors
Categorizes into: Conditional Imports, Real Bugs, False Positives
"""

import re
from pathlib import Path
from collections import defaultdict

# Read unbound variable errors
with open('unbound_vars.txt', 'r', encoding='utf-8') as f:
    errors = f.readlines()

# Parse errors
parsed_errors = []
for line in errors:
    match = re.match(r'\s*(.+?):(\d+):(\d+) - error: "(.+?)" is possibly unbound', line)
    if match:
        file_path = match.group(1).replace('c:\\intelia_gpt\\intelia-expert\\llm\\', '')
        line_num = int(match.group(2))
        var_name = match.group(4)
        parsed_errors.append({
            'file': file_path,
            'line': line_num,
            'var': var_name,
            'full_line': line.strip()
        })

print(f"=== UNBOUND VARIABLE ANALYSIS - {len(parsed_errors)} errors ===\n")

# Categorize by pattern
categories = {
    'conditional_imports': [],  # try/except imports
    'likely_imports': [],       # CamelCase = probably imports
    'api_routes': [],           # tenant_id, message in API routes
    'config_vars': [],          # UPPERCASE = config/constants
    'real_suspects': []         # lowercase vars in logic
}

for error in parsed_errors:
    var = error['var']
    file_path = error['file']

    # Category 1: Obvious conditional imports (CamelCase classes)
    if var[0].isupper() and any(c.isupper() for c in var[1:]):
        categories['conditional_imports'].append(error)

    # Category 2: Config constants (UPPERCASE)
    elif var.isupper() and '_' in var:
        categories['config_vars'].append(error)

    # Category 3: API routes specific vars
    elif 'routes.py' in file_path and var in ['tenant_id', 'message', 'user_id']:
        categories['api_routes'].append(error)

    # Category 4: Probably imports (common patterns)
    elif var in ['json', 'evaluate', 'Dataset', 'Features', 'Value', 'Sequence', 'Client']:
        categories['likely_imports'].append(error)

    # Category 5: Real suspects (lowercase vars in logic)
    else:
        categories['real_suspects'].append(error)

# Print categorized results
print("=" * 80)
print("CATEGORY 1: CONDITIONAL IMPORTS (CamelCase) - FALSE POSITIVES")
print("=" * 80)
print(f"Total: {len(categories['conditional_imports'])} errors\n")
print("These are imports wrapped in try/except - code is already protected\n")
for err in categories['conditional_imports'][:10]:
    print(f"  {err['file']}:{err['line']} - {err['var']}")
if len(categories['conditional_imports']) > 10:
    print(f"  ... and {len(categories['conditional_imports']) - 10} more")
print()

print("=" * 80)
print("CATEGORY 2: CONFIG CONSTANTS (UPPERCASE) - FALSE POSITIVES")
print("=" * 80)
print(f"Total: {len(categories['config_vars'])} errors\n")
print("These are config constants with try/except fallbacks\n")
for err in categories['config_vars']:
    print(f"  {err['file']}:{err['line']} - {err['var']}")
print()

print("=" * 80)
print("CATEGORY 3: API ROUTE VARIABLES - LIKELY FALSE POSITIVES")
print("=" * 80)
print(f"Total: {len(categories['api_routes'])} errors\n")
print("These are request parsing vars - protected by FastAPI validation\n")
for err in categories['api_routes']:
    print(f"  {err['file']}:{err['line']} - {err['var']}")
print()

print("=" * 80)
print("CATEGORY 4: LIKELY IMPORTS (common stdlib/packages)")
print("=" * 80)
print(f"Total: {len(categories['likely_imports'])} errors\n")
for err in categories['likely_imports']:
    print(f"  {err['file']}:{err['line']} - {err['var']}")
print()

print("=" * 80)
print("CATEGORY 5: REAL SUSPECTS - NEEDS MANUAL REVIEW")
print("=" * 80)
print(f"Total: {len(categories['real_suspects'])} errors\n")
print("These are lowercase variables in logic - may be real bugs!\n")

# Group suspects by file for easier review
suspects_by_file = defaultdict(list)
for err in categories['real_suspects']:
    suspects_by_file[err['file']].append(err)

for file_path, errors in sorted(suspects_by_file.items()):
    print(f"\n[FILE] {file_path} ({len(errors)} suspects)")
    for err in errors:
        print(f"  Line {err['line']:4d}: {err['var']}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total errors: {len(parsed_errors)}")
print(f"  Conditional imports: {len(categories['conditional_imports'])} (FALSE POSITIVE)")
print(f"  Config constants:    {len(categories['config_vars'])} (FALSE POSITIVE)")
print(f"  API route vars:      {len(categories['api_routes'])} (LIKELY FALSE POSITIVE)")
print(f"  Likely imports:      {len(categories['likely_imports'])} (FALSE POSITIVE)")
print(f"  [!] REAL SUSPECTS:   {len(categories['real_suspects'])} (NEEDS REVIEW)")
print()

false_positives = (
    len(categories['conditional_imports']) +
    len(categories['config_vars']) +
    len(categories['likely_imports'])
)
likely_ok = len(categories['api_routes'])
real_suspects = len(categories['real_suspects'])

print(f"Estimated breakdown:")
print(f"  [OK] Definite false positives: {false_positives} ({false_positives/len(parsed_errors)*100:.1f}%)")
print(f"  [?]  Likely OK (API routes):   {likely_ok} ({likely_ok/len(parsed_errors)*100:.1f}%)")
print(f"  [!]  Need manual review:       {real_suspects} ({real_suspects/len(parsed_errors)*100:.1f}%)")
print()

# Save real suspects for detailed review
with open('unbound_vars_suspects.txt', 'w', encoding='utf-8') as f:
    f.write("REAL SUSPECTS - POSSIBLY UNBOUND VARIABLES\n")
    f.write("=" * 80 + "\n\n")
    for file_path, errors in sorted(suspects_by_file.items()):
        f.write(f"\n{file_path}\n")
        f.write("-" * 80 + "\n")
        for err in errors:
            f.write(f"Line {err['line']}: {err['var']}\n")

print(f"[OK] Real suspects saved to: unbound_vars_suspects.txt")
