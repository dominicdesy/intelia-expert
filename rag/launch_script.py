#!/usr/bin/env python3
"""
Launch Script for Modular Document Embedder
Main entry point with intelligent routing and enhanced capabilities
Now with robust configuration detection and path handling
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Tuple, List
import json

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def load_environment():
    """Load environment variables from multiple sources with intelligent fallback"""
    config_loaded = False
    config_source = None
    
    # Method 1: Try .env file in current directory
    env_file = Path('.env')
    if env_file.exists():
        config_loaded = _load_env_file(env_file)
        if config_loaded:
            config_source = f".env file at {env_file.absolute()}"
    
    # Method 2: Try Streamlit secrets
    if not config_loaded:
        secrets_paths = [
            Path('.streamlit/secrets.toml'),
            Path('../.streamlit/secrets.toml')
        ]
        
        for secrets_path in secrets_paths:
            if secrets_path.exists():
                config_loaded = _load_streamlit_secrets(secrets_path)
                if config_loaded:
                    config_source = f"Streamlit secrets at {secrets_path.absolute()}"
                    break
    
    # Method 3: Check environment variables directly
    if not config_loaded:
        if os.getenv('OPENAI_API_KEY'):
            config_loaded = True
            config_source = "Environment variables"
    
    if config_loaded:
        print(f"✅ Configuration loaded from: {config_source}")
    else:
        print("⚠️ No configuration found")
        print("📍 Searched locations:")
        print(f"   • {Path('.env').absolute()}")
        print(f"   • {Path('.streamlit/secrets.toml').absolute()}")
        print(f"   • {Path('../.streamlit/secrets.toml').absolute()}")
        print("   • Environment variables")
    
    return config_loaded

def _load_env_file(env_file: Path) -> bool:
    """Load environment variables from .env file"""
    try:
        # Try to load python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"✅ Loaded .env using dotenv library")
            return True
        except ImportError:
            # Manual parsing if python-dotenv not available
            print("ℹ️ Loading .env manually (install python-dotenv for better support)")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            return True
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        return False

def _load_streamlit_secrets(secrets_path: Path) -> bool:
    """Load configuration from Streamlit secrets"""
    try:
        import toml
        with open(secrets_path, 'r') as f:
            secrets = toml.load(f)
        
        # Set as environment variables
        for key, value in secrets.items():
            if isinstance(value, str):
                os.environ[key.upper()] = value
                if key == 'openai_key':
                    os.environ['OPENAI_API_KEY'] = value
        
        print(f"✅ Loaded Streamlit secrets")
        return True
        
    except ImportError:
        # Manual TOML parsing
        return _parse_toml_manually(secrets_path)
    except Exception as e:
        print(f"❌ Error loading Streamlit secrets: {e}")
        return False

def _parse_toml_manually(secrets_path: Path) -> bool:
    """Manually parse TOML file when toml library is not available"""
    try:
        with open(secrets_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    os.environ[key.upper()] = value
                    if key == 'openai_key':
                        os.environ['OPENAI_API_KEY'] = value
        
        print("✅ Parsed Streamlit secrets manually")
        return True
    except Exception as e:
        print(f"❌ Error parsing Streamlit secrets: {e}")
        return False

def check_prerequisites() -> Tuple[bool, List[str]]:
    """Check system prerequisites and dependencies"""
    print("\n🔍 Checking system prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False, []
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check required packages
    required_packages = [
        ('langchain', 'LangChain core'),
        ('langchain_openai', 'LangChain OpenAI integration'),
        ('openai', 'OpenAI client library'),
        ('pandas', 'Data processing'),
        ('faiss', 'Vector search'),
        ('streamlit', 'Web interface')
    ]
    
    missing_packages = []
    
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - Missing package: {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing required packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r data/requirements.txt")
        return False, missing_packages
    
    # Check optional packages with enhanced descriptions
    optional_packages = [
        ('rank_bm25', 'BM25 for hybrid search (HIGHLY RECOMMENDED)'),
        ('tika', 'Universal document parsing (1000+ formats)'),
        ('pdfplumber', 'Advanced PDF processing'),
        ('orjson', 'Fast JSON processing')
    ]
    
    print("\n📋 Optional enhancements:")
    enhanced_features = []
    for package, description in optional_packages:
        try:
            __import__(package)
            print(f"✅ {description}")
            enhanced_features.append(package)
        except ImportError:
            print(f"⚠️ {description} (not installed)")
    
    return True, enhanced_features

def check_api_keys() -> bool:
    """Verify API keys are configured"""
    print("\n🔑 Checking API configuration...")
    
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found")
        print("   Available configuration methods:")
        print("   1. Set in .env file: OPENAI_API_KEY=your_key_here")
        print("   2. Set in .streamlit/secrets.toml: openai_key = \"your_key_here\"")
        print("   3. Set as environment variable")
        return False
    
    # Validate key format (basic check)
    if not openai_key.startswith('sk-'):
        print("⚠️ OpenAI API key format looks incorrect")
        print("   Should start with 'sk-'")
    else:
        print(f"✅ OpenAI API key configured: {openai_key[:8]}...")
    
    # Check optional keys
    claude_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    if claude_key:
        print(f"✅ Claude/Anthropic API key configured: {claude_key[:8]}...")
    
    return True

def setup_directories():
    """Create necessary directories with intelligent path detection"""
    print("\n📁 Setting up directories...")
    
    # Determine base paths
    base_dirs = [
        ('documents', 'Document storage'),
        ('rag_index', 'Vector index storage'),
        ('logs', 'Application logs'),
        ('data', 'Configuration and data')
    ]
    
    for directory, description in base_dirs:
        # Try current directory first, then parent
        for base_path in [Path('.'), Path('..')]:
            dir_path = base_path / directory
            try:
                dir_path.mkdir(exist_ok=True)
                print(f"✅ {description}: {dir_path.absolute()}")
                break
            except PermissionError:
                continue
        else:
            print(f"⚠️ Could not create {directory} directory")

def create_sample_documents():
    """Create sample documents if documents folder is empty"""
    # Find documents directory
    docs_paths = [Path('documents'), Path('../documents')]
    docs_path = None
    
    for path in docs_paths:
        if path.exists():
            docs_path = path
            break
    
    if not docs_path:
        docs_path = Path('documents')
        docs_path.mkdir(exist_ok=True)
    
    # Check if documents exist
    doc_files = [f for f in docs_path.rglob('*.*') if f.is_file() and not f.name.startswith('.')]
    
    if doc_files:
        print(f"\n📄 Found {len(doc_files)} existing documents in {docs_path.absolute()}")
        for doc in doc_files[:5]:  # Show first 5
            print(f"   • {doc.name}")
        if len(doc_files) > 5:
            print(f"   ... and {len(doc_files) - 5} more")
        return False
    
    print(f"\n📝 Creating sample documents in {docs_path.absolute()}...")
    
    # Sample Ross 308 performance data
    ross_csv = """age,weight_g,daily_gain_g,temperature_c,feed_intake_g,fcr,humidity_pct
