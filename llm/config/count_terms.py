#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick script to count terms in the centralized config files
"""
import json
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 80)
print("CENTRALIZED CONFIGURATION FILES STATISTICS")
print("=" * 80)

# 1. Veterinary Terms
print("\n1. VETERINARY_TERMS.JSON")
print("-" * 80)
vet_path = os.path.join(CONFIG_DIR, "veterinary_terms.json")
with open(vet_path, "r", encoding="utf-8") as f:
    vet_data = json.load(f)

categories = {}
total_terms = 0
for category_name, category_data in vet_data.items():
    if category_name == "metadata":
        continue
    if isinstance(category_data, dict):
        cat_total = sum(
            len(terms) for terms in category_data.values() if isinstance(terms, list)
        )
        categories[category_name] = cat_total
        total_terms += cat_total

print(f"Total categories: {len(categories)}")
for cat, count in categories.items():
    print(f"  - {cat}: {count} terms")
print(f"\nTotal veterinary terms: {total_terms}")

# 2. Breeds Mapping
print("\n2. BREEDS_MAPPING.JSON")
print("-" * 80)
breeds_path = os.path.join(CONFIG_DIR, "breeds_mapping.json")
with open(breeds_path, "r", encoding="utf-8") as f:
    breeds_data = json.load(f)

breed_counts = {}
total_breeds = 0
total_aliases = 0
for species in ["broilers", "layers", "breeders"]:
    if species in breeds_data:
        count = len(breeds_data[species])
        breed_counts[species] = count
        total_breeds += count

        # Count aliases
        for breed_id, breed_info in breeds_data[species].items():
            if "aliases" in breed_info:
                total_aliases += len(breed_info["aliases"])

print(f"Total species categories: {len(breed_counts)}")
for species, count in breed_counts.items():
    print(f"  - {species}: {count} breeds")
print(f"\nTotal breeds: {total_breeds}")
print(f"Total aliases: {total_aliases}")

# 3. Metrics Normalization
print("\n3. METRICS_NORMALIZATION.JSON")
print("-" * 80)
metrics_path = os.path.join(CONFIG_DIR, "metrics_normalization.json")
with open(metrics_path, "r", encoding="utf-8") as f:
    metrics_data = json.load(f)

metrics = [k for k in metrics_data.keys() if k != "metadata"]
total_translations = 0
languages = set()

for metric_id in metrics:
    if "translations" in metrics_data[metric_id]:
        trans = metrics_data[metric_id]["translations"]
        total_translations += sum(len(terms) for terms in trans.values())
        languages.update(trans.keys())

print(f"Total metrics: {len(metrics)}")
print(f"Languages supported: {len(languages)}")
print(f"  Languages: {', '.join(sorted(languages))}")
print(f"Total translation variants: {total_translations}")
print("\nMetrics list:")
for i, metric in enumerate(metrics, 1):
    category = metrics_data[metric].get("category", "unknown")
    unit = metrics_data[metric].get("unit", "unknown")
    print(f"  {i:2d}. {metric:30s} [{category:12s}] ({unit})")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Veterinary terms:     {total_terms:4d} terms")
print(f"Breeds:               {total_breeds:4d} breeds with {total_aliases} aliases")
print(f"Metrics:              {len(metrics):4d} metrics in {len(languages)} languages")
print(f"Total configuration:  {total_terms + total_breeds + len(metrics)} items")
print("=" * 80)
