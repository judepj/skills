# Claude Code Skills

A collection of custom skills for Claude Code to enhance research workflows.

## Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [science-grounded](./science-grounded/) | Prevent scientific hallucinations by requiring verified sources for all research claims. Provides access to PubMed, arXiv, bioRxiv, Semantic Scholar, and other academic databases. | Stable |
| [latex-report-generator](./latex-report-generator/) | Generate professional LaTeX reports with paragraph-based prose, interactive figure selection, and flexible citation styles. Supports multiple report types and citation formats. | Beta |

## Skill Chaining

These skills are designed to work together. For example:

1. **Literature Search → Report Generation**
   - Use `science-grounded` to search for papers on a topic
   - Feed the results into `latex-report-generator` to create a formatted literature review

2. **Web Scraping → Report Generation**
   - Scrape content from websites
   - Use `latex-report-generator` to convert it into a professional PDF report

3. **Complete Research Workflow**
   ```
   science-grounded (search) → latex-report-generator (format) → PDF output
   ```

## Installation

Each skill can be installed independently. See the README in each skill folder for specific installation instructions.

### General Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/judepj/skills.git
   ```
2. Navigate to the desired skill folder
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the skill to your Claude Code skills directory:
   ```bash
   cp -r skill-name ~/.claude/skills/custom/
   ```

## Adding New Skills

To add a new skill:

1. Create a new folder with a descriptive name (e.g., `my-new-skill/`)
2. Include at minimum:
   - `README.md` - Documentation
   - `SKILL.md` - Claude Code skill definition
   - `requirements.txt` - Python dependencies (if applicable)
3. Update this README to include the new skill in the table above

## Repository Structure

```
skills/
├── README.md                     # This file
├── science-grounded/             # Literature search and citation verification
│   ├── README.md
│   ├── SKILL.md
│   ├── requirements.txt
│   ├── scripts/
│   └── config/
└── latex-report-generator/       # LaTeX report generation (beta)
    ├── README.md
    ├── SKILL.md
    ├── requirements.txt
    ├── scripts/
    ├── templates/
    └── config/
```

## License

These skills are provided for research and educational purposes.
