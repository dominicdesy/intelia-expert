#!/usr/bin/env python3
"""
Script to add version headers to all production files
Version: 1.4.1
Last modified: 2025-10-26
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Configuration
APP_VERSION = "1.4.1"
TODAY = datetime.now().strftime("%Y-%m-%d")

# Paths to process
INCLUDE_PATHS = [
    "backend/app",
    "llm",
    "frontend",
]

# Exclusions
EXCLUDE_PATTERNS = [
    "*/tests/*",
    "*/test/*",
    "*test*.py",
    "*spec*.py",
    "*test*.ts",
    "*test*.tsx",
    "*spec*.ts",
    "*spec*.tsx",
    "*/node_modules/*",
    "*/__pycache__/*",
    "*.pyc",
]

# File extensions to process
PYTHON_EXTENSIONS = [".py"]
TYPESCRIPT_EXTENSIONS = [".ts", ".tsx", ".jsx"]

# Version header templates
PYTHON_HEADER = '''"""
{description}
Version: {version}
Last modified: {date}
"""

'''

TYPESCRIPT_HEADER = '''/**
 * {description}
 * Version: {version}
 * Last modified: {date}
 */

'''

def should_exclude(filepath: str) -> bool:
    """Check if file should be excluded"""
    for pattern in EXCLUDE_PATTERNS:
        if Path(filepath).match(pattern):
            return True
    return False


def has_version_header(content: str) -> bool:
    """Check if file already has a version header"""
    # Look for "Version: X.X.X" in first 20 lines
    lines = content.split('\n')[:20]
    for line in lines:
        if re.search(r'Version:\s*\d+\.\d+\.\d+', line):
            return True
    return False


def extract_description(filepath: str, content: str) -> str:
    """Extract or generate module description"""
    lines = content.split('\n')

    # Check for existing docstring/comment
    for i, line in enumerate(lines[:10]):
        # Python docstring
        if '"""' in line or "'''" in line:
            if i + 1 < len(lines):
                desc_line = lines[i + 1].strip()
                if desc_line and not desc_line.startswith(('"""', "'''")):
                    return desc_line

        # TypeScript comment
        if line.strip().startswith('*') and not line.strip().startswith('*/'):
            desc = line.strip().lstrip('*').strip()
            if desc and len(desc) > 5:
                return desc

    # Generate from filename
    filename = Path(filepath).stem
    # Convert snake_case or camelCase to Title Case
    desc = filename.replace('_', ' ').replace('-', ' ').title()
    return desc


def add_version_header_python(filepath: str, content: str) -> str:
    """Add version header to Python file"""
    lines = content.split('\n')

    # Find where to insert (after shebang and encoding)
    insert_index = 0

    # Skip shebang
    if lines and lines[0].startswith('#!'):
        insert_index = 1

    # Skip encoding declaration
    if insert_index < len(lines) and re.match(r'#.*coding[:=]', lines[insert_index]):
        insert_index += 1

    # Skip empty lines
    while insert_index < len(lines) and not lines[insert_index].strip():
        insert_index += 1

    # Extract description
    description = extract_description(filepath, content)

    # Create header
    header = PYTHON_HEADER.format(
        description=description,
        version=APP_VERSION,
        date=TODAY
    )

    # Insert header
    lines.insert(insert_index, header.rstrip())

    return '\n'.join(lines)


def add_version_header_typescript(filepath: str, content: str) -> str:
    """Add version header to TypeScript/React file"""
    lines = content.split('\n')

    # Find where to insert (top of file)
    insert_index = 0

    # Skip empty lines
    while insert_index < len(lines) and not lines[insert_index].strip():
        insert_index += 1

    # Extract description
    description = extract_description(filepath, content)

    # Create header
    header = TYPESCRIPT_HEADER.format(
        description=description,
        version=APP_VERSION,
        date=TODAY
    )

    # Insert header
    lines.insert(insert_index, header.rstrip())

    return '\n'.join(lines)


