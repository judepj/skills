---
name: latex-report-generator
version: 0.9.0-beta
description: Generate professional LaTeX reports with paragraph-based prose, interactive figure selection, and flexible citation styles. Integrates with web-scraper, literature-review, and science-grounded skills.
author: Community
tags: [latex, report-generation, academic-writing, citations, figures, pdf, web-scraper-integration, literature-review, scientific-writing, beta]
---

# LaTeX Report Generator Skill

**Professional LaTeX report generation with interactive figure curation and flexible formatting**

## When to Use This Skill

- Generate reports from web-scraper output with curated figures
- Create scientific manuscripts with proper citations (IMRAD structure)
- Format literature reviews with bibliography
- Produce technical reports with professional layout
- Convert bullet-point content to flowing academic paragraphs

## Key Features

### 1. Two-Phase Generation Workflow

**Phase 1: Draft Generation (Fast)**
- Auto-select best figures using scoring algorithm
- Generate `figure_manifest.json` for review
- Create draft LaTeX + PDF preview
- Non-interactive, completes in seconds

**Phase 2: Final Generation (Curated)**
- Edit `figure_manifest.json` to select figures and write captions
- Regenerate with `--use-manifest --finalize`
- Produce publication-ready PDF

### 2. Smart Figure Selection

Auto-selection scores images (0-100) based on:
- **Size** (25 pts): Prefer 200KB-2MB
- **Dimensions** (25 pts): Prefer ≥1200px width
- **Alt text** (20 pts): Descriptive text scores higher
- **Filename** (15 pts): Descriptive names > hash names
- **Aspect ratio** (10 pts): Landscape/square preferred
- **Format** (5 pts): PNG/PDF > JPG

### 3. Content Processing

- **Bullets → Paragraphs**: Converts bullet points to flowing academic prose
- **Transition words**: Adds "however", "moreover", "in contrast", etc.
- **Section-aware**: Preserves bullets in Methods criteria lists, etc.
- **Terminology preservation**: Keeps scientific terms, citations, data intact

### 4. Multiple Citation Styles

Supported styles (configurable per report):
- **APA**: (Author et al., Year) - Psychology/Social Sciences
- **Vancouver**: [1], [2] - Medical/Biomedical
- **Nature**: ¹, ² - High-impact journals
- **IEEE**: [1], [2] - Engineering

### 5. Skill Integration

- **web-scraper**: Format scraped content with images
- **literature-review**: Extract citations from markdown
- **science-grounded**: Add verified papers to bibliography
- **Standalone**: Works with manual input

## Quick Start

### Basic Usage: Generate from Web-Scraper Output

```bash
# Step 1: Generate draft (auto-selected figures)
cd .claude/skills/latex-report-generator
python scripts/cli.py \
    --source web-scraper \
    --input ../web-scraper/data/precisionneuro/scrape_results.json \
    --output ./data/reports/precisionneuro \
    --title "Brain-Computer Interface Technology: Precision Neuroscience" \
    --author "Research Team" \
    --citation-style vancouver \
    --max-figures 6

# Outputs:
#   data/reports/precisionneuro/figure_manifest.json
#   data/reports/precisionneuro/draft_report.tex
#   data/reports/precisionneuro/draft_report.pdf
#   data/reports/precisionneuro/figures/ (6 auto-selected images)

# Step 2: Review draft
open data/reports/precisionneuro/draft_report.pdf

# Step 3: Edit figure manifest
vim data/reports/precisionneuro/figure_manifest.json
# - Set include: false for unwanted figures
# - Write descriptive captions
# - Adjust widths, placements

# Step 4: Generate final report
python scripts/cli.py \
    --source web-scraper \
    --input ../web-scraper/data/precisionneuro/scrape_results.json \
    --output ./data/reports/precisionneuro \
    --use-manifest \
    --finalize

# Final output:
#   data/reports/precisionneuro/final_report.pdf
```

### Generate Scientific Manuscript

