"""
Source Integrators

Parse outputs from other skills (web-scraper, literature-review, science-grounded).
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class WebScraperIntegrator:
    """Parse web-scraper skill output."""

    def __init__(self):
        """Initialize web-scraper integrator."""
        pass

    def parse(self, scrape_results_file: Path) -> Dict:
        """
        Parse web-scraper output JSON file.

        Args:
            scrape_results_file: Path to scrape_results.json

        Returns:
            Structured content dict with:
                - title: Page title
                - description: Meta description
                - content: Main text content
                - sections: List of content sections
                - images_dir: Path to images directory
                - metadata: Additional metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        if not scrape_results_file.exists():
            raise FileNotFoundError(f"Scrape results not found: {scrape_results_file}")

        with open(scrape_results_file, 'r') as f:
            data = json.load(f)

        # Parse content
        title = data.get('title', 'Untitled Report')
        description = data.get('metadata', {}).get('description', '')
        content = data.get('content', '')

        # Find images directory (sibling to scrape_results.json)
        images_dir = scrape_results_file.parent / 'images'

        # Build sections from content
        sections = self._parse_content_to_sections(content, title)

        result = {
            'title': title,
            'description': description,
            'content': content,
            'sections': sections,
            'images_dir': images_dir if images_dir.exists() else None,
            'metadata': data.get('metadata', {}),
            'url': data.get('url', ''),
            'links': data.get('links', {}),
            'lists': data.get('lists', [])
        }

        logger.info(f"Parsed web-scraper output: {title}")
        logger.info(f"  Sections: {len(sections)}")
        logger.info(f"  Images directory: {images_dir if images_dir.exists() else 'Not found'}")

        return result

    def _parse_content_to_sections(self, content: str, title: str) -> List[Dict]:
        """
        Parse content into sections.

        Args:
            content: Main content text
            title: Page title

        Returns:
            List of section dicts with 'title' and 'content'
        """
        sections = []

        # Simple parsing: split on common section headers
        # In a full implementation, this would be more sophisticated

        # For now, create a single main section
        sections.append({
            'title': 'Overview',
            'content': content[:2000] if len(content) > 2000 else content
        })

        # Extract key findings (look for bullet lists)
        if '-' in content or '*' in content or '•' in content:
            # Find bullet-heavy sections
            bullet_section = self._extract_bullet_section(content)
            if bullet_section:
                sections.append({
                    'title': 'Key Findings',
                    'content': bullet_section
                })

        return sections

    def _extract_bullet_section(self, content: str) -> str:
        """
        Extract a section with bullet points.

        Args:
            content: Full content text

        Returns:
            Section with bullets or empty string
        """
        lines = content.split('\n')
        bullet_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith(('-', '*', '•')):
                bullet_lines.append(line)

        if len(bullet_lines) > 3:
            return '\n'.join(bullet_lines[:10])  # Limit to 10 bullets
        return ''


class LiteratureReviewIntegrator:
    """Parse literature-review skill output."""

    def __init__(self):
        """Initialize literature-review integrator."""
        pass

    def parse(self, markdown_file: Path) -> Dict:
        """
        Parse literature review markdown file.

        Args:
            markdown_file: Path to markdown file with citations

        Returns:
            Structured content dict
        """
        if not markdown_file.exists():
            raise FileNotFoundError(f"Literature review not found: {markdown_file}")

        with open(markdown_file, 'r') as f:
            content = f.read()

        # Extract title (first # header)
        title = 'Literature Review'
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line.replace('# ', '').strip()
                break

        return {
            'title': title,
            'content': content,
            'sections': [],  # TODO: Parse markdown sections
            'citations': []   # TODO: Extract citations
        }


class ScienceGroundedIntegrator:
    """Parse science-grounded skill output."""

    def __init__(self):
        """Initialize science-grounded integrator."""
        pass

    def parse(self, papers_file: Path) -> Dict:
        """
        Parse science-grounded verified papers JSON.

        Args:
            papers_file: Path to verified_papers.json

        Returns:
            Structured content dict with papers
        """
        if not papers_file.exists():
            raise FileNotFoundError(f"Papers file not found: {papers_file}")

        with open(papers_file, 'r') as f:
            data = json.load(f)

        papers = data.get('papers', [])

        return {
            'papers': papers,
            'count': len(papers)
        }


def main():
    """Test source integrators."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python source_integrators.py <scrape_results.json>")
        sys.exit(1)

    scrape_file = Path(sys.argv[1])

    integrator = WebScraperIntegrator()

    try:
        result = integrator.parse(scrape_file)

        print(f"Title: {result['title']}")
        print(f"Description: {result['description'][:100]}...")
        print(f"\nSections:")
        for section in result['sections']:
            print(f"  - {section['title']} ({len(section['content'])} chars)")

        if result['images_dir']:
            print(f"\nImages directory: {result['images_dir']}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
