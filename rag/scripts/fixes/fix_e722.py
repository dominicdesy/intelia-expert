"""
Fix E722
Version: 1.4.1
Last modified: 2025-10-26
"""

import re
from pathlib import Path

# Files to fix based on ruff output
files_to_fix = {
    "scripts/analyze_unused_files.py": [139, 203],
    "scripts/deep_optimization_analysis.py": [
        130,
        180,
        230,
        272,
        308,
        345,
        394,
        426,
        468,
    ],
    "scripts/final_analysis.py": [53, 86, 114, 136, 164],
    "scripts/trace_query_flow.py": [103],
}

for file_path, line_numbers in files_to_fix.items():
    path = Path(file_path)
    if not path.exists():
        print(f"SKIP: {file_path} (not found)")
        continue

    # Read file
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Fix each bare except (process from end to start to preserve line numbers)
    fixed_count = 0
    for line_num in sorted(line_numbers, reverse=True):
        idx = line_num - 1
        if idx < len(lines):
            original = lines[idx]
            # Match bare except with optional whitespace
            if re.search(r"^\s*except\s*:\s*$", original):
                # Preserve indentation
                indent = re.match(r"^(\s*)", original).group(1)
                lines[idx] = f"{indent}except Exception as e:\n"
                fixed_count += 1
                print(
                    f"FIX {file_path}:{line_num}: {original.strip()} -> {lines[idx].strip()}"
                )
            else:
                print(
                    f"WARN {file_path}:{line_num}: Not a bare except: {original.strip()}"
                )

    # Write back
    if fixed_count > 0:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"OK: Fixed {fixed_count} bare excepts in {file_path}\n")

print("E722 fixes complete!")
