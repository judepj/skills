# FUTURE ROADMAP: Multi-Domain Database Expansion

**Status:** Saved for later implementation
**Created:** December 2024

## Goal
Expand science-grounded skill from biomedical-focused to universal academic search with smart auto-routing.

## Current State
- 14 fields defined (mostly neuroscience/epilepsy)
- 7 databases: PubMed, arXiv, bioRxiv, Semantic Scholar, NIH Reporter, NSF Awards, Local KB
- Keyword-based field detection with weighted scoring
- Query sanitization in `paper_utils.py`

## New Domains & Databases to Add

| Domain | New Databases | Free API? |
|--------|---------------|-----------|
| **Computer Science** | DBLP, ACM DL | Yes (DBLP) |
| **Physics/Astronomy** | ADS (Astrophysics), INSPIRE-HEP | Yes |
| **Chemistry** | PubChem, ChemRxiv | Yes |
| **Economics** | RePEc, SSRN, NBER | Partial |
| **Law** | Google Scholar Cases, CourtListener | Yes |
| **Patents** | USPTO, Google Patents | Yes |
| **Clinical Trials** | ClinicalTrials.gov | Yes |

## Implementation Plan

### Phase 1: Add New Database Scripts
Create new search scripts following existing pattern:

| File | Database | API |
|------|----------|-----|
| `scripts/dblp_search.py` | DBLP | https://dblp.org/search/publ/api |
| `scripts/ads_search.py` | NASA ADS | https://api.adsabs.harvard.edu |
| `scripts/pubchem_search.py` | PubChem | https://pubchem.ncbi.nlm.nih.gov/rest/pug |
| `scripts/repec_search.py` | RePEc/IDEAS | https://ideas.repec.org/cgi-bin/htsearch |
| `scripts/clinicaltrials_search.py` | ClinicalTrials.gov | https://clinicaltrials.gov/api/v2 |
| `scripts/courtlistener_search.py` | CourtListener | https://www.courtlistener.com/api |
| `scripts/patents_search.py` | USPTO | https://developer.uspto.gov |

### Phase 2: Expand Field Keywords
Update `config/field_keywords.json` with new domains:

```json
{
  "computer_science": {
    "weight": 1.0,
    "keywords": ["algorithm", "complexity", "distributed systems", "cryptography", "compiler", "database", "software engineering"],
    "databases": ["dblp", "arxiv", "semantic_scholar"]
  },
  "physics_astronomy": {
    "weight": 1.0,
    "keywords": ["astrophysics", "cosmology", "particle physics", "quantum", "relativity", "stellar", "galaxy"],
    "databases": ["ads", "arxiv", "inspire_hep"]
  },
  "chemistry": {
    "weight": 1.1,
    "keywords": ["molecule", "reaction", "synthesis", "catalyst", "polymer", "spectroscopy", "compound"],
    "databases": ["pubchem", "pubmed", "arxiv"]
  },
  "economics": {
    "weight": 0.9,
    "keywords": ["econometric", "monetary", "fiscal", "GDP", "inflation", "market", "trade"],
    "databases": ["repec", "ssrn", "semantic_scholar"]
  },
  "law": {
    "weight": 1.0,
    "keywords": ["statute", "precedent", "jurisdiction", "tort", "contract", "litigation", "constitutional"],
    "databases": ["courtlistener", "semantic_scholar"]
  },
  "clinical_trials": {
    "weight": 1.2,
    "keywords": ["trial", "randomized", "placebo", "efficacy", "phase 1", "phase 2", "FDA"],
    "databases": ["clinicaltrials", "pubmed"]
  },
  "patents": {
    "weight": 0.8,
    "keywords": ["patent", "invention", "claims", "prior art", "USPTO", "intellectual property"],
    "databases": ["patents", "semantic_scholar"]
  }
}
```

### Phase 3: Improve Field Detector
Enhance `scripts/field_detector.py`:

1. **Add phrase matching** (not just single keywords)
2. **Hierarchical field structure** - detect "science" → "natural" → "biology"
3. **Confidence-based multi-routing** - query multiple relevant DBs

```python
def detect_and_route(query: str) -> Dict:
    """Auto-detect field and return optimal database routing."""
    fields = self.detect_fields(query)

    # Get all recommended DBs from top fields
    routing = []
    for field in fields[:3]:
        for db in field['databases']:
            if db not in [r['db'] for r in routing]:
                routing.append({
                    'db': db,
                    'priority': field['confidence'],
                    'field': field['name']
                })

    return sorted(routing, key=lambda x: x['priority'], reverse=True)
```

### Phase 4: Update SKILL.md & README
- Add new databases to documentation
- Update architecture diagram
- Add examples for each domain

## Files to Modify

| File | Change |
|------|--------|
| `scripts/dblp_search.py` | CREATE - DBLP API wrapper |
| `scripts/ads_search.py` | CREATE - NASA ADS wrapper |
| `scripts/pubchem_search.py` | CREATE - PubChem wrapper |
| `scripts/repec_search.py` | CREATE - RePEc wrapper |
| `scripts/clinicaltrials_search.py` | CREATE - ClinicalTrials.gov wrapper |
| `scripts/courtlistener_search.py` | CREATE - CourtListener wrapper |
| `scripts/patents_search.py` | CREATE - USPTO wrapper |
| `config/field_keywords.json` | UPDATE - Add new domains |
| `scripts/field_detector.py` | UPDATE - Add phrase matching, improve routing |
| `README.md` | UPDATE - Document new databases |
| `SKILL.md` | UPDATE - Add usage examples |
| `requirements.txt` | UPDATE - Add any new dependencies |

## Priority Order
1. **DBLP** (CS) - Simple REST API, high value
2. **ClinicalTrials.gov** - Complements PubMed well
3. **PubChem** (Chemistry) - NCBI family, similar to PubMed
4. **NASA ADS** (Astronomy) - Well-documented API
5. **RePEc** (Economics) - Good for social sciences
6. **CourtListener** (Law) - Free legal API
7. **USPTO** (Patents) - Complex but valuable

## API vs MCP Decision

| Approach | Pros | Cons |
|----------|------|------|
| **Direct API** | Full control, portable, proven (current approach) | More code to maintain |
| **MCP Servers** | Standardized, Claude-native, reusable | Fewer academic DB servers exist, less control |

**Recommendation: Hybrid Approach**
- Keep using **Direct APIs** for core databases (working well, full control)
- Use **MCP** only if a well-maintained server already exists
- Current academic MCP landscape is sparse - most DBs need custom wrappers anyway

**Known MCP servers for academic use:**
- None specifically for DBLP, ADS, PubChem, RePEc, CourtListener, USPTO
- Could build custom MCP servers later as a V2 enhancement

**Decision: Start with Direct APIs** (like current PubMed, arXiv implementations)

## User Decisions
- **Domains**: All 7 (CS, Physics, Chemistry, Economics, Law, Clinical Trials, Patents)
- **Auto-routing**: Yes, smart field detection with auto-routing to best DBs
