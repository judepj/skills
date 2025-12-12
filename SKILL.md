---
name: science-grounded
version: 1.0.0
description: Prevent scientific hallucinations by requiring verified sources for all research claims
author: Science-Grounded Research Assistant
tags: [research, science, literature-search, anti-hallucination, neuroscience, epilepsy]
---

# Science-Grounded Literature Search

## CRITICAL RULE: NO HALLUCINATED CITATIONS

**NEVER cite a paper without verification through this skill's search functions.**

When asked about scientific topics, especially in:
- Neuroscience / Epilepsy / sEEG
- Signal processing / Dynamical systems
- Machine learning / Physics-informed methods
- Computational models / Brain connectivity

You MUST:
1. Search for verified sources FIRST using this skill
2. Only cite papers found and verified by the search
3. If no relevant sources found, REFUSE to answer rather than hallucinate

## How to Use This Skill

### Step 1: Detect the Research Field

```python
import sys
sys.path.append('/Users/jsavarraj/Dropbox/GPTQueries/Brunton/neural_ODE/.claude/skills/science-grounded/scripts')
from field_detector import FieldDetector

detector = FieldDetector()
result = detector.detect_fields(query)
fields = result['detected_fields']
databases = result['recommended_sources']
```

### Step 2: Search for Papers and Grants

**We now have 7 search engines available:**

1. **PubMed** - Best for clinical/medical papers:
```python
from pubmed_search import PubMedSearch
searcher = PubMedSearch()
papers = searcher.search(query, limit=10, recent_only=True)
# Or search for reviews: searcher.search_reviews(query)
# Or clinical trials: searcher.search_clinical_trials(query)
```

2. **arXiv** - Best for preprints in physics/math/CS/neuroscience:
```python
from arxiv_search import ArxivSearch
searcher = ArxivSearch()
papers = searcher.search(query, limit=10)
```

3. **bioRxiv/medRxiv** - Best for biological/medical preprints:
```python
from biorxiv_search import BiorxivSearch
searcher = BiorxivSearch()
papers = searcher.search(query, server="both", limit=10)
# Or just bioRxiv: server="biorxiv"
# Or just medRxiv: server="medrxiv"
```

4. **Semantic Scholar** - Best for citation counts (currently rate-limited):
```python
from semantic_scholar_search import SemanticScholarSearch
searcher = SemanticScholarSearch()
papers = searcher.search(query, limit=10)
```

5. **NIH RePORTER** - Best for NIH grants and funding information:
```python
from nih_reporter_search import NIHReporterSearch
searcher = NIHReporterSearch()
projects = searcher.search_projects(query, limit=10, recent_only=True)
# Or search by PI: searcher.search_by_pi("Principal Investigator Name")
# Or by institution: searcher.search_by_institution("University Name")
# Or by topic with funding filter: searcher.search_by_topic(query, min_funding=500000)
```

6. **NSF Awards** - Best for NSF grants across all science/engineering disciplines:
```python
from nsf_awards_search import NSFAwardsSearch
searcher = NSFAwardsSearch()
awards = searcher.search_awards(query, limit=10, recent_only=True)
# Or search by PI: searcher.search_by_pi("Principal Investigator Name")
# Or by institution: searcher.search_by_institution("University Name")
# Or by topic with funding filter: searcher.search_by_topic(query, min_funding=500000)
```

### Step 3: Verify and Present Results

```python
# Papers are already sorted by impact score
for paper in papers[:5]:
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'][:3])}")
    print(f"Year: {paper['year']}")
    print(f"Citations: {paper.get('citation_count', 'N/A')}")
    if paper.get('doi'):
        print(f"DOI: https://doi.org/{paper['doi']}")
```

### Step 4: PDF Review Workflow (Enhanced Discovery)

When finding highly promising papers (impact_score > 150 or citation_count > 50), request PDF for detailed review:

