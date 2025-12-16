#!/usr/bin/env python3
"""
arxiv_pdf_screener.py - Smart PDF screening for arXiv papers

Downloads PDFs temporarily, extracts full text, scores relevance,
presents to user for decision on knowledge base inclusion.
"""

import json
import logging
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "pdf-paper-extractor" / "scripts"))

from arxiv_search import ArxivSearch
from relevance_scorer import RelevanceScorer

# Try to import pdf-extractor utilities
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PyMuPDF not available - PDF screening disabled")

logger = logging.getLogger(__name__)


class ArxivPDFScreener:
    """
    Smart arXiv paper screening with full-text analysis.
    """

    def __init__(self, temp_dir: Optional[Path] = None):
        """
        Initialize PDF screener.

        Args:
            temp_dir: Temporary directory for PDF downloads (defaults to /tmp)
        """
        self.arxiv_search = ArxivSearch()
        self.scorer = RelevanceScorer()
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "arxiv_screening"
        self.temp_dir.mkdir(exist_ok=True)

    def screen_papers(self, query: str, num_candidates: int = 10,
                     present_top: int = 5) -> List[Dict]:
        """
        Search arXiv, download PDFs, score relevance, return top papers.

        Args:
            query: Search query
            num_candidates: Number of papers to download and screen
            present_top: Number of top-scoring papers to present to user

        Returns:
            List of scored papers with extraction data
        """
        if not PDF_AVAILABLE:
            logger.error("PyMuPDF required for PDF screening")
            return []

        # Step 1: Search arXiv
        logger.info(f"Searching arXiv for: {query}")
        papers = self.arxiv_search.search(query, limit=num_candidates)

        if not papers:
            logger.info("No papers found on arXiv")
            return []

        logger.info(f"Found {len(papers)} candidates, screening PDFs...")

        # Step 2: Download and score each paper
        scored_papers = []

        for i, paper in enumerate(papers, 1):
            try:
                logger.info(f"Screening {i}/{len(papers)}: {paper['title'][:50]}...")

                # Download PDF
                pdf_path = self._download_pdf(paper)

                if not pdf_path:
                    logger.warning(f"Could not download PDF for {paper['arxiv_id']}")
                    continue

                # Extract text
                full_text = self._extract_text(pdf_path)

                if not full_text:
                    logger.warning(f"Could not extract text from {pdf_path}")
                    self._cleanup(pdf_path)
                    continue

                # Score relevance
                score, reasons = self.scorer.score_paper(
                    title=paper['title'],
                    abstract=paper.get('abstract', ''),
                    full_text=full_text
                )

                # Add scoring info to paper
                paper['relevance_score'] = score
                paper['relevance_reasons'] = reasons
                paper['full_text_length'] = len(full_text)
                paper['pdf_path'] = str(pdf_path)  # Keep path for later

                scored_papers.append(paper)

                logger.info(f"  Score: {score}/100 - {', '.join(reasons[:2])}")

            except Exception as e:
                logger.error(f"Error screening paper {i}: {e}")
                continue

        # Step 3: Sort by relevance score
        scored_papers.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Return top N
        top_papers = scored_papers[:present_top]

        logger.info(f"Screening complete: {len(top_papers)} papers above threshold")

        return top_papers

    def _download_pdf(self, paper: Dict) -> Optional[Path]:
        """
        Download PDF from arXiv.

        Args:
            paper: Paper dict with arxiv_id or pdf_url

        Returns:
            Path to downloaded PDF or None
        """
        arxiv_id = paper.get('arxiv_id', '')

        # Construct PDF URL
        if 'pdf_url' in paper:
            pdf_url = paper['pdf_url']
        elif arxiv_id:
            # arXiv PDF URL format: https://arxiv.org/pdf/{arxiv_id}.pdf
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        else:
            return None

        # Download to temp directory
        safe_filename = arxiv_id.replace('/', '_') + ".pdf"
        pdf_path = self.temp_dir / safe_filename

        try:
            urllib.request.urlretrieve(pdf_url, pdf_path)
            return pdf_path
        except Exception as e:
            logger.error(f"Failed to download {pdf_url}: {e}")
            return None

    def _extract_text(self, pdf_path: Path) -> str:
        """
        Extract full text from PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Full text content
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""

            # Extract from all pages (limit to first 20 for speed)
            for page_num in range(min(20, len(doc))):
                text += doc[page_num].get_text()

            doc.close()
            return text

        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return ""

    def _cleanup(self, pdf_path: Path):
        """Delete temporary PDF."""
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete {pdf_path}: {e}")

    def cleanup_all(self):
        """Clean up all temporary PDFs."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Could not clean up temp dir: {e}")

    def present_for_decision(self, papers: List[Dict]) -> Dict[str, bool]:
        """
        Present scored papers to user for keep/discard decision.

        Args:
            papers: List of scored papers

        Returns:
            Dict mapping arxiv_id to keep decision {arxiv_id: True/False}
        """
        print("\n" + "="*70)
        print("ARXIV PDF SCREENING RESULTS")
        print("="*70 + "\n")

        decisions = {}

        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}")
            if len(paper['authors']) > 3:
                print(f"           + {len(paper['authors']) - 3} more")
            print(f"   arXiv: {paper['arxiv_id']}")
            print(f"   Date: {paper.get('published', 'N/A')}")
            print(f"\n   RELEVANCE SCORE: {paper['relevance_score']}/100")
            print(f"   Reasons: {', '.join(paper['relevance_reasons'])}")
            print()

            # In interactive mode, would prompt user here
            # For now, auto-decide based on threshold
            keep = paper['relevance_score'] >= 70

            decisions[paper['arxiv_id']] = keep

            if keep:
                print(f"   → RECOMMENDATION: KEEP (score ≥ 70)")
            else:
                print(f"   → RECOMMENDATION: DISCARD (score < 70)")

            print()

        return decisions


def screen_arxiv_papers(query: str, num_screen: int = 10, num_present: int = 5):
    """
    Convenience function for arXiv PDF screening.

    Usage:
        from arxiv_pdf_screener import screen_arxiv_papers
        top_papers = screen_arxiv_papers("epilepsy machine learning", num_screen=10)
    """
    screener = ArxivPDFScreener()

    try:
        # Screen papers
        top_papers = screener.screen_papers(query, num_screen, num_present)

        # Present for decision
        decisions = screener.present_for_decision(top_papers)

        # Cleanup temporary PDFs for discarded papers
        for paper in top_papers:
            if not decisions.get(paper['arxiv_id'], False):
                pdf_path = Path(paper['pdf_path'])
                screener._cleanup(pdf_path)

        return top_papers

    finally:
        # Always cleanup at end
        screener.cleanup_all()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "epilepsy seizure prediction machine learning"

    print(f"Screening arXiv papers for: {query}\n")
    screen_arxiv_papers(query, num_screen=5, num_present=3)
