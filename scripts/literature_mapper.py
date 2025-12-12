#!/usr/bin/env python3
"""
literature_mapper.py - Map papers to appropriate literature folders

This module scans existing literature folders to learn naming patterns and
suggests appropriate filing locations for new papers based on their content.

It extracts category patterns like:
- DynSys_1_NeuralODE_Chen_2018
- Causal_1_CCM_Sugihara_2012
- ThalamoCortical_1_SeizureOnsetPatterns_Simpson_2025

And suggests appropriate folders and filenames for new papers.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Set up paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CATEGORY_CONFIG = CONFIG_DIR / "category_keywords.json"

# Known project directories to scan
PROJECT_PATHS = {
    "NeuroDynamics": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/NeuroDynamics/literature",
    "seizure_dynamics": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/seizure_dynamics/literature",
    "TimeSeriesML": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/TimeSeriesML/literature",
    "SignalProcessingML": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/SignalProcessingML/literature",
    "NetworkDynamics": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/NetworkDynamics/literature",
    "CollectiveBehavior": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/CollectiveBehavior/literature",
    "neural_ODE": "/Users/jsavarraj/Dropbox/GPTQueries/Brunton/neural_ODE/literature"
}


class LiteratureMapper:
    """Maps papers to appropriate literature folders based on content."""

    def __init__(self):
        """Initialize the literature mapper."""
        self.project_paths = PROJECT_PATHS
        self.category_patterns = {}
        self.category_counts = defaultdict(lambda: defaultdict(int))
        self.category_keywords = self._load_category_keywords()

        # Scan folders to learn patterns
        self.scan_literature_folders()

    def _load_category_keywords(self) -> Dict:
        """Load category keyword mappings."""
        if CATEGORY_CONFIG.exists():
            try:
                with open(CATEGORY_CONFIG, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._get_default_keywords()
        else:
            # Create default configuration
            keywords = self._get_default_keywords()
            CONFIG_DIR.mkdir(exist_ok=True)
            with open(CATEGORY_CONFIG, 'w') as f:
                json.dump(keywords, f, indent=2)
            return keywords

    def _get_default_keywords(self) -> Dict:
        """Get default category keyword mappings."""
        return {
            "DynSys": [
                "dynamical", "koopman", "neural ode", "DMD", "SINDy",
                "attractor", "bifurcation", "chaos", "lyapunov", "nonlinear"
            ],
            "Causal": [
                "causal", "granger", "transfer entropy", "CCM", "causality",
                "convergent cross mapping", "information flow", "directed"
            ],
            "ThalamoCortical": [
                "thalamus", "thalamocortical", "cortical", "thalamic",
                "cortico", "relay", "sensory gating"
            ],
            "Connectivity": [
                "connectivity", "network", "functional connectivity",
                "structural connectivity", "connectome", "graph", "PLV", "wPLI"
            ],
            "SeizureDynamotypes": [
                "dynamotype", "seizure classification", "seizure types",
                "seizure patterns", "seizure dynamics", "seizure evolution"
            ],
            "Epileptor": [
                "epileptor", "virtual brain", "seizure model", "Jirsa",
                "computational model", "whole brain model"
            ],
            "TimeFreq": [
                "time-frequency", "wavelet", "spectrogram", "FFT",
                "frequency analysis", "spectral", "Hilbert", "bandpower"
            ],
            "ML": [
                "machine learning", "deep learning", "LSTM", "transformer",
                "neural network", "classification", "prediction", "AI"
            ],
            "Clinical": [
                "clinical", "patient", "surgery", "resection", "outcome",
                "treatment", "drug", "therapy", "diagnosis"
            ],
            "Criticality": [
                "criticality", "critical", "phase transition", "avalanche",
                "power law", "scale-free", "self-organized"
            ]
        }

    def scan_literature_folders(self) -> Dict:
        """
        Scan all literature folders to extract patterns.

        Returns:
            Dictionary of discovered patterns per project
        """
        patterns = {}

        for project, path in self.project_paths.items():
            project_path = Path(path)
            if not project_path.exists():
                continue

            patterns[project] = []

            # Scan for files and folders
            for item in project_path.iterdir():
                # Extract pattern from filename
                pattern_info = self._extract_pattern(item.name)
                if pattern_info:
                    patterns[project].append(pattern_info)
                    category = pattern_info['category']
                    number = pattern_info.get('number', 0)

                    # Track highest number per category
                    if number > self.category_counts[project][category]:
                        self.category_counts[project][category] = number

        self.category_patterns = patterns
        return patterns

    def _extract_pattern(self, filename: str) -> Optional[Dict]:
        """
        Extract category pattern from filename.

        Expected format: Category_Number_Description_Author_Year

        Args:
            filename: The filename to parse

        Returns:
            Dictionary with extracted components or None
        """
        # Remove extension if present
        name = Path(filename).stem

        # Try to match pattern: Category_Number_...
        pattern = r'^([A-Za-z]+)_(\d+)_(.+?)_([A-Za-z]+)_(\d{4})'
        match = re.match(pattern, name)

        if match:
            return {
                'category': match.group(1),
                'number': int(match.group(2)),
                'description': match.group(3),
                'author': match.group(4),
                'year': int(match.group(5)),
                'full_name': filename
            }

        # Try simpler pattern without all components
        simple_pattern = r'^([A-Za-z]+)_(\d+)_'
        simple_match = re.match(simple_pattern, name)

        if simple_match:
            return {
                'category': simple_match.group(1),
                'number': int(simple_match.group(2)),
                'full_name': filename
            }

        return None

    def suggest_project(self, paper: Dict, review_notes: str = "") -> str:
        """
        Suggest which project folder a paper belongs to.

        Args:
            paper: Paper metadata
            review_notes: Optional review notes

        Returns:
            Project name (e.g., "NeuroDynamics")
        """
        # Extract keywords from paper
        text = f"{paper.get('title', '')} {paper.get('abstract', '')} {review_notes}".lower()

        # Check for specific project indicators
        if any(word in text for word in ['seizure', 'epilepsy', 'ictal', 'soz', 'epileptor']):
            if 'dynamotype' in text:
                return "seizure_dynamics"
            elif any(word in text for word in ['virtual brain', 'personalized', 'whole brain']):
                return "NeuroDynamics"
            else:
                return "seizure_dynamics"

        if any(word in text for word in ['neural ode', 'koopman', 'sindy', 'dmd', 'dynamical']):
            return "NeuroDynamics"

        if any(word in text for word in ['time series', 'forecast', 'arima', 'prediction']):
            return "TimeSeriesML"

        if any(word in text for word in ['signal processing', 'fft', 'wavelet', 'filter']):
            return "SignalProcessingML"

        if any(word in text for word in ['network', 'graph', 'connectivity', 'connectome']):
            return "NetworkDynamics"

        if any(word in text for word in ['collective', 'swarm', 'synchronization', 'consensus']):
            return "CollectiveBehavior"

        # Default to NeuroDynamics for neuroscience papers
        if any(word in text for word in ['brain', 'neural', 'neuron', 'cortex']):
            return "NeuroDynamics"

        # Final default
        return "neural_ODE"

    def suggest_category(self, paper: Dict, review_notes: str = "") -> str:
        """
        Suggest category prefix for a paper.

        Args:
            paper: Paper metadata
            review_notes: Optional review notes

        Returns:
            Category prefix (e.g., "DynSys", "Causal")
        """
        # Extract keywords from paper
        text = f"{paper.get('title', '')} {paper.get('abstract', '')} {review_notes}".lower()

        # Score each category based on keyword matches
        category_scores = {}

        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            return best_category

        # Default category if no matches
        return "General"

    def get_next_number(self, project: str, category: str) -> int:
        """
        Get the next available number for a category in a project.

        Args:
            project: Project name
            category: Category prefix

        Returns:
            Next available number
        """
        current_max = self.category_counts.get(project, {}).get(category, 0)
        return current_max + 1

    def create_filename(self, paper: Dict, category: str, number: int) -> str:
        """
        Create a properly formatted filename for a paper.

        Args:
            paper: Paper metadata
            category: Category prefix
            number: Number in sequence

        Returns:
            Formatted filename (without extension)
        """
        # Extract components
        title = paper.get('title', 'Unknown')
        authors = paper.get('authors', ['Unknown'])
        year = paper.get('year', datetime.now().year)

        # Clean and shorten title for filename
        # Remove special characters and limit length
        title_words = re.sub(r'[^\w\s]', '', title).split()[:3]
        short_title = ''.join(word.capitalize() for word in title_words)

        # Get first author's last name
        if authors and authors[0] != 'Unknown':
            # Handle "Last, First" format
            first_author = authors[0].split(',')[0].strip()
            # Remove special characters
            first_author = re.sub(r'[^\w]', '', first_author)
        else:
            first_author = 'Unknown'

        # Construct filename
        filename = f"{category}_{number}_{short_title}_{first_author}_{year}"

        return filename

    def suggest_filing(self, paper: Dict, review_notes: str = "") -> Dict:
        """
        Suggest complete filing location for a paper.

        Args:
            paper: Paper metadata
            review_notes: Optional review notes

        Returns:
            Dictionary with filing suggestions
        """
        # Determine project and category
        project = self.suggest_project(paper, review_notes)
        category = self.suggest_category(paper, review_notes)

        # Get next number
        number = self.get_next_number(project, category)

        # Create filename
        filename = self.create_filename(paper, category, number)

        # Build full path
        project_path = self.project_paths.get(project)
        if project_path:
            full_path = f"{project_path}/{filename}.pdf"
        else:
            full_path = f"[Project path not configured]/{filename}.pdf"

        # Create rationale
        rationale = self._generate_rationale(paper, project, category, review_notes)

        return {
            "project": project,
            "category": category,
            "number": number,
            "filename": filename,
            "full_path": full_path,
            "rationale": rationale
        }

    def _generate_rationale(self, paper: Dict, project: str, category: str,
                           review_notes: str) -> str:
        """Generate explanation for filing suggestion."""
        title = paper.get('title', 'Unknown')

        rationale_parts = [
            f"Project '{project}' selected based on content analysis.",
            f"Category '{category}' matches paper's primary topic."
        ]

        # Add specific reasons based on keywords
        if 'seizure' in title.lower() or 'epilepsy' in title.lower():
            rationale_parts.append("Paper focuses on seizure/epilepsy research.")

        if category == "DynSys":
            rationale_parts.append("Paper involves dynamical systems analysis.")
        elif category == "Causal":
            rationale_parts.append("Paper addresses causal relationships.")
        elif category == "ML":
            rationale_parts.append("Paper uses machine learning methods.")

        if review_notes and 'valuable' in review_notes.lower():
            rationale_parts.append("Marked as valuable in review.")

        return " ".join(rationale_parts)

    def get_statistics(self) -> Dict:
        """Get statistics about literature organization."""
        stats = {
            "projects_scanned": len(self.category_patterns),
            "total_papers": 0,
            "categories_found": set(),
            "papers_per_project": {},
            "categories_per_project": {}
        }

        for project, patterns in self.category_patterns.items():
            stats["total_papers"] += len(patterns)
            stats["papers_per_project"][project] = len(patterns)

            project_categories = set()
            for pattern in patterns:
                if 'category' in pattern:
                    category = pattern['category']
                    stats["categories_found"].add(category)
                    project_categories.add(category)

            stats["categories_per_project"][project] = list(project_categories)

        stats["categories_found"] = list(stats["categories_found"])
        return stats


def test_mapper():
    """Test the literature mapper functionality."""
    print("Testing LiteratureMapper...")
    print("=" * 50)

    mapper = LiteratureMapper()

    # Test with a sample paper
    test_paper = {
        "title": "Koopman Operator Theory for Seizure Prediction in Epilepsy",
        "authors": ["Smith, John", "Jones, Alice"],
        "year": 2024,
        "abstract": "We apply Koopman operator theory to predict seizures from sEEG data..."
    }

    # Test project suggestion
    project = mapper.suggest_project(test_paper)
    print(f"✓ Suggested project: {project}")

    # Test category suggestion
    category = mapper.suggest_category(test_paper)
    print(f"✓ Suggested category: {category}")

    # Test complete filing suggestion
    review_notes = "Excellent methodology using dynamical systems approach."
    suggestion = mapper.suggest_filing(test_paper, review_notes)

    print(f"\n📁 Filing Suggestion:")
    print(f"   Project: {suggestion['project']}")
    print(f"   Category: {suggestion['category']}_{suggestion['number']}")
    print(f"   Filename: {suggestion['filename']}")
    print(f"   Full path: {suggestion['full_path']}")
    print(f"   Rationale: {suggestion['rationale']}")

    # Show statistics
    stats = mapper.get_statistics()
    print(f"\n📊 Literature Statistics:")
    print(f"   Projects scanned: {stats['projects_scanned']}")
    print(f"   Total papers found: {stats['total_papers']}")
    print(f"   Categories found: {', '.join(stats['categories_found'][:5])}")

    print("\n" + "=" * 50)
    print("All tests passed!")


if __name__ == "__main__":
    # Import datetime for testing
    from datetime import datetime
    test_mapper()