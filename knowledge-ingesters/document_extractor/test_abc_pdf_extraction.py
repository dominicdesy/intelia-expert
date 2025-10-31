# -*- coding: utf-8 -*-
"""
Test A/B/C - Comparaison d'outils d'extraction PDF

Compare 3 outils gratuits:
A - PyMuPDF (fitz)
B - pdfplumber
C - pypdf

Critères: Vitesse, Qualité, Structure, Tables, Robustesse
"""

import time
from pathlib import Path

# Test file
TEST_PDF = "C:/Software_Development/intelia-cognito/data-pipelines/Sources/intelia/public/veterinary_services/common/AviaTech_Staph.pdf"

def test_pymupdf():
    """Option A: PyMuPDF (fitz)"""
    try:
        import fitz

        start = time.time()
        doc = fitz.open(TEST_PDF)

        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        doc.close()

        elapsed = time.time() - start

        return {
            'success': True,
            'tool': 'PyMuPDF (fitz)',
            'time': elapsed,
            'text_length': len(full_text),
            'word_count': len(full_text.split()),
            'pages': len(doc),
            'text_sample': full_text[:500],
            'has_tables': False,  # Would need extra logic
            'error': None
        }
    except ImportError:
        return {
            'success': False,
            'tool': 'PyMuPDF (fitz)',
            'error': 'Not installed - run: pip install PyMuPDF'
        }
    except Exception as e:
        return {
            'success': False,
            'tool': 'PyMuPDF (fitz)',
            'error': str(e)
        }

def test_pdfplumber():
    """Option B: pdfplumber"""
    try:
        import pdfplumber

        start = time.time()

        text_parts = []
        tables_found = False

        with pdfplumber.open(TEST_PDF) as pdf:
            for page in pdf.pages:
                # Extract text
                text = page.extract_text()
                if text:
                    text_parts.append(text)

                # Check for tables
                tables = page.extract_tables()
                if tables:
                    tables_found = True

        full_text = "\n\n".join(text_parts)
        elapsed = time.time() - start

        return {
            'success': True,
            'tool': 'pdfplumber',
            'time': elapsed,
            'text_length': len(full_text),
            'word_count': len(full_text.split()),
            'pages': len(pdf.pages),
            'text_sample': full_text[:500],
            'has_tables': tables_found,
            'error': None
        }
    except ImportError:
        return {
            'success': False,
            'tool': 'pdfplumber',
            'error': 'Not installed - run: pip install pdfplumber'
        }
    except Exception as e:
        return {
            'success': False,
            'tool': 'pdfplumber',
            'error': str(e)
        }

def test_pypdf():
    """Option C: pypdf"""
    try:
        from pypdf import PdfReader

        start = time.time()

        reader = PdfReader(TEST_PDF)

        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            text_parts.append(text)

        full_text = "\n\n".join(text_parts)
        elapsed = time.time() - start

        return {
            'success': True,
            'tool': 'pypdf',
            'time': elapsed,
            'text_length': len(full_text),
            'word_count': len(full_text.split()),
            'pages': len(reader.pages),
            'text_sample': full_text[:500],
            'has_tables': False,  # No built-in table detection
            'error': None
        }
    except ImportError:
        return {
            'success': False,
            'tool': 'pypdf',
            'error': 'Not installed - run: pip install pypdf'
        }
    except Exception as e:
        return {
            'success': False,
            'tool': 'pypdf',
            'error': str(e)
        }

def main():
    print("="*80)
    print("TEST A/B/C - Extraction de Texte PDF")
    print("="*80)
    print(f"Fichier test: {Path(TEST_PDF).name}")
    print(f"Taille: {Path(TEST_PDF).stat().st_size / 1024:.1f} KB")
    print()

    # Run tests
    results = []

    print("Test A: PyMuPDF (fitz)...")
    result_a = test_pymupdf()
    results.append(result_a)

    print("Test B: pdfplumber...")
    result_b = test_pdfplumber()
    results.append(result_b)

    print("Test C: pypdf...")
    result_c = test_pypdf()
    results.append(result_c)

    # Display results
    print("\n" + "="*80)
    print("RESULTATS")
    print("="*80)

    for result in results:
        print(f"\n### {result['tool']} ###")

        if not result['success']:
            print(f"  ERREUR: {result['error']}")
            continue

        print(f"  Vitesse: {result['time']:.3f} secondes")
        print(f"  Pages: {result['pages']}")
        print(f"  Longueur texte: {result['text_length']:,} caracteres")
        print(f"  Mots extraits: {result['word_count']:,} mots")
        print(f"  Detection tables: {'OUI' if result['has_tables'] else 'NON'}")
        print(f"\n  Extrait (premiers 200 caracteres):")
        print(f"  {result['text_sample'][:200]}...")

    # Comparison
    successful = [r for r in results if r['success']]

    if successful:
        print("\n" + "="*80)
        print("COMPARAISON")
        print("="*80)

        # Fastest
        fastest = min(successful, key=lambda x: x['time'])
        print(f"  Plus rapide: {fastest['tool']} ({fastest['time']:.3f}s)")

        # Most text extracted
        most_text = max(successful, key=lambda x: x['text_length'])
        print(f"  Plus de texte: {most_text['tool']} ({most_text['text_length']:,} chars)")

        # Tables support
        with_tables = [r for r in successful if r['has_tables']]
        if with_tables:
            print(f"  Support tables: {', '.join([r['tool'] for r in with_tables])}")

        # Recommendation
        print("\n" + "="*80)
        print("RECOMMANDATION")
        print("="*80)

        # Score calculation (vitesse + qualite)
        for r in successful:
            # Normalize scores (0-1)
            time_score = 1 - (r['time'] / max([x['time'] for x in successful]))
            quality_score = r['text_length'] / max([x['text_length'] for x in successful])
            table_bonus = 0.1 if r.get('has_tables', False) else 0

            r['final_score'] = (time_score * 0.4) + (quality_score * 0.5) + table_bonus

        winner = max(successful, key=lambda x: x['final_score'])

        print(f"  GAGNANT: {winner['tool']}")
        print(f"  Score: {winner['final_score']:.2f}/1.0")
        print(f"  Raison: Meilleur equilibre vitesse/qualite")

        if winner['has_tables']:
            print(f"  Bonus: Support des tables!")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
