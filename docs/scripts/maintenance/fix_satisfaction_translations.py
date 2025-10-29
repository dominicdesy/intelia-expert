#!/usr/bin/env python3
"""
Fix satisfaction thank you translations - convert arrays to numbered keys
"""

import json
import os
from pathlib import Path

def fix_translations(file_path):
    """Convert satisfactionThankYou arrays to numbered keys"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if satisfactionThankYou exists and needs fixing
    if 'chat' in data and 'satisfactionThankYou' in data['chat']:
        thank_you = data['chat']['satisfactionThankYou']

        # Convert each category from array to numbered keys
        for category in ['satisfied', 'neutral', 'unsatisfied']:
            if category in thank_you and isinstance(thank_you[category], list):
                messages = thank_you[category]
                # Convert to numbered keys
                thank_you[category] = {
                    str(i): msg for i, msg in enumerate(messages)
                }

        # Add default fallback if not present
        if 'default' not in thank_you:
            thank_you['default'] = "Thank you for your feedback!"

        # Save back
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Fixed: {file_path}")
        return True
    else:
        print(f"[SKIP] Skipped: {file_path} (no satisfactionThankYou found)")
        return False

def main():
    """Fix all translation files"""
    frontend_dir = Path(__file__).parent / 'frontend'
    locales_dir = frontend_dir / 'public' / 'locales'

    if not locales_dir.exists():
        print(f"[ERROR] Error: {locales_dir} not found")
        return

    print(f"[INFO] Fixing translation files in {locales_dir}")
    print()

    fixed_count = 0
    for json_file in locales_dir.glob('*.json'):
        if fix_translations(json_file):
            fixed_count += 1

    print()
    print(f"[DONE] Done! Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
