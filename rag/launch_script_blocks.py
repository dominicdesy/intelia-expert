"""
RAG builder with Prefect Blocks integration.
Located in rag/ directory.
"""

import os
import sys
import asyncio
from pathlib import Path


async def setup_environment_with_blocks():
    """Configure environment by loading secrets from Prefect Blocks."""
    print("🔧 Configuring with Prefect Blocks...")
    
    # Script is in rag/, project root is parent
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Set RAG paths
    rag_index_path = project_root / "rag_index"
    os.environ['RAG_INDEX_PATH'] = str(rag_index_path)
    rag_index_path.mkdir(exist_ok=True)
    
    # Load secrets from Prefect Blocks
    try:
        from prefect.blocks.system import Secret
        
        # Load OpenAI key from blocks
        openai_secret = await Secret.load("openai-key")
        openai_key = openai_secret.get()
        
        # Set environment variable
        os.environ['OPENAI_API_KEY'] = openai_key
        
        print("✅ OpenAI key loaded from Prefect Blocks")
        print(f"✅ Project root: {project_root}")
        print(f"✅ RAG index path: {rag_index_path}")
        
        return project_root
        
    except Exception as e:
        print(f"❌ Error loading blocks: {e}")
        print("Ensure you're connected to Prefect Cloud:")
        print("python -m prefect cloud login")
        return None


def check_documents(project_root):
    """Check for source documents."""
    print("\n📄 Checking documents...")
    
    documents_dir = project_root / "documents"
    print(f"🔍 Searching documents in: {documents_dir}")
    
    if not documents_dir.exists():
        print(f"❌ Documents folder missing: {documents_dir}")
        return False
    
    # Count files
    pdf_files = list(documents_dir.rglob("*.pdf"))
    excel_files = list(documents_dir.rglob("*.xlsx"))
    md_files = list(documents_dir.rglob("*.md"))
    
    print(f"✅ Documents found:")
    print(f"   📄 PDF: {len(pdf_files)}")
    print(f"   📊 Excel: {len(excel_files)}")
    print(f"   📝 Markdown: {len(md_files)}")
    
    total = len(pdf_files) + len(excel_files) + len(md_files)
    print(f"📊 Total: {total} documents")
    
    return total > 0


def build_rag_index():
    """Build RAG index."""
    print("\n🚀 Building RAG index...")
    
    try:
        # Check OpenAI key is available
        if not os.environ.get('OPENAI_API_KEY'):
            print("❌ OPENAI_API_KEY not set")
            return False
        
        # Import and run original RAG script
        from launch_script import main as build_rag
        
        print("📋 Parsing documents...")
        print("🔗 Creating embeddings...")
        print("💾 Building FAISS index...")
        
        # Execute build
        success = build_rag()
        
        return success != False
        
    except Exception as e:
        print(f"❌ Build error: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_index():
    """Verify index was created."""
    print("\n🔍 Verifying index...")
    
    rag_index_path = Path(os.environ.get('RAG_INDEX_PATH', '../rag_index'))
    
    required_files = ["index.faiss", "index.pkl", "build_metadata.json"]
    
    all_present = True
    for file in required_files:
        file_path = rag_index_path / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file}: {size:,} bytes")
        else:
            print(f"❌ {file}: Missing")
            all_present = False
    
    if all_present:
        print(f"✅ Complete index in: {rag_index_path}")
    
    return all_present


async def main():
    """Main entry point."""
    print("🚀 RAG Builder with Prefect Blocks")
    print("🔒 Secure version - Broiler Analysis")
    print("📁 From rag/ directory")
    print("=" * 60)
    
    # Configuration with Prefect blocks
    project_root = await setup_environment_with_blocks()
    if not project_root:
        print("\n❌ Configuration failed")
        return False
    
    # Document verification
    if not check_documents(project_root):
        print("\n❌ Documents missing")
        return False
    
    # Build
    if not build_rag_index():
        print("\n❌ Build failed")
        return False
    
    # Verification
    if not verify_index():
        print("\n❌ Index incomplete")
        return False
    
    # Success!
    print("\n" + "=" * 60)
    print("🎉 RAG BUILD SUCCESSFUL")
    print("=" * 60)
    print("✅ RAG index created with Prefect blocks")
    print("✅ Secure configuration")
    print("✅ Ready for AI analysis")
    
    print("\n🚀 Test the application:")
    print("cd ..")
    print("python3 apps/app_prefect_blocks.py --mode test")
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Build interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)