# Science-Grounded Literature Search Skill - Implementation Plan

## OBJECTIVE
Build a Claude Code skill that prevents hallucinations by requiring verified scientific sources before answering questions. The skill should intelligently detect research fields, search appropriate databases, prioritize high-impact and highly-cited papers, and refuse to answer without sources.

## USER CONTEXT
- **Research focus**: Computational neuroscience for epilepsy
- **Key areas**: Signal processing, dynamical systems, machine learning, physics-informed methods
- **Data types**: sEEG, EEG, LFP, MEG recordings
- **Applications**: Seizure prediction, epileptogenic zone localization, brain connectivity

## IMPLEMENTATION STEPS

### Step 1: Create Directory Structure
```bash
~/.claude/skills/science-grounded/
├── SKILL.md                          # Main skill file (create this LAST)
├── config/
│   ├── field_keywords.json           # Field detection keywords
│   ├── authors.json                  # Tracked researchers
│   └── journals.json                 # Journal rankings
├── scripts/
│   ├── paper_utils.py                # Shared utilities (BUILD FIRST)
│   ├── field_detector.py             # Field detection (BUILD SECOND)
│   ├── semantic_scholar_search.py    # Primary search (BUILD THIRD)
│   ├── arxiv_search.py               # arXiv with categories
│   ├── pubmed_search.py              # PubMed/PMC
│   ├── biorxiv_search.py             # bioRxiv/medRxiv
│   ├── mathoverflow_search.py        # Math Q&A
│   ├── stackexchange_search.py       # Stack Exchange
│   ├── zenodo_search.py              # Code/data archives
│   └── test_all.py                   # Integration tests
├── cache/                             # Result caching
├── logs/                              # API access logs
└── requirements.txt
```

### Step 2: Build Core Utilities (paper_utils.py)

**SAFETY REQUIREMENTS:**
```python
# CRITICAL SAFETY FEATURES TO IMPLEMENT:

1. Rate Limiting:
   - Minimum 2 second delay between API calls
   - Track requests per minute/hour
   - Exponential backoff on errors

2. Request Logging:
   - Log all external API calls to logs/api_access.log
   - Include timestamp, API, query, response code
   - Monitor for unusual patterns

3. Input Sanitization:
   - Validate all search queries (alphanumeric + spaces only)
   - Max query length: 200 characters
   - No special characters that could be injection attempts

4. Cache Management:
   - 24-hour cache expiry
   - Max cache size: 100MB
   - Hash queries for cache keys (privacy)

5. Error Handling:
   - Never expose API keys in errors
   - Graceful degradation if API fails
   - Timeout after 10 seconds per request

6. Result Validation:
   - Verify JSON structure before parsing
   - Sanitize paper titles/abstracts
   - Check for reasonable result counts (max 50)
```

**Core functions to implement:**
- `rate_limit_request(api_name)` - Enforce delays
- `sanitize_query(query)` - Clean user input
- `cache_results(query, results)` - Store with TTL
- `get_cached_results(query)` - Check cache first
- `sort_by_citations(papers)` - Citation sorting
- `calculate_impact_score(paper)` - Combined metric

### Step 3: Field Detection System (field_detector.py)

Create comprehensive keyword mappings for 15 research areas:
1. Electrophysiology (sEEG, EEG, LFP, etc.)
2. Epilepsy clinical (ictal, interictal, SOZ, etc.)
3. Signal processing (FFT, wavelets, spectrograms)
4. Linear algebra/decomposition (PCA, ICA, DMD)
5. Time series models (AR, ARIMA, VAR)
6. Nonlinear dynamics (Lyapunov, attractors, chaos)
7. Information theory (entropy, transfer entropy)
8. Machine learning (LSTM, CNN, transformers)
9. Physics-informed (SINDy, Koopman, Neural ODEs)
10. Connectivity (PLV, coherence, Granger)
11. Brain states (sleep, anesthesia, consciousness)
12. Complexity measures (sample entropy, DFA)
13. Graph theory (networks, centrality, modularity)
14. Clinical applications (seizure detection/prediction)
15. Advanced math (topology, manifolds, tensors)

### Step 4: Semantic Scholar Search (PRIMARY)

**Key features:**
- Returns: title, authors, year, DOI, abstract, **citationCount**, journal, **isOpenAccess**
- Track specific authors: Jirsa, Brunton, Sarma, etc.
- Journal impact weighting
- API: https://api.semanticscholar.org/v1/

**Safety:**
- API rate limit: 100 requests/5 minutes
- Use official Python client if available

