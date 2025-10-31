"""
Metadata Enricher
Combines metadata from 3 sources:
1. Path-based classification (70%) - from directory structure
2. Vision-based classification (25%) - from document content analysis
3. Smart defaults (5%) - fallback values

Final enriched metadata is used for Weaviate ingestion
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import anthropic
import os


@dataclass
class EnrichedMetadata:
    """Complete metadata for a document chunk"""

    # Path-based (70%)
    owner_org_id: str
    visibility_level: str
    site_type: Optional[str] = None
    breed: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    climate_zone: Optional[str] = None

    # Vision-based (25%)
    species: Optional[str] = None  # chicken, turkey, duck
    topics: List[str] = field(default_factory=list)  # Main topics
    genetic_line: Optional[str] = None  # Ross, Cobb, Hy-Line, etc.
    document_type: Optional[str] = None  # handbook, guide, technical_note, etc.
    target_audience: Optional[str] = None  # farmer, veterinarian, manager
    technical_level: Optional[str] = None  # basic, intermediate, advanced

    # Document-level
    company: Optional[str] = None  # Aviagen, Cobb, Hy-Line, etc.
    language: str = "en"
    unit_system: str = "metric"

    # Confidence scores
    path_confidence: float = 0.0
    vision_confidence: float = 0.0
    overall_confidence: float = 0.0

    # Source tracking
    source_file: str = ""
    extraction_method: str = ""  # pdf_vision, docx_text, web_scrape


class MetadataEnricher:
    """
    Enriches metadata by combining path, vision, and default sources.

    Workflow:
    1. Extract path-based metadata (70%)
    2. Analyze document content with vision (25%)
    3. Apply smart defaults (5%)
    4. Combine and validate
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Metadata Enricher.

        Args:
            api_key: Anthropic API key (default: from ANTHROPIC_API_KEY or CLAUDE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def enrich_metadata(
        self,
        path_metadata: Dict[str, Any],
        document_text: str,
        extraction_method: str
    ) -> EnrichedMetadata:
        """
        Enrich metadata from all sources.

        Args:
            path_metadata: Metadata from path_based_classifier
            document_text: Full document text (first 5000 words for analysis)
            extraction_method: pdf_vision, docx_text, or web_scrape

        Returns:
            EnrichedMetadata with combined information
        """
        print("Enriching metadata...")

        # Start with path-based metadata (70%)
        enriched = EnrichedMetadata(
            owner_org_id=path_metadata.get("owner_org_id", "unknown"),
            visibility_level=path_metadata.get("visibility_level", "unknown"),
            site_type=path_metadata.get("site_type"),
            breed=path_metadata.get("breed"),
            category=path_metadata.get("category"),
            subcategory=path_metadata.get("subcategory"),
            climate_zone=path_metadata.get("climate_zone"),
            source_file=path_metadata.get("source_file", ""),
            extraction_method=extraction_method,
            path_confidence=path_metadata.get("confidence_score", 0.0)
        )

        # Analyze document content with vision (25%)
        vision_metadata = self._analyze_document_content(document_text, path_metadata)
        self._merge_vision_metadata(enriched, vision_metadata)

        # Apply smart defaults (5%)
        self._apply_defaults(enriched, path_metadata)

        # Calculate overall confidence
        enriched.overall_confidence = self._calculate_overall_confidence(enriched)

        return enriched

    def _analyze_document_content(
        self,
        document_text: str,
        path_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze document content using Claude to extract metadata.

        Focus on: species, topics, genetic_line, document_type, target_audience
        """
        # Limit text for analysis (first 5000 words)
        words = document_text.split()
        analysis_text = " ".join(words[:5000])

        # Context from path
        site_type = path_metadata.get("site_type", "unknown")
        breed = path_metadata.get("breed", "unknown")

        prompt = f"""Analyze this poultry industry document and extract metadata.

Document preview:
{analysis_text[:3000]}...

Context from path:
- Site type: {site_type}
- Breed: {breed}

Extract the following metadata:

1. **species**: Main poultry species (chicken, turkey, duck, or unknown)
2. **genetic_line**: Specific genetic line/brand (Ross, Cobb, Hy-Line, Lohmann, Hubbard, or unknown)
3. **company**: Company/breeder (Aviagen, Cobb-Vantress, Hy-Line, Lohmann, or unknown)
4. **document_type**: Type of document (handbook, guide, technical_note, research, standard, supplement, or unknown)
5. **target_audience**: Primary audience (farmer, veterinarian, manager, technician, all, or unknown)
6. **technical_level**: Technical complexity (basic, intermediate, advanced, or unknown)
7. **topics**: List of 3-5 main topics covered (e.g., nutrition, housing, health, biosecurity, management, breeding)

Return as JSON:
{{
    "species": "chicken",
    "genetic_line": "Ross",
    "company": "Aviagen",
    "document_type": "handbook",
    "target_audience": "farmer",
    "technical_level": "intermediate",
    "topics": ["nutrition", "housing", "management"]
}}

Important:
- Use "unknown" if information is not clear
- Be conservative with classifications
- Extract, don't infer beyond what's clearly stated"""

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Parse JSON response
            import json
            response_text = response.content[0].text

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            metadata = json.loads(json_str)
            metadata["confidence"] = 0.8  # High confidence from Claude analysis

            return metadata

        except Exception as e:
            print(f"  Warning: Vision analysis failed: {e}")
            return {
                "species": "unknown",
                "genetic_line": "unknown",
                "company": "unknown",
                "document_type": "unknown",
                "target_audience": "unknown",
                "technical_level": "unknown",
                "topics": [],
                "confidence": 0.0
            }

    def _merge_vision_metadata(self, enriched: EnrichedMetadata, vision: Dict[str, Any]):
        """Merge vision-based metadata into enriched metadata"""
        enriched.species = vision.get("species")
        enriched.genetic_line = vision.get("genetic_line")
        enriched.company = vision.get("company")
        enriched.document_type = vision.get("document_type")
        enriched.target_audience = vision.get("target_audience")
        enriched.technical_level = vision.get("technical_level")
        enriched.topics = vision.get("topics", [])
        enriched.vision_confidence = vision.get("confidence", 0.0)

    def _apply_defaults(self, enriched: EnrichedMetadata, path_metadata: Dict[str, Any]):
        """Apply smart defaults for missing fields"""

        # Language default
        if not enriched.language:
            enriched.language = "en"

        # Unit system default (metric for most of the world)
        if not enriched.unit_system:
            enriched.unit_system = "metric"

        # Infer species from site_type if not detected
        if not enriched.species or enriched.species == "unknown":
            if enriched.site_type:
                if "broiler" in enriched.site_type or "breeding" in enriched.site_type:
                    enriched.species = "chicken"
                elif "layer" in enriched.site_type:
                    enriched.species = "chicken"

        # Infer genetic_line from breed if not detected
        if not enriched.genetic_line or enriched.genetic_line == "unknown":
            if enriched.breed:
                breed = enriched.breed.lower()
                if "ross" in breed:
                    enriched.genetic_line = "Ross"
                    enriched.company = "Aviagen"
                elif "cobb" in breed:
                    enriched.genetic_line = "Cobb"
                    enriched.company = "Cobb-Vantress"
                elif "hy_line" in breed:
                    enriched.genetic_line = "Hy-Line"
                    enriched.company = "Hy-Line"
                elif "lohmann" in breed:
                    enriched.genetic_line = "Lohmann"
                    enriched.company = "Lohmann"
                elif "hubbard" in breed:
                    enriched.genetic_line = "Hubbard"
                    enriched.company = "Hubbard"

        # Default target audience based on site_type
        if not enriched.target_audience or enriched.target_audience == "unknown":
            if enriched.site_type in ["broiler_farms", "layer_farms", "breeding_farms"]:
                enriched.target_audience = "farmer"
            elif enriched.site_type == "veterinary_services":
                enriched.target_audience = "veterinarian"
            elif enriched.site_type in ["hatcheries", "feed_mills", "processing_plants"]:
                enriched.target_audience = "manager"

    def _calculate_overall_confidence(self, enriched: EnrichedMetadata) -> float:
        """
        Calculate overall confidence score.

        Weighted average:
        - Path confidence: 70%
        - Vision confidence: 25%
        - Defaults applied: 5%
        """
        path_weight = 0.70
        vision_weight = 0.25
        default_weight = 0.05

        # Count how many defaults were needed
        defaults_used = 0
        total_fields = 0

        for field_name in ["species", "genetic_line", "company", "target_audience"]:
            total_fields += 1
            value = getattr(enriched, field_name, None)
            if not value or value == "unknown":
                defaults_used += 1

        default_score = 1.0 - (defaults_used / total_fields) if total_fields > 0 else 1.0

        overall = (
            enriched.path_confidence * path_weight +
            enriched.vision_confidence * vision_weight +
            default_score * default_weight
        )

        return min(overall, 1.0)


# Example usage
if __name__ == "__main__":
    # Sample path metadata
    path_metadata = {
        "owner_org_id": "intelia",
        "visibility_level": "public_global",
        "site_type": "broiler_farms",
        "breed": "ross_308",
        "category": "breed",
        "source_file": "Aviagen-ROSS-Broiler-Handbook-EN.pdf",
        "confidence_score": 1.0
    }

    # Sample document text
    document_text = """
    ROSS 308 BROILER MANAGEMENT HANDBOOK

    This handbook provides comprehensive guidance for managing Ross 308 broiler chickens
    from day-old to processing. It covers all aspects of commercial broiler production
    including nutrition, housing, health management, and biosecurity.

    Target Audience: Commercial broiler farmers and farm managers

    Contents:
    1. Introduction to Ross 308 Genetics
    2. Brooding Management
    3. Nutrition Programs
    4. House Environment
    5. Health and Biosecurity
    """

    # Initialize enricher
    enricher = MetadataEnricher()

    # Enrich metadata
    enriched = enricher.enrich_metadata(
        path_metadata=path_metadata,
        document_text=document_text,
        extraction_method="pdf_vision"
    )

    print("\n" + "="*80)
    print("ENRICHED METADATA")
    print("="*80)
    print(f"Owner: {enriched.owner_org_id}")
    print(f"Visibility: {enriched.visibility_level}")
    print(f"Site Type: {enriched.site_type}")
    print(f"Breed: {enriched.breed}")
    print(f"Species: {enriched.species}")
    print(f"Genetic Line: {enriched.genetic_line}")
    print(f"Company: {enriched.company}")
    print(f"Document Type: {enriched.document_type}")
    print(f"Target Audience: {enriched.target_audience}")
    print(f"Technical Level: {enriched.technical_level}")
    print(f"Topics: {', '.join(enriched.topics)}")
    print()
    print(f"Path Confidence: {enriched.path_confidence:.2f}")
    print(f"Vision Confidence: {enriched.vision_confidence:.2f}")
    print(f"Overall Confidence: {enriched.overall_confidence:.2f}")