0,42,0,35.0,0,0.0,65
1,45,3,35.0,4,0.89,65
7,160,16,32.0,35,1.02,60
14,410,36,29.0,75,1.15,58
21,820,58,26.0,125,1.28,55
28,1450,90,23.0,180,1.35,52
35,2100,93,21.0,220,1.42,50
42,2800,100,19.0,260,1.48,50"""
    
    # Sample temperature management guide
    temp_guide = """Ross 308 Temperature Management Guidelines

ENVIRONMENTAL CONTROL FOR OPTIMAL PERFORMANCE

Week 1 (Days 1-7): Critical Establishment Phase
Target Temperature: 32-35°C
Humidity: 60-70%
- Chicks are most vulnerable during first week
- Monitor for huddling (too cold) or panting (too hot)
- Gradual temperature reduction: 0.5°C every 2 days

Week 2 (Days 8-14): Early Development
Target Temperature: 29-32°C  
Humidity: 55-65%
- Birds begin to regulate body temperature
- Watch for uniform distribution in house
- Adjust ventilation to maintain air quality

Week 3 (Days 15-21): Rapid Growth Phase
Target Temperature: 26-29°C
Humidity: 50-60%
- Growth rate accelerates significantly
- Increased feed consumption and heat production
- Monitor for heat stress indicators

Week 4 (Days 22-28): Growth Optimization
Target Temperature: 23-26°C
Humidity: 45-55%
- Birds approaching target weights
- Fine-tune environment for optimal FCR
- Prepare for finishing phase temperatures

Week 5+ (Days 29+): Finishing Phase
Target Temperature: 20-23°C
Humidity: 45-55%
- Market weight approach
- Prevent heat stress in larger birds
- Maintain comfort through harvest

PRACTICAL MANAGEMENT TIPS:

Temperature Adjustment:
- Never adjust more than 2°C per day
- Use multiple measurement points in house
- Consider bird behavior over thermometer readings

Humidity Control:
- Higher humidity requires lower air temperature
- Use ventilation to control moisture buildup
- Monitor litter moisture content

