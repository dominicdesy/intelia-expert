"""
Add imageUrls to bot messages in page.tsx
"""
import re
import time

def read_with_retry(path, retries=5):
    for i in range(retries):
        try:
            time.sleep(0.3)  # Wait a bit
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  Retry {i+1}...")

def write_with_retry(path, content, retries=5):
    for i in range(retries):
        try:
            time.sleep(0.3)  # Wait a bit
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  Retry {i+1}...")

path = r'C:\Software_Development\intelia-cognito\frontend\app\chat\page.tsx'

print("Fixing page.tsx to add images to bot messages...\n")

# Read file
content = read_with_retry(path)

# Check if already done
if 'imageUrls: response.images' in content or 'imageUrls: aiResponse.images' in content:
    print("SKIP: page.tsx already has imageUrls from response.images\n")
    exit(0)

modified = False

# Fix 1: Add imageUrls to updateMessage call at line 1306
# This is where the final message is updated with conversation_id and response_versions
pattern1 = r'(\s+updateMessage\(assistantId, \{\s+conversation_id: response\.conversation_id,)'

if re.search(pattern1, content):
    replacement1 = r'''\1
			// Add images from API response
			imageUrls: response.images?.map(img => img.image_url) || [],'''

    new_content = re.sub(pattern1, replacement1, content, count=1)
    if new_content != content:
        content = new_content
        modified = True
        print("DONE: Added imageUrls to updateMessage call")
    else:
        print("SKIP: Pattern 1 not modified")
else:
    print("WARNING: Pattern 1 not found")

# Fix 2: Also add imageUrls to vision response message creation (line 1176)
pattern2 = r'(addMessage\(\{\s+id: assistantId,\s+content: response\.response,\s+isUser: false,\s+timestamp: new Date\(\),\s+conversation_id: response\.conversation_id,)'

if re.search(pattern2, content):
    replacement2 = r'''\1
			// Add images from vision response if available
			imageUrls: response.images?.map(img => img.image_url) || [],'''

    new_content = re.sub(pattern2, replacement2, content, count=1)
    if new_content != content:
        content = new_content
        modified = True
        print("DONE: Added imageUrls to vision addMessage call")
    else:
        print("SKIP: Pattern 2 not modified")
else:
    print("WARNING: Pattern 2 not found")

if modified:
    write_with_retry(path, content)
    print("\n" + "=" * 60)
    print("SUCCESS: page.tsx updated with imageUrls!")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("WARNING: No modifications made - patterns may have changed")
    print("=" * 60)
