# -*- coding: utf-8 -*-
"""
test_llm_translation.py - Tests pour LLMTranslator et modules intégrés
"""

import sys
import os
import io

# Fix UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger .env
from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from utils.llm_translator import LLMTranslator
from utils.clarification_helper import ClarificationHelper

print("=" * 80)
print("TEST 1: LLMTranslator - Traduction simple")
print("=" * 80)

translator = LLMTranslator()

test_cases = [
    ("To analyze performance of Ross 308, I need to know:", "fr"),
    ("Please specify **the breed**. For example: Ross 308, Cobb 500.", "fr"),
    ("To help you best, I need details on:", "th"),
    ("Please specify **the age** of the flock. For example: 21 days, 35 days.", "es"),
]

for text_en, lang in test_cases:
    print(f"\n--- EN to {lang.upper()} ---")
    print(f"Input:  {text_en}")
    translation = translator.translate(text_en, lang)
    print(f"Output: {translation}")

print("\n" + "=" * 80)
print("TEST 2: ClarificationHelper - Messages complets")
print("=" * 80)

helper = ClarificationHelper("config/clarification_strategies.json")

# Test 1: Message simple en FR
print("\n--- Test FR: breed + age manquants ---")
message_fr = helper.build_clarification_message(
    missing_fields=["breed", "age"],
    language="fr",
    query="Quel est le poids d'un poulet ?",
    entities={}
)
print(message_fr)

# Test 2: Message EN
print("\n--- Test EN: breed + age manquants ---")
message_en = helper.build_clarification_message(
    missing_fields=["breed", "age"],
    language="en",
    query="What is the weight of a chicken?",
    entities={}
)
print(message_en)

# Test 3: Message TH
print("\n--- Test TH: breed + age manquants ---")
message_th = helper.build_clarification_message(
    missing_fields=["breed", "age"],
    language="th",
    query="น้ำหนักของไก่คืออะไร?",
    entities={}
)
print(message_th)

print("\n" + "=" * 80)
print("TEST 3: Vérification fragments non traduits")
print("=" * 80)

# Vérifier qu'il n'y a pas de fragments anglais dans les messages FR
fragments_to_avoid = ["the breed", "the age", "of the flock", "Please specify", "For example"]

has_untranslated = False
for fragment in fragments_to_avoid:
    if fragment in message_fr:
        print(f"❌ FAIL: Fragment anglais trouvé dans message FR: '{fragment}'")
        has_untranslated = True

if not has_untranslated:
    print("✅ PASS: Aucun fragment anglais détecté dans message FR")

print("\n" + "=" * 80)
print("TESTS TERMINÉS")
print("=" * 80)
