#!/usr/bin/env python3
"""
Script to update all imports after directory reorganization
"""

import os
import re
from pathlib import Path

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # PostgreSQL moves
    "from retrieval.postgresql.retriever import": "from retrieval.postgresql.retriever import",
    "from retrieval.postgresql.query_builder import": "from retrieval.postgresql.query_builder import",
    "from retrieval.postgresql.normalizer import": "from retrieval.postgresql.normalizer import",
    "from retrieval.postgresql.models import": "from retrieval.postgresql.models import",
    "from retrieval.postgresql.config import": "from retrieval.postgresql.config import",
    "from retrieval.postgresql.router import": "from retrieval.postgresql.router import",
    "from retrieval.postgresql.temporal import": "from retrieval.postgresql.temporal import",
    "from retrieval.postgresql.main import": "from retrieval.postgresql.main import",
    "from retrieval.postgresql.main import": "from retrieval.postgresql.main import",
    "import retrieval.postgresql.main": "import retrieval.postgresql.main",

    # Weaviate moves
    "from retrieval.weaviate.core import": "from retrieval.weaviate.core import",
    "from retrieval.weaviate.core import": "from retrieval.weaviate.core import",
    "import retrieval.weaviate.core": "import retrieval.weaviate.core",

    # Comparison handler move
    "from core.handlers.comparison_handler import": "from core.handlers.comparison_handler import",
    "from .handlers.comparison_handler import": "from .handlers.comparison_handler import",

    # Core renames (remove rag_ prefix)
    "from core.query_processor import": "from core.query_processor import",
    "from .query_processor import": "from .query_processor import",
    "import core.query_processor": "import core.query_processor",

    "from core.response_generator import": "from core.response_generator import",
    "from .response_generator import": "from .response_generator import",
    "import core.response_generator": "import core.response_generator",

    "from core.json_system import": "from core.json_system import",
    "from .json_system import": "from .json_system import",
    "import core.json_system": "import core.json_system",
}

def update_file_imports(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = []

        for old_import, new_import in IMPORT_MAPPINGS.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                changes_made.append(f"{old_import} -> {new_import}")

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Updated {file_path}")
            for change in changes_made:
                print(f"   - {change}")
            return True

        return False

    except Exception as e:
        print(f"[ERROR] Error updating {file_path}: {e}")
        return False

def main():
    """Main function to update all Python files"""
    base_dir = Path(__file__).parent.parent
    python_files = list(base_dir.rglob("*.py"))

    # Exclude certain directories
    exclude_patterns = ["venv", "__pycache__", ".git", "docs"]
    python_files = [
        f for f in python_files
        if not any(pattern in str(f) for pattern in exclude_patterns)
    ]

    print(f"Found {len(python_files)} Python files to check")
    print("=" * 60)

    updated_count = 0
    for file_path in python_files:
        if update_file_imports(file_path):
            updated_count += 1

    print("=" * 60)
    print(f"[OK] Updated {updated_count} files")
    print(f"[OK] Checked {len(python_files)} files total")

if __name__ == "__main__":
    main()
