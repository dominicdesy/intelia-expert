#!/usr/bin/env python3
"""
Test Script - Validate HuggingFace Llama Access
Run this to verify your HuggingFace API key and Llama access are working
"""

import os
import sys


def test_huggingface_access():
    """Test HuggingFace API access and Llama model availability"""

    print("=" * 60)
    print("🧪 Intelia LLM - HuggingFace Access Test")
    print("=" * 60)
    print()

    # Check if API key is set
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        print("❌ ERROR: HUGGINGFACE_API_KEY environment variable not set")
        print()
        print("Please set it:")
        print("  export HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxx")
        print()
        return False

    if not api_key.startswith("hf_"):
        print("⚠️  WARNING: API key doesn't start with 'hf_'")
        print("   Are you sure this is a valid HuggingFace token?")
        print()

    print(f"✓ API Key found: {api_key[:10]}...{api_key[-5:]}")
    print()

    # Test huggingface_hub import
    try:
        from huggingface_hub import InferenceClient

        print("✓ huggingface_hub library installed")
    except ImportError:
        print("❌ ERROR: huggingface_hub not installed")
        print()
        print("Install it with:")
        print("  pip install huggingface-hub")
        print()
        return False

    print()
    print("Testing HuggingFace API access...")
    print("-" * 60)

    # Initialize client
    try:
        client = InferenceClient(token=api_key)
        print("✓ InferenceClient initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False

    # Test Llama 3.1 8B access
    model = "meta-llama/Llama-3.1-8B-Instruct"
    print(f"✓ Testing model: {model}")
    print()

    try:
        print("Calling HuggingFace Inference API...")
        print("(This may take 5-10s on first call - cold start)")
        print()

        response = client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": "Hello, respond with just 'Hi'"}],
            max_tokens=10,
        )

        generated_text = response.choices[0].message.content

        print("=" * 60)
        print("✅ SUCCESS! Llama 3.1 8B access validated")
        print("=" * 60)
        print()
        print(f"Model response: {generated_text}")
        print()
        print("✓ Your HuggingFace API key is working correctly")
        print("✓ Meta Llama access has been approved")
        print("✓ Ready to deploy Intelia LLM service!")
        print()
        return True

    except Exception as e:
        error_msg = str(e).lower()

        print("=" * 60)
        print("❌ ACCESS TEST FAILED")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()

        # Provide specific guidance based on error
        if "gated" in error_msg or "access" in error_msg:
            print("🔒 Gated Model - Access Not Granted")
            print()
            print("This means you haven't been approved for Meta Llama yet.")
            print()
            print("Steps to fix:")
            print("1. Go to: https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct")
            print("2. Click 'Agree and access repository'")
            print("3. Accept Meta's terms and conditions")
            print("4. Wait for approval email (usually instant, max 2h)")
            print("5. Re-run this test script")
            print()

        elif "token" in error_msg or "unauthorized" in error_msg:
            print("🔑 Invalid API Token")
            print()
            print("Your HuggingFace token may be invalid or expired.")
            print()
            print("Steps to fix:")
            print("1. Go to: https://huggingface.co/settings/tokens")
            print("2. Create new token with 'Write' permissions")
            print("3. Ensure these permissions are checked:")
            print("   - Read access to gated repos")
            print("   - Make calls to Inference Providers")
            print("4. Copy token and set HUGGINGFACE_API_KEY")
            print()

        elif "rate limit" in error_msg:
            print("⏱️  Rate Limit Exceeded")
            print()
            print("Too many requests. Wait a few minutes and try again.")
            print()

        else:
            print("❓ Unknown Error")
            print()
            print("Please check:")
            print("- Internet connection")
            print("- HuggingFace service status: https://status.huggingface.co")
            print()

        return False


if __name__ == "__main__":
    print()
    success = test_huggingface_access()
    print()

    if success:
        print("🎉 All checks passed! You're ready to deploy.")
        sys.exit(0)
    else:
        print("⚠️  Please fix the issues above before deploying.")
        sys.exit(1)
