#!/usr/bin/env python3
"""
Direct Document Parser for RAG System
Simple script to parse documents and build vector index
Uses multiple configuration sources with intelligent fallback
"""

import os
import sys
import toml
import logging
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def load_config() -> Optional[str]:
    """Load OpenAI API key from multiple sources with intelligent fallback"""
    
    # Method 1: Try Streamlit secrets from current directory
    secrets_path = Path('.streamlit/secrets.toml')
    if secrets_path.exists():
        print(f"✅ Found Streamlit secrets at: {secrets_path.absolute()}")
        return _load_from_streamlit_secrets(secrets_path)
    
    # Method 2: Try Streamlit secrets from parent directory (in case we're in rag/)
    secrets_path_parent = Path('../.streamlit/secrets.toml')
    if secrets_path_parent.exists():
        print(f"✅ Found Streamlit secrets at: {secrets_path_parent.absolute()}")
        return _load_from_streamlit_secrets(secrets_path_parent)
    
    # Method 3: Try .env file
    env_path = Path('.env')
    if env_path.exists():
        print(f"✅ Found .env file at: {env_path.absolute()}")
        return _load_from_env_file(env_path)
    
    # Method 4: Try environment variable
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key:
        print("✅ Found OpenAI key in environment variables")
        return env_key
    
    # Method 5: Interactive input as last resort
    print("❌ No configuration files found")
    print("📍 Searched locations:")
    print(f"   • {Path('.streamlit/secrets.toml').absolute()}")
    print(f"   • {Path('../.streamlit/secrets.toml').absolute()}")
    print(f"   • {Path('.env').absolute()}")
    print("   • Environment variable OPENAI_API_KEY")
    
    return None

def _load_from_streamlit_secrets(secrets_path: Path) -> Optional[str]:
    """Load OpenAI key from Streamlit secrets file"""
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            secrets = toml.load(f)
        
        openai_key = secrets.get('openai_key')
        if openai_key:
            print(f"✅ OpenAI API key loaded from Streamlit secrets: {openai_key[:8]}...")
            return openai_key
        else:
            print("❌ openai_key not found in secrets.toml")
            return None
            
    except ImportError:
        print("⚠️ toml library not available, trying manual parsing...")
        return _parse_toml_manually(secrets_path)
    except Exception as e:
        print(f"❌ Error loading Streamlit secrets: {e}")
        return None

def _load_from_env_file(env_path: Path) -> Optional[str]:
    """Load OpenAI key from .env file"""
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    key = line.split('=', 1)[1].strip().strip('"\'')
                    if key:
                        print(f"✅ OpenAI API key loaded from .env: {key[:8]}...")
                        return key
        
        print("❌ OPENAI_API_KEY not found in .env file")
        return None
        
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        return None

