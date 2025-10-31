"""
Web Scraper
Extracts text content from web pages
Converts HTML to clean markdown for knowledge extraction
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse


@dataclass
class WebExtractionResult:
    """Result of web page extraction"""
    url: str
    title: str
    full_text: str
    metadata: Dict[str, Any]
    word_count: int
    success: bool
    error: Optional[str] = None


class WebScraper:
    """
    Extract text content from web pages.

    Strategy:
    1. Fetch HTML content
    2. Extract main content (remove nav, footer, ads, etc.)
    3. Convert to clean markdown
    4. Return structured content
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize Web Scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def extract_web_page(self, url: str) -> WebExtractionResult:
        """
        Extract text content from web page.

        Args:
            url: URL of the web page

        Returns:
            WebExtractionResult with extracted content
        """
        print(f"Fetching {url}")

        try:
            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract metadata
            metadata = self._extract_metadata(soup, url)

            # Extract title
            title = self._extract_title(soup, metadata)

            # Remove unwanted elements
            self._remove_unwanted_elements(soup)

            # Extract main content
            main_content = self._extract_main_content(soup)

            # Convert to markdown
            markdown_text = md(str(main_content), heading_style="ATX")

            # Clean up markdown
            markdown_text = self._clean_markdown(markdown_text)

            # Calculate word count
            word_count = len(markdown_text.split())

            return WebExtractionResult(
                url=url,
                title=title,
                full_text=markdown_text,
                metadata=metadata,
                word_count=word_count,
                success=True
            )

        except Exception as e:
            return WebExtractionResult(
                url=url,
                title="",
                full_text="",
                metadata={},
                word_count=0,
                success=False,
                error=str(e)
            )

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract page metadata"""
        metadata = {
            "url": url,
            "domain": urlparse(url).netloc,
        }

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            metadata["description"] = meta_desc["content"]

        # Meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            metadata["keywords"] = meta_keywords["content"]

        # Author
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            metadata["author"] = meta_author["content"]

        # Open Graph metadata
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            metadata["og_title"] = og_title["content"]

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            metadata["og_description"] = og_desc["content"]

        return metadata

    def _extract_title(self, soup: BeautifulSoup, metadata: Dict[str, Any]) -> str:
        """Extract page title"""
        # Try different sources
        if "og_title" in metadata:
            return metadata["og_title"]

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        return "Untitled"

    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove navigation, footer, ads, scripts, etc."""
        # Remove scripts and styles
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Remove common unwanted elements
        unwanted_selectors = [
            "nav", "header", "footer",
            ".navigation", ".nav", ".menu",
            ".sidebar", ".widget",
            ".advertisement", ".ad", ".ads",
            ".social-share", ".comments",
            "#comments", "#sidebar", "#footer", "#header", "#navigation"
        ]

        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

    def _extract_main_content(self, soup: BeautifulSoup):
        """Extract main content area"""
        # Try to find main content container
        main_selectors = [
            "main",
            "article",
            '[role="main"]',
            ".main-content",
            ".content",
            "#main",
            "#content",
            ".article-content",
            ".post-content"
        ]

        for selector in main_selectors:
            main = soup.select_one(selector)
            if main:
                return main

        # Fallback: use body
        return soup.body if soup.body else soup

    def _clean_markdown(self, markdown_text: str) -> str:
        """Clean up markdown text"""
        # Remove excessive blank lines
        lines = markdown_text.split('\n')
        cleaned_lines = []
        prev_blank = False

        for line in lines:
            is_blank = line.strip() == ""

            if is_blank:
                if not prev_blank:
                    cleaned_lines.append(line)
                prev_blank = True
            else:
                cleaned_lines.append(line)
                prev_blank = False

        return '\n'.join(cleaned_lines).strip()


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python web_scraper.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    # Initialize scraper
    scraper = WebScraper()

    # Extract web page
    result = scraper.extract_web_page(url)

    if result.success:
        print("\n" + "="*80)
        print("EXTRACTION SUCCESSFUL")
        print("="*80)
        print(f"URL: {result.url}")
        print(f"Title: {result.title}")
        print(f"Total words: {result.word_count}")
        print()

        # Show metadata
        print("Metadata:")
        for key, value in result.metadata.items():
            if value:
                print(f"  {key}: {value[:100] if isinstance(value, str) else value}")
        print()

        # Show first 500 characters
        print("Content preview:")
        print("-" * 80)
        print(result.full_text[:500])
        if len(result.full_text) > 500:
            print("...")
        print()
    else:
        print(f"ERROR: {result.error}")