Emergency Procedures:
- Power failure: Implement backup heating/cooling
- Extreme weather: Adjust targets accordingly
- Disease outbreak: May require temperature modification"""
    
    # Sample feed management guide
    feed_guide = """# Broiler Feed Management Best Practices

## Feed Quality Standards

### Storage Requirements
- **Temperature**: Store below 25°C to prevent rancidity
- **Humidity**: Maintain below 70% to prevent mold
- **Duration**: Use within 3 weeks of manufacture date
- **Containers**: Use clean, sealed containers

### Quality Indicators
- **Appearance**: Uniform pellet size and color
- **Smell**: Fresh, grain-like odor (no musty smell)
- **Texture**: Firm pellets, minimal fines
- **Moisture**: Below 12% moisture content

## Feeding Programs by Age

### Starter Phase (Days 1-14)
- **Protein**: 22-24%
- **Energy**: 3000-3100 ME kcal/kg
- **Form**: Crumbles or mini-pellets
- **Feeding**: Ad libitum with feeders always full

### Grower Phase (Days 15-28)
- **Protein**: 20-22%
- **Energy**: 3100-3200 ME kcal/kg
- **Form**: Pellets (3-4mm diameter)
- **Feeding**: Scheduled feeding may begin

### Finisher Phase (Days 29-42)
- **Protein**: 18-20%
- **Energy**: 3200-3300 ME kcal/kg
- **Form**: Pellets (4-5mm diameter)
- **Feeding**: Monitor intake closely for optimal FCR

## Feed Conversion Monitoring

### Target FCR by Week
- Week 1: 0.80-1.00
- Week 2: 1.00-1.20
- Week 3: 1.20-1.40
- Week 4: 1.40-1.60
- Week 5: 1.55-1.75
- Week 6: 1.65-1.85

### Troubleshooting Poor FCR
1. **Check feed quality** - Nutritional analysis
2. **Verify feeding space** - 2.5cm per bird minimum
3. **Monitor water intake** - 1.8-2.2 times feed intake
4. **Environmental factors** - Temperature stress affects FCR
5. **Health status** - Disease impacts feed efficiency

## Water Management

### Quality Standards
- **pH**: 6.0-8.0
- **Bacteria**: <100 CFU/ml total bacteria
- **Nitrates**: <50 ppm
- **Temperature**: 10-20°C optimal

