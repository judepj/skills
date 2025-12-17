# LaTeX Report Generator

> **Beta Version** - This skill is under active development. Features may change.

A Claude Code skill for generating professional LaTeX reports with paragraph-based prose, interactive figure selection, and flexible citation styles.

## Features

- **Two-phase workflow**: Fast draft generation → curated final output
- **Smart figure selection**: Automatic scoring and ranking of images
- **Content processing**: Converts bullets to flowing academic paragraphs
- **Multiple report types**: Scientific papers, literature reviews, technical reports
- **Citation styles**: APA, Vancouver, Nature, IEEE, Chicago, AMA
- **Integrations**: Works with web-scraper, literature-review, and science-grounded skills

## Installation

1. Copy this folder to `.claude/skills/custom/latex-report-generator/`
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure LaTeX is installed (`pdflatex` available in PATH)

## Quick Start

### Generate a report from web-scraper output:

```bash
python scripts/generate_report.py data/scraped_content.json \
    --output reports/my_report \
    --title "My Report Title" \
    --author "Your Name"
```

### Two-phase workflow:

1. **Phase 1** - Generate draft with auto-selected figures:
   ```bash
   python scripts/generate_report.py input.json --output reports/draft
   ```

2. **Review** `reports/draft/figure_manifest.json` and edit captions

3. **Phase 2** - Generate final with curated figures:
   ```bash
   python scripts/generate_report.py input.json --output reports/draft --use-manifest --finalize
   ```

## Report Types

| Type | Structure | Use Case |
|------|-----------|----------|
| `web_scraping` | Summary + Figures | Reports from scraped web content |
| `scientific_paper` | IMRAD | Research manuscripts |
| `literature_review` | Systematic review | Literature surveys |
| `technical_report` | Flexible sections | Documentation |
| `conference_paper` | Short format | Conference submissions |

## Configuration

See `config/` for customization options:
- `default_config.yaml` - General settings
- `report_types.yaml` - Report type definitions
- `citation_styles.yaml` - Citation format specifications

## License

MIT
