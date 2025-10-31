"""
Web Auto-Classifier
Analyse les pages web et classifie automatiquement dans le fichier Excel

Ce script:
1. Lit les URLs avec Classification = "To be analyzed"
2. Extrait le contenu + métadonnées de classification (breadcrumbs, tags, catégories)
3. Utilise Claude pour classifier selon la taxonomie Intelia
4. Écrit la classification dans Excel

Usage:
    python web_auto_classifier.py                    # Traiter toutes les URLs "To be analyzed"
    python web_auto_classifier.py --limit 5          # Limiter à 5 URLs
    python web_auto_classifier.py --dry-run          # Afficher sans modifier Excel
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import httpx
from bs4 import BeautifulSoup
import anthropic
import yaml

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent / "document_extractor"))

class WebAutoClassifier:
    def __init__(self, excel_file: str = "websites.xlsx", sheet_name: str = "URL"):
        self.excel_file = excel_file
        self.sheet_name = sheet_name

        # Charger la taxonomie
        taxonomy_path = Path(__file__).parent.parent / "document_extractor" / "config" / "path_rules" / "intelia.yaml"
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            self.taxonomy = yaml.safe_load(f)

        # Initialiser Claude
        self.claude = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    async def extract_page_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extrait le contenu et les métadonnées de classification d'une page web

        Returns:
            Dict avec: title, content, breadcrumbs, categories, tags, meta_keywords
        """
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraire le titre
            title = soup.find('title')
            title = title.get_text().strip() if title else ""

            # Extraire les breadcrumbs (fil d'Ariane)
            breadcrumbs = []

            # Méthode 1: Chercher les breadcrumbs Schema.org
            breadcrumb_schema = soup.find('ol', {'itemtype': 'https://schema.org/BreadcrumbList'})
            if breadcrumb_schema:
                items = breadcrumb_schema.find_all('li', {'itemprop': 'itemListElement'})
                breadcrumbs = [item.get_text().strip() for item in items]

            # Méthode 2: Chercher par classes communes
            if not breadcrumbs:
                for selector in [
                    {'class': 'breadcrumb'},
                    {'class': 'breadcrumbs'},
                    {'class': 'breadcrumb-trail'},
                    {'id': 'breadcrumb'},
                    {'aria-label': 'breadcrumb'},
                    {'role': 'navigation', 'aria-label': 'Breadcrumb'}
                ]:
                    breadcrumb_elem = soup.find(['nav', 'ol', 'ul', 'div'], selector)
                    if breadcrumb_elem:
                        items = breadcrumb_elem.find_all(['li', 'a', 'span'])
                        breadcrumbs = [item.get_text().strip() for item in items if item.get_text().strip()]
                        break

            # Extraire les catégories (souvent dans meta tags ou classes)
            categories = []

            # Meta tag category
            meta_category = soup.find('meta', {'name': 'category'})
            if meta_category and meta_category.get('content'):
                categories.append(meta_category['content'])

            # Classes avec 'category'
            category_elements = soup.find_all(['span', 'a', 'div'], class_=lambda x: x and 'category' in x.lower())
            for elem in category_elements:
                text = elem.get_text().strip()
                if text and len(text) < 50:  # Éviter les longs paragraphes
                    categories.append(text)

            # Extraire les tags
            tags = []

            # Meta keywords
            meta_keywords = soup.find('meta', {'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                tags.extend([k.strip() for k in meta_keywords['content'].split(',')])

            # Tags visuels
            tag_elements = soup.find_all(['a', 'span'], class_=lambda x: x and 'tag' in x.lower())
            for elem in tag_elements:
                text = elem.get_text().strip()
                if text and len(text) < 30:
                    tags.append(text)

            # Extraire le contenu principal
            # Supprimer scripts, styles, navigation
            for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                elem.decompose()

            # Prendre le contenu principal (article ou body)
            main_content = soup.find('article') or soup.find('main') or soup.find('body')
            content = main_content.get_text(separator=' ', strip=True) if main_content else ""

            # Limiter à 3000 caractères pour l'analyse
            content = content[:3000]

            return {
                'url': url,
                'title': title,
                'content': content,
                'breadcrumbs': breadcrumbs,
                'categories': list(set(categories)),  # Dédupliquer
                'tags': list(set(tags))[:10],  # Max 10 tags
                'word_count': len(content.split())
            }

        except Exception as e:
            print(f"  ❌ Erreur extraction: {e}")
            return {
                'url': url,
                'title': '',
                'content': '',
                'breadcrumbs': [],
                'categories': [],
                'tags': [],
                'error': str(e)
            }

    async def classify_with_claude(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Utilise Claude pour classifier la page selon la taxonomie Intelia

        Returns:
            Dict avec: classification_path, confidence, reasoning
        """
        # Construire le prompt avec la taxonomie
        site_types = list(self.taxonomy['site_type_mapping'].keys())
        categories = list(self.taxonomy['categories'].keys())

        prompt = f"""Tu es un expert en classification de contenu avicole. Analyse cette page web et classifie-la selon la taxonomie Intelia.

**PAGE WEB À ANALYSER:**

URL: {page_data['url']}
Titre: {page_data['title']}

Breadcrumbs (fil d'Ariane): {' > '.join(page_data['breadcrumbs']) if page_data['breadcrumbs'] else 'N/A'}
Catégories de la page: {', '.join(page_data['categories']) if page_data['categories'] else 'N/A'}
Tags: {', '.join(page_data['tags'][:5]) if page_data['tags'] else 'N/A'}

Contenu (extrait):
{page_data['content'][:2000]}

---

**TAXONOMIE INTELIA:**

Format de classification: `intelia/{{visibility}}/{{site_type}}/{{category}}/{{subcategory}}`

**Visibility (visibilité):**
- `public` - Contenu public accessible à tous
- `internal` - Contenu interne Intelia

**Site Types disponibles:**
{chr(10).join(f'- {st}' for st in site_types)}

**Catégories principales:**
{chr(10).join(f'- {cat}: {self.taxonomy["categories"][cat]["description"]}' for cat in categories)}

**Subcategories:**
- `common` - Contenu général applicable à tous
- `{{breed_name}}` - Spécifique à une race (ex: ross_308, cobb_500, hy_line_brown)

**Races connues:**
Broilers: ross_308, cobb_500, hubbard_flex
Layers: hy_line_brown, hy_line_w36, lohmann_brown, lohmann_lsl

---

**INSTRUCTIONS:**

1. Analyse le titre, les breadcrumbs, catégories et contenu
2. Détermine le type de site (broiler_farms, layer_farms, veterinary_services, etc.)
3. Identifie la catégorie (biosecurity, management, breed, housing)
4. Détermine si c'est spécifique à une race ou général (common)
5. Évalue ton niveau de confiance (0-100%)

**RÉPONSE ATTENDUE (JSON):**

{{
  "classification": "intelia/public/{{site_type}}/{{category}}/{{subcategory}}",
  "confidence": 85,
  "reasoning": "Explication courte de ta décision basée sur les indices trouvés",
  "key_indicators": ["breadcrumb indique broiler", "mentionne Ross 308", "etc."]
}}

**EXEMPLES:**

- Article sur biosécurité en élevage de poulets de chair → `intelia/public/broiler_farms/biosecurity/common`
- Guide Ross 308 → `intelia/public/broiler_farms/breed/ross_308`
- Article sur maladies aviaires → `intelia/public/veterinary_services/common`
- Guide pondeuses Hy-Line Brown → `intelia/public/layer_farms/breed/hy_line_brown`

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

        try:
            response = await self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extraire le JSON de la réponse
            import json
            response_text = response.content[0].text.strip()

            # Nettoyer le JSON (enlever les balises markdown si présentes)
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result = json.loads(response_text)

            return {
                'classification': result.get('classification', ''),
                'confidence': result.get('confidence', 0),
                'reasoning': result.get('reasoning', ''),
                'key_indicators': result.get('key_indicators', [])
            }

        except Exception as e:
            print(f"  ❌ Erreur classification Claude: {e}")
            return {
                'classification': '',
                'confidence': 0,
                'reasoning': f'Erreur: {str(e)}',
                'key_indicators': []
            }

    async def process_url(self, url: str, row_index: int, dry_run: bool = False) -> Dict[str, Any]:
        """
        Traite une URL: extraction + classification

        Returns:
            Dict avec les résultats
        """
        print(f"\n[{row_index}] {url}")

        # 1. Extraire les métadonnées de la page
        print("  📥 Extraction de la page...")
        page_data = await self.extract_page_metadata(url)

        if 'error' in page_data:
            return {
                'success': False,
                'error': page_data['error']
            }

        # Afficher les métadonnées trouvées
        if page_data['breadcrumbs']:
            print(f"  📍 Breadcrumbs: {' > '.join(page_data['breadcrumbs'][:5])}")
        if page_data['categories']:
            print(f"  🏷️  Catégories: {', '.join(page_data['categories'][:3])}")
        if page_data['tags']:
            print(f"  🔖 Tags: {', '.join(page_data['tags'][:5])}")

        # 2. Classifier avec Claude
        print("  🤖 Classification avec Claude...")
        classification_result = await self.classify_with_claude(page_data)

        if not classification_result['classification']:
            return {
                'success': False,
                'error': classification_result['reasoning']
            }

        print(f"  ✅ Classification: {classification_result['classification']}")
        print(f"     Confiance: {classification_result['confidence']}%")
        print(f"     Raison: {classification_result['reasoning']}")

        return {
            'success': True,
            'classification': classification_result['classification'],
            'confidence': classification_result['confidence'],
            'reasoning': classification_result['reasoning'],
            'page_title': page_data['title'],
            'word_count': page_data['word_count']
        }

    def process_all(self, limit: Optional[int] = None, dry_run: bool = False):
        """
        Traite toutes les URLs avec Classification = "To be analyzed"
        """
        print("=" * 80)
        print("WEB AUTO-CLASSIFIER")
        print("=" * 80)

        # Charger le fichier Excel
        if not os.path.exists(self.excel_file):
            print(f"❌ Fichier Excel non trouvé: {self.excel_file}")
            return

        df = pd.read_excel(self.excel_file, sheet_name=self.sheet_name)

        # Filtrer les URLs à analyser
        to_analyze = df[df['Classification'].str.lower() == 'to be analyzed'].copy()

        if limit:
            to_analyze = to_analyze.head(limit)

        total = len(to_analyze)

        if total == 0:
            print("✅ Aucune URL avec 'To be analyzed' trouvée")
            return

        print(f"📊 {total} URLs à classifier")
        if dry_run:
            print("⚠️  MODE DRY-RUN - Aucune modification ne sera sauvegardée")
        print()

        # Traiter chaque URL
        results = []
        for idx, row in to_analyze.iterrows():
            url = row['Website Address']

            result = asyncio.run(self.process_url(url, idx + 1, dry_run))

            if result['success']:
                # Mettre à jour le DataFrame
                df.at[idx, 'Classification'] = result['classification']
                df.at[idx, 'Notes'] = f"Auto-classified (confidence: {result['confidence']}%) - {result['reasoning']}"

                results.append({
                    'url': url,
                    'classification': result['classification'],
                    'confidence': result['confidence']
                })
            else:
                df.at[idx, 'Notes'] = f"Classification failed: {result['error']}"
                results.append({
                    'url': url,
                    'classification': 'FAILED',
                    'error': result['error']
                })

            # Petite pause entre URLs
            if idx < len(to_analyze) - 1:
                import time
                time.sleep(2)

        # Sauvegarder le fichier Excel
        if not dry_run:
            print("\n💾 Sauvegarde dans Excel...")
            df.to_excel(self.excel_file, sheet_name=self.sheet_name, index=False)
            print(f"✅ Fichier sauvegardé: {self.excel_file}")

        # Afficher le résumé
        print("\n" + "=" * 80)
        print("RÉSUMÉ DE LA CLASSIFICATION")
        print("=" * 80)

        successful = [r for r in results if r.get('classification') != 'FAILED']
        failed = [r for r in results if r.get('classification') == 'FAILED']

        print(f"Total traité: {total}")
        print(f"✅ Succès: {len(successful)}")
        print(f"❌ Échecs: {len(failed)}")

        if successful:
            avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
            print(f"📊 Confiance moyenne: {avg_confidence:.1f}%")

        print("\n📋 Classifications attribuées:")
        classification_counts = {}
        for r in successful:
            classification_counts[r['classification']] = classification_counts.get(r['classification'], 0) + 1

        for classification, count in sorted(classification_counts.items()):
            print(f"  - {classification}: {count} URL(s)")

        if failed:
            print("\n⚠️  URLs en échec:")
            for r in failed:
                print(f"  - {r['url']}: {r.get('error', 'Unknown error')}")

        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Auto-classifier pour pages web')
    parser.add_argument('--limit', type=int, help='Limiter le nombre d\'URLs à traiter')
    parser.add_argument('--dry-run', action='store_true', help='Afficher sans modifier Excel')
    parser.add_argument('--excel', default='websites.xlsx', help='Fichier Excel (défaut: websites.xlsx)')

    args = parser.parse_args()

    classifier = WebAutoClassifier(excel_file=args.excel)
    classifier.process_all(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
