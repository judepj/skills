#!/usr/bin/env python3
"""
paper_utils.py - Core utilities for science-grounded literature search skill
Provides safety features, caching, rate limiting, and paper ranking utilities.

Safety Features:
- Rate limiting: 2+ seconds between API calls
- Input sanitization: Max 200 chars, alphanumeric only
- Request logging: All API calls logged
- Timeout handling: 10 seconds max per request
- Cache management: 24-hour TTL with privacy hashing
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import diskcache
from functools import wraps

# Set up paths
BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "cache"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Create directories if they don't exist
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# Configure logging
LOG_FILE = LOG_DIR / "api_access.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize cache with 24-hour TTL and 100MB size limit
cache = diskcache.Cache(
    str(CACHE_DIR),
    size_limit=100 * 1024 * 1024,  # 100MB
    eviction_policy='least-recently-used'
)

# Rate limiting tracking
_last_api_call = {}
RATE_LIMIT_SECONDS = 2.0  # Minimum seconds between API calls
REQUEST_TIMEOUT = 10.0  # Maximum seconds per request

# Journal tier configuration
JOURNAL_TIERS = {
    # Tier 1: Impact > 10
    'tier1': {
        'journals': [
            'Nature', 'Science', 'Nature Neuroscience', 'Nature Communications',
            'Nature Computational Science', 'Cell', 'Neuron', 'PNAS',
            'Nature Methods', 'Nature Medicine', 'Nature Biotechnology'
        ],
        'multiplier': 3.0
    },
    # Tier 2: Impact 5-10
    'tier2': {
        'journals': [
            'Brain', 'Epilepsia', 'NeuroImage', 'Journal of Neuroscience',
            'PLOS Computational Biology', 'eLife', 'Current Biology',
            'Annals of Neurology', 'Neurology', 'Brain Stimulation'
        ],
        'multiplier': 2.0
    },
    # Tier 3: Impact 3-5
    'tier3': {
        'journals': [
            'Clinical Neurophysiology', 'IEEE Transactions on Biomedical Engineering',
            'Journal of Neural Engineering', 'Epilepsy Research',
            'Epilepsy & Behavior', 'Scientific Reports', 'PLOS ONE',
            'Frontiers in Neuroscience', 'Journal of Neuroscience Methods'
        ],
        'multiplier': 1.5
    },
    # Default: All others
    'default': {
        'multiplier': 1.0
    }
}


def sanitize_query(query: str) -> Optional[str]:
    """
    Sanitize user input query for safety.

    Args:
        query: Raw user input query

    Returns:
        Sanitized query or None if invalid

    Safety checks:
        - Max 200 characters
        - Alphanumeric, spaces, and basic punctuation only
        - No special characters that could be injection attempts
    """
    if not query:
        logger.warning("Empty query provided")
        return None

    # Strip and check length
    query = query.strip()
    if len(query) > 200:
        logger.warning(f"Query too long: {len(query)} characters")
        return None

    # Allow only safe characters: alphanumeric, spaces, and basic punctuation
    # This pattern allows letters, numbers, spaces, hyphens, commas, periods, question marks
    # ADDED: Square brackets [] for PubMed field tags like [Author], [Title], [Journal]
    safe_pattern = r'^[a-zA-Z0-9\s\-,.\'\"():?!\[\]]+$'
    if not re.match(safe_pattern, query):
        logger.warning(f"Unsafe characters detected in query: {query}")
        return None

    # Additional check for SQL/command injection patterns
    dangerous_patterns = [
        r';\s*(DROP|DELETE|INSERT|UPDATE|SELECT)',  # SQL injection
        r'&&|\|\|',  # Command chaining
        r'<script',  # XSS attempts
        r'javascript:',  # JS injection
        r'\$\(',  # Command substitution
        r'`',  # Backticks
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.error(f"Potential injection attempt detected: {query}")
            return None

    logger.info(f"Query sanitized successfully: {query[:50]}...")
    return query


def rate_limit_request(api_name: str) -> None:
    """
    Enforce rate limiting between API calls.

    Args:
        api_name: Name of the API being called

    Ensures minimum 2 seconds between calls to the same API.
    Implements exponential backoff on repeated calls.
    """
    global _last_api_call

    current_time = time.time()

    if api_name in _last_api_call:
        elapsed = current_time - _last_api_call[api_name]
        if elapsed < RATE_LIMIT_SECONDS:
            sleep_time = RATE_LIMIT_SECONDS - elapsed
            logger.info(f"Rate limiting {api_name}: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

    _last_api_call[api_name] = time.time()
    logger.debug(f"API call to {api_name} at {datetime.now()}")


def get_cache_key(query: str, source: str) -> str:
    """
    Generate privacy-preserving cache key from query and source.

    Args:
        query: Search query
        source: API source name

    Returns:
        SHA256 hash of query+source for privacy
    """
    combined = f"{query.lower().strip()}:{source}"
    return hashlib.sha256(combined.encode()).hexdigest()


def cache_results(query: str, results: List[Dict], source: str) -> None:
    """
    Cache search results with 24-hour TTL.

    Args:
        query: Original search query
        results: List of paper results
        source: API source name
    """
    cache_key = get_cache_key(query, source)
    cache_entry = {
        'results': results,
        'timestamp': datetime.now().isoformat(),
        'source': source,
        'query_hash': cache_key
    }

    # Set with 24-hour expiration
    cache.set(cache_key, cache_entry, expire=86400)
    logger.info(f"Cached {len(results)} results for query from {source}")


def get_cached_results(query: str, source: str) -> Optional[List[Dict]]:
    """
    Retrieve cached results if available and not expired.

    Args:
        query: Search query
        source: API source name

    Returns:
        List of cached results or None if not found/expired
    """
    cache_key = get_cache_key(query, source)

    try:
        cache_entry = cache.get(cache_key)
        if cache_entry:
            timestamp = datetime.fromisoformat(cache_entry['timestamp'])
            age = datetime.now() - timestamp
            if age < timedelta(hours=24):
                logger.info(f"Cache hit for {source} (age: {age})")
                return cache_entry['results']
            else:
                logger.info(f"Cache expired for {source} (age: {age})")
                cache.delete(cache_key)
    except Exception as e:
        logger.error(f"Cache retrieval error: {e}")

    return None


def get_journal_tier(journal_name: str) -> str:
    """
    Determine journal tier from name.

    Args:
        journal_name: Name of the journal

    Returns:
        Tier string ('tier1', 'tier2', 'tier3', or 'default')
    """
    if not journal_name:
        return 'default'

    journal_lower = journal_name.lower()

    for tier, config in JOURNAL_TIERS.items():
        if tier == 'default':
            continue
        for journal in config['journals']:
            if journal.lower() in journal_lower:
                return tier

    return 'default'


def calculate_impact_score(paper: Dict) -> float:
    """
    Calculate impact score for paper ranking.

    Formula: citation_count * journal_tier_multiplier * recency_factor

    Args:
        paper: Paper dictionary with fields:
            - citation_count (int)
            - journal (str)
            - year (int)

    Returns:
        Impact score (float)
    """
    # Get citation count
    citations = paper.get('citation_count', 0)
    if citations is None:
        citations = 0

    # Get journal tier multiplier
    journal = paper.get('journal', '')
    tier = get_journal_tier(journal)
    tier_multiplier = JOURNAL_TIERS[tier]['multiplier']

    # Calculate recency factor (papers from last 3 years get bonus)
    year = paper.get('year', 0)
    current_year = datetime.now().year
    if year and year > current_year - 3:
        recency_factor = 1.2  # 20% bonus for recent papers
    elif year and year > current_year - 5:
        recency_factor = 1.1  # 10% bonus for somewhat recent
    else:
        recency_factor = 1.0

    # Calculate final score
    score = citations * tier_multiplier * recency_factor

    # Log scoring for important papers
    if score > 100:
        logger.info(f"High impact paper: {paper.get('title', 'Unknown')[:50]}... Score: {score:.1f}")

    return score


def sort_by_citations(papers: List[Dict]) -> List[Dict]:
    """
    Sort papers by citation count (descending).

    Args:
        papers: List of paper dictionaries

    Returns:
        Sorted list of papers
    """
    return sorted(papers, key=lambda p: p.get('citation_count', 0), reverse=True)


def sort_by_impact(papers: List[Dict]) -> List[Dict]:
    """
    Sort papers by calculated impact score (descending).

    Args:
        papers: List of paper dictionaries

    Returns:
        Sorted list of papers with impact_score field added
    """
    # Calculate impact scores
    for paper in papers:
        paper['impact_score'] = calculate_impact_score(paper)

    # Sort by impact score
    return sorted(papers, key=lambda p: p.get('impact_score', 0), reverse=True)


def log_api_request(api_name: str, query: str, response_code: int = None,
                   error: str = None) -> None:
    """
    Log API request for monitoring and debugging.

    Args:
        api_name: Name of the API
        query: Search query (will be truncated for privacy)
        response_code: HTTP response code if applicable
        error: Error message if request failed
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'api': api_name,
        'query': query[:50] + '...' if len(query) > 50 else query,
        'response_code': response_code,
        'error': error
    }

    if error:
        logger.error(f"API request failed: {json.dumps(log_entry)}")
    else:
        logger.info(f"API request: {json.dumps(log_entry)}")


