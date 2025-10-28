#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test HuggingFace API Access for Llama 3.1 8B Instruct
"""
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from huggingface_hub import InferenceClient

def test_huggingface_access():
    """Test HuggingFace API access with detailed error reporting"""

    # Get API key from environment
    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not api_key:
        print("❌ ERROR: HUGGINGFACE_API_KEY not set")
        print("Set it with: export HUGGINGFACE_API_KEY='hf_...'")
        sys.exit(1)

    print(f"✓ API Key found: {api_key[:10]}...")
    print()

    model = "meta-llama/Llama-3.1-8B-Instruct"

    print(f"Testing model: {model}")
    print("=" * 60)
    print()

    # Test 1: Initialize client
    print("Test 1: Initializing InferenceClient...")
    try:
        client = InferenceClient(model=model, token=api_key)
        print("✓ Client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        sys.exit(1)

    print()

    # Test 2: Try chat_completion
    print("Test 2: Testing chat_completion method...")
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=10,
        )
        print("✓ chat_completion works!")
        print(f"Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ chat_completion failed: {e}")
        print()
        print("Details:")
        print(f"  - Error type: {type(e).__name__}")
        print(f"  - Error message: {str(e)}")

        # Check if it's a 404
        if "404" in str(e):
            print()
            print("🔍 404 Error Analysis:")
            print("  Possible causes:")
            print("  1. Model requires Pro subscription for Serverless Inference")
            print("  2. API endpoint changed")
            print("  3. Model temporarily unavailable")
            print()
            print("  Trying text_generation fallback...")

            # Test 3: Try text_generation fallback
            try:
                prompt = "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\nSay hello<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
                response = client.text_generation(
                    prompt=prompt,
                    max_new_tokens=10,
                )
                print("  ✓ text_generation works!")
                print(f"  Response: {response}")
            except Exception as e2:
                print(f"  ❌ text_generation also failed: {e2}")
                print()
                print("🚨 Both methods failed. This suggests:")
                print("   - Model is not available on Serverless Inference API")
                print("   - You may need HuggingFace Pro subscription")
                print("   - Or use Inference Endpoints (dedicated)")

    print()
    print("=" * 60)
    print("Test complete!")

if __name__ == "__main__":
    test_huggingface_access()
