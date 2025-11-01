"""
Add ImageRetriever call to standard_handler.py
"""
import time

file_path = "C:/Software_Development/intelia-cognito/rag/core/handlers/standard_handler.py"

# Wait a moment to ensure file is not being modified
time.sleep(0.5)

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the target section
old_code = """                result.metadata["top_k_used"] = weaviate_top_k
                result.metadata["processing_time"] = time.time() - start_time
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters

                return result"""

new_code = """                result.metadata["top_k_used"] = weaviate_top_k
                result.metadata["processing_time"] = time.time() - start_time
                result.metadata["language_used"] = language
                result.metadata["filters_applied"] = filters

                # 🖼️ Retrieve associated images
                if result.context_docs and self.weaviate_core and self.weaviate_core.weaviate_client:
                    try:
                        from retrieval.image_retriever import ImageRetriever
                        image_retriever = ImageRetriever(self.weaviate_core.weaviate_client)
                        result.images = image_retriever.get_images_for_chunks(result.context_docs, max_images_per_chunk=3)
                        if result.images:
                            logger.info(f"🖼️ Retrieved {len(result.images)} images for query")
                    except Exception as e:
                        logger.warning(f"🖼️ Error retrieving images: {e}")
                        result.images = []

                return result"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Added ImageRetriever call to handler")
else:
    print("[ERROR] Could not find target code - may already be modified")
    print("\nSearching for similar code...")
    if "result.images = image_retriever.get_images_for_chunks" in content:
        print("[INFO] ImageRetriever call already appears to be in the file")
    else:
        print("[ERROR] Target code not found and ImageRetriever call not present")
