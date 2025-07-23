#!/usr/bin/env python3
"""
Tenant Document Manager
Multi-tenant document management with security and isolation
"""

import os
import json
import uuid
import shutil
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

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


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentType(Enum):
    """Document types."""
    PERFORMANCE = "performance"
    ENVIRONMENTAL = "environmental"
    NUTRITION = "nutrition"
    TECHNICAL = "technical"
    REPORT = "report"
    PROTOCOL = "protocol"
    STANDARD = "standard"
    OTHER = "other"


@dataclass
class TenantConfig:
    """Configuration for a tenant."""
    tenant_id: str
    tenant_name: str
    data_classification: str
    allowed_document_types: List[str] = field(default_factory=list)
    storage_quota_mb: int = 1000
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: Optional[str] = None
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentMetadata:
    """Metadata for a document."""
    document_id: str
    tenant_id: str
    filename: str
    file_path: str
    file_size: int
    document_type: str
    classification: str
    created_at: str
    last_modified: str
    checksum: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantStorageInfo:
    """Storage information for a tenant."""
    tenant_id: str
    total_documents: int
    total_size_mb: float
    quota_mb: int
    usage_percentage: float
    last_updated: str
    document_types: Dict[str, int] = field(default_factory=dict)
    classifications: Dict[str, int] = field(default_factory=dict)


