# -*- coding: utf-8 -*-
"""
Entity Extractor - Extrait entités clés pour améliorer le filtering et le boost

Extrait automatiquement:
- Breeds (Ross 308, Cobb 500, etc.)
- Diseases (Newcastle, Gumboro, Coccidiosis, etc.)
- Medications (Amprolium, Vaccines, etc.)
- Performance Metrics (FCR, Weight, Mortality, etc.)
- Age Ranges (1-21 days, 22-35 days, etc.)

Utilisation en retrieval:
- Filtering: breed=Ross 308 AND age_range=21-35
- Boosting: Si query contient "Ross 308", boost chunks avec breed="Ross 308"
- Analytics: Statistiques sur couverture du corpus
"""

import re
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ExtractedEntities:
    """Entités extraites d'un chunk"""
    breeds: List[str]
    diseases: List[str]
    medications: List[str]
    metrics: List[Dict[str, Any]]  # [{"type": "fcr", "value": 1.65}, ...]
    age_ranges: List[Dict[str, int]]  # [{"start": 1, "end": 21, "unit": "days"}, ...]

    # Champs additionnels pour filtering
    has_performance_data: bool
    has_health_info: bool
    has_nutrition_info: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)


class EntityExtractor:
    """
    Extract domain-specific entities from poultry text

    Usage:
        extractor = EntityExtractor()
        entities = extractor.extract(chunk_content)
        print(f"Breeds: {entities.breeds}")
        print(f"Diseases: {entities.diseases}")
    """

    # Breed patterns (case-insensitive)
    BREED_PATTERNS = {
        'ross': r'\b(Ross)\s*(\d+)?\s*(AP|PS|PM)?\b',
        'cobb': r'\b(Cobb)\s*(\d+)?\s*(Slow Growing)?\b',
        'hubbard': r'\b(Hubbard)\s*(JA\d+|M\d+|Classic)?\b',
        'aviagen': r'\b(Aviagen)(?:\s+\w+)?\b',
        'isa': r'\b(ISA)\s*(Brown|White|Hendrix)?\b',
        'lohmann': r'\b(Lohmann)\s*(Brown|White|Classic|LSL)?\b',
        'hyline': r'\b(Hy-Line|HyLine)\s*(Brown|W-36|W-80)?\b',
        'novogen': r'\b(Novogen)\s*(Brown|White)?\b',
    }

    # Disease patterns
    DISEASE_PATTERNS = {
        'newcastle': r'\b(Newcastle\s+Disease|ND|Newcastle)\b',
        'gumboro': r'\b(Gumboro|IBD|Infectious\s+Bursal\s+Disease)\b',
        'marek': r'\b(Marek\'?s?\s+Disease|MD)\b',
        'coccidiosis': r'\b(Coccidiosis|Coccidia|Eimeria)\b',
        'salmonella': r'\b(Salmonella|Salmonellosis)\b',
        'ecoli': r'\b(E\.?\s*coli|Escherichia\s+coli|Colibacillosis)\b',
        'avian_influenza': r'\b(Avian\s+Influenza|AI|Bird\s+Flu|H\d+N\d+)\b',
        'bronchitis': r'\b(Infectious\s+Bronchitis|IB|Bronchitis)\b',
        'laryngotracheitis': r'\b(Infectious\s+Laryngotracheitis|ILT|Laryngotracheitis)\b',
        'mycoplasma': r'\b(Mycoplasma|MG|MS|Mycoplasmosis)\b',
    }

    # Medication patterns
    MEDICATION_PATTERNS = {
        'coccidiostat': r'\b(Amprolium|Monensin|Salinomycin|Nicarbazin|Maduramicin|Coccidiostat)\b',
        'antibiotic': r'\b(Enrofloxacin|Amoxicillin|Tetracycline|Tiamulin|Tylosin|Doxycycline)\b',
        'vaccine': r'\b(Vaccine|Vaccination|Immunization|Marek\s+Vaccine|Newcastle\s+Vaccine)\b',
        'disinfectant': r'\b(Disinfectant|Virkon|Formaldehyde|Quaternary\s+Ammonium)\b',
    }

    # Performance metrics patterns
    METRIC_PATTERNS = {
        'fcr': r'\b(FCR|Feed\s+Conversion\s+Ratio?)\s*[:=]?\s*(\d+[.,]\d+)\b',
        'weight': r'\b(\d+[.,]?\d*)\s*(g|grams?|kg|kilograms?)\b',
        'mortality': r'\b(Mortality|Death\s+Rate)\s*[:=]?\s*([<>]?\d+[.,]?\d*)\s*%?\b',
        'livability': r'\b(Livability|Viability)\s*[:=]?\s*([<>]?\d+[.,]?\d*)\s*%?\b',
    }

    # Age range patterns
    AGE_PATTERNS = [
        r'(\d+)[-–](\d+)\s*(days?|weeks?)',  # 1-21 days, 1-3 weeks
        r'day\s+(\d+)',  # day 35
        r'week\s+(\d+)',  # week 5
        r'(\d+)\s*days?\s+old',  # 21 days old
    ]

    def __init__(self):
        """Initialize entity extractor"""
        self.logger = logging.getLogger(__name__)

        # Compile all patterns
        self.breed_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.BREED_PATTERNS.items()
        }

        self.disease_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.DISEASE_PATTERNS.items()
        }

        self.medication_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.MEDICATION_PATTERNS.items()
        }

        self.metric_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.METRIC_PATTERNS.items()
        }

        self.age_regexes = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.AGE_PATTERNS
        ]

    def extract(self, content: str) -> ExtractedEntities:
        """
        Extract all entities from content

        Args:
            content: Text content to analyze

        Returns:
            ExtractedEntities with all extracted information
        """
        if not content or len(content.strip()) < 10:
            return self._empty_entities()

        # Extract each entity type
        breeds = self._extract_breeds(content)
        diseases = self._extract_diseases(content)
        medications = self._extract_medications(content)
        metrics = self._extract_metrics(content)
        age_ranges = self._extract_age_ranges(content)

        # Determine content type flags
        has_performance_data = len(metrics) > 0
        has_health_info = len(diseases) > 0 or len(medications) > 0
        has_nutrition_info = 'feed' in content.lower() or 'nutrition' in content.lower()

        return ExtractedEntities(
            breeds=breeds,
            diseases=diseases,
            medications=medications,
            metrics=metrics,
            age_ranges=age_ranges,
            has_performance_data=has_performance_data,
            has_health_info=has_health_info,
            has_nutrition_info=has_nutrition_info
        )

    def _extract_breeds(self, content: str) -> List[str]:
        """Extract breed names"""
        breeds = set()

        for name, regex in self.breed_regexes.items():
            matches = regex.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    # Combine parts (e.g., "Ross 308")
                    breed = ' '.join([str(p) for p in match if p]).strip()
                else:
                    breed = match.strip()

                if breed:
                    breeds.add(breed)

        return sorted(list(breeds))

    def _extract_diseases(self, content: str) -> List[str]:
        """Extract disease names"""
        diseases = set()

        for name, regex in self.disease_regexes.items():
            matches = regex.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    disease = match[0].strip()
                else:
                    disease = match.strip()

                if disease:
                    diseases.add(disease)

        return sorted(list(diseases))

    def _extract_medications(self, content: str) -> List[str]:
        """Extract medication names"""
        medications = set()

        for name, regex in self.medication_regexes.items():
            matches = regex.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    med = match[0].strip()
                else:
                    med = match.strip()

                if med:
                    medications.add(med)

        return sorted(list(medications))

    def _extract_metrics(self, content: str) -> List[Dict[str, Any]]:
        """Extract performance metrics with values"""
        metrics = []

        for metric_type, regex in self.metric_regexes.items():
            matches = regex.findall(content)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    value_str = match[1].replace(',', '.')
                    try:
                        value = float(value_str)
                        metrics.append({
                            'type': metric_type,
                            'value': value,
                            'raw_match': ' '.join(match)
                        })
                    except ValueError:
                        continue

        return metrics

    def _extract_age_ranges(self, content: str) -> List[Dict[str, int]]:
        """Extract age ranges in days"""
        age_ranges = []

        for regex in self.age_regexes:
            matches = regex.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) >= 3:
                        # Range format: 1-21 days
                        try:
                            start = int(match[0])
                            end = int(match[1])
                            unit = match[2].lower()

                            # Convert weeks to days
                            if 'week' in unit:
                                start *= 7
                                end *= 7

                            age_ranges.append({
                                'start': start,
                                'end': end,
                                'unit': 'days'
                            })
                        except (ValueError, IndexError):
                            continue
                    elif len(match) >= 2:
                        # Single age format: day 35 or week 5
                        try:
                            age = int(match[0])
                            unit = match[1].lower() if len(match) > 1 else 'days'

                            if 'week' in unit:
                                age *= 7

                            age_ranges.append({
                                'start': age,
                                'end': age,
                                'unit': 'days'
                            })
                        except (ValueError, IndexError):
                            continue

        return age_ranges

    def _empty_entities(self) -> ExtractedEntities:
        """Return empty entities"""
        return ExtractedEntities(
            breeds=[],
            diseases=[],
            medications=[],
            metrics=[],
            age_ranges=[],
            has_performance_data=False,
            has_health_info=False,
            has_nutrition_info=False
        )