### System Maintenance
- **Daily**: Check water flow and pressure
- **Weekly**: Clean water lines and nipples
- **Monthly**: Bacteriological testing
- **Annually**: Complete system disinfection"""
    
    # Write sample files
    with open(docs_path / 'ross308_sample_data.csv', 'w', encoding='utf-8') as f:
        f.write(ross_csv)
    
    with open(docs_path / 'ross308_temperature_guide.txt', 'w', encoding='utf-8') as f:
        f.write(temp_guide)
    
    with open(docs_path / 'feed_management_guide.md', 'w', encoding='utf-8') as f:
        f.write(feed_guide)
    
    print("✅ Created sample documents:")
    print("   • ross308_sample_data.csv")
    print("   • ross308_temperature_guide.txt") 
    print("   • feed_management_guide.md")
    
    return True

def test_parser_detection():
    """Test automatic parser detection with intelligent routing"""
    print("\n🔍 Testing automatic parser detection...")
    
    try:
        from rag.embedder import EnhancedDocumentEmbedder
        
        # Initialize embedder with intelligent routing
        api_key = os.getenv('OPENAI_API_KEY', 'dummy-key-for-testing')
        embedder = EnhancedDocumentEmbedder(
            api_key,
            use_intelligent_routing=True,
            use_hybrid_search=False  # Skip for detection test
        )
        
        # Find documents directory
        docs_paths = [Path('documents'), Path('../documents')]
        docs_path = None
        for path in docs_paths:
            if path.exists():
                docs_path = path
                break
        
        if not docs_path:
            print("   No documents to test")
            return True
        
        test_files = [f for f in docs_path.rglob('*.*') if f.is_file()]
        
        if not test_files:
            print("   No files to test")
            return True
        
        print(f"   Testing {len(test_files)} files with intelligent routing:")
        
        for file_path in test_files[:5]:  # Test first 5 files
            try:
                parser, confidence = embedder.detect_file_type(str(file_path))
                print(f"   📄 {file_path.name}")
                print(f"      → Parser: {parser.capability.name}")
                print(f"      → Confidence: {confidence:.2f}")
                print(f"      → Quality: {parser.capability.quality_score}")
                print(f"      → Routing: {'Intelligent' if embedder.use_intelligent_routing else 'Basic'}")
            except Exception as e:
                print(f"   ❌ {file_path.name}: {e}")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Cannot test detection: {e}")
        return False

def run_full_pipeline():
    """Run the complete document processing pipeline with all enhancements"""
    print("\n⚙️ Running enhanced document processing pipeline...")
    
    try:
        from rag.embedder import EnhancedDocumentEmbedder
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ Cannot run pipeline without OpenAI API key")
            return False
        
        # Initialize embedder with all enhancements
        print("   🔧 Initializing enhanced embedder with intelligent routing...")
        embedder = EnhancedDocumentEmbedder(
            api_key,
            use_hybrid_search=True,
            use_intelligent_routing=True
        )
        
        print(f"   ✅ Initialized with {len(embedder.parser_registry.parsers)} parsers")
        print(f"   🧠 Intelligent routing: {embedder.use_intelligent_routing}")
        print(f"   🔍 Hybrid search: {embedder.search_engine is not None}")
        
        # Determine paths
        docs_paths = [Path('documents'), Path('../documents')]
        index_paths = [Path('rag_index'), Path('../rag_index')]
        
        documents_path = None
        for path in docs_paths:
            if path.exists():
                documents_path = str(path)
                break
        
        index_path = str(index_paths[0])  # Use first option
        
        # Build vector store
        print(f"   📚 Processing documents and building vector store...")
        print(f"   📂 Documents: {documents_path}")
        print(f"   💾 Index: {index_path}")
        
        success = embedder.build_vector_store(
            documents_path=documents_path or "documents/",
            index_path=index_path
        )
        
        if not success:
            print("   ❌ Vector store build failed")
            return False
        
        print("   ✅ Vector store built successfully")
        
        # Test search capabilities
        if embedder.search_engine:
            print("   🔍 Testing enhanced search capabilities...")
            
            test_queries = [
                "Ross 308 temperature management",
                "feed conversion ratio targets",
                "weight targets by week",
                "humidity control guidelines"
            ]
            
            for query in test_queries:
                print(f"\n   🔎 Query: '{query}'")
                try:
                    results = embedder.search_documents(query, k=3)
                    
                    if results:
                        for i, (doc, score) in enumerate(results):
                            source = doc.metadata.get('source_file', 'unknown')
                            parser = doc.metadata.get('parser_name', 'unknown')
                            routing_info = ""
                            if 'routing_confidence' in doc.metadata:
                                routing_info = f" | Router: {doc.metadata['routing_confidence']:.2f}"
                            print(f"      {i+1}. Score: {score:.3f} | {source} | {parser}{routing_info}")
                            # Show preview
                            preview = doc.page_content.replace('\n', ' ')[:80]
                            print(f"         Preview: {preview}...")
                    else:
                        print("      No results found")
                        
                except Exception as e:
                    print(f"      ❌ Search error: {e}")
        
        # Get and save enhanced system statistics
        print("   📊 Collecting system statistics...")
        try:
            stats = embedder.get_routing_statistics()
            
            # Ensure data directory exists
            data_dir = Path('data')
            if not data_dir.exists():
                data_dir = Path('../data')
            data_dir.mkdir(exist_ok=True)
            
            status = {
                'last_build': str(Path(index_path).stat().st_mtime if Path(index_path).exists() else 'never'),
                'documents_processed': len([f for f in Path(documents_path or 'documents').rglob('*.*') if f.is_file()]),
                'intelligent_routing_enabled': embedder.use_intelligent_routing,
                'hybrid_search_available': embedder.search_engine is not None,
                'parsers_available': len(embedder.parser_registry.parsers),
                'routing_statistics': stats
            }
            
            with open(data_dir / 'system_status.json', 'w') as f:
                json.dump(status, f, indent=2, default=str)
            
            print(f"   ✅ Enhanced system status saved to {data_dir}/system_status.json")
            
            # Export performance report if router is available
            if embedder.use_intelligent_routing and embedder.router:
                embedder.export_performance_report("performance_report.json")
                print("   ✅ Performance report exported to performance_report.json")
            
        except Exception as e:
            print(f"   ⚠️ Could not save statistics: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Pipeline error: {e}")
        logging.error(f"Pipeline failed: {e}")
        return False

def show_usage_instructions():
    """Display enhanced usage instructions for the system"""
    print("\n" + "="*60)
    print("✅ ENHANCED MODULAR DOCUMENT EMBEDDER READY!")
    print("="*60)
    
    print("\n🎯 CORE CAPABILITIES:")
    print("  ✅ Ross 308 specialized parsing (optimal quality)")
    print("  ✅ General CSV/Excel processing (high quality)")
    print("  ✅ PDF and text documents (good quality)")
    print("  ✅ Automatic file type detection")
    print("  ✅ Vector similarity search")
    
    # Check for enhanced features
    enhanced_features = []
    
    # Check intelligent routing
    try:
        from rag.parser_router import IntelligentParserRouter
        enhanced_features.append("🧠 Intelligent routing with adaptive learning")
    except ImportError:
        pass
    
    # Check hybrid search
    try:
        import rank_bm25
        enhanced_features.append("🔍 Hybrid search (Vector + BM25)")
    except ImportError:
        pass
    
    # Check universal parsing
    try:
        import tika
        enhanced_features.append("🌐 Universal format support (1000+ types)")
    except ImportError:
        pass
    
    # Check advanced PDF
    try:
        import pdfplumber
        enhanced_features.append("📊 Advanced PDF table extraction")
    except ImportError:
        pass
    
    if enhanced_features:
        print("\n🌟 ENHANCED FEATURES ACTIVE:")
        for feature in enhanced_features:
            print(f"  ✅ {feature}")
    
    print("\n🚀 HOW TO USE:")
    print("  1. Add documents to documents/ folder")
    print("  2. Run: python rag/launch_script.py")
    print("  3. Use the embedder in your code:")
    
    print("""
