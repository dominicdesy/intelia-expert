# -*- coding: utf-8 -*-
"""
Advanced Result Boosting for RAG System
Implements quality-score boosting and entity-based filtering/boosting
"""

import logging
from typing import List, Dict, Optional, Any
from utils.types import List as TypeList, Dict as TypeDict

logger = logging.getLogger(__name__)


class AdvancedResultBoosting:
    """
    Advanced boosting system for RAG results.

    Features:
    1. Quality-Score Boosting: Promotes high-quality chunks
    2. Entity-Based Boosting: Boosts chunks matching query entities
    3. Configurable boost weights
    """

    def __init__(
        self,
        quality_boost_weight: float = 0.2,  # Max +20% for quality
        breed_boost_multiplier: float = 1.3,  # +30% for breed match
        disease_boost_multiplier: float = 1.2,  # +20% for disease match
        medication_boost_multiplier: float = 1.15,  # +15% for medication match
        enable_quality_boost: bool = True,
        enable_entity_boost: bool = True
    ):
        """
        Initialize advanced boosting system.

        Args:
            quality_boost_weight: Weight for quality score boosting (0.0-1.0)
            breed_boost_multiplier: Multiplier when breed matches
            disease_boost_multiplier: Multiplier when disease matches
            medication_boost_multiplier: Multiplier when medication matches
            enable_quality_boost: Enable quality-based boosting
            enable_entity_boost: Enable entity-based boosting
        """
        self.quality_boost_weight = quality_boost_weight
        self.breed_boost = breed_boost_multiplier
        self.disease_boost = disease_boost_multiplier
        self.medication_boost = medication_boost_multiplier
        self.enable_quality = enable_quality_boost
        self.enable_entity = enable_entity_boost

        logger.info(f"Advanced Boosting initialized:")
        logger.info(f"  Quality boost: {enable_quality_boost} (weight={quality_boost_weight})")
        logger.info(f"  Entity boost: {enable_entity_boost}")
        logger.info(f"  Breed multiplier: {breed_boost_multiplier}x")
        logger.info(f"  Disease multiplier: {disease_boost_multiplier}x")

    def extract_entities_from_query(self, query_text: str) -> Dict[str, List[str]]:
        """
        Extract potential entities from query text.

        Simple pattern-based extraction for common poultry entities.
        Can be enhanced with NER models in the future.

        Args:
            query_text: Query text to analyze

        Returns:
            Dictionary with entity lists: {breeds: [], diseases: [], medications: []}
        """
        query_lower = query_text.lower()

        entities = {
            "breeds": [],
            "diseases": [],
            "medications": []
        }

        # Common breed patterns
        breed_patterns = [
            "ross 308", "ross308", "ross",
            "cobb 500", "cobb500", "cobb",
            "hy-line", "hyline", "hy line",
            "lohmann", "isa brown", "isa",
            "hubbard", "arbor acres"
        ]

        for breed in breed_patterns:
            if breed in query_lower:
                # Normalize breed name
                normalized = breed.replace("-", " ").replace("  ", " ").title()
                if normalized not in entities["breeds"]:
                    entities["breeds"].append(normalized)

        # Common disease patterns
        disease_patterns = [
            "newcastle", "gumboro", "marek", "coccidiosis",
            "ascites", "ibv", "infectious bronchitis",
            "avian influenza", "salmonella", "e.coli",
            "mycoplasma", "fowl cholera", "necrotic enteritis"
        ]

        for disease in disease_patterns:
            if disease in query_lower:
                normalized = disease.title()
                if normalized not in entities["diseases"]:
                    entities["diseases"].append(normalized)

        # Common medication patterns
        medication_patterns = [
            "vaccine", "vaccination", "antibiotic",
            "anticoccidial", "probiotic", "vitamin"
        ]

        for med in medication_patterns:
            if med in query_lower:
                normalized = med.title()
                if normalized not in entities["medications"]:
                    entities["medications"].append(normalized)

        # Log extraction
        if any(entities.values()):
            logger.debug(f"Extracted entities from query: {entities}")

        return entities

    def boost_results(
        self,
        results: List[Dict],
        query_entities: Optional[Dict[str, List[str]]] = None,
        query_text: Optional[str] = None
    ) -> List[Dict]:
        """
        Apply advanced boosting to search results.

        Args:
            results: List of search results with metadata
            query_entities: Pre-extracted entities (optional)
            query_text: Query text for entity extraction (optional)

        Returns:
            Boosted and re-ranked results
        """
        if not results:
            return results

        # Extract entities from query if not provided
        if query_entities is None and query_text:
            query_entities = self.extract_entities_from_query(query_text)
        elif query_entities is None:
            query_entities = {"breeds": [], "diseases": [], "medications": []}

        boosted_results = []

        for result in results:
            original_score = result.get('score', 0.0)
            boosted_score = original_score
            boost_factors = []

            # Get result metadata
            metadata = result.get('metadata', {}) or {}

            # 1. Quality Score Boosting
            if self.enable_quality:
                quality_score = result.get('quality_score') or metadata.get('quality_score', 0.5)

                if quality_score is not None:
                    # Apply quality boost: score * (1 + quality * weight)
                    quality_boost_factor = 1 + (quality_score * self.quality_boost_weight)
                    boosted_score *= quality_boost_factor
                    boost_factors.append(f"quality={quality_boost_factor:.3f}")

            # 2. Entity-Based Boosting
            if self.enable_entity and query_entities:

                # Breed matching
                if query_entities.get('breeds'):
                    result_breeds = result.get('breeds', []) or metadata.get('breeds', []) or []
                    # Normalize for comparison
                    result_breeds_lower = [b.lower() if b else '' for b in result_breeds]
                    query_breeds_lower = [b.lower() if b else '' for b in query_entities['breeds']]

                    # Check for any match (exact or partial)
                    breed_match = any(
                        any(qb in rb or rb in qb for rb in result_breeds_lower if rb)
                        for qb in query_breeds_lower if qb
                    )

                    if breed_match:
                        boosted_score *= self.breed_boost
                        boost_factors.append(f"breed={self.breed_boost}x")

                # Disease matching
                if query_entities.get('diseases'):
                    result_diseases = result.get('diseases', []) or metadata.get('diseases', []) or []
                    result_diseases_lower = [d.lower() if d else '' for d in result_diseases]
                    query_diseases_lower = [d.lower() if d else '' for d in query_entities['diseases']]

                    disease_match = any(
                        any(qd in rd or rd in qd for rd in result_diseases_lower if rd)
                        for qd in query_diseases_lower if qd
                    )

                    if disease_match:
                        boosted_score *= self.disease_boost
                        boost_factors.append(f"disease={self.disease_boost}x")

                # Medication matching
                if query_entities.get('medications'):
                    result_meds = result.get('medications', []) or metadata.get('medications', []) or []
                    result_meds_lower = [m.lower() if m else '' for m in result_meds]
                    query_meds_lower = [m.lower() if m else '' for m in query_entities['medications']]

                    med_match = any(
                        any(qm in rm or rm in qm for rm in result_meds_lower if rm)
                        for qm in query_meds_lower if qm
                    )

                    if med_match:
                        boosted_score *= self.medication_boost
                        boost_factors.append(f"medication={self.medication_boost}x")

            # Create boosted result
            boosted_result = result.copy()
            boosted_result['original_score'] = original_score
            boosted_result['boosted_score'] = boosted_score
            boosted_result['boost_factor'] = boosted_score / original_score if original_score > 0 else 1.0
            boosted_result['boost_details'] = ' + '.join(boost_factors) if boost_factors else 'none'

            # Update the score field
            boosted_result['score'] = boosted_score

            boosted_results.append(boosted_result)

        # Re-sort by boosted score
        boosted_results.sort(key=lambda x: x['boosted_score'], reverse=True)

        # Log boosting summary
        if any(r['boost_factor'] > 1.0 for r in boosted_results):
            boosted_count = sum(1 for r in boosted_results if r['boost_factor'] > 1.0)
            max_boost = max(r['boost_factor'] for r in boosted_results)
            logger.debug(
                f"Boosted {boosted_count}/{len(boosted_results)} results "
                f"(max boost: {max_boost:.2f}x)"
            )

        return boosted_results

    def filter_by_entities(
        self,
        results: List[Dict],
        breeds: Optional[List[str]] = None,
        diseases: Optional[List[str]] = None,
        medications: Optional[List[str]] = None,
        strict_mode: bool = False
    ) -> List[Dict]:
        """
        Filter results by entity criteria.

        Args:
            results: Search results to filter
            breeds: Required breed names (None = no filter)
            diseases: Required disease names (None = no filter)
            medications: Required medication names (None = no filter)
            strict_mode: If True, require ALL specified entities. If False, require ANY.

        Returns:
            Filtered results
        """
        if not any([breeds, diseases, medications]):
            return results  # No filters specified

        filtered = []

        for result in results:
            metadata = result.get('metadata', {}) or {}

            # Get entity lists from result
            result_breeds = result.get('breeds', []) or metadata.get('breeds', []) or []
            result_diseases = result.get('diseases', []) or metadata.get('diseases', []) or []
            result_meds = result.get('medications', []) or metadata.get('medications', []) or []

            # Normalize for comparison
            result_breeds_lower = [b.lower() for b in result_breeds if b]
            result_diseases_lower = [d.lower() for d in result_diseases if d]
            result_meds_lower = [m.lower() for m in result_meds if m]

            matches = []

            # Check breed filter
            if breeds:
                breeds_lower = [b.lower() for b in breeds if b]
                breed_match = any(
                    any(qb in rb or rb in qb for rb in result_breeds_lower)
                    for qb in breeds_lower
                )
                matches.append(breed_match)

            # Check disease filter
            if diseases:
                diseases_lower = [d.lower() for d in diseases if d]
                disease_match = any(
                    any(qd in rd or rd in qd for rd in result_diseases_lower)
                    for qd in diseases_lower
                )
                matches.append(disease_match)

            # Check medication filter
            if medications:
                meds_lower = [m.lower() for m in medications if m]
                med_match = any(
                    any(qm in rm or rm in qm for rm in result_meds_lower)
                    for qm in meds_lower
                )
                matches.append(med_match)

            # Apply filter logic
            if strict_mode:
                # Require ALL matches
                if all(matches):
                    filtered.append(result)
            else:
                # Require ANY match
                if any(matches):
                    filtered.append(result)

        logger.debug(
            f"Entity filtering: {len(results)} -> {len(filtered)} results "
            f"(mode={'strict' if strict_mode else 'any'})"
        )

        return filtered

    def get_boosting_stats(self) -> Dict[str, Any]:
        """Get current boosting configuration."""
        return {
            "quality_boost": {
                "enabled": self.enable_quality,
                "weight": self.quality_boost_weight,
                "max_boost_percent": self.quality_boost_weight * 100
            },
            "entity_boost": {
                "enabled": self.enable_entity,
                "breed_multiplier": self.breed_boost,
                "disease_multiplier": self.disease_boost,
                "medication_multiplier": self.medication_boost
            }
        }


# Convenience function for easy import
def create_advanced_booster(**kwargs) -> AdvancedResultBoosting:
    """Factory function to create AdvancedResultBoosting instance."""
    return AdvancedResultBoosting(**kwargs)
