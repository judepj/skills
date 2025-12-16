#!/usr/bin/env python3
"""
biorxiv_search.py - Search for preprints on bioRxiv and medRxiv
Focuses on biological and medical preprints relevant to neuroscience and epilepsy.

bioRxiv: Biological sciences preprints
medRxiv: Medical and health sciences preprints

API Documentation: https://api.biorxiv.org/
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
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

# bioRxiv/medRxiv API configuration
BASE_URL = "https://api.biorxiv.org"
CONTENT_DETAIL_URL = f"{BASE_URL}/details"
SEARCH_URL = f"{BASE_URL}/pubs"

# Categories relevant to neuroscience/epilepsy
RELEVANT_CATEGORIES = [
    'neuroscience',
    'biophysics',
    'systems biology',
    'bioinformatics',
    'cell biology',
    'genetics',
    'physiology',
    'epidemiology',
    'neurology',
    'psychiatry and clinical psychology'
]

# Maximum results
MAX_RESULTS = 100
DEFAULT_LIMIT = 10


class BiorxivSearch:
    """
    Search for papers on bioRxiv and medRxiv preprint servers.
    """

    def __init__(self):
        """Initialize the bioRxiv/medRxiv search client."""
        self.api_name = "biorxiv"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science-Grounded-Skill/1.0 (Educational/Research Tool)',
            'Accept': 'application/json'
        })

    def search(self, query: str, server: str = "both", limit: int = DEFAULT_LIMIT,
              use_cache: bool = True) -> List[Dict]:
        """
        Search for papers on bioRxiv/medRxiv.

        Args:
            query: Search query
            server: Which server to search ("biorxiv", "medrxiv", or "both")
            limit: Maximum number of results
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
        cache_key = f"{clean_query}_{server}"
        if use_cache:
            cached = get_cached_results(cache_key, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        papers = self._search_papers(clean_query, server, min(limit * 2, MAX_RESULTS))

        # Cache results if successful
        if papers:
            cache_results(cache_key, papers, self.api_name)

        # Sort by impact (for preprints, we use recency and relevance)
        sorted_papers = self._sort_biorxiv_papers(papers)
        return sorted_papers[:limit]

    @timeout_handler
    def _search_papers(self, query: str, server: str, limit: int) -> List[Dict]:
        """
        Internal method to search papers via bioRxiv/medRxiv API.

        Args:
            query: Sanitized search query
            server: Which server(s) to search
            limit: Number of results to retrieve

        Returns:
            List of paper dictionaries
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        papers = []

        # Determine which servers to search
        servers_to_search = []
        if server in ["biorxiv", "both"]:
            servers_to_search.append("biorxiv")
        if server in ["medrxiv", "both"]:
            servers_to_search.append("medrxiv")

        for srv in servers_to_search:
            try:
                # Use content detail API for date-based retrieval
                # We'll get recent papers and filter by query
                papers_from_server = self._get_recent_papers(srv, query, limit)
                papers.extend(papers_from_server)

            except Exception as e:
                logger.error(f"Error searching {srv}: {e}")
                log_api_request(self.api_name, query, error=str(e))

        # Remove duplicates based on title
        unique_papers = {}
        for paper in papers:
            title_key = paper['title'].lower().strip()
            if title_key not in unique_papers:
                unique_papers[title_key] = paper

        return list(unique_papers.values())

    def _get_recent_papers(self, server: str, query: str, limit: int) -> List[Dict]:
        """
        Get recent papers from a specific server and filter by query.

        Args:
            server: "biorxiv" or "medrxiv"
            query: Search terms to filter by
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        # Get date range (last 6 months)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        # Build API URL for content details
        # Format: /details/{server}/{interval}/{cursor}/{format}
        # We'll use interval format: YYYY-MM-DD/YYYY-MM-DD
        url = f"{CONTENT_DETAIL_URL}/{server}/{start_date}/{end_date}/0/json"

        try:
            logger.info(f"Fetching recent papers from {server}: {query[:50]}...")
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])

                if messages and messages[0].get('status') == 'ok':
                    papers_data = data.get('collection', [])

                    # Filter papers by query terms
                    filtered_papers = []
                    query_terms = query.lower().split()

                    for paper_data in papers_data:
                        # Check if any query term appears in title or abstract
                        title = paper_data.get('title', '').lower()
                        abstract = paper_data.get('abstract', '').lower()
                        category = paper_data.get('category', '').lower()

                        # Check relevance
                        is_relevant = any(term in title or term in abstract
                                        for term in query_terms)

                        # Also check if it's in a relevant category
                        is_relevant_category = any(cat in category
                                                  for cat in RELEVANT_CATEGORIES)

                        if is_relevant or (is_relevant_category and len(query_terms) <= 2):
                            std_paper = self._standardize_paper(paper_data, server)
                            if validate_paper_data(std_paper):
                                filtered_papers.append(std_paper)

                    logger.info(f"Found {len(filtered_papers)} relevant papers on {server}")
                    log_api_request(self.api_name, query, 200)
                    return filtered_papers

            logger.error(f"API error for {server}: {response.status_code}")
            return []

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out for {server}")
            return []

        except Exception as e:
            logger.error(f"Error fetching from {server}: {e}")
            return []

    def _standardize_paper(self, paper_data: Dict, server: str) -> Dict:
        """
        Convert bioRxiv/medRxiv format to standardized format.

        Args:
            paper_data: Paper data from API
            server: Source server name

        Returns:
            Standardized paper dictionary
        """
        # Extract authors
        authors = []
        author_string = paper_data.get('authors', '')
        if author_string:
            # Authors are usually in "Last, First; Last, First" format
            author_parts = author_string.split(';')
            for author in author_parts[:10]:  # Limit to 10 authors
                author = author.strip()
                if author:
                    authors.append(author)

        # Extract date information
        date_str = paper_data.get('date', '')
        year = None
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                year = date_obj.year
            except:
                pass

        # Build standardized paper
        std_paper = {
            'title': paper_data.get('title', 'Unknown Title'),
            'authors': authors,
            'year': year,
            'doi': paper_data.get('doi', ''),
            'abstract': paper_data.get('abstract', ''),
            'citation_count': 0,  # Preprints don't have citations yet
            'journal': f'{server} preprint',
            'is_open_access': True,  # All preprints are open access
            'url': f"https://www.{server}.org/content/{paper_data.get('doi', '')}v{paper_data.get('version', 1)}",
            'source': server,
            'category': paper_data.get('category', ''),
            'version': paper_data.get('version', 1),
            'published_date': paper_data.get('date', ''),
            'server': server
        }

        return std_paper

    def _sort_biorxiv_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Sort bioRxiv/medRxiv papers by relevance and recency.

        Args:
            papers: List of paper dictionaries

        Returns:
            Sorted list of papers
        """
        for paper in papers:
            # Calculate pseudo-impact score based on recency and category
            score = 1.0

            # Boost for very recent papers
            year = paper.get('year')
            current_year = datetime.now().year
            if year:
                if year == current_year:
                    score *= 2.0  # Current year
                elif year == current_year - 1:
                    score *= 1.5  # Last year

            # Boost for relevant categories
            category = paper.get('category', '').lower()
            if 'neuroscience' in category:
                score *= 2.0
            elif 'neurology' in category:
                score *= 1.8
            elif any(cat in category for cat in ['biophysics', 'systems biology']):
                score *= 1.5

            # Boost medRxiv papers for clinical relevance
            if paper.get('server') == 'medrxiv':
                score *= 1.2

            paper['impact_score'] = score

        # Sort by impact score
        return sorted(papers, key=lambda p: p.get('impact_score', 0), reverse=True)

    def search_neuroscience(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search specifically for neuroscience papers.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        # Add neuroscience terms to enhance search
        enhanced_query = f"{query} neuroscience brain neural"
        return self.search(enhanced_query, server="biorxiv", limit=limit)

    def search_clinical(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search specifically for clinical/medical papers.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        # Search primarily medRxiv for clinical papers
        return self.search(query, server="medrxiv", limit=limit)


def test_biorxiv():
    """
    Test bioRxiv/medRxiv search functionality.
    """
    print("Testing bioRxiv/medRxiv Search")
    print("=" * 60)

    # Initialize searcher
    searcher = BiorxivSearch()

    # Test queries relevant to user's research
    test_queries = [
        ("epilepsy seizure", "both"),
        ("brain connectivity", "biorxiv"),
        ("COVID-19 neurological", "medrxiv"),
        ("EEG analysis", "biorxiv"),
        ("neural dynamics", "biorxiv")
    ]

    for query, server in test_queries:
        print(f"\nQuery: {query} (Server: {server})")
        print("-" * 40)

        # Search without cache to test actual API
        papers = searcher.search(query, server=server, limit=3, use_cache=False)

        if papers:
            for i, paper in enumerate(papers, 1):
                print(f"\n{i}. {paper['title'][:70]}...")
                if paper['authors']:
                    print(f"   Authors: {'; '.join(paper['authors'][:2])}")
                    if len(paper['authors']) > 2:
                        print(f"            et al.")
                print(f"   Year: {paper['year']}")
                print(f"   Category: {paper['category']}")
                print(f"   Server: {paper['server']}")
                print(f"   Score: {paper.get('impact_score', 0):.1f}")
                if paper.get('doi'):
                    print(f"   DOI: {paper['doi']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test neuroscience-specific search
    print("\n" + "=" * 60)
    print("Testing neuroscience-specific search...")
    papers = searcher.search_neuroscience("oscillations", limit=3)
    print(f"Neuroscience papers about oscillations: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    # Test clinical search
    print("\nTesting clinical search...")
    papers = searcher.search_clinical("epilepsy treatment", limit=3)
    print(f"Clinical papers about epilepsy treatment: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    print("\n" + "=" * 60)
    print("bioRxiv/medRxiv testing complete!")


if __name__ == "__main__":
    # Handle command line usage
    if len(sys.argv) > 1:
        # Parse arguments
        query = ' '.join(sys.argv[1:])
        server = "both"  # Default to both servers

        # Check if server specified
        if "--biorxiv" in sys.argv:
            server = "biorxiv"
            query = query.replace("--biorxiv", "").strip()
        elif "--medrxiv" in sys.argv:
            server = "medrxiv"
            query = query.replace("--medrxiv", "").strip()

        searcher = BiorxivSearch()
        papers = searcher.search(query, server=server, limit=10)

        print(f"Query: {query}")
        print(f"Server: {server}")
        print(f"Found {len(papers)} papers\n")

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            if paper['authors']:
                print(f"   Authors: {'; '.join(paper['authors'][:3])}")
                if len(paper['authors']) > 3:
                    print(f"            et al.")
            print(f"   Year: {paper['year']}")
            print(f"   Category: {paper['category']}")
            print(f"   Server: {paper['server']}")
            print(f"   URL: {paper['url']}")
            print()
    else:
        # Run tests
        test_biorxiv()