from rag.embedder import EnhancedDocumentEmbedder

# Initialize with all enhancements
embedder = EnhancedDocumentEmbedder(
    os.getenv('OPENAI_API_KEY'),
    use_intelligent_routing=True,
    use_hybrid_search=True
)

# Load existing index
if Path('rag_index').exists():
    embedder.search_engine.load_index('rag_index')

# Search with enhanced capabilities
results = embedder.search_documents("your query", k=10)
for doc, score in results:
    print(f"Score: {score:.3f}")
    print(f"Source: {doc.metadata['source_file']}")
    print(f"Parser: {doc.metadata['parser_name']}")
    print(f"Content: {doc.page_content[:200]}...")
""")
    
    print("\n🔧 ADVANCED FEATURES:")
    print("  • Performance optimization: embedder.optimize_system_performance()")
    print("  • Routing statistics: embedder.get_routing_statistics()")
    print("  • Performance reports: embedder.export_performance_report()")
    print("  • Check data/system_status.json for detailed metrics")
    
    print("\n🔌 EXTENDING THE SYSTEM:")
    print("  • Add custom parsers in rag/parsers/ directory")
    print("  • Register new parsers: embedder.register_parser(YourParser())")
    print("  • System learns and adapts automatically")
    print("  • Router optimizes based on performance history")
    
    print("\n🎮 APPLICATIONS:")
    print("  • Streamlit app: python -m streamlit run apps/app_streamlit.py")
    print("  • Expert assistant: python -m streamlit run apps/app_expert.py") 
    print("  • Automated reports: python apps/app_auto.py")
    print("  • Prefect workflows: python apps/app_prefect.py")

def main():
    """Main launch function with enhanced capabilities and robust configuration"""
    print("🚀 ENHANCED MODULAR DOCUMENT EMBEDDER LAUNCHER")
    print("🏗️ Clean Architecture with Intelligent Configuration Detection")
    print("="*70)
    
    setup_logging()
    
    # Load environment configuration with fallback
    config_loaded = load_environment()
    
    # Check system prerequisites
    prereq_success, enhanced_features = check_prerequisites()
    
    if not prereq_success:
        print("\n❌ Prerequisites check failed")
        print("   Install missing packages and try again")
        sys.exit(1)
    
    # Check API configuration
    if not check_api_keys():
        print("\n❌ API configuration incomplete")
        if not config_loaded:
            print("   No configuration source found")
            print("\n💡 Quick setup options:")
            print("   1. Create .env file: echo OPENAI_API_KEY=sk-your-key > .env")
            print("   2. Create .streamlit/secrets.toml with openai_key")
            print("   3. Set environment variable: set OPENAI_API_KEY=sk-your-key")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Create sample documents if needed
    sample_created = create_sample_documents()
    if sample_created:
        print("   ℹ️ Using sample documents for demonstration")
    
    # Test enhanced parser detection
    if not test_parser_detection():
        print("\n⚠️ Parser detection test failed")
        print("   System may not work correctly")
    
    # Run enhanced pipeline
    if not run_full_pipeline():
        print("\n❌ SYSTEM SETUP FAILED")
        print("   Check error messages above")
        print(f"   Current directory: {Path.cwd()}")
        print("   Expected: broiler_agent/ (project root)")
        sys.exit(1)
    
    # Show enhanced usage instructions
    show_usage_instructions()

if __name__ == "__main__":
    main()
