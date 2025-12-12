#!/usr/bin/env python3
"""
nih_reporter_search.py - Search for NIH grants and funded projects
Provides access to NIH RePORTER database for grant funding information.

Uses NIH RePORTER API v2 for project and publication search.
API Documentation: https://api.reporter.nih.gov/
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

# NIH RePORTER API configuration
BASE_URL = "https://api.reporter.nih.gov/v2"
PROJECTS_URL = f"{BASE_URL}/projects/search"
PUBLICATIONS_URL = f"{BASE_URL}/publications/search"

# API parameters
DEFAULT_LIMIT = 10
MAX_LIMIT = 500
MAX_RESULTS = 10000  # API limitation

# Major NIH institutes and centers
MAJOR_INSTITUTES = {
    'NINDS': 'National Institute of Neurological Disorders and Stroke',
    'NIMH': 'National Institute of Mental Health',
    'NIDA': 'National Institute on Drug Abuse',
    'NCI': 'National Cancer Institute',
    'NHLBI': 'National Heart, Lung, and Blood Institute',
    'NIAID': 'National Institute of Allergy and Infectious Diseases',
    'NIDDK': 'National Institute of Diabetes and Digestive and Kidney Diseases',
    'NEI': 'National Eye Institute',
    'NICHD': 'National Institute of Child Health and Human Development',
    'NIGMS': 'National Institute of General Medical Sciences'
}


class NIHReporterSearch:
    """
    Search for NIH grants and funded projects using NIH RePORTER API v2.
    """

    def __init__(self):
        """
        Initialize NIH RePORTER search client.
        No authentication required for public API.
        """
        self.api_name = "nih_reporter"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Science-Grounded-Skill/1.0 (Educational/Research Tool)',
            'Content-Type': 'application/json'
        })

    def search_projects(self, query: str, limit: int = DEFAULT_LIMIT,
                       use_cache: bool = True, recent_only: bool = False,
                       include_active: bool = False) -> List[Dict]:
        """
        Search for NIH-funded projects/grants.

        Args:
            query: Search query (keywords, PI name, institution, etc.)
            limit: Maximum number of results (max 500 per request)
            use_cache: Whether to use cached results
            recent_only: Only return projects from last 5 years
            include_active: Only include currently active projects

        Returns:
            List of project/grant dictionaries with standardized format
        """
        # Sanitize query
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.error("Query failed sanitization")
            return []

        # Determine fiscal years to search
        fiscal_years = None
        if recent_only:
            current_year = datetime.now().year
            fiscal_years = list(range(current_year - 4, current_year + 1))

        # Check cache first
        cache_key = f"{clean_query}_fy{fiscal_years}_active{include_active}" if fiscal_years else f"{clean_query}_active{include_active}"
        if use_cache:
            cached = get_cached_results(cache_key, self.api_name)
            if cached:
                logger.info(f"Returning {len(cached)} cached results")
                return cached[:limit]

        # Perform search
        projects = self._search_projects(clean_query, min(limit * 2, MAX_LIMIT),
                                        fiscal_years, include_active)

        # Cache results if successful
        if projects:
            cache_results(cache_key, projects, self.api_name)

        # Sort by funding amount and recency
        sorted_projects = self._sort_projects(projects)
        return sorted_projects[:limit]

    @timeout_handler
    def _search_projects(self, query: str, limit: int,
                        fiscal_years: Optional[List[int]] = None,
                        include_active: bool = False) -> List[Dict]:
        """
        Internal method to search projects via NIH RePORTER API.

        Args:
            query: Sanitized search query
            limit: Number of results to retrieve
            fiscal_years: List of fiscal years to search
            include_active: Only include active projects

        Returns:
            List of project dictionaries
        """
        # Rate limit the request
        rate_limit_request(self.api_name)

        try:
            # Build search criteria
            criteria = {
                'advanced_text_search': {
                    'search_field': 'terms',
                    'search_text': query
                }
            }

            # Add fiscal year filter if specified
            if fiscal_years:
                criteria['fiscal_years'] = fiscal_years

            # Add active projects filter if specified
            if include_active:
                criteria['include_active_projects'] = True

            # Build request payload
            payload = {
                'criteria': criteria,
                'offset': 0,
                'limit': min(limit, MAX_LIMIT),
                'sort_field': 'project_start_date',
                'sort_order': 'desc',
                'include_fields': [
                    'ProjectNum',
                    'ProjectTitle',
                    'ContactPiName',
                    'OrgName',
                    'OrgCity',
                    'OrgState',
                    'OrgCountry',
                    'ProjectStartDate',
                    'ProjectEndDate',
                    'AbstractText',
                    'AwardAmount',
                    'FiscalYear',
                    'AgencyIcFundings',
                    'ProjectNumSplit',
                    'FullStudySection',
                    'PhrText'
                ]
            }

            logger.info(f"Searching NIH RePORTER for: {query[:50]}...")
            response = self.session.post(PROJECTS_URL, json=payload, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                total = data.get('meta', {}).get('total', 0)

                logger.info(f"Found {total} total results, returning {len(results)} projects")
                log_api_request(self.api_name, query, 200)

                # Parse projects into standardized format
                projects = [self._parse_project(proj) for proj in results]
                return [p for p in projects if p is not None]

            else:
                logger.error(f"NIH RePORTER error: {response.status_code}")
                log_api_request(self.api_name, query, response.status_code)
                return []

        except Exception as e:
            logger.error(f"Error searching NIH RePORTER: {e}")
            log_api_request(self.api_name, query, error=str(e))
            return []

    def _parse_project(self, project_data: Dict) -> Optional[Dict]:
        """
        Parse a single project from NIH RePORTER API response.

        Args:
            project_data: Raw project data from API

        Returns:
            Standardized project dictionary
        """
        try:
            # Extract basic info
            project_num = project_data.get('project_num', 'Unknown')
            title = project_data.get('project_title', 'Untitled Project')
            pi_name = project_data.get('contact_pi_name', 'Unknown PI')
            org_name = project_data.get('org_name', 'Unknown Institution')
            org_city = project_data.get('org_city', '')
            org_state = project_data.get('org_state', '')
            org_country = project_data.get('org_country', 'USA')

            # Extract dates
            start_date = project_data.get('project_start_date', '')
            end_date = project_data.get('project_end_date', '')

            # Parse start year
            year = None
            if start_date:
                try:
                    year = int(start_date[:4])
                except (ValueError, TypeError):
                    year = None

            # Extract funding info
            award_amount = project_data.get('award_amount', 0)
            fiscal_year = project_data.get('fiscal_year', year)

            # Extract funding agencies
            agencies = []
            ic_fundings = project_data.get('agency_ic_fundings', [])
            for funding in ic_fundings:
                ic_code = funding.get('code', '')
                if ic_code:
                    agencies.append(ic_code)

            # Extract abstract/description
            abstract = project_data.get('abstract_text', '')
            if not abstract:
                abstract = project_data.get('phr_text', '')  # Public health relevance

            # Extract study section
            study_section = project_data.get('full_study_section', {})
            study_section_name = study_section.get('name', '') if study_section else ''

            # Build location string
            location = org_city
            if org_state:
                location = f"{location}, {org_state}" if location else org_state
            if org_country and org_country != 'USA':
                location = f"{location}, {org_country}"

            # Determine project type from project number
            project_split = project_data.get('project_num_split', {})
            activity_code = project_split.get('activity_code', '')
            project_type = self._classify_project_type(activity_code)

            # Build standardized project dictionary
            std_project = {
                'project_number': project_num,
                'title': title,
                'pi_name': pi_name,
                'institution': org_name,
                'location': location,
                'year': year,
                'start_date': start_date,
                'end_date': end_date,
                'fiscal_year': fiscal_year,
                'award_amount': award_amount,
                'agencies': agencies,
                'abstract': abstract,
                'study_section': study_section_name,
                'project_type': project_type,
                'activity_code': activity_code,
                'source': 'nih_reporter',
                'url': f"https://reporter.nih.gov/project-details/{project_num.replace(' ', '')}"
            }

            return std_project

        except Exception as e:
            logger.error(f"Error parsing project: {e}")
            return None

    def _classify_project_type(self, activity_code: str) -> str:
        """
        Classify project type based on NIH activity code.

        Args:
            activity_code: NIH activity code (e.g., R01, R21, P01)

        Returns:
            Human-readable project type
        """
        if not activity_code:
            return "Unknown"

        code_upper = activity_code.upper()

        # Research grants
        if code_upper.startswith('R'):
            if code_upper in ['R01', 'R37']:
                return "Research Project Grant"
            elif code_upper == 'R21':
                return "Exploratory/Developmental Research Grant"
            elif code_upper == 'R03':
                return "Small Research Grant"
            elif code_upper == 'R15':
                return "Academic Research Enhancement Award"
            else:
                return "Research Grant"

        # Program projects and centers
        elif code_upper.startswith('P'):
            if code_upper == 'P01':
                return "Research Program Project"
            elif code_upper in ['P50', 'P30']:
                return "Center Grant"
            else:
                return "Program Project/Center"

        # Career development
        elif code_upper.startswith('K'):
            return "Career Development Award"

        # Training grants
        elif code_upper.startswith('T'):
            return "Training Grant"

        # Fellowships
        elif code_upper.startswith('F'):
            return "Fellowship"

        # Cooperative agreements
        elif code_upper.startswith('U'):
            return "Cooperative Agreement"

        else:
            return f"Other ({activity_code})"

    def _sort_projects(self, projects: List[Dict]) -> List[Dict]:
        """
        Sort projects by funding amount, recency, and impact.

        Args:
            projects: List of project dictionaries

        Returns:
            Sorted list of projects
        """
        for project in projects:
            score = 0.0

            # Base score on funding amount (normalized)
            award_amount = project.get('award_amount', 0)
            if award_amount > 0:
                # Normalize to reasonable scale (e.g., $1M = 1.0 point)
                score += award_amount / 1_000_000

            # Boost for recent projects
            year = project.get('year')
            current_year = datetime.now().year
            if year:
                if year >= current_year - 2:
                    score *= 1.5  # Very recent
                elif year >= current_year - 5:
                    score *= 1.2  # Recent

            # Boost for major research grants
            activity_code = project.get('activity_code', '')
            if activity_code in ['R01', 'R37', 'P01', 'P50']:
                score *= 1.3

            # Boost for major neuroscience institutes
            agencies = project.get('agencies', [])
            if 'NINDS' in agencies:
                score *= 1.4
            elif any(inst in agencies for inst in ['NIMH', 'NCI', 'NHLBI']):
                score *= 1.2

            project['impact_score'] = score

        # Sort by impact score
        return sorted(projects, key=lambda p: p.get('impact_score', 0), reverse=True)

    def search_by_pi(self, pi_name: str, limit: int = DEFAULT_LIMIT) -> List[Dict]:
        """
        Search for projects by principal investigator name.

        Args:
            pi_name: Name of principal investigator
            limit: Maximum number of results

        Returns:
            List of project dictionaries
        """
        # Use advanced search for PI name
        return self.search_projects(pi_name, limit=limit)

    def search_by_institution(self, institution: str, limit: int = DEFAULT_LIMIT,
                             recent_only: bool = True) -> List[Dict]:
        """
        Search for projects by institution/organization.

        Args:
            institution: Institution or organization name
            limit: Maximum number of results
            recent_only: Only return recent projects

        Returns:
            List of project dictionaries
        """
        return self.search_projects(institution, limit=limit, recent_only=recent_only)

    def search_by_topic(self, topic: str, limit: int = DEFAULT_LIMIT,
                       min_funding: Optional[int] = None) -> List[Dict]:
        """
        Search for projects by research topic with optional funding filter.

        Args:
            topic: Research topic keywords
            limit: Maximum number of results
            min_funding: Minimum funding amount (in dollars)

        Returns:
            List of project dictionaries filtered by minimum funding
        """
        projects = self.search_projects(topic, limit=limit * 2, recent_only=True)

        # Filter by minimum funding if specified
        if min_funding:
            projects = [p for p in projects if p.get('award_amount', 0) >= min_funding]

        return projects[:limit]


def test_nih_reporter():
    """
    Test NIH RePORTER search functionality.
    """
    print("Testing NIH RePORTER Search")
    print("=" * 60)

    # Initialize searcher
    searcher = NIHReporterSearch()

    # Test queries relevant to neuroscience research
    test_queries = [
        "epilepsy seizure prediction",
        "deep brain stimulation",
        "neural dynamics",
        "brain computer interface"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)

        # Search without cache to test actual API
        projects = searcher.search_projects(query, limit=3, use_cache=False, recent_only=True)

        if projects:
            for i, proj in enumerate(projects, 1):
                print(f"\n{i}. {proj['title'][:70]}...")
                print(f"   PI: {proj['pi_name']}")
                print(f"   Institution: {proj['institution']}")
                print(f"   Location: {proj['location']}")
                print(f"   Type: {proj['project_type']}")
                print(f"   Funding: ${proj['award_amount']:,}")
                print(f"   Fiscal Year: {proj['fiscal_year']}")
                if proj['agencies']:
                    print(f"   Agencies: {', '.join(proj['agencies'])}")
                print(f"   Score: {proj.get('impact_score', 0):.2f}")
                print(f"   Project #: {proj['project_number']}")
        else:
            print("   No results found")

        # Wait between queries to respect rate limit
        time.sleep(2)

    # Test PI search
    print("\n" + "=" * 60)
    print("Testing PI name search...")
    projects = searcher.search_by_pi("Steven Brunton", limit=3)
    print(f"Projects for PI 'Steven Brunton': {len(projects)} found")
    for proj in projects[:2]:
        print(f"  - {proj['title'][:60]}... (${proj['award_amount']:,})")

    # Test topic with funding filter
    print("\nTesting topic search with funding filter...")
    projects = searcher.search_by_topic("machine learning", limit=5, min_funding=500000)
    print(f"ML projects with >$500K funding: {len(projects)} found")
    for proj in projects[:3]:
        print(f"  - {proj['title'][:60]}... (${proj['award_amount']:,})")

    print("\n" + "=" * 60)
    print("NIH RePORTER testing complete!")


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

        searcher = NIHReporterSearch()
        projects = searcher.search_projects(query, limit=10, recent_only=recent_only)

        print(f"Query: {query}")
        if recent_only:
            print("Filter: Recent projects only (last 5 years)")
        print(f"Found {len(projects)} projects\n")

        for i, proj in enumerate(projects, 1):
            print(f"{i}. {proj['title']}")
            print(f"   PI: {proj['pi_name']}")
            print(f"   Institution: {proj['institution']}, {proj['location']}")
            print(f"   Type: {proj['project_type']} ({proj['activity_code']})")
            print(f"   Funding: ${proj['award_amount']:,} (FY {proj['fiscal_year']})")
            print(f"   Period: {proj['start_date']} to {proj['end_date']}")
            if proj['agencies']:
                print(f"   Funding from: {', '.join(proj['agencies'])}")
            print(f"   URL: {proj['url']}")
            print()
    else:
        # Run tests
        test_nih_reporter()
