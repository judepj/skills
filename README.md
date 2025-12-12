# Science-Grounded Literature Search Skill

## Quick Start for Implementation

**IMPORTANT**: Read `IMPLEMENTATION_PLAN.md` for full details!

## What This Is
A Claude Code skill that prevents scientific hallucinations by requiring verified sources before answering research questions.

## Implementation Order
1. Read `IMPLEMENTATION_PLAN.md` thoroughly
2. Build `scripts/paper_utils.py` with ALL safety features
3. Test safety features extensively
4. Build `field_detector.py`
5. Build `semantic_scholar_search.py` and test
6. Add other search scripts one by one, testing each
7. Create `SKILL.md` as the FINAL step

## Safety First!
- **Rate limiting**: 2+ seconds between API calls
- **Input validation**: Sanitize all queries
- **Logging**: Track all API access
- **Timeouts**: 10 second max per request
- **Caching**: 24-hour TTL to reduce API load

## Testing Required
Test EACH script individually before integration:
```bash
python scripts/semantic_scholar_search.py "test query"
python scripts/test_all.py --test-safety
```

## Contact
If you have questions about the research context, check `INFORMAL_NOTES.md`

---
**Remember**: The user values accuracy over speed. Better to implement safely and correctly than to rush.