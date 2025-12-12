#!/usr/bin/env python3
"""
relevance_scorer.py - Score paper relevance for epilepsy/iEEG research

Keyword-based scoring with weighted categories matching user's research interests.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Weighted keyword categories (higher weight = more important)
KEYWORD_WEIGHTS = {
    # Core research focus (weight: 10)
    'core': {
        'weight': 10,
        'keywords': [
            'epilepsy', 'seizure', 'interictal', 'ictal', 'epileptiform',
            'anticonvulsant', 'antiepileptic', 'temporal lobe epilepsy'
        ]
    },

    # Recording modalities (weight: 8)
    'modality': {
        'weight': 8,
        'keywords': [
            'iEEG', 'intracranial EEG', 'sEEG', 'stereo-EEG', 'ECoG',
            'electrocorticography', 'depth electrode', 'subdural'
        ]
    },

    # Brain regions (weight: 7)
    'regions': {
        'weight': 7,
        'keywords': [
            'thalamus', 'thalamic', 'hippocampus', 'hippocampal',
            'anterior nucleus', 'centromedian', 'pulvinar',
            'limbic system', 'amygdala'
        ]
    },

    # Neuromodulation (weight: 8)
    'neuromodulation': {
        'weight': 8,
        'keywords': [
            'deep brain stimulation', 'DBS', 'responsive neurostimulation',
            'RNS', 'neuromodulation', 'electrical stimulation',
            'closed-loop', 'adaptive stimulation'
        ]
    },

    # Biomarkers (weight: 7)
    'biomarkers': {
        'weight': 7,
        'keywords': [
            'biomarker', 'seizure prediction', 'seizure forecasting',
            'brain state', 'connectivity', 'functional connectivity',
            'high-frequency oscillation', 'HFO'
        ]
    },

    # Methods (weight: 6)
    'methods': {
        'weight': 6,
        'keywords': [
            'machine learning', 'deep learning', 'neural network',
            'foundation model', 'transformer', 'LSTM', 'CNN',
            'dynamical systems', 'Koopman', 'state space model'
        ]
    },

    # Clinical (weight: 5)
    'clinical': {
        'weight': 5,
        'keywords': [
            'drug-resistant', 'refractory epilepsy', 'surgical',
            'resection', 'epilepsy surgery', 'seizure freedom',
            'clinical trial', 'patient'
        ]
    },

    # Specific devices (weight: 6)
    'devices': {
        'weight': 6,
        'keywords': [
            'NeuroPace', 'Medtronic', 'Summit', 'RC+S', 'Percept',
            'Neuropixels', 'Precision Neuroscience', 'Axoft'
        ]
    }
}


class RelevanceScorer:
    """Score paper relevance based on epilepsy/iEEG research keywords."""

    def __init__(self, custom_weights: Optional[Dict] = None):
        """
        Initialize scorer with keyword weights.

        Args:
            custom_weights: Custom keyword categories (overrides defaults)
        """
        self.weights = custom_weights or KEYWORD_WEIGHTS

    def score_paper(self, title: str, abstract: str, full_text: str = "") -> Tuple[int, List[str]]:
        """
        Score paper relevance (0-100).

        Args:
            title: Paper title
            abstract: Paper abstract
            full_text: Full paper text (optional, improves scoring)

        Returns:
            (score, reasons) tuple
        """
        # Combine text with different weights
        # Title matches count 3x, abstract 2x, full_text 1x
        title_lower = title.lower()
        abstract_lower = abstract.lower()
        full_text_lower = full_text.lower() if full_text else ""

        total_score = 0
        matched_categories = []
        matched_keywords = set()

        for category_name, category_data in self.weights.items():
            weight = category_data['weight']
            keywords = category_data['keywords']

            category_matches = 0

            for keyword in keywords:
                keyword_lower = keyword.lower()

                # Count matches in each section
                title_matches = title_lower.count(keyword_lower) * 3
                abstract_matches = abstract_lower.count(keyword_lower) * 2

                if full_text:
                    # Limit full text matches to avoid overwhelming score
                    full_text_matches = min(full_text_lower.count(keyword_lower), 10)
                else:
                    full_text_matches = 0

                total_matches = title_matches + abstract_matches + full_text_matches

                if total_matches > 0:
                    category_matches += total_matches
                    matched_keywords.add(keyword)

            # Add weighted category score
            if category_matches > 0:
                category_score = min(category_matches * weight, weight * 5)  # Cap per category
                total_score += category_score
                matched_categories.append(category_name)

        # Normalize to 0-100
        # Max possible score ~ 400 (all categories maxed)
        normalized_score = min(int((total_score / 400) * 100), 100)

        # Generate reasons
        reasons = self._generate_reasons(matched_categories, matched_keywords)

        return normalized_score, reasons

    def _generate_reasons(self, categories: List[str], keywords: set) -> List[str]:
        """
        Generate human-readable reasons for score.

        Args:
            categories: Matched category names
            keywords: Matched keywords

        Returns:
            List of reason strings
        """
        reasons = []

        if not categories:
            return ["No matches found"]

        # Category-based reasons
        category_map = {
            'core': 'Core epilepsy research',
            'modality': 'iEEG/ECoG recording',
            'regions': 'Relevant brain regions',
            'neuromodulation': 'DBS/RNS neuromodulation',
            'biomarkers': 'Biomarker development',
            'methods': 'ML/dynamical systems methods',
            'clinical': 'Clinical translation',
            'devices': 'Specific devices/platforms'
        }

        for cat in categories[:3]:  # Top 3 categories
            if cat in category_map:
                reasons.append(category_map[cat])

        # Add specific high-value keywords if matched
        priority_keywords = ['foundation model', 'closed-loop', 'seizure prediction',
                            'thalamic DBS', 'responsive neurostimulation']

        for kw in priority_keywords:
            if kw in keywords:
                reasons.append(f"Contains '{kw}'")

        return reasons[:5]  # Max 5 reasons


if __name__ == "__main__":
    # Test the scorer
    scorer = RelevanceScorer()

    test_cases = [
        {
            'title': 'Deep Brain Stimulation of Anterior Nucleus for Epilepsy',
            'abstract': 'We tested DBS in patients with drug-resistant temporal lobe epilepsy using iEEG monitoring.',
            'full_text': ''
        },
        {
            'title': 'Machine Learning for Image Classification',
            'abstract': 'We developed a CNN for classifying images of cats and dogs.',
            'full_text': ''
        },
        {
            'title': 'Foundation Models for Seizure Prediction from Intracranial EEG',
            'abstract': 'Transformer-based foundation model trained on 1000 hours of sEEG from epilepsy patients.',
            'full_text': 'Methods involved recording from hippocampus and thalamus with closed-loop responsive neurostimulation.'
        }
    ]

    for i, test in enumerate(test_cases, 1):
        score, reasons = scorer.score_paper(test['title'], test['abstract'], test['full_text'])

        print(f"\nTest {i}: {test['title'][:50]}...")
        print(f"Score: {score}/100")
        print(f"Reasons: {', '.join(reasons)}")
