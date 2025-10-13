#!/usr/bin/env python3
"""Replace console.log with secureLog in apiService.ts"""

import re
from pathlib import Path

FILE_PATH = Path(__file__).parent / "app" / "chat" / "services" / "apiService.ts"

def replace_console_logs(content):
    """Replace console.log/error/warn with secureLog equivalents"""

    # Simple replacements
    replacements = [
        (r'console\.log\(', 'secureLog.log('),
        (r'console\.error\(', 'secureLog.error('),
        (r'console\.warn\(', 'secureLog.warn('),
        (r'console\.debug\(', 'secureLog.debug('),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    return content

# Read file
with open(FILE_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"[BEFORE] File size: {len(content)} characters")

# Count console.log before
console_count_before = len(re.findall(r'console\.(log|error|warn|debug)\(', content))
print(f"[BEFORE] console.* calls: {console_count_before}")

# Replace
new_content = replace_console_logs(content)

# Count after
secureLog_count_after = len(re.findall(r'secureLog\.(log|error|warn|debug)\(', content))
console_count_after = len(re.findall(r'console\.(log|error|warn|debug)\(', new_content))
print(f"[AFTER] console.* calls: {console_count_after}")
print(f"[AFTER] secureLog.* calls: {secureLog_count_after}")

# Write back
with open(FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"[OK] File updated: {FILE_PATH.name}")
print(f"[OK] Replaced {console_count_before - console_count_after} console calls")
