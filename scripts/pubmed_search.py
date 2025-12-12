#!/usr/bin/env python3
"""
pubmed_search.py - Search for papers in PubMed/PMC database
Provides access to clinical and biomedical literature.

Uses NCBI's E-utilities API for PubMed access.
API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""

import json
import logging
import sys
import time
import xml.etree.ElementTree as ET
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

# PubMed E-utilities API configuration
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_URL = f"{BASE_URL}/esearch.fcgi"
FETCH_URL = f"{BASE_URL}/efetch.fcgi"
SUMMARY_URL = f"{BASE_URL}/esummary.fcgi"

# API parameters
DB_NAME = "pubmed"
RETMAX = 100  # Maximum results per request
DEFAULT_LIMIT = 10

# Important journals for epilepsy and neuroscience
PRIORITY_JOURNALS = [
    'Epilepsia',
    'Epilepsy Research',
    'Epilepsy & Behavior',
    'Brain',
    'Neurology',
    'Annals of Neurology',
    'Journal of Neuroscience',
    'Nature Neuroscience',
    'Neuron',
    'Clinical Neurophysiology',
    'Journal of Neural Engineering',
    'NeuroImage'
]


class PubMedSearch:
    """
    Search for papers in PubMed database.
    """

    def __init__(self, email: str = "science-grounded@example.com"):
        """
        Initialize PubMed search client.

        Args:
            email: Email address for NCBI (required for API usage)
        """
        self.api_name = "pubmed"
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science-Grounded-Skill/1.0 (Educational/Research Tool)'
        })

    def search(self, query: str, limit: int = DEFAULT_LIMIT,
              use_cache: bool = True, recent_only: bool = False) -> List[Dict]:
        """
        Search for papers in PubMed.

        Args:
            query: Search query
            limit: Maximum number of results
            use_cache: Whether to use cached results
            recent_only: Only return papers from last 5 years

        Returns:
            List of paper dictionaries with standardized format
        """
        # Sanitize query
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.error("Query failed sanitization")
            return []

        # Add date filter if requested
        if recent_only:
            clean_query = f"{clean_query} AND (\"last 5 years\"[PDat])"

        # Check cache first
        cache_key = f"{clean_query}_recent" if recent_only else clean_query
        if use_cache:
            cached = get_cached_results(cache_key, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        papers = self._search_papers(clean_query, min(limit * 2, RETMAX))

        # Cache results if successful
        if papers:
            cache_results(cache_key, papers, self.api_name)

        # Sort by relevance and journal priority
        sorted_papers = self._sort_pubmed_papers(papers)
        return sorted_papers[:limit]

    @timeout_handler
    def _search_papers(self, query: str, limit: int) -> List[Dict]:
        """
        Internal method to search papers via PubMed API.

        Args:
            query: Sanitized search query (may include date filters)
            limit: Number of results to retrieve

        Returns:
            List of paper dictionaries
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        try:
            # Step 1: Search for PMIDs
            pmids = self._search_pmids(query, limit)

            if not pmids:
                logger.info("No PMIDs found for query")
                return []

            # Step 2: Fetch paper details for PMIDs
            papers = self._fetch_paper_details(pmids)

            logger.info(f"Found {len(papers)} papers in PubMed")
            log_api_request(self.api_name, query, 200)

            return papers

        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            log_api_request(self.api_name, query, error=str(e))
            return []

    def _search_pmids(self, query: str, limit: int) -> List[str]:
        """
        Search for PubMed IDs matching the query.

        Args:
            query: Search query
            limit: Maximum number of IDs to retrieve

        Returns:
            List of PubMed IDs
        """
        params = {
            'db': DB_NAME,
            'term': query,
            'retmax': limit,
            'retmode': 'json',
            'email': self.email,
            'sort': 'relevance'
        }

        try:
            logger.info(f"Searching PubMed for: {query[:50]}...")
            response = self.session.get(SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                esearchresult = data.get('esearchresult', {})
                pmids = esearchresult.get('idlist', [])
                count = esearchresult.get('count', '0')

                logger.info(f"Found {count} total results, fetching {len(pmids)} PMIDs")
                return pmids

            else:
                logger.error(f"PubMed search error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching PMIDs: {e}")
            return []

    def _fetch_paper_details(self, pmids: List[str]) -> List[Dict]:
        """
        Fetch detailed information for a list of PMIDs.

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of paper dictionaries
        """
        if not pmids:
            return []

        # Join PMIDs for batch fetching
        id_list = ','.join(pmids)

        params = {
            'db': DB_NAME,
            'id': id_list,
            'retmode': 'xml',
            'email': self.email
        }

        try:
            # Rate limit before fetching details
            rate_limit_request(self.api_name)

            response = self.session.get(FETCH_URL, params=params, timeout=REQUEST_TIMEOUT * 2)

            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)
                papers = []

                for article in root.findall('.//PubmedArticle'):
                    paper = self._parse_article(article)
                    if paper and validate_paper_data(paper):
                        papers.append(paper)

                return papers

            else:
                logger.error(f"PubMed fetch error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching paper details: {e}")
            return []

    def _parse_article(self, article: ET.Element) -> Optional[Dict]:
        """
        Parse a single PubMed article from XML.

        Args:
            article: XML element containing article data

        Returns:
            Standardized paper dictionary or None if parsing fails
        """
        try:
            # Get basic article info
            medline = article.find('.//MedlineCitation')
            article_data = medline.find('.//Article')

            # Extract title
            title_elem = article_data.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "Unknown Title"

            # Extract authors
            authors = []
            author_list = article_data.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.find('.//LastName')
                    first_name = author.find('.//ForeName')
                    if last_name is not None:
                        name = last_name.text
                        if first_name is not None:
                            name = f"{last_name.text}, {first_name.text}"
                        authors.append(name)

            # Extract abstract
            abstract = ""
            abstract_elem = article_data.find('.//Abstract')
            if abstract_elem is not None:
                abstract_texts = abstract_elem.findall('.//AbstractText')
                abstract_parts = []
                for text_elem in abstract_texts:
                    if text_elem.text:
                        abstract_parts.append(text_elem.text)
                abstract = ' '.join(abstract_parts)

            # Extract journal
            journal_elem = article_data.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else None

            # Extract year
            year = None
            pub_date = article_data.find('.//Journal/JournalIssue/PubDate')
            if pub_date is not None:
                year_elem = pub_date.find('.//Year')
                if year_elem is not None:
                    year = int(year_elem.text)
                else:
                    # Try MedlineDate
                    medline_date = pub_date.find('.//MedlineDate')
                    if medline_date is not None and medline_date.text:
                        # Extract year from strings like "2023 Jan-Feb"
                        year_str = medline_date.text[:4]
                        if year_str.isdigit():
                            year = int(year_str)

            # Extract PMID
            pmid_elem = medline.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None

            # Extract DOI if available
            doi = None
            article_ids = article.findall('.//PubmedData/ArticleIdList/ArticleId')
            for article_id in article_ids:
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break

            # Build standardized paper
            std_paper = {
                'title': title,
                'authors': authors,
                'year': year,
                'doi': doi,
                'abstract': abstract,
                'citation_count': 0,  # PubMed doesn't provide citation counts
                'journal': journal,
                'is_open_access': False,  # Check PMC for open access
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                'source': 'pubmed',
                'pmid': pmid
            }

            # Check if available in PMC (open access)
            pmc_elem = article.find('.//PubmedData/ArticleIdList/ArticleId[@IdType="pmc"]')
            if pmc_elem is not None:
                std_paper['is_open_access'] = True
                std_paper['pmc_id'] = pmc_elem.text

            return std_paper

        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None

    def _sort_pubmed_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Sort PubMed papers by journal priority and recency.

        Args:
            papers: List of paper dictionaries

        Returns:
            Sorted list of papers
        """
        for paper in papers:
            score = 1.0

            # Boost for priority journals
            journal = paper.get('journal', '')
            if journal:
                for priority_journal in PRIORITY_JOURNALS:
                    if priority_journal.lower() in journal.lower():
                        score *= 2.0
                        break

            # Boost for recent papers
            year = paper.get('year')
            current_year = datetime.now().year
            if year:
                if year >= current_year - 2:
                    score *= 1.5  # Very recent
                elif year >= current_year - 5:
                    score *= 1.2  # Recent

            # Boost for open access
            if paper.get('is_open_access'):
                score *= 1.1

            paper['impact_score'] = score

        # Sort by impact score
        return sorted(papers, key=lambda p: p.get('impact_score', 0), reverse=True)

    def search_clinical_trials(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search specifically for clinical trials.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        clinical_query = f"{query} AND (Clinical Trial[PT] OR Randomized Controlled Trial[PT])"
        return self.search(clinical_query, limit=limit)

    def search_reviews(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search specifically for review articles.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        review_query = f"{query} AND (Review[PT] OR Systematic Review[PT])"
        return self.search(review_query, limit=limit)

    def search_epilepsy(self, query: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search with epilepsy-specific filters.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of paper dictionaries
        """
        epilepsy_query = f"{query} AND (epilepsy[MeSH] OR seizure[MeSH] OR anticonvulsants[MeSH])"
        return self.search(epilepsy_query, limit=limit, recent_only=True)


