# -*- coding: utf-8 -*-
"""
Automatic RAG Migration Script
Migrates RAG code to use new InteliaKnowledge collection with text-embedding-3-large

Changes:
1. Collection name: InteliaExpertKnowledge → InteliaKnowledge
2. Vector dimension: 1536 → 3072
3. Default embedding model: text-embedding-3-small → text-embedding-3-large
"""

import os
import sys
from pathlib import Path

# Files to update
FILES_TO_UPDATE = [
    "retrieval/retriever_core.py",
    "retrieval/hybrid_retriever.py",
]

# Find and replace patterns
REPLACEMENTS = [
    # Collection name changes
    ('collection_name: str = "InteliaExpertKnowledge"', 'collection_name: str = "InteliaKnowledge"'),
    ('collection_name="InteliaExpertKnowledge"', 'collection_name="InteliaKnowledge"'),

    # Dimension changes - be careful with comments
    ('self.working_vector_dimension = (\n            1536  # CORRIGÉ: OpenAI text-embedding-3-small = 1536\n        )',
     'self.working_vector_dimension = (\n            3072  # UPDATED: OpenAI text-embedding-3-large = 3072\n        )'),

    ('self.working_vector_dimension = 1536  # CORRIGÉ: Fallback sur 1536',
     'self.working_vector_dimension = 3072  # UPDATED: Fallback to 3072'),

    # Test vectors order - prioritize 3072
    ('test_vectors = {\n                1536: [0.1] * 1536,  # text-embedding-3-small (plus probable)\n                3072: [0.1] * 3072,  # text-embedding-3-large',
     'test_vectors = {\n                3072: [0.1] * 3072,  # text-embedding-3-large (default)\n                1536: [0.1] * 1536,  # text-embedding-3-small (fallback)'),
]

def main():
    """Execute migration"""
    print("="*80)
    print("RAG MIGRATION SCRIPT - InteliaKnowledge v2.0")
    print("="*80)
    print()

    rag_base = Path("C:/Software_Development/intelia-cognito/rag")

    if not rag_base.exists():
        print(f"ERROR: RAG directory not found: {rag_base}")
        sys.exit(1)

    print(f"RAG Base: {rag_base}")
    print(f"Files to update: {len(FILES_TO_UPDATE)}")
    print()

    updated_files = []
    failed_files = []

    for relative_path in FILES_TO_UPDATE:
        file_path = rag_base / relative_path

        print(f"Processing: {relative_path}")

        if not file_path.exists():
            print(f"  Status: SKIP (file not found)")
            failed_files.append(relative_path)
            continue

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes_made = 0

            # Apply replacements
            for old_text, new_text in REPLACEMENTS:
                if old_text in content:
                    content = content.replace(old_text, new_text)
                    changes_made += 1
                    print(f"  - Applied replacement: {old_text[:50]}...")

            if changes_made > 0:
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                print(f"  Status: UPDATED ({changes_made} changes)")
                updated_files.append((relative_path, changes_made))
            else:
                print(f"  Status: NO CHANGES NEEDED")

        except Exception as e:
            print(f"  Status: ERROR - {e}")
            failed_files.append(relative_path)

    # Summary
    print()
    print("="*80)
    print("MIGRATION SUMMARY")
    print("="*80)
    print(f"Files processed: {len(FILES_TO_UPDATE)}")
    print(f"Files updated: {len(updated_files)}")
    print(f"Files failed: {len(failed_files)}")
    print()

    if updated_files:
        print("Updated files:")
        for file_path, changes in updated_files:
            print(f"  - {file_path} ({changes} changes)")

    if failed_files:
        print("\nFailed files:")
        for file_path in failed_files:
            print(f"  - {file_path}")

    print()
    print("Next steps:")
    print("  1. Test RAG connection to Weaviate")
    print("  2. Verify embedding dimension (3072)")
    print("  3. Test hybrid search")
    print("  4. Ingest 457 chunks")
    print("="*80)

if __name__ == "__main__":
    main()