def _parse_toml_manually(secrets_path: Path) -> Optional[str]:
    """Manually parse TOML file when toml library is not available"""
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('openai_key') and '=' in line:
                    key = line.split('=', 1)[1].strip().strip('"\'')
                    if key:
                        print(f"✅ OpenAI API key loaded (manual parsing): {key[:8]}...")
                        return key
        
        print("❌ openai_key not found in secrets file")
        return None
        
    except Exception as e:
        print(f"❌ Error parsing secrets file manually: {e}")
        return None

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def check_documents() -> bool:
    """Check if documents are available for processing"""
    # Try multiple document locations
    possible_docs_paths = [
        Path('documents'),           # From root
        Path('../documents'),        # From rag/ folder
        Path('docs'),               # Alternative name
        Path('../docs')             # Alternative from rag/
    ]
    
    docs_path = None
    for path in possible_docs_paths:
        if path.exists():
            docs_path = path
            break
    
    if not docs_path:
        print("❌ Documents folder not found")
        print("📍 Searched locations:")
        for path in possible_docs_paths:
            print(f"   • {path.absolute()}")
        return False
    
    print(f"📁 Using documents folder: {docs_path.absolute()}")
    
    # Count documents recursively
    doc_count = 0
    doc_types = {}
    
    for file_path in docs_path.rglob('*.*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            doc_count += 1
            ext = file_path.suffix.lower()
            doc_types[ext] = doc_types.get(ext, 0) + 1
    
    if doc_count == 0:
        print(f"⚠️ No documents found in {docs_path}")
        return False
    
    print(f"✅ Found {doc_count} documents")
    if doc_types:
        print("📋 Document types:")
        for ext, count in sorted(doc_types.items()):
            print(f"   • {ext}: {count} files")
    
    return True

def create_sample_documents():
    """Create sample documents for testing"""
    # Determine best location for documents
    docs_path = Path('documents')
    if not docs_path.exists():
        # Try relative to rag/ folder
        docs_path = Path('../documents')
    
    docs_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📝 Creating sample documents in: {docs_path.absolute()}")
    
    # Sample Ross 308 data
    sample_csv = """age,weight_g,daily_gain_g,temperature_c,feed_intake_g,fcr,humidity_pct
0,42,0,35.0,0,0.0,65
1,45,3,35.0,4,0.89,65
7,160,16,32.0,35,1.02,60
14,410,36,29.0,75,1.15,58
21,820,58,26.0,125,1.28,55
28,1450,90,23.0,180,1.35,52
35,2100,93,21.0,220,1.42,50
42,2800,100,19.0,260,1.48,50"""
    
    sample_guide = """Ross 308 Broiler Performance Guide

WEEKLY TARGETS:
- Week 1 (Day 7): 160g target weight
- Week 2 (Day 14): 410g target weight  
- Week 3 (Day 21): 820g target weight
- Week 4 (Day 28): 1450g target weight

TEMPERATURE MANAGEMENT:
- Week 1: 32-35°C (critical establishment phase)
- Week 2: 29-32°C (early development)
- Week 3: 26-29°C (rapid growth phase)
- Week 4: 23-26°C (optimization phase)

FEED CONVERSION TARGETS:
- Week 1: 1.00-1.10 FCR
- Week 2: 1.20-1.35 FCR
- Week 3: 1.40-1.55 FCR
- Week 4: 1.55-1.70 FCR

TROUBLESHOOTING WEIGHT ISSUES:
If birds are underweight:
1. Check feed quality and availability
2. Verify temperature is within target range
3. Ensure adequate water access
4. Monitor for disease signs
5. Adjust feeder space if overcrowded

HEAT STRESS INDICATORS:
- Panting with open beaks
- Wings spread from body
- Reduced feed intake (>10% drop)
- Increased water consumption
- Birds gathering near water sources"""
    
    # Write sample files
    with open(docs_path / 'ross308_sample_data.csv', 'w', encoding='utf-8') as f:
        f.write(sample_csv)
    
    with open(docs_path / 'ross_308_sample_guide.txt', 'w', encoding='utf-8') as f:
        f.write(sample_guide)
    
    print("✅ Sample documents created:")
    print("   • ross308_sample_data.csv")
    print("   • ross_308_sample_guide.txt")

def determine_index_path() -> Path:
    """Determine the best path for the RAG index"""
    possible_paths = [
        Path('rag_index'),          # From root
        Path('../rag_index'),       # From rag/ folder
        Path('index'),              # Alternative name
        Path('../index')            # Alternative from rag/
    ]
    
    # Check if any index already exists
    for path in possible_paths:
        if path.exists() and any(path.iterdir()):
            print(f"📁 Using existing index at: {path.absolute()}")
            return path
    
    # Use the first viable option (prefer root level)
    index_path = possible_paths[0]
    print(f"📁 Will create index at: {index_path.absolute()}")
    return index_path

def main():
    """Main parsing function with intelligent configuration detection"""
    print("🚀 RAG DOCUMENT PARSER")
    print("🔧 Intelligent Configuration Detection")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    # Load configuration with fallback
    openai_key = load_config()
    if not openai_key:
        print("\n❌ Cannot proceed without OpenAI API key")
        print("\n💡 Configuration options:")
        print("1. Create .streamlit/secrets.toml with openai_key")
        print("2. Create .env with OPENAI_API_KEY")
        print("3. Set environment variable OPENAI_API_KEY")
        print("\n📝 Example .env file:")
        print("OPENAI_API_KEY=sk-your-key-here")
        return
    
    # Check documents
    if not check_documents():
        print("\n📝 Creating sample documents for testing...")
        create_sample_documents()
        if not check_documents():
            print("❌ Still no documents available")
            return
    
    # Import and initialize embedder
    try:
        print(f"\n🔧 Initializing RAG system...")
        from rag.embedder import EnhancedDocumentEmbedder
        
        embedder = EnhancedDocumentEmbedder(
            openai_api_key=openai_key,
            chunk_size=500,
            chunk_overlap=50,
            use_hybrid_search=True,
            use_intelligent_routing=True
        )
        print("✅ Enhanced Document Embedder initialized")
        
    except ImportError as e:
        print(f"❌ Error importing embedder: {e}")
        print("   Make sure you're running from the correct directory")
        print(f"   Current directory: {Path.cwd()}")
        print("   Expected: broiler_agent/ (project root)")
        return
    except Exception as e:
        print(f"❌ Error initializing embedder: {e}")
        return
    
    # Determine paths
    documents_path = None
    for path in [Path('documents'), Path('../documents')]:
        if path.exists():
            documents_path = str(path)
            break
    
    index_path = str(determine_index_path())
    
    # Parse documents and build vector store
    try:
        print(f"\n📚 Starting document processing...")
        print(f"📂 Documents: {documents_path}")
        print(f"💾 Index: {index_path}")
        
        success = embedder.build_vector_store(
            documents_path=documents_path,
            index_path=index_path
        )
        
        if success:
            print("\n🎉 SUCCESS!")
            print("=" * 50)
            print("✅ Documents processed and indexed")
            print(f"✅ Vector store saved to {index_path}")
            print("✅ System ready for searches")
            
            # Show processing statistics
            try:
                stats = embedder.get_routing_statistics()
                if stats and isinstance(stats, dict):
                    print(f"\n📊 Processing Statistics:")
                    
                    # Try to get parser usage
                    parser_usage = None
                    if 'processing_statistics' in stats:
                        parser_usage = stats['processing_statistics'].get('parser_usage', {})
                    elif 'parsers' in stats:
                        parser_usage = {name: info.get('total_attempts', 0) 
                                      for name, info in stats['parsers'].items() 
                                      if info.get('total_attempts', 0) > 0}
                    
                    if parser_usage:
                        for parser, count in parser_usage.items():
                            print(f"   • {parser}: {count} documents")
                    else:
                        print(f"   • Total documents processed successfully")
                        
            except Exception as e:
                print(f"   ⚠️ Could not retrieve detailed statistics: {e}")
            
            # Test search
            print(f"\n🔍 Testing search functionality...")
            test_queries = [
                "Ross 308 weight targets",
                "temperature management week 1",
                "feed conversion ratio"
            ]
            
            for query in test_queries:
                try:
                    results = embedder.search_documents(query, k=2)
                    if results:
                        doc, score = results[0]
                        source = doc.metadata.get('source_file', 'unknown')
                        print(f"   Query: '{query}'")
                        print(f"   → Best result: {source} (score: {score:.3f})")
                    else:
                        print(f"   Query: '{query}' → No results")
                except Exception as e:
                    print(f"   Query: '{query}' → Error: {e}")
            
            print(f"\n🎯 Next Steps:")
            print(f"1. Add more documents to {documents_path}")
            print("2. Re-run this script to update the index")
            print("3. Use the search functionality in your applications")
            print(f"4. Check {index_path} for saved vector store")
            print("5. Run Streamlit: python -m streamlit run apps/app_streamlit.py")
            
        else:
            print("\n❌ Document processing failed")
            print("   Check the error messages above")
            
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        print("\n🔧 Full error details:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
