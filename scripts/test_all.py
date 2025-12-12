#!/usr/bin/env python3
"""
test_all.py - Integration tests for the science-grounded skill
Tests the complete workflow from query to verified results.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from paper_utils import sanitize_query, validate_paper_data
from field_detector import FieldDetector
from arxiv_search import ArxivSearch
from semantic_scholar_search import SemanticScholarSearch


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_complete_workflow():
    """Test the complete workflow from query to results."""
    print_section("COMPLETE WORKFLOW TEST")

    # Test query
    query = "How does SINDy work for discovering nonlinear dynamics?"
    print(f"\nTest Query: {query}")

    # Step 1: Sanitize query
    print("\nStep 1: Sanitizing query...")
    clean_query = sanitize_query(query)
    if clean_query:
        print(f"✓ Query sanitized: {clean_query}")
    else:
        print("✗ Query failed sanitization")
        return False

    # Step 2: Detect research field
    print("\nStep 2: Detecting research field...")
    detector = FieldDetector()
    field_result = detector.detect_fields(clean_query)

    if field_result['detected_fields']:
        print(f"✓ Detected fields: {', '.join(field_result['detected_fields'][:3])}")
        print(f"  Recommended sources: {', '.join(field_result['recommended_sources'][:3])}")
    else:
        print("✗ No fields detected")

    # Step 3: Search for papers
    print("\nStep 3: Searching for papers...")

    # Try arXiv first (since Semantic Scholar has rate limits)
    arxiv = ArxivSearch()
    papers = arxiv.search(clean_query, limit=5)

    if papers:
        print(f"✓ Found {len(papers)} papers on arXiv")
        print("\nTop results:")
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper['title'][:60]}...")
            print(f"   Authors: {', '.join(paper['authors'][:2])}")
            if paper.get('year'):
                print(f"   Year: {paper['year']}")
            print(f"   Score: {paper.get('impact_score', 0):.1f}")
    else:
        print("✗ No papers found")
        return False

    # Step 4: Validate paper data
    print("\nStep 4: Validating paper data...")
    valid_count = sum(1 for p in papers if validate_paper_data(p))
    print(f"✓ {valid_count}/{len(papers)} papers passed validation")

    return True


def test_safety_features():
    """Test all safety features are working."""
    print_section("SAFETY FEATURES TEST")

    tests_passed = 0
    tests_total = 0

    # Test 1: Input sanitization
    print("\nTest 1: Input Sanitization")
    dangerous_queries = [
        "'; DROP TABLE papers; --",
        "<script>alert('xss')</script>",
        "query && rm -rf /",
        "a" * 201  # Too long
    ]

    for query in dangerous_queries:
        tests_total += 1
        result = sanitize_query(query)
        if result is None:
            print(f"  ✓ Blocked: {query[:30]}...")
            tests_passed += 1
        else:
            print(f"  ✗ NOT blocked: {query[:30]}...")

    # Test 2: Valid queries pass
    print("\nTest 2: Valid Queries")
    valid_queries = [
        "epilepsy seizure prediction",
        "Koopman operator theory",
        "What is SINDy?",
        "neural networks for EEG analysis"
    ]

    for query in valid_queries:
        tests_total += 1
        result = sanitize_query(query)
        if result is not None:
            print(f"  ✓ Allowed: {query}")
            tests_passed += 1
        else:
            print(f"  ✗ Blocked incorrectly: {query}")

    # Test 3: Rate limiting
    print("\nTest 3: Rate Limiting")
    print("  Testing 2-second delay between API calls...")
    arxiv = ArxivSearch()

    start = time.time()
    # Make two quick searches (should be rate limited)
    arxiv._search_papers("test1", 1, False)
    arxiv._search_papers("test2", 1, False)
    elapsed = time.time() - start

    tests_total += 1
    if elapsed >= 2.0:
        print(f"  ✓ Rate limiting working: {elapsed:.1f}s elapsed")
        tests_passed += 1
    else:
        print(f"  ✗ Rate limiting NOT working: {elapsed:.1f}s elapsed")

    # Summary
    print(f"\nSafety Tests: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total


def test_field_detection():
    """Test field detection for various queries."""
    print_section("FIELD DETECTION TEST")

    detector = FieldDetector()

    test_cases = [
        ("seizure onset zone localization with PLV", ["epilepsy_clinical", "connectivity"]),
        ("LSTM for EEG classification", ["machine_learning", "electrophysiology"]),
        ("Koopman operator theory", ["physics_informed", "nonlinear_dynamics"]),
        ("transfer entropy brain networks", ["information_theory", "graph_theory"]),
        ("wavelet transform seizure detection", ["signal_processing", "clinical_applications"])
    ]

    passed = 0
    for query, expected_fields in test_cases:
        result = detector.detect_fields(query)
        detected = result['detected_fields']

        # Check if at least one expected field was detected
        match = any(field in detected for field in expected_fields)

        if match:
            print(f"✓ {query[:40]}...")
            print(f"  Detected: {', '.join(detected[:3])}")
            passed += 1
        else:
            print(f"✗ {query[:40]}...")
            print(f"  Expected: {expected_fields}")
            print(f"  Got: {detected[:3] if detected else 'None'}")

    print(f"\nField Detection: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_no_hallucination():
    """Test that the system refuses when no sources are found."""
    print_section("NO HALLUCINATION TEST")

    # Test with a query that should return no results
    nonsense_query = "zzxqwerty neuroblastoma quantum entanglement"

    print(f"Testing with nonsense query: {nonsense_query}")

    arxiv = ArxivSearch()
    papers = arxiv.search(nonsense_query, limit=5)

    if not papers:
        print("✓ System correctly returned no results for nonsense query")
        print("  (Would trigger REFUSAL in production)")
        return True
    else:
        print(f"✗ System returned {len(papers)} results for nonsense query")
        print("  This could lead to hallucination!")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("   SCIENCE-GROUNDED SKILL INTEGRATION TESTS")
    print("=" * 60)

    all_passed = True

    # Run tests
    tests = [
        ("Safety Features", test_safety_features),
        ("Field Detection", test_field_detection),
        ("Complete Workflow", test_complete_workflow),
        ("No Hallucination", test_no_hallucination)
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"\n✗ {test_name} failed with error: {e}")
            results[test_name] = False
            all_passed = False

    # Summary
    print_section("TEST SUMMARY")
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")

    if all_passed:
        print("\n🎉 ALL TESTS PASSED! The skill is ready for use.")
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues.")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)