"""Test Intelia product detection regex"""
import re

query = "Comment voir les températures dans le nano ?"
query_lower = query.lower()

# Current pattern from entity_extractor.py
keyword = "nano"
pattern = r'\b(?:le|la|l\'|du|de la|dans le|avec le|sur le)?\s*' + re.escape(keyword) + r'\b'

print(f"Query: {query}")
print(f"Query lower: {query_lower}")
print(f"Pattern: {pattern}")
print(f"Match: {re.search(pattern, query_lower, re.IGNORECASE)}")

# Try to find what matches
matches = re.findall(pattern, query_lower, re.IGNORECASE)
print(f"All matches: {matches}")

# Test with simpler pattern
simple_pattern = r'\bnano\b'
print(f"\nSimple pattern '{simple_pattern}':")
print(f"Match: {re.search(simple_pattern, query_lower, re.IGNORECASE)}")
