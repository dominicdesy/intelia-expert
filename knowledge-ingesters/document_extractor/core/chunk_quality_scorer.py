# -*- coding: utf-8 -*-
"""
Chunk Quality Scorer - Évalue la qualité de chaque chunk pour améliorer le retrieval

Calcule un score de qualité (0-1) basé sur:
1. Densité informationnelle (30%) - Présence d'entités, nombres, termes techniques
2. Complétude (20%) - Contexte au début, conclusion/résumé
3. Cohérence sémantique (30%) - Similarité entre phrases du chunk
4. Longueur optimale (10%) - 400-600 mots optimal
5. Structure (10%) - Listes, tableaux, sections

Score élevé = Chunk de haute qualité, prioritaire pour retrieval
"""

import re
import logging
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class QualityMetrics:
    """Métriques de qualité détaillées d'un chunk"""
    overall_score: float  # Score global (0-1)
    info_density: float  # Densité informationnelle (0-1)
    completeness: float  # Complétude contexte (0-1)
    semantic_coherence: float  # Cohérence sémantique (0-1)
    length_score: float  # Score longueur optimale (0-1)
    structure_score: float  # Score structure (0-1)

    # Métriques brutes pour analytics
    entity_count: int
    number_count: int
    has_intro: bool
    has_conclusion: bool
    has_lists: bool
    has_tables: bool
    word_count: int


