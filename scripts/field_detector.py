#!/usr/bin/env python3
"""
field_detector.py - Detect research field from user query
Routes queries to appropriate databases based on detected field.

Uses keyword matching with configurable weights to determine
the most relevant research areas and databases.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from paper_utils import sanitize_query

# Set up paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"

# Configure logging
logger = logging.getLogger(__name__)


class FieldDetector:
    """
    Detect research field from query keywords.
    """

    def __init__(self, config_path: str = None):
        """
        Initialize field detector with keyword configuration.

        Args:
            config_path: Path to field_keywords.json (optional)
        """
        if config_path is None:
            config_path = CONFIG_DIR / "field_keywords.json"

        self.config = self._load_config(config_path)
        self.fields = self.config.get('fields', {})
        self.default_databases = self.config.get('default_databases', ['semantic_scholar'])
        self.confidence_threshold = self.config.get('confidence_threshold', 0.3)

    def _load_config(self, config_path: Path) -> Dict:
        """
        Load field keywords configuration from JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded field configuration from {config_path}")
                return config
        except Exception as e:
            logger.error(f"Failed to load field configuration: {e}")
            # Return minimal default config
            return {
                'fields': {
                    'general': {
                        'keywords': [],
                        'weight': 1.0,
                        'databases': ['semantic_scholar']
                    }
                },
                'default_databases': ['semantic_scholar'],
                'confidence_threshold': 0.3
            }

    def detect_fields(self, query: str) -> Dict:
        """
        Detect research fields from query.

        Args:
            query: User's search query

        Returns:
            Dictionary with:
                - detected_fields: List of detected field names
                - confidence_scores: Dict of field -> confidence score
                - recommended_sources: List of recommended databases
                - keywords_matched: Dict of field -> matched keywords
        """
        # Sanitize query first
        clean_query = sanitize_query(query)
        if not clean_query:
            logger.warning("Query failed sanitization")
            return self._default_result()

        # Convert query to lowercase for matching
        query_lower = clean_query.lower()
        query_words = set(query_lower.split())

        # Score each field based on keyword matches
        field_scores = {}
        keywords_matched = defaultdict(list)

        for field_name, field_config in self.fields.items():
            keywords = field_config.get('keywords', [])
            weight = field_config.get('weight', 1.0)

            # Count keyword matches
            matches = 0
            matched_keywords = []

            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Check for exact match or substring match
                if keyword_lower in query_lower:
                    matches += 1
                    matched_keywords.append(keyword)
                # Also check word-level matches for short keywords
                elif len(keyword_lower.split()) == 1 and keyword_lower in query_words:
                    matches += 0.8  # Slightly lower weight for word-only match
                    matched_keywords.append(keyword)

            if matches > 0:
                # Calculate score based on matches and weight
                score = (matches / len(keywords)) * weight
                field_scores[field_name] = score
                keywords_matched[field_name] = matched_keywords

        # Normalize scores to get confidence values
        if field_scores:
            max_score = max(field_scores.values())
            confidence_scores = {
                field: score / max_score if max_score > 0 else 0
                for field, score in field_scores.items()
            }
        else:
            confidence_scores = {}

        # Filter fields above confidence threshold
        detected_fields = [
            field for field, conf in confidence_scores.items()
            if conf >= self.confidence_threshold
        ]

        # Sort by confidence
        detected_fields.sort(key=lambda f: confidence_scores[f], reverse=True)

        # Get recommended databases
        recommended_sources = self._get_recommended_sources(detected_fields)

        # Log detection results
        if detected_fields:
            logger.info(f"Detected fields: {detected_fields[:3]} for query: {clean_query[:50]}...")
        else:
            logger.info(f"No specific fields detected for query: {clean_query[:50]}...")

        return {
            'detected_fields': detected_fields,
            'confidence_scores': confidence_scores,
            'recommended_sources': recommended_sources,
            'keywords_matched': dict(keywords_matched)
        }

    def _get_recommended_sources(self, detected_fields: List[str]) -> List[str]:
        """
        Get recommended databases based on detected fields.

        Args:
            detected_fields: List of detected field names

        Returns:
            Ordered list of recommended database names
        """
        if not detected_fields:
            return self.default_databases

        # Collect all recommended databases with weights
        database_scores = defaultdict(float)

        for field in detected_fields[:3]:  # Consider top 3 fields
            field_config = self.fields.get(field, {})
            databases = field_config.get('databases', self.default_databases)
            field_weight = field_config.get('weight', 1.0)

            for i, db in enumerate(databases):
                # Give higher weight to databases listed first
                db_weight = field_weight * (1.0 - i * 0.1)
                database_scores[db] += db_weight

        # Sort databases by score
        sorted_databases = sorted(
            database_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Return ordered list of database names
        return [db for db, _ in sorted_databases]

    def _default_result(self) -> Dict:
        """
        Return default result when no fields detected.

        Returns:
            Default detection result
        """
        return {
            'detected_fields': [],
            'confidence_scores': {},
            'recommended_sources': self.default_databases,
            'keywords_matched': {}
        }

    def get_field_info(self, field_name: str) -> Dict:
        """
        Get detailed information about a specific field.

        Args:
            field_name: Name of the field

        Returns:
            Field configuration dictionary
        """
        return self.fields.get(field_name, {})

    def list_all_fields(self) -> List[str]:
        """
        List all available research fields.

        Returns:
            List of field names
        """
        return list(self.fields.keys())


def test_field_detection():
    """
    Test field detection with various queries.
    """
    print("Testing field_detector.py")
    print("=" * 60)

    # Initialize detector
    detector = FieldDetector()

    # Test queries covering different research areas
    test_queries = [
        # Epilepsy + Signal Processing
        "How to detect seizures using wavelet transform in sEEG data?",

        # Physics-informed ML
        "What is SINDy and how does it work for discovering equations?",

        # Nonlinear dynamics + Epilepsy
        "Lyapunov exponents in epileptic brain dynamics",

        # Connectivity + Clinical
        "Phase locking value for seizure onset zone localization",

        # Machine Learning
        "LSTM networks for seizure prediction from EEG",

        # Information theory
        "Transfer entropy analysis of brain networks",

        # Advanced math
        "Riemannian manifold methods for EEG classification",

        # General neuroscience
        "How do neurons communicate?",

        # Invalid/dangerous query
        "'; DROP TABLE papers; --",

        # Empty query
        ""
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query[:60]}...")
        result = detector.detect_fields(query)

        if result['detected_fields']:
            print(f"   Detected fields: {', '.join(result['detected_fields'][:3])}")

            # Show top confidence scores
            top_scores = sorted(
                result['confidence_scores'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            print("   Confidence scores:")
            for field, score in top_scores:
                print(f"      - {field}: {score:.2f}")

            print(f"   Recommended databases: {', '.join(result['recommended_sources'][:3])}")

            # Show matched keywords for top field
            if result['keywords_matched']:
                top_field = result['detected_fields'][0]
                if top_field in result['keywords_matched']:
                    keywords = result['keywords_matched'][top_field][:5]
                    print(f"   Keywords matched ({top_field}): {', '.join(keywords)}")
        else:
            print("   No fields detected (will use default databases)")
            print(f"   Default databases: {', '.join(result['recommended_sources'])}")

    # Test listing all fields
    print("\n" + "=" * 60)
    print("Available research fields:")
    all_fields = detector.list_all_fields()
    for field in sorted(all_fields):
        print(f"  - {field}")

    print("\n" + "=" * 60)
    print("Field detection testing complete!")


if __name__ == "__main__":
    # Handle command line usage
    if len(sys.argv) > 1:
        # Use provided query
        query = ' '.join(sys.argv[1:])
        detector = FieldDetector()
        result = detector.detect_fields(query)

        print(f"Query: {query}")
        print("\nDetection Results:")
        print("-" * 40)

        if result['detected_fields']:
            print(f"Primary field: {result['detected_fields'][0]}")
            print(f"Confidence: {result['confidence_scores'][result['detected_fields'][0]]:.2f}")
            print(f"\nAll detected fields: {', '.join(result['detected_fields'])}")
            print(f"Recommended sources: {', '.join(result['recommended_sources'][:5])}")

            if result['keywords_matched'] and result['detected_fields'][0] in result['keywords_matched']:
                print(f"\nMatched keywords: {', '.join(result['keywords_matched'][result['detected_fields'][0]][:10])}")
        else:
            print("No specific field detected")
            print(f"Using default sources: {', '.join(result['recommended_sources'])}")
    else:
        # Run tests
        test_field_detection()