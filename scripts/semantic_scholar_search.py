#!/usr/bin/env python3
"""
semantic_scholar_search.py - Primary literature search via Semantic Scholar API
Provides citation counts, journal information, and open access status.

Rate limit: 100 requests per 5 minutes (enforced via paper_utils)
API Documentation: https://api.semanticscholar.org/
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
from urllib.parse import quote

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from paper_utils import (
    sanitize_query,
    rate_limit_request,
    get_cached_results,
    cache_results,
    sort_by_impact,
    log_api_request,
    timeout_handler,
    validate_paper_data,
    REQUEST_TIMEOUT
)

# Configure logging
logger = logging.getLogger(__name__)

# Semantic Scholar API configuration
BASE_URL = "https://api.semanticscholar.org/graph/v1"
PAPER_SEARCH_URL = f"{BASE_URL}/paper/search"
PAPER_DETAILS_URL = f"{BASE_URL}/paper"

# Fields to retrieve from API
SEARCH_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "abstract",
    "citationCount",
    "journal",
    "publicationTypes",
    "isOpenAccess",
    "url",
    "venue",
    "fieldsOfStudy",
    "externalIds"
]

# Maximum papers to retrieve
MAX_RESULTS = 50
DEFAULT_LIMIT = 10


class SemanticScholarSearch:
    """
    Search for papers using Semantic Scholar API.
    """

    def __init__(self):
        """Initialize the Semantic Scholar search client."""
        self.api_name = "semantic_scholar"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science-Grounded-Skill/1.0 (Educational/Research Tool)'
        })

    def search(self, query: str, limit: int = DEFAULT_LIMIT,
              use_cache: bool = True) -> List[Dict]:
        """
        Search for papers on Semantic Scholar.

        Args:
            query: Search query
            limit: Maximum number of results (max 50)
            use_cache: Whether to use cached results

        Returns:
            List of paper dictionaries with standardized format
        """
        # Sanitize query
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.error("Query failed sanitization")
            return []

        # Check cache first
        if use_cache:
            cached = get_cached_results(clean_query, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        papers = self._search_papers(clean_query, min(limit, MAX_RESULTS))

        # Cache results if successful
        if papers:
            cache_results(clean_query, papers, self.api_name)

        # Sort by impact and return requested number
        sorted_papers = sort_by_impact(papers)
        return sorted_papers[:limit]

    @timeout_handler
    def _search_papers(self, query: str, limit: int) -> List[Dict]:
        """
        Internal method to search papers via API.

        Args:
            query: Sanitized search query
            limit: Number of results to retrieve

        Returns:
            List of paper dictionaries
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        # Prepare request parameters
        params = {
            'query': query,
            'limit': limit,
            'fields': ','.join(SEARCH_FIELDS)
        }

        try:
            # Make API request
            logger.info(f"Searching Semantic Scholar for: {query[:50]}...")
            response = self.session.get(
                PAPER_SEARCH_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            # Log the request
            log_api_request(self.api_name, query, response.status_code)

            # Check response
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                logger.info(f"Found {len(papers)} papers")

                # Convert to standardized format
                standardized = []
                for paper in papers:
                    std_paper = self._standardize_paper(paper)
                    if validate_paper_data(std_paper):
                        standardized.append(std_paper)

                return standardized

            elif response.status_code == 429:
                logger.error("Rate limit exceeded for Semantic Scholar")
                return []

            else:
                logger.error(f"Semantic Scholar API error: {response.status_code}")
                return []

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after {REQUEST_TIMEOUT}s")
            log_api_request(self.api_name, query, error="Timeout")
            return []

        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
            log_api_request(self.api_name, query, error=str(e))
            return []

    def _standardize_paper(self, paper: Dict) -> Dict:
        """
        Convert Semantic Scholar format to standardized format.

        Args:
            paper: Paper data from Semantic Scholar API

        Returns:
            Standardized paper dictionary
        """
        # Extract authors
        authors = []
        author_list = paper.get('authors', [])
        for author in author_list:
            if author and 'name' in author:
                authors.append(author['name'])

        # Extract DOI if available
        doi = None
        external_ids = paper.get('externalIds', {})
        if external_ids:
            doi = external_ids.get('DOI')

        # Get journal name (prefer journal over venue)
        journal = paper.get('journal', {})
        journal_name = None
        if journal and 'name' in journal:
            journal_name = journal['name']
        elif paper.get('venue'):
            journal_name = paper.get('venue')

        # Build standardized paper
        std_paper = {
            'title': paper.get('title', 'Unknown Title'),
            'authors': authors,
            'year': paper.get('year'),
            'doi': doi,
            'abstract': paper.get('abstract', ''),
            'citation_count': paper.get('citationCount', 0),
            'journal': journal_name,
            'is_open_access': paper.get('isOpenAccess', False),
            'url': paper.get('url', ''),
            'source': 'semantic_scholar',
            'paper_id': paper.get('paperId'),
            'fields_of_study': paper.get('fieldsOfStudy', []),
            'publication_types': paper.get('publicationTypes', [])
        }

        return std_paper

    def get_paper_details(self, paper_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific paper.

        Args:
            paper_id: Semantic Scholar paper ID

        Returns:
            Paper dictionary or None if not found
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        # Build URL
        url = f"{PAPER_DETAILS_URL}/{paper_id}"
        params = {'fields': ','.join(SEARCH_FIELDS)}

        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                paper = response.json()
                return self._standardize_paper(paper)
            else:
                logger.error(f"Failed to get paper details: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting paper details: {e}")
            return None


def test_semantic_scholar():
    """
    Test Semantic Scholar search functionality.
    """
    print("Testing Semantic Scholar Search")
    print("=" * 60)

    # Initialize searcher
    searcher = SemanticScholarSearch()

    # Test queries relevant to user's research
    test_queries = [
        "Epileptor model Jirsa",
        "SINDy Brunton sparse identification",
        "Koopman operator neural networks",
        "seizure prediction machine learning",
        "phase amplitude coupling epilepsy"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Search without cache to test actual API
        papers = searcher.search(query, limit=5, use_cache=False)

        if papers:
            for i, paper in enumerate(papers[:3], 1):
                print(f"\n{i}. {paper['title'][:80]}...")
                print(f"   Authors: {', '.join(paper['authors'][:3])}")
                print(f"   Year: {paper['year']}")
                print(f"   Citations: {paper['citation_count']}")
                print(f"   Journal: {paper['journal']}")
                print(f"   Open Access: {paper['is_open_access']}")
                print(f"   Impact Score: {paper.get('impact_score', 0):.1f}")
                if paper.get('doi'):
                    print(f"   DOI: {paper['doi']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test caching
    print("\n" + "=" * 60)
    print("Testing cache functionality...")
    test_query = "neural oscillations"

    # First search (will cache)
    print(f"First search for: {test_query}")
    start = time.time()
    papers1 = searcher.search(test_query, limit=5)
    time1 = time.time() - start
    print(f"Time: {time1:.2f}s, Results: {len(papers1)}")

    # Second search (should use cache)
    print(f"Second search (cached): {test_query}")
    start = time.time()
    papers2 = searcher.search(test_query, limit=5)
    time2 = time.time() - start
    print(f"Time: {time2:.2f}s, Results: {len(papers2)}")

    if time2 < time1 / 2:
        print("✓ Cache is working (second search was faster)")
    else:
        print("✗ Cache might not be working properly")

    print("\n" + "=" * 60)
    print("Semantic Scholar testing complete!")


if __name__ == "__main__":
    # Handle command line usage
    if len(sys.argv) > 1:
        # Use provided query
        query = ' '.join(sys.argv[1:])
        searcher = SemanticScholarSearch()
        papers = searcher.search(query, limit=10)

        print(f"Query: {query}")
        print(f"Found {len(papers)} papers\n")

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}")
            if len(paper['authors']) > 3:
                print(f"            et al.")
            print(f"   Year: {paper['year']}")
            print(f"   Citations: {paper['citation_count']}")
            print(f"   Journal: {paper['journal']}")
            print(f"   Impact Score: {paper.get('impact_score', 0):.1f}")
            if paper.get('doi'):
                print(f"   DOI: https://doi.org/{paper['doi']}")
            print()
    else:
        # Run tests
        test_semantic_scholar()