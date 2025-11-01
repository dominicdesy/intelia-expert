"""
Add images field to streaming response
"""
import time

file_path = "C:/Software_Development/intelia-cognito/rag/api/chat_handlers.py"

# Wait a moment
time.sleep(0.5)

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# MODIFICATION 1: Add images extraction after context_docs
old_section_1 = """            if documents_used == 0:
                documents_used = len(context_docs)

            # Event END"""

new_section_1 = """            if documents_used == 0:
                documents_used = len(context_docs)

            # 🖼️ Extraction des images associées
            images = safe_get_attribute(rag_result, "images", [])
            if not isinstance(images, list):
                images = []
            logger.info(f"🖼️ Retrieved {len(images)} images for response")

            # Event END"""

# MODIFICATION 2: Add images to end_data
old_section_2 = """                # 🧠 Chain-of-Thought sections for PostgreSQL storage
                "cot_thinking": cot_thinking,
                "cot_analysis": cot_analysis,
                "has_cot_structure": has_cot_structure,
            }"""

new_section_2 = """                # 🧠 Chain-of-Thought sections for PostgreSQL storage
                "cot_thinking": cot_thinking,
                "cot_analysis": cot_analysis,
                "has_cot_structure": has_cot_structure,
                # 🖼️ Associated images
                "images": images,
            }"""

# Apply modifications
modified = False

if old_section_1 in content:
    content = content.replace(old_section_1, new_section_1)
    print("[OK] Added images extraction section")
    modified = True
else:
    print("[SKIP] Images extraction section already present or code changed")

if old_section_2 in content:
    content = content.replace(old_section_2, new_section_2)
    print("[OK] Added images to end_data")
    modified = True
else:
    print("[SKIP] Images in end_data already present or code changed")

if modified:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("\n[SUCCESS] File updated successfully")
else:
    print("\n[INFO] No modifications needed")
