"""
Apply frontend image changes - simplified version without emojis
"""
import time
import re

def read_file_with_retry(filepath, max_retries=3):
    for attempt in range(max_retries):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1} reading {filepath}...")
                time.sleep(0.5)
            else:
                raise e

def write_file_with_retry(filepath, content, max_retries=3):
    for attempt in range(max_retries):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1} writing {filepath}...")
                time.sleep(0.5)
            else:
                raise e

print("Applying frontend image changes...\n")

# ============================================================================
# 1. Update types/index.ts
# ============================================================================
print("[1/5] Updating types/index.ts...")
types_path = r'C:\Software_Development\intelia-cognito\frontend\types\index.ts'

try:
    types_content = read_file_with_retry(types_path)

    if 'images?: Array<{' in types_content:
        print("   SKIP: Already has images field\n")
    else:
        old_pattern = r'export type EndEvent = \{\s+type: "end";\s+total_time\?: number;\s+confidence\?: number;\s+documents_used\?: number;\s+source\?: string;\s*\};'

        new_text = '''export type EndEvent = {
  type: "end";
  total_time?: number;
  confidence?: number;
  documents_used?: number;
  source?: string;
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
  }>;
};'''

        types_content = re.sub(old_pattern, new_text, types_content)
        write_file_with_retry(types_path, types_content)
        print("   DONE: Added images to EndEvent\n")

except Exception as e:
    print(f"   ERROR: {e}\n")

# ============================================================================
# 2. Update apiService.ts interface
# ============================================================================
print("[2/5] Updating apiService.ts interface...")
api_path = r'C:\Software_Development\intelia-cognito\frontend\app\chat\services\apiService.ts'

try:
    api_content = read_file_with_retry(api_path)

    if re.search(r'interface EnhancedAIResponse[\s\S]{0,500}images\?:', api_content):
        print("   SKIP: Interface already has images field\n")
    else:
        old_interface = r'(// NOUVELLES PROPRIÉTÉS AGENT\s+agent_metadata\?: AgentMetadata;\s*)\}'

        new_interface = r'''\1
  // Images associated with response
  images?: Array<{
    image_id: string;
    image_url: string;
    caption?: string;
    image_type?: string;
  }>;
}'''

        api_content = re.sub(old_interface, new_interface, api_content)
        write_file_with_retry(api_path, api_content)
        print("   DONE: Added images to EnhancedAIResponse interface\n")

except Exception as e:
    print(f"   ERROR: {e}\n")

# ============================================================================
# 3. Update apiService.ts END event handler
# ============================================================================
print("[3/5] Updating apiService.ts END event handler...")

try:
    api_content = read_file_with_retry(api_path)

    if '(agentMetadata as any).images = endEvent.images' in api_content:
        print("   SKIP: Already captures images from END event\n")
    else:
        old_end_handler = r'(if \(endEvent\.source\) \{\s+agentMetadata\.response_source = endEvent\.source;\s+secureLog\.log\(`\[apiService\] Source capturée: \$\{endEvent\.source\}`\);\s+\})\s+break;'

        new_end_handler = r'''\1
              // Capture images from END event
              if (endEvent.images && Array.isArray(endEvent.images)) {
                (agentMetadata as any).images = endEvent.images;
                secureLog.log(`[apiService] ${endEvent.images.length} images retrieved`);
              }
              break;'''

        api_content = re.sub(old_end_handler, new_end_handler, api_content)
        write_file_with_retry(api_path, api_content)
        print("   DONE: Added image capture to END event handler\n")

except Exception as e:
    print(f"   ERROR: {e}\n")

# ============================================================================
# 4. Update apiService.ts response return
# ============================================================================
print("[4/5] Updating apiService.ts response return...")

try:
    api_content = read_file_with_retry(api_path)

    if re.search(r'const processedResponse: EnhancedAIResponse[\s\S]{0,300}images:', api_content):
        print("   SKIP: Response already includes images\n")
    else:
        old_response = r'(const processedResponse: EnhancedAIResponse = \{\s+response: finalResponse,\s+conversation_id: finalConversationId,\s+)agentMetadata,(\s+\};)'

        new_response = r'''\1agentMetadata,
      // Include images from agent metadata if available
      images: (agentMetadata as any).images || [],\2'''

        api_content = re.sub(old_response, new_response, api_content)
        write_file_with_retry(api_path, api_content)
        print("   DONE: Added images to response return\n")

except Exception as e:
    print(f"   ERROR: {e}\n")

# ============================================================================
# 5. Update page.tsx bot message
# ============================================================================
print("[5/5] Updating page.tsx bot message...")
page_path = r'C:\Software_Development\intelia-cognito\frontend\app\chat\page.tsx'

try:
    page_content = read_file_with_retry(page_path)

    if 'imageUrls: aiResponse.images' in page_content:
        print("   SKIP: Bot message already includes imageUrls\n")
    else:
        pattern = r'(const botMessage: Message = \{[\s\S]{0,800}timestamp: new Date\(\),)'

        if re.search(pattern, page_content):
            replacement = r'''\1
          // Add images from API response
          imageUrls: aiResponse.images?.map(img => img.image_url) || [],'''

            page_content = re.sub(pattern, replacement, page_content, count=1)
            write_file_with_retry(page_path, page_content)
            print("   DONE: Added imageUrls to bot message\n")
        else:
            print("   ERROR: Bot message pattern not found\n")

except Exception as e:
    print(f"   ERROR: {e}\n")

print("=" * 60)
print("Frontend image implementation complete!")
print("=" * 60)