```python
from paper_tracker import PaperTracker
from literature_mapper import LiteratureMapper

tracker = PaperTracker()
mapper = LiteratureMapper()

# After finding papers via API search
for paper in papers[:5]:
    # Track the search result
    paper_id = tracker.track_search_result(paper, query)

    # Check if paper is highly promising
    if paper.get('impact_score', 0) > 150 or paper.get('citation_count', 0) > 50:
        # Request PDF review
        tracker.request_pdf_review(paper_id)

        print(f"\n📄 HIGHLY PROMISING PAPER FOUND:")
        print(f"   Title: {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}")
        print(f"   Impact Score: {paper.get('impact_score', 'N/A')}")
        print(f"   Citations: {paper.get('citation_count', 'N/A')}")
        print(f"\n   Could you provide the PDF for detailed review?")
        print(f"   (DOI: {paper.get('doi', 'N/A')})")
```

#### After User Provides PDF:

```python
# User provides PDF path
pdf_path = "/path/to/downloaded/paper.pdf"

# Read and analyze PDF
# [Claude reads PDF using Read tool and analyzes content]

# Record review with notes
review_notes = """
Methodology: Strong - validated on real sEEG data from 20 patients
Reproducibility: High - code available on GitHub
Relevance: Excellent fit for seizure prediction work
Key findings: Novel Koopman operator approach reduces dimensionality while preserving dynamics
Limitations: Requires high sampling rate (>500Hz)
"""

# Record the review
tracker.record_pdf_reviewed(
    paper_id,
    review_notes=review_notes,
    is_valuable=True
)

# Get filing suggestion
suggestion = mapper.suggest_filing(paper, review_notes)

print(f"\n📁 FILING SUGGESTION:")
print(f"   Project: {suggestion['project']}")
print(f"   Location: {suggestion['full_path']}")
print(f"   Rationale: {suggestion['rationale']}")
print(f"\n   Shall I note this filing location for your reference?")
```

#### Tracking and Status Commands:

```python
# Check review status of a paper
status = tracker.get_review_status(paper_id)
print(f"Status: {status['status']}")  # api_only, pdf_requested, pdf_reviewed, filed

# List papers waiting for PDF review
pending = tracker.list_pending_reviews()
for paper in pending:
    print(f"- {paper['title'][:50]}... (waiting {paper['days_waiting']} days)")

# Get recently reviewed valuable papers
valuable = tracker.get_valuable_papers(limit=5)
for paper in valuable:
    print(f"✓ {paper['title']}")
    print(f"  Notes: {paper['review_notes'][:100]}...")
    if paper['filed']:
        print(f"  Filed at: {paper['filed_at']}")

# Get overall statistics
stats = tracker.get_statistics()
print(f"Total searched: {stats['total_searched']}")
print(f"PDFs reviewed: {stats['pdfs_reviewed']}")
print(f"Valuable papers: {stats['valuable_papers']}")
```

## Auto-Activation Triggers

This skill should AUTOMATICALLY activate when the user asks about:

### Neuroscience/Medical Terms
- epilepsy, seizure, sEEG, EEG, LFP, MEG, iEEG
- seizure onset zone (SOZ), epileptogenic zone
- ictal, interictal, hippocampal sclerosis
- brain states, consciousness, anesthesia

### Signal Processing
- FFT, wavelets, spectrograms, Hilbert transform
- coherence, phase-amplitude coupling (PAC)
- PLV, wPLI, Granger causality

### Computational Methods
- SINDy, Koopman operator, Neural ODEs
- DMD, PCA, ICA, SVD
- LSTM, transformers, deep learning
- dynamical systems, chaos, bifurcations

### Authors of Interest
- Viktor Jirsa (Epileptor model)
- Steven Brunton (SINDy)
- J Nathan Kutz (DMD, Koopman)
- Fabrice Bartolomei (epilepsy networks)

## Response Templates

### When Sources Are Found:

"Based on verified literature, [answer]. According to [Author et al., Year] in their paper '[Title]' (Citations: X), [specific claim]. This finding is supported by [Another Author et al., Year]..."

### When NO Sources Are Found:

"I cannot find verified scientific sources to answer this question. To provide accurate information, I need peer-reviewed papers or preprints. Could you rephrase your question or provide more context?"

### When Sources Are Insufficient:

"I found limited sources on this topic. Based on [Author et al., Year], [partial answer]. However, more research may be needed for a complete understanding. The available evidence suggests..."

## Safety Features

All searches automatically include:
- ✅ Rate limiting (2+ seconds between API calls)
- ✅ Input sanitization (max 200 chars, no injections)
- ✅ Result caching (24-hour TTL)
- ✅ Request logging
- ✅ 10-second timeouts

