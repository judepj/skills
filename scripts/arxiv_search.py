#!/usr/bin/env python3
"""
arxiv_search.py - Search for preprints on arXiv
Focuses on neuroscience, signal processing, machine learning, and dynamical systems.

Categories of interest:
- q-bio.NC: Neurons and Cognition
- eess.SP: Signal Processing
- cs.LG: Machine Learning
- nlin.CD: Chaotic Dynamics
- math.DS: Dynamical Systems
- physics.comp-ph: Computational Physics
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import arxiv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from paper_utils import (
    sanitize_query,
    rate_limit_request,
    get_cached_results,
    cache_results,
    sort_by_impact,
    log_api_request,
    validate_paper_data
)

# Configure logging
logger = logging.getLogger(__name__)

# ArXiv categories relevant to the user's research
RELEVANT_CATEGORIES = [
    'q-bio.NC',  # Neurons and Cognition
    'eess.SP',   # Signal Processing
    'cs.LG',     # Machine Learning
    'cs.NE',     # Neural and Evolutionary Computing
    'nlin.CD',   # Chaotic Dynamics
    'math.DS',   # Dynamical Systems
    'physics.comp-ph',  # Computational Physics
    'stat.ML',   # Machine Learning (Statistics)
    'physics.med-ph',  # Medical Physics
    'cs.AI',     # Artificial Intelligence
    'math.NA',   # Numerical Analysis
    'physics.bio-ph',  # Biological Physics
]

# Maximum results
MAX_RESULTS = 50
DEFAULT_LIMIT = 10


class ArxivSearch:
    """
    Search for papers on arXiv preprint server.
    """

    def __init__(self):
        """Initialize the arXiv search client."""
        self.api_name = "arxiv"

    def search(self, query: str, limit: int = DEFAULT_LIMIT,
              use_cache: bool = True, filter_categories: bool = True) -> List[Dict]:
        """
        Search for papers on arXiv.

        Args:
            query: Search query
            limit: Maximum number of results (max 50)
            use_cache: Whether to use cached results
            filter_categories: Filter to relevant categories only

        Returns:
            List of paper dictionaries with standardized format
        """
        # Sanitize query
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.error("Query failed sanitization")
            return []

        # Check cache first
        cache_key = f"{clean_query}_filtered" if filter_categories else clean_query
        if use_cache:
            cached = get_cached_results(cache_key, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        papers = self._search_papers(clean_query, min(limit * 2, MAX_RESULTS), filter_categories)

        # Cache results if successful
        if papers:
            cache_results(cache_key, papers, self.api_name)

        # Sort by impact (for arXiv, we use a modified scoring)
        sorted_papers = self._sort_arxiv_papers(papers)
        return sorted_papers[:limit]

    def _search_papers(self, query: str, limit: int, filter_categories: bool) -> List[Dict]:
        """
        Internal method to search papers via arXiv API.

        Args:
            query: Sanitized search query
            limit: Number of results to retrieve
            filter_categories: Whether to filter by relevant categories

        Returns:
            List of paper dictionaries
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        try:
            # Create search object
            logger.info(f"Searching arXiv for: {query[:50]}...")

            # Build arXiv query
            if filter_categories:
                # Add category filtering to query
                cat_query = ' OR '.join([f'cat:{cat}' for cat in RELEVANT_CATEGORIES])
                full_query = f'({query}) AND ({cat_query})'
            else:
                full_query = query

            # Perform search
            search = arxiv.Search(
                query=full_query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending
            )

            # Execute search and collect results
            papers = []
            for result in search.results():
                std_paper = self._standardize_paper(result)
                if validate_paper_data(std_paper):
                    papers.append(std_paper)

            logger.info(f"Found {len(papers)} papers on arXiv")
            log_api_request(self.api_name, query, 200)

            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            log_api_request(self.api_name, query, error=str(e))
            return []

    def _standardize_paper(self, result: arxiv.Result) -> Dict:
        """
        Convert arXiv result to standardized format.

        Args:
            result: arXiv Result object

        Returns:
            Standardized paper dictionary
        """
        # Extract authors
        authors = [author.name for author in result.authors]

        # Extract year from published date
        year = result.published.year if result.published else None

        # Get categories
        categories = result.categories

        # Check if it's in relevant categories
        is_relevant = any(cat in RELEVANT_CATEGORIES for cat in categories)

        # Build standardized paper
        std_paper = {
            'title': result.title,
            'authors': authors,
            'year': year,
            'doi': result.doi,
            'abstract': result.summary,
            'citation_count': 0,  # arXiv doesn't provide citations
            'journal': 'arXiv preprint',
            'is_open_access': True,  # All arXiv papers are open access
            'url': result.entry_id,
            'pdf_url': result.pdf_url,
            'source': 'arxiv',
            'arxiv_id': result.entry_id.split('/')[-1],
            'categories': categories,
            'is_relevant_category': is_relevant,
            'published_date': result.published.isoformat() if result.published else None,
            'updated_date': result.updated.isoformat() if result.updated else None
        }

        return std_paper

    def _sort_arxiv_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Sort arXiv papers by relevance and recency.
        Since arXiv doesn't have citation counts, we use different criteria.

        Args:
            papers: List of paper dictionaries

        Returns:
            Sorted list of papers
        """
        for paper in papers:
            # Calculate a pseudo-impact score based on:
            # 1. Category relevance
            # 2. Recency
            # 3. Whether it's been updated (indicates active work)

            score = 1.0

            # Boost for relevant categories
            if paper.get('is_relevant_category'):
                score *= 2.0

            # Boost for recent papers (last 2 years)
            year = paper.get('year')
            current_year = datetime.now().year
            if year:
                if year >= current_year - 1:
                    score *= 2.0  # Very recent
                elif year >= current_year - 2:
                    score *= 1.5  # Recent
                elif year >= current_year - 3:
                    score *= 1.2  # Somewhat recent

            # Check if paper has been updated after initial publication
            if paper.get('updated_date') and paper.get('published_date'):
                if paper['updated_date'] > paper['published_date']:
                    score *= 1.1  # Has been updated

            paper['impact_score'] = score

        # Sort by impact score
        return sorted(papers, key=lambda p: p.get('impact_score', 0), reverse=True)

    def search_by_author(self, author_name: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search for papers by a specific author.

        Args:
            author_name: Name of the author
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        query = f'au:"{author_name}"'
        return self.search(query, limit=limit, filter_categories=False)

    def search_by_category(self, category: str, query: str = "",
                          limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search within a specific arXiv category.

        Args:
            category: arXiv category code (e.g., 'q-bio.NC')
            query: Additional search terms
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        if query:
            full_query = f'{query} AND cat:{category}'
        else:
            full_query = f'cat:{category}'

        return self.search(full_query, limit=limit, filter_categories=False)


def test_arxiv():
    """
    Test arXiv search functionality.
    """
    print("Testing arXiv Search")
    print("=" * 60)

    # Initialize searcher
    searcher = ArxivSearch()

    # Test queries relevant to user's research
    test_queries = [
        "Koopman operator neural networks",
        "SINDy sparse identification nonlinear",
        "seizure prediction deep learning",
        "EEG signal processing wavelets",
        "dynamical systems brain"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Search without cache to test actual API
        papers = searcher.search(query, limit=3, use_cache=False)

        if papers:
            for i, paper in enumerate(papers, 1):
                print(f"\n{i}. {paper['title'][:80]}...")
                print(f"   Authors: {', '.join(paper['authors'][:2])}")
                if len(paper['authors']) > 2:
                    print(f"            et al.")
                print(f"   Year: {paper['year']}")
                print(f"   Categories: {', '.join(paper['categories'][:3])}")
                print(f"   Relevant: {paper['is_relevant_category']}")
                print(f"   Score: {paper.get('impact_score', 0):.1f}")
                print(f"   arXiv ID: {paper['arxiv_id']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test author search
    print("\n" + "=" * 60)
    print("Testing author search...")
    papers = searcher.search_by_author("Steven L. Brunton", limit=3)
    print(f"Papers by Steven L. Brunton: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    # Test category search
    print("\nTesting category search...")
    papers = searcher.search_by_category("q-bio.NC", "oscillations", limit=3)
    print(f"Papers in q-bio.NC about oscillations: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    print("\n" + "=" * 60)
    print("arXiv testing complete!")


if __name__ == "__main__":
    # Handle command line usage
    if len(sys.argv) > 1:
        # Use provided query
        query = ' '.join(sys.argv[1:])
        searcher = ArxivSearch()
        papers = searcher.search(query, limit=10)

        print(f"Query: {query}")
        print(f"Found {len(papers)} papers\n")

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}")
            if len(paper['authors']) > 3:
                print(f"            et al.")
            print(f"   Year: {paper['year']}")
            print(f"   Categories: {', '.join(paper['categories'])}")
            print(f"   arXiv: https://arxiv.org/abs/{paper['arxiv_id']}")
            print(f"   PDF: {paper['pdf_url']}")
            print()
    else:
        # Run tests
        test_arxiv()