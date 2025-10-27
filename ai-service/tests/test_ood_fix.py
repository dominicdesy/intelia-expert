#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test OOD detector avec la question sur processing plants
"""

import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] .env loaded from {env_path}")
else:
    print(f"[WARN] .env not found at {env_path}")

# Add llm to path
sys.path.insert(0, str(Path(__file__).parent))

from security.llm_ood_detector import LLMOODDetector  # noqa: E402

# Initialize detector
detector = LLMOODDetector()

# Test cases
test_queries = [
    "What are the main data points processing plants need from farms to plan efficiently?",
    "Quelles données les usines d'abattage ont-elles besoin de recevoir des fermes?",
    "What is the capital of France?",  # OUT-OF-DOMAIN control
    "How to cook chicken parmesan?",  # OUT-OF-DOMAIN control
    "What is the target FCR for Ross 308 at 35 days?",  # IN-DOMAIN control
]

print("=" * 80)
print("Testing OOD Detector with Processing Plant Questions")
print("=" * 80)

for i, query in enumerate(test_queries, 1):
    print(f"\n[{i}/{len(test_queries)}] Query: {query}")

    is_in_domain, confidence, details = detector.is_in_domain(query)

    status = "[IN-DOMAIN]" if is_in_domain else "[OUT-OF-DOMAIN]"
    print(f"   Result: {status} (confidence: {confidence:.2f})")
    print(f"   Response: {details.get('llm_response', 'N/A')}")

print("\n" + "=" * 80)
print("[OK] Test completed")
print("=" * 80)