def test_pubmed():
    """
    Test PubMed search functionality.
    """
    print("Testing PubMed Search")
    print("=" * 60)

    # Initialize searcher
    searcher = PubMedSearch()

    # Test queries relevant to user's research
    test_queries = [
        "epilepsy seizure prediction",
        "deep brain stimulation epilepsy",
        "EEG biomarkers seizure",
        "hippocampal sclerosis temporal lobe epilepsy",
        "responsive neurostimulation"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Search without cache to test actual API
        papers = searcher.search(query, limit=3, use_cache=False, recent_only=True)

        if papers:
            for i, paper in enumerate(papers, 1):
                print(f"\n{i}. {paper['title'][:70]}...")
                if paper['authors']:
                    print(f"   Authors: {', '.join(paper['authors'][:2])}")
                    if len(paper['authors']) > 2:
                        print(f"            et al.")
                print(f"   Year: {paper['year']}")
                print(f"   Journal: {paper['journal']}")
                print(f"   Open Access: {paper['is_open_access']}")
                print(f"   Score: {paper.get('impact_score', 0):.1f}")
                if paper.get('pmid'):
                    print(f"   PMID: {paper['pmid']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test clinical trials search
    print("\n" + "=" * 60)
    print("Testing clinical trials search...")
    papers = searcher.search_clinical_trials("epilepsy drug", limit=3)
    print(f"Clinical trials for epilepsy drugs: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    # Test review search
    print("\nTesting review articles search...")
    papers = searcher.search_reviews("seizure detection algorithms", limit=3)
    print(f"Review articles on seizure detection: {len(papers)} found")
    for paper in papers[:2]:
        print(f"  - {paper['title'][:60]}... ({paper['year']})")

    print("\n" + "=" * 60)
    print("PubMed testing complete!")


if __name__ == "__main__":
    # Handle command line usage
    if len(sys.argv) > 1:
        # Parse arguments
        query = ' '.join(sys.argv[1:])
        recent_only = False

        # Check if recent flag specified
        if "--recent" in sys.argv:
            recent_only = True
            query = query.replace("--recent", "").strip()

        searcher = PubMedSearch()
        papers = searcher.search(query, limit=10, recent_only=recent_only)

        print(f"Query: {query}")
        if recent_only:
            print("Filter: Recent papers only (last 5 years)")
        print(f"Found {len(papers)} papers\n")

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            if paper['authors']:
                print(f"   Authors: {', '.join(paper['authors'][:3])}")
                if len(paper['authors']) > 3:
                    print(f"            et al.")
            print(f"   Year: {paper['year']}")
            print(f"   Journal: {paper['journal']}")
            if paper.get('doi'):
                print(f"   DOI: {paper['doi']}")
            print(f"   PubMed: {paper['url']}")
            print()
    else:
        # Run tests
        test_pubmed()