#!/usr/bin/env python3
"""
RAG Index Builder - Multi-Tenant Support
Clean code compliant version using translation_manager
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import translation manager
try:
    from core.notifications.translation_manager import EnhancedTranslationManager
    translation_manager = EnhancedTranslationManager()
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    # Fallback messages
    MESSAGES = {
        'setup_environment': "Configuring RAG environment...",
        'project_root_found': "Project root:",
        'openai_configured': "OpenAI key configured",
        'no_openai_key': "No OpenAI key found - will use local models only",
        'initializing_embedder': "Initializing OptimizedRAGEmbedder...",
        'embedder_ready': "OptimizedRAGEmbedder initialized",
        'discovering_tenants': "Discovering tenants in:",
        'tenant_found': "Found tenant:",
        'tenants_discovered': "Discovered tenants:",
        'building_index': "Building index for tenant:",
        'files_found': "Found files",
        'processing_documents': "Processing documents...",
        'processing_success': "Successfully processed documents",
        'processing_failed': "Processing failed:",
        'no_documents': "No documents found for tenant",
        'verifying_index': "Verifying index for tenant:",
        'system_ready': "System ready",
        'retrieval_test_passed': "Retrieval test passed - found results",
        'retrieval_test_failed': "Retrieval test returned no results",
        'verification_failed': "Verification failed:",
        'creating_summary': "Creating build summary...",
        'summary_saved': "Build summary saved:",
        'build_completed': "RAG INDEX BUILD COMPLETED!",
        'successful_tenants': "Successful tenants:",
        'failed_tenants': "Failed tenants:",
        'total_time': "Total time:",
        'index_location': "Index location:",
        'next_steps': "Next steps:",
        'test_application': "Test with: streamlit run apps/app_expert_local.py",
        'verify_queries': "Verify queries work correctly",
        'build_failed': "Build failed",
        'build_successful': "Build successful",
        'build_interrupted': "Build interrupted",
        'fatal_error': "Fatal error:"
    }


def get_message(key: str, *args) -> str:
    """Get translated message or fallback."""
    if TRANSLATION_AVAILABLE:
        try:
            return translation_manager.get(f"rag.build.{key}").format(*args)
        except:
            pass
    
    return MESSAGES.get(key, key).format(*args) if args else MESSAGES.get(key, key)


def setup_environment():
    """Configure environment and paths."""
    print(f"🔧 {get_message('setup_environment')}")
    
    # Get project root
    current_path = Path.cwd()
    if current_path.name == "rag" and (current_path.parent / "core").exists():
        project_root = current_path.parent
        print(f"📁 Detected execution from rag directory, moving to project root: {project_root}")
        os.chdir(project_root)
    else:
        project_root = current_path
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    print(f"✅ {get_message('project_root_found')} {project_root}")
    
    # Check OpenAI key
    openai_key = os.environ.get('OPENAI_API_KEY')
    if not openai_key:
        try:
            import streamlit as st
            openai_key = st.secrets.get('openai_key')
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
        except:
            pass
    
    if openai_key:
        print(f"✅ {get_message('openai_configured')}")
    else:
        print(f"⚠️ {get_message('no_openai_key')}")
    
    return project_root


def discover_tenants(documents_directory: Path) -> List[str]:
    """Discover available tenants from documents directory."""
    print(f"\n🔍 {get_message('discovering_tenants')} {documents_directory}")
    
    tenants = []
    
    # Look for tenant directories
    if documents_directory.exists():
        for item in documents_directory.iterdir():
            if item.is_dir():
                # Tenant directories start with "tenant_" or are "shared"
                if item.name.startswith("tenant_") or item.name == "shared":
                    tenants.append(item.name)
                    print(f"   {get_message('tenant_found')} {item.name}")
    
    if not tenants:
        print("   No tenant directories found, using default structure")
        # Check if documents exist directly
        if documents_directory.exists() and any(documents_directory.iterdir()):
            tenants = ["shared"]  # Default tenant
    
    print(f"✅ {get_message('tenants_discovered')} {len(tenants)} tenant(s): {tenants}")
    return tenants


def build_tenant_index(tenant_id: str, documents_path: Path, embedder) -> Dict[str, Any]:
    """Build RAG index for a specific tenant."""
    print(f"\n📄 {get_message('building_index')} {tenant_id}")
    
    tenant_documents_path = documents_path / tenant_id
    
    if not tenant_documents_path.exists():
        error_message = f"Documents path not found: {tenant_documents_path}"
        print(f"❌ {error_message}")
        return {"success": False, "error": error_message}
    
    # Count documents
    document_files = list(tenant_documents_path.rglob("*"))
    document_files = [f for f in document_files if f.is_file() and not f.name.startswith('.')]
    print(f"   📊 {get_message('files_found')} {len(document_files)}")
    
    if not document_files:
        print(f"   ⚠️ {get_message('no_documents')} {tenant_id}")
        return {"success": False, "error": "No documents found"}
    
    # Show sample files
    for i, document_file in enumerate(document_files[:5]):
        print(f"   📄 {document_file.relative_to(tenant_documents_path)}")
    if len(document_files) > 5:
        print(f"   📄 ... and {len(document_files) - 5} more files")
    
    try:
        # Process documents using RAG embedder
        print(f"   🔄 {get_message('processing_documents')}")
        
        result = embedder.process_documents(
            documents_path=str(tenant_documents_path),
            tenant_id=tenant_id,
            force_rebuild=True
        )
        
        if result.get('status') == 'success':
            documents_processed = result.get('documents_processed', 0)
            processing_time = result.get('processing_time', 0)
            print(f"   ✅ {get_message('processing_success')} {documents_processed}")
            print(f"   ⏱️ Processing time: {processing_time:.2f}s")
            return {
                "success": True,
                "tenant_id": tenant_id,
                "documents_processed": documents_processed,
                "processing_time": processing_time,
                "total_chunks": result.get('total_chunks', 0)
            }
        else:
            error_message = result.get('message', 'Unknown error')
            print(f"   ❌ {get_message('processing_failed')} {error_message}")
            return {"success": False, "error": error_message}
    
    except Exception as e:
        print(f"   ❌ Exception during processing: {e}")
        return {"success": False, "error": str(e)}


def verify_index(tenant_id: str, embedder) -> bool:
    """Verify that the index was created successfully."""
    print(f"\n🧪 {get_message('verifying_index')} {tenant_id}")
    
    try:
        # Try to get system status
        status = embedder.get_system_status()
        
        if status.get('system_ready', False):
            print(f"   ✅ {get_message('system_ready')}")
            
            # Show statistics
            stats = status.get('processing_stats', {})
            print(f"   📊 Documents processed: {stats.get('documents_processed', 0)}")
            print(f"   📊 Total chunks: {stats.get('total_chunks', 0)}")
            
            # Try simple retrieval test
            if hasattr(embedder, 'retriever') and embedder.retriever:
                try:
                    # Test query
                    test_result = embedder.retriever.get_contextual_diagnosis("Ross 308 temperature", k=3)
                    if test_result and test_result.get('documents'):
                        print(f"   ✅ {get_message('retrieval_test_passed')} {len(test_result['documents'])}")
                    else:
                        print(f"   ⚠️ {get_message('retrieval_test_failed')}")
                except Exception as e:
                    print(f"   ⚠️ Retrieval test failed: {e}")
            
            return True
        else:
            print(f"   ❌ System not ready")
            return False
    
    except Exception as e:
        print(f"   ❌ {get_message('verification_failed')} {e}")
        return False


def create_build_summary(tenant_results: List[Dict], build_time: float, output_directory: Path):
    """Create a summary of the build process."""
    print(f"\n📝 {get_message('creating_summary')}")
    
    summary = {
        "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_duration": build_time,
        "tenants_processed": len(tenant_results),
        "successful_tenants": len([r for r in tenant_results if r.get('success')]),
        "failed_tenants": len([r for r in tenant_results if not r.get('success')]),
        "total_documents": sum(r.get('documents_processed', 0) for r in tenant_results if r.get('success')),
        "total_chunks": sum(r.get('total_chunks', 0) for r in tenant_results if r.get('success')),
        "tenant_details": tenant_results
    }
    
    # Save summary
    summary_file = output_directory / "build_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ {get_message('summary_saved')} {summary_file}")
    return summary


def main():
    """Main function for RAG building."""
    print("🚀 RAG INDEX BUILDER")
    print("Multi-tenant support with OptimizedRAGEmbedder")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        # Setup environment
        project_root = setup_environment()
        
        # Import the RAG embedder
        print(f"\n🔄 {get_message('initializing_embedder')}")
        
        try:
            from rag.embedder import OptimizedRAGEmbedder
            
            # Create embedder with optimized configuration
            embedder_config = {
                'model_name': 'all-MiniLM-L6-v2',  # Fast and efficient
                'chunk_size': 256,  # Optimal for broiler data
                'overlap': 64,
                'use_adaptive_chunking': True,
                'enable_intelligent_routing': True,
                'enable_hybrid_search': True,
                'tenant_isolation': True
            }
            
            embedder = OptimizedRAGEmbedder(config=embedder_config)
            
            if not embedder.available:
                print("❌ RAG embedder not available - missing dependencies")
                print("\n💡 Required packages:")
                print("   pip install sentence-transformers faiss-cpu")
                return False
            
            print(f"✅ {get_message('embedder_ready')}")
            
            # Show available features
            features = embedder.available_features
            print(f"   📊 Available features: {sum(features.values())}/{len(features)}")
            for feature, available in features.items():
                status = "✅" if available else "❌"
                print(f"   {status} {feature}")
        
        except ImportError as e:
            print(f"❌ Failed to import OptimizedRAGEmbedder: {e}")
            return False
        
        # Discover tenants
        documents_directory = project_root / "documents"
        tenants = discover_tenants(documents_directory)
        
        if not tenants:
            print("❌ No tenants found")
            return False
        
        # Build indexes for each tenant
        tenant_results = []
        
        for tenant_id in tenants:
            result = build_tenant_index(tenant_id, documents_directory, embedder)
            tenant_results.append(result)
            
            # Verify the index
            if result.get('success'):
                verify_index(tenant_id, embedder)
        
        # Create build summary
        build_time = time.time() - start_time
        rag_index_directory = project_root / "rag_index"
        rag_index_directory.mkdir(exist_ok=True)
        
        summary = create_build_summary(tenant_results, build_time, rag_index_directory)
        
        # Final summary
        print("\n" + "=" * 70)
        print(f"🎉 {get_message('build_completed')}")
        print("=" * 70)
        
        successful = [r for r in tenant_results if r.get('success')]
        failed = [r for r in tenant_results if not r.get('success')]
        
        print(f"✅ {get_message('successful_tenants')} {len(successful)}")
        for result in successful:
            tenant = result['tenant_id']
            documents = result.get('documents_processed', 0)
            chunks = result.get('total_chunks', 0)
            print(f"   📄 {tenant}: {documents} documents, {chunks} chunks")
        
        if failed:
            print(f"❌ {get_message('failed_tenants')} {len(failed)}")
            for result in failed:
                tenant = result.get('tenant_id', 'unknown')
                error = result.get('error', 'Unknown error')
                print(f"   ❌ {tenant}: {error}")
        
        print(f"⏱️ {get_message('total_time')} {build_time:.1f} seconds")
        print(f"📁 {get_message('index_location')} {rag_index_directory}")
        
        print(f"\n🚀 {get_message('next_steps')}")
        print(f"1. Your RAG indexes are ready")
        print(f"2. {get_message('test_application')}")
        print(f"3. {get_message('verify_queries')}")
        
        return len(successful) > 0
    
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print(f"\n❌ {get_message('build_failed')}")
            sys.exit(1)
        else:
            print(f"\n✅ {get_message('build_successful')}")
    except KeyboardInterrupt:
        print(f"\n\n🛑 {get_message('build_interrupted')}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ {get_message('fatal_error')} {e}")
        sys.exit(1)