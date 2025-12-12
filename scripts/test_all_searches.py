#!/usr/bin/env python3
"""
test_all_searches.py - Test all search engines together
Shows comprehensive literature search across all databases.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from field_detector import FieldDetector
from arxiv_search import ArxivSearch
from pubmed_search import PubMedSearch
from biorxiv_search import BiorxivSearch
from semantic_scholar_search import SemanticScholarSearch
from nih_reporter_search import NIHReporterSearch
from nsf_awards_search import NSFAwardsSearch


def search_all_databases(query, limit_per_db=3):
    """
    Search all available databases for a query.

    Args:
        query: Search query
        limit_per_db: Max results per database

    Returns:
        Dict with results from each database
    """
    print(f"\n{'='*60}")
    print(f"COMPREHENSIVE SEARCH: {query}")
    print(f"{'='*60}")

    # Step 1: Detect research field
    print("\n1. DETECTING RESEARCH FIELD...")
    detector = FieldDetector()
    field_result = detector.detect_fields(query)

    if field_result['detected_fields']:
        print(f"   Detected fields: {', '.join(field_result['detected_fields'][:3])}")
        print(f"   Recommended sources: {', '.join(field_result['recommended_sources'][:3])}")
    else:
        print("   No specific fields detected, will search all databases")

    all_results = {}

    # Step 2: Search PubMed
    print("\n2. SEARCHING PUBMED...")
    try:
        pubmed = PubMedSearch()
        pubmed_papers = pubmed.search(query, limit=limit_per_db, recent_only=True, use_cache=False)
        all_results['pubmed'] = pubmed_papers
        print(f"   ✓ Found {len(pubmed_papers)} papers in PubMed")
        if pubmed_papers:
            print(f"   Top result: {pubmed_papers[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ✗ PubMed search failed: {e}")
        all_results['pubmed'] = []

    time.sleep(2)  # Rate limiting

    # Step 3: Search arXiv
    print("\n3. SEARCHING ARXIV...")
    try:
        arxiv = ArxivSearch()
        arxiv_papers = arxiv.search(query, limit=limit_per_db, use_cache=False)
        all_results['arxiv'] = arxiv_papers
        print(f"   ✓ Found {len(arxiv_papers)} papers in arXiv")
        if arxiv_papers:
            print(f"   Top result: {arxiv_papers[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ✗ arXiv search failed: {e}")
        all_results['arxiv'] = []

    time.sleep(2)  # Rate limiting

    # Step 4: Search bioRxiv/medRxiv
    print("\n4. SEARCHING BIORXIV/MEDRXIV...")
    try:
        biorxiv = BiorxivSearch()
        biorxiv_papers = biorxiv.search(query, server="both", limit=limit_per_db, use_cache=False)
        all_results['biorxiv'] = biorxiv_papers
        print(f"   ✓ Found {len(biorxiv_papers)} papers in bioRxiv/medRxiv")
        if biorxiv_papers:
            print(f"   Top result: {biorxiv_papers[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ✗ bioRxiv/medRxiv search failed: {e}")
        all_results['biorxiv'] = []

    time.sleep(2)  # Rate limiting

    # Step 5: Try Semantic Scholar (may be rate limited)
    print("\n5. SEARCHING SEMANTIC SCHOLAR...")
    try:
        semantic = SemanticScholarSearch()
        semantic_papers = semantic.search(query, limit=limit_per_db, use_cache=False)
        all_results['semantic_scholar'] = semantic_papers
        if semantic_papers:
            print(f"   ✓ Found {len(semantic_papers)} papers in Semantic Scholar")
            print(f"   Top result: {semantic_papers[0]['title'][:60]}...")
        else:
            print("   ⚠ Semantic Scholar returned no results (likely rate limited)")
    except Exception as e:
        print(f"   ⚠ Semantic Scholar search failed (likely rate limited): {e}")
        all_results['semantic_scholar'] = []

    time.sleep(2)  # Rate limiting

    # Step 6: Search NIH RePORTER for grants
    print("\n6. SEARCHING NIH REPORTER (GRANTS)...")
    try:
        nih = NIHReporterSearch()
        nih_projects = nih.search_projects(query, limit=limit_per_db, use_cache=False, recent_only=True)
        all_results['nih_reporter'] = nih_projects
        print(f"   ✓ Found {len(nih_projects)} grants in NIH RePORTER")
        if nih_projects:
            print(f"   Top result: {nih_projects[0]['title'][:60]}...")
            print(f"   Funding: ${nih_projects[0]['award_amount']:,}")
    except Exception as e:
        print(f"   ✗ NIH RePORTER search failed: {e}")
        all_results['nih_reporter'] = []

    time.sleep(2)  # Rate limiting

    # Step 7: Search NSF Awards for grants
    print("\n7. SEARCHING NSF AWARDS (GRANTS)...")
    try:
        nsf = NSFAwardsSearch()
        nsf_awards = nsf.search_awards(query, limit=limit_per_db, use_cache=False, recent_only=True)
        all_results['nsf_awards'] = nsf_awards
        print(f"   ✓ Found {len(nsf_awards)} awards in NSF")
        if nsf_awards:
            print(f"   Top result: {nsf_awards[0]['title'][:60]}...")
            print(f"   Funding: ${nsf_awards[0]['award_amount']:,}")
    except Exception as e:
        print(f"   ✗ NSF Awards search failed: {e}")
        all_results['nsf_awards'] = []

    # Step 8: Summary
    print("\n" + "="*60)
    print("SEARCH SUMMARY")
    print("="*60)

    grant_dbs = ['nih_reporter', 'nsf_awards']
    paper_dbs = [db for db in all_results.keys() if db not in grant_dbs]

    total_papers = sum(len(all_results.get(db, [])) for db in paper_dbs)
    total_grants = sum(len(all_results.get(db, [])) for db in grant_dbs)
    print(f"\nTotal papers found: {total_papers}")
    print(f"Total grants found: {total_grants}")

    for db_name, items in all_results.items():
        is_grant_db = db_name in grant_dbs
        print(f"\n{db_name.upper()}: {len(items)} {'grants/awards' if is_grant_db else 'papers'}")
        for i, item in enumerate(items[:2], 1):
            print(f"  {i}. {item['title'][:50]}...")
            if item.get('year'):
                print(f"     Year: {item['year']}")
            if is_grant_db:
                print(f"     PI: {item.get('pi_name', 'N/A')}")
                print(f"     Funding: ${item.get('award_amount', 0):,}")
            elif item.get('journal'):
                print(f"     Journal: {item.get('journal', 'N/A')}")

    return all_results


def main():
    """Run comprehensive search tests."""
    print("\n" + "="*60)
    print("   TESTING ALL SEVEN SEARCH ENGINES")
    print("="*60)

    # Test queries covering different areas
    test_queries = [
        "seizure prediction machine learning",
        "Koopman operator dynamical systems",
        "drug-resistant epilepsy treatment"
    ]

    for query in test_queries:
        results = search_all_databases(query, limit_per_db=2)
        print("\n" + "-"*60)

        # Check which databases worked
        working_dbs = [db for db, papers in results.items() if papers]
        print(f"\n✓ Working databases: {', '.join(working_dbs)}")

        if not working_dbs:
            print("⚠ WARNING: No databases returned results!")

        time.sleep(3)  # Wait between different queries

    print("\n" + "="*60)
    print("ALL SEARCH ENGINES TEST COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Custom query from command line
        query = ' '.join(sys.argv[1:])
        search_all_databases(query, limit_per_db=3)
    else:
        # Run default tests
        main()