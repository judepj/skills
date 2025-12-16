#!/usr/bin/env python3
"""
nsf_awards_search.py - Search for NSF awards and grants
Provides access to NSF Awards database for grant funding information.

Uses NSF Awards API v1 for award search.
API Documentation: https://resources.research.gov/common/webapi/awardapisearch-v1.htm
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from paper_utils import (
    sanitize_query,
    rate_limit_request,
    get_cached_results,
    cache_results,
    log_api_request,
    timeout_handler,
    REQUEST_TIMEOUT
)

# Configure logging
logger = logging.getLogger(__name__)

# NSF Awards API configuration
BASE_URL = "http://api.nsf.gov/services/v1"
AWARDS_URL = f"{BASE_URL}/awards.json"

# API parameters
DEFAULT_LIMIT = 10
MAX_LIMIT = 25  # NSF API limit per request
MAX_RESULTS = 3000  # NSF API total result limit

# Major NSF directorates and divisions
NSF_DIRECTORATES = {
    'BIO': 'Biological Sciences',
    'CISE': 'Computer and Information Science and Engineering',
    'EHR': 'Education and Human Resources',
    'ENG': 'Engineering',
    'GEO': 'Geosciences',
    'MPS': 'Mathematical and Physical Sciences',
    'SBE': 'Social, Behavioral and Economic Sciences',
    'TIP': 'Technology, Innovation and Partnerships'
}

# Key NSF programs for computational/neuroscience research
KEY_PROGRAMS = [
    'Brain Research through Advancing Innovative Neurotechnologies (BRAIN)',
    'Cognitive Neuroscience',
    'Collaborative Research in Computational Neuroscience',
    'Computational Neuroscience',
    'Neural Systems',
    'Perception, Action & Cognition',
    'Physics of Living Systems',
    'Machine Learning',
    'Robust Intelligence',
    'Cyberinfrastructure'
]


class NSFAwardsSearch:
    """
    Search for NSF awards and grants using NSF Awards API v1.
    """

    def __init__(self):
        """
        Initialize NSF Awards search client.
        No authentication required for public API.
        """
        self.api_name = "nsf_awards"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science-Grounded-Skill/1.0 (Educational/Research Tool)'
        })

    def search_awards(self, query: str, limit: int = DEFAULT_LIMIT,
                     use_cache: bool = True, recent_only: bool = False,
                     min_funding: Optional[int] = None) -> List[Dict]:
        """
        Search for NSF awards/grants.

        Args:
            query: Search query (keywords, PI name, institution, etc.)
            limit: Maximum number of results
            use_cache: Whether to use cached results
            recent_only: Only return awards from last 5 years
            min_funding: Minimum funding amount (in dollars)

        Returns:
            List of award dictionaries with standardized format
        """
        # Sanitize query
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.error("Query failed sanitization")
            return []

        # Determine date range if recent_only
        start_date = None
        if recent_only:
            current_year = datetime.now().year
            start_date = f"01/01/{current_year - 4}"

        # Check cache first
        cache_key = f"{clean_query}_recent{recent_only}_minfund{min_funding}"
        if use_cache:
            cached = get_cached_results(cache_key, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        awards = self._search_awards(clean_query, min(limit * 2, 100), start_date)

        # Filter by minimum funding if specified
        if min_funding and awards:
            awards = [a for a in awards if a.get('award_amount', 0) >= min_funding]

        # Cache results if successful
        if awards:
            cache_results(cache_key, awards, self.api_name)

        # Sort by funding amount and recency
        sorted_awards = self._sort_awards(awards)
        return sorted_awards[:limit]

    @timeout_handler
    def _search_awards(self, query: str, limit: int,
                      start_date: Optional[str] = None) -> List[Dict]:
        """
        Internal method to search awards via NSF Awards API.

        Args:
            query: Sanitized search query
            limit: Number of results to retrieve
            start_date: Start date filter (MM/DD/YYYY format)

        Returns:
            List of award dictionaries
        """
        # NSF API uses pagination with max 25 results per request
        awards = []
        offset = 1  # NSF uses 1-based indexing

        while len(awards) < limit and offset <= MAX_RESULTS:
            # Rate limit the request
            rate_limit_request(self.api_name)

            try:
                # Build query parameters
                params = {
                    'keyword': query,
                    'rpp': min(MAX_LIMIT, limit - len(awards)),
                    'offset': offset,
                    'printFields': 'id,agency,title,pdPIName,piEmail,piFirstName,piLastName,'
                                  'coPDPI,awardeeName,awardeeCity,awardeeStateCode,'
                                  'awardeeCountryCode,date,startDate,expDate,'
                                  'estimatedTotalAmt,fundsObligatedAmt,abstractText,'
                                  'fundProgramName,publicationResearch'
                }

                # Add date filter if specified
                if start_date:
                    params['startDateStart'] = start_date

                logger.info(f"Searching NSF Awards for: {query[:50]}... (offset={offset})")
                response = self.session.get(AWARDS_URL, params=params, timeout=REQUEST_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    response_data = data.get('response', {})
                    award_list = response_data.get('award', [])

                    # NSF API returns single award as dict, not list
                    if isinstance(award_list, dict):
                        award_list = [award_list]

                    if not award_list:
                        logger.info("No more awards found")
                        break

                    # Parse awards into standardized format
                    for award_data in award_list:
                        award = self._parse_award(award_data)
                        if award:
                            awards.append(award)

                    logger.info(f"Retrieved {len(award_list)} awards (total: {len(awards)})")

                    # Check if we got fewer results than requested (end of results)
                    if len(award_list) < MAX_LIMIT:
                        break

                    offset += MAX_LIMIT

                else:
                    logger.error(f"NSF Awards API error: {response.status_code}")
                    log_api_request(self.api_name, query, response.status_code)
                    break

            except Exception as e:
                logger.error(f"Error searching NSF Awards: {e}")
                log_api_request(self.api_name, query, error=str(e))
                break

        if awards:
            log_api_request(self.api_name, query, 200)

        return awards

    def _parse_award(self, award_data: Dict) -> Optional[Dict]:
        """
        Parse a single award from NSF Awards API response.

        Args:
            award_data: Raw award data from API

        Returns:
            Standardized award dictionary
        """
        try:
            # Extract basic info
            award_id = award_data.get('id', 'Unknown')
            title = award_data.get('title', 'Untitled Award')

            # Extract PI information
            pi_name = award_data.get('pdPIName', 'Unknown PI')
            pi_first = award_data.get('piFirstName', '')
            pi_last = award_data.get('piLastName', '')
            pi_email = award_data.get('piEmail', '')

            # Format PI name
            if pi_first and pi_last:
                pi_name = f"{pi_first} {pi_last}"

            # Extract co-PIs
            co_pis = []
            co_pi_data = award_data.get('coPDPI', [])
            if isinstance(co_pi_data, str):
                co_pis = [co_pi_data]
            elif isinstance(co_pi_data, list):
                co_pis = co_pi_data

            # Extract institution info
            institution = award_data.get('awardeeName', 'Unknown Institution')
            city = award_data.get('awardeeCity', '')
            state = award_data.get('awardeeStateCode', '')
            country = award_data.get('awardeeCountryCode', 'USA')

            # Build location string
            location = city
            if state:
                location = f"{location}, {state}" if location else state
            if country and country != 'USA':
                location = f"{location}, {country}"

            # Extract dates
            award_date = award_data.get('date', '')
            start_date = award_data.get('startDate', '')
            exp_date = award_data.get('expDate', '')

            # Parse year
            year = None
            if start_date:
                try:
                    # Date format is MM/DD/YYYY
                    year = int(start_date.split('/')[-1])
                except (ValueError, IndexError):
                    year = None

            # Extract funding info
            estimated_total = award_data.get('estimatedTotalAmt', '0')
            funds_obligated = award_data.get('fundsObligatedAmt', '0')

            # Convert funding to integer
            try:
                award_amount = int(float(estimated_total))
            except (ValueError, TypeError):
                try:
                    award_amount = int(float(funds_obligated))
                except (ValueError, TypeError):
                    award_amount = 0

            # Extract program info
            program_name = award_data.get('fundProgramName', '')

            # Extract abstract
            abstract = award_data.get('abstractText', '')

            # Build standardized award dictionary
            std_award = {
                'award_number': award_id,
                'title': title,
                'pi_name': pi_name,
                'pi_email': pi_email,
                'co_pis': co_pis,
                'institution': institution,
                'location': location,
                'year': year,
                'award_date': award_date,
                'start_date': start_date,
                'expiration_date': exp_date,
                'award_amount': award_amount,
                'program': program_name,
                'abstract': abstract,
                'source': 'nsf',
                'url': f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award_id}"
            }

            return std_award

        except Exception as e:
            logger.error(f"Error parsing award: {e}")
            return None

    def _sort_awards(self, awards: List[Dict]) -> List[Dict]:
        """
        Sort awards by funding amount, recency, and relevance.

        Args:
            awards: List of award dictionaries

        Returns:
            Sorted list of awards
        """
        for award in awards:
            score = 0.0

            # Base score on funding amount (normalized)
            award_amount = award.get('award_amount', 0)
            if award_amount > 0:
                # Normalize to reasonable scale (e.g., $1M = 1.0 point)
                score += award_amount / 1_000_000

            # Boost for recent awards
            year = award.get('year')
            current_year = datetime.now().year
            if year:
                if year >= current_year - 2:
                    score *= 1.5  # Very recent
                elif year >= current_year - 5:
                    score *= 1.2  # Recent

            # Boost for key programs
            program = award.get('program', '')
            for key_program in KEY_PROGRAMS:
                if key_program.lower() in program.lower():
                    score *= 1.3
                    break

            award['impact_score'] = score

        # Sort by impact score
        return sorted(awards, key=lambda a: a.get('impact_score', 0), reverse=True)

    def search_by_pi(self, pi_name: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search for awards by principal investigator name.

        Args:
            pi_name: Name of principal investigator
            limit: Maximum number of results

        Returns:
            List of award dictionaries
        """
        return self.search_awards(pi_name, limit=limit)

    def search_by_institution(self, institution: str, limit: int = DEFAULT_LIMIT,
                             recent_only: bool = True) -> List[Dict]:
        """
        Search for awards by institution/organization.

        Args:
            institution: Institution or organization name
            limit: Maximum number of results
            recent_only: Only return recent awards

        Returns:
            List of award dictionaries
        """
        return self.search_awards(institution, limit=limit, recent_only=recent_only)

    def search_by_topic(self, topic: str, limit: int = DEFAULT_LIMIT,
                       min_funding: Optional[int] = None) -> List[Dict]:
        """
        Search for awards by research topic with optional funding filter.

        Args:
            topic: Research topic keywords
            limit: Maximum number of results
            min_funding: Minimum funding amount (in dollars)

        Returns:
            List of award dictionaries filtered by minimum funding
        """
        return self.search_awards(topic, limit=limit, recent_only=True,
                                 min_funding=min_funding)