def process_file(filepath: str) -> Tuple[bool, str]:
    """
    Process a single file
    Returns: (modified, message)
    """
    try:
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if already has version
        if has_version_header(content):
            return False, "Already has version header"

        # Determine file type and add header
        ext = Path(filepath).suffix

        if ext in PYTHON_EXTENSIONS:
            new_content = add_version_header_python(filepath, content)
        elif ext in TYPESCRIPT_EXTENSIONS:
            new_content = add_version_header_typescript(filepath, content)
        else:
            return False, f"Unsupported extension: {ext}"

        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True, "Version header added"

    except Exception as e:
        return False, f"Error: {str(e)}"


def find_files() -> List[str]:
    """Find all files to process"""
    files = []

    for base_path in INCLUDE_PATHS:
        if not os.path.exists(base_path):
            print(f"Warning: Path does not exist: {base_path}")
            continue

        for root, dirs, filenames in os.walk(base_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

            for filename in filenames:
                filepath = os.path.join(root, filename)

                # Check extension
                ext = Path(filename).suffix
                if ext not in PYTHON_EXTENSIONS + TYPESCRIPT_EXTENSIONS:
                    continue

                # Check exclusions
                if should_exclude(filepath):
                    continue

                files.append(filepath)

    return sorted(files)


def main():
    """Main execution"""
    print("=" * 80)
    print("Adding Version Headers to Production Files")
    print("=" * 80)
    print(f"App Version: {APP_VERSION}")
    print(f"Date: {TODAY}")
    print()

    # Find files
    print("Finding files...")
    files = find_files()
    print(f"Found {len(files)} files to process")
    print()

    # Process files
    modified_count = 0
    skipped_count = 0
    error_count = 0

    results = {
        'modified': [],
        'skipped': [],
        'errors': []
    }

    for i, filepath in enumerate(files, 1):
        # Progress indicator
        if i % 50 == 0:
            print(f"Progress: {i}/{len(files)} files processed...")

        modified, message = process_file(filepath)

        if modified:
            modified_count += 1
            results['modified'].append(filepath)
        elif "Error" in message:
            error_count += 1
            results['errors'].append((filepath, message))
        else:
            skipped_count += 1
            results['skipped'].append((filepath, message))

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(files)}")
    print(f"Modified: {modified_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    print()

    # Show errors if any
    if results['errors']:
        print("ERRORS:")
        for filepath, error in results['errors'][:10]:  # Show first 10
            print(f"  - {filepath}: {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
        print()

    # Show sample of modified files
    if results['modified']:
        print("MODIFIED FILES (sample):")
        for filepath in results['modified'][:20]:  # Show first 20
            print(f"  ✓ {filepath}")
        if len(results['modified']) > 20:
            print(f"  ... and {len(results['modified']) - 20} more files")
        print()

    # Write detailed report
    report_file = "version_update_report.txt"
    with open(report_file, 'w') as f:
        f.write(f"Version Update Report\n")
        f.write(f"Date: {TODAY}\n")
        f.write(f"App Version: {APP_VERSION}\n")
        f.write(f"\n")
        f.write(f"Modified: {modified_count}\n")
        f.write(f"Skipped: {skipped_count}\n")
        f.write(f"Errors: {error_count}\n")
        f.write(f"\n")

        f.write(f"Modified Files:\n")
        for filepath in results['modified']:
            f.write(f"  {filepath}\n")

        f.write(f"\nSkipped Files:\n")
        for filepath, reason in results['skipped']:
            f.write(f"  {filepath}: {reason}\n")

        if results['errors']:
            f.write(f"\nErrors:\n")
            for filepath, error in results['errors']:
                f.write(f"  {filepath}: {error}\n")

    print(f"Detailed report saved to: {report_file}")
    print()
    print("Done!")


if __name__ == '__main__':
    main()