# CLI pour tester
if __name__ == "__main__":
    extractor = EntityExtractor()

    test_content = """
    Ross 308 Broiler Performance at 35 Days

    The Ross 308 breed shows excellent growth performance during the 35-day
    production cycle. Male birds typically achieve 2100g body weight with an
    FCR of 1.65, while females reach 1850g at FCR 1.70.

    Health Management:
    - Newcastle Disease vaccination at day 7 and 21
    - Coccidiosis prevention using Amprolium in drinking water
    - Monitor for Gumboro symptoms during weeks 3-4
    - E. coli control through proper biosecurity

    Mortality should remain below 3% with proper management.
    """

    entities = extractor.extract(test_content)

    print("="*60)
    print("EXTRACTED ENTITIES:")
    print(f"\nBreeds: {entities.breeds}")
    print(f"Diseases: {entities.diseases}")
    print(f"Medications: {entities.medications}")
    print(f"\nMetrics:")
    for metric in entities.metrics:
        print(f"  - {metric['type']}: {metric['value']}")
    print(f"\nAge Ranges:")
    for age in entities.age_ranges:
        print(f"  - {age['start']}-{age['end']} {age['unit']}")
    print(f"\nContent Flags:")
    print(f"  - Has Performance Data: {entities.has_performance_data}")
    print(f"  - Has Health Info: {entities.has_health_info}")
    print(f"  - Has Nutrition Info: {entities.has_nutrition_info}")