def test_nsf_awards():
    """
    Test NSF Awards search functionality.
    """
    print("Testing NSF Awards Search")
    print("=" * 60)

    # Initialize searcher
    searcher = NSFAwardsSearch()

    # Test queries relevant to computational neuroscience research
    test_queries = [
        "neural networks machine learning",
        "brain dynamics",
        "computational neuroscience",
        "dynamical systems"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Search without cache to test actual API
        awards = searcher.search_awards(query, limit=3, use_cache=False, recent_only=True)

        if awards:
            for i, award in enumerate(awards, 1):
                print(f"\n{i}. {award['title'][:70]}...")
                print(f"   PI: {award['pi_name']}")
                if award['co_pis']:
                    print(f"   Co-PIs: {', '.join(award['co_pis'][:2])}")
                print(f"   Institution: {award['institution']}")
                print(f"   Location: {award['location']}")
                print(f"   Program: {award['program']}")
                print(f"   Funding: ${award['award_amount']:,}")
                print(f"   Period: {award['start_date']} to {award['expiration_date']}")
                print(f"   Score: {award.get('impact_score', 0):.2f}")
                print(f"   Award #: {award['award_number']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test PI search
    print("\n" + "=" * 60)
    print("Testing PI name search...")
    awards = searcher.search_by_pi("Steven Brunton", limit=3)
    print(f"Awards for PI 'Steven Brunton': {len(awards)} found")
    for award in awards[:2]:
        print(f"  - {award['title'][:60]}... (${award['award_amount']:,})")

    # Test topic with funding filter
    print("\nTesting topic search with funding filter...")
    awards = searcher.search_by_topic("data science", limit=5, min_funding=500000)
    print(f"Data science awards with >$500K funding: {len(awards)} found")
    for award in awards[:3]:
        print(f"  - {award['title'][:60]}... (${award['award_amount']:,})")

    print("\n" + "=" * 60)
    print("NSF Awards testing complete!")


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

        searcher = NSFAwardsSearch()
        awards = searcher.search_awards(query, limit=10, recent_only=recent_only)

        print(f"Query: {query}")
        if recent_only:
            print("Filter: Recent awards only (last 5 years)")
        print(f"Found {len(awards)} awards\n")

        for i, award in enumerate(awards, 1):
            print(f"{i}. {award['title']}")
            print(f"   PI: {award['pi_name']}")
            if award['co_pis']:
                print(f"   Co-PIs: {', '.join(award['co_pis'][:3])}")
            print(f"   Institution: {award['institution']}, {award['location']}")
            print(f"   Program: {award['program']}")
            print(f"   Funding: ${award['award_amount']:,}")
            print(f"   Period: {award['start_date']} to {award['expiration_date']}")
            print(f"   URL: {award['url']}")
            print()
    else:
        # Run tests
        test_nsf_awards()
