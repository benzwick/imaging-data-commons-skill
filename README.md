# Imaging Data Commons Skill

[![Tests](https://github.com/benzwick/imaging-data-commons-skill/actions/workflows/test.yml/badge.svg)](https://github.com/benzwick/imaging-data-commons-skill/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Renovate enabled](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com/)

A [Claude Code skill](https://docs.anthropic.com/en/docs/claude-code/skills) for querying and downloading public cancer imaging data from the [NCI Imaging Data Commons](https://portal.imaging.datacommons.cancer.gov/).

## Installation

Add this skill to your Claude Code project:

```bash
# Option 1: Add as git submodule (recommended for version control)
cd your-project
git submodule add git@github.com:benzwick/imaging-data-commons-skill.git .claude/skills/imaging-data-commons

# Option 2: Clone directly
cd your-project/.claude/skills
git clone git@github.com:benzwick/imaging-data-commons-skill.git imaging-data-commons

# Option 3: Symlink from another location
ln -s /path/to/imaging-data-commons-skill .claude/skills/imaging-data-commons
```

## Dependencies

Install the required Python packages:

```bash
uv sync
```

## Usage

Once installed, Claude Code can use this skill to:

- Query IDC metadata for CT, MR, PET, and pathology images
- Download DICOM files with license filtering
- Visualize images in browser
- Validate downloaded data integrity

Example prompts:
- "Find all chest CT scans in the NLST collection"
- "Download brain MRI data with CC-BY license only"
- "How many segmentations are available for lung cancer?"

## Running Tests

```bash
cd imaging-data-commons-skill
uv sync --extra test
uv run pytest
```

## Development

### Setting Up Reference for Comparison

To compare this skill with the official ImagingDataCommons/idc-claude-skill, clone it into the `_reference` directory (gitignored):

```bash
mkdir -p _reference
git clone https://github.com/ImagingDataCommons/idc-claude-skill.git _reference/idc-claude-skill
```

Then use the `/sync-official` skill to generate comparison reports and apply improvements.

## Structure

```
├── SKILL.md              # Main skill documentation (read by Claude)
├── references/           # Detailed reference documentation
├── scripts/              # Utility scripts (batch_download.py, validate_download.py)
└── tests/                # Pytest test suite
```

## Acknowledgments

This skill was originally created by [Andrey Fedorov](https://github.com/fedorov) as part of the [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) collection.

## License

MIT License. IDC data has individual licensing (CC-BY, CC-NC) - see SKILL.md for details.

## Related IDC Skills

Other Claude Code skills for Imaging Data Commons:

- [ImagingDataCommons/idc-claude-skill](https://github.com/ImagingDataCommons/idc-claude-skill) - Official IDC skill by Andrey Fedorov. Search datasets, review licensing, generate citations, access DICOM viewers.
- [mhalle/idc-skill](https://github.com/mhalle/idc-skill) - Query 160+ collections, generate download scripts, analyze DICOM metadata, supports restricted network environments.
- [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills) - Collection of 140+ scientific skills including the original IDC skill. Covers bioinformatics, cheminformatics, proteomics, and more.

## Resources

- [Claude Code Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [IDC Portal](https://portal.imaging.datacommons.cancer.gov/)
- [IDC Documentation](https://learn.canceridc.dev/)