### Step 5: arXiv Search with Category Filtering

**Categories by field:**
- Neuroscience: q-bio.NC, physics.bio-ph
- Signal processing: eess.SP, cs.SD
- Machine learning: cs.LG, stat.ML
- Dynamical systems: nlin.CD, math.DS
- Physics-informed: physics.comp-ph

### Step 6: Additional Sources (implement in order)

1. **PubMed** - Clinical epilepsy papers
2. **bioRxiv/medRxiv** - Preprints
3. **MathOverflow** - Mathematical questions
4. **Stack Exchange** - Signal processing
5. **Zenodo** - Datasets and code

### Step 7: Testing Protocol

**TEST EACH SCRIPT INDIVIDUALLY:**
```bash
# Test semantic scholar
python semantic_scholar_search.py "Koopman operator epilepsy"
# Should return papers with citations, verify sorting

# Test field detection
python field_detector.py "What is phase-amplitude coupling in sEEG?"
# Should detect: epilepsy, signal_processing, connectivity

# Test safety features
python test_all.py --test-rate-limiting
python test_all.py --test-input-validation
```

### Step 8: Create SKILL.md (FINAL STEP)

```markdown
---
name: science-grounded
description: Searches scientific literature before answering. Auto-activates for research questions about neuroscience, epilepsy, signal processing, dynamical systems, or ML. REFUSES to answer without verified sources. Prioritizes high-impact journals and cited papers.
---

# Science Grounding Protocol

## STRICT RULES:
1. ALWAYS search literature FIRST
2. NEVER cite papers without verification
3. REFUSE if no sources found: "I need to find verified sources first"
4. Prioritize: Nature/Science > Brain/Epilepsia > specialized journals

## Search workflow:
1. Detect field from keywords
2. Search Semantic Scholar first (has citations)
3. If needed, search field-specific sources
4. Sort by impact: citations × journal_tier × recency
5. Return top 5-10 papers with DOIs

## Safety checks:
- All queries sanitized
- Rate limited (2s between requests)
- Results cached for 24h
- Timeout after 10s
```

## JOURNAL RANKINGS TO IMPLEMENT

**Tier 1 (impact > 10):**
Nature, Science, Nature Neuroscience, Nature Communications, Nature Computational Science, Cell, Neuron, PNAS

**Tier 2 (impact 5-10):**
Brain, Epilepsia, NeuroImage, Journal of Neuroscience, PLOS Computational Biology, eLife, Current Biology

**Tier 3 (impact 3-5):**
Clinical Neurophysiology, IEEE TBME, Journal of Neural Engineering, Epilepsy Research

## TRACKED AUTHORS
```json
{
  "computational_epilepsy": ["Viktor Jirsa", "Fabrice Bartolomei", "William Stacey"],
  "clinical_epilepsy": ["Dario Englot", "Jorge Gonzalez-Martinez", "Gregory Worrell"],
  "data_driven": ["Steven Brunton", "J Nathan Kutz"],
  "control_theory": ["Sridevi Sarma"],
  "causality": ["Jakob Runge"],
  "neural_modeling": ["Christophe Bernard"]
}
```

## TESTING CHECKLIST
- [ ] Rate limiting works (2s delays)
- [ ] Cache prevents duplicate requests
- [ ] Input validation blocks injections
- [ ] Timeout after 10s
- [ ] Field detection accurate
- [ ] Citation sorting correct
- [ ] Journal weighting applied
- [ ] Author tracking works
- [ ] Refuses without sources
- [ ] Logs API access properly

## EXAMPLE QUERIES TO TEST
1. "What is the Epileptor model?" → Should find Jirsa papers
2. "How does SINDy work?" → Should find Brunton papers
3. "Phase-amplitude coupling in epilepsy" → Multiple sources
4. "Random made-up method XYZ" → Should REFUSE (no sources)

## DEPENDENCIES
```txt
requests>=2.28.0
arxiv>=1.4.0
biopython>=1.79  # For PubMed
ratelimit>=2.2.1
diskcache>=5.4.0  # For caching
python-dotenv>=0.19.0  # For API keys if needed
```

## SAFETY REMINDERS
⚠️ NEVER hardcode API keys - use environment variables
⚠️ ALWAYS validate user input before API calls
⚠️ LOG all external requests for audit
⚠️ IMPLEMENT timeouts to prevent hanging
⚠️ CACHE to minimize API load
⚠️ FAIL GRACEFULLY - don't crash on API errors

---
END OF IMPLEMENTATION PLAN
This document provides everything needed to build the science-grounded skill safely and effectively.