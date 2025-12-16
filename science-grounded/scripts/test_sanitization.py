#!/usr/bin/env python3
"""
Test suite for query sanitization with relaxed PubMed field tag support.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from paper_utils import sanitize_query


def test_pubmed_field_tags():
    """Test that PubMed field tags are now allowed."""
    print("=== TEST 1: PubMed Field Tags ===\n")

    test_cases = [
        ("Cash SS[Author]", True, "Author field tag"),
        ("epilepsy[Title]", True, "Title field tag"),
        ("Brain[Journal]", True, "Journal field tag"),
        ("seizure[MeSH Terms]", True, "MeSH field tag"),
        ("Cash SS[Author] AND thalamus[Title]", True, "Multiple field tags"),
    ]

    passed = 0
    for query, should_pass, description in test_cases:
        result = sanitize_query(query)
        success = (result is not None) == should_pass

        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {description}")
        print(f"  Query: '{query}'")
        print(f"  Result: {result if result else 'REJECTED'}")
        print()

        if success:
            passed += 1

    print(f"Passed: {passed}/{len(test_cases)}\n")
    return passed == len(test_cases)


def test_injection_protection():
    """Test that injection attacks are still blocked."""
    print("=== TEST 2: Injection Protection ===\n")

    malicious_queries = [
        ("test; DROP TABLE papers", "SQL injection"),
        ("query && rm -rf /", "Command chaining"),
        ("search <script>alert('xss')</script>", "XSS attempt"),
        ("query $(malicious command)", "Command substitution"),
        ("test `dangerous`", "Backtick execution"),
        ("javascript:alert('bad')", "JavaScript injection"),
    ]

    passed = 0
    for query, attack_type in malicious_queries:
        result = sanitize_query(query)
        blocked = (result is None)

        status = "✓ PASS" if blocked else "✗ FAIL"
        print(f"{status}: {attack_type}")
        print(f"  Query: '{query}'")
        print(f"  Blocked: {blocked}")
        print()

        if blocked:
            passed += 1

    print(f"Passed: {passed}/{len(malicious_queries)}\n")
    return passed == len(malicious_queries)


def test_normal_queries():
    """Test that normal scientific queries still work."""
    print("=== TEST 3: Normal Queries ===\n")

    normal_queries = [
        "epilepsy treatment 2024",
        "Sydney Cash thalamus",
        "deep brain stimulation, anterior nucleus",
        "What is the role of hippocampus in memory?",
        "seizure forecasting (machine learning)",
    ]

    passed = 0
    for query in normal_queries:
        result = sanitize_query(query)
        success = (result is not None)

        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: '{query}'")
        print(f"  Result: {result if result else 'REJECTED'}")
        print()

        if success:
            passed += 1

    print(f"Passed: {passed}/{len(normal_queries)}\n")
    return passed == len(normal_queries)


def test_edge_cases():
    """Test edge cases."""
    print("=== TEST 4: Edge Cases ===\n")

    test_cases = [
        ("", False, "Empty query"),
        ("a" * 201, False, "Too long (>200 chars)"),
        ("test@#$%^&*", False, "Special chars not in whitelist"),
        ("normal query [Author]", True, "Brackets with normal text"),
    ]

    passed = 0
    for query, should_pass, description in test_cases:
        result = sanitize_query(query)
        success = (result is not None) == should_pass

        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {description}")
        print(f"  Expected: {'PASS' if should_pass else 'REJECT'}")
        print(f"  Got: {'PASS' if result else 'REJECT'}")
        print()

        if success:
            passed += 1

    print(f"Passed: {passed}/{len(test_cases)}\n")
    return passed == len(test_cases)


def run_all_tests():
    """Run all sanitization tests."""
    print("\n" + "="*70)
    print("QUERY SANITIZATION - TEST SUITE")
    print("="*70 + "\n")

    tests = [
        test_pubmed_field_tags,
        test_injection_protection,
        test_normal_queries,
        test_edge_cases,
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
    print(f"OVERALL: {sum(results)}/{len(results)} test suites passed")
    print("="*70 + "\n")

    return all(results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
