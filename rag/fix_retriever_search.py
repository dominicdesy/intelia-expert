"""
Add source_file to fallback retriever in retriever_search.py
"""
import re

file_path = "C:/Software_Development/intelia-cognito/rag/retrieval/retriever_search.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the fallback retriever section
old_pattern = r'                    "title": properties\.get\("title", ""\),\n                    "source": properties\.get\("source", ""\),\n                    "geneticLine": properties\.get\("geneticLine", ""\),'

new_replacement = '''                    "title": properties.get("title", ""),
                    "source": properties.get("source", ""),
                    "source_file": properties.get("source_file", ""),  # For image retrieval
                    "geneticLine": properties.get("geneticLine", ""),'''

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_replacement, content)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Added source_file to fallback retriever")
else:
    print("[SKIP] Pattern not found or already modified")
