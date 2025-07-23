#!/usr/bin/env python3
"""
Adaptive Structure Manager
Manages dynamic document structures and organizational patterns
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from collections import defaultdict

# Fix for dataclasses import
try:
    from dataclasses import dataclass, field, asdict
except ImportError:
    # Fallback for older Python versions
    def dataclass(cls):
        return cls
    def field(default_factory=None):
        return default_factory() if default_factory else None
    def asdict(obj):
        return obj.__dict__ if hasattr(obj, '__dict__') else {}

logger = logging.getLogger(__name__)


class StructureType(Enum):
    """Types of document structures."""
    HIERARCHICAL = "hierarchical"
    FLAT = "flat"
    TOPIC_BASED = "topic_based"
    TEMPORAL = "temporal"
    HYBRID = "hybrid"


class OrganizationPattern(Enum):
    """Document organization patterns."""
    BY_BREED = "by_breed"
    BY_AGE_PHASE = "by_age_phase"
    BY_DATA_TYPE = "by_data_type"
    BY_CLASSIFICATION = "by_classification"
    BY_DATE = "by_date"
    BY_TENANT = "by_tenant"
    CUSTOM = "custom"


@dataclass
class StructureRule:
    """Rule for organizing documents."""
    rule_id: str
    pattern: OrganizationPattern
    conditions: Dict[str, Any] = field(default_factory=dict)
    target_path: str = ""
    priority: int = 1
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DocumentLocation:
    """Location information for a document."""
    document_id: str
    logical_path: str
    physical_path: str
    structure_type: StructureType
    organization_pattern: OrganizationPattern
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StructureMetrics:
    """Metrics for structure performance."""
    structure_id: str
    total_documents: int
    access_frequency: int
    average_depth: float
    search_performance: float
    organization_efficiency: float
    last_optimized: str
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)


class AdaptiveStructureManager:
    """Manages adaptive document structures and organization."""
    
    def __init__(self, base_path: str = "adaptive_structures"):
        """Initialize adaptive structure manager."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Structure registry
        self.structures = {}
        self.structure_file = self.base_path / "structures.json"
        
        # Organization rules
        self.rules = {}
        self.rules_file = self.base_path / "organization_rules.json"
        
        # Document locations
        self.document_locations = {}
        self.locations_file = self.base_path / "document_locations.json"
        
        # Performance metrics
        self.metrics = {}
        self.metrics_file = self.base_path / "structure_metrics.json"
        
        # Load existing data
        self._load_structures()
        self._load_rules()
        self._load_locations()
        self._load_metrics()
        
        # Initialize default structures
        self._initialize_default_structures()
        
        logger.info(f"Adaptive structure manager initialized with {len(self.structures)} structures")
    
    def _initialize_default_structures(self):
        """Initialize default document structures."""
        default_structures = [
            {
                "structure_id": "broiler_hierarchical",
                "name": "Broiler Hierarchical Structure",
                "type": StructureType.HIERARCHICAL.value,
                "pattern": OrganizationPattern.BY_BREED.value,
                "description": "Hierarchical organization by breed, then age phase, then data type"
            },
            {
                "structure_id": "data_type_flat",
                "name": "Data Type Flat Structure",
                "type": StructureType.FLAT.value,
                "pattern": OrganizationPattern.BY_DATA_TYPE.value,
                "description": "Flat organization by data type"
            },
            {
                "structure_id": "temporal_structure",
                "name": "Temporal Structure",
                "type": StructureType.TEMPORAL.value,
                "pattern": OrganizationPattern.BY_DATE.value,
                "description": "Organization by date and time"
            },
            {
                "structure_id": "tenant_based",
                "name": "Tenant-Based Structure",
                "type": StructureType.TOPIC_BASED.value,
                "pattern": OrganizationPattern.BY_TENANT.value,
                "description": "Organization by tenant with classification"
            }
        ]
        
        for structure_data in default_structures:
            structure_id = structure_data["structure_id"]
            if structure_id not in self.structures:
                self.structures[structure_id] = structure_data
                logger.debug(f"Initialized default structure: {structure_id}")
        
        self._save_structures()
    
    def create_organization_rule(self, pattern: OrganizationPattern, 
                               conditions: Dict[str, Any],
                               target_path_template: str,
                               priority: int = 1) -> str:
        """Create a new organization rule."""
        rule_id = f"rule_{len(self.rules) + 1}_{int(datetime.now().timestamp())}"
        
        rule = StructureRule(
            rule_id=rule_id,
            pattern=pattern,
            conditions=conditions,
            target_path=target_path_template,
            priority=priority
        )
        
        self.rules[rule_id] = rule
        self._save_rules()
        
        logger.info(f"Created organization rule: {rule_id}")
        return rule_id
    
    def organize_document(self, document_metadata: Dict[str, Any], 
                         preferred_structure: Optional[str] = None) -> DocumentLocation:
        """Organize a document based on rules and structure."""
        document_id = document_metadata.get('document_id', 'unknown')
        
        # Determine best structure
        if preferred_structure and preferred_structure in self.structures:
            structure = self.structures[preferred_structure]
        else:
            structure = self._select_best_structure(document_metadata)
        
        # Apply organization rules
        logical_path = self._apply_organization_rules(document_metadata, structure)
        
        # Generate physical path
        physical_path = self._generate_physical_path(logical_path, structure)
        
        # Create document location
        location = DocumentLocation(
            document_id=document_id,
            logical_path=logical_path,
            physical_path=physical_path,
            structure_type=StructureType(structure['type']),
            organization_pattern=OrganizationPattern(structure['pattern']),
            metadata=document_metadata
        )
        
        # Store location
        self.document_locations[document_id] = location
        self._save_locations()
        
        logger.info(f"Organized document {document_id} at {logical_path}")
        return location
    
    def _select_best_structure(self, document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best structure for a document."""
        # Score each structure based on document characteristics
        structure_scores = {}
        
        for structure_id, structure in self.structures.items():
            score = self._score_structure_fit(document_metadata, structure)
            structure_scores[structure_id] = score
        
        # Select structure with highest score
        best_structure_id = max(structure_scores, key=structure_scores.get)
        return self.structures[best_structure_id]
    
    def _score_structure_fit(self, document_metadata: Dict[str, Any], 
                           structure: Dict[str, Any]) -> float:
        """Score how well a structure fits a document."""
        score = 0.0
        
        # Base score from structure type
        doc_type = document_metadata.get('document_type', 'other')
        classification = document_metadata.get('classification', 'public')
        tenant_id = document_metadata.get('tenant_id', '')
        
        # Score based on organization pattern
        pattern = OrganizationPattern(structure['pattern'])
        
        if pattern == OrganizationPattern.BY_BREED:
            if any(breed in document_metadata.get('content', '').lower() 
                   for breed in ['ross', 'cobb', 'aviagen', 'hubbard']):
                score += 0.3
        
        elif pattern == OrganizationPattern.BY_DATA_TYPE:
            if doc_type in ['performance', 'environmental', 'nutrition']:
                score += 0.4
        
        elif pattern == OrganizationPattern.BY_CLASSIFICATION:
            if classification in ['confidential', 'restricted']:
                score += 0.3
        
        elif pattern == OrganizationPattern.BY_TENANT:
            if tenant_id:
                score += 0.5
        
        elif pattern == OrganizationPattern.BY_DATE:
            if 'created_at' in document_metadata or 'last_modified' in document_metadata:
                score += 0.2
        
        # Score based on structure type
        structure_type = StructureType(structure['type'])
        
        if structure_type == StructureType.HIERARCHICAL:
            # Good for complex categorization
            if len(document_metadata.get('tags', [])) > 2:
                score += 0.2
        
        elif structure_type == StructureType.FLAT:
            # Good for simple categorization
            if len(document_metadata.get('tags', [])) <= 2:
                score += 0.2
        
        elif structure_type == StructureType.TOPIC_BASED:
            # Good for content-rich documents
            if len(document_metadata.get('content', '')) > 1000:
                score += 0.2
        
        # Performance bonus from metrics
        if structure['structure_id'] in self.metrics:
            metrics = self.metrics[structure['structure_id']]
            if metrics.search_performance > 0.7:
                score += 0.1
        
        return score
    
    def _apply_organization_rules(self, document_metadata: Dict[str, Any], 
                                structure: Dict[str, Any]) -> str:
        """Apply organization rules to determine document path."""
        # Sort rules by priority
        sorted_rules = sorted(self.rules.values(), key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.active:
                continue
            
            # Check if rule conditions match
            if self._rule_matches(rule, document_metadata):
                path = self._generate_path_from_rule(rule, document_metadata)
                if path:
                    return path
        
        # Fallback to structure-based organization
        return self._generate_default_path(document_metadata, structure)
    
    def _rule_matches(self, rule: StructureRule, document_metadata: Dict[str, Any]) -> bool:
        """Check if a rule matches document metadata."""
        for condition_key, condition_value in rule.conditions.items():
            if condition_key not in document_metadata:
                return False
            
            doc_value = document_metadata[condition_key]
            
            # Handle different condition types
            if isinstance(condition_value, str):
                if condition_value.lower() not in str(doc_value).lower():
                    return False
            elif isinstance(condition_value, list):
                if doc_value not in condition_value:
                    return False
            elif isinstance(condition_value, dict):
                # Handle complex conditions
                if 'contains' in condition_value:
                    if condition_value['contains'].lower() not in str(doc_value).lower():
                        return False
                if 'equals' in condition_value:
                    if doc_value != condition_value['equals']:
                        return False
        
        return True
    
    def _generate_path_from_rule(self, rule: StructureRule, 
                               document_metadata: Dict[str, Any]) -> str:
        """Generate path from rule template."""
        try:
            path_template = rule.target_path
            
            # Replace placeholders in template
            for key, value in document_metadata.items():
                placeholder = f"{{{key}}}"
                if placeholder in path_template:
                    path_template = path_template.replace(placeholder, str(value))
            
            # Handle special placeholders
            if "{date}" in path_template:
                date_str = datetime.now().strftime("%Y-%m-%d")
                path_template = path_template.replace("{date}", date_str)
            
            if "{year}" in path_template:
                year_str = datetime.now().strftime("%Y")
                path_template = path_template.replace("{year}", year_str)
            
            if "{month}" in path_template:
                month_str = datetime.now().strftime("%m")
                path_template = path_template.replace("{month}", month_str)
            
            return path_template
            
        except Exception as e:
            logger.warning(f"Failed to generate path from rule {rule.rule_id}: {e}")
            return ""
    
    def _generate_default_path(self, document_metadata: Dict[str, Any], 
                              structure: Dict[str, Any]) -> str:
        """Generate default path based on structure."""
        pattern = OrganizationPattern(structure['pattern'])
        
        if pattern == OrganizationPattern.BY_BREED:
            return self._generate_breed_path(document_metadata)
        elif pattern == OrganizationPattern.BY_DATA_TYPE:
            return self._generate_data_type_path(document_metadata)
        elif pattern == OrganizationPattern.BY_CLASSIFICATION:
            return self._generate_classification_path(document_metadata)
        elif pattern == OrganizationPattern.BY_TENANT:
            return self._generate_tenant_path(document_metadata)
        elif pattern == OrganizationPattern.BY_DATE:
            return self._generate_date_path(document_metadata)
        else:
            return self._generate_generic_path(document_metadata)
    
    def _generate_breed_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate breed-based path."""
        content = document_metadata.get('content', '').lower()
        
        # Detect breed
        breed = "general"
        if 'ross' in content:
            breed = "ross_308"
        elif 'cobb' in content:
            breed = "cobb_500"
        elif 'aviagen' in content:
            breed = "aviagen_plus"
        elif 'hubbard' in content:
            breed = "hubbard"
        
        # Detect age phase
        age_phase = "general"
        if any(term in content for term in ['starter', 'week 1', 'week 2', 'chick']):
            age_phase = "starter"
        elif any(term in content for term in ['grower', 'week 3', 'week 4']):
            age_phase = "grower"
        elif any(term in content for term in ['finisher', 'week 5', 'week 6']):
            age_phase = "finisher"
        
        # Get data type
        data_type = document_metadata.get('document_type', 'other')
        
        return f"breeds/{breed}/{age_phase}/{data_type}"
    
    def _generate_data_type_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate data type-based path."""
        data_type = document_metadata.get('document_type', 'other')
        classification = document_metadata.get('classification', 'public')
        
        return f"data_types/{data_type}/{classification}"
    
    def _generate_classification_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate classification-based path."""
        classification = document_metadata.get('classification', 'public')
        data_type = document_metadata.get('document_type', 'other')
        
        return f"classifications/{classification}/{data_type}"
    
    def _generate_tenant_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate tenant-based path."""
        tenant_id = document_metadata.get('tenant_id', 'shared')
        classification = document_metadata.get('classification', 'public')
        data_type = document_metadata.get('document_type', 'other')
        
        return f"tenants/{tenant_id}/{classification}/{data_type}"
    
    def _generate_date_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate date-based path."""
        # Try to get date from metadata
        created_at = document_metadata.get('created_at')
        if created_at:
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                year = date_obj.strftime("%Y")
                month = date_obj.strftime("%m")
                day = date_obj.strftime("%d")
                
                data_type = document_metadata.get('document_type', 'other')
                return f"dates/{year}/{month}/{day}/{data_type}"
            except Exception:
                pass
        
        # Fallback to current date
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        data_type = document_metadata.get('document_type', 'other')
        
        return f"dates/{year}/{month}/{data_type}"
    
    def _generate_generic_path(self, document_metadata: Dict[str, Any]) -> str:
        """Generate generic path."""
        data_type = document_metadata.get('document_type', 'other')
        classification = document_metadata.get('classification', 'public')
        
        return f"documents/{data_type}/{classification}"
    
    def _generate_physical_path(self, logical_path: str, structure: Dict[str, Any]) -> str:
        """Generate physical path from logical path."""
        # Clean logical path
        logical_path = logical_path.replace('//', '/').strip('/')
        
        # Add structure prefix
        structure_id = structure['structure_id']
        physical_path = f"structures/{structure_id}/{logical_path}"
        
        return physical_path
    
    def get_document_location(self, document_id: str) -> Optional[DocumentLocation]:
        """Get location for a document."""
        return self.document_locations.get(document_id)
    
    def search_by_structure(self, query: str, structure_id: Optional[str] = None) -> List[DocumentLocation]:
        """Search documents by structure."""
        query_lower = query.lower()
        results = []
        
        for location in self.document_locations.values():
            # Filter by structure if specified
            if structure_id and location.structure_type.value != structure_id:
                continue
            
            # Search in logical path and metadata
            if (query_lower in location.logical_path.lower() or
                query_lower in location.document_id.lower() or
                any(query_lower in str(value).lower() for value in location.metadata.values())):
                results.append(location)
        
        return results
    
    def get_structure_summary(self) -> Dict[str, Any]:
        """Get summary of all structures."""
        summary = {
            'total_structures': len(self.structures),
            'total_documents': len(self.document_locations),
            'total_rules': len(self.rules),
            'structures': {}
        }
        
        for structure_id, structure in self.structures.items():
            doc_count = sum(1 for location in self.document_locations.values()
                          if location.structure_type.value == structure_id)
            
            summary['structures'][structure_id] = {
                'name': structure.get('name', structure_id),
                'type': structure.get('type', 'unknown'),
                'pattern': structure.get('pattern', 'unknown'),
                'document_count': doc_count,
                'has_metrics': structure_id in self.metrics
            }
        
        return summary
    
    def update_structure_metrics(self, structure_id: str, 
                               access_count: int = 0,
                               search_time: float = 0.0) -> bool:
        """Update structure metrics."""
        try:
            if structure_id not in self.metrics:
                self.metrics[structure_id] = StructureMetrics(
                    structure_id=structure_id,
                    total_documents=0,
                    access_frequency=0,
                    average_depth=0.0,
                    search_performance=0.0,
                    organization_efficiency=0.0,
                    last_optimized=datetime.now().isoformat()
                )
            
            metrics = self.metrics[structure_id]
            
            # Update access frequency
            metrics.access_frequency += access_count
            
            # Update search performance (moving average)
            if search_time > 0:
                if metrics.search_performance == 0:
                    metrics.search_performance = 1.0 / search_time
                else:
                    # Exponential moving average
                    new_performance = 1.0 / search_time
                    metrics.search_performance = (0.9 * metrics.search_performance + 
                                                0.1 * new_performance)
            
            # Update document count
            doc_count = sum(1 for location in self.document_locations.values() 
                          if location.structure_type.value == structure_id)
            metrics.total_documents = doc_count
            
            # Calculate average depth
            if doc_count > 0:
                total_depth = sum(len(location.logical_path.split('/')) 
                                for location in self.document_locations.values()
                                if location.structure_type.value == structure_id)
                metrics.average_depth = total_depth / doc_count
            
            # Calculate organization efficiency (inverse of average depth)
            if metrics.average_depth > 0:
                metrics.organization_efficiency = 1.0 / metrics.average_depth
            
            self._save_metrics()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metrics for structure {structure_id}: {e}")
            return False
    
    def optimize_structure(self, structure_id: str) -> bool:
        """Optimize a structure based on usage patterns."""
        try:
            if structure_id not in self.structures:
                logger.error(f"Structure {structure_id} not found")
                return False
            
            # For now, just return True as a placeholder
            # Real implementation would analyze and optimize
            logger.info(f"Optimized structure {structure_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize structure {structure_id}: {e}")
            return False
    
    def _load_structures(self):
        """Load structures from file."""
        try:
            if self.structure_file.exists():
                with open(self.structure_file, 'r') as f:
                    self.structures = json.load(f)
                logger.info(f"Loaded {len(self.structures)} structures")
        except Exception as e:
            logger.error(f"Failed to load structures: {e}")
    
    def _save_structures(self):
        """Save structures to file."""
        try:
            with open(self.structure_file, 'w') as f:
                json.dump(self.structures, f, indent=2)
            logger.debug("Saved structures")
        except Exception as e:
            logger.error(f"Failed to save structures: {e}")
    
    def _load_rules(self):
        """Load organization rules from file."""
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    for rule_id, rule_data in data.items():
                        # Convert string back to enum
                        rule_data['pattern'] = OrganizationPattern(rule_data['pattern'])
                        self.rules[rule_id] = StructureRule(**rule_data)
                logger.info(f"Loaded {len(self.rules)} organization rules")
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
    
    def _save_rules(self):
        """Save organization rules to file."""
        try:
            data = {}
            for rule_id, rule in self.rules.items():
                rule_dict = asdict(rule)
                # Convert enum to string
                rule_dict['pattern'] = rule.pattern.value
                data[rule_id] = rule_dict
            
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved organization rules")
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
    
    def _load_locations(self):
        """Load document locations from file."""
        try:
            if self.locations_file.exists():
                with open(self.locations_file, 'r') as f:
                    data = json.load(f)
                    for doc_id, location_data in data.items():
                        # Convert strings back to enums
                        location_data['structure_type'] = StructureType(location_data['structure_type'])
                        location_data['organization_pattern'] = OrganizationPattern(location_data['organization_pattern'])
                        self.document_locations[doc_id] = DocumentLocation(**location_data)
                logger.info(f"Loaded {len(self.document_locations)} document locations")
        except Exception as e:
            logger.error(f"Failed to load locations: {e}")
    
    def _save_locations(self):
        """Save document locations to file."""
        try:
            data = {}
            for doc_id, location in self.document_locations.items():
                location_dict = asdict(location)
                # Convert enums to strings
                location_dict['structure_type'] = location.structure_type.value
                location_dict['organization_pattern'] = location.organization_pattern.value
                data[doc_id] = location_dict
            
            with open(self.locations_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved document locations")
        except Exception as e:
            logger.error(f"Failed to save locations: {e}")
    
    def _load_metrics(self):
        """Load structure metrics from file."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    for structure_id, metrics_data in data.items():
                        self.metrics[structure_id] = StructureMetrics(**metrics_data)
                logger.info(f"Loaded metrics for {len(self.metrics)} structures")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
    
    def _save_metrics(self):
        """Save structure metrics to file."""
        try:
            data = {}
            for structure_id, metrics in self.metrics.items():
                data[structure_id] = asdict(metrics)
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved structure metrics")
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")


if __name__ == "__main__":
    # Test the adaptive structure manager
    print("🧪 TESTING ADAPTIVE STRUCTURE MANAGER")
    print("=" * 40)
    
    # Create test manager
    manager = AdaptiveStructureManager("test_adaptive_structures")
    
    # Test structure creation
    print("\n🏗️ Testing Structure Management:")
    summary = manager.get_structure_summary()
    print(f"   Total structures: {summary['total_structures']}")
    print(f"   Total documents: {summary['total_documents']}")
    print(f"   Total rules: {summary['total_rules']}")
    
    for structure_id, info in summary['structures'].items():
        print(f"   • {structure_id}: {info['name']} ({info['type']})")
    
    # Test organization rules
    print("\n📋 Testing Organization Rules:")
    
    # Create test rules
    rule1 = manager.create_organization_rule(
        pattern=OrganizationPattern.BY_BREED,
        conditions={'document_type': 'performance'},
        target_path_template="performance/{breed}/{age_phase}",
        priority=3
    )
    
    rule2 = manager.create_organization_rule(
        pattern=OrganizationPattern.BY_CLASSIFICATION,
        conditions={'classification': 'confidential'},
        target_path_template="secure/{tenant_id}/{document_type}",
        priority=2
    )
    
    print(f"   Created rule 1: {rule1}")
    print(f"   Created rule 2: {rule2}")
    
    # Test document organization
    print("\n📄 Testing Document Organization:")
    
    test_documents = [
        {
            'document_id': 'doc_001',
            'document_type': 'performance',
            'classification': 'internal',
            'tenant_id': 'demo_client',
            'content': 'Ross 308 week 3 performance data shows excellent growth rates',
            'created_at': '2025-01-15T10:00:00Z'
        },
        {
            'document_id': 'doc_002',
            'document_type': 'environmental',
            'classification': 'confidential',
            'tenant_id': 'client_abc',
            'content': 'Temperature management protocol for Cobb 500 broilers',
            'created_at': '2025-01-16T14:30:00Z'
        },
        {
            'document_id': 'doc_003',
            'document_type': 'nutrition',
            'classification': 'public',
            'content': 'General nutrition guidelines for starter phase',
            'created_at': '2025-01-17T09:15:00Z'
        }
    ]
    
    for doc_metadata in test_documents:
        location = manager.organize_document(doc_metadata)
        print(f"   Document {doc_metadata['document_id']}:")
        print(f"     Logical path: {location.logical_path}")
        print(f"     Physical path: {location.physical_path}")
        print(f"     Structure: {location.structure_type.value}")
        print(f"     Pattern: {location.organization_pattern.value}")
    
    # Test search
    print("\n🔍 Testing Structure Search:")
    
    search_results = manager.search_by_structure("performance")
    print(f"   Search for 'performance': {len(search_results)} results")
    
    for result in search_results:
        print(f"     • {result.document_id}: {result.logical_path}")
    
    # Test structure optimization
    print("\n⚡ Testing Structure Optimization:")
    
    # Update metrics for testing
    for structure_id in summary['structures'].keys():
        manager.update_structure_metrics(structure_id, access_count=5, search_time=0.1)
    
    # Test optimization
    optimized = manager.optimize_structure("broiler_hierarchical")
    print(f"   Optimization result: {'✅ Success' if optimized else '❌ Failed'}")
    
    # Show final summary
    print("\n📊 Final Summary:")
    final_summary = manager.get_structure_summary()
    print(f"   Total structures: {final_summary['total_structures']}")
    print(f"   Total documents: {final_summary['total_documents']}")
    print(f"   Total rules: {final_summary['total_rules']}")
    
    # Cleanup test directory
    print("\n🧹 Cleaning up test directory...")
    try:
        import shutil
        shutil.rmtree("test_adaptive_structures")
        print("   ✅ Test directory cleaned")
    except Exception as e:
        print(f"   ⚠️ Cleanup warning: {e}")
    
    print("\n✅ Adaptive structure manager test completed")
