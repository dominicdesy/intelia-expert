"""
Script to add source_file to hybrid_retriever.py metadata dicts
"""
import re

file_path = "C:/Software_Development/intelia-cognito/rag/retrieval/hybrid_retriever.py"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to match: "source": obj.properties.get("source", ""),
# We want to add source_file right after it
pattern = r'("source": obj\.properties\.get\("source", ""\),)'
replacement = r'\1\n                        "source_file": obj.properties.get("source_file", ""),  # For image retrieval'

# Apply replacement (will match all 3 occurrences)
new_content, count = re.subn(pattern, replacement, content)

if count > 0:
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✓ Applied fix to {count} location(s) in hybrid_retriever.py")
    print(f"  Added 'source_file' to metadata dict")
else:
    print("✗ Pattern not found - file may already be fixed or have different format")

print(f"\nModifications complete!")