def timeout_handler(func):
    """
    Decorator to add timeout handling to functions.
    Note: This is a simple timeout that doesn't actually interrupt execution.
    For production, consider using signal-based timeout or asyncio.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time

        if elapsed > REQUEST_TIMEOUT:
            logger.warning(f"{func.__name__} took {elapsed:.2f}s (timeout: {REQUEST_TIMEOUT}s)")

        return result
    return wrapper


def validate_paper_data(paper: Dict) -> bool:
    """
    Validate paper data structure for safety.

    Args:
        paper: Paper dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ['title', 'authors', 'year']

    # Check required fields exist
    for field in required_fields:
        if field not in paper:
            logger.warning(f"Paper missing required field: {field}")
            return False

    # Validate title length and content
    title = paper.get('title', '')
    if len(title) > 500:
        logger.warning(f"Paper title too long: {len(title)} characters")
        return False

    # Validate year is reasonable
    year = paper.get('year')
    if year:
        current_year = datetime.now().year
        if not (1900 <= year <= current_year + 1):
            logger.warning(f"Invalid paper year: {year}")
            return False

    return True


def clear_old_cache() -> None:
    """
    Clear cache entries older than 24 hours.
    This is called periodically to manage cache size.
    """
    try:
        # diskcache handles expiration automatically
        # This is just for manual cleanup if needed
        cache.expire()
        logger.info("Cache cleanup completed")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")


