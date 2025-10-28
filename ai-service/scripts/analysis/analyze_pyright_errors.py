"""
Analyze Pyright Errors
Version: 1.4.1
Last modified: 2025-10-26
"""

import re
import subprocess
from collections import defaultdict

# Run Pyright and capture output
result = subprocess.run(["pyright", "."], capture_output=True, text=True, cwd=".")
output = result.stdout + result.stderr

# Parse errors
error_pattern = r"([\w\/.]+\.py):(\d+):(\d+) - error: (.+?) \((\w+)\)"
errors = re.findall(error_pattern, output)

# Categorize by error type
by_type = defaultdict(list)
by_file = defaultdict(list)

for file, line, col, message, code in errors:
    clean_file = file.replace("c:\\intelia_gpt\\intelia-expert\\llm\\", "")
    by_type[code].append(
        {"file": clean_file, "line": line, "message": message, "code": code}
    )
    by_file[file].append(code)

# Print summary
print("=" * 80)
print("PYRIGHT ERROR ANALYSIS - CATEGORIZED BY RISK")
print("=" * 80)
print()

# Define risk categories
SAFE_FIXES = {
    "reportMissingImports": "SAFE - Missing imports (install dependencies)",
    "reportInvalidTypeForm": "SAFE - Type annotation syntax errors",
}

LOW_RISK = {
    "reportIncompatibleMethodOverride": "LOW RISK - Method signature mismatches",
    "reportAttributeAccessIssue": "LOW RISK - Unknown attribute access",
}

MEDIUM_RISK = {
    "reportOptionalMemberAccess": "MEDIUM RISK - Accessing attributes on Optional types",
    "reportPossiblyUnboundVariable": "MEDIUM RISK - Variables possibly not initialized",
    "reportArgumentType": "MEDIUM RISK - Argument type mismatches",
}

HIGH_RISK = {
    "reportReturnType": "HIGH RISK - Return type mismatches (behavior change)",
    "reportCallIssue": "HIGH RISK - Function call issues (may crash)",
}

print("SAFE TO FIX (0% risk):")
print("-" * 80)
for code, description in SAFE_FIXES.items():
    count = len(by_type.get(code, []))
    if count > 0:
        print(f"  {code:40} {count:3} errors - {description}")
print()

print("LOW RISK (10-20% risk):")
print("-" * 80)
for code, description in LOW_RISK.items():
    count = len(by_type.get(code, []))
    if count > 0:
        print(f"  {code:40} {count:3} errors - {description}")
print()

print("MEDIUM RISK (30-50% risk):")
print("-" * 80)
for code, description in MEDIUM_RISK.items():
    count = len(by_type.get(code, []))
    if count > 0:
        print(f"  {code:40} {count:3} errors - {description}")
print()

print("HIGH RISK (60-80% risk):")
print("-" * 80)
for code, description in HIGH_RISK.items():
    count = len(by_type.get(code, []))
    if count > 0:
        print(f"  {code:40} {count:3} errors - {description}")
print()

# Show top 10 files with most errors
print()
print("=" * 80)
print("TOP 10 FILES WITH MOST ERRORS:")
print("=" * 80)
sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]
for file, codes in sorted_files:
    clean_file = file.replace("c:\\intelia_gpt\\intelia-expert\\llm\\", "")
    print(f"  {len(codes):3} errors - {clean_file}")

# Total
print()
print("=" * 80)
print(f"TOTAL ERRORS: {len(errors)}")
print("=" * 80)