## Example Usage

```python
# User asks: "What are the latest treatments for drug-resistant epilepsy?"

# 1. Detect field
from field_detector import FieldDetector
detector = FieldDetector()
fields = detector.detect_fields("latest treatments drug-resistant epilepsy")
# Returns: ['epilepsy_clinical', 'clinical_applications']

# 2. Search multiple databases for comprehensive coverage
all_papers = []

# Search PubMed for clinical papers
from pubmed_search import PubMedSearch
pubmed = PubMedSearch()
clinical_papers = pubmed.search("drug-resistant epilepsy treatment", limit=5, recent_only=True)
all_papers.extend(clinical_papers)

# Search medRxiv for recent clinical preprints
from biorxiv_search import BiorxivSearch
biorxiv = BiorxivSearch()
preprints = biorxiv.search("drug-resistant epilepsy", server="medrxiv", limit=5)
all_papers.extend(preprints)

# Search arXiv for computational/ML approaches
from arxiv_search import ArxivSearch
arxiv = ArxivSearch()
ml_papers = arxiv.search("epilepsy treatment machine learning", limit=5)
all_papers.extend(ml_papers)

# Search NIH grants for funded research
from nih_reporter_search import NIHReporterSearch
nih = NIHReporterSearch()
nih_grants = nih.search_projects("drug-resistant epilepsy", limit=5, recent_only=True)

# Search NSF awards for funded research
from nsf_awards_search import NSFAwardsSearch
nsf = NSFAwardsSearch()
nsf_awards = nsf.search_awards("epilepsy machine learning", limit=5, recent_only=True)

# 3. Present findings
if all_papers:
    # "Based on recent literature from PubMed and medRxiv..."
    # "According to Smith et al. (2024) in Epilepsia..."
    # [Provide comprehensive answer based on multiple sources]

    # Also mention funded research if relevant
    if nih_grants or nsf_awards:
        # "Current NIH-funded research includes work by Dr. X at Institution Y..."
        # "with $X million in funding focusing on..."
        # "NSF is funding related work on computational approaches by Dr. Y..."
else:
    # "I cannot find verified sources about drug-resistant epilepsy treatments..."
    # [REFUSE to answer without sources]
```

## Quality Metrics

Papers are ranked by impact score:
- **Tier 1 journals** (Nature, Science, Cell): 3x multiplier
- **Tier 2 journals** (Brain, Epilepsia): 2x multiplier
- **Tier 3 journals** (Clinical Neurophysiology): 1.5x multiplier
- **Recent papers** (< 3 years): 1.2x bonus
- **Citation count** is the base metric

## Important Notes

1. **Better to refuse than hallucinate** - If you can't find sources, say so
2. **Always cite with details** - Include authors, year, title, and DOI when available
3. **Prioritize high-impact venues** - Nature/Science > Brain/Epilepsia > others
4. **Check relevance** - Ensure papers actually address the user's question
5. **Be transparent** - Tell users when evidence is limited or conflicting

## Troubleshooting

- **Semantic Scholar rate limit (429 error)**: Use PubMed, arXiv, or bioRxiv instead
- **No results found**: Try broader search terms or search multiple databases
- **Timeout errors**: Retry with shorter query
- **PubMed returns no PMIDs**: Check if query is too specific, try removing filters
- **bioRxiv/medRxiv empty results**: Papers may be too recent, try broader date range
- **NIH RePORTER no results**: Try broader keywords, check fiscal year filters
- **NSF Awards no results**: Try broader keywords, note API has 3000 result limit
- **Cache issues**: Delete cache directory and restart

## Debug Commands

```python
# Check what fields were detected
print(f"Detected fields: {fields}")
print(f"Recommended databases: {databases}")

# View search logs
with open('/Users/jsavarraj/Dropbox/GPTQueries/Brunton/neural_ODE/.claude/skills/science-grounded/logs/api_access.log', 'r') as f:
    print(f.read()[-1000:])  # Last 1000 chars

# Clear cache if needed
import shutil
shutil.rmtree('/Users/jsavarraj/Dropbox/GPTQueries/Brunton/neural_ODE/.claude/skills/science-grounded/cache')
```

Remember: **NEVER make up citations. ALWAYS search first. REFUSE if unsure.**