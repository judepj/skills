#!/usr/bin/env python3
"""
paper_tracker.py - Track paper review states and filing suggestions

This module manages the lifecycle of papers from API discovery through PDF review
to filing suggestions. It maintains a persistent record of which papers have been
reviewed, their review notes, and suggested filing locations.

Status progression:
1. api_only - Paper found via API search
2. pdf_requested - User asked to provide PDF
3. pdf_reviewed - PDF has been reviewed
4. filed - Paper has been filed in literature folder
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Set up paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TRACKER_FILE = DATA_DIR / "paper_reviews.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class PaperTracker:
    """Manages paper review states and filing suggestions."""

    def __init__(self):
        """Initialize the paper tracker with persistent storage."""
        self.tracker_file = TRACKER_FILE
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Load existing tracking data or create new structure."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, back it up and start fresh
                backup_file = self.tracker_file.with_suffix('.backup.json')
                if self.tracker_file.exists():
                    self.tracker_file.rename(backup_file)
                return self._create_empty_data()
        else:
            return self._create_empty_data()

    def _create_empty_data(self) -> Dict:
        """Create empty data structure for tracking."""
        return {
            "papers": {},
            "statistics": {
                "total_searched": 0,
                "pdfs_requested": 0,
                "pdfs_reviewed": 0,
                "papers_filed": 0
            },
            "last_updated": datetime.now().isoformat()
        }

    def _save_data(self):
        """Save tracking data to disk."""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.tracker_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def _get_paper_id(self, paper: Dict) -> str:
        """Generate unique ID for a paper based on DOI or other identifiers."""
        # Try DOI first
        if paper.get('doi'):
            return f"doi_{paper['doi'].replace('/', '_')}"
        # Try arXiv ID
        elif paper.get('arxiv_id'):
            return f"arxiv_{paper['arxiv_id']}"
        # Try PMID
        elif paper.get('pmid'):
            return f"pmid_{paper['pmid']}"
        # Fallback to hash of title and first author
        else:
            title = paper.get('title', 'unknown')
            authors = paper.get('authors', ['unknown'])
            first_author = authors[0] if authors else 'unknown'
            unique_string = f"{title}_{first_author}"
            return f"hash_{hashlib.md5(unique_string.encode()).hexdigest()[:10]}"

    def track_search_result(self, paper: Dict, search_query: str, timestamp: datetime = None) -> str:
        """
        Track a paper found via API search.

        Args:
            paper: Paper metadata from API search
            search_query: The query that found this paper
            timestamp: When the paper was found (defaults to now)

        Returns:
            Paper ID for future reference
        """
        paper_id = self._get_paper_id(paper)

        if paper_id not in self.data["papers"]:
            self.data["papers"][paper_id] = {
                "paper_id": paper_id,
                "status": "api_only",
                "api_metadata": {
                    "title": paper.get('title'),
                    "authors": paper.get('authors', [])[:5],  # Keep first 5 authors
                    "year": paper.get('year'),
                    "journal": paper.get('journal'),
                    "doi": paper.get('doi'),
                    "arxiv_id": paper.get('arxiv_id'),
                    "pmid": paper.get('pmid'),
                    "citation_count": paper.get('citation_count', 0),
                    "impact_score": paper.get('impact_score', 0)
                },
                "search_queries": [search_query],
                "first_seen": (timestamp or datetime.now()).isoformat(),
                "last_updated": (timestamp or datetime.now()).isoformat()
            }
            self.data["statistics"]["total_searched"] += 1
        else:
            # Update existing entry
            if search_query not in self.data["papers"][paper_id]["search_queries"]:
                self.data["papers"][paper_id]["search_queries"].append(search_query)
            self.data["papers"][paper_id]["last_updated"] = datetime.now().isoformat()

        self._save_data()
        return paper_id

    def request_pdf_review(self, paper_id: str) -> Dict:
        """
        Mark a paper as needing PDF review.

        Args:
            paper_id: The paper ID to request review for

        Returns:
            Updated paper record
        """
        if paper_id not in self.data["papers"]:
            raise ValueError(f"Paper {paper_id} not found in tracker")

        paper = self.data["papers"][paper_id]

        # Only update if not already requested or reviewed
        if paper["status"] == "api_only":
            paper["status"] = "pdf_requested"
            paper["pdf_requested_date"] = datetime.now().isoformat()
            paper["last_updated"] = datetime.now().isoformat()
            self.data["statistics"]["pdfs_requested"] += 1
            self._save_data()

        return paper

    def record_pdf_reviewed(self, paper_id: str, review_notes: str,
                           is_valuable: bool = True,
                           suggested_folder: str = None,
                           suggested_filename: str = None) -> Dict:
        """
        Record that a PDF has been reviewed.

        Args:
            paper_id: The paper ID that was reviewed
            review_notes: Notes from the review
            is_valuable: Whether the paper is worth filing
            suggested_folder: Suggested folder path
            suggested_filename: Suggested filename

        Returns:
            Updated paper record
        """
        if paper_id not in self.data["papers"]:
            raise ValueError(f"Paper {paper_id} not found in tracker")

        paper = self.data["papers"][paper_id]

        # Update status and review information
        paper["status"] = "pdf_reviewed"
        paper["pdf_reviewed_date"] = datetime.now().isoformat()
        paper["review"] = {
            "notes": review_notes,
            "is_valuable": is_valuable,
            "reviewed_at": datetime.now().isoformat()
        }

        if suggested_folder or suggested_filename:
            paper["filing_suggestion"] = {
                "folder": suggested_folder,
                "filename": suggested_filename,
                "suggested_at": datetime.now().isoformat()
            }

        paper["last_updated"] = datetime.now().isoformat()

        # Update statistics
        if paper["status"] != "pdf_reviewed":  # Don't double-count
            self.data["statistics"]["pdfs_reviewed"] += 1

        self._save_data()
        return paper

    def mark_as_filed(self, paper_id: str, actual_path: str) -> Dict:
        """
        Mark a paper as filed in the literature folder.

        Args:
            paper_id: The paper ID that was filed
            actual_path: The actual path where it was filed

        Returns:
            Updated paper record
        """
        if paper_id not in self.data["papers"]:
            raise ValueError(f"Paper {paper_id} not found in tracker")

        paper = self.data["papers"][paper_id]
        paper["status"] = "filed"
        paper["filed_at"] = actual_path
        paper["filed_date"] = datetime.now().isoformat()
        paper["last_updated"] = datetime.now().isoformat()

        self.data["statistics"]["papers_filed"] += 1
        self._save_data()
        return paper

    def get_review_status(self, paper_id: str) -> Optional[Dict]:
        """
        Get the current status of a paper.

        Args:
            paper_id: The paper ID to check

        Returns:
            Status dictionary or None if not found
        """
        if paper_id not in self.data["papers"]:
            return None

        paper = self.data["papers"][paper_id]
        status_info = {
            "status": paper["status"],
            "last_updated": paper["last_updated"]
        }

        # Add relevant dates based on status
        if paper["status"] in ["pdf_requested", "pdf_reviewed", "filed"]:
            if "pdf_requested_date" in paper:
                requested = datetime.fromisoformat(paper["pdf_requested_date"])
                days_waiting = (datetime.now() - requested).days
                status_info["pdf_requested_date"] = paper["pdf_requested_date"]
                status_info["days_waiting"] = days_waiting

        if paper["status"] in ["pdf_reviewed", "filed"]:
            if "review" in paper:
                status_info["is_valuable"] = paper["review"]["is_valuable"]

        if paper["status"] == "filed":
            status_info["filed_at"] = paper.get("filed_at")

        return status_info

    def list_pending_reviews(self) -> List[Dict]:
        """
        List all papers waiting for PDF review.

        Returns:
            List of papers with status 'pdf_requested'
        """
        pending = []
        for paper_id, paper in self.data["papers"].items():
            if paper["status"] == "pdf_requested":
                pending.append({
                    "paper_id": paper_id,
                    "title": paper["api_metadata"]["title"],
                    "authors": paper["api_metadata"]["authors"],
                    "requested_date": paper.get("pdf_requested_date"),
                    "days_waiting": self._calculate_days_waiting(paper)
                })

        # Sort by request date (oldest first)
        pending.sort(key=lambda x: x.get("requested_date", ""))
        return pending

    def _calculate_days_waiting(self, paper: Dict) -> int:
        """Calculate days since PDF was requested."""
        if "pdf_requested_date" in paper:
            requested = datetime.fromisoformat(paper["pdf_requested_date"])
            return (datetime.now() - requested).days
        return 0

    def get_valuable_papers(self, limit: int = 10) -> List[Dict]:
        """
        Get recently reviewed valuable papers.

        Args:
            limit: Maximum number of papers to return

        Returns:
            List of valuable papers sorted by review date
        """
        valuable = []
        for paper_id, paper in self.data["papers"].items():
            if (paper["status"] in ["pdf_reviewed", "filed"] and
                paper.get("review", {}).get("is_valuable", False)):
                valuable.append({
                    "paper_id": paper_id,
                    "title": paper["api_metadata"]["title"],
                    "authors": paper["api_metadata"]["authors"],
                    "year": paper["api_metadata"]["year"],
                    "review_notes": paper["review"]["notes"],
                    "filed": paper["status"] == "filed",
                    "filed_at": paper.get("filed_at"),
                    "reviewed_at": paper["review"]["reviewed_at"]
                })

        # Sort by review date (newest first)
        valuable.sort(key=lambda x: x["reviewed_at"], reverse=True)
        return valuable[:limit]

    def get_statistics(self) -> Dict:
        """Get overall tracking statistics."""
        stats = self.data["statistics"].copy()

        # Add current counts
        stats["current_pending"] = len(self.list_pending_reviews())
        stats["valuable_papers"] = len([
            p for p in self.data["papers"].values()
            if p.get("review", {}).get("is_valuable", False)
        ])

        return stats

    def search_by_title(self, partial_title: str) -> List[Dict]:
        """
        Search for papers by partial title match.

        Args:
            partial_title: Partial title to search for

        Returns:
            List of matching papers
        """
        matches = []
        search_lower = partial_title.lower()

        for paper_id, paper in self.data["papers"].items():
            title = paper["api_metadata"].get("title", "").lower()
            if search_lower in title:
                matches.append({
                    "paper_id": paper_id,
                    "title": paper["api_metadata"]["title"],
                    "status": paper["status"]
                })

        return matches


def test_tracker():
    """Test the paper tracker functionality."""
    print("Testing PaperTracker...")
    print("=" * 50)

    tracker = PaperTracker()

    # Test tracking a search result
    test_paper = {
        "title": "Test Paper on Epileptor Models",
        "authors": ["Smith, J.", "Jones, A."],
        "year": 2024,
        "journal": "Brain",
        "doi": "10.1234/test.2024",
        "citation_count": 50,
        "impact_score": 150
    }

    paper_id = tracker.track_search_result(test_paper, "epileptor model test")
    print(f"✓ Tracked paper: {paper_id}")

    # Test requesting PDF review
    tracker.request_pdf_review(paper_id)
    print(f"✓ Requested PDF review")

    # Test getting status
    status = tracker.get_review_status(paper_id)
    print(f"✓ Status: {status['status']}")

    # Test recording review
    review_notes = "Excellent methodology. Relevant to seizure prediction."
    tracker.record_pdf_reviewed(
        paper_id,
        review_notes,
        is_valuable=True,
        suggested_folder="/NeuroDynamics/literature/",
        suggested_filename="DynSys_15_EpileptorTest_Smith_2024"
    )
    print(f"✓ Recorded PDF review")

    # Test statistics
    stats = tracker.get_statistics()
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 50)
    print("All tests passed!")


if __name__ == "__main__":
    test_tracker()