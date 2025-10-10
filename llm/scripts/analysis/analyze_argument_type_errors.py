#!/usr/bin/env python3
"""
Analyze Pyright reportArgumentType errors
Extract and categorize by pattern and risk level
"""

import re
from pathlib import Path
from collections import defaultdict

# Read Pyright output
with open('pyright_output.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Parse errors - reportArgumentType appears on 3rd line after main error
parsed_errors = []
current_file = None

for i, line in enumerate(lines):
    # Look for lines with "error:" and check if next lines have reportArgumentType
    if ' - error: ' in line and line.startswith('  '):
        # Extract file:line:col using split
        parts = line.strip().split(' - error: ')
        if len(parts) == 2:
            location = parts[0].strip()
            # Parse c:\path\file.py:123:45
            loc_parts = location.rsplit(':', 2)
            if len(loc_parts) == 3:
                file_path = loc_parts[0].replace('c:\\intelia_gpt\\intelia-expert\\llm\\', '').replace('/', '\\')
                try:
                    line_num = int(loc_parts[1])
                    col_num = int(loc_parts[2])

                    # Check next 3 lines for reportArgumentType
                    check_range = min(i + 4, len(lines))
                    for j in range(i, check_range):
                        if 'reportArgumentType' in lines[j]:
                            # Extract the specific error message from line before reportArgumentType
                            error_detail = lines[j].strip()
                            parsed_errors.append({
                                'file': file_path,
                                'line': line_num,
                                'col': col_num,
                                'message': error_detail,
                                'full_line': line.strip()
                            })
                            break
                except (ValueError, IndexError):
                    continue

print(f"=== ARGUMENT TYPE ERRORS ANALYSIS - {len(parsed_errors)} errors ===\n")

# Categorize by pattern
categories = {
    'none_to_type': [],      # "None" is not assignable to "str/int/Dict"
    'wrong_type': [],         # "str" is not assignable to "bool"
    'missing_protocol': [],   # "__abs__" is not present
    'language_detection': [], # LanguageDetectionResult issues
    'other': []
}

for error in parsed_errors:
    msg = error['message']

    if 'LanguageDetectionResult' in msg:
        categories['language_detection'].append(error)
    elif '"None" is not assignable' in msg:
        categories['none_to_type'].append(error)
    elif 'is not present' in msg:
        categories['missing_protocol'].append(error)
    elif 'is not assignable' in msg or 'incompatible with' in msg:
        categories['wrong_type'].append(error)
    else:
        categories['other'].append(error)

# Print categorized results
print("=" * 80)
print("CATEGORY 1: None passed where type expected - HIGH RISK")
print("=" * 80)
print(f"Total: {len(categories['none_to_type'])} errors\n")
print("These are the most dangerous - None causes AttributeError/TypeError at runtime\n")

# Group by file
none_by_file = defaultdict(list)
for err in categories['none_to_type']:
    none_by_file[err['file']].append(err)

for file_path, errors in sorted(none_by_file.items())[:10]:
    print(f"\n[FILE] {file_path} ({len(errors)} errors)")
    for err in errors[:3]:
        print(f"  Line {err['line']:4d}: {err['message'][:80]}")
    if len(errors) > 3:
        print(f"  ... and {len(errors) - 3} more")

if len(none_by_file) > 10:
    print(f"\n... and {len(none_by_file) - 10} more files")

print("\n" + "=" * 80)
print("CATEGORY 2: Wrong type passed - MEDIUM RISK")
print("=" * 80)
print(f"Total: {len(categories['wrong_type'])} errors\n")

wrong_by_file = defaultdict(list)
for err in categories['wrong_type']:
    wrong_by_file[err['file']].append(err)

for file_path, errors in sorted(wrong_by_file.items())[:5]:
    print(f"\n[FILE] {file_path} ({len(errors)} errors)")
    for err in errors[:2]:
        print(f"  Line {err['line']:4d}: {err['message'][:80]}")

print("\n" + "=" * 80)
print("CATEGORY 3: LanguageDetectionResult issues - MEDIUM RISK")
print("=" * 80)
print(f"Total: {len(categories['language_detection'])} errors\n")

for err in categories['language_detection'][:5]:
    print(f"  {err['file']}:{err['line']} - {err['message'][:70]}")

print("\n" + "=" * 80)
print("CATEGORY 4: Missing protocol methods - LOW RISK")
print("=" * 80)
print(f"Total: {len(categories['missing_protocol'])} errors\n")

protocol_by_method = defaultdict(list)
for err in categories['missing_protocol']:
    # Extract method name
    method_match = re.search(r'"(__\w+__)"', err['message'])
    if method_match:
        method = method_match.group(1)
        protocol_by_method[method].append(err)

for method, errors in sorted(protocol_by_method.items()):
    print(f"  {method}: {len(errors)} errors")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total errors: {len(parsed_errors)}")
print(f"  [HIGH] None to type:           {len(categories['none_to_type'])} (REVIEW ALL)")
print(f"  [MED]  Wrong type:              {len(categories['wrong_type'])} (REVIEW SAMPLE)")
print(f"  [MED]  LanguageDetectionResult: {len(categories['language_detection'])} (SPECIFIC ISSUE)")
print(f"  [LOW]  Missing protocol:        {len(categories['missing_protocol'])} (LIKELY OK)")
print(f"  [?]    Other:                   {len(categories['other'])}")
print()

# Calculate risk assessment
high_risk = len(categories['none_to_type'])
med_risk = len(categories['wrong_type']) + len(categories['language_detection'])
low_risk = len(categories['missing_protocol'])

if len(parsed_errors) > 0:
    print(f"Risk Assessment:")
    print(f"  HIGH RISK (None errors):  {high_risk} ({high_risk/len(parsed_errors)*100:.1f}%)")
    print(f"  MEDIUM RISK:              {med_risk} ({med_risk/len(parsed_errors)*100:.1f}%)")
    print(f"  LOW RISK:                 {low_risk} ({low_risk/len(parsed_errors)*100:.1f}%)")
    print()
else:
    print("No errors found - check pyright_output.txt format")
    print()

# Save high-risk errors for manual review
with open('argument_type_high_risk.txt', 'w', encoding='utf-8') as f:
    f.write("HIGH RISK - NONE PASSED WHERE TYPE EXPECTED\n")
    f.write("=" * 80 + "\n\n")

    for file_path, errors in sorted(none_by_file.items()):
        f.write(f"\n{file_path}\n")
        f.write("-" * 80 + "\n")
        for err in errors:
            f.write(f"Line {err['line']}: {err['message']}\n")

print("[OK] High-risk errors saved to: argument_type_high_risk.txt")
print()
print("RECOMMENDATION: Start manual review with 'None to type' errors")
print("These have highest probability of being real bugs (~60-80%)")
