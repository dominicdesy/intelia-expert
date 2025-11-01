"""
Fix ImageRetriever to handle Document objects (not just dicts)
"""

file_path = "C:/Software_Development/intelia-cognito/rag/retrieval/image_retriever.py"

# Read
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the source_file extraction logic
old_code = """        # Extract unique source files from chunks
        source_files = set()
        for chunk in chunks:
            source_file = chunk.get("source_file") or chunk.get("metadata", {}).get("source_file")
            if source_file:
                source_files.add(source_file)"""

new_code = """        # Extract unique source files from chunks
        source_files = set()
        for chunk in chunks:
            # Handle both dict and Document objects
            if isinstance(chunk, dict):
                source_file = chunk.get("source_file") or chunk.get("metadata", {}).get("source_file")
            else:
                # Document object - use .get() method which checks metadata
                source_file = chunk.get("source_file") if hasattr(chunk, 'get') else None

            if source_file:
                source_files.add(source_file)"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Fixed image_retriever.py to handle Document objects")
else:
    print("[ERROR] Could not find code to replace - may already be fixed")
