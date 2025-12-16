#!/usr/bin/env python3
"""
test_pdf_workflow.py - Test the complete PDF review workflow

This script demonstrates the full workflow:
1. Search for papers
2. Identify promising papers
3. Request PDF review
4. Simulate PDF review
5. Get filing suggestions
"""

import sys
from datetime import datetime
from pathlib import Path

# Add scripts to path (relative to this file's location)
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from pubmed_search import PubMedSearch
from paper_tracker import PaperTracker
from literature_mapper import LiteratureMapper

def test_workflow():
    """Test the complete PDF review workflow."""
    print("\n" + "=" * 60)
    print("TESTING PDF REVIEW WORKFLOW")
    print("=" * 60)

    # Initialize components
    pubmed = PubMedSearch()
    tracker = PaperTracker()
    mapper = LiteratureMapper()

    # Step 1: Search for papers
    print("\n📚 STEP 1: Searching for papers about Epileptor model...")
    print("-" * 40)

    query = "Jirsa Epileptor seizure model"
    papers = pubmed.search(query, limit=3)

    if not papers:
        print("No papers found. Using test data...")
        # Create test papers if search fails
        papers = [
            {
                "title": "Personalised virtual brain models in epilepsy",
                "authors": ["Jirsa, Viktor", "Wang, Huifang", "Triebkorn, Paul"],
                "year": 2023,
                "journal": "The Lancet Neurology",
                "doi": "10.1016/S1474-4422(23)00008-X",
                "pmid": "36972720",
                "citation_count": 85,
                "impact_score": 255
            }
        ]

    # Display found papers
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}")
        print(f"   Year: {paper.get('year', 'N/A')}")
        print(f"   Citations: {paper.get('citation_count', 0)}")
        print(f"   Impact Score: {paper.get('impact_score', 0)}")

    # Step 2: Track and identify promising papers
    print("\n\n🔍 STEP 2: Identifying promising papers...")
    print("-" * 40)

    promising_papers = []

    for paper in papers:
        # Track the search result
        paper_id = tracker.track_search_result(paper, query)

        # Check if paper is highly promising
        impact_score = paper.get('impact_score', 0)
        citations = paper.get('citation_count', 0)

        if impact_score > 150 or citations > 50:
            promising_papers.append((paper_id, paper))
            print(f"\n✅ PROMISING: {paper['title'][:50]}...")
            print(f"   Impact Score: {impact_score}")
            print(f"   Citations: {citations}")

    # Step 3: Request PDF review for the most promising paper
    if promising_papers:
        print("\n\n📄 STEP 3: Requesting PDF review...")
        print("-" * 40)

        # Take the first promising paper
        paper_id, paper = promising_papers[0]

        # Request PDF review
        tracker.request_pdf_review(paper_id)

        print(f"\n📄 HIGHLY PROMISING PAPER FOUND:")
        print(f"   Title: {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}")
        print(f"   Impact Score: {paper.get('impact_score', 'N/A')}")
        print(f"   Citations: {paper.get('citation_count', 'N/A')}")
        print(f"\n   🔗 Could you provide the PDF for detailed review?")
        print(f"   (DOI: https://doi.org/{paper.get('doi', 'N/A')})")

        # Check current status
        status = tracker.get_review_status(paper_id)
        print(f"\n   Current Status: {status['status']}")

    # Step 4: Simulate PDF review
    print("\n\n📖 STEP 4: Simulating PDF review...")
    print("-" * 40)

    if promising_papers:
        paper_id, paper = promising_papers[0]

        # Simulate reading and reviewing the PDF
        print("\n[Simulating PDF analysis...]")

        review_notes = """
Methodology: Excellent - Virtual brain modeling using patient-specific connectivity
Validation: Strong - Validated on 50+ patients with drug-resistant epilepsy
Reproducibility: High - The Virtual Brain platform is open-source
Relevance: Critical for personalized epilepsy treatment planning
Key findings: Patient-specific models can predict surgical outcomes
Innovation: Combines structural connectivity with dynamical modeling
Clinical impact: Could reduce failed epilepsy surgeries by 30%
Limitations: Requires high-quality MRI and sEEG data
        """

        print("\n✅ Review completed!")
        print("\nReview Notes:")
        print("-" * 20)
        print(review_notes.strip())

        # Record the review
        tracker.record_pdf_reviewed(
            paper_id,
            review_notes=review_notes,
            is_valuable=True
        )

    # Step 5: Get filing suggestion
    print("\n\n📁 STEP 5: Getting filing suggestion...")
    print("-" * 40)

    if promising_papers:
        paper_id, paper = promising_papers[0]

        # Get filing suggestion
        suggestion = mapper.suggest_filing(paper, review_notes)

        print(f"\n📁 FILING SUGGESTION:")
        print(f"   Project: {suggestion['project']}")
        print(f"   Category: {suggestion['category']}")
        print(f"   Number: {suggestion['number']}")
        print(f"   Filename: {suggestion['filename']}.pdf")
        print(f"\n   Full Path:")
        print(f"   {suggestion['full_path']}")
        print(f"\n   Rationale: {suggestion['rationale']}")

    # Step 6: Show tracking statistics
    print("\n\n📊 STEP 6: Tracking Statistics")
    print("-" * 40)

    stats = tracker.get_statistics()
    print(f"\nOverall Statistics:")
    print(f"   Total papers searched: {stats['total_searched']}")
    print(f"   PDFs requested: {stats['pdfs_requested']}")
    print(f"   PDFs reviewed: {stats['pdfs_reviewed']}")
    print(f"   Valuable papers: {stats['valuable_papers']}")
    print(f"   Currently pending: {stats['current_pending']}")

    # Show pending reviews
    pending = tracker.list_pending_reviews()
    if pending:
        print(f"\n⏳ Papers Waiting for Review:")
        for p in pending:
            print(f"   - {p['title'][:50]}... (waiting {p['days_waiting']} days)")

    # Show valuable papers
    valuable = tracker.get_valuable_papers(limit=3)
    if valuable:
        print(f"\n💎 Recently Reviewed Valuable Papers:")
        for p in valuable:
            print(f"   ✓ {p['title'][:50]}...")
            if p.get('filed'):
                print(f"     Filed at: {p['filed_at']}")

    print("\n" + "=" * 60)
    print("WORKFLOW TEST COMPLETE!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_workflow()