class ChunkQualityScorer:
    """
    Calcule un score de qualité pour chaque chunk

    Usage:
        scorer = ChunkQualityScorer()
        metrics = scorer.score_chunk("Content of the chunk...")
        print(f"Quality: {metrics.overall_score:.2f}")
    """

    # Patterns pour détection d'entités et structure
    ENTITY_PATTERNS = {
        'breeds': r'\b(Ross|Cobb|Hubbard|Aviagen|ISA|Lohmann|Hy-Line)\s*\d*\b',
        'diseases': r'\b(Newcastle|Gumboro|Marek|Coccidiosis|Salmonella|E\.?\s*coli|Avian\s+Influenza)\b',
        'medications': r'\b(Amprolium|Enrofloxacin|Tiamulin|Coccidiostat|Antibiotic|Vaccine)\b',
        'metrics': r'\b(FCR|Feed\s+Conversion|Weight|Mortality|Livability|kg|grams?|g\b|%)\b',
        'ages': r'\b(\d+[-–]\d+\s*days?|\d+\s*weeks?|day\s+\d+|week\s+\d+)\b'
    }

    INTRO_PATTERNS = [
        r'^(This|The|In|Introduction|Overview|Summary):?',
        r'^[A-Z][^.!?]{10,80}[:,]\s',  # Section title followed by colon
        r'^\s*#+\s+',  # Markdown header
    ]

    CONCLUSION_PATTERNS = [
        r'(In\s+conclusion|To\s+summarize|In\s+summary|Finally|Therefore|Thus|Overall)',
        r'(Key\s+points?|Takeaways?|Recommendations?|Best\s+practices?)',
    ]

    def __init__(self):
        """Initialize quality scorer"""
        self.logger = logging.getLogger(__name__)

        # Compile patterns pour performance
        self.entity_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.ENTITY_PATTERNS.items()
        }

        self.intro_regexes = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INTRO_PATTERNS
        ]

        self.conclusion_regexes = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.CONCLUSION_PATTERNS
        ]

    def score_chunk(self, content: str) -> QualityMetrics:
        """
        Calculate comprehensive quality score for a chunk

        Args:
            content: Text content of the chunk

        Returns:
            QualityMetrics with detailed scores
        """
        if not content or len(content.strip()) < 10:
            return self._empty_metrics()

        # Calculate individual components
        info_density, entity_count, number_count = self._calculate_info_density(content)
        completeness, has_intro, has_conclusion = self._calculate_completeness(content)
        semantic_coherence = self._calculate_semantic_coherence(content)
        length_score, word_count = self._calculate_length_score(content)
        structure_score, has_lists, has_tables = self._calculate_structure_score(content)

        # Weighted overall score
        overall_score = (
            info_density * 0.30 +
            completeness * 0.20 +
            semantic_coherence * 0.30 +
            length_score * 0.10 +
            structure_score * 0.10
        )

        return QualityMetrics(
            overall_score=round(overall_score, 3),
            info_density=round(info_density, 3),
            completeness=round(completeness, 3),
            semantic_coherence=round(semantic_coherence, 3),
            length_score=round(length_score, 3),
            structure_score=round(structure_score, 3),
            entity_count=entity_count,
            number_count=number_count,
            has_intro=has_intro,
            has_conclusion=has_conclusion,
            has_lists=has_lists,
            has_tables=has_tables,
            word_count=word_count
        )

    def _calculate_info_density(self, content: str) -> tuple[float, int, int]:
        """
        Calculate information density (0-1)

        Measures presence of entities, numbers, technical terms

        Returns:
            (score, entity_count, number_count)
        """
        words = content.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0, 0, 0

        # Count entities of all types
        entity_count = 0
        for name, regex in self.entity_regexes.items():
            matches = regex.findall(content)
            entity_count += len(matches)

        # Count numbers (ages, weights, percentages, etc.)
        number_pattern = r'\b\d+[.,]?\d*\b'
        number_matches = re.findall(number_pattern, content)
        number_count = len(number_matches)

        # Calculate density (entities + numbers per 100 words)
        density_raw = (entity_count + number_count) / word_count * 100

        # Normalize to 0-1 (assume 10 entities/numbers per 100 words = perfect)
        density_score = min(density_raw / 10.0, 1.0)

        return density_score, entity_count, number_count

    def _calculate_completeness(self, content: str) -> tuple[float, bool, bool]:
        """
        Calculate completeness score (0-1)

        Checks for:
        - Introduction/context at start
        - Conclusion/summary at end

        Returns:
            (score, has_intro, has_conclusion)
        """
        # Check for intro (first 150 chars)
        intro_text = content[:150]
        has_intro = any(regex.search(intro_text) for regex in self.intro_regexes)

        # Check for conclusion (last 200 chars)
        conclusion_text = content[-200:]
        has_conclusion = any(regex.search(conclusion_text) for regex in self.conclusion_regexes)

        # Score: 0.5 for each component
        score = (0.5 if has_intro else 0.0) + (0.5 if has_conclusion else 0.0)

        return score, has_intro, has_conclusion

    def _calculate_semantic_coherence(self, content: str) -> float:
        """
        Calculate semantic coherence (0-1)

        Measures:
        - Sentence length variance (too much variance = poor coherence)
        - Repetition rate (some repetition good, too much bad)
        - Transition words presence

        Returns:
            Coherence score (0-1)
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return 0.5  # Neutral score for single sentence

        # 1. Sentence length variance (lower is better)
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
        std_dev = variance ** 0.5

        # Normalize variance score (std_dev < 10 words = good)
        variance_score = max(0, 1 - (std_dev / 20))

        # 2. Repetition rate (moderate repetition good for coherence)
        words = content.lower().split()
        unique_words = set(words)
        repetition_rate = len(unique_words) / len(words) if words else 1.0

        # Optimal: 0.4-0.7 (40-70% unique words)
        if 0.4 <= repetition_rate <= 0.7:
            repetition_score = 1.0
        elif repetition_rate < 0.4:
            repetition_score = repetition_rate / 0.4
        else:
            repetition_score = (1 - repetition_rate) / 0.3

        # 3. Transition words (however, therefore, additionally, etc.)
        transition_words = [
            'however', 'therefore', 'thus', 'additionally', 'furthermore',
            'moreover', 'consequently', 'nevertheless', 'although', 'while',
            'because', 'since', 'as a result', 'for example', 'in contrast'
        ]
        transition_count = sum(1 for word in transition_words if word in content.lower())
        transition_score = min(transition_count / 3, 1.0)  # 3+ transitions = perfect

        # Combine scores
        coherence_score = (
            variance_score * 0.4 +
            repetition_score * 0.4 +
            transition_score * 0.2
        )

        return coherence_score

    def _calculate_length_score(self, content: str) -> tuple[float, int]:
        """
        Calculate optimal length score (0-1)

        Optimal range: 400-600 words
        Acceptable range: 300-700 words

        Returns:
            (score, word_count)
        """
        words = content.split()
        word_count = len(words)

        if 400 <= word_count <= 600:
            # Perfect range
            score = 1.0
        elif 300 <= word_count < 400:
            # Below optimal, but acceptable
            score = 0.5 + (word_count - 300) / 200 * 0.5
        elif 600 < word_count <= 700:
            # Above optimal, but acceptable
            score = 1.0 - (word_count - 600) / 200 * 0.5
        elif word_count < 300:
            # Too short
            score = word_count / 300 * 0.5
        else:
            # Too long (>700)
            score = max(0.0, 0.5 - (word_count - 700) / 500 * 0.5)

        return score, word_count

    def _calculate_structure_score(self, content: str) -> tuple[float, bool, bool]:
        """
        Calculate structure score (0-1)

        Checks for:
        - Lists (bullet points, numbered)
        - Tables
        - Sections/headers

        Returns:
            (score, has_lists, has_tables)
        """
        score = 0.0

        # Check for lists
        has_lists = bool(re.search(r'^\s*[-*•]\s', content, re.MULTILINE) or
                        re.search(r'^\s*\d+\.\s', content, re.MULTILINE))
        if has_lists:
            score += 0.4

        # Check for tables (markdown or plain text)
        has_tables = bool(re.search(r'\|[^\n]+\|', content) or
                         re.search(r'\t[^\n]+\t', content))
        if has_tables:
            score += 0.3

        # Check for sections/headers
        has_sections = bool(re.search(r'^#+\s+', content, re.MULTILINE) or
                          re.search(r'^[A-Z][^.!?]{10,80}:$', content, re.MULTILINE))
        if has_sections:
            score += 0.3

        return score, has_lists, has_tables

    def _empty_metrics(self) -> QualityMetrics:
        """Return empty/zero metrics"""
        return QualityMetrics(
            overall_score=0.0,
            info_density=0.0,
            completeness=0.0,
            semantic_coherence=0.0,
            length_score=0.0,
            structure_score=0.0,
            entity_count=0,
            number_count=0,
            has_intro=False,
            has_conclusion=False,
            has_lists=False,
            has_tables=False,
            word_count=0
        )


# CLI pour tester
if __name__ == "__main__":
    scorer = ChunkQualityScorer()

    # Test chunk 1: High quality
    test_chunk_high = """
    Ross 308 Broiler Performance at 35 Days

    The Ross 308 breed shows excellent growth performance during the 35-day
    production cycle. Male birds typically achieve 2100g body weight with an
    FCR of 1.65, while females reach 1850g at FCR 1.70.

    Key performance indicators:
    - Weight gain: 60g/day average
    - Feed intake: 3.5kg total
    - Mortality: <3% target
    - Livability: >97%

    Temperature management is critical during this period. Maintain 32°C
    for days 1-7, then reduce by 0.5°C daily until reaching 21°C. However,
    variations may be needed based on bird behavior and environmental conditions.

    In summary, achieving these targets requires proper nutrition, biosecurity,
    and environmental control throughout the production cycle.
    """

    # Test chunk 2: Low quality
    test_chunk_low = """
    Chickens need food and water. They also need shelter.
    """

    metrics_high = scorer.score_chunk(test_chunk_high)
    metrics_low = scorer.score_chunk(test_chunk_low)

    print("="*60)
    print("HIGH QUALITY CHUNK:")
    print(f"Overall Score: {metrics_high.overall_score:.2f}")
    print(f"  - Info Density: {metrics_high.info_density:.2f} ({metrics_high.entity_count} entities, {metrics_high.number_count} numbers)")
    print(f"  - Completeness: {metrics_high.completeness:.2f} (intro={metrics_high.has_intro}, conclusion={metrics_high.has_conclusion})")
    print(f"  - Coherence: {metrics_high.semantic_coherence:.2f}")
    print(f"  - Length: {metrics_high.length_score:.2f} ({metrics_high.word_count} words)")
    print(f"  - Structure: {metrics_high.structure_score:.2f} (lists={metrics_high.has_lists}, tables={metrics_high.has_tables})")

    print("\n" + "="*60)
    print("LOW QUALITY CHUNK:")
    print(f"Overall Score: {metrics_low.overall_score:.2f}")
    print(f"  - Info Density: {metrics_low.info_density:.2f} ({metrics_low.entity_count} entities, {metrics_low.number_count} numbers)")
    print(f"  - Completeness: {metrics_low.completeness:.2f}")
    print(f"  - Coherence: {metrics_low.semantic_coherence:.2f}")
    print(f"  - Length: {metrics_low.length_score:.2f} ({metrics_low.word_count} words)")
    print(f"  - Structure: {metrics_low.structure_score:.2f}")