class TenantDocumentManager:
    """Multi-tenant document manager with security and isolation."""
    
    def __init__(self, base_storage_path: str = "tenant_storage", base_index_path: str = "tenant_indexes"):
        """Initialize tenant document manager."""
        self.base_storage_path = Path(base_storage_path)
        self.base_index_path = Path(base_index_path)
        
        # Create base directories
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        self.base_index_path.mkdir(parents=True, exist_ok=True)
        
        # Tenant registry
        self.tenants = {}
        self.tenant_config_file = self.base_storage_path / "tenant_registry.json"
        
        # Document registry
        self.documents = {}
        self.document_registry_file = self.base_storage_path / "document_registry.json"
        
        # Load existing data
        self._load_tenant_registry()
        self._load_document_registry()
        
        logger.info(f"Tenant manager initialized with {len(self.tenants)} tenants")
    
    def register_tenant(self, tenant_config: TenantConfig) -> bool:
        """Register a new tenant."""
        try:
            # Validate tenant configuration
            if not self._validate_tenant_config(tenant_config):
                return False
            
            # Check if tenant already exists
            if tenant_config.tenant_id in self.tenants:
                logger.warning(f"Tenant {tenant_config.tenant_id} already exists")
                return False
            
            # Create tenant directory structure
            tenant_storage_path = self.base_storage_path / tenant_config.tenant_id
            tenant_index_path = self.base_index_path / tenant_config.tenant_id
            
            tenant_storage_path.mkdir(parents=True, exist_ok=True)
            tenant_index_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories based on classification
            for classification in DataClassification:
                (tenant_storage_path / classification.value).mkdir(exist_ok=True)
            
            # Register tenant
            self.tenants[tenant_config.tenant_id] = tenant_config
            
            # Save tenant registry
            self._save_tenant_registry()
            
            logger.info(f"Registered tenant: {tenant_config.tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tenant {tenant_config.tenant_id}: {e}")
            return False
    
    def _validate_tenant_config(self, config: TenantConfig) -> bool:
        """Validate tenant configuration."""
        # Check required fields
        if not config.tenant_id or not config.tenant_name:
            logger.error("Tenant ID and name are required")
            return False
        
        # Validate tenant ID format
        if not config.tenant_id.replace('_', '').isalnum():
            logger.error("Tenant ID must be alphanumeric with underscores")
            return False
        
        # Validate data classification
        if config.data_classification not in [c.value for c in DataClassification]:
            logger.error(f"Invalid data classification: {config.data_classification}")
            return False
        
        # Validate document types
        valid_types = [t.value for t in DocumentType]
        for doc_type in config.allowed_document_types:
            if doc_type not in valid_types:
                logger.error(f"Invalid document type: {doc_type}")
                return False
        
        return True
    
    def store_document(self, tenant_id: str, file_path: str, 
                      classification: str, document_type: str,
                      tags: Optional[List[str]] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Store a document for a tenant."""
        try:
            # Validate tenant
            if tenant_id not in self.tenants:
                logger.error(f"Tenant {tenant_id} not found")
                return None
            
            tenant_config = self.tenants[tenant_id]
            
            # Validate document type
            if document_type not in tenant_config.allowed_document_types:
                logger.error(f"Document type {document_type} not allowed for tenant {tenant_id}")
                return None
            
            # Validate classification
            if classification not in [c.value for c in DataClassification]:
                logger.error(f"Invalid classification: {classification}")
                return None
            
            # Check file exists
            source_path = Path(file_path)
            if not source_path.exists():
                logger.error(f"Source file not found: {file_path}")
                return None
            
            # Check storage quota
            if not self._check_storage_quota(tenant_id, source_path.stat().st_size):
                logger.error(f"Storage quota exceeded for tenant {tenant_id}")
                return None
            
            # Generate document ID
            document_id = str(uuid.uuid4())
            
            # Determine destination path
            tenant_storage_path = self.base_storage_path / tenant_id / classification
            dest_filename = f"{document_id}_{source_path.name}"
            dest_path = tenant_storage_path / dest_filename
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Calculate checksum
            checksum = self._calculate_checksum(dest_path)
            
            # Create document metadata
            doc_metadata = DocumentMetadata(
                document_id=document_id,
                tenant_id=tenant_id,
                filename=source_path.name,
                file_path=str(dest_path),
                file_size=dest_path.stat().st_size,
                document_type=document_type,
                classification=classification,
                created_at=datetime.now().isoformat(),
                last_modified=datetime.fromtimestamp(dest_path.stat().st_mtime).isoformat(),
                checksum=checksum,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Store document metadata
            self.documents[document_id] = doc_metadata
            
            # Save document registry
            self._save_document_registry()
            
            # Update tenant last accessed
            tenant_config.last_accessed = datetime.now().isoformat()
            self._save_tenant_registry()
            
            logger.info(f"Stored document {document_id} for tenant {tenant_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to store document for tenant {tenant_id}: {e}")
            return None
    
    def _check_storage_quota(self, tenant_id: str, file_size: int) -> bool:
        """Check if adding a file would exceed storage quota."""
        tenant_config = self.tenants[tenant_id]
        
        # Calculate current usage
        current_usage = self._calculate_tenant_usage(tenant_id)
        
        # Check if adding this file would exceed quota
        new_usage_mb = (current_usage + file_size) / (1024 * 1024)
        
        return new_usage_mb <= tenant_config.storage_quota_mb
    
    def _calculate_tenant_usage(self, tenant_id: str) -> int:
        """Calculate total storage usage for a tenant."""
        total_size = 0
        
        for doc_id, doc_metadata in self.documents.items():
            if doc_metadata.tenant_id == tenant_id:
                total_size += doc_metadata.file_size
        
        return total_size
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def get_tenant_documents(self, tenant_id: str, 
                           classification: Optional[str] = None,
                           document_type: Optional[str] = None) -> List[DocumentMetadata]:
        """Get documents for a tenant."""
        if tenant_id not in self.tenants:
            return []
        
        tenant_docs = []
        
        for doc_id, doc_metadata in self.documents.items():
            if doc_metadata.tenant_id != tenant_id:
                continue
            
            if classification and doc_metadata.classification != classification:
                continue
            
            if document_type and doc_metadata.document_type != document_type:
                continue
            
            tenant_docs.append(doc_metadata)
        
        return tenant_docs
    
    def get_tenant_storage_info(self, tenant_id: str) -> Optional[TenantStorageInfo]:
        """Get storage information for a tenant."""
        if tenant_id not in self.tenants:
            return None
        
        tenant_config = self.tenants[tenant_id]
        tenant_docs = self.get_tenant_documents(tenant_id)
        
        # Calculate totals
        total_size = sum(doc.file_size for doc in tenant_docs)
        total_size_mb = total_size / (1024 * 1024)
        usage_percentage = (total_size_mb / tenant_config.storage_quota_mb) * 100
        
        # Count by document type
        doc_types = {}
        for doc in tenant_docs:
            doc_types[doc.document_type] = doc_types.get(doc.document_type, 0) + 1
        
        # Count by classification
        classifications = {}
        for doc in tenant_docs:
            classifications[doc.classification] = classifications.get(doc.classification, 0) + 1
        
        return TenantStorageInfo(
            tenant_id=tenant_id,
            total_documents=len(tenant_docs),
            total_size_mb=total_size_mb,
            quota_mb=tenant_config.storage_quota_mb,
            usage_percentage=usage_percentage,
            last_updated=datetime.now().isoformat(),
            document_types=doc_types,
            classifications=classifications
        )
    
    def list_tenants(self) -> List[TenantConfig]:
        """List all tenants."""
        return list(self.tenants.values())
    
    def _load_tenant_registry(self):
        """Load tenant registry from file."""
        try:
            if self.tenant_config_file.exists():
                with open(self.tenant_config_file, 'r') as f:
                    data = json.load(f)
                
                for tenant_id, tenant_data in data.items():
                    self.tenants[tenant_id] = TenantConfig(**tenant_data)
                
                logger.info(f"Loaded {len(self.tenants)} tenants from registry")
        except Exception as e:
            logger.error(f"Failed to load tenant registry: {e}")
    
    def _save_tenant_registry(self):
        """Save tenant registry to file."""
        try:
            data = {}
            for tenant_id, tenant_config in self.tenants.items():
                data[tenant_id] = asdict(tenant_config)
            
            with open(self.tenant_config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved tenant registry")
        except Exception as e:
            logger.error(f"Failed to save tenant registry: {e}")
    
    def _load_document_registry(self):
        """Load document registry from file."""
        try:
            if self.document_registry_file.exists():
                with open(self.document_registry_file, 'r') as f:
                    data = json.load(f)
                
                for doc_id, doc_data in data.items():
                    self.documents[doc_id] = DocumentMetadata(**doc_data)
                
                logger.info(f"Loaded {len(self.documents)} documents from registry")
        except Exception as e:
            logger.error(f"Failed to load document registry: {e}")
    
    def _save_document_registry(self):
        """Save document registry to file."""
        try:
            data = {}
            for doc_id, doc_metadata in self.documents.items():
                data[doc_id] = asdict(doc_metadata)
            
            with open(self.document_registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved document registry")
        except Exception as e:
            logger.error(f"Failed to save document registry: {e}")


class TenantAwareVectorStore:
    """Vector store with tenant isolation."""
    
    def __init__(self, base_index_path: str):
        """Initialize tenant-aware vector store."""
        self.base_index_path = Path(base_index_path)
        self.base_index_path.mkdir(parents=True, exist_ok=True)
        
        # Tenant-specific vector stores
        self.tenant_stores = {}
        
        logger.info("Tenant-aware vector store initialized")
    
    def get_tenant_store(self, tenant_id: str):
        """Get or create vector store for a tenant."""
        if tenant_id not in self.tenant_stores:
            # Create tenant-specific index path
            tenant_index_path = self.base_index_path / tenant_id
            tenant_index_path.mkdir(exist_ok=True)
            
            # Initialize tenant store (would use actual vector store implementation)
            self.tenant_stores[tenant_id] = {
                'index_path': tenant_index_path,
                'initialized': False
            }
        
        return self.tenant_stores[tenant_id]


if __name__ == "__main__":
    # Test the tenant document manager
    print("🧪 TESTING TENANT DOCUMENT MANAGER")
    print("=" * 40)
    
    # Create test manager
    manager = TenantDocumentManager("test_tenant_storage", "test_tenant_indexes")
    
    # Test tenant registration
    print("\n🏢 Testing Tenant Registration:")
    
    test_tenant = TenantConfig(
        tenant_id="test_tenant_001",
        tenant_name="Test Tenant 001",
        data_classification="confidential",
        allowed_document_types=["performance", "environmental", "nutrition"],
        storage_quota_mb=50
    )
    
    success = manager.register_tenant(test_tenant)
    print(f"   Tenant registration: {'Success' if success else 'Failed'}")
    
    # Test tenant listing
    print("\n📋 Testing Tenant Listing:")
    tenants = manager.list_tenants()
    print(f"   Total tenants: {len(tenants)}")
    
    for tenant in tenants:
        print(f"   \u2022 {tenant.tenant_id}: {tenant.tenant_name} ({tenant.data_classification})")
    
    # Test storage info
    print("\n📊 Testing Storage Info:")
    for tenant in tenants:
        storage_info = manager.get_tenant_storage_info(tenant.tenant_id)
        if storage_info:
            print(f"   Tenant {tenant.tenant_id}:")
            print(f"     Documents: {storage_info.total_documents}")
            print(f"     Storage: {storage_info.total_size_mb:.2f} MB / {storage_info.quota_mb} MB")
            print(f"     Usage: {storage_info.usage_percentage:.1f}%")
    
    print("\n✅ Tenant document manager test completed")