```bash
python scripts/cli.py \
    --template scientific_paper \
    --title "Novel Brain-Computer Interface Achieves High-Bandwidth Communication" \
    --author "Smith J, Doe A, Johnson B" \
    --abstract "Abstract text..." \
    --sections methods.md results.md discussion.md \
    --bibliography papers.json \
    --citation-style nature \
    --output ./data/reports/manuscript
```

### Generate from Multiple Sources

```bash
python scripts/cli.py \
    --config multi_source_config.json \
    --output ./data/reports/comprehensive

# multi_source_config.json:
{
  "sources": [
    {"type": "web-scraper", "path": "scrape_results.json", "use_images": true},
    {"type": "science-grounded", "path": "verified_papers.json", "add_to_bibliography": true}
  ],
  "report": {
    "title": "Comprehensive BCI Analysis",
    "template": "technical_report",
    "bibliography_style": "ieee"
  }
}
```

## Figure Manifest Format

The `figure_manifest.json` file controls which figures are included and their captions:

```json
{
  "version": "1.0",
  "auto_selected": true,
  "figures": [
    {
      "id": "fig1",
      "source_path": "/path/to/image.png",
      "filename": "brain_interface.png",
      "caption": "Layer 7 Cortical Interface showing high-resolution neural activity mapping. Edit this caption to describe the figure.",
      "short_caption": "Layer 7 Interface",
      "label": "fig:layer7",
      "width": 0.9,
      "placement": "htbp",
      "include": true,
      "score": 95.5,
      "notes": "Main technology figure - must include"
    }
  ]
}
```

**Editing the Manifest**:
1. Set `include: false` to exclude a figure
2. Rewrite `caption` with descriptive text (keep it LaTeX-compatible)
3. Adjust `width` (0.1-1.0 = fraction of text width)
4. Change `placement`:
   - `h` = here
   - `t` = top of page
   - `b` = bottom of page
   - `!` = force placement
   - `htbp` = try here, then top, bottom, separate page

## Configuration Files

### Citation Styles (`config/citation_styles.yaml`)

```yaml
apa:
  name: "APA 7th Edition"
  inline_format: "({authors}, {year})"
  bibliography_format: "{authors}. ({year}). {title}. *{journal}*, *{volume}*({issue}), {pages}."
  sort_method: "alphabetical"
  max_authors_inline: 3

vancouver:
  name: "Vancouver (ICMJE)"
  inline_format: "[{index}]"
  bibliography_format: "{authors}. {title}. {journal}. {year};{volume}({issue}):{pages}."
  sort_method: "citation_order"
```

### Report Types (`config/report_types.yaml`)

```yaml
scientific_paper:
  name: "Scientific Manuscript (IMRAD)"
  template: "templates/report_types/scientific_paper.tex"
  paragraph_mode: true
  allowed_bullets:
    - "Methods::Inclusion Criteria"
    - "Methods::Exclusion Criteria"
```

## Content Processing: Bullets to Paragraphs

### Example Conversion

**Input (bullet points)**:
```
- CRISPR delivery methods investigated
  * AAV vectors: 65-85% efficiency
  * Lipid nanoparticles: 40-60% efficiency, better safety
- Immunogenicity concerns with viral vectors
```

**Output (flowing paragraphs)**:
```
Multiple delivery approaches have been investigated for therapeutic gene
editing. Viral vectors (AAV) demonstrated high transduction efficiency
ranging from 65-85%, though they raised immunogenicity concerns. In
contrast, lipid nanoparticles showed lower efficiency (40-60%) but offered
improved safety profiles.
```

### How It Works

1. Parses bullet hierarchy
2. Groups related bullets (max 3-4 per paragraph)
3. Expands to complete sentences with subject-verb-object
4. Adds transition words (however, moreover, subsequently)
5. Preserves scientific terminology and citations

### When Bullets Are Kept

Some sections allow bullets (configured in `report_types.yaml`):
- Methods: Inclusion/exclusion criteria
- Materials lists
- Numbered procedures

## Integration with Other Skills

