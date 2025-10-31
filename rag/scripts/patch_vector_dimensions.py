#!/usr/bin/env python3
"""
Patch retriever_core.py to read WEAVIATE_VECTOR_DIMENSIONS from environment
"""

import re

file_path = "../retrieval/retriever_core.py"

print("🔧 Patching retriever_core.py to use WEAVIATE_VECTOR_DIMENSIONS...")

# Read file
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

original_content = content

# 1. Add 'import os' if not present
if "import os" not in content:
    content = content.replace(
        "import logging\nimport re",
        "import logging\nimport os\nimport re"
    )
    print("✅ Added 'import os'")
else:
    print("✓  'import os' already present")

# 2. Replace hardcoded 3072 in __init__
pattern1 = r'self\.working_vector_dimension = \(\s*3072\s*#.*?\)'
replacement1 = '''self.working_vector_dimension = int(
            os.getenv("WEAVIATE_VECTOR_DIMENSIONS", "3072")
        )  # text-embedding-3-large native = 3072 (configurable via env)'''

if re.search(pattern1, content, re.DOTALL):
    content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)
    print("✅ Replaced hardcoded dimension in __init__")
else:
    print("⚠️  Pattern 1 not found (might be already patched)")

# 3. Replace hardcoded 3072 in fallback (ligne ~144)
pattern2 = r'self\.working_vector_dimension = 3072\s*#\s*UPDATED: Fallback to 3072'
replacement2 = '''self.working_vector_dimension = int(
                os.getenv("WEAVIATE_VECTOR_DIMENSIONS", "3072")
            )  # Fallback from env'''

if re.search(pattern2, content):
    content = re.sub(pattern2, replacement2, content)
    print("✅ Replaced hardcoded dimension in fallback")
else:
    print("⚠️  Pattern 2 not found (might be already patched)")

# Check if changes were made
if content != original_content:
    # Write back
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ File patched successfully!")
    print(f"📁 Modified: {file_path}")
else:
    print("\n✓  No changes needed - file already patched or patterns not found")

print("\n📊 Next step: Set WEAVIATE_VECTOR_DIMENSIONS=3072 in Digital Ocean env vars")
