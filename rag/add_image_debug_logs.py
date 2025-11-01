"""Add debug logs for image serialization in chat_handlers.py"""
import time

def read_with_retry(path, retries=5):
    for i in range(retries):
        try:
            time.sleep(0.2)
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"Retry {i+1}...")

def write_with_retry(path, content, retries=5):
    for i in range(retries):
        try:
            time.sleep(0.2)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"Retry {i+1}...")

path = r'C:\Software_Development\intelia-cognito\rag\api\chat_handlers.py'

print("Adding image debug logs...")
content = read_with_retry(path)

# Find and replace the serialization section
old_code = '''            serialized_data = safe_serialize_for_json(end_data)
            logger.info(f"🔍 END event full data: {str(serialized_data)[:500]}")
            yield sse_event(serialized_data)'''

new_code = '''            # 🖼️ Log images before serialization
            logger.info(f"🖼️ END event - images count in end_data: {len(images)}")
            if images:
                logger.info(f"🖼️ END event - first image ID: {images[0].get('image_id', 'N/A')}")

            serialized_data = safe_serialize_for_json(end_data)
            logger.info(f"🔍 END event full data: {str(serialized_data)[:500]}")

            # 🖼️ Log images after serialization
            if 'images' in serialized_data:
                logger.info(f"🖼️ END event SERIALIZED - images key exists: {len(serialized_data['images'])} images")
            else:
                logger.warning(f"🖼️ END event SERIALIZED - images key MISSING!")

            yield sse_event(serialized_data)'''

if old_code in content:
    content = content.replace(old_code, new_code)
    write_with_retry(path, content)
    print("✅ Debug logs added successfully")
else:
    print("⚠️  Pattern not found - code may have changed")
