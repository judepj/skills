#!/usr/bin/env python3
"""
topic_classifier.py - Classify papers by research topic for smart caching

Determines paper topic (epilepsy/clinical, methods/reviews, general) to set
appropriate cache TTL (Time To Live).
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Topic definitions with cache TTLs (in hours)
TOPIC_CONFIG = {
    'epilepsy_clinical': {
        'ttl_hours': 168,  # 7 days
        'keywords': [
            'epilepsy', 'seizure', 'interictal', 'ictal', 'epileptiform',
            'iEEG', 'sEEG', 'ECoG', 'thalamus', 'hippocampus',
            'deep brain stimulation', 'DBS', 'RNS', 'responsive neurostimulation',
            'antiepileptic', 'anticonvulsant', 'temporal lobe epilepsy'
        ]
    },

    'methods_reviews': {
        'ttl_hours': 720,  # 30 days
        'keywords': [
            'review', 'systematic review', 'meta-analysis', 'survey',
            'methods', 'algorithm', 'framework', 'open source',
            'benchmark', 'dataset', 'tutorial', 'perspective'
        ]
    },

    'foundational': {
        'ttl_hours': 720,  # 30 days (foundation models are stable)
        'keywords': [
            'foundation model', 'pretrain', 'self-supervised',
            'transfer learning', 'large language model', 'transformer',
            'BERT', 'GPT', 'generative model'
        ]
    },

    'general': {
        'ttl_hours': 24,  # 1 day (default)
        'keywords': []  # Catch-all
    }
}


class TopicClassifier:
    """Classify papers by research topic."""

    def __init__(self, config: Dict = None):
        """
        Initialize classifier.

        Args:
            config: Topic configuration (defaults to TOPIC_CONFIG)
        """
        self.config = config or TOPIC_CONFIG

    def classify(self, title: str, abstract: str = "", authors: list = None) -> Tuple[str, int]:
        """
        Classify paper and return topic + cache TTL.

        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            authors: List of authors (optional)

        Returns:
            (topic_name, ttl_hours) tuple
        """
        # Combine text for analysis
        text = f"{title} {abstract}".lower()

        # Score each topic
        topic_scores = {}

        for topic_name, topic_data in self.config.items():
            if topic_name == 'general':
                continue  # Skip default

            keywords = topic_data['keywords']
            score = sum(text.count(kw.lower()) for kw in keywords)
            topic_scores[topic_name] = score

        # Find best matching topic
        if not topic_scores or max(topic_scores.values()) == 0:
            best_topic = 'general'
        else:
            best_topic = max(topic_scores, key=topic_scores.get)

        # Get TTL
        ttl_hours = self.config[best_topic]['ttl_hours']

        logger.info(f"Classified as '{best_topic}' (TTL: {ttl_hours}h) - scores: {topic_scores}")

        return best_topic, ttl_hours

    def get_ttl(self, topic: str) -> int:
        """
        Get cache TTL for a topic.

        Args:
            topic: Topic name

        Returns:
            TTL in hours
        """
        return self.config.get(topic, self.config['general'])['ttl_hours']


# Convenience function
def classify_paper(title: str, abstract: str = "") -> Tuple[str, int]:
    """
    Quick paper classification.

    Usage:
        from topic_classifier import classify_paper
        topic, ttl_hours = classify_paper(title, abstract)
    """
    classifier = TopicClassifier()
    return classifier.classify(title, abstract)


if __name__ == "__main__":
    # Test the classifier
    classifier = TopicClassifier()

    test_cases = [
        ("Thalamic DBS for Drug-Resistant Epilepsy",
         "We tested deep brain stimulation in 10 patients with intractable seizures using iEEG."),

        ("A Review of Machine Learning Methods for EEG Analysis",
         "This systematic review surveys deep learning approaches for electroencephalography."),

        ("Foundation Models for Neural Data",
         "We pretrain a transformer on large-scale neural recordings using self-supervised learning."),

        ("Quantum Computing for Optimization",
         "We apply quantum algorithms to solve combinatorial optimization problems."),
    ]

    print("\n" + "="*70)
    print("TOPIC CLASSIFIER - TEST CASES")
    print("="*70 + "\n")

    for title, abstract in test_cases:
        topic, ttl = classifier.classify(title, abstract)

        print(f"Title: {title}")
        print(f"Topic: {topic}")
        print(f"Cache TTL: {ttl} hours ({ttl//24} days)")
        print()