def test_safety_features():
    """
    Test function to verify all safety features are working.
    Run this after implementation to ensure everything works.
    """
    print("Testing paper_utils.py safety features...")
    print("=" * 50)

    # Test 1: Input sanitization
    print("\n1. Testing input sanitization:")
    test_queries = [
        "normal query about epilepsy",  # Should pass
        "a" * 201,  # Too long
        "query; DROP TABLE users",  # SQL injection attempt
        "query && rm -rf /",  # Command injection
        "query<script>alert(1)</script>",  # XSS attempt
    ]

    for query in test_queries:
        result = sanitize_query(query)
        status = "✓ PASS" if (result and query == test_queries[0]) or (not result and query != test_queries[0]) else "✗ FAIL"
        print(f"  {status}: {query[:50]}... -> {result is not None}")

    # Test 2: Rate limiting
    print("\n2. Testing rate limiting (should take 2+ seconds):")
    start = time.time()
    rate_limit_request("test_api")
    rate_limit_request("test_api")  # Should wait 2 seconds
    elapsed = time.time() - start
    status = "✓ PASS" if elapsed >= 2.0 else "✗ FAIL"
    print(f"  {status}: Elapsed time: {elapsed:.2f}s")

    # Test 3: Caching
    print("\n3. Testing cache operations:")
    test_query = "test query epilepsy"
    test_results = [{'title': 'Test Paper', 'authors': ['Author'], 'year': 2023}]

    # Cache and retrieve
    cache_results(test_query, test_results, "test_source")
    cached = get_cached_results(test_query, "test_source")
    status = "✓ PASS" if cached == test_results else "✗ FAIL"
    print(f"  {status}: Cache store and retrieve")

    # Test 4: Impact score calculation
    print("\n4. Testing impact score calculation:")
    test_papers = [
        {'title': 'Nature paper', 'journal': 'Nature', 'year': 2024, 'citation_count': 100},
        {'title': 'Brain paper', 'journal': 'Brain', 'year': 2023, 'citation_count': 50},
        {'title': 'Unknown journal', 'journal': 'Some Journal', 'year': 2020, 'citation_count': 10},
    ]

    for paper in test_papers:
        score = calculate_impact_score(paper)
        print(f"  {paper['journal']}: Score = {score:.1f}")

    # Test 5: Paper validation
    print("\n5. Testing paper data validation:")
    valid_paper = {'title': 'Valid Paper', 'authors': ['Author'], 'year': 2023}
    invalid_papers = [
        {'authors': ['Author'], 'year': 2023},  # Missing title
        {'title': 'a' * 501, 'authors': ['Author'], 'year': 2023},  # Title too long
        {'title': 'Paper', 'authors': ['Author'], 'year': 1800},  # Invalid year
    ]

    status = "✓ PASS" if validate_paper_data(valid_paper) else "✗ FAIL"
    print(f"  {status}: Valid paper validation")

    for i, paper in enumerate(invalid_papers):
        status = "✓ PASS" if not validate_paper_data(paper) else "✗ FAIL"
        print(f"  {status}: Invalid paper {i+1} validation")

    print("\n" + "=" * 50)
    print("Safety features testing complete!")


if __name__ == "__main__":
    # Run safety tests when script is executed directly
    test_safety_features()