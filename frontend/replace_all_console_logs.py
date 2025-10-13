#!/usr/bin/env python3
"""
Replace ALL console.log/error/warn/debug with secureLog equivalents
across the entire frontend codebase.

This script:
1. Finds all .ts and .tsx files that contain console statements
2. Adds secureLog import if not present
3. Replaces all console.* calls with secureLog.*
4. Skips files that already use secureLog or are the secureLogger itself
"""

import re
import subprocess
from pathlib import Path

# Base directory
FRONTEND_DIR = Path(__file__).parent

# Files to skip
SKIP_FILES = [
    "secureLogger.ts",  # The logger itself
    "node_modules",     # Third-party code
]

def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped"""
    file_str = str(file_path)
    return any(skip in file_str for skip in SKIP_FILES)

def has_secure_log_import(content: str) -> bool:
    """Check if file already imports secureLog"""
    return 'from "@/lib/utils/secureLogger"' in content or \
           "from '@/lib/utils/secureLogger'" in content

def add_secure_log_import(content: str, file_path: Path) -> str:
    """Add secureLog import after the last import statement"""

    # Skip if already has import
    if has_secure_log_import(content):
        return content

    lines = content.split('\n')

    # Find the last import statement
    last_import_index = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('} from'):
            last_import_index = i

    # If no imports found, add at the beginning after "use client" or "use server"
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
        # Insert after the last import
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

def find_files_with_console() -> list[Path]:
    """Find all TS/TSX files that contain console statements"""
    try:
        # Use ripgrep to find files
        result = subprocess.run(
            ['rg', '--type', 'ts', '-l', r'console\.(log|error|warn|debug)\('],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            files = [FRONTEND_DIR / line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return [f for f in files if f.exists() and not should_skip_file(f)]
        else:
            print("No files found with console statements")
            return []
    except FileNotFoundError:
        print("Error: ripgrep (rg) not found. Please install ripgrep.")
        return []

def process_file(file_path: Path) -> dict:
    """Process a single file"""
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Check if already fully using secureLog
        if 'console.log(' not in original_content and \
           'console.error(' not in original_content and \
           'console.warn(' not in original_content and \
           'console.debug(' not in original_content:
            return {'skipped': True, 'reason': 'no_console_statements'}

        # Add import if needed
        content = add_secure_log_import(original_content, file_path)

        # Replace console statements
        content, replacement_count = replace_console_statements(content)

        # Write back only if changes were made
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
        return {'error': True, 'message': str(e), 'file': str(file_path)}

def main():
    print("=" * 70)
    print("SECURE LOGGING MIGRATION - FRONTEND")
    print("=" * 70)
    print()

    # Find files
    print("[1/3] Finding files with console statements...")
    files = find_files_with_console()
    print(f"      Found {len(files)} files to process")
    print()

    # Process files
    print("[2/3] Processing files...")
    results = {
        'success': [],
        'skipped': [],
        'errors': []
    }

    total_replacements = 0

    for file_path in files:
        result = process_file(file_path)

        if result.get('success'):
            results['success'].append(result)
            total_replacements += result['replacements']
            print(f"  ✅ {result['file']}: {result['replacements']} replacements")
        elif result.get('skipped'):
            results['skipped'].append(result)
        elif result.get('error'):
            results['errors'].append(result)
            print(f"  ❌ {result.get('file', 'unknown')}: {result['message']}")

    print()
    print("[3/3] Summary")
    print("=" * 70)
    print(f"  📝 Files processed:  {len(results['success'])}")
    print(f"  ⏭️  Files skipped:    {len(results['skipped'])}")
    print(f"  ❌ Files with errors: {len(results['errors'])}")
    print(f"  🔄 Total replacements: {total_replacements}")
    print()

    if results['success']:
        print("Successfully processed files:")
        for r in results['success'][:10]:  # Show first 10
            print(f"  - {r['file']} ({r['replacements']} replacements)")
        if len(results['success']) > 10:
            print(f"  ... and {len(results['success']) - 10} more files")

    print()
    print("=" * 70)
    print("✅ MIGRATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
