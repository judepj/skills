#!/usr/bin/env python3
"""
local_kb_search.py - Search local knowledge base before hitting external APIs

Integrates with existing query_kb.py to search ~70 papers already extracted.
Returns local papers FIRST, then falls back to external APIs if needed.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOCAL_PATHS_CONFIG = CONFIG_DIR / "local_paths.json"


def _load_kb_path() -> Optional[Path]:
    """Load knowledge base path from local config.

    Returns None if config doesn't exist (graceful degradation).
    Users can copy local_paths.template.json to local_paths.json and add their paths.
    """
    if LOCAL_PATHS_CONFIG.exists():
        try:
            with open(LOCAL_PATHS_CONFIG, 'r') as f:
                config = json.load(f)
                kb_path = config.get('knowledge_base')
                if kb_path:
                    return Path(kb_path)
        except (json.JSONDecodeError, IOError):
            pass
    return None


# Load KB path from config (None if not configured)
KB_BASE = _load_kb_path()
PAPERS_DIR = KB_BASE / "raw" / "papers" if KB_BASE else None
INDEX_FILE = KB_BASE / "indexes" / "master_index.json" if KB_BASE else None


class LocalKBSearch:
    """Search local knowledge base for papers."""

    def __init__(self, kb_path: Optional[Path] = None):
        """
        Initialize local KB search.

        Args:
            kb_path: Path to knowledge base (defaults to config or None)
        """
        self.kb_path = kb_path or KB_BASE

        # Handle case where no KB is configured
        if self.kb_path is None:
            self.papers_dir = None
            self.index_file = None
            self.available = False
            logger.info("Local knowledge base not configured. Set path in config/local_paths.json")
        else:
            self.papers_dir = self.kb_path / "raw" / "papers"
            self.index_file = self.kb_path / "indexes" / "master_index.json"

            # Check if knowledge base exists
            self.available = self.papers_dir.exists()
            if not self.available:
                logger.info(f"Local knowledge base not found at {self.papers_dir}. Local search disabled.")

        # Load index if exists
        self.index = self._load_index()

    def is_available(self) -> bool:
        """Check if local knowledge base is available."""
        return self.available

    def _load_index(self) -> Dict:
        """Load master index if available."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load index: {e}")
                return {}
        return {}

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search local knowledge base for papers matching query.

        Args:
            query: Search query (keywords)
            limit: Maximum results to return

        Returns:
            List of paper dictionaries with metadata (empty list if KB not available)
        """
        # Return empty if knowledge base not available
        if not self.available:
            return []

        query_lower = query.lower()
        keywords = query_lower.split()

        results = []

        # Search through papers directory
        for paper_dir in self.papers_dir.iterdir():
            if not paper_dir.is_dir():
                continue

            # Try to load paper metadata
            extraction_file = paper_dir / "extraction.json"
            clean_text_file = paper_dir / "clean_text.txt"

            if not (extraction_file.exists() or clean_text_file.exists()):
                continue

            # Load metadata
            metadata = None
            if extraction_file.exists():
                try:
                    with open(extraction_file, 'r') as f:
                        data = json.load(f)
                        metadata = data.get('metadata', {})
                except:
                    pass

            # Load clean text for searching
            text_content = ""
            if clean_text_file.exists():
                try:
                    with open(clean_text_file, 'r') as f:
                        text_content = f.read().lower()
                except:
                    pass

            # Score this paper based on keyword matches
            score = 0
            matched_keywords = []

            for keyword in keywords:
                if len(keyword) < 3:  # Skip very short keywords
                    continue

                # Check in folder name
                if keyword in paper_dir.name.lower():
                    score += 5
                    matched_keywords.append(keyword)

                # Check in text content
                if keyword in text_content:
                    score += text_content.count(keyword)
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

                # Check in metadata if available
                if metadata:
                    title = metadata.get('title', '').lower()
                    authors = ' '.join(metadata.get('authors', [])).lower()
                    if keyword in title:
                        score += 10
                    if keyword in authors:
                        score += 8

            # If any keywords matched, add to results
            if score > 0:
                paper_info = {
                    'paper_id': paper_dir.name,
                    'local_path': str(paper_dir),
                    'score': score,
                    'matched_keywords': matched_keywords,
                    'source': 'local_kb'
                }

                # Add metadata if available
                if metadata:
                    paper_info.update({
                        'title': metadata.get('title', ''),
                        'authors': metadata.get('authors', []),
                        'year': metadata.get('year', ''),
                        'journal': metadata.get('journal', ''),
                        'doi': metadata.get('doi', '')
                    })
                else:
                    # Extract from clean_text if no extraction.json
                    paper_info['title'] = paper_dir.name.replace('_', ' ').title()

                results.append(paper_info)

        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)

        logger.info(f"Local KB search found {len(results)} papers for query: {query}")

        return results[:limit]

    def get_paper_content(self, paper_id: str) -> Optional[str]:
        """
        Get full content of a paper from local KB.

        Args:
            paper_id: Paper identifier (folder name)

        Returns:
            Full paper text or None if not found or KB not available
        """
        # Return None if knowledge base not available
        if not self.available:
            return None

        paper_dir = self.papers_dir / paper_id

        if not paper_dir.exists():
            # Try partial match
            for dir in self.papers_dir.iterdir():
                if paper_id.lower() in dir.name.lower():
                    paper_dir = dir
                    break

        if not paper_dir.exists():
            return None

        clean_text = paper_dir / "clean_text.txt"
        if clean_text.exists():
            with open(clean_text, 'r') as f:
                return f.read()

        return None


# Convenience function for quick searches
def search_local_kb(query: str, limit: int = 5) -> List[Dict]:
    """
    Quick search of local knowledge base.

    Usage:
        from local_kb_search import search_local_kb
        results = search_local_kb("thalamic stimulation epilepsy")
    """
    searcher = LocalKBSearch()
    return searcher.search(query, limit=limit)


if __name__ == "__main__":
    # Test the search
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "thalamic stimulation"

    print(f"Searching local KB for: {query}\n")

    searcher = LocalKBSearch()
    results = searcher.search(query, limit=10)

    print(f"Found {len(results)} results:\n")

    for i, paper in enumerate(results, 1):
        print(f"{i}. {paper.get('title', paper['paper_id'])}")
        print(f"   Score: {paper['score']}")
        print(f"   Matched: {', '.join(paper['matched_keywords'])}")
        if paper.get('authors'):
            print(f"   Authors: {', '.join(paper['authors'][:3])}")
        if paper.get('year'):
            print(f"   Year: {paper['year']}")
        print()
