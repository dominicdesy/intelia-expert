#!/usr/bin/env python3
"""
Test version header script on a few files
Version: 1.4.1
Last modified: 2025-10-26
"""

import os
import shutil
from add_version_headers import process_file

# Test files
TEST_FILES = [
    "backend/app/api/v1/admin.py",
    "backend/app/api/v1/auth.py",
    "backend/app/api/v1/billing.py",
    "frontend/app/about/page.tsx",
    "frontend/app/admin/statistics/page.tsx",
]

def main():
    print("=" * 80)
    print("Testing Version Header Script on Sample Files")
    print("=" * 80)
    print()

    # Create backups
    backups = {}
    for filepath in TEST_FILES:
        if os.path.exists(filepath):
            backup_path = filepath + ".backup"
            shutil.copy2(filepath, backup_path)
            backups[filepath] = backup_path
            print(f"[OK] Backed up: {filepath}")
        else:
            print(f"[!!] Not found: {filepath}")

    print()
    print("Processing files...")
    print()

    # Process files
    for filepath in TEST_FILES:
        if not os.path.exists(filepath):
            continue

        print(f"Processing: {filepath}")
        modified, message = process_file(filepath)

        if modified:
            print(f"  [OK] {message}")
            # Show first few lines
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:15]
                print("  Preview:")
                for i, line in enumerate(lines, 1):
                    print(f"    {i:2d} | {line.rstrip()}")
        else:
            print(f"  [SKIP] {message}")

        print()

    print("=" * 80)
    print("Test completed!")
    print()
    print("Options:")
    print("  1. Keep changes (delete backups)")
    print("  2. Restore backups (undo changes)")
    print()

    choice = input("Your choice (1/2): ").strip()

    if choice == "2":
        print("\nRestoring backups...")
        for filepath, backup_path in backups.items():
            shutil.copy2(backup_path, filepath)
            print(f"  [OK] Restored: {filepath}")

    # Clean up backups
    print("\nCleaning up backup files...")
    for backup_path in backups.values():
        if os.path.exists(backup_path):
            os.remove(backup_path)
            print(f"  [OK] Deleted: {backup_path}")

    print("\nDone!")


if __name__ == '__main__':
    main()
