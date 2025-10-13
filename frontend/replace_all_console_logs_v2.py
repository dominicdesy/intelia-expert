#!/usr/bin/env python3
"""
Replace ALL console.log/error/warn/debug with secureLog equivalents
across the entire frontend codebase - Windows compatible version.
"""

import re
from pathlib import Path

# Base directory
FRONTEND_DIR = Path(__file__).parent

# Files to skip
SKIP_FILES = [
    "secureLogger.ts",
    "node_modules",
    ".next",
    "dist",
    "build",
]

def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped"""
    file_str = str(file_path)
    return any(skip in file_str for skip in SKIP_FILES)

def find_ts_files() -> list[Path]:
    """Find all TypeScript files"""
    files = []
    for pattern in ['**/*.ts', '**/*.tsx']:
        files.extend(FRONTEND_DIR.glob(pattern))

    return [f for f in files if f.is_file() and not should_skip_file(f)]

def has_console_statements(content: str) -> bool:
    """Check if content has console statements"""
    return bool(re.search(r'console\.(log|error|warn|debug)\(', content))

def has_secure_log_import(content: str) -> bool:
    """Check if file already imports secureLog"""
    return 'from "@/lib/utils/secureLogger"' in content or \
           "from '@/lib/utils/secureLogger'" in content

def add_secure_log_import(content: str) -> str:
    """Add secureLog import after the last import statement"""

    if has_secure_log_import(content):
        return content

    lines = content.split('\n')
    last_import_index = -1

    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('} from'):
            last_import_index = i

    if last_import_index == -1:
        use_directive_index = -1
        for i, line in enumerate(lines):
            if '"use client"' in line or "'use client'" in line or \
               '"use server"' in line or "'use server'" in line:
                use_directive_index = i
                break

        if use_directive_index != -1:
            lines.insert(use_directive_index + 1, '')
            lines.insert(use_directive_index + 2, 'import { secureLog } from "@/lib/utils/secureLogger";')
        else:
            lines.insert(0, 'import { secureLog } from "@/lib/utils/secureLogger";')
            lines.insert(1, '')
    else:
        lines.insert(last_import_index + 1, 'import { secureLog } from "@/lib/utils/secureLogger";')

    return '\n'.join(lines)

def replace_console_statements(content: str) -> tuple[str, int]:
    """Replace console.* with secureLog.*"""
    replacements = [
        (r'console\.log\(', 'secureLog.log('),
        (r'console\.error\(', 'secureLog.error('),
        (r'console\.warn\(', 'secureLog.warn('),
        (r'console\.debug\(', 'secureLog.debug('),
    ]

    total_replacements = 0
    for pattern, replacement in replacements:
        content, count = re.subn(pattern, replacement, content)
        total_replacements += count

    return content, total_replacements

def process_file(file_path: Path) -> dict:
    """Process a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        if not has_console_statements(original_content):
            return {'skipped': True, 'reason': 'no_console'}

        content = add_secure_log_import(original_content)
        content, replacement_count = replace_console_statements(content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                'success': True,
                'replacements': replacement_count,
                'file': str(file_path.relative_to(FRONTEND_DIR))
            }
        else:
            return {'skipped': True, 'reason': 'no_changes'}

    except Exception as e:
        return {'error': True, 'message': str(e), 'file': str(file_path.relative_to(FRONTEND_DIR))}

def main():
    print("=" * 70)
    print("SECURE LOGGING MIGRATION - FRONTEND")
    print("=" * 70)
    print()

    print("[1/3] Finding TypeScript files...")
    all_files = find_ts_files()
    print(f"      Found {len(all_files)} TypeScript files")

    # Filter to only files with console statements
    files_to_process = []
    for f in all_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                if has_console_statements(file.read()):
                    files_to_process.append(f)
        except:
            pass

    print(f"      {len(files_to_process)} files contain console statements")
    print()

    print("[2/3] Processing files...")
    results = {'success': [], 'skipped': [], 'errors': []}
    total_replacements = 0

    for file_path in files_to_process:
        result = process_file(file_path)

        if result.get('success'):
            results['success'].append(result)
            total_replacements += result['replacements']
            print(f"  OK {result['file']}: {result['replacements']} replacements")
        elif result.get('error'):
            results['errors'].append(result)
            print(f"  ERROR {result.get('file', 'unknown')}: {result['message']}")

    print()
    print("[3/3] Summary")
    print("=" * 70)
    print(f"  Files processed:  {len(results['success'])}")
    print(f"  Files skipped:    {len(results['skipped'])}")
    print(f"  Files with errors: {len(results['errors'])}")
    print(f"  Total replacements: {total_replacements}")
    print()

    if results['success']:
        print("Successfully processed files:")
        for r in results['success'][:15]:
            print(f"  - {r['file']} ({r['replacements']} replacements)")
        if len(results['success']) > 15:
            print(f"  ... and {len(results['success']) - 15} more files")

    print()
    print("=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
