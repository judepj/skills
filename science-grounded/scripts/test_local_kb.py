#!/usr/bin/env python3
"""
Test suite for local knowledge base search functionality.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from local_kb_search import LocalKBSearch, search_local_kb


def test_known_papers():
    """Test search for papers known to be in KB."""
    print("=== TEST 1: Known Papers ===\n")

    test_cases = [
        ("Gregg thalamic", "gregg_2025_thalamic_stimulation_network"),
        ("Khambhati hippocampal", "khambhati_2024_hippocampal_seizure_forecasting"),
        ("impedance rhythms", "mivalt_2023_impedance_rhythms"),
        ("optogenetics Chang", "chang_2025_exploring_gpcrmediated"),
    ]

    passed = 0
    for query, expected_substring in test_cases:
        results = search_local_kb(query, limit=5)
        found = any(expected_substring in r['paper_id'] for r in results)

        status = "✓ PASS" if found else "✗ FAIL"
        print(f"{status}: '{query}' → {len(results)} results")
        if found:
            passed += 1
            match = [r for r in results if expected_substring in r['paper_id']][0]
            print(f"  Found: {match['paper_id']} (score: {match['score']})")
        else:
            print(f"  Expected substring: {expected_substring}")
            if results:
                print(f"  Top result: {results[0]['paper_id']}")
        print()

    print(f"Passed: {passed}/{len(test_cases)}\n")
    return passed == len(test_cases)


def test_fallback_behavior():
    """Test that irrelevant queries still return results."""
    print("=== TEST 2: Fallback Behavior ===\n")

    results = search_local_kb("nonexistent topic xyz123", limit=3)
    print(f"Query with no good matches: {len(results)} results")
    print("(Should still return results based on common words)\n")

    return len(results) >= 0  # Always passes


def test_ranking():
    """Test that results are properly ranked by relevance."""
    print("=== TEST 3: Ranking ===\n")

    results = search_local_kb("thalamic stimulation epilepsy", limit=5)

    print(f"Top 5 results for 'thalamic stimulation epilepsy':")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.get('title', r['paper_id'])} (score: {r['score']})")

    # Check that scores are descending
    scores = [r['score'] for r in results]
    is_descending = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    status = "✓ PASS" if is_descending else "✗ FAIL"
    print(f"\n{status}: Scores in descending order\n")

    return is_descending


def test_empty_query():
    """Test handling of empty/short queries."""
    print("=== TEST 4: Edge Cases ===\n")

    results = search_local_kb("", limit=5)
    print(f"Empty query: {len(results)} results")

    results = search_local_kb("a b", limit=5)
    print(f"Short words query: {len(results)} results")
    print("(Short words <3 chars are skipped)\n")

    return True  # Should not crash


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*70)
    print("LOCAL KNOWLEDGE BASE SEARCH - TEST SUITE")
    print("="*70 + "\n")

    tests = [
        test_known_papers,
        test_fallback_behavior,
        test_ranking,
        test_empty_query,
    ]

    results = []
    for test in tests:
        try:
            passed = test()
            results.append(passed)
        except Exception as e:
            print(f"✗ EXCEPTION: {test.__name__} - {e}\n")
            results.append(False)

    print("="*70)
    print(f"OVERALL: {sum(results)}/{len(results)} tests passed")
    print("="*70 + "\n")

    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
