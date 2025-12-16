# Claude Code Skills

A collection of custom skills for Claude Code to enhance research workflows.

## Available Skills

| Skill | Description |
|-------|-------------|
| [science-grounded](./science-grounded/) | Prevent scientific hallucinations by requiring verified sources for all research claims. Provides access to PubMed, arXiv, bioRxiv, Semantic Scholar, and other academic databases. |

## Installation

Each skill can be installed independently. See the README in each skill folder for specific installation instructions.

### General Setup

1. Clone this repository
2. Navigate to the desired skill folder
3. Follow the skill-specific installation instructions

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
├── README.md                 # This file
├── science-grounded/         # Literature search and citation verification
│   ├── README.md
│   ├── SKILL.md
│   ├── requirements.txt
│   ├── scripts/
│   └── config/
└── [future-skill]/           # Additional skills
```

## License

These skills are provided for research and educational purposes.
