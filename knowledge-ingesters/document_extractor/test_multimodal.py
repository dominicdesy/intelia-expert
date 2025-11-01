"""
Test Multimodal Extractor
Quick test to verify image extraction works
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from multimodal_extractor import MultimodalExtractor

def test_basic_extraction():
    """Test basic multimodal extraction."""
    print("="*80)
    print("TESTING MULTIMODAL EXTRACTION")
    print("="*80)

    # Initialize extractor
    extractor = MultimodalExtractor(
        enable_image_extraction=True
    )

    # Test file (use Nano manual if exists)
    test_file = Path("Sources/intelia/intelia_products/nano/nano-manual.pdf")

    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        print("Please specify a PDF file to test")
        return

    # Process document
    result = extractor.process_document(
        str(test_file),
        classification_path="intelia/intelia_products/nano/documentation/common",
        extract_images=True
    )

    # Print results
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Text chunks: {result['text_chunks']}")
    print(f"Images extracted: {result['images']}")
    print(f"Errors: {len(result['errors'])}")

    if result['errors']:
        print("\nErrors:")
        for error in result['errors']:
            print(f"  - {error}")

    # Print statistics
    extractor.print_statistics()

if __name__ == "__main__":
    test_basic_extraction()