### Web-Scraper Integration

**Input**: `scrape_results.json` + `images/download_manifest.json`

**Process**:
1. Parses scraped content (title, text, metadata)
2. Scores all downloaded images
3. Auto-selects top N figures
4. Converts content to paragraphs
5. Generates LaTeX report

**Example**:
```python
from source_integrators import WebScraperIntegrator

integrator = WebScraperIntegrator()
content = integrator.parse('../web-scraper/data/precisionneuro/scrape_results.json')
# Returns structured content ready for LaTeX generation
```

### Literature-Review Integration

**Input**: Markdown file with citations

**Process**:
1. Extracts citations (DOI, author-year, title-journal formats)
2. Converts to BibTeX entries
3. Formats bibliography in specified style
4. Converts markdown sections to LaTeX

### Science-Grounded Integration

**Input**: `verified_papers.json`

**Process**:
1. Parses paper metadata (DOI, PMID, authors, journal, etc.)
2. Generates BibTeX entries
3. De-duplicates by DOI/PMID
4. Merges with existing bibliography

## LaTeX Templates

### Available Templates

- **web_scraping.tex**: Web scraping summary reports
- **scientific_paper.tex**: IMRAD structure for manuscripts
- **literature_review.tex**: Review articles with extensive citations
- **technical_report.tex**: General technical documentation

### Custom Templates

Templates use Jinja2 with LaTeX-safe delimiters:

```latex
\documentclass[11pt,a4paper]{article}

\title{\VAR{title}}
\author{\VAR{authors}}

\begin{document}
\maketitle

\BLOCK{for section in sections}
\section{\VAR{section.title}}
\VAR{section.content}

\BLOCK{if section.figures}
\BLOCK{for fig in section.figures}
\begin{figure}[\VAR{fig.placement}]
\centering
\includegraphics[width=\VAR{fig.width}\textwidth]{\VAR{fig.path}}
\caption{\VAR{fig.caption}}
\label{\VAR{fig.label}}
\end{figure}
\BLOCK{endfor}
\BLOCK{endif}
\BLOCK{endfor}

\end{document}
```

**Delimiters**:
- `\VAR{...}` - Variable insertion
- `\BLOCK{...}` - Control blocks (for, if)
- `\#{...}` - Comments

## Command-Line Interface

### Full CLI Options

```bash
python scripts/cli.py [OPTIONS]

Required (choose one):
  --source TYPE              Source type: web-scraper, literature-review, science-grounded
  --config FILE              Multi-source configuration JSON

Input:
  --input FILE               Input file path
  --title TEXT               Report title
  --author TEXT              Author name(s)
  --abstract TEXT            Abstract text
  --sections FILE [FILE...]  Section content files
  --bibliography FILE        Bibliography JSON/BibTeX

Output:
  --output DIR               Output directory
  --template TYPE            Template: web_scraping, scientific_paper, literature_review, technical_report
  --citation-style STYLE     Citation style: apa, vancouver, nature, ieee

Figures:
  --max-figures N            Maximum figures to auto-select (default: 5)
  --figures-dir DIR          Additional figures directory
  --use-manifest             Use existing figure_manifest.json
  --finalize                 Generate final report (use with --use-manifest)

Compilation:
  --no-compile               Skip PDF compilation
  --latex-engine ENGINE      LaTeX engine: pdflatex, xelatex, lualatex (default: pdflatex)
  --keep-aux                 Keep auxiliary files (.aux, .log, .out)

Other:
  --verbose                  Verbose output
  --help                     Show help message
```

## Troubleshooting

### "LaTeX compilation failed"

**Cause**: Missing LaTeX packages or syntax errors

**Solution**:
1. Check the `.log` file in output directory
2. Install missing packages: `tlmgr install <package>`
3. Verify LaTeX special characters are escaped
4. Run with `--keep-aux` to inspect intermediate files

### "No figures found in source"

**Cause**: Image directory not found or no compatible images

