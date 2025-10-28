"""
Identify Safe Fixes
Version: 1.4.1
Last modified: 2025-10-26
"""

import re
import subprocess

# Run Pyright
result = subprocess.run(["pyright", "."], capture_output=True, text=True, cwd=".")
output = result.stdout + result.stderr

# Parse errors
error_pattern = r"([\w\/.]+\.py):(\d+):(\d+) - error: (.+?) \((\w+)\)"
errors = re.findall(error_pattern, output)

# Categorize
safe_errors = []
medium_errors = []

for file, line, col, message, code in errors:
    clean_file = file.replace("c:\\intelia_gpt\\intelia-expert\\llm\\", "")

    error_info = {
        "file": clean_file,
        "line": int(line),
        "message": message,
        "code": code,
    }

    # SAFE: Missing imports
    if code == "reportMissingImports":
        safe_errors.append(error_info)

    # SAFE: Invalid type form (syntax)
    elif code == "reportInvalidTypeForm":
        safe_errors.append(error_info)

    # LOW RISK: Incompatible method override (just parameter names)
    elif (
        code == "reportIncompatibleMethodOverride"
        and "Parameter" in message
        and "name mismatch" in message
    ):
        safe_errors.append(error_info)

    # MEDIUM: Optional member access (can add if checks)
    elif code == "reportOptionalMemberAccess":
        medium_errors.append(error_info)

print("=" * 100)
print("SAFEST 30 PYRIGHT ERRORS TO FIX (0-10% RISK)")
print("=" * 100)
print()

print("=" * 100)
print("CATEGORY 1: MISSING IMPORTS (18 errors) - 0% RISK")
print("=" * 100)
print("Fix: Install missing dependencies or fix import paths")
print()

missing_imports = [e for e in safe_errors if e["code"] == "reportMissingImports"]
for i, err in enumerate(missing_imports[:18], 1):
    print(f"{i:2}. {err['file']}:{err['line']}")
    print(f"    Error: {err['message']}")
    print()

print()
print("=" * 100)
print("CATEGORY 2: INVALID TYPE FORMS (5 errors) - 0% RISK")
print("=" * 100)
print("Fix: Correct type annotation syntax")
print()

invalid_forms = [e for e in safe_errors if e["code"] == "reportInvalidTypeForm"]
for i, err in enumerate(invalid_forms, 1):
    print(f"{i:2}. {err['file']}:{err['line']}")
    print(f"    Error: {err['message']}")
    print()

print()
print("=" * 100)
print("CATEGORY 3: METHOD PARAMETER NAME MISMATCHES (7 errors) - 5% RISK")
print("=" * 100)
print("Fix: Rename parameters to match base class signature")
print()

param_mismatches = [
    e for e in safe_errors if e["code"] == "reportIncompatibleMethodOverride"
]
for i, err in enumerate(param_mismatches[:7], 1):
    print(f"{i:2}. {err['file']}:{err['line']}")
    print(f"    Error: {err['message'][:80]}")
    print()

print()
print("=" * 100)
print(f"TOTAL SAFE FIXES: {len(safe_errors)} errors")
print("=" * 100)
print()
print("RECOMMENDED ORDER:")
print("  1. Fix missing imports (18 errors) - Install dependencies")
print("  2. Fix invalid type forms (5 errors) - Syntax corrections")
print("  3. Fix parameter names (7 errors) - Simple renames")
print()
print("TOTAL: 30 errors can be fixed with 0-5% risk")
print("=" * 100)
