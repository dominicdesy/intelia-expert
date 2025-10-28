"""
Extract and consolidate poultry terminology from PDF glossaries

This script:
1. Extracts text from all PDF glossary files
2. Parses term definitions (format: "Term: definition")
3. Categorizes terms by domain (hatchery, nutrition, health, etc.)
4. Creates a consolidated JSON file with structured terminology
"""

import pdfplumber
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_terms_from_text(text: str) -> List[Tuple[str, str]]:
    """
    Extract term-definition pairs from glossary text

    Format expected: "Term: definition text."

    Returns:
        List of (term, definition) tuples
    """
    terms = []

    # Split by lines and find term definitions
    lines = text.split('\n')
    current_term = None
    current_definition = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line starts with a term (ends with colon)
        # Terms are usually at the start of a line and end with ':'
        if ':' in line and not line.startswith(' '):
            # Save previous term if exists
            if current_term and current_definition:
                definition = ' '.join(current_definition).strip()
                if definition:
                    terms.append((current_term, definition))

            # Extract new term and its definition
            parts = line.split(':', 1)
            if len(parts) == 2:
                current_term = parts[0].strip()
                current_definition = [parts[1].strip()]
        else:
            # Continuation of previous definition
            if current_term:
                current_definition.append(line)

    # Save last term
    if current_term and current_definition:
        definition = ' '.join(current_definition).strip()
        if definition:
            terms.append((current_term, definition))

    return terms


def categorize_term(term: str, definition: str) -> str:
    """
    Categorize a term based on keywords in term and definition

    Categories:
    - hatchery_incubation
    - processing_meat_quality
    - layer_production_egg_quality
    - breeding_genetics
    - nutrition_feed
    - health_disease
    - farm_management_equipment
    - anatomy_physiology
    - general
    """
    text = (term + ' ' + definition).lower()

    # Hatchery & Incubation
    hatchery_keywords = ['incubat', 'hatch', 'egg', 'embryo', 'candling', 'setter',
                         'chick quality', 'pip', 'germinal', 'fertility']
    if any(kw in text for kw in hatchery_keywords):
        # Exclude egg production (that's layer production)
        if not any(kw in text for kw in ['laying', 'layer', 'hen-day', 'production']):
            return 'hatchery_incubation'

    # Processing & Meat Quality
    processing_keywords = ['process', 'slaughter', 'carcass', 'eviscerat', 'scald',
                          'stun', 'debon', 'yield', 'breast', 'meat quality',
                          'ph', 'drip loss', 'woody breast']
    if any(kw in text for kw in processing_keywords):
        return 'processing_meat_quality'

    # Layer Production & Egg Quality
    layer_keywords = ['layer', 'laying', 'hen-day', 'egg production', 'haugh unit',
                     'shell strength', 'yolk color', 'molt', 'point of lay',
                     'blood spot', 'dirty egg']
    if any(kw in text for kw in layer_keywords):
        return 'layer_production_egg_quality'

    # Breeding & Genetics
    breeding_keywords = ['breeding', 'genetic', 'heritab', 'selection', 'inbreed',
                        'crossbreed', 'heterosis', 'pedigree', 'progeny', 'snp',
                        'genomic']
    if any(kw in text for kw in breeding_keywords):
        return 'breeding_genetics'

    # Nutrition & Feed
    nutrition_keywords = ['feed', 'nutrition', 'protein', 'energy', 'amino acid',
                         'lysine', 'methionine', 'vitamin', 'mineral', 'calcium',
                         'phosphorus', 'pellet', 'mash', 'metabolizable']
    if any(kw in text for kw in nutrition_keywords):
        return 'nutrition_feed'

    # Health & Disease
    health_keywords = ['disease', 'virus', 'bacteria', 'infection', 'vaccin',
                      'coccidiosis', 'newcastle', 'influenza', 'marek',
                      'mortality', 'biosecurity', 'pathogen', 'antibiotic']
    if any(kw in text for kw in health_keywords):
        return 'health_disease'

    # Farm Management & Equipment
    management_keywords = ['ventilat', 'temperature', 'house', 'housing', 'litter',
                          'drinker', 'feeder', 'density', 'stocking', 'light',
                          'ammonia', 'humidity', 'brooding']
    if any(kw in text for kw in management_keywords):
        return 'farm_management_equipment'

    # Anatomy & Physiology
    anatomy_keywords = ['bone', 'muscle', 'organ', 'blood', 'heart', 'liver',
                       'intestine', 'respiratory', 'digestive', 'gizzard',
                       'crop', 'cloaca', 'feather', 'skin']
    if any(kw in text for kw in anatomy_keywords):
        return 'anatomy_physiology'

    return 'general'


def extract_all_glossaries(glossary_dir: Path) -> Dict[str, Dict]:
    """
    Extract all terms from PDF glossaries and categorize them

    Returns:
        Dictionary with categorized terms
    """
    all_terms = {}
    categories_count = {}

    pdf_files = sorted(glossary_dir.glob('glossary-*.pdf'))
    logger.info(f"Found {len(pdf_files)} PDF files to process")

    for pdf_file in pdf_files:
        logger.info(f"Processing {pdf_file.name}...")

        try:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ''
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    full_text += text + '\n'

                # Extract terms
                terms = extract_terms_from_text(full_text)
                logger.info(f"  Extracted {len(terms)} terms from {pdf_file.name}")

                # Categorize and store
                for term, definition in terms:
                    category = categorize_term(term, definition)

                    # Store term
                    term_key = term.lower().replace(' ', '_').replace('-', '_')
                    all_terms[term_key] = {
                        'term': term,
                        'definition': definition,
                        'category': category,
                        'source': pdf_file.name
                    }

                    # Count categories
                    categories_count[category] = categories_count.get(category, 0) + 1

        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
            continue

    logger.info(f"\n📊 Extraction complete!")
    logger.info(f"Total terms extracted: {len(all_terms)}")
    logger.info(f"\nTerms by category:")
    for cat, count in sorted(categories_count.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count}")

    return all_terms


def create_consolidated_glossary(glossary_dir: Path, output_file: Path):
    """
    Create consolidated glossary JSON file
    """
    logger.info("🚀 Starting glossary extraction...")

    # Extract all terms
    all_terms = extract_all_glossaries(glossary_dir)

    # Create structured output
    output_data = {
        'metadata': {
            'version': '2.0.0',
            'description': 'Consolidated poultry terminology extracted from University of Kentucky Poultry Glossary',
            'source': 'Multiple PDF glossaries',
            'total_terms': len(all_terms),
            'extraction_date': '2025-10-27',
            'categories': list(set(term['category'] for term in all_terms.values()))
        },
        'terms': all_terms
    }

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ Consolidated glossary saved to {output_file}")
    logger.info(f"File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    # Paths
    project_root = Path(__file__).parent.parent.parent
    glossary_dir = project_root / 'glossary'
    output_file = project_root / 'llm' / 'app' / 'domain_config' / 'domains' / 'aviculture' / 'extended_glossary.json'

    # Run extraction
    create_consolidated_glossary(glossary_dir, output_file)