**Solution**:
1. Verify web-scraper downloaded images to `images/` directory
2. Check `download_manifest.json` exists
3. Ensure images are PNG, JPG, or PDF format
4. Use `--figures-dir` to specify additional directory

### "Citation extraction failed"

**Cause**: Unrecognized citation format

**Solution**:
1. Check input file has citations in supported formats
2. Verify DOI format: `10.1234/journal.year.id`
3. Verify author-year format: `(Author et al., Year)`
4. Add citations manually to `references.bib`

### "Figure captions are placeholders"

**This is expected!**

**Workflow**:
1. Draft report has `[TODO: Add caption]` placeholders
2. Edit `figure_manifest.json` to write real captions
3. Regenerate with `--use-manifest --finalize`
4. Final report will have your captions

## Files Created

```
output_directory/
├── figure_manifest.json      # Figure selection and captions (edit this!)
├── draft_report.tex          # Draft LaTeX source
├── draft_report.pdf          # Draft PDF preview
├── final_report.tex          # Final LaTeX source
├── final_report.pdf          # Final publication-ready PDF
├── references.bib            # BibTeX bibliography
├── figures/                  # Copied figure files
│   ├── fig1.png
│   ├── fig2.jpg
│   └── ...
└── logs/
    └── compilation.log       # LaTeX compilation log
```

## Python API

### Programmatic Usage

```python
from latex_generator import LatexGenerator, ReportType, CitationStyle
from figure_manager import FigureManager
from compiler import LatexCompiler

# Initialize generator
generator = LatexGenerator(
    report_type=ReportType.WEB_SCRAPING,
    citation_style=CitationStyle.VANCOUVER
)

# Prepare content
content = {
    'title': 'My Report',
    'author': 'Author Name',
    'sections': [
        {'title': 'Introduction', 'content': 'Text...'},
        {'title': 'Results', 'content': 'Text...'}
    ]
}

# Generate LaTeX
tex_file = generator.generate(content, output_file='report.tex')

# Compile to PDF
compiler = LatexCompiler()
pdf_file = compiler.compile(tex_file, cleanup=True)
```

### Figure Management API

```python
from figure_manager import FigureManager

fm = FigureManager(output_dir='./output')

# Scan for images
images = fm.scan_images([Path('./images')])

# Auto-select top figures
selected = fm.auto_select_figures(images, max_figures=5)

# Generate manifest for user editing
fm.generate_selection_file(selected)

# Load user-edited manifest
curated = fm.load_user_selections()
```

## Examples

See `examples/` directory for:
- `example_web_scraping.py` - Generate from web-scraper output
- `example_manuscript.py` - Create scientific manuscript
- `example_literature_review.py` - Format literature review
- `example_multi_source.py` - Combine multiple sources

## Testing

```bash
# Run all tests
cd tests
python -m pytest

# Test specific module
python -m pytest test_content_processor.py -v

# Test with coverage
python -m pytest --cov=../scripts
```

## Limitations

- **Static images only**: No video/animation support
- **LaTeX required**: Must have LaTeX distribution installed
- **PDF output**: Cannot generate other formats (DOCX, HTML) directly
- **English-focused**: Transition words and prose generation optimized for English
- **Manual figure curation**: Auto-selection requires user review for best results

## Version History

### v1.0.0 (2025-12-12)
- Initial release
- Two-phase generation workflow (draft → edit → final)
- Smart figure auto-selection with scoring algorithm
- Bullets-to-paragraphs content processing
- Multiple citation styles (APA, Vancouver, Nature, IEEE)
- Integration with web-scraper, literature-review, science-grounded skills
- Jinja2 templates with LaTeX-safe delimiters
- CLI and Python API

## Dependencies

See `requirements.txt`:
- jinja2 >= 3.1.0
- pyyaml >= 6.0
- requests >= 2.28.0 (optional)
- markdown >= 3.4.0
- pytest >= 7.0.0 (dev)

## License

Educational and research use only.

## Support

For issues or questions, see the troubleshooting section above or check the implementation plan.
