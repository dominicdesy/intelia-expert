"""
Path-Based Classifier
Extracts metadata from directory structure (70% of classification)
Configurable via YAML rules per organization
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import yaml
import re


@dataclass
class PathMetadata:
    """Metadata extracted from file path"""

    # Core path-based fields (from directory structure)
    owner_org_id: str  # Organization ID (intelia, client_abc, etc.)
    visibility_level: str  # public_global, intelia_internal, org_internal, org_customer_facing
    site_type: Optional[str] = None  # broiler_farms, layer_farms, breeding_farms, etc.
    breed: Optional[str] = None  # ross_308, cobb_500, hy_line_brown, etc.
    category: Optional[str] = None  # biosecurity, breed, housing, management
    subcategory: Optional[str] = None  # common, by_breed, by_climate, etc.
    climate_zone: Optional[str] = None  # tropical, temperate, cold

    # File-level information
    source_file: str = ""  # Full file path
    filename: str = ""  # Just the filename

    # Additional context
    path_segments: List[str] = None  # All directory segments
    confidence_score: float = 0.0  # Path parsing confidence


class PathBasedClassifier:
    """
    Classifies documents based on their directory path structure.

    Rules are configurable per organization via YAML files in config/path_rules/

    Example path: Sources/intelia/public/broiler_farms/breed/ross_308/handbook.pdf

    Extracts:
    - owner_org_id: intelia
    - visibility_level: public_global
    - site_type: broiler_farms
    - category: breed
    - breed: ross_308
    """

    def __init__(self, config_dir: Path = None):
        """
        Initialize classifier with configuration directory.

        Args:
            config_dir: Directory containing YAML rule files (default: config/path_rules/)
        """
        if config_dir is None:
            # Default to config/path_rules/ relative to this file
            base_dir = Path(__file__).parent.parent
            config_dir = base_dir / "config" / "path_rules"

        self.config_dir = Path(config_dir)
        self.rules_cache: Dict[str, Dict[str, Any]] = {}

        # Load all organization rules
        self._load_all_rules()

    def _load_all_rules(self):
        """Load all YAML rule files from config directory"""
        if not self.config_dir.exists():
            print(f"Warning: Config directory not found: {self.config_dir}")
            return

        for yaml_file in self.config_dir.glob("*.yaml"):
            org_id = yaml_file.stem  # Filename without extension
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    rules = yaml.safe_load(f)
                    self.rules_cache[org_id] = rules
                    print(f"Loaded path rules for: {org_id}")
            except Exception as e:
                print(f"Error loading rules for {org_id}: {e}")

    def classify_path(self, file_path: str | Path) -> PathMetadata:
        """
        Classify a file based on its path.

        Args:
            file_path: Full path to the document file

        Returns:
            PathMetadata with extracted information
        """
        file_path = Path(file_path)

        # Extract path segments
        segments = file_path.parts

        # Find Sources/ directory index
        sources_index = None
        for i, segment in enumerate(segments):
            if segment.lower() == "sources":
                sources_index = i
                break

        if sources_index is None:
            # Not in Sources/ structure - return minimal metadata
            return PathMetadata(
                owner_org_id="unknown",
                visibility_level="unknown",
                source_file=str(file_path),
                filename=file_path.name,
                path_segments=list(segments),
                confidence_score=0.0
            )

        # Extract organization ID (directory after Sources/)
        if sources_index + 1 < len(segments):
            org_id = segments[sources_index + 1]
        else:
            org_id = "unknown"

        # Get rules for this organization
        rules = self.rules_cache.get(org_id, {})

        # Extract visibility level (public, internal, etc.)
        if sources_index + 2 < len(segments):
            visibility_raw = segments[sources_index + 2]
            visibility_level = self._map_visibility(visibility_raw, org_id, rules)
        else:
            visibility_level = "unknown"

        # Extract remaining path components
        remaining_segments = segments[sources_index + 3:]  # After Sources/org/visibility/

        # Parse site type, category, breed, etc.
        site_type = None
        category = None
        subcategory = None
        breed = None
        climate_zone = None

        if len(remaining_segments) >= 1:
            site_type = self._map_site_type(remaining_segments[0], rules)

        if len(remaining_segments) >= 2:
            category = remaining_segments[1]

        if len(remaining_segments) >= 3:
            # Could be breed, subcategory, or climate zone
            segment = remaining_segments[2]

            # Check if it's a known breed pattern
            if self._is_breed(segment, rules):
                breed = segment
            elif segment == "by_climate":
                subcategory = segment
                # Next segment should be climate zone
                if len(remaining_segments) >= 4:
                    climate_zone = remaining_segments[3]
            elif segment == "by_breed":
                subcategory = segment
                # Next segment should be breed
                if len(remaining_segments) >= 4:
                    breed = remaining_segments[3]
            elif segment == "common":
                subcategory = segment
            else:
                # Could be a breed or subcategory
                breed = segment

        # Calculate confidence score
        confidence = self._calculate_confidence(
            org_id, visibility_level, site_type, breed, remaining_segments
        )

        return PathMetadata(
            owner_org_id=org_id,
            visibility_level=visibility_level,
            site_type=site_type,
            breed=breed,
            category=category,
            subcategory=subcategory,
            climate_zone=climate_zone,
            source_file=str(file_path),
            filename=file_path.name,
            path_segments=list(remaining_segments),
            confidence_score=confidence
        )

    def _map_visibility(self, visibility_raw: str, org_id: str, rules: Dict) -> str:
        """Map directory name to visibility level"""
        visibility_map = rules.get("visibility_mapping", {})

        # Check custom mapping first
        if visibility_raw in visibility_map:
            return visibility_map[visibility_raw]

        # Default mapping
        if visibility_raw == "public":
            return "public_global" if org_id == "intelia" else "org_customer_facing"
        elif visibility_raw == "internal":
            return "intelia_internal" if org_id == "intelia" else "org_internal"
        else:
            return visibility_raw

    def _map_site_type(self, site_raw: str, rules: Dict) -> Optional[str]:
        """Map directory name to site type"""
        site_type_map = rules.get("site_type_mapping", {})

        # Check custom mapping first
        if site_raw in site_type_map:
            return site_type_map[site_raw]

        # Default: use as-is if it matches known site types
        known_site_types = [
            "broiler_farms", "layer_farms", "breeding_farms", "hatcheries",
            "rearing_farms", "feed_mills", "processing_plants", "grading_stations",
            "veterinary_services", "intelia_about", "intelia_products"
        ]

        if site_raw in known_site_types:
            return site_raw

        return None

    def _is_breed(self, segment: str, rules: Dict) -> bool:
        """Check if segment represents a breed name"""
        breed_patterns = rules.get("breed_patterns", [])

        # Check against known breed patterns
        known_breeds = [
            "ross_308", "cobb_500", "hubbard_flex",
            "hy_line_brown", "hy_line_w36", "hy_line_w80",
            "lohmann_brown", "lohmann_lsl",
            "ross_308_parent_stock", "cobb_500_breeder",
            "hy_line_brown_parent_stock", "hy_line_w36_parent_stock", "hy_line_w80_parent_stock"
        ]

        if segment in known_breeds:
            return True

        # Check custom patterns from rules
        for pattern in breed_patterns:
            if re.match(pattern, segment):
                return True

        return False

    def _calculate_confidence(
        self,
        org_id: str,
        visibility: str,
        site_type: Optional[str],
        breed: Optional[str],
        segments: List[str]
    ) -> float:
        """
        Calculate confidence score for path classification.

        Confidence based on:
        - Organization ID found: +0.2
        - Visibility level mapped: +0.2
        - Site type identified: +0.3
        - Breed identified: +0.2
        - Path structure depth: +0.1
        """
        score = 0.0

        if org_id != "unknown":
            score += 0.2

        if visibility != "unknown":
            score += 0.2

        if site_type is not None:
            score += 0.3

        if breed is not None:
            score += 0.2

        if len(segments) >= 2:
            score += 0.1

        return min(score, 1.0)

    def get_default_metadata_for_org(self, org_id: str) -> Dict[str, Any]:
        """Get default metadata values for an organization"""
        rules = self.rules_cache.get(org_id, {})
        return rules.get("defaults", {})


# Example usage
if __name__ == "__main__":
    # Initialize classifier
    classifier = PathBasedClassifier()

    # Test paths
    test_paths = [
        "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public/broiler_farms/breed/ross_308/Aviagen-ROSS-Broiler-Handbook-EN.pdf",
        "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public/veterinary_services/common/ascites.pdf",
        "C:/Software_Development/intelia-cognito/knowledge-ingesters/Sources/intelia/public/layer_farms/breed/hy_line_brown/Hyline_Brown_STD.pdf",
    ]

    for path in test_paths:
        print(f"\nClassifying: {path}")
        metadata = classifier.classify_path(path)
        print(f"  Org: {metadata.owner_org_id}")
        print(f"  Visibility: {metadata.visibility_level}")
        print(f"  Site Type: {metadata.site_type}")
        print(f"  Category: {metadata.category}")
        print(f"  Breed: {metadata.breed}")
        print(f"  Confidence: {metadata.confidence_score:.2f}